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
    admin_email = "admin@example.test"
    admin_password = "TestPassword!ForCyberTriage"

    def setUp(self):
        if client.get("/api/auth/me").status_code == 200:
            return
        status = client.get("/api/auth/status").json()
        if status["setup_required"]:
            response = client.post(
                "/api/auth/bootstrap",
                json={
                    "email": self.admin_email,
                    "display_name": "Test Administrator",
                    "password": self.admin_password,
                },
            )
        else:
            response = client.post(
                "/api/auth/login",
                json={"email": self.admin_email, "password": self.admin_password},
            )
        self.assertEqual(response.status_code, 201 if status["setup_required"] else 200)
        client.headers.update({"X-CSRF-Token": response.json()["csrf_token"]})

    def unique_name(self, prefix):
        return f"{prefix}-{uuid.uuid4().hex[:10]}"

    def test_api_requires_login(self):
        anonymous = TestClient(app)
        response = anonymous.get("/api/cases")
        self.assertEqual(response.status_code, 401)

    def test_password_hash_session_cookie_and_logout(self):
        with get_db() as db:
            stored = db.execute(
                "SELECT password_hash FROM users WHERE email=?", (self.admin_email,)
            ).fetchone()["password_hash"]
        self.assertTrue(stored.startswith("pbkdf2_sha256$600000$"))
        self.assertNotIn(self.admin_password, stored)

        session_client = TestClient(app)
        response = session_client.post(
            "/api/auth/login",
            json={"email": self.admin_email, "password": self.admin_password},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("httponly", response.headers["set-cookie"].lower())
        self.assertIn("samesite=lax", response.headers["set-cookie"].lower())
        session_client.headers.update({"X-CSRF-Token": response.json()["csrf_token"]})
        self.assertEqual(session_client.get("/api/auth/me").status_code, 200)
        self.assertEqual(session_client.post("/api/auth/logout").status_code, 200)
        self.assertEqual(session_client.get("/api/cases").status_code, 401)

    def test_analyst_role_and_case_ownership(self):
        analyst_one = self.unique_name("one") + "@example.test"
        analyst_two = self.unique_name("two") + "@example.test"
        for email in (analyst_one, analyst_two):
            created = client.post(
                "/api/auth/users",
                json={"email": email, "display_name": email, "password": "AnalystPassword!123"},
            )
            self.assertEqual(created.status_code, 201)

        first = TestClient(app)
        login_one = first.post(
            "/api/auth/login",
            json={"email": analyst_one, "password": "AnalystPassword!123"},
        )
        first.headers.update({"X-CSRF-Token": login_one.json()["csrf_token"]})
        case = first.post("/api/cases", json={"name": "Analyst One private case"})
        self.assertEqual(case.status_code, 201)
        case_id = case.json()["case_id"]
        self.assertEqual(first.get("/api/auth/users").status_code, 403)
        evidence = first.post(
            "/api/evidence",
            data={"case_id": case_id},
            files={"file": ("private.txt", b"analyst one evidence", "text/plain")},
        )
        self.assertEqual(evidence.status_code, 201)

        second = TestClient(app)
        login_two = second.post(
            "/api/auth/login",
            json={"email": analyst_two, "password": "AnalystPassword!123"},
        )
        second.headers.update({"X-CSRF-Token": login_two.json()["csrf_token"]})
        cases = second.get("/api/cases").json()
        self.assertFalse(any(row["case_id"] == case_id for row in cases))
        evidence_rows = second.get("/api/evidence").json()
        self.assertFalse(any(row["evidence_id"] == evidence.json()["evidence_id"] for row in evidence_rows))
        self.assertEqual(
            second.get(f"/api/evidence/{evidence.json()['evidence_id']}/download").status_code,
            404,
        )
        forbidden_update = second.patch(
            f"/api/cases/{case_id}", json={"status": "Completed"}
        )
        self.assertEqual(forbidden_update.status_code, 404)

    def test_mutating_request_requires_csrf_header(self):
        no_csrf = TestClient(app)
        login = no_csrf.post(
            "/api/auth/login",
            json={"email": self.admin_email, "password": self.admin_password},
        )
        self.assertEqual(login.status_code, 200)
        response = no_csrf.post("/api/cases", json={"name": "CSRF check"})
        self.assertEqual(response.status_code, 403)

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

    def test_legacy_case_migration_preserves_data_and_adds_owner_column(self):
        db_path = _test_root / "legacy-ownership.db"
        with sqlite3.connect(db_path) as legacy:
            legacy.execute("""
                CREATE TABLE investigations (
                    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    investigator TEXT NOT NULL,
                    date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    severity TEXT NOT NULL
                )
            """)
            legacy.execute(
                "INSERT INTO investigations VALUES (1, 'CASE-LEGACY-1', 'Preserved case', 'Analyst', '01 Nov 2026', 'Pending', 'Medium')"
            )

        env = os.environ.copy()
        env["DATABASE_URL"] = "sqlite:///" + db_path.as_posix()
        subprocess.run(
            [sys.executable, "-c", "from app.database import initialize_schema; initialize_schema()"],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        with sqlite3.connect(db_path) as migrated:
            columns = {row[1] for row in migrated.execute("PRAGMA table_info(investigations)")}
            preserved = migrated.execute(
                "SELECT case_id, name FROM investigations WHERE row_id=1"
            ).fetchone()
            fk_errors = migrated.execute("PRAGMA foreign_key_check").fetchall()
        self.assertIn("owner_id", columns)
        self.assertEqual(preserved, ("CASE-LEGACY-1", "Preserved case"))
        self.assertEqual(fk_errors, [])


if __name__ == "__main__":
    unittest.main()
