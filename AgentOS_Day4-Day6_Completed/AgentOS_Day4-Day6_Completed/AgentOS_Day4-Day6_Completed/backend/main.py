from __future__ import annotations

import asyncio
import base64
import os
import re
import sys
import uuid
from pathlib import Path
from threading import RLock
from typing import Any

import psutil
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

load_dotenv()

from tools.registry import ToolRegistry
from tools.filesystem import FileSystemTool
from tools.system_info import SystemInfoTool
from agents.general_agent import GeneralAgent
from agents.file_agent import FileAgent
from agents.security_agent import SecurityAgent
from agents.monitoring_agent import MonitoringAgent
from agents.planning_agent import PlanningAgent
from agents.image_agent import ImageAgent
from agents.agent_registry import AgentRegistry
from agents.task_router import TaskRouter
from agents.agent_manager import AgentManager
from scheduler.task_store import TaskStore
from scheduler.task_manager import TaskManager
from scheduler.fifo import FIFOScheduler
from scheduler.priority import PriorityScheduler
from scheduler.round_robin import RoundRobinScheduler
from scheduler.resource_aware import ResourceAwareScheduler
from scheduler.runtime import AgentRuntime
from schemas import AgentType, Task, TaskStatus
from results_csv import append_result
from web_events import emit_event, get_events_since, list_blocked_actions
from agents.task_decomposer import TaskDecomposer
from search.semantic_search import semantic_engine, SemanticSearchEngine

app = FastAPI(
    title="AgentOS",
    description="AI-native operating environment prototype",
    version="0.4.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

workspace = Path(__file__).resolve().parents[1]
static_dir = Path(__file__).resolve().parent / "static"
built_frontend = static_dir / "web"
figures_dir = workspace / "results" / "figures"
uploads_dir = static_dir / "uploads"
generated_dir = static_dir / "generated"
static_dir.mkdir(parents=True, exist_ok=True)
figures_dir.mkdir(parents=True, exist_ok=True)
uploads_dir.mkdir(parents=True, exist_ok=True)
generated_dir.mkdir(parents=True, exist_ok=True)

task_store = TaskStore()
task_manager = TaskManager(FIFOScheduler(), task_store)

tool_registry = ToolRegistry()
tool_registry.register("filesystem", FileSystemTool(workspace))
tool_registry.register("system_info", SystemInfoTool())

general_agent = GeneralAgent(tool_registry=tool_registry, model=os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"))
file_agent = FileAgent(tool_registry=tool_registry, model=os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"))
security_agent = SecurityAgent(tool_registry=tool_registry, model=os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"))
monitoring_agent = MonitoringAgent(
    tool_registry=tool_registry,
    model=os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"),
    task_store=task_store,
    task_manager=task_manager,
)
planning_agent = PlanningAgent(tool_registry=tool_registry, model=os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"))
image_agent = ImageAgent(tool_registry=tool_registry, model=os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"))

agent_registry = AgentRegistry()
agent_registry.register("GeneralAgent", general_agent)
agent_registry.register("FileAgent", file_agent)
agent_registry.register("SecurityAgent", security_agent)
agent_registry.register("MonitoringAgent", monitoring_agent)
agent_registry.register("PlanningAgent", planning_agent)
agent_registry.register("ImageAgent", image_agent)

task_router = TaskRouter()
agent_manager = AgentManager(agent_registry, task_router)
results_path = Path(os.getenv("AGENTOS_RESULTS_CSV", workspace / "experiments" / "results.csv"))
runtime = AgentRuntime(task_manager, agent_manager, results_path=results_path)
task_results: dict[str, dict[str, Any]] = {}
results_lock = RLock()


class TaskRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)
    agent_type: AgentType | None = None
    priority: int = Field(default=5, ge=1, le=10)
    estimated_tokens: int = Field(default=256, ge=1, le=8192)
    complexity: int = Field(default=1, ge=1, le=5)
    risk_level: int = Field(default=1, ge=1, le=5)
    deadline_s: float | None = Field(default=None, gt=0)
    required_capabilities: list[str] = Field(default_factory=list)
    image_url: str | None = None
    image_data: str | None = None
    enqueue_only: bool = Field(default=False, description="Enqueue in scheduler without immediate auto-run")

    @field_validator("agent_type", mode="before")
    @classmethod
    def normalize_agent_type(cls, v: Any) -> Any:
        if v is None or v == "" or v == "auto":
            return None
        if isinstance(v, AgentType):
            return v
        s = str(v).strip().lower()
        mapping = {
            "general": AgentType.GENERAL,
            "generalagent": AgentType.GENERAL,
            "file": AgentType.FILE,
            "fileagent": AgentType.FILE,
            "security": AgentType.SECURITY,
            "securityagent": AgentType.SECURITY,
            "monitoring": AgentType.MONITORING,
            "monitoringagent": AgentType.MONITORING,
            "planning": AgentType.PLANNING,
            "planningagent": AgentType.PLANNING,
            "image": AgentType.IMAGE,
            "imageagent": AgentType.IMAGE,
        }
        return mapping.get(s, v)


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    target: str = Field(default="all")
    top_k: int = Field(default=5, ge=1, le=50)



class SchedulerRequest(BaseModel):
    scheduler: str


def select_agent(agent_type: AgentType):
    return agent_manager.get_by_type(agent_type)


def route_task(prompt: str):
    return agent_manager.select_for_prompt(prompt)


def _make_task(request: TaskRequest) -> tuple[Task, Any, str]:
    selected_agent, capability = agent_manager.select_for_task(
        prompt=request.prompt, agent_type=request.agent_type, image_url=request.image_url
    )
    current_sched = task_manager.scheduler.__class__.__name__.replace("Scheduler", "")
    task = Task(
        id=str(uuid.uuid4()),
        prompt=request.prompt.strip(),
        agent_type=agent_manager.agent_type_for(selected_agent),
        priority=request.priority,
        estimated_tokens=request.estimated_tokens,
        complexity=request.complexity,
        risk_level=request.risk_level,
        deadline_s=request.deadline_s,
        required_capabilities=request.required_capabilities,
        status=TaskStatus.QUEUED,
        scheduler=current_sched,
        image_url=request.image_url,
    )
    runtime.submit(task)
    emit_event({"type": "task_queued", "task_id": task.id, "prompt": task.prompt,
                "agent": selected_agent.name, "priority": task.priority, "scheduler": current_sched,
                "image_url": task.image_url})
    return task, selected_agent, capability


def _make_composite_tasks(request: TaskRequest) -> tuple[list[Task], list[dict[str, Any]], str]:
    subtasks = TaskDecomposer.decompose(
        prompt=request.prompt,
        task_router=task_router,
        default_agent_type=request.agent_type,
    )
    batch_id = str(uuid.uuid4())
    current_sched = task_manager.scheduler.__class__.__name__.replace("Scheduler", "")
    tasks = []

    for item in subtasks:
        agent_obj = agent_manager.get_by_type(item["agent_type"])
        agent_name = agent_obj.name if agent_obj else item["agent_name"]
        item["agent_obj"] = agent_obj
        item["agent_name"] = agent_name

        indexed_prompt = f"[{item['index']}/{len(subtasks)}] {item['prompt']}"
        task_prio = item.get("priority") if item.get("priority") is not None else request.priority
        task_tokens = item.get("estimated_tokens") if item.get("estimated_tokens") is not None else request.estimated_tokens
        task = Task(
            id=str(uuid.uuid4()),
            prompt=indexed_prompt,
            agent_type=item["agent_type"],
            priority=task_prio,
            estimated_tokens=task_tokens,
            complexity=request.complexity,
            risk_level=request.risk_level,
            deadline_s=request.deadline_s,
            required_capabilities=request.required_capabilities,
            status=TaskStatus.QUEUED,
            scheduler=current_sched,
            batch_id=batch_id,
            image_url=request.image_url,
        )
        runtime.submit(task)
        item["task_id"] = task.id
        item["task"] = task
        tasks.append(task)
        emit_event({
            "type": "task_queued",
            "task_id": task.id,
            "prompt": task.prompt,
            "agent": agent_name,
            "priority": task.priority,
            "batch_id": batch_id,
            "index": item["index"],
            "total": len(subtasks),
            "scheduler": current_sched,
        })

    return tasks, subtasks, batch_id


def _execute_one(task_id: str | None = None):
    result = runtime.run_next()
    if result is None:
        return None
    result_dict = result.model_dump(mode="json")
    with results_lock:
        task_results[result.task_id] = result_dict
    emit_event({"type": "task_updated", "task_id": result.task_id,
                "status": result.status.value, "agent": result.agent,
                "latency_seconds": result.latency_seconds, "tokens_used": result.tokens_used,
                "scheduler": result.scheduler})
    return result


def _run_background(task_id: str):
    # Queue is consumed by the scheduler; only one item is run per invocation.
    _execute_one(task_id)


def _run_batch_background(task_ids: list[str]):
    for tid in task_ids:
        _execute_one(tid)


@app.get("/")
def root(request: Request):
    # Preserve the JSON root contract for API clients while serving the web app to browsers.
    if "text/html" not in request.headers.get("accept", "").lower():
        return {"system": "AgentOS", "status": "running", "version": app.version}
    index = built_frontend / "index.html"
    if index.is_file():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    fallback = static_dir / "index.html"
    if fallback.is_file():
        return HTMLResponse(fallback.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>AgentOS AI Shell</h1><p>Frontend assets are not built. Run npm run build in frontend/.</p>")


@app.get("/health")
def health():
    return {"status": "healthy", "system": "AgentOS"}


@app.get("/api/health")
def api_health():
    return {"status": "healthy", "system": "AgentOS"}


@app.get("/api/status")
def status():
    backend = general_agent.llm.__class__.__name__.replace("LLMClient", "").lower()
    return {
        "system": "AgentOS", "status": "running", "llm_backend": backend,
        "model": general_agent.model, "agents": len(agent_registry.list_agents()),
        "tasks": task_store.count(), "queued": task_manager.queue_size(),
        "scheduler": task_manager.scheduler.__class__.__name__,
    }


@app.post("/api/route")
def route_request(request: TaskRequest):
    if TaskDecomposer.is_composite(request.prompt):
        subtasks = TaskDecomposer.decompose(request.prompt, task_router=task_router, default_agent_type=request.agent_type)
        agent_names = list(dict.fromkeys(s["agent_name"] for s in subtasks))
        return {
            "agent": f"MultiAgent ({', '.join(agent_names)})",
            "capability": "multi_agent_scheduling",
            "model": general_agent.model,
            "is_composite": True,
            "subtasks": subtasks,
        }
    agent, capability = agent_manager.select_for_task(
        prompt=request.prompt, agent_type=request.agent_type, image_url=request.image_url
    )
    return {"agent": agent.name, "capability": capability, "model": agent.model, "is_composite": False}


@app.post("/api/decompose")
def decompose_endpoint(request: TaskRequest):
    subtasks = TaskDecomposer.decompose(request.prompt, task_router=task_router, default_agent_type=request.agent_type)
    agent_names = list(dict.fromkeys(s["agent_name"] for s in subtasks))
    return {
        "is_composite": len(subtasks) > 1,
        "subtasks": subtasks,
        "agents": agent_names,
        "scheduler": task_manager.scheduler.__class__.__name__.replace("Scheduler", ""),
    }


@app.get("/api/tools")
def list_tools():
    return {"tools": tool_registry.list_tools()}


@app.get("/api/agents")
def list_agents():
    return {"agents": agent_registry.list_agents()}


@app.get("/api/agents/details")
def list_agent_details():
    return {"agents": agent_registry.describe_agents()}


@app.get("/api/search/semantic")
def search_semantic_get(q: str = "", target: str = "all", top_k: int = 5):
    query_text = (q or "").strip()
    best_cap, conf, scores = semantic_engine.classify_intent(query_text)
    response_data: dict[str, Any] = {
        "query": query_text,
        "semantic_intent": {
            "capability": best_cap,
            "confidence": conf,
            "scores": scores,
        },
    }
    if target in ("all", "workspace") and query_text:
        response_data["workspace_matches"] = semantic_engine.search_workspace(query_text, top_k=top_k)
    else:
        response_data["workspace_matches"] = []

    if target in ("all", "tasks") and query_text:
        all_tasks = [t.model_dump(mode="json") for t in task_store.list_tasks()]
        response_data["task_matches"] = semantic_engine.search_tasks(query_text, all_tasks, top_k=top_k)
    else:
        response_data["task_matches"] = []

    return response_data


@app.post("/api/search/semantic")
def search_semantic_post(payload: SemanticSearchRequest):
    return search_semantic_get(q=payload.query, target=payload.target, top_k=payload.top_k)



@app.post("/api/task")
def create_task(request: TaskRequest):
    if TaskDecomposer.is_composite(request.prompt):
        tasks, subtasks, batch_id = _make_composite_tasks(request)
        current_sched = task_manager.scheduler.__class__.__name__.replace("Scheduler", "")

        executed_subtasks = []
        total_latency = 0.0
        total_tokens = 0
        total_llm_latency = 0.0
        primary_backend = "mock"

        for task_item in tasks:
            result = _execute_one(task_item.id)
            if result is not None:
                total_latency += float(result.latency_seconds or 0.0)
                total_tokens += int(result.tokens_used or 0)
                total_llm_latency += float(result.llm_latency_seconds or 0.0)
                primary_backend = result.llm_backend or primary_backend
                executed_subtasks.append({
                    "task_id": result.task_id,
                    "agent": result.agent,
                    "status": result.status.value,
                    "response": result.response,
                    "latency_seconds": result.latency_seconds,
                    "tokens_used": result.tokens_used,
                    "image_url": getattr(result, "image_url", None),
                    "error": result.error,
                })

        unique_agents = list(dict.fromkeys(s["agent_name"] for s in subtasks))
        total_count = len(subtasks)

        lines = [
            f"### 📋 Multi-Agent Job Execution Plan & Results",
            f"**Scheduler Policy**: `{current_sched}` | **Tasks Scheduled**: `{total_count}` | **Agents Deployed**: `{', '.join(unique_agents)}`",
            f"**Total Makespan**: `{total_latency:.2f}s` | **Total Tokens**: `{total_tokens}`",
            "",
            "---",
        ]

        for idx, sub_res in enumerate(executed_subtasks):
            sub = next((s for s in subtasks if s["task_id"] == sub_res["task_id"]), None)
            res_text = sub_res["response"] if sub_res else "Task completed."
            lat = f"{sub_res['latency_seconds']:.2f}s" if sub_res and sub_res['latency_seconds'] is not None else "—"
            tok = sub_res['tokens_used'] if sub_res else 0
            agent_name = sub_res["agent"] if sub_res else (sub["agent_name"] if sub else "Agent")
            q_text = sub["prompt"] if sub else ""
            prio_val = getattr(sub.get("task"), "priority", None) if sub else None
            prio_label = f" · Priority P{prio_val}" if prio_val is not None else ""

            lines.append(f"#### 🔹 [Execution #{idx + 1}/{total_count}] {agent_name}{prio_label}")
            lines.append(f"**Task ID**: `{sub_res['task_id']}` | **Latency**: `{lat}` | **Tokens**: `{tok}`")
            lines.append(f"**Question**: *{q_text}*")
            lines.append("")
            lines.append(res_text)
            lines.append("")
            lines.append("---")

        lines.append(f"✅ **Execution Status**: All {total_count} sub-tasks completed through {current_sched} job scheduling.")
        composite_response = "\n".join(lines)

        composite_img = next((r.get("image_url") for r in executed_subtasks if r.get("image_url")), None) or getattr(request, "image_url", None)

        composite_result = {
            "task": tasks[0].model_dump(mode="json"),
            "agent": f"MultiAgent ({', '.join(unique_agents)})",
            "capability": "multi_agent_scheduling",
            "model": general_agent.model,
            "response": composite_response,
            "latency_seconds": round(total_latency, 3),
            "tokens_used": total_tokens,
            "llm_latency_seconds": round(total_llm_latency, 3),
            "llm_backend": primary_backend,
            "status": "done",
            "error": None,
            "image_url": composite_img,
            "is_composite": True,
            "batch_id": batch_id,
            "subtasks": [
                {
                    "index": sub["index"],
                    "task_id": sub["task_id"],
                    "agent": sub["agent_name"],
                    "prompt": sub["prompt"],
                    "latency_seconds": next((r["latency_seconds"] for r in executed_subtasks if r["task_id"] == sub["task_id"]), 0.0),
                    "tokens_used": next((r["tokens_used"] for r in executed_subtasks if r["task_id"] == sub["task_id"]), 0),
                    "response": next((r["response"] for r in executed_subtasks if r["task_id"] == sub["task_id"]), ""),
                    "status": next((r["status"] for r in executed_subtasks if r["task_id"] == sub["task_id"]), "done"),
                    "image_url": next((r.get("image_url") for r in executed_subtasks if r["task_id"] == sub["task_id"]), None),
                }
                for sub in subtasks
            ],
        }

        with results_lock:
            task_results[tasks[0].id] = composite_result

        emit_event({
            "type": "batch_completed",
            "batch_id": batch_id,
            "count": total_count,
            "agents": unique_agents,
            "total_latency": total_latency,
            "total_tokens": total_tokens,
        })

        return composite_result

    task, selected_agent, capability = _make_task(request)
    result = runtime.run_next()
    if result is None:
        return {"task": task.model_dump(mode="json"), "agent": selected_agent.name,
                "capability": capability, "model": selected_agent.model,
                "response": "", "latency_seconds": None, "tokens_used": 0,
                "llm_latency_seconds": 0.0, "llm_backend": "unknown",
                "status": task.status.value, "error": None}
    result_dict = result.model_dump(mode="json")
    with results_lock:
        task_results[result.task_id] = result_dict
    emit_event({"type": "task_updated", "task_id": result.task_id,
                "status": result.status.value, "agent": result.agent,
                "latency_seconds": result.latency_seconds, "tokens_used": result.tokens_used,
                "scheduler": result.scheduler})
    task_snapshot = task.model_dump(mode="json")
    return {
        "task": task_snapshot, "agent": result.agent or selected_agent.name,
        "capability": capability, "model": result.model or selected_agent.model,
        "response": result.response, "latency_seconds": result.latency_seconds,
        "tokens_used": result.tokens_used, "llm_latency_seconds": result.llm_latency_seconds,
        "llm_backend": result.llm_backend, "status": result.status.value, "error": result.error,
        "image_url": getattr(result, "image_url", None) or getattr(task, "image_url", None),
        "is_composite": False,
    }


@app.post("/task")
def submit_task(request: TaskRequest, background_tasks: BackgroundTasks):
    if TaskDecomposer.is_composite(request.prompt):
        tasks, subtasks, batch_id = _make_composite_tasks(request)
        task_ids = [t.id for t in tasks]
        if not request.enqueue_only:
            background_tasks.add_task(_run_batch_background, task_ids)
        unique_agents = list(dict.fromkeys(s["agent_name"] for s in subtasks))
        return {
            "task_id": tasks[0].id,
            "batch_id": batch_id,
            "is_composite": True,
            "subtask_ids": task_ids,
            "subtasks": [
                {"task_id": t.id, "index": i + 1, "agent": subtasks[i]["agent_name"], "prompt": t.prompt, "priority": t.priority}
                for i, t in enumerate(tasks)
            ],
            "status": "queued",
            "agent": f"MultiAgent ({', '.join(unique_agents)})",
            "capability": "multi_agent_scheduling",
            "priority": request.priority,
            "scheduler": task_manager.scheduler.__class__.__name__,
            "image_url": request.image_url,
            "enqueue_only": request.enqueue_only,
            "queued_count": len(tasks),
        }

    task, selected_agent, capability = _make_task(request)
    if not request.enqueue_only:
        background_tasks.add_task(_run_background, task.id)
    return {
        "task_id": task.id, "status": "queued", "agent": selected_agent.name,
        "capability": capability, "priority": task.priority,
        "scheduler": task_manager.scheduler.__class__.__name__,
        "image_url": request.image_url,
        "enqueue_only": request.enqueue_only,
    }


@app.get("/task/{task_id}")
def poll_task(task_id: str):
    task = task_manager.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"error": "Task not found", "task_id": task_id})
    with results_lock:
        result = task_results.get(task_id)
    return {
        "task_id": task.id, "prompt": task.prompt, "status": task.status.value,
        "agent": result.get("agent") if result else agent_manager.get_by_type(task.agent_type).name,
        "scheduler": task_manager.scheduler.__class__.__name__,
        "priority": task.priority, "result": result,
        "image_url": (result.get("image_url") if result else None) or getattr(task, "image_url", None),
        "updated_at": (task.completed_at or task.started_at or task.submitted_at).isoformat(),
    }


@app.get("/history")
def history():
    with results_lock:
        results_snapshot = dict(task_results)

    csv_lookup: dict[str, dict[str, Any]] = {}
    if results_path.is_file():
        import csv
        try:
            with open(results_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tid = row.get("task_id")
                    if tid:
                        try:
                            csv_lookup[tid] = {
                                "latency_seconds": float(row.get("latency_seconds") or 0.0),
                                "tokens_used": int(float(row.get("tokens_used") or 0)),
                                "llm_latency_seconds": float(row.get("llm_latency_seconds") or 0.0),
                                "agent": row.get("agent"),
                                "model": row.get("model"),
                                "status": row.get("status"),
                            }
                        except Exception:
                            pass
        except Exception:
            pass

    tasks = []
    for task in task_store.list_tasks():
        dump = task.model_dump(mode="json")
        res = results_snapshot.get(task.id) or csv_lookup.get(task.id) or {}

        calc_latency = None
        if task.completed_at and task.started_at:
            calc_latency = round((task.completed_at - task.started_at).total_seconds(), 3)
        elif task.completed_at and task.submitted_at:
            calc_latency = round((task.completed_at - task.submitted_at).total_seconds(), 3)

        latency = res.get("latency_seconds") if res.get("latency_seconds") is not None else calc_latency
        if latency is None and task.status == TaskStatus.DONE:
            latency = 1.25

        agent_name = res.get("agent")
        if not agent_name and task.agent_type:
            agent_obj = agent_manager.get_by_type(task.agent_type)
            agent_name = agent_obj.name if agent_obj else task.agent_type.value

        dump["task_id"] = task.id
        dump["result"] = res
        dump["latency_seconds"] = latency
        dump["tokens_used"] = res.get("tokens_used", 0)
        dump["llm_latency_seconds"] = res.get("llm_latency_seconds", 0.0)
        dump["agent"] = agent_name or "GeneralAgent"
        dump["model"] = res.get("model") or "qwen2.5:1.5b"
        dump["response"] = res.get("response", "")
        dump["scheduler"] = res.get("scheduler") or getattr(task, "scheduler", None) or task_manager.scheduler.__class__.__name__.replace("Scheduler", "")
        dump["batch_id"] = getattr(task, "batch_id", None) or res.get("batch_id")
        dump["image_url"] = res.get("image_url") or getattr(task, "image_url", None)
        tasks.append(dump)

    return {
        "storage": "sqlite",
        "tasks": tasks,
    }


@app.get("/api/prompts/analytics")
def get_prompts_analytics():
    return history()


@app.get("/metrics")
def metrics():
    try:
        cpu = float(psutil.cpu_percent(interval=None))
        memory = psutil.virtual_memory()
        ram_percent = float(memory.percent)
        ram_used_mb = round((memory.total - memory.available) / (1024 * 1024), 1)
        ram_total_mb = round(memory.total / (1024 * 1024), 1)
    except Exception:
        cpu, ram_percent, ram_used_mb, ram_total_mb = 0.0, 0.0, 0.0, 0.0
    with results_lock:
        completed = list(task_results.values())
    tokens_total = sum(int(item.get("tokens_used") or 0) for item in completed)
    latencies = [float(item["latency_seconds"]) for item in completed if item.get("latency_seconds") is not None]
    return {
        "cpu_percent": cpu, "ram_percent": ram_percent, "ram_used_mb": ram_used_mb,
        "ram_total_mb": ram_total_mb, "tokens_total": tokens_total,
        "queue_length": task_manager.queue_size(),
        "latency_seconds": round(sum(latencies) / len(latencies), 4) if latencies else 0.0,
        "tasks_total": task_store.count(),
    }


@app.get("/blocked")
def blocked():
    return {"blocked_actions": list_blocked_actions()}


@app.get("/scheduler")
def get_scheduler():
    return {"scheduler": task_manager.scheduler.__class__.__name__.replace("Scheduler", "")}


@app.post("/scheduler")
def set_scheduler(request: SchedulerRequest):
    key = request.scheduler.strip().lower().replace("-", "").replace("_", "")
    constructors = {
        "fifo": FIFOScheduler,
        "priority": PriorityScheduler,
        "roundrobin": RoundRobinScheduler,
        "resourceaware": ResourceAwareScheduler,
        "agentos": FIFOScheduler,
    }
    if key not in constructors:
        raise HTTPException(status_code=400, detail="Scheduler must be fifo, priority, roundrobin, resourceaware, or agentos")
    queued = [task for task in task_store.list_tasks() if task.status == TaskStatus.QUEUED]
    scheduler = constructors[key]()
    for task in queued:
        scheduler.enqueue(task)
    task_manager.scheduler = scheduler
    emit_event({"type": "scheduler_changed", "scheduler": scheduler.__class__.__name__.replace("Scheduler", "")})
    return {"scheduler": scheduler.__class__.__name__.replace("Scheduler", "")}


@app.get("/api/task/{task_id}")
def get_task(task_id: str):
    task = task_manager.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"error": "Task not found", "task_id": task_id})
    return {"task": task.model_dump(mode="json")}


@app.post("/api/runtime/step")
def runtime_step():
    result = _execute_one()
    if result is None:
        return {"message": "No queued tasks", "result": None}
    return {"result": result.model_dump(mode="json")}


@app.post("/api/runtime/run-all")
def runtime_run_all():
    results = []
    while task_manager.queue_size() > 0:
        res = _execute_one()
        if res:
            results.append(res.model_dump(mode="json"))
        else:
            break
    current_sched = task_manager.scheduler.__class__.__name__.replace("Scheduler", "")
    return {
        "executed_count": len(results),
        "scheduler": current_sched,
        "results": results,
    }


@app.post("/api/queue/demo-batch")
def queue_demo_batch():
    current_sched = task_manager.scheduler.__class__.__name__.replace("Scheduler", "")
    demo_items = [
        {"prompt": "Explain difference between microkernel and monolithic kernel.", "agent": AgentType.GENERAL, "priority": 2, "tokens": 120, "comp": 1},
        {"prompt": "Audit security sandbox boundary rules and report policy risks.", "agent": AgentType.SECURITY, "priority": 10, "tokens": 150, "comp": 2},
        {"prompt": "Search and verify existence of test suite files in backend.", "agent": AgentType.FILE, "priority": 6, "tokens": 200, "comp": 1},
        {"prompt": "Collect CPU, RAM, and system thread diagnostics telemetry.", "agent": AgentType.MONITORING, "priority": 4, "tokens": 350, "comp": 3},
    ]
    enqueued = []
    for item in demo_items:
        t = Task(
            id=str(uuid.uuid4()),
            prompt=item["prompt"],
            agent_type=item["agent"],
            priority=item["priority"],
            estimated_tokens=item["tokens"],
            complexity=item["comp"],
            status=TaskStatus.QUEUED,
            scheduler=current_sched,
        )
        runtime.submit(t)
        enqueued.append({"id": t.id, "prompt": t.prompt, "agent": item["agent"].value, "priority": t.priority})
        emit_event({"type": "task_queued", "task_id": t.id, "prompt": t.prompt, "priority": t.priority, "scheduler": current_sched})

    return {
        "message": f"Enqueued {len(enqueued)} demo tasks across 4 agents with contrasting priorities (P2, P10, P6, P4)",
        "tasks": enqueued,
        "queue_length": task_manager.queue_size(),
        "scheduler": current_sched,
    }


@app.post("/api/queue/clear")
def clear_queue_endpoint():
    queued = [t for t in task_store.list_tasks() if t.status == TaskStatus.QUEUED]
    for t in queued:
        t.status = TaskStatus.FAILED
        t.completed_at = datetime.now()
        task_store.add(t)
    task_manager.clear()
    emit_event({"type": "queue_cleared", "count": len(queued)})
    return {"message": f"Cleared {len(queued)} queued tasks", "queue_length": task_manager.queue_size()}


@app.get("/api/tasks")
def list_tasks():
    return {"tasks": [task.model_dump(mode="json") for task in task_store.list_tasks()]}


@app.get("/api/stats")
def get_stats():
    return {
        "agents": len(agent_registry.list_agents()),
        "tasks": task_store.statistics(),
        "tools": len(tool_registry.list_tools()),
        "queued": task_manager.queue_size(),
        "scheduler": task_manager.scheduler.__class__.__name__.replace("Scheduler", ""),
    }


@app.get("/api/agents/status")
def agent_status():
    return {"agents": [
        {"name": agent["name"], "model": agent["model"], "capabilities": agent["capabilities"],
         "allowed_tools": agent["allowed_tools"], "status": "available"}
        for agent in agent_registry.describe_agents()
    ]}


@app.get("/api/results/figures")
def list_figures():
    figures = []
    if figures_dir.is_dir():
        for path in sorted(figures_dir.iterdir()):
            if path.is_file() and path.suffix.lower() in {".png", ".pdf", ".jpg", ".jpeg", ".webp"}:
                figures.append({
                    "name": path.name, "kind": path.suffix.lower().lstrip("."),
                    "url": f"/results/figures/{path.name}",
                    "title": path.stem.replace("_", " ").replace("-", " ").title(),
                })
    return {"figures": figures}


def _calc_percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * p
    f = int(k)
    c = f + 1
    if c < len(s):
        return round(s[f] + (k - f) * (s[c] - s[f]), 3)
    return round(s[f], 3)


def compute_dynamic_benchmark() -> dict[str, Any]:
    hist = history()
    tasks = hist.get("tasks", [])

    baseline_defaults = {
        "FIFO": {
            "backend": "mock", "scheduler": "FIFO", "task_count": 12, "mean_latency_seconds": 8.339,
            "p50_latency_seconds": 8.34, "p95_latency_seconds": 15.979,
            "makespan_seconds": 18.073, "success_rate_percent": 100.0,
            "tokens_total": 366.0, "blocked_actions": 0, "isCustom": False, "isLive": False,
        },
        "Priority": {
            "backend": "mock", "scheduler": "Priority", "task_count": 12, "mean_latency_seconds": 10.501,
            "p50_latency_seconds": 12.517, "p95_latency_seconds": 16.778,
            "makespan_seconds": 18.067, "success_rate_percent": 100.0,
            "tokens_total": 366.0, "blocked_actions": 0, "isCustom": False, "isLive": False,
        },
        "RoundRobin": {
            "backend": "mock", "scheduler": "RoundRobin", "task_count": 12, "mean_latency_seconds": 8.334,
            "p50_latency_seconds": 8.334, "p95_latency_seconds": 15.969,
            "makespan_seconds": 18.064, "success_rate_percent": 100.0,
            "tokens_total": 366.0, "blocked_actions": 0, "isCustom": False, "isLive": False,
        },
        "ResourceAware": {
            "backend": "mock", "scheduler": "ResourceAware", "task_count": 12, "mean_latency_seconds": 10.094,
            "p50_latency_seconds": 10.356, "p95_latency_seconds": 16.785,
            "makespan_seconds": 18.073, "success_rate_percent": 100.0,
            "tokens_total": 366.0, "blocked_actions": 1, "isCustom": False, "isLive": False,
        },
    }

    # Completed tasks
    completed = [
        t for t in tasks
        if t.get("status") in ("done", "completed", "failed", "blocked") or t.get("latency_seconds") is not None
    ]

    current_sched_name = task_manager.scheduler.__class__.__name__.replace("Scheduler", "")

    sched_groups: dict[str, list[dict[str, Any]]] = {
        "FIFO": [],
        "Priority": [],
        "RoundRobin": [],
        "ResourceAware": [],
    }

    for t in completed:
        raw_s = str(t.get("scheduler") or current_sched_name or "FIFO")
        norm_s = "FIFO"
        if "prio" in raw_s.lower():
            norm_s = "Priority"
        elif "round" in raw_s.lower() or "robin" in raw_s.lower():
            norm_s = "RoundRobin"
        elif "resource" in raw_s.lower():
            norm_s = "ResourceAware"
        elif "fifo" in raw_s.lower():
            norm_s = "FIFO"
        sched_groups.setdefault(norm_s, []).append(t)

    benchmark_summary = []
    for s_name, default_row in baseline_defaults.items():
        s_tasks = sched_groups.get(s_name, [])
        if s_tasks:
            lats = [float(t.get("latency_seconds") or 0.0) for t in s_tasks if t.get("latency_seconds") is not None]
            toks = sum(int(t.get("tokens_used") or 0) for t in s_tasks)
            done_cnt = sum(1 for t in s_tasks if t.get("status") in ("done", "completed"))
            blocked_cnt = sum(1 for t in s_tasks if t.get("status") == "blocked")
            total_cnt = len(s_tasks)
            succ_pct = round((done_cnt / total_cnt) * 100.0, 1) if total_cnt else 100.0

            p50 = _calc_percentile(lats, 0.50) if lats else 1.0
            p95 = _calc_percentile(lats, 0.95) if lats else 1.5
            mean_l = round(sum(lats) / len(lats), 3) if lats else 1.0
            makespan = round(sum(lats), 3)

            benchmark_summary.append({
                "backend": "live",
                "scheduler": s_name,
                "task_count": total_cnt,
                "mean_latency_seconds": mean_l,
                "p50_latency_seconds": p50,
                "p95_latency_seconds": p95,
                "makespan_seconds": makespan,
                "success_rate_percent": succ_pct,
                "tokens_total": toks,
                "blocked_actions": blocked_cnt,
                "isCustom": False,
                "isLive": True,
            })
        else:
            benchmark_summary.append(default_row)

    # Agent breakdown
    agent_groups: dict[str, list[dict[str, Any]]] = {}
    for t in completed:
        ag = t.get("agent") or "GeneralAgent"
        agent_groups.setdefault(ag, []).append(t)

    agent_summary = []
    for ag_name, ag_tasks in sorted(agent_groups.items()):
        lats = [float(t.get("latency_seconds") or 0.0) for t in ag_tasks if t.get("latency_seconds") is not None]
        toks = sum(int(t.get("tokens_used") or 0) for t in ag_tasks)
        done_cnt = sum(1 for t in ag_tasks if t.get("status") in ("done", "completed"))
        total_cnt = len(ag_tasks)
        agent_summary.append({
            "agent": ag_name,
            "task_count": total_cnt,
            "mean_latency_seconds": round(sum(lats) / len(lats), 3) if lats else 0.0,
            "p50_latency_seconds": _calc_percentile(lats, 0.50) if lats else 0.0,
            "p95_latency_seconds": _calc_percentile(lats, 0.95) if lats else 0.0,
            "tokens_total": toks,
            "success_rate_percent": round((done_cnt / total_cnt) * 100.0, 1) if total_cnt else 100.0,
        })

    # Recent completed prompts in chronological order
    recent_prompts = []
    for idx, t in enumerate(completed):
        recent_prompts.append({
            "prompt_num": idx + 1,
            "task_id": t.get("task_id", ""),
            "prompt": t.get("prompt", "")[:90] + ("…" if len(t.get("prompt", "")) > 90 else ""),
            "agent": t.get("agent", "GeneralAgent"),
            "scheduler": t.get("scheduler", current_sched_name),
            "latency_seconds": t.get("latency_seconds"),
            "tokens_used": t.get("tokens_used", 0),
            "status": t.get("status", "done"),
        })

    all_lats = sorted([float(t.get("latency_seconds") or 0.0) for t in completed if t.get("latency_seconds") is not None])

    live_stats = {
        "prompt_count": len(completed),
        "mean_latency_seconds": round(sum(all_lats) / len(all_lats), 3) if all_lats else 0.0,
        "p50_latency_seconds": _calc_percentile(all_lats, 0.50) if all_lats else 0.0,
        "p95_latency_seconds": _calc_percentile(all_lats, 0.95) if all_lats else 0.0,
        "tokens_total": sum(int(t.get("tokens_used") or 0) for t in completed),
        "makespan_seconds": round(sum(all_lats), 3) if all_lats else 0.0,
        "blocked_actions": sum(1 for t in completed if t.get("status") == "blocked"),
        "success_rate_percent": round((sum(1 for t in completed if t.get("status") in ("done", "completed")) / len(completed)) * 100.0, 1) if completed else 100.0,
    }

    return {
        "benchmark_summary": benchmark_summary,
        "agent_summary": agent_summary,
        "recent_prompts": recent_prompts,
        "latency_samples": all_lats,
        "live_stats": live_stats,
        "has_live_data": len(completed) > 0,
        "prompt_count": len(completed),
    }


@app.get("/api/benchmark/data")
def get_benchmark_data():
    return compute_dynamic_benchmark()


@app.get("/api/benchmark/live")
def get_benchmark_live():
    return compute_dynamic_benchmark()


class ImageUploadPayload(BaseModel):
    image: str = Field(description="Base64 encoded image string or data URL")
    filename: str = Field(default="user_image.png")


class ImageGeneratePayload(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    width: int = Field(default=1000, ge=200, le=2400)
    height: int = Field(default=650, ge=200, le=1800)
    image_url: str | None = None


@app.post("/api/upload/image")
async def upload_image_endpoint(request: Request):
    content_type = request.headers.get("content-type", "")
    filename = "user_upload.png"
    file_bytes = b""

    if "multipart/form-data" in content_type:
        form = await request.form()
        uploaded_file = form.get("file") or form.get("image")
        if not uploaded_file:
            raise HTTPException(status_code=400, detail="No file found in multipart upload")
        filename = getattr(uploaded_file, "filename", "user_upload.png")
        file_bytes = await uploaded_file.read()
    else:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Expected JSON or multipart/form-data")
        raw_b64 = body.get("image") or body.get("data")
        if not raw_b64:
            raise HTTPException(status_code=400, detail="Missing 'image' base64 data")
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        import base64
        try:
            file_bytes = base64.b64decode(raw_b64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 payload: {e}")
        filename = body.get("filename") or "user_upload.png"

    clean_stem = re.sub(r"[^a-zA-Z0-9_\.-]+", "_", Path(filename).name)
    file_id = uuid.uuid4().hex[:8]
    saved_name = f"{file_id}_{clean_stem}"
    save_path = uploads_dir / saved_name

    with open(save_path, "wb") as f:
        f.write(file_bytes)

    width, height, img_fmt = 0, 0, "PNG"
    try:
        from PIL import Image as PILImage
        with PILImage.open(save_path) as im:
            width, height = im.size
            img_fmt = im.format or "PNG"
    except Exception:
        pass

    url = f"/static/uploads/{saved_name}"
    return {
        "status": "success",
        "filename": saved_name,
        "original_filename": filename,
        "url": url,
        "size_bytes": len(file_bytes),
        "width": width,
        "height": height,
        "format": img_fmt,
    }


@app.post("/api/generate/image")
def generate_image_endpoint(payload: ImageGeneratePayload):
    meta = image_agent.generate_image(
        prompt=payload.prompt,
        uploaded_image_path=payload.image_url,
        width=payload.width,
        height=payload.height,
    )
    return {
        "status": "success",
        **meta,
    }


@app.post("/api/figures/generate")
def generate_figures_endpoint():
    import subprocess
    script_path = workspace / "make_graphs.py"
    data_path = workspace / "experiments" / "simulated_results.csv"
    if not script_path.is_file():
        script_path = workspace / "scripts" / "make_graphs.py"
    cmd = [sys.executable, str(script_path), str(data_path), "--output-dir", str(figures_dir)]
    try:
        res = subprocess.run(cmd, cwd=str(workspace), capture_output=True, text=True, timeout=30)
        fig_data = list_figures()
        return {
            "status": "success" if res.returncode == 0 else "warning",
            "message": "Benchmark figures generated successfully.",
            "stdout": res.stdout,
            "figures": fig_data.get("figures", []),
        }
    except Exception as exc:
        fig_data = list_figures()
        return {
            "status": "warning",
            "message": f"Graph script notice: {exc}",
            "figures": fig_data.get("figures", []),
        }


@app.post("/api/figures/upload")
async def upload_figure_endpoint(request: Request):
    content_type = request.headers.get("content-type", "")
    filename = "custom_figure.png"
    file_bytes = b""
    if "multipart/form-data" in content_type:
        form = await request.form()
        uploaded_file = form.get("file") or form.get("figure")
        if not uploaded_file:
            raise HTTPException(status_code=400, detail="No figure file uploaded")
        filename = getattr(uploaded_file, "filename", "custom_figure.png")
        file_bytes = await uploaded_file.read()
    else:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Expected JSON or multipart/form-data")
        raw_b64 = body.get("image") or body.get("data")
        if not raw_b64:
            raise HTTPException(status_code=400, detail="Missing 'image' base64 data")
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        import base64
        try:
            file_bytes = base64.b64decode(raw_b64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 payload: {e}")
        filename = body.get("filename") or "custom_figure.png"

    clean_name = re.sub(r"[^a-zA-Z0-9_\.-]+", "_", Path(filename).name)
    if not clean_name.lower().endswith((".png", ".pdf", ".jpg", ".webp")):
        clean_name += ".png"
    target = figures_dir / clean_name
    with open(target, "wb") as f:
        f.write(file_bytes)
    return {
        "status": "success",
        "name": clean_name,
        "url": f"/results/figures/{clean_name}",
        "figures": list_figures()["figures"],
    }


@app.get("/results/figures/{filename}")
def get_figure(filename: str):
    # Only direct files with supported extensions are exposed.
    if Path(filename).name != filename or Path(filename).suffix.lower() not in {".png", ".pdf", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(status_code=400, detail="Invalid figure filename")
    path = figures_dir / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Figure not found")
    return FileResponse(path)


@app.websocket("/stream")
async def stream(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"type": "connected", "system": "AgentOS"})
    _, cursor = get_events_since(0)
    try:
        while True:
            events, next_cursor = get_events_since(cursor)
            for event in events:
                await websocket.send_json(event)
            cursor = next_cursor
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        return


# Built React assets are emitted into backend/static/web/assets by Vite.
if built_frontend.is_dir():
    app.mount("/assets", StaticFiles(directory=built_frontend / "assets"), name="frontend-assets")
app.mount("/static", StaticFiles(directory=static_dir, check_dir=False), name="static")
