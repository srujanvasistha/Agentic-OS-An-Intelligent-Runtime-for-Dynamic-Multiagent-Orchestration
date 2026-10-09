import csv
import os
from datetime import datetime


class MetricsLogger:

    def __init__(self, csv_path="data/metrics/metrics.csv"):
        self.csv_path = csv_path
        self.metrics = []

    def log_metric(
        self,
        task_id,
        agent_name,
        status,
        duration,
        cpu_percent=None,
        memory_percent=None,
        tokens=None
    ):
        metric = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "agent_name": agent_name,
            "status": status,
            "duration": duration,
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "tokens": tokens
        }

        self.metrics.append(metric)

        return metric

    def get_metrics(self):
        return self.metrics

    def clear(self):
        self.metrics.clear()

    def export_csv(self):
        directory = os.path.dirname(self.csv_path)

        if directory:
            os.makedirs(directory, exist_ok=True)

        fieldnames = [
            "timestamp",
            "task_id",
            "agent_name",
            "status",
            "duration",
            "cpu_percent",
            "memory_percent",
            "tokens"
        ]

        with open(
            self.csv_path,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames
            )

            writer.writeheader()

            writer.writerows(self.metrics)

        return self.csv_path

    def read_csv(self):
        if not os.path.exists(self.csv_path):
            return []

        with open(
            self.csv_path,
            "r",
            newline="",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)

            return list(reader)
    