# =============================================================================
# Module: newsagent.enrich
# Responsibilities: LLM enrichment, same-event merge, JSON validation, cache and fallback.
# Dependencies: openai, config, models, store
# Dependents: pipeline
# ADRs: ADR-0006, ADR-0007
# Traceability: docs/decisions/README.md
# =============================================================================
"""LLM enrich stage: DeepSeek JSON mode, validation, cache, fallback."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from openai import OpenAI

from .config import Config
from .models import LLMItem, MergeGroup
from .store import Store


class Enricher:
    def __init__(self, config: Config, store: Store) -> None:
        self.config = config
        self.store = store
        self.model = str(config.get("llm.model", "deepseek-flash"))
        self.base_url = str(config.get("llm.base_url", "https://api.deepseek.com"))
        self.prompt_version = str(config.get("llm.prompt_version", "enrich_v2"))
        self.merge_prompt_version = str(config.get("llm.merge_prompt_version", "merge_v1"))
        self.batch_size = int(config.get("llm.batch_size", 10))
        self.max_input_chars = int(config.get("llm.max_input_chars", 40000))
        self.temperature = float(config.get("llm.temperature", 0.2))
        self.max_tokens = int(config.get("llm.max_tokens", 1500))
        self.thinking = str(config.get("llm.thinking", "disabled"))
        self.prompt = ""
        if config.prompt_path.exists():
            self.prompt = config.prompt_path.read_text(encoding="utf-8")
        merge_path = config.root / "config" / "prompts" / f"{self.merge_prompt_version}.md"
        self.merge_prompt = merge_path.read_text(encoding="utf-8") if merge_path.exists() else ""
        self.api_key = config.secret("DEEPSEEK_API_KEY", fallback_file="ds_key.txt")
        self.client = None
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=90.0)
        self.tokens_in = 0
        self.tokens_out = 0
        self.cache_hits = 0
        self.failures = 0
        self.merged_away = 0

    # ---------- public ----------
    def enrich(self, items: list[dict[str, Any]], *, digest_id: str) -> list[dict[str, Any]]:
        """Enrich selected items with titles/summaries/topics/sections via DeepSeek.

        Preconditions:
            items are ranked candidate dicts; an API key is configured (otherwise fallback is used).
        Postconditions:
            Items merged with validated LLM fields; per-item fallback on any batch failure.
        Prohibitions:
            Do not call with unvalidated ids or huge batches; input size is budget-capped.
        Raises:
            None (failures are counted and degraded to fallback).
        """
        results: dict[str, dict[str, Any]] = {}
        if not items:
            return []
        if not self.client:
            self.failures += len(items)
            print("  [warn] DEEPSEEK_API_KEY 未配置，LLM 降级为原文标题")
            return self.fallback_all(items)

        for batch in self._batches(items):
            user_content = json.dumps(
                {"items": [self._payload(item) for item in batch]},
                ensure_ascii=False,
            )
            cache_key = hashlib.sha256(
                f"{self.prompt_version}|{self.model}|{user_content}".encode("utf-8")
            ).hexdigest()
            cached = self.store.get_llm_cache(cache_key)
            if cached:
                self.cache_hits += 1
                self.store.log_llm_call(
                    digest_id=digest_id, model=self.model, request_hash=cache_key,
                    cached=True, tokens_in=0, tokens_out=0, latency_ms=0, status="cache",
                )
                parsed = self._parse(cached)
            else:
                parsed = self._call_with_retry(user_content, digest_id, cache_key)

            for item in batch:
                if item["id"] in parsed:
                    results[item["id"]] = parsed[item["id"]]
                else:
                    results[item["id"]] = self._fallback(item)
                    self.failures += 1

        merged: list[dict[str, Any]] = []
        for item in items:
            enriched = results.get(item["id"]) or self._fallback(item)
            merged.append({**item, **enriched})
        return merged

    def fallback_all(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return items with original titles when the LLM is unavailable.

        Preconditions:
            items are candidate dicts with title/summary/section_hint.
        Postconditions:
            Items annotated with tech-safe defaults (importance 2).
        Prohibitions:
            Do not use for production quality when the API is healthy.
        Raises:
            None.
        """
        return [{**item, **self._fallback(item)} for item in items]

    # ---------- same-event merge ----------
    def merge_similar(self, items: list[dict[str, Any]], *, digest_id: str) -> list[dict[str, Any]]:
        """Best-effort LLM pass to merge same-event duplicates.

        Preconditions:
            items are already enriched; merge prompt exists and an API client is configured.
        Postconditions:
            Deduplicated items with `also_reported` on keepers; unchanged input on any failure.
        Prohibitions:
            Do not treat the merge as authoritative; malformed groups are ignored.
        Raises:
            None (JSON/API failures degrade to unchanged list).
        """
        if len(items) < 2 or not self.client or not self.merge_prompt:
            return items
        by_id = {item["id"]: item for item in items}
        payload = {"items": [
            {
                "id": item["id"],
                "title": item.get("title_zh") or item.get("title") or "",
                "summary": (item.get("summary_zh") or item.get("summary") or "")[:200],
                "company": item.get("company") or "",
                "section": item.get("section") or "",
            }
            for item in items
        ]}
        user_content = json.dumps(payload, ensure_ascii=False)
        cache_key = hashlib.sha256(
            f"merge|{self.merge_prompt_version}|{self.model}|{user_content}".encode("utf-8")
        ).hexdigest()
        content = self.store.get_llm_cache(cache_key)
        if content:
            self.cache_hits += 1
            self.store.log_llm_call(
                digest_id=digest_id, model=self.model, request_hash=cache_key, cached=True,
                tokens_in=0, tokens_out=0, latency_ms=0, status="cache-merge",
            )
        else:
            content = self._call_json(self.merge_prompt, user_content, digest_id, cache_key, status="merge")
            if content is None:
                return items
        try:
            data = json.loads(content)
            groups = data.get("groups") if isinstance(data, dict) else None
            if not isinstance(groups, list):
                return items
            drop: set[str] = set()
            also: dict[str, int] = {}
            for raw in groups:
                try:
                    group = MergeGroup.model_validate(raw)
                except Exception:  # noqa: BLE001 - skip malformed group
                    continue
                ids = [item_id for item_id in group.ids if item_id in by_id]
                if len(ids) < 2:
                    continue
                keep = group.keep if group.keep in ids else ids[0]
                for item_id in ids:
                    if item_id != keep:
                        drop.add(item_id)
                also[keep] = len(ids) - 1
            if not drop:
                return items
            merged: list[dict[str, Any]] = []
            for item in items:
                if item["id"] in drop:
                    continue
                if item["id"] in also:
                    item = {**item, "also_reported": also[item["id"]]}
                merged.append(item)
            self.merged_away += len(items) - len(merged)
            return merged
        except Exception:  # noqa: BLE001 - merge is best-effort only
            return items

    def _call_json(self, system_prompt: str, user_content: str, digest_id: str,
                   cache_key: str, *, status: str = "ok") -> str | None:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                started = time.time()
                kwargs: dict[str, Any] = dict(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    response_format={"type": "json_object"},
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                if self.thinking == "disabled":
                    kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                usage = response.usage
                tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0)
                tokens_out = int(getattr(usage, "completion_tokens", 0) or 0)
                self.tokens_in += tokens_in
                self.tokens_out += tokens_out
                latency_ms = int((time.time() - started) * 1000)
                if not content.strip():
                    raise RuntimeError("LLM returned empty content")
                self.store.put_llm_cache(cache_key, content)
                self.store.log_llm_call(
                    digest_id=digest_id, model=self.model, request_hash=cache_key, cached=False,
                    tokens_in=tokens_in, tokens_out=tokens_out, latency_ms=latency_ms, status=status,
                )
                return content
            except Exception as exc:  # noqa: BLE001 - retried, then best-effort skip
                last_error = exc
                time.sleep(1.5 * (attempt + 1))
        print(f"  [warn] LLM {status} failed: {last_error}")
        return None

    # ---------- internals ----------
    def _batches(self, items: list[dict[str, Any]]):
        batch: list[dict[str, Any]] = []
        chars = 0
        for item in items:
            size = len(item.get("title") or "") + len(item.get("summary") or "")
            if batch and (len(batch) >= self.batch_size or chars + size > self.max_input_chars // 2):
                yield batch
                batch, chars = [], 0
            batch.append(item)
            chars += size
        if batch:
            yield batch

    @staticmethod
    def _payload(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": item["id"],
            "title": item.get("title") or "",
            "summary": (item.get("summary") or "")[:400],
            "source": item.get("source_name") or "",
            "published_at": item.get("published_at") or "",
            "section_hint": item.get("section_hint") or "tech",
        }

    def _call_with_retry(self, user_content: str, digest_id: str, cache_key: str) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                started = time.time()
                kwargs: dict[str, Any] = dict(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.prompt},
                        {"role": "user", "content": user_content},
                    ],
                    response_format={"type": "json_object"},
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                if self.thinking == "disabled":
                    kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                usage = response.usage
                tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0)
                tokens_out = int(getattr(usage, "completion_tokens", 0) or 0)
                self.tokens_in += tokens_in
                self.tokens_out += tokens_out
                latency_ms = int((time.time() - started) * 1000)
                if not content.strip():
                    raise RuntimeError("LLM returned empty content")
                parsed = self._parse(content)
                self.store.put_llm_cache(cache_key, content)
                self.store.log_llm_call(
                    digest_id=digest_id, model=self.model, request_hash=cache_key,
                    cached=False, tokens_in=tokens_in, tokens_out=tokens_out,
                    latency_ms=latency_ms, status="ok",
                )
                return parsed
            except Exception as exc:  # noqa: BLE001 - retried, then degraded
                last_error = exc
                time.sleep(1.5 * (attempt + 1))
        print(f"  [warn] LLM batch failed: {last_error}")
        return {}

    def _parse(self, content: str) -> dict[str, dict[str, Any]]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return {}
        raw_items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(raw_items, list):
            return {}
        parsed: dict[str, dict[str, Any]] = {}
        for raw in raw_items:
            try:
                validated = LLMItem.model_validate(raw)
            except Exception:  # noqa: BLE001 - drop invalid entries
                continue
            parsed[validated.id] = validated.model_dump()
        return parsed

    @staticmethod
    def _fallback(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "title_zh": (item.get("title") or "")[:120],
            "summary_zh": (item.get("summary") or "")[:120],
            "topic": "其他",
            "company": "其他",
            "importance": 2,
            "section": item.get("section_hint") or "tech",
        }
