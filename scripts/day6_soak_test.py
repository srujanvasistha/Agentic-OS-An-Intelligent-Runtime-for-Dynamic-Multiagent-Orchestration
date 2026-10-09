"""Run a bounded long workload using MockLLM; no Ollama service is required."""
from __future__ import annotations

import csv
import os
import sys
import tracemalloc
import psutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ["AGENTOS_LLM_BACKEND"] = "mock"
os.environ["AGENTOS_POLICY_ENFORCEMENT"] = "on"
os.environ.setdefault("AGENTOS_SEED", "42")

from agents.agent_manager import AgentManager
from agents.agent_registry import AgentRegistry
from agents.general_agent import GeneralAgent
from agents.task_router import TaskRouter
from llm.client import MockLLMClient
from results_csv import RESULT_COLUMNS
from scheduler.fifo import FIFOScheduler
from scheduler.runtime import AgentRuntime
from scheduler.task_manager import TaskManager
from scheduler.task_store import TaskStore
from schemas import Task
from memory.store import MemoryStore
from reproducibility import configure_reproducibility


def main() -> None:
    seed = configure_reproducibility()
    output = ROOT / "experiments" / "day6_soak_results.csv"
    if output.exists():
        output.unlink()
    registry = AgentRegistry()
    registry.register("GeneralAgent", GeneralAgent(llm_client=MockLLMClient()))
    manager = AgentManager(registry, TaskRouter())
    store = TaskStore(max_history=100)
    task_manager = TaskManager(FIFOScheduler(), store)
    memory = MemoryStore(max_entries=50)
    runtime = AgentRuntime(task_manager, manager, results_path=output, memory=memory, model_tier="1.5b", concurrency_limit=2)

    process = psutil.Process()
    rss_before = process.memory_info().rss
    tracemalloc.start()
    for index in range(1000):
        runtime.submit(Task(id=f"day6-soak-{index:04d}", prompt=f"repeatable stability task number {index}"))
    results = runtime.run_until_empty()
    current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss_after = process.memory_info().rss

    if len(results) != 1000 or any(result.status.value != "done" for result in results):
        raise SystemExit(f"FAIL: completed {sum(r.status.value == 'done' for r in results)}/1000 tasks")
    if store.count() > 100:
        raise SystemExit(f"FAIL: task history was not bounded ({store.count()} entries)")
    if memory.size() > 50:
        raise SystemExit(f"FAIL: runtime memory was not bounded ({memory.size()} entries)")
    with output.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        if reader.fieldnames != RESULT_COLUMNS or len(rows) != 1000:
            raise SystemExit("FAIL: soak CSV does not match the frozen result schema")
    print(f"Day 6 soak PASS: 1000/1000 tasks completed (seed={seed})")
    print(f"Bounded state PASS: task_history={store.count()}/100, memory={memory.size()}/50")
    print(f"CSV PASS: {len(rows)} rows with the frozen schema")
    print(f"tracemalloc current={current_bytes / 1024:.1f} KiB, peak={peak_bytes / 1024:.1f} KiB")
    print(f"process RSS before={rss_before / (1024 * 1024):.1f} MiB, after={rss_after / (1024 * 1024):.1f} MiB")


if __name__ == "__main__":
    main()
