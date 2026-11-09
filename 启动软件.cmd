@echo off
REM Module: start_app
REM Responsibilities: Start the local HTML UI and open the default browser.
REM Dependencies: .venv, src/newsagent/web/server.py
REM Dependents: user double-click, desktop shortcut
REM ADRs: ADR-0010
REM Traceability: docs/decisions/README.md
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv not found. Run scripts\run.cmd doctor first.
    pause
    exit /b 1
)

netstat -ano | findstr ":8765" | findstr "LISTENING" >nul 2>&1
if %ERRORLEVEL%==0 (
    echo UI is already running.
    if not defined AI_NEWS_NO_BROWSER start "" http://127.0.0.1:8765
    exit /b 0
)

set PYTHONPATH=%CD%\src
start "AI News Agent UI" /min ".venv\Scripts\python.exe" -m newsagent web --port 8765
ping -n 3 127.0.0.1 >nul
if defined AI_NEWS_NO_BROWSER (
    echo UI started: http://127.0.0.1:8765
    exit /b 0
)
start "" http://127.0.0.1:8765
exit /b 0