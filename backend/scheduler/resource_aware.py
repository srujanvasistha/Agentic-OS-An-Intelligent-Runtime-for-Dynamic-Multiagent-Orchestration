"""Resource-aware scheduler for AgentOS Day 3."""

from scheduler.base import Scheduler
from schemas import Task


class ResourceAwareScheduler(Scheduler):
    name = 'resource_aware'
    """Choose work using current host pressure and estimated task cost.

    Under high pressure, smaller tasks are preferred to improve responsiveness.
    Under low pressure, priority dominates while cost is used as a tie-breaker.
    """

    def __init__(self, system_state_provider=None):
        self._tasks: list[Task] = []
        self._system_state_provider = system_state_provider
        self._system_state: dict = {}

    def set_system_state(self, state: dict) -> None:
        self._system_state = dict(state or {})

    def enqueue(self, task: Task) -> None:
        self._tasks.append(task)

    def _pressure(self) -> float:
        state = self._system_state
        cpu = float(state.get("cpu_percent", 0.0))
        memory = float(state.get("memory_percent", 0.0))
        return max(cpu, memory)

    def next_task(self) -> Task | None:
        if not self._tasks:
            return None
        pressure = self._pressure()
        if pressure >= 80.0:
            key = lambda t: (t.estimated_tokens, -t.priority, t.submitted_at.timestamp())
        else:
            key = lambda t: (-t.priority, t.estimated_tokens, t.submitted_at.timestamp())
        return self._tasks.pop(min(range(len(self._tasks)), key=lambda i: key(self._tasks[i])))

    def has_tasks(self) -> bool:
        return bool(self._tasks)

    def size(self) -> int:
        return len(self._tasks)

    def clear(self) -> None:
        self._tasks.clear()
