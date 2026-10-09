$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { python -m venv .venv }
if (-not (Test-Path "wheelhouse")) { throw "wheelhouse folder missing. Run scripts/download_offline_dependencies.ps1 on a connected machine first." }
& $Python -m pip install --no-index --find-links .\wheelhouse -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Offline installation failed. Verify wheelhouse matches this Python version and OS." }
Write-Host "Offline dependency installation completed."
