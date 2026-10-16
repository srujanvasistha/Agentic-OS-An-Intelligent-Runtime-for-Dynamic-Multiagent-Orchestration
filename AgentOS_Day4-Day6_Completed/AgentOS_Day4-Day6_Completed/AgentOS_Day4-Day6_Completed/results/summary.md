# AgentOS scheduler summary

Statistics are calculated from the selected raw task rows. Latency is in seconds; blank metrics mean the source CSV does not contain enough information to calculate them.

| Backend | Scheduler | Tasks | Mean latency (s) | p50 latency (s) | p95 latency (s) | Makespan (s) | Success rate (%) | Tokens |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| mock | FIFO | 12 | 8.3393 | 8.3399 | 15.9790 | 18.0726 | 100.0000 | 366.0000 |
| mock | Priority | 12 | 10.5010 | 12.5172 | 16.7778 | 18.0665 | 100.0000 | 366.0000 |
| mock | ResourceAware | 12 | 10.0941 | 10.3559 | 16.7854 | 18.0734 | 100.0000 | 366.0000 |
| mock | RoundRobin | 12 | 8.3345 | 8.3338 | 15.9690 | 18.0636 | 100.0000 | 366.0000 |
