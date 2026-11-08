from datetime import datetime
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import uuid
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(
    title="CyberTriage API",
    description="Digital Forensics and Incident Response Platform",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE = Path(__file__).resolve().parent.parent / "cybertriage.db"
EVIDENCE_DIR = Path(__file__).resolve().parents[2] / "evidence"
MAX_EVIDENCE_BYTES = 25 * 1024 * 1024

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection

def record_event(db, event_type, description, case_id=None, occurred_at=None):
    db.execute(
        "INSERT INTO timeline_events (case_id, event_type, description, occurred_at) VALUES (?, ?, ?, ?)",
        (case_id, event_type, description, occurred_at or datetime.now().astimezone().isoformat(timespec="seconds")),
    )

def initialize_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS investigations (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                investigator TEXT NOT NULL,
                date TEXT NOT NULL,
                status TEXT NOT NULL,
                severity TEXT NOT NULL
            )
        """)

        db.executescript("""
            CREATE TABLE IF NOT EXISTS evidence (
                evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES investigations(case_id)
            );
            CREATE TABLE IF NOT EXISTS findings (
                finding_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES investigations(case_id)
            );
            CREATE TABLE IF NOT EXISTS analysis_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id INTEGER NOT NULL,
                summary TEXT NOT NULL,
                indicators_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(evidence_id) REFERENCES evidence(evidence_id)
            ); 
            CREATE TABLE IF NOT EXISTS timeline_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES investigations(case_id)
            );
        """)

        existing = db.execute(
            "SELECT COUNT(*) FROM investigations"
        ).fetchone()[0]

        if existing == 0:
            sample_cases = [
                (
                    "CASE-2026-001",
                    "Suspicious Network Activity",
                    "A. Pal",
                    "03 Nov 2026",
                    "Analyzing",
                    "High",
                ),
               (
                    "CASE-2026-002",
                    "Endpoint Security Review",
                    "A. Pal",
                    "02 Nov 2026",
                    "Completed",
                    "Medium",
                ),
                (
                    "CASE-2026-003",
                    "Unauthorized File Access",
                    "A. Pal",
                    "01 Nov 2026",
                    "Pending",
                    "Critical",
                ),
            ]

            db.executemany("""
                INSERT INTO investigations
                (case_id, name, investigator, date, status, severity)
                VALUES (?, ?, ?, ?, ?, ?)
            """, sample_cases)

        missing_events = db.execute("""
            SELECT i.case_id, i.name, i.date FROM investigations i
            WHERE NOT EXISTS (
                SELECT 1 FROM timeline_events t
                WHERE t.case_id = i.case_id AND t.event_type = 'Investigation created'
            )
        """).fetchall()

        for item in missing_events:
            try:
                case_date = datetime.strptime(item["date"], "%d %b %Y").astimezone().isoformat(timespec="seconds")
            except ValueError:
                case_date = None
            record_event(db, "Investigation created", f"Investigation recorded: {item['name']}", item["case_id"], case_date)

        legacy_events = db.execute("""
            SELECT t.event_id, i.date FROM timeline_events t
            JOIN investigations i ON i.case_id = t.case_id
            WHERE t.event_type = 'Investigation created' AND t.description LIKE 'Investigation recorded:%'
        """).fetchall()
        for event in legacy_events:
            try:
                case_date = datetime.strptime(event["date"], "%d %b %Y").astimezone().isoformat(timespec="seconds")
            except ValueError:
                continue
            db.execute("UPDATE timeline_events SET occurred_at = ? WHERE event_id = ?", (case_date, event["event_id"]))

initialize_db()


class InvestigationCreate(BaseModel):
    name: str
    investigator: str = "A. Pal"
    severity: str = "Unassigned"

class InvestigationStatusUpdate(BaseModel):
    status: str

@app.get("/")
def home():
    return {
        "application": "CyberTriage",
        "status": "online",
        "version": "0.2.0",
    }

@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "CyberTriage API",
    }

@app.get("/api/cases")
def get_cases():
    with get_db() as db:
        rows = db.execute("""
            SELECT case_id, name, investigator, date, status, severity
            FROM investigations
            ORDER BY row_id DESC
        """).fetchall()

    return [dict(row) for row in rows]

@app.post("/api/cases", status_code=201)
def create_case(case: InvestigationCreate):
    name = case.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Investigation name cannot be empty.",
        )

    with get_db() as db:
        next_number = db.execute(
            "SELECT COALESCE(MAX(row_id), 0) + 1 FROM investigations"
        ).fetchone()[0]

        case_id = f"CASE-{datetime.now().year}-{next_number:03d}"
        date = datetime.now().strftime("%d %b %Y")

        db.execute("""
            INSERT INTO investigations
            (case_id, name, investigator, date, status, severity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            case_id,
            name,
            case.investigator,
            date,
            "Pending",
            case.severity,
        ))
        record_event(db, "Investigation created", f"Created investigation: {name}", case_id)

        created = db.execute("""
            SELECT case_id, name, investigator, date, status, severity
            FROM investigations
            WHERE case_id = ?
        """, (case_id,)).fetchone()

    return dict(created)

@app.patch("/api/cases/{case_id}")
def update_case_status(case_id: str, update: InvestigationStatusUpdate):
    if update.status not in {"Pending", "Analyzing", "Completed"}:
        raise HTTPException(status_code=400, detail="Status must be Pending, Analyzing, or Completed.")
    with get_db() as db:
        case = db.execute("SELECT name, status FROM investigations WHERE case_id = ?", (case_id,)).fetchone()
        if not case:
            raise HTTPException(status_code=404, detail="Investigation not found.")
        db.execute("UPDATE investigations SET status = ? WHERE case_id = ?", (update.status, case_id))
        record_event(db, "Investigation status updated", f"Changed {case['name']} from {case['status']} to {update.status}.", case_id)
        updated = db.execute("""
            SELECT case_id, name, investigator, date, status, severity
            FROM investigations WHERE case_id = ?
        """, (case_id,)).fetchone()
    return dict(updated)

@app.get("/api/dashboard/counts")
def dashboard_counts():
    with get_db() as db:
        return {
            "investigations": db.execute("SELECT COUNT(*) FROM investigations").fetchone()[0],
            "findings": db.execute("SELECT COUNT(*) FROM findings").fetchone()[0],
            "evidence": db.execute("SELECT COUNT(*) FROM evidence").fetchone()[0],
            "completed": db.execute("SELECT COUNT(*) FROM investigations WHERE lower(status) = 'completed'").fetchone()[0],
        }

@app.get("/api/evidence")
def get_evidence():
    with get_db() as db:
        rows = db.execute("""
            SELECT e.evidence_id, e.case_id, e.original_name, e.sha256, e.size_bytes,
                   e.uploaded_at, i.name AS case_name
            FROM evidence e LEFT JOIN investigations i ON i.case_id = e.case_id
            ORDER BY e.evidence_id DESC
        """).fetchall()
    return [dict(row) for row in rows]

@app.get("/api/evidence/{evidence_id}/download")
def download_evidence(evidence_id: int):
    with get_db() as db:
        row = db.execute(
            "SELECT original_name, stored_name FROM evidence WHERE evidence_id = ?",
            (evidence_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Evidence item not found.")
    file_path = EVIDENCE_DIR / row["stored_name"]
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Stored evidence file is missing.")
    return FileResponse(
        path=file_path,
        filename=row["original_name"],
        media_type="application/octet-stream",
    )