"""
MCP Tool: summarize_research_area

Generate a comprehensive overview of a research area from citation analysis.
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


summarize_area_tool = types.Tool(
    name="summarize_research_area",
    description="""Generate a comprehensive overview of a research area from citation analysis.

Synthesizes insights from the citation graph including:
- Foundational papers (most cited)
- Recent influential work (high citation velocity)
- Bridging papers (connecting sub-areas)
- Major themes and methodology trends
- Research timeline and evolution
- Sub-area clusters

Use this to:
- Get oriented in a new research area quickly
- Understand the structure and evolution of a field
- Identify the most important papers to read
- Find emerging trends and directions""",
    inputSchema={
        "type": "object",
        "properties": {
            "paper_id": {
                "type": "string",
                "description": "Central paper for the research area analysis",
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


async def handle_summarize_area(arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle the summarize_research_area tool call."""
    try:
        service = _get_service()

        paper_id = arguments["paper_id"]
        depth = min(arguments.get("depth", 2), 3)

        logger.info(f"Summarizing research area around {paper_id}")

        summary = await service.summarize_research_area(
            paper_id=paper_id,
            depth=depth,
        )

        result = {
            "root_paper_id": summary.root_paper_id,
            "area_name": summary.area_name,
            "overview": {
                "total_papers": summary.total_papers,
                "year_range": summary.year_range,
                "major_themes": summary.major_themes,
                "methodology_trends": summary.methodology_trends,
            },
            "foundational_papers": [
                {
                    "paper_id": p.paper_id,
                    "title": p.title,
                    "year": p.year,
                    "citations": p.citation_count,
                    "arxiv_id": p.arxiv_id,
                }
                for p in summary.foundational_papers[:5]
            ],
            "recent_influential": [
                {
                    "paper_id": p.paper_id,
                    "title": p.title,
                    "year": p.year,
                    "citations": p.citation_count,
                    "arxiv_id": p.arxiv_id,
                }
                for p in summary.recent_influential[:5]
            ],
            "bridging_papers": [
                {
                    "paper_id": p.paper_id,
                    "title": p.title,
                    "year": p.year,
                }
                for p in summary.bridging_papers[:3]
            ],
            "timeline": summary.timeline[:10],
            "sub_areas": [
                {
                    "label": c.label,
                    "paper_count": len(c.papers),
                    "key_terms": c.key_terms[:5],
                }
                for c in summary.sub_areas[:5]
            ],
        }

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Error summarizing research area: {e}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]
