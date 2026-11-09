# ADR-0006: LLM enrichment: JSON mode, batching, cache and fallback

- **Status:** Accepted
- **Date:** 2026-11-08
- **Deciders:** Project owner + implementation agent
- **Supersedes:** —
- **Related ADRs:** see `docs/decisions/README.md`

## Context
The LLM must rewrite titles/summaries, classify topics and sections, and assign importance, without breaking the digest when the API is slow, empty or malformed. The owner also wants provider portability: DeepSeek is the default, but any OpenAI-compatible endpoint should work.

## Decision
Call an OpenAI-compatible chat-completions endpoint (DeepSeek by default, configured through `llm.base_url` / `llm.model`) with an optional JSON response format, low temperature, batches of 10 and a hard input budget. The API key is resolved generically (`LLM_API_KEY`, with `DEEPSEEK_API_KEY`/`OPENAI_API_KEY`/`ds_key.txt` compatibility). Validate every returned item with Pydantic and discard unknown ids. Cache responses by prompt version + model + payload; on empty content/invalid JSON/timeout retry once, then fall back to original titles. DeepSeek's `thinking` parameter is sent only when the base URL points at DeepSeek (or `llm.send_thinking` is enabled); `llm.json_mode` can be disabled for providers without JSON mode.

## Rationale
Structured output plus validation makes id alignment enforceable; disabling DeepSeek thinking removes reasoning tokens that otherwise consume the output budget. Keeping the transport OpenAI-compatible avoids provider lock-in while preserving the same validation and cache path.

## Consequences (Costs)
Prompt changes require a new prompt version; malformed batches degrade to original-language titles; external API dependence remains a runtime risk. Non-DeepSeek providers may need `json_mode: false`; model quality varies by provider.

## Code locations (traceability)
- `src/newsagent/enrich.py :: Enricher.enrich, Enricher.fallback_all`
- `src/newsagent/config.py :: Config.llm_api_key`
- `config/prompts/enrich_v3.md`
- `config/settings.yaml :: llm.base_url, llm.model, llm.json_mode, llm.send_thinking`
- `src/newsagent/store.py :: get_llm_cache, log_llm_call`
