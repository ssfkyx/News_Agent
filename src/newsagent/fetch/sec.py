# =============================================================================
# Module: newsagent.fetch.sec
# Responsibilities: SEC EDGAR 8-K Atom adapter (hard financial information).
# Dependencies: base
# Dependents: fetch.__init__
# ADRs: ADR-0003, ADR-0011
# Traceability: docs/decisions/README.md
# =============================================================================
"""SEC EDGAR 8-K Atom adapter (official financial filings)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from ..models import RawItem
from .base import Adapter, FetchContext, parse_iso, source_base

ATOM = "{http://www.w3.org/2005/Atom}"


class Sec8kAdapter(Adapter):
    type = "sec_8k"

    def fetch(self, source: dict[str, Any], ctx: FetchContext) -> list[RawItem]:
        """Fetch SEC EDGAR 8-K Atom filings for one CIK.

        Preconditions:
            source.cik is a valid 10-digit CIK; a descriptive user agent is configured.
        Postconditions:
            Raw items pointing at filing index pages.
        Prohibitions:
            Do not exceed SEC rate limits or omit the contact user agent.
        Raises:
            RuntimeError on non-200 or invalid Atom XML.
        """
        base = source_base(source)
        cik = str(source["cik"]).zfill(10)
        url = (
            "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
            f"&CIK={cik}&type=8-K&output=atom"
        )
        response = ctx.client.get(url)
        if response.status_code != 200:
            raise RuntimeError(f"sec_8k {source['id']} -> HTTP {response.status_code}")
        root = ET.fromstring(response.content)

        items: list[RawItem] = []
        for entry in root.findall(f"{ATOM}entry")[: int(source.get("max_items", 5))]:
            filing_title = (entry.findtext(f"{ATOM}title") or "8-K").strip()
            updated = parse_iso(entry.findtext(f"{ATOM}updated"))
            link_element = entry.find(f"{ATOM}link")
            href = (link_element.get("href") if link_element is not None else "") or url
            company = source.get("name") or source["id"]
            items.append(RawItem(
                **base,
                title=f"{company} 提交 SEC 8-K 公告",
                url=href,
                summary=f"{filing_title}；SEC EDGAR 原始文件（财务/重大事项）",
                published_at=updated,
                raw={"cik": cik},
            ))
        return items
