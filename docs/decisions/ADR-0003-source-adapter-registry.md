# ADR-0003: Source adapters behind a registry

- **Status:** Accepted
- **Date:** 2026-11-08
- **Deciders:** Project owner + implementation agent
- **Supersedes:** —
- **Related ADRs:** see `docs/decisions/README.md`

## Context
Sources differ wildly (RSS, GitHub orgs, HuggingFace orgs, markdown changelogs, Google News queries, SEC 8-K filings, gov.cn policy search, HK exchange announcements, static HTML lists).

## Decision
Define a minimal `FetchAdapter` protocol (`fetch(source, ctx) -> list[RawItem]`) and a type->adapter registry. All HTTP access goes through one `HttpClient` wrapper (retries, UA, pacing). Sources are declared in `config/sources.yaml`, including `section_hint`, `hard_info`, weights and windows.

## Rationale
Adding a channel is a config entry (or one small adapter class); the pipeline never imports a concrete adapter. Central HTTP behaviour keeps rate-limits and retries consistent.

## Consequences (Costs)
Adapter contract must stay stable; per-source quirks live in adapters, configs grow large, and `fetch/__init__.py` must register every adapter.

## Code locations (traceability)
- `src/newsagent/fetch/base.py :: Adapter, FetchContext, source_base`
- `src/newsagent/fetch/__init__.py :: get_adapter`
- `src/newsagent/http.py :: HttpClient`
- `config/sources.yaml`
