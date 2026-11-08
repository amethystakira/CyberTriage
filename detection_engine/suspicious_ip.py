"""Simple IP reputation heuristics; production deployments should use vetted feeds."""
import ipaddress

def identify_suspicious_ips(events, denylist=None):
    denylist = set(denylist or [])
    counts = {}
    for event in events:
        ip = event.get("source_ip")
        if not ip:
            continue
        try:
            parsed = ipaddress.ip_address(ip)
        except ValueError:
            continue
        item = counts.setdefault(ip, {"source_ip": ip, "events": 0, "private": parsed.is_private})
        item["events"] += 1
        item["denylisted"] = ip in denylist
    return [
        {**item, "severity": "High" if item.get("denylisted") else ("Info" if item["private"] else "Review")}
        for item in counts.values()
    ]
