"""Round-Robin scheduler that interleaves tasks by agent type."""

from collections import deque
from scheduler.base import Scheduler
from schemas import Task


class RoundRobinScheduler(Scheduler):
    def __init__(self):
        self._queues = {}
        self._agents = deque()
        self._size = 0

    def enqueue(self, task: Task) -> None:
        key = task.agent_type.value
        if key not in self._queues:
            self._queues[key] = deque()
            self._agents.append(key)
        self._queues[key].append(task)
        self._size += 1

    def next_task(self) -> Task | None:
        while self._agents:
            key = self._agents.popleft()
            queue = self._queues[key]
            task = queue.popleft()
            self._size -= 1

            if queue:
                self._agents.append(key)
            else:
                del self._queues[key]

            return task
        return None

    def has_tasks(self) -> bool:
        return self._size > 0

    def size(self) -> int:
        return self._size

    def clear(self) -> None:
        self._queues.clear()
        self._agents.clear()
        self._size = 0
