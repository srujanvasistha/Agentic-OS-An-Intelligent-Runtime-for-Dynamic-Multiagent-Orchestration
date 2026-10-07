class ToolRegistry:
    """
    Central registry for AgentOS tools.
    """

    def __init__(self):
        self._tools = {}

    def register(self, name: str, tool):
        self._tools[name] = tool

    def get(self, name: str):
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    def list_tools(self):
        return list(self._tools.keys())