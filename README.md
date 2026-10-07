# AgentOS

AgentOS is an AI-native operating-environment prototype built as a Linux/system layer rather than a custom kernel. Day 1 establishes the contracts and runtime foundation used by the scheduler, agents, policy layer, and monitoring components.

## Day 1 architecture

```text
User / Frontend
      |
      v
 FastAPI API
      |
      v
 Task contract -> TaskExecutor -> Agent
                              |
                              v
                    Common LLM interface
                       /            \
                   Ollama           Mock
                     |                |
              Qwen2.5-1.5B      offline tests
```

The measured local Qwen2.5-1.5B generation rate is **20.32 tokens/sec** on the development machine. The value is stored as `DEFAULT_TPS` in `backend/llm/client.py` and is used by the mock backend as the scheduling estimate.

## Project structure

```text
AgentOS/
├── backend/
│   ├── agents/              # General, File, Security agents
│   ├── llm/                 # Ollama + Mock LLM abstraction
│   ├── scheduler/           # Task contracts, executor, task store
│   ├── tools/               # Tools and Day 1 deny-only boundary
│   ├── tests/               # Day 1 tests
│   ├── main.py              # FastAPI application
│   ├── schemas.py           # Frozen cross-component contracts
│   └── results_csv.py       # Experiment result schema/writer
├── experiments/             # Benchmark output
├── frontend/                # React/Vite dashboard
├── policies/                # Future policy enforcement layer
├── scripts/                 # Setup and runtime scripts
├── .env.example
├── .gitignore
└── requirements.txt
```

## Setup on Windows

From the AgentOS root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks `Activate.ps1`, use the direct `.venv\Scripts\python.exe` commands above; activation is not required.

## Configuration

`.env` controls the LLM backend:

```text
AGENTOS_LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:1.5b
OLLAMA_TIMEOUT=120
```

For a machine without Ollama, use:

```text
AGENTOS_LLM_BACKEND=mock
```

The mock backend never contacts a model service, so tests and offline team development do not require Ollama.

## Run tests

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Day 1 currently has 17 automated tests.

## Run backend

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Useful endpoints:

- `GET /health`
- `GET /api/health`
- `GET /api/status`
- `POST /api/task`
- `GET /api/tasks`
- `GET /api/tools`
- `GET /api/agents`
- `GET /api/stats`

A task response includes `tokens_used`, `llm_latency_seconds`, `llm_backend`, and `latency_seconds`.

## Run frontend

In a second terminal:

```powershell
cd frontend
npm run dev
```

## Team Git convention

`main` is the protected integration branch. Each teammate works on a feature branch, opens a merge request/pull request, and merges only after the tests pass. The Day 1 scheduler/task contract, `schemas.py`, `results_csv.py`, and `tools/interface.py` should be treated as frozen interfaces after team review.

Priority is an integer from 1 to 10, where 10 is urgent. Complexity and risk are integers from 1 to 5. `deadline_s` is measured in seconds from task submission. Teammates without Ollama should use `AGENTOS_LLM_BACKEND=mock`.

## Security boundary

`backend/tools/interface.py` is intentionally deny-only in Day 1. The LLM cannot acquire an OS capability merely by requesting a tool. P3 will connect this interface to the policy enforcement layer and the OS sandbox.


## Day 2 architecture: agents and dispatch

Day 2 adds the agent runtime layer with three specialized agents:

```text
Task
 |
 v
AgentManager
 |
 +--> TaskRouter --> capability classification
 |
 +--> GeneralAgent  --> general reasoning/conversation
 |
 +--> FileAgent     --> workspace file operations/analysis
 |
 +--> SecurityAgent --> security/risk analysis
 |
 v
Shared LLM interface
 |
 +--> Ollama / Qwen2.5-1.5B
 +--> MockLLM
```

`AgentManager` is the single integration point for agent selection. A task can either
specify an explicit `agent_type`, or leave it unset so the router selects an agent
from the task prompt. Explicit selection is useful for controlled experiments;
automatic routing is the normal AI-shell path.

The three agents intentionally share the same `BaseAgent` and LLM interface:

- `GeneralAgent`: general questions, reasoning and explanations.
- `FileAgent`: workspace listing, filename/extension search, content search and file analysis.
- `SecurityAgent`: security, risk and authorization analysis. It does not execute commands.

Day 2 does not implement the final permission sandbox. Tool authority remains
behind the Day 1 deny-only `run_tool(...)` boundary; full policy enforcement is
reserved for the security/policy implementation day.

## Day 2 verification

The test suite verifies agent registration, capability routing, explicit agent
selection, automatic API dispatch and the `/api/route` endpoint.

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

The Day 2 development suite contains 25 passing tests.

## Day 2 — Runtime Core

Day 2 adds the runtime execution contract required by P1:

```text
Task API
   ↓
TaskManager
   ↓
Scheduler (FIFO placeholder)
   ↓
AgentRuntime
   ↓
AgentManager
   ↓
GeneralAgent / FileAgent / SecurityAgent
   ↓
TaskResult
```

Tasks use the lifecycle:

```text
queued → running → done
                 ↘ failed
                 ↘ blocked
```

`backend/scheduler/base.py` defines the `Scheduler` interface. The Day 2 `FIFOScheduler` is intentionally simple so P2 can replace it with Round-Robin, Priority and resource-aware schedulers without modifying `AgentRuntime`.

`backend/scheduler/task_manager.py` owns task creation, queueing, status transitions and task history.

`backend/scheduler/runtime.py` owns the execution loop. It asks the scheduler for the next task, obtains the correct agent from `AgentManager`, runs it and produces the frozen `TaskResult` contract.

### Day 2 verification

```powershell
..\\.venv\\Scripts\\python.exe -m pytest -v
```

The API still provides `POST /api/task` for submit-and-run behavior. For runtime integration testing, `POST /api/runtime/step` executes one queued task, and `GET /api/task/{task_id}` returns the stored task lifecycle state.
