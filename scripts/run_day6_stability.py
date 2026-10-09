"""One-command, timeout-protected Day 6 validation runner."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = [
    ("Full pytest suite", [sys.executable, "-m", "pytest", "-v"]),
    ("Day 5 MockLLM workload", [sys.executable, "scripts/day5_mock_workload.py"]),
    ("Day 5 failure paths", [sys.executable, "scripts/day5_failure_paths.py"]),
    ("Day 6 1000-task soak test", [sys.executable, "scripts/day6_soak_test.py"]),
]


def main() -> int:
    env = os.environ.copy()
    env["AGENTOS_LLM_BACKEND"] = "mock"
    env["AGENTOS_SEED"] = env.get("AGENTOS_SEED", "42")
    env["PYTHONHASHSEED"] = env.get("PYTHONHASHSEED", env["AGENTOS_SEED"])
    os.chdir(ROOT)
    for index, (label, command) in enumerate(STEPS, start=1):
        print(f"\n[{index}/{len(STEPS)}] {label}", flush=True)
        try:
            completed = subprocess.run(
                command, cwd=ROOT, env=env, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300,
            )
        except subprocess.TimeoutExpired as exc:
            print(exc.stdout or "")
            print(f"FAIL: {label} exceeded 300 seconds (hang watchdog)", file=sys.stderr)
            return 124
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
        if completed.returncode != 0:
            print(f"FAIL: {label} exited with {completed.returncode}", file=sys.stderr)
            return completed.returncode
    print("\nAgentOS Day 6 stability validation PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
