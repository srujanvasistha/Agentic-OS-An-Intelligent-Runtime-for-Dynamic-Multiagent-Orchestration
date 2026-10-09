
from datetime import datetime

from app.memory.task_history import TaskHistory
from app.monitor.resource_monitor import ResourceMonitor


def test_task_lifecycle_and_resource_snapshot():
    history = TaskHistory()
    monitor = ResourceMonitor()

    task_id = "integration-test-" + datetime.now().strftime(
        "%Y%m%d%H%M%S%f"
    )

    history.create_task(
        task_id,
        "Integration test resource collection"
    )

    history.update_status(task_id, "running")

    snapshot = monitor.get_snapshot()

    assert "cpu_percent" in snapshot
    assert "memory" in snapshot
    assert "disk" in snapshot

    result = (
        f"CPU: {snapshot['cpu_percent']}%; "
        f"RAM: {snapshot['memory']['percent']}%"
    )

    history.save_result(task_id, result)
    history.update_status(task_id, "completed")

    saved_task = history.get_task(task_id)

    assert saved_task is not None
    assert saved_task[1] == task_id
    assert saved_task[3] == "completed"
    assert saved_task[4] == result
