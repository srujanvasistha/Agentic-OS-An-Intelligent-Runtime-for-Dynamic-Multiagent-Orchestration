# AgentOS Day 3 Completion

## Completed

1. Four scheduler implementations behind the Day 2 `Scheduler` contract:
   - FIFO
   - Round-Robin
   - Priority
   - Resource-Aware
2. Runtime scheduler selection through `AGENTOS_SCHEDULER`.
3. P4-compatible `get_system_state()` monitor provider using `psutil`.
4. Resource-aware scheduler receives live system state before selecting work.
5. Runtime concurrency limit constrained to 1 or 2 parallel inference tasks.
6. Runtime model-tier support:
   - `AGENTOS_MODEL_TIER=0.5b`
   - `AGENTOS_MODEL_TIER=1.5b`
7. Resource pressure can select the 0.5B tier for resource-aware execution.
8. Per-task agent/client isolation for safe parallel inference.
9. Added `POST /api/runtime/run` for bounded batch execution.
10. Added a minimal shell client in `shell/cli.py`.
11. Added `scripts/smoke_test.py` and `experiments/smoke_test.log`.
12. Added Day 3 automated tests.

## Verification

- Day 1 + Day 2 + Day 3 tests: **39 passed**
- Python compile check: **passed**
- Fresh-process scheduler configuration checks: FIFO, Round-Robin, Priority, Resource-Aware all selected correctly.
- End-to-end offline smoke test: **passed**
  - shell/request
  - `/api/task`
  - configured scheduler
  - AgentManager
  - FileAgent
  - filesystem tool
  - TaskResult

## Important

The uploaded Day 2 repository did not contain P2's alternative scheduler files or a separate P4 monitor module. Day 3 therefore adds those missing implementation pieces while preserving the existing Day 2 interfaces.

The security/policy tool boundary remains unchanged. This is intentional: the Day 3 smoke path uses the existing FileSystemTool through FileAgent, while the frozen `run_tool(...)` policy boundary remains available for P3's later enforcement work.
