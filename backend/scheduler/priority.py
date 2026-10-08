"""Priority scheduler for AgentOS Day 3."""

import heapq
from itertools import count
from scheduler.base import Scheduler
from schemas import Task


class PriorityScheduler(Scheduler):
    name = 'priority'
    """Highest priority first; submission order breaks ties."""

    def __init__(self):
        self._heap = []
        self._sequence = count()

    def enqueue(self, task: Task) -> None:
        heapq.heappush(self._heap, (-task.priority, next(self._sequence), task))

    def next_task(self) -> Task | None:
        return heapq.heappop(self._heap)[2] if self._heap else None

    def has_tasks(self) -> bool:
        return bool(self._heap)

    def size(self) -> int:
        return len(self._heap)

    def clear(self) -> None:
        self._heap.clear()
