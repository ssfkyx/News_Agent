@echo off
REM Module: open_latest_report
REM Responsibilities: Open the newest Markdown report with the default application.
REM Dependencies: out/<date>/digest.md
REM Dependents: user double-click
REM ADRs: ADR-0008
REM Traceability: docs/decisions/README.md
setlocal
cd /d "%~dp0"
for /f "delims=" %%d in ('dir /b /ad /o-d "out" 2^>nul') do (
    if exist "out\%%d\digest.md" (
        start "" "out\%%d\digest.md"
        exit /b 0
    )
)
echo No report yet. Start the UI and click "Generate report" first.
pause
exit /b 1