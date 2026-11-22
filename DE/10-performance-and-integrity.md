# Performance and data integrity

## Constraints

- Every table has a primary key. `investigations.case_id` is unique and is the
  business key used by existing routes and child references.
- `evidence.stored_name` is unique so two records cannot point to the same
  stored file path accidentally. `sha256` is not unique because separate
  collections may contain identical bytes.
- `analysis_indicators(run_id, ordinal)` is unique, preserving one ordered
  indicator at each position in a run.
- Required fields use `NOT NULL`. Evidence, findings, and timeline events may
  have a null case link to preserve the existing unlinked workflow.
- Foreign keys connect optional case links, analysis runs to evidence, and
  indicators to runs. No cascading delete is configured; parent deletion must
  not silently remove forensic history.
- Checks constrain case/finding statuses, accepted severities, nonnegative
  evidence size, 64-character SHA-256 values, and nonnegative indicator order.
- FastAPI validates allowed status/severity values and verifies referenced
  cases/evidence before writing.

The original SQLite schema predates several database-level checks. SQLAlchemy
adds indexes on existing workspaces; application validation remains active.
Fresh SQLite and PostgreSQL schemas receive the declared checks. The
PostgreSQL schema is in `04-database-schema.sql`.

## Duplicate and missing data handling

Case IDs have a unique constraint. Demo seed inserts are keyed by stable case,
evidence hash/name, finding title, analysis summary, or event description so a
restart does not duplicate the demonstration records. Evidence can be unlinked
from a case, but an analysis run cannot be unlinked from its source evidence.
The migration refuses missing evidence files or hash mismatches instead of
copying incomplete evidence metadata.

## Indexes

Indexes cover evidence and findings by case, analysis runs by evidence,
indicators by run, and timeline events by case/time. They support the joins and
chronological filters used by `/api/evidence`, `/api/findings`, `/api/analysis`,
`/api/timeline`, and reports. `investigations.case_id` and evidence stored
names are unique-indexed. SQLite's original database had no explicit foreign
key indexes; SQLAlchemy creates these indexes on application startup.

## Query and scale considerations

The dashboard/report endpoints currently load workspace collections and
compose them in Python, which is suitable for this small local workspace but
may transfer more rows than needed as data grows. The joins and `GROUP BY`
examples in `06-queries.sql` show how aggregate work can move into SQL.
PostgreSQL supports concurrent clients more naturally than one SQLite file.
Evidence bytes remain outside the database, so storage capacity and backup
must include the configured evidence directory as well as the database.

## Transaction safety

Investigation creation and its timeline event share one transaction. Evidence
metadata and its timeline event share a transaction, with file cleanup on
failure. Analysis runs, ordered indicators, generated findings, and timeline
events share a transaction. The migration uses one PostgreSQL transaction for
database rows, verifies counts before commit, verifies file hashes, and never
modifies the SQLite source.
