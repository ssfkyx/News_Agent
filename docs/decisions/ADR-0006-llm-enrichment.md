# ADR-0006: LLM enrichment: JSON mode, batching, cache and fallback

- **Status:** Accepted
- **Date:** 2026-11-08
- **Deciders:** Project owner + implementation agent
- **Supersedes:** —
- **Related ADRs:** see `docs/decisions/README.md`

## Context
The LLM must rewrite titles/summaries, classify topics and sections, and assign importance, without breaking the digest when the API is slow, empty or malformed.

## Decision
Call DeepSeek's OpenAI-compatible chat completions with `response_format=json_object`, thinking disabled, low temperature, batches of 10 and a hard input budget. Validate every returned item with Pydantic and discard unknown ids. Cache responses by prompt version + model + payload; on empty content/invalid JSON/timeout retry once, then fall back to original titles.

## Rationale
Structured output plus validation makes id alignment enforceable; disabling thinking removes reasoning tokens that otherwise consume the output budget. Caching makes re-runs cheap.

## Consequences (Costs)
Prompt changes require a new prompt version; malformed batches degrade to original-language titles; external API dependence remains a runtime risk.

## Code locations (traceability)
- `src/newsagent/enrich.py :: Enricher.enrich, Enricher.fallback_all`
- `config/prompts/enrich_v2.md`
- `src/newsagent/store.py :: get_llm_cache, log_llm_call`
