import csv

from app.metrics.metrics_logger import MetricsLogger


def test_log_metric():
    logger = MetricsLogger()

    metric = logger.log_metric(
        task_id="test-001",
        agent_name="TestAgent",
        status="completed",
        duration=1.5,
        cpu_percent=20.0,
        memory_percent=40.0,
        tokens=50
    )

    assert metric["task_id"] == "test-001"
    assert metric["agent_name"] == "TestAgent"
    assert metric["status"] == "completed"
    assert metric["duration"] == 1.5
    assert metric["tokens"] == 50


def test_get_metrics():
    logger = MetricsLogger()

    logger.log_metric(
        task_id="test-002",
        agent_name="TestAgent",
        status="completed",
        duration=2.0
    )

    metrics = logger.get_metrics()

    assert len(metrics) == 1
    assert metrics[0]["task_id"] == "test-002"


def test_clear():
    logger = MetricsLogger()

    logger.log_metric(
        task_id="test-003",
        agent_name="TestAgent",
        status="completed",
        duration=1.0
    )

    assert len(logger.get_metrics()) == 1

    logger.clear()

    assert len(logger.get_metrics()) == 0


def test_export_csv(tmp_path):
    csv_path = tmp_path / "metrics.csv"

    logger = MetricsLogger(str(csv_path))

    logger.log_metric(
        task_id="test-004",
        agent_name="TestAgent",
        status="completed",
        duration=3.0,
        cpu_percent=30.0,
        memory_percent=50.0,
        tokens=100
    )

    exported_file = logger.export_csv()

    assert exported_file == str(csv_path)
    assert csv_path.exists()

    with open(
        csv_path,
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)
        rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["task_id"] == "test-004"


def test_read_csv(tmp_path):
    csv_path = tmp_path / "metrics.csv"

    logger = MetricsLogger(str(csv_path))

    logger.log_metric(
        task_id="test-005",
        agent_name="TestAgent",
        status="completed",
        duration=4.0
    )

    logger.export_csv()

    saved_metrics = logger.read_csv()

    assert len(saved_metrics) == 1
    assert saved_metrics[0]["task_id"] == "test-005"