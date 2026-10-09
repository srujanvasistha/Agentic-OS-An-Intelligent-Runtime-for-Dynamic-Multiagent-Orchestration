from app.monitor.resource_monitor import ResourceMonitor


def test_cpu_usage():
    monitor = ResourceMonitor()

    cpu = monitor.get_cpu_usage()

    assert isinstance(cpu, float)
    assert 0 <= cpu <= 100


def test_memory_usage():
    monitor = ResourceMonitor()

    memory = monitor.get_memory_usage()

    assert "total" in memory
    assert "available" in memory
    assert "used" in memory
    assert "percent" in memory

    assert 0 <= memory["percent"] <= 100


def test_disk_usage():
    monitor = ResourceMonitor()

    disk = monitor.get_disk_usage()

    assert "total" in disk
    assert "used" in disk
    assert "free" in disk
    assert "percent" in disk

    assert 0 <= disk["percent"] <= 100


def test_cpu_count():
    monitor = ResourceMonitor()

    count = monitor.get_cpu_count()

    assert isinstance(count, int)
    assert count > 0


def test_process_count():
    monitor = ResourceMonitor()

    count = monitor.get_process_count()

    assert isinstance(count, int)
    assert count > 0


def test_snapshot():
    monitor = ResourceMonitor()

    snapshot = monitor.get_snapshot()

    assert "timestamp" in snapshot
    assert "cpu_percent" in snapshot
    assert "memory" in snapshot
    assert "disk" in snapshot
    assert "cpu_count" in snapshot
    assert "process_count" in snapshot