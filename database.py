from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from taxi_bot.config import Settings


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(settings: Settings) -> None:
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(settings.sqlite_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                name TEXT
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                pickup TEXT NOT NULL,
                "drop" TEXT NOT NULL,
                vehicle TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )


def upsert_user(settings: Settings, telegram_id: int, name: str | None) -> int:
    with _connect(settings.sqlite_path) as conn:
        conn.execute(
            """
            INSERT INTO users (telegram_id, name)
            VALUES (?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                name=excluded.name
            """,
            (telegram_id, name),
        )
        row = conn.execute(
            "SELECT id FROM users WHERE telegram_id = ?",
            (telegram_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError("Failed to upsert user.")
        return int(row["id"])


def create_booking(
    settings: Settings,
    user_id: int,
    pickup: str,
    drop: str,
    vehicle: str,
    status: str = "CONFIRMED",
) -> int:
    with _connect(settings.sqlite_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO bookings (user_id, pickup, "drop", vehicle, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, pickup, drop, vehicle, status),
        )
        return int(cur.lastrowid)


def list_bookings_for_user(
    settings: Settings, user_id: int, limit: int = 10
) -> list[dict[str, Any]]:
    with _connect(settings.sqlite_path) as conn:
        rows = conn.execute(
            """
            SELECT id, pickup, "drop", vehicle, status, created_at
            FROM bookings
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
