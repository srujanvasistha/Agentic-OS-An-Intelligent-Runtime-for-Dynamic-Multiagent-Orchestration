from app.metrics.metrics_logger import MetricsLogger


logger = MetricsLogger(
    "data/metrics/empty_metrics.csv"
)

print("Metrics before export:")
print(logger.get_metrics())

logger.export_csv()

print("\nEmpty CSV created successfully.")