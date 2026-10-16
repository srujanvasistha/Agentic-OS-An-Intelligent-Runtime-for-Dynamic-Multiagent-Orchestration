"""Default-deny capability policy for AgentOS tool calls.

This is an application-layer guard, not a substitute for OS sandboxing. Use
bubblewrap/seccomp/Landlock/AppArmor as a second enforcement boundary in Linux.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    capability: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"allowed": self.allowed, "reason": self.reason, "capability": self.capability}


class PolicyEngine:
    """Small deny-by-default policy engine for the MVP.

    Allowed operations are read-only filesystem listing/search/read and read-only
    system information. File writes, shell execution, and network access remain
    denied unless a future explicit policy is implemented.
    """

    SENSITIVE_PARTS = {".env", ".ssh", ".aws", ".config", "secrets", "credentials"}
    ALLOWED_FILESYSTEM_OPS = {"list_files", "find_files", "find_by_extension", "search_contents", "read_file"}

    def __init__(self, workspace: str | Path, agent_capabilities: dict[str, set[str]] | None = None):
        self.workspace = Path(workspace).resolve()
        self.agent_capabilities = agent_capabilities or {
            "GeneralAgent": {"system_info"},
            "FileAgent": {"filesystem.read", "filesystem.list", "filesystem.search"},
            "SecurityAgent": {"system_info", "security_analysis"},
        }

    def check(self, agent: str, tool: str, args: dict[str, Any] | None = None) -> PolicyDecision:
        args = args or {}
        capabilities = self.agent_capabilities.get(agent, set())
        if tool == "system_info":
            if "system_info" in capabilities and not args:
                return PolicyDecision(True, "Read-only system information is allowed", "system_info")
            return PolicyDecision(False, "Agent lacks system_info capability or supplied unexpected arguments")

        if tool == "filesystem":
            operation = str(args.get("operation", "")).strip()
            if operation not in self.ALLOWED_FILESYSTEM_OPS:
                return PolicyDecision(False, "Unsupported filesystem operation; write/delete are denied by default")
            capability = "filesystem.list" if operation == "list_files" else (
                "filesystem.search" if operation in {"find_files", "find_by_extension", "search_contents"}
                else "filesystem.read"
            )
            if capability not in capabilities:
                return PolicyDecision(False, f"Agent lacks {capability} capability")
            if operation in {"read_file", "find_files"}:
                raw_path = str(args.get("relative_path", args.get("filename", ""))).strip()
                if not raw_path:
                    return PolicyDecision(False, "A non-empty path or filename is required")
                if operation == "read_file":
                    candidate = (self.workspace / raw_path.replace("\\", "/")).resolve()
                    try:
                        candidate.relative_to(self.workspace)
                    except ValueError:
                        return PolicyDecision(False, "Path escapes the AgentOS workspace")
                    if any(part.lower() in self.SENSITIVE_PARTS for part in candidate.relative_to(self.workspace).parts):
                        return PolicyDecision(False, "Access to sensitive paths is denied")
            return PolicyDecision(True, f"{operation} is permitted for {agent}", capability)

        # shell, network, arbitrary service names, and unknown tools are denied.
        return PolicyDecision(False, f"Unknown or prohibited tool '{tool}'")
