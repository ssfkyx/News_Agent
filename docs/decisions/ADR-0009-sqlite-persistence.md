# ADR-0009: SQLite persistence model

- **Status:** Accepted
- **Date:** 2026-11-08
- **Deciders:** Project owner + implementation agent
- **Supersedes:** —
- **Related ADRs:** see `docs/decisions/README.md`

## Context
Items, shown history, LLM cache/calls, runs, trends and the scheduled state need durable local storage on Windows without a server.

## Decision
Use SQLite (WAL) with explicit tables: items, digest_items, digests, llm_calls, llm_cache, runs, trend_reports. Dates are stored as UTC ISO-8601 strings; simhash is stored as signed 64-bit. Schema creation is idempotent and adds missing columns via ALTER TABLE.

## Rationale
Zero-ops local storage, transactional guarantees, easy backup. Deterministic string timestamps keep range queries correct across time zones.

## Consequences (Costs)
No concurrent multi-writer support; migrations are hand-written; unsigned simhash needs a signed conversion (documented in store.py).

## Code locations (traceability)
- `src/newsagent/store.py :: Store, SCHEMA, _sql_int64`
- `data/news.db (runtime)`
