from .base_agent import BaseAgent
from tools.registry import ToolRegistry


class GeneralAgent(BaseAgent):
    def __init__(self, tool_registry=None, model: str = "qwen2.5:1.5b", llm_client=None):
        super().__init__(
            name="GeneralAgent",
            model=model,
            capabilities=["general_questions", "reasoning", "explanation", "conversation"],
            allowed_tools=[],
            llm_client=llm_client,
        )
        self.tools = tool_registry if tool_registry is not None else ToolRegistry()

    def run(self, prompt: str) -> str:
        system_prompt = (
            "You are the general-purpose AgentOS assistant. "
            "Answer clearly and concisely."
        )
        result = self.generate(f"{system_prompt}\n\nUser task:\n{prompt}")
        return result.text
