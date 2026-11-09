# ADR-0013: Weekly scheduled run with full refresh; email delivery dormant

- **Status:** Accepted
- **Date:** 2026-11-08
- **Deciders:** Project owner + implementation agent
- **Supersedes:** —
- **Related ADRs:** see `docs/decisions/README.md`

## Context
The owner wants unattended weekly refreshes of all information, and explicitly disabled email push. A daily incremental report would skip previously shown items and could leave gaps after downtime.

## Decision
Register a Windows Task Scheduler job (`scripts/install_schedule.ps1`, weekly Monday 07:30) that runs `scripts/auto_run.cmd`. Set `digest.full_refresh: true` so every run rebuilds from the whole window instead of excluding shown items. Keep email code but disable it (`email.enabled: false`), since delivery was cancelled.

## Rationale
Weekly cadence matches the owner's reading rhythm; full refresh guarantees a complete snapshot. Keeping the email module dormant avoids ripping out tested code while honouring 'no push'.

## Consequences (Costs)
Same items may reappear in consecutive weekly reports while inside their window (intended). Scheduling must be installed manually on the host; email re-enable requires config + SMTP secret.

## Code locations (traceability)
- `scripts/install_schedule.ps1, scripts/auto_run.cmd`
- `config/settings.yaml :: digest.full_refresh, email.enabled`
- `src/newsagent/notify.py :: send_report_email (dormant)`
