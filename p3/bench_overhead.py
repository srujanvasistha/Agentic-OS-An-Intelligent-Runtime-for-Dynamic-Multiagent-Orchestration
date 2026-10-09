#!/usr/bin/env python3
"""Measure the cost of one policy check() call (includes writing the audit-log line).  -> results/overhead.json"""
import json
import os
import statistics
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from security import PolicyEngine  # noqa: E402

N = 20000
CASES = [
    ("FileAgent", "fs.read", "notes.txt"),
    ("FileAgent", "fs.read", "../outside.txt"),
    ("FileAgent", "shell.exec", ["grep", "-c", "ERROR", "app.log"]),
    ("FileAgent", "net", "evil.example"),
    ("GeneralAgent", "fs.write", "x.txt"),
]


def main():
    base = tempfile.mkdtemp(prefix="agentos_bench_")
    os.makedirs(os.path.join(base, "workspace"))
    eng = PolicyEngine(os.path.join(HERE, "security", "capabilities.yaml"),
                       audit_path=os.path.join(base, "audit.jsonl"), base_dir=base)
    times = []
    for i in range(N):
        agent, action, target = CASES[i % len(CASES)]
        t0 = time.perf_counter()
        eng.check(agent, action, target, task_id="bench")
        times.append((time.perf_counter() - t0) * 1000)
    times.sort()
    res = {"calls": N, "mean_ms": round(statistics.mean(times), 4), "p50_ms": round(times[N // 2], 4),
           "p95_ms": round(times[int(N * 0.95)], 4), "p99_ms": round(times[int(N * 0.99)], 4)}
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", "overhead.json"), "w") as f:
        json.dump(res, f, indent=2)
    print(res)


if __name__ == "__main__":
    main()
