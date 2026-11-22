
from datetime import datetime
import csv
import hashlib
import io
import os
from pathlib import Path
import re
import uuid
from typing import Literal, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .database import get_db, initialize_schema


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

EVIDENCE_DIR = Path(
    os.getenv(
        "CYBERTRIAGE_EVIDENCE_DIR",
        str(Path(__file__).resolve().parents[2] / "evidence"),
    )
)
MAX_EVIDENCE_BYTES = 25 * 1024 * 1024


def record_event(db, event_type, description, case_id=None, occurred_at=None):
    db.execute(
        "INSERT INTO timeline_events (case_id, event_type, description, occurred_at) VALUES (?, ?, ?, ?)",
        (case_id, event_type, description, occurred_at or datetime.now().astimezone().isoformat(timespec="seconds")),
    )


def create_analysis_run(db, evidence_id, summary, indicators, created_at):
    run = db.execute(
        "INSERT INTO analysis_runs (evidence_id, summary, created_at) "
        "VALUES (?, ?, ?) RETURNING run_id",
        (evidence_id, summary, created_at),
    ).fetchone()
    run_id = run["run_id"]
    for ordinal, indicator in enumerate(indicators):
        db.execute(
            "INSERT INTO analysis_indicators "
            "(run_id, ordinal, indicator_type, value, reason) VALUES (?, ?, ?, ?, ?)",
            (
                run_id,
                ordinal,
                indicator["type"],
                indicator["value"],
                indicator["reason"],
            ),
        )
    return run_id


def initialize_db():
    initialize_schema()
    with get_db() as db:
        # Seed each demo record by its stable business key. This adds the full
        # demonstration dataset to empty or existing workspaces without touching
        # user-created rows, and is safe to run on every backend restart.
        demo_cases = [
            ("CASE-2026-001", "Northstar payroll ransomware response", "Maya Chen", "03 Nov 2026", "Analyzing", "Critical"),
            ("CASE-2026-002", "Meridian VPN credential compromise", "Ravi Menon", "05 Nov 2026", "Analyzing", "High"),
            ("CASE-2026-003", "Harborview cloud storage exposure", "Elena Torres", "08 Nov 2026", "Pending", "High"),
            ("CASE-2026-004", "Aster Labs insider data exfiltration", "Jordan Blake", "11 Nov 2026", "Completed", "Critical"),
            ("CASE-2026-005", "Redwood finance business email compromise", "Samira Khan", "14 Nov 2026", "Completed", "Medium"),
        ]
        created_demo_files = []
        try:
            for case in demo_cases:
                db.execute("""
                    INSERT OR IGNORE INTO investigations
                    (case_id, name, investigator, date, status, severity)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, case)

            evidence_samples = [
                ("CASE-2026-001", "payroll-host-memory-notes.txt", b"Forensic triage notes\nHost: PAYROLL-WS17\nObserved remote address 198.51.100.24\nPowerShell -enc command observed in process log\n"),
                ("CASE-2026-001", "ransom-note-readme.txt", b"Incident artifact sample\nFiles encrypted; contact response@example.invalid\nNo executable content.\n"),
                ("CASE-2026-002", "vpn-authentication-export.csv", b"timestamp,account,source_ip,result\n2026-11-05T08:12:00Z,svc-backup,203.0.113.77,failed\n2026-11-05T08:14:00Z,svc-backup,203.0.113.77,success\n"),
                ("CASE-2026-002", "vpn-client-config.txt", b"Client configuration collected for review\nGateway: vpn.meridian.example\n"),
                ("CASE-2026-003", "object-access-audit.log", b"2026-11-08T12:22:31Z GET /exports/customer-q3.csv principal=unknown source=192.0.2.44\n"),
                ("CASE-2026-004", "usb-inventory.txt", b"Endpoint inventory\nDevice: USB mass storage\nUser: analyst.temp\n"),
                ("CASE-2026-004", "endpoint-command-history.txt", b"Review sample command history\nrundll32.exe observed during collection\n"),
                ("CASE-2026-005", "mail-header-sample.txt", b"From: finance-director@redwood.example\nReply-To: payment-review@outside.example\nSubject: Urgent invoice update\n"),
            ]
            evidence_ids = {}
            for case_id, filename, content in evidence_samples:
                digest = hashlib.sha256(content).hexdigest()
                stored_name = f"demo_{digest[:16]}_{filename}"
                EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
                file_path = EVIDENCE_DIR / stored_name
                if not file_path.exists():
                    file_path.write_bytes(content)
                    created_demo_files.append(file_path)
                elif hashlib.sha256(file_path.read_bytes()).hexdigest() != digest:
                    raise RuntimeError(f"Demo evidence file hash mismatch: {stored_name}")
                db.execute("""
                    INSERT INTO evidence
                    (case_id, original_name, stored_name, sha256, size_bytes, uploaded_at)
                    SELECT ?, ?, ?, ?, ?, ? WHERE NOT EXISTS (
                        SELECT 1 FROM evidence WHERE case_id = ? AND sha256 = ?
                    )
                """, (case_id, filename, stored_name, digest, len(content),
                      f"2026-11-{3 + len(evidence_ids):02d}T09:30:00+05:30", case_id, digest))
                evidence_id = db.execute(
                    "SELECT evidence_id FROM evidence WHERE case_id = ? AND sha256 = ?",
                    (case_id, digest),
                ).fetchone()[0]
                evidence_ids[filename] = evidence_id

            findings = [
                ("CASE-2026-001", "Ransomware note present", "A ransom note was recovered from the payroll workstation image.", "Critical", "Open", "2026-11-03T11:15:00+05:30"),
                ("CASE-2026-001", "Suspicious outbound connection", "Triage notes record a connection to 198.51.100.24 during encryption activity.", "High", "Open", "2026-11-03T12:10:00+05:30"),
                ("CASE-2026-002", "Service account login from new region", "The svc-backup account succeeded from an unfamiliar source address after repeated failures.", "High", "Open", "2026-11-05T10:30:00+05:30"),
                ("CASE-2026-002", "Legacy VPN client configuration", "The collected profile permits an outdated authentication method.", "Medium", "Resolved", "2026-11-05T13:20:00+05:30"),
                ("CASE-2026-003", "Public object accessed by unknown principal", "Audit log shows an unauthenticated request for a customer export.", "Critical", "Open", "2026-11-08T13:00:00+05:30"),
                ("CASE-2026-003", "Customer export exposure window identified", "Access review narrowed the exposure window to approximately 18 minutes.", "High", "Resolved", "2026-11-08T15:40:00+05:30"),
                ("CASE-2026-004", "Removable media connected before departure", "USB inventory and endpoint records align with the employee access window.", "High", "Resolved", "2026-11-11T14:05:00+05:30"),
                ("CASE-2026-004", "Suspicious library execution", "Command history contains a rundll32 invocation requiring attribution review.", "Medium", "Resolved", "2026-11-11T16:25:00+05:30"),
                ("CASE-2026-005", "Reply-to address differs from sender", "Mail header directs replies to an external lookalike address.", "High", "Open", "2026-11-14T09:50:00+05:30"),
                ("CASE-2026-005", "Invoice payment request held", "Finance placed the requested transfer on hold pending out-of-band verification.", "Medium", "Resolved", "2026-11-14T11:30:00+05:30"),
            ]
            for finding in findings:
                db.execute("""
                    INSERT INTO findings (case_id, title, description, severity, status, created_at)
                    SELECT ?, ?, ?, ?, ?, ? WHERE NOT EXISTS (
                        SELECT 1 FROM findings WHERE case_id = ? AND title = ?
                    )
                """, (*finding, finding[0], finding[1]))

            analysis_samples = [
                ("payroll-host-memory-notes.txt", "Text triage found a suspicious remote address and an encoded PowerShell command reference.", [{"type": "IPv4 address", "value": "198.51.100.24", "reason": "Address found in evidence text"}, {"type": "Keyword", "value": "powershell -enc", "reason": "Matched a simple review keyword"}]),
                ("ransom-note-readme.txt", "No configured indicators found in readable text.", []),
                ("vpn-authentication-export.csv", "Text triage found one source address for analyst review.", [{"type": "IPv4 address", "value": "203.0.113.77", "reason": "Address found in evidence text"}]),
                ("object-access-audit.log", "Text triage found an address associated with the object access event.", [{"type": "IPv4 address", "value": "192.0.2.44", "reason": "Address found in evidence text"}]),
                ("endpoint-command-history.txt", "Text triage found a command-line utility reference for manual review.", [{"type": "Keyword", "value": "rundll32", "reason": "Matched a simple review keyword"}]),
            ]
            for index, (filename, summary, indicators) in enumerate(analysis_samples, 1):
                evidence_id = evidence_ids[filename]
                existing_run = db.execute(
                    "SELECT run_id FROM analysis_runs WHERE evidence_id = ? AND summary = ?",
                    (evidence_id, summary),
                ).fetchone()
                if not existing_run:
                    create_analysis_run(
                        db,
                        evidence_id,
                        summary,
                        indicators,
                        f"2026-11-{3 + index:02d}T10:00:00+05:30",
                    )

            events = [
                ("CASE-2026-001", "Evidence added", "Added evidence file: payroll-host-memory-notes.txt", "2026-11-03T09:30:00+05:30"),
                ("CASE-2026-001", "Evidence added", "Added evidence file: ransom-note-readme.txt", "2026-11-03T10:10:00+05:30"),
                ("CASE-2026-001", "Evidence analyzed", "Analyzed evidence file: payroll-host-memory-notes.txt", "2026-11-04T10:00:00+05:30"),
                ("CASE-2026-001", "Finding recorded", "Recorded finding: Ransomware note present", "2026-11-03T11:15:00+05:30"),
                ("CASE-2026-002", "Evidence added", "Added evidence file: vpn-authentication-export.csv", "2026-11-05T09:30:00+05:30"),
                ("CASE-2026-002", "Evidence added", "Added evidence file: vpn-client-config.txt", "2026-11-05T10:00:00+05:30"),
                ("CASE-2026-002", "Evidence analyzed", "Analyzed evidence file: vpn-authentication-export.csv", "2026-11-05T11:00:00+05:30"),
                ("CASE-2026-002", "Finding recorded", "Recorded finding: Service account login from new region", "2026-11-05T10:30:00+05:30"),
                ("CASE-2026-003", "Evidence added", "Added evidence file: object-access-audit.log", "2026-11-08T12:00:00+05:30"),
                ("CASE-2026-003", "Evidence analyzed", "Analyzed evidence file: object-access-audit.log", "2026-11-09T10:00:00+05:30"),
                ("CASE-2026-003", "Finding recorded", "Recorded finding: Public object accessed by unknown principal", "2026-11-08T13:00:00+05:30"),
                ("CASE-2026-004", "Evidence added", "Added evidence file: usb-inventory.txt", "2026-11-11T09:30:00+05:30"),
                ("CASE-2026-004", "Evidence analyzed", "Analyzed evidence file: endpoint-command-history.txt", "2026-11-12T10:00:00+05:30"),
                ("CASE-2026-004", "Finding recorded", "Recorded finding: Suspicious library execution", "2026-11-11T16:25:00+05:30"),
                ("CASE-2026-005", "Evidence added", "Added evidence file: mail-header-sample.txt", "2026-11-14T09:30:00+05:30"),
                ("CASE-2026-005", "Evidence analyzed", "Reviewed mail header indicators", "2026-11-14T10:00:00+05:30"),
                ("CASE-2026-005", "Finding recorded", "Recorded finding: Reply-to address differs from sender", "2026-11-14T09:50:00+05:30"),
            ]
            for event in events:
                db.execute("""
                    INSERT INTO timeline_events (case_id, event_type, description, occurred_at)
                    SELECT ?, ?, ?, ? WHERE NOT EXISTS (
                        SELECT 1 FROM timeline_events WHERE case_id = ? AND event_type = ? AND description = ?
                    )
                """, (*event, event[0], event[1], event[2]))
        except Exception:
            for file_path in created_demo_files:
                file_path.unlink(missing_ok=True)
            raise

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
    severity: Literal["Unassigned", "Low", "Medium", "High", "Critical"] = "Unassigned"


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


@app.post("/api/evidence", status_code=201)
async def upload_evidence(file: UploadFile = File(...), case_id: str = Form(default="")):
    original_name = Path(file.filename or "evidence.bin").name
    content = await file.read(MAX_EVIDENCE_BYTES + 1)
    await file.close()
    if len(content) > MAX_EVIDENCE_BYTES:
        raise HTTPException(status_code=413, detail="Evidence file exceeds the 25 MB upload limit.")
    case_id = case_id.strip() or None
    stored_name = f"{uuid.uuid4().hex}_{original_name}"
    digest = hashlib.sha256(content).hexdigest()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / stored_name).write_bytes(content)
    uploaded_at = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        with get_db() as db:
            if case_id and not db.execute("SELECT 1 FROM investigations WHERE case_id = ?", (case_id,)).fetchone():
                raise HTTPException(status_code=404, detail="Investigation not found.")
            inserted = db.execute("""
                INSERT INTO evidence (case_id, original_name, stored_name, sha256, size_bytes, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING evidence_id
            """, (case_id, original_name, stored_name, digest, len(content), uploaded_at)).fetchone()
            evidence_id = inserted["evidence_id"]
            record_event(db, "Evidence added", f"Added evidence file: {original_name}", case_id)
    except Exception:
        (EVIDENCE_DIR / stored_name).unlink(missing_ok=True)
        raise
    return {"evidence_id": evidence_id, "case_id": case_id, "original_name": original_name,
            "sha256": digest, "size_bytes": len(content), "uploaded_at": uploaded_at}


class FindingCreate(BaseModel):
    title: str
    description: str
    severity: str = "Medium"
    case_id: Optional[str] = None


class FindingStatusUpdate(BaseModel):
    status: str


@app.get("/api/findings")
def get_findings():
    with get_db() as db:
        rows = db.execute("""
            SELECT f.finding_id, f.case_id, f.title, f.description, f.severity, f.status,
                   f.created_at, i.name AS case_name
            FROM findings f LEFT JOIN investigations i ON i.case_id = f.case_id
            ORDER BY f.finding_id DESC
        """).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/findings", status_code=201)
def create_finding(finding: FindingCreate):
    title = finding.title.strip()
    description = finding.description.strip()
    if not title or not description:
        raise HTTPException(status_code=400, detail="Finding title and description are required.")
    if finding.severity not in {"Low", "Medium", "High", "Critical"}:
        raise HTTPException(status_code=400, detail="Severity must be Low, Medium, High, or Critical.")
    with get_db() as db:
        if finding.case_id and not db.execute("SELECT 1 FROM investigations WHERE case_id = ?", (finding.case_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Investigation not found.")
        created_at = datetime.now().astimezone().isoformat(timespec="seconds")
        inserted = db.execute("""
            INSERT INTO findings (case_id, title, description, severity, status, created_at)
            VALUES (?, ?, ?, ?, 'Open', ?)
            RETURNING finding_id
        """, (finding.case_id, title, description, finding.severity, created_at)).fetchone()
        record_event(db, "Finding recorded", f"Recorded finding: {title}", finding.case_id)
        row = db.execute(
            "SELECT * FROM findings WHERE finding_id = ?",
            (inserted["finding_id"],),
        ).fetchone()
    return dict(row)


@app.patch("/api/findings/{finding_id}")
def update_finding_status(finding_id: int, update: FindingStatusUpdate):
    if update.status not in {"Open", "Resolved"}:
        raise HTTPException(status_code=400, detail="Status must be Open or Resolved.")
    with get_db() as db:
        finding = db.execute("SELECT * FROM findings WHERE finding_id = ?", (finding_id,)).fetchone()
        if not finding:
            raise HTTPException(status_code=404, detail="Finding not found.")
        db.execute("UPDATE findings SET status = ? WHERE finding_id = ?", (update.status, finding_id))
        record_event(db, "Finding status updated", f"Marked finding {finding_id} {update.status.lower()}.", finding["case_id"])
        updated = db.execute("SELECT * FROM findings WHERE finding_id = ?", (finding_id,)).fetchone()
    return dict(updated)


@app.get("/api/analysis")
def get_analysis_runs():
    with get_db() as db:
        rows = db.execute("""
            SELECT r.run_id, r.evidence_id, r.summary, r.created_at, e.original_name,
                   i.indicator_id, i.ordinal, i.indicator_type, i.value, i.reason
            FROM analysis_runs r
            JOIN evidence e ON e.evidence_id = r.evidence_id
            LEFT JOIN analysis_indicators i ON i.run_id = r.run_id
            ORDER BY r.run_id DESC, i.ordinal
        """).fetchall()
    runs = {}
    for row in rows:
        run = runs.get(row["run_id"])
        if run is None:
            run = {
                "run_id": row["run_id"],
                "evidence_id": row["evidence_id"],
                "summary": row["summary"],
                "created_at": row["created_at"],
                "original_name": row["original_name"],
                "indicators": [],
            }
            runs[row["run_id"]] = run
        if row["indicator_id"] is not None:
            run["indicators"].append(
                {
                    "type": row["indicator_type"],
                    "value": row["value"],
                    "reason": row["reason"],
                }
            )
    return list(runs.values())


@app.post("/api/evidence/{evidence_id}/analyze")
def analyze_evidence(evidence_id: int):
    ipv4_pattern = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
    suspicious_terms = ("mimikatz", "powershell -enc", "encodedcommand", "credential dump", "rundll32")
    with get_db() as db:
        evidence = db.execute("SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
        if not evidence:
            raise HTTPException(status_code=404, detail="Evidence item not found.")
        file_path = EVIDENCE_DIR / evidence["stored_name"]
        if not file_path.is_file():
            raise HTTPException(status_code=404, detail="Stored evidence file is missing.")
        raw = file_path.read_bytes()
        text = raw.decode("utf-8", errors="ignore")
        indicators = []
        for value in sorted(set(ipv4_pattern.findall(text))):
            octets = [int(part) for part in value.split(".")]
            if all(0 <= octet <= 255 for octet in octets):
                indicators.append({"type": "IPv4 address", "value": value, "reason": "Address found in evidence text"})
        lowered = text.lower()
        for term in suspicious_terms:
            if term in lowered:
                indicators.append({"type": "Keyword", "value": term, "reason": "Matched a simple review keyword"})
        summary = f"Found {len(indicators)} indicator(s) using simple text rules." if indicators else "No configured indicators found in readable text."
        created_at = datetime.now().astimezone().isoformat(timespec="seconds")
        create_analysis_run(db, evidence_id, summary, indicators, created_at)
        record_event(db, "Evidence analyzed", f"Analyzed evidence file: {evidence['original_name']}", evidence["case_id"])
        for indicator in indicators:
            title = f"{indicator['type']} found: {indicator['value']}"
            db.execute("""
                INSERT INTO findings (case_id, title, description, severity, status, created_at)
                VALUES (?, ?, ?, 'Medium', 'Open', ?)
            """, (evidence["case_id"], title, f"{indicator['reason']} in {evidence['original_name']}.", created_at))
            record_event(db, "Finding created by rule scan", title, evidence["case_id"])
    return {"evidence_id": evidence_id, "summary": summary, "indicators": indicators, "created_at": created_at}


@app.get("/api/timeline")
def get_timeline(case_id: Optional[str] = None):
    with get_db() as db:
        query = """
            SELECT t.event_id, t.case_id, t.event_type, t.description, t.occurred_at,
                   i.name AS case_name
            FROM timeline_events t LEFT JOIN investigations i ON i.case_id = t.case_id
        """
        if case_id:
            rows = db.execute(query + " WHERE t.case_id = ? ORDER BY t.event_id DESC", (case_id,)).fetchall()
        else:
            rows = db.execute(query + " ORDER BY t.event_id DESC").fetchall()
    return [dict(row) for row in rows]


@app.get("/api/reports")
def get_report_data():
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "investigations": get_cases(),
        "evidence": get_evidence(),
        "findings": get_findings(),
        "timeline": get_timeline(),
        "analysis_runs": get_analysis_runs(),
    }
