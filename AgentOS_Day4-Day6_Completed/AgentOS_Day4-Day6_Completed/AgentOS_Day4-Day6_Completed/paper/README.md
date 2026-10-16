# Day 7 paper artifacts

`DAY7_SCHEDULER_DESIGN_AND_EVALUATION.md` contains the draft evaluation section first, followed by scheduler design, as requested in the Day 7 instructions.

## Source files and method

- Main simulated task-level data: `../experiments/simulated_results.csv`
- Per-seed experiment summaries and ablations: `../experiments/experiment_summary.csv`
- Day 5 mock-only summary: `../experiments/day5/day5_summary.csv`
- `day7_main_metrics.csv`: mean and sample standard deviation across five seeds for each scheduler/workload. p50/p95 are calculated per seed from `end - arrival`; the per-seed quantiles are then summarized across seeds.
- `day7_ablation_metrics.csv`: mean and sample standard deviation across five seeds from the experiment summary's mean completion, makespan, and deadline-success fields.
- `day7_day5_mock_reference.csv`: copy of the Day 5 mock summary used by the paper.

## Figures

The `figures/` directory contains CSV-derived SVG charts for p95 latency, deadline success, ablation outcomes, and held-out default-vs-tuned comparison. P5 figure assets and P3 security-metric tables were not present in the provided ZIP, so these are newly generated from the existing experiment CSVs rather than copied from P5. Add P3's validated security numbers during team integration.

## Important caveats

- The main evaluation is a simulation, not measured real-Qwen inference.
- The uploaded archive contains Day 5 mock results only; real-Qwen comparison and throughput calibration are pending.
- The current ResourceAware scheduler does not implement model-tier routing or a low-privilege queue. Its risk score is a scheduling penalty, not an access-control guarantee.
- Metrics and conclusions in the draft are restricted to values available in the CSVs, with derived p50/p95 values computed from the task-level simulation CSV.
