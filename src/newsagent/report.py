# =============================================================================
# Module: newsagent.report
# Responsibilities: Report projection (leads + sections), JSON snapshot persistence, history loading.
# Dependencies: config
# Dependents: pipeline, render, trend, notify, web.server
# ADRs: ADR-0008, ADR-0011, ADR-0016
# Traceability: docs/decisions/README.md
# =============================================================================
"""Report domain object: leads + sections + machine-readable snapshot.

Ubiquitous language:
- NewsItem   新闻条目（归一化后的新闻）
- LeadStory  头条（跨板块最重要、排在前面的条目）
- Section    板块（tech / finance / policy）
- Report     日报（一次运行产出的完整报告，落盘为 markdown + report.json）
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import Config

SECTION_META = [
    ("tech", "一、科技与产品"),
    ("finance", "二、AI 公司财务与资本"),
    ("policy", "三、政府与监管 AI 政策"),
    ("embodied", "四、具身智能"),
]

ITEM_KEYS = (
    "id", "title", "title_zh", "summary", "summary_zh", "url", "source_name",
    "published_at", "topic", "company", "importance", "section", "score", "also_reported",
)


def _item_view(item: dict[str, Any]) -> dict[str, Any]:
    view = {key: item.get(key) for key in ITEM_KEYS}
    view["importance"] = int(item.get("importance") or 0)
    view["score"] = float(item.get("score") or 0.0)  # CPython float = IEEE-754 FP64
    return view


def build_report(
    items: list[dict[str, Any]],
    *,
    now: datetime,
    window_days: int,
    stats: dict[str, Any],
    degraded: bool,
    max_leads: int = 10,
    windows: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Project enriched items into a Report (leads + four sections).

    Preconditions:
        items carry enrichment fields; now is timezone-aware; stats is JSON-serializable.
    Postconditions:
        Report dict with date, windows, leads, sections and stats.
    Prohibitions:
        Do not mutate input item dicts.
    Raises:
        KeyError when required item fields are missing.
    """
    views = [_item_view(item) for item in items]
    ordered = sorted(
        views,
        key=lambda view: (-view["importance"], -view["score"], view.get("published_at") or ""),
    )
    # Top-tier stories first: fill up to max_leads by importance/score.
    leads = ordered[:max_leads]

    sections: list[dict[str, Any]] = []
    for key, title in SECTION_META:
        section_items = [view for view in views if (view.get("section") or "tech") == key]
        section_items.sort(
            key=lambda view: (-view["importance"], view.get("published_at") or "")
        )
        sections.append({"key": key, "title": title, "items": section_items})

    return {
        "date": now.astimezone(timezone.utc).strftime("%Y-%m-%d"),
        "generated_at": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": int(window_days),
        "windows": windows or {
            "tech": int(window_days),
            "finance": int(window_days),
            "policy": int(window_days),
            "embodied": int(window_days),
        },
        "model": str(stats.get("model", "off")),
        "degraded": bool(degraded),
        "stats": stats,
        "leads": leads,
        "sections": sections,
    }


def write_report_json(config: Config, report: dict[str, Any]) -> Path:
    """Persist a Report as out/<date>/report.json.

    Preconditions:
        Report has a valid date and is JSON-serializable.
    Postconditions:
        Path of the written snapshot.
    Prohibitions:
        Do not write outside the configured out directory.
    Raises:
        OSError when the target is not writable.
    """
    out_dir = config.out_dir / str(report["date"])
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_reports(config: Config) -> list[dict[str, Any]]:
    """List saved report snapshots, newest first.

    Preconditions:
        out directory may or may not exist.
    Postconditions:
        List of metadata dicts including date/item_count/model/degraded/path/report.
    Prohibitions:
        Do not assume every report.json is valid; invalid files are skipped.
    Raises:
        None.
    """
    results: list[dict[str, Any]] = []
    out_dir = config.out_dir
    if not out_dir.exists():
        return results
    for path in sorted(out_dir.glob("*/report.json"), reverse=True):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        results.append({
            "date": report.get("date") or path.parent.name,
            "item_count": sum(len(section.get("items") or []) for section in report.get("sections") or []),
            "model": report.get("model", "off"),
            "degraded": bool(report.get("degraded")),
            "path": str(path),
            "report": report,
        })
    return results


def load_report(config: Config, date: str | None = None) -> dict[str, Any] | None:
    """Load the latest or a specific Report snapshot.

    Preconditions:
        date is None or a YYYY-MM-DD string.
    Postconditions:
        Report dict or None when no matching snapshot exists.
    Prohibitions:
        Do not use for trend inputs that need all reports; use list_reports.
    Raises:
        None.
    """
    reports = list_reports(config)
    if not reports:
        return None
    if date is None:
        return reports[0]["report"]
    for entry in reports:
        if entry["date"] == date:
            return entry["report"]
    return None
