"""Voice Input integration and safety tests for AgentOS P5.

Verifies Web Speech API integration, frontend asset serving,
and seamless compatibility with existing /api/task and /task endpoints.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ["AGENTOS_LLM_BACKEND"] = "mock"

from fastapi.testclient import TestClient
from main import app, task_manager
from scheduler.fifo import FIFOScheduler

client = TestClient(app)


def setup_function():
    task_manager.clear()
    task_manager.scheduler = FIFOScheduler()


def test_voice_input_script_served_locally():
    """Verify that voice_input.js is properly mounted and served."""
    response = client.get("/static/voice_input.js")
    assert response.status_code == 200
    assert "SpeechRecognition" in response.text
    assert "btn-voice-mic" in response.text
    assert "attachVoiceInput" in response.text


def test_standalone_shell_includes_voice_button_and_script():
    """Verify that the fallback / standalone shell provides native voice controls."""
    response = client.get("/static/index.html")
    assert response.status_code == 200
    assert "voiceBtn" in response.text
    assert "voiceStatus" in response.text
    assert "btn-voice" in response.text

    app_js = client.get("/static/app.js")
    assert app_js.status_code == 200
    assert "initVoiceInput" in app_js.text
    assert "SpeechRecognition" in app_js.text


def test_web_dashboard_includes_voice_input_script():
    """Verify that the built web dashboard index.html includes the voice_input script."""
    response = client.get("/", headers={"accept": "text/html"})
    assert response.status_code == 200
    assert "voice_input.js" in response.text


def test_voice_transcribed_task_submission_api_task():
    """Simulate a voice-transcribed prompt submitted through /api/task.

    A voice prompt must be processed identically to a typed task without schema changes.
    """
    voice_transcript = "Explain how the resource aware scheduler prevents CPU starvation"
    response = client.post(
        "/api/task",
        json={
            "prompt": voice_transcript,
            "priority": 7,
            "estimated_tokens": 128,
            "complexity": 2,
            "risk_level": 1,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["task"]["prompt"] == voice_transcript
    assert data["task"]["priority"] == 7
    assert data["status"] in {"done", "failed", "blocked"}
    assert "agent" in data
    assert data["response"]


def test_voice_transcribed_task_submission_queue_and_poll():
    """Simulate a voice-transcribed prompt dispatched to the scheduler queue via /task."""
    voice_transcript = "Analyze host memory metrics and detect anomalous spikes"
    response = client.post(
        "/task",
        json={
            "prompt": voice_transcript,
            "priority": 5,
            "estimated_tokens": 256,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"
    assert data["task_id"]
    task_id = data["task_id"]

    # Poll status
    poll_res = client.get(f"/task/{task_id}")
    assert poll_res.status_code == 200
    poll_data = poll_res.json()
    assert poll_data["prompt"] == voice_transcript
    assert poll_data["task_id"] == task_id


def test_voice_transcribed_empty_prompt_is_rejected():
    """Verify that an empty transcription cannot be submitted accidentally."""
    response = client.post("/api/task", json={"prompt": ""})
    assert response.status_code == 422  # Validation error (min_length=1)


def test_general_agent_lock_and_normalization():
    """Verify that target-locking 'GeneralAgent' normalizes correctly and executes."""
    response = client.post(
        "/api/task",
        json={
            "prompt": "Explain the concept of process isolation.",
            "agent_type": "GeneralAgent",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "GeneralAgent"
    assert data["status"] == "done"
    assert data["response"]


def test_general_agent_auto_routing():
    """Verify general conversational/reasoning queries route to GeneralAgent."""
    response = client.post(
        "/api/task",
        json={
            "prompt": "What are the fundamental objectives of an operating system kernel?",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "GeneralAgent"
    assert data["status"] == "done"

