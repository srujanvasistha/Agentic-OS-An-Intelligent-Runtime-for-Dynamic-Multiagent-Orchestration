"""Policy-enforced tool boundary with an auditable default-deny decision."""
from typing import Any
from web_events import record_blocked_action


def run_tool(agent: str, tool: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    # No shell or network capability is exposed through this boundary.
    reason = "Tool execution denied by default: only explicitly policy-approved read-only tools may run."
    record_blocked_action({
        "agent": agent,
        "action": tool,
        "tool": tool,
        "args": args,
        "reason": reason,
        "allowed": False,
    })
    return {
        "allowed": False,
        "agent": agent,
        "tool": tool,
        "args": args,
        "result": None,
        "reason": reason,
    }
