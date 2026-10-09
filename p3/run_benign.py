#!/usr/bin/env python3
"""Run the benign task suite: do legitimate tasks still work under each defence configuration?

  python run_benign.py [--configs off,caps,caps+taint,caps+taint+sandbox]

A task that is blocked ONLY by the taint layer is counted as 'needs approval' (a false positive that a
human can resolve with one click). We re-run it with approved=True to show it then passes.
Writes results/benign.csv.
"""
import argparse
import csv
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from security.harness import CONFIGS, DEFAULT_CONFIGS, run_spec  # noqa: E402

FIELDS = ["task_id", "name", "agent", "config", "passed", "needs_approval", "passed_with_approval",
          "blocked_by", "reason", "scanner_flagged", "sandbox_active", "check_ms_mean"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default=",".join(DEFAULT_CONFIGS))
    ap.add_argument("--out", default=os.path.join(HERE, "results", "benign.csv"))
    a = ap.parse_args()

    tasks = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(HERE, "suite", "benign", "*.json")))]
    rows = []
    for cfg in a.configs.split(","):
        for t in tasks:
            r = run_spec(t, cfg)
            passed = r["condition_met"] and r["n_denied"] == 0 and r["n_errors"] == 0
            with_appr = passed
            if not passed and r["needs_approval"]:
                r2 = run_spec(t, cfg, approved=True)
                with_appr = r2["condition_met"] and r2["n_denied"] == 0 and r2["n_errors"] == 0
            rows.append({"task_id": t["id"], "name": t["name"], "agent": t["agent"], "config": cfg,
                         "passed": passed, "needs_approval": (not passed) and r["needs_approval"],
                         "passed_with_approval": with_appr, "blocked_by": ";".join(r["layers"]),
                         "reason": r["first_reason"], "scanner_flagged": r["detected"],
                         "sandbox_active": r["sandbox_active"], "check_ms_mean": r["check_ms_mean"]})
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)

    print(f"{'config':<22}{'passed':>8}{'needs approval':>16}{'pass w/ approval':>18}")
    for cfg in a.configs.split(","):
        m = [r for r in rows if r["config"] == cfg]
        print(f"{cfg:<22}{sum(r['passed'] for r in m):>5}/{len(m):<2}{sum(r['needs_approval'] for r in m):>16}"
              f"{sum(r['passed_with_approval'] for r in m):>12}/{len(m)}")
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
