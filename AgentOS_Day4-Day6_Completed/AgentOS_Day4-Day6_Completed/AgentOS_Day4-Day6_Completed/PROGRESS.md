# Agentic-OS — Project Progress Report

## 1. Project Overview

Agentic-OS is an intelligent runtime for dynamic multi-agent orchestration. The project explores how scheduling policies can be used to coordinate tasks and evaluate scheduling performance under different simulated workload conditions.

## 2. Work Completed

### Scheduler Implementation
- Implemented a FIFO scheduling policy.
- Implemented Round Robin scheduling.
- Implemented Priority-based scheduling.
- Implemented ResourceAware scheduling.
- Added a tuned ResourceAware scheduler configuration.
- Added priority scheduling logic in `backend/scheduler/priority.py`.

### Simulation and Experiment Framework
- Built a simulation-based experiment framework to compare scheduler policies.
- Added support for light, mixed, and bursty workload scenarios.
- Added fixed random seeds to support reproducible experiments.
- Added held-out comparisons between scheduler configurations.
- Added five-seed experiment runs and mean ± standard deviation reporting.
- Added ablation experiments to evaluate the effect of individual scheduling components.
- Added CSV export for detailed simulation results and experiment summaries.
- Added a Makefile target to run experiments using `make experiments`.

### Results and Reporting
- Generated `simulated_results.csv` containing 5,040 detailed simulation records.
- Generated `experiment_summary.csv` for summarized experiment results.
- Updated `experiments/report_results.py` to include held-out comparisons and seed counts.
- Evaluated the tuned ResourceAware configuration against the original configuration.
- Evaluated the effect of removing urgency from the scheduling policy.

## 3. Validation and Testing

- Ran the project test suite using `make test`.
- Latest recorded test result: 36 tests passed.
- One Starlette/httpx deprecation warning was reported.
- Experiment outputs were generated using the simulation framework.

## 4. Preliminary Experimental Observations

In the recorded held-out comparison:

- ResourceAware mean completion metric: 129.247.
- Tuned ResourceAware mean completion metric: 129.196.
- The reported deadline-success metric was 1.00 for both configurations.
- The ablation experiment without urgency reported a deadline-success metric of 3.00%.

These are preliminary simulation results. Their interpretation depends on the metric definitions and units used by the experiment runner. They should not be interpreted as real-world performance guarantees.

## 5. Limitations

- The experiments described here are simulation-based.
- Real Qwen/LLM integration through Ollama has not yet been verified.
- Simulation results do not establish real-world multi-agent orchestration performance.
- Further validation of result schemas, metrics, and experimental assumptions remains necessary.

## 6. Remaining Work

- Complete and review the project documentation.
- Verify the CSV column names and consistency between detailed results and summaries.
- Validate the interpretation of all reported metrics.
- Review experiment reproducibility and scheduler behavior.
- Investigate real-LLM integration and test it separately when the environment supports it.
- Document the architecture, setup instructions, experiment commands, and limitations.
- Review the repository for generated or unnecessary files.

## 7. Reproducibility

Run the test suite:

```bash
make test
```

Run the experiment framework:

```bash
make experiments
```

Review the generated CSV files and reporting scripts to understand the experimental setup and results.

## 8. Current Status

The core scheduler policies, simulation experiment framework, and initial reporting workflow have been implemented. The test suite has passed in the latest recorded run. Documentation, result validation, and real-LLM integration remain areas for further work.


## Day 5 Benchmark Harness

- Added `experiments/run_day5_real_qwen.py` to run a fixed 12-task mixed workload through FIFO, RoundRobin, Priority, and ResourceAware.
- Added one-task-at-a-time Ollama Qwen2.5-1.5B execution, a warm-up request, capped generation tokens, and per-task timing/token/deadline/CPU/RAM logging.
- Added mock-backend timing runs, summary metrics, p95 latency and makespan ranking comparisons, and observed-TPS calibration guidance.
- Added `experiments/DAY5_README.md` and `make day5` / `make day5-mock` commands.
- **Not yet completed by adding code alone:** real Qwen measurements must be run on a machine with Ollama and the model installed. No real-run CSVs or benchmark conclusions are claimed until those commands finish successfully.


## Day 7 Paper Sections

- Added `paper/DAY7_SCHEDULER_DESIGN_AND_EVALUATION.md`, with evaluation first and scheduler design second.
- Added CSV-derived mean ± standard deviation tables for p50/p95 latency, makespan, estimated token budget, deadline success, and deadline misses across light, mixed, and bursty workloads.
- Added ablation and held-out tuning summaries and figures.
- Kept the Day 5 mock benchmark separate from the seeded simulation results.
- The supplied archive did not include a successful real-Qwen benchmark CSV or P5 figure assets; the paper explicitly records those gaps and uses newly generated figures from available CSVs.
- Documented that model-tier routing and a low-privilege queue are not implemented in the current ResourceAware scheduler.
