"""Safe tool executor. Every tool calls PolicyEngine.check() first; there is no bypass.

Anything these tools return (file text, command output) is treated as UNTRUSTED:
the task is marked tainted so later risky actions need explicit user approval.
"""
from __future__ import annotations

import os
import subprocess
from typing import Sequence

from .policy import PolicyEngine
from .sandbox import bwrap_available, wrap


class PermissionDenied(Exception):
    def __init__(self, decision):
        super().__init__(f"[{decision.layer}] {decision.reason}")
        self.decision = decision


class SafeTools:
    def __init__(self, engine: PolicyEngine, use_sandbox: bool = False, timeout: int = 10):
        self.engine = engine
        self.use_sandbox = use_sandbox and bwrap_available()
        self.timeout = timeout
        self.net_calls: list[dict] = []     # every network call that was allowed (host, data)
        self.exec_guard = None              # optional hook used by the test harness for safety

    def _guard(self, agent, action, target, task_id, approved):
        d = self.engine.check(agent, action, target, task_id=task_id, approved=approved)
        if not d.allow:
            raise PermissionDenied(d)

    def read_file(self, agent: str, path: str, task_id: str = "-", approved: bool = False) -> str:
        self._guard(agent, "fs.read", path, task_id, approved)
        with open(self.engine.resolve(path), "r", errors="replace") as f:
            text = f.read()
        self.engine.mark_untrusted(task_id, f"file:{path}")
        return text

    def write_file(self, agent: str, path: str, content: str, task_id: str = "-", approved: bool = False) -> str:
        self._guard(agent, "fs.write", path, task_id, approved)
        real = self.engine.resolve(path)
        os.makedirs(os.path.dirname(real), exist_ok=True)
        with open(real, "w") as f:
            f.write(content)
        return f"wrote {len(content)} chars to {path}"

    def delete_file(self, agent: str, path: str, task_id: str = "-", approved: bool = False) -> str:
        self._guard(agent, "fs.delete", path, task_id, approved)
        os.remove(self.engine.resolve(path))
        return f"deleted {path}"

    def run_cmd(self, agent: str, argv: Sequence[str], task_id: str = "-", approved: bool = False) -> str:
        self._guard(agent, "shell.exec", argv, task_id, approved)
        if self.exec_guard:
            self.exec_guard(list(argv))
        cmd = wrap(list(argv), self.engine.workspace) if self.use_sandbox else list(argv)
        res = subprocess.run(cmd, cwd=self.engine.workspace, capture_output=True, text=True,
                             timeout=self.timeout, shell=False)
        out = (res.stdout + res.stderr).strip()
        self.engine.mark_untrusted(task_id, f"cmd:{argv[0]}")
        return out

    def http_get(self, agent: str, host: str, task_id: str = "-", approved: bool = False, data: str = "") -> str:
        """Placeholder network tool: only the permission check is real. No packet is ever sent.
        Allowed calls are recorded in net_calls so experiments can see what WOULD have left the machine."""
        self._guard(agent, "net", host, task_id, approved)
        self.net_calls.append({"host": host, "data": data})
        return f"(network call to {host} would happen here)"
