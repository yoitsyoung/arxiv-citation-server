"""
MCP Tool: search_semantic_scholar

Search for papers using Semantic Scholar's semantic search API.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import mcp.types as types

from ..config import Settings
from ..core import CitationService

logger = logging.getLogger("arxiv-citation-server")

_service: CitationService | None = None


def _get_service() -> CitationService:
    global _service
    if _service is None:
        settings = Settings()
        _service = CitationService(
            api_key=settings.S2_API_KEY,
            timeout=settings.REQUEST_TIMEOUT,
        )
    return _service


search_s2_tool = types.Tool(
    name="search_semantic_scholar",
    description="""Search for papers using Semantic Scholar's semantic search.

Provides relevance-based search complementing arXiv's keyword search.
Returns papers with full metadata including citation counts.

Use this when you want:
- Semantic/relevance-based search (not just keyword matching)
- Papers from any venue (not just arXiv)
- Citation-aware results

Results are automatically added to the local knowledge graph.""",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results to return (default: 20, max: 100)",
                "default": 20,
                "minimum": 1,
                "maximum": 100,
            },
            "year_start": {
                "type": "integer",
                "description": "Filter papers from this year onwards",
            },
            "year_end": {
                "type": "integer",
                "description": "Filter papers up to this year",
            },
            "min_citations": {
                "type": "integer",
                "description": "Minimum citation count filter",
                "minimum": 0,
            },
        },
        "required": ["query"],
    },
)


async def handle_search_s2(arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle the search_semantic_scholar tool call."""
    try:
        service = _get_service()

        query = arguments["query"]
        limit = min(arguments.get("max_results", 20), 100)
        year_start = arguments.get("year_start")
        year_end = arguments.get("year_end")
        min_citations = arguments.get("min_citations")

        year_range = None
        if year_start or year_end:
            year_range = (year_start or 1900, year_end or 2030)

        logger.info(f"Searching Semantic Scholar: {query}")

        result = await service.search_semantic_scholar(
            query=query,
            limit=limit,
            year_range=year_range,
            min_citations=min_citations,
        )

        if not result.papers:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "query": query,
                            "total_results": 0,
                            "message": "No papers found. Try broader search terms.",
                        },
                        indent=2,
                    ),
                )
            ]

        response = {
            "query": query,
            "total_results": result.total_results,
            "returned": len(result.papers),
            "papers": [
                {
                    "paper_id": p.paper_id,
                    "title": p.title,
                    "authors": p.authors[:5],
                    "year": p.year,
                    "venue": p.venue,
                    "citation_count": p.citation_count,
                    "arxiv_id": p.arxiv_id,
                    "abstract_preview": (
                        p.abstract[:200] + "..."
                        if p.abstract and len(p.abstract) > 200
                        else p.abstract
                    ),
                }
                for p in result.papers[:15]  # Preview first 15
            ],
        }

        if result.next_offset:
            response["has_more"] = True
            response["next_offset"] = result.next_offset

        return [types.TextContent(type="text", text=json.dumps(response, indent=2))]

    except Exception as e:
        logger.error(f"S2 search error: {e}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]
