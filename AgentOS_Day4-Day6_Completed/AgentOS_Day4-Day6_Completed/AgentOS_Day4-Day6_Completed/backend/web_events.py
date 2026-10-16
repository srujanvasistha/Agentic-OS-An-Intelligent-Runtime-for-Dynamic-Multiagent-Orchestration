"""Thread-safe event and blocked-action history shared by API and tool boundary."""
from __future__ import annotations
from collections import deque
from datetime import datetime, timezone
from threading import RLock
from typing import Any

_lock = RLock()
_events = deque(maxlen=1000)
_blocked = deque(maxlen=500)


def emit_event(event: dict[str, Any]) -> dict[str, Any]:
    item = {"timestamp": datetime.now(timezone.utc).isoformat(), **event}
    with _lock:
        _events.append(item)
    return item


def record_blocked_action(action: dict[str, Any]) -> dict[str, Any]:
    item = {"timestamp": datetime.now(timezone.utc).isoformat(), **action}
    with _lock:
        _blocked.appendleft(item)
        _events.append({"timestamp": item["timestamp"], "type": "blocked_action", **action})
    return item


def get_events_since(index: int):
    with _lock:
        events = list(_events)
    return events[index:], len(events)


def list_blocked_actions():
    with _lock:
        return list(_blocked)


def clear_events():
    with _lock:
        _events.clear()
        _blocked.clear()
