"""Create a JSON-serializable forensic analysis report."""
from .threat_scoring import score_findings
from .timeline import build_timeline

def generate_report(events, findings):
    return {
        "event_count": len(events),
        "finding_count": len(findings),
        **score_findings(findings),
        "findings": findings,
        "timeline": build_timeline(events, findings),
    }
