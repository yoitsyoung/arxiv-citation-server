"""
Configuration for the arxiv-citation-server.

Uses Pydantic Settings for environment variable support.
All settings can be overridden via environment variables with
the CITATION_ prefix.
"""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    Environment variables are prefixed with CITATION_.
    Example: CITATION_S2_API_KEY=your-key

    Storage:
        Papers are stored as human-readable markdown files at:
        ~/.arxiv-citation-server/citations/{paper_id}/
    """

    model_config = SettingsConfigDict(
        env_prefix="CITATION_",
        extra="ignore",
    )

    # Application info
    APP_NAME: str = "arxiv-citation-server"
    APP_VERSION: str = "0.1.0"

    # Storage configuration
    STORAGE_PATH: Path = Path.home() / ".arxiv-citation-server" / "citations"
    PAPERS_PATH: Path = Path.home() / ".arxiv-citation-server" / "papers"

    # Semantic Scholar API
    S2_API_KEY: Optional[str] = None  # Optional, for higher rate limits
    REQUEST_TIMEOUT: int = 60  # Seconds

    # Rate limiting (informational - handled by semanticscholar library)
    # Without API key: ~100 requests per 5 minutes
    # With API key: ~1 request per second

    # Result limits
    MAX_CITATIONS: int = 100  # Maximum citations to return
    MAX_REFERENCES: int = 100  # Maximum references to return
    MAX_GRAPH_DEPTH: int = 3  # Maximum citation graph depth
    MAX_PAPERS_PER_LEVEL: int = 50  # Max papers at each graph level

    # Caching
    CACHE_DAYS: int = 7  # Days to cache citation data before refreshing

    # arXiv search settings
    MAX_SEARCH_RESULTS: int = 50  # Max results per search

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure storage directories exist
        self.STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        self.PAPERS_PATH.mkdir(parents=True, exist_ok=True)
