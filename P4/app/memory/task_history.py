import sqlite3
from datetime import datetime
from pathlib import Path


class TaskHistory:

    def __init__(self, db_path="data/agentos_memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self):
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                result TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT
            )
        """)

        connection.commit()
        connection.close()

    def create_task(self, task_id, description):
        now = datetime.now().isoformat()

        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO tasks
            (
                task_id,
                description,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            task_id,
            description,
            "pending",
            now
        ))

        connection.commit()
        connection.close()

    def update_status(self, task_id, status):
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        if status == "running":
            cursor.execute("""
                UPDATE tasks
                SET status = ?,
                    started_at = ?
                WHERE task_id = ?
            """, (
                status,
                datetime.now().isoformat(),
                task_id
            ))

        elif status in ("completed", "failed"):
            cursor.execute("""
                UPDATE tasks
                SET status = ?,
                    completed_at = ?
                WHERE task_id = ?
            """, (
                status,
                datetime.now().isoformat(),
                task_id
            ))

        else:
            cursor.execute("""
                UPDATE tasks
                SET status = ?
                WHERE task_id = ?
            """, (
                status,
                task_id
            ))

        connection.commit()
        connection.close()

    def save_result(self, task_id, result):
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE tasks
            SET result = ?
            WHERE task_id = ?
        """, (
            result,
            task_id
        ))

        connection.commit()
        connection.close()

    def get_task(self, task_id):
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                task_id,
                description,
                status,
                result,
                created_at,
                started_at,
                completed_at
            FROM tasks
            WHERE task_id = ?
        """, (task_id,))

        row = cursor.fetchone()

        connection.close()

        return row


    def get_recent_tasks(self, limit=10):
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                task_id,
                description,
                status,
                result,
                created_at,
                started_at,
                completed_at
            FROM tasks
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()

        connection.close()

        return rows