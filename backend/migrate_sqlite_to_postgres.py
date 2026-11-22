"""Copy an existing CyberTriage SQLite workspace into PostgreSQL."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3

from sqlalchemy import text

from backend.app.database import (
    DEFAULT_SQLITE_PATH,
    DATABASE_URL,
    PROJECT_ROOT,
    analysis_indicators,
    analysis_runs,
    engine,
    evidence,
    findings,
    initialize_schema,
    investigations,
    metadata,
    timeline_events,
)


TABLES = (
    investigations,
    evidence,
    findings,
    analysis_runs,
    analysis_indicators,
    timeline_events,
)
ID_COLUMNS = {
    "investigations": "row_id",
    "evidence": "evidence_id",
    "findings": "finding_id",
    "analysis_runs": "run_id",
    "analysis_indicators": "indicator_id",
    "timeline_events": "event_id",
}


def _indicator_values(run_id, raw_json):
    values = json.loads(raw_json or "[]")
    if not isinstance(values, list):
        raise ValueError(f"analysis run {run_id} indicators_json is not an array")
    result = []
    for ordinal, item in enumerate(values):
        if not isinstance(item, dict):
            raise ValueError(f"analysis run {run_id} contains a non-object indicator")
        result.append(
            {
                "run_id": run_id,
                "ordinal": ordinal,
                "indicator_type": str(item.get("type", "Unknown")),
                "value": str(item.get("value", "")),
                "reason": str(item.get("reason", "")),
            }
        )
    return result


def _copy_evidence_files(rows, source_dir, destination_dir):
    created = []
    destination_dir.mkdir(parents=True, exist_ok=True)
    try:
        for row in rows:
            stored_name = row["stored_name"]
            if Path(stored_name).name != stored_name:
                raise ValueError(f"Unsafe stored evidence filename: {stored_name}")
            source = source_dir / stored_name
            destination = destination_dir / stored_name
            if not source.is_file():
                raise FileNotFoundError(f"Evidence file is missing: {source}")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            if digest != row["sha256"]:
                raise ValueError(f"Evidence hash does not match the database: {stored_name}")
            if destination.exists():
                existing_digest = hashlib.sha256(destination.read_bytes()).hexdigest()
                if existing_digest != digest:
                    raise ValueError(f"Destination evidence file conflicts: {stored_name}")
                continue
            if source.resolve() == destination.resolve():
                continue
            shutil.copy2(source, destination)
            created.append(destination)
        return created
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise


def migrate():
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Set DATABASE_URL to a PostgreSQL URL before running this script.")

    source_path = Path(os.getenv("SQLITE_SOURCE_PATH", str(DEFAULT_SQLITE_PATH))).resolve()
    source_evidence_dir = Path(
        os.getenv("SQLITE_SOURCE_EVIDENCE_DIR", str(PROJECT_ROOT / "evidence"))
    ).resolve()
    destination_evidence_dir = Path(
        os.getenv("CYBERTRIAGE_EVIDENCE_DIR", str(PROJECT_ROOT / "evidence"))
    ).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"SQLite source database not found: {source_path}")

    uri = source_path.as_uri() + "?mode=ro"
    source = sqlite3.connect(uri, uri=True)
    source.row_factory = sqlite3.Row
    created_files = []
    try:
        source_tables = {
            row[0]
            for row in source.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        required = {"investigations", "evidence", "findings", "analysis_runs", "timeline_events"}
        missing = required - source_tables
        if missing:
            raise ValueError(f"SQLite source is missing tables: {', '.join(sorted(missing))}")

        rows = {}
        for table in (investigations, evidence, findings, analysis_runs, timeline_events):
            rows[table.name] = [
                dict(row)
                for row in source.execute(
                    f'SELECT * FROM "{table.name}" ORDER BY "{ID_COLUMNS[table.name]}"'
                )
            ]
        legacy_analysis = bool(rows["analysis_runs"] and "indicators_json" in rows["analysis_runs"][0])
        if "analysis_indicators" in source_tables:
            rows["analysis_indicators"] = [
                dict(row)
                for row in source.execute(
                    "SELECT * FROM analysis_indicators ORDER BY indicator_id"
                )
            ]
        else:
            rows["analysis_indicators"] = []
            if legacy_analysis:
                for run in rows["analysis_runs"]:
                    rows["analysis_indicators"].extend(
                        _indicator_values(run["run_id"], run["indicators_json"])
                    )
                    del run["indicators_json"]

        created_files = _copy_evidence_files(
            rows["evidence"], source_evidence_dir, destination_evidence_dir
        )
        initialize_schema()

        with engine.begin() as target:
            nonempty = [
                table.name
                for table in TABLES
                if target.execute(text(f'SELECT COUNT(*) FROM "{table.name}"')).scalar_one()
            ]
            if nonempty:
                raise RuntimeError(
                    "PostgreSQL target must be empty; found existing rows in: "
                    + ", ".join(nonempty)
                )

            for table in TABLES:
                values = rows[table.name]
                if values:
                    target.execute(table.insert(), values)

            for table_name, id_column in ID_COLUMNS.items():
                target.execute(
                    text(
                        "SELECT setval(pg_get_serial_sequence(:table_name, :id_column), "
                        ":last_value, :is_called)"
                    ),
                    {
                        "table_name": table_name,
                        "id_column": id_column,
                        "last_value": max(
                            (row[id_column] for row in rows[table_name]), default=1
                        ),
                        "is_called": bool(rows[table_name]),
                    },
                )

            target_counts = {
                table.name: target.execute(
                    text(f'SELECT COUNT(*) FROM "{table.name}"')
                ).scalar_one()
                for table in TABLES
            }
            expected_counts = {name: len(values) for name, values in rows.items()}
            if target_counts != expected_counts:
                raise RuntimeError(
                    f"Post-migration row count mismatch: expected {expected_counts}, "
                    f"received {target_counts}"
                )
    except Exception:
        for path in created_files:
            path.unlink(missing_ok=True)
        raise
    finally:
        source.close()

    print("Migration completed. The SQLite source was left unchanged.")
    for table_name, count in target_counts.items():
        print(f"{table_name}: {count} rows")
    print(f"Evidence files copied: {len(created_files)}")
    print("DATABASE_URL target:", DATABASE_URL.split("@")[-1])


if __name__ == "__main__":
    migrate()
