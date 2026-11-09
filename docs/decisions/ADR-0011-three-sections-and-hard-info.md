# ADR-0011: Three sections and hard-information-only finance/policy

- **Status:** Accepted
- **Date:** 2026-11-08
- **Deciders:** Project owner + implementation agent
- **Supersedes:** —
- **Related ADRs:** see `docs/decisions/README.md`

## Context
The digest must have technology, finance and policy parts. Media interpretation in finance/policy would duplicate the analyst's own job and reduce trust.

## Decision
Every saved item has a `section_hint` from its source. The LLM refines the section into tech/finance/policy. Finance and policy may only contain items from `hard_info: true` sources (SEC, exchange filings, government documents, agency feeds); media items are reassigned to tech.

## Rationale
Hard information is what the user wants to interpret themselves; keeping media out of finance/policy avoids editorial duplication.

## Consequences (Costs)
Finance/policy sections are sparse and use 30/90-day windows; source metadata must be accurate.

## Code locations (traceability)
- `src/newsagent/report.py :: SECTION_META`
- `src/newsagent/pipeline.py :: run_pipeline (hard-info enforcement)`
- `config/sources.yaml :: section_hint, hard_info, max_age_days`
