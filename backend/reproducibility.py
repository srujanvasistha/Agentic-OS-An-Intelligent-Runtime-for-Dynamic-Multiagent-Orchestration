"""Seed Python's supported pseudo-random generators for repeatable experiments."""

from __future__ import annotations

import os
import random


def configure_reproducibility(seed: int | None = None) -> int:
    """Set process seed configuration and seed Python's random module.

    PYTHONHASHSEED only affects hash randomization when set before process start;
    the launcher sets it before starting Python. This function also seeds random.
    If NumPy is installed by an experiment extension, seed it without requiring it.
    """
    chosen = int(os.getenv("AGENTOS_SEED", "42")) if seed is None else int(seed)
    os.environ["AGENTOS_SEED"] = str(chosen)
    random.seed(chosen)
    try:
        import numpy as np  # optional; core AgentOS does not require NumPy
        np.random.seed(chosen)
    except ImportError:
        pass
    return chosen
