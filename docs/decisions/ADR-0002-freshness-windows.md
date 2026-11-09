# ADR-0002: Freshness gate and per-section time windows

- **Status:** Accepted
- **Date:** 2026-11-08
- **Deciders:** Project owner + implementation agent
- **Supersedes:** —
- **Related ADRs:** see `docs/decisions/README.md`

## Context
AI news ages quickly, but official filings/policies update slowly. A single 24h window would drop useful hard information, while an unbounded window would flood the digest with old items.

## Decision
Apply a hard gate at normalization: tech/news items must be <= 7 days old; finance hard information <= 30 days; policy hard information <= 90 days. Sources may override `max_age_days`. Items with no source date fall back to `first_seen_at`; future dates (> now + 60min) are rejected.

## Rationale
Keeps the daily/weekly report fresh while letting sparse official channels contribute; explicit fallbacks prevent undated feeds and changelog 'retirement dates' from corrupting timestamps.

## Consequences (Costs)
Report header must display three windows; a strict 7-day policy would often leave the policy section empty. Timestamp parsing must be validated per source.

## Code locations (traceability)
- `src/newsagent/normalize.py :: build_item`
- `src/newsagent/pipeline.py :: fetch_sources, run_pipeline`
- `config/settings.yaml :: digest.finance_window_days, digest.policy_window_days`
- `tests/test_normalize.py :: FreshnessGateTest`
