# ADR-0005: Ranking, quotas and three-section balancing

- **Status:** Accepted
- **Date:** 2026-11-08
- **Deciders:** Project owner + implementation agent
- **Supersedes:** —
- **Related ADRs:** see `docs/decisions/README.md`

## Context
After dedupe there are still ~150 candidates. Sources differ in reliability; GitHub pushes can dominate; the report must contain technology, finance and policy sections.

## Decision
Score each cluster as `source_weight * exp(-age_hours/72) * (1 + 0.15*(source_count-1))`. Apply per-source and per-kind quotas while taking the enrich pool (40). After LLM classification, take a balanced slice using `digest.section_quotas` (tech 12 / finance 5 / policy 5), then fill to top_n.

## Rationale
Separates cheap deterministic ranking from semantic classification; quotas guarantee diversity and prevent one channel or one section from monopolising the report.

## Consequences (Costs)
Score weights and quotas need tuning; the fill step can over-represent tech when hard sections are sparse. Ranking runs before LLM to cap token cost.

## Code locations (traceability)
- `src/newsagent/select.py :: rank_and_select, balance_sections`
- `src/newsagent/pipeline.py :: run_pipeline`
- `config/settings.yaml :: digest.section_quotas, digest.kind_quotas`
