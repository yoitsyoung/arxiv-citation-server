"""
MCP Tools for paper and citation operations.

Provides tools for:
- Paper operations: search, download, list, read
- Citation operations: get citations, get references, build graph
- Analysis operations: similarity, clustering, gaps, comparison, summarization
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

# Advanced search
from .search_s2 import search_s2_tool, handle_search_s2

# Analysis tools
from .find_similar import find_similar_tool, handle_find_similar
from .cluster_papers import cluster_papers_tool, handle_cluster_papers
from .summarize_area import summarize_area_tool, handle_summarize_area
from .find_gaps import find_gaps_tool, handle_find_gaps
from .compare_papers import compare_papers_tool, handle_compare_papers

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
    # Advanced search
    "search_s2_tool",
    "handle_search_s2",
    # Analysis tools
    "find_similar_tool",
    "handle_find_similar",
    "cluster_papers_tool",
    "handle_cluster_papers",
    "summarize_area_tool",
    "handle_summarize_area",
    "find_gaps_tool",
    "handle_find_gaps",
    "compare_papers_tool",
    "handle_compare_papers",
]
