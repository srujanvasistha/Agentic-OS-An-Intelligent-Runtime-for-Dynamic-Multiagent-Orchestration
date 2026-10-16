# P2/P3 implementation handoff

This package adds implementation support for the scheduler experiment and policy/security tasks.

## P2: scheduler and experiment logging

- `experiments/run_experiments.py` runs repeatable FIFO, Round-Robin, Priority, and resource-aware simulations across fixed seeds and workload classes.
- `experiments/simulated_results.csv` is generated simulation data. Its timestamps/latency are simulated seconds and its model label explicitly says no LLM inference was performed.
- Runtime logging now writes the common task-level columns to `experiments/results.csv`: task ID/type, scheduler, submit/start/end timestamps, latency, tokens, status-derived success/blocked flags, model/backend, and experiment label.
- A runtime row is not a four-scheduler comparison unless the runtime is actually configured to run each scheduler. Do not compare FIFO-only live rows against the other scheduler simulations as if they were measured on the same execution path.

## P3: capability enforcement and prompt-injection harness

- `backend/security/policy.py` implements a default-deny application policy. It permits limited read-only workspace filesystem operations for FileAgent and read-only system info for approved agents; it denies path traversal, sensitive paths, write/delete operations, shell, network, unknown tools, and unknown agents.
- `backend/tools/interface.py` is the common policy-before-tool-execution boundary.
- FileAgent filesystem operations now call through that boundary.
- `experiments/run_security_attacks.py` defines 20 deterministic attack cases from malicious files, logs, web text, and tool output. It writes both policy-off and policy-on rows to `experiments/security_attack_results.csv`.
- The attack harness never executes payloads. Policy-off rows mean the harness did not consult the policy, not that an OS command was actually run. These results demonstrate the policy decision boundary only; they are not an LLM prompt-injection success rate or proof of OS-level isolation.
- Linux deployments should add bubblewrap/seccomp/Landlock/AppArmor as an independent OS-level boundary. The Python policy layer alone is not a security sandbox.

## Commands

From the project root (with the project venv active):

```powershell
python -m pip install -r requirements.txt
python experiments/run_experiments.py
python experiments/run_security_attacks.py
python make_graphs.py experiments/simulated_results.csv --security-csv experiments/security_attack_results.csv
python -m pytest backend/tests -q
```

The final command creates the scheduler figures from simulation data and the blocked-actions figure from the separate policy harness CSV. The plotted security comparison must be described as a deterministic policy-harness result, not real model inference.

## Remaining work before paper claims

1. Run task-level live experiments with the chosen model and record the actual scheduler for each run.
2. Validate task success against a task-specific expected outcome, not only `status == done`.
3. Run the attack corpus through real agents with untrusted content, preserving the policy-on/off condition and logging attempted, allowed, blocked, and completed actions.
4. Repeat security tests inside the intended Linux OS sandbox before making containment claims.

## P5 metric integrity note

- `make_graphs.py` plots task execution success only when the CSV has explicit non-empty `success` values; otherwise it writes a clearly marked unavailable figure rather than using `deadline_met` as a proxy.
- Deadline attainment is plotted separately in `05_deadline_success_rate.png/.pdf`.
- The simulation `tokens` field is an estimated token budget, not actual LLM token consumption; the chart title and axis say so.
- Simulation timestamps and latency are simulated seconds. Actual task execution success and real LLM token use require live task execution instrumentation.
