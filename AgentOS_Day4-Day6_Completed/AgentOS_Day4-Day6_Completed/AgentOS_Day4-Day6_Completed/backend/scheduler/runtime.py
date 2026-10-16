"""Core AgentOS runtime loop.

The runtime knows only the Scheduler interface and AgentManager. This keeps
P2 scheduler implementations replaceable without changing execution logic.
"""

import re
from datetime import datetime
from pathlib import Path
from schemas import Task, TaskResult, TaskStatus
from results_csv import append_result


class AgentRuntime:
    def __init__(self, task_manager, agent_manager, results_path: Path | None = None):
        self.task_manager = task_manager
        self.agent_manager = agent_manager
        self.results_path = results_path

    def submit(self, task: Task) -> Task:
        return self.task_manager.create_task(task)

    def run_next(self) -> TaskResult | None:
        task = self.task_manager.next_task()
        if task is None:
            return None

        agent = None
        started = task.started_at or datetime.now()
        try:
            agent = self.agent_manager.get_by_type(task.agent_type)
            if agent is None:
                raise ValueError(f"No agent registered for type: {task.agent_type.value}")

            task_img = getattr(task, "image_url", None)
            if hasattr(agent, "run") and task_img:
                try:
                    response = agent.run(task.prompt, image_url=task_img)
                except TypeError:
                    response = agent.run(task.prompt)
            else:
                response = agent.run(task.prompt)

            img_match = re.search(r"(/static/(?:generated|uploads)/[^\s\)\"']+)", response or "")
            result_img = img_match.group(1) if img_match else task_img

            llm = agent.last_llm_response
            self.task_manager.mark_done(task)
            current_scheduler = task.scheduler or self.task_manager.scheduler.__class__.__name__.replace("Scheduler", "")
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
                scheduler=current_scheduler,
                batch_id=task.batch_id,
                image_url=result_img,
                error=None,
            )
        except PermissionError as exc:
            self.task_manager.mark_blocked(task)
            current_scheduler = task.scheduler or self.task_manager.scheduler.__class__.__name__.replace("Scheduler", "")
            result = TaskResult(
                task_id=task.id,
                status=TaskStatus.BLOCKED,
                agent=agent.name if agent else None,
                model=agent.model if agent else None,
                response="",
                latency_seconds=(task.completed_at - started).total_seconds(),
                scheduler=current_scheduler,
                batch_id=task.batch_id,
                error=str(exc),
            )
        except Exception as exc:
            self.task_manager.mark_failed(task)
            current_scheduler = task.scheduler or self.task_manager.scheduler.__class__.__name__.replace("Scheduler", "")
            result = TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                agent=agent.name if agent else None,
                model=agent.model if agent else None,
                response=f"Task execution failed: {exc}",
                latency_seconds=(task.completed_at - started).total_seconds(),
                scheduler=current_scheduler,
                batch_id=task.batch_id,
                error=str(exc),
            )

        if self.results_path:
            self._record(task, result)
        return result

    def run_until_empty(self) -> list[TaskResult]:
        results = []
        while self.task_manager.queue_size() > 0:
            result = self.run_next()
            if result is not None:
                results.append(result)
        return results

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
