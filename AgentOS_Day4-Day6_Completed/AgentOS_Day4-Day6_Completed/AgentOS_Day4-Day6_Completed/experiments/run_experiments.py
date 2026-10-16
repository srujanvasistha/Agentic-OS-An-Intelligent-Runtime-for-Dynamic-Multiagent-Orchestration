"""Repeatable scheduler simulation. This does not measure real LLM latency."""

import csv
import random
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from schemas import AgentType, Task
from scheduler.fifo import FIFOScheduler
from scheduler.round_robin import RoundRobinScheduler
from scheduler.priority import PriorityScheduler
from scheduler.resource_aware import ResourceAwareScheduler

OUT = ROOT / "experiments" / "simulated_results.csv"
SUMMARY = ROOT / "experiments" / "experiment_summary.csv"
SEEDS = [11, 23, 37, 41, 59]
SCHEDULERS = ("FIFO", "RoundRobin", "Priority", "ResourceAware")
TERMS = (
    "W_PRIORITY", "W_URGENCY", "W_COMPLEXITY",
    "W_TOKEN_COST", "W_RISK",
)
DEFAULT_WEIGHTS = {
    "W_PRIORITY": 3.0,
    "W_URGENCY": 2.0,
    "W_COMPLEXITY": 1.0,
    "W_TOKEN_COST": 0.01,
    "W_RISK": 2.0,
}


def new_scheduler(name, overrides=None):
    cls = {
        "FIFO": FIFOScheduler,
        "RoundRobin": RoundRobinScheduler,
        "Priority": PriorityScheduler,
        "ResourceAware": ResourceAwareScheduler,
    }[name]
    scheduler = cls()

    if name == "ResourceAware":
        for key, value in DEFAULT_WEIGHTS.items():
            setattr(scheduler, key, value)
        for key, value in (overrides or {}).items():
            setattr(scheduler, key, value)

    return scheduler


def make_workload(kind, seed):
    rng = random.Random(seed)
    base = datetime(2026, 1, 1)
    count = {"light": 12, "mixed": 30, "bursty": 60}[kind]
    arrival = 0.0
    tasks = []

    for i in range(count):
        if kind == "light":
            arrival += rng.uniform(0.5, 2.0)
            tokens = rng.randint(10, 80)
            complexity = rng.randint(1, 2)
            risk = rng.randint(1, 2)
            deadline = rng.randint(15, 35)
        elif kind == "mixed":
            arrival += rng.uniform(0.1, 1.0)
            tokens = rng.randint(20, 300)
            complexity = rng.randint(1, 5)
            risk = rng.randint(1, 4)
            deadline = rng.randint(5, 25)
        else:
            # A short burst of arrivals creates a queue under overload.
            arrival += rng.uniform(0.0, 0.12)
            tokens = rng.randint(100, 700)
            complexity = rng.randint(2, 5)
            risk = rng.randint(2, 5)
            deadline = rng.randint(2, 12)

        tasks.append({
            "arrival": round(arrival, 4),
            "task": Task(
                id=f"{kind}-{seed}-{i:03}",
                prompt=f"Simulated {kind} task {i}",
                agent_type=rng.choice(list(AgentType)),
                priority=rng.randint(1, 10),
                estimated_tokens=tokens,
                complexity=complexity,
                risk_level=risk,
                deadline_s=float(deadline),
                submitted_at=base + timedelta(seconds=arrival),
            ),
        })

    return tasks


def run_simulation(name, workload, seed, overrides=None):
    rng = random.Random(seed)
    scheduler = new_scheduler(name, overrides)
    pending = sorted(workload, key=lambda item: item["arrival"])
    next_index = 0
    elapsed = 0.0
    rows = []
    base = datetime(2026, 1, 1)

    while next_index < len(pending) or scheduler.has_tasks():
        # Enqueue tasks whose simulated submission time has arrived.
        while (
            next_index < len(pending)
            and pending[next_index]["arrival"] <= elapsed
        ):
            scheduler.enqueue(pending[next_index]["task"])
            next_index += 1

        if not scheduler.has_tasks():
            # CPU is idle until the next task arrives.
            elapsed = max(elapsed, pending[next_index]["arrival"])
            continue

        simulated_now = base + timedelta(seconds=elapsed)
        if name == "ResourceAware":
            pressure = 0.9 if len(workload) >= 60 else 0.35
            task = scheduler.next_task(
                resources={
                    "cpu_percent": pressure * 100,
                    "memory_percent": pressure * 90,
                },
                now=simulated_now,
            )
        else:
            task = scheduler.next_task()

        if task is None:
            continue

        arrival_time = (
            task.submitted_at - base
        ).total_seconds()
        start = max(elapsed, arrival_time)
        duration = (
            task.estimated_tokens / 100.0
            + task.complexity * 0.15
            + rng.uniform(0.01, 0.05)
        )
        end = start + duration
        absolute_deadline = arrival_time + task.deadline_s
        deadline_met = end <= absolute_deadline
        elapsed = end

        rows.append({
            "scheduler": name,
            "task_id": task.id,
            "start": round(start, 4),
            "end": round(end, 4),
            "tokens": task.estimated_tokens,
            "deadline_met": deadline_met,
            "workload": task.id.split("-")[0],
            "seed": seed,
            "arrival": round(arrival_time, 4),
            "deadline": round(absolute_deadline, 4),
        })

    return rows


def metrics(rows):
    if not rows:
        return {
            "tasks": 0,
            "makespan": 0.0,
            "mean_completion": 0.0,
            "deadline_success_percent": 0.0,
            "tokens": 0,
        }

    starts = [row["start"] for row in rows]
    ends = [row["end"] for row in rows]
    return {
        "tasks": len(rows),
        "makespan": round(max(ends) - min(starts), 4),
        "mean_completion": round(
            statistics.mean(
                row["end"] - row["arrival"] for row in rows
            ), 4
        ),
        "deadline_success_percent": round(
            100 * sum(row["deadline_met"] for row in rows) / len(rows), 2
        ),
        "tokens": sum(row["tokens"] for row in rows),
    }


def write_csv(path, rows, columns):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main():
    all_rows = []
    summaries = []

    # Main evaluation: same workloads and seeds for all four schedulers.
    for workload_name in ("light", "mixed", "bursty"):
        for seed in SEEDS:
            workload = make_workload(workload_name, seed)
            for name in SCHEDULERS:
                rows = run_simulation(name, workload, seed)
                all_rows.extend(rows)
                summaries.append({
                    "experiment": "main",
                    "workload": workload_name,
                    "scheduler": name,
                    "seed": seed,
                    **metrics(rows),
                })

    # Grid search only on mixed tuning seeds.
    candidates = []
    for wp in (2.0, 3.0, 4.0):
        for wu in (1.0, 2.0, 3.0):
            overrides = {"W_PRIORITY": wp, "W_URGENCY": wu}
            rows = []
            for seed in SEEDS[:3]:
                rows.extend(run_simulation(
                    "ResourceAware", make_workload("mixed", seed),
                    seed, overrides,
                ))
            result = metrics(rows)
            candidates.append((
                result["deadline_success_percent"],
                -result["mean_completion"],
                overrides,
            ))

    best_weights = max(candidates, key=lambda item: (item[0], item[1]))[2]
    print("Weights selected on mixed tuning workload:", best_weights)

    # Held-out evaluation uses different seeds and bursty workload.
    
    # Held-out evaluation: compare every scheduler on the same unseen seeds.
    held_out_seeds = (101, 202, 303, 404, 505)

    for seed in held_out_seeds:
        workload = make_workload("bursty", seed)

        # Evaluate the four default schedulers.
        for name in SCHEDULERS:
            rows = run_simulation(name, workload, seed)
            all_rows.extend(rows)

            summaries.append({
                "experiment": "held_out",
                "workload": "bursty",
                "scheduler": name,
                "seed": seed,
                **metrics(rows),
            })

        # Evaluate tuned ResourceAware on the same workload and seed.
        tuned_rows = run_simulation(
            "ResourceAware",
            workload,
            seed,
            best_weights,
        )
        all_rows.extend(tuned_rows)

        summaries.append({
            "experiment": "held_out",
            "workload": "bursty",
            "scheduler": "ResourceAware_tuned",
            "seed": seed,
            **metrics(tuned_rows),
        })

    # Ablation: remove one score term at a time, recording each seed separately.
    for removed in TERMS:
        for seed in SEEDS:
            rows = run_simulation(
                "ResourceAware",
                make_workload("bursty", seed),
                seed,
                {removed: 0.0},
            )
            all_rows.extend(rows)

            summaries.append({
                "experiment": f"ablation_remove_{removed}",
                "workload": "bursty",
                "scheduler": "ResourceAware",
                "seed": seed,
                **metrics(rows),
            })


    write_csv(
        OUT,
        all_rows,
        [
            "scheduler", "task_id", "start", "end", "tokens",
            "deadline_met", "workload", "seed", "arrival", "deadline",
        ],
    )
    write_csv(
        SUMMARY,
        summaries,
        [
            "experiment", "workload", "scheduler", "seed", "tasks",
            "makespan", "mean_completion",
            "deadline_success_percent", "tokens",
        ],
    )

    print(f"Detailed results: {OUT}")
    print(f"Summary results: {SUMMARY}")
    print(f"Detailed rows: {len(all_rows)}")


if __name__ == "__main__":
    main()
