"""Unit tests for Stage 7: Evaluation Metrics (Precision@K, Recall@K, NDCG@K, MRR).

Tests mathematical correctness using known textbook cases.
"""

import unittest
import math
from src.evaluation.metrics import (
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    dcg_at_k,
    ndcg_at_k,
)


class TestMetrics(unittest.TestCase):

    def setUp(self):
        self.retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        self.relevant = {"doc1", "doc3", "doc7"}

    def test_precision_at_k(self):
        # top 3: doc1 (rel), doc2 (not rel), doc3 (rel) -> 2 / 3
        p3 = precision_at_k(self.retrieved, self.relevant, k=3)
        self.assertAlmostEqual(p3, 2 / 3, places=4)

        # top 5: doc1, doc3 -> 2 / 5
        p5 = precision_at_k(self.retrieved, self.relevant, k=5)
        self.assertAlmostEqual(p5, 2 / 5, places=4)

        # zero k
        self.assertEqual(precision_at_k(self.retrieved, self.relevant, k=0), 0.0)

    def test_recall_at_k(self):
        # total relevant = 3 (doc1, doc3, doc7)
        # top 3 contains doc1, doc3 -> 2 / 3
        r3 = recall_at_k(self.retrieved, self.relevant, k=3)
        self.assertAlmostEqual(r3, 2 / 3, places=4)

        # top 5 contains doc1, doc3 -> 2 / 3 (doc7 was not retrieved)
        r5 = recall_at_k(self.retrieved, self.relevant, k=5)
        self.assertAlmostEqual(r5, 2 / 3, places=4)

        # empty relevant set
        self.assertEqual(recall_at_k(self.retrieved, set(), k=5), 0.0)

    def test_reciprocal_rank(self):
        # first relevant item is doc1 at rank 1 -> 1 / 1 = 1.0
        self.assertEqual(reciprocal_rank(self.retrieved, self.relevant), 1.0)

        # first relevant item at rank 2
        self.assertEqual(reciprocal_rank(["doc9", "doc1"], self.relevant), 0.5)

        # no relevant item in retrieved list
        self.assertEqual(reciprocal_rank(["doc9", "doc8"], self.relevant), 0.0)

    def test_ndcg_at_k_perfect_ranking(self):
        """When retrieved documents match ideal relevance, NDCG must be 1.0."""
        rel_map = {"doc1": 3.0, "doc2": 2.0, "doc3": 1.0}
        perfect_retrieved = ["doc1", "doc2", "doc3"]
        ndcg = ndcg_at_k(perfect_retrieved, rel_map, k=3)
        self.assertAlmostEqual(ndcg, 1.0, places=4)

    def test_ndcg_at_k_inverted_ranking(self):
        """Sub-optimal ranking must produce NDCG < 1.0."""
        rel_map = {"doc1": 3.0, "doc2": 2.0, "doc3": 1.0}
        suboptimal = ["doc3", "doc2", "doc1"]
        ndcg = ndcg_at_k(suboptimal, rel_map, k=3)
        self.assertLess(ndcg, 1.0)
        self.assertGreater(ndcg, 0.0)


if __name__ == "__main__":
    unittest.main()
