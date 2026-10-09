# P3: Security + capabilities (all deliverables)

```
p3_security/
  security/                 # the library P1/P4 import
    capabilities.yaml       # per-agent capability table + allowlists
    policy.py               # PolicyEngine.check(), taint tracking, audit log
    tools.py                # SafeTools: every tool goes through check()
    sandbox.py              # bubblewrap wrapper
    security_agent.py       # injection scanner (advisory)
    llm.py                  # ScriptedLLM (compromised mock) + QwenLLM (Ollama)
    harness.py              # experiment harness (temp worlds, success checks, safety guard)
  suite/                    # 22 attacks + 16 benign tasks (JSON), build_suite.py generates them
  tests/                    # 108 tests (policy, tools, suite results)
  run_attacks.py  run_benign.py  bench_overhead.py  summarize.py
  demo.py                   # 90-second live demo (policy off vs on)
  sandbox_check.py          # run on YOUR machine: proves the sandbox contains a policy bug
  results/                  # CSVs, audit logs, summary.md  (already generated)
  docs/                     # threat_model.md, findings.md, paper_security_section.md
```

## Commands
```bash
pip install pyyaml pytest requests
make all            # build suite, run tests, run attacks, benign, overhead, summary
make demo           # live demo
make sandbox        # needs: sudo apt install bubblewrap
make qwen           # real Qwen through Ollama (needs `ollama serve` + `ollama pull qwen2.5:1.5b`)
```
Always run with `python3 -m pytest` / `make` from inside `p3_security/`.

## Integration (copy-paste to P1 and P4)
```python
from security import PolicyEngine, SafeTools, PermissionDenied
engine = PolicyEngine("security/capabilities.yaml", audit_path="logs/audit.jsonl")
tools = SafeTools(engine, use_sandbox=True)      # sandbox only activates if bwrap is installed
tools.read_file("FileAgent", "notes.txt", task_id=task.id)   # raises PermissionDenied when blocked
```
- Agents must use `tools.*` for every file, shell or network action. Never call `open()` or `subprocess` directly.
- Catch `PermissionDenied`; show `e.decision.reason` to the user. For a taint block, ask the user and retry with `approved=True`.
- Use one `task_id` per user task, because taint is tracked per task.
- Ablation switches: `PolicyEngine(cfg, enabled=False)` = policy off; `taint_rules=False` = caps only.

## Results (scripted compromised LLM, details in results/summary.md)
| | off | caps | caps+taint |
|---|---|---|---|
| action-level attacks that succeed | 20/20 | 9/20 | **0/20** |
| answer-manipulation (known limit) | 2/2 | 2/2 | 2/2 |
| benign tasks passing without approval | 16/16 | 16/16 | 12/16 (16/16 with approval) |

Policy check overhead: 0.051 ms mean.

## What is NOT done / what only you can do
1. **Run `make sandbox` on a machine with bubblewrap.** I could not install it in my environment, so the `+sandbox`
   columns equal `caps+taint` and the sandbox is unverified.
2. **Run the real model:** `make qwen`. The Qwen adapter is written but untested (no Ollama in my environment).
   Report its results separately from the scripted ones.
3. **Integrate with P1's runtime** and re-run on the final VM. My harness uses its own tiny agent loop.
4. Fill the **[TODO]** items in `docs/paper_security_section.md` and check citation 7 (Saltzer & Schroeder).
5. Read `docs/findings.md` and be ready to explain every finding in the viva.
