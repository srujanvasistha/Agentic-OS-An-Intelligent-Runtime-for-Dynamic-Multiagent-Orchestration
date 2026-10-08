"""Environment-backed Day 3 runtime configuration."""

from __future__ import annotations

import os


MODEL_TIERS = {
    "0.5b": "qwen2.5:0.5b",
    "1.5b": "qwen2.5:1.5b",
}


def model_for_tier(tier: str) -> str:
    key = tier.strip().lower()
    if key not in MODEL_TIERS:
        raise ValueError(f"Unsupported model tier {tier!r}; choose 0.5b or 1.5b")
    return MODEL_TIERS[key]


def default_model_tier() -> str:
    tier = os.getenv("AGENTOS_MODEL_TIER", "1.5b").strip().lower()
    if tier not in MODEL_TIERS:
        raise ValueError("AGENTOS_MODEL_TIER must be 0.5b or 1.5b")
    return tier


def max_concurrency() -> int:
    value = int(os.getenv("AGENTOS_MAX_CONCURRENCY", "1"))
    if value not in (1, 2):
        raise ValueError("AGENTOS_MAX_CONCURRENCY must be 1 or 2")
    return value
