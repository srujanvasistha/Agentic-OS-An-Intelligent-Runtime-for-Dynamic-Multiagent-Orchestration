from __future__ import annotations

import platform
import sys
from typing import Any
from .base_agent import BaseAgent
from tools.registry import ToolRegistry

try:
    import psutil
except ImportError:
    psutil = None


class MonitoringAgent(BaseAgent):
    """
    Monitoring Agent for AgentOS.
    Collects CPU, memory, queue, latency, and task-status information;
    detects anomalies and generates operational reports.
    """

    def __init__(
        self,
        tool_registry=None,
        model: str = "qwen2.5:1.5b",
        llm_client=None,
        task_store=None,
        task_manager=None,
    ):
        super().__init__(
            name="MonitoringAgent",
            model=model,
            capabilities=[
                "monitoring",
                "system_metrics",
                "anomaly_detection",
                "operational_reports",
                "diagnostics",
                "telemetry",
            ],
            allowed_tools=["system_info"],
            llm_client=llm_client,
        )
        self.tools = tool_registry if tool_registry is not None else ToolRegistry()
        self.task_store = task_store
        self.task_manager = task_manager

    def collect_telemetry(self) -> dict[str, Any]:
        """Gathers real runtime telemetry and hardware statistics."""
        data: dict[str, Any] = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "architecture": platform.machine(),
            "python_version": sys.version.split()[0],
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_used_mb": 0.0,
            "memory_total_mb": 0.0,
            "queue_length": 0,
            "total_tasks": 0,
            "status_breakdown": {},
            "anomalies": [],
        }

        if psutil is not None:
            try:
                data["cpu_percent"] = float(psutil.cpu_percent(interval=0.1))
                mem = psutil.virtual_memory()
                data["memory_percent"] = float(mem.percent)
                data["memory_used_mb"] = round((mem.total - mem.available) / (1024 * 1024), 1)
                data["memory_total_mb"] = round(mem.total / (1024 * 1024), 1)
            except Exception:
                pass

        if self.task_manager is not None:
            try:
                data["queue_length"] = self.task_manager.queue_size()
            except Exception:
                pass

        if self.task_store is not None:
            try:
                stats = self.task_store.statistics()
                data["total_tasks"] = stats.get("total", 0)
                data["status_breakdown"] = stats
            except Exception:
                pass

        # Anomaly detection logic
        anomalies = []
        if data["cpu_percent"] > 80.0:
            anomalies.append(f"HIGH_CPU_LOAD: CPU utilization is {data['cpu_percent']}% (>80% threshold).")
        if data["memory_percent"] > 85.0:
            anomalies.append(f"HIGH_MEMORY_PRESSURE: RAM utilization is {data['memory_percent']}% (>85% threshold).")
        if data["queue_length"] > 10:
            anomalies.append(f"QUEUE_BACKLOG: Scheduler queue has {data['queue_length']} pending tasks (>10 threshold).")

        failed_count = data["status_breakdown"].get("failed", 0)
        blocked_count = data["status_breakdown"].get("blocked", 0)
        if failed_count > 0:
            anomalies.append(f"FAILED_TASKS_DETECTED: {failed_count} task(s) failed in history.")
        if blocked_count > 0:
            anomalies.append(f"BLOCKED_ACTIONS_DETECTED: {blocked_count} task(s) blocked by security policies.")

        data["anomalies"] = anomalies
        return data

    def run(self, prompt: str) -> str:
        telemetry = self.collect_telemetry()
        has_anomalies = len(telemetry["anomalies"]) > 0
        overall_status = "WARNING / ATTENTION REQUIRED" if has_anomalies else "NOMINAL / HEALTHY"

        anomaly_text = "\n".join(f"- {a}" for a in telemetry["anomalies"]) if has_anomalies else "No active threshold violations detected."

        telemetry_summary = (
            f"=== LIVE AGENTOS TELEMETRY SNAPSHOT ===\n"
            f"System Status: {overall_status}\n"
            f"Platform: {telemetry['platform']} {telemetry['platform_release']} ({telemetry['architecture']})\n"
            f"CPU Utilization: {telemetry['cpu_percent']}%\n"
            f"Memory: {telemetry['memory_percent']}% ({telemetry['memory_used_mb']} MB / {telemetry['memory_total_mb']} MB)\n"
            f"Scheduler Queue Depth: {telemetry['queue_length']}\n"
            f"Total Processed Tasks: {telemetry['total_tasks']}\n"
            f"Task Status Breakdown: {telemetry['status_breakdown']}\n"
            f"Anomalies Detected:\n{anomaly_text}\n"
        )

        system_prompt = (
            "You are the AgentOS Monitoring Agent.\n\n"
            "Your responsibilities:\n"
            "1. Collect and report CPU, memory, queue, latency, and task-status information.\n"
            "2. Detect operational anomalies, bottlenecks, or policy blocks.\n"
            "3. Generate a structured, professional operational telemetry report.\n\n"
            "Use the live system telemetry snapshot provided below to answer the user's inquiry.\n"
            "Structure your report clearly with sections:\n"
            "• Executive Health Status\n"
            "• System Resource Utilization (CPU & RAM)\n"
            "• Scheduler Queue & Task Execution Metrics\n"
            "• Anomaly & Safety Audit Findings\n"
            "• Operational Recommendations"
        )

        llm_input = f"{system_prompt}\n\n{telemetry_summary}\n\nUser Request:\n{prompt}"
        try:
            result = self.generate(llm_input)
            if result and result.text.strip():
                return result.text
        except Exception:
            pass

        # Fallback structured report if LLM is unavailable
        return (
            f"### AgentOS Operational & Telemetry Report\n\n"
            f"**Overall Status**: {overall_status}\n\n"
            f"#### System Resource Utilization\n"
            f"- **CPU Usage**: {telemetry['cpu_percent']}%\n"
            f"- **RAM Usage**: {telemetry['memory_percent']}% ({telemetry['memory_used_mb']} MB used of {telemetry['memory_total_mb']} MB)\n"
            f"- **Host Platform**: {telemetry['platform']} {telemetry['platform_release']} ({telemetry['architecture']})\n\n"
            f"#### Queue & Task Status\n"
            f"- **Queue Depth**: {telemetry['queue_length']} pending task(s)\n"
            f"- **Total Recorded Tasks**: {telemetry['total_tasks']}\n"
            f"- **Task Breakdown**: {telemetry['status_breakdown']}\n\n"
            f"#### Anomaly Detection Findings\n"
            f"{anomaly_text}\n\n"
            f"#### Recommendation\n"
            f"System is operating within normal boundaries. Continue monitoring telemetry stream."
        )
