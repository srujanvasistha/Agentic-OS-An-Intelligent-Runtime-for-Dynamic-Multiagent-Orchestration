# Day 5 Validation Report

Date: 2026-10-08

## Automated tests

```text
53 passed in 0.62s
```

## MockLLM workload

```text
5 tasks completed
CSV schema validated against backend/results_csv.py::RESULT_COLUMNS
```

Output: `experiments/day5_mock_workload.csv`

## Failure paths

```text
malformed task: PASS
model timeout: PASS
denied action: PASS
Ollama unavailable: PASS
All Day 5 failure paths passed.
```

## End-to-end shell smoke test

The `shell/cli.py` client was run against a live Uvicorn instance with MockLLM enabled. The shell submitted a task to `/api/task` and received a `done` `TaskResult` from the integrated runtime.

## Freeze status

The Day 5 v1 feature set is frozen. The real Git repository should be tagged `v1-freeze` after merging the Day 5 branch into `main` and confirming the final CI/test result.
