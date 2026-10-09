from app.memory.task_history import TaskHistory


def test_create_task(tmp_path):
    db_path = tmp_path / "tasks.db"

    history = TaskHistory(str(db_path))

    history.create_task(
        "task-001",
        "Test task"
    )

    task = history.get_task("task-001")

    assert task is not None
    assert task[1] == "task-001"
    assert task[2] == "Test task"
    assert task[3] == "pending"


def test_task_completion(tmp_path):
    db_path = tmp_path / "tasks.db"

    history = TaskHistory(str(db_path))

    history.create_task(
        "task-002",
        "Complete test"
    )

    history.update_status(
        "task-002",
        "running"
    )

    history.save_result(
        "task-002",
        "Success"
    )

    history.update_status(
        "task-002",
        "completed"
    )

    task = history.get_task("task-002")

    assert task[3] == "completed"
    assert task[4] == "Success"
    assert task[6] is not None
    assert task[7] is not None


def test_failed_task(tmp_path):
    db_path = tmp_path / "tasks.db"

    history = TaskHistory(str(db_path))

    history.create_task(
        "task-003",
        "Failure test"
    )

    history.update_status(
        "task-003",
        "running"
    )

    history.save_result(
        "task-003",
        "Something went wrong"
    )

    history.update_status(
        "task-003",
        "failed"
    )

    task = history.get_task("task-003")

    assert task[3] == "failed"
    assert task[4] == "Something went wrong"


def test_task_persistence(tmp_path):
    db_path = tmp_path / "tasks.db"

    history1 = TaskHistory(str(db_path))

    history1.create_task(
        "task-004",
        "Persistence test"
    )

    history2 = TaskHistory(str(db_path))

    task = history2.get_task("task-004")

    assert task is not None
    assert task[2] == "Persistence test"