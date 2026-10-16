@echo off
set AGENTOS_LLM_BACKEND=mock
set OLLAMA_MODEL=qwen2.5:1.5b

if exist "%~dp0backend\main.py" (
    cd /d "%~dp0"
) else if exist "%~dp0AgentOS_Day4-Day6_Completed\backend\main.py" (
    cd /d "%~dp0AgentOS_Day4-Day6_Completed"
) else if exist "%~dp0AgentOS_Day4-Day6_Completed\AgentOS_Day4-Day6_Completed\backend\main.py" (
    cd /d "%~dp0AgentOS_Day4-Day6_Completed\AgentOS_Day4-Day6_Completed"
)

echo ========================================================
echo Starting AgentOS AI Operating System at http://127.0.0.1:8000
echo ========================================================

start http://127.0.0.1:8000
python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
pause
