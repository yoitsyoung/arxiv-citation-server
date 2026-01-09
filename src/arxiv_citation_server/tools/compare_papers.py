"""
MCP Tool: compare_papers

Side-by-side comparison of multiple papers.
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


compare_papers_tool = types.Tool(
    name="compare_papers",
    description="""Generate side-by-side comparison of multiple papers.

Compares papers on:
- Publication timeline and venues
- Citation counts and impact
- Shared references (what they build on in common)
- Unique references (what each paper uniquely builds on)
- Shared citers (papers that cite all of them)
- Common themes from titles
- Distinguishing aspects

Use this to:
- Compare alternative approaches to a problem
- Understand how papers relate to each other
- Decide which papers to focus on
- Understand the relationship between influential works""",
    inputSchema={
        "type": "object",
        "properties": {
            "paper_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of paper IDs to compare (2-5 recommended)",
                "minItems": 2,
                "maxItems": 5,
            },
        },
        "required": ["paper_ids"],
    },
)


async def handle_compare_papers(arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle the compare_papers tool call."""
    try:
        service = _get_service()

        paper_ids = arguments["paper_ids"]

        if len(paper_ids) < 2:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {"error": "At least 2 papers required for comparison"}, indent=2
                    ),
                )
            ]

        if len(paper_ids) > 5:
            paper_ids = paper_ids[:5]  # Limit to 5

        logger.info(f"Comparing papers: {paper_ids}")

        comparison = await service.compare_papers(paper_ids)

        result = {
            "papers_compared": len(comparison.papers),
            "papers": [
                {
                    "paper_id": p.paper_id,
                    "title": p.title,
                    "year": p.year,
                    "venue": p.venue,
                    "citations": comparison.citation_counts.get(p.paper_id, 0),
                    "arxiv_id": p.arxiv_id,
                }
                for p in comparison.papers
            ],
            "timeline": comparison.publication_timeline,
            "citation_comparison": {
                "citation_counts": comparison.citation_counts,
                "overlap_score": round(comparison.citation_overlap_score, 3),
            },
            "shared_references": [
                {
                    "paper_id": p.paper_id,
                    "title": p.title[:60],
                    "year": p.year,
                }
                for p in comparison.shared_references[:10]
            ],
            "shared_references_count": len(comparison.shared_references),
            "unique_references": {
                pid: [{"title": r.title[:50], "year": r.year} for r in refs[:3]]
                for pid, refs in comparison.unique_references.items()
            },
            "shared_citers": [
                {
                    "paper_id": p.paper_id,
                    "title": p.title[:60],
                    "year": p.year,
                }
                for p in comparison.shared_citers[:10]
            ],
            "shared_citers_count": len(comparison.shared_citers),
            "themes": {
                "common": comparison.common_themes,
                "distinguishing": comparison.distinguishing_aspects,
            },
        }

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Error comparing papers: {e}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]
