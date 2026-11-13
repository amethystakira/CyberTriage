"""CyberTriage standalone log-analysis and detection package.

Modules:
  log_parser       – parse auth log lines to normalized event dicts
  brute_force      – rolling-window brute-force detector
  suspicious_ip    – IP heuristics and denylist checking
  threat_scoring   – weighted risk scoring (0-100)
  timeline         – forensic event timeline builder
  report_generator – JSON report generator
"""
