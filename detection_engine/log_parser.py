\
"""Parse common auth-log lines into normalized event dictionaries."""
from __future__ import annotations
import re
from datetime import datetime, timezone

PATTERNS = [
    re.compile(r"(?P<ts>\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2}).*Failed password for (?:invalid user )?(?P<user>\S+) from (?P<ip>\d{1,3}(?:\.\d{1,3}){3})"),
    re.compile(r"(?P<ts>\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2}).*Accepted password for (?P<user>\S+) from (?P<ip>\d{1,3}(?:\.\d{1,3}){3})"),
]

def parse_auth_line(line: str, year: int | None = None) -> dict | None:
    """Return a normalized event, or None for unsupported lines."""
    for pattern in PATTERNS:
        match = pattern.search(line)
        if not match:
            continue
        data = match.groupdict()
        try:
            parsed = datetime.strptime(data["ts"], "%b %d %H:%M:%S")
            parsed = parsed.replace(year=year or datetime.now().year, tzinfo=timezone.utc)
            timestamp = parsed.isoformat()
        except ValueError:
            timestamp = None
        return {
            "timestamp": timestamp,
            "event": "failed_login" if "Failed password" in line else "successful_login",
            "username": data["user"],
            "source_ip": data["ip"],
            "raw": line.rstrip("\n"),
        }
    return None

def parse_auth_log(text: str, year: int | None = None) -> list[dict]:
    return [event for line in text.splitlines() if (event := parse_auth_line(line, year))]
