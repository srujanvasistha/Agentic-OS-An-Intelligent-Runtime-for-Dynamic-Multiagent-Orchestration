import sqlite3
from datetime import datetime
from pathlib import Path
class SQLiteMemory:

    def __init__(self, db_path="data/agentos_memory.db"):
        self.db_path = Path(db_path)

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.initialize()

    def initialize(self):

        connection = sqlite3.connect(self.db_path)

        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                source TEXT,
                task_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        connection.commit()
        connection.close()

    def remember(
        self,
        key,
        value,
        source=None,
        task_id=None
    ):

        now = datetime.now().isoformat()

        connection = sqlite3.connect(self.db_path)

        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO memory
            (
                key,
                value,
                source,
                task_id,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(key)
            DO UPDATE SET
                value = excluded.value,
                source = excluded.source,
                task_id = excluded.task_id,
                updated_at = excluded.updated_at
        """, (
            key,
            value,
            source,
            task_id,
            now,
            now
        ))

        connection.commit()
        connection.close()

    def recall(self, key):

        connection = sqlite3.connect(self.db_path)

        cursor = connection.cursor()

        cursor.execute("""
            SELECT value
            FROM memory
            WHERE key = ?
        """, (key,))

        result = cursor.fetchone()

        connection.close()

        if result is None:
            return None

        return result[0]

    def forget(self, key):

        connection = sqlite3.connect(self.db_path)

        cursor = connection.cursor()

        cursor.execute("""
            DELETE FROM memory
            WHERE key = ?
        """, (key,))

        connection.commit()
        connection.close()

    def get_recent(self, limit=10):

        connection = sqlite3.connect(self.db_path)

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                key,
                value,
                source,
                task_id,
                created_at,
                updated_at
            FROM memory
            ORDER BY updated_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()

        connection.close()

        return rows

    def clear(self):

        connection = sqlite3.connect(self.db_path)

        cursor = connection.cursor()

        cursor.execute("DELETE FROM memory")

        connection.commit()
        connection.close()

if __name__ == "__main__":
        memory = SQLiteMemory()

        print("P4 memory database initialized.")