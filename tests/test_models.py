"""
Tests for core data models.
"""

import pytest
from datetime import datetime

from arxiv_citation_server.core.models import (
    CitationContext,
    CitationGraph,
    CitationIntent,
    CitationRelationship,
    PaperInfo,
)


class TestPaperInfo:
    """Tests for PaperInfo model."""

    def test_create_minimal(self):
        """Test creating paper with minimal fields."""
        paper = PaperInfo(paper_id="2103.12345", title="Test Paper")
        assert paper.paper_id == "2103.12345"
        assert paper.title == "Test Paper"
        assert paper.authors == []
        assert paper.year is None

    def test_create_full(self, sample_paper: PaperInfo):
        """Test creating paper with all fields."""
        assert sample_paper.paper_id == "2103.12345"
        assert sample_paper.title == "Attention Is All You Need"
        assert len(sample_paper.authors) == 3
        assert sample_paper.year == 2017
        assert sample_paper.citation_count == 50000

    def test_immutable(self, sample_paper: PaperInfo):
        """Test that PaperInfo is immutable (frozen)."""
        with pytest.raises(Exception):  # ValidationError or AttributeError
            sample_paper.title = "Changed Title"

    def test_serialization(self, sample_paper: PaperInfo):
        """Test JSON serialization."""
        data = sample_paper.model_dump()
        assert data["paper_id"] == "2103.12345"
        assert data["title"] == "Attention Is All You Need"

        # Roundtrip
        restored = PaperInfo(**data)
        assert restored.paper_id == sample_paper.paper_id


class TestCitationContext:
    """Tests for CitationContext model."""

    def test_create_with_intent(self, sample_citation_context: CitationContext):
        """Test creating context with intent."""
        assert sample_citation_context.intent == CitationIntent.METHOD
        assert "transformer" in sample_citation_context.text
        assert sample_citation_context.is_influential

    def test_default_intent(self):
        """Test default intent is UNKNOWN."""
        ctx = CitationContext(text="Some citation text")
        assert ctx.intent == CitationIntent.UNKNOWN
        assert not ctx.is_influential


class TestCitationIntent:
    """Tests for CitationIntent enum."""

    def test_values(self):
        """Test all intent values exist."""
        assert CitationIntent.BACKGROUND.value == "background"
        assert CitationIntent.METHOD.value == "method"
        assert CitationIntent.RESULT.value == "result"
        assert CitationIntent.UNKNOWN.value == "unknown"


class TestCitationRelationship:
    """Tests for CitationRelationship model."""

    def test_create(self, sample_citation: CitationRelationship):
        """Test creating citation relationship."""
        assert sample_citation.citing_paper.paper_id == "2104.56789"
        assert sample_citation.cited_paper.paper_id == "2103.12345"
        assert len(sample_citation.contexts) == 1
        assert sample_citation.is_influential

    def test_multiple_contexts(
        self,
        sample_citing_paper: PaperInfo,
        sample_paper: PaperInfo,
    ):
        """Test citation with multiple contexts."""
        contexts = [
            CitationContext(text="Context 1", intent=CitationIntent.BACKGROUND),
            CitationContext(text="Context 2", intent=CitationIntent.METHOD),
            CitationContext(text="Context 3", intent=CitationIntent.RESULT),
        ]
        citation = CitationRelationship(
            citing_paper=sample_citing_paper,
            cited_paper=sample_paper,
            contexts=contexts,
        )
        assert len(citation.contexts) == 3


class TestCitationGraph:
    """Tests for CitationGraph model."""

    def test_create(self, sample_graph: CitationGraph):
        """Test creating citation graph."""
        assert sample_graph.root_paper_id == "2103.12345"
        assert sample_graph.depth == 2
        assert sample_graph.direction == "both"

    def test_node_count(self, sample_graph: CitationGraph):
        """Test node count property."""
        assert sample_graph.node_count == 4  # root + 3 connected

    def test_edge_count(self, sample_graph: CitationGraph):
        """Test edge count property."""
        assert sample_graph.edge_count == 3

    def test_adjacency_list(self, sample_graph: CitationGraph):
        """Test adjacency list generation."""
        adj = sample_graph.to_adjacency_list()
        assert isinstance(adj, dict)
        assert sample_graph.root_paper_id in adj

    def test_get_citing_papers(self, sample_graph: CitationGraph):
        """Test getting papers that cite a paper."""
        citing = sample_graph.get_citing_papers(sample_graph.root_paper_id)
        assert len(citing) == 3

    def test_get_referenced_papers(self, sample_graph: CitationGraph):
        """Test getting papers that a paper references."""
        # In our sample, graph_0 references the root
        refs = sample_graph.get_referenced_papers("graph_0")
        assert sample_graph.root_paper_id in refs
