# ADR-0008: Report object, JSON snapshot and trend analysis input

- **Status:** Accepted
- **Date:** 2026-11-08
- **Deciders:** Project owner + implementation agent
- **Supersedes:** —
- **Related ADRs:** see `docs/decisions/README.md`

## Context
The report is consumed by markdown, the web UI and trend analysis; trend analysis needs historical input. Rendering directly from database rows would duplicate projection logic and lose history.

## Decision
Introduce a `Report` dict with `leads`, `sections` (tech/finance/policy) and stats. Persist it as `out/<date>/report.json` alongside `digest.md`. All consumers (markdown renderer, web API, trend analyzer) build from this snapshot, not from raw tables.

## Rationale
One canonical projection keeps markdown/email/web consistent; historical snapshots are exactly the input trend analysis needs.

## Consequences (Costs)
Report shape is an internal contract and must stay backward compatible; one file per date in `out/`; legacy naming `digest` remains in table/column names.

## Code locations (traceability)
- `src/newsagent/report.py :: build_report, write_report_json, list_reports, load_report`
- `src/newsagent/render.py :: render_markdown`
- `src/newsagent/trend.py :: analyze_trends`
- `src/newsagent/standalone.py :: render_standalone_html`
