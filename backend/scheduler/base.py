"""Scheduler contract used by the AgentOS runtime.

Day 2 provides FIFO. P2 can implement alternative schedulers against this
interface without modifying the runtime or agent code.
"""

from abc import ABC, abstractmethod
from schemas import Task


class Scheduler(ABC):
    @abstractmethod
    def enqueue(self, task: Task) -> None:
        """Add a queued task to the scheduler."""
        raise NotImplementedError

    @abstractmethod
    def next_task(self) -> Task | None:
        """Return the next task to execute, or None when empty."""
        raise NotImplementedError

    @abstractmethod
    def has_tasks(self) -> bool:
        """Return whether the scheduler currently has work."""
        raise NotImplementedError

    @abstractmethod
    def size(self) -> int:
        """Return the number of tasks waiting for execution."""
        raise NotImplementedError
