#!/usr/bin/env python3
"""Generate reproducible AgentOS benchmark figures and scheduler summaries.

Default input is the checked-in P2 Day 5 mock-LLM run CSVs. Pass --input to use
another CSV or a directory of CSVs. The script never fabricates missing metrics:
it reports unavailable fields and skips calculations that the source cannot support.
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "experiments" / "day5" / "mock"
DEFAULT_SECURITY = ROOT / "experiments" / "security_attack_results.csv"
DEFAULT_OUTPUT = ROOT / "results" / "figures"
SUMMARY_CSV = ROOT / "results" / "summary.csv"
SUMMARY_MD = ROOT / "results" / "summary.md"
VALIDATION_MD = ROOT / "results" / "validation_report.md"

SCHEDULER_ORDER = ["FIFO", "RoundRobin", "Priority", "ResourceAware", "Unspecified"]
SCHEDULER_COLORS = {
    "FIFO": "#2878B5",
    "RoundRobin": "#F28E2B",
    "Priority": "#59A14F",
    "ResourceAware": "#B07AA1",
    "Unspecified": "#7F8793",
}
BACKEND_LABELS = {
    "mock": "Mock LLM",
    "ollama": "Real Qwen / Ollama",
    "real": "Real model",
    "unknown": "Backend unspecified",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, nargs="+", default=[DEFAULT_INPUT],
                        help="One or more input CSV files/directories (default: P2 mock benchmark folder).")
    parser.add_argument("--security-csv", type=Path, default=DEFAULT_SECURITY,
                        help="Policy ablation/attack CSV.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT,
                        help="Output directory for PNG and PDF figures.")
    parser.add_argument("--summary-csv", type=Path, default=SUMMARY_CSV)
    parser.add_argument("--summary-md", type=Path, default=SUMMARY_MD)
    parser.add_argument("--validation-md", type=Path, default=VALIDATION_MD)
    parser.add_argument("--cdf", action="store_true", help="Also generate a latency CDF figure.")
    return parser.parse_args()


def _normalise_scheduler(value: Any) -> str:
    text = str(value or "").strip()
    compact = text.lower().replace("_", "").replace("-", "").replace(" ", "")
    known = {
        "fifo": "FIFO", "fifoscheduler": "FIFO",
        "roundrobin": "RoundRobin", "roundrobinscheduler": "RoundRobin",
        "priority": "Priority", "priorityscheduler": "Priority",
        "resourceaware": "ResourceAware", "resourceawarescheduler": "ResourceAware",
    }
    return known.get(compact, text or "Unspecified")


def _normalise_backend(row: pd.Series) -> str:
    value = str(row.get("backend", "") or "").strip().lower()
    if value in {"mock", "ollama", "real"}:
        return value
    value = str(row.get("llm_backend", "") or "").strip().lower()
    if value in {"mock", "ollama", "real"}:
        return value
    return "unknown"


def _read_input(paths: list[Path]) -> tuple[pd.DataFrame, list[Path]]:
    files: list[Path] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Experiment input does not exist: {path}")
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(p for p in path.rglob("*.csv")
                                if p.is_file() and "summary" not in p.name.lower()
                                and "report" not in p.name.lower()))
        else:
            raise ValueError(f"Input must be a CSV file or directory: {path}")
    # A user may pass a parent directory and an explicit file under it.
    files = list(dict.fromkeys(files))
    if not files:
        raise FileNotFoundError(f"No CSV files found under: {path}")

    frames = []
    loaded = []
    for file in files:
        try:
            frame = pd.read_csv(file)
        except Exception as exc:
            print(f"WARNING: skipping unreadable CSV {file}: {exc}", file=sys.stderr)
            continue
        if frame.empty:
            print(f"WARNING: skipping empty CSV: {file}", file=sys.stderr)
            continue
        frame["__source_file"] = str(file.relative_to(ROOT)) if file.is_relative_to(ROOT) else file.name
        # Scheduler name is normally a CSV column; a per-scheduler filename is
        # used only when the file is known to be a scheduler-specific benchmark.
        if "scheduler" not in frame.columns:
            name = file.stem.lower()
            for candidate in SCHEDULER_ORDER:
                if candidate.lower() in name and candidate != "Unspecified":
                    frame["scheduler"] = candidate
                    break
        if "scheduler" not in frame.columns:
            frame["scheduler"] = "Unspecified"
        frame["scheduler"] = frame["scheduler"].map(_normalise_scheduler)
        frame["backend"] = frame.apply(_normalise_backend, axis=1)
        frames.append(frame)
        loaded.append(file)
    if not frames:
        raise ValueError("No readable, non-empty experiment CSVs were found.")
    data = pd.concat(frames, ignore_index=True, sort=False)
    return data, loaded


def _numeric(data: pd.DataFrame, column: str) -> pd.Series | None:
    if column not in data.columns:
        return None
    return pd.to_numeric(data[column], errors="coerce")


def _latency_column(data: pd.DataFrame) -> str | None:
    for name in ("latency_seconds", "latency", "completion_latency_seconds", "completion_latency"):
        if name in data.columns:
            return name
    # For simulated results with start/end/arrival timestamps, latency is end - arrival.
    if {"end", "arrival"}.issubset(data.columns):
        end = pd.to_numeric(data["end"], errors="coerce")
        arrival = pd.to_numeric(data["arrival"], errors="coerce")
        data["__latency_seconds"] = end - arrival
        return "__latency_seconds"
    return None


def _model_label(backend: str) -> str:
    return BACKEND_LABELS.get(str(backend).lower(), str(backend) or "Backend unspecified")


def _scheduler_backend_pairs(data: pd.DataFrame) -> list[tuple[str, str]]:
    schedulers = set(data["scheduler"].dropna().astype(str))
    backends = set(data["backend"].dropna().astype(str))
    scheduler_order = [name for name in SCHEDULER_ORDER if name in schedulers]
    scheduler_order += sorted(schedulers - set(scheduler_order))
    return [(scheduler, backend)
            for scheduler in scheduler_order
            for backend in sorted(backends, key=lambda b: (b != "mock", b != "ollama", b))]


def _save(fig, output_dir: Path, stem: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_dir / f"{stem}.png", dpi=180, bbox_inches="tight", facecolor="white")
    fig.savefig(output_dir / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _draw_metric(data: pd.DataFrame, values: pd.Series | None, title: str, ylabel: str,
                 stem: str, output_dir: Path, statistic: str = "mean", percent: bool = False) -> str | None:
    if values is None:
        print(f"WARNING: {title} skipped: required metric column is absent.")
        return None
    work = data.copy()
    work["__value"] = pd.to_numeric(values, errors="coerce")
    work = work.dropna(subset=["__value"])
    if work.empty:
        print(f"WARNING: {title} skipped: no valid numeric values.")
        return None

    pairs = _scheduler_backend_pairs(work)
    labels, vals, colors, hatches = [], [], [], []
    for scheduler, backend in pairs:
        subset = work[(work["scheduler"] == scheduler) & (work["backend"] == backend)]["__value"]
        if subset.empty:
            continue
        if statistic == "sum":
            value = float(subset.sum())
        elif statistic == "success_rate":
            value = float(subset.mean() * 100)
        else:
            value = float(subset.mean())
        labels.append(f"{scheduler}\n{_model_label(backend)}")
        vals.append(value)
        colors.append(SCHEDULER_COLORS.get(scheduler, SCHEDULER_COLORS["Unspecified"]))
        hatches.append("//" if backend in {"ollama", "real"} else "")

    if not vals:
        print(f"WARNING: {title} skipped: no group has usable values.")
        return None
    width = max(8.5, len(vals) * 1.25)
    fig, ax = plt.subplots(figsize=(width, 5.2))
    bars = ax.bar(range(len(vals)), vals, color=colors, edgecolor="#ffffff", linewidth=0.6)
    for bar, hatch in zip(bars, hatches):
        bar.set_hatch(hatch)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=14)
    ax.set_ylabel(ylabel)
    ax.set_xticks(range(len(labels)), labels, rotation=0, fontsize=9)
    ax.grid(axis="y", alpha=.25, linestyle="--")
    ax.set_axisbelow(True)
    if percent:
        ax.set_ylim(0, max(100, max(vals) * 1.12))
    for bar, value in zip(bars, vals):
        ax.annotate(f"{value:.1f}" if percent else f"{value:.3g}",
                    (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=8)
    fig.text(.99, .01, "Bars are coloured by scheduler; real-model runs use diagonal hatching.",
             ha="right", va="bottom", fontsize=8, color="#555555")
    _save(fig, output_dir, stem)
    return stem


def _run_makespans(data: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, group in data.groupby(["scheduler", "backend"], dropna=False):
        scheduler = str(group["scheduler"].iloc[0])
        backend = str(group["backend"].iloc[0])
        # Prefer explicit makespan summary columns when supplied.
        explicit = next((col for col in ("makespan_seconds", "makespan") if col in group.columns), None)
        if explicit:
            values = pd.to_numeric(group[explicit], errors="coerce").dropna()
            for index, value in enumerate(values):
                rows.append({"scheduler": scheduler, "backend": backend, "makespan": float(value),
                             "run_id": f"explicit-{index}"})
            continue
        if {"start_time", "end_time"}.issubset(group.columns):
            start_column = "start_time" if "start_time" in group.columns else "arrival_time"
            starts = pd.to_datetime(group[start_column], errors="coerce", utc=True)
            ends = pd.to_datetime(group["end_time"], errors="coerce", utc=True)
            valid = starts.notna() & ends.notna()
            if valid.any():
                rows.append({"scheduler": scheduler, "backend": backend,
                             "makespan": float((ends[valid].max() - starts[valid].min()).total_seconds()),
                             "run_id": str(group.get("task_id", pd.Series(["run"])).iloc[0])})
            continue
        if {"start", "end"}.issubset(group.columns):
            end = pd.to_numeric(group["end"], errors="coerce")
            start_col = "start" if "start" in group.columns else "arrival"
            start = pd.to_numeric(group[start_col], errors="coerce")
            valid = end.notna() & start.notna()
            if valid.any():
                if "seed" in group.columns or "workload" in group.columns:
                    keys = [key for key in ("seed", "workload", "experiment") if key in group.columns]
                    for run_key, run_group in group[valid].groupby(keys, dropna=False):
                        e = pd.to_numeric(run_group["end"], errors="coerce")
                        s = pd.to_numeric(run_group[start_col], errors="coerce")
                        rows.append({"scheduler": scheduler, "backend": backend,
                                     "makespan": float(e.max() - s.min()), "run_id": str(run_key)})
                else:
                    rows.append({"scheduler": scheduler, "backend": backend,
                                 "makespan": float(end[valid].max() - start[valid].min()), "run_id": "run"})
    return pd.DataFrame(rows)


def _success_values(data: pd.DataFrame) -> pd.Series | None:
    result = pd.Series(np.nan, index=data.index, dtype="float64")
    found = False
    for column in ("deadline_met", "success", "task_success"):
        if column not in data.columns:
            continue
        found = True
        series = data[column]
        if series.dtype == object:
            mapped = series.astype(str).str.strip().str.lower().map({
                "true": 1.0, "false": 0.0, "yes": 1.0, "no": 0.0, "1": 1.0, "0": 0.0,
            })
            numeric = pd.to_numeric(series, errors="coerce")
            parsed = mapped.where(mapped.notna(), numeric)
        else:
            parsed = pd.to_numeric(series, errors="coerce")
        result = result.where(result.notna(), parsed)
    if "status" in data.columns:
        found = True
        from_status = data["status"].astype(str).str.lower().isin(
            {"done", "completed", "success", "succeeded"}
        ).astype(float)
        result = result.where(result.notna(), from_status)
    return result if found else None


def _token_values(data: pd.DataFrame) -> pd.Series | None:
    result = pd.Series(np.nan, index=data.index, dtype="float64")
    found = False
    for column in ("tokens", "tokens_used", "token_count"):
        if column in data.columns:
            found = True
            parsed = pd.to_numeric(data[column], errors="coerce")
            result = result.where(result.notna(), parsed)
    return result if found else None


def _write_summary(data: pd.DataFrame, latency_col: str | None, summary_csv: Path, summary_md: Path) -> list[dict[str, Any]]:
    rows = []
    if latency_col is None:
        print("WARNING: summary latency statistics unavailable because no latency column could be derived.")
    else:
        work = data.copy()
        work["__latency"] = pd.to_numeric(work[latency_col], errors="coerce")
        work = work.dropna(subset=["__latency"])
        for (scheduler, backend), group in work.groupby(["scheduler", "backend"], dropna=False):
            values = group["__latency"].astype(float).tolist()
            if not values:
                continue
            row = {
                "backend": backend, "scheduler": scheduler, "task_count": len(values),
                "mean_latency_seconds": statistics.mean(values),
                "p50_latency_seconds": float(np.percentile(values, 50)),
                "p95_latency_seconds": float(np.percentile(values, 95, method="higher")),
            }
            rows.append(row)
    makespans = _run_makespans(data)
    for row in rows:
        subset = makespans[(makespans["scheduler"] == row["scheduler"]) &
                           (makespans["backend"] == row["backend"])] if not makespans.empty else pd.DataFrame()
        row["makespan_seconds"] = float(subset["makespan"].mean()) if not subset.empty else ""
        success = _success_values(data)
        if success is not None:
            tmp = data.copy()
            tmp["__success"] = pd.to_numeric(success, errors="coerce")
            tmp = tmp[(tmp["scheduler"] == row["scheduler"]) & (tmp["backend"] == row["backend"])]
            row["success_rate_percent"] = round(float(tmp["__success"].mean() * 100), 4) if tmp["__success"].notna().any() else ""
        else:
            row["success_rate_percent"] = ""
        token_values = _token_values(data)
        if token_values is not None:
            mask = (data["scheduler"] == row["scheduler"]) & (data["backend"] == row["backend"])
            row["tokens_total"] = float(token_values[mask].fillna(0).sum())
        else:
            row["tokens_total"] = ""
    summary_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = ["backend", "scheduler", "task_count", "mean_latency_seconds", "p50_latency_seconds",
              "p95_latency_seconds", "makespan_seconds", "success_rate_percent", "tokens_total"]
    with summary_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: (round(value, 6) if isinstance(value, float) else value) for key, value in row.items()})
    lines = [
        "# AgentOS scheduler summary", "",
        "Statistics are calculated from the selected raw task rows. Latency is in seconds; blank metrics mean the source CSV does not contain enough information to calculate them.", "",
        "| Backend | Scheduler | Tasks | Mean latency (s) | p50 latency (s) | p95 latency (s) | Makespan (s) | Success rate (%) | Tokens |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        def fmt(key):
            value = row.get(key, "")
            return f"{value:.4f}" if isinstance(value, (int, float)) and value != "" else (str(value) if value != "" else "—")
        lines.append("| " + " | ".join([str(row["backend"]), str(row["scheduler"]), str(row["task_count"]),
                    fmt("mean_latency_seconds"), fmt("p50_latency_seconds"), fmt("p95_latency_seconds"),
                    fmt("makespan_seconds"), fmt("success_rate_percent"), fmt("tokens_total")]) + " |")
    summary_md.parent.mkdir(parents=True, exist_ok=True)
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows


def _sanity_checks(data: pd.DataFrame, loaded_files: list[Path], latency_col: str | None) -> list[str]:
    notes = []
    if latency_col:
        work = data.copy()
        work["__latency"] = pd.to_numeric(work[latency_col], errors="coerce")
        for (scheduler, backend), group in work.groupby(["scheduler", "backend"], dropna=False):
            values = group["__latency"].dropna()
            if len(values) and np.percentile(values, 95, method="higher") + 1e-9 < np.percentile(values, 50):
                notes.append(f"ERROR: p95 latency is below p50 for {scheduler}/{backend}.")

    # Compare task identity and workload-defining fields across schedulers,
    # excluding "Unspecified" rows that have no scheduler assignment.
    if "task_id" in data.columns:
        id_sets = {}
        groups = {}
        for (backend, scheduler), group in data.groupby(["backend", "scheduler"], dropna=False):
            if str(scheduler) == "Unspecified":
                continue
            ids = set(group["task_id"].dropna().astype(str))
            if ids:
                id_sets[(str(backend), str(scheduler))] = ids
                groups[(str(backend), str(scheduler))] = group
        workload_candidates = [
            "task_kind", "agent_type", "agent", "priority", "complexity", "risk_level",
            "estimated_tokens", "arrival_offset_seconds", "deadline_seconds", "workload",
            "seed", "arrival", "deadline", "prompt",
        ]
        workload_columns = [column for column in workload_candidates if column in data.columns]
        key_columns = ["task_id"] + [column for column in ("seed", "workload", "experiment") if column in data.columns]
        compare_columns = [column for column in workload_columns if column not in key_columns]
        for backend in sorted({key[0] for key in id_sets}):
            scheduler_names = sorted(scheduler for (b, scheduler) in id_sets if b == backend)
            if len(scheduler_names) < 2:
                continue
            reference_scheduler = scheduler_names[0]
            reference_ids = id_sets[(backend, reference_scheduler)]
            reference_group = groups[(backend, reference_scheduler)]
            for scheduler in scheduler_names[1:]:
                ids = id_sets[(backend, scheduler)]
                current_group = groups[(backend, scheduler)]
                if ids != reference_ids:
                    notes.append(
                        f"WARNING: task IDs differ for backend {backend}: {reference_scheduler} has "
                        f"{len(reference_ids)}, {scheduler} has {len(ids)}; intersection={len(reference_ids & ids)}."
                    )
                if compare_columns:
                    left = reference_group[key_columns + compare_columns].drop_duplicates(key_columns).set_index(key_columns).sort_index()
                    right = current_group[key_columns + compare_columns].drop_duplicates(key_columns).set_index(key_columns).sort_index()
                    common = left.index.intersection(right.index)
                    if len(common):
                        left_values = left.loc[common, compare_columns].astype("string").fillna("<NA>")
                        right_values = right.loc[common, compare_columns].astype("string").fillna("<NA>")
                        mismatched_rows = (left_values != right_values).any(axis=1)
                        if mismatched_rows.any():
                            changed_fields = [
                                column for column in compare_columns
                                if (left_values[column] != right_values[column]).any()
                            ]
                            notes.append(
                                f"WARNING: workload fields differ for backend {backend}, "
                                f"{reference_scheduler} vs {scheduler}, on {int(mismatched_rows.sum())} "
                                f"matching task key(s): {', '.join(changed_fields)}."
                            )
    if not notes:
        notes.append("PASS: p95 latency is not below p50 for any available group; task IDs and workload-defining fields are consistent wherever multiple schedulers were available.")
    notes.insert(0, f"Input files loaded: {len(loaded_files)}")
    notes.extend([
        "", "Workload comparability must be interpreted within each backend. Different model backends can have different execution semantics.",
        "CPU/RAM samples are not treated as per-task attribution unless the source explicitly provides them.",
    ])
    return notes


def _plot_blocked(security_csv: Path, output_dir: Path) -> str | None:
    if not security_csv.exists():
        print(f"WARNING: security comparison skipped; file not found: {security_csv}")
        return None
    try:
        data = pd.read_csv(security_csv)
    except Exception as exc:
        print(f"WARNING: could not read security CSV: {exc}")
        return None
    required = {"policy_enabled", "blocked"}
    if not required.issubset(data.columns):
        print(f"WARNING: security comparison skipped; required columns are {sorted(required)}.")
        return None
    def boolean_series(series):
        if series.dtype == object:
            return series.astype(str).str.strip().str.lower().map({"true": True, "false": False, "1": True, "0": False, "yes": True, "no": False})
        return series.astype("boolean")
    data["__policy"] = boolean_series(data["policy_enabled"])
    data["__blocked"] = boolean_series(data["blocked"])
    data = data.dropna(subset=["__policy", "__blocked"])
    if data.empty:
        print("WARNING: security comparison skipped; no parseable policy data.")
        return None
    counts = data.groupby(["__policy", "__blocked"]).size()
    labels = ["Policy disabled", "Policy enabled"]
    blocked_counts = [int(counts.get((False, True), 0)), int(counts.get((True, True), 0))]
    not_blocked = [int(counts.get((False, False), 0)), int(counts.get((True, False), 0))]
    x = np.arange(2)
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.bar(x, not_blocked, label="Not blocked", color="#E0A458")
    ax.bar(x, blocked_counts, bottom=not_blocked, label="Blocked", color="#3A9D77")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Unsafe actions recorded (count)")
    ax.set_title("Policy ablation: blocked vs unblocked unsafe actions", fontsize=13, fontweight="bold", pad=14)
    ax.grid(axis="y", alpha=.25, linestyle="--")
    ax.set_axisbelow(True)
    ax.legend(frameon=False)
    for i, (nb, bl) in enumerate(zip(not_blocked, blocked_counts)):
        ax.text(i, nb + bl + .15, f"{nb + bl} attempted", ha="center", fontsize=9)
    fig.text(.99, .01, "Counts are taken from the supplied security attack/ablation CSV.", ha="right", fontsize=8, color="#555")
    _save(fig, output_dir, "blocked_actions")
    return "blocked_actions"


def _plot_cdf(data: pd.DataFrame, latency_col: str | None, output_dir: Path) -> str | None:
    if latency_col is None:
        return None
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    drawn = False
    for scheduler in SCHEDULER_ORDER + sorted(set(data["scheduler"].astype(str)) - set(SCHEDULER_ORDER)):
        group = data[data["scheduler"] == scheduler]
        for backend in sorted(group["backend"].dropna().astype(str).unique()):
            values = pd.to_numeric(group.loc[group["backend"] == backend, latency_col], errors="coerce").dropna().sort_values().to_numpy()
            if not len(values):
                continue
            y = np.arange(1, len(values) + 1) / len(values)
            ax.plot(values, y, label=f"{scheduler} · {_model_label(backend)}",
                    color=SCHEDULER_COLORS.get(scheduler, SCHEDULER_COLORS["Unspecified"]), linewidth=2,
                    linestyle="--" if backend in {"ollama", "real"} else "-")
            drawn = True
    if not drawn:
        plt.close(fig)
        return None
    ax.set_title("Latency cumulative distribution (CDF)", fontsize=13, fontweight="bold", pad=14)
    ax.set_xlabel("Latency (seconds)")
    ax.set_ylabel("Cumulative probability")
    ax.set_ylim(0, 1.02)
    ax.grid(alpha=.25, linestyle="--")
    ax.legend(frameon=False, fontsize=8)
    _save(fig, output_dir, "latency_cdf")
    return "latency_cdf"


def main() -> int:
    args = parse_args()
    try:
        data, loaded = _read_input(args.input)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    latency_col = _latency_column(data)
    if latency_col:
        latency = pd.to_numeric(data[latency_col], errors="coerce")
        p50_values = latency.groupby([data["scheduler"], data["backend"]]).transform(lambda values: values.quantile(.50))
        p95_values = latency.groupby([data["scheduler"], data["backend"]]).transform(lambda values: values.quantile(.95, interpolation="higher"))
        _draw_metric(data, p50_values, "p50 task latency", "Latency (seconds)", "latency_p50", args.output_dir)
        _draw_metric(data, p95_values, "p95 task latency", "Latency (seconds)", "latency_p95", args.output_dir)
    else:
        print("WARNING: latency charts skipped: no supported latency columns found.")

    makespans = _run_makespans(data)
    if not makespans.empty:
        _draw_metric(makespans, makespans["makespan"], "Run makespan", "Makespan (seconds)",
                     "makespan", args.output_dir, statistic="mean")
    else:
        print("WARNING: makespan chart skipped: no supported run boundary data found.")

    _draw_metric(data, _token_values(data),
                 "Token usage", "Tokens (count)", "tokens", args.output_dir, statistic="sum")

    success = _success_values(data)
    _draw_metric(data, success, "Task success rate", "Success rate (%)",
                 "success_rate", args.output_dir, statistic="success_rate", percent=True)

    _plot_blocked(args.security_csv, args.output_dir)
    if args.cdf:
        if _plot_cdf(data, latency_col, args.output_dir) is None:
            print("WARNING: latency CDF skipped: no usable latency values.")

    summary_rows = _write_summary(data, latency_col, args.summary_csv, args.summary_md)
    notes = _sanity_checks(data, loaded, latency_col)
    args.validation_md.parent.mkdir(parents=True, exist_ok=True)
    args.validation_md.write_text("# Benchmark sanity checks\n\n" + "\n".join(f"- {note}" for note in notes) + "\n", encoding="utf-8")

    print(f"Loaded {len(data)} task rows from {len(loaded)} CSV file(s).")
    print(f"Figures: {args.output_dir}")
    print(f"Summary CSV: {args.summary_csv}")
    print(f"Summary Markdown: {args.summary_md}")
    print(f"Validation report: {args.validation_md}")
    print(f"Summary groups: {len(summary_rows)}")
    if any(note.startswith("ERROR:") for note in notes):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
