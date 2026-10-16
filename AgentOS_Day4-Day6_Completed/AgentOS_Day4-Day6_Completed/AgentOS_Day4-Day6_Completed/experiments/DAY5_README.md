# Day 5 — Real Qwen small-batch benchmark

This benchmark runs the same fixed 12-task mixed workload through FIFO, RoundRobin, Priority, and ResourceAware, sequentially, using either Ollama Qwen2.5-1.5B and/or the mock backend. It performs one warm-up call before the real runs and caps generated output tokens.

## Prerequisites

- Python dependencies from the repository's `requirements.txt` (`requests`, `psutil`, etc.).
- For real runs, Ollama must be running and `qwen2.5:1.5b` must be installed:

```bash
ollama pull qwen2.5:1.5b
ollama list
```

Close heavy applications before benchmarking. The script makes one request at a time; real CPU inference may take a while.

## Run the full experiment

From the repository root, with the project's Python environment activated:

```bash
python experiments/run_day5_real_qwen.py
```

Options:

```bash
python experiments/run_day5_real_qwen.py --backend mock
python experiments/run_day5_real_qwen.py --backend real
python experiments/run_day5_real_qwen.py --max-tokens 32
python experiments/run_day5_real_qwen.py --persist-tps-calibration
```

`--persist-tps-calibration` explicitly updates `backend/llm/client.py` only when the measured aggregate real generation rate differs from the current `DEFAULT_TPS` by at least 25%. Without that flag, the source file is not changed. When both backends are run, a far-off observed rate is used for the mock timing model for that run.

## Output files

- `experiments/day5/real/qwen2_5_1_5b_fifo.csv` (and one file for each other scheduler)
- `experiments/day5/mock/mock_fifo.csv` (and one file for each other scheduler)
- `experiments/day5/day5_summary.csv`
- `experiments/day5/DAY5_REPORT.md`

The report compares scheduler rankings by p95 latency and makespan. It records actual results only; no example/fabricated measurements are committed. CPU and RAM values are system/process samples around each task, not precise per-task attribution. A matching ranking on this single small workload is preliminary evidence, not proof that the mock is generally faithful.
