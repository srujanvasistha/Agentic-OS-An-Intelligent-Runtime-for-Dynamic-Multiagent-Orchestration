"""Scheduler selection and Day 3 runtime configuration."""

from __future__ import annotations

import os

from scheduler.fifo import FIFOScheduler
from scheduler.priority import PriorityScheduler
from scheduler.resource_aware import ResourceAwareScheduler
from scheduler.round_robin import RoundRobinScheduler


SCHEDULER_NAMES = ("fifo", "round_robin", "priority", "resource_aware")


def create_scheduler(name: str | None = None, system_state_provider=None):
    selected = (name or os.getenv("AGENTOS_SCHEDULER", "fifo")).strip().lower()
    aliases = {
        "round-robin": "round_robin",
        "roundrobin": "round_robin",
        "priority": "priority",
        "resource-aware": "resource_aware",
        "resource": "resource_aware",
    }
    selected = aliases.get(selected, selected)
    schedulers = {
        "fifo": FIFOScheduler,
        "round_robin": RoundRobinScheduler,
        "priority": PriorityScheduler,
        "resource_aware": lambda: ResourceAwareScheduler(system_state_provider),
    }
    if selected not in schedulers:
        raise ValueError(
            f"Unsupported AGENTOS_SCHEDULER={selected!r}. "
            f"Choose one of: {', '.join(SCHEDULER_NAMES)}"
        )
    return schedulers[selected]()
