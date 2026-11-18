"""Unit tests for Stage 1: Data Ingestion, Schema Validation, and Cleaning.

Tests verify:
- Pydantic schema validation & sanitization
- HTML stripping and whitespace normalization
- Skill canonicalization and synonym mapping
- Experience level bucket classification
- Content-hash deduplication
- File loading and persistence
"""

import unittest
from pathlib import Path
import tempfile
import json

from src.ingestion.schema import JobPosting
from src.ingestion.cleaner import (
    clean_text,
    normalize_skill,
    normalize_skills,
    normalize_experience,
    compute_content_fingerprint,
    JobDataCleaner,
)
from src.ingestion.loader import save_processed_jobs, load_raw_jobs


class TestJobSchema(unittest.TestCase):
    """Tests Pydantic validation rules and helper methods."""

    def test_valid_job_creation(self):
        job = JobPosting(
            id="job_001",
            title="  Backend Engineer  ",
            company="  Elip AI  ",
            description="Building high performance distributed systems with Python.",
            skills=["Python", "FastAPI", "Docker"],
            location="Bangalore",
            experience_required="Fresher",
            employment_type="Full-time",
        )
        # Verify automatic whitespace stripping by ConfigDict(str_strip_whitespace=True)
        self.assertEqual(job.title, "Backend Engineer")
        self.assertEqual(job.company, "Elip AI")
        self.assertEqual(len(job.skills), 3)

    def test_skills_from_comma_separated_string(self):
        job = JobPosting(
            id="job_002",
            title="Data Scientist",
            company="Acme Corp",
            description="Machine learning and statistical modeling.",
            skills="Python, PyTorch | Scikit-Learn",
        )
        self.assertEqual(job.skills, ["Python", "PyTorch", "Scikit-Learn"])

    def test_to_searchable_text(self):
        job = JobPosting(
            id="job_003",
            title="AI Engineer",
            company="OpenCo",
            description="Train sentence transformers for semantic retrieval.",
            skills=["Python", "PyTorch"],
            location="Remote",
            experience_required="1-3 years",
        )
        text = job.to_searchable_text()
        self.assertIn("Title: AI Engineer", text)
        self.assertIn("Company: OpenCo", text)
        self.assertIn("Skills: Python, PyTorch", text)
        self.assertIn("Train sentence transformers", text)


class TestTextCleaner(unittest.TestCase):
    """Tests HTML removal and text normalization."""

    def test_strip_html_tags(self):
        raw_html = "<p>We are hiring a <b>Backend Developer</b> with &amp; expertise in APIs.</p>"
        cleaned = clean_text(raw_html)
        self.assertEqual(cleaned, "We are hiring a Backend Developer with & expertise in APIs.")

    def test_whitespace_collapsing(self):
        messy_text = "Python   \t  FastAPI \n\n\n\n\n  Docker"
        cleaned = clean_text(messy_text)
        self.assertNotIn("   ", cleaned)
        self.assertNotIn("\n\n\n", cleaned)


class TestSkillNormalization(unittest.TestCase):
    """Tests skill synonym canonicalization and deduplication."""

    def test_synonym_mapping(self):
        self.assertEqual(normalize_skill("py"), "python")
        self.assertEqual(normalize_skill("Python3"), "python")
        self.assertEqual(normalize_skill("react.js"), "react")
        self.assertEqual(normalize_skill("fast api"), "fastapi")
        self.assertEqual(normalize_skill("k8s"), "kubernetes")

    def test_normalize_skills_list(self):
        skills = ["Python", "py", "React.js", "react", "Docker", "DOCKER"]
        normalized = normalize_skills(skills)
        self.assertEqual(normalized, ["python", "react", "docker"])


class TestExperienceNormalization(unittest.TestCase):
    """Tests experience string categorization."""

    def test_fresher_bucket(self):
        self.assertEqual(normalize_experience("Fresher"), "Fresher")
        self.assertEqual(normalize_experience("0-1 years"), "Fresher")
        self.assertEqual(normalize_experience("Entry level intern"), "Fresher")

    def test_junior_mid_bucket(self):
        self.assertEqual(normalize_experience("1-3 years"), "1-3 years")
        self.assertEqual(normalize_experience("2+ years required"), "1-3 years")

    def test_senior_bucket(self):
        self.assertEqual(normalize_experience("5+ years"), "5+ years")
        self.assertEqual(normalize_experience("Senior Principal Architect"), "5+ years")


class TestJobDataCleaner(unittest.TestCase):
    """Tests batch processing and duplicate detection."""

    def test_deduplication(self):
        cleaner = JobDataCleaner()
        record_1 = {
            "id": "job_101",
            "title": "Software Engineer",
            "company": "TechStart",
            "description": "Building microservices using Python and FastAPI in Bangalore.",
            "skills": ["Python", "FastAPI"],
        }
        # Duplicate record with different ID and minor extra spaces
        record_2 = {
            "id": "job_999",
            "title": "Software Engineer  ",
            "company": " TechStart ",
            "description": "<p>Building microservices using Python and FastAPI in Bangalore.</p>",
            "skills": ["python", "fast-api"],
        }

        results = cleaner.process_batch([record_1, record_2])
        self.assertEqual(len(results), 1)
        self.assertEqual(cleaner.stats["dropped_duplicates"], 1)
        self.assertEqual(cleaner.stats["valid_records"], 1)

    def test_invalid_record_dropping(self):
        cleaner = JobDataCleaner()
        # Missing description / too short
        invalid_record = {
            "id": "job_bad",
            "title": "Developer",
            "company": "BadCorp",
            "description": "Short",  # Min length is 10
        }
        results = cleaner.process_batch([invalid_record])
        self.assertEqual(len(results), 0)
        self.assertEqual(cleaner.stats["dropped_invalid"], 1)


class TestFilePersistence(unittest.TestCase):
    """Tests saving and loading JSON records."""

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_jobs.json"
            job = JobPosting(
                id="test_01",
                title="QA Automation Engineer",
                company="TestLabs",
                description="Writing automated test suites in Python.",
                skills=["Python", "PyTest"],
            )
            save_processed_jobs([job], file_path)

            loaded = load_raw_jobs(file_path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["title"], "QA Automation Engineer")
            self.assertEqual(loaded[0]["company"], "TestLabs")


if __name__ == "__main__":
    unittest.main()
