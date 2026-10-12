# Benchmark sanity checks

- Input files loaded: 4
- PASS: p95 latency is not below p50 for any available group; task IDs and workload-defining fields are consistent wherever multiple schedulers were available.
- 
- Workload comparability must be interpreted within each backend. Different model backends can have different execution semantics.
- CPU/RAM samples are not treated as per-task attribution unless the source explicitly provides them.
