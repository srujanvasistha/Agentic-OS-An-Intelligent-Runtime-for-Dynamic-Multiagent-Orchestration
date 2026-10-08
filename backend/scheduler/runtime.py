"""Core AgentOS Day 3 runtime: scheduler + monitor + bounded inference."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
from datetime import datetime
from pathlib import Path
import os

from schemas import Task, TaskResult, TaskStatus
from results_csv import append_result
from policy.metrics import append_metric
from memory.store import MemoryStore
from scheduler.config import default_model_tier, max_concurrency, model_for_tier


class AgentRuntime:
    def __init__(
        self,
        task_manager,
        agent_manager,
        results_path: Path | None = None,
        monitor=None,
        model_tier: str | None = None,
        concurrency_limit: int | None = None,
        memory=None,
        metrics_path: Path | None = None,
    ):
        self.task_manager = task_manager
        self.agent_manager = agent_manager
        self.results_path = results_path
        self.monitor = monitor
        self.model_tier = (model_tier or default_model_tier()).lower()
        self.concurrency_limit = concurrency_limit or max_concurrency()
        if self.concurrency_limit not in (1, 2):
            raise ValueError("concurrency_limit must be 1 or 2")
        self.memory = memory or MemoryStore()
        self.metrics_path = metrics_path

    def submit(self, task: Task) -> Task:
        return self.task_manager.create_task(task)

    def get_system_state(self) -> dict:
        if self.monitor is None:
            return {}
        provider = getattr(self.monitor, "get_system_state", self.monitor)
        return provider()

    def _sync_scheduler_state(self):
        scheduler = self.task_manager.scheduler
        setter = getattr(scheduler, "set_system_state", None)
        if setter:
            setter(self.get_system_state())

    def _select_model_tier(self, task: Task, state: dict) -> str:
        configured = os.getenv("AGENTOS_MODEL_TIER", self.model_tier).lower()
        # Resource-aware scheduling uses the small tier under sustained pressure.
        if getattr(self.task_manager.scheduler, "name", "") == "resource_aware":
            pressure = max(float(state.get("cpu_percent", 0)), float(state.get("memory_percent", 0)))
            if pressure >= 80:
                return "0.5b"
        return configured

    def _execute(self, task: Task) -> TaskResult:
        agent = None
        started = task.started_at or datetime.now()
        try:
            registered_agent = self.agent_manager.get_by_type(task.agent_type)
            if registered_agent is None:
                raise ValueError(f"No agent registered for type: {task.agent_type.value}")

            # Each parallel inference gets an isolated agent/client instance so
            # model selection and last_llm_response cannot race across tasks.
            agent = copy.copy(registered_agent)
            agent.task_id = task.id
            state = self.get_system_state()
            tier = self._select_model_tier(task, state)
            agent.configure_model(model_for_tier(tier))
            memory_context = self.memory.context_for(task.prompt)
            prompt = f"{memory_context}\n\nCurrent task:\n{task.prompt}" if memory_context else task.prompt
            response = agent.run(prompt)
            llm = agent.last_llm_response
            self.task_manager.mark_done(task)
            result = TaskResult(
                task_id=task.id,
                status=TaskStatus.DONE,
                agent=agent.name,
                model=agent.model,
                response=response,
                tokens_used=llm.tokens_used if llm else 0,
                llm_latency_seconds=llm.latency_seconds if llm else 0.0,
                llm_backend=llm.backend if llm else "unknown",
                latency_seconds=(task.completed_at - started).total_seconds(),
                error=None,
            )
        except PermissionError as exc:
            self.task_manager.mark_blocked(task)
            self._record_metric(task.id, "task_blocked", metadata={"error": str(exc)})
            result = TaskResult(
                task_id=task.id, status=TaskStatus.BLOCKED,
                agent=agent.name if agent else None,
                model=agent.model if agent else None,
                response="", latency_seconds=(task.completed_at - started).total_seconds(),
                error=str(exc),
            )
        except Exception as exc:
            self.task_manager.mark_failed(task)
            event = "model_timeout" if "timeout" in str(exc).lower() else "task_failed"
            self._record_metric(task.id, event, metadata={"error": str(exc)})
            result = TaskResult(
                task_id=task.id, status=TaskStatus.FAILED,
                agent=agent.name if agent else None,
                model=agent.model if agent else None,
                response=f"Task execution failed: {exc}",
                latency_seconds=(task.completed_at - started).total_seconds(),
                error=str(exc),
            )

        if result.status == TaskStatus.DONE:
            self.memory.remember(task.id, task.prompt, result.status.value, result.response)
        else:
            self.memory.remember(task.id, task.prompt, result.status.value, result.error or result.response)
        if self.results_path:
            self._record(task, result)
        return result

    def run_next(self) -> TaskResult | None:
        self._sync_scheduler_state()
        task = self.task_manager.next_task()
        return self._execute(task) if task is not None else None

    def run_pending(self, limit: int | None = None) -> list[TaskResult]:
        """Execute up to the configured 1–2 inference tasks concurrently."""
        self._sync_scheduler_state()
        slots = min(limit or self.concurrency_limit, self.concurrency_limit)
        tasks = []
        for _ in range(slots):
            task = self.task_manager.next_task()
            if task is None:
                break
            tasks.append(task)
        if not tasks:
            return []

        if len(tasks) == 1:
            return [self._execute(tasks[0])]

        results = []
        with ThreadPoolExecutor(max_workers=len(tasks), thread_name_prefix="agentos-infer") as pool:
            futures = {pool.submit(self._execute, task): task for task in tasks}
            for future in as_completed(futures):
                results.append(future.result())
        return results

    def run_until_empty(self) -> list[TaskResult]:
        results = []
        while self.task_manager.queue_size() > 0:
            results.extend(self.run_pending())
        return results

    def _record_metric(self, task_id: str, event: str, metadata=None) -> None:
        if self.metrics_path:
            append_metric(self.metrics_path, task_id, event, metadata=metadata)

    def _record(self, task: Task, result: TaskResult) -> None:
        append_result(self.results_path, {
            "timestamp": task.completed_at.isoformat() if task.completed_at else "",
            "task_id": task.id,
            "agent": result.agent or "",
            "model": result.model or "",
            "status": result.status.value,
            "priority": task.priority,
            "complexity": task.complexity,
            "risk_level": task.risk_level,
            "estimated_tokens": task.estimated_tokens,
            "tokens_used": result.tokens_used,
            "llm_latency_seconds": result.llm_latency_seconds,
            "latency_seconds": result.latency_seconds,
            "llm_backend": result.llm_backend,
        })
