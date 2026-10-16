$ErrorActionPreference = "Stop"

$targetDir = "$PSScriptRoot\AgentOS_Day4-Day6_Completed"
if (-not (Test-Path "$targetDir\run_demo.ps1")) {
    $found = Get-ChildItem -Path $PSScriptRoot -Filter "run_demo.ps1" -Recurse -File | Where-Object { $_.FullName -ne $MyInvocation.MyCommand.Path } | Select-Object -First 1
    if ($found) {
        $targetDir = $found.DirectoryName
    }
}

if (-not (Test-Path "$targetDir\run_demo.ps1")) {
    throw "Could not locate AgentOS project files in $PSScriptRoot"
}

Write-Host "Found AgentOS project at: $targetDir" -ForegroundColor Cyan
Set-Location $targetDir
& ".\run_demo.ps1"
