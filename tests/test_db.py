"""Unit tests for Stage 4: PostgreSQL + pgvector Database Layer.

Tests verify:
- Schema creation and idempotency (re-running doesn't crash)
- Job ingestion and upsert behaviour (no duplicates on re-run)
- Semantic similarity search correctness (right job ranks first)
- Cosine similarity score range (always 0-1 for normalized vectors)
- Metadata filter queries (location, employment_type)
- get_job_by_id fetches the right record
- count_jobs returns accurate count
"""

import unittest
import numpy as np
from src.search.db import VectorDB
from src.ingestion.schema import JobPosting
from src.search.vector_search import VectorSearchEngine


class TestVectorDB(unittest.TestCase):
    """Integration tests against the live jobsearch_ai PostgreSQL database."""

    @classmethod
    def setUpClass(cls):
        """Index a small test corpus for all tests in this class."""
        cls.db = VectorDB().connect()
        cls.engine = VectorSearchEngine()

        cls.test_jobs = [
            JobPosting(
                id="test_db_01",
                title="Backend Python Developer",
                company="AlphaTech",
                description="Build scalable REST APIs using Python and FastAPI with PostgreSQL.",
                skills=["python", "fastapi", "postgresql"],
                location="Bangalore",
                experience_required="Fresher",
                employment_type="Internship",
            ),
            JobPosting(
                id="test_db_02",
                title="Frontend React Engineer",
                company="BetaUI",
                description="Design interactive web interfaces using React, TypeScript, and TailwindCSS.",
                skills=["react", "typescript"],
                location="Remote",
                experience_required="1-3 years",
                employment_type="Full-time",
            ),
            JobPosting(
                id="test_db_03",
                title="AI ML Engineer",
                company="GammaAI",
                description="Train and deploy PyTorch transformer models for semantic search and NLP tasks.",
                skills=["python", "pytorch", "nlp"],
                location="Hyderabad",
                experience_required="1-3 years",
                employment_type="Full-time",
            ),
        ]

        texts = [j.to_searchable_text() for j in cls.test_jobs]
        cls.embeddings = cls.engine.encode(texts, normalize=True)
        cls.db.create_schema(drop_existing=False)
        cls.db.ingest_jobs(cls.test_jobs, cls.embeddings)

    @classmethod
    def tearDownClass(cls):
        """Remove test records from the database after all tests run."""
        with cls.db.conn.cursor() as cur:
            cur.execute("DELETE FROM jobs WHERE id LIKE 'test_db_%';")
        cls.db.conn.commit()
        cls.db.close()

    def test_jobs_were_ingested(self):
        total = self.db.count_jobs()
        self.assertGreaterEqual(total, 3)

    def test_upsert_idempotency(self):
        """Re-inserting the same records should not increase the job count."""
        before = self.db.count_jobs()
        self.db.ingest_jobs(self.test_jobs, self.embeddings)
        after = self.db.count_jobs()
        self.assertEqual(before, after)

    def test_semantic_search_correct_ranking(self):
        """A backend Python query should return the Python job ranked first."""
        query_vec = self.engine.encode("Python FastAPI backend developer", normalize=True)
        results = self.db.search_semantic(query_vec, top_k=3)
        ids = [r.job.id for r in results]
        self.assertIn("test_db_01", ids)
        # Verify rank 1 is the Python backend job
        top_job = next(r for r in results if r.job.id == "test_db_01")
        self.assertEqual(top_job.rank, 1)

    def test_score_range(self):
        """All cosine similarity scores must be in [0, 1] for normalized vectors."""
        query_vec = self.engine.encode("software engineer", normalize=True)
        results = self.db.search_semantic(query_vec, top_k=3)
        for r in results:
            self.assertGreaterEqual(r.score, -0.01)   # allow tiny float epsilon
            self.assertLessEqual(r.score, 1.01)

    def test_employment_type_filter(self):
        """Filtering by 'Internship' should only return internship positions."""
        query_vec = self.engine.encode("python developer", normalize=True)
        results = self.db.search_semantic(
            query_vec, top_k=10, employment_type_filter="Internship"
        )
        for r in results:
            self.assertEqual(r.job.employment_type.lower(), "internship")

    def test_location_filter(self):
        """Filtering by 'Hyderabad' should only return Hyderabad jobs."""
        query_vec = self.engine.encode("machine learning engineer", normalize=True)
        results = self.db.search_semantic(
            query_vec, top_k=10, location_filter="Hyderabad"
        )
        for r in results:
            self.assertIn("hyderabad", r.job.location.lower())

    def test_get_job_by_id(self):
        """Fetching by ID should return the exact matching record."""
        job = self.db.get_job_by_id("test_db_02")
        self.assertIsNotNone(job)
        self.assertEqual(job.title, "Frontend React Engineer")
        self.assertEqual(job.company, "BetaUI")

    def test_get_job_by_id_not_found(self):
        """Fetching a non-existent ID should return None."""
        job = self.db.get_job_by_id("job_does_not_exist_xyz")
        self.assertIsNone(job)


if __name__ == "__main__":
    unittest.main()
