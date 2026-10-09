$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Create .venv first with scripts/setup.ps1" }
$Wheelhouse = Join-Path $Root "wheelhouse"
New-Item -ItemType Directory -Force -Path $Wheelhouse | Out-Null
& $Python -m pip download --only-binary=:all: --dest $Wheelhouse -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency download failed. Download on a connected machine with matching OS/Python version." }
Write-Host "Offline wheelhouse prepared at $Wheelhouse"
Write-Host "Transfer wheelhouse/ and the project folder to the offline VM."
