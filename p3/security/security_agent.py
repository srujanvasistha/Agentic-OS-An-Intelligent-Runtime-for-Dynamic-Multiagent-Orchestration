"""SecurityAgent (minimal): scans text for prompt-injection patterns and reports a risk level.

It is read-only and deliberately simple (regex + base64 decoding). It is a *detector*,
not the enforcement layer: enforcement is the PolicyEngine. Flagged content is marked
untrusted so the taint rules apply.
"""
from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field

from .policy import PolicyEngine

PATTERNS = {
    "override":    r"ignore (all |any )?(previous|prior|above) (instructions|rules)|disregard (the )?(system|previous)",
    "role_change": r"you are now|new instructions:|system prompt|developer mode",
    "destructive": r"\b(delete|remove|erase|wipe)\b.{0,40}\b(file|folder|directory|data|logs?)\b|\brm\s+-",
    "exfil":       r"\b(send|upload|post|email|curl|wget)\b.{0,60}\b(secret|password|key|token|credential|http)",
    "secrets":     r"/etc/passwd|\.ssh|api[_-]?key|secrets?/|\.env\b",
    "traversal":   r"\.\./",
    "fake_auth":   r"(the )?user (said|told|approved|authorized)|you have (my )?permission|it'?s (ok|okay) to",
    "shell":       r"\b(bash|sh|powershell)\b\s+-c|;\s*(rm|curl|wget|nc)\b|&&\s*(rm|curl|wget)\b",
}
B64 = re.compile(r"[A-Za-z0-9+/]{24,}={0,2}")


@dataclass
class Report:
    risk: str                      # "low" | "medium" | "high"
    findings: list[str] = field(default_factory=list)


class SecurityAgent:
    name = "SecurityAgent"

    def scan(self, text: str) -> Report:
        findings = [k for k, p in PATTERNS.items() if re.search(p, text, re.I | re.S)]
        for tok in B64.findall(text):                       # obfuscation: look inside base64 blobs
            try:
                dec = base64.b64decode(tok + "=" * (-len(tok) % 4)).decode("utf-8", "ignore")
            except Exception:
                continue
            findings += [f"b64:{k}" for k, p in PATTERNS.items() if re.search(p, dec, re.I | re.S)]
        findings = sorted(set(findings))
        risk = "high" if len(findings) >= 2 else "medium" if findings else "low"
        return Report(risk, findings)

    def inspect(self, engine: PolicyEngine, task_id: str, text: str, source: str) -> Report:
        """Scan content; if suspicious, mark the task as having seen untrusted input."""
        rep = self.scan(text)
        if rep.risk != "low":
            engine.mark_untrusted(task_id, f"{source} (flagged: {','.join(rep.findings)})")
        return rep
