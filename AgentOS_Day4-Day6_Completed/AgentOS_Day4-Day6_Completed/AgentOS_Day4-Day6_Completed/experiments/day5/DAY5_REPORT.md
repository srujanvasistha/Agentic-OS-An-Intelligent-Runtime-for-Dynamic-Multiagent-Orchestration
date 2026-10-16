# Day 5: Real Qwen vs mock benchmark

## Setup

- Workload: 12 fixed tasks (light and heavy), same IDs and arrival offsets for every scheduler/backend.
- Execution: one request at a time; one warm-up request is excluded from measurements.
- Real backend: Ollama Qwen2.5-1.5B; mock backend: duration modeled from estimated output tokens / mock TPS.
- Metrics: p95 latency (arrival to completion), makespan, deadline success, token count, CPU/RAM samples.
- CPU/RAM readings are host/process samples, not isolated per-task resource attribution.

## Results

See `day5_summary.csv` and the per-scheduler CSVs for measured values.

| Backend | Scheduler | p95 latency (s) | Makespan (s) | Deadline success | Failures |
|---|---|---:|---:|---:|---:|
| mock | FIFO | 15.979 | 18.0726 | 100.0% | 0 |
| mock | RoundRobin | 15.969 | 18.0636 | 100.0% | 0 |
| mock | Priority | 16.7778 | 18.0665 | 100.0% | 0 |
| mock | ResourceAware | 16.7854 | 18.0734 | 100.0% | 0 |

## Scheduler ranking comparison

- **p95 latency:** comparison unavailable until all four schedulers have successful real and mock runs.
- **makespan:** comparison unavailable until all four schedulers have successful real and mock runs.

## Mock TPS calibration

- Not calculated because no successful real Qwen results were available.

## Interpretation and limitations

- Matching rankings on this single 12-task workload is preliminary evidence only; it does not prove the mock is generally faithful.
- Mock token counts and durations are modeled from task estimates, while real token counts and generation durations come from Ollama. Treat the two backends as different measurement modes.
- Check failure counts before interpreting rankings. A scheduler with failed tasks must not be considered equivalent to a fully successful run.
- No benchmark results are prefilled: this report is generated from the actual local runs.
