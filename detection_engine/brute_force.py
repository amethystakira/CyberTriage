"""Rule-based brute-force detection over normalized authentication events."""
from collections import defaultdict

def detect_brute_force(events, threshold=5, window_minutes=10):
    """Flag source IPs with >= threshold failed logins in a rolling time window."""
    grouped = defaultdict(list)
    for event in events:
        if event.get("event") == "failed_login" and event.get("source_ip"):
            grouped[event["source_ip"]].append(event)
    findings = []
    # TODO: implement sliding window logic
    for ip, rows in grouped.items():
        if len(rows) >= threshold:
            findings.append({
                "type": "brute_force",
                "source_ip": ip,
                "failed_attempts": len(rows),
                "severity": "High",
                "description": f"{len(rows)} failed logins from {ip}",
            })
    return findings
