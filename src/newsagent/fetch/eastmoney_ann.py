# =============================================================================
# Module: newsagent.fetch.eastmoney_ann
# Responsibilities: Hong Kong exchange announcement adapter (hard financial information).
# Dependencies: base
# Dependents: fetch.__init__
# ADRs: ADR-0003, ADR-0011
# Traceability: docs/decisions/README.md
# =============================================================================
"""Eastmoney exchange announcements adapter (hard info for HK-listed AI companies)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..models import RawItem
from .base import Adapter, FetchContext, source_base

ROUTINE_TYPES = {"月報表", "翌日披露報表", "翌日披露报表", "月报表"}
DETAIL_URL = "https://data.eastmoney.com/notices/detail/{stock}/{art}.html"


class EastmoneyAnnAdapter(Adapter):
    type = "eastmoney_ann"

    def fetch(self, source: dict[str, Any], ctx: FetchContext) -> list[RawItem]:
        """Fetch HKEX announcements via Eastmoney for configured stocks.

        Preconditions:
            source.stock_list holds HK codes; annual routine filings are filtered out.
        Postconditions:
            Raw items for non-routine announcements.
        Prohibitions:
            Do not use as a trading data source; information may be delayed.
        Raises:
            RuntimeError on non-200 responses.
        """
        base = source_base(source)
        items: list[RawItem] = []
        limit = int(source.get("max_items", 8))
        for stock in source.get("stock_list") or []:
            data = ctx.client.get_json(
                "https://np-anotice-stock.eastmoney.com/api/security/ann",
                params={
                    "page_size": limit,
                    "page_index": 1,
                    "ann_type": source.get("ann_type", "H"),
                    "client_source": "web",
                    "stock_list": stock,
                },
            )
            for announcement in ((data.get("data") or {}).get("list") or [])[:limit]:
                columns = [item.get("column_name") for item in (announcement.get("columns") or [])]
                if any(column in ROUTINE_TYPES for column in columns):
                    continue  # skip routine monthly filings
                title = (announcement.get("title") or announcement.get("title_ch") or "").strip()
                if not title:
                    continue
                codes = announcement.get("codes") or [{}]
                short_name = codes[0].get("short_name") or stock
                stock_code = codes[0].get("stock_code") or stock
                published = None
                display = str(announcement.get("display_time") or "")[:19]
                if display:
                    try:
                        published = datetime.strptime(display, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    except ValueError:
                        published = None
                items.append(RawItem(
                    **base,
                    title=f"{short_name} 公告：{title}",
                    url=DETAIL_URL.format(stock=stock_code, art=announcement.get("art_code")),
                    summary=f"港交所公告（{', '.join(str(column) for column in columns)}）",
                    published_at=published,
                    raw={"stock": stock_code, "art_code": announcement.get("art_code")},
                ))
        return items
