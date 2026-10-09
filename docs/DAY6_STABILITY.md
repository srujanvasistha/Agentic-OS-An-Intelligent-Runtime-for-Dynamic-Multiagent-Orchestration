# Day 6 — Stability and Reproducibility

## Implemented stability changes

- Pinned direct Python dependencies in `requirements.txt` to the versions installed in the Day 6 validation environment. Re-run validation after any intentional dependency upgrade.
- Added `backend/reproducibility.py`; the experiment launcher sets `AGENTOS_SEED=42` and `PYTHONHASHSEED=42` before Python starts. Python's `random` module is seeded, and NumPy is seeded if an optional experiment adds it.
- Made task history bounded (default 1,000 terminal/recent entries, configurable with `AGENTOS_TASK_HISTORY_LIMIT`). Completed/failed/blocked history is evicted oldest-first when over the cap; queued/running tasks are not evicted.
- Made `MemoryStore` operations thread-safe and retained its bounded deque.
- Serialized result and policy-metric CSV appends within the process to prevent parallel task writes from racing over headers/rows.
- Replaced recursive stale-queue skipping with an iterative loop to avoid recursion-depth failures.
- Added a 1,000-task MockLLM soak test and regression tests for deterministic seeds, bounded history/memory, and concurrent CSV appends.
- Added a one-command PowerShell launcher, offline dependency wheelhouse helpers, and a Linux systemd service template.

## One-command validation (Windows PowerShell)

From any working directory, run the script by its project path, or from the AgentOS root:

```powershell
.\scripts\setup.ps1
.\scripts\run_day6_stability.ps1
```

The validation launcher sets MockLLM mode and a fixed seed, runs all pytest tests, validates the Day 5 MockLLM workload, checks timeout/denied/Ollama-unavailable failure paths, and runs 1,000 tasks through the runtime. Each phase has a 300-second subprocess watchdog to fail visibly instead of hanging forever. It intentionally does not require Ollama.

## Reproducibility controls

- `AGENTOS_SEED=42` is the default experiment seed. Change it only when recording a new experiment condition.
- `PYTHONHASHSEED` must be set before Python starts; the launcher does this.
- MockLLM is deterministic for a given prompt, but wall-clock latency, timestamps, OS scheduling, and live Ollama generation are not guaranteed bit-for-bit identical. Report these limitations in the evaluation.
- Save experiment outputs with the code revision, dependency versions, scheduler, policy enforcement setting, model tier/backend, seed, workload size, and machine configuration. Do not compare runs with different conditions as if they were controlled.

## Memory and hang checks

The soak test submits 1,000 deterministic MockLLM tasks and asserts that all complete, the task history remains bounded to 100 in the test configuration, runtime memory remains bounded to 50 entries, and the results CSV has exactly 1,000 rows with the frozen schema. It also reports Python `tracemalloc` current/peak values and process RSS before/after. Each launch phase has a 300-second timeout watchdog. These are regression guards, not a proof that every OS-level leak is impossible.

## Offline dependency packaging

On a connected machine with the same OS, Python version, and architecture as the target VM:

```powershell
.\scripts\setup.ps1
.\scripts\download_offline_dependencies.ps1
```

Transfer the project and `wheelhouse/` to the offline VM, then run:

```powershell
.\scripts\install_offline_dependencies.ps1
```

Wheelhouses are platform/Python-version specific. Build one for each target OS and Python version. Do not assume a Windows wheelhouse can install on Linux. Ollama and model weights are separate from Python dependencies; download/install them separately when the VM must run the real model. MockLLM mode works without Ollama.

## VM paths and service setup

- All Python scripts resolve the project root from `__file__`; invoke scripts by their project-relative paths rather than relying on the terminal's current directory.
- On Windows, run FastAPI from the `backend` directory with `..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000`.
- `deploy/agentos.service` is a Linux systemd template for a deployment at `/opt/agentos`. Create a dedicated `agentos` user, copy the project to that location, create the virtual environment, configure `/opt/agentos/.env`, and ensure the user can write to `/opt/agentos/experiments` before installing the service. Review the service hardening options against the VM's filesystem layout before enabling it.
- Keep the API bound to loopback unless remote access is intentionally protected by a firewall and authentication/reverse proxy.

## Team integration bug log

No experiment-run bug reports from P2, P3, P4, or P5 were included in the supplied archive. Record and triage any real reports here rather than inventing resolutions.

| Reporter | Reproduction / environment | Expected | Actual | Severity | Owner | Fix / regression test | Status |
|---|---|---|---|---|---|---|---|
| P2 | Pending report | Pending | Pending | TBD | P1/P2 | Add once reproduced | Awaiting report |
| P3 | Pending report | Pending | Pending | TBD | P1/P3 | Add once reproduced | Awaiting report |
| P4 | Pending report | Pending | Pending | TBD | P1/P4 | Add once reproduced | Awaiting report |
| P5 | Pending VM/package report | Pending | Pending | TBD | P1/P5 | Add once reproduced | Awaiting report |
