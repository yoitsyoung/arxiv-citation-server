"""
MCP Tool: find_similar_papers

Find semantically similar papers using citation-based analysis.
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


find_similar_tool = types.Tool(
    name="find_similar_papers",
    description="""Find papers similar to a given paper using citation analysis.

Computes similarity based on citation patterns:
- co_citation: Papers often cited together (indicates topical similarity)
- bibliographic_coupling: Papers citing same references (indicates methodological similarity)
- citation_overlap: Combined approach (default, balanced)

No external ML services required - all computation is local.

Use this to:
- Discover related work you may have missed
- Find alternative approaches to the same problem
- Identify papers in the same research community""",
    inputSchema={
        "type": "object",
        "properties": {
            "paper_id": {
                "type": "string",
                "description": "arXiv paper ID to find similar papers for",
            },
            "method": {
                "type": "string",
                "enum": ["co_citation", "bibliographic_coupling", "citation_overlap"],
                "description": "Similarity computation method (default: citation_overlap)",
                "default": "citation_overlap",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of similar papers to return (default: 10)",
                "default": 10,
                "minimum": 1,
                "maximum": 25,
            },
            "graph_depth": {
                "type": "integer",
                "description": "Citation graph depth to explore (default: 2)",
                "default": 2,
                "minimum": 1,
                "maximum": 3,
            },
        },
        "required": ["paper_id"],
    },
)


async def handle_find_similar(arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle the find_similar_papers tool call."""
    try:
        service = _get_service()

        paper_id = arguments["paper_id"]
        method = arguments.get("method", "citation_overlap")
        top_k = min(arguments.get("top_k", 10), 25)
        graph_depth = min(arguments.get("graph_depth", 2), 3)

        logger.info(f"Finding similar papers to {paper_id} using {method}")

        similarities = await service.find_similar_papers(
            paper_id=paper_id,
            method=method,
            top_k=top_k,
            graph_depth=graph_depth,
        )

        if not similarities:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "paper_id": paper_id,
                            "similar_papers": [],
                            "message": "No similar papers found. The paper may have limited citation data.",
                        },
                        indent=2,
                    ),
                )
            ]

        result = {
            "paper_id": paper_id,
            "method": method,
            "similar_papers": [
                {
                    "paper_id": s.paper_b.paper_id,
                    "title": s.paper_b.title,
                    "year": s.paper_b.year,
                    "similarity_score": round(s.similarity_score, 3),
                    "shared_references": len(s.shared_citations),
                    "shared_citers": len(s.shared_citers),
                    "explanation": s.explanation,
                    "arxiv_id": s.paper_b.arxiv_id,
                }
                for s in similarities
            ],
        }

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Error finding similar papers: {e}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]
