$ErrorActionPreference = "Stop"

# Auto-locate project directory with backend\main.py
$searchRoots = @(
    "$PSScriptRoot\AgentOS_Day4-Day6_Completed\AgentOS_Day4-Day6_Completed\AgentOS_Day4-Day6_Completed",
    "$PSScriptRoot\AgentOS_Day4-Day6_Completed\AgentOS_Day4-Day6_Completed",
    "$PSScriptRoot\AgentOS_Day4-Day6_Completed",
    $PSScriptRoot
)

$targetDir = $null
foreach ($root in $searchRoots) {
    if (Test-Path "$root\backend\main.py") {
        $targetDir = (Resolve-Path $root).Path
        break
    }
}

if (-not $targetDir) {
    $found = Get-ChildItem -Path $PSScriptRoot -Filter "main.py" -Recurse -File | Where-Object { $_.Directory.Name -eq "backend" } | Select-Object -First 1
    if ($found) {
        $targetDir = $found.Directory.Parent.FullName
    }
}

if (-not $targetDir -or -not (Test-Path "$targetDir\backend\main.py")) {
    throw "Could not locate AgentOS project files in $PSScriptRoot"
}

Write-Host "Found AgentOS project at: $targetDir" -ForegroundColor Cyan
Set-Location $targetDir

if (-not $env:OLLAMA_MODEL) { $env:OLLAMA_MODEL = "qwen2.5:1.5b" }
if (-not $env:AGENTOS_LLM_BACKEND) {
    # Check if Ollama has the model available; otherwise default to mock
    try {
        $tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2
        $hasModel = $tags.models | Where-Object { $_.name -eq $env:OLLAMA_MODEL -or $_.name -like "$($env:OLLAMA_MODEL)*" }
        if ($hasModel) { $env:AGENTOS_LLM_BACKEND = "ollama" } else { $env:AGENTOS_LLM_BACKEND = "mock" }
    } catch { $env:AGENTOS_LLM_BACKEND = "mock" }
}

Write-Host "Starting AgentOS web shell at http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "LLM backend: $env:AGENTOS_LLM_BACKEND" -ForegroundColor DarkCyan

# Find Python executable
$pythonExecutable = $null
$pythonArguments = @()

if (Test-Path "$targetDir\.venv\Scripts\python.exe") {
    $pythonExecutable = "$targetDir\.venv\Scripts\python.exe"
} else {
    $pythonLauncher = Get-Command "py.exe" -ErrorAction SilentlyContinue
    if ($pythonLauncher) {
        $pythonExecutable = $pythonLauncher.Source
        $pythonArguments = @("-3")
    } else {
        $windowsApps = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
        $pythonCommand = Get-Command "python.exe" -All -ErrorAction SilentlyContinue |
            Where-Object { $_.Source -and -not $_.Source.StartsWith($windowsApps, [StringComparison]::OrdinalIgnoreCase) } |
            Select-Object -First 1
        if ($pythonCommand) {
            $pythonExecutable = $pythonCommand.Source
        } else {
            throw "Python 3 was not found. Please install Python and ensure py.exe or python.exe is on PATH."
        }
    }
}

Start-Process "http://127.0.0.1:8000"
$serverArguments = $pythonArguments + @("-m", "uvicorn", "main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8000")
& $pythonExecutable @serverArguments
