# CyberTriage

CyberTriage is a local digital forensics and incident response workspace. It
includes a React dashboard, a FastAPI API, a SQLite database, evidence storage,
basic rule-based evidence scans, investigation timelines, and report exports.

## Requirements

- Python 3.10 or newer
- Node.js 22.12 or newer and npm

## Run from a fresh clone

Clone the repository and open the project directory:

```bash
git clone https://github.com/amethystakira/CyberTriage.git
cd CyberTriage
```

### Start the API

In one terminal, from the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --reload
```

On Windows PowerShell, activate the environment with
`.venv\Scripts\Activate.ps1` instead of `source .venv/bin/activate`.

The API runs at <http://127.0.0.1:8000>. Its interactive documentation is at
<http://127.0.0.1:8000/docs>. The first run creates the SQLite database and
sample investigations automatically. Uploaded evidence is saved in the local
`evidence/` folder.

### Start the web app

In a second terminal, from the project root:

```bash
cd frontend
npm ci
npm run dev
```

Open the local URL printed by Vite, normally <http://localhost:5173>. Keep both
terminals running while using the app. Vite forwards `/api` requests to the API
at `http://127.0.0.1:8000`.

## Build the frontend

```bash
cd frontend
npm ci
npm run build
```

## Detection engine quick analysis

From the project root, with Python 3.10 or newer:

```bash
python - <<'PY'
from pathlib import Path
from detection_engine.log_parser import parse_auth_log
from detection_engine.brute_force import detect_brute_force
from detection_engine.suspicious_ip import identify_suspicious_ips
from detection_engine.report_generator import generate_report

events = parse_auth_log(Path("sample_data/synthetic_auth_activity.log").read_text())
findings = detect_brute_force(events) + identify_suspicious_ips(events)
print(generate_report(events, findings))
PY
```

Evidence analysis in the app is a simple text rule scan for readable text. Treat
its matches as triage hints for manual review, not as proof of malicious
activity or a substitute for forensic analysis.
