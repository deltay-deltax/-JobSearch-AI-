"""Stage 5: Hybrid Search with Reciprocal Rank Fusion (RRF).

Combines BM25 keyword retrieval and pgvector semantic retrieval
into a single unified ranked list using the RRF algorithm.

Why Hybrid Search?
──────────────────
BM25 alone:    Great at exact keyword matches, fails on vocabulary mismatch.
Vector alone:  Great at semantic understanding, fails on exact identifiers.
Hybrid (RRF):  Takes the best of both — robust, high-recall, high-precision.

RRF Formula:
    RRF_score(d) = Σ  1 / (k + rank_i(d))
                  i ∈ {bm25, vector}

    Where:
        d       = a document (job posting)
        k       = smoothing constant (default = 60), prevents top-rank documents
                  from completely dominating the final list
        rank_i  = position of document d in retrieval list i (1-indexed)

    If a document appears in only one list, it still gets a contribution from
    that list alone. Documents appearing in BOTH lists get double contributions
    and naturally float to the top.
"""

from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field

import numpy as np

from src.ingestion.schema import JobPosting
from src.search.bm25_search import BM25Index
from src.search.db import VectorDB
from src.search.vector_search import VectorSearchEngine
from src.config import RRF_K_CONSTANT, DEFAULT_TOP_K


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class HybridSearchResult:
    """A job posting ranked by its combined RRF score."""
    job: JobPosting
    rrf_score: float          # Final combined score (higher = more relevant)
    rank: int                 # Final rank in the merged list

    # Component scores for transparency and debugging
    bm25_rank: Optional[int] = None    # Rank in BM25 results (None if not retrieved)
    bm25_score: float = 0.0            # Raw BM25 score
    vector_rank: Optional[int] = None  # Rank in vector results (None if not retrieved)
    vector_score: float = 0.0          # Raw cosine similarity score

    @property
    def sources(self) -> List[str]:
        """Which retrievers contributed to this result."""
        s = []
        if self.bm25_rank is not None:
            s.append("BM25")
        if self.vector_rank is not None:
            s.append("Vector")
        return s


# ---------------------------------------------------------------------------
# Core Hybrid Search Engine
# ---------------------------------------------------------------------------

class HybridSearchEngine:
    """Combines BM25 and pgvector semantic search with Reciprocal Rank Fusion.

    Usage:
        engine = HybridSearchEngine()
        engine.fit(jobs)                           # builds BM25 index
        results = engine.search("Python backend")  # returns RRF-ranked results
    """

    def __init__(
        self,
        bm25_k1: float = 1.5,
        bm25_b: float = 0.75,
        rrf_k: int = RRF_K_CONSTANT,
        embedding_model: Optional[str] = None,
    ):
        self.rrf_k = rrf_k

        # BM25 index (in-memory, rebuilt from jobs at startup)
        self.bm25_index = BM25Index(k1=bm25_k1, b=bm25_b)

        # Vector encoder for query embedding
        self.vector_engine = VectorSearchEngine(
            model_name=embedding_model
        ) if embedding_model else VectorSearchEngine()

        self._fitted = False

    def fit(self, jobs: List[JobPosting]) -> "HybridSearchEngine":
        """Builds the BM25 inverted index from the job corpus.

        The pgvector side does NOT need fitting here — it queries the
        live PostgreSQL database directly at search time.

        Args:
            jobs: Full list of JobPosting objects (loaded from DB or disk).
        """
        self.bm25_index.fit(jobs)
        self._fitted = True
        return self

    # -----------------------------------------------------------------------
    # RRF Core
    # -----------------------------------------------------------------------

    def _rrf_score(self, rank: int) -> float:
        """Computes the RRF contribution for a single document at a given rank.

        RRF_contribution = 1 / (k + rank)

        With k=60:
            rank 1  → 1/61  ≈ 0.01639
            rank 2  → 1/62  ≈ 0.01613
            rank 10 → 1/70  ≈ 0.01429
            rank 50 → 1/110 ≈ 0.00909

        The k=60 constant ensures that:
        (a) The difference between rank 1 and rank 2 is small (~1.6%),
            so a solid second-place finish in one list still counts heavily.
        (b) Documents ranked near the bottom don't completely vanish.
        """
        return 1.0 / (self.rrf_k + rank)

    def _fuse(
        self,
        bm25_results: List,     # List[BM25SearchResult]
        vector_results: List,   # List[DBSearchResult]
        top_k: int,
        min_vector_similarity: float = 0.23,
    ) -> List[HybridSearchResult]:
        """Merges two ranked lists using Reciprocal Rank Fusion with Relevance Thresholding.

        Quality Guardrails:
        ───────────────────
        1. Both systems agree (BM25 + Vector): High confidence -> ALWAYS kept.
        2. Vector-only match (BM25 = 0): Must pass min_vector_similarity threshold (>= 0.23)
           to prevent KNN hallucination on out-of-domain words like 'maid' or 'banana'.
        3. BM25-only match (Vector = 0): Must have non-trivial score (>= 1.0) so single
           filler word matches don't dominate.
        """
        # accumulator: job_id → dict of score components
        acc: Dict[str, Dict] = {}

        # --- Walk BM25 results ---
        for res in bm25_results:
            jid = res.job.id
            if jid not in acc:
                acc[jid] = {
                    "job": res.job,
                    "rrf_score": 0.0,
                    "bm25_rank": None,
                    "bm25_score": 0.0,
                    "vector_rank": None,
                    "vector_score": 0.0,
                }
            acc[jid]["rrf_score"] += self._rrf_score(res.rank)
            acc[jid]["bm25_rank"] = res.rank
            acc[jid]["bm25_score"] = res.score

        # --- Walk Vector results ---
        for res in vector_results:
            jid = res.job.id
            if jid not in acc:
                acc[jid] = {
                    "job": res.job,
                    "rrf_score": 0.0,
                    "bm25_rank": None,
                    "bm25_score": 0.0,
                    "vector_rank": None,
                    "vector_score": 0.0,
                }
            acc[jid]["rrf_score"] += self._rrf_score(res.rank)
            acc[jid]["vector_rank"] = res.rank
            acc[jid]["vector_score"] = res.score

        # --- Quality Guardrail: Filter out weak single-source noise ---
        filtered_items = []
        for item in acc.values():
            in_bm25 = item["bm25_rank"] is not None
            in_vec = item["vector_rank"] is not None

            # Case A: Both systems agreed -> Keep!
            if in_bm25 and in_vec:
                filtered_items.append(item)
            # Case B: Only vector returned it -> ensure semantic score is actually meaningful
            elif in_vec and not in_bm25:
                if item["vector_score"] >= min_vector_similarity:
                    filtered_items.append(item)
            # Case C: Only BM25 returned it -> ensure keyword score is non-trivial
            elif in_bm25 and not in_vec:
                if item["bm25_score"] >= 1.0:
                    filtered_items.append(item)

        # --- Sort by total RRF score descending ---
        sorted_items = sorted(
            filtered_items,
            key=lambda x: x["rrf_score"],
            reverse=True,
        )

        # --- Build final result list ---
        results = []
        for final_rank, item in enumerate(sorted_items[:top_k], start=1):
            results.append(
                HybridSearchResult(
                    job=item["job"],
                    rrf_score=round(item["rrf_score"], 6),
                    rank=final_rank,
                    bm25_rank=item["bm25_rank"],
                    bm25_score=round(item["bm25_score"], 4),
                    vector_rank=item["vector_rank"],
                    vector_score=round(item["vector_score"], 4),
                )
            )

        return results

    # -----------------------------------------------------------------------
    # Public search interface
    # -----------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        bm25_candidate_k: int = 50,     # over-fetch before fusion
        vector_candidate_k: int = 50,   # over-fetch before fusion
        location_filter: Optional[str] = None,
        experience_filter: Optional[str] = None,
        employment_type_filter: Optional[str] = None,
    ) -> List[HybridSearchResult]:
        """Runs hybrid search: BM25 + pgvector → RRF → top_k results.

        Why over-fetch (candidate_k > top_k)?
            If we only retrieved top_k=10 from each system, a highly relevant
            document could be ranked #11 in BM25 and #9 in vector search, and
            would be missed in BOTH truncated lists despite being a great match.
            Fetching top 50 from each gives RRF the full picture to work with,
            then we return only the best top_k after fusion.

        Args:
            query:                Natural language search query.
            top_k:                Final number of results to return after fusion.
            bm25_candidate_k:     Number of candidates to retrieve from BM25.
            vector_candidate_k:   Number of candidates to retrieve from pgvector.
            location_filter:      Optional location substring filter (SQL LIKE).
            experience_filter:    Optional exact experience bucket filter.
            employment_type_filter: Optional employment type filter.

        Returns:
            List of HybridSearchResult sorted by RRF score (descending).
        """
        if not query.strip():
            return []

        # 1. BM25 Retrieval — keyword matching via inverted index
        bm25_results = self.bm25_index.search(query, top_k=bm25_candidate_k)

        # 2. Vector Retrieval — semantic similarity via pgvector HNSW
        query_vec = self.vector_engine.encode(query, normalize=True)
        with VectorDB() as db:
            vector_results = db.search_semantic(
                query_embedding=query_vec,
                top_k=vector_candidate_k,
                location_filter=location_filter,
                experience_filter=experience_filter,
                employment_type_filter=employment_type_filter,
            )

        # 3. Apply BM25-side metadata post-filter to match vector-side filters
        if location_filter:
            bm25_results = [
                r for r in bm25_results
                if location_filter.lower() in r.job.location.lower()
            ]
        if experience_filter:
            bm25_results = [
                r for r in bm25_results
                if r.job.experience_required == experience_filter
            ]
        if employment_type_filter:
            bm25_results = [
                r for r in bm25_results
                if r.job.employment_type.lower() == employment_type_filter.lower()
            ]

        # 4. Reciprocal Rank Fusion
        return self._fuse(bm25_results, vector_results, top_k=top_k)
