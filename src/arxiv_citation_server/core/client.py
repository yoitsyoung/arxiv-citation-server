"""
Semantic Scholar API client.

Direct HTTP client for the Semantic Scholar API using httpx.
Avoids asyncio conflicts from the semanticscholar library.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from .models import (
    CitationContext,
    CitationIntent,
    CitationRelationship,
    PaperInfo,
)

logger = logging.getLogger("arxiv-citation-server")

# Semantic Scholar API base URL
BASE_URL = "https://api.semanticscholar.org/graph/v1"


class SemanticScholarClient:
    """
    Async client for the Semantic Scholar API.

    Uses httpx directly to avoid event loop conflicts with the
    semanticscholar library.
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
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None:
            headers = {}
            if self.api_key:
                headers["x-api-key"] = self.api_key
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    def _format_paper_id(self, paper_id: str) -> str:
        """
        Format a paper ID for the Semantic Scholar API.

        Handles multiple formats:
        - arXiv ID: '2103.12345' or '2103.12345v1' -> 'ARXIV:2103.12345'
        - arXiv with prefix: 'arXiv:2103.12345' -> 'ARXIV:2103.12345'
        - Semantic Scholar ID (40-char hex): used directly
        - DOI: '10.xxxx/...' -> 'DOI:10.xxxx/...'
        """
        paper_id = paper_id.strip()

        # Already has a prefix (ARXIV:, DOI:, etc.)
        if ":" in paper_id and not paper_id.startswith("10."):
            prefix, value = paper_id.split(":", 1)
            # Normalize arXiv prefix
            if prefix.lower() == "arxiv":
                # Remove version suffix
                clean_id = value.split("v")[0] if "v" in value else value
                return f"ARXIV:{clean_id}"
            return paper_id

        # Semantic Scholar 40-character hex ID
        if len(paper_id) == 40 and all(c in "0123456789abcdef" for c in paper_id.lower()):
            return paper_id

        # DOI format
        if paper_id.startswith("10."):
            return f"DOI:{paper_id}"

        # Assume arXiv ID format (e.g., '1908.10063' or '2103.12345v1')
        # Remove version suffix if present
        clean_id = paper_id.split("v")[0] if "v" in paper_id else paper_id
        return f"ARXIV:{clean_id}"

    def _parse_paper_dict(
        self,
        data: dict[str, Any],
        original_id: Optional[str] = None,
    ) -> PaperInfo:
        """Convert API response dict to PaperInfo model."""
        external_ids = data.get("externalIds") or {}
        paper_id = original_id or data.get("paperId", "unknown")

        # Parse authors - API returns list of dicts with 'name' key
        authors = []
        for author in data.get("authors") or []:
            if isinstance(author, dict):
                authors.append(author.get("name", "Unknown"))
            else:
                authors.append(str(author))

        return PaperInfo(
            paper_id=paper_id,
            title=data.get("title") or "Unknown Title",
            authors=authors,
            year=data.get("year"),
            venue=data.get("venue"),
            abstract=data.get("abstract"),
            arxiv_id=external_ids.get("ArXiv"),
            doi=external_ids.get("DOI"),
            s2_paper_id=data.get("paperId"),
            citation_count=data.get("citationCount"),
            reference_count=data.get("referenceCount"),
            influential_citation_count=data.get("influentialCitationCount"),
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
        data: dict[str, Any],
    ) -> list[CitationContext]:
        """Extract citation contexts from API response."""
        contexts = []
        raw_contexts = data.get("contexts") or []
        raw_intents = data.get("intents") or []
        is_influential = data.get("isInfluential", False)

        for i, ctx_text in enumerate(raw_contexts):
            intent = CitationIntent.UNKNOWN
            if i < len(raw_intents) and raw_intents[i]:
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

    async def get_paper(self, paper_id: str) -> Optional[PaperInfo]:
        """
        Get paper metadata from Semantic Scholar.

        Args:
            paper_id: Paper identifier - arXiv ID, S2 paper ID, or DOI.

        Returns:
            PaperInfo or None if not found.
        """
        client = await self._get_client()
        s2_id = self._format_paper_id(paper_id)
        fields = ",".join(self.PAPER_FIELDS)

        try:
            response = await client.get(f"/paper/{s2_id}", params={"fields": fields})

            if response.status_code == 404:
                logger.warning(f"Paper not found: {paper_id}")
                return None

            response.raise_for_status()
            data = response.json()
            return self._parse_paper_dict(data, original_id=paper_id)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching paper {paper_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch paper {paper_id}: {e}")
            return None

    async def get_citations(
        self,
        paper_id: str,
        limit: int = 50,
    ) -> list[CitationRelationship]:
        """
        Get papers that cite the given paper.

        Args:
            paper_id: Paper identifier - arXiv ID, S2 paper ID, or DOI.
            limit: Maximum number of citations to return.

        Returns:
            List of CitationRelationship objects.
        """
        client = await self._get_client()
        s2_id = self._format_paper_id(paper_id)

        # Fields for the citing paper (nested under citingPaper)
        fields = ",".join([f"citingPaper.{f}" for f in self.PAPER_FIELDS])
        fields += ",contexts,intents,isInfluential"

        try:
            # Get the cited paper's info first
            cited_paper = await self.get_paper(paper_id)
            if cited_paper is None:
                cited_paper = PaperInfo(paper_id=paper_id, title="Unknown")

            # Fetch citations
            response = await client.get(
                f"/paper/{s2_id}/citations",
                params={"fields": fields, "limit": limit},
            )

            if response.status_code == 404:
                logger.warning(f"Paper not found for citations: {paper_id}")
                return []

            response.raise_for_status()
            data = response.json()

            citations = []
            for item in data.get("data", []):
                citing_paper_data = item.get("citingPaper")
                if not citing_paper_data:
                    continue

                citing_paper = self._parse_paper_dict(citing_paper_data)
                contexts = self._parse_citation_contexts(item)

                citations.append(
                    CitationRelationship(
                        citing_paper=citing_paper,
                        cited_paper=cited_paper,
                        contexts=contexts,
                        is_influential=item.get("isInfluential", False),
                    )
                )

            logger.info(f"Found {len(citations)} citations for {paper_id}")
            return citations

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching citations for {paper_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch citations for {paper_id}: {e}")
            return []

    async def get_references(
        self,
        paper_id: str,
        limit: int = 50,
    ) -> list[CitationRelationship]:
        """
        Get papers referenced by the given paper.

        Args:
            paper_id: Paper identifier - arXiv ID, S2 paper ID, or DOI.
            limit: Maximum number of references to return.

        Returns:
            List of CitationRelationship objects.
        """
        client = await self._get_client()
        s2_id = self._format_paper_id(paper_id)

        # Fields for the cited paper (nested under citedPaper)
        fields = ",".join([f"citedPaper.{f}" for f in self.PAPER_FIELDS])
        fields += ",contexts,intents,isInfluential"

        try:
            # Get the citing paper's info first
            citing_paper = await self.get_paper(paper_id)
            if citing_paper is None:
                citing_paper = PaperInfo(paper_id=paper_id, title="Unknown")

            # Fetch references
            response = await client.get(
                f"/paper/{s2_id}/references",
                params={"fields": fields, "limit": limit},
            )

            if response.status_code == 404:
                logger.warning(f"Paper not found for references: {paper_id}")
                return []

            response.raise_for_status()
            data = response.json()

            references = []
            for item in data.get("data", []):
                cited_paper_data = item.get("citedPaper")
                if not cited_paper_data:
                    continue

                cited_paper = self._parse_paper_dict(cited_paper_data)
                contexts = self._parse_citation_contexts(item)

                references.append(
                    CitationRelationship(
                        citing_paper=citing_paper,
                        cited_paper=cited_paper,
                        contexts=contexts,
                        is_influential=item.get("isInfluential", False),
                    )
                )

            logger.info(f"Found {len(references)} references for {paper_id}")
            return references

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching references for {paper_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch references for {paper_id}: {e}")
            return []

    async def get_papers_batch(
        self,
        paper_ids: list[str],
    ) -> dict[str, Optional[PaperInfo]]:
        """
        Batch fetch multiple papers.

        Args:
            paper_ids: List of paper identifiers (arXiv IDs, S2 IDs, or DOIs).

        Returns:
            Dict mapping paper_id to PaperInfo (or None if not found).
        """
        client = await self._get_client()
        fields = ",".join(self.PAPER_FIELDS)

        # Semantic Scholar batch endpoint
        formatted_ids = [self._format_paper_id(pid) for pid in paper_ids]

        try:
            response = await client.post(
                "/paper/batch",
                params={"fields": fields},
                json={"ids": formatted_ids},
            )
            response.raise_for_status()
            results = response.json()

            return {
                pid: self._parse_paper_dict(result, original_id=pid) if result else None
                for pid, result in zip(paper_ids, results)
            }
        except Exception as e:
            logger.error(f"Batch fetch failed: {e}")
            return {pid: None for pid in paper_ids}

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
            year: Filter by year (e.g., "2020", "2018-2022", "2020-", "-2020").
            fields_of_study: Filter by fields (e.g., ["Computer Science"]).

        Returns:
            List of PaperInfo objects.
        """
        client = await self._get_client()
        limit = min(limit, 100)
        fields = ",".join(self.PAPER_FIELDS)

        params: dict[str, Any] = {
            "query": query,
            "limit": limit,
            "fields": fields,
        }

        if year:
            params["year"] = year
        if fields_of_study:
            params["fieldsOfStudy"] = ",".join(fields_of_study)

        try:
            response = await client.get("/paper/search", params=params)
            response.raise_for_status()
            data = response.json()

            papers = []
            for item in data.get("data", []):
                papers.append(self._parse_paper_dict(item))

            logger.info(f"Search returned {len(papers)} papers for query: {query}")
            return papers

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error searching for '{query}': {e}")
            return []
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return []

    async def close(self) -> None:
        """Close the client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
