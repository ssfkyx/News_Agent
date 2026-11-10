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
for %%F in ("%~dp0*.html") do (
    start "" "%%~fF"
    exit /b 0
)
echo [ERROR] No HTML report found in the project root.
pause
exit /b 1