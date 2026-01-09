"""
MCP Tool: list_papers

List all locally stored papers.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import mcp.types as types

from ..resources import PaperManager

logger = logging.getLogger("arxiv-citation-server")

# Lazy initialization
_manager: PaperManager | None = None


def _get_manager() -> PaperManager:
    """Get or create the paper manager."""
    global _manager
    if _manager is None:
        _manager = PaperManager()
    return _manager


# Tool definition
list_papers_tool = types.Tool(
    name="list_papers",
    description="""List all papers stored locally.

Shows papers that have been downloaded and are available
for reading. Includes basic metadata for each paper.""",
    inputSchema={
        "type": "object",
        "properties": {
            "include_metadata": {
                "type": "boolean",
                "description": "Include paper metadata (slower, requires API calls)",
                "default": False,
            },
        },
    },
)


async def handle_list_papers(arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle the list_papers tool call."""
    try:
        manager = _get_manager()
        include_metadata = arguments.get("include_metadata", False)

        paper_ids = await manager.list_papers()

        if not paper_ids:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "total_papers": 0,
                        "papers": [],
                        "message": "No papers stored locally. Use download_paper to download papers.",
                        "storage_path": str(manager.storage_path),
                    }, indent=2),
                )
            ]

        papers = []
        for paper_id in paper_ids:
            paper_info = {"id": paper_id}

            if include_metadata:
                try:
                    metadata = await manager.get_paper_metadata(paper_id)
                    paper_info.update({
                        "title": metadata.get("title"),
                        "authors": metadata.get("authors", [])[:3],
                        "published": metadata.get("published"),
                    })
                except Exception as e:
                    paper_info["metadata_error"] = str(e)

            papers.append(paper_info)

        result = {
            "total_papers": len(papers),
            "papers": papers,
            "storage_path": str(manager.storage_path),
        }

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"List papers error: {e}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]
