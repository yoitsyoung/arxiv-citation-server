"""
Research analysis algorithms.

Provides local computation for:
- Paper similarity (citation-based)
- Paper clustering (modularity-based)
- Research gap identification (pattern-based)
- Research area summarization

All algorithms work on citation graph data without external ML services.
"""

from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Optional

from .models import (
    CitationGraph,
    ClusteringResult,
    GapAnalysisResult,
    PaperCluster,
    PaperComparison,
    PaperInfo,
    PaperSimilarity,
    ResearchAreaSummary,
    ResearchGap,
    SimilarityMethod,
)

logger = logging.getLogger("arxiv-citation-server")


class SimilarityAnalyzer:
    """
    Compute paper similarity using citation patterns.

    Methods:
    - Co-citation: Papers frequently cited together are similar
    - Bibliographic coupling: Papers citing same references are similar
    - Citation overlap: Combined approach
    """

    def __init__(self, graph: CitationGraph):
        self.graph = graph
        self._build_indexes()

    def _build_indexes(self):
        """Pre-compute citation relationships for fast lookup."""
        # paper_id -> set of papers it cites
        self.cites: dict[str, set[str]] = defaultdict(set)
        # paper_id -> set of papers that cite it
        self.cited_by: dict[str, set[str]] = defaultdict(set)

        for citing_id, cited_id in self.graph.edges:
            self.cites[citing_id].add(cited_id)
            self.cited_by[cited_id].add(citing_id)

    def compute_similarity(
        self,
        paper_id: str,
        method: SimilarityMethod = SimilarityMethod.CITATION_OVERLAP,
        top_k: int = 10,
    ) -> list[PaperSimilarity]:
        """
        Find papers most similar to the given paper.

        Args:
            paper_id: The paper to find similar papers for
            method: Similarity computation method
            top_k: Number of similar papers to return

        Returns:
            List of PaperSimilarity objects, sorted by score descending
        """
        if paper_id not in self.graph.papers:
            return []

        source_paper = self.graph.papers[paper_id]
        scores: dict[str, float] = {}
        shared_data: dict[str, tuple[list[str], list[str]]] = {}

        for other_id in self.graph.papers:
            if other_id == paper_id:
                continue

            score, shared_refs, shared_citers = self._compute_pair_similarity(
                paper_id, other_id, method
            )

            if score > 0:
                scores[other_id] = score
                shared_data[other_id] = (shared_refs, shared_citers)

        # Sort by score and take top_k
        top_papers = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for other_id, score in top_papers:
            other_paper = self.graph.papers[other_id]
            shared_refs, shared_citers = shared_data[other_id]

            results.append(
                PaperSimilarity(
                    paper_a=source_paper,
                    paper_b=other_paper,
                    similarity_score=score,
                    method=method,
                    shared_citations=shared_refs,
                    shared_citers=shared_citers,
                    explanation=self._explain_similarity(
                        score, shared_refs, shared_citers, method
                    ),
                )
            )

        return results

    def _compute_pair_similarity(
        self,
        paper_a: str,
        paper_b: str,
        method: SimilarityMethod,
    ) -> tuple[float, list[str], list[str]]:
        """Compute similarity between two papers."""
        refs_a = self.cites.get(paper_a, set())
        refs_b = self.cites.get(paper_b, set())
        citers_a = self.cited_by.get(paper_a, set())
        citers_b = self.cited_by.get(paper_b, set())

        shared_refs = list(refs_a & refs_b)
        shared_citers = list(citers_a & citers_b)

        if method == SimilarityMethod.BIBLIOGRAPHIC_COUPLING:
            # Jaccard similarity on references
            union = refs_a | refs_b
            if not union:
                return 0.0, shared_refs, shared_citers
            score = len(shared_refs) / len(union)

        elif method == SimilarityMethod.CO_CITATION:
            # Jaccard similarity on citers
            union = citers_a | citers_b
            if not union:
                return 0.0, shared_refs, shared_citers
            score = len(shared_citers) / len(union)

        else:  # CITATION_OVERLAP
            # Weighted combination
            ref_union = refs_a | refs_b
            citer_union = citers_a | citers_b

            ref_score = len(shared_refs) / len(ref_union) if ref_union else 0
            citer_score = len(shared_citers) / len(citer_union) if citer_union else 0

            # Weight citers higher (co-citation is stronger signal)
            score = 0.4 * ref_score + 0.6 * citer_score

        return score, shared_refs, shared_citers

    def _explain_similarity(
        self,
        score: float,
        shared_refs: list[str],
        shared_citers: list[str],
        method: SimilarityMethod,
    ) -> str:
        """Generate human-readable explanation."""
        parts = []
        if shared_refs:
            parts.append(f"Both papers cite {len(shared_refs)} common references")
        if shared_citers:
            parts.append(f"{len(shared_citers)} papers cite both")

        strength = "strong" if score > 0.5 else "moderate" if score > 0.2 else "weak"
        base = f"{strength.title()} similarity ({method.value})"
        if parts:
            return base + ": " + "; ".join(parts)
        return base


class ClusterAnalyzer:
    """
    Cluster papers based on citation patterns.

    Uses a simple modularity-based approach:
    1. Build adjacency matrix from citation graph
    2. Use iterative label propagation for community detection
    3. No external ML dependencies required
    """

    def __init__(self, graph: CitationGraph):
        self.graph = graph
        self._build_adjacency()

    def _build_adjacency(self):
        """Build undirected adjacency for clustering."""
        self.neighbors: dict[str, set[str]] = defaultdict(set)

        for citing_id, cited_id in self.graph.edges:
            # Treat as undirected for clustering
            self.neighbors[citing_id].add(cited_id)
            self.neighbors[cited_id].add(citing_id)

    def cluster_papers(
        self,
        min_cluster_size: int = 3,
        max_iterations: int = 50,
    ) -> ClusteringResult:
        """
        Cluster papers using label propagation.

        Args:
            min_cluster_size: Minimum papers per cluster
            max_iterations: Max label propagation iterations

        Returns:
            ClusteringResult with identified clusters
        """
        paper_ids = list(self.graph.papers.keys())

        if len(paper_ids) < min_cluster_size:
            # Too few papers to cluster
            return ClusteringResult(
                clusters=[],
                unclustered_papers=list(self.graph.papers.values()),
                total_papers=len(paper_ids),
                method="label_propagation",
            )

        # Initialize: each paper in its own cluster
        labels = {pid: i for i, pid in enumerate(paper_ids)}

        # Label propagation
        for iteration in range(max_iterations):
            changed = False

            for pid in paper_ids:
                neighbors = self.neighbors.get(pid, set())
                if not neighbors:
                    continue

                # Count neighbor labels
                label_counts = Counter(labels[n] for n in neighbors if n in labels)
                if not label_counts:
                    continue

                # Take most common label
                new_label = label_counts.most_common(1)[0][0]
                if labels[pid] != new_label:
                    labels[pid] = new_label
                    changed = True

            if not changed:
                break

        # Group by labels
        label_to_papers: dict[int, list[str]] = defaultdict(list)
        for pid, label in labels.items():
            label_to_papers[label].append(pid)

        # Build clusters
        clusters = []
        unclustered = []

        for label, paper_ids_in_cluster in label_to_papers.items():
            if len(paper_ids_in_cluster) < min_cluster_size:
                unclustered.extend(
                    self.graph.papers[pid] for pid in paper_ids_in_cluster
                )
                continue

            papers = [self.graph.papers[pid] for pid in paper_ids_in_cluster]

            # Find central paper (most connections within cluster)
            cluster_set = set(paper_ids_in_cluster)
            internal_degrees = {
                pid: len(self.neighbors.get(pid, set()) & cluster_set)
                for pid in paper_ids_in_cluster
            }
            central_id = max(internal_degrees, key=internal_degrees.get)

            # Compute cohesion (internal edges / possible internal edges)
            internal_edges = sum(internal_degrees.values()) / 2
            max_edges = len(paper_ids_in_cluster) * (len(paper_ids_in_cluster) - 1) / 2
            cohesion = internal_edges / max_edges if max_edges > 0 else 0

            # Extract key terms from titles
            key_terms = self._extract_key_terms(papers)

            # Get year range
            years = [p.year for p in papers if p.year]
            year_range = (min(years), max(years)) if years else (None, None)

            clusters.append(
                PaperCluster(
                    cluster_id=f"cluster_{len(clusters)}",
                    label=self._infer_cluster_label(papers, key_terms),
                    papers=papers,
                    central_paper_id=central_id,
                    cohesion_score=min(cohesion, 1.0),
                    key_terms=key_terms[:10],
                    year_range=year_range,
                )
            )

        return ClusteringResult(
            clusters=sorted(clusters, key=lambda c: len(c.papers), reverse=True),
            unclustered_papers=unclustered,
            total_papers=len(self.graph.papers),
            method="label_propagation",
        )

    def _extract_key_terms(self, papers: list[PaperInfo], top_k: int = 10) -> list[str]:
        """Extract common terms from paper titles."""
        # Simple stop words
        stop_words = {
            "a",
            "an",
            "the",
            "of",
            "in",
            "for",
            "on",
            "with",
            "to",
            "and",
            "is",
            "are",
            "by",
            "from",
            "using",
            "via",
            "based",
            "towards",
            "its",
            "as",
            "at",
            "be",
            "or",
            "this",
            "that",
        }

        word_counts = Counter()
        for paper in papers:
            words = re.findall(r"\b[a-zA-Z]{3,}\b", paper.title.lower())
            word_counts.update(w for w in words if w not in stop_words)

        return [word for word, _ in word_counts.most_common(top_k)]

    def _infer_cluster_label(
        self, papers: list[PaperInfo], key_terms: list[str]
    ) -> str:
        """Generate a label for the cluster."""
        if not key_terms:
            return "Unlabeled Cluster"

        # Use top 2-3 terms
        return " / ".join(key_terms[:3]).title()


class GapAnalyzer:
    """
    Identify research gaps from citation patterns.

    Gap types:
    - Unexplored: Areas with few papers but high surrounding activity
    - Bridging: Missing connections between clusters
    - Temporal: Topics that stopped being researched
    - Methodological: Methods not applied to certain domains
    """

    def __init__(self, graph: CitationGraph, clusters: ClusteringResult):
        self.graph = graph
        self.clusters = clusters
        self._build_indexes()

    def _build_indexes(self):
        """Build indexes for gap analysis."""
        # paper -> cluster mapping
        self.paper_to_cluster: dict[str, str] = {}
        for cluster in self.clusters.clusters:
            for paper in cluster.papers:
                self.paper_to_cluster[paper.paper_id] = cluster.cluster_id

        # Cross-cluster citation counts
        self.cross_cluster_citations: dict[tuple[str, str], int] = defaultdict(int)
        for citing_id, cited_id in self.graph.edges:
            cluster_a = self.paper_to_cluster.get(citing_id)
            cluster_b = self.paper_to_cluster.get(cited_id)
            if cluster_a and cluster_b and cluster_a != cluster_b:
                key = tuple(sorted([cluster_a, cluster_b]))
                self.cross_cluster_citations[key] += 1

    def find_gaps(self) -> GapAnalysisResult:
        """Identify research gaps."""
        gaps = []

        # 1. Find bridging gaps (disconnected clusters)
        gaps.extend(self._find_bridging_gaps())

        # 2. Find temporal gaps (declining research areas)
        gaps.extend(self._find_temporal_gaps())

        # 3. Find methodological gaps (methods not applied across areas)
        gaps.extend(self._find_methodological_gaps())

        return GapAnalysisResult(
            gaps=gaps,
            analyzed_paper_count=len(self.graph.papers),
            analysis_depth=self.graph.depth,
        )

    def _find_bridging_gaps(self) -> list[ResearchGap]:
        """Find clusters with weak connections that could be bridged."""
        gaps = []

        clusters = self.clusters.clusters
        for i, cluster_a in enumerate(clusters):
            for cluster_b in clusters[i + 1 :]:
                key = tuple(sorted([cluster_a.cluster_id, cluster_b.cluster_id]))
                cross_citations = self.cross_cluster_citations.get(key, 0)

                # Low cross-citation between substantial clusters = potential gap
                if len(cluster_a.papers) >= 3 and len(cluster_b.papers) >= 3:
                    max_possible = len(cluster_a.papers) * len(cluster_b.papers)
                    connection_ratio = (
                        cross_citations / max_possible if max_possible > 0 else 0
                    )

                    if connection_ratio < 0.05:  # Less than 5% connected
                        gaps.append(
                            ResearchGap(
                                gap_id=f"bridge_{cluster_a.cluster_id}_{cluster_b.cluster_id}",
                                description=f"Limited research connecting '{cluster_a.label}' and '{cluster_b.label}'",
                                gap_type="bridging",
                                evidence_papers=[
                                    cluster_a.central_paper_id,
                                    cluster_b.central_paper_id,
                                ],
                                related_clusters=[
                                    cluster_a.cluster_id,
                                    cluster_b.cluster_id,
                                ],
                                confidence=min(0.9, 1 - connection_ratio * 10),
                                potential_topics=[
                                    f"Applying {cluster_a.key_terms[0] if cluster_a.key_terms else 'methods'} to {cluster_b.key_terms[0] if cluster_b.key_terms else 'domain'}",
                                ],
                            )
                        )

        return gaps

    def _find_temporal_gaps(self) -> list[ResearchGap]:
        """Find research areas that have declined in activity."""
        gaps = []

        for cluster in self.clusters.clusters:
            if not cluster.year_range[1]:
                continue

            # Get papers by year
            papers_by_year = defaultdict(list)
            for paper in cluster.papers:
                if paper.year:
                    papers_by_year[paper.year].append(paper)

            if len(papers_by_year) < 3:
                continue

            years = sorted(papers_by_year.keys())

            # Check if recent years have declining activity
            if len(years) >= 2:
                recent_years = years[-2:]
                early_years = years[:2]

                recent_count = sum(len(papers_by_year[y]) for y in recent_years)
                early_count = sum(len(papers_by_year[y]) for y in early_years)

                if early_count > 0 and recent_count / early_count < 0.5:
                    gaps.append(
                        ResearchGap(
                            gap_id=f"temporal_{cluster.cluster_id}",
                            description=f"Declining research activity in '{cluster.label}' (peaked around {max(early_years)})",
                            gap_type="temporal",
                            evidence_papers=[p.paper_id for p in cluster.papers[:3]],
                            related_clusters=[cluster.cluster_id],
                            confidence=0.6,
                            potential_topics=[
                                f"Revisiting {term} with modern techniques"
                                for term in cluster.key_terms[:2]
                            ],
                        )
                    )

        return gaps

    def _find_methodological_gaps(self) -> list[ResearchGap]:
        """Find methods that haven't been applied across all relevant areas."""
        gaps = []

        # Identify "method" clusters (often have terms like "algorithm", "model")
        method_indicators = {
            "algorithm",
            "model",
            "method",
            "approach",
            "network",
            "learning",
        }

        method_clusters = []
        domain_clusters = []

        for cluster in self.clusters.clusters:
            terms_lower = set(t.lower() for t in cluster.key_terms)
            if terms_lower & method_indicators:
                method_clusters.append(cluster)
            else:
                domain_clusters.append(cluster)

        # Check for method clusters with low connection to domain clusters
        for method_cluster in method_clusters:
            for domain_cluster in domain_clusters:
                key = tuple(
                    sorted([method_cluster.cluster_id, domain_cluster.cluster_id])
                )
                cross_citations = self.cross_cluster_citations.get(key, 0)

                if cross_citations < 2:
                    gaps.append(
                        ResearchGap(
                            gap_id=f"method_{method_cluster.cluster_id}_{domain_cluster.cluster_id}",
                            description=f"'{method_cluster.label}' techniques rarely applied to '{domain_cluster.label}'",
                            gap_type="methodological",
                            evidence_papers=[
                                method_cluster.central_paper_id,
                                domain_cluster.central_paper_id,
                            ],
                            related_clusters=[
                                method_cluster.cluster_id,
                                domain_cluster.cluster_id,
                            ],
                            confidence=0.5,
                            potential_topics=[
                                f"Applying {method_cluster.key_terms[0] if method_cluster.key_terms else 'method'} to {domain_cluster.key_terms[0] if domain_cluster.key_terms else 'domain'}"
                            ],
                        )
                    )

        return gaps[:10]  # Limit to top 10 methodological gaps


class SummaryGenerator:
    """Generate research area summaries from citation graphs."""

    def __init__(
        self,
        graph: CitationGraph,
        clusters: ClusteringResult,
    ):
        self.graph = graph
        self.clusters = clusters

    def generate_summary(self) -> ResearchAreaSummary:
        """Generate a comprehensive research area summary."""
        root_paper = self.graph.papers.get(self.graph.root_paper_id)

        # Get all years
        years = [p.year for p in self.graph.papers.values() if p.year]
        year_range = (min(years), max(years)) if years else (None, None)

        # Find foundational papers (most cited within graph)
        citation_counts = defaultdict(int)
        for citing_id, cited_id in self.graph.edges:
            citation_counts[cited_id] += 1

        top_cited = sorted(citation_counts.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]

        foundational = [
            self.graph.papers[pid] for pid, _ in top_cited if pid in self.graph.papers
        ]

        # Find recent influential (high citations relative to age)
        current_year = datetime.now().year
        recent_papers = [
            p
            for p in self.graph.papers.values()
            if p.year and p.year >= current_year - 3
        ]

        recent_influential = sorted(
            recent_papers,
            key=lambda p: (p.citation_count or 0)
            / max(1, current_year - (p.year or current_year) + 1),
            reverse=True,
        )[:5]

        # Find bridging papers (cite multiple clusters)
        bridging = self._find_bridging_papers()

        # Extract major themes from clusters
        major_themes = []
        for cluster in self.clusters.clusters[:5]:
            if cluster.label:
                major_themes.append(cluster.label)

        # Build timeline
        timeline = self._build_timeline()

        return ResearchAreaSummary(
            root_paper_id=self.graph.root_paper_id,
            area_name=root_paper.title[:50] + "..." if root_paper else "",
            total_papers=len(self.graph.papers),
            year_range=year_range,
            foundational_papers=foundational[:5],
            recent_influential=recent_influential,
            bridging_papers=bridging[:5],
            major_themes=major_themes,
            methodology_trends=self._extract_methodology_trends(),
            timeline=timeline,
            sub_areas=self.clusters.clusters[:5],
        )

    def _find_bridging_papers(self) -> list[PaperInfo]:
        """Find papers that cite papers in multiple clusters."""
        # paper_id -> set of clusters it connects to
        cluster_connections: dict[str, set[str]] = defaultdict(set)

        paper_to_cluster = {}
        for cluster in self.clusters.clusters:
            for paper in cluster.papers:
                paper_to_cluster[paper.paper_id] = cluster.cluster_id

        for citing_id, cited_id in self.graph.edges:
            if cited_id in paper_to_cluster:
                cluster_connections[citing_id].add(paper_to_cluster[cited_id])

        # Papers connecting 2+ clusters
        bridging_ids = [
            pid
            for pid, clusters in cluster_connections.items()
            if len(clusters) >= 2 and pid in self.graph.papers
        ]

        # Sort by number of clusters connected
        bridging_ids.sort(key=lambda x: len(cluster_connections[x]), reverse=True)

        return [self.graph.papers[pid] for pid in bridging_ids[:5]]

    def _build_timeline(self) -> list[dict]:
        """Build a timeline of key developments."""
        papers_by_year: dict[int, list[PaperInfo]] = defaultdict(list)

        for paper in self.graph.papers.values():
            if paper.year:
                papers_by_year[paper.year].append(paper)

        timeline = []
        for year in sorted(papers_by_year.keys()):
            papers = papers_by_year[year]
            # Pick most cited paper that year
            top_paper = max(papers, key=lambda p: p.citation_count or 0)

            timeline.append(
                {
                    "year": year,
                    "paper_count": len(papers),
                    "key_paper": top_paper.title[:60],
                    "key_paper_id": top_paper.paper_id,
                }
            )

        return timeline

    def _extract_methodology_trends(self) -> list[str]:
        """Extract methodology trends from paper titles/abstracts."""
        method_terms = Counter()
        method_keywords = {
            "neural",
            "deep learning",
            "transformer",
            "attention",
            "cnn",
            "rnn",
            "bert",
            "gpt",
            "llm",
            "reinforcement",
            "supervised",
            "unsupervised",
            "graph neural",
            "diffusion",
            "generative",
            "contrastive",
        }

        for paper in self.graph.papers.values():
            text = (paper.title + " " + (paper.abstract or "")).lower()
            for keyword in method_keywords:
                if keyword in text:
                    method_terms[keyword] += 1

        return [term for term, _ in method_terms.most_common(5)]


class ComparisonAnalyzer:
    """Compare multiple papers side-by-side."""

    def __init__(self, graph: CitationGraph):
        self.graph = graph
        self._build_indexes()

    def _build_indexes(self):
        """Build citation indexes."""
        self.cites: dict[str, set[str]] = defaultdict(set)
        self.cited_by: dict[str, set[str]] = defaultdict(set)

        for citing_id, cited_id in self.graph.edges:
            self.cites[citing_id].add(cited_id)
            self.cited_by[cited_id].add(citing_id)

    def compare_papers(self, paper_ids: list[str]) -> PaperComparison:
        """
        Generate side-by-side comparison of papers.

        Args:
            paper_ids: List of paper IDs to compare

        Returns:
            PaperComparison object
        """
        papers = [
            self.graph.papers[pid] for pid in paper_ids if pid in self.graph.papers
        ]

        if len(papers) < 2:
            return PaperComparison(papers=papers)

        # Citation counts
        citation_counts = {p.paper_id: p.citation_count or 0 for p in papers}

        # Find shared references
        reference_sets = [self.cites.get(p.paper_id, set()) for p in papers]
        if reference_sets:
            shared_ref_ids = set.intersection(*reference_sets)
            shared_references = [
                self.graph.papers[rid]
                for rid in shared_ref_ids
                if rid in self.graph.papers
            ]
        else:
            shared_references = []

        # Find unique references per paper
        unique_references = {}
        all_refs = set.union(*reference_sets) if reference_sets else set()
        for paper in papers:
            paper_refs = self.cites.get(paper.paper_id, set())
            unique = paper_refs - (all_refs - paper_refs)
            unique_references[paper.paper_id] = [
                self.graph.papers[rid] for rid in unique if rid in self.graph.papers
            ][:5]  # Limit to 5

        # Find shared citers
        citer_sets = [self.cited_by.get(p.paper_id, set()) for p in papers]
        if citer_sets:
            shared_citer_ids = set.intersection(*citer_sets)
            shared_citers = [
                self.graph.papers[cid]
                for cid in shared_citer_ids
                if cid in self.graph.papers
            ]
        else:
            shared_citers = []

        # Citation overlap score
        if citer_sets:
            all_citers = set.union(*citer_sets)
            overlap_score = len(shared_citer_ids) / len(all_citers) if all_citers else 0
        else:
            overlap_score = 0

        # Extract common themes from titles
        common_themes = self._extract_common_themes(papers)

        return PaperComparison(
            papers=papers,
            publication_timeline=[
                {"paper_id": p.paper_id, "year": p.year, "title": p.title[:50]}
                for p in sorted(papers, key=lambda x: x.year or 0)
            ],
            venue_comparison={p.paper_id: p.venue or "Unknown" for p in papers},
            citation_counts=citation_counts,
            shared_references=shared_references[:10],
            unique_references=unique_references,
            shared_citers=shared_citers[:10],
            citation_overlap_score=overlap_score,
            common_themes=common_themes,
            distinguishing_aspects=self._find_distinguishing_aspects(papers),
        )

    def _extract_common_themes(self, papers: list[PaperInfo]) -> list[str]:
        """Find terms common to all papers."""
        stop_words = {
            "a",
            "an",
            "the",
            "of",
            "in",
            "for",
            "on",
            "with",
            "to",
            "and",
            "is",
            "are",
        }

        word_sets = []
        for paper in papers:
            words = set(
                w.lower()
                for w in re.findall(r"\b[a-zA-Z]{3,}\b", paper.title)
                if w.lower() not in stop_words
            )
            word_sets.append(words)

        if not word_sets:
            return []

        common = set.intersection(*word_sets)
        return list(common)[:5]

    def _find_distinguishing_aspects(
        self, papers: list[PaperInfo]
    ) -> dict[str, list[str]]:
        """Find unique terms for each paper."""
        stop_words = {
            "a",
            "an",
            "the",
            "of",
            "in",
            "for",
            "on",
            "with",
            "to",
            "and",
            "is",
            "are",
        }

        all_words = Counter()
        paper_words = {}

        for paper in papers:
            words = [
                w.lower()
                for w in re.findall(r"\b[a-zA-Z]{3,}\b", paper.title)
                if w.lower() not in stop_words
            ]
            paper_words[paper.paper_id] = set(words)
            all_words.update(words)

        # Find words unique to each paper (appear only in that paper)
        result = {}
        for paper in papers:
            unique = [
                word for word in paper_words[paper.paper_id] if all_words[word] == 1
            ]
            result[paper.paper_id] = unique[:3]

        return result
