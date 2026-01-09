"""
ArXiv Citation Server
=====================

Citation relationship analysis for arXiv papers using Semantic Scholar.

This package provides:
- core: Pure Python citation service (no MCP dependencies, usable by web apps)
- resources: Citation storage management (markdown files)
- tools: MCP tools for citation operations
- prompts: MCP prompts for guided citation analysis
"""

from .server import main

__version__ = "0.1.0"
__all__ = ["main"]
