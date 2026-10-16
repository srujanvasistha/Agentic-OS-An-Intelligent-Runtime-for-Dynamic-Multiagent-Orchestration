class AgentRegistry:
    """
    Central registry for AgentOS agents.
    """

    def __init__(self):
        self._agents = {}

    def register(self, name: str, agent):
        self._agents[name] = agent

    def get(self, name: str):
        return self._agents.get(name)

    def has(self, name: str) -> bool:
        return name in self._agents

    def list_agents(self):
        return list(self._agents.keys())

    def describe_agents(self):
        descriptions = []

        for name, agent in self._agents.items():
            descriptions.append({
                "name": name,
                "model": agent.model,
                "capabilities": agent.capabilities,
                "allowed_tools": agent.allowed_tools,
            })

        return descriptions

    def find_by_capability(self, capability: str):
        matches = []

        for name, agent in self._agents.items():
            if capability in agent.capabilities:
                matches.append(agent)

        return matches

    def can_use_tool(self, agent_name: str, tool_name: str) -> bool:
        agent = self.get(agent_name)

        if agent is None:
            return False

        return tool_name in agent.allowed_tools