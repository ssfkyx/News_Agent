# =============================================================================
# Module: newsagent.fetch.docs
# Responsibilities: Markdown changelog adapter.
# Dependencies: base
# Dependents: fetch.__init__
# ADRs: ADR-0003
# Traceability: docs/decisions/README.md
# =============================================================================
"""Markdown changelog adapter (e.g. StepFun release notes)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from ..models import RawItem
from .base import Adapter, FetchContext, source_base

DATE_RE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")


class DocsMdAdapter(Adapter):
    type = "docs_md"

    def fetch(self, source: dict[str, Any], ctx: FetchContext) -> list[RawItem]:
        """Parse a markdown changelog into dated raw items.

        Preconditions:
            source.url points to markdown with '## version' sections and Chinese date lines.
        Postconditions:
            Raw items for sections that contain a valid date.
        Prohibitions:
            Do not use on HTML pages.
        Raises:
            RuntimeError on non-200 responses.
        """
        base = source_base(source)
        response = ctx.client.get(source["url"])
        if response.status_code != 200:
            raise RuntimeError(f"docs {source['id']} -> HTTP {response.status_code}")

        items: list[RawItem] = []
        limit = int(source.get("max_items", 5))
        sections = re.split(r"\n(?=##\s)", response.text)
        for section in sections:
            heading_match = re.match(r"##\s+(.+?)\s*\n", section)
            if not heading_match:
                continue
            heading = heading_match.group(1).strip()
            date_match = DATE_RE.search(section)
            if not date_match:
                continue
            year, month, day = (int(part) for part in date_match.groups())
            try:
                published = datetime(year, month, day, tzinfo=timezone.utc)
            except ValueError:
                continue
            body = " ".join(line.strip() for line in section.splitlines()[1:]
                            if line.strip() and not line.strip().startswith(">"))[:400]
            items.append(RawItem(
                **base,
                title=f"{source['name']} {heading}",
                url=source["url"],
                summary=body,
                published_at=published,
                raw={"heading": heading},
            ))
            if len(items) >= limit:
                break
        return items
