"""Day 1 tool boundary.

P3 will replace the default deny-only implementation with policy-enforced
execution. Keeping this boundary now prevents agents from gaining implicit
OS capabilities merely because an LLM requested them.
"""

from typing import Any


def run_tool(agent: str, tool: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a denial until the policy layer is implemented."""
    return {
        "allowed": False,
        "agent": agent,
        "tool": tool,
        "args": args or {},
        "result": None,
        "reason": "Tool execution denied: policy layer not enabled yet.",
    }
