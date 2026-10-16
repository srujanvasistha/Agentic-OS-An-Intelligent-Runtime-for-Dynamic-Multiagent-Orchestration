"""Unit and integration tests for multi-question prompt decomposition and dynamic benchmarks."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ["AGENTOS_LLM_BACKEND"] = "mock"

from fastapi.testclient import TestClient
from main import app, compute_dynamic_benchmark
from agents.task_decomposer import TaskDecomposer


client = TestClient(app)


def test_task_decomposer_numbered_questions():
    prompt = """
    1. Read the configuration file /etc/config.json
    2. Check system CPU and memory load
    3. Audit security logs for root authentication failures
    """
    sub_tasks = TaskDecomposer.decompose(prompt)
    assert len(sub_tasks) == 3
    assert sub_tasks[0]["index"] == 1
    assert sub_tasks[1]["index"] == 2
    assert sub_tasks[2]["index"] == 3
    # Check automated capability routing
    assert sub_tasks[0]["agent_name"] in ["FileAgent", "GeneralAgent"]
    assert sub_tasks[1]["agent_name"] in ["MonitoringAgent", "GeneralAgent"]
    assert sub_tasks[2]["agent_name"] in ["SecurityAgent", "GeneralAgent"]


def test_task_decomposer_explicit_agent_tags():
    prompt = """
    [1] (FileAgent) List files in /workspace/data
    [2] (SecurityAgent) Scan for exposed secrets
    """
    sub_tasks = TaskDecomposer.decompose(prompt)
    assert len(sub_tasks) == 2
    assert sub_tasks[0]["agent_name"] == "FileAgent"
    assert sub_tasks[1]["agent_name"] == "SecurityAgent"
    assert "List files" in sub_tasks[0]["prompt"]


def test_single_prompt_decomposer_passthrough():
    prompt = "Explain what an operating system scheduler does."
    sub_tasks = TaskDecomposer.decompose(prompt)
    assert len(sub_tasks) == 1
    assert sub_tasks[0]["index"] == 1
    assert sub_tasks[0]["agent_name"] == "GeneralAgent"


def test_api_decompose_endpoint():
    payload = {
        "prompt": "1. [FileAgent] check disk usage\n2. [SecurityAgent] audit permissions"
    }
    response = client.post("/api/decompose", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_composite"] is True
    assert len(data["subtasks"]) == 2
    assert data["subtasks"][0]["agent_name"] == "FileAgent"
    assert data["subtasks"][1]["agent_name"] == "SecurityAgent"


def test_composite_instant_task_execution():
    payload = {
        "prompt": """
        [1] (FileAgent) Summarize contents of docs/readme.txt
        [2] (MonitoringAgent) Check system memory usage
        """,
        "scheduler": "resource_aware"
    }
    response = client.post("/api/task", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_composite"] is True
    assert len(data["subtasks"]) == 2
    assert data["status"] == "done"
    assert "Multi-Agent Job Execution Plan" in data["response"]


def test_dynamic_benchmark_data_endpoint():
    response = client.get("/api/benchmark/data")
    assert response.status_code == 200
    data = response.json()
    assert "benchmark_summary" in data
    assert "agent_summary" in data
    assert "recent_prompts" in data
    assert "live_stats" in data
    assert "latency_samples" in data

    # Check live stats structure
    live = data["live_stats"]
    assert "prompt_count" in live
    assert "mean_latency_seconds" in live
    assert "p50_latency_seconds" in live
    assert "p95_latency_seconds" in live
    assert live["prompt_count"] > 0


def test_dynamic_benchmark_live_endpoint():
    response = client.get("/api/benchmark/live")
    assert response.status_code == 200
    data = response.json()
    assert "live_stats" in data
    assert "agent_summary" in data
    assert "benchmark_summary" in data
    assert "recent_prompts" in data
