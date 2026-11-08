"""Transparent weighted severity scoring for generated detection findings."""

def score_findings(findings):
    score = 0
    for finding in findings:
        kind = finding.get("type")
        if kind == "brute_force":
            score += min(60, 15 + 5 * int(finding.get("failed_attempts", 0)))
        elif kind == "suspicious_ip":
            score += 25
        else:
            score += 5
    score = min(score, 100)
    severity = "Critical" if score >= 80 else "High" if score >= 50 else "Medium" if score >= 20 else "Low"
    return {"risk_score": score, "severity": severity}
