-- Synthetic CyberTriage records for a fresh schema or disposable database.
-- The matching evidence fixture is DE/sample-evidence/de-auth-sample.log.

BEGIN;

INSERT INTO investigations (case_id, name, investigator, date, status, severity)
VALUES
    ('CASE-DE-101', 'Synthetic repeated login review', 'Example Analyst', '19 Nov 2026', 'Analyzing', 'High'),
    ('CASE-DE-102', 'Synthetic endpoint review', 'Example Analyst', '20 Nov 2026', 'Pending', 'Medium')
ON CONFLICT (case_id) DO NOTHING;

INSERT INTO evidence
    (case_id, original_name, stored_name, sha256, size_bytes, uploaded_at)
VALUES
    ('CASE-DE-101', 'de-auth-sample.log', 'de-auth-sample.log',
     '28f856513d954abdd6700056635c86c7d4664103df601e336889a298444a4a28', 166,
     '2026-11-19T10:15:00+00:00')
ON CONFLICT DO NOTHING;

INSERT INTO findings (case_id, title, description, severity, status, created_at)
SELECT 'CASE-DE-101', 'Repeated failed login attempts',
       'Two synthetic authentication failures share a source address.',
       'Medium', 'Open', '2026-11-19T10:20:00+00:00'
WHERE NOT EXISTS (
    SELECT 1 FROM findings
    WHERE case_id = 'CASE-DE-101' AND title = 'Repeated failed login attempts'
);

INSERT INTO findings (case_id, title, description, severity, status, created_at)
SELECT 'CASE-DE-102', 'Endpoint review pending',
       'Synthetic case is waiting for evidence review.',
       'Low', 'Open', '2026-11-20T09:00:00+00:00'
WHERE NOT EXISTS (
    SELECT 1 FROM findings
    WHERE case_id = 'CASE-DE-102' AND title = 'Endpoint review pending'
);

INSERT INTO analysis_runs (evidence_id, summary, created_at)
SELECT e.evidence_id, 'Synthetic auth log contains repeated failure indicators.',
       '2026-11-19T10:30:00+00:00'
FROM evidence e
WHERE e.stored_name = 'de-auth-sample.log'
  AND NOT EXISTS (
      SELECT 1 FROM analysis_runs r
      WHERE r.evidence_id = e.evidence_id
        AND r.summary = 'Synthetic auth log contains repeated failure indicators.'
  );

INSERT INTO analysis_indicators (run_id, ordinal, indicator_type, value, reason)
SELECT r.run_id, 0, 'IPv4 address', '203.0.113.10',
       'Address appears in the synthetic authentication log.'
FROM analysis_runs r
JOIN evidence e ON e.evidence_id = r.evidence_id
WHERE e.stored_name = 'de-auth-sample.log'
  AND r.summary = 'Synthetic auth log contains repeated failure indicators.'
  AND NOT EXISTS (
      SELECT 1 FROM analysis_indicators i WHERE i.run_id = r.run_id AND i.ordinal = 0
  );

INSERT INTO timeline_events (case_id, event_type, description, occurred_at)
SELECT 'CASE-DE-101', 'Evidence added', 'Added evidence file: de-auth-sample.log',
       '2026-11-19T10:15:00+00:00'
WHERE NOT EXISTS (
    SELECT 1 FROM timeline_events
    WHERE case_id = 'CASE-DE-101' AND event_type = 'Evidence added'
      AND description = 'Added evidence file: de-auth-sample.log'
);

INSERT INTO timeline_events (case_id, event_type, description, occurred_at)
SELECT 'CASE-DE-101', 'Evidence analyzed', 'Analyzed evidence file: de-auth-sample.log',
       '2026-11-19T10:30:00+00:00'
WHERE NOT EXISTS (
    SELECT 1 FROM timeline_events
    WHERE case_id = 'CASE-DE-101' AND event_type = 'Evidence analyzed'
      AND description = 'Analyzed evidence file: de-auth-sample.log'
);

COMMIT;
