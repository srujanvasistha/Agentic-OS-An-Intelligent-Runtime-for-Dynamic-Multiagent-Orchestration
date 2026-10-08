"""Minimal AgentOS shell client for the Day 3 smoke path."""

from __future__ import annotations

import argparse
import json
import requests


def submit(base_url: str, prompt: str, agent_type: str | None = None) -> dict:
    payload = {"prompt": prompt}
    if agent_type:
        payload["agent_type"] = agent_type
    response = requests.post(f"{base_url.rstrip('/')}/api/task", json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(description="AgentOS shell")
    parser.add_argument("prompt", help="Task to submit")
    parser.add_argument("--agent-type", choices=["general", "file", "security"])
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    print(json.dumps(submit(args.base_url, args.prompt, args.agent_type), indent=2))


if __name__ == "__main__":
    main()
