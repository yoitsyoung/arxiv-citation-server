"""
MCP Tool: get_paper_citations

Gets papers that cite a given arXiv paper, with citation contexts.
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
get_citations_tool = types.Tool(
    name="get_paper_citations",
    description="""Get papers that cite a given paper.

Returns citation relationships with:
- Paper metadata (title, authors, year, venue)
- Citation contexts (text snippets showing how it's cited)
- Citation intents (Background, Method, Result)
- Whether the citation is influential

Results are saved as human-readable markdown at:
~/.arxiv-citation-server/citations/{paper_id}/citations.md

Use this to:
- Find follow-up work that builds on a paper
- Discover competing approaches
- Understand a paper's influence in the field""",
    inputSchema={
        "type": "object",
        "properties": {
            "paper_id": {
                "type": "string",
                "description": "Paper identifier: arXiv ID (e.g., '1908.10063'), Semantic Scholar ID (40-char hex), or DOI (e.g., '10.xxxx/...')",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum citations to return (default: 20, max: 100)",
                "default": 20,
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


async def handle_get_citations(arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle the get_paper_citations tool call."""
    try:
        service = _get_service()
        manager = _get_manager()

        paper_id = arguments["paper_id"]
        limit = min(arguments.get("limit", 20), 100)
        include_contexts = arguments.get("include_contexts", True)

        logger.info(f"Fetching citations for {paper_id} (limit={limit})")

        # Fetch citations from Semantic Scholar
        citations = await service.get_citations(
            paper_id,
            limit=limit,
            include_contexts=include_contexts,
        )

        if not citations:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "paper_id": paper_id,
                        "total_citations": 0,
                        "message": "No citations found. The paper may not be indexed in Semantic Scholar.",
                    }, indent=2),
                )
            ]

        # Store as markdown
        md_path = await manager.store_citations(paper_id, citations)

        # Also store paper info if available
        if citations and citations[0].cited_paper:
            await manager.store_paper_info(citations[0].cited_paper)

        # Build response
        result = {
            "paper_id": paper_id,
            "total_citations": len(citations),
            "stored_at": str(md_path),
            "influential_count": sum(1 for c in citations if c.is_influential),
            "citations": [
                {
                    "title": c.citing_paper.title,
                    "authors": c.citing_paper.authors[:3],
                    "year": c.citing_paper.year,
                    "arxiv_id": c.citing_paper.arxiv_id,
                    "is_influential": c.is_influential,
                    "context_preview": (
                        c.contexts[0].text[:200] + "..."
                        if c.contexts and len(c.contexts[0].text) > 200
                        else c.contexts[0].text if c.contexts else None
                    ),
                    "intent": c.contexts[0].intent.value if c.contexts else None,
                }
                for c in citations[:10]  # Preview first 10
            ],
        }

        if len(citations) > 10:
            result["note"] = f"Showing 10 of {len(citations)} citations. See {md_path} for full list."

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Error fetching citations: {e}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]
