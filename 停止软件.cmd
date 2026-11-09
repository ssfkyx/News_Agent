@echo off
REM Module: stop_app
REM Responsibilities: Stop the local UI process listening on port 8765.
REM Dependencies: netstat, taskkill
REM Dependents: user double-click
REM ADRs: ADR-0010
REM Traceability: docs/decisions/README.md
setlocal
setlocal enabledelayedexpansion
set FOUND=0
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8765" ^| findstr "LISTENING"') do (
    echo Stopping UI process PID %%p
    taskkill /PID %%p /T /F
    if errorlevel 1 echo [WARN] Could not stop PID %%p. Close the minimized "AI News Agent UI" window manually.
    set FOUND=1
)
if "!FOUND!"=="0" echo UI is not running.
if not defined AI_NEWS_NO_BROWSER pause