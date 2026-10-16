# AgentOS

AgentOS is an AI-native operating-environment prototype built as a Linux/system layer rather than a custom kernel. Day 1 establishes the contracts and runtime foundation used by the scheduler, agents, policy layer, and monitoring components.




## Day 5: Real Qwen vs mock benchmark

A repeatable 12-task comparison harness is available in `experiments/run_day5_real_qwen.py`. It runs FIFO, RoundRobin, Priority, and ResourceAware sequentially on the same workload using Ollama Qwen2.5-1.5B and the mock timing backend, logs per-task timing/token/deadline/CPU/RAM samples, and compares p95 latency and makespan rankings.

See [`experiments/DAY5_README.md`](experiments/DAY5_README.md) for prerequisites and commands. Run `make day5` for the full benchmark (Ollama and `qwen2.5:1.5b` required), or `make day5-mock` for an offline mock-only smoke run. Real benchmark results are generated locally and are not claimed until the real run succeeds.


## Day 7: Scheduler design and evaluation paper sections

The CSV-grounded draft sections, derived metric tables, and figures are in [`paper/`](paper/README.md). The evaluation separates the seeded simulation results from the Day 5 mock-only benchmark; no real-Qwen results are claimed unless a successful real run is added to the CSVs.


## Day 4–6: web shell, benchmark graphs, and packaging

The Day 4–6 implementation notes and exact run commands are in [`DAY4_DAY6.md`](DAY4_DAY6.md).

### Start the local web demo

On Windows PowerShell:

```powershell
$env:AGENTOS_LLM_BACKEND = "mock"
.un_demo.ps1
```

On Linux/WSL2, after dependencies are installed:

```bash
AGENTOS_LLM_BACKEND=mock ./run_demo.sh
```

Open `http://127.0.0.1:8000`. The browser UI includes a live AI Shell, task history, scheduler switching, host metrics, blocked-action audit, and a Results tab. The standalone shell is served locally and uses CSS perspective transforms and animations without remote CDNs. For the React source dashboard, run `cd frontend && npm ci && npm run build`; Vite emits the build into `backend/static/web`.

### Generate Day 5/6 figures

```bash
python scripts/make_graphs.py --cdf
python scripts/make_graphs.py --input experiments/day5 experiments/results.csv --cdf
```

The first command uses the checked-in P2 mock-LLM scheduler runs. The second includes P2's full runtime CSV as a separately labelled `Unspecified` scheduler group where that CSV has no scheduler field. See `results/validation_report.md` before drawing scheduler comparisons.

### Offline packaging

`setup.sh`, `run_demo.sh`, `Dockerfile`, and `docker-compose.yml` are provided. Offline deployment still requires a target-compatible `wheelhouse/`, Ollama Linux installer, Qwen model/model store, and any missing system-package installers. These large, architecture-specific third-party artifacts are deliberately not fabricated or bundled in this source archive.
