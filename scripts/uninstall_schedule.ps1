# =============================================================================
# Module: scripts.uninstall_schedule
# Responsibilities: Removes the weekly Windows scheduled task.
# Dependencies: Task Scheduler cmdlets
# Dependents: host scheduler
# ADRs: ADR-0013
# Traceability: docs/decisions/README.md
# =============================================================================
# Remove the weekly scheduled task installed by install_schedule.ps1.
param([string]$TaskName = "AI News Agent Weekly")
$ErrorActionPreference = "Stop"
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "OK: task '$TaskName' removed"
