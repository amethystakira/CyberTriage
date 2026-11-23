# CyberTriage

CyberTriage is a digital forensics and incident response workspace. It includes
a React dashboard, a FastAPI API, a relational database, evidence storage, basic
rule-based evidence scans, investigation timelines, and report exports.

The backend uses SQLite by default. Set `DATABASE_URL` to a PostgreSQL URL to
use PostgreSQL through SQLAlchemy; the existing SQLite database remains the
default fallback. See [DE/README.md](DE/README.md) for the data model, SQL
examples, migration notes, and query evidence.

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
seeds a demo dataset automatically: 5 investigations, 8 harmless text evidence
files, 10 findings, 5 analysis runs, and related timeline events. Seeding is
idempotent: backend restarts do not duplicate demo rows or overwrite
user-created records. Uploaded evidence is saved in the local `evidence/`
folder. On first use, the web app prompts you to create the initial
administrator account. Authentication, session, and viva demo details are in
[docs/AUTHENTICATION.md](docs/AUTHENTICATION.md).

To use a local `.env` file, copy `.env.example` to `.env`, fill in
`DATABASE_URL` if needed, then export its values before starting the API:

```bash
set -a
source .env
set +a
```

Leave `DATABASE_URL` empty to use SQLite. For PostgreSQL, set it to a
`postgresql+psycopg://...` URL. Do not commit `.env` or real credentials.

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

## macOS desktop installer

The macOS desktop app bundles the frontend and FastAPI backend. It creates an
empty SQLite database on first launch, then prompts the user to set up the
initial administrator account. New users start with no investigations, evidence,
findings, analysis runs, or timeline events. Development runs still seed the
demo dataset by default. The packaged app stores its database and uploaded
evidence in `~/Library/Application Support/CyberTriage/`; it does not use or
modify the development database in this checkout. The current build is for
Apple Silicon (arm64).

See [DMG_BUILD.md](DMG_BUILD.md) for setup and build commands. The local DMG is
unsigned and not notarized; for public distribution, sign and notarize it with
a Developer ID certificate.

## Run backend tests

From the repository root:

```bash
cd backend
python -m unittest discover -s tests -v
cd ..
python -m unittest discover -s tests -v
```

The backend tests use a temporary SQLite database by default. To run them
against a dedicated PostgreSQL test database, set
`CYBERTRIAGE_TEST_DATABASE_URL` to that database's URL before invoking unittest.
Do not point tests at a database containing data you need to keep.

## Migrate SQLite data to PostgreSQL

First create an empty PostgreSQL database and take a backup of the SQLite
database and `evidence/` directory. Then set `DATABASE_URL` to the PostgreSQL
target and run:

```bash
python -m backend.migrate_sqlite_to_postgres
```

The migration copies the existing rows, expands legacy analysis indicator JSON
into rows, verifies evidence SHA-256 hashes, and leaves the SQLite source
unchanged. It refuses to copy into a PostgreSQL database that already contains
application rows. Set `SQLITE_SOURCE_PATH`, `SQLITE_SOURCE_EVIDENCE_DIR`, and
`CYBERTRIAGE_EVIDENCE_DIR` to override the default paths.

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
