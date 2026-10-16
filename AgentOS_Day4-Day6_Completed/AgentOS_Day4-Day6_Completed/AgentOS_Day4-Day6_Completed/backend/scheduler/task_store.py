"""SQLite-backed task history for the AgentOS web runtime."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any

from schemas import Task


class TaskStore:
    """Persists task snapshots in SQLite while preserving the original API."""

    def __init__(self, db_path: str | Path | None = None):
        default_path = Path(__file__).resolve().parents[2] / "results" / "agentos_tasks.sqlite3"
        self.db_path = Path(db_path or os.getenv("AGENTOS_DB_PATH", default_path)).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _connect(self):
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def add(self, task: Task):
        payload = task.model_dump_json()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO tasks(id, payload, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, updated_at=CURRENT_TIMESTAMP",
                (task.id, payload),
            )
            conn.commit()

    def get(self, task_id: str):
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT payload FROM tasks WHERE id=?", (task_id,)).fetchone()
        return Task.model_validate_json(row["payload"]) if row else None

    def list_tasks(self):
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT payload FROM tasks ORDER BY updated_at ASC, rowid ASC").fetchall()
        return [Task.model_validate_json(row["payload"]) for row in rows]

    def count(self):
        with self._lock, self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0])

    def clear(self):
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM tasks")
            conn.commit()

    def statistics(self):
        from schemas import TaskStatus
        tasks = self.list_tasks()
        counts = {status.value: 0 for status in TaskStatus}
        for task in tasks:
            counts[task.status.value] += 1
        return {"total": len(tasks), **counts}
