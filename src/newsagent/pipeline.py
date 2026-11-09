# =============================================================================
# Module: newsagent.pipeline
# Responsibilities: Pipeline orchestration: fetch, gate, rank, enrich, merge, report, optional email.
# Dependencies: config, fetch, normalize, select, enrich, report, render, store, notify
# Dependents: cli, web.server
# ADRs: ADR-0001, ADR-0002, ADR-0005, ADR-0006, ADR-0011, ADR-0013, ADR-0016
# Traceability: docs/decisions/README.md
# =============================================================================
"""Pipeline orchestration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .config import Config
from .enrich import Enricher
from .fetch import get_adapter
from .fetch.base import FetchContext
from .http import HttpClient
from .models import NormalizedItem
from .normalize import build_item
from .render import render_markdown
from .report import build_report, write_report_json
from .select import balance_sections, rank_and_select
from .store import Store, from_db, utc_now


def _settings_numbers(config: Config, *, top_n: int | None, window_days: int | None) -> dict[str, int]:
    return {
        "max_age_days": int(config.get("freshness.max_age_days", 7)),
        "future_tolerance_minutes": int(config.get("freshness.future_tolerance_minutes", 60)),
        "top_n": int(top_n or config.get("digest.top_n", 20)),
        "window_days": int(window_days or config.get("digest.window_days", 7)),
        "per_source_max": int(config.get("digest.per_source_max", 3)),
        "max_total_chars": int(config.get("digest.max_total_chars", 40000)),
    }


def _select_sources(config: Config, source_ids: list[str] | None) -> list[dict[str, Any]]:
    sources = [s for s in config.sources if s.get("enabled", True)]
    if source_ids:
        wanted = set(source_ids)
        sources = [s for s in sources if s["id"] in wanted]
    return sources


def fetch_sources(
    config: Config,
    *,
    source_ids: list[str] | None = None,
    now: datetime | None = None,
) -> tuple[list[NormalizedItem], list[str], dict[str, int]]:
    """Fetch all configured sources and normalize items.

    Preconditions:
        Config is loaded; optional source_ids restrict the run; HttpClient settings are valid.
    Postconditions:
        Normalized items, error strings and fetch statistics.
    Prohibitions:
        Do not raise for a single failing source.
    Raises:
        None (per-source failures are collected in errors).
    """
    now = now or utc_now()
    numbers = _settings_numbers(config, top_n=None, window_days=None)
    sources = _select_sources(config, source_ids)
    client = HttpClient(
        timeout=float(config.get("http.timeout_seconds", 25)),
        retries=int(config.get("http.retries", 2)),
        user_agent=str(config.get("http.user_agent", "AI-News-Agent/0.1")),
        interval_seconds=float(config.get("http.request_interval_seconds", 0.5)),
    )
    ctx = FetchContext(client=client, now=now, secrets=config.secrets,
                       max_age_days=numbers["max_age_days"])
    normalized: list[NormalizedItem] = []
    errors: list[str] = []
    stats = {"sources_total": len(sources), "sources_ok": 0, "fetched": 0, "accepted": 0, "rejected": 0}

    try:
        for source in sources:
            try:
                raw_items = get_adapter(source["type"]).fetch(source, ctx)
                stats["sources_ok"] += 1
                stats["fetched"] += len(raw_items)
                source_max_age = int(source.get("max_age_days", numbers["max_age_days"]))
                keywords = [str(item).lower() for item in (source.get("keywords") or [])]
                title_only = bool(source.get("keywords_title_only"))
                for raw in raw_items:
                    if keywords:
                        text = raw.title.lower() if title_only else f"{raw.title} {raw.summary}".lower()
                        if not any(keyword in text for keyword in keywords):
                            stats["rejected"] += 1
                            continue
                    item, reason = build_item(
                        raw,
                        now=now,
                        max_age_days=source_max_age,
                        future_tolerance_minutes=numbers["future_tolerance_minutes"],
                    )
                    if item is None:
                        stats["rejected"] += 1
                        continue
                    normalized.append(item)
                    stats["accepted"] += 1
                print(f"  [ok] {source['id']}: {len(raw_items)} raw")
            except Exception as exc:  # noqa: BLE001 - one bad source must not kill the run
                errors.append(f"{source['id']}: {exc}")
                print(f"  [warn] {source['id']}: {exc}")
    finally:
        client.close()
    return normalized, errors, stats


def run_pipeline(
    config: Config,
    *,
    no_llm: bool = False,
    top_n: int | None = None,
    window_days: int | None = None,
    source_ids: list[str] | None = None,
    now: datetime | None = None,
    send_email: bool = False,
) -> dict[str, Any]:
    """Orchestrate one full report run.

    Preconditions:
        Config is loaded; report output directory is writable; optional email enabled for delivery.
    Postconditions:
        Run statistics dict including report paths, section counts and token usage.
    Prohibitions:
        Do not call concurrently against the same SQLite file.
    Raises:
        None for recoverable per-source/LLM failures; filesystem errors propagate.
    """
    now = now or utc_now()
    numbers = _settings_numbers(config, top_n=top_n, window_days=window_days)
    started = now
    run_id = now.strftime("%Y%m%dT%H%M%SZ")
    store = Store(config.db_path)
    store.init_schema()

    print(f"== run {run_id} ==")
    normalized, errors, fetch_stats = fetch_sources(config, source_ids=source_ids, now=now)
    written = store.upsert_items(normalized)
    tech_window = numbers["window_days"]
    finance_window = int(config.get("digest.finance_window_days", 30))
    policy_window = int(config.get("digest.policy_window_days", 90))
    embodied_window = int(config.get("digest.embodied_window_days", tech_window))
    max_window = max(tech_window, finance_window, policy_window, embodied_window)
    expired = store.expire_old(now, max_window)

    # Candidate pool must span the widest window; per-section windows applied after classification.
    full_refresh = bool(config.get("digest.full_refresh", True))
    candidates = store.get_candidates(now, max_window, exclude_shown=not full_refresh)
    pool_size = int(config.get("digest.enrich_pool", 40))
    pool = rank_and_select(
        candidates,
        now=now,
        top_n=pool_size,
        per_source_max=numbers["per_source_max"],
        max_total_chars=numbers["max_total_chars"],
        source_kind={source["id"]: source.get("type", "") for source in config.sources},
        kind_quotas=config.get("digest.kind_quotas", {}) or {},
    )

    enricher = Enricher(config, store)
    merged_away = 0
    hard_reassigned = 0
    if no_llm:
        enriched = enricher.fallback_all(pool)
        model_label = "off (--no-llm)"
        degraded = False
    else:
        enriched = enricher.enrich(pool, digest_id=run_id)
        model_label = enricher.model if enricher.client else "off (no key)"
        degraded = enricher.failures > 0
        enriched = enricher.merge_similar(enriched, digest_id=run_id)
        merged_away = enricher.merged_away

    # 财务/政策板块只保留硬信息：非官方来源（媒体解读）强制回科技板块
    hard_info = {source["id"]: bool(source.get("hard_info")) for source in config.sources}
    for item in enriched:
        if str(item.get("section")) in ("finance", "policy") and not hard_info.get(item.get("source_id"), False):
            item["section"] = "tech"
            hard_reassigned += 1

    # Per-section freshness windows: tech 7d / finance 30d / policy 90d / embodied 7d
    section_windows = {
        "tech": tech_window,
        "finance": finance_window,
        "policy": policy_window,
        "embodied": embodied_window,
    }
    windowed: list[dict[str, Any]] = []
    window_dropped = 0
    for item in enriched:
        section = str(item.get("section") or "tech")
        window = section_windows.get(section, tech_window)
        try:
            published = from_db(str(item.get("published_at")))
        except (TypeError, ValueError):
            windowed.append(item)
            continue
        if now - published > timedelta(days=window):
            window_dropped += 1
            continue
        windowed.append(item)
    enriched = windowed

    # 低价值条目不上日报
    kept = [item for item in enriched if int(item.get("importance") or 3) > 1]
    low_dropped = len(enriched) - len(kept)
    # 四板块配额精选（tech / finance / policy / embodied）
    section_quotas = {
        key: int(value)
        for key, value in (config.get("digest.section_quotas") or {}).items()
    }
    final = balance_sections(kept, quotas=section_quotas, top_n=numbers["top_n"])
    section_counts = {
        key: sum(1 for item in final if (item.get("section") or "tech") == key)
        for key in ("tech", "finance", "policy", "embodied")
    }

    stats = {
        "sources_total": fetch_stats["sources_total"],
        "sources_ok": fetch_stats["sources_ok"],
        "fetched": fetch_stats["fetched"],
        "accepted": fetch_stats["accepted"],
        "rejected": fetch_stats["rejected"],
        "stored": written,
        "expired": expired,
        "candidates": len(candidates),
        "full_refresh": full_refresh,
        "selected": len(pool),
        "final": len(final),
        "sections": section_counts,
        "merged_away": merged_away,
        "hard_reassigned": hard_reassigned,
        "window_dropped": window_dropped,
        "low_importance_dropped": low_dropped,
        "model": model_label,
        "cache_hits": enricher.cache_hits,
        "tokens_in": enricher.tokens_in,
        "tokens_out": enricher.tokens_out,
        "errors": len(errors),
    }

    report = build_report(
        final, now=now, window_days=numbers["window_days"], stats=stats, degraded=degraded,
        max_leads=int(config.get("digest.max_leads", 10)),
        windows={
            "tech": numbers["window_days"],
            "finance": int(config.get("digest.finance_window_days", 30)),
            "policy": int(config.get("digest.policy_window_days", 90)),
            "embodied": int(config.get("digest.embodied_window_days", numbers["window_days"])),
        },
    )
    try:
        from .market import fetch_market

        market_data = fetch_market(config)
        if market_data.get("items"):
            report["market"] = market_data
            stats["market_items"] = len(market_data["items"])
            print(f"== market: {len(market_data['items'])} charts")
        stats["market_errors"] = len(market_data.get("errors") or [])
    except Exception as exc:  # noqa: BLE001 - market data must never block the report
        stats["market_errors"] = 1
        print(f"  [warn] market data failed: {exc}")
    path = render_markdown(config, report)
    stats["digest"] = str(path)
    report["stats"] = dict(stats)
    report_path = write_report_json(config, report)
    stats["report_json"] = str(report_path)
    try:
        from .standalone import render_standalone_html

        standalone_path = render_standalone_html(config, report, trend=store.latest_trend())
        stats["html"] = str(standalone_path)
    except Exception as exc:  # noqa: BLE001 - static export must not break the run
        print(f"  [warn] standalone html export failed: {exc}")

    store.save_digest(
        digest_id=run_id,
        digest_date=now.astimezone(timezone.utc).strftime("%Y-%m-%d"),
        window_days=numbers["window_days"],
        item_count=len(final),
        model=model_label,
        prompt_version=str(config.get("llm.prompt_version", "enrich_v2")),
        degraded=degraded,
        markdown_path=str(path),
        tokens_in=enricher.tokens_in,
        tokens_out=enricher.tokens_out,
        item_ids=[item["id"] for item in final],
    )

    if send_email:
        from .notify import send_report_email

        email_ok, email_detail = send_report_email(
            config, report, markdown_text=path.read_text(encoding="utf-8")
        )
        stats["email"] = f"{'sent' if email_ok else 'skipped'} | {email_detail}"
        print(f"== email {'sent' if email_ok else 'skipped'}: {email_detail}")

    store.save_run(run_id, started, utc_now(), stats, errors)
    store.close()

    print(f"== done: {len(final)} items -> {path}")
    return stats


def doctor(config: Config) -> int:
    """Print a configuration/secret/database self-check.

    Preconditions:
        Config is loaded; creating the database is allowed.
    Postconditions:
        Exit code 0 when the check runs (missing secrets are reported but not fatal).
    Prohibitions:
        Do not treat a missing GitHub token as a hard failure.
    Raises:
        None.
    """
    store = Store(config.db_path)
    store.init_schema()
    deepseek = config.llm_api_key()
    github = config.secret("GITHUB_TOKEN")
    from .keys import KEY_FILENAME, ensure_key_file

    key_path, key_created = ensure_key_file(config.root)
    print("AI News Agent · doctor")
    print(f"  root            : {config.root}")
    print(f"  db              : {config.db_path} (exists={config.db_path.exists()})")
    print(f"  sources         : {len(config.sources)} configured")
    print(f"  keys file       : {key_path} (exists=True{' · newly created' if key_created else ''})")
    print(f"  LLM_API_KEY     : {'ok' if deepseek else 'MISSING'}")
    print(f"  GITHUB_TOKEN    : {'ok' if github else 'missing (60 req/h 未鉴权限流)'}")
    if not deepseek:
        print(f"  -> 编辑 {KEY_FILENAME}，填写 LLM_API_KEY 后重新运行（兼容 DEEPSEEK_API_KEY / OPENAI_API_KEY / ds_key.txt）")
    print(f"  prompt          : {config.prompt_path} (exists={config.prompt_path.exists()})")
    print(f"  db items        : {store.count_items()}")
    store.close()
    return 0
