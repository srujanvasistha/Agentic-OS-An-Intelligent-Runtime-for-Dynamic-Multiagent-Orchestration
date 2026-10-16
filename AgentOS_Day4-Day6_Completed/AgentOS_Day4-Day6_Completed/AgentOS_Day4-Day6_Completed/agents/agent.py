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

import time


class Agent:

    def __init__(self, agent_id, capabilities=None):

        self.agent_id = agent_id
        self.capabilities = capabilities or []

        self.status = "IDLE"
        self.current_task = None

        self.completed_tasks = 0
        self.failed_tasks = 0

        self.total_execution_time = 0.0

    # -----------------------------------------
    # Capability check
    # -----------------------------------------

    def can_execute(self, task):

        if not self.capabilities:
            return True

        return task.task_type in self.capabilities

    # -----------------------------------------
    # Current load
    # -----------------------------------------

    def get_load(self):

        return (
            self.completed_tasks +
            self.failed_tasks
        )

    # -----------------------------------------
    # Execute task
    # -----------------------------------------

    def execute(self, task):

        if not self.can_execute(task):

            print(
                f"[{self.agent_id}] "
                f"Cannot execute {task.task_id}"
            )

            return False

        self.status = "BUSY"
        self.current_task = task

        print(
            f"[{self.agent_id}] "
            f"Starting {task.task_id} "
            f"({task.task_type})"
        )

        task.mark_running()

        start_time = time.time()

        try:

            duration = min(
                task.estimated_duration,
                2.0
            )

            time.sleep(duration)

            task.mark_completed()

            execution_time = (
                time.time() - start_time
            )

            self.total_execution_time += execution_time

            self.completed_tasks += 1

            self.status = "IDLE"
            self.current_task = None

            print(
                f"[{self.agent_id}] "
                f"Completed {task.task_id} "
                f"in {execution_time:.2f}s"
            )

            return True

        except Exception as error:

            task.mark_failed()

            self.failed_tasks += 1

            self.status = "IDLE"
            self.current_task = None

            print(
                f"[{self.agent_id}] "
                f"Failed {task.task_id}: {error}"
            )

            return False

    # -----------------------------------------
    # Success rate
    # -----------------------------------------

    def get_success_rate(self):

        total_tasks = (
            self.completed_tasks +
            self.failed_tasks
        )

        if total_tasks == 0:
            return 0.0

        return (
            self.completed_tasks /
            total_tasks
        ) * 100

    # -----------------------------------------
    # Average execution time
    # -----------------------------------------

    def get_average_execution_time(self):

        if self.completed_tasks == 0:
            return 0.0

        return (
            self.total_execution_time /
            self.completed_tasks
        )

    # -----------------------------------------
    # Performance score
    # -----------------------------------------

    def get_performance_score(self):

        success_rate = self.get_success_rate()

        avg_time = self.get_average_execution_time()

        if avg_time <= 0:
            return success_rate

        # Higher success and lower execution time
        # produce a better score.

        speed_score = 100 / (1 + avg_time)

        score = (
            0.7 * success_rate +
            0.3 * speed_score
        )

        return score

    # -----------------------------------------
    # Statistics
    # -----------------------------------------

    def get_statistics(self):

        return {

            "agent_id":
                self.agent_id,

            "status":
                self.status,

            "completed_tasks":
                self.completed_tasks,

            "failed_tasks":
                self.failed_tasks,

            "total_execution_time":
                round(
                    self.total_execution_time,
                    2
                ),

            "average_execution_time":
                round(
                    self.get_average_execution_time(),
                    2
                ),

            "success_rate":
                round(
                    self.get_success_rate(),
                    2
                ),

            "load":
                self.get_load(),

            "performance_score":
                round(
                    self.get_performance_score(),
                    2
                )
        }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    from workload.task import Task

    agent = Agent(
        "AGENT-001",
        ["compute", "data"]
    )

    task1 = Task(
        task_id="TEST-001",
        task_type="compute",
        priority=5,
        complexity="medium",
        payload={
            "operation": "matrix_multiplication"
        },
        estimated_duration=1
    )

    task2 = Task(
        task_id="TEST-002",
        task_type="data",
        priority=4,
        complexity="low",
        payload={
            "operation": "data_cleaning"
        },
        estimated_duration=1
    )

    print("\nInitial Statistics:")

    print(agent.get_statistics())

    print("\nExecuting tasks...")

    agent.execute(task1)
    agent.execute(task2)

    print("\nFinal Agent Statistics:")

    statistics = agent.get_statistics()

    for key, value in statistics.items():

        print(
            f"{key}: {value}"
        )