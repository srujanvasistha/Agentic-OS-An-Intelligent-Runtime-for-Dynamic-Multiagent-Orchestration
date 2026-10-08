import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ["AGENTOS_LLM_BACKEND"] = "mock"
os.environ["AGENTOS_POLICY_ENFORCEMENT"] = "on"

from fastapi.testclient import TestClient
from main import app, task_manager, runtime
from llm.client import LLMClient, LLMResponse, OllamaLLMClient
from schemas import Task
from agents.general_agent import GeneralAgent
from agents.agent_registry import AgentRegistry
from agents.agent_manager import AgentManager
from agents.task_router import TaskRouter
from scheduler.fifo import FIFOScheduler
from scheduler.task_manager import TaskManager
from scheduler.task_store import TaskStore
from scheduler.runtime import AgentRuntime


client = TestClient(app)


def setup_function():
    task_manager.clear()
    runtime.memory.clear()


def test_full_v1_flow_exposes_memory_and_runtime_components():
    response = client.post("/api/task", json={"prompt": "Explain scheduler integration"})
    assert response.status_code == 200
    assert response.json()["status"] == "done"
    status = client.get("/api/status").json()
    assert status["scheduler"] in {"fifo", "round_robin", "priority", "resource_aware"}
    assert status["memory_entries"] >= 1
    assert client.get("/api/memory").json()["entries"]


def test_mock_workload_result_matches_csv_schema(tmp_path):
    from results_csv import RESULT_COLUMNS
    from llm.client import MockLLMClient
    from agents.agent_registry import AgentRegistry
    from agents.agent_manager import AgentManager
    from agents.task_router import TaskRouter

    registry = AgentRegistry()
    registry.register("GeneralAgent", GeneralAgent(llm_client=MockLLMClient()))
    manager = AgentManager(registry, TaskRouter())
    store = TaskStore()
    task_manager_local = TaskManager(FIFOScheduler(), store)
    result_path = tmp_path / "results.csv"
    rt = AgentRuntime(task_manager_local, manager, results_path=result_path, model_tier="1.5b")
    for index in range(5):
        rt.submit(Task(id=f"mock-{index}", prompt=f"workload task {index}"))
    results = rt.run_until_empty()
    assert len(results) == 5
    assert all(result.status.value == "done" for result in results)
    with result_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == RESULT_COLUMNS
        rows = list(reader)
    assert len(rows) == 5
    assert {row["llm_backend"] for row in rows} == {"mock"}


def test_malformed_task_is_rejected():
    response = client.post("/api/task", json={"priority": 20})
    assert response.status_code == 422


def test_model_timeout_failure_path():
    class TimeoutClient(LLMClient):
        def generate(self, prompt: str) -> LLMResponse:
            raise TimeoutError("model timeout during inference")

    registry = AgentRegistry()
    registry.register("GeneralAgent", GeneralAgent(llm_client=TimeoutClient()))
    manager = AgentManager(registry, TaskRouter())
    store = TaskStore()
    tm = TaskManager(FIFOScheduler(), store)
    rt = AgentRuntime(tm, manager)
    task = Task(id="timeout-1", prompt="timeout test")
    rt.submit(task)
    result = rt.run_next()
    assert result.status.value == "failed"
    assert "timeout" in result.error.lower()


def test_denied_action_failure_path(tmp_path):
    from policy.engine import configure_policy_engine
    from tools.registry import ToolRegistry
    from tools.filesystem import FileSystemTool

    registry = ToolRegistry()
    registry.register("filesystem", FileSystemTool(ROOT))
    metrics = tmp_path / "metrics.csv"
    engine = configure_policy_engine(registry, metrics, enforcement=True)
    try:
        result = engine.execute("GeneralAgent", "filesystem", {"operation": "list_files", "_task_id": "denied-1"})
        assert False, result
    except PermissionError as exc:
        assert "denied" in str(exc).lower()
    rows = list(csv.DictReader(metrics.open(encoding="utf-8")))
    assert any(row["event"] == "tool_blocked" and row["task_id"] == "denied-1" for row in rows)
    configure_policy_engine(registry=None, metrics_path=None, enforcement=True)


def test_ollama_down_failure_path():
    client_llm = OllamaLLMClient(base_url="http://127.0.0.1:1", model="qwen2.5:1.5b", timeout=0.2)
    registry = AgentRegistry()
    registry.register("GeneralAgent", GeneralAgent(llm_client=client_llm))
    manager = AgentManager(registry, TaskRouter())
    store = TaskStore()
    tm = TaskManager(FIFOScheduler(), store)
    rt = AgentRuntime(tm, manager)
    task = Task(id="ollama-down-1", prompt="ollama down test")
    rt.submit(task)
    result = rt.run_next()
    assert result.status.value == "failed"
    assert result.error
