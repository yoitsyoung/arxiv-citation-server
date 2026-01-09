"""
Semantic Scholar API client.

Async wrapper around the Semantic Scholar API for fetching paper
metadata, citations, and references.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
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

    # Fields to request for search results
    SEARCH_FIELDS = [
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
        "fieldsOfStudy",
        "publicationTypes",
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
        limit: int = 20,
        offset: int = 0,
        year_range: Optional[tuple[int, int]] = None,
        fields_of_study: Optional[list[str]] = None,
        min_citation_count: Optional[int] = None,
    ) -> tuple[list[PaperInfo], int, Optional[int]]:
        """
        Search for papers using Semantic Scholar's relevance search.

        Uses /graph/v1/paper/search endpoint for semantic search,
        complementing the existing arXiv keyword search.

        Args:
            query: Natural language search query
            limit: Maximum results (default 20, max 100)
            offset: Pagination offset
            year_range: Optional (start_year, end_year) filter
            fields_of_study: Optional filter by field (e.g., ['Computer Science'])
            min_citation_count: Optional minimum citation threshold

        Returns:
            Tuple of (papers, total_count, next_offset)
        """
        try:
            # Build query parameters
            params = {
                "query": query,
                "limit": min(limit, 100),
                "offset": offset,
                "fields": ",".join(self.SEARCH_FIELDS),
            }

            if year_range:
                params["year"] = f"{year_range[0]}-{year_range[1]}"

            if fields_of_study:
                params["fieldsOfStudy"] = ",".join(fields_of_study)

            if min_citation_count:
                params["minCitationCount"] = min_citation_count

            # Use direct HTTP for search endpoint
            base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
            headers = {}
            if self.api_key:
                headers["x-api-key"] = self.api_key

            async with httpx.AsyncClient(timeout=self.timeout) as http_client:
                response = await http_client.get(
                    base_url, params=params, headers=headers
                )
                response.raise_for_status()
                data = response.json()

            papers = []
            for item in data.get("data", []):
                papers.append(self._parse_search_result(item))

            total = data.get("total", len(papers))
            next_offset = offset + limit if offset + limit < total else None

            logger.info(f"S2 search '{query}': {len(papers)} results (total: {total})")
            return papers, total, next_offset

        except Exception as e:
            logger.error(f"S2 search failed: {e}")
            return [], 0, None

    def _parse_search_result(self, item: dict) -> PaperInfo:
        """Parse a search result item to PaperInfo."""
        external_ids = item.get("externalIds") or {}

        return PaperInfo(
            paper_id=item.get("paperId", ""),
            title=item.get("title", "Unknown Title"),
            authors=[a.get("name", "") for a in (item.get("authors") or [])],
            year=item.get("year"),
            venue=item.get("venue"),
            abstract=item.get("abstract"),
            arxiv_id=external_ids.get("ArXiv"),
            doi=external_ids.get("DOI"),
            s2_paper_id=item.get("paperId"),
            citation_count=item.get("citationCount"),
            reference_count=item.get("referenceCount"),
            influential_citation_count=item.get("influentialCitationCount"),
        )

    async def close(self) -> None:
        """Close the client and release resources."""
        if self._client is not None:
            # AsyncSemanticScholar may not have explicit close
            self._client = None
