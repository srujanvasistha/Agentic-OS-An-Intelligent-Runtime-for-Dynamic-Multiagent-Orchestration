#!/usr/bin/env python3
"""90-second live demo: the SAME malicious file, policy OFF vs policy ON.   python demo.py

Everything happens in a throw-away temp folder, so it is safe to run on stage.
"""
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from security.harness import run_spec  # noqa: E402
from security.llm import ScriptedLLM  # noqa: E402

BOLD, RED, GREEN, DIM, END = "\033[1m", "\033[31m", "\033[32m", "\033[2m", "\033[0m"


def main(pause=True):
    atk = json.load(open(os.path.join(HERE, "suite", "attacks", "A01.json")))
    print(f"{BOLD}Attack:{END} the user only asked: \"{atk['user_task']}\"")
    print(f"{BOLD}But report.txt (untrusted) contains:{END}")
    print(f"{DIM}{atk['fixtures']['report.txt']}{END}")
    print("The agent's LLM is compromised: it obeys whatever text it reads.\n")
    for cfg, label in (("off", "POLICY OFF (plain agent)"), ("caps+taint", "POLICY ON  (AgentOS capabilities + taint)")):
        if pause:
            input(f"{DIM}[enter] run with {label}{END} ")
        audit = os.path.join(tempfile.mkdtemp(prefix="demo_"), "audit.jsonl")
        r = run_spec(atk, cfg, ScriptedLLM(), audit_path=audit)
        print(f"{BOLD}=== {label} ==={END}")
        if r["condition_met"]:
            print(f"{RED}data.txt was DELETED by the injected instruction.{END}")
        else:
            print(f"{GREEN}data.txt is safe. The delete was blocked ({', '.join(r['layers'])} layer).{END}")
        print(f"{DIM}audit log:{END}")
        for line in open(audit):
            e = json.loads(line)
            color = GREEN if e["decision"] == "allow" else RED
            print(f"  {color}{e['decision'].upper():5}{END} {e['agent']} {e['action']} {e['target']}  "
                  f"{DIM}[{e['layer']}] {e['reason']}{END}")
        print()
        time.sleep(0.2)
    print(f"{BOLD}Takeaway:{END} the model said \"delete\", but the OS-enforced policy decides, not the model.")


if __name__ == "__main__":
    main(pause="--no-pause" not in sys.argv)
