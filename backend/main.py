from pathlib import Path
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

from tools.registry import ToolRegistry
from tools.filesystem import FileSystemTool
from tools.system_info import SystemInfoTool
from agents.general_agent import GeneralAgent
from agents.file_agent import FileAgent
from agents.security_agent import SecurityAgent
from agents.agent_registry import AgentRegistry
from agents.task_router import TaskRouter
from agents.agent_manager import AgentManager
from scheduler.task_store import TaskStore
from scheduler.task_manager import TaskManager
from scheduler.factory import create_scheduler, SCHEDULER_NAMES
from scheduler.runtime import AgentRuntime
from monitor.system_monitor import get_system_state
from scheduler.task import AgentType, Task, TaskStatus
from results_csv import append_result
from policy.engine import configure_policy_engine, get_enforcement_enabled, set_enforcement_enabled


app = FastAPI(
    title="AgentOS",
    description="AI-native operating environment prototype",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

workspace = Path(__file__).resolve().parents[1]

tool_registry = ToolRegistry()
tool_registry.register("filesystem", FileSystemTool(workspace))
tool_registry.register("system_info", SystemInfoTool())

general_agent = GeneralAgent(tool_registry=tool_registry, model="qwen2.5:1.5b")
file_agent = FileAgent(tool_registry=tool_registry, model="qwen2.5:1.5b")
security_agent = SecurityAgent(tool_registry=tool_registry, model="qwen2.5:1.5b")

agent_registry = AgentRegistry()
agent_registry.register("GeneralAgent", general_agent)
agent_registry.register("FileAgent", file_agent)
agent_registry.register("SecurityAgent", security_agent)

task_router = TaskRouter()
agent_manager = AgentManager(agent_registry, task_router)
task_store = TaskStore()
scheduler = create_scheduler(system_state_provider=get_system_state)
task_manager = TaskManager(scheduler, task_store)
results_path = Path(__file__).resolve().parents[1] / "experiments" / "results.csv"
metrics_path = Path(__file__).resolve().parents[1] / "experiments" / "metrics.csv"
policy_engine = configure_policy_engine(
    registry=tool_registry,
    metrics_path=metrics_path,
    enforcement=get_enforcement_enabled(),
)
runtime = AgentRuntime(task_manager, agent_manager, results_path=results_path, monitor=get_system_state)


class TaskRequest(BaseModel):
    prompt: str = Field(min_length=1)
    agent_type: AgentType | None = None
    priority: int = Field(default=5, ge=1, le=10)
    estimated_tokens: int = Field(default=256, ge=1)
    complexity: int = Field(default=1, ge=1, le=5)
    risk_level: int = Field(default=1, ge=1, le=5)
    deadline_s: float | None = Field(default=None, gt=0)
    required_capabilities: list[str] = Field(default_factory=list)


def select_agent(agent_type: AgentType):
    return agent_manager.get_by_type(agent_type)


def route_task(prompt: str):
    return agent_manager.select_for_prompt(prompt)




@app.get("/")
def root():
    return {"system": "AgentOS", "status": "running", "version": app.version}


@app.get("/health")
def health():
    return {"status": "healthy", "system": "AgentOS"}


@app.get("/api/health")
def api_health():
    return {"status": "healthy", "system": "AgentOS"}


@app.get("/api/status")
def status():
    return {
        "system": "AgentOS",
        "status": "running",
        "llm_backend": general_agent.llm.__class__.__name__.replace("LLMClient", "").lower(),
        "model": general_agent.model,
        "agents": len(agent_registry.list_agents()),
        "tasks": task_store.count(),
        "queued": task_manager.queue_size(),
        "scheduler": getattr(task_manager.scheduler, "name", task_manager.scheduler.__class__.__name__),
        "scheduler_options": list(SCHEDULER_NAMES),
        "concurrency_limit": runtime.concurrency_limit,
        "model_tier": runtime.model_tier,
        "policy_enforcement": policy_engine.enforcement,
    }


class EnforcementRequest(BaseModel):
    enabled: bool


@app.get("/api/policy")
def policy_status():
    return {"enforcement": policy_engine.enforcement, "mode": "enforced" if policy_engine.enforcement else "ablation"}


@app.post("/api/policy/enforcement")
def set_policy_enforcement(request: EnforcementRequest):
    set_enforcement_enabled(request.enabled)
    policy_engine.set_enforcement(request.enabled)
    return {"enforcement": policy_engine.enforcement, "mode": "enforced" if policy_engine.enforcement else "ablation"}


@app.post("/api/route")
def route_request(request: TaskRequest):
    agent, capability = route_task(request.prompt)
    return {"agent": agent.name, "capability": capability, "model": agent.model}


@app.get("/api/tools")
def list_tools():
    return {"tools": tool_registry.list_tools()}


@app.get("/api/agents")
def list_agents():
    return {"agents": agent_registry.list_agents()}


@app.get("/api/agents/details")
def list_agent_details():
    return {"agents": agent_registry.describe_agents()}


@app.post("/api/task")
def create_task(request: TaskRequest):
    selected_agent, capability = agent_manager.select_for_task(
        prompt=request.prompt,
        agent_type=request.agent_type,
    )

    task = Task(
        id=str(uuid.uuid4()),
        prompt=request.prompt,
        agent_type=agent_manager.agent_type_for(selected_agent),
        priority=request.priority,
        estimated_tokens=request.estimated_tokens,
        complexity=request.complexity,
        risk_level=request.risk_level,
        deadline_s=request.deadline_s,
        required_capabilities=request.required_capabilities,
        status=TaskStatus.QUEUED,
    )

    runtime.submit(task)
    result = runtime.run_next()
    return {
        "task": task.model_dump(mode="json"),
        "agent": result.agent if result else selected_agent.name,
        "capability": capability,
        "model": result.model if result else selected_agent.model,
        "response": result.response if result else "",
        "latency_seconds": result.latency_seconds if result else None,
        "tokens_used": result.tokens_used if result else 0,
        "llm_latency_seconds": result.llm_latency_seconds if result else 0.0,
        "llm_backend": result.llm_backend if result else "unknown",
        "status": result.status.value if result else task.status.value,
        "error": result.error if result else None,
    }


@app.get("/api/task/{task_id}")
def get_task(task_id: str):
    task = task_manager.get(task_id)
    if task is None:
        return {"error": "Task not found", "task_id": task_id}
    return {"task": task.model_dump(mode="json")}


@app.post("/api/runtime/run")
def runtime_run():
    results = runtime.run_pending()
    return {"results": [result.model_dump(mode="json") for result in results]}


@app.post("/api/runtime/step")
def runtime_step():
    result = runtime.run_next()
    if result is None:
        return {"message": "No queued tasks", "result": None}
    return {"result": result.model_dump(mode="json")}


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
    }


@app.get("/api/agents/status")
def agent_status():
    return {
        "agents": [
            {
                "name": agent["name"],
                "model": agent["model"],
                "capabilities": agent["capabilities"],
                "allowed_tools": agent["allowed_tools"],
                "status": "available",
            }
            for agent in agent_registry.describe_agents()
        ]
    }
