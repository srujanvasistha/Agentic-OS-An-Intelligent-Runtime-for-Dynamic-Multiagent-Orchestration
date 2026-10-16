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

from workload.generator import generate_workload
from workload.queue import TaskQueue
from agents.agent import Agent
from agents.manager import AgentManager
from metrics.collector import MetricsCollector


class Scheduler:

    def __init__(self, agent_manager):

        self.task_queue = TaskQueue()
        self.agent_manager = agent_manager

        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.unassigned_tasks = 0
        self.fallback_tasks = 0
        self.metrics = MetricsCollector()

    def submit_task(self, task):

        self.task_queue.add_task(task)
        self.total_tasks += 1

    def submit_tasks(self, tasks):

        for task in tasks:
            self.submit_task(task)

    def schedule_next(self):

        if self.task_queue.is_empty():
            return None

        # Get highest-priority task
        task = self.task_queue.get_next_task()

        print(
            f"\n[SCHEDULER] Selected "
            f"{task.task_id} "
            f"(Type: {task.task_type}, "
            f"Priority: {task.priority})"
        )

        # -----------------------------------------
        # Try specialized agent first
        # -----------------------------------------

        agent = self.agent_manager.find_agent_for_task(task)

        # -----------------------------------------
        # If no specialized agent exists,
        # use fallback agent
        # -----------------------------------------

        if agent is None:

            agent = self.agent_manager.get_fallback_agent()

            if agent is not None:

                print(
                    f"[SCHEDULER] No specialized agent found"
                )

                print(
                    f"[SCHEDULER] Using fallback agent "
                    f"→ {agent.agent_id}"
                )

                self.fallback_tasks += 1

            else:

                print(
                    f"[SCHEDULER] No agent available "
                    f"for {task.task_id}"
                )

                task.mark_failed()

                self.failed_tasks += 1
                self.unassigned_tasks += 1

                return task

        else:

            print(
                f"[SCHEDULER] Assigned "
                f"{task.task_id} → {agent.agent_id}"
            )

        # -----------------------------------------
        # Execute task
        # -----------------------------------------

        success = agent.execute(task)

        if success:
            self.completed_tasks += 1
        else:
            self.failed_tasks += 1

        return task

    def run(self):

        print("\n" + "=" * 70)
        print("DYNAMIC SCHEDULER STARTED")
        print("=" * 70)

        self.metrics.start()

        while not self.task_queue.is_empty():

            task = self.schedule_next()

            if task is not None:
                self.metrics.record_task(task)

        self.metrics.stop()

        print("\n" + "=" * 70)
        print("DYNAMIC SCHEDULER FINISHED")
        print("=" * 70)

        print("\n" + "=" * 70)
        print("DYNAMIC SCHEDULER FINISHED")
        print("=" * 70)

    def get_statistics(self):

        return {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "unassigned_tasks": self.unassigned_tasks,
            "fallback_tasks": self.fallback_tasks,
            "remaining_tasks": self.task_queue.size()
        }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    # -----------------------------------------
    # Create Agent Manager
    # -----------------------------------------

    manager = AgentManager()

    # Specialized agents
    agent1 = Agent(
        "AGENT-001",
        ["compute", "data"]
    )

    agent2 = Agent(
        "AGENT-002",
        ["network", "io"]
    )

    agent3 = Agent(
        "AGENT-003",
        ["ml", "text"]
    )

    # Fallback agent
    fallback_agent = Agent(
        "AGENT-FALLBACK",
        []
    )

    # Register specialized agents
    manager.register_agent(agent1)
    manager.register_agent(agent2)
    manager.register_agent(agent3)

    # Register fallback agent
    manager.register_agent(
        fallback_agent,
        fallback=True
    )

    # -----------------------------------------
    # Create Scheduler
    # -----------------------------------------

    scheduler = Scheduler(manager)

    # -----------------------------------------
    # Generate workload
    # -----------------------------------------

    workload = generate_workload(
        num_tasks=10,
        seed=42
    )

    # -----------------------------------------
    # Submit workload
    # -----------------------------------------

    scheduler.submit_tasks(workload)

    # -----------------------------------------
    # Run scheduler
    # -----------------------------------------

    scheduler.run()

    # -----------------------------------------
    # Display statistics
    # -----------------------------------------

    print("\nScheduler Statistics:")

    for key, value in scheduler.get_statistics().items():

        print(f"{key}: {value}")

    print("\nAgent Statistics:")

    for stats in manager.get_statistics():

        print(stats)