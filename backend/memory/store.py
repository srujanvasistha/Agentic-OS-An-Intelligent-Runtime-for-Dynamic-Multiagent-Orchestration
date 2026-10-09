"""Small persistent-free runtime memory used by the AgentOS v1 prototype.

Memory is deliberately bounded and process-local for the v1 freeze. It keeps
recent task summaries available to later tasks without introducing a database
that would complicate the evaluation baseline.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from threading import RLock


@dataclass
class MemoryEntry:
    task_id: str
    prompt: str
    status: str
    response: str
    timestamp: str


class MemoryStore:
    def __init__(self, max_entries: int = 50):
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self.max_entries = max_entries
        self._entries: deque[MemoryEntry] = deque(maxlen=max_entries)
        self._lock = RLock()

    def remember(self, task_id: str, prompt: str, status: str, response: str) -> MemoryEntry:
        entry = MemoryEntry(
            task_id=task_id,
            prompt=prompt,
            status=status,
            response=response,
            timestamp=datetime.now().isoformat(),
        )
        with self._lock:
            self._entries.append(entry)
        return entry

    def recent(self, limit: int = 5) -> list[MemoryEntry]:
        if limit < 1:
            return []
        with self._lock:
            return list(self._entries)[-limit:][::-1]

    def context_for(self, prompt: str, limit: int = 3) -> str:
        """Return concise recent context relevant to the current request.

        v1 intentionally uses a simple lexical overlap score instead of an
        embedding database so experiments remain deterministic and portable.
        """
        query_terms = {term.lower() for term in prompt.split() if len(term) > 2}
        candidates = []
        with self._lock:
            snapshot = list(self._entries)
        for entry in snapshot:
            terms = set(entry.prompt.lower().split())
            score = len(query_terms & terms)
            candidates.append((score, entry.timestamp, entry))
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        selected = [item[2] for item in candidates if item[0] > 0][:limit]
        if not selected:
            selected = self.recent(limit)
        if not selected:
            return ""
        lines = ["Relevant AgentOS memory from previous tasks:"]
        for entry in selected:
            summary = entry.response.replace("\n", " ").strip()
            if len(summary) > 240:
                summary = summary[:237] + "..."
            lines.append(f"- [{entry.status}] {entry.prompt}: {summary}")
        return "\n".join(lines)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._entries)
