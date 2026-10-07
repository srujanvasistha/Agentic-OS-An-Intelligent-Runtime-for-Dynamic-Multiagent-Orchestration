"""Day 2 FIFO scheduler placeholder.

This is intentionally simple. P2 replaces it with research schedulers while
keeping the Scheduler interface unchanged.
"""

from collections import deque
from scheduler.base import Scheduler
from schemas import Task


class FIFOScheduler(Scheduler):
    def __init__(self):
        self._queue = deque()

    def enqueue(self, task: Task) -> None:
        self._queue.append(task)

    def next_task(self) -> Task | None:
        return self._queue.popleft() if self._queue else None

    def has_tasks(self) -> bool:
        return bool(self._queue)

    def size(self) -> int:
        return len(self._queue)

    def clear(self) -> None:
        self._queue.clear()
