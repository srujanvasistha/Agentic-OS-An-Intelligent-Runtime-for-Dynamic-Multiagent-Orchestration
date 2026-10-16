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


class MetricsCollector:

    def __init__(self):

        self.start_time = None
        self.end_time = None

        self.tasks = []

    # -----------------------------------------
    # Start runtime measurement
    # -----------------------------------------

    def start(self):

        self.start_time = time.time()

    # -----------------------------------------
    # End runtime measurement
    # -----------------------------------------

    def stop(self):

        self.end_time = time.time()

    # -----------------------------------------
    # Record task
    # -----------------------------------------

    def record_task(self, task):

        self.tasks.append(task)

    # -----------------------------------------
    # Total runtime
    # -----------------------------------------

    def get_total_runtime(self):

        if self.start_time and self.end_time:

            return self.end_time - self.start_time

        return 0.0

    # -----------------------------------------
    # Average waiting time
    # -----------------------------------------

    def get_average_waiting_time(self):

        if not self.tasks:
            return 0.0

        total = sum(
            task.get_waiting_time()
            for task in self.tasks
        )

        return total / len(self.tasks)

    # -----------------------------------------
    # Average execution time
    # -----------------------------------------

    def get_average_execution_time(self):

        if not self.tasks:
            return 0.0

        total = sum(
            task.get_execution_time()
            for task in self.tasks
        )

        return total / len(self.tasks)

    # -----------------------------------------
    # Average turnaround time
    # -----------------------------------------

    def get_average_turnaround_time(self):

        if not self.tasks:
            return 0.0

        total = sum(
            task.get_turnaround_time()
            for task in self.tasks
        )

        return total / len(self.tasks)

    # -----------------------------------------
    # Throughput
    # -----------------------------------------

    def get_throughput(self):

        runtime = self.get_total_runtime()

        if runtime <= 0:
            return 0.0

        completed = sum(
            1
            for task in self.tasks
            if task.status == "COMPLETED"
        )

        return completed / runtime

    # -----------------------------------------
    # Generate report
    # -----------------------------------------

    def get_report(self):

        return {

            "total_tasks":
                len(self.tasks),

            "completed_tasks":
                sum(
                    1
                    for task in self.tasks
                    if task.status == "COMPLETED"
                ),

            "failed_tasks":
                sum(
                    1
                    for task in self.tasks
                    if task.status == "FAILED"
                ),

            "total_runtime":
                round(
                    self.get_total_runtime(),
                    2
                ),

            "average_waiting_time":
                round(
                    self.get_average_waiting_time(),
                    4
                ),

            "average_execution_time":
                round(
                    self.get_average_execution_time(),
                    4
                ),

            "average_turnaround_time":
                round(
                    self.get_average_turnaround_time(),
                    4
                ),

            "throughput":
                round(
                    self.get_throughput(),
                    4
                )
        }