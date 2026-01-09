"""
Resources layer for data management.

Handles storage and retrieval of papers and citation data
as human-readable markdown files.
"""

from .citations import CitationManager
from .papers import PaperManager

__all__ = ["CitationManager", "PaperManager"]
