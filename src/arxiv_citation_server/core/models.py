"""
Data models for citation analysis.

These models are pure Pydantic with no MCP dependencies,
making them usable by both MCP tools and web applications.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CitationIntent(str, Enum):
    """
    Semantic Scholar citation intents.

    - BACKGROUND: Historical context, justification, or related information
    - METHOD: Uses procedures or experiments from the cited paper
    - RESULT: Extends or builds on findings from the cited paper
    - UNKNOWN: Intent could not be determined
    """

    BACKGROUND = "background"
    METHOD = "method"
    RESULT = "result"
    UNKNOWN = "unknown"


class PaperInfo(BaseModel):
    """
    Compact paper metadata.

    This model stores only essential metadata, not the paper content itself.
    Content is stored separately as markdown files.
    """

    paper_id: str = Field(..., description="Primary identifier (arXiv ID or S2 ID)")
    title: str = Field(..., description="Paper title")
    authors: list[str] = Field(default_factory=list, description="List of author names")
    year: Optional[int] = Field(default=None, description="Publication year")
    venue: Optional[str] = Field(default=None, description="Publication venue")
    abstract: Optional[str] = Field(default=None, description="Paper abstract")

    # Cross-reference identifiers
    arxiv_id: Optional[str] = Field(default=None, description="arXiv identifier")
    doi: Optional[str] = Field(default=None, description="DOI")
    s2_paper_id: Optional[str] = Field(default=None, description="Semantic Scholar paper ID")

    # Citation metrics
    citation_count: Optional[int] = Field(default=None, description="Total citation count")
    reference_count: Optional[int] = Field(default=None, description="Number of references")
    influential_citation_count: Optional[int] = Field(
        default=None, description="Number of influential citations"
    )

    # Metadata
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this data was fetched"
    )

    class Config:
        frozen = True  # Immutable for use as dict keys


class CitationContext(BaseModel):
    """
    A citation mention with surrounding text.

    This captures the specific context in which a paper is cited,
    including the text snippet and the intent of the citation.
    """

    text: str = Field(..., description="Text snippet where the citation appears")
    intent: CitationIntent = Field(
        default=CitationIntent.UNKNOWN, description="Why the paper was cited"
    )
    section: Optional[str] = Field(
        default=None, description="Section where citation appears (e.g., 'Introduction')"
    )
    is_influential: bool = Field(
        default=False, description="Whether this is an influential citation"
    )


class CitationRelationship(BaseModel):
    """
    A citation link between two papers.

    Represents one paper citing another, with all the contexts
    where the citation appears.
    """

    citing_paper: PaperInfo = Field(..., description="The paper doing the citing")
    cited_paper: PaperInfo = Field(..., description="The paper being cited")
    contexts: list[CitationContext] = Field(
        default_factory=list, description="All citation mentions with context"
    )
    is_influential: bool = Field(
        default=False, description="Whether this is an influential citation"
    )

    # Metadata
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this relationship was fetched"
    )


class CitationGraph(BaseModel):
    """
    A network of citation relationships centered on a paper.

    This represents a citation graph traversed N levels deep
    from a starting paper.
    """

    root_paper_id: str = Field(..., description="The paper at the center of the graph")
    papers: dict[str, PaperInfo] = Field(
        default_factory=dict, description="All papers in the graph (paper_id -> PaperInfo)"
    )
    edges: list[tuple[str, str]] = Field(
        default_factory=list, description="Citation edges as (citing_id, cited_id) tuples"
    )
    depth: int = Field(..., description="How many levels were traversed")
    direction: str = Field(
        ..., description="Traversal direction: 'citations', 'references', or 'both'"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the graph was created"
    )

    @property
    def node_count(self) -> int:
        """Number of papers in the graph."""
        return len(self.papers)

    @property
    def edge_count(self) -> int:
        """Number of citation relationships in the graph."""
        return len(self.edges)

    def get_papers_at_depth(self, target_depth: int) -> list[PaperInfo]:
        """
        Get all papers at a specific depth from the root.

        Note: This requires depth tracking in papers, which is handled
        during graph construction.
        """
        # For now, this is a placeholder - full implementation
        # would track depth per paper during graph building
        return list(self.papers.values())

    def to_adjacency_list(self) -> dict[str, list[str]]:
        """Export graph as adjacency list for graph algorithms."""
        adj: dict[str, list[str]] = {pid: [] for pid in self.papers}
        for citing_id, cited_id in self.edges:
            if citing_id in adj:
                adj[citing_id].append(cited_id)
        return adj

    def get_citing_papers(self, paper_id: str) -> list[str]:
        """Get all papers that cite the given paper."""
        return [citing for citing, cited in self.edges if cited == paper_id]

    def get_referenced_papers(self, paper_id: str) -> list[str]:
        """Get all papers that the given paper cites."""
        return [cited for citing, cited in self.edges if citing == paper_id]


# =============================================================================
# NEW MODELS FOR ENHANCED FEATURES
# =============================================================================


class SimilarityMethod(str, Enum):
    """Methods for computing paper similarity."""

    CO_CITATION = "co_citation"  # Papers cited together
    BIBLIOGRAPHIC_COUPLING = "bibliographic_coupling"  # Papers citing same references
    CITATION_OVERLAP = "citation_overlap"  # Combined citation/reference overlap


class PaperSimilarity(BaseModel):
    """
    Similarity relationship between two papers.

    Computed locally from citation graph data, not from external ML services.
    """

    paper_a: PaperInfo = Field(..., description="First paper")
    paper_b: PaperInfo = Field(..., description="Second paper")
    similarity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Similarity score 0-1"
    )
    method: SimilarityMethod = Field(..., description="How similarity was computed")
    shared_citations: list[str] = Field(
        default_factory=list,
        description="Paper IDs that both papers cite (for bibliographic coupling)",
    )
    shared_citers: list[str] = Field(
        default_factory=list,
        description="Paper IDs that cite both papers (for co-citation)",
    )
    explanation: str = Field(default="", description="Human-readable explanation")

    class Config:
        frozen = True


class PaperCluster(BaseModel):
    """
    A cluster of related papers grouped by topic/methodology.

    Clustering is based on citation patterns, not external ML.
    """

    cluster_id: str = Field(..., description="Unique cluster identifier")
    label: str = Field(default="", description="Inferred cluster label/topic")
    papers: list[PaperInfo] = Field(
        default_factory=list, description="Papers in this cluster"
    )
    central_paper_id: Optional[str] = Field(
        default=None, description="Most central paper (highest in-cluster citations)"
    )
    cohesion_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Internal connectivity strength"
    )
    key_terms: list[str] = Field(
        default_factory=list, description="Common terms from titles/abstracts"
    )
    year_range: tuple[Optional[int], Optional[int]] = Field(
        default=(None, None), description="Year range of papers in cluster"
    )


class ClusteringResult(BaseModel):
    """Result of clustering a set of papers."""

    clusters: list[PaperCluster] = Field(default_factory=list)
    unclustered_papers: list[PaperInfo] = Field(
        default_factory=list, description="Papers that didn't fit any cluster"
    )
    total_papers: int = Field(default=0)
    method: str = Field(
        default="label_propagation", description="Clustering method used"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ResearchGap(BaseModel):
    """
    An identified gap in the research landscape.

    Gaps are identified through citation pattern analysis.
    """

    gap_id: str = Field(..., description="Unique gap identifier")
    description: str = Field(..., description="Description of the research gap")
    gap_type: str = Field(
        default="unexplored",
        description="Type: 'unexplored', 'bridging', 'temporal', 'methodological'",
    )
    evidence_papers: list[str] = Field(
        default_factory=list,
        description="Paper IDs that support this gap identification",
    )
    related_clusters: list[str] = Field(
        default_factory=list, description="Cluster IDs related to this gap"
    )
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    potential_topics: list[str] = Field(
        default_factory=list, description="Suggested research directions"
    )


class GapAnalysisResult(BaseModel):
    """Result of research gap analysis."""

    gaps: list[ResearchGap] = Field(default_factory=list)
    analyzed_paper_count: int = Field(default=0)
    analysis_depth: int = Field(default=2)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ResearchAreaSummary(BaseModel):
    """
    Synthesized summary of a research area from citation graph.
    """

    root_paper_id: str = Field(..., description="Starting paper for the analysis")
    area_name: str = Field(default="", description="Inferred area name")

    # Overview statistics
    total_papers: int = Field(default=0)
    year_range: tuple[Optional[int], Optional[int]] = Field(default=(None, None))

    # Key papers
    foundational_papers: list[PaperInfo] = Field(
        default_factory=list,
        description="Most-cited papers (foundations of the field)",
    )
    recent_influential: list[PaperInfo] = Field(
        default_factory=list,
        description="Recent papers with high citation velocity",
    )
    bridging_papers: list[PaperInfo] = Field(
        default_factory=list, description="Papers connecting different sub-areas"
    )

    # Themes
    major_themes: list[str] = Field(default_factory=list)
    methodology_trends: list[str] = Field(default_factory=list)

    # Evolution
    timeline: list[dict] = Field(
        default_factory=list, description="Key milestones by year"
    )

    # Clusters
    sub_areas: list[PaperCluster] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class PaperComparison(BaseModel):
    """
    Side-by-side comparison of two or more papers.
    """

    papers: list[PaperInfo] = Field(
        default_factory=list, description="Papers being compared"
    )

    # Metadata comparison
    publication_timeline: list[dict] = Field(default_factory=list)
    venue_comparison: dict[str, str] = Field(default_factory=dict)

    # Citation comparison
    citation_counts: dict[str, int] = Field(default_factory=dict)
    shared_references: list[PaperInfo] = Field(
        default_factory=list, description="Papers cited by all compared papers"
    )
    unique_references: dict[str, list[PaperInfo]] = Field(
        default_factory=dict,
        description="Paper ID -> references unique to that paper",
    )

    # Influence comparison
    shared_citers: list[PaperInfo] = Field(
        default_factory=list, description="Papers that cite all compared papers"
    )
    citation_overlap_score: float = Field(default=0.0, ge=0.0, le=1.0)

    # Content comparison (from abstracts)
    common_themes: list[str] = Field(default_factory=list)
    distinguishing_aspects: dict[str, list[str]] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class SearchResult(BaseModel):
    """
    Result from Semantic Scholar paper search.
    """

    query: str = Field(..., description="Original search query")
    total_results: int = Field(default=0)
    papers: list[PaperInfo] = Field(default_factory=list)
    next_offset: Optional[int] = Field(default=None, description="For pagination")
    searched_at: datetime = Field(default_factory=datetime.utcnow)
