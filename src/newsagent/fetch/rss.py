# =============================================================================
# Module: newsagent.fetch.rss
# Responsibilities: RSS/Atom source adapter.
# Dependencies: feedparser, base, normalize
# Dependents: fetch.__init__
# ADRs: ADR-0003
# Traceability: docs/decisions/README.md
# =============================================================================
"""RSS / Atom adapter."""

from __future__ import annotations

import calendar
from datetime import datetime, timezone
from typing import Any

import feedparser

from ..models import RawItem
from ..normalize import clean_text
from .base import Adapter, FetchContext, source_base


class RssAdapter(Adapter):
    type = "rss"

    def fetch(self, source: dict[str, Any], ctx: FetchContext) -> list[RawItem]:
        """Fetch and parse an RSS/Atom feed into raw items.

        Preconditions:
            source.url is a feed URL; max_items >= 1.
        Postconditions:
            Raw items with UTC publish dates when the feed provides them.
        Prohibitions:
            Do not retry inside the adapter; HttpClient already retries.
        Raises:
            RuntimeError on non-200 responses; feedparser is tolerant of malformed XML.
        """
        base = source_base(source)
        response = ctx.client.get(source["url"])
        if response.status_code != 200:
            raise RuntimeError(f"RSS {source['id']} -> HTTP {response.status_code}")
        feed = feedparser.parse(response.content)
        items: list[RawItem] = []
        limit = int(source.get("max_items", 20))
        for entry in feed.entries[:limit]:
            title = clean_text(entry.get("title"))
            url = (entry.get("link") or "").strip()
            if not title or not url:
                continue
            summary = clean_text(entry.get("summary") or entry.get("description") or "")
            published: datetime | None = None
            for key in ("published_parsed", "updated_parsed"):
                struct = entry.get(key)
                if struct:
                    published = datetime.fromtimestamp(calendar.timegm(struct), tz=timezone.utc)
                    break
            items.append(RawItem(
                **base,
                title=title,
                url=url,
                summary=summary[:500],
                published_at=published,
                raw={"feed_title": feed.feed.get("title", "")},
            ))
        return items
