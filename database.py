from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from config import settings

def utc_now() -> str:
    """Return the current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()

def get_database_path() -> Path:
    """Resolve and create the database directory."""
    path = Path(settings.database_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    database_path = get_database_path()
    connection = sqlite3.connect(
        str(database_path),
        timeout=15,
        isolation_level=None,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 15000")
    try:
        connection.execute("BEGIN")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def init_db() -> None:
    """Create all application tables and indexes if they do not exist."""
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                importance INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id, created_at);

            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                rating INTEGER NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id, created_at);

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON tasks(user_id, status);

            CREATE TABLE IF NOT EXISTS learning_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                summary TEXT NOT NULL,
                source TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_learning_user ON learning_records(user_id, created_at);

            CREATE TABLE IF NOT EXISTS code_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                target_file TEXT NOT NULL,
                proposed_code TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                test_result TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_proposals_user_status ON code_proposals(user_id, status);
            """
        )

def add_memory(
    user_id: str,
    content: str,
    category: str = "general",
    importance: int = 1,
) -> int:
    now = utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO memories (
                user_id, content, category, importance, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                content,
                category,
                max(1, min(5, int(importance))),
                now,
                now,
            ),
        )
        return int(cursor.lastrowid)

def get_memories(user_id: str, limit: int = 100) -> list[dict[str, Any]]:
    safe_limit = max(1, min(500, int(limit)))
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM memories WHERE user_id = ? 
            ORDER BY importance DESC, created_at DESC LIMIT ?
            """,
            (user_id, safe_limit),
        ).fetchall()
        return [dict(row) for row in rows]

def delete_memory(user_id: str, memory_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM memories WHERE id = ? AND user_id = ?",
            (memory_id, user_id),
        )
        return cursor.rowcount > 0

def clear_memories(user_id: str) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM memories WHERE user_id = ?",
            (user_id,),
        )
        return cursor.rowcount

def add_feedback(
    user_id: str,
    message: str,
    rating: int,
    details: str | None = None,
) -> int:
    if not 1 <= int(rating) <= 5:
        raise ValueError("Rating must be between 1 and 5.")
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO feedback (
                user_id, message, rating, details, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, message, int(rating), details, utc_now()),
        )
        return int(cursor.lastrowid)

def get_feedback(user_id: str, limit: int = 100) -> list[dict[str, Any]]:
    safe_limit = max(1, min(500, int(limit)))
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM feedback WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT ?
            """,
            (user_id, safe_limit),
        ).fetchall()
        return [dict(row) for row in rows]

def add_task(
    user_id: str,
    title: str,
    description: str | None = None,
) -> int:
    now = utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO tasks (
                user_id, title, description, status, created_at, updated_at
            ) VALUES (?, ?, ?, 'pending', ?, ?)
            """,
            (user_id, title, description, now, now),
        )
        return int(cursor.lastrowid)

def get_tasks(
    user_id: str,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    safe_limit = max(1, min(500, int(limit)))
    with get_connection() as connection:
        if status is None:
            rows = connection.execute(
                """
                SELECT * FROM tasks WHERE user_id = ? 
                ORDER BY created_at DESC LIMIT ?
                """,
                (user_id, safe_limit),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT * FROM tasks WHERE user_id = ? AND status = ? 
                ORDER BY created_at DESC LIMIT ?
                """,
                (user_id, status, safe_limit),
            ).fetchall()
        return [dict(row) for row in rows]

def update_task_status(
    user_id: str,
    task_id: int,
    status: str,
) -> bool:
    allowed_statuses = {"pending", "in_progress", "completed", "cancelled"}
    if status not in allowed_statuses:
        raise ValueError("Invalid task status.")
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE tasks SET status = ?, updated_at = ? 
            WHERE id = ? AND user_id = ?
            """,
            (status, utc_now(), task_id, user_id),
        )
        return cursor.rowcount > 0

def add_learning_record(
    user_id: str,
    topic: str,
    summary: str,
    source: str | None = None,
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO learning_records (
                user_id, topic, summary, source, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, topic, summary, source, utc_now()),
        )
        return int(cursor.lastrowid)

def get_learning_records(user_id: str, limit: int = 100) -> list[dict[str, Any]]:
    safe_limit = max(1, min(500, int(limit)))
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM learning_records WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT ?
            """,
            (user_id, safe_limit),
        ).fetchall()
        return [dict(row) for row in rows]

def add_code_proposal(
    user_id: str,
    title: str,
    description: str,
    target_file: str,
    proposed_code: str,
    test_result: str | None = None,
) -> int:
    now = utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO code_proposals (
                user_id, title, description, target_file, proposed_code, 
                status, test_result, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)
            """,
            (
                user_id,
                title,
                description,
                target_file,
                proposed_code,
                test_result,
                now,
                now,
            ),
        )
        return int(cursor.lastrowid)

def get_code_proposals(
    user_id: str,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    safe_limit = max(1, min(500, int(limit)))
    with get_connection() as connection:
        if status is None:
            rows = connection.execute(
                """
                SELECT * FROM code_proposals WHERE user_id = ? 
                ORDER BY created_at DESC LIMIT ?
                """,
                (user_id, safe_limit),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT * FROM code_proposals WHERE user_id = ? AND status = ? 
                ORDER BY created_at DESC LIMIT ?
                """,
                (user_id, status, safe_limit),
            ).fetchall()
        return [dict(row) for row in rows]

def update_code_proposal_status(
    user_id: str,
    proposal_id: int,
    status: str,
    test_result: str | None = None,
) -> bool:
    allowed_statuses = {"pending", "approved", "rejected", "tested", "applied"}
    if status not in allowed_statuses:
        raise ValueError("Invalid proposal status.")
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE code_proposals SET status = ?, test_result = ?, updated_at = ? 
            WHERE id = ? AND user_id = ?
            """,
            (status, test_result, utc_now(), proposal_id, user_id),
        )
        return cursor.rowcount > 0

def check_database() -> bool:
    try:
        with get_connection() as connection:
            result = connection.execute("SELECT 1").fetchone()
            return result is not None and result[0] == 1
    except sqlite3.Error:
        return False
