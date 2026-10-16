# P5 Day 5 — Experiment graph generation

## One-command usage

From the repository root:

```bash
python make_graphs.py experiments/simulated_results.csv
```

Regenerate the simulation CSV with the standardized graph columns, then plot it:

```bash
python experiments/run_experiments.py
python make_graphs.py experiments/simulated_results.csv
```

Do not pass `experiments/results.csv` for scheduler comparisons: that file is runtime/model telemetry and has no scheduler column. The graph script now fails with a clear explanation rather than emitting misleading scheduler placeholders. A final task-level CSV from P2 can be passed directly once it contains scheduler labels.

The default output directory is `results/figures/`. Every figure is written as both a 300-DPI PNG and a vector PDF. To select another output directory, pass `--output-dir path/to/figures`. To omit the optional CDF, pass `--no-cdf`.

## Figures

1. p50 and p95 latency per scheduler (seconds).
2. Mean makespan per workload/seed trial (seconds), with ±1 standard deviation error bars when there are repeated trials.
3. Total token usage per scheduler (tokens).
4. Task success rate (%) when `success` or `status` is present. For the repository's current simulation CSV, this figure uses `deadline_met` and is explicitly labelled **deadline success rate**; deadline success is not the same as task execution success.
5. Unsafe actions blocked with vs without policy enforcement, only when the CSV contains both a policy condition and a blocked-action field. Otherwise the script writes a clearly labelled placeholder and warning instead of inventing an ablation result.
6. Optional empirical latency CDF.

Scheduler order is FIFO, RR, Priority, AgentOS (ResourceAware is normalised to AgentOS). The same scheduler palette and hatch patterns are reused across figures for grayscale readability. Model/backend information is annotated on plots. The current simulated scheduler CSV has no LLM model field, so it is labelled `Simulation (no LLM inference)` rather than being misrepresented as a real Qwen run.

## Input schema and current repository data

The preferred task-level schema is:

`task_id, scheduler, task_type, submit_ts, start_ts, end_ts, latency, tokens, success, blocked, model`

Optional policy-ablation column: `policy_enabled` (true/false, or equivalent with/without labels). `experiments/run_experiments.py` now writes these standard columns in addition to the legacy simulation columns. `latency` is simulated completion minus arrival; `model` is explicitly `Simulation (no LLM inference)`. `success`, `blocked`, and `policy_enabled` remain blank because the scheduler simulator does not execute agent tasks or security attacks. The success plot therefore uses `deadline_met` and is explicitly labelled deadline success. The blocked-action figure remains a placeholder until P3 supplies real policy-on/off attack results. The runner tags rows as `main`, `held_out`, `held_out_tuned`, `tuning`, or `ablation`; scheduler comparison figures use only `main` and `held_out` rows to prevent tuning/ablation rows from biasing the baseline comparison.

The existing `experiments/results.csv` is runtime/model telemetry and currently has no scheduler column, so it cannot support scheduler-comparison figures by itself. Use `experiments/simulated_results.csv` to test the plotting pipeline today. P2/P3 should ensure final experiment CSVs log scheduler, task timing, tokens, success, blocked, model/backend, and policy-on/off attack condition for the policy-ablation chart.

## Dependency

Install requirements with `pip install -r requirements.txt`; `matplotlib` is required for graph generation.
