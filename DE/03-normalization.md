# Normalization

This review uses the five tables and actual SQLite records inspected in
`backend/cybertriage.db`, then describes the normalized schema now used by the
backend. The original schema had one semi-structured exception:
`analysis_runs.indicators_json` stored a list of indicators in one text field.
The startup migration moves each list member into `analysis_indicators`; the
API still returns the same JSON-shaped `indicators` array to React.

## Functional dependencies and keys

- `investigations`: `row_id -> case_id, name, investigator, date, status,
  severity`. Because `case_id` is unique, it is also a candidate key and
  determines the other investigation attributes.
- `evidence`: `evidence_id -> case_id, original_name, stored_name, sha256,
  size_bytes, uploaded_at`. `stored_name` is unique because it names the
  stored file. The SHA-256 value is not unique; identical content may be
  collected as separate evidence records.
- `findings`: `finding_id -> case_id, title, description, severity, status,
  created_at`.
- `analysis_runs`: `run_id -> evidence_id, summary, created_at`.
- `analysis_indicators`: `indicator_id -> run_id, ordinal, indicator_type,
  value, reason`; the candidate key `(run_id, ordinal)` also identifies one
  ordered indicator within a run.
- `timeline_events`: `event_id -> case_id, event_type, description,
  occurred_at`.

## First Normal Form (1NF)

The ordinary columns hold one scalar value per row. In the original database,
`indicators_json` contained a JSON array, so it was not atomic in the logical
relational sense even though SQLite stored it as one text value. The migration
removes that column and writes one row per indicator into
`analysis_indicators`, with `ordinal` retaining the original order. Empty
indicator arrays become an analysis run with zero child rows.

The conceptual flat form below illustrates the repeating data from the actual
sample case; it is a joined report shape, not an extra stored table:

| case_id | investigation name | evidence name | indicator |
|---|---|---|---|
| CASE-2026-001 | Northstar payroll ransomware response | payroll-host-memory-notes.txt | 198.51.100.24 |
| CASE-2026-001 | Northstar payroll ransomware response | payroll-host-memory-notes.txt | powershell -enc |

The final tables keep each indicator in its own row and store investigation,
evidence, and analysis-run attributes once.

## Second Normal Form (2NF)

There are no partial functional dependencies in the entity tables. Each
primary key is a single column, so a non-key attribute cannot depend on only a
proper subset of that primary key. `analysis_indicators` also has a composite
candidate key `(run_id, ordinal)`; the type, value, and reason describe the
indicator at that position and require the pair. `ordinal` by itself does not
identify an indicator across runs.

## Third Normal Form (3NF)

No non-key attribute is stored in a child table when it depends on a different
non-key attribute. For example, case name and investigator are kept in
`investigations`, not repeated in `evidence`, `findings`, or
`timeline_events`; routes retrieve them with joins. Evidence filenames and
hashes are not copied into analysis runs. Indicator details belong to
`analysis_indicators`, while the run's evidence, summary, and timestamp belong
to `analysis_runs`.

The current design does not add investigator, severity, or event-type lookup
tables because the app has no separate attributes or workflows for those
entities. Fixed status and severity values are guarded by checks and API input
validation instead.

## Intentional design decisions

- `investigations.case_id` remains a unique business key because current API
  routes and foreign keys use it.
- Case links in evidence, findings, and timeline events remain nullable to
  preserve the app's existing “unlinked” workflow.
- Timestamps and the display-formatted investigation date remain text to
  preserve existing API values. A future date/time migration should define
  timezone and formatting behavior explicitly.
- Evidence bytes remain files; the relational record stores their generated
  filename, size, and hash.
