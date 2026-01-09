"""
Tests for CitationService.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arxiv_citation_server.core.models import (
    CitationIntent,
    CitationRelationship,
    PaperInfo,
)
from arxiv_citation_server.core.service import CitationService


@pytest.fixture
def service() -> CitationService:
    """Create a CitationService instance."""
    return CitationService()


class TestCitationService:
    """Tests for CitationService."""

    @pytest.mark.asyncio
    async def test_get_paper_info(self, service: CitationService, mock_s2_client: AsyncMock):
        """Test getting paper info."""
        with patch.object(service, "client", mock_s2_client):
            paper = await service.get_paper_info("2103.12345")

            assert paper is not None
            assert paper.title == "Test Paper"
            mock_s2_client.get_paper.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_citations(self, service: CitationService, mock_s2_client: AsyncMock):
        """Test getting citations."""
        with patch.object(service, "client", mock_s2_client):
            citations = await service.get_citations("2103.12345", limit=10)

            assert len(citations) > 0
            mock_s2_client.get_citations.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_citations_without_contexts(
        self,
        service: CitationService,
        mock_s2_client: AsyncMock,
    ):
        """Test getting citations with contexts stripped."""
        # Mock a citation with contexts
        mock_citation = CitationRelationship(
            citing_paper=PaperInfo(paper_id="cite1", title="Citing Paper"),
            cited_paper=PaperInfo(paper_id="2103.12345", title="Target"),
            contexts=[],
            is_influential=True,
        )

        mock_s2_client.get_citations.return_value = [mock_citation]

        with patch.object(service, "client", mock_s2_client):
            citations = await service.get_citations(
                "2103.12345",
                include_contexts=False,
            )

            assert len(citations) == 1
            # Contexts should be empty when include_contexts=False
            assert len(citations[0].contexts) == 0

    @pytest.mark.asyncio
    async def test_get_references(self, service: CitationService, mock_s2_client: AsyncMock):
        """Test getting references."""
        with patch.object(service, "client", mock_s2_client):
            references = await service.get_references("2103.12345", limit=20)

            assert len(references) > 0
            mock_s2_client.get_references.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_citation_summary(
        self,
        service: CitationService,
        mock_s2_client: AsyncMock,
    ):
        """Test getting citation summary."""
        with patch.object(service, "client", mock_s2_client):
            summary = await service.get_citation_summary("2103.12345")

            assert "paper_id" in summary
            assert "citation_count" in summary
            assert summary["title"] == "Test Paper"

    @pytest.mark.asyncio
    async def test_get_citation_summary_not_found(
        self,
        service: CitationService,
        mock_s2_client: AsyncMock,
    ):
        """Test citation summary when paper not found."""
        mock_s2_client.get_paper.return_value = None

        with patch.object(service, "client", mock_s2_client):
            summary = await service.get_citation_summary("nonexistent")

            assert "error" in summary

    @pytest.mark.asyncio
    async def test_limit_enforcement(
        self,
        service: CitationService,
        mock_s2_client: AsyncMock,
    ):
        """Test that limits are enforced."""
        with patch.object(service, "client", mock_s2_client):
            # Request more than max
            await service.get_citations("2103.12345", limit=500)

            # Should be capped at 100
            call_args = mock_s2_client.get_citations.call_args
            assert call_args[1]["limit"] <= 100


class TestCitationServiceInit:
    """Tests for CitationService initialization."""

    def test_default_init(self):
        """Test default initialization."""
        service = CitationService()
        assert service.client is not None

    def test_custom_api_key(self):
        """Test initialization with API key."""
        service = CitationService(api_key="test-key")
        assert service.client.api_key == "test-key"

    def test_custom_timeout(self):
        """Test initialization with custom timeout."""
        service = CitationService(timeout=120)
        assert service.client.timeout == 120
