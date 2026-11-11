
import unittest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestCyberTriageAPI(unittest.TestCase):

    def test_health_endpoint(self):
        response = client.get("/api/health")
        self.assertEqual(response.status_code, 200)

    def test_dashboard_counts(self):
        response = client.get("/api/dashboard/counts")
        self.assertEqual(response.status_code, 200)

    def test_cases_endpoint(self):
        response = client.get("/api/cases")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
