
from datetime import datetime
from time import perf_counter

from app.memory.sqlite_memory import SQLiteMemory
from app.memory.task_history import TaskHistory
from app.monitor.resource_monitor import ResourceMonitor
from app.metrics.metrics_logger import MetricsLogger


def main():
    print("=" * 50)
    print(" AGENTOS P4 - DAY 5 INTEGRATION DEMO")
    print("=" * 50)

    # Initialize the four P4 components.
    memory = SQLiteMemory()
    history = TaskHistory()
    monitor = ResourceMonitor()
    logger = MetricsLogger()

    # Use a unique ID so rerunning the demo won't conflict
    # with the UNIQUE task_id constraint in SQLite.
    task_id = "p4-day5-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    description = "Collect and record system resource information"

    # 1. Create and start the task.
    history.create_task(task_id, description)
    history.update_status(task_id, "running")

    print(f"\nTask ID: {task_id}")
    print("Task status: running")

    # 2. Collect a real system resource snapshot.
    start_time = perf_counter()
    snapshot = monitor.get_snapshot()
    duration = round(perf_counter() - start_time, 3)

    # 3. Save a task result.
    result = (
        f"CPU: {snapshot['cpu_percent']}%; "
        f"RAM: {snapshot['memory']['percent']}%; "
        f"Disk: {snapshot['disk']['percent']}%"
    )

    history.save_result(task_id, result)
    history.update_status(task_id, "completed")

    # 4. Store the result in persistent memory.
    memory.remember(
        key=f"result_{task_id}",
        value=result,
        source="day5_integration_demo",
        task_id=task_id
    )

    # 5. Log metrics using the actual resource snapshot.
    logger.log_metric(
        task_id=task_id,
        agent_name="P4DemoAgent",
        status="completed",
        duration=duration,
        cpu_percent=snapshot["cpu_percent"],
        memory_percent=snapshot["memory"]["percent"],
        tokens=0
    )

    # 6. Export metrics to CSV.
    csv_path = logger.export_csv()

    # 7. Display the results from the components.
    print("\n--- Resource Snapshot ---")
    monitor.print_snapshot()

    print("\n--- Saved Task History ---")
    print(history.get_task(task_id))

    print("\n--- Recalled Memory ---")
    print(memory.recall(f"result_{task_id}"))

    print("\n--- Metrics Recorded ---")
    for metric in logger.get_metrics():
        print(metric)

    print("\n--- CSV Export ---")
    print(f"Metrics saved to: {csv_path}")

    print("\nTask status: completed")
    print("P4 integration demo finished successfully.")


if __name__ == "__main__":
    main()
