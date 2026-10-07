"""CSV schema and writer for AgentOS experiments."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

RESULT_COLUMNS = [
    "timestamp",
    "task_id",
    "agent",
    "model",
    "status",
    "priority",
    "complexity",
    "risk_level",
    "estimated_tokens",
    "tokens_used",
    "llm_latency_seconds",
    "latency_seconds",
    "llm_backend",
]


def append_result(path: str | Path, row: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_COLUMNS, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow({column: row.get(column, "") for column in RESULT_COLUMNS})
