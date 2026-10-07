class TaskStore:
    """In-memory task history used by the Day 2 runtime."""

    def __init__(self):
        self._tasks = {}

    def add(self, task):
        self._tasks[task.id] = task

    def get(self, task_id: str):
        return self._tasks.get(task_id)

    def list_tasks(self):
        return list(self._tasks.values())

    def count(self):
        return len(self._tasks)

    def clear(self):
        self._tasks.clear()

    def statistics(self):
        tasks = self.list_tasks()
        counts = {status.value: 0 for status in __import__('schemas').TaskStatus}
        for task in tasks:
            counts[task.status.value] += 1
        return {"total": len(tasks), **counts}
