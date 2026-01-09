"""
Citation service - main business logic.

This is the core service that can be used by both MCP tools
and web applications. It has NO MCP dependencies.
"""

from __future__ import annotations

import logging
from typing import Optional

from .client import SemanticScholarClient
from .graph import GraphBuilder
from .models import CitationGraph, CitationRelationship, PaperInfo

logger = logging.getLogger("arxiv-citation-server")


class CitationService:
    """
    Core citation analysis service.

    This class provides all citation-related functionality without
    any MCP dependencies. It can be used directly by:
    - MCP tools (via the tools layer)
    - Web applications (import directly)
    - CLI tools
    - Jupyter notebooks

    Example usage:
        service = CitationService()
        citations = await service.get_citations("2103.12345")
        for cit in citations:
            print(f"{cit.citing_paper.title} cites this paper")
            for ctx in cit.contexts:
                print(f"  Context: {ctx.text[:100]}...")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 60,
    ):
        """
        Initialize the citation service.

        Args:
            api_key: Optional Semantic Scholar API key for higher rate limits.
            timeout: Request timeout in seconds.
        """
        self.client = SemanticScholarClient(api_key=api_key, timeout=timeout)

    async def get_paper_info(self, arxiv_id: str) -> Optional[PaperInfo]:
        """
        Get paper metadata from Semantic Scholar.

        Args:
            arxiv_id: The arXiv paper ID (e.g., '2103.12345').

        Returns:
            PaperInfo with metadata, or None if not found.
        """
        return await self.client.get_paper(arxiv_id)

    async def get_citations(
        self,
        arxiv_id: str,
        limit: int = 50,
        include_contexts: bool = True,
    ) -> list[CitationRelationship]:
        """
        Get papers that cite the given paper.

        Args:
            arxiv_id: The arXiv paper ID.
            limit: Maximum citations to return (default 50, max 100).
            include_contexts: Whether to include citation context snippets.
                            Context is always fetched but can be filtered.

        Returns:
            List of CitationRelationship objects, each containing:
            - citing_paper: The paper that cites this one
            - cited_paper: This paper (the one being cited)
            - contexts: Text snippets showing how it's cited
            - is_influential: Whether it's an influential citation
        """
        limit = min(limit, 100)
        citations = await self.client.get_citations(arxiv_id, limit=limit)

        if not include_contexts:
            # Strip contexts if not requested (saves memory/bandwidth)
            for cit in citations:
                cit.contexts.clear()

        return citations

    async def get_references(
        self,
        arxiv_id: str,
        limit: int = 50,
        include_contexts: bool = True,
    ) -> list[CitationRelationship]:
        """
        Get papers referenced by the given paper.

        Args:
            arxiv_id: The arXiv paper ID.
            limit: Maximum references to return (default 50, max 100).
            include_contexts: Whether to include citation context snippets.

        Returns:
            List of CitationRelationship objects, each containing:
            - citing_paper: This paper (the one doing the citing)
            - cited_paper: The referenced paper
            - contexts: Text snippets showing how it's referenced
            - is_influential: Whether it's an influential reference
        """
        limit = min(limit, 100)
        references = await self.client.get_references(arxiv_id, limit=limit)

        if not include_contexts:
            for ref in references:
                ref.contexts.clear()

        return references

    async def build_citation_graph(
        self,
        arxiv_id: str,
        depth: int = 2,
        direction: str = "both",
        max_papers_per_level: int = 25,
    ) -> CitationGraph:
        """
        Build a citation graph around a paper.

        Traverses citation relationships N levels deep to create
        a network of related papers.

        Args:
            arxiv_id: The center paper's arXiv ID.
            depth: How many levels to traverse (1-3 recommended).
                  Higher depths exponentially increase API calls.
            direction: Which relationships to follow:
                      - 'citations': Papers that cite the root
                      - 'references': Papers the root cites
                      - 'both': Both directions
            max_papers_per_level: Max papers to fetch at each level.
                                 Limits graph size and API usage.

        Returns:
            CitationGraph containing:
            - root_paper_id: The starting paper
            - papers: Dict of paper_id -> PaperInfo
            - edges: List of (citing_id, cited_id) tuples
            - depth: Actual depth traversed
            - direction: The direction used
        """
        builder = GraphBuilder(
            client=self.client,
            max_papers_per_level=max_papers_per_level,
        )
        return await builder.build(
            root_paper_id=arxiv_id,
            depth=depth,
            direction=direction,
        )

    async def search_papers(
        self,
        query: str,
        limit: int = 10,
        year: Optional[str] = None,
        fields_of_study: Optional[list[str]] = None,
    ) -> list[PaperInfo]:
        """
        Search for papers using Semantic Scholar.

        This allows agents to discover papers beyond arXiv and build
        relationships using their own reasoning.

        Args:
            query: Search query string.
            limit: Maximum results (default 10, max 100).
            year: Filter by year. Supports:
                  - Single year: "2020"
                  - Range: "2018-2022"
                  - Partial: "2020-" or "-2020"
            fields_of_study: Filter by fields (e.g., ["Computer Science"]).

        Returns:
            List of PaperInfo objects with metadata and citation counts.
        """
        return await self.client.search_papers(
            query=query,
            limit=limit,
            year=year,
            fields_of_study=fields_of_study,
        )

    async def get_citation_summary(
        self,
        arxiv_id: str,
    ) -> dict:
        """
        Get a quick summary of citation metrics for a paper.

        Useful for getting an overview without fetching all citations.

        Args:
            arxiv_id: The arXiv paper ID.

        Returns:
            Dict with citation metrics and basic info.
        """
        paper = await self.get_paper_info(arxiv_id)
        if paper is None:
            return {"error": f"Paper not found: {arxiv_id}"}

        return {
            "paper_id": paper.paper_id,
            "title": paper.title,
            "year": paper.year,
            "citation_count": paper.citation_count,
            "reference_count": paper.reference_count,
            "influential_citation_count": paper.influential_citation_count,
            "arxiv_id": paper.arxiv_id,
            "doi": paper.doi,
        }

    async def close(self) -> None:
        """Clean up resources."""
        await self.client.close()
