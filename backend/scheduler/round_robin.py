"""Round-Robin scheduler for AgentOS Day 3."""

from collections import defaultdict, deque
from scheduler.base import Scheduler
from schemas import Task


class RoundRobinScheduler(Scheduler):
    name = 'round_robin'
    """Fairly rotate work across agent types."""

    def __init__(self):
        self._queues = defaultdict(deque)
        self._agents = deque()

    def enqueue(self, task: Task) -> None:
        key = task.agent_type.value
        if not self._queues[key]:
            self._agents.append(key)
        self._queues[key].append(task)

    def next_task(self) -> Task | None:
        if not self._agents:
            return None
        for _ in range(len(self._agents)):
            key = self._agents[0]
            self._agents.rotate(-1)
            if self._queues[key]:
                task = self._queues[key].popleft()
                if not self._queues[key]:
                    try:
                        self._agents.remove(key)
                    except ValueError:
                        pass
                return task
        return None

    def has_tasks(self) -> bool:
        return bool(self._agents)

    def size(self) -> int:
        return sum(len(q) for q in self._queues.values())

    def clear(self) -> None:
        self._queues.clear()
        self._agents.clear()
