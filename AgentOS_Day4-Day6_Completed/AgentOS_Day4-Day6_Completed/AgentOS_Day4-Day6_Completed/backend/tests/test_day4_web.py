"""Day 4 local web shell/API integration tests."""
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ["AGENTOS_LLM_BACKEND"] = "mock"

from fastapi.testclient import TestClient
from main import app, task_manager, task_store
from scheduler.fifo import FIFOScheduler
from tools.interface import run_tool

client = TestClient(app)


def setup_function():
    task_manager.clear()
    task_manager.scheduler = FIFOScheduler()


def test_browser_root_serves_local_static_shell():
    response = client.get("/", headers={"accept": "text/html"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "AI Shell" in response.text
    assert "/static/app.js" in response.text


def test_task_submit_returns_id_and_can_be_polled():
    response = client.post("/task", json={"prompt": "Explain the FIFO scheduler"})
    assert response.status_code == 200
    submitted = response.json()
    assert submitted["task_id"]
    assert submitted["status"] == "queued"

    deadline = time.time() + 5
    result = None
    while time.time() < deadline:
        result = client.get(f"/task/{submitted['task_id']}").json()
        if result.get("status") in {"done", "failed", "blocked"}:
            break
        time.sleep(0.05)
    assert result is not None
    assert result["task_id"] == submitted["task_id"]
    assert result["status"] == "done"
    assert result["result"]["response"]


def test_history_metrics_and_scheduler_switch_contracts():
    response = client.post("/api/task", json={"prompt": "hello from day four"})
    assert response.status_code == 200
    history = client.get("/history").json()
    assert history["storage"] == "sqlite"
    assert any(item["task_id"] == response.json()["task"]["id"] for item in history["tasks"])

    metrics = client.get("/metrics").json()
    assert {"cpu_percent", "ram_percent", "tokens_total", "queue_length", "latency_seconds"}.issubset(metrics)

    switched = client.post("/scheduler", json={"scheduler": "priority"})
    assert switched.status_code == 200
    assert switched.json()["scheduler"] == "Priority"
    assert client.get("/scheduler").json()["scheduler"] == "Priority"
    client.post("/scheduler", json={"scheduler": "fifo"})


def test_denied_tool_calls_appear_in_blocked_audit():
    decision = run_tool("GeneralAgent", "shell", {"command": "whoami"})
    assert decision["allowed"] is False
    blocked = client.get("/blocked").json()["blocked_actions"]
    assert blocked
    assert "shell" in blocked[0]["action"]
    assert blocked[0]["reason"]


def test_websocket_stream_connects_and_receives_policy_events():
    with client.websocket_connect("/stream") as websocket:
        assert websocket.receive_json()["type"] == "connected"
        run_tool("GeneralAgent", "network", {"url": "https://example.invalid"})
        event = websocket.receive_json()
        assert event["type"] == "blocked_action"
        assert event["action"] == "network"


def test_results_tab_lists_generated_pngs_and_pdfs():
    response = client.get("/api/results/figures")
    assert response.status_code == 200
    figures = response.json()["figures"]
    names = {item["name"] for item in figures}
    assert "latency_p50.png" in names
    assert "latency_p95.png" in names
    assert "blocked_actions.png" in names
    png = client.get("/results/figures/latency_p50.png")
    assert png.status_code == 200
    assert png.headers["content-type"].startswith("image/png")


def test_standalone_shell_javascript_is_served_locally():
    response = client.get("/static/app.js")
    assert response.status_code == 200
    assert "refreshMetrics" in response.text
    assert "run" in response.text
