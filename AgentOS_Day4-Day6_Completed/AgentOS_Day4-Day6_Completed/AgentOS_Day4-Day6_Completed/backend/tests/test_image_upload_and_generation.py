"""Tests for image uploading and image generation in AgentOS."""
import base64
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


def test_image_upload_endpoint_json():
    # 1x1 transparent png in base64
    tiny_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    payload = {
        "image": tiny_png_b64,
        "filename": "test_upload.png",
    }
    response = client.post("/api/upload/image", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "test_upload.png" in data["filename"]
    assert data["url"].startswith("/static/uploads/")
    assert data["width"] >= 1
    assert data["height"] >= 1


def test_image_generate_endpoint():
    payload = {
        "prompt": "generate image of AgentOS system architecture diagram",
        "width": 800,
        "height": 500,
    }
    response = client.post("/api/generate/image", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["url"].startswith("/static/generated/")
    assert data["width"] == 800
    assert data["height"] == 500
    assert Path(data["path"]).is_file()


def test_task_routing_to_image_agent():
    # Test route preview
    payload = {
        "prompt": "generate an image of futuristic neural cluster network",
    }
    response = client.post("/api/route", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "ImageAgent"
    assert data["capability"] == "image_generation"


def test_image_generation_task_execution():
    payload = {
        "prompt": "create an image of cyberpunk orbital core",
        "priority": 7,
    }
    response = client.post("/api/task", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "ImageAgent"
    assert data["status"] == "done"
    assert "/static/generated/" in data["response"]
    assert data.get("image_url") is not None
    assert "/static/generated/" in data["image_url"]


def test_image_upload_task_integration():
    # Upload an image first
    tiny_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    upload_res = client.post("/api/upload/image", json={"image": tiny_png_b64, "filename": "sample.png"})
    assert upload_res.status_code == 200
    uploaded_url = upload_res.json()["url"]

    # Run task referencing uploaded image
    task_payload = {
        "prompt": f"analyze and enhance uploaded image {uploaded_url}",
        "image_url": uploaded_url,
    }
    task_res = client.post("/api/task", json=task_payload)
    assert task_res.status_code == 200
    task_data = task_res.json()
    assert task_data["status"] == "done"
    assert task_data.get("image_url") is not None


def test_figures_generation_endpoint():
    response = client.post("/api/figures/generate")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["success", "warning"]
    assert "figures" in data


def test_image_analysis_routing_variations():
    """Verify that user queries with various phrasing and spellings route accurately to ImageAgent."""
    prompts = [
        "analyse my image and let me know what is there in the image",
        "analyse the image and tell the output",
        "what is there in the image",
        "what is in this image",
        "explain this image",
        "describe this picture",
    ]
    for p in prompts:
        res = client.post("/api/route", json={"prompt": p})
        assert res.status_code == 200
        assert res.json()["agent"] == "ImageAgent"
        assert res.json()["capability"] == "image_analysis"


def test_image_agent_ocr_text_extraction():
    """Verify ImageAgent extracts and reports printed text from uploaded documents/quotes."""
    txt_img_path = ROOT / "backend" / "static" / "uploads" / "6348b14f_sample_txt_img.png"
    if txt_img_path.is_file():
        from agents.image_agent import ImageAgent
        agent = ImageAgent()
        res = agent.run("analyse the image and tell the output", image_url=str(txt_img_path))
        assert "It was the best of times" in res
        assert "Text Document" in res
        assert "OCR" in res


def test_image_agent_landscape_scene_classification():
    """Verify ImageAgent accurately classifies natural photos rather than false-positiving as diagrams."""
    photo_path = ROOT / "backend" / "static" / "uploads" / "8419bd8e_d1.jpg"
    if photo_path.is_file():
        from agents.image_agent import ImageAgent
        agent = ImageAgent()
        res = agent.run("analyse my image and let me know what is there in the image", image_url=str(photo_path))
        assert "Photographic" in res
        assert "Landscape" in res or "Nature" in res
        assert "Detailed Infographic" not in res


def test_image_agent_analysis_without_image_returns_guidance():
    """Verify that requesting analysis without providing an image provides helpful instructions instead of fake images."""
    from agents.image_agent import ImageAgent
    agent = ImageAgent()
    res = agent.run("analyse my image and let me know what is there in the image", image_url=None)
    assert "Image Required" in res
    assert "Attach Image" in res
