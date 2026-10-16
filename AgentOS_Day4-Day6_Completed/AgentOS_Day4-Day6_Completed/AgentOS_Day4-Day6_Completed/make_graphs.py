#!/usr/bin/env python3
"""Generate reproducible AgentOS scheduler figures from an experiment CSV.

Usage:
    python make_graphs.py results.csv
    python make_graphs.py experiments/simulated_results.csv --output-dir results/figures

Supports the task-level schema described in the project brief and the repository's
current simulation schema (scheduler/start/end/tokens/deadline_met/workload/seed).
Missing measurements are never fabricated: unavailable figures are emitted with
an explanatory note, and a warning is printed.
"""
from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCHEDULER_ORDER = ["FIFO", "RR", "Priority", "AgentOS"]
SCHEDULER_ALIASES = {
    "fifo": "FIFO",
    "rr": "RR",
    "roundrobin": "RR",
    "round_robin": "RR",
    "round-robin": "RR",
    "priority": "Priority",
    "agentos": "AgentOS",
    "resourceaware": "AgentOS",
    "resource_aware": "AgentOS",
    "resource-aware": "AgentOS",
    "agentos_scheduler": "AgentOS",
}
COLORS = {"FIFO": "#4477AA", "RR": "#EE9944", "Priority": "#228833", "AgentOS": "#AA3377"}
HATCHES = {"FIFO": "///", "RR": "\\\\", "Priority": "xx", "AgentOS": ".."}
REQUIRED_BRIEF_COLUMNS = {
    "task_id", "scheduler", "task_type", "submit_ts", "start_ts", "end_ts",
    "latency", "tokens", "success", "blocked", "model",
}
TRIAL_COLUMNS = ["workload", "seed", "trial", "run_id", "experiment"]


def _truthy(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float)) and not math.isnan(float(value)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "success", "succeeded", "completed", "ok", "passed"}


def _number(value: Any) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else float("nan")
    except (TypeError, ValueError):
        # Accept ISO-8601 timestamps as well as numeric seconds/epoch values.
        try:
            stamp = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=__import__("datetime").timezone.utc)
            return stamp.timestamp()
        except (TypeError, ValueError, OverflowError):
            return float("nan")


def _normalise_scheduler(value: Any) -> str:
    key = re.sub(r"\s+", "", str(value).strip()).lower()
    return SCHEDULER_ALIASES.get(key, str(value).strip())


def read_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Input CSV does not exist: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"CSV contains no data rows: {path}")
    return reader.fieldnames, rows


def normalise_rows(rows: list[dict[str, Any]], columns: list[str], *, warn_missing_schema: bool = True):
    colset = set(columns)
    missing = sorted(REQUIRED_BRIEF_COLUMNS - colset)
    if missing and warn_missing_schema:
        print("NOTE: CSV does not use the full task-level schema; missing columns: " + ", ".join(missing), file=sys.stderr)
        print("      The script will use compatible repository fields where possible and will not invent unavailable measurements.", file=sys.stderr)

    out = []
    for raw in rows:
        row = dict(raw)
        scheduler_raw = row.get("scheduler", "")
        scheduler = _normalise_scheduler(scheduler_raw) if str(scheduler_raw).strip() else ""
        if not scheduler:
            # The runtime results.csv is useful for model/backend checks but has no scheduler comparison.
            scheduler = ""
        start = _number(row.get("start_ts", row.get("start", float("nan"))))
        end = _number(row.get("end_ts", row.get("end", float("nan"))))
        latency = _number(row.get("latency", row.get("latency_seconds", float("nan"))))
        if not math.isfinite(latency) and math.isfinite(start) and math.isfinite(end):
            latency = max(0.0, end - start)
        submit = _number(row.get("submit_ts", row.get("arrival", float("nan"))))
        tokens = _number(row.get("tokens", row.get("tokens_used", float("nan"))))
        success_field = row.get("success", row.get("status", ""))
        success_available = str(success_field).strip() != ""
        success = _truthy(success_field) if success_available else None
        deadline_field = row.get("deadline_met", "")
        deadline_available = str(deadline_field).strip() != ""
        deadline_met = _truthy(deadline_field) if deadline_available else None
        blocked_field = row.get("blocked", row.get("unsafe_action_blocked", ""))
        blocked_available = str(blocked_field).strip() != ""
        blocked = _truthy(blocked_field) if blocked_available else None
        model_name = str(row.get("model", "") or "").strip()
        backend_name = str(row.get("llm_backend", row.get("backend", "")) or "").strip()
        if model_name and backend_name and backend_name.lower() not in model_name.lower():
            model = f"{model_name} / {backend_name} backend"
        else:
            model = model_name or backend_name
        if not model:
            model = "Simulation (no LLM inference)" if "start" in colset and "end" in colset else "Model/backend not recorded"
        policy_raw = row.get("policy_enabled", row.get("policy_enforcement", row.get("policy", "")))
        policy = None
        if str(policy_raw).strip():
            p = str(policy_raw).strip().lower()
            if p in {"0", "false", "no", "off", "disabled", "without", "none"}:
                policy = "Without policy"
            elif p in {"1", "true", "yes", "on", "enabled", "with", "enforced"}:
                policy = "With policy"
            elif "without" in p or "disabled" in p or "off" == p:
                policy = "Without policy"
            elif "with" in p or "enabled" in p or "enforced" in p:
                policy = "With policy"
        out.append({
            **row, "_scheduler": scheduler, "_start": start, "_end": end,
            "_submit": submit, "_latency": latency, "_tokens": tokens,
            "_success": success, "_success_available": success_available,
            "_deadline_met": deadline_met, "_deadline_available": deadline_available,
            "_blocked": blocked, "_blocked_available": blocked_available,
            "_model": model, "_policy_group": policy,
        })
    return out


def configure_plot():
    plt.rcParams.update({
        "figure.figsize": (8.4, 5.0), "figure.dpi": 120,
        "savefig.dpi": 300, "font.size": 10, "axes.titlesize": 12,
        "axes.labelsize": 10, "legend.fontsize": 9,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.alpha": 0.25, "grid.linestyle": "--",
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })


def save_figure(fig, output_dir: Path, stem: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(output_dir / f"{stem}.{ext}", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def annotate_model(ax, rows):
    labels = sorted({r["_model"] for r in rows if r["_model"]})
    label = "Model/backend: " + (", ".join(labels) if labels else "not recorded")
    ax.text(0.99, 1.015, label, transform=ax.transAxes, ha="right", va="bottom", fontsize=7.5,
            clip_on=False, bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "edgecolor": "0.75", "alpha": 0.9})


def available_schedulers(rows):
    present = {r["_scheduler"] for r in rows if r["_scheduler"]}
    return [name for name in SCHEDULER_ORDER if name in present] + sorted(present - set(SCHEDULER_ORDER))


def _bar_style(bars, scheduler):
    for bar in bars:
        bar.set_facecolor(COLORS.get(scheduler, "#777777"))
        bar.set_edgecolor("black")
        bar.set_linewidth(0.8)
        bar.set_hatch(HATCHES.get(scheduler, "++"))


def unavailable_figure(title: str, message: str, output_dir: Path, stem: str, rows):
    fig, ax = plt.subplots()
    ax.axis("off")
    ax.set_title(title, pad=18)
    ax.text(0.5, 0.55, message, ha="center", va="center", wrap=True, fontsize=11,
            bbox={"boxstyle": "round,pad=0.8", "facecolor": "#f2f2f2", "edgecolor": "#777777"})
    ax.text(0.5, 0.18, "No values are fabricated. Supply the required measurement column(s) to populate this figure.",
            ha="center", va="center", fontsize=8)
    save_figure(fig, output_dir, stem)


def plot_latency(rows, output_dir):
    valid = [r for r in rows if r["_scheduler"] and math.isfinite(r["_latency"]) and r["_latency"] >= 0]
    schedulers = [s for s in available_schedulers(valid) if any(r["_scheduler"] == s for r in valid)]
    if not valid or not schedulers:
        unavailable_figure("Latency by scheduler", "Latency data or scheduler labels are missing.", output_dir, "01_latency_p50_p95", rows)
        return
    p50 = [float(np.percentile([r["_latency"] for r in valid if r["_scheduler"] == s], 50)) for s in schedulers]
    p95 = [float(np.percentile([r["_latency"] for r in valid if r["_scheduler"] == s], 95)) for s in schedulers]
    x = np.arange(len(schedulers)); width = 0.36
    fig, ax = plt.subplots()
    b1 = ax.bar(x - width / 2, p50, width, label="p50", color="#4477AA", edgecolor="black", hatch="///")
    b2 = ax.bar(x + width / 2, p95, width, label="p95", color="#EE9944", edgecolor="black", hatch="xx")
    ax.set_xticks(x, schedulers); ax.set_ylabel("Latency (seconds)"); ax.set_xlabel("Scheduler")
    ax.set_title("p50 and p95 task latency by scheduler"); ax.legend(frameon=True)
    ax.bar_label(b1, fmt="%.3g", padding=2, fontsize=8); ax.bar_label(b2, fmt="%.3g", padding=2, fontsize=8)
    annotate_model(ax, valid); fig.tight_layout(); save_figure(fig, output_dir, "01_latency_p50_p95")


def trial_groups(rows):
    # Use available trial dimensions so each workload/seed contributes one makespan.
    dimensions = [c for c in TRIAL_COLUMNS if any(str(r.get(c, "")).strip() for r in rows)]
    groups = {}
    for r in rows:
        if not r["_scheduler"] or not math.isfinite(r["_start"]) or not math.isfinite(r["_end"]):
            continue
        key = (r["_scheduler"],) + tuple(str(r.get(c, "")) for c in dimensions)
        groups.setdefault(key, []).append(r)
    summaries = []
    for key, items in groups.items():
        starts = [r["_start"] for r in items]; ends = [r["_end"] for r in items]
        summaries.append({"scheduler": key[0], "makespan": max(ends) - min(starts), "items": items})
    return summaries


def plot_makespan(rows, output_dir):
    summaries = trial_groups(rows)
    schedulers = [s for s in SCHEDULER_ORDER if any(x["scheduler"] == s for x in summaries)]
    schedulers += sorted({x["scheduler"] for x in summaries} - set(schedulers))
    if not summaries or not schedulers:
        unavailable_figure("Makespan by scheduler", "Start/end timestamps are required to calculate makespan.", output_dir, "02_makespan", rows)
        return
    means = [float(np.mean([x["makespan"] for x in summaries if x["scheduler"] == s])) for s in schedulers]
    stds = [float(np.std([x["makespan"] for x in summaries if x["scheduler"] == s], ddof=1)) if sum(x["scheduler"] == s for x in summaries) > 1 else 0 for s in schedulers]
    fig, ax = plt.subplots(); bars = ax.bar(schedulers, means, yerr=stds, capsize=4)
    for bar, scheduler in zip(bars, schedulers): _bar_style([bar], scheduler)
    ax.set_ylabel("Makespan (seconds)"); ax.set_xlabel("Scheduler"); ax.set_title("Mean makespan by scheduler (error bars: ±1 SD)")
    ax.bar_label(bars, fmt="%.3g", padding=3, fontsize=8); annotate_model(ax, rows)
    fig.tight_layout(); save_figure(fig, output_dir, "02_makespan")


def plot_tokens(rows, output_dir):
    valid = [r for r in rows if r["_scheduler"] and math.isfinite(r["_tokens"]) and r["_tokens"] >= 0]
    schedulers = [s for s in SCHEDULER_ORDER if any(r["_scheduler"] == s for r in valid)]
    schedulers += sorted({r["_scheduler"] for r in valid} - set(schedulers))
    if not valid or not schedulers:
        unavailable_figure("Token usage by scheduler", "A numeric tokens or tokens_used column is required.", output_dir, "03_token_usage", rows)
        return
    totals = [sum(r["_tokens"] for r in valid if r["_scheduler"] == s) for s in schedulers]
    fig, ax = plt.subplots(); bars = ax.bar(schedulers, totals)
    for bar, scheduler in zip(bars, schedulers): _bar_style([bar], scheduler)
    ax.set_ylabel("Estimated tokens (tokens)"); ax.set_xlabel("Scheduler"); ax.set_title("Total estimated token budget by scheduler")
    ax.bar_label(bars, labels=[f"{v:,.0f}" for v in totals], padding=3, fontsize=8); annotate_model(ax, valid)
    fig.tight_layout(); save_figure(fig, output_dir, "03_token_usage")


def plot_success(rows, output_dir):
    """Plot task execution success only when the input explicitly records it."""
    valid = [r for r in rows if r["_scheduler"] and r["_success_available"]]
    schedulers = [s for s in SCHEDULER_ORDER if any(r["_scheduler"] == s for r in valid)]
    schedulers += sorted({r["_scheduler"] for r in valid} - set(schedulers))
    if not valid or not schedulers:
        unavailable_figure(
            "Task execution success rate by scheduler",
            "Task execution success is not recorded in this dataset. The scheduler simulation models queueing and completion timing, not actual agent-task execution.",
            output_dir, "04_task_success_rate", rows,
        )
        print("NOTE: task execution success is unavailable; wrote an explicit placeholder instead of treating deadline success as task success.", file=sys.stderr)
        return
    rates = []
    for scheduler in schedulers:
        selected = [r for r in valid if r["_scheduler"] == scheduler]
        values = [r["_success"] for r in selected if r["_success"] is not None]
        rates.append(100 * sum(bool(v) for v in values) / len(values) if values else float("nan"))
    fig, ax = plt.subplots(); bars = ax.bar(schedulers, rates)
    for bar, scheduler in zip(bars, schedulers): _bar_style([bar], scheduler)
    ax.set_ylim(0, 105); ax.set_ylabel("Task execution success rate (%)")
    ax.set_xlabel("Scheduler"); ax.set_title("Task execution success rate by scheduler")
    ax.bar_label(bars, labels=["N/A" if not math.isfinite(v) else f"{v:.1f}%" for v in rates], padding=3, fontsize=8)
    annotate_model(ax, valid); fig.tight_layout(); save_figure(fig, output_dir, "04_task_success_rate")


def plot_deadline_success(rows, output_dir):
    """Plot deadline attainment separately from task execution success."""
    valid = [r for r in rows if r["_scheduler"] and r["_deadline_available"]]
    schedulers = [s for s in SCHEDULER_ORDER if any(r["_scheduler"] == s for r in valid)]
    schedulers += sorted({r["_scheduler"] for r in valid} - set(schedulers))
    if not valid or not schedulers:
        unavailable_figure("Deadline success rate by scheduler", "A deadline_met measurement is required.", output_dir, "05_deadline_success_rate", rows)
        return
    rates = []
    for scheduler in schedulers:
        selected = [r for r in valid if r["_scheduler"] == scheduler]
        values = [r["_deadline_met"] for r in selected if r["_deadline_met"] is not None]
        rates.append(100 * sum(bool(v) for v in values) / len(values) if values else float("nan"))
    fig, ax = plt.subplots(); bars = ax.bar(schedulers, rates)
    for bar, scheduler in zip(bars, schedulers): _bar_style([bar], scheduler)
    ax.set_ylim(0, 105); ax.set_ylabel("Deadline attainment rate (%)")
    ax.set_xlabel("Scheduler"); ax.set_title("Deadline success rate by scheduler")
    ax.bar_label(bars, labels=["N/A" if not math.isfinite(v) else f"{v:.1f}%" for v in rates], padding=3, fontsize=8)
    annotate_model(ax, valid); fig.tight_layout(); save_figure(fig, output_dir, "05_deadline_success_rate")


def plot_blocked(rows, output_dir):
    # A valid policy ablation needs explicit policy condition and blocked-action data.
    valid = [r for r in rows if r["_blocked_available"] and r["_policy_group"] in {"With policy", "Without policy"}]
    conditions = ["Without policy", "With policy"]
    if not valid or not all(any(r["_policy_group"] == c for r in valid) for c in conditions):
        unavailable_figure(
            "Unsafe actions blocked: policy ablation",
            "Policy-ablation data not found. Include a policy condition (e.g. policy_enabled) and a blocked/unsafe_action_blocked column with both policy-on and policy-off attack runs.",
            output_dir, "06_unsafe_actions_blocked", rows,
        )
        print("WARNING: blocked-action comparison needs both with-policy and without-policy ablation rows; generated an explicit placeholder rather than inventing results.", file=sys.stderr)
        return
    values = [sum(1 for r in valid if r["_policy_group"] == c and _truthy(r["_blocked"])) for c in conditions]
    fig, ax = plt.subplots(); bars = ax.bar(conditions, values, color=["#999999", "#228833"], edgecolor="black", hatch=["///", "xx"])
    ax.set_ylabel("Unsafe actions blocked (count)"); ax.set_xlabel("Policy enforcement")
    ax.set_title("Unsafe actions blocked with vs without policy enforcement")
    ax.bar_label(bars, fmt="%.0f", padding=3); annotate_model(ax, valid)
    fig.tight_layout(); save_figure(fig, output_dir, "06_unsafe_actions_blocked")


def plot_latency_cdf(rows, output_dir):
    valid = [r for r in rows if r["_scheduler"] and math.isfinite(r["_latency"]) and r["_latency"] >= 0]
    schedulers = [s for s in SCHEDULER_ORDER if any(r["_scheduler"] == s for r in valid)]
    schedulers += sorted({r["_scheduler"] for r in valid} - set(schedulers))
    if not valid or not schedulers:
        unavailable_figure("Task latency CDF", "Latency data and scheduler labels are required.", output_dir, "07_latency_cdf", rows)
        return
    fig, ax = plt.subplots()
    for s in schedulers:
        values = np.sort([r["_latency"] for r in valid if r["_scheduler"] == s])
        y = np.arange(1, len(values) + 1) / len(values)
        ax.step(values, y, where="post", label=s, color=COLORS.get(s, "#777777"), linestyle={"FIFO": "-", "RR": "--", "Priority": ":", "AgentOS": "-."}.get(s, "-"), linewidth=2)
    ax.set_xlabel("Task latency (seconds)"); ax.set_ylabel("Cumulative probability"); ax.set_ylim(0, 1.02)
    ax.set_title("Empirical task latency CDF"); ax.legend(title="Scheduler")
    annotate_model(ax, valid); fig.tight_layout(); save_figure(fig, output_dir, "07_latency_cdf")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", type=Path, help="Experiment CSV file")
    parser.add_argument("--output-dir", type=Path, default=Path("results/figures"), help="Output directory (default: results/figures)")
    parser.add_argument("--no-cdf", action="store_true", help="Skip optional latency CDF figure")
    parser.add_argument("--security-csv", type=Path, default=None,
                        help="Optional separate policy-ablation CSV; used only for the blocked-actions figure")
    args = parser.parse_args(argv)
    columns, raw_rows = read_csv(args.csv)
    if "scheduler" not in columns:
        raise ValueError(
            f"{args.csv} has no 'scheduler' column, so it cannot produce scheduler-comparison figures. "
            "Use experiments/simulated_results.csv for scheduler simulations, or provide a task-level "
            "experiment CSV with scheduler labels. Runtime telemetry such as experiments/results.csv "
            "is not a scheduler-comparison dataset."
        )
    rows = normalise_rows(raw_rows, columns)
    # The repository simulator also stores tuning and scheduler-weight ablations in the
    # detailed CSV. Keep those rows out of baseline comparisons so they do not bias AgentOS.
    comparison_rows = rows
    if "experiment" in columns:
        evaluation_rows = [r for r in rows if str(r.get("experiment", "")).strip().lower() in {"main", "held_out"}]
        if evaluation_rows:
            comparison_rows = evaluation_rows
            excluded = len(rows) - len(comparison_rows)
            if excluded:
                print(f"NOTE: scheduler figures use main/held_out evaluation rows only; excluded {excluded} tuning/ablation rows.", file=sys.stderr)
    configure_plot()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for plotter in [plot_latency, plot_makespan, plot_tokens, plot_success, plot_deadline_success]:
        plotter(comparison_rows, args.output_dir)
    # Keep security ablation separate from scheduler timing data when supplied.
    security_rows = rows
    if args.security_csv is not None:
        security_columns, security_raw = read_csv(args.security_csv)
        security_rows = normalise_rows(security_raw, security_columns, warn_missing_schema=False)
        print(f"Read {len(security_rows)} policy-ablation rows from {args.security_csv}")
    plot_blocked(security_rows, args.output_dir)
    if not args.no_cdf:
        plot_latency_cdf(comparison_rows, args.output_dir)
    print(f"Read {len(rows)} rows from {args.csv}")
    print(f"Wrote PNG and PDF figures to {args.output_dir.resolve()}")
    print("Figures: latency p50/p95, makespan, estimated token budget, task execution success (when measured), deadline success, policy-ablation blocked actions" + ("." if args.no_cdf else ", latency CDF."))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
