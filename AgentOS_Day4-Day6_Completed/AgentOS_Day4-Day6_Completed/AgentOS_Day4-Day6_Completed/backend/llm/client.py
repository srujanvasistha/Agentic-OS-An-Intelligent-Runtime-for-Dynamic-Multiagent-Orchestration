"""Common LLM interface for AgentOS.

Day 1 keeps model selection behind one small interface so agents do not
need to know whether inference is provided by Ollama or the deterministic
mock backend used for offline development and tests.
"""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import requests

DEFAULT_TPS = 20.32  # measured on the project machine with qwen2.5:1.5b


@dataclass
class LLMResponse:
    text: str
    tokens_used: int = 0
    latency_seconds: float = 0.0
    backend: str = "unknown"
    model: str = "unknown"


class LLMClient(ABC):
    """Stable interface used by AgentOS agents."""

    @abstractmethod
    def generate(self, prompt: str) -> LLMResponse:
        raise NotImplementedError


class OllamaLLMClient(LLMClient):
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
        self.timeout = float(timeout or os.getenv("OLLAMA_TIMEOUT", "120"))

    def generate(self, prompt: str) -> LLMResponse:
        started = time.perf_counter()
        num_gpu = int(os.getenv("OLLAMA_NUM_GPU", "0"))
        num_predict = int(os.getenv("OLLAMA_NUM_PREDICT", "256"))
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_gpu": num_gpu, "num_predict": num_predict},
        }
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            if response.status_code == 404:
                raise RuntimeError(
                    f"Ollama model '{self.model}' not found at {self.base_url}. "
                    f"Please run 'ollama pull {self.model}' to download it."
                )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            latency = time.perf_counter() - started
            return LLMResponse(
                text=data.get("response", "").strip() or "No response generated.",
                tokens_used=int(data.get("eval_count") or 0),
                latency_seconds=latency,
                backend="ollama",
                model=self.model,
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException) as exc:
            latency = time.perf_counter() - started
            tokens = max(1, min(64, len(prompt.split())))
            return LLMResponse(
                text=f"Task executed with fallback response: {prompt.strip()[:180]} (Backend note: {exc.__class__.__name__})",
                tokens_used=tokens,
                latency_seconds=latency,
                backend="fallback",
                model=self.model,
            )


class MockLLMClient(LLMClient):
    """Deterministic offline backend.

    It deliberately does not call a model. The measured TPS is retained as a
    scheduling estimate so experiments can compare model-backed and offline
    execution without requiring Ollama on every developer machine.
    """

    def __init__(self, model: str = "mock-qwen2.5:1.5b", tps: float = DEFAULT_TPS):
        self.model = model
        self.tps = float(tps)

    def generate(self, prompt: str) -> LLMResponse:
        started = time.perf_counter()
        tokens = max(1, min(64, len(prompt.split())))
        text = f"[MockLLM] Task received: {prompt.strip()}"
        latency = max(time.perf_counter() - started, tokens / self.tps)
        return LLMResponse(
            text=text,
            tokens_used=tokens,
            latency_seconds=latency,
            backend="mock",
            model=self.model,
        )


def create_llm_client() -> LLMClient:
    backend = os.getenv("AGENTOS_LLM_BACKEND", "").strip().lower()
    if backend == "mock":
        return MockLLMClient()
    if backend == "ollama":
        return OllamaLLMClient()

    # When AGENTOS_LLM_BACKEND is not explicitly specified, auto-detect:
    # If Ollama is running and has the model installed, use Ollama; otherwise fallback to Mock.
    try:
        url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
        res = requests.get(f"{url}/api/tags", timeout=1.5)
        if res.status_code == 200:
            models = [m.get("name", "") for m in res.json().get("models", [])]
            if any(model == name or name.startswith(model) for name in models):
                return OllamaLLMClient()
    except Exception:
        pass

    return MockLLMClient()
