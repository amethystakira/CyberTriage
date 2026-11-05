# Member 3 – Digital Forensics Detection Engine

## Ownership
This package owns authentication-log parsing, brute-force detection, suspicious-IP heuristics,
risk scoring, forensic timelines, and JSON report generation.

## Run a quick analysis
From this folder:
```bash
python3 - <<'PY'
from pathlib import Path
from detection_engine.log_parser import parse_auth_log
from detection_engine.brute_force import detect_brute_force
from detection_engine.suspicious_ip import identify_suspicious_ips
from detection_engine.report_generator import generate_report

raw = Path("sample_data/synthetic_auth_activity.log").read_text()
events = parse_auth_log(raw)
findings = detect_brute_force(events) + identify_suspicious_ips(events)
print(generate_report(events, findings))
PY
```

## Git ownership
Use branch `feature/detection-engine`. Own `detection_engine/`, detection-specific tests,
and the sample authentication dataset. Coordinate API integration with the backend owner.
