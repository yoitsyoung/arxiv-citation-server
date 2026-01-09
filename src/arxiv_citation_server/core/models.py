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
