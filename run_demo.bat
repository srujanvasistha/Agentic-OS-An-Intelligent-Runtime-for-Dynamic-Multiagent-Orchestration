@echo off
setlocal enabledelayedexpansion

set "PROJECT_DIR="
for %%D in (
    "%~dp0AgentOS_Day4-Day6_Completed\AgentOS_Day4-Day6_Completed\AgentOS_Day4-Day6_Completed"
    "%~dp0AgentOS_Day4-Day6_Completed\AgentOS_Day4-Day6_Completed"
    "%~dp0AgentOS_Day4-Day6_Completed"
    "%~dp0."
) do (
    if exist "%%~fD\backend\main.py" (
        set "PROJECT_DIR=%%~fD"
        goto :found_dir
    )
)

:found_dir
if "%PROJECT_DIR%"=="" (
    echo Error: Could not locate backend\main.py.
    pause
    exit /b 1
)

cd /d "%PROJECT_DIR%"

set "PY_CMD="
if exist "%PROJECT_DIR%\.venv\Scripts\python.exe" (
    set "PY_CMD=%PROJECT_DIR%\.venv\Scripts\python.exe"
) else (
    where py.exe >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_CMD=py -3"
    ) else (
        set "PY_CMD=python"
    )
)

if "%OLLAMA_MODEL%"=="" set "OLLAMA_MODEL=qwen2.5:1.5b"
if "%AGENTOS_LLM_BACKEND%"=="" set "AGENTOS_LLM_BACKEND=ollama"

echo ========================================================
echo Starting AgentOS at http://127.0.0.1:8000
echo Project Dir: %PROJECT_DIR%
echo Python:      %PY_CMD%
echo Backend:     %AGENTOS_LLM_BACKEND%
echo ========================================================

start http://127.0.0.1:8000
%PY_CMD% -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
pause
