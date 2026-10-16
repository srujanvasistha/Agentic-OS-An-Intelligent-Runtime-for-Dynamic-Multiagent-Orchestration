#!/usr/bin/env python3
"""Day 5: compare the same small workload on Ollama Qwen and the mock LLM.

This is a sequential benchmark: one model request at a time. It writes one CSV
per scheduler/backend and a comparison report. It never fabricates real-model
results; Ollama runs must be executed on the developer's machine.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import re
import statistics
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psutil
import requests

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from llm.client import DEFAULT_TPS, MockLLMClient  # noqa: E402
from schemas import AgentType, Task  # noqa: E402
from scheduler.fifo import FIFOScheduler  # noqa: E402
from scheduler.round_robin import RoundRobinScheduler  # noqa: E402
from scheduler.priority import PriorityScheduler  # noqa: E402
from scheduler.resource_aware import ResourceAwareScheduler  # noqa: E402

MODEL_DEFAULT = "qwen2.5:1.5b"
MAX_TOKENS_DEFAULT = 48
ARRIVAL_GAP_SECONDS = 0.20
CALIBRATION_THRESHOLD = 0.25

SCHEDULERS = {
    "FIFO": FIFOScheduler,
    "RoundRobin": RoundRobinScheduler,
    "Priority": PriorityScheduler,
    "ResourceAware": ResourceAwareScheduler,
}

# Twelve short, mixed-cost tasks. The exact same definitions and arrival offsets
# are reused for each scheduler and backend.
TASK_DEFINITIONS: list[dict[str, Any]] = [
    {"id": "d5-01", "kind": "light", "agent": AgentType.GENERAL, "priority": 3, "tokens": 12, "complexity": 1, "risk": 1, "deadline": 35, "prompt": "Define an operating system in one sentence."},
    {"id": "d5-02", "kind": "heavy", "agent": AgentType.SECURITY, "priority": 9, "tokens": 48, "complexity": 5, "risk": 4, "deadline": 60, "prompt": "Give three concise steps to harden a Linux server."},
    {"id": "d5-03", "kind": "light", "agent": AgentType.FILE, "priority": 4, "tokens": 14, "complexity": 1, "risk": 1, "deadline": 35, "prompt": "Explain what a CSV file is in one sentence."},
    {"id": "d5-04", "kind": "heavy", "agent": AgentType.GENERAL, "priority": 7, "tokens": 48, "complexity": 4, "risk": 2, "deadline": 55, "prompt": "Compare FIFO and priority scheduling in three brief points."},
    {"id": "d5-05", "kind": "light", "agent": AgentType.SECURITY, "priority": 2, "tokens": 12, "complexity": 1, "risk": 2, "deadline": 35, "prompt": "What is multi-factor authentication? Be concise."},
    {"id": "d5-06", "kind": "heavy", "agent": AgentType.FILE, "priority": 8, "tokens": 48, "complexity": 4, "risk": 2, "deadline": 60, "prompt": "Outline a safe workflow for validating a JSON configuration."},
    {"id": "d5-07", "kind": "light", "agent": AgentType.GENERAL, "priority": 5, "tokens": 14, "complexity": 2, "risk": 1, "deadline": 40, "prompt": "What does an API do? Answer in one sentence."},
    {"id": "d5-08", "kind": "heavy", "agent": AgentType.SECURITY, "priority": 10, "tokens": 48, "complexity": 5, "risk": 5, "deadline": 60, "prompt": "List concise defensive checks for a suspicious file upload."},
    {"id": "d5-09", "kind": "light", "agent": AgentType.FILE, "priority": 1, "tokens": 12, "complexity": 1, "risk": 1, "deadline": 40, "prompt": "Define a file checksum in one sentence."},
    {"id": "d5-10", "kind": "heavy", "agent": AgentType.GENERAL, "priority": 6, "tokens": 48, "complexity": 4, "risk": 2, "deadline": 65, "prompt": "Give a short checklist for debugging a slow Python program."},
    {"id": "d5-11", "kind": "light", "agent": AgentType.SECURITY, "priority": 3, "tokens": 14, "complexity": 2, "risk": 2, "deadline": 40, "prompt": "What is the principle of least privilege? Be concise."},
    {"id": "d5-12", "kind": "heavy", "agent": AgentType.FILE, "priority": 8, "tokens": 48, "complexity": 5, "risk": 3, "deadline": 65, "prompt": "Describe three checks before processing an uploaded archive."},
]

CSV_COLUMNS = [
    "backend", "model", "scheduler", "task_id", "task_kind", "agent_type",
    "priority", "complexity", "risk_level", "estimated_tokens",
    "arrival_offset_seconds", "deadline_seconds", "arrival_time", "start_time",
    "end_time", "queue_wait_seconds", "latency_seconds", "llm_latency_seconds",
    "generation_seconds", "tokens", "deadline_met", "system_cpu_percent_start",
    "system_cpu_percent_end", "system_memory_percent_start",
    "system_memory_percent_end", "process_rss_mb_start", "process_rss_mb_end",
    "error",
]


def make_scheduler(name: str):
    return SCHEDULERS[name]()


def make_task(definition: dict[str, Any], run_start: datetime, index: int) -> Task:
    arrival_offset = index * ARRIVAL_GAP_SECONDS
    submitted_at = run_start + timedelta(seconds=arrival_offset)
    return Task(
        id=definition["id"],
        prompt=definition["prompt"],
        agent_type=definition["agent"],
        priority=definition["priority"],
        estimated_tokens=definition["tokens"],
        complexity=definition["complexity"],
        risk_level=definition["risk"],
        deadline_s=float(definition["deadline"]),
        submitted_at=submitted_at,
    )


def system_snapshot(process: psutil.Process) -> dict[str, float]:
    return {
        "cpu": float(psutil.cpu_percent(interval=None)),
        "memory": float(psutil.virtual_memory().percent),
        "rss_mb": process.memory_info().rss / (1024 * 1024),
    }


def ensure_ollama(base_url: str, model: str, timeout: float, max_tokens: int) -> None:
    try:
        tags_response = requests.get(f"{base_url}/api/tags", timeout=min(timeout, 10))
        tags_response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Cannot reach Ollama at {base_url}. Start Ollama and retry. Details: {exc}"
        ) from exc

    available = {item.get("name", "") for item in tags_response.json().get("models", [])}
    if model not in available:
        raise RuntimeError(
            f"Model {model!r} is not installed. Run `ollama pull {model}` and retry."
        )

    print(f"Warming up {model}; this request is excluded from benchmark CSVs...")
    try:
        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": "Reply with OK.",
                "stream": False,
                "keep_alive": "30m",
                "options": {"num_predict": min(8, max_tokens), "temperature": 0},
            },
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Ollama warm-up failed: {exc}") from exc


def call_ollama(prompt: str, base_url: str, model: str, timeout: float, max_tokens: int) -> dict[str, Any]:
    started = time.perf_counter()
    response = requests.post(
        f"{base_url}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "30m",
            "options": {"num_predict": max_tokens, "temperature": 0},
        },
        timeout=timeout,
    )
    response.raise_for_status()
    request_seconds = time.perf_counter() - started
    data = response.json()
    eval_count = int(data.get("eval_count") or 0)
    eval_duration_ns = int(data.get("eval_duration") or 0)
    generation_seconds = eval_duration_ns / 1_000_000_000 if eval_duration_ns > 0 else request_seconds
    return {
        "tokens": eval_count,
        "llm_latency_seconds": request_seconds,
        "generation_seconds": max(generation_seconds, 0.000001),
        "text": data.get("response", ""),
    }


def call_mock(prompt: str, definition: dict[str, Any], client: MockLLMClient, max_tokens: int) -> dict[str, Any]:
    started = time.perf_counter()
    response = client.generate(prompt)
    # Use the workload's declared output-token estimate for the mock duration.
    # This is an explicit model assumption, not a measured token count.
    modeled_tokens = min(int(definition["tokens"]), max_tokens)
    modeled_seconds = modeled_tokens / max(client.tps, 0.001)
    remaining = modeled_seconds - (time.perf_counter() - started)
    if remaining > 0:
        time.sleep(remaining)
    elapsed = time.perf_counter() - started
    return {
        "tokens": modeled_tokens,
        "llm_latency_seconds": elapsed,
        "generation_seconds": max(modeled_seconds, 0.000001),
        "text": response.text,
    }


def run_one_scheduler(
    scheduler_name: str,
    backend_name: str,
    output_path: Path,
    *,
    model: str,
    base_url: str,
    timeout: float,
    max_tokens: int,
    mock_tps: float,
) -> list[dict[str, Any]]:
    scheduler = make_scheduler(scheduler_name)
    run_start_dt = datetime.now().astimezone()
    run_start_mono = time.perf_counter()
    tasks = [make_task(definition, run_start_dt, i) for i, definition in enumerate(TASK_DEFINITIONS)]
    task_defs = {item["id"]: item for item in TASK_DEFINITIONS}
    next_index = 0
    rows: list[dict[str, Any]] = []
    process = psutil.Process(os.getpid())
    mock_client = MockLLMClient(tps=mock_tps) if backend_name == "mock" else None

    # Prime CPU sampling before the first task.
    psutil.cpu_percent(interval=0.1)

    while next_index < len(tasks) or scheduler.has_tasks():
        elapsed = time.perf_counter() - run_start_mono
        while next_index < len(tasks) and next_index * ARRIVAL_GAP_SECONDS <= elapsed:
            scheduler.enqueue(tasks[next_index])
            next_index += 1

        if not scheduler.has_tasks():
            if next_index < len(tasks):
                until_next = next_index * ARRIVAL_GAP_SECONDS - (time.perf_counter() - run_start_mono)
                if until_next > 0:
                    time.sleep(until_next)
            continue

        now = datetime.now().astimezone()
        if scheduler_name == "ResourceAware":
            task = scheduler.next_task(
                resources={
                    "cpu_percent": psutil.cpu_percent(interval=None),
                    "memory_percent": psutil.virtual_memory().percent,
                },
                now=now,
            )
        else:
            task = scheduler.next_task()
        if task is None:
            continue

        definition = task_defs[task.id]
        arrival_offset = tasks.index(task) * ARRIVAL_GAP_SECONDS
        arrival_mono = run_start_mono + arrival_offset
        start_mono = time.perf_counter()
        start_dt = datetime.now().astimezone()
        start_snapshot = system_snapshot(process)
        error = ""
        token_count = 0
        llm_latency = 0.0
        generation_seconds = 0.0
        try:
            if backend_name == "real":
                generated = call_ollama(
                    task.prompt, base_url, model, timeout, max_tokens
                )
            else:
                assert mock_client is not None
                generated = call_mock(task.prompt, definition, mock_client, max_tokens)
            token_count = int(generated["tokens"])
            llm_latency = float(generated["llm_latency_seconds"])
            generation_seconds = float(generated["generation_seconds"])
        except Exception as exc:  # retain failures in the CSV rather than losing the run
            error = f"{type(exc).__name__}: {exc}"

        end_dt = datetime.now().astimezone()
        end_mono = time.perf_counter()
        end_snapshot = system_snapshot(process)
        latency_seconds = max(0.0, end_mono - arrival_mono)
        deadline_met = (end_dt <= task.submitted_at + timedelta(seconds=float(task.deadline_s))) if not error else False

        rows.append({
            "backend": backend_name,
            "model": model if backend_name == "real" else f"mock-qwen2.5:1.5b (tps={mock_tps:.3f})",
            "scheduler": scheduler_name,
            "task_id": task.id,
            "task_kind": definition["kind"],
            "agent_type": task.agent_type.value,
            "priority": task.priority,
            "complexity": task.complexity,
            "risk_level": task.risk_level,
            "estimated_tokens": task.estimated_tokens,
            "arrival_offset_seconds": round(arrival_offset, 4),
            "deadline_seconds": task.deadline_s,
            "arrival_time": task.submitted_at.isoformat(),
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "queue_wait_seconds": round(max(0.0, start_mono - arrival_mono), 4),
            "latency_seconds": round(latency_seconds, 4),
            "llm_latency_seconds": round(llm_latency, 4),
            "generation_seconds": round(generation_seconds, 4),
            "tokens": token_count,
            "deadline_met": deadline_met,
            "system_cpu_percent_start": round(start_snapshot["cpu"], 2),
            "system_cpu_percent_end": round(end_snapshot["cpu"], 2),
            "system_memory_percent_start": round(start_snapshot["memory"], 2),
            "system_memory_percent_end": round(end_snapshot["memory"], 2),
            "process_rss_mb_start": round(start_snapshot["rss_mb"], 2),
            "process_rss_mb_end": round(end_snapshot["rss_mb"], 2),
            "error": error,
        })
        print(f"[{backend_name:4}] {scheduler_name:13} {task.id}: {token_count} tokens, {llm_latency:.2f}s" + (f" ERROR {error}" if error else ""))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def percentile95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [row for row in rows if not row["error"]]
    latencies = [float(row["latency_seconds"]) for row in successful]
    starts = [datetime.fromisoformat(row["start_time"]) for row in successful]
    ends = [datetime.fromisoformat(row["end_time"]) for row in successful]
    generation_time = sum(float(row["generation_seconds"]) for row in successful)
    tokens = sum(int(row["tokens"]) for row in successful)
    return {
        "tasks": len(rows),
        "successful_tasks": len(successful),
        "failed_tasks": len(rows) - len(successful),
        "p95_latency_seconds": round(percentile95(latencies), 4),
        "makespan_seconds": round((max(ends) - min(starts)).total_seconds(), 4) if starts else 0.0,
        "deadline_success_percent": round(100 * sum(bool(row["deadline_met"]) for row in successful) / len(successful), 2) if successful else 0.0,
        "tokens": tokens,
        "aggregate_tokens_per_second": round(tokens / generation_time, 4) if generation_time > 0 else 0.0,
        "mean_system_memory_percent": round(statistics.mean([float(r["system_memory_percent_end"]) for r in successful]), 2) if successful else 0.0,
    }


def write_comparison(all_rows: dict[tuple[str, str], list[dict[str, Any]]], output_dir: Path, calibrated_tps: float | None, default_tps: float) -> None:
    summary_rows = []
    for (backend_name, scheduler_name), rows in all_rows.items():
        summary_rows.append({"backend": backend_name, "scheduler": scheduler_name, **summarize(rows)})
    summary_path = output_dir / "day5_summary.csv"
    columns = ["backend", "scheduler", "tasks", "successful_tasks", "failed_tasks", "p95_latency_seconds", "makespan_seconds", "deadline_success_percent", "tokens", "aggregate_tokens_per_second", "mean_system_memory_percent"]
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(summary_rows)

    lines = [
        "# Day 5: Real Qwen vs mock benchmark",
        "",
        "## Setup",
        "",
        f"- Workload: {len(TASK_DEFINITIONS)} fixed tasks (light and heavy), same IDs and arrival offsets for every scheduler/backend.",
        "- Execution: one request at a time; one warm-up request is excluded from measurements.",
        "- Real backend: Ollama Qwen2.5-1.5B; mock backend: duration modeled from estimated output tokens / mock TPS.",
        "- Metrics: p95 latency (arrival to completion), makespan, deadline success, token count, CPU/RAM samples.",
        "- CPU/RAM readings are host/process samples, not isolated per-task resource attribution.",
        "",
        "## Results",
        "",
        "See `day5_summary.csv` and the per-scheduler CSVs for measured values.",
        "",
        "| Backend | Scheduler | p95 latency (s) | Makespan (s) | Deadline success | Failures |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(f"| {row['backend']} | {row['scheduler']} | {row['p95_latency_seconds']} | {row['makespan_seconds']} | {row['deadline_success_percent']}% | {row['failed_tasks']} |")

    lines += ["", "## Scheduler ranking comparison", ""]
    for metric, label in [("p95_latency_seconds", "p95 latency"), ("makespan_seconds", "makespan")]:
        real_rows = [r for r in summary_rows if r["backend"] == "real" and r["successful_tasks"] > 0]
        mock_rows = [r for r in summary_rows if r["backend"] == "mock" and r["successful_tasks"] > 0]
        if len(real_rows) == len(SCHEDULERS) and len(mock_rows) == len(SCHEDULERS):
            real_rank = [r["scheduler"] for r in sorted(real_rows, key=lambda r: r[metric])]
            mock_rank = [r["scheduler"] for r in sorted(mock_rows, key=lambda r: r[metric])]
            lines.append(f"- **{label}:** real ranking = `{ ' > '.join(real_rank) }`; mock ranking = `{ ' > '.join(mock_rank) }`; exact order match = **{real_rank == mock_rank}**.")
        else:
            lines.append(f"- **{label}:** comparison unavailable until all four schedulers have successful real and mock runs.")

    if calibrated_tps is not None:
        relative_delta = abs(calibrated_tps - default_tps) / default_tps if default_tps else float("inf")
        lines += ["", "## Mock TPS calibration", "", f"- Existing DEFAULT_TPS: `{default_tps:.4f}` tokens/s.", f"- Aggregate observed real generation rate: `{calibrated_tps:.4f}` tokens/s.", f"- Relative difference: `{relative_delta * 100:.1f}%`."]
        if relative_delta >= CALIBRATION_THRESHOLD:
            lines.append(f"- Difference exceeds {CALIBRATION_THRESHOLD * 100:.0f}%; mock runs used the measured rate `{calibrated_tps:.4f}` tokens/s. To persist it to `backend/llm/client.py`, rerun with `--persist-tps-calibration`.")
        else:
            lines.append("- Difference is within the calibration threshold; mock runs used the existing TPS value.")
    else:
        lines += ["", "## Mock TPS calibration", "", "- Not calculated because no successful real Qwen results were available."]

    lines += [
        "", "## Interpretation and limitations", "",
        "- Matching rankings on this single 12-task workload is preliminary evidence only; it does not prove the mock is generally faithful.",
        "- Mock token counts and durations are modeled from task estimates, while real token counts and generation durations come from Ollama. Treat the two backends as different measurement modes.",
        "- Check failure counts before interpreting rankings. A scheduler with failed tasks must not be considered equivalent to a fully successful run.",
        "- No benchmark results are prefilled: this report is generated from the actual local runs.",
    ]
    (output_dir / "DAY5_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Summary written: {summary_path}")
    print(f"Report written: {output_dir / 'DAY5_REPORT.md'}")


def persist_tps(value: float) -> None:
    client_path = BACKEND / "llm" / "client.py"
    content = client_path.read_text(encoding="utf-8")
    updated, count = re.subn(r"^DEFAULT_TPS\s*=\s*[0-9]+(?:\.[0-9]+)?", f"DEFAULT_TPS = {value:.4f}", content, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"Could not safely update DEFAULT_TPS in {client_path}")
    client_path.write_text(updated, encoding="utf-8")
    print(f"Persisted DEFAULT_TPS = {value:.4f} to {client_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("both", "real", "mock"), default="both", help="Run both backends (default), only real Ollama, or mock-only offline.")
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", MODEL_DEFAULT))
    parser.add_argument("--base-url", default=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("OLLAMA_TIMEOUT", "180")))
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS_DEFAULT)
    parser.add_argument("--mock-tps", type=float, default=DEFAULT_TPS, help="Override mock token/s estimate when no real calibration is available.")
    parser.add_argument("--persist-tps-calibration", action="store_true", help="Persist measured real TPS to backend/llm/client.py if it differs by at least 25%%.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments" / "day5")
    args = parser.parse_args()
    if args.max_tokens < 1 or args.timeout <= 0 or args.mock_tps <= 0:
        parser.error("--max-tokens, --timeout, and --mock-tps must be positive")

    run_real = args.backend in ("both", "real")
    run_mock = args.backend in ("both", "mock")
    if run_real:
        try:
            ensure_ollama(args.base_url.rstrip("/"), args.model, args.timeout, args.max_tokens)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    real_rows: dict[str, list[dict[str, Any]]] = {}
    mock_rows: dict[str, list[dict[str, Any]]] = {}
    real_tps = None
    if run_real:
        for name in SCHEDULERS:
            path = args.output_dir / "real" / f"qwen2_5_1_5b_{name.lower()}.csv"
            rows = run_one_scheduler(name, "real", path, model=args.model, base_url=args.base_url.rstrip("/"), timeout=args.timeout, max_tokens=args.max_tokens, mock_tps=args.mock_tps)
            real_rows[name] = rows
        successful = [row for rows in real_rows.values() for row in rows if not row["error"]]
        token_total = sum(int(row["tokens"]) for row in successful)
        duration_total = sum(float(row["generation_seconds"]) for row in successful)
        if duration_total > 0 and token_total > 0:
            real_tps = token_total / duration_total
            relative_delta = abs(real_tps - DEFAULT_TPS) / DEFAULT_TPS if DEFAULT_TPS else float("inf")
            if args.persist_tps_calibration and relative_delta >= CALIBRATION_THRESHOLD:
                persist_tps(real_tps)

    mock_tps_used = args.mock_tps
    if run_mock and real_tps is not None:
        relative_delta = abs(real_tps - DEFAULT_TPS) / DEFAULT_TPS if DEFAULT_TPS else float("inf")
        if relative_delta >= CALIBRATION_THRESHOLD:
            mock_tps_used = real_tps
            print(f"Measured real TPS differs from DEFAULT_TPS by {relative_delta * 100:.1f}%; mock run will use {mock_tps_used:.4f} TPS.")
        else:
            mock_tps_used = DEFAULT_TPS
            print(f"Measured real TPS is within {CALIBRATION_THRESHOLD * 100:.0f}% of DEFAULT_TPS; mock run will use {mock_tps_used:.4f} TPS.")
    elif run_mock:
        print(f"No real calibration in this run; mock will use {mock_tps_used:.4f} TPS.")

    if run_mock:
        for name in SCHEDULERS:
            path = args.output_dir / "mock" / f"mock_{name.lower()}.csv"
            rows = run_one_scheduler(name, "mock", path, model=args.model, base_url=args.base_url.rstrip("/"), timeout=args.timeout, max_tokens=args.max_tokens, mock_tps=mock_tps_used)
            mock_rows[name] = rows

    all_rows: dict[tuple[str, str], list[dict[str, Any]]] = {}
    all_rows.update({("real", name): rows for name, rows in real_rows.items()})
    all_rows.update({("mock", name): rows for name, rows in mock_rows.items()})
    write_comparison(all_rows, args.output_dir, real_tps, DEFAULT_TPS)
    print("Day 5 benchmark run completed. Review DAY5_REPORT.md and day5_summary.csv.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
