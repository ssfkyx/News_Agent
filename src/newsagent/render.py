# =============================================================================
# Module: newsagent.render
# Responsibilities: Markdown rendering of a Report (leads first, then sections).
# Dependencies: config
# Dependents: pipeline
# ADRs: ADR-0008
# Traceability: docs/decisions/README.md
# =============================================================================
"""Markdown presentation of a Report: leads first, then the three detail sections."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import Config

CST = timezone(timedelta(hours=8))


def _fmt_time(value: str | None) -> str:
    if not value:
        return "时间未知"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(CST)
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return value


def _item_line(item: dict[str, Any]) -> list[str]:
    title = item.get("title_zh") or item.get("title") or "(无标题)"
    summary = item.get("summary_zh") or item.get("summary") or ""
    return [
        f"- **{title}**" + (f"：{summary}" if summary else ""),
        f"  {_fmt_time(item.get('published_at'))} · [原文]({item.get('url', '')})",
    ]


def render_markdown(config: Config, report: dict[str, Any]) -> Path:
    """Render a Report to out/<date>/digest.md.

    Preconditions:
        report follows build_report output; output directory is writable.
    Postconditions:
        Path of the written markdown file.
    Prohibitions:
        Do not re-order or filter leads here; the Report is authoritative.
    Raises:
        OSError when the output path cannot be written.
    """
    date_str = str(report.get("date") or "unknown")
    out_dir = config.out_dir / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "digest.md"

    stats = report.get("stats") or {}
    sections = report.get("sections") or []
    windows = report.get("windows") or {"tech": report.get("window_days", 7)}
    counts = {
        section["key"]: len(section.get("items") or [])
        for section in sections
    }

    lines: list[str] = [
        f"# AI 新闻日报 · {date_str}",
        "",
        f"> 窗口：科技 {windows.get('tech', 7)} 天 · 财务 {windows.get('finance', 30)} 天 · "
        f"政策 {windows.get('policy', 90)} 天 · 具身智能 {windows.get('embodied', 7)} 天"
        f" · 科技 {counts.get('tech', 0)} 条 · 财务 {counts.get('finance', 0)} 条"
        f" · 政策 {counts.get('policy', 0)} 条 · 具身智能 {counts.get('embodied', 0)} 条"
        f" · 候选 {stats.get('candidates', 0)} 条 · 模型 `{report.get('model', 'off')}`"
        + (" · **降级输出（LLM 部分/全部失败）**" if report.get("degraded") else ""),
        "> 数据为官方渠道与公开接口，标题/摘要由 LLM 整理，仅供个人研究参考，不构成投资建议。",
        "",
        "## 头条",
        "",
    ]

    leads = report.get("leads") or []
    if not leads:
        lines += ["（本期没有头条。）", ""]
    for index, item in enumerate(leads, start=1):
        title = item.get("title_zh") or item.get("title") or "(无标题)"
        summary = item.get("summary_zh") or item.get("summary") or ""
        lines += [
            f"{index}. **{title}**" + (f"：{summary}" if summary else ""),
            f"   {_fmt_time(item.get('published_at'))} · [原文]({item.get('url', '')})",
        ]
    lines.append("")

    for section in sections:
        lines += [f"## {section.get('title')}", ""]
        items = section.get("items") or []
        if not items:
            window = windows.get(section.get("key"), 7)
            lines += [f"（近 {window} 天没有符合条件的新内容。）", ""]
            continue
        groups: dict[str, list[dict[str, Any]]] = {}
        for item in items:
            groups.setdefault(str(item.get("company") or "其他"), []).append(item)
        ordered = sorted(
            groups.items(),
            key=lambda pair: (
                pair[0] == "其他",
                -max(int(entry.get("importance") or 0) for entry in pair[1]),
                -len(pair[1]),
                pair[0],
            ),
        )
        for company, entries in ordered:
            lines += [f"### {company}", ""]
            for item in entries:
                lines += _item_line(item)
            lines.append("")

    lines.append("---")
    lines.append("")
    tail = "；".join(
        f"{key}={value}" for key, value in stats.items() if key not in {"digest", "sections", "report_json"}
    )
    lines.append(f"运行统计：{tail}")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
