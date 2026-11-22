# Database selection

## What CyberTriage used before this DE work

The checked-in backend implementation created its tables in
`backend/app/main.py` and used Python's built-in `sqlite3` module. The active
database at inspection time was `backend/cybertriage.db`. It contained five
tables: `investigations` (5 rows), `evidence` (8), `findings` (10),
`analysis_runs` (5), and `timeline_events` (22). SQLite's
`PRAGMA foreign_key_check` returned no violations. The only pre-existing unique
index was for `investigations.case_id`.

The existing routes use parameterized SQL for inserts, reads, and updates.
There are no delete routes. The React app calls those FastAPI routes; SQLite
stores records while evidence bytes live as files in `evidence/`.

## Selected database

PostgreSQL is the preferred production/academic database. The application now
uses SQLAlchemy Core and accepts a `DATABASE_URL` environment variable. An
empty or unset URL keeps SQLite as the working default, so a clean clone still
runs without a PostgreSQL server. A PostgreSQL URL selects the psycopg 3
dialect. PostgreSQL is **not configured or verified in this environment**;
this project adds the integration and migration path but does not claim a live
PostgreSQL deployment.

## Why a relational database fits

CyberTriage records have clear entities and references: investigations own
optional evidence, findings, and timeline events; evidence has analysis runs;
analysis runs return zero or more indicators. Queries commonly join a case to
its evidence or findings and aggregate counts by case. A relational database
can enforce those references and prevent records from pointing at nonexistent
parents.

Referential integrity is especially important for forensic work. An evidence
item must keep its case association, an analysis must reference an existing
evidence record, and findings and timeline events must not silently refer to a
misspelled or deleted case. The schema keeps the current optional case links
nullable where the application permits unlinked records.

## PostgreSQL benefits for this workload

- Foreign-key, unique, check, and not-null constraints protect records even
  when data is inserted outside the web form.
- Transactions group related writes, such as an analysis run and its
  indicators, so a partial result is not committed.
- Joins and `GROUP BY` queries support the dashboard, case review, and reports.
- Indexes on foreign keys and timeline timestamps help common joins and
  chronological reads as the workspace grows.
- PostgreSQL can support concurrent users and larger datasets more comfortably
  than one local SQLite file.

## Migration considerations

The existing schema is small and relational, so its five tables and keys map
cleanly. The migration preserves case IDs, integer IDs, text timestamps, status
values, nullable case links, and evidence SHA-256 metadata. It also migrates the
legacy `analysis_runs.indicators_json` array into normalized
`analysis_indicators` rows. Evidence bytes are separate from the database, so
the migration verifies each source file's SHA-256 and copies it to the selected
destination evidence directory.

The migration command refuses a populated PostgreSQL target, preserves the
SQLite source, and checks row counts. Back up both the SQLite file and evidence
directory before running it. If no PostgreSQL server or URL is available, the
SQLite fallback remains the runnable configuration.
