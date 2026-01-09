"""
MCP Tool: search_papers

Search for papers on arXiv.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import arxiv
import mcp.types as types

from ..config import Settings

logger = logging.getLogger("arxiv-citation-server")

# Valid arXiv categories
VALID_CATEGORIES = {
    "cs", "econ", "eess", "math", "physics", "q-bio", "q-fin", "stat",
    "astro-ph", "cond-mat", "gr-qc", "hep-ex", "hep-lat", "hep-ph",
    "hep-th", "math-ph", "nlin", "nucl-ex", "nucl-th", "quant-ph",
}

# Tool definition
search_papers_tool = types.Tool(
    name="search_papers",
    description="""Search for papers on arXiv.

Supports various query formats:
- Simple keywords: "transformer attention"
- Exact phrases: "\"neural network\""
- Author search: au:vaswani
- Title search: ti:attention
- Abstract search: abs:language model
- Category filter: cat:cs.AI
- Combined: au:bengio AND ti:deep learning

Results include paper ID, title, authors, abstract, categories,
and publication date.""",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (supports arXiv query syntax)",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results to return (default: 10, max: 50)",
                "default": 10,
                "minimum": 1,
                "maximum": 50,
            },
            "categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter by arXiv categories (e.g., ['cs.AI', 'cs.LG'])",
            },
            "sort_by": {
                "type": "string",
                "enum": ["relevance", "date"],
                "description": "Sort results by relevance or date (default: relevance)",
                "default": "relevance",
            },
        },
        "required": ["query"],
    },
)


async def handle_search_papers(arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle the search_papers tool call."""
    try:
        settings = Settings()
        client = arxiv.Client()

        query = arguments["query"]
        max_results = min(arguments.get("max_results", 10), settings.MAX_SEARCH_RESULTS)
        categories = arguments.get("categories", [])
        sort_by = arguments.get("sort_by", "relevance")

        # Build query with category filters
        query_parts = [query]
        if categories:
            valid_cats = [c for c in categories if _is_valid_category(c)]
            if valid_cats:
                cat_filter = " OR ".join(f"cat:{cat}" for cat in valid_cats)
                query_parts.append(f"({cat_filter})")

        final_query = " AND ".join(query_parts) if len(query_parts) > 1 else query

        # Set sort criterion
        sort_criterion = (
            arxiv.SortCriterion.SubmittedDate
            if sort_by == "date"
            else arxiv.SortCriterion.Relevance
        )

        logger.info(f"Searching arXiv: {final_query} (max: {max_results})")

        # Execute search
        search = arxiv.Search(
            query=final_query,
            max_results=max_results,
            sort_by=sort_criterion,
        )

        papers = []
        for paper in client.results(search):
            papers.append({
                "id": paper.get_short_id(),
                "title": paper.title,
                "authors": [a.name for a in paper.authors[:5]],
                "author_count": len(paper.authors),
                "abstract": paper.summary[:500] + "..." if len(paper.summary) > 500 else paper.summary,
                "categories": paper.categories,
                "published": paper.published.strftime("%Y-%m-%d"),
                "pdf_url": paper.pdf_url,
                "arxiv_url": f"https://arxiv.org/abs/{paper.get_short_id()}",
            })

        result = {
            "query": query,
            "total_results": len(papers),
            "papers": papers,
        }

        if not papers:
            result["message"] = "No papers found matching your query."

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Search error: {e}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]


def _is_valid_category(category: str) -> bool:
    """Check if a category is valid."""
    # Check main category (e.g., "cs" from "cs.AI")
    main_cat = category.split(".")[0]
    return main_cat in VALID_CATEGORIES
