# =============================================================================
# Module: newsagent.fetch.base
# Responsibilities: Adapter protocol, fetch context, common helpers.
# Dependencies: models, http
# Dependents: all fetch adapters, fetch.__init__
# ADRs: ADR-0002, ADR-0003
# Traceability: docs/decisions/README.md
# =============================================================================
"""Source adapter interface and fetch context."""

from __future__ import annotations

import email.utils
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..http import HttpClient
from ..models import RawItem


@dataclass
class FetchContext:
    client: HttpClient
    now: datetime
    secrets: dict[str, str]
    max_age_days: int


class Adapter(ABC):
    type: str = "base"

    @abstractmethod
    def fetch(self, source: dict[str, Any], ctx: FetchContext) -> list[RawItem]:
        """Return raw items for one configured source.

        Preconditions:
            source contains the adapter-specific fields declared in config/sources.yaml;
            ctx provides a live HttpClient and the run timestamp.
        Postconditions:
            A list of RawItem values carrying source metadata and optional publish times.
        Prohibitions:
            Do not mutate ctx or shared source configuration; do not swallow HTTP errors silently.
        Raises:
            RuntimeError (or adapter-specific exceptions) when the source cannot be fetched.
        """


def parse_iso(value: str | None) -> datetime | None:
    """Parse ISO-8601 or RFC-822 timestamps to UTC.

    Preconditions:
        value is None or a timestamp string.
    Postconditions:
        Timezone-aware UTC datetime when parseable, otherwise None.
    Prohibitions:
        Do not assume local time; naive values are treated as UTC.
    Raises:
        None (parse failures return None).
    """
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def source_base(source: dict[str, Any]) -> dict[str, Any]:
    """Copy common source fields into a RawItem kwargs dict.

    Preconditions:
        source has at least an id; weight/tier/section_hint are optional.
    Postconditions:
        Dict with source_id/source_name/source_weight/tier/section_hint.
    Prohibitions:
        Do not mutate the returned dict for other sources.
    Raises:
        KeyError when source id is missing.
    """
    return {
        "source_id": source["id"],
        "source_name": source.get("name") or source["id"],
        "source_weight": float(source.get("weight", 1.0)),
        "tier": source.get("tier", "standard"),
        "section_hint": source.get("section_hint", "tech"),
    }
