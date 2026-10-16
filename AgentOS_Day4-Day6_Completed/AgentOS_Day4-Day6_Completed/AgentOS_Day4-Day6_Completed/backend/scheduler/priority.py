"""Stable priority-based scheduler. Higher priority values run first."""

import heapq
from scheduler.base import Scheduler
from schemas import Task


class PriorityScheduler(Scheduler):
    def __init__(self):
        self._heap = []
        self._sequence = 0

    def enqueue(self, task: Task) -> None:
        heapq.heappush(
            self._heap,
            (-task.priority, self._sequence, task),
        )
        self._sequence += 1

    def next_task(self) -> Task | None:
        if not self._heap:
            return None
        return heapq.heappop(self._heap)[2]

    def has_tasks(self) -> bool:
        return bool(self._heap)

    def size(self) -> int:
        return len(self._heap)

    def clear(self) -> None:
        self._heap.clear()
        self._sequence = 0
