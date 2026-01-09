"""
Core citation analysis module.

This module contains the pure Python business logic with NO MCP dependencies.
It can be used directly by web applications or other Python code.

Example usage:
    from arxiv_citation_server.core import CitationService

    service = CitationService()
    citations = await service.get_citations("2103.12345")
"""

from .models import (
    CitationIntent,
    PaperInfo,
    CitationContext,
    CitationRelationship,
    CitationGraph,
)
from .service import CitationService
from .client import SemanticScholarClient

__all__ = [
    "CitationIntent",
    "PaperInfo",
    "CitationContext",
    "CitationRelationship",
    "CitationGraph",
    "CitationService",
    "SemanticScholarClient",
]
