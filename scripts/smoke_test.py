"""Day 3 end-to-end smoke test.

Use AGENTOS_LLM_BACKEND=mock for a deterministic offline test, or set it to
ollama to exercise a live Ollama model.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("AGENTOS_LLM_BACKEND", "mock")

from fastapi.testclient import TestClient
from main import app


logging.basicConfig(
    filename=ROOT / "experiments" / "smoke_test.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("agentos.smoke")


def main():
    with TestClient(app) as client:
        log.info("shell -> /api/task: submitting file task")
        response = client.post("/api/task", json={
            "prompt": "list files in the workspace",
            "agent_type": "file",
        })
        response.raise_for_status()
        data = response.json()
        log.info("scheduler -> agent: selected %s", data.get("agent"))
        log.info("agent -> tool -> result: status=%s error=%s", data.get("status"), data.get("error"))
        print("SMOKE TEST RESULT")
        print(f"status={data['status']}")
        print(f"agent={data['agent']}")
        print(f"model={data['model']}")
        print(f"tokens_used={data['tokens_used']}")
        print(f"error={data['error']}")
        print(f"log={ROOT / 'experiments' / 'smoke_test.log'}")


if __name__ == "__main__":
    main()
