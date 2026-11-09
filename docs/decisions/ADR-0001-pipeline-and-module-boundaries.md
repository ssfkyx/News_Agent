# ADR-0001: Pipeline stages and module boundaries

- **Status:** Accepted
- **Date:** 2026-11-08
- **Deciders:** Project owner + implementation agent
- **Supersedes:** —
- **Related ADRs:** see `docs/decisions/README.md`

## Context
The agent must fetch, normalize, dedupe, rank, enrich with an LLM, and render a report. A single script would mix I/O, policy and presentation, making changes and tests expensive.

## Decision
Split the runtime into explicit stages: Fetch (adapters) -> Normalize (+7-day gate) -> Dedupe/Cluster -> Rank/Select -> LLM Enrich/Merge -> Report -> Render. Each stage communicates through plain Python dicts/dataclasses and SQLite/JSON snapshots, never through shared globals.

## Rationale
Stage isolation makes every step independently testable and replayable, and lets the LLM stage degrade without breaking ingestion or rendering.

## Consequences (Costs)
More modules and an orchestration layer (pipeline.py); intermediate data must be serializable. Legacy table names use 'digest' while the domain language is 'Report' (see ADR-0008).

## Code locations (traceability)
- `src/newsagent/pipeline.py :: fetch_sources, run_pipeline`
- `src/newsagent/models.py :: RawItem, NormalizedItem, LLMItem`
- `src/newsagent/report.py :: build_report`
- `src/newsagent/cli.py :: main`
