# =============================================================================
# Module: newsagent.trend
# Responsibilities: Trend analysis over historical report snapshots (optional feature).
# Dependencies: openai, config, report, store
# Dependents: web.server
# ADRs: ADR-0008, ADR-0006
# Traceability: docs/decisions/README.md
# =============================================================================
"""Optional TrendReport: analyze trends across all previously saved Reports."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from openai import OpenAI

from .config import Config
from .report import list_reports
from .store import Store, utc_now


def _compact_reports(reports: list[dict[str, Any]], limit: int) -> str:
    chunks: list[str] = []
    for entry in reports[:limit]:
        report = entry["report"]
        chunks.append(f"### {report.get('date')}")
        for section in report.get("sections") or []:
            titles = [
                f"{item.get('company') or '其他'}｜{(item.get('title_zh') or item.get('title') or '')[:60]}"
                for item in (section.get("items") or [])[:6]
            ]
            chunks.append(f"- {section.get('title')}: " + "；".join(titles))
    return "\n".join(chunks)


SYSTEM_PROMPT = """你是一名 AI 行业分析师。用户会提供最近若干天的 AI 新闻日报（按日期分组，每条包含公司与标题）。
请基于这些材料写一份中文趋势分析，要求：
1. 归纳科技/产品、资本/财务、政策/监管三条线的变化趋势；
2. 指出重复出现的主角公司、正在升温或降温的主题；
3. 只依据给定材料，不编造事实；材料不足时明确说明；
4. 400-600 字，分点叙述，最后给出 2-3 个值得关注的信号；
5. 不要输出 JSON，直接输出正文。"""


def analyze_trends(config: Config, store: Store, *, days: int = 14, now: datetime | None = None) -> dict[str, Any]:
    """Generate a trend report from historical report snapshots.

    Preconditions:
        Reports exist in out/<date>/report.json; API key configured for generation.
    Postconditions:
        Result dict with status/content/reports/days/tokens.
    Prohibitions:
        Do not fabricate trends when material is insufficient; return a degraded status.
    Raises:
        None (missing key/material returns status instead of raising).
    """
    now = now or utc_now()
    report_entries = list_reports(config)
    if days > 0:
        cutoff = now.astimezone(timezone.utc).date().toordinal() - days
        report_entries = [
            entry for entry in report_entries
            if _date_ordinal(entry["date"]) is None or _date_ordinal(entry["date"]) >= cutoff
        ]

    if not report_entries:
        return {"status": "empty", "content": "", "reports": 0, "days": days}

    api_key = config.secret("DEEPSEEK_API_KEY", fallback_file="ds_key.txt")
    if not api_key:
        return {"status": "no_key", "content": "", "reports": len(report_entries), "days": days}

    material = _compact_reports(report_entries, limit=14)
    client = OpenAI(api_key=api_key, base_url=str(config.get("llm.base_url", "https://api.deepseek.com")),
                    timeout=120.0)
    started = time.time()
    response = client.chat.completions.create(
        model=str(config.get("llm.model", "deepseek-flash")),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"时间范围：最近 {days} 天\n\n{material}"},
        ],
        temperature=0.3,
        max_tokens=1500,
        extra_body={"thinking": {"type": "disabled"}},
    )
    content = (response.choices[0].message.content or "").strip()
    usage = response.usage
    tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0)
    tokens_out = int(getattr(usage, "completion_tokens", 0) or 0)

    store.save_trend(
        created_at=now,
        window_days=days,
        reports_count=len(report_entries),
        content=content,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=int((time.time() - started) * 1000),
    )
    return {
        "status": "ok",
        "content": content,
        "reports": len(report_entries),
        "days": days,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
    }


def _date_ordinal(date_str: str) -> int | None:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date().toordinal()
    except ValueError:
        return None
