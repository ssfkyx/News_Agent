# =============================================================================
# Module: newsagent.models
# Responsibilities: Domain records (RawItem/NormalizedItem), LLM output schemas (LLMItem/MergeGroup), section aliases.
# Dependencies: pydantic
# Dependents: normalize, fetch adapters, enrich, report, store, select
# ADRs: ADR-0001, ADR-0002, ADR-0006, ADR-0011, ADR-0016
# Traceability: docs/decisions/README.md
# =============================================================================
"""Data models shared across fetch / normalize / enrich."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


@dataclass
class RawItem:
    """One item as returned by a source adapter (before normalization)."""

    source_id: str
    source_name: str
    source_weight: float
    tier: str
    title: str
    url: str
    summary: str = ""
    published_at: datetime | None = None
    section_hint: str = "tech"
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedItem:
    """One item after normalization + 7-day freshness gate."""

    id: str
    source_id: str
    source_name: str
    source_weight: float
    title: str
    summary: str
    url: str
    canonical_url: str
    published_at: datetime
    date_estimated: bool
    first_seen_at: datetime
    last_seen_at: datetime
    lang: str
    content_hash: str
    simhash: int
    section_hint: str = "tech"


SECTION_ALIASES = {
    "tech": "tech", "科技": "tech", "科技与产品": "tech", "产品": "tech", "技术": "tech",
    "finance": "finance", "financial": "finance", "财务": "finance", "资本": "finance",
    "融资": "finance", "投资": "finance",
    "policy": "policy", "政策": "policy", "监管": "policy", "政府": "policy",
    "embodied": "embodied", "具身智能": "embodied", "机器人": "embodied",
    "人形机器人": "embodied", "robotics": "embodied", "robot": "embodied",
}


class LLMItem(BaseModel):
    """Validated item returned by the LLM enrich stage."""

    id: str
    title_zh: str = ""
    summary_zh: str = ""
    topic: str = "其他"
    company: str = "其他"
    importance: int = 3
    section: str = "tech"

    @field_validator("importance", mode="before")
    @classmethod
    def _clamp(cls, value: Any) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return 3
        return max(1, min(5, number))

    @field_validator("section", mode="before")
    @classmethod
    def _normalize_section(cls, value: Any) -> str:
        return SECTION_ALIASES.get(str(value or "").strip().lower(), "tech")


class MergeGroup(BaseModel):
    """One same-event group returned by the LLM merge pass."""

    ids: list[str]
    keep: str = ""
    reason: str = ""

