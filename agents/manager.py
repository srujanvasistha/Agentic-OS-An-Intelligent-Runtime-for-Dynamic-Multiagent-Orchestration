import sys
import os

# Add project root to Python path
sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from agents.agent import Agent


class AgentManager:

    def __init__(self):

        self.agents = []
        self.fallback_agent = None

    def register_agent(self, agent, fallback=False):

        self.agents.append(agent)

        if fallback:
            self.fallback_agent = agent

        print(
            f"[MANAGER] Registered "
            f"{agent.agent_id}"
        )

    def get_available_agents(self):

        return [
            agent
            for agent in self.agents
            if agent.status == "IDLE"
        ]

    def find_agent_for_task(self, task):

        available_agents = []

        for agent in self.get_available_agents():

            # Don't use fallback for normal selection
            if agent == self.fallback_agent:
                continue

            if agent.can_execute(task):

                available_agents.append(agent)

        # No capable agent
        if not available_agents:
            return None

        # Select least-loaded agent
        selected_agent = min(
            available_agents,
            key=lambda agent: agent.get_load()
        )

        return selected_agent

    
    def get_fallback_agent(self):

        if (
            self.fallback_agent is not None
            and self.fallback_agent.status == "IDLE"
        ):

            return self.fallback_agent

        return None

    def get_agent_count(self):

        return len(self.agents)

    def get_statistics(self):

        return [
            agent.get_statistics()
            for agent in self.agents
        ]


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    from workload.task import Task

    manager = AgentManager()

    # Two agents with the same capability
    agent1 = Agent(
        "AGENT-001",
        ["compute", "data"]
    )

    agent2 = Agent(
        "AGENT-002",
        ["compute", "data"]
    )

    agent3 = Agent(
        "AGENT-003",
        ["ml", "text"]
    )

    # Register agents
    manager.register_agent(agent1)
    manager.register_agent(agent2)
    manager.register_agent(agent3)

    # Simulate previous workload
    agent1.completed_tasks = 5
    agent2.completed_tasks = 2
    agent3.completed_tasks = 0

    # Create a compute task
    task = Task(
        task_id="TEST-001",
        task_type="compute",
        priority=5,
        complexity="medium",
        payload={
            "operation": "matrix_multiplication"
        }
    )

    # Find best agent
    selected = manager.find_agent_for_task(task)

    print("\nAgent Loads:")

    print(
        f"{agent1.agent_id}: "
        f"{agent1.get_load()}"
    )

    print(
        f"{agent2.agent_id}: "
        f"{agent2.get_load()}"
    )

    print(
        f"{agent3.agent_id}: "
        f"{agent3.get_load()}"
    )

    print("\nSelected Agent:")

    if selected:
        print(selected.agent_id)
    else:
        print("No suitable agent")