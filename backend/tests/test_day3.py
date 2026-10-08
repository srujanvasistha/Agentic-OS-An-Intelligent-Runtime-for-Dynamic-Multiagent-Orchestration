import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ["AGENTOS_LLM_BACKEND"] = "mock"

from fastapi.testclient import TestClient
from schemas import Task
from main import app, task_manager, runtime
from scheduler.factory import create_scheduler
from scheduler.fifo import FIFOScheduler
from scheduler.round_robin import RoundRobinScheduler
from scheduler.priority import PriorityScheduler
from scheduler.resource_aware import ResourceAwareScheduler


class FakeMonitor:
    def __init__(self, cpu=10, memory=20):
        self.cpu = cpu
        self.memory = memory

    def get_system_state(self):
        return {
            "cpu_percent": self.cpu,
            "memory_percent": self.memory,
            "available_memory_mb": 8000,
            "cpu_count": 12,
        }


def setup_function():
    task_manager.clear()


def test_all_four_schedulers_are_available():
    assert isinstance(create_scheduler("fifo"), FIFOScheduler)
    assert isinstance(create_scheduler("round_robin"), RoundRobinScheduler)
    assert isinstance(create_scheduler("priority"), PriorityScheduler)
    assert isinstance(create_scheduler("resource_aware"), ResourceAwareScheduler)


def test_priority_scheduler_changes_order():
    scheduler = PriorityScheduler()
    low = Task(id="low", prompt="low", priority=1)
    high = Task(id="high", prompt="high", priority=10)
    scheduler.enqueue(low)
    scheduler.enqueue(high)
    assert scheduler.next_task().id == "high"


def test_round_robin_rotates_agent_types():
    scheduler = RoundRobinScheduler()
    tasks = [
        Task(id="g1", prompt="g1"),
        Task(id="g2", prompt="g2"),
        Task(id="f1", prompt="f1", agent_type="file"),
    ]
    for task in tasks:
        scheduler.enqueue(task)
    first = scheduler.next_task()
    second = scheduler.next_task()
    assert {first.id, second.id} == {"g1", "f1"}


def test_resource_aware_prefers_small_task_under_pressure():
    scheduler = ResourceAwareScheduler()
    scheduler.set_system_state({"cpu_percent": 90, "memory_percent": 50})
    scheduler.enqueue(Task(id="large", prompt="large", estimated_tokens=1000))
    scheduler.enqueue(Task(id="small", prompt="small", estimated_tokens=50))
    assert scheduler.next_task().id == "small"


def test_monitor_state_is_passed_to_scheduler():
    scheduler = ResourceAwareScheduler()
    scheduler.set_system_state({"cpu_percent": 90, "memory_percent": 50})
    assert scheduler._pressure() == 90


def test_runtime_supports_model_tiers_with_mock():
    from agents.general_agent import GeneralAgent
    from llm.client import MockLLMClient
    from agents.agent_registry import AgentRegistry
    from agents.agent_manager import AgentManager
    from agents.task_router import TaskRouter
    from scheduler.task_store import TaskStore
    from scheduler.task_manager import TaskManager
    from scheduler.runtime import AgentRuntime

    registry = AgentRegistry()
    registry.register("GeneralAgent", GeneralAgent(llm_client=MockLLMClient()))
    manager = AgentManager(registry, TaskRouter())
    store = TaskStore()
    tm = TaskManager(FIFOScheduler(), store)
    rt = AgentRuntime(tm, manager, monitor=FakeMonitor(), model_tier="0.5b", concurrency_limit=1)

    task = Task(id="tier", prompt="hello")
    rt.submit(task)
    result = rt.run_next()
    assert result.status.value == "done"
    assert result.model == "qwen2.5:0.5b"


def test_runtime_concurrency_limit_two():
    # Exercise the public runtime batch interface with two queued tasks.
    from scheduler.task_store import TaskStore
    from scheduler.task_manager import TaskManager
    from scheduler.runtime import AgentRuntime
    from agents.agent_registry import AgentRegistry
    from agents.agent_manager import AgentManager
    from agents.task_router import TaskRouter
    from agents.general_agent import GeneralAgent
    from llm.client import MockLLMClient

    registry = AgentRegistry()
    registry.register("GeneralAgent", GeneralAgent(llm_client=MockLLMClient()))
    manager = AgentManager(registry, TaskRouter())
    store = TaskStore()
    tm = TaskManager(FIFOScheduler(), store)
    rt = AgentRuntime(tm, manager, monitor=FakeMonitor(), concurrency_limit=2)

    rt.submit(Task(id="c1", prompt="one"))
    rt.submit(Task(id="c2", prompt="two"))
    results = rt.run_pending()
    assert len(results) == 2
    assert {r.status.value for r in results} == {"done"}


def test_api_status_exposes_day3_runtime_config():
    client = TestClient(app)
    data = client.get("/api/status").json()
    assert data["scheduler"] in {"fifo", "round_robin", "priority", "resource_aware"}
    assert set(data["scheduler_options"]) == {"fifo", "round_robin", "priority", "resource_aware"}
    assert data["concurrency_limit"] in {1, 2}
    assert data["model_tier"] in {"0.5b", "1.5b"}


def test_end_to_end_file_agent_tool_result():
    client = TestClient(app)
    response = client.post("/api/task", json={
        "prompt": "list files in the workspace",
        "agent_type": "file",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "FileAgent"
    assert data["status"] == "done"
    assert data["response"]
