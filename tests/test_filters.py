"""Unit tests for Stage 6: Metadata Filtering and Personalization.

Tests verify:
- Hard location filter restricts results correctly
- Hard experience level filter works
- Hard employment type filter works
- Skill boosting increases final_score above rrf_score
- Location soft boost adds to score for matching locations
- why_matched() returns non-empty explanation string
- Multiple employment_types filter works (set of acceptable types)
- Results are sorted by final_score descending
"""

import unittest
from src.search.filters import (
    PersonalizedSearchEngine, UserPreferences, FilterSpec, PersonalizedResult
)
from src.ingestion.schema import JobPosting
from src.ingestion.loader import load_raw_jobs
from src.config import DEFAULT_PROCESSED_JOBS_PATH


class TestPersonalizedSearch(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        raw = load_raw_jobs(DEFAULT_PROCESSED_JOBS_PATH)
        cls.jobs = [JobPosting(**item) for item in raw]
        cls.engine = PersonalizedSearchEngine()
        cls.engine.fit(cls.jobs)

    def test_hard_employment_type_filter(self):
        filters = FilterSpec(employment_type="Internship")
        results = self.engine.search("software engineer", filters=filters, top_k=10)
        self.assertGreater(len(results), 0)
        for r in results:
            self.assertEqual(r.job.employment_type.lower(), "internship")

    def test_hard_experience_filter(self):
        filters = FilterSpec(experience_level="Fresher")
        results = self.engine.search("developer", filters=filters, top_k=10)
        self.assertGreater(len(results), 0)
        for r in results:
            self.assertEqual(r.job.experience_required, "Fresher")

    def test_hard_location_filter(self):
        filters = FilterSpec(location_contains="Bangalore")
        results = self.engine.search("engineer", filters=filters, top_k=10)
        self.assertGreater(len(results), 0)
        for r in results:
            self.assertIn("bangalore", r.job.location.lower())

    def test_skill_boost_raises_final_score(self):
        """Final score should be higher than raw rrf_score when skill matches exist."""
        prefs = UserPreferences(
            preferred_skills=["Python", "FastAPI"],
            skill_boost_weight=0.005,
        )
        results = self.engine.search("backend Python developer", prefs=prefs, top_k=5)
        # At least one result should have a boost > 0 (Python/FastAPI jobs should match)
        boosted = [r for r in results if r.boost > 0]
        self.assertGreater(len(boosted), 0)
        for r in boosted:
            self.assertGreater(r.final_score, r.rrf_score)

    def test_location_boost_applied(self):
        prefs = UserPreferences(
            preferred_location="Bangalore",
            location_boost=0.01,
        )
        results = self.engine.search("software engineer", prefs=prefs, top_k=10)
        # At least some results should have a boost
        boosted = [r for r in results if r.boost > 0]
        self.assertGreater(len(boosted), 0)

    def test_why_matched_not_empty(self):
        prefs = UserPreferences(preferred_skills=["Python"])
        results = self.engine.search("Python engineer", prefs=prefs, top_k=3)
        for r in results:
            self.assertIsInstance(r.why_matched(), str)
            self.assertGreater(len(r.why_matched()), 0)

    def test_results_sorted_by_final_score(self):
        prefs = UserPreferences(preferred_skills=["Python", "React"])
        results = self.engine.search("developer", prefs=prefs, top_k=10)
        for i in range(len(results) - 1):
            self.assertGreaterEqual(results[i].final_score, results[i + 1].final_score)

    def test_ranks_are_sequential(self):
        results = self.engine.search("engineer", top_k=5)
        ranks = [r.rank for r in results]
        self.assertEqual(ranks, list(range(1, len(results) + 1)))

    def test_matched_skills_subset_of_job_skills(self):
        """Matched skills reported must actually exist in the job's skill list."""
        prefs = UserPreferences(preferred_skills=["Python", "Docker", "FastAPI"])
        results = self.engine.search("backend developer", prefs=prefs, top_k=5)
        for r in results:
            job_skills_lower = {s.lower() for s in r.job.skills}
            for skill in r.matched_skills:
                self.assertIn(skill.lower(), job_skills_lower)

    def test_no_prefs_returns_plain_hybrid_results(self):
        """Without prefs, should still work and return results."""
        results = self.engine.search("machine learning engineer", top_k=5)
        self.assertGreater(len(results), 0)
        for r in results:
            self.assertEqual(r.boost, 0.0)
            self.assertEqual(r.final_score, r.rrf_score)


if __name__ == "__main__":
    unittest.main()
