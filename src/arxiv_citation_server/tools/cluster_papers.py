"""
MCP Tool: cluster_papers

Group papers by topic/methodology using citation-based clustering.
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


cluster_papers_tool = types.Tool(
    name="cluster_papers",
    description="""Group papers by topic/methodology using citation-based clustering.

Uses label propagation on the citation graph - no external ML required.
Papers that cite each other or share citation patterns cluster together.

Identifies:
- Distinct research sub-areas
- Central papers in each cluster
- Key terms for each cluster
- Cohesion (how tightly connected each cluster is)

Use this to:
- Understand the structure of a research area
- Identify distinct approaches to a problem
- Find the key papers in each sub-area""",
    inputSchema={
        "type": "object",
        "properties": {
            "root_paper_id": {
                "type": "string",
                "description": "Build citation graph from this paper and cluster",
            },
            "min_cluster_size": {
                "type": "integer",
                "description": "Minimum papers per cluster (default: 3)",
                "default": 3,
                "minimum": 2,
                "maximum": 10,
            },
            "graph_depth": {
                "type": "integer",
                "description": "Citation graph depth to explore (default: 2)",
                "default": 2,
                "minimum": 1,
                "maximum": 3,
            },
        },
        "required": ["root_paper_id"],
    },
)


async def handle_cluster_papers(arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle the cluster_papers tool call."""
    try:
        service = _get_service()

        root_paper_id = arguments["root_paper_id"]
        min_cluster_size = arguments.get("min_cluster_size", 3)
        graph_depth = min(arguments.get("graph_depth", 2), 3)

        logger.info(f"Clustering papers around {root_paper_id}")

        result = await service.cluster_papers(
            root_paper_id=root_paper_id,
            min_cluster_size=min_cluster_size,
            graph_depth=graph_depth,
        )

        response = {
            "root_paper_id": root_paper_id,
            "total_papers": result.total_papers,
            "cluster_count": len(result.clusters),
            "unclustered_count": len(result.unclustered_papers),
            "method": result.method,
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "label": c.label,
                    "paper_count": len(c.papers),
                    "cohesion_score": round(c.cohesion_score, 3),
                    "key_terms": c.key_terms[:5],
                    "year_range": c.year_range,
                    "central_paper": (
                        {
                            "paper_id": c.central_paper_id,
                            "title": next(
                                (
                                    p.title
                                    for p in c.papers
                                    if p.paper_id == c.central_paper_id
                                ),
                                "Unknown",
                            ),
                        }
                        if c.central_paper_id
                        else None
                    ),
                    "sample_papers": [
                        {
                            "paper_id": p.paper_id,
                            "title": p.title[:60],
                            "year": p.year,
                        }
                        for p in c.papers[:5]
                    ],
                }
                for c in result.clusters
            ],
        }

        return [types.TextContent(type="text", text=json.dumps(response, indent=2))]

    except Exception as e:
        logger.error(f"Error clustering papers: {e}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]
