"""Policy / capability engine for AgentOS.

The LLM only *proposes* actions. This module decides whether they are allowed.
Everything is deny-by-default and every decision is appended to a JSONL audit log.

Ablation switches (for the experiments):
    enabled=False      -> "policy off": everything is allowed (still logged)
    taint_rules=False  -> capabilities + allowlists only, no taint-tracking layer
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Union

import yaml

ACTIONS = {"fs.read", "fs.write", "fs.delete", "shell.exec", "net"}
# After an agent has seen untrusted content, these need explicit user approval.
RISKY_WHEN_TAINTED = {"fs.delete", "shell.exec", "net"}

Target = Union[str, Sequence[str]]


@dataclass
class Decision:
    allow: bool
    reason: str
    layer: str = "policy"   # which layer decided: off | capability | path | command | taint | ok

    # NOTE: no __bool__ on purpose. Always test `decision.allow` explicitly;
    # a truthy/falsy Decision caused a real bypass bug during development.


def _inside(path: str, root: str) -> bool:
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:  # different drives / empty
        return False


class PolicyEngine:
    def __init__(
        self,
        config_path: str,
        audit_path: str = "audit.jsonl",
        base_dir: str | None = None,
        enabled: bool = True,
        taint_rules: bool = True,
        strict_args: bool = True,      # also check paths hidden in option values (--opt=/path)
        taint_overwrite: bool = True,  # overwriting an existing file after untrusted input needs approval
    ):
        with open(config_path) as f:
            self.cfg = yaml.safe_load(f)
        self.base = os.path.realpath(base_dir or os.getcwd())
        self.workspace = os.path.realpath(os.path.join(self.base, self.cfg["workspace"]))
        self.deny_paths = [os.path.realpath(os.path.join(self.base, p)) for p in self.cfg.get("deny_paths", [])]
        self.commands = set(self.cfg.get("commands", []))
        self.net_allow = set(self.cfg.get("net_allow", []))
        self.agents = self.cfg.get("agents", {})
        self.audit_path = audit_path
        self.enabled = enabled
        self.taint_rules = taint_rules
        self.strict_args = strict_args
        self.taint_overwrite = taint_overwrite
        self.check_count = 0           # for measuring policy overhead
        self.check_time_s = 0.0
        self._tainted: dict[str, list[str]] = {}   # task_id -> sources of untrusted content

    # ---------------- taint tracking ----------------
    def mark_untrusted(self, task_id: str, source: str) -> None:
        self._tainted.setdefault(task_id, []).append(source)

    def is_tainted(self, task_id: str) -> bool:
        return bool(self._tainted.get(task_id))

    # ---------------- path helpers ----------------
    def resolve(self, target: str) -> str:
        """Absolute, symlink-free path. Relative paths are relative to the workspace."""
        p = target if os.path.isabs(target) else os.path.join(self.workspace, target)
        return os.path.realpath(p)

    def _agent_roots(self, agent: str) -> list[str]:
        return [os.path.realpath(os.path.join(self.base, p)) for p in self.agents[agent].get("paths", [])]

    def _path_ok(self, agent: str, real: str) -> Decision | None:
        """Return a deny Decision, or None if the path is fine."""
        for d in self.deny_paths:
            if _inside(real, d):
                return Decision(False, f"path {real} is in a protected folder", "path")
        if not any(_inside(real, r) for r in self._agent_roots(agent)):
            return Decision(False, f"path {real} is outside the allowed workspace", "path")
        return None

    def _arg_paths(self, arg: str) -> list[str]:
        """Path-like pieces of one command-line argument that must be checked."""
        if not arg.startswith("-"):
            if "/" in arg or arg.startswith(".") or os.path.exists(os.path.join(self.workspace, arg)):
                return [arg]
            return []
        if not self.strict_args:       # legacy v1 behaviour: options were skipped (a real gap)
            return []
        cands = []
        if "=" in arg:                 # --files0-from=/etc/passwd
            cands.append(arg.split("=", 1)[1])
        for marker in ("/", ".."):     # -f/etc/passwd, -f../x
            i = arg.find(marker)
            if i > 0:
                cands.append(arg[i:])
        return [c for c in dict.fromkeys(cands) if c]

    # ---------------- main entry point ----------------
    def check(self, agent: str, action: str, target: Target, task_id: str = "-", approved: bool = False) -> Decision:
        """Ask: may `agent` do `action` on `target`? `approved` = a human explicitly said yes."""
        t0 = time.perf_counter()
        if not self.enabled:
            d = Decision(True, "policy disabled (ablation baseline)", "off")
        else:
            d = self._decide(agent, action, target, task_id, approved)
        self._log(task_id, agent, action, target, d)
        self.check_count += 1
        self.check_time_s += time.perf_counter() - t0
        return d

    def _decide(self, agent, action, target, task_id, approved) -> Decision:
        if action not in ACTIONS:
            return Decision(False, f"unknown action '{action}'", "capability")
        if agent not in self.agents:
            return Decision(False, f"unknown agent '{agent}'", "capability")
        if action not in self.agents[agent].get("capabilities", []):
            return Decision(False, f"{agent} does not have capability {action}", "capability")

        risky = action in RISKY_WHEN_TAINTED
        if (not risky and self.taint_overwrite and action == "fs.write"
                and isinstance(target, str) and os.path.isfile(self.resolve(target))):
            risky = True   # overwriting an EXISTING file is destructive; creating a new file is not
        if self.taint_rules and risky and self.is_tainted(task_id) and not approved:
            src = ", ".join(self._tainted[task_id][:3])
            return Decision(False, f"{action} blocked: task has read untrusted content ({src}); needs user approval", "taint")

        if action in ("fs.read", "fs.write", "fs.delete"):
            if not isinstance(target, str):
                return Decision(False, "file target must be a path string", "path")
            bad = self._path_ok(agent, self.resolve(target))
            return bad if bad is not None else Decision(True, "allowed", "ok")

        if action == "shell.exec":
            if isinstance(target, str) or not isinstance(target, (list, tuple)) or not target:
                return Decision(False, "commands must be an argv list, not a shell string", "command")
            argv = [str(a) for a in target]
            if os.path.basename(argv[0]) != argv[0] or argv[0] not in self.commands:
                return Decision(False, f"command '{argv[0]}' is not in the allowlist", "command")
            for arg in argv[1:]:
                for cand in self._arg_paths(arg):
                    bad = self._path_ok(agent, self.resolve(cand))
                    if bad is not None:
                        return Decision(False, f"argument '{arg}': {bad.reason}", "command")
            return Decision(True, "allowed", "ok")

        if action == "net":
            host = target if isinstance(target, str) else str(target)
            if host not in self.net_allow:
                return Decision(False, f"host '{host}' is not allowlisted", "capability")
            return Decision(True, "allowed", "ok")

        return Decision(False, "no rule matched (deny by default)", "capability")

    # ---------------- audit log ----------------
    def _log(self, task_id, agent, action, target, d: Decision) -> None:
        rec = {
            "ts": round(time.time(), 3),
            "task_id": task_id,
            "agent": agent,
            "action": action,
            "target": target if isinstance(target, str) else list(target),
            "decision": "allow" if d.allow else "deny",
            "reason": d.reason,
            "layer": d.layer,
            "tainted": self.is_tainted(task_id),
        }
        Path(self.audit_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.audit_path, "a") as f:
            f.write(json.dumps(rec) + "\n")
