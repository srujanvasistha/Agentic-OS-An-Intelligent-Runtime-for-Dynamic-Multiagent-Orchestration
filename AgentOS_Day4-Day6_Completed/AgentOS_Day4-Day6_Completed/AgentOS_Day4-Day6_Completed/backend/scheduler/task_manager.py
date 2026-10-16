"""Task lifecycle and queue management for AgentOS Day 2."""

from datetime import datetime
from schemas import Task, TaskResult, TaskStatus
from scheduler.base import Scheduler
from scheduler.task_store import TaskStore


class TaskManager:
    def __init__(self, scheduler: Scheduler, store: TaskStore | None = None):
        self.scheduler = scheduler
        self.store = store or TaskStore()

    def create_task(self, task: Task) -> Task:
        task.status = TaskStatus.QUEUED
        self.store.add(task)
        self.scheduler.enqueue(task)
        return task

    def next_task(self) -> Task | None:
        task = self.scheduler.next_task()
        if task is None:
            return None
        if task.status != TaskStatus.QUEUED:
            return self.next_task()
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.store.add(task)
        return task

    def mark_done(self, task: Task) -> None:
        task.status = TaskStatus.DONE
        task.completed_at = datetime.now()
        self.store.add(task)

    def mark_failed(self, task: Task) -> None:
        task.status = TaskStatus.FAILED
        task.completed_at = datetime.now()
        self.store.add(task)

    def mark_blocked(self, task: Task) -> None:
        task.status = TaskStatus.BLOCKED
        task.completed_at = datetime.now()
        self.store.add(task)

    def get(self, task_id: str):
        return self.store.get(task_id)

    def list_tasks(self):
        return self.store.list_tasks()

    def queue_size(self) -> int:
        return self.scheduler.size()

    def clear(self) -> None:
        self.store.clear()
        clear = getattr(self.scheduler, "clear", None)
        if clear:
            clear()
