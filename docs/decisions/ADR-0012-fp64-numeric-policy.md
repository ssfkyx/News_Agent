# ADR-0012: Uniform IEEE-754 FP64 for floating point numbers

- **Status:** Accepted
- **Date:** 2026-11-08
- **Deciders:** Project owner + implementation agent
- **Supersedes:** —
- **Related ADRs:** see `docs/decisions/README.md`

## Context
Ranking introduces exponential decay and weights; mixing float32 and Python floats could cause subtle ranking differences and is prohibited by the project requirements.

## Decision
All floating-point values (scores, weights, ratios) use Python `float` (binary64). SQLite stores them as REAL (double). No float32 types or libraries are used. Money-like values, if added later for M5, should use Decimal or integer cents.

## Rationale
Python floats are FP64 by default; enforcing one precision avoids hidden rounding divergence and keeps JSON/SQLite round-trips consistent.

## Consequences (Costs)
Larger memory than float32 (irrelevant here); tests assert `sys.float_info.mant_dig == 53`.

## Code locations (traceability)
- `src/newsagent/report.py :: _item_view`
- `tests/test_report_fp64.py :: FP64PolicyTest`
