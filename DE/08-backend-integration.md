# Backend integration

## Database configuration and access layer

The FastAPI application is `backend/app/main.py`. SQLAlchemy Core metadata,
engine creation, table definitions, SQLite foreign-key setup, and compatibility
with the existing parameterized route SQL live in `backend/app/database.py`.

At startup, `DATABASE_URL` selects the database. An empty value chooses
`backend/cybertriage.db`; a `postgresql+psycopg://...` URL selects PostgreSQL.
The `get_db()` context manager wraps each route's database work in a
SQLAlchemy transaction. SQLite foreign-key enforcement is enabled on every
connection. `metadata.create_all()` creates missing tables and indexes.

The current Pydantic request schemas are defined in `backend/app/main.py`:
`InvestigationCreate`, `InvestigationStatusUpdate`, `FindingCreate`, and
`FindingStatusUpdate`. SQLAlchemy Core is used instead of ORM classes because
the existing API already uses explicit SQL statements and lightweight row
operations.

## Example route-to-database flows

- `POST /api/cases` validates the investigation name and severity, inserts an
  investigation, records a timeline event, then returns the inserted case.
- `PATCH /api/cases/{case_id}` validates status, updates the investigation,
  records the status change, and returns the updated row.
- `POST /api/evidence` validates the file size, writes bytes to `EVIDENCE_DIR`,
  calculates SHA-256, inserts metadata, and records a timeline event. If the
  database transaction fails, it removes the new file.
- `POST /api/evidence/{evidence_id}/analyze` reads stored text, inserts an
  `analysis_runs` row and ordered `analysis_indicators` rows, then records
  findings and timeline events in the same transaction.
- `POST /api/findings` inserts the finding and its timeline event;
  `PATCH /api/findings/{finding_id}` updates its status and records the change.
- `GET /api/reports` composes investigation, evidence, finding, timeline, and
  analysis data from the existing GET route functions.

FastAPI commits a route's SQLAlchemy transaction when its `get_db()` context
exits successfully; an exception rolls it back. Upload cleanup is handled
alongside the transaction because file storage is outside the database.

## React communication

The React entry point is `frontend/src/main.jsx`; the workspace UI and API
helpers are in `frontend/src/App.jsx`. The frontend calls same-origin `/api`
paths. During local development, `frontend/vite.config.js` proxies these to
`http://127.0.0.1:8000`. The backend returns JSON, which React stores in
workspace state and renders by module. Workspace identity preferences are
stored separately in browser `localStorage`.

## PostgreSQL migration behavior

`backend/migrate_sqlite_to_postgres.py` copies an existing SQLite workspace
into an empty PostgreSQL database. It preserves integer IDs and checks counts,
copies referenced evidence files after verifying SHA-256, and converts legacy
JSON indicator arrays into rows. It does not edit or remove the SQLite source.
On ordinary app startup, an old SQLite `analysis_runs.indicators_json` table is
migrated transactionally to the normalized run/indicator tables.

PostgreSQL availability was not present in the inspected environment, so the
integration code is described as implemented but a live PostgreSQL connection
and CRUD run remain unverified.
