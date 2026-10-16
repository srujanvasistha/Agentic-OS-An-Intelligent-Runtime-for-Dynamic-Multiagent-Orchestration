import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ["AGENTOS_LLM_BACKEND"] = "mock"

from fastapi.testclient import TestClient
from main import app, task_store
from llm.client import MockLLMClient, LLMResponse, DEFAULT_TPS
from schemas import AgentType, Task, TaskResult, Policy, MetricEvent, TaskStatus
from tools.interface import run_tool


@pytest.fixture(autouse=True)
def clear_tasks():
    task_store.clear()
    yield
    task_store.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["system"] == "AgentOS"


def test_health(client):
    assert client.get("/health").json()["status"] == "healthy"


def test_api_health(client):
    assert client.get("/api/health").status_code == 200


def test_status(client):
    data = client.get("/api/status").json()
    assert data["agents"] >= 3
    assert data["llm_backend"] == "mock"


def test_tools(client):
    assert set(client.get("/api/tools").json()["tools"]) == {"filesystem", "system_info"}


def test_agents(client):
    assert len(client.get("/api/agents").json()["agents"]) >= 3


def test_tasks_empty(client):
    assert client.get("/api/tasks").json() == {"tasks": []}


def test_create_general_task(client):
    r = client.post("/api/task", json={"prompt": "hello"})
    assert r.status_code == 200
    data = r.json()
    assert data["task"]["status"] == "done"
    assert data["llm_backend"] == "mock"
    assert data["tokens_used"] > 0


def test_create_task_has_contract_fields(client):
    data = client.post("/api/task", json={"prompt": "hello", "priority": 10, "complexity": 3, "risk_level": 2, "deadline_s": 30}).json()
    task = data["task"]
    assert task["priority"] == 10
    assert task["complexity"] == 3
    assert task["risk_level"] == 2
    assert task["deadline_s"] == 30
    assert "submitted_at" in task


def test_list_tasks_after_execution(client):
    client.post("/api/task", json={"prompt": "history"})
    data = client.get("/api/tasks").json()
    assert len(data["tasks"]) == 1


def test_route(client):
    data = client.post("/api/route", json={"prompt": "list files"}).json()
    assert data["agent"] == "FileAgent"


def test_invalid_priority(client):
    assert client.post("/api/task", json={"prompt": "x", "priority": 11}).status_code == 422


def test_invalid_complexity(client):
    assert client.post("/api/task", json={"prompt": "x", "complexity": 0}).status_code == 422


def test_mock_llm():
    result = MockLLMClient().generate("hello world")
    assert isinstance(result, LLMResponse)
    assert result.backend == "mock"
    assert result.tokens_used == 2


def test_default_tps():
    assert DEFAULT_TPS == 20.32


def test_tool_boundary_denies():
    result = run_tool("GeneralAgent", "filesystem", {"path": "x"})
    assert result["allowed"] is False
    assert "denied" in result["reason"].lower()


def test_contract_models():
    task = Task(id="1", prompt="x")
    assert task.status == TaskStatus.QUEUED
    result = TaskResult(task_id="1", status=TaskStatus.DONE)
    policy = Policy(name="p")
    event = MetricEvent(task_id="1", event="completed")
    assert result.task_id == task.id
    assert policy.name == "p"
    assert event.event == "completed"
    assert AgentType.GENERAL.value == "general"
