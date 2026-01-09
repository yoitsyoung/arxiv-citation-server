"""
Citation storage management.

Stores citation data as human-readable markdown files,
similar to how arxiv-mcp-server stores papers.

Storage structure:
    ~/.arxiv-citation-server/citations/{paper_id}/
    ├── paper_info.md       # Paper metadata
    ├── citations.md        # Papers that cite this
    ├── references.md       # Papers this cites
    └── graph_depth{N}.md   # Citation graph visualization
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles

from ..config import Settings
from ..core.models import (
    CitationGraph,
    CitationRelationship,
    PaperInfo,
)

logger = logging.getLogger("arxiv-citation-server")


class CitationManager:
    """
    Manages citation data storage as markdown files.

    All data is stored in human-readable markdown format,
    making it easy to inspect, edit, and version control.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the citation manager.

        Args:
            settings: Optional settings instance. If not provided,
                     creates default settings.
        """
        self.settings = settings or Settings()
        self.storage_path = self.settings.STORAGE_PATH
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_paper_dir(self, paper_id: str) -> Path:
        """Get the directory for a paper's citation data."""
        # Sanitize paper_id for filesystem
        safe_id = paper_id.replace("/", "_").replace(":", "_")
        return self.storage_path / safe_id

    def _ensure_paper_dir(self, paper_id: str) -> Path:
        """Ensure paper directory exists and return path."""
        paper_dir = self._get_paper_dir(paper_id)
        paper_dir.mkdir(parents=True, exist_ok=True)
        return paper_dir

    # ==================== Paper Info ====================

    async def store_paper_info(self, paper: PaperInfo) -> Path:
        """
        Store paper metadata as markdown.

        Args:
            paper: PaperInfo to store.

        Returns:
            Path to the created markdown file.
        """
        paper_dir = self._ensure_paper_dir(paper.paper_id)
        md_path = paper_dir / "paper_info.md"

        content = self._format_paper_info_markdown(paper)

        async with aiofiles.open(md_path, "w", encoding="utf-8") as f:
            await f.write(content)

        logger.info(f"Stored paper info: {md_path}")
        return md_path

    def _format_paper_info_markdown(self, paper: PaperInfo) -> str:
        """Format paper metadata as markdown."""
        lines = [
            f"# {paper.title}",
            "",
            f"**Paper ID:** {paper.paper_id}",
            f"**arXiv:** {paper.arxiv_id or 'N/A'}",
            f"**DOI:** {paper.doi or 'N/A'}",
            "",
            "## Authors",
            "",
        ]

        for author in paper.authors:
            lines.append(f"- {author}")

        lines.extend([
            "",
            "## Metadata",
            "",
            f"- **Year:** {paper.year or 'Unknown'}",
            f"- **Venue:** {paper.venue or 'Unknown'}",
            f"- **Citation Count:** {paper.citation_count or 'Unknown'}",
            f"- **Reference Count:** {paper.reference_count or 'Unknown'}",
            f"- **Influential Citations:** {paper.influential_citation_count or 'Unknown'}",
            "",
        ])

        if paper.abstract:
            lines.extend([
                "## Abstract",
                "",
                paper.abstract,
                "",
            ])

        lines.extend([
            "---",
            "",
            f"*Retrieved: {paper.fetched_at.isoformat()}*",
        ])

        return "\n".join(lines)

    # ==================== Citations ====================

    async def store_citations(
        self,
        paper_id: str,
        citations: list[CitationRelationship],
    ) -> Path:
        """
        Store citations as human-readable markdown.

        Args:
            paper_id: The paper being cited.
            citations: List of papers that cite it.

        Returns:
            Path to the created markdown file.
        """
        paper_dir = self._ensure_paper_dir(paper_id)
        md_path = paper_dir / "citations.md"

        content = self._format_citations_markdown(paper_id, citations)

        async with aiofiles.open(md_path, "w", encoding="utf-8") as f:
            await f.write(content)

        logger.info(f"Stored {len(citations)} citations: {md_path}")
        return md_path

    def _format_citations_markdown(
        self,
        paper_id: str,
        citations: list[CitationRelationship],
    ) -> str:
        """Format citations as readable markdown."""
        lines = [
            f"# Papers Citing {paper_id}",
            "",
            f"*Retrieved: {datetime.utcnow().isoformat()}*",
            f"*Total: {len(citations)} papers*",
            "",
        ]

        # Summary statistics
        influential_count = sum(1 for c in citations if c.is_influential)
        if influential_count > 0:
            lines.append(f"*Influential citations: {influential_count}*")
        lines.extend(["", "---", ""])

        for i, cit in enumerate(citations, 1):
            paper = cit.citing_paper
            lines.extend([
                f"## {i}. {paper.title}",
                "",
                f"**Authors:** {', '.join(paper.authors[:5])}{'...' if len(paper.authors) > 5 else ''}",
                f"**Year:** {paper.year or 'Unknown'}",
                f"**Venue:** {paper.venue or 'Unknown'}",
            ])

            if paper.arxiv_id:
                lines.append(f"**arXiv:** [{paper.arxiv_id}](https://arxiv.org/abs/{paper.arxiv_id})")
            if paper.doi:
                lines.append(f"**DOI:** [{paper.doi}](https://doi.org/{paper.doi})")

            lines.append(f"**Influential:** {'Yes' if cit.is_influential else 'No'}")
            lines.append("")

            if cit.contexts:
                lines.append("### Citation Contexts")
                lines.append("")
                for ctx in cit.contexts:
                    lines.extend([
                        f"> {ctx.text}",
                        "",
                        f"*Intent: {ctx.intent.value}*",
                        "",
                    ])

            lines.extend(["---", ""])

        return "\n".join(lines)

    # ==================== References ====================

    async def store_references(
        self,
        paper_id: str,
        references: list[CitationRelationship],
    ) -> Path:
        """
        Store references as human-readable markdown.

        Args:
            paper_id: The paper doing the citing.
            references: List of papers it references.

        Returns:
            Path to the created markdown file.
        """
        paper_dir = self._ensure_paper_dir(paper_id)
        md_path = paper_dir / "references.md"

        content = self._format_references_markdown(paper_id, references)

        async with aiofiles.open(md_path, "w", encoding="utf-8") as f:
            await f.write(content)

        logger.info(f"Stored {len(references)} references: {md_path}")
        return md_path

    def _format_references_markdown(
        self,
        paper_id: str,
        references: list[CitationRelationship],
    ) -> str:
        """Format references as readable markdown."""
        lines = [
            f"# References from {paper_id}",
            "",
            f"*Retrieved: {datetime.utcnow().isoformat()}*",
            f"*Total: {len(references)} papers*",
            "",
            "---",
            "",
        ]

        for i, ref in enumerate(references, 1):
            paper = ref.cited_paper
            lines.extend([
                f"## {i}. {paper.title}",
                "",
                f"**Authors:** {', '.join(paper.authors[:5])}{'...' if len(paper.authors) > 5 else ''}",
                f"**Year:** {paper.year or 'Unknown'}",
                f"**Venue:** {paper.venue or 'Unknown'}",
            ])

            if paper.arxiv_id:
                lines.append(f"**arXiv:** [{paper.arxiv_id}](https://arxiv.org/abs/{paper.arxiv_id})")
            if paper.doi:
                lines.append(f"**DOI:** [{paper.doi}](https://doi.org/{paper.doi})")

            lines.append(f"**Influential:** {'Yes' if ref.is_influential else 'No'}")
            lines.append("")

            if ref.contexts:
                lines.append("### How It's Referenced")
                lines.append("")
                for ctx in ref.contexts:
                    lines.extend([
                        f"> {ctx.text}",
                        "",
                        f"*Intent: {ctx.intent.value}*",
                        "",
                    ])

            lines.extend(["---", ""])

        return "\n".join(lines)

    # ==================== Citation Graph ====================

    async def store_graph(self, graph: CitationGraph) -> Path:
        """
        Store citation graph as markdown visualization.

        Args:
            graph: The citation graph to store.

        Returns:
            Path to the created markdown file.
        """
        paper_dir = self._ensure_paper_dir(graph.root_paper_id)
        filename = f"graph_depth{graph.depth}_{graph.direction}.md"
        md_path = paper_dir / filename

        content = self._format_graph_markdown(graph)

        async with aiofiles.open(md_path, "w", encoding="utf-8") as f:
            await f.write(content)

        logger.info(f"Stored graph: {md_path}")
        return md_path

    def _format_graph_markdown(self, graph: CitationGraph) -> str:
        """Format citation graph as readable markdown."""
        root = graph.papers.get(graph.root_paper_id)
        root_title = root.title if root else graph.root_paper_id

        lines = [
            f"# Citation Graph: {root_title}",
            "",
            f"*Created: {graph.created_at.isoformat()}*",
            "",
            "## Graph Statistics",
            "",
            f"- **Root Paper:** {graph.root_paper_id}",
            f"- **Direction:** {graph.direction}",
            f"- **Depth:** {graph.depth}",
            f"- **Total Papers:** {graph.node_count}",
            f"- **Total Edges:** {graph.edge_count}",
            "",
            "---",
            "",
            "## Papers in Graph",
            "",
        ]

        # List all papers
        for i, (paper_id, paper) in enumerate(graph.papers.items(), 1):
            is_root = paper_id == graph.root_paper_id
            marker = " (ROOT)" if is_root else ""
            lines.extend([
                f"### {i}. {paper.title}{marker}",
                "",
                f"- **ID:** {paper_id}",
                f"- **Year:** {paper.year or 'Unknown'}",
                f"- **Citations:** {paper.citation_count or 'Unknown'}",
                "",
            ])

        lines.extend([
            "---",
            "",
            "## Citation Relationships",
            "",
            "```",
            "citing_paper -> cited_paper",
            "```",
            "",
        ])

        # List edges
        for citing_id, cited_id in graph.edges:
            citing = graph.papers.get(citing_id)
            cited = graph.papers.get(cited_id)
            citing_short = citing.title[:50] + "..." if citing and len(citing.title) > 50 else (citing.title if citing else citing_id)
            cited_short = cited.title[:50] + "..." if cited and len(cited.title) > 50 else (cited.title if cited else cited_id)
            lines.append(f"- {citing_short} → {cited_short}")

        return "\n".join(lines)

    # ==================== Retrieval ====================

    async def has_citations(self, paper_id: str) -> bool:
        """Check if citations are stored for a paper."""
        paper_dir = self._get_paper_dir(paper_id)
        return (paper_dir / "citations.md").exists()

    async def has_references(self, paper_id: str) -> bool:
        """Check if references are stored for a paper."""
        paper_dir = self._get_paper_dir(paper_id)
        return (paper_dir / "references.md").exists()

    async def list_stored_papers(self) -> list[str]:
        """List all paper IDs with stored citation data."""
        return [p.name for p in self.storage_path.iterdir() if p.is_dir()]

    async def get_citations_path(self, paper_id: str) -> Optional[Path]:
        """Get path to citations file if it exists."""
        paper_dir = self._get_paper_dir(paper_id)
        citations_path = paper_dir / "citations.md"
        return citations_path if citations_path.exists() else None

    async def get_references_path(self, paper_id: str) -> Optional[Path]:
        """Get path to references file if it exists."""
        paper_dir = self._get_paper_dir(paper_id)
        references_path = paper_dir / "references.md"
        return references_path if references_path.exists() else None
