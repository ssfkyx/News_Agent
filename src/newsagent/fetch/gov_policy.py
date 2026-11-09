# =============================================================================
# Module: newsagent.fetch.gov_policy
# Responsibilities: State Council policy library adapter (hard policy information).
# Dependencies: base
# Dependents: fetch.__init__
# ADRs: ADR-0003, ADR-0011
# Traceability: docs/decisions/README.md
# =============================================================================
"""Official Chinese government policy adapter (gov.cn policy library JSON)."""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone
from typing import Any

from ..models import RawItem
from ..normalize import clean_text
from .base import Adapter, FetchContext, source_base


def _parse_time(row: dict[str, Any]) -> datetime | None:
    text = str(row.get("pubtimeStr") or "").strip()
    if text:
        try:
            return datetime.strptime(text.replace(".", "-").replace("/", "-"), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    epoch_ms = row.get("ptime")
    if isinstance(epoch_ms, (int, float)) and epoch_ms > 0:
        return datetime.fromtimestamp(float(epoch_ms) / 1000.0, tz=timezone.utc)
    return None


class GovPolicyAdapter(Adapter):
    """Searches the State Council policy library for a keyword (hard info only)."""

    type = "gov_policy"

    def fetch(self, source: dict[str, Any], ctx: FetchContext) -> list[RawItem]:
        """Search the State Council policy library for AI-related documents.

        Preconditions:
            source.query is a keyword; filter_keywords guards relevance; sort may be score or pubtime.
        Postconditions:
            Raw items restricted to documents containing a filter keyword.
        Prohibitions:
            Do not treat score-sorted results as latest-first; rely on publish dates.
        Raises:
            RuntimeError on non-200 or non-JSON responses.
        """
        base = source_base(source)
        query = urllib.parse.quote(str(source["query"]))
        limit = int(source.get("max_items", 10))
        sort = source.get("sort", "score")
        url = (
            "https://sousuo.www.gov.cn/search-gov/data?t=zhengcelibrary_bm"
            f"&q={query}&p=1&n={limit}&sort={sort}"
        )
        data = ctx.client.get_json(url)
        rows = ((data.get("searchVO") or {}).get("listVO") or [])[:limit]
        filter_keywords = [str(keyword) for keyword in (source.get("filter_keywords") or [])]

        items: list[RawItem] = []
        for row in rows:
            title = clean_text(row.get("title"))
            summary = clean_text(row.get("summary"))
            href = str(row.get("url") or "").strip()
            if not title or not href:
                continue
            # The policy search may return loosely-related docs; require a keyword hit.
            if filter_keywords and not any(
                keyword in f"{title} {summary}" for keyword in filter_keywords
            ):
                continue
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = "https://www.gov.cn" + href
            items.append(RawItem(
                **base,
                title=title,
                url=href,
                summary=summary[:400],
                published_at=_parse_time(row),
                raw={"puborg": row.get("puborg"), "pcode": row.get("pcode")},
            ))
        return items
