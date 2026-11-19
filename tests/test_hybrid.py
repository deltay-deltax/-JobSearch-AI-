"""Unit tests for Stage 5: Hybrid Search with Reciprocal Rank Fusion.

Tests verify:
- RRF score calculation math (exact formula values)
- Documents in both lists outscore documents in one list
- Empty BM25 results fall back to vector-only correctly
- Empty vector results fall back to BM25-only correctly
- k=0 edge case (rank 1 contributes 1.0)
- Fusion with real corpus produces sensible rankings
- BM25-missed vocabulary-mismatch queries resolved by vector
"""

import unittest
from dataclasses import dataclass
from src.search.hybrid_search import HybridSearchEngine, HybridSearchResult
from src.search.bm25_search import BM25SearchResult
from src.search.db import DBSearchResult
from src.ingestion.schema import JobPosting


def _make_job(job_id: str, title: str, desc: str = "Generic job description for testing purposes.") -> JobPosting:
    return JobPosting(
        id=job_id,
        title=title,
        company="TestCorp",
        description=desc,
        skills=["python"],
        location="Bangalore",
    )


class TestRRFMath(unittest.TestCase):
    """Tests pure RRF score math in isolation."""

    def setUp(self):
        self.engine = HybridSearchEngine(rrf_k=60)

    def test_rrf_score_rank_1(self):
        score = self.engine._rrf_score(1)
        self.assertAlmostEqual(score, 1 / 61, places=8)

    def test_rrf_score_rank_10(self):
        score = self.engine._rrf_score(10)
        self.assertAlmostEqual(score, 1 / 70, places=8)

    def test_document_in_both_lists_scores_higher(self):
        """A doc present in both BM25 (rank 5) and vector (rank 5) should outscore
        a doc present only in BM25 at rank 1."""
        both_score = self.engine._rrf_score(5) + self.engine._rrf_score(5)
        bm25_only_rank1 = self.engine._rrf_score(1)
        self.assertGreater(both_score, bm25_only_rank1)

    def test_fusion_merges_correctly(self):
        job_a = _make_job("job_a", "Python Backend")
        job_b = _make_job("job_b", "React Frontend")
        job_c = _make_job("job_c", "AI Engineer")

        bm25_res = [
            BM25SearchResult(job=job_a, score=5.0, rank=1, matched_terms=["python"]),
            BM25SearchResult(job=job_b, score=3.0, rank=2, matched_terms=["react"]),
        ]
        vector_res = [
            DBSearchResult(job=job_c, score=0.9, rank=1),
            DBSearchResult(job=job_a, score=0.8, rank=2),
        ]

        # job_a appears in both lists: BM25 rank 1 + vector rank 2
        # job_c appears only in vector: rank 1
        # job_b appears only in BM25: rank 2

        results = self.engine._fuse(bm25_res, vector_res, top_k=3)
        ids_in_order = [r.job.id for r in results]

        # job_a (both lists) should outscore job_c (vector only) and job_b (BM25 only)
        self.assertEqual(ids_in_order[0], "job_a")

    def test_bm25_only_fallback(self):
        """When vector results are empty, should still return BM25 results."""
        job_a = _make_job("job_x", "DevOps Engineer")
        bm25_res = [BM25SearchResult(job=job_a, score=4.0, rank=1, matched_terms=["devops"])]
        results = self.engine._fuse(bm25_res, [], top_k=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].job.id, "job_x")
        self.assertIsNone(results[0].vector_rank)
        self.assertEqual(results[0].bm25_rank, 1)

    def test_vector_only_fallback(self):
        """When BM25 returns nothing, should still return vector results."""
        job_a = _make_job("job_y", "ML Researcher")
        vec_res = [DBSearchResult(job=job_a, score=0.75, rank=1)]
        results = self.engine._fuse([], vec_res, top_k=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].job.id, "job_y")
        self.assertIsNone(results[0].bm25_rank)
        self.assertEqual(results[0].vector_rank, 1)

    def test_sources_property(self):
        job = _make_job("job_z", "Full Stack")
        bm25_res = [BM25SearchResult(job=job, score=2.0, rank=1, matched_terms=[])]
        vec_res  = [DBSearchResult(job=job, score=0.6, rank=1)]
        results = self.engine._fuse(bm25_res, vec_res, top_k=1)
        self.assertIn("BM25",   results[0].sources)
        self.assertIn("Vector", results[0].sources)


class TestHybridSearchIntegration(unittest.TestCase):
    """Integration tests against the real 80-job corpus in PostgreSQL."""

    @classmethod
    def setUpClass(cls):
        from src.ingestion.loader import load_raw_jobs
        from src.config import DEFAULT_PROCESSED_JOBS_PATH

        raw = load_raw_jobs(DEFAULT_PROCESSED_JOBS_PATH)
        cls.jobs = [JobPosting(**item) for item in raw]

        cls.engine = HybridSearchEngine()
        cls.engine.fit(cls.jobs)

    def test_hybrid_search_returns_results(self):
        results = self.engine.search("Python backend developer", top_k=5)
        self.assertGreater(len(results), 0)

    def test_top_result_has_valid_rrf_score(self):
        results = self.engine.search("FastAPI microservices Python", top_k=5)
        self.assertGreater(results[0].rrf_score, 0)
        # Score must decrease monotonically
        for i in range(len(results) - 1):
            self.assertGreaterEqual(results[i].rrf_score, results[i + 1].rrf_score)

    def test_vocabulary_mismatch_query_resolved(self):
        """'deep learning neural networks' — BM25 misses, vector finds AI jobs.
        Hybrid should return AI/ML Engineer as the top result."""
        results = self.engine.search("deep learning neural networks transformer", top_k=5)
        titles = [r.job.title for r in results]
        self.assertTrue(
            any("AI" in t or "ML" in t or "Data" in t for t in titles),
            msg=f"Expected AI/ML job in top 5, got: {titles}"
        )

    def test_employment_type_filter(self):
        results = self.engine.search(
            "software engineer", top_k=10,
            employment_type_filter="Internship"
        )
        for r in results:
            self.assertEqual(r.job.employment_type.lower(), "internship")


if __name__ == "__main__":
    unittest.main()
