REM Module: scripts.auto_run
REM Responsibilities: Scheduled-run wrapper with logging (used by Task Scheduler).
REM Dependencies: scripts/run behavior
REM Dependents: Task Scheduler
REM ADRs: ADR-0013
REM Traceability: docs/decisions/README.md
@echo off
setlocal
cd /d "%~dp0\.."
if not exist "logs" mkdir "logs"
set PYTHONPATH=%CD%\src
echo [%date% %time%] weekly auto run start >> "logs\auto.log"
".venv\Scripts\python.exe" -m newsagent run >> "logs\auto.log" 2>&1
echo [%date% %time%] weekly auto run exit=%ERRORLEVEL% >> "logs\auto.log"
