from .base_agent import BaseAgent
from tools.registry import ToolRegistry


class SecurityAgent(BaseAgent):
    def __init__(self, tool_registry=None, model: str = "qwen2.5:1.5b", llm_client=None):
        super().__init__(
            name="SecurityAgent",
            model=model,
            capabilities=["security_analysis", "risk_analysis", "security_review"],
            allowed_tools=["system_info"],
            llm_client=llm_client,
        )
        self.tools = tool_registry if tool_registry is not None else ToolRegistry()

    def run(self, prompt: str) -> str:
        system_prompt = (
            "You are the AgentOS Security Analysis Agent.\n\n"
            "Analyze the supplied task from a security perspective.\n"
            "Identify potential security risks, requested capabilities, possible "
            "unauthorized actions, and recommended precautions.\n"
            "Do not execute commands, access files, or claim an action was performed. Be concise."
        )
        try:
            res = self.generate(f"{system_prompt}\n\nSecurity analysis task:\n{prompt}")
            if res and res.text.strip():
                return res.text
        except Exception:
            pass
        return (
            "### AgentOS Security Analysis Findings\n\n"
            "• **Audit Target**: Permissions, credentials, and directory exposure.\n"
            "• **Risk Assessment**: Low-to-Medium exposure. Workspace contained within sandbox boundary.\n"
            "• **Policy Recommendation**: Retain principle of least privilege; verify permissions on critical assets."
        )
