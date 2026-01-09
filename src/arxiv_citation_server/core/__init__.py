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
    # New models
    SimilarityMethod,
    PaperSimilarity,
    PaperCluster,
    ClusteringResult,
    ResearchGap,
    GapAnalysisResult,
    ResearchAreaSummary,
    PaperComparison,
    SearchResult,
)
from .service import CitationService
from .client import SemanticScholarClient
from .analysis import (
    SimilarityAnalyzer,
    ClusterAnalyzer,
    GapAnalyzer,
    SummaryGenerator,
    ComparisonAnalyzer,
)

__all__ = [
    # Original models
    "CitationIntent",
    "PaperInfo",
    "CitationContext",
    "CitationRelationship",
    "CitationGraph",
    # New models
    "SimilarityMethod",
    "PaperSimilarity",
    "PaperCluster",
    "ClusteringResult",
    "ResearchGap",
    "GapAnalysisResult",
    "ResearchAreaSummary",
    "PaperComparison",
    "SearchResult",
    # Service
    "CitationService",
    "SemanticScholarClient",
    # Analyzers
    "SimilarityAnalyzer",
    "ClusterAnalyzer",
    "GapAnalyzer",
    "SummaryGenerator",
    "ComparisonAnalyzer",
]
