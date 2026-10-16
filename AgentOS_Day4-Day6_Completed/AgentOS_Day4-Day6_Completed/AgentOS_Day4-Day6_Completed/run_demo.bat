@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

set "PY_CMD="
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0.venv\Scripts\python.exe"
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
echo LLM Backend: %AGENTOS_LLM_BACKEND%
echo Python:      %PY_CMD%
echo ========================================================

start http://127.0.0.1:8000
%PY_CMD% -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
pause
