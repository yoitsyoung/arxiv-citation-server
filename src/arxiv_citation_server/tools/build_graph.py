"""
MCP Tool: build_citation_graph

Builds a citation network graph around a paper.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import mcp.types as types

from ..config import Settings
from ..core import CitationService
from ..resources import CitationManager

logger = logging.getLogger("arxiv-citation-server")

# Lazy initialization
_service: CitationService | None = None
_manager: CitationManager | None = None


def _get_service() -> CitationService:
    """Get or create the citation service."""
    global _service
    if _service is None:
        settings = Settings()
        _service = CitationService(
            api_key=settings.S2_API_KEY,
            timeout=settings.REQUEST_TIMEOUT,
        )
    return _service


def _get_manager() -> CitationManager:
    """Get or create the citation manager."""
    global _manager
    if _manager is None:
        _manager = CitationManager()
    return _manager


# Tool definition
build_graph_tool = types.Tool(
    name="build_citation_graph",
    description="""Build a citation network graph around a paper.

Creates a graph showing citation relationships N levels deep.
Useful for:
- Understanding a paper's position in the literature
- Finding clusters of related work
- Identifying influential papers in a research area
- Building comprehensive literature reviews

The graph traverses in the specified direction:
- 'citations': Find papers that cite the root, then papers that cite those, etc.
- 'references': Find papers the root cites, then papers those cite, etc.
- 'both': Traverse in both directions

Results are saved as markdown at:
~/.arxiv-citation-server/citations/{paper_id}/graph_depth{N}_{direction}.md

Warning: Higher depths exponentially increase API calls.
Depth 2 is recommended for most use cases.""",
    inputSchema={
        "type": "object",
        "properties": {
            "paper_id": {
                "type": "string",
                "description": "Paper identifier: arXiv ID (e.g., '1908.10063'), Semantic Scholar ID (40-char hex), or DOI",
            },
            "depth": {
                "type": "integer",
                "description": "How many citation levels to traverse (default: 2, max: 3)",
                "default": 2,
                "minimum": 1,
                "maximum": 3,
            },
            "direction": {
                "type": "string",
                "enum": ["citations", "references", "both"],
                "description": "Which direction to traverse (default: 'both')",
                "default": "both",
            },
            "max_papers_per_level": {
                "type": "integer",
                "description": "Max papers to fetch at each level (default: 25)",
                "default": 25,
                "minimum": 5,
                "maximum": 50,
            },
        },
        "required": ["paper_id"],
    },
)


async def handle_build_graph(arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle the build_citation_graph tool call."""
    try:
        service = _get_service()
        manager = _get_manager()

        paper_id = arguments["paper_id"]
        depth = min(arguments.get("depth", 2), 3)
        direction = arguments.get("direction", "both")
        max_papers_per_level = min(arguments.get("max_papers_per_level", 25), 50)

        logger.info(
            f"Building citation graph for {paper_id} "
            f"(depth={depth}, direction={direction})"
        )

        # Build the graph
        graph = await service.build_citation_graph(
            paper_id,
            depth=depth,
            direction=direction,
            max_papers_per_level=max_papers_per_level,
        )

        if graph.node_count == 0:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "paper_id": paper_id,
                        "error": "Could not build graph. Paper may not be indexed.",
                    }, indent=2),
                )
            ]

        # Store as markdown
        md_path = await manager.store_graph(graph)

        # Get root paper info
        root_paper = graph.papers.get(paper_id)
        root_title = root_paper.title if root_paper else paper_id

        # Find most cited papers in the graph
        citation_counts = {}
        for citing_id, cited_id in graph.edges:
            citation_counts[cited_id] = citation_counts.get(cited_id, 0) + 1

        top_cited = sorted(
            citation_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        # Build response
        result = {
            "paper_id": paper_id,
            "root_title": root_title,
            "depth": depth,
            "direction": direction,
            "stored_at": str(md_path),
            "statistics": {
                "total_papers": graph.node_count,
                "total_edges": graph.edge_count,
            },
            "most_cited_in_graph": [
                {
                    "paper_id": pid,
                    "title": graph.papers[pid].title if pid in graph.papers else pid,
                    "citations_in_graph": count,
                }
                for pid, count in top_cited
            ],
            "sample_papers": [
                {
                    "paper_id": p.paper_id,
                    "title": p.title[:80] + "..." if len(p.title) > 80 else p.title,
                    "year": p.year,
                }
                for p in list(graph.papers.values())[:10]
            ],
        }

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Error building graph: {e}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]
