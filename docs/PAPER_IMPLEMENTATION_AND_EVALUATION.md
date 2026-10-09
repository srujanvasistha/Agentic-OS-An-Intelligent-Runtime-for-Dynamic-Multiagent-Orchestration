# Paper Draft: Implementation and Evaluation Setup

> Draft sections for the AgentOS capstone paper. Replace any machine-specific statements with the exact configuration and output captured for the final reported runs. Do not report planned experiments as completed results.

## 3. Implementation

AgentOS is implemented as a modular Python runtime operating above an existing host operating system. The prototype does not implement a kernel, bootloader, or kernel-level sandbox. Its main entry point is a FastAPI service that accepts task requests and returns task execution results. The request contract includes a prompt, optional agent type, priority, estimated token count, complexity, risk level, optional deadline, and required capabilities.

The runtime separates task storage and lifecycle management from scheduling and execution. Tasks move through queued, running, done, failed, or blocked states. A scheduler interface permits alternative scheduling strategies to be selected without changing the agent execution contract. The available implementations are FIFO, round-robin, priority-based, and resource-aware scheduling. The resource-aware strategy receives host state from a system monitor and uses task estimates and resource-pressure signals to inform scheduling decisions. Runtime concurrency and model tier are configurable for controlled experiments.

Agent dispatch is mediated by an Agent Manager and registry. The prototype provides GeneralAgent, FileAgent, and SecurityAgent. GeneralAgent handles general requests, FileAgent supports workspace-oriented file tasks, and SecurityAgent provides security/risk analysis. The agents share a common LLM client interface, with an Ollama backend for local inference and a MockLLM backend for deterministic/offline validation. The configured primary local model is Qwen2.5 1.5B; model weights must be installed separately through Ollama.

OS-facing tool requests pass through a policy engine and registered tool boundary. Policy enforcement can be enabled or disabled for an explicit ablation, and policy decisions/runtime events are recorded as metrics. Tool results and externally sourced file/log content are marked as untrusted before being passed into model context. This is application-level capability mediation; the current prototype does not claim isolation equivalent to a kernel sandbox. Runtime memory is bounded, and the monitoring component exposes system resource state used by the scheduler.

Experiment results are serialized to CSV using a shared result schema. The repository includes automated tests, deterministic MockLLM workloads, failure-path checks, a smoke test, and a 1,000-task stability/soak validation runner. A reproducibility seed is configured for the validation scripts. Because operating-system scheduling, package versions, and model inference may vary, exact latency and memory values should be tied to the environment and run identifier rather than treated as universal constants.

## 4. Evaluation Setup

### 4.1 Hardware and software environment

The recorded development configuration is a desktop with an Intel Core i7-12700F CPU, 16 GB RAM, and NVIDIA Quadro K620 GPU with 2 GB VRAM. The prototype uses CPU inference as the conservative default for this hardware class. The intended future deployment target is a Linux/Debian/Ubuntu environment; the current capstone implementation is a Python prototype that is also developed and validated on Windows. Record the exact OS build, Python version, package versions, and Ollama version for every final experiment. The repository's pinned direct dependencies are listed in `requirements.txt`.

### 4.2 Models and execution modes

Two execution modes are distinguished. In offline controlled tests, MockLLM provides a common-interface substitute that avoids model-service availability and generation variability. In local inference tests, the Ollama backend invokes the locally installed Qwen2.5 1.5B model; the small model tier is configurable where supported by the runtime. Results from these modes are reported separately. MockLLM measurements evaluate orchestration/runtime behavior and are not interpreted as model-quality or real inference-throughput measurements.

### 4.3 Workloads and reproducibility

The repository provides a deterministic five-task MockLLM workload and a 1,000-task Day 6 soak/stability test. The validation script sets the seed to 42 and runs the controlled workload and failure-path checks before the soak phase. The five-task workload covers orchestration components including scheduler behavior, policy, monitoring, memory, and request execution. For each run, record the workload definition, seed, scheduler, concurrency limit, model tier, LLM backend/model, policy setting, Python and OS versions, and output CSV path. A clean-clone validation should install dependencies from `requirements.txt`, execute the automated test suite, start the API in MockLLM mode, submit one request through `/docs`, and run at least one workload or stability experiment.

### 4.4 Configurations and comparisons

The runtime exposes four scheduler choices: FIFO, round-robin, priority, and resource-aware. Policy enforcement is enabled by default and can be switched off for a policy ablation. Concurrency is configurable (the documented baseline is one worker), and the model tier is configurable. For a scheduler comparison, hold workload and policy/backend settings constant and vary only the scheduler. For a policy ablation, hold the workload and scheduler constant and compare enforcement enabled versus disabled. Do not combine changes to scheduler, concurrency, backend, and policy in a single comparison if the goal is to attribute effects to one factor.

### 4.5 Metrics

The runtime result schema records task/agent information, status, workload attributes, token count, LLM latency, end-to-end latency, and backend. Policy/runtime metrics record allowed or blocked tool calls and runtime failure events. The evaluation should report at least task completion rate, failure and blocked-task counts, end-to-end latency, LLM latency where applicable, token count, memory observations, and policy decision outcomes. Report mean and p95 latency when computed from sufficient individual task samples. State the number of repetitions and show variability where feasible. For soak tests, include completed/failed task counts and before/after memory observations, while acknowledging that a single process memory sample cannot establish the absence of memory leaks.

### 4.6 Reproduction procedure

From a fresh clone, create a virtual environment and install `requirements.txt`, configure `.env` to use MockLLM, run `python -m pytest -v`, and execute `scripts/run_day6_stability.ps1` on Windows. Start the API using Uvicorn and exercise `POST /api/task` through the generated OpenAPI interface at `/docs`. Save test output and generated CSVs alongside the run configuration. For local-model trials, separately install Ollama and pull the exact model identifier before switching the backend to Ollama. A successful prior run is a baseline reference; the fresh-clone run must be performed and recorded on the target machine before claiming clean-install reproducibility.

### 4.7 Threats to validity

MockLLM reduces inference variability but cannot represent real LLM latency or output quality. Local-model measurements are affected by model version, quantization, hardware load, and Ollama settings. Results from one desktop and a small controlled workload may not generalize to other systems or production workloads. Resource-aware decisions depend on the quality and timing of monitoring signals. Application-level policy checks do not provide kernel-level isolation. These constraints should be stated explicitly when interpreting results.
