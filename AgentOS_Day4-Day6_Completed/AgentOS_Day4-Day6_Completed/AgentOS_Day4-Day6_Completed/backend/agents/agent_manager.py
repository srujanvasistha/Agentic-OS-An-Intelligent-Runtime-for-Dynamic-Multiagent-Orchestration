"""Agent selection and dispatch for AgentOS Day 2.

The manager is deliberately small: it owns agent selection while the agents
remain responsible for task-specific behavior. The scheduler can later call
this same manager after choosing an execution policy/model.
"""

from schemas import AgentType


class AgentManager:
    TYPE_TO_NAME = {
        AgentType.GENERAL: "GeneralAgent",
        AgentType.FILE: "FileAgent",
        AgentType.SECURITY: "SecurityAgent",
        AgentType.MONITORING: "MonitoringAgent",
        AgentType.PLANNING: "PlanningAgent",
        AgentType.IMAGE: "ImageAgent",
    }

    NAME_TO_TYPE = {value: key for key, value in TYPE_TO_NAME.items()}

    def __init__(self, registry, router):
        self.registry = registry
        self.router = router

    def get_by_type(self, agent_type: AgentType):
        name = self.TYPE_TO_NAME.get(agent_type, "GeneralAgent")
        return self.registry.get(name)

    def select_for_prompt(self, prompt: str, image_url: str | None = None):
        capability = self.router.classify(prompt, image_url=image_url)
        matches = self.registry.find_by_capability(capability)
        agent = matches[0] if matches else self.registry.get("GeneralAgent")
        return agent, capability

    def select_for_task(self, prompt: str, agent_type: AgentType | None = None, image_url: str | None = None):
        if agent_type is not None:
            agent = self.get_by_type(agent_type)
            return agent, agent_type.value
        return self.select_for_prompt(prompt, image_url=image_url)

    def agent_type_for(self, agent) -> AgentType:
        return self.NAME_TO_TYPE.get(agent.name, AgentType.GENERAL)

    def describe(self):
        return self.registry.describe_agents()
