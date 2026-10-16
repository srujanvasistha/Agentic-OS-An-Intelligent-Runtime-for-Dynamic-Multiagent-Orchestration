
"""Report mean and standard deviation for scheduler experiments."""

import csv
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "experiment_summary.csv"
OUTPUT = ROOT / "mean_std_report.csv"

METRICS = [
    "makespan",
    "mean_completion",
    "deadline_success_percent",
    "tokens",
]


def main():
    groups = defaultdict(list)

    with INPUT.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            experiment = row["experiment"]

            if experiment != "main" and not (
                experiment == "held_out"
                or experiment == "held_out_tuned"
                or experiment.startswith("ablation_remove_")
            ):
                continue

            key = (
                experiment,
                row["workload"],
                row["scheduler"],
            )
            groups[key].append(row)

    report = []

    for (experiment, workload, scheduler), rows in sorted(groups.items()):
        result = {
            "experiment": experiment,
            "workload": workload,
            "scheduler": scheduler,
            "seed_count": len(rows),
        }

        for metric in METRICS:
            values = [float(row[metric]) for row in rows]

            result[f"{metric}_mean"] = round(
                statistics.mean(values), 4
            )
            result[f"{metric}_std"] = round(
                statistics.stdev(values), 4
            ) if len(values) > 1 else 0.0

        report.append(result)

    columns = [
        "experiment",
        "workload",
        "scheduler",
        "seed_count",
        *[f"{metric}_mean" for metric in METRICS],
        *[f"{metric}_std" for metric in METRICS],
    ]

    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(report)

    print("Experiment report — simulated results")
    print("-" * 100)

    for row in report:
        print(
            f'{row["experiment"]:28} '
            f'{row["scheduler"]:22} '
            f'n={row["seed_count"]}  '
            f'deadline={row["deadline_success_percent_mean"]:.2f}'
            f' ± {row["deadline_success_percent_std"]:.2f}%  '
            f'completion={row["mean_completion_mean"]:.3f}'
            f' ± {row["mean_completion_std"]:.3f}'
        )

    print(f"\nSaved report: {OUTPUT}")


if __name__ == "__main__":
    main()
