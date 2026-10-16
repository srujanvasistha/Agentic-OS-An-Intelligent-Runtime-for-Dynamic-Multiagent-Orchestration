# AgentOS Day 4–6 implementation and runbook

## Day 4 — Web runtime

- FastAPI serves the local AI Shell at `http://127.0.0.1:8000`.
- `POST /task` accepts a task and returns a task ID; `GET /task/{task_id}` returns lifecycle state and result.
- `GET /history` reads task snapshots from SQLite (`results/agentos_tasks.sqlite3` by default).
- `GET /metrics` reports host CPU/RAM, runtime token totals, queue length, task count, and mean completed-task latency.
- `GET /blocked` exposes the default-deny tool audit log.
- `POST /scheduler` switches among FIFO, Priority, Round Robin, and Resource Aware; queued tasks are transferred to the replacement scheduler.
- `WS /stream` emits task/scheduler/policy events.
- The web console recognizes `run`, `status`, `history`, `scheduler`, and `help`. Other input is a task prompt; the UI does not execute arbitrary shell commands.
- Results figures are served by `/api/results/figures` and `/results/figures/{filename}`.

The UI uses local CSS animations and perspective/3D hover transforms. It does not load a remote animation library or CDN. The Python backend also has a no-build fallback shell at `/` in `backend/static/index.html`; build the React dashboard for the full React experience.

## Day 5 — Benchmark figures

From the repository root:

```bash
python scripts/make_graphs.py
python scripts/make_graphs.py --cdf
```

By default, the script reads the P2 Day 5 mock-LLM scheduler CSVs from `experiments/day5/mock/`, plus the policy-ablation CSV at `experiments/security_attack_results.csv`. It writes PNG/PDF figures to `results/figures/`, summary CSV/Markdown to `results/summary.csv` and `results/summary.md`, and validation notes to `results/validation_report.md`.

Use `--input PATH` for a CSV or directory. For the Day 6 full comparison, point it at `experiments/day5/` after real runs have been generated. The graph script labels mock and real-model runs separately and does not synthesize missing metrics.

## Day 6 — Final graph checks and packaging

1. Ensure P2's full experiment CSV and P3 attack/ablation CSVs are copied into this repository. The checked-in files include `experiments/results.csv` and `experiments/security_attack_results.csv`; actual real-Qwen CSVs are generated locally by `experiments/run_day5_real_qwen.py` and are not included unless a real run has been performed.
2. Generate figures and the summary with `python scripts/make_graphs.py --input experiments/day5 experiments/results.csv --cdf`.
3. Review `results/validation_report.md`. The report checks p95 >= p50 where latency data exists and compares task ID sets across scheduler runs.
4. Build the React UI with `cd frontend && npm ci && npm run build`. This emits static assets into `backend/static/web`, served by FastAPI at the root URL.
5. Prepare `wheelhouse/`, `installers/`, and `models/` before disconnecting the internet. They are intentionally not populated with third-party binaries/model weights in this source archive.
6. On Linux/WSL2, run `./setup.sh`, then `./run_demo.sh`. On Windows, use WSL2 or Docker for the Linux backend.

## Limitations to preserve in the demo

- Mock results are not real-model results; mock and real runs must be labelled separately.
- The security ablation CSV records simulated attack attempts; it does not execute the payloads.
- Host CPU/RAM snapshots are not precise per-task resource attribution.
- bubblewrap is installed/checked by setup, but the current app-layer default-deny tool boundary is not the same as a fully integrated bubblewrap/Landlock sandbox. Do not claim OS-level isolation until the runtime actually launches tasks inside that sandbox.
- Offline setup cannot be certified until the target-specific Python wheelhouse, Ollama installer, model weights/model store, and required system packages have been staged and tested with networking disabled.
