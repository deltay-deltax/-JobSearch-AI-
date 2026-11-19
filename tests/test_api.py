"""Unit and integration tests for FastAPI REST API endpoints.

Tests verify:
- GET /api/health returns 200 and healthy status
- POST /api/search returns valid ranked JSON response
- GET /api/jobs/{id} returns job metadata
- GET /api/jobs/{invalid} returns 404
"""

import unittest
from fastapi.testclient import TestClient
from src.api.main import app


class TestAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Using TestClient as context manager triggers the lifespan event
        cls.client_ctx = TestClient(app)
        cls.client = cls.client_ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_ctx.__exit__(None, None, None)

    def test_health_endpoint(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["postgres_connected"])
        self.assertGreaterEqual(data["total_jobs_indexed"], 80)

    def test_search_endpoint(self):
        payload = {
            "query": "Python FastAPI backend intern",
            "location": "Bangalore",
            "experience": "Fresher",
            "top_k": 3,
        }
        resp = self.client.post("/api/search", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["query"], payload["query"])
        self.assertGreaterEqual(len(data["results"]), 1)
        first = data["results"][0]
        self.assertIn("job_id", first)
        self.assertIn("score", first)
        self.assertIn("why_matched", first)

    def test_get_job_by_id(self):
        resp = self.client.get("/api/jobs/job_0001")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["id"], "job_0001")
        self.assertIn("title", data)
        self.assertIn("company", data)

    def test_get_job_not_found(self):
        resp = self.client.get("/api/jobs/job_nonexistent_99999")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
