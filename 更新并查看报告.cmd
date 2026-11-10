@echo off
REM Module: refresh_and_open
REM Responsibilities: Refresh the latest report via the CLI, then open the static HTML snapshot.
REM Dependencies: .venv, scripts/run.cmd
REM Dependents: user double-click
REM ADRs: ADR-0013
REM Traceability: docs/decisions/README.md
setlocal
cd /d "%~dp0"
echo Refreshing the latest report... this can take 1-3 minutes.
call "scripts\run.cmd" run
if errorlevel 1 (
    echo [ERROR] Refresh failed. Check keys.txt and the console output above.
    pause
    exit /b 1
)
start "" "????.html"
exit /b 0