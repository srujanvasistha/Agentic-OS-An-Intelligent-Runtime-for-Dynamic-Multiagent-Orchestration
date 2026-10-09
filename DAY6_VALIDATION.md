# Day 6 Validation Record

Validation run in the available Python 3.13 Linux validation environment from the Day 5 baseline after the Day 6 changes.

- Full automated tests: **58 passed**.
- Day 5 MockLLM workload: **5/5 tasks completed**; CSV schema validated.
- Failure paths: malformed task **PASS**; model timeout **PASS**; denied action **PASS**; Ollama unavailable **PASS**.
- Day 6 soak: **1,000/1,000 tasks completed** with seed `42`.
- Bounded state after soak: task history **100/100**, runtime memory **50/50**.
- Results CSV: **1,000 rows** matching the frozen schema.
- Python allocation trace during soak: current **2456.9 KiB**, peak **2612.3 KiB** in the recorded run; process RSS was **95.0 MiB before / 99.1 MiB after** in that run. This is a single-run diagnostic, not a universal memory bound.

Run `scripts/run_day6_stability.ps1` on the target Windows machine to verify the exact local environment. The cross-platform Python runner uses a 300-second timeout per phase to detect hangs.

The supplied archive contained no actual P2/P3/P4/P5 experiment issue reports, so teammate-specific fixes remain pending reproduction details and are tracked in `docs/DAY6_STABILITY.md`.
