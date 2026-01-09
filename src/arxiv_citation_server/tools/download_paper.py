"""
MCP Tool: download_paper

Download a paper from arXiv and store as markdown.
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
download_paper_tool = types.Tool(
    name="download_paper",
    description="""Download a paper from arXiv and store locally as markdown.

Downloads the PDF, converts it to markdown for easy reading,
and stores it at ~/.arxiv-citation-server/papers/{paper_id}.md

The markdown includes:
- Paper metadata (title, authors, abstract, categories)
- Full paper content converted from PDF

Use this before reading a paper's content.""",
    inputSchema={
        "type": "object",
        "properties": {
            "paper_id": {
                "type": "string",
                "description": "arXiv paper ID (e.g., '2103.12345' or '2103.12345v1')",
            },
        },
        "required": ["paper_id"],
    },
)


async def handle_download_paper(arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle the download_paper tool call."""
    try:
        manager = _get_manager()
        paper_id = arguments["paper_id"]

        # Clean paper ID (remove version if present for storage)
        clean_id = paper_id.split("v")[0] if "v" in paper_id else paper_id

        logger.info(f"Downloading paper: {paper_id}")

        # Check if already downloaded
        if await manager.has_paper(clean_id):
            path = manager._get_paper_path(clean_id)
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "paper_id": clean_id,
                        "status": "already_stored",
                        "stored_at": str(path),
                        "message": "Paper was already downloaded. Use read_paper to view content.",
                    }, indent=2),
                )
            ]

        # Download and store
        path = await manager.store_paper(paper_id)

        # Get metadata for response
        metadata = await manager.get_paper_metadata(clean_id)

        result = {
            "paper_id": clean_id,
            "status": "downloaded",
            "stored_at": str(path),
            "title": metadata.get("title"),
            "authors": metadata.get("authors", [])[:5],
            "message": "Paper downloaded and converted to markdown. Use read_paper to view content.",
        }

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except ValueError as e:
        logger.error(f"Download error: {e}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({
                    "paper_id": arguments.get("paper_id"),
                    "status": "error",
                    "error": str(e),
                }, indent=2),
            )
        ]
    except Exception as e:
        logger.error(f"Unexpected download error: {e}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]
