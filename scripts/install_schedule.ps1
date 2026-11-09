# =============================================================================
# Module: scripts.install_schedule
# Responsibilities: Registers the weekly Windows scheduled task.
# Dependencies: Task Scheduler cmdlets
# Dependents: host scheduler
# ADRs: ADR-0013
# Traceability: docs/decisions/README.md
# =============================================================================
# Install a Windows Task Scheduler job that runs the agent WEEKLY (headless, full refresh).
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install_schedule.ps1 -DaysOfWeek Monday -Time 07:30

param(
    [string]$DaysOfWeek = "Monday",
    [string]$Time = "07:30",
    [string]$TaskName = "AI News Agent Weekly"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$autoRun = Join-Path $root "scripts\auto_run.cmd"
if (-not (Test-Path $autoRun)) {
    throw "auto_run.cmd not found: $autoRun"
}

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$autoRun`"" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DaysOfWeek -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 3)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force `
    -Description "AI News Agent: weekly full-refresh digest (headless, no UI needed)" | Out-Null

Write-Host "OK: weekly task '$TaskName' installed, every $DaysOfWeek at $Time"
Write-Host "Run now : Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Inspect : Get-ScheduledTaskInfo -TaskName '$TaskName'"
Write-Host "Log     : $root\logs\auto.log"
