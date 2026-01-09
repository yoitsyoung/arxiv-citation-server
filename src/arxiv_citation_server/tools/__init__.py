"""
MCP Tools for citation operations.

Each tool wraps the core CitationService to provide
MCP-compatible interfaces.
"""

from .get_citations import get_citations_tool, handle_get_citations
from .get_references import get_references_tool, handle_get_references
from .build_graph import build_graph_tool, handle_build_graph

__all__ = [
    "get_citations_tool",
    "handle_get_citations",
    "get_references_tool",
    "handle_get_references",
    "build_graph_tool",
    "handle_build_graph",
]
