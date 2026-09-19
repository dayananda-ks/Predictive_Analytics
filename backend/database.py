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
    user_id INTEGER,
    input_data TEXT NOT NULL,
    t21_probability REAL NOT NULL,
    t21_risk_level TEXT NOT NULL,
    t18_probability REAL NOT NULL,
    t18_risk_level TEXT NOT NULL,
    model_name TEXT NOT NULL
)

;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TEXT NOT NULL,
    last_login TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
)
;
"""


def _connect(database_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(database_path))
    connection.row_factory = sqlite3.Row
    return connection


def init_db(database_path: str | Path) -> None:
    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(database_path) as connection:
        connection.executescript(SCHEMA)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(screening_history)").fetchall()}
        if "user_id" not in columns:
            connection.execute("ALTER TABLE screening_history ADD COLUMN user_id INTEGER")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_screening_history_user_id ON screening_history(user_id)")
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
                timestamp, user_id, input_data, t21_probability, t21_risk_level,
                t18_probability, t18_risk_level, model_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                payload.get("user_id"),
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


def list_history_records(database_path: str | Path, user_id: int | None = None) -> list[dict[str, Any]]:
    with get_connection(database_path) as connection:
        if user_id is None:
            rows = connection.execute(
                "SELECT id, timestamp, user_id, input_data, t21_probability, t21_risk_level, t18_probability, t18_risk_level, model_name FROM screening_history ORDER BY id DESC"
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT id, timestamp, user_id, input_data, t21_probability, t21_risk_level, t18_probability, t18_risk_level, model_name FROM screening_history WHERE user_id = ? ORDER BY id DESC",
                (int(user_id),),
            ).fetchall()
    records: list[dict[str, Any]] = []
    for row in rows:
        records.append(
            {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "user_id": row["user_id"],
                "input_data": json.loads(row["input_data"]),
                "t21_probability": row["t21_probability"],
                "t21_risk_level": row["t21_risk_level"],
                "t18_probability": row["t18_probability"],
                "t18_risk_level": row["t18_risk_level"],
                "model_name": row["model_name"],
            }
        )
    return records


def delete_history_record(database_path: str | Path, record_id: int, user_id: int | None = None) -> bool:
    with get_connection(database_path) as connection:
        if user_id is None:
            cursor = connection.execute("DELETE FROM screening_history WHERE id = ?", (int(record_id),))
        else:
            cursor = connection.execute(
                "DELETE FROM screening_history WHERE id = ? AND user_id = ?",
                (int(record_id), int(user_id)),
            )
        connection.commit()
        return cursor.rowcount > 0



def create_user(database_path: str | Path, name: str, email: str, password_hash: str, role: str = "user") -> int:
    created_at = datetime.now(timezone.utc).isoformat()
    with get_connection(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (name, email, password_hash, role, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (name, email, password_hash, role, created_at),
        )
        connection.commit()
        return int(cursor.lastrowid)


def get_user_by_email(database_path: str | Path, email: str) -> dict | None:
    with get_connection(database_path) as connection:
        row = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not row:
        return None
    return dict(row)


def get_user_by_id(database_path: str | Path, user_id: int) -> dict | None:
    with get_connection(database_path) as connection:
        row = connection.execute("SELECT * FROM users WHERE id = ?", (int(user_id),)).fetchone()
    if not row:
        return None
    return dict(row)


def update_last_login(database_path: str | Path, user_id: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(database_path) as connection:
        connection.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, int(user_id)))
        connection.commit()


def list_users(database_path: str | Path) -> list[dict]:
    with get_connection(database_path) as connection:
        rows = connection.execute("SELECT id, name, email, role, created_at, last_login, is_active FROM users ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


def set_user_active(database_path: str | Path, user_id: int, active: bool) -> bool:
    with get_connection(database_path) as connection:
        cursor = connection.execute("UPDATE users SET is_active = ? WHERE id = ?", (1 if active else 0, int(user_id)))
        connection.commit()
        return cursor.rowcount > 0


def change_user_role(database_path: str | Path, user_id: int, role: str) -> bool:
    with get_connection(database_path) as connection:
        cursor = connection.execute("UPDATE users SET role = ? WHERE id = ?", (role, int(user_id)))
        connection.commit()
        return cursor.rowcount > 0


def update_user_name(database_path: str | Path, user_id: int, name: str) -> bool:
    with get_connection(database_path) as connection:
        cursor = connection.execute("UPDATE users SET name = ? WHERE id = ?", (name, int(user_id)))
        connection.commit()
        return cursor.rowcount > 0
