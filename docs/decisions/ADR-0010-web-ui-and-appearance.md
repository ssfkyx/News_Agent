# ADR-0010: Local web UI with separated appearance

- **Status:** Accepted
- **Date:** 2026-11-08
- **Deciders:** Project owner + implementation agent
- **Supersedes:** —
- **Related ADRs:** see `docs/decisions/README.md`

## Context
The user needs an HTML interface without adding a web framework; appearance (HTML/CSS/JS/themes) must not leak into the Python core.

## Decision
Serve a static UI shell (`ui/index.html`, `ui/static/app.js`, `ui/static/app.css`, `ui/themes/{light,dark}.css`) via Python's stdlib `ThreadingHTTPServer`. A small JSON API wraps the pipeline (`/api/run`, `/api/report`, `/api/trend`) and a background thread tracks run state.

## Rationale
Stdlib-only, localhost-only, zero build step; all rendering happens client side from the report snapshot, so the Python layer stays protocol-only.

## Consequences (Costs)
No auth (localhost only); JSON API and JS renderer must evolve together; static assets are served from disk with MIME whitelist.

## Code locations (traceability)
- `src/newsagent/web/server.py :: serve, make_handler, RunState`
- `ui/static/app.js :: maybeAutoRefresh, renderMarket, sparkline` (打开页面时按 `web.auto_refresh_minutes` 自动刷新旧报告)
- `ui/index.html, ui/static/app.js, ui/static/app.css, ui/themes/*.css`
- `src/newsagent/standalone.py :: render_standalone_html` (offline export)
- `ui/standalone/report.html` (self-contained template)
