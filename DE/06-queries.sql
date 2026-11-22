-- Run on a disposable database. The transaction is rolled back at the end,
-- including the INSERT, UPDATE, and DELETE demonstration statements.
BEGIN;

-- Query 1 — INSERT: create a synthetic investigation.
-- Use case: demonstrate creating a case; expected: one row inserted.
INSERT INTO investigations (case_id, name, investigator, date, status, severity)
VALUES ('CASE-DE-QUERY-001', 'Query demonstration case', 'SQL Analyst',
        '21 Nov 2026', 'Pending', 'Medium')
ON CONFLICT (case_id) DO NOTHING;

-- Query 2 — INSERT: attach synthetic evidence to that investigation.
-- Use case: demonstrate evidence metadata and its foreign key; expected: one row.
INSERT INTO evidence
    (case_id, original_name, stored_name, sha256, size_bytes, uploaded_at)
VALUES
    ('CASE-DE-QUERY-001', 'query-evidence.txt', 'de-query-evidence.txt',
     'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 0,
     '2026-11-21T10:00:00+00:00')
ON CONFLICT DO NOTHING;

-- Query 3 — SELECT with WHERE: retrieve one investigation by its business key.
-- Expected: CASE-DE-QUERY-001 and its demonstration details.
SELECT case_id, name, investigator, status, severity
FROM investigations
WHERE case_id = 'CASE-DE-QUERY-001';

-- Query 4 — SELECT with ORDER BY: list recently inserted investigations.
-- row_id order is used because the existing date column is display-formatted text.
-- Expected: up to five rows, newest inserted row_id first.
SELECT row_id, case_id, name, date, status
FROM investigations
ORDER BY row_id DESC
LIMIT 5;

-- Query 5 — INNER JOIN: display evidence with its investigation.
-- Expected: the synthetic query-evidence row and case details.
SELECT e.evidence_id, e.original_name, e.sha256, e.size_bytes,
       i.case_id, i.name AS investigation_name
FROM evidence e
INNER JOIN investigations i ON i.case_id = e.case_id
WHERE e.case_id = 'CASE-DE-QUERY-001';

-- Query 6 — JOIN: display findings with their investigation details.
-- Expected: all findings linked to CASE-DE-QUERY-001 (none in this query transaction).
SELECT f.finding_id, f.title, f.severity, f.status,
       i.case_id, i.name AS investigation_name
FROM findings f
INNER JOIN investigations i ON i.case_id = f.case_id
WHERE i.case_id = 'CASE-DE-QUERY-001'
ORDER BY f.finding_id;

-- Query 7 — COUNT and GROUP BY: count evidence files for each investigation.
-- Expected: one row per investigation, including cases with zero evidence.
SELECT i.case_id, i.name, COUNT(e.evidence_id) AS evidence_count
FROM investigations i
LEFT JOIN evidence e ON e.case_id = i.case_id
GROUP BY i.case_id, i.name
ORDER BY i.case_id;

-- Query 8 — GROUP BY and HAVING: find cases with multiple findings.
-- Expected: cases with more than one finding; no row is created for the test case.
SELECT i.case_id, i.name, COUNT(f.finding_id) AS finding_count
FROM investigations i
JOIN findings f ON f.case_id = i.case_id
GROUP BY i.case_id, i.name
HAVING COUNT(f.finding_id) > 1
ORDER BY finding_count DESC, i.case_id;

-- Query 9 — UPDATE: change the demonstration investigation status.
-- Expected: the following SELECT reports Analyzing.
UPDATE investigations
SET status = 'Analyzing'
WHERE case_id = 'CASE-DE-QUERY-001';
SELECT case_id, status
FROM investigations
WHERE case_id = 'CASE-DE-QUERY-001';

-- Query 10 — DELETE: remove only the synthetic evidence row inserted above.
-- Expected: one returned row; transaction rollback restores it afterwards.
DELETE FROM evidence
WHERE case_id = 'CASE-DE-QUERY-001'
  AND stored_name = 'de-query-evidence.txt'
RETURNING evidence_id, stored_name;

-- Query 11 — Subquery: find investigations with high or critical findings.
-- Expected: cases containing at least one High or Critical finding.
SELECT case_id, name, status, severity
FROM investigations
WHERE case_id IN (
    SELECT case_id
    FROM findings
    WHERE severity IN ('High', 'Critical') AND case_id IS NOT NULL
)
ORDER BY case_id;

-- Query 12 — Aggregate: count analysis runs per evidence item.
-- Expected: one row per evidence item, including evidence never analyzed.
SELECT e.evidence_id, e.original_name, COUNT(r.run_id) AS analysis_run_count
FROM evidence e
LEFT JOIN analysis_runs r ON r.evidence_id = e.evidence_id
GROUP BY e.evidence_id, e.original_name
ORDER BY e.evidence_id;

ROLLBACK;
