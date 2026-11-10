import unittest
from detection_engine.log_parser import parse_auth_log
from detection_engine.brute_force import detect_brute_force
from detection_engine.threat_scoring import score_findings

class DetectionTests(unittest.TestCase):
    def test_parser_extracts_failed_login(self):
        events = parse_auth_log("Nov  6 10:00:00 host sshd: Failed password for root from 203.0.113.10 port 22 ssh2", year=2026)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "failed_login")
        self.assertEqual(events[0]["source_ip"], "203.0.113.10")

    def test_brute_force_threshold(self):
        events = []
        for minute in range(6):
            events.append({
                "event": "failed_login",
                "source_ip": "203.0.113.10",
                "timestamp": f"2026-11-06T10:{minute:02d}:00+00:00",
            })
        self.assertEqual(len(detect_brute_force(events, threshold=5)), 1)

    def test_risk_score_is_bounded(self):
        result = score_findings([{"type": "brute_force", "failed_attempts": 20}])
        self.assertGreaterEqual(result["risk_score"], 0)
        self.assertLessEqual(result["risk_score"], 100)

if __name__ == "__main__":
    unittest.main()
