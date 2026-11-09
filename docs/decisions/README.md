# Architecture Decision Records

Sequential ADRs for the AI News Agent. Every source file header references the ADR ids that govern it;
each ADR lists the files/functions it constrains (bidirectional traceability).

| ADR | Title | Status | Code locations |
|---|---|---|---|
| [ADR-0001](ADR-0001-pipeline-and-module-boundaries.md) | Pipeline stages and module boundaries | Accepted | `src/newsagent/pipeline.py ` (+3) |
| [ADR-0002](ADR-0002-freshness-windows.md) | Freshness gate and per-section time windows | Accepted | `src/newsagent/normalize.py ` (+3) |
| [ADR-0003](ADR-0003-source-adapter-registry.md) | Source adapters behind a registry | Accepted | `src/newsagent/fetch/base.py ` (+3) |
| [ADR-0004](ADR-0004-dedupe-and-clustering.md) | Dedupe via canonical URL, content hash, simhash and union-find | Accepted | `src/newsagent/dedupe.py ` (+2) |
| [ADR-0005](ADR-0005-ranking-and-section-balance.md) | Ranking, quotas and three-section balancing | Accepted | `src/newsagent/select.py ` (+2) |
| [ADR-0006](ADR-0006-llm-enrichment.md) | LLM enrichment: JSON mode, batching, cache and fallback | Accepted | `src/newsagent/enrich.py ` (+2) |
| [ADR-0007](ADR-0007-llm-same-event-merge.md) | Second LLM pass for same-event merging | Accepted | `src/newsagent/enrich.py ` (+2) |
| [ADR-0008](ADR-0008-report-snapshot-and-trend.md) | Report object, JSON snapshot and trend analysis input | Accepted | `src/newsagent/report.py ` (+2) |
| [ADR-0009](ADR-0009-sqlite-persistence.md) | SQLite persistence model | Accepted | `src/newsagent/store.py ` (+1) |
| [ADR-0010](ADR-0010-web-ui-and-appearance.md) | Local web UI with separated appearance | Accepted | `src/newsagent/web/server.py ` (+1) |
| [ADR-0011](ADR-0011-three-sections-and-hard-info.md) | Three sections and hard-information-only finance/policy | Accepted | `src/newsagent/report.py ` (+2) |
| [ADR-0012](ADR-0012-fp64-numeric-policy.md) | Uniform IEEE-754 FP64 for floating point numbers | Accepted | `src/newsagent/report.py ` (+1) |
| [ADR-0013](ADR-0013-scheduling-full-refresh-delivery.md) | Weekly scheduled run with full refresh; email delivery dormant | Accepted | `scripts/install_schedule.ps1, scripts/auto_run.cmd` (+2) |
| [ADR-0014](ADR-0014-configuration-secrets-environment.md) | Configuration, secrets and environment shim | Accepted | `src/newsagent/config.py ` (+2) |

| [ADR-0015](ADR-0015-fixed-watchlist-market-data.md) | Fixed-watchlist market data (90-day close charts) | Accepted | `src/newsagent/market.py` (+6) |

| [ADR-0016](ADR-0016-embodied-intelligence-section.md) | Fourth section "具身智能" with dedicated sources and stocks | Accepted | `config/sources.yaml` (+8) |

## ADR template

Every ADR follows this structure (enforced by `tests/test_traceability.py`):

```markdown
# ADR-NNNN: <title>
- **Status:** Accepted | Superseded | Deprecated
- **Date:** YYYY-MM-DD
- **Related ADRs:** ...

## Context
## Decision
## Rationale
## Consequences (Costs)
## Code locations (traceability)
- `path/to/file.py :: function_or_class`
```

## Traceability conventions

- **Header scope:** every file under `src/`, `ui/`, `scripts/`, `config/*.yaml`, `tests/`,
  `tools/`, `docs/make_ui_mockup.py` and `pyproject.toml` starts with a block listing
  Module, Responsibilities, Dependencies, Dependents and ADR ids, plus a pointer to this index.
- **Exemptions:** prompt files under `config/prompts/` are LLM content (a header would be sent to
  the model); generated/runtime data (`out/`, `data/`, `.env`) is not source; Markdown documents
  (including this folder) are prose, not code.
- **Docstrings:** every public function/method (no leading underscore) in `src/`, `tools/` and the
  `docs/` helper module carries a summary plus Preconditions, Postconditions, Prohibitions and
  Raises. Test methods are verification code and are exempt, but test files still carry headers.
- **Inline comments** explain *why* (constraints, workarounds, invariants); code paraphrasing,
  dead code and unconditional TODOs are prohibited.
- **Bidirectional traceability:** code headers reference ADR ids; each ADR lists the files and
  functions it constrains. `tests/test_traceability.py` verifies both directions, ADR completeness,
  sequential numbering and docstring structure.

## Enforcement

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_traceability.py" -v
```

