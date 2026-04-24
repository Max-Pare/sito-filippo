from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import Flask, current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    patient_name TEXT NOT NULL,
    visit_type TEXT NOT NULL,
    patient_email TEXT NOT NULL DEFAULT '',
    patient_phone TEXT NOT NULL,
    patient_notes TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_appointments_created_at ON appointments (created_at);
"""

LEGACY_COLUMNS = {
    "date_received",
    "patient_name",
    "visit_type",
    "patient_email",
    "patient_phone",
    "patient_notes",
}
CURRENT_COLUMNS = {
    "created_at",
    "patient_name",
    "visit_type",
    "patient_email",
    "patient_phone",
    "patient_notes",
}


def init_storage(app: Flask) -> None:
    database_path = Path(app.config["DATABASE_PATH"])
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(database_path) as connection:
        _configure_sqlite(connection, app.config["SQLITE_JOURNAL_MODE"])
        _migrate_legacy_table(connection)
        connection.executescript(SCHEMA)

    app.teardown_appcontext(close_db)


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        connection = sqlite3.connect(current_app.config["DATABASE_PATH"])
        connection.row_factory = sqlite3.Row
        _configure_sqlite(connection, current_app.config["SQLITE_JOURNAL_MODE"])
        g.db = connection
    return g.db


def close_db(_error: Exception | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def save_appointment(submission) -> None:
    database = get_db()
    database.execute(
        """
        INSERT INTO appointments (
            created_at,
            patient_name,
            visit_type,
            patient_email,
            patient_phone,
            patient_notes
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            submission.created_at,
            submission.patient_name,
            submission.visit_type,
            submission.patient_email,
            submission.patient_phone,
            submission.patient_notes,
        ),
    )
    database.commit()


def _configure_sqlite(connection: sqlite3.Connection, journal_mode: str) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(f"PRAGMA journal_mode = {journal_mode}")
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.execute("PRAGMA busy_timeout = 5000")


def _migrate_legacy_table(connection: sqlite3.Connection) -> None:
    table_names = {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }

    if "appointments" in table_names and _table_columns(connection, "appointments") >= CURRENT_COLUMNS:
        return

    legacy_table = _find_legacy_table(connection, table_names)
    if legacy_table is None:
        return

    if legacy_table == "appointments":
        legacy_table = "appointments_legacy"
        connection.execute('ALTER TABLE "appointments" RENAME TO "appointments_legacy"')

    connection.executescript(SCHEMA)
    connection.execute(
        f"""
        INSERT INTO appointments (
            created_at,
            patient_name,
            visit_type,
            patient_email,
            patient_phone,
            patient_notes
        )
        SELECT
            COALESCE(date_received, ''),
            COALESCE(patient_name, ''),
            COALESCE(visit_type, ''),
            COALESCE(patient_email, ''),
            COALESCE(patient_phone, ''),
            COALESCE(patient_notes, '')
        FROM {_quote_identifier(legacy_table)}
        """
    )
    connection.commit()


def _find_legacy_table(connection: sqlite3.Connection, table_names: set[str]) -> str | None:
    for table_name in sorted(table_names):
        if _table_columns(connection, table_name) >= LEGACY_COLUMNS:
            return table_name
    return None


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({_quote_identifier(table_name)})").fetchall()
    return {row[1] for row in rows}


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'
