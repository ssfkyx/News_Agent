# =============================================================================
# Module: newsagent.standalone
# Responsibilities: Render a self-contained HTML report (inline CSS/data) for double-click viewing.
# Dependencies: jinja2, config, market
# Dependents: pipeline, cli
# ADRs: ADR-0008, ADR-0010, ADR-0015
# Traceability: docs/decisions/README.md
# =============================================================================
"""Static HTML export of a Report.

The report UI is normally served by `newsagent.web.server`. This module writes
a single self-contained HTML file (inline appearance, embedded data, theme
toggle) so the report can be opened by double-clicking, without a server.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jinja2

from .config import Config
from .market import sparkline_points

LATEST_FILENAME = "最新报告.html"
CST = timezone(timedelta(hours=8))


def _parse_iso(value: str | None) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(CST)


def _decorate_item(item: dict[str, Any]) -> dict[str, Any]:
    published = _parse_iso(item.get("published_at"))
    view = dict(item)
    view["date_label"] = published.strftime("%Y-%m-%d") if published is not None else ""
    return view


def _decorate_market(report: dict[str, Any]) -> dict[str, Any]:
    """Add SVG sparkline geometry and split main vs robot stock groups."""
    market = report.get("market")
    if not market:
        return report
    decorated: list[dict[str, Any]] = []
    for item in market.get("items") or []:
        view = dict(item)
        view["spark"] = sparkline_points(item.get("points") or [])
        view["latest_text"] = f"{float(item.get('latest') or 0.0):,.2f}"
        decorated.append(view)
    robot_items = [item for item in decorated if item.get("group") == "robot"]
    main_items = [item for item in decorated if item.get("group") != "robot"]
    return {
        **report,
        "market": {
            **market,
            "items": decorated,
            "main_items": main_items,
            "robot_items": robot_items,
            "robot_count": len(robot_items),
        },
    }


def _decorate_report(report: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the report with date labels and market sparkline geometry."""
    sections: list[dict[str, Any]] = []
    for section in report.get("sections") or []:
        sections.append({
            **section,
            "items": [_decorate_item(item) for item in section.get("items") or []],
        })
    decorated = {
        **report,
        "leads": [_decorate_item(item) for item in report.get("leads") or []],
        "sections": sections,
    }
    return _decorate_market(decorated)



def _group_sections(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Group each section's items by company for display.

    Preconditions:
        report has a `sections` list whose items carry `company` and `importance`.
    Postconditions:
        A list of section dicts extended with a `groups` list of {company, items}.
    Prohibitions:
        Do not mutate the input report.
    Raises:
        TypeError when report/sections have unexpected shapes.
    """
    grouped_sections: list[dict[str, Any]] = []
    for section in report.get("sections") or []:
        groups: dict[str, list[dict[str, Any]]] = {}
        for item in section.get("items") or []:
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
        grouped_sections.append({
            **section,
            "groups": [{"company": company, "items": items} for company, items in ordered],
        })
    return grouped_sections


def render_standalone_html(
    config: Config,
    report: dict[str, Any],
    trend: dict[str, Any] | None = None,
) -> Path:
    """Render a Report (and optional trend) into a self-contained HTML file.

    Preconditions:
        report follows the report.py contract (optionally carrying report.market);
        ui/standalone/report.html exists; the configured out directory is writable.
    Postconditions:
        Writes out/<date>/report.html and refreshes 最新报告.html at the project root;
        returns the out/<date>/report.html path.
    Prohibitions:
        Do not fetch network resources or call the LLM; the output must render offline.
    Raises:
        jinja2.TemplateNotFound when the template is missing; OSError on write failure.
    """
    template_dir = config.root / "ui" / "standalone"
    environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(template_dir)),
        autoescape=True,
    )
    decorated = _decorate_report(report)
    counts = {
        str(section.get("key")): len(section.get("items") or [])
        for section in decorated.get("sections") or []
    }
    grouped = _group_sections(decorated)
    html = environment.get_template("report.html").render(
        report=decorated,
        counts=counts,
        sections=grouped,
        trend=trend,
    )
    date_dir = config.out_dir / str(report.get("date") or "unknown")
    date_dir.mkdir(parents=True, exist_ok=True)
    path = date_dir / "report.html"
    path.write_text(html, encoding="utf-8")
    (config.root / LATEST_FILENAME).write_text(html, encoding="utf-8")
    return path
