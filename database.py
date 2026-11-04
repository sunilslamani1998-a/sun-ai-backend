from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from config import settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_database_path() -> Path:
    path = Path(settings.database_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(str(get_database_path()), timeout=15, isolation_level=None)
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
    # executescript manages its own transaction boundary in sqlite3.
    with get_connection() as connection:
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
            content TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'general',
            importance INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id, created_at);
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
            message TEXT NOT NULL, rating INTEGER NOT NULL, details TEXT, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id, created_at);
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
            title TEXT NOT NULL, description TEXT, status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON tasks(user_id, status);
        CREATE TABLE IF NOT EXISTS learning_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
            topic TEXT NOT NULL, summary TEXT NOT NULL, source TEXT, created_at TEXT NOT NULL,
            language TEXT NOT NULL DEFAULT 'english',
            approval_status TEXT NOT NULL DEFAULT 'approved', approved_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_learning_user ON learning_records(user_id, created_at);
        CREATE TABLE IF NOT EXISTS code_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
            title TEXT NOT NULL, description TEXT NOT NULL, target_file TEXT NOT NULL,
            proposed_code TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
            test_result TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_proposals_user_status ON code_proposals(user_id, status);
        """)
    # Additive, repeatable migrations preserve existing rows and default them to English.
    with get_connection() as connection:
        for table in ("memories", "learning_records"):
            columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
            if "language" not in columns:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN language TEXT NOT NULL DEFAULT 'english'")
        learning_columns = {row["name"] for row in connection.execute("PRAGMA table_info(learning_records)").fetchall()}
        if "approval_status" not in learning_columns:
            # Existing user-created learning records remain usable; only new records await approval.
            connection.execute("ALTER TABLE learning_records ADD COLUMN approval_status TEXT NOT NULL DEFAULT 'approved'")
        if "approved_at" not in learning_columns:
            connection.execute("ALTER TABLE learning_records ADD COLUMN approved_at TEXT")


def add_memory(user_id: str, content: str, category: str = "general", importance: int = 1, language: str = "english") -> int:
    now = utc_now()
    with get_connection() as c:
        cur = c.execute("INSERT INTO memories(user_id,content,category,importance,created_at,updated_at,language) VALUES(?,?,?,?,?,?,?)",
                         (user_id, content, category, max(1, min(5, int(importance))), now, now, language))
        return int(cur.lastrowid)


def get_memories(user_id: str, limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(500, int(limit)))
    with get_connection() as c:
        rows = c.execute("SELECT * FROM memories WHERE user_id=? ORDER BY importance DESC, created_at DESC LIMIT ?", (user_id, limit)).fetchall()
    return [dict(r) for r in rows]


def delete_memory(user_id: str, memory_id: int) -> bool:
    with get_connection() as c:
        return c.execute("DELETE FROM memories WHERE id=? AND user_id=?", (memory_id, user_id)).rowcount > 0


def clear_memories(user_id: str) -> int:
    with get_connection() as c:
        return c.execute("DELETE FROM memories WHERE user_id=?", (user_id,)).rowcount


def add_feedback(user_id: str, message: str, rating: int, details: str | None = None) -> int:
    if not 1 <= int(rating) <= 5:
        raise ValueError("Rating must be between 1 and 5.")
    with get_connection() as c:
        cur = c.execute("INSERT INTO feedback(user_id,message,rating,details,created_at) VALUES(?,?,?,?,?)", (user_id, message, int(rating), details, utc_now()))
        return int(cur.lastrowid)


def get_feedback(user_id: str, limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(500, int(limit)))
    with get_connection() as c:
        rows = c.execute("SELECT * FROM feedback WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit)).fetchall()
    return [dict(r) for r in rows]


def add_task(user_id: str, title: str, description: str | None = None) -> int:
    now = utc_now()
    with get_connection() as c:
        cur = c.execute("INSERT INTO tasks(user_id,title,description,status,created_at,updated_at) VALUES(?,?,?,'pending',?,?)", (user_id, title, description, now, now))
        return int(cur.lastrowid)


def get_tasks(user_id: str, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(500, int(limit)))
    with get_connection() as c:
        if status is None:
            rows = c.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit)).fetchall()
        else:
            rows = c.execute("SELECT * FROM tasks WHERE user_id=? AND status=? ORDER BY created_at DESC LIMIT ?", (user_id, status, limit)).fetchall()
    return [dict(r) for r in rows]


def update_task_status(user_id: str, task_id: int, status: str) -> bool:
    if status not in {"pending", "in_progress", "completed", "cancelled"}:
        raise ValueError("Invalid task status.")
    with get_connection() as c:
        return c.execute("UPDATE tasks SET status=?,updated_at=? WHERE id=? AND user_id=?", (status, utc_now(), task_id, user_id)).rowcount > 0


def add_learning_record(user_id: str, topic: str, summary: str, source: str | None = None, language: str = "english") -> int:
    with get_connection() as c:
        cur = c.execute(
            "INSERT INTO learning_records(user_id,topic,summary,source,created_at,language,approval_status,approved_at) VALUES(?,?,?,?,?,?,'pending',NULL)",
            (user_id, topic, summary, source, utc_now(), language),
        )
        return int(cur.lastrowid)


def get_learning_records(user_id: str, limit: int = 100, approval_status: str | None = None) -> list[dict[str, Any]]:
    limit = max(1, min(500, int(limit)))
    with get_connection() as c:
        if approval_status is None:
            rows = c.execute("SELECT * FROM learning_records WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit)).fetchall()
        else:
            rows = c.execute("SELECT * FROM learning_records WHERE user_id=? AND approval_status=? ORDER BY created_at DESC LIMIT ?", (user_id, approval_status, limit)).fetchall()
    return [dict(r) for r in rows]


def update_learning_approval(user_id: str, record_id: int, approval_status: str) -> bool:
    if approval_status not in {"approved", "rejected"}:
        raise ValueError("Approval status must be approved or rejected.")
    approved_at = utc_now() if approval_status == "approved" else None
    with get_connection() as c:
        return c.execute(
            "UPDATE learning_records SET approval_status=?, approved_at=? WHERE id=? AND user_id=? AND approval_status='pending'",
            (approval_status, approved_at, record_id, user_id),
        ).rowcount > 0


def add_code_proposal(user_id: str, title: str, description: str, target_file: str, proposed_code: str, test_result: str | None = None) -> int:
    now = utc_now()
    with get_connection() as c:
        cur = c.execute("INSERT INTO code_proposals(user_id,title,description,target_file,proposed_code,status,test_result,created_at,updated_at) VALUES(?,?,?,?,?,'pending',?,?,?)", (user_id, title, description, target_file, proposed_code, test_result, now, now))
        return int(cur.lastrowid)


def get_code_proposals(user_id: str, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(500, int(limit)))
    with get_connection() as c:
        if status is None:
            rows = c.execute("SELECT * FROM code_proposals WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit)).fetchall()
        else:
            rows = c.execute("SELECT * FROM code_proposals WHERE user_id=? AND status=? ORDER BY created_at DESC LIMIT ?", (user_id, status, limit)).fetchall()
    return [dict(r) for r in rows]


def update_code_proposal_status(user_id: str, proposal_id: int, status: str, test_result: str | None = None) -> bool:
    if status not in {"pending", "approved", "rejected", "tested", "applied"}:
        raise ValueError("Invalid proposal status.")
    with get_connection() as c:
        return c.execute("UPDATE code_proposals SET status=?,test_result=?,updated_at=? WHERE id=? AND user_id=?", (status, test_result, utc_now(), proposal_id, user_id)).rowcount > 0


def check_database() -> bool:
    try:
        with get_connection() as c:
            result = c.execute("SELECT 1").fetchone()
        return result is not None and result[0] == 1
    except sqlite3.Error:
        return False
