"""
Citation graph building logic.

Handles traversing citation relationships to build
multi-level citation networks.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from .client import SemanticScholarClient
from .models import CitationGraph, CitationRelationship, PaperInfo

logger = logging.getLogger("arxiv-citation-server")


class GraphBuilder:
    """
    Builds citation graphs by traversing relationships.

    Supports building graphs in different directions:
    - 'citations': Papers that cite the root paper
    - 'references': Papers the root paper cites
    - 'both': Both directions
    """

    def __init__(
        self,
        client: SemanticScholarClient,
        max_papers_per_level: int = 25,
    ):
        """
        Initialize the graph builder.

        Args:
            client: Semantic Scholar client for API calls.
            max_papers_per_level: Maximum papers to fetch at each depth level.
        """
        self.client = client
        self.max_papers_per_level = max_papers_per_level

    async def build(
        self,
        root_paper_id: str,
        depth: int = 2,
        direction: str = "both",
    ) -> CitationGraph:
        """
        Build a citation graph starting from the root paper.

        Args:
            root_paper_id: The arXiv ID of the center paper.
            depth: How many levels to traverse (1-3 recommended).
            direction: 'citations', 'references', or 'both'.

        Returns:
            CitationGraph containing all discovered papers and relationships.
        """
        # Validate depth
        depth = min(max(depth, 1), 3)

        # Initialize graph structures
        papers: dict[str, PaperInfo] = {}
        edges: list[tuple[str, str]] = []
        visited: set[str] = set()

        # Get root paper info
        root_paper = await self.client.get_paper(root_paper_id)
        if root_paper is None:
            root_paper = PaperInfo(paper_id=root_paper_id, title="Unknown")
        papers[root_paper_id] = root_paper

        # BFS traversal by level
        current_level = {root_paper_id}

        for current_depth in range(depth):
            next_level: set[str] = set()
            logger.info(
                f"Building graph level {current_depth + 1}/{depth}, "
                f"processing {len(current_level)} papers"
            )

            # Process papers at current level in parallel
            tasks = []
            for paper_id in current_level:
                if paper_id in visited:
                    continue
                visited.add(paper_id)

                if direction in ("citations", "both"):
                    tasks.append(self._fetch_citations(paper_id))
                if direction in ("references", "both"):
                    tasks.append(self._fetch_references(paper_id))

            # Gather results
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"Error fetching relationships: {result}")
                    continue

                relationships, rel_type = result
                for rel in relationships[: self.max_papers_per_level]:
                    if rel_type == "citation":
                        # citing_paper cites cited_paper
                        other_paper = rel.citing_paper
                        edge = (other_paper.paper_id, rel.cited_paper.paper_id)
                    else:  # reference
                        other_paper = rel.cited_paper
                        edge = (rel.citing_paper.paper_id, other_paper.paper_id)

                    # Add paper if not seen
                    if other_paper.paper_id not in papers:
                        papers[other_paper.paper_id] = other_paper
                        next_level.add(other_paper.paper_id)

                    # Add edge if not duplicate
                    if edge not in edges:
                        edges.append(edge)

            current_level = next_level

            if not current_level:
                logger.info(f"No more papers to explore at depth {current_depth + 1}")
                break

        logger.info(
            f"Graph complete: {len(papers)} papers, {len(edges)} edges, "
            f"depth {depth}, direction '{direction}'"
        )

        return CitationGraph(
            root_paper_id=root_paper_id,
            papers=papers,
            edges=edges,
            depth=depth,
            direction=direction,
        )

    async def _fetch_citations(
        self,
        paper_id: str,
    ) -> tuple[list[CitationRelationship], str]:
        """Fetch citations and return with type marker."""
        citations = await self.client.get_citations(
            paper_id, limit=self.max_papers_per_level
        )
        return (citations, "citation")

    async def _fetch_references(
        self,
        paper_id: str,
    ) -> tuple[list[CitationRelationship], str]:
        """Fetch references and return with type marker."""
        references = await self.client.get_references(
            paper_id, limit=self.max_papers_per_level
        )
        return (references, "reference")
