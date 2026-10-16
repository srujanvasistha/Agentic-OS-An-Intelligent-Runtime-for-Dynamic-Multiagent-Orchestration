"""Day 5 figure generation smoke tests against the checked-in mock-LLM runs."""
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_graph_script_generates_required_png_pdf_and_summary(tmp_path):
    figures = tmp_path / "figures"
    summary_csv = tmp_path / "summary.csv"
    summary_md = tmp_path / "summary.md"
    validation = tmp_path / "validation.md"
    command = [
        sys.executable, str(ROOT / "scripts" / "make_graphs.py"),
        "--input", str(ROOT / "experiments" / "day5" / "mock"),
        "--security-csv", str(ROOT / "experiments" / "security_attack_results.csv"),
        "--output-dir", str(figures),
        "--summary-csv", str(summary_csv),
        "--summary-md", str(summary_md),
        "--validation-md", str(validation),
        "--cdf",
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    for stem in ("latency_p50", "latency_p95", "makespan", "tokens", "success_rate", "blocked_actions", "latency_cdf"):
        assert (figures / f"{stem}.png").is_file()
        assert (figures / f"{stem}.pdf").is_file()
    assert summary_csv.is_file()
    assert summary_md.is_file()
    assert validation.is_file()


def test_day5_summary_quantiles_match_raw_mock_csv(tmp_path):
    command = [
        sys.executable, str(ROOT / "scripts" / "make_graphs.py"),
        "--input", str(ROOT / "experiments" / "day5" / "mock"),
        "--output-dir", str(tmp_path / "figures"),
        "--summary-csv", str(tmp_path / "summary.csv"),
        "--summary-md", str(tmp_path / "summary.md"),
        "--validation-md", str(tmp_path / "validation.md"),
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    with (tmp_path / "summary.csv").open(newline="", encoding="utf-8") as handle:
        rows = {row["scheduler"]: row for row in csv.DictReader(handle)}
    assert set(rows) == {"FIFO", "RoundRobin", "Priority", "ResourceAware"}
    assert float(rows["FIFO"]["p95_latency_seconds"]) >= float(rows["FIFO"]["p50_latency_seconds"])
    assert float(rows["FIFO"]["p95_latency_seconds"]) == 15.979
    assert float(rows["FIFO"]["makespan_seconds"]) == 18.072622
