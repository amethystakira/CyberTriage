"""Build a chronological, normalized forensic event timeline."""

def build_timeline(events, findings=None):
    timeline = [{
        "timestamp": e.get("timestamp"),
        "category": e.get("event", "unknown"),
        "description": f"{e.get('event', 'event')} for {e.get('username', 'unknown user')} from {e.get('source_ip', 'unknown IP')}",
        "source_ip": e.get("source_ip"),
    } for e in events]
    for finding in findings or []:
        timeline.append({
            "timestamp": None,
            "category": "detection",
            "description": finding.get("description", finding.get("type", "Detection finding")),
            "source_ip": finding.get("source_ip"),
        })
    return sorted(timeline, key=lambda x: x.get("timestamp") or "")
