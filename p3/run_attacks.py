#!/usr/bin/env python3
"""Run the prompt-injection attack suite under each defence configuration.

  python run_attacks.py                         # scripted compromised LLM, all 4 configs
  python run_attacks.py --policy off            # shorthand for --configs off
  python run_attacks.py --policy on             # shorthand for --configs caps+taint
  python run_attacks.py --llm qwen --only A01,A02,A08    # real model through Ollama (slow)
  python run_attacks.py --legacy-policy         # the v1 policy (before the fixes) for docs/findings.md

Writes results/attacks_<llm>.csv and per-config audit logs in results/audit/.
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
from security.llm import QwenLLM, ScriptedLLM  # noqa: E402

FIELDS = ["attack_id", "category", "action_level", "agent", "config", "llm", "policy_version", "succeeded",
          "blocked_by", "reason", "detected", "sandbox_active", "steps_executed", "steps_denied", "errors",
          "checks", "check_ms_mean"]


def load_specs(sub):
    return [json.load(open(p)) for p in sorted(glob.glob(os.path.join(HERE, "suite", sub, "*.json")))]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--llm", choices=["scripted", "qwen"], default="scripted")
    ap.add_argument("--policy", choices=["on", "off"], help="shorthand: off -> 'off', on -> 'caps+taint'")
    ap.add_argument("--configs", help="comma list from: " + ", ".join(CONFIGS))
    ap.add_argument("--only", help="comma list of attack ids, e.g. A01,A02")
    ap.add_argument("--legacy-policy", action="store_true", help="v1 policy without the two fixes")
    ap.add_argument("--out", help="CSV path (default results/attacks_<llm>.csv)")
    a = ap.parse_args()

    configs = (a.configs.split(",") if a.configs else {"off": ["off"], "on": ["caps+taint"]}.get(a.policy, DEFAULT_CONFIGS))
    attacks = load_specs("attacks")
    if a.only:
        keep = set(a.only.split(","))
        attacks = [x for x in attacks if x["id"] in keep]

    llm = ScriptedLLM() if a.llm == "scripted" else QwenLLM()
    if a.llm == "qwen" and not llm.available():
        sys.exit("Ollama is not reachable. Start it (ollama serve) and pull the model (ollama pull qwen2.5:1.5b).")

    version = "v1-legacy" if a.legacy_policy else "v2"
    audit_dir = os.path.join(HERE, "results", "audit")
    os.makedirs(audit_dir, exist_ok=True)
    rows = []
    for cfg in configs:
        audit = os.path.join(audit_dir, f"{a.llm}_{cfg}{'_legacy' if a.legacy_policy else ''}.jsonl")
        if os.path.exists(audit):
            os.remove(audit)
        for atk in attacks:
            r = run_spec(atk, cfg, llm=llm, legacy=a.legacy_policy, audit_path=audit)
            rows.append({
                "attack_id": atk["id"], "category": atk["category"], "action_level": atk["action_level"],
                "agent": atk["agent"], "config": cfg, "llm": llm.name, "policy_version": version,
                "succeeded": r["condition_met"], "blocked_by": ";".join(r["layers"]), "reason": r["first_reason"],
                "detected": r["detected"], "sandbox_active": r["sandbox_active"],
                "steps_executed": r["n_executed"], "steps_denied": r["n_denied"], "errors": r["n_errors"],
                "checks": r["checks"], "check_ms_mean": r["check_ms_mean"],
            })

    out = a.out or os.path.join(HERE, "results", f"attacks_{a.llm}{'_legacy' if a.legacy_policy else ''}.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)

    print(f"\nLLM: {llm.name}   policy: {version}   attacks: {len(attacks)}")
    print(f"{'config':<22}{'action-level':>14}{'answer-manip.':>15}{'sandbox':>9}")
    for cfg in configs:
        mine = [r for r in rows if r["config"] == cfg]
        act = [r for r in mine if r["action_level"]]
        con = [r for r in mine if not r["action_level"]]
        sb = "yes" if mine and mine[0]["sandbox_active"] else "no"
        print(f"{cfg:<22}{sum(r['succeeded'] for r in act):>6}/{len(act):<7}{sum(r['succeeded'] for r in con):>7}/{len(con):<7}{sb:>9}")
    if any(c.endswith("sandbox") for c in configs) and not any(r["sandbox_active"] for r in rows):
        print("\nNOTE: bubblewrap is not installed, so '+sandbox' configs ran WITHOUT a sandbox "
              "(sandbox_active=False in the CSV). Install it: sudo apt install bubblewrap")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
