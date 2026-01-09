"""
Tests for citation storage (CitationManager).
"""

from pathlib import Path

import pytest

from arxiv_citation_server.core.models import (
    CitationGraph,
    CitationRelationship,
    PaperInfo,
)
from arxiv_citation_server.resources.citations import CitationManager
from arxiv_citation_server.config import Settings


@pytest.fixture
def manager(temp_storage: Path) -> CitationManager:
    """Create a CitationManager with temp storage."""
    settings = Settings(STORAGE_PATH=temp_storage)
    return CitationManager(settings=settings)


class TestCitationManager:
    """Tests for CitationManager."""

    @pytest.mark.asyncio
    async def test_store_paper_info(
        self,
        manager: CitationManager,
        sample_paper: PaperInfo,
    ):
        """Test storing paper info as markdown."""
        path = await manager.store_paper_info(sample_paper)

        assert path.exists()
        assert path.suffix == ".md"

        content = path.read_text()
        assert sample_paper.title in content
        assert sample_paper.paper_id in content

    @pytest.mark.asyncio
    async def test_store_citations(
        self,
        manager: CitationManager,
        sample_citations: list[CitationRelationship],
    ):
        """Test storing citations as markdown."""
        paper_id = "2103.12345"
        path = await manager.store_citations(paper_id, sample_citations)

        assert path.exists()
        assert path.name == "citations.md"

        content = path.read_text()
        assert f"Papers Citing {paper_id}" in content
        assert "Paper 0 that cites the target" in content
        assert "Context 0" in content

    @pytest.mark.asyncio
    async def test_store_references(
        self,
        manager: CitationManager,
        sample_citations: list[CitationRelationship],
    ):
        """Test storing references as markdown."""
        paper_id = "2103.12345"
        path = await manager.store_references(paper_id, sample_citations)

        assert path.exists()
        assert path.name == "references.md"

        content = path.read_text()
        assert f"References from {paper_id}" in content

    @pytest.mark.asyncio
    async def test_store_graph(
        self,
        manager: CitationManager,
        sample_graph: CitationGraph,
    ):
        """Test storing citation graph as markdown."""
        path = await manager.store_graph(sample_graph)

        assert path.exists()
        assert "graph_depth2_both.md" in path.name

        content = path.read_text()
        assert "Citation Graph" in content
        assert str(sample_graph.node_count) in content

    @pytest.mark.asyncio
    async def test_has_citations(
        self,
        manager: CitationManager,
        sample_citations: list[CitationRelationship],
    ):
        """Test checking if citations exist."""
        paper_id = "2103.12345"

        # Before storing
        assert not await manager.has_citations(paper_id)

        # After storing
        await manager.store_citations(paper_id, sample_citations)
        assert await manager.has_citations(paper_id)

    @pytest.mark.asyncio
    async def test_list_stored_papers(
        self,
        manager: CitationManager,
        sample_paper: PaperInfo,
        sample_citations: list[CitationRelationship],
    ):
        """Test listing stored papers."""
        # Store some data
        await manager.store_paper_info(sample_paper)
        await manager.store_citations("2104.00000", sample_citations)

        papers = await manager.list_stored_papers()
        assert len(papers) >= 1

    @pytest.mark.asyncio
    async def test_paper_dir_sanitization(self, manager: CitationManager):
        """Test that paper IDs are sanitized for filesystem."""
        paper = PaperInfo(
            paper_id="cs.AI/2103.12345",  # Contains /
            title="Test",
        )
        path = await manager.store_paper_info(paper)

        # Should not contain / in path
        assert "/" not in path.parent.name

    @pytest.mark.asyncio
    async def test_markdown_formatting(
        self,
        manager: CitationManager,
        sample_citations: list[CitationRelationship],
    ):
        """Test that markdown is properly formatted."""
        paper_id = "2103.12345"
        path = await manager.store_citations(paper_id, sample_citations)

        content = path.read_text()

        # Check markdown structure
        assert content.startswith("# ")  # Title
        assert "**Authors:**" in content
        assert "**Year:**" in content
        assert "---" in content  # Dividers
        assert ">" in content  # Block quotes for contexts
