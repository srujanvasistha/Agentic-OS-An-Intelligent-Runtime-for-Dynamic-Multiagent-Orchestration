"""Thread-safe, bounded in-memory task history for the AgentOS runtime."""

from __future__ import annotations

from threading import RLock
import os
from schemas import TaskStatus


_TERMINAL = {TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.BLOCKED}


class TaskStore:
    """Keep recent task history without allowing completed-task memory to grow forever.

    Queued/running tasks are never evicted. If active tasks alone exceed the cap,
    the store temporarily exceeds it rather than losing live work.
    """

    def __init__(self, max_history: int | None = None):
        max_history = int(os.getenv("AGENTOS_TASK_HISTORY_LIMIT", "1000")) if max_history is None else max_history
        if max_history < 1:
            raise ValueError("max_history must be positive")
        self.max_history = max_history
        self._tasks = {}
        self._lock = RLock()

    def _trim(self) -> None:
        while len(self._tasks) > self.max_history:
            evict_id = next(
                (task_id for task_id, task in self._tasks.items() if task.status in _TERMINAL),
                None,
            )
            if evict_id is None:
                break
            del self._tasks[evict_id]

    def add(self, task):
        with self._lock:
            self._tasks[task.id] = task
            self._trim()

    def get(self, task_id: str):
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self):
        with self._lock:
            return list(self._tasks.values())

    def count(self):
        with self._lock:
            return len(self._tasks)

    def clear(self):
        with self._lock:
            self._tasks.clear()

    def statistics(self):
        with self._lock:
            tasks = list(self._tasks.values())
        counts = {status.value: 0 for status in TaskStatus}
        for task in tasks:
            counts[task.status.value] += 1
        return {"total": len(tasks), **counts}
