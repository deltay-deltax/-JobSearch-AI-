"""Unit tests for Stage 3: Dense Vector Embeddings and Cosine Similarity Retrieval.

Tests verify:
- Cosine similarity mathematical calculations (identical, orthogonal, opposite vectors)
- Embedding generation shape (384 dimensions)
- Unit-length L2 normalization
- Semantic ranking order (synonymous queries rank above irrelevant docs)
- Caching mechanism for precomputed embeddings
"""

import unittest
import numpy as np
import tempfile
from pathlib import Path

from src.search.vector_search import (
    compute_cosine_similarity,
    VectorSearchEngine,
)
from src.ingestion.schema import JobPosting


class TestCosineMath(unittest.TestCase):
    """Tests the pure mathematical properties of cosine similarity."""

    def test_identical_vectors(self):
        vec = np.array([0.5, 0.5, 0.5, 0.5])
        sim = compute_cosine_similarity(vec, vec)
        self.assertAlmostEqual(sim, 1.0, places=5)

    def test_orthogonal_vectors(self):
        vec_a = np.array([1.0, 0.0])
        vec_b = np.array([0.0, 1.0])
        sim = compute_cosine_similarity(vec_a, vec_b)
        self.assertAlmostEqual(sim, 0.0, places=5)

    def test_opposite_vectors(self):
        vec_a = np.array([1.0, 2.0, 3.0])
        vec_b = np.array([-1.0, -2.0, -3.0])
        sim = compute_cosine_similarity(vec_a, vec_b)
        self.assertAlmostEqual(sim, -1.0, places=5)

    def test_zero_vector(self):
        vec_a = np.array([0.0, 0.0])
        vec_b = np.array([1.0, 2.0])
        sim = compute_cosine_similarity(vec_a, vec_b)
        self.assertEqual(sim, 0.0)


class TestVectorSearchEngine(unittest.TestCase):
    """Tests VectorSearchEngine integration, encoding, and ranking."""

    @classmethod
    def setUpClass(cls):
        # Initialize engine once for tests
        cls.engine = VectorSearchEngine()
        cls.job_backend = JobPosting(
            id="vec_01",
            title="Backend Python Engineer",
            company="ServerCo",
            description="Build scalable REST microservices and APIs using Python, FastAPI, and PostgreSQL.",
            skills=["Python", "FastAPI"],
            location="Bangalore",
        )
        cls.job_frontend = JobPosting(
            id="vec_02",
            title="Frontend UI Engineer",
            company="DesignCo",
            description="Craft responsive web interfaces and user designs using React, TypeScript, and CSS.",
            skills=["React", "TypeScript"],
            location="Remote",
        )
        cls.job_data = JobPosting(
            id="vec_03",
            title="Data Scientist",
            company="StatsCorp",
            description="Statistical modeling, pandas analysis, and machine learning pipelines in Python.",
            skills=["Python", "Machine Learning"],
            location="Bangalore",
        )

    def test_encode_dimensions_and_normalization(self):
        text = "Backend engineer developing scalable cloud APIs."
        vec = self.engine.encode(text, normalize=True)
        # all-MiniLM-L6-v2 outputs 384 dimensions
        self.assertEqual(len(vec), 384)
        norm = np.linalg.norm(vec)
        self.assertAlmostEqual(float(norm), 1.0, places=4)

    def test_semantic_ranking(self):
        # Query uses words that are not in the job_backend title ('server-side', 'endpoints')
        query = "server-side developer building web endpoints"
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_path = Path(tmp_dir) / "test_cache.npy"
            test_engine = VectorSearchEngine(cache_file=cache_path)
            test_engine.fit([self.job_backend, self.job_frontend, self.job_data])

            results = test_engine.search(query, top_k=3)
            self.assertEqual(len(results), 3)
            # Backend job should be rank #1 despite vocabulary differences
            self.assertEqual(results[0].job.id, "vec_01")
            self.assertGreater(results[0].score, results[1].score)
            
            # Verify cache was written
            self.assertTrue(cache_path.exists())


if __name__ == "__main__":
    unittest.main()
