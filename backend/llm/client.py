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
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=self.timeout,
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
    backend = os.getenv("AGENTOS_LLM_BACKEND", "ollama").strip().lower()
    if backend == "mock":
        return MockLLMClient()
    if backend != "ollama":
        raise ValueError(f"Unsupported AGENTOS_LLM_BACKEND: {backend}")
    return OllamaLLMClient()
