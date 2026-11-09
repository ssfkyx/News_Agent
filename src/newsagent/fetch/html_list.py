# =============================================================================
# Module: newsagent.fetch.html_list
# Responsibilities: Generic static HTML list adapter.
# Dependencies: base, normalize
# Dependents: fetch.__init__
# ADRs: ADR-0003
# Traceability: docs/decisions/README.md
# =============================================================================
"""Generic static HTML list adapter (e.g. CAC policy/news list)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

from ..models import RawItem
from ..normalize import clean_text
from .base import Adapter, FetchContext, source_base

ANCHOR_RE = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S)
URL_DATE_RE = re.compile(r"/(20\d{2})-(\d{2})/(\d{2})/")


class HtmlListAdapter(Adapter):
    type = "html_list"

    def fetch(self, source: dict[str, Any], ctx: FetchContext) -> list[RawItem]:
        """Extract dated links from a static HTML list page.

        Preconditions:
            source.url returns HTML; link_pattern filters anchors; max_items >= 1.
        Postconditions:
            Raw items with dates parsed from the URL when present.
        Prohibitions:
            Do not use on JS-rendered pages.
        Raises:
            RuntimeError on non-200 responses.
        """
        base = source_base(source)
        response = ctx.client.get(source["url"])
        if response.status_code != 200:
            raise RuntimeError(f"html_list {source['id']} -> HTTP {response.status_code}")
        link_pattern = source.get("link_pattern")
        limit = int(source.get("max_items", 5))
        items: list[RawItem] = []
        seen: set[str] = set()
        for href, raw_title in ANCHOR_RE.findall(response.text):
            if link_pattern and not re.search(link_pattern, href):
                continue
            title = clean_text(raw_title)
            if not title or not (6 <= len(title) <= 120):
                continue
            url = urljoin(source["url"], href)
            if url in seen:
                continue
            seen.add(url)
            published = None
            match = URL_DATE_RE.search(href)
            if match:
                try:
                    published = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)),
                                         tzinfo=timezone.utc)
                except ValueError:
                    published = None
            items.append(RawItem(**base, title=title, url=url, summary="", published_at=published))
            if len(items) >= limit:
                break
        return items
