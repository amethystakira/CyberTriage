"""Shared SQLAlchemy schema and database selection for CyberTriage."""

from contextlib import contextmanager
import os
from pathlib import Path
import re

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    inspect,
    text,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "backend" / "cybertriage.db"


def _database_url():
    value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        return "sqlite:///" + DEFAULT_SQLITE_PATH.as_posix()
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql+psycopg://") or value.startswith("sqlite:///"):
        return value
    raise ValueError("DATABASE_URL must use SQLite or PostgreSQL with psycopg.")


DATABASE_URL = _database_url()
IS_SQLITE = DATABASE_URL.startswith("sqlite:")
engine_options = {"pool_pre_ping": True}
if IS_SQLITE:
    engine_options["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_options)

if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()


metadata = MetaData()

investigations = Table(
    "investigations",
    metadata,
    Column("row_id", Integer, primary_key=True, autoincrement=True),
    Column("case_id", Text, nullable=False, unique=True),
    Column("name", Text, nullable=False),
    Column("investigator", Text, nullable=False),
    Column("date", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("severity", Text, nullable=False),
    CheckConstraint(
        "status IN ('Pending', 'Analyzing', 'Completed')",
        name="ck_investigations_status",
    ),
    CheckConstraint(
        "severity IN ('Unassigned', 'Low', 'Medium', 'High', 'Critical')",
        name="ck_investigations_severity",
    ),
)

evidence = Table(
    "evidence",
    metadata,
    Column("evidence_id", Integer, primary_key=True, autoincrement=True),
    Column("case_id", Text, ForeignKey("investigations.case_id"), nullable=True),
    Column("original_name", Text, nullable=False),
    Column("stored_name", Text, nullable=False),
    Column("sha256", Text, nullable=False),
    Column("size_bytes", Integer, nullable=False),
    Column("uploaded_at", Text, nullable=False),
    CheckConstraint("length(sha256) = 64", name="ck_evidence_sha256_length"),
    CheckConstraint("size_bytes >= 0", name="ck_evidence_size_nonnegative"),
)

findings = Table(
    "findings",
    metadata,
    Column("finding_id", Integer, primary_key=True, autoincrement=True),
    Column("case_id", Text, ForeignKey("investigations.case_id"), nullable=True),
    Column("title", Text, nullable=False),
    Column("description", Text, nullable=False),
    Column("severity", Text, nullable=False),
    Column("status", Text, nullable=False, server_default=text("'Open'")),
    Column("created_at", Text, nullable=False),
    CheckConstraint(
        "severity IN ('Low', 'Medium', 'High', 'Critical')",
        name="ck_findings_severity",
    ),
    CheckConstraint("status IN ('Open', 'Resolved')", name="ck_findings_status"),
)

analysis_runs = Table(
    "analysis_runs",
    metadata,
    Column("run_id", Integer, primary_key=True, autoincrement=True),
    Column("evidence_id", Integer, ForeignKey("evidence.evidence_id"), nullable=False),
    Column("summary", Text, nullable=False),
    Column("created_at", Text, nullable=False),
)

analysis_indicators = Table(
    "analysis_indicators",
    metadata,
    Column("indicator_id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", Integer, ForeignKey("analysis_runs.run_id"), nullable=False),
    Column("ordinal", Integer, nullable=False),
    Column("indicator_type", Text, nullable=False),
    Column("value", Text, nullable=False),
    Column("reason", Text, nullable=False),
    UniqueConstraint("run_id", "ordinal", name="uq_analysis_indicator_order"),
    CheckConstraint("ordinal >= 0", name="ck_analysis_indicator_ordinal"),
)

timeline_events = Table(
    "timeline_events",
    metadata,
    Column("event_id", Integer, primary_key=True, autoincrement=True),
    Column("case_id", Text, ForeignKey("investigations.case_id"), nullable=True),
    Column("event_type", Text, nullable=False),
    Column("description", Text, nullable=False),
    Column("occurred_at", Text, nullable=False),
)

Index("ix_evidence_case_id", evidence.c.case_id)
Index("ux_evidence_stored_name", evidence.c.stored_name, unique=True)
Index("ix_findings_case_id", findings.c.case_id)
Index("ix_analysis_runs_evidence_id", analysis_runs.c.evidence_id)
Index("ix_analysis_indicators_run_id", analysis_indicators.c.run_id)
Index("ix_timeline_events_case_id", timeline_events.c.case_id)
Index("ix_timeline_events_occurred_at", timeline_events.c.occurred_at)


class _CompatibleRow(dict):
    """Allow existing route code to read result rows by name or position."""

    def __init__(self, mapping):
        super().__init__(mapping)
        self._values = tuple(mapping.values())

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


class _CompatibleResult:
    def __init__(self, result):
        self._result = result

    def fetchone(self):
        row = self._result.fetchone()
        return None if row is None else _CompatibleRow(row._mapping)

    def fetchall(self):
        return [_CompatibleRow(row._mapping) for row in self._result.fetchall()]


class DatabaseConnection:
    """Small qmark adapter to keep the existing SQL route code readable."""

    def __init__(self, connection):
        self._connection = connection

    def execute(self, statement, parameters=None):
        sql = str(statement).strip()
        ignore_conflicts = bool(
            re.match(r"INSERT\s+OR\s+IGNORE\s+INTO\b", sql, flags=re.IGNORECASE)
        )
        if ignore_conflicts:
            sql = re.sub(
                r"^INSERT\s+OR\s+IGNORE\s+INTO\b",
                "INSERT INTO",
                sql,
                count=1,
                flags=re.IGNORECASE,
            )

        if parameters is None:
            bound = {}
        elif isinstance(parameters, dict):
            bound = parameters
        else:
            values = tuple(parameters)
            index = 0

            def replace_placeholder(_match):
                nonlocal index
                name = f"p{index}"
                index += 1
                return f":{name}"

            sql = re.sub(r"\?", replace_placeholder, sql)
            if index != len(values):
                raise ValueError("SQL parameter count does not match placeholders.")
            bound = {f"p{position}": value for position, value in enumerate(values)}

        if ignore_conflicts:
            sql = sql.rstrip(";") + " ON CONFLICT DO NOTHING"
        return _CompatibleResult(self._connection.execute(text(sql), bound))


@contextmanager
def get_db():
    with engine.begin() as connection:
        yield DatabaseConnection(connection)


def _insert_indicators(connection, run_id, raw_json):
    import json

    indicators = json.loads(raw_json or "[]")
    if not isinstance(indicators, list):
        raise ValueError("Legacy analysis indicators must be a JSON array.")
    for ordinal, indicator in enumerate(indicators):
        if not isinstance(indicator, dict):
            raise ValueError("Legacy analysis indicator entries must be objects.")
        connection.execute(
            analysis_indicators.insert().values(
                run_id=run_id,
                ordinal=ordinal,
                indicator_type=indicator.get("type", "Unknown"),
                value=str(indicator.get("value", "")),
                reason=str(indicator.get("reason", "")),
            )
        )


def initialize_schema():
    """Create missing tables and migrate legacy JSON indicator arrays."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    has_legacy_indicators = (
        "analysis_runs" in table_names
        and "indicators_json"
        in {column["name"] for column in inspector.get_columns("analysis_runs")}
    )

    if not has_legacy_indicators:
        metadata.create_all(engine)
        return

    if IS_SQLITE:
        with engine.begin() as connection:
            legacy_rows = connection.exec_driver_sql(
                "SELECT run_id, evidence_id, summary, indicators_json, created_at "
                "FROM analysis_runs ORDER BY run_id"
            ).mappings().all()
            # SQLite carries indexes along when a table is renamed. Drop the
            # legacy index first so metadata can recreate it on the new table.
            connection.exec_driver_sql("DROP INDEX IF EXISTS ix_analysis_runs_evidence_id")
            connection.exec_driver_sql(
                "ALTER TABLE analysis_runs RENAME TO analysis_runs_legacy"
            )
            metadata.create_all(connection)
            for row in legacy_rows:
                connection.execute(
                    analysis_runs.insert().values(
                        run_id=row["run_id"],
                        evidence_id=row["evidence_id"],
                        summary=row["summary"],
                        created_at=row["created_at"],
                    )
                )
                _insert_indicators(connection, row["run_id"], row["indicators_json"])
            connection.exec_driver_sql("DROP TABLE analysis_runs_legacy")
        return

    metadata.create_all(engine)
    with engine.begin() as connection:
        legacy_rows = connection.execute(
            text(
                "SELECT run_id, indicators_json FROM analysis_runs "
                "ORDER BY run_id"
            )
        ).mappings().all()
        for row in legacy_rows:
            _insert_indicators(connection, row["run_id"], row["indicators_json"])
        connection.exec_driver_sql("ALTER TABLE analysis_runs DROP COLUMN indicators_json")
