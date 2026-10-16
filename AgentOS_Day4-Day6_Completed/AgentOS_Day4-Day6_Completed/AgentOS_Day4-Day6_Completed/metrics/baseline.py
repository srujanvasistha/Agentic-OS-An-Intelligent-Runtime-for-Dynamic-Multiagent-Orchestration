
"""Calculate baseline metrics from experiments/results.csv."""

import csv
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "experiments" / "results.csv"


def percentile(values, percent):
    if not values:
        return None

    values = sorted(values)
    position = (len(values) - 1) * percent
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower

    return round(
        values[lower] * (1 - fraction) + values[upper] * fraction, 4
    )


def main():
    if not CSV_PATH.exists():
        raise SystemExit(f"Results file not found: {CSV_PATH}")

    with CSV_PATH.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise SystemExit("No experiment results found.")

    latencies = []
    tokens = 0
    completed = 0
    timestamps = []

    for row in rows:
        try:
            latency = float(row.get("latency_seconds") or 0)
            if latency >= 0:
                latencies.append(latency)
        except (ValueError, TypeError):
            pass

        try:
            tokens += int(float(row.get("tokens_used") or 0))
        except (ValueError, TypeError):
            pass

        status = (row.get("status") or "").strip().lower()
        if status in {"done", "completed", "success", "succeeded"}:
            completed += 1

        timestamp = (row.get("timestamp") or "").strip()
        if timestamp:
            try:
                timestamps.append(datetime.fromisoformat(timestamp))
            except ValueError:
                pass

    result = {
        "source_file": str(CSV_PATH.relative_to(ROOT)),
        "note": "Metrics describe existing CSV rows, not necessarily a fresh run.",
        "total_tasks": len(rows),
        "p50_latency_seconds": percentile(latencies, 0.50),
        "p95_latency_seconds": percentile(latencies, 0.95),
        "makespan_seconds": (
            round((max(timestamps) - min(timestamps)).total_seconds(), 4)
            if len(timestamps) >= 2 else None
        ),
        "total_tokens": tokens,
        "success_rate_percent": round(100 * completed / len(rows), 2),
        "deadline_misses": None,
        "unsafe_actions_blocked": None,
        "limitations": {
            "deadline_misses": (
                "Not recorded in the current CSV; deadline_s is not logged."
            ),
            "unsafe_actions_blocked": (
                "The CSV does not record the reason for blocked tasks."
            ),
            "makespan": (
                "Timestamp span across recorded tasks; not necessarily the "
                "actual runtime of a complete experiment."
            ),
        },
    }

    output = ROOT / "experiments" / "baseline_metrics.json"
    output.write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )

    print(json.dumps(result, indent=2))
    print(f"\nSaved metrics to: {output}")


if __name__ == "__main__":
    main()
