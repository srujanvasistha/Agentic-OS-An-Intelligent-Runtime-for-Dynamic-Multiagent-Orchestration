"""Frozen AgentOS tool boundary.

Every agent-facing tool call must go through policy.run_tool. The implementation
is imported here for backwards compatibility with the Day 1 contract.
"""

from policy.engine import run_tool

__all__ = ["run_tool"]
