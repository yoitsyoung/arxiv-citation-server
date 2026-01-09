"""
MCP Tool: find_research_gaps

Identify under-explored areas in a citation network.
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


find_gaps_tool = types.Tool(
    name="find_research_gaps",
    description="""Identify under-explored research areas in a citation network.

Analyzes citation patterns to find:
- Bridging gaps: Disconnected research clusters that could be connected
- Temporal gaps: Research areas that have declined and could be revisited
- Methodological gaps: Methods not yet applied to certain domains

All analysis is based on citation patterns - no external ML required.

Use this to:
- Find novel research directions
- Identify opportunities for interdisciplinary work
- Discover areas ripe for new contributions
- Plan future research directions""",
    inputSchema={
        "type": "object",
        "properties": {
            "paper_id": {
                "type": "string",
                "description": "Central paper to analyze around",
            },
            "depth": {
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


async def handle_find_gaps(arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle the find_research_gaps tool call."""
    try:
        service = _get_service()

        paper_id = arguments["paper_id"]
        depth = min(arguments.get("depth", 2), 3)

        logger.info(f"Finding research gaps around {paper_id}")

        result = await service.find_research_gaps(
            paper_id=paper_id,
            depth=depth,
        )

        response = {
            "paper_id": paper_id,
            "analyzed_papers": result.analyzed_paper_count,
            "analysis_depth": result.analysis_depth,
            "gaps_found": len(result.gaps),
            "gaps": [
                {
                    "gap_id": g.gap_id,
                    "type": g.gap_type,
                    "description": g.description,
                    "confidence": round(g.confidence, 2),
                    "potential_topics": g.potential_topics,
                    "related_clusters": g.related_clusters,
                }
                for g in result.gaps
            ],
        }

        return [types.TextContent(type="text", text=json.dumps(response, indent=2))]

    except Exception as e:
        logger.error(f"Error finding research gaps: {e}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]
