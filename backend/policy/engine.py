"""Central policy gate for every AgentOS tool invocation.

Agents never call operating-system-facing tools directly. They call run_tool,
which resolves the registered capability and applies the policy gate first.
The enforcement flag is intentionally centralized so Day 6 can ablate policy
without changing agent/runtime code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from policy.metrics import append_metric


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    agent: str
    tool: str


class PolicyEngine:
    def __init__(self, registry=None, metrics_path=None, enforcement: bool | None = None):
        self.registry = registry
        self.metrics_path = metrics_path
        self.enforcement = get_enforcement_enabled() if enforcement is None else bool(enforcement)
        self.policies = {
            "GeneralAgent": {"allowed_tools": set(), "max_risk_level": 1},
            "FileAgent": {"allowed_tools": {"filesystem"}, "max_risk_level": 3},
            "SecurityAgent": {"allowed_tools": {"system_info"}, "max_risk_level": 5},
        }

    def set_registry(self, registry):
        self.registry = registry

    def set_enforcement(self, enabled: bool):
        self.enforcement = bool(enabled)

    def authorize(self, agent: str, tool: str, args: dict[str, Any] | None = None) -> PolicyDecision:
        policy = self.policies.get(agent, {"allowed_tools": set(), "max_risk_level": 1})
        if not self.enforcement:
            return PolicyDecision(True, "Policy enforcement disabled (ablation mode).", agent, tool)
        if tool not in policy["allowed_tools"]:
            return PolicyDecision(False, f"Tool execution denied by policy: '{tool}' is not permitted for agent '{agent}'.", agent, tool)
        return PolicyDecision(True, "Allowed by agent policy.", agent, tool)

    def execute(self, agent: str, tool: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        clean_args = dict(args or {})
        task_id = str(clean_args.pop("_task_id", "unknown"))
        decision = self.authorize(agent, tool, clean_args)
        if not decision.allowed:
            self._metric(task_id, "tool_blocked", metadata={
                "agent": agent, "tool": tool, "reason": decision.reason,
            })
            raise PermissionError(decision.reason)

        if self.registry is None:
            raise RuntimeError("Policy tool registry is not configured.")
        implementation = self.registry.get(tool)
        if implementation is None:
            self._metric(task_id, "tool_blocked", metadata={
                "agent": agent, "tool": tool, "reason": "Unknown tool",
            })
            raise PermissionError(f"Tool '{tool}' is not registered.")

        try:
            result = _invoke_tool(implementation, clean_args)
        except PermissionError:
            self._metric(task_id, "tool_blocked", metadata={"agent": agent, "tool": tool, "reason": "Tool denied execution"})
            raise
        except Exception as exc:
            self._metric(task_id, "tool_error", metadata={"agent": agent, "tool": tool, "reason": str(exc)})
            raise
        self._metric(task_id, "tool_allowed", metadata={"agent": agent, "tool": tool})
        return {"allowed": True, "agent": agent, "tool": tool, "args": clean_args, "result": result, "reason": decision.reason}

    def _metric(self, task_id: str, event: str, value: float | None = None, metadata=None):
        if self.metrics_path:
            append_metric(self.metrics_path, task_id, event, value, metadata)


def _invoke_tool(tool, args: dict[str, Any]):
    """Dispatch only through a registered tool object."""
    if "operation" in args:
        operation = args.pop("operation")
        method = getattr(tool, operation, None)
        if method is None or not callable(method):
            raise PermissionError(f"Tool operation '{operation}' is not supported.")
        return method(**args)
    if hasattr(tool, "summary") and not args:
        return tool.summary()
    raise ValueError("Tool call requires an operation and arguments.")


def get_enforcement_enabled() -> bool:
    return os.getenv("AGENTOS_POLICY_ENFORCEMENT", "on").strip().lower() not in {"off", "false", "0", "no"}


def set_enforcement_enabled(enabled: bool):
    os.environ["AGENTOS_POLICY_ENFORCEMENT"] = "on" if enabled else "off"


# Frozen tool boundary used by agents. All OS-facing operations must pass here.
def run_tool(agent: str, tool: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    """Frozen boundary: return a structured allowed/denied result."""
    try:
        return _get_engine().execute(agent, tool, args)
    except PermissionError as exc:
        return {
            "allowed": False,
            "agent": agent,
            "tool": tool,
            "args": args or {},
            "result": None,
            "reason": str(exc),
        }


_ENGINE: PolicyEngine | None = None


def configure_policy_engine(registry=None, metrics_path=None, enforcement=None) -> PolicyEngine:
    global _ENGINE
    _ENGINE = PolicyEngine(registry=registry, metrics_path=metrics_path, enforcement=enforcement)
    return _ENGINE


def _get_engine() -> PolicyEngine:
    if _ENGINE is None:
        raise RuntimeError("Policy engine is not configured. Initialize AgentOS policy before running agents.")
    return _ENGINE
