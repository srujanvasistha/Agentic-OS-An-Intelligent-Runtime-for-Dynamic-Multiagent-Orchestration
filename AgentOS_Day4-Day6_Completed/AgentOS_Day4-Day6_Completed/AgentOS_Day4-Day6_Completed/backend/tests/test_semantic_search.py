"""Unit and integration tests for Semantic Search & Intent Engine."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ["AGENTOS_LLM_BACKEND"] = "mock"

from fastapi.testclient import TestClient
from main import app
from search.semantic_search import SemanticSearchEngine, SemanticVectorizer
from agents.task_router import TaskRouter


client = TestClient(app)


def test_semantic_vectorizer_basic():
    vec1 = SemanticVectorizer.vectorize("cpu memory performance monitoring telemetry")
    vec2 = SemanticVectorizer.vectorize("processor cores hardware strain diagnostics")
    sim = SemanticVectorizer.cosine_similarity(vec1, vec2)
    assert sim > 0.0, "Related concepts should have positive cosine similarity"


def test_semantic_intent_classification_without_keywords():
    engine = SemanticSearchEngine()
    
    # Prompt with NO literal keywords from the old keyword list
    prompt_sec = "Examine if unauthorized intruders compromised confidential credentials or escalated standing"
    cap, conf, _ = engine.classify_intent(prompt_sec)
    assert cap == "security_analysis", f"Expected security_analysis, got {cap}"
    assert conf > 0.10

    # Prompt with conceptual hardware strain without saying "cpu" or "ram"
    prompt_mon = "Inspect hardware strain, thermal throttling, and volatile cache bottlenecks"
    cap, conf, _ = engine.classify_intent(prompt_mon)
    assert cap == "monitoring", f"Expected monitoring, got {cap}"
    assert conf > 0.10


def test_task_router_semantic_classification():
    router = TaskRouter()

    # Test semantic routing for prompts without standard keywords
    cap1 = router.classify("Assess unauthorized actors trying to exfiltrate secret tokens")
    assert cap1 == "security_analysis"

    cap2 = router.classify("Check compute core saturation and telemetry anomalies")
    assert cap2 == "monitoring"

    # Test that existing classic keyword prompts still route properly
    assert router.classify("Explain what an AI agent is") == "general_questions"
    assert router.classify("read config.json") == "file_search"


def test_semantic_search_api_get():
    response = client.get("/api/search/semantic?q=security+credentials+vulnerabilities")
    assert response.status_code == 200
    data = response.json()
    assert "semantic_intent" in data
    assert data["semantic_intent"]["capability"] == "security_analysis"
    assert "workspace_matches" in data
    assert "task_matches" in data


def test_semantic_search_api_post():
    payload = {
        "query": "telemetry metrics and processor hardware utilization",
        "target": "all",
        "top_k": 3
    }
    response = client.post("/api/search/semantic", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["semantic_intent"]["capability"] == "monitoring"
    assert isinstance(data["workspace_matches"], list)
