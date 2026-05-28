from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class ThreadMessage:
    role: str
    content: str
    timestamp: str
    retrieval_debug_id: str | None = None


@dataclass
class ThreadRecord:
    thread_id: str
    session_key: str | None
    created_at: str
    updated_at: str
    title: str | None = None
    pinned: bool = False


class SqliteThreadStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS threads (
                    thread_id TEXT PRIMARY KEY,
                    session_key TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    title TEXT,
                    pinned INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    retrieval_debug_id TEXT,
                    FOREIGN KEY (thread_id) REFERENCES threads(thread_id)
                );
                CREATE INDEX IF NOT EXISTS idx_messages_thread
                    ON messages(thread_id, id);
                """
            )
            cols = {r["name"] for r in conn.execute("PRAGMA table_info(threads)").fetchall()}
            if "title" not in cols:
                conn.execute("ALTER TABLE threads ADD COLUMN title TEXT")
            if "pinned" not in cols:
                conn.execute("ALTER TABLE threads ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")

    def get_or_create(
        self,
        thread_id: str | None = None,
        *,
        session_key: str | None = None,
    ) -> ThreadRecord:
        if thread_id:
            existing = self.get_thread(thread_id)
            if existing:
                return existing
            now = datetime.now(timezone.utc).isoformat()
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO threads (thread_id, session_key, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (thread_id, session_key, now, now),
                )
            return ThreadRecord(
                thread_id=thread_id,
                session_key=session_key,
                created_at=now,
                updated_at=now,
                title=None,
                pinned=False,
            )
        return self.new_thread(session_key=session_key)

    def new_thread(self, session_key: str | None = None) -> ThreadRecord:
        tid = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO threads (thread_id, session_key, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (tid, session_key, now, now),
            )
        return ThreadRecord(
            thread_id=tid,
            session_key=session_key,
            created_at=now,
            updated_at=now,
            title=None,
            pinned=False,
        )

    def get_thread(self, thread_id: str) -> ThreadRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM threads WHERE thread_id = ?", (thread_id,)
            ).fetchone()
        if not row:
            return None
        return ThreadRecord(
            thread_id=row["thread_id"],
            session_key=row["session_key"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            title=row["title"],
            pinned=bool(row["pinned"]),
        )

    def list_threads(self, session_key: str | None = None, limit: int = 50) -> list[ThreadRecord]:
        with self._connect() as conn:
            if session_key:
                rows = conn.execute(
                    """
                    SELECT * FROM threads
                    WHERE session_key = ?
                    ORDER BY pinned DESC, updated_at DESC
                    LIMIT ?
                    """,
                    (session_key, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM threads ORDER BY pinned DESC, updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [
            ThreadRecord(
                thread_id=r["thread_id"],
                session_key=r["session_key"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                title=r["title"],
                pinned=bool(r["pinned"]),
            )
            for r in rows
        ]

    def update_thread(
        self,
        thread_id: str,
        *,
        title: str | None = None,
        pinned: bool | None = None,
    ) -> ThreadRecord | None:
        existing = self.get_thread(thread_id)
        if not existing:
            return None
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            if title is not None:
                conn.execute(
                    "UPDATE threads SET title = ?, updated_at = ? WHERE thread_id = ?",
                    (title.strip() or None, now, thread_id),
                )
            if pinned is not None:
                conn.execute(
                    "UPDATE threads SET pinned = ?, updated_at = ? WHERE thread_id = ?",
                    (1 if pinned else 0, now, thread_id),
                )
        return self.get_thread(thread_id)

    def delete_thread(self, thread_id: str) -> bool:
        with self._connect() as conn:
            exists = conn.execute(
                "SELECT 1 FROM threads WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
            if not exists:
                return False
            conn.execute("DELETE FROM messages WHERE thread_id = ?", (thread_id,))
            conn.execute("DELETE FROM threads WHERE thread_id = ?", (thread_id,))
            return True

    def append_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        *,
        retrieval_debug_id: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (thread_id, role, content, timestamp, retrieval_debug_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (thread_id, role, content, now, retrieval_debug_id),
            )
            conn.execute(
                "UPDATE threads SET updated_at = ? WHERE thread_id = ?",
                (now, thread_id),
            )

    def history(self, thread_id: str, limit: int = 100) -> list[ThreadMessage]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content, timestamp, retrieval_debug_id
                FROM messages WHERE thread_id = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (thread_id, limit),
            ).fetchall()
        return [
            ThreadMessage(
                role=r["role"],
                content=r["content"],
                timestamp=r["timestamp"],
                retrieval_debug_id=r["retrieval_debug_id"],
            )
            for r in rows
        ]

    def recent_user_lines(self, thread_id: str, max_turns: int) -> list[str]:
        messages = self.history(thread_id)
        user_lines = [m.content for m in messages if m.role == "user"]
        return user_lines[-max_turns:]
