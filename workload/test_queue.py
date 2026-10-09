from generator import generate_workload
from queue import TaskQueue


def main():

    # Generate 40 realistic tasks
    workload = generate_workload(
        num_tasks=40,
        seed=42
    )

    # Create priority queue
    queue = TaskQueue()

    # Add generated tasks to queue
    for task in workload:
        queue.add_task(task)

    print("\n" + "=" * 70)
    print("AGENTICOS PRIORITY QUEUE TEST")
    print("=" * 70)

    print("\nTotal Tasks Generated:", len(workload))
    print("Tasks in Queue:", queue.size())

    print("\nPriority Order")
    print("-" * 70)

    for task in queue.get_all_tasks():

        print(
            f"{task.task_id} | "
            f"Type: {task.task_type:<8} | "
            f"Priority: {task.priority} | "
            f"Complexity: {task.complexity:<6} | "
            f"Status: {task.status}"
        )

    print("\n" + "=" * 70)
    print("SIMULATED TASK SELECTION")
    print("=" * 70)

    count = 0

    while not queue.is_empty():

        task = queue.get_next_task()

        count += 1

        print(
            f"{count:02d}. "
            f"{task.task_id} → "
            f"{task.task_type} → "
            f"Priority {task.priority}"
        )

    print("\nRemaining Tasks:", queue.size())

    print("\nQueue test completed successfully.")


if __name__ == "__main__":
    main()
    