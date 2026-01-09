"""
MCP Tool: get_paper_references

Gets papers referenced by a given arXiv paper.
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

# Lazy initialization (shared with get_citations if same process)
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
get_references_tool = types.Tool(
    name="get_paper_references",
    description="""Get papers referenced by a given paper.

Returns the papers that the target paper cites, useful for:
- Understanding the foundation a paper builds on
- Finding related prior work
- Building literature reviews

Results include citation contexts when available, showing
how each reference is used in the paper.

Results are saved as human-readable markdown at:
~/.arxiv-citation-server/citations/{paper_id}/references.md""",
    inputSchema={
        "type": "object",
        "properties": {
            "paper_id": {
                "type": "string",
                "description": "Paper identifier: arXiv ID (e.g., '1908.10063'), Semantic Scholar ID (40-char hex), or DOI (e.g., '10.xxxx/...')",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum references to return (default: 50, max: 100)",
                "default": 50,
                "minimum": 1,
                "maximum": 100,
            },
            "include_contexts": {
                "type": "boolean",
                "description": "Include citation context snippets (default: true)",
                "default": True,
            },
        },
        "required": ["paper_id"],
    },
)


async def handle_get_references(arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle the get_paper_references tool call."""
    try:
        service = _get_service()
        manager = _get_manager()

        paper_id = arguments["paper_id"]
        limit = min(arguments.get("limit", 50), 100)
        include_contexts = arguments.get("include_contexts", True)

        logger.info(f"Fetching references for {paper_id} (limit={limit})")

        # Fetch references from Semantic Scholar
        references = await service.get_references(
            paper_id,
            limit=limit,
            include_contexts=include_contexts,
        )

        if not references:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "paper_id": paper_id,
                        "total_references": 0,
                        "message": "No references found. The paper may not be indexed in Semantic Scholar.",
                    }, indent=2),
                )
            ]

        # Store as markdown
        md_path = await manager.store_references(paper_id, references)

        # Also store paper info if available
        if references and references[0].citing_paper:
            await manager.store_paper_info(references[0].citing_paper)

        # Build response
        result = {
            "paper_id": paper_id,
            "total_references": len(references),
            "stored_at": str(md_path),
            "influential_count": sum(1 for r in references if r.is_influential),
            "references": [
                {
                    "title": r.cited_paper.title,
                    "authors": r.cited_paper.authors[:3],
                    "year": r.cited_paper.year,
                    "arxiv_id": r.cited_paper.arxiv_id,
                    "is_influential": r.is_influential,
                    "context_preview": (
                        r.contexts[0].text[:200] + "..."
                        if r.contexts and len(r.contexts[0].text) > 200
                        else r.contexts[0].text if r.contexts else None
                    ),
                    "intent": r.contexts[0].intent.value if r.contexts else None,
                }
                for r in references[:10]  # Preview first 10
            ],
        }

        if len(references) > 10:
            result["note"] = f"Showing 10 of {len(references)} references. See {md_path} for full list."

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Error fetching references: {e}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]
