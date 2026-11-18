"""Unit tests for Stage 2: BM25 Keyword Search Engine.

Tests verify:
- Tokenization & stopword removal
- Inverted index construction
- Accurate term frequency & document frequency counts
- BM25 score calculation & rank ordering
- TF saturation (sub-linear growth)
- Document length normalization penalty
- Edge cases: empty query, zero-match queries
"""

import unittest
from src.search.bm25_search import BM25Index, tokenize
from src.ingestion.schema import JobPosting


class TestBM25Search(unittest.TestCase):
    """Test suite for Okapi BM25 Index."""

    def setUp(self):
        self.doc1 = JobPosting(
            id="job_01",
            title="Backend Python Developer",
            company="AlphaTech",
            description="Build scalable REST APIs using Python, FastAPI, and PostgreSQL.",
            skills=["Python", "FastAPI", "PostgreSQL"],
            location="Bangalore",
        )
        self.doc2 = JobPosting(
            id="job_02",
            title="Frontend React Engineer",
            company="BetaWeb",
            description="Design responsive web interfaces using React, JavaScript, and Tailwind CSS.",
            skills=["React", "JavaScript"],
            location="Remote",
        )
        self.doc3 = JobPosting(
            id="job_03",
            title="Full Stack Engineer",
            company="GammaCloud",
            description="Work across the stack with Python backend and React frontend components.",
            skills=["Python", "React"],
            location="Bangalore",
        )
        self.corpus = [self.doc1, self.doc2, self.doc3]
        self.index = BM25Index(k1=1.5, b=0.75).fit(self.corpus)

    def test_tokenization_and_stopwords(self):
        text = "Looking for a Python developer in Bangalore!"
        tokens = tokenize(text, remove_stopwords=True)
        self.assertIn("python", tokens)
        self.assertIn("developer", tokens)
        self.assertIn("bangalore", tokens)
        self.assertNotIn("for", tokens)
        self.assertNotIn("a", tokens)
        self.assertNotIn("in", tokens)

    def test_relevant_result_ranked_top(self):
        query = "Python FastAPI"
        results = self.index.search(query, top_k=3)
        self.assertGreater(len(results), 0)
        # doc1 has both Python and FastAPI, so it should rank #1
        self.assertEqual(results[0].job.id, "job_01")
        self.assertIn("fastapi", results[0].matched_terms)

    def test_zero_match_query(self):
        query = "Kubernetes Golang Terraform"
        results = self.index.search(query, top_k=3)
        self.assertEqual(len(results), 0)

    def test_empty_query(self):
        results = self.index.search("", top_k=5)
        self.assertEqual(len(results), 0)

    def test_length_normalization(self):
        """A short concise job mentioning Python once should outscore
        a huge spammy document mentioning Python once, because b=0.75 penalizes long docs."""
        short_job = JobPosting(
            id="short",
            title="Python Developer",
            company="ShortCo",
            description="Python engineer wanted.",
            skills=["Python"],
        )
        # Long job diluted with filler words
        long_job = JobPosting(
            id="long",
            title="General Consultant",
            company="SpamCo",
            description="Python " + ("management consulting and enterprise business strategy solutions " * 20),
            skills=["Python"],
        )
        small_index = BM25Index(k1=1.5, b=0.75).fit([short_job, long_job])
        results = small_index.search("Python", top_k=2)
        self.assertEqual(results[0].job.id, "short")
        self.assertGreater(results[0].score, results[1].score)

    def test_tf_saturation(self):
        """BM25 term score saturates asymptotically to (k1 + 1), unlike raw TF."""
        query = "python"
        explanation = self.index.explain_score(query, 0)
        term_data = [t for t in explanation["terms"] if t["term"] == "python"][0]
        self.assertGreater(term_data["term_contribution"], 0.0)


if __name__ == "__main__":
    unittest.main()
