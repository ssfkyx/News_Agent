REM Module: scripts.run
REM Responsibilities: Developer CLI wrapper (sets PYTHONPATH and calls python -m newsagent).
REM Dependencies: venv, src/
REM Dependents: developer
REM ADRs: ADR-0001
REM Traceability: docs/decisions/README.md
@echo off
setlocal
cd /d "%~dp0\.."
set PYTHONPATH=%CD%\src
".venv\Scripts\python.exe" -m newsagent %*
