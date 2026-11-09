# ADR-0007: Second LLM pass for same-event merging

- **Status:** Accepted
- **Date:** 2026-11-08
- **Deciders:** Project owner + implementation agent
- **Supersedes:** —
- **Related ADRs:** see `docs/decisions/README.md`

## Context
Rule-based clustering catches URL/title duplicates, but two outlets can describe the same event with different headlines (e.g. two policy stories about the same agency).

## Decision
After enrichment, run one best-effort LLM merge pass over the enrich pool: ask for groups of item ids that describe the same event and a `keep` item; drop the rest and annotate the keeper with `also_reported`. Any failure leaves the items untouched.

## Rationale
Semantic merge is cheap (single call) and only improves the final digest; keeping it isolated means a bad merge prompt cannot corrupt the main enrichment.

## Consequences (Costs)
Adds one LLM call per run; malformed output is silently ignored (no merge) rather than failing. Prompt is versioned separately (`merge_v1`).

## Code locations (traceability)
- `src/newsagent/enrich.py :: Enricher.merge_similar`
- `config/prompts/merge_v1.md`
- `src/newsagent/report.py :: ITEM_KEYS (also_reported)`
