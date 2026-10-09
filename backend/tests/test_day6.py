from __future__ import annotations

import csv
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from memory.store import MemoryStore
from reproducibility import configure_reproducibility
from results_csv import RESULT_COLUMNS, append_result
from scheduler.task_store import TaskStore
from schemas import Task, TaskStatus


def test_reproducibility_seed_repeats_random_sequence(monkeypatch):
    monkeypatch.setenv("AGENTOS_SEED", "1234")
    configure_reproducibility()
    first = [random.random() for _ in range(5)]
    configure_reproducibility()
    second = [random.random() for _ in range(5)]
    assert first == second


def test_task_store_bounds_terminal_history_but_keeps_active_tasks():
    store = TaskStore(max_history=10)
    for index in range(30):
        task = Task(id=f"done-{index}", prompt="completed")
        task.status = TaskStatus.DONE
        store.add(task)
    assert store.count() == 10
    active = Task(id="active", prompt="still running")
    active.status = TaskStatus.RUNNING
    store.add(active)
    assert store.get("active") is active
    assert store.count() == 10


def test_memory_store_remains_bounded():
    store = MemoryStore(max_entries=12)
    for index in range(1000):
        store.remember(str(index), f"prompt {index}", "done", "response")
    assert store.size() == 12
    assert len(store.recent(100)) == 12


def test_concurrent_csv_appends_keep_one_header_and_all_rows(tmp_path: Path):
    output = tmp_path / "results.csv"
    def write(index: int) -> None:
        append_result(output, {"task_id": f"task-{index}", "status": "done", "llm_backend": "mock"})
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write, range(200)))
    with output.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert reader.fieldnames == RESULT_COLUMNS
    assert len(rows) == 200
    assert len({row["task_id"] for row in rows}) == 200


def test_task_store_rejects_non_positive_limit():
    try:
        TaskStore(max_history=0)
    except ValueError as exc:
        assert "positive" in str(exc)
    else:
        raise AssertionError("TaskStore should reject a non-positive history limit")
