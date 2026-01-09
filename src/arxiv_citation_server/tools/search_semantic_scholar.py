"""
MCP Tool: search_semantic_scholar

Search for papers on Semantic Scholar.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import mcp.types as types

from ..config import Settings
from ..core.service import CitationService

logger = logging.getLogger("arxiv-citation-server")

# Module-level service instance (lazy initialization)
_service: CitationService | None = None


def _get_service() -> CitationService:
    """Get or create the CitationService instance."""
    global _service
    if _service is None:
        settings = Settings()
        _service = CitationService(api_key=settings.S2_API_KEY)
    return _service


# Tool definition
search_semantic_scholar_tool = types.Tool(
    name="search_semantic_scholar",
    description="""Search Semantic Scholar for academic papers.

Returns papers with full metadata and citation counts, enabling you to
discover relevant work and build citation relationships.

Use this alongside arXiv search to find papers that may not be on arXiv,
or to get citation metrics for papers you've found.

Examples:
- "transformer attention mechanism"
- "deep learning medical imaging"
- "graph neural networks" with year="2020-2023"
- "climate change modeling" with fields_of_study=["Environmental Science"]""",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query string",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results to return (default: 10, max: 50)",
                "default": 10,
                "minimum": 1,
                "maximum": 50,
            },
            "year": {
                "type": "string",
                "description": "Filter by publication year. Single year (2020), range (2018-2022), or partial (-2020, 2020-)",
            },
            "fields_of_study": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter by fields of study (e.g., ['Computer Science', 'Medicine'])",
            },
        },
        "required": ["query"],
    },
)


async def handle_search_semantic_scholar(arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle the search_semantic_scholar tool call."""
    try:
        settings = Settings()
        service = _get_service()

        query = arguments["query"]
        limit = min(arguments.get("limit", 10), settings.MAX_SEARCH_RESULTS)
        year = arguments.get("year")
        fields_of_study = arguments.get("fields_of_study")

        logger.info(f"Searching Semantic Scholar: {query} (limit: {limit})")

        papers = await service.search_papers(
            query=query,
            limit=limit,
            year=year,
            fields_of_study=fields_of_study,
        )

        # Format results
        paper_results = []
        for paper in papers:
            paper_results.append({
                "paper_id": paper.paper_id,
                "title": paper.title,
                "authors": paper.authors[:5] if paper.authors else [],
                "author_count": len(paper.authors) if paper.authors else 0,
                "year": paper.year,
                "venue": paper.venue,
                "abstract": (
                    paper.abstract[:500] + "..."
                    if paper.abstract and len(paper.abstract) > 500
                    else paper.abstract
                ),
                "citation_count": paper.citation_count,
                "reference_count": paper.reference_count,
                "influential_citation_count": paper.influential_citation_count,
                "arxiv_id": paper.arxiv_id,
                "doi": paper.doi,
                "s2_paper_id": paper.s2_paper_id,
            })

        result = {
            "query": query,
            "total_results": len(paper_results),
            "papers": paper_results,
        }

        if year:
            result["year_filter"] = year
        if fields_of_study:
            result["fields_of_study_filter"] = fields_of_study

        if not paper_results:
            result["message"] = "No papers found matching your query."

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Semantic Scholar search error: {e}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]
