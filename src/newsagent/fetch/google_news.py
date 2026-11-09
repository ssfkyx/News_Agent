# =============================================================================
# Module: newsagent.fetch.google_news
# Responsibilities: Google News query adapter (zh/en language routing).
# Dependencies: feedparser, base, normalize
# Dependents: fetch.__init__
# ADRs: ADR-0003
# Traceability: docs/decisions/README.md
# =============================================================================
"""Google News RSS adapter: language/region-specific queries (zh for CN, en for US)."""

from __future__ import annotations

import calendar
import urllib.parse
from datetime import datetime, timezone
from typing import Any

import feedparser

from ..models import RawItem
from ..normalize import clean_text
from .base import Adapter, FetchContext, source_base


class GoogleNewsAdapter(Adapter):
    type = "google_news"

    def fetch(self, source: dict[str, Any], ctx: FetchContext) -> list[RawItem]:
        """Run a Google News RSS query and normalize headlines.

        Preconditions:
            source.query is non-empty; hl/gl/ceid configure language and region.
        Postconditions:
            Raw items with cleaned titles and publish dates.
        Prohibitions:
            Do not bypass language routing; CN queries use zh-CN, US queries en-US.
        Raises:
            RuntimeError on non-200 responses.
        """
        base = source_base(source)
        query = str(source["query"])
        hl = source.get("hl", "en-US")
        gl = source.get("gl", "US")
        ceid = source.get("ceid", "US:en")
        url = (
            "https://news.google.com/rss/search?q=" + urllib.parse.quote(query)
            + f"&hl={hl}&gl={gl}&ceid={ceid}"
        )
        response = ctx.client.get(url)
        if response.status_code != 200:
            raise RuntimeError(f"google_news {source['id']} -> HTTP {response.status_code}")
        feed = feedparser.parse(response.content)

        items: list[RawItem] = []
        for entry in feed.entries[: int(source.get("max_items", 10))]:
            title = clean_text(entry.get("title"))
            link = (entry.get("link") or "").strip()
            if not title or not link:
                continue
            # Google News titles end with " - Source"; keep the headline only.
            if " - " in title:
                head, tail = title.rsplit(" - ", 1)
                if len(tail) <= 30:
                    title = head.strip()
            summary = clean_text(entry.get("summary") or entry.get("description") or "")[:500]
            published = None
            for key in ("published_parsed", "updated_parsed"):
                struct = entry.get(key)
                if struct:
                    published = datetime.fromtimestamp(calendar.timegm(struct), tz=timezone.utc)
                    break
            items.append(RawItem(
                **base,
                title=title,
                url=link,
                summary=summary,
                published_at=published,
                raw={"query": query},
            ))
        return items
