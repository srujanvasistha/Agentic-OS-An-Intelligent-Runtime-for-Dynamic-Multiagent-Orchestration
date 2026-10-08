"""System-state provider used by Day 3 schedulers."""

from __future__ import annotations

import os
import psutil


def get_system_state() -> dict:
    """Return lightweight, scheduler-safe host telemetry."""
    memory = psutil.virtual_memory()
    return {
        "cpu_percent": float(psutil.cpu_percent(interval=None)),
        "memory_percent": float(memory.percent),
        "available_memory_mb": round(memory.available / (1024 * 1024), 2),
        "cpu_count": int(os.cpu_count() or 1),
    }
