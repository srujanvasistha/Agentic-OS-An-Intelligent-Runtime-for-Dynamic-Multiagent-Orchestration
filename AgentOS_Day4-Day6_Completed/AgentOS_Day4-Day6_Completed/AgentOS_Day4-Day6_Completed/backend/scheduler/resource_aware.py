"""Explainable resource-aware scheduler using a weighted task score."""

from datetime import datetime
from scheduler.base import Scheduler
from schemas import Task


class ResourceAwareScheduler(Scheduler):
    W_PRIORITY = 3.0
    W_URGENCY = 2.0
    W_COMPLEXITY = 1.0
    W_TOKEN_COST = 0.01
    W_RISK = 2.0

    def __init__(self):
        self._tasks = []
        self._sequence = 0

    @staticmethod
    def _pressure(resources):
        resources = resources or {}
        cpu = float(resources.get("cpu_percent", 0))
        memory = float(resources.get("memory_percent", 0))
        return max(0.0, min(1.0, max(cpu, memory) / 100.0))

    @staticmethod
    def _urgency(task, now):
        if task.deadline_s is None:
            return 0.0

        deadline = task.submitted_at.timestamp() + task.deadline_s
        remaining = deadline - now.timestamp()

        if remaining <= 0:
            return 10.0

        return min(10.0, 10.0 / (1.0 + remaining))

    def score(self, task, resources=None, now=None):
        resources = resources or {}
        now = now or datetime.now()
        pressure = self._pressure(resources)

        return (
            self.W_PRIORITY * float(task.priority)
            + self.W_URGENCY * self._urgency(task, now)
            - self.W_COMPLEXITY * float(task.complexity) * (1 + pressure)
            - self.W_TOKEN_COST * float(task.estimated_tokens)
            - self.W_RISK * float(task.risk_level) * pressure
        )

    def enqueue(self, task: Task) -> None:
        self._tasks.append((self._sequence, task))
        self._sequence += 1

    def next_task(self, resources=None, now=None) -> Task | None:
        if not self._tasks:
            return None

        now = now or datetime.now()
        best_index = max(
            range(len(self._tasks)),
            key=lambda i: (
                self.score(self._tasks[i][1], resources, now),
                -self._tasks[i][0],
            ),
        )
        _, task = self._tasks.pop(best_index)
        return task

    def has_tasks(self) -> bool:
        return bool(self._tasks)

    def size(self) -> int:
        return len(self._tasks)

    def clear(self) -> None:
        self._tasks.clear()
        self._sequence = 0
