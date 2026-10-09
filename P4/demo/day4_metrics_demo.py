from app.metrics.metrics_logger import MetricsLogger
from app.monitor.resource_monitor import ResourceMonitor


logger = MetricsLogger()
monitor = ResourceMonitor()


print("Collecting system resources...")

snapshot = monitor.get_snapshot()

print("\nSystem snapshot:")
print(snapshot)


logger.log_metric(
    task_id="task-101",
    agent_name="GeneralAgent",
    status="completed",
    duration=2.4,
    cpu_percent=snapshot["cpu_percent"],
    memory_percent=snapshot["memory"]["percent"],
    tokens=120
)


logger.log_metric(
    task_id="task-102",
    agent_name="FileAgent",
    status="completed",
    duration=1.8,
    cpu_percent=snapshot["cpu_percent"],
    memory_percent=snapshot["memory"]["percent"],
    tokens=95
)


logger.log_metric(
    task_id="task-103",
    agent_name="GeneralAgent",
    status="failed",
    duration=3.1,
    cpu_percent=snapshot["cpu_percent"],
    memory_percent=snapshot["memory"]["percent"],
    tokens=140
)


print("\nRecorded metrics:")

for metric in logger.get_metrics():
    print(metric)


csv_file = logger.export_csv()

print("\nMetrics exported to:")
print(csv_file)


print("\nReading metrics from CSV:")

saved_metrics = logger.read_csv()

for metric in saved_metrics:
    print(metric)