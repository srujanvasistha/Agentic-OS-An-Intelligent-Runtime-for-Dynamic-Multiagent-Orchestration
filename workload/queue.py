import heapq
from workload.task import Task


class TaskQueue:

    def __init__(self):
        self._queue = []
        self._counter = 0

    def add_task(self, task: Task):

        task.mark_queued()

        # Negative priority means higher priority comes first
        heapq.heappush(
            self._queue,
            (-task.priority, self._counter, task)
        )

        self._counter += 1

    def get_next_task(self):

        if self._queue:

            _, _, task = heapq.heappop(self._queue)

            return task

        return None

    def peek(self):

        if self._queue:

            return self._queue[0][2]

        return None

    def size(self):

        return len(self._queue)

    def is_empty(self):

        return len(self._queue) == 0

    def get_all_tasks(self):

        # Return tasks sorted by priority
        sorted_queue = sorted(
            self._queue,
            key=lambda item: (
                item[0],
                item[1]
            )
        )

        return [
            item[2]
            for item in sorted_queue
        ]


if __name__ == "__main__":

    queue = TaskQueue()

    tasks = [

        Task(
            task_id="TASK-001",
            task_type="compute",
            priority=2,
            complexity="medium",
            payload={
                "operation": "matrix_multiplication",
                "size": 500
            },
            estimated_duration=4.5
        ),

        Task(
            task_id="TASK-002",
            task_type="network",
            priority=5,
            complexity="low",
            payload={
                "operation": "api_request",
                "endpoint": "/api/users"
            },
            estimated_duration=2.0
        ),

        Task(
            task_id="TASK-003",
            task_type="ml",
            priority=3,
            complexity="high",
            payload={
                "operation": "classification",
                "samples": 5000
            },
            estimated_duration=8.0
        ),

        Task(
            task_id="TASK-004",
            task_type="data",
            priority=1,
            complexity="medium",
            payload={
                "operation": "data_cleaning",
                "records": 10000
            },
            estimated_duration=5.0
        ),

        Task(
            task_id="TASK-005",
            task_type="text",
            priority=4,
            complexity="low",
            payload={
                "operation": "keyword_extraction",
                "documents": 100
            },
            estimated_duration=3.0
        )
    ]

    print("\nAdding Tasks")
    print("=" * 60)

    for task in tasks:

        queue.add_task(task)

        print(
            task.task_id,
            "| Priority:",
            task.priority
        )

    print("\nQueue Size:")
    print(queue.size())

    print("\nTasks in Priority Order")
    print("=" * 60)

    for task in queue.get_all_tasks():

        print(
            task.task_id,
            "|",
            task.task_type,
            "| Priority:",
            task.priority,
            "| Status:",
            task.status
        )

    print("\nExecution Order")
    print("=" * 60)

    while not queue.is_empty():

        task = queue.get_next_task()

        print(
            "Selected:",
            task.task_id,
            "| Priority:",
            task.priority,
            "| Type:",
            task.task_type
        )

    print("\nFinal Queue Size:")
    print(queue.size())