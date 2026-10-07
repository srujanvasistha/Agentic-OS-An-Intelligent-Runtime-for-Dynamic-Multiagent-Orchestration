"""Backward-compatible adapter for code that still imports TaskExecutor.

The Day 2 runtime is implemented by AgentRuntime. This adapter delegates to
that runtime so older integrations do not bypass task lifecycle management.
"""

from scheduler.runtime import AgentRuntime


class TaskExecutor:
    def __init__(self, agent_selector=None):
        self.agent_selector = agent_selector
        self._runtime = None

    def bind_runtime(self, runtime: AgentRuntime):
        self._runtime = runtime

    def execute(self, task):
        if self._runtime is None:
            raise RuntimeError("TaskExecutor must be bound to AgentRuntime")
        self._runtime.submit(task)
        result = self._runtime.run_next()
        return result
