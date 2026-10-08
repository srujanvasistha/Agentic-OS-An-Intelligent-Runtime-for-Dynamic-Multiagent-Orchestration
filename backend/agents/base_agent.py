from abc import ABC, abstractmethod

from llm.client import LLMClient, create_llm_client, OllamaLLMClient, MockLLMClient
from policy.engine import run_tool
from policy.untrusted import mark_untrusted


class BaseAgent(ABC):
    def __init__(
        self,
        name: str,
        model: str,
        capabilities: list[str] | None = None,
        allowed_tools: list[str] | None = None,
        llm_client: LLMClient | None = None,
    ):
        self.name = name
        self.model = model
        self.capabilities = capabilities or []
        self.allowed_tools = allowed_tools or []
        self.llm = llm_client or create_llm_client()
        self.last_llm_response = None
        self.last_llm_prompt = None
        self.task_id = "unknown"

    def configure_model(self, model: str):
        """Switch the inference model while preserving the shared client abstraction."""
        self.model = model
        if isinstance(self.llm, OllamaLLMClient):
            self.llm = OllamaLLMClient(
                base_url=self.llm.base_url,
                model=model,
                timeout=self.llm.timeout,
            )
        elif isinstance(self.llm, MockLLMClient):
            self.llm = MockLLMClient(model=f"mock-{model}", tps=self.llm.tps)

    def call_tool(self, tool: str, args: dict | None = None, source: str = "tool_output") -> str:
        """Invoke an OS-facing capability only through the policy boundary."""
        payload = dict(args or {})
        payload["_task_id"] = self.task_id
        result = run_tool(self.name, tool, payload)
        if not result.get("allowed"):
            raise PermissionError(result.get("reason", "Tool execution denied by policy."))
        return mark_untrusted(result.get("result"), source=source)

    def generate(self, prompt: str):
        """Generate through the shared LLM interface."""
        self.last_llm_prompt = prompt
        self.last_llm_response = self.llm.generate(prompt)
        return self.last_llm_response

    @abstractmethod
    def run(self, prompt: str) -> str:
        pass
