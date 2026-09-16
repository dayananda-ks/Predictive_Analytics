from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS screening_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    input_data TEXT NOT NULL,
    t21_probability REAL NOT NULL,
    t21_risk_level TEXT NOT NULL,
    t18_probability REAL NOT NULL,
    t18_risk_level TEXT NOT NULL,
    model_name TEXT NOT NULL
)
"""


def _connect(database_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(database_path))
    connection.row_factory = sqlite3.Row
    return connection


def init_db(database_path: str | Path) -> None:
    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(database_path) as connection:
        connection.execute(SCHEMA)
        connection.commit()


@contextmanager
def get_connection(database_path: str | Path):
    connection = _connect(database_path)
    try:
        yield connection
    finally:
        connection.close()


def add_history_record(database_path: str | Path, payload: dict[str, Any]) -> int:
    timestamp = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
    input_data = json.dumps(payload["input_data"], ensure_ascii=True)
    with get_connection(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO screening_history (
                timestamp, input_data, t21_probability, t21_risk_level,
                t18_probability, t18_risk_level, model_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                input_data,
                float(payload["t21_probability"]),
                payload["t21_risk_level"],
                float(payload["t18_probability"]),
                payload["t18_risk_level"],
                payload["model_name"],
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_history_records(database_path: str | Path) -> list[dict[str, Any]]:
    with get_connection(database_path) as connection:
        rows = connection.execute(
            "SELECT id, timestamp, input_data, t21_probability, t21_risk_level, t18_probability, t18_risk_level, model_name FROM screening_history ORDER BY id DESC"
        ).fetchall()
    records: list[dict[str, Any]] = []
    for row in rows:
        records.append(
            {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "input_data": json.loads(row["input_data"]),
                "t21_probability": row["t21_probability"],
                "t21_risk_level": row["t21_risk_level"],
                "t18_probability": row["t18_probability"],
                "t18_risk_level": row["t18_risk_level"],
                "model_name": row["model_name"],
            }
        )
    return records


def delete_history_record(database_path: str | Path, record_id: int) -> bool:
    with get_connection(database_path) as connection:
        cursor = connection.execute("DELETE FROM screening_history WHERE id = ?", (int(record_id),))
        connection.commit()
        return cursor.rowcount > 0
