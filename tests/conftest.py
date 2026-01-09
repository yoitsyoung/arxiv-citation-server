"""
Shared test fixtures for arxiv-citation-server tests.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from arxiv_citation_server.core.models import (
    CitationContext,
    CitationGraph,
    CitationIntent,
    CitationRelationship,
    PaperInfo,
)
from arxiv_citation_server.config import Settings


@pytest.fixture
def sample_paper() -> PaperInfo:
    """Create a sample paper for testing."""
    return PaperInfo(
        paper_id="2103.12345",
        title="Attention Is All You Need",
        authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
        year=2017,
        venue="NeurIPS",
        arxiv_id="2103.12345",
        doi="10.5555/3295222.3295349",
        s2_paper_id="abc123def456",
        citation_count=50000,
        reference_count=40,
        influential_citation_count=5000,
    )


@pytest.fixture
def sample_citing_paper() -> PaperInfo:
    """Create a sample citing paper for testing."""
    return PaperInfo(
        paper_id="2104.56789",
        title="BERT: Pre-training of Deep Bidirectional Transformers",
        authors=["Jacob Devlin", "Ming-Wei Chang"],
        year=2018,
        venue="NAACL",
        arxiv_id="2104.56789",
        citation_count=30000,
    )


@pytest.fixture
def sample_citation_context() -> CitationContext:
    """Create a sample citation context."""
    return CitationContext(
        text="Building on the transformer architecture introduced in [1], we propose...",
        intent=CitationIntent.METHOD,
        section="Introduction",
        is_influential=True,
    )


@pytest.fixture
def sample_citation(
    sample_citing_paper: PaperInfo,
    sample_paper: PaperInfo,
    sample_citation_context: CitationContext,
) -> CitationRelationship:
    """Create a sample citation relationship."""
    return CitationRelationship(
        citing_paper=sample_citing_paper,
        cited_paper=sample_paper,
        contexts=[sample_citation_context],
        is_influential=True,
    )


@pytest.fixture
def sample_citations(sample_paper: PaperInfo) -> list[CitationRelationship]:
    """Create a list of sample citations."""
    citations = []
    for i in range(5):
        citing_paper = PaperInfo(
            paper_id=f"210{i}.{i}0000",
            title=f"Paper {i} that cites the target",
            authors=[f"Author {i}"],
            year=2020 + i,
        )
        citations.append(
            CitationRelationship(
                citing_paper=citing_paper,
                cited_paper=sample_paper,
                contexts=[
                    CitationContext(
                        text=f"Context {i}: We use the approach from [target]...",
                        intent=CitationIntent.METHOD if i % 2 == 0 else CitationIntent.BACKGROUND,
                    )
                ],
                is_influential=i < 2,
            )
        )
    return citations


@pytest.fixture
def sample_graph(sample_paper: PaperInfo) -> CitationGraph:
    """Create a sample citation graph."""
    papers = {
        sample_paper.paper_id: sample_paper,
    }
    edges = []

    # Add some connected papers
    for i in range(3):
        paper = PaperInfo(
            paper_id=f"graph_{i}",
            title=f"Graph Paper {i}",
            authors=[f"Graph Author {i}"],
            year=2020 + i,
        )
        papers[paper.paper_id] = paper
        edges.append((paper.paper_id, sample_paper.paper_id))

    return CitationGraph(
        root_paper_id=sample_paper.paper_id,
        papers=papers,
        edges=edges,
        depth=2,
        direction="both",
    )


@pytest.fixture
def temp_storage(tmp_path: Path) -> Path:
    """Create a temporary storage directory."""
    storage_path = tmp_path / "citations"
    storage_path.mkdir(parents=True)
    return storage_path


@pytest.fixture
def mock_settings(temp_storage: Path) -> Settings:
    """Create settings with temporary storage."""
    return Settings(STORAGE_PATH=temp_storage)


@pytest.fixture
def mock_s2_client() -> AsyncMock:
    """Create a mock Semantic Scholar client."""
    client = AsyncMock()

    # Mock paper result
    mock_paper = MagicMock()
    mock_paper.paperId = "abc123"
    mock_paper.title = "Test Paper"
    mock_paper.authors = [MagicMock(name="Author One"), MagicMock(name="Author Two")]
    mock_paper.year = 2023
    mock_paper.venue = "Test Venue"
    mock_paper.citationCount = 100
    mock_paper.referenceCount = 50
    mock_paper.influentialCitationCount = 10
    mock_paper.externalIds = {"ArXiv": "2103.12345", "DOI": "10.1234/test"}

    client.get_paper.return_value = mock_paper

    # Mock citations
    mock_citation = MagicMock()
    mock_citation.paperId = "citing123"
    mock_citation.title = "Citing Paper"
    mock_citation.authors = [MagicMock(name="Citing Author")]
    mock_citation.year = 2024
    mock_citation.venue = "Citing Venue"
    mock_citation.citationCount = 50
    mock_citation.externalIds = {"ArXiv": "2104.00001"}
    mock_citation.contexts = ["We build on the work of [1]..."]
    mock_citation.intents = [["methodology"]]
    mock_citation.isInfluential = True

    client.get_paper_citations.return_value = [mock_citation]
    client.get_paper_references.return_value = [mock_citation]

    return client
