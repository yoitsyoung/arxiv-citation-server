"""
Citation service - main business logic.

This is the core service that can be used by both MCP tools
and web applications. It has NO MCP dependencies.
"""

from __future__ import annotations

import logging
from typing import Optional

from .analysis import (
    ClusterAnalyzer,
    ComparisonAnalyzer,
    GapAnalyzer,
    SimilarityAnalyzer,
    SummaryGenerator,
)
from .client import SemanticScholarClient
from .graph import GraphBuilder
from .models import (
    CitationGraph,
    CitationRelationship,
    ClusteringResult,
    GapAnalysisResult,
    PaperComparison,
    PaperInfo,
    PaperSimilarity,
    ResearchAreaSummary,
    SearchResult,
    SimilarityMethod,
)

logger = logging.getLogger("arxiv-citation-server")


class CitationService:
    """
    Core citation analysis service.

    This class provides all citation-related functionality without
    any MCP dependencies. It can be used directly by:
    - MCP tools (via the tools layer)
    - Web applications (import directly)
    - CLI tools
    - Jupyter notebooks

    Example usage:
        service = CitationService()
        citations = await service.get_citations("2103.12345")
        for cit in citations:
            print(f"{cit.citing_paper.title} cites this paper")
            for ctx in cit.contexts:
                print(f"  Context: {ctx.text[:100]}...")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 60,
    ):
        """
        Initialize the citation service.

        Args:
            api_key: Optional Semantic Scholar API key for higher rate limits.
            timeout: Request timeout in seconds.
        """
        self.client = SemanticScholarClient(api_key=api_key, timeout=timeout)

    async def get_paper_info(self, arxiv_id: str) -> Optional[PaperInfo]:
        """
        Get paper metadata from Semantic Scholar.

        Args:
            arxiv_id: The arXiv paper ID (e.g., '2103.12345').

        Returns:
            PaperInfo with metadata, or None if not found.
        """
        return await self.client.get_paper(arxiv_id)

    async def get_citations(
        self,
        arxiv_id: str,
        limit: int = 50,
        include_contexts: bool = True,
    ) -> list[CitationRelationship]:
        """
        Get papers that cite the given paper.

        Args:
            arxiv_id: The arXiv paper ID.
            limit: Maximum citations to return (default 50, max 100).
            include_contexts: Whether to include citation context snippets.
                            Context is always fetched but can be filtered.

        Returns:
            List of CitationRelationship objects, each containing:
            - citing_paper: The paper that cites this one
            - cited_paper: This paper (the one being cited)
            - contexts: Text snippets showing how it's cited
            - is_influential: Whether it's an influential citation
        """
        limit = min(limit, 100)
        citations = await self.client.get_citations(arxiv_id, limit=limit)

        if not include_contexts:
            # Strip contexts if not requested (saves memory/bandwidth)
            for cit in citations:
                cit.contexts.clear()

        return citations

    async def get_references(
        self,
        arxiv_id: str,
        limit: int = 50,
        include_contexts: bool = True,
    ) -> list[CitationRelationship]:
        """
        Get papers referenced by the given paper.

        Args:
            arxiv_id: The arXiv paper ID.
            limit: Maximum references to return (default 50, max 100).
            include_contexts: Whether to include citation context snippets.

        Returns:
            List of CitationRelationship objects, each containing:
            - citing_paper: This paper (the one doing the citing)
            - cited_paper: The referenced paper
            - contexts: Text snippets showing how it's referenced
            - is_influential: Whether it's an influential reference
        """
        limit = min(limit, 100)
        references = await self.client.get_references(arxiv_id, limit=limit)

        if not include_contexts:
            for ref in references:
                ref.contexts.clear()

        return references

    async def build_citation_graph(
        self,
        arxiv_id: str,
        depth: int = 2,
        direction: str = "both",
        max_papers_per_level: int = 25,
    ) -> CitationGraph:
        """
        Build a citation graph around a paper.

        Traverses citation relationships N levels deep to create
        a network of related papers.

        Args:
            arxiv_id: The center paper's arXiv ID.
            depth: How many levels to traverse (1-3 recommended).
                  Higher depths exponentially increase API calls.
            direction: Which relationships to follow:
                      - 'citations': Papers that cite the root
                      - 'references': Papers the root cites
                      - 'both': Both directions
            max_papers_per_level: Max papers to fetch at each level.
                                 Limits graph size and API usage.

        Returns:
            CitationGraph containing:
            - root_paper_id: The starting paper
            - papers: Dict of paper_id -> PaperInfo
            - edges: List of (citing_id, cited_id) tuples
            - depth: Actual depth traversed
            - direction: The direction used
        """
        builder = GraphBuilder(
            client=self.client,
            max_papers_per_level=max_papers_per_level,
        )
        return await builder.build(
            root_paper_id=arxiv_id,
            depth=depth,
            direction=direction,
        )

    async def get_citation_summary(
        self,
        arxiv_id: str,
    ) -> dict:
        """
        Get a quick summary of citation metrics for a paper.

        Useful for getting an overview without fetching all citations.

        Args:
            arxiv_id: The arXiv paper ID.

        Returns:
            Dict with citation metrics and basic info.
        """
        paper = await self.get_paper_info(arxiv_id)
        if paper is None:
            return {"error": f"Paper not found: {arxiv_id}"}

        return {
            "paper_id": paper.paper_id,
            "title": paper.title,
            "year": paper.year,
            "citation_count": paper.citation_count,
            "reference_count": paper.reference_count,
            "influential_citation_count": paper.influential_citation_count,
            "arxiv_id": paper.arxiv_id,
            "doi": paper.doi,
        }

    async def search_semantic_scholar(
        self,
        query: str,
        limit: int = 20,
        year_range: Optional[tuple[int, int]] = None,
        min_citations: Optional[int] = None,
    ) -> SearchResult:
        """
        Search for papers using Semantic Scholar's semantic search.

        Complements arXiv search with relevance-based results.

        Args:
            query: Natural language search query
            limit: Maximum results
            year_range: Optional (start, end) year filter
            min_citations: Optional minimum citation count

        Returns:
            SearchResult with matching papers
        """
        papers, total, next_offset = await self.client.search_papers(
            query=query,
            limit=limit,
            year_range=year_range,
            min_citation_count=min_citations,
        )

        return SearchResult(
            query=query,
            total_results=total,
            papers=papers,
            next_offset=next_offset,
        )

    async def find_similar_papers(
        self,
        paper_id: str,
        method: str = "citation_overlap",
        top_k: int = 10,
        graph_depth: int = 2,
    ) -> list[PaperSimilarity]:
        """
        Find papers similar to the given paper using citation analysis.

        First builds a citation graph, then computes similarity based on
        citation patterns (no external ML required).

        Args:
            paper_id: The arXiv ID to find similar papers for
            method: Similarity method ('co_citation', 'bibliographic_coupling', 'citation_overlap')
            top_k: Number of similar papers to return
            graph_depth: How deep to build the citation graph

        Returns:
            List of PaperSimilarity objects, sorted by score
        """
        # Build citation graph first
        graph = await self.build_citation_graph(
            paper_id,
            depth=graph_depth,
            direction="both",
        )

        # Map method string to enum
        method_map = {
            "co_citation": SimilarityMethod.CO_CITATION,
            "bibliographic_coupling": SimilarityMethod.BIBLIOGRAPHIC_COUPLING,
            "citation_overlap": SimilarityMethod.CITATION_OVERLAP,
        }
        similarity_method = method_map.get(method, SimilarityMethod.CITATION_OVERLAP)

        # Compute similarities
        analyzer = SimilarityAnalyzer(graph)
        return analyzer.compute_similarity(paper_id, method=similarity_method, top_k=top_k)

    async def cluster_papers(
        self,
        paper_ids: Optional[list[str]] = None,
        root_paper_id: Optional[str] = None,
        min_cluster_size: int = 3,
        graph_depth: int = 2,
    ) -> ClusteringResult:
        """
        Cluster papers by topic/methodology using citation patterns.

        Either provide a list of paper_ids OR a root_paper_id to build a graph from.

        Args:
            paper_ids: List of paper IDs to cluster (optional)
            root_paper_id: Build graph from this paper and cluster (optional)
            min_cluster_size: Minimum papers per cluster
            graph_depth: Graph depth if building from root

        Returns:
            ClusteringResult with identified clusters
        """
        if root_paper_id:
            graph = await self.build_citation_graph(
                root_paper_id,
                depth=graph_depth,
                direction="both",
            )
        elif paper_ids:
            # Fetch papers and build a simple graph from their citations
            graph = await self._build_graph_from_papers(paper_ids)
        else:
            raise ValueError("Either paper_ids or root_paper_id must be provided")

        analyzer = ClusterAnalyzer(graph)
        return analyzer.cluster_papers(min_cluster_size=min_cluster_size)

    async def summarize_research_area(
        self,
        paper_id: str,
        depth: int = 2,
    ) -> ResearchAreaSummary:
        """
        Generate a comprehensive summary of a research area.

        Builds citation graph, clusters papers, and synthesizes insights.

        Args:
            paper_id: Central paper for the research area
            depth: How many citation levels to explore

        Returns:
            ResearchAreaSummary with synthesized overview
        """
        # Build graph
        graph = await self.build_citation_graph(
            paper_id,
            depth=depth,
            direction="both",
        )

        # Cluster papers
        cluster_analyzer = ClusterAnalyzer(graph)
        clusters = cluster_analyzer.cluster_papers()

        # Generate summary
        generator = SummaryGenerator(graph, clusters)
        return generator.generate_summary()

    async def find_research_gaps(
        self,
        paper_id: str,
        depth: int = 2,
    ) -> GapAnalysisResult:
        """
        Identify under-explored research areas in a citation network.

        Analyzes the citation graph to find:
        - Bridging gaps (disconnected clusters)
        - Temporal gaps (declining areas)
        - Methodological gaps (unused method-domain combinations)

        Args:
            paper_id: Central paper to analyze around
            depth: Citation graph depth

        Returns:
            GapAnalysisResult with identified research gaps
        """
        # Build graph
        graph = await self.build_citation_graph(
            paper_id,
            depth=depth,
            direction="both",
        )

        # Cluster papers
        cluster_analyzer = ClusterAnalyzer(graph)
        clusters = cluster_analyzer.cluster_papers()

        # Find gaps
        gap_analyzer = GapAnalyzer(graph, clusters)
        return gap_analyzer.find_gaps()

    async def compare_papers(
        self,
        paper_ids: list[str],
        include_references: bool = True,
    ) -> PaperComparison:
        """
        Generate side-by-side comparison of multiple papers.

        Args:
            paper_ids: Papers to compare (2-5 recommended)
            include_references: Whether to analyze shared/unique references

        Returns:
            PaperComparison with detailed comparison
        """
        if len(paper_ids) < 2:
            raise ValueError("At least 2 papers required for comparison")

        # Build a graph containing all papers and their relationships
        graph = await self._build_graph_from_papers(paper_ids)

        analyzer = ComparisonAnalyzer(graph)
        return analyzer.compare_papers(paper_ids)

    async def _build_graph_from_papers(self, paper_ids: list[str]) -> CitationGraph:
        """Build a citation graph from a list of papers."""
        papers = {}
        edges = []

        # Fetch each paper's info and references
        for pid in paper_ids:
            paper = await self.client.get_paper(pid)
            if paper:
                papers[pid] = paper

                # Get references
                refs = await self.client.get_references(pid, limit=50)
                for ref in refs:
                    if ref.cited_paper.paper_id not in papers:
                        papers[ref.cited_paper.paper_id] = ref.cited_paper
                    edges.append((pid, ref.cited_paper.paper_id))

                # Get citations
                cits = await self.client.get_citations(pid, limit=50)
                for cit in cits:
                    if cit.citing_paper.paper_id not in papers:
                        papers[cit.citing_paper.paper_id] = cit.citing_paper
                    edges.append((cit.citing_paper.paper_id, pid))

        return CitationGraph(
            root_paper_id=paper_ids[0],
            papers=papers,
            edges=edges,
            depth=1,
            direction="both",
        )

    async def close(self) -> None:
        """Clean up resources."""
        await self.client.close()
