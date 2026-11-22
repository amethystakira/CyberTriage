import os
from pathlib import Path
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError


_test_root = Path(tempfile.mkdtemp(prefix="cybertriage-tests-"))
os.environ["DATABASE_URL"] = os.getenv(
    "CYBERTRIAGE_TEST_DATABASE_URL",
    "sqlite:///" + (_test_root / "test.db").as_posix(),
)
os.environ["CYBERTRIAGE_EVIDENCE_DIR"] = os.getenv(
    "CYBERTRIAGE_TEST_EVIDENCE_DIR", str(_test_root / "evidence")
)

from app.database import get_db
from app.main import app


client = TestClient(app)


class TestCyberTriageAPI(unittest.TestCase):
    def unique_name(self, prefix):
        return f"{prefix}-{uuid.uuid4().hex[:10]}"

    def test_health_endpoint(self):
        response = client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    def test_reports_endpoint_returns_database_data(self):
        response = client.get("/api/reports")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        for key in ("investigations", "evidence", "findings", "timeline", "analysis_runs"):
            self.assertIn(key, payload)

    def test_dashboard_counts(self):
        response = client.get("/api/dashboard/counts")
        self.assertEqual(response.status_code, 200)
        self.assertIn("evidence", response.json())

    def test_cases_endpoint(self):
        response = client.get("/api/cases")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_investigation_creation_and_status_update(self):
        name = self.unique_name("DE test case")
        created = client.post(
            "/api/cases",
            json={"name": name, "investigator": "Test Analyst", "severity": "High"},
        )
        self.assertEqual(created.status_code, 201)
        case_id = created.json()["case_id"]

        updated = client.patch(f"/api/cases/{case_id}", json={"status": "Analyzing"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["status"], "Analyzing")

    def test_evidence_upload_analysis_and_indicator_rows(self):
        case = client.post("/api/cases", json={"name": self.unique_name("DE evidence case")})
        self.assertEqual(case.status_code, 201)
        content = b"review sample source 203.0.113.25; powershell -enc observed"
        uploaded = client.post(
            "/api/evidence",
            data={"case_id": case.json()["case_id"]},
            files={"file": ("review.txt", content, "text/plain")},
        )
        self.assertEqual(uploaded.status_code, 201)
        evidence_id = uploaded.json()["evidence_id"]
        self.assertEqual(uploaded.json()["size_bytes"], len(content))

        scan = client.post(f"/api/evidence/{evidence_id}/analyze")
        self.assertEqual(scan.status_code, 200)
        self.assertEqual(len(scan.json()["indicators"]), 2)

        runs = client.get("/api/analysis")
        self.assertEqual(runs.status_code, 200)
        matching = [row for row in runs.json() if row["evidence_id"] == evidence_id]
        self.assertEqual(len(matching), 1)
        self.assertEqual(len(matching[0]["indicators"]), 2)

    def test_finding_create_retrieval_and_update(self):
        case = client.post("/api/cases", json={"name": self.unique_name("DE finding case")})
        self.assertEqual(case.status_code, 201)
        created = client.post(
            "/api/findings",
            json={
                "case_id": case.json()["case_id"],
                "title": self.unique_name("Indicator reviewed"),
                "description": "A synthetic record used to verify CRUD behavior.",
                "severity": "Medium",
            },
        )
        self.assertEqual(created.status_code, 201)
        finding_id = created.json()["finding_id"]
        retrieved = client.get("/api/findings")
        self.assertEqual(retrieved.status_code, 200)
        self.assertTrue(any(row["finding_id"] == finding_id for row in retrieved.json()))

        updated = client.patch(f"/api/findings/{finding_id}", json={"status": "Resolved"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["status"], "Resolved")

    def test_database_rejects_orphan_evidence_reference(self):
        with self.assertRaises(IntegrityError):
            with get_db() as db:
                db.execute(
                    "INSERT INTO evidence "
                    "(case_id, original_name, stored_name, sha256, size_bytes, uploaded_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        "CASE-DOES-NOT-EXIST",
                        "orphan.txt",
                        self.unique_name("orphan"),
                        "0" * 64,
                        0,
                        "2026-11-01T00:00:00+00:00",
                    ),
                )

    def test_analysis_endpoint_returns_normalized_indicator_lists(self):
        response = client.get("/api/analysis")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all("indicators" in run for run in response.json()))

    def test_legacy_sqlite_migration_preserves_rows_and_indicators(self):
        source_path = Path(__file__).resolve().parents[1] / "cybertriage.db"
        if not source_path.is_file():
            self.skipTest("Repository SQLite database is not present.")
        db_path = _test_root / "legacy-migration.db"
        with source_path.open("rb") as source, db_path.open("wb") as target:
            target.write(source.read())

        with sqlite3.connect(db_path) as source:
            columns = {
                row[1] for row in source.execute("PRAGMA table_info(analysis_runs)")
            }
            if "indicators_json" not in columns:
                self.skipTest("Source database already uses normalized indicators.")
            table_names = (
                "investigations", "evidence", "findings", "analysis_runs",
                "timeline_events",
            )
            counts_before = {
                table: source.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in table_names
            }
            indicators_before = sum(
                len(json.loads(row[0] or "[]"))
                for row in source.execute("SELECT indicators_json FROM analysis_runs")
            )

        env = os.environ.copy()
        env["DATABASE_URL"] = "sqlite:///" + db_path.as_posix()
        env["CYBERTRIAGE_EVIDENCE_DIR"] = str(_test_root / "migration-evidence")
        subprocess.run(
            [sys.executable, "-c", "from app.database import initialize_schema; initialize_schema()"],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        with sqlite3.connect(db_path) as migrated:
            columns_after = {
                row[1] for row in migrated.execute("PRAGMA table_info(analysis_runs)")
            }
            counts_after = {
                table: migrated.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in table_names
            }
            indicators_after = migrated.execute(
                "SELECT COUNT(*) FROM analysis_indicators"
            ).fetchone()[0]
            fk_errors = migrated.execute("PRAGMA foreign_key_check").fetchall()

        self.assertNotIn("indicators_json", columns_after)
        self.assertEqual(counts_after, counts_before)
        self.assertEqual(indicators_after, indicators_before)
        self.assertEqual(fk_errors, [])


if __name__ == "__main__":
    unittest.main()
