"""
Semantic Scholar API client.

Async wrapper around the Semantic Scholar API for fetching paper
metadata, citations, and references.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from semanticscholar import AsyncSemanticScholar

from .models import (
    CitationContext,
    CitationIntent,
    CitationRelationship,
    PaperInfo,
)

logger = logging.getLogger("arxiv-citation-server")


class SemanticScholarClient:
    """
    Async client for the Semantic Scholar API.

    Handles paper lookups, citation retrieval, and reference retrieval
    using arXiv IDs or other external identifiers.
    """

    # Fields to request for paper metadata
    PAPER_FIELDS = [
        "paperId",
        "externalIds",
        "title",
        "authors",
        "year",
        "venue",
        "abstract",
        "citationCount",
        "referenceCount",
        "influentialCitationCount",
    ]

    # Fields to request for citations/references (includes context)
    CITATION_FIELDS = [
        "paperId",
        "externalIds",
        "title",
        "authors",
        "year",
        "venue",
        "citationCount",
        "contexts",
        "intents",
        "isInfluential",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 60,
    ):
        """
        Initialize the Semantic Scholar client.

        Args:
            api_key: Optional API key for higher rate limits.
                    Without a key: ~100 requests per 5 minutes.
                    With a key: ~1 request per second.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[AsyncSemanticScholar] = None

    async def _get_client(self) -> AsyncSemanticScholar:
        """Get or create the async client instance."""
        if self._client is None:
            self._client = AsyncSemanticScholar(
                api_key=self.api_key,
                timeout=self.timeout,
            )
        return self._client

    def _format_arxiv_id(self, arxiv_id: str) -> str:
        """
        Format an arXiv ID for the Semantic Scholar API.

        Converts '2103.12345' or '2103.12345v1' to 'ARXIV:2103.12345'.
        """
        # Remove version suffix if present
        clean_id = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id
        return f"ARXIV:{clean_id}"

    def _parse_paper(
        self,
        result: Any,
        original_id: Optional[str] = None,
    ) -> PaperInfo:
        """Convert Semantic Scholar result to PaperInfo model."""
        external_ids = getattr(result, "externalIds", {}) or {}

        # Determine the paper_id to use
        paper_id = original_id or result.paperId

        return PaperInfo(
            paper_id=paper_id,
            title=result.title or "Unknown Title",
            authors=[author.name for author in (result.authors or [])],
            year=result.year,
            venue=result.venue,
            abstract=getattr(result, "abstract", None),
            arxiv_id=external_ids.get("ArXiv"),
            doi=external_ids.get("DOI"),
            s2_paper_id=result.paperId,
            citation_count=getattr(result, "citationCount", None),
            reference_count=getattr(result, "referenceCount", None),
            influential_citation_count=getattr(result, "influentialCitationCount", None),
        )

    def _parse_intent(self, intent_str: str) -> CitationIntent:
        """Parse a citation intent string to enum."""
        intent_map = {
            "background": CitationIntent.BACKGROUND,
            "methodology": CitationIntent.METHOD,
            "method": CitationIntent.METHOD,
            "result": CitationIntent.RESULT,
        }
        return intent_map.get(intent_str.lower(), CitationIntent.UNKNOWN)

    def _parse_citation_contexts(
        self,
        result: Any,
    ) -> list[CitationContext]:
        """Extract citation contexts from a Semantic Scholar result."""
        contexts = []
        raw_contexts = getattr(result, "contexts", []) or []
        raw_intents = getattr(result, "intents", []) or []
        is_influential = getattr(result, "isInfluential", False)

        # Contexts and intents are parallel arrays
        for i, ctx_text in enumerate(raw_contexts):
            # Get intent for this context (may have multiple intents)
            intent = CitationIntent.UNKNOWN
            if i < len(raw_intents) and raw_intents[i]:
                # Take the first intent if multiple
                intent_str = raw_intents[i][0] if isinstance(raw_intents[i], list) else raw_intents[i]
                intent = self._parse_intent(intent_str)

            contexts.append(
                CitationContext(
                    text=ctx_text,
                    intent=intent,
                    is_influential=is_influential,
                )
            )

        return contexts

    async def get_paper(self, arxiv_id: str) -> Optional[PaperInfo]:
        """
        Get paper metadata from Semantic Scholar.

        Args:
            arxiv_id: The arXiv paper ID (e.g., '2103.12345').

        Returns:
            PaperInfo or None if not found.
        """
        client = await self._get_client()
        s2_id = self._format_arxiv_id(arxiv_id)

        try:
            result = await client.get_paper(s2_id, fields=self.PAPER_FIELDS)
            if result is None:
                logger.warning(f"Paper not found: {arxiv_id}")
                return None
            return self._parse_paper(result, original_id=arxiv_id)
        except Exception as e:
            logger.error(f"Failed to fetch paper {arxiv_id}: {e}")
            return None

    async def get_citations(
        self,
        arxiv_id: str,
        limit: int = 50,
    ) -> list[CitationRelationship]:
        """
        Get papers that cite the given paper.

        Args:
            arxiv_id: The arXiv paper ID.
            limit: Maximum number of citations to return.

        Returns:
            List of CitationRelationship objects.
        """
        client = await self._get_client()
        s2_id = self._format_arxiv_id(arxiv_id)

        try:
            # Get the cited paper's info first
            cited_paper = await self.get_paper(arxiv_id)
            if cited_paper is None:
                cited_paper = PaperInfo(paper_id=arxiv_id, title="Unknown")

            # Fetch citations
            results = await client.get_paper_citations(
                s2_id,
                fields=self.CITATION_FIELDS,
                limit=limit,
            )

            citations = []
            for result in results:
                if result is None:
                    continue

                citing_paper = self._parse_paper(result)
                contexts = self._parse_citation_contexts(result)

                citations.append(
                    CitationRelationship(
                        citing_paper=citing_paper,
                        cited_paper=cited_paper,
                        contexts=contexts,
                        is_influential=getattr(result, "isInfluential", False),
                    )
                )

            logger.info(f"Found {len(citations)} citations for {arxiv_id}")
            return citations

        except Exception as e:
            logger.error(f"Failed to fetch citations for {arxiv_id}: {e}")
            return []

    async def get_references(
        self,
        arxiv_id: str,
        limit: int = 50,
    ) -> list[CitationRelationship]:
        """
        Get papers referenced by the given paper.

        Args:
            arxiv_id: The arXiv paper ID.
            limit: Maximum number of references to return.

        Returns:
            List of CitationRelationship objects.
        """
        client = await self._get_client()
        s2_id = self._format_arxiv_id(arxiv_id)

        try:
            # Get the citing paper's info first
            citing_paper = await self.get_paper(arxiv_id)
            if citing_paper is None:
                citing_paper = PaperInfo(paper_id=arxiv_id, title="Unknown")

            # Fetch references
            results = await client.get_paper_references(
                s2_id,
                fields=self.CITATION_FIELDS,
                limit=limit,
            )

            references = []
            for result in results:
                if result is None:
                    continue

                cited_paper = self._parse_paper(result)
                contexts = self._parse_citation_contexts(result)

                references.append(
                    CitationRelationship(
                        citing_paper=citing_paper,
                        cited_paper=cited_paper,
                        contexts=contexts,
                        is_influential=getattr(result, "isInfluential", False),
                    )
                )

            logger.info(f"Found {len(references)} references for {arxiv_id}")
            return references

        except Exception as e:
            logger.error(f"Failed to fetch references for {arxiv_id}: {e}")
            return []

    async def get_papers_batch(
        self,
        arxiv_ids: list[str],
    ) -> dict[str, Optional[PaperInfo]]:
        """
        Batch fetch multiple papers.

        More efficient than individual requests for many papers.

        Args:
            arxiv_ids: List of arXiv paper IDs.

        Returns:
            Dict mapping paper_id to PaperInfo (or None if not found).
        """
        client = await self._get_client()
        s2_ids = [self._format_arxiv_id(aid) for aid in arxiv_ids]

        try:
            results = await client.get_papers(s2_ids, fields=self.PAPER_FIELDS)
            return {
                arxiv_id: self._parse_paper(result, original_id=arxiv_id) if result else None
                for arxiv_id, result in zip(arxiv_ids, results)
            }
        except Exception as e:
            logger.error(f"Batch fetch failed: {e}")
            return {aid: None for aid in arxiv_ids}

    async def search_papers(
        self,
        query: str,
        limit: int = 10,
        year: Optional[str] = None,
        fields_of_study: Optional[list[str]] = None,
    ) -> list[PaperInfo]:
        """
        Search for papers using the Semantic Scholar API.

        Args:
            query: Search query string.
            limit: Maximum number of results (default 10, max 100).
            year: Filter by year. Supports:
                  - Single year: "2020"
                  - Range: "2018-2022"
                  - Partial: "2020-" or "-2020"
            fields_of_study: Filter by fields (e.g., ["Computer Science"]).

        Returns:
            List of PaperInfo objects.
        """
        client = await self._get_client()
        limit = min(limit, 100)

        try:
            results = await client.search_paper(
                query=query,
                limit=limit,
                year=year,
                fields_of_study=fields_of_study,
                fields=self.PAPER_FIELDS,
            )

            # search_paper returns a PaginatedResults object
            # Access the items attribute to get the papers
            papers = []
            raw_items = getattr(results, "items", []) or []
            for result in raw_items:
                if result is not None:
                    papers.append(self._parse_paper(result))

            logger.info(f"Search returned {len(papers)} papers for query: {query}")
            return papers

        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return []

    async def close(self) -> None:
        """Close the client and release resources."""
        if self._client is not None:
            # AsyncSemanticScholar may not have explicit close
            self._client = None
