import platform
import sys


class SystemInfoTool:
    """
    Provides safe, read-only information about the AgentOS runtime.
    """

    def get_info(self) -> dict:
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "architecture": platform.machine(),
            "python_version": sys.version.split()[0],
        }

    def summary(self) -> str:
        info = self.get_info()

        return (
            f"Platform: {info['platform']} "
            f"{info['platform_release']}\n"
            f"Architecture: {info['architecture']}\n"
            f"Python: {info['python_version']}"
        )