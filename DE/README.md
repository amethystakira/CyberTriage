# CyberTriage Data Engineering Project

This folder documents and implements the database layer used by CyberTriage.
The repository originally used SQLite through Python's `sqlite3` module. The
backend now uses SQLAlchemy Core with SQLite as its default and PostgreSQL as an
environment-selected option. Existing SQLite workspaces are migrated in place
from the old JSON indicator field to a normalized indicator table; a separate
command copies a SQLite workspace into PostgreSQL without changing the source.

## Folder guide

- `01-database-selection.md` compares the existing SQLite implementation with
  PostgreSQL for this application.
- `02-er-diagram.mmd` is the editable ER diagram source. A PNG is included when
  a Mermaid renderer is available in the development environment.
- `03-normalization.md` explains the verified schema's 1NF, 2NF, and 3NF
  decisions, including the indicator-list migration.
- `04-database-schema.sql` is the PostgreSQL DDL matching the SQLAlchemy schema.
- `05-sample-data.sql` inserts synthetic records for a disposable database.
- `06-queries.sql` contains 12 project-specific SQL examples in a transaction
  that ends with `ROLLBACK`.
- `07-query-outputs/` records actual SQLite execution and PostgreSQL limitations.
- `08-backend-integration.md` traces API requests through SQLAlchemy to the DB.
- `09-database-architecture.md` describes the component and data flow.
- `10-performance-and-integrity.md` covers constraints, validation, and indexes.
- `sample-evidence/` contains a small, synthetic evidence fixture.

## Database configuration

If `DATABASE_URL` is unset or empty, the application uses the existing SQLite
file at `backend/cybertriage.db`. A PostgreSQL URL must use the psycopg 3
dialect, for example:

```text
postgresql+psycopg://cybertriage:YOUR_PASSWORD@localhost:5432/cybertriage
```

Set the URL in the process environment. Do not put real credentials in Git.
`.env.example` shows the expected setting without containing a secret.

## Create a PostgreSQL schema and exercise the SQL

With an empty PostgreSQL database and `DATABASE_URL` exported:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f DE/04-database-schema.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f DE/05-sample-data.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f DE/06-queries.sql
```

`05-sample-data.sql` inserts database metadata only. To let the application
download its synthetic evidence record, copy
`DE/sample-evidence/de-auth-sample.log` to `evidence/de-auth-sample.log`; the
fixture's digest and size match the SQL row.

## Move an existing SQLite workspace to PostgreSQL

Back up the SQLite file and evidence folder first. Set `DATABASE_URL` to an
empty PostgreSQL database, then run:

```bash
python -m backend.migrate_sqlite_to_postgres
```

Optional environment variables are `SQLITE_SOURCE_PATH`,
`SQLITE_SOURCE_EVIDENCE_DIR`, and `CYBERTRIAGE_EVIDENCE_DIR`. The migration
checks file hashes and row counts, preserves IDs, translates legacy JSON
indicator arrays into child rows, and leaves the SQLite source unchanged. The
target PostgreSQL schema must be empty.

## Query output status

The outputs in `07-query-outputs/` are from an isolated copy of the repository's
SQLite database. A local PostgreSQL server was not available during this work,
so no PostgreSQL execution is claimed. The instructions there explain how to
capture actual PostgreSQL output when a server is available.

## Run tests

From the repository root:

```bash
cd backend
python -m unittest discover -s tests -v
cd ..
python -m unittest discover -s tests -v
```

Backend tests use a temporary SQLite database unless
`CYBERTRIAGE_TEST_DATABASE_URL` is set to a dedicated test database.
