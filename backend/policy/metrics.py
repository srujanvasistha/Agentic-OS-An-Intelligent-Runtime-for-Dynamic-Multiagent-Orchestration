"""Append-only metrics log for policy enforcement and runtime events."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from datetime import datetime
from threading import RLock

_METRIC_LOCK = RLock()

METRIC_COLUMNS = ["timestamp", "task_id", "event", "value", "metadata"]


def append_metric(path: str | Path, task_id: str, event: str, value: float | None = None, metadata: dict[str, Any] | None = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _METRIC_LOCK:
        exists = path.exists() and path.stat().st_size > 0
        with path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=METRIC_COLUMNS)
            if not exists:
                writer.writeheader()
            writer.writerow({
                "timestamp": datetime.now().isoformat(),
                "task_id": task_id,
                "event": event,
                "value": "" if value is None else value,
                "metadata": json.dumps(metadata or {}, sort_keys=True),
            })
