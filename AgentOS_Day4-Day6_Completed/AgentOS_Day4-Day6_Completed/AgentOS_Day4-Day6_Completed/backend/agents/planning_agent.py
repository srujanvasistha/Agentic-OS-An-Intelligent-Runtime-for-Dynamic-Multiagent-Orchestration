from __future__ import annotations

from typing import Any
from .base_agent import BaseAgent
from tools.registry import ToolRegistry


class PlanningAgent(BaseAgent):
    """
    Planning Agent for AgentOS.
    Breaks a complex request into subtasks, assigns them to suitable agents,
    tracks dependencies, and combines their outputs.
    """

    def __init__(self, tool_registry=None, model: str = "qwen2.5:1.5b", llm_client=None):
        super().__init__(
            name="PlanningAgent",
            model=model,
            capabilities=[
                "task_planning",
                "subtask_decomposition",
                "dependency_tracking",
                "workflow_orchestration",
                "pipeline_planning",
            ],
            allowed_tools=[],
            llm_client=llm_client,
        )
        self.tools = tool_registry if tool_registry is not None else ToolRegistry()

    def run(self, prompt: str) -> str:
        system_prompt = (
            "You are the AgentOS Planning Agent, the central workflow architect and task orchestrator.\n\n"
            "Your purpose is to:\n"
            "1. Deconstruct complex, multi-stage user requests into atomic, actionable subtasks.\n"
            "2. Assign each subtask to the most suitable AgentOS specialized agent:\n"
            "   • GeneralAgent: General reasoning, explanations, summarization, and conversation.\n"
            "   • FileAgent: File creation, filesystem navigation, reading, writing, and search.\n"
            "   • SecurityAgent: Security posture verification, sandboxing, threat analysis, permission checks.\n"
            "   • MonitoringAgent: Live CPU/RAM metrics, queue inspection, latency monitoring, anomaly detection.\n"
            "   • PlanningAgent: Workflow coordination and multi-phase orchestration.\n"
            "3. Identify and track dependencies between subtasks (Sequential vs Concurrent/Parallel execution).\n"
            "4. Specify how intermediate outputs will be combined, validated, and synthesized into the final result.\n\n"
            "Format your response cleanly with the following markdown sections:\n"
            "### 🎯 Strategic Orchestration Plan\n"
            "**Primary Goal**: Brief statement of the user's ultimate objective.\n\n"
            "#### 📋 Subtask Decomposition & Agent Assignment\n"
            "| ID | Subtask Name | Assigned Agent | Execution Mode | Dependencies |\n"
            "|:---|:-------------|:---------------|:---------------|:-------------|\n"
            "(Fill table with concrete steps)\n\n"
            "#### 🔄 Dependency & Execution Flow\n"
            "(Outline Phase 1 -> Phase 2 -> Final Synthesis)\n\n"
            "#### 🧩 Output Combination & Synthesis Strategy\n"
            "(Explain how data from each agent merges into the final output)\n\n"
            "#### 🛡️ Contingency & Failure Mitigation\n"
            "(What to do if a subtask or policy check fails)"
        )

        llm_input = f"{system_prompt}\n\nUser Request to Plan:\n{prompt}"
        try:
            result = self.generate(llm_input)
            if result and result.text.strip():
                return result.text
        except Exception:
            pass

        # Fallback structured plan if LLM is unavailable
        return (
            "### 🎯 Strategic Orchestration Plan\n\n"
            f"**Primary Goal**: Execute task plan for: *{prompt}*\n\n"
            "#### 📋 Subtask Decomposition & Agent Assignment\n"
            "| ID | Subtask Name | Assigned Agent | Execution Mode | Dependencies |\n"
            "|:---|:-------------|:---------------|:---------------|:-------------|\n"
            "| T1 | Requirements & Pre-Condition Analysis | GeneralAgent | Sequential | None |\n"
            "| T2 | Security Sandboxing & Policy Validation | SecurityAgent | Sequential | T1 |\n"
            "| T3 | Environment & Resource Telemetry Check | MonitoringAgent | Parallel | T1 |\n"
            "| T4 | Primary Execution & File / Data Ops | FileAgent / GeneralAgent | Sequential | T2, T3 |\n"
            "| T5 | Output Aggregation & Final Synthesis | PlanningAgent | Sequential | T4 |\n\n"
            "#### 🔄 Dependency & Execution Flow\n"
            "1. **Phase 1 (Preparation)**: T1 parses goals, T2 verifies permissions, T3 checks CPU/RAM headroom.\n"
            "2. **Phase 2 (Execution)**: T4 performs the core workload with sandboxed agents.\n"
            "3. **Phase 3 (Synthesis)**: T5 aggregates outputs into a unified deliverable.\n\n"
            "#### 🧩 Output Combination & Synthesis Strategy\n"
            "Intermediate artifacts from T4 are verified against safety policies (T2) and merged into the final operational summary.\n\n"
            "#### 🛡️ Contingency & Failure Mitigation\n"
            "If any security or resource threshold fails, execute fallback rollback and alert the administrator."
        )
