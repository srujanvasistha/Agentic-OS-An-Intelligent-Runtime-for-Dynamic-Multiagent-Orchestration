import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ["AGENTOS_LLM_BACKEND"] = "mock"

from fastapi.testclient import TestClient
from main import app, task_store, agent_manager, task_manager, runtime
from schemas import AgentType, Task, TaskStatus


client = TestClient(app)


def setup_function():
    task_manager.clear()


def test_three_agents_registered():
    assert {
        "GeneralAgent", "FileAgent", "SecurityAgent"
    }.issubset(set(agent_manager.registry.list_agents()))


def test_general_agent_selection():
    agent, capability = agent_manager.select_for_prompt("Explain what an AI agent is")
    assert agent.name == "GeneralAgent"
    assert capability == "general_questions"


def test_file_agent_selection():
    agent, capability = agent_manager.select_for_prompt("list files in the workspace")
    assert agent.name == "FileAgent"
    assert capability == "file_search"


def test_security_agent_selection():
    agent, capability = agent_manager.select_for_prompt("analyze this security vulnerability")
    assert agent.name == "SecurityAgent"
    assert capability == "security_analysis"


def test_api_task_automatically_routes_file_request():
    response = client.post("/api/task", json={"prompt": "list files in the workspace"})
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "FileAgent"
    assert data["task"]["agent_type"] == AgentType.FILE.value
    assert data["error"] is None


def test_api_task_automatically_routes_security_request():
    response = client.post("/api/task", json={"prompt": "analyze this security attack"})
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "SecurityAgent"
    assert data["task"]["agent_type"] == AgentType.SECURITY.value


def test_explicit_agent_type_overrides_router():
    response = client.post(
        "/api/task",
        json={
            "prompt": "explain files",
            "agent_type": "general",
        },
    )
    assert response.status_code == 200
    assert response.json()["agent"] == "GeneralAgent"


def test_route_endpoint_exposes_capability():
    response = client.post("/api/route", json={"prompt": "search files for hello"})
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "FileAgent"
    assert data["capability"] == "file_search"


def test_fifo_scheduler_and_task_manager_lifecycle():
    task = Task(id="fifo-1", prompt="hello")
    runtime.submit(task)
    stored = task_manager.get("fifo-1")
    assert stored.status == TaskStatus.QUEUED
    assert task_manager.queue_size() == 1
    result = runtime.run_next()
    assert result is not None
    assert result.task_id == "fifo-1"
    assert result.status == TaskStatus.DONE
    assert task_manager.get("fifo-1").status == TaskStatus.DONE


def test_runtime_returns_task_result_contract():
    response = client.post("/api/task", json={"prompt": "hello"})
    assert response.status_code == 200
    assert response.json()["status"] == "done"
    assert response.json()["task"]["status"] == "done"


def test_scheduler_interface_is_replaceable():
    from scheduler.base import Scheduler
    from scheduler.fifo import FIFOScheduler
    assert isinstance(FIFOScheduler(), Scheduler)


def test_blocked_status_is_supported():
    task = Task(id="blocked-1", prompt="blocked")
    task_manager.create_task(task)
    queued = task_manager.next_task()
    task_manager.mark_blocked(queued)
    assert task_manager.get("blocked-1").status == TaskStatus.BLOCKED


def test_task_statistics_include_all_day2_statuses():
    data = client.get("/api/stats").json()["tasks"]
    assert set(["queued", "running", "done", "failed", "blocked"]).issubset(data.keys())
