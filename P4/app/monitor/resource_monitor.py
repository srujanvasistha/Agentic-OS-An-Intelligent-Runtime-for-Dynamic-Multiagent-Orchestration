import psutil
from datetime import datetime


class ResourceMonitor:

    def get_cpu_usage(self):
        return psutil.cpu_percent(interval=1)

    def get_memory_usage(self):
        memory = psutil.virtual_memory()

        return {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percent": memory.percent
        }

    def get_disk_usage(self):
        disk = psutil.disk_usage("C:\\")

        return {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent
        }

    def get_cpu_count(self):
        return psutil.cpu_count()

    def get_process_count(self):
        return len(psutil.pids())

    def get_snapshot(self):
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": self.get_cpu_usage(),
            "memory": self.get_memory_usage(),
            "disk": self.get_disk_usage(),
            "cpu_count": self.get_cpu_count(),
            "process_count": self.get_process_count()
        }

    def print_snapshot(self):
        snapshot = self.get_snapshot()

        print("\n===== SYSTEM RESOURCE SNAPSHOT =====")

        print(
            "Timestamp:",
            snapshot["timestamp"]
        )

        print(
            "CPU:",
            snapshot["cpu_percent"],
            "%"
        )

        print(
            "RAM:",
            snapshot["memory"]["percent"],
            "%"
        )

        print(
            "Disk:",
            snapshot["disk"]["percent"],
            "%"
        )

        print(
            "CPU cores:",
            snapshot["cpu_count"]
        )

        print(
            "Processes:",
            snapshot["process_count"]
        )

    