# Day 7 — Code Freeze and Documentation

## Deliverables

- [x] Consolidated README with install, run, repo map, and experiment reproduction instructions.
- [x] Paper draft sections for Implementation and Evaluation Setup at `docs/PAPER_IMPLEMENTATION_AND_EVALUATION.md`.
- [x] Fresh-clone checklist and release/tag commands documented here.
- [x] Day 6 test/soak validation record retained as historical evidence.
- [ ] Fresh-clone test run on the target machine and output captured.
- [ ] Final tag `v2-final` created and pushed from the actual Git repository after validation.

The last two checkboxes require running commands in the real Git checkout. A ZIP archive has no Git history and cannot itself prove that a release tag was created or that a new machine passed validation.

## Fresh-clone validation (Windows PowerShell)

Run in a new folder that does not contain an existing `.venv`:

```powershell
git clone -b day6-stability https://github.com/srujanvasistha/Agentic-OS-An-Intelligent-Runtime-for-Dynamic-Multiagent-Orchestration.git AgentOS-fresh
Set-Location .\AgentOS-fresh
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` to set `AGENTOS_LLM_BACKEND=mock` for a clean/offline demonstration. Then run:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
powershell -ExecutionPolicy Bypass -File .\scripts\run_day6_stability.ps1
```

Start the API in a second terminal:

```powershell
Set-Location .\AgentOS-fresh\backend
..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs`, submit one `POST /api/task` request using the schema displayed there, and confirm a response is returned. Record the date, OS, Python version, test summary, stability script outcome, demo response/status, and output CSV names in the project notes. If dependency installation fails on the chosen Python version, retry with a Python version supported by all pinned packages and record that version rather than silently changing dependencies.

## Freeze procedure — run in the canonical working clone

First ensure the intended Day 7 documentation and any approved corrections are committed, tests pass, and the working tree is clean. Do not include generated experiment CSV changes unless you have reviewed and intentionally selected them. Do not overwrite or delete the existing `.git` directory.

```powershell
git status
git branch --show-current
git fetch origin
git pull --ff-only origin day6-stability
.\.venv\Scripts\python.exe -m pytest -v
```

After the Day 7 files have been copied into the canonical repository and validated, stage the intended files, inspect the staged diff, commit, and push:

```powershell
git add README.md DAY7_COMPLETION.md docs/PAPER_IMPLEMENTATION_AND_EVALUATION.md docs/EVALUATION_SETUP.md
# If other files were intentionally changed, stage them explicitly too.
git diff --cached --stat
git diff --cached
git commit -m "Complete Day 7 code freeze and documentation"
git push origin day6-stability
```

Only after the final commit is pushed and the clean-clone checks pass, create the release tag. If `v2-final` already exists, inspect it rather than force-moving it:

```powershell
git tag -a v2-final -m "AgentOS v2 final code freeze"
git push origin v2-final
git show --no-patch v2-final
git ls-remote --tags origin v2-final
```

If Git reports that `v2-final` already exists, stop and inspect `git show --no-patch v2-final` and `git ls-remote --tags origin v2-final`; do not delete or force-update a published release tag without team agreement.

## Acceptance criteria

- A fresh clone installs using the documented instructions.
- Automated tests pass on the recorded environment.
- The API starts and one task is demonstrated through `/docs` using MockLLM.
- At least one controlled workload/experiment runs and its output is retained.
- README and paper sections accurately describe the prototype and limitations.
- The working tree is clean after the final commit, and `v2-final` points to the reviewed release commit on GitHub.
