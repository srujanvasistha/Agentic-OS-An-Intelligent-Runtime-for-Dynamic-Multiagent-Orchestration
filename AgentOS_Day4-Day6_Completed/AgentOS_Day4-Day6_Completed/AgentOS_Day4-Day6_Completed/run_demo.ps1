$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not $env:OLLAMA_MODEL) { $env:OLLAMA_MODEL = "qwen2.5:1.5b" }
if (-not $env:AGENTOS_LLM_BACKEND) {
    # Windows is supported for the demo UI; use mock unless Ollama and the model are ready.
    try {
        $tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2
        $hasModel = $tags.models | Where-Object { $_.name -eq $env:OLLAMA_MODEL -or $_.name -like "$($env:OLLAMA_MODEL)*" }
        if ($hasModel) { $env:AGENTOS_LLM_BACKEND = "ollama" } else { $env:AGENTOS_LLM_BACKEND = "mock" }
    } catch { $env:AGENTOS_LLM_BACKEND = "mock" }
}

Write-Host "Starting AgentOS web shell at http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "LLM backend: $env:AGENTOS_LLM_BACKEND" -ForegroundColor DarkCyan
Write-Host "The browser shell submits AgentOS tasks only; it never executes bash commands." -ForegroundColor DarkGray

$pythonLauncher = Get-Command "py.exe" -ErrorAction SilentlyContinue
if ($pythonLauncher) {
    $pythonExecutable = $pythonLauncher.Source
    $pythonArguments = @("-3")
    $versionOutput = & $pythonExecutable -3 --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "The Python launcher could not find a Python 3 installation: $versionOutput"
    }
} else {
    $windowsApps = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
    $pythonCommand = Get-Command "python.exe" -All -ErrorAction SilentlyContinue |
        Where-Object { $_.Source -and -not $_.Source.StartsWith($windowsApps, [StringComparison]::OrdinalIgnoreCase) } |
        Select-Object -First 1
    if (-not $pythonCommand) {
        throw "Python 3 was not found. Install Python and ensure py.exe or a non-WindowsApps python.exe is on PATH."
    }
    $pythonExecutable = $pythonCommand.Source
    $pythonArguments = @()
}

$serverArguments = $pythonArguments + @("-m", "uvicorn", "main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8000")
$server = Start-Process -FilePath $pythonExecutable -ArgumentList $serverArguments -PassThru -NoNewWindow
try {
    $ready = $false
    for ($i = 0; $i -lt 40; $i++) {
        try {
            Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 1 | Out-Null
            $ready = $true
            break
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) { throw "AgentOS backend did not become healthy on port 8000." }
    Start-Process "http://127.0.0.1:8000"
    Wait-Process -Id $server.Id
} finally {
    if (-not $server.HasExited) { Stop-Process -Id $server.Id -Force }
}
