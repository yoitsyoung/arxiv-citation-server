"""
MCP Tools for paper and citation operations.

Provides tools for:
- Paper operations: search, download, list, read
- Citation operations: get citations, get references, build graph
"""

# Paper tools
from .search_papers import search_papers_tool, handle_search_papers
from .download_paper import download_paper_tool, handle_download_paper
from .list_papers import list_papers_tool, handle_list_papers
from .read_paper import read_paper_tool, handle_read_paper

# Citation tools
from .get_citations import get_citations_tool, handle_get_citations
from .get_references import get_references_tool, handle_get_references
from .build_graph import build_graph_tool, handle_build_graph

__all__ = [
    # Paper tools
    "search_papers_tool",
    "handle_search_papers",
    "download_paper_tool",
    "handle_download_paper",
    "list_papers_tool",
    "handle_list_papers",
    "read_paper_tool",
    "handle_read_paper",
    # Citation tools
    "get_citations_tool",
    "handle_get_citations",
    "get_references_tool",
    "handle_get_references",
    "build_graph_tool",
    "handle_build_graph",
]
