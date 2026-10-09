# AgentOS — Day 7 Code Freeze (v2-final)

AgentOS is an AI-native runtime prototype built as an application/system layer on top of an existing operating system. It is **not a custom kernel or a finished bootable OS**. The prototype demonstrates task intake, scheduling, multi-agent dispatch, policy-gated tool use, local/mock LLM backends, bounded memory, monitoring, and reproducible validation.

## Current capabilities

- FastAPI task API and task lifecycle (`queued`, `running`, `done`, `failed`, `blocked`).
- GeneralAgent, FileAgent, and SecurityAgent behind an Agent Manager/router.
- FIFO, round-robin, priority, and resource-aware scheduler implementations.
- Ollama-backed local inference or deterministic MockLLM mode for offline testing.
- Policy boundary for tool calls, with policy events and untrusted tool output handling.
- Runtime/system metrics, bounded task history and memory, CSV experiment results.
- Automated tests and Day 6 stability/soak validation scripts.

## Repository map

```text
AgentOS/
├── backend/
│   ├── agents/       # Agent implementations, registry, routing
│   ├── llm/          # Ollama and MockLLM clients
│   ├── memory/       # Bounded runtime memory
│   ├── monitor/      # CPU/memory/system state
│   ├── policy/       # Tool policy, untrusted-data tagging, policy metrics
│   ├── scheduler/    # Task store/manager, runtime, scheduler strategies
│   ├── tests/        # Day 1–Day 6 automated tests
│   ├── tools/        # Registered tool implementations and interfaces
│   ├── main.py       # FastAPI app and endpoints
│   ├── schemas.py    # Shared request/result contracts
│   └── results_csv.py
├── docs/             # Implementation, evaluation, stability, paper setup
├── experiments/      # CSV outputs and validation logs
├── frontend/         # React/Vite dashboard
├── scripts/          # Setup, smoke tests, workload and soak validation
├── shell/            # CLI entry point
├── deploy/           # Example systemd service
├── requirements.txt
├── .env.example
└── V1_FREEZE.md
```

## Prerequisites

- Git
- Python 3.13 or 3.14; use a version supported by the pinned dependencies on your OS
- Optional: Ollama plus `qwen2.5:1.5b` for real local inference
- Optional frontend: Node.js/npm

The MockLLM path does not need Ollama or internet access at runtime once Python dependencies are installed. The project is currently developed/tested as a Windows-compatible Python prototype; the longer-term OS target is Linux/Debian/Ubuntu.

## Install on Windows PowerShell

Run from the repository root (the folder containing `requirements.txt`):

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

If `.env` already exists, do not overwrite your local configuration. The virtual environment is intentionally not committed; recreate it on each machine. You can also run `powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1` to install dependencies and create `.env` only when missing.

For an offline/mock setup, edit `.env` and set:

```text
AGENTOS_LLM_BACKEND=mock
AGENTOS_SCHEDULER=fifo
AGENTOS_POLICY_ENFORCEMENT=on
AGENTOS_SEED=42
```

For local inference, install Ollama separately, pull the configured model with `ollama pull qwen2.5:1.5b`, and use `AGENTOS_LLM_BACKEND=ollama`. Python package installation does not install the model weights.

## Test and run the backend

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Start the API in a separate PowerShell terminal:

```powershell
Set-Location .\backend
..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Open `http://127.0.0.1:8000/docs`. Useful endpoints include `GET /health`, `GET /api/status`, `GET /api/agents`, `GET /api/tools`, `POST /api/task`, `GET /api/tasks`, `GET /api/stats`, `GET /api/policy`, and `GET /api/memory`.

Example `POST /api/task` request body in Swagger UI:

```json
{
  "prompt": "Explain what the AgentOS runtime does",
  "agent_type": "GeneralAgent",
  "priority": 5,
  "estimated_tokens": 128,
  "complexity": 1,
  "risk_level": 1,
  "required_capabilities": []
}
```

If the API rejects an `agent_type` value, use the enum options shown by `/docs` for the current build. The API executes a task and returns the result, status, selected agent, backend, and latency/token fields.

## Reproduce the stability and workload experiments

The canonical Windows validation script creates deterministic environment variables and runs the project validation phases:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_day6_stability.ps1
```

It expects `.venv` and dependencies to be installed first. It sets the reproducibility seed to `42`, runs the Day 5 MockLLM workload, failure-path checks, and the 1,000-task Day 6 soak test. Outputs are written under `experiments/`. Use a clean working tree or copy the baseline CSVs before a run if you need to preserve prior measurements; scripts may append/update experiment output files.

To run the MockLLM workload alone:

```powershell
$env:AGENTOS_LLM_BACKEND = "mock"
.\.venv\Scripts\python.exe .\scripts\day5_mock_workload.py
```

To run the API smoke test:

```powershell
$env:AGENTOS_LLM_BACKEND = "mock"
.\.venv\Scripts\python.exe .\scripts\smoke_test.py
```

For a meaningful experiment report, record OS/Python/dependency versions, scheduler, concurrency limit, model/backend, policy setting, seed, workload size, completion/failure counts, latency, memory and the exact CSV file used. Repeat runs where practical; do not generalize single-run memory readings as universal bounds.

## Experiment design and interpretation

The code supports comparison of scheduler strategies (`fifo`, `round_robin`, `priority`, `resource_aware`) and policy enforcement on/off. Keep workload prompts and configuration constant when comparing a single factor. Report completion rate, failure/blocked rate, end-to-end latency (mean and p95 if calculated), LLM latency, token counts, memory observations, and policy allow/deny outcomes. Separate MockLLM measurements from Ollama-backed measurements: MockLLM is useful for controlled orchestration tests but is not evidence of language-model quality or real inference speed.

The archived Day 6 validation record reports 58 passing tests, five completed MockLLM workload tasks, passing checks for malformed input/model timeout/denied action/Ollama unavailable, and a 1,000-task soak with bounded history and memory. Treat these as recorded validation results from that run, not a guarantee that every clean machine will reproduce identical timings. Re-run the commands above on the target system and preserve the resulting logs/CSV evidence.

## Paper and documentation

- `docs/IMPLEMENTATION.md` — architecture and implementation details.
- `docs/EVALUATION_SETUP.md` — hardware/software, model, workload, scheduler, policy and metric configuration.
- `docs/PAPER_IMPLEMENTATION_AND_EVALUATION.md` — draft-ready Implementation and Evaluation Setup sections, with claims limited to what the prototype actually implements.
- `DAY6_VALIDATION.md` — prior validation record.
- `DAY7_COMPLETION.md` — Day 7 freeze and fresh-clone checklist.

## Limitations

AgentOS is a Python runtime prototype, not a bootable OS image or a new kernel. Tool policy enforcement in this prototype is an application-level boundary and should not be represented as equivalent to kernel-enforced sandboxing. MockLLM results measure orchestration behavior, not model reasoning. A fresh-clone check is not considered complete until installation, tests, API demo, and at least one experiment have been run on the target machine.
