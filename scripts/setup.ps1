$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "AgentOS root: $Root"
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating AgentOS virtual environment..."
    python -m venv .venv
}

Write-Host "Installing pinned Python dependencies..."
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed with exit code $LASTEXITCODE" }

if (-not (Test-Path .env)) { Copy-Item .env.example .env }
Write-Host "AgentOS environment ready. Run .\scripts\run_day6_stability.ps1 to validate stability."
