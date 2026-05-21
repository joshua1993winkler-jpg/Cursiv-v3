"""
SQLite schema + helpers for the Cursiv Board backend.
Users + posts. No ORM — plain sqlite3, no extra dependencies.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

_DB_PATH = Path(__file__).parent / "board.db"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(_DB_PATH))
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id        TEXT PRIMARY KEY,
                username  TEXT UNIQUE NOT NULL,
                pw_hash   TEXT NOT NULL,
                created   TEXT NOT NULL,
                device_id TEXT
            );
            CREATE TABLE IF NOT EXISTS posts (
                id        TEXT PRIMARY KEY,
                user_id   TEXT NOT NULL,
                username  TEXT NOT NULL,
                text      TEXT NOT NULL,
                source    TEXT NOT NULL DEFAULT 'broadcast',
                timestamp TEXT NOT NULL
            );
        """)
        # migrate: add device_id column if upgrading from older schema
        try:
            c.execute("ALTER TABLE users ADD COLUMN device_id TEXT")
        except Exception:
            pass


# ── Users ─────────────────────────────────────────────────────────────────────

def create_user(username: str, pw_hash: str, device_id: str | None = None) -> dict[str, Any]:
    uid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with _conn() as c:
        c.execute(
            "INSERT INTO users (id, username, pw_hash, created, device_id) VALUES (?,?,?,?,?)",
            (uid, username.lower().strip(), pw_hash, now, device_id),
        )
    return {"id": uid, "username": username}


def get_user_by_device_id(device_id: str) -> dict[str, Any] | None:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM users WHERE device_id = ?", (device_id,)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_username(username: str) -> dict[str, Any] | None:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM users WHERE username = ?", (username.lower().strip(),)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(uid: str) -> dict[str, Any] | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    return dict(row) if row else None


# ── Posts ─────────────────────────────────────────────────────────────────────

def count_posts_today(user_id: str) -> int:
    today = datetime.utcnow().date().isoformat()   # "YYYY-MM-DD"
    with _conn() as c:
        row = c.execute(
            "SELECT COUNT(*) FROM posts WHERE user_id = ? AND timestamp LIKE ?",
            (user_id, f"{today}%"),
        ).fetchone()
    return row[0] if row else 0


def create_post(user_id: str, username: str, text: str, source: str) -> dict[str, Any]:
    pid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with _conn() as c:
        c.execute(
            "INSERT INTO posts (id, user_id, username, text, source, timestamp) "
            "VALUES (?,?,?,?,?,?)",
            (pid, user_id, username, text[:2000], source, now),
        )
    return {"id": pid, "username": username, "text": text[:2000],
            "source": source, "timestamp": now}


def get_posts(limit: int = 100) -> list[dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, username, text, source, timestamp FROM posts "
            "ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def delete_post(post_id: str, user_id: str) -> bool:
    with _conn() as c:
        cur = c.execute(
            "DELETE FROM posts WHERE id = ? AND user_id = ?", (post_id, user_id)
        )
    return cur.rowcount > 0
