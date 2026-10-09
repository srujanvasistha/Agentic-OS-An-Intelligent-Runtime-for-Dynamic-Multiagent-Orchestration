import sys
import os

# Add project root to Python path
PROJECT_ROOT = os.path.dirname(
    os.path.abspath(__file__)
)

sys.path.append(PROJECT_ROOT)


from workload.generator import generate_workload
from agents.agent import Agent
from agents.manager import AgentManager
from scheduler.scheduler import Scheduler


class AgenticOSRuntime:

    def __init__(self, num_tasks=20, seed=42):

        self.num_tasks = num_tasks
        self.seed = seed

        # -----------------------------------------
        # Create Agent Manager
        # -----------------------------------------

        self.manager = AgentManager()

        # Specialized agents
        self.manager.register_agent(
            Agent(
                "AGENT-001",
                ["compute", "data"]
            )
        )

        self.manager.register_agent(
            Agent(
                "AGENT-002",
                ["network", "io"]
            )
        )

        self.manager.register_agent(
            Agent(
                "AGENT-003",
                ["ml", "text"]
            )
        )

        # Fallback agent
        self.manager.register_agent(
            Agent(
                "AGENT-FALLBACK",
                []
            ),
            fallback=True
        )

        # -----------------------------------------
        # Create Scheduler
        # -----------------------------------------

        self.scheduler = Scheduler(
            self.manager
        )

    # ---------------------------------------------
    # Generate workload
    # ---------------------------------------------

    def create_workload(self):

        print("\n[Runtime] Generating workload...")

        workload = generate_workload(
            num_tasks=self.num_tasks,
            seed=self.seed
        )

        print(
            f"[Runtime] Generated "
            f"{len(workload)} tasks"
        )

        return workload

    # ---------------------------------------------
    # Submit workload
    # ---------------------------------------------

    def submit_workload(self, workload):

        print(
            "[Runtime] Submitting workload "
            "to scheduler..."
        )

        self.scheduler.submit_tasks(
            workload
        )

    # ---------------------------------------------
    # Start runtime
    # ---------------------------------------------

    def start(self):

        print("\n")
        print("=" * 70)
        print("        AGENTIC OS RUNTIME")
        print(" Dynamic Multiagent Orchestration")
        print("=" * 70)

        # Create workload
        workload = self.create_workload()

        # Submit workload
        self.submit_workload(workload)

        # Execute
        print(
            "\n[Runtime] Starting scheduler..."
        )

        self.scheduler.run()

        # Display results
        self.display_results()

    # ---------------------------------------------
    # Display results
    # ---------------------------------------------

    def display_results(self):

        print("\n")
        print("=" * 70)
        print("              RUNTIME RESULTS")
        print("=" * 70)

        # Scheduler statistics
        print("\nScheduler Statistics:")

        scheduler_stats = (
            self.scheduler.get_statistics()
        )

        for key, value in scheduler_stats.items():

            print(
                f"{key}: {value}"
            )

        # Metrics
        print("\nExecution Metrics:")

        metrics = (
            self.scheduler.metrics.get_report()
        )

        for key, value in metrics.items():

            print(
                f"{key}: {value}"
            )

        # Agent statistics
        print("\nAgent Performance:")

        for stats in self.manager.get_statistics():

            print(
                f"\n{stats['agent_id']}"
            )

            print(
                f"  Completed: "
                f"{stats['completed_tasks']}"
            )

            print(
                f"  Failed: "
                f"{stats['failed_tasks']}"
            )

            print(
                f"  Load: "
                f"{stats['load']}"
            )

            print(
                f"  Success Rate: "
                f"{stats['success_rate']}%"
            )

            print(
                f"  Avg Execution: "
                f"{stats['average_execution_time']}s"
            )

            print(
                f"  Performance Score: "
                f"{stats['performance_score']}"
            )

        print("\n")
        print("=" * 70)
        print("             RUNTIME COMPLETED")
        print("=" * 70)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    runtime = AgenticOSRuntime(
        num_tasks=20,
        seed=42
    )

    runtime.start()