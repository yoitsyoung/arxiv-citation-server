"""
Paper storage management.

Handles downloading, converting, and storing arXiv papers
as human-readable markdown files.

Storage structure:
    ~/.arxiv-citation-server/papers/{paper_id}.md
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import aiofiles
import arxiv
import pymupdf4llm
from pydantic import AnyUrl
import mcp.types as types

from ..config import Settings

logger = logging.getLogger("arxiv-citation-server")


class PaperManager:
    """
    Manages the storage, retrieval, and resource handling of arXiv papers.

    Papers are stored as markdown files for human readability.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the paper manager.

        Args:
            settings: Optional settings instance.
        """
        self.settings = settings or Settings()
        self.storage_path = self.settings.PAPERS_PATH
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.client = arxiv.Client()

    def _get_paper_path(self, paper_id: str) -> Path:
        """Get the absolute file path for a paper."""
        # Sanitize paper_id for filesystem
        safe_id = paper_id.replace("/", "_").replace(":", "_")
        return self.storage_path / f"{safe_id}.md"

    async def store_paper(self, paper_id: str) -> Path:
        """
        Download and store a paper from arXiv.

        Args:
            paper_id: The arXiv paper ID (e.g., '2103.12345').

        Returns:
            Path to the stored markdown file.

        Raises:
            ValueError: If paper not found or download fails.
        """
        paper_md_path = self._get_paper_path(paper_id)

        # Return existing if already stored
        if paper_md_path.exists():
            logger.info(f"Paper {paper_id} already stored at {paper_md_path}")
            return paper_md_path

        paper_pdf_path = paper_md_path.with_suffix(".pdf")

        try:
            # Fetch paper metadata
            search = arxiv.Search(id_list=[paper_id])
            paper = next(self.client.results(search))

            logger.info(f"Downloading paper: {paper.title}")

            # Download PDF
            paper.download_pdf(dirpath=self.storage_path, filename=paper_pdf_path.name)

            # Convert to markdown
            logger.info(f"Converting {paper_id} to markdown...")
            markdown = pymupdf4llm.to_markdown(str(paper_pdf_path), show_progress=False)

            # Add metadata header
            header = self._format_paper_header(paper)
            full_content = header + "\n\n---\n\n" + markdown

            # Write markdown file
            async with aiofiles.open(paper_md_path, "w", encoding="utf-8") as f:
                await f.write(full_content)

            # Clean up PDF
            if paper_pdf_path.exists():
                paper_pdf_path.unlink()

            logger.info(f"Stored paper at {paper_md_path}")
            return paper_md_path

        except StopIteration:
            raise ValueError(f"Paper with ID {paper_id} not found on arXiv.")
        except arxiv.ArxivError as e:
            raise ValueError(f"Failed to download paper {paper_id}: {str(e)}")
        except Exception as e:
            # Clean up partial files
            if paper_pdf_path.exists():
                paper_pdf_path.unlink()
            raise ValueError(f"Error storing paper {paper_id}: {str(e)}")

    def _format_paper_header(self, paper: arxiv.Result) -> str:
        """Format paper metadata as markdown header."""
        authors = ", ".join(a.name for a in paper.authors[:10])
        if len(paper.authors) > 10:
            authors += f" ... (+{len(paper.authors) - 10} more)"

        categories = ", ".join(paper.categories)

        lines = [
            f"# {paper.title}",
            "",
            f"**arXiv:** [{paper.get_short_id()}](https://arxiv.org/abs/{paper.get_short_id()})",
            f"**Authors:** {authors}",
            f"**Published:** {paper.published.strftime('%Y-%m-%d')}",
            f"**Categories:** {categories}",
            "",
            "## Abstract",
            "",
            paper.summary,
        ]

        return "\n".join(lines)

    async def has_paper(self, paper_id: str) -> bool:
        """Check if a paper is available in storage."""
        return self._get_paper_path(paper_id).exists()

    async def list_papers(self) -> list[str]:
        """List all stored paper IDs."""
        paper_ids = [p.stem for p in self.storage_path.glob("*.md")]
        logger.info(f"Found {len(paper_ids)} stored papers")
        return paper_ids

    async def get_paper_content(self, paper_id: str) -> str:
        """
        Get the markdown content of a stored paper.

        Args:
            paper_id: The arXiv paper ID.

        Returns:
            The paper content as markdown.

        Raises:
            ValueError: If paper not found in storage.
        """
        paper_path = self._get_paper_path(paper_id)
        if not paper_path.exists():
            raise ValueError(f"Paper {paper_id} not found in storage. Download it first.")

        async with aiofiles.open(paper_path, "r", encoding="utf-8") as f:
            return await f.read()

    async def get_paper_metadata(self, paper_id: str) -> dict:
        """
        Get metadata for a paper from arXiv.

        Args:
            paper_id: The arXiv paper ID.

        Returns:
            Dict with paper metadata.
        """
        try:
            search = arxiv.Search(id_list=[paper_id])
            paper = next(self.client.results(search))

            return {
                "id": paper.get_short_id(),
                "title": paper.title,
                "authors": [a.name for a in paper.authors],
                "abstract": paper.summary,
                "categories": paper.categories,
                "published": paper.published.isoformat(),
                "pdf_url": paper.pdf_url,
                "is_stored": await self.has_paper(paper_id),
            }
        except StopIteration:
            raise ValueError(f"Paper {paper_id} not found on arXiv.")

    async def list_resources(self) -> List[types.Resource]:
        """List all papers as MCP resources with metadata."""
        paper_ids = await self.list_papers()
        resources = []

        for paper_id in paper_ids:
            try:
                search = arxiv.Search(id_list=[paper_id])
                papers = list(self.client.results(search))

                if papers:
                    paper = papers[0]
                    paper_path = self._get_paper_path(paper_id)
                    resources.append(
                        types.Resource(
                            uri=AnyUrl(f"file://{str(paper_path)}"),
                            name=paper.title,
                            description=paper.summary[:200] + "..." if len(paper.summary) > 200 else paper.summary,
                            mimeType="text/markdown",
                        )
                    )
            except Exception as e:
                logger.warning(f"Could not get metadata for {paper_id}: {e}")

        return resources

    async def delete_paper(self, paper_id: str) -> bool:
        """
        Delete a stored paper.

        Args:
            paper_id: The arXiv paper ID.

        Returns:
            True if deleted, False if not found.
        """
        paper_path = self._get_paper_path(paper_id)
        if paper_path.exists():
            paper_path.unlink()
            logger.info(f"Deleted paper {paper_id}")
            return True
        return False
