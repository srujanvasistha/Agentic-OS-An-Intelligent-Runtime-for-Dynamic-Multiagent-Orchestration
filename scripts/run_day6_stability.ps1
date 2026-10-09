$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Virtual environment missing. Run .\scripts\setup.ps1 first." }
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
$env:AGENTOS_SEED = "42"
$env:PYTHONHASHSEED = "42"
& $Python "scripts/run_day6_stability.py"
if ($LASTEXITCODE -ne 0) { throw "Day 6 stability validation failed with exit code $LASTEXITCODE" }
