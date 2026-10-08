"""Run the Day 5 v1 MockLLM workload and validate the agreed CSV schema."""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ["AGENTOS_LLM_BACKEND"] = "mock"
os.environ["AGENTOS_POLICY_ENFORCEMENT"] = "on"

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


OUTPUT = ROOT / "experiments" / "day5_mock_workload.csv"


def main() -> None:
    registry = AgentRegistry()
    registry.register("GeneralAgent", GeneralAgent(llm_client=MockLLMClient()))
    manager = AgentManager(registry, TaskRouter())
    store = TaskStore()
    task_manager = TaskManager(FIFOScheduler(), store)
    runtime = AgentRuntime(task_manager, manager, results_path=OUTPUT, model_tier="1.5b")

    if OUTPUT.exists():
        OUTPUT.unlink()

    workload = [
        "Explain the AgentOS scheduler.",
        "Explain why policy enforcement is useful.",
        "Summarize the purpose of the system monitor.",
        "Explain how runtime memory supports later tasks.",
        "Describe the AgentOS end-to-end request flow.",
    ]
    for index, prompt in enumerate(workload, start=1):
        runtime.submit(Task(id=f"day5-mock-{index}", prompt=prompt))

    results = runtime.run_until_empty()
    assert len(results) == len(workload)
    assert all(result.status.value == "done" for result in results)

    with OUTPUT.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == RESULT_COLUMNS
        rows = list(reader)
    assert len(rows) == len(workload)
    assert {row["llm_backend"] for row in rows} == {"mock"}

    print(f"Day 5 MockLLM workload: {len(rows)} tasks completed")
    print(f"CSV schema validated: {OUTPUT}")


if __name__ == "__main__":
    main()
