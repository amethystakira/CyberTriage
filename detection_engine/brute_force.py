"""Rule-based brute-force detection over normalized authentication events."""
from collections import defaultdict
from datetime import datetime

def detect_brute_force(events, threshold=5, window_minutes=10):
    """Flag source IPs with >= threshold failed logins in a rolling time window."""
    grouped = defaultdict(list)
    for event in events:
        if event.get("event") == "failed_login" and event.get("source_ip"):
            grouped[event["source_ip"]].append(event)
    findings = []
    for ip, rows in grouped.items():
        rows = sorted(rows, key=lambda x: x.get("timestamp") or "")
        for start, first in enumerate(rows):
            if not first.get("timestamp"):
                continue
            try:
                t0 = datetime.fromisoformat(first["timestamp"])
            except ValueError:
                continue
            matched = []
            for row in rows[start:]:
                try:
                    t1 = datetime.fromisoformat(row["timestamp"])
                except (ValueError, TypeError):
                    continue
                if (t1 - t0).total_seconds() <= window_minutes * 60:
                    matched.append(row)
                else:
                    break
            if len(matched) >= threshold:
                findings.append({
                    "type": "brute_force",
                    "source_ip": ip,
                    "failed_attempts": len(matched),
                    "window_minutes": window_minutes,
                    "severity": "High" if len(matched) < threshold * 2 else "Critical",
                    "description": f"{len(matched)} failed logins from {ip} within {window_minutes} minutes",
                })
                break
    return findings

# Note: events missing timestamps are explicitly skipped above to prevent
# fromisoformat crashes on None values – edge case caught during local testing.
