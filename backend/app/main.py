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