"""Standalone Day 5 failure-path validation for the v1 freeze."""

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

from fastapi.testclient import TestClient
from agents.agent_manager import AgentManager
from agents.agent_registry import AgentRegistry
from agents.general_agent import GeneralAgent
from agents.task_router import TaskRouter
from llm.client import LLMClient, LLMResponse, OllamaLLMClient
from policy.engine import configure_policy_engine
from scheduler.fifo import FIFOScheduler
from scheduler.runtime import AgentRuntime
from scheduler.task_manager import TaskManager
from scheduler.task_store import TaskStore
from schemas import Task
from tools.filesystem import FileSystemTool
from tools.registry import ToolRegistry
from main import app


def runtime_with(agent: GeneralAgent) -> AgentRuntime:
    registry = AgentRegistry()
    registry.register("GeneralAgent", agent)
    manager = AgentManager(registry, TaskRouter())
    tm = TaskManager(FIFOScheduler(), TaskStore())
    return AgentRuntime(tm, manager)


def main() -> None:
    client = TestClient(app)
    malformed = client.post("/api/task", json={"priority": 20})
    assert malformed.status_code == 422
    print("malformed task: PASS")

    class TimeoutClient(LLMClient):
        def generate(self, prompt: str) -> LLMResponse:
            raise TimeoutError("model timeout during inference")

    rt = runtime_with(GeneralAgent(llm_client=TimeoutClient()))
    task = Task(id="day5-timeout", prompt="timeout")
    rt.submit(task)
    result = rt.run_next()
    assert result.status.value == "failed" and "timeout" in result.error.lower()
    print("model timeout: PASS")

    registry = ToolRegistry()
    registry.register("filesystem", FileSystemTool(ROOT))
    metrics = ROOT / "experiments" / "day5_failure_metrics.csv"
    if metrics.exists():
        metrics.unlink()
    engine = configure_policy_engine(registry, metrics, enforcement=True)
    try:
        engine.execute("GeneralAgent", "filesystem", {"operation": "list_files", "_task_id": "day5-denied"})
        raise AssertionError("policy should deny filesystem to GeneralAgent")
    except PermissionError:
        pass
    rows = list(csv.DictReader(metrics.open(encoding="utf-8")))
    assert any(row["event"] == "tool_blocked" for row in rows)
    print("denied action: PASS")

    down = OllamaLLMClient(base_url="http://127.0.0.1:1", timeout=0.2)
    rt = runtime_with(GeneralAgent(llm_client=down))
    task = Task(id="day5-ollama-down", prompt="ollama down")
    rt.submit(task)
    result = rt.run_next()
    assert result.status.value == "failed"
    print("Ollama unavailable: PASS")

    print("All Day 5 failure paths passed.")


if __name__ == "__main__":
    main()
