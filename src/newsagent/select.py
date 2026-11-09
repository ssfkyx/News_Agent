# =============================================================================
# Module: newsagent.select
# Responsibilities: Candidate scoring, quotas and section balancing.
# Dependencies: dedupe, store
# Dependents: pipeline
# ADRs: ADR-0005, ADR-0016
# Traceability: docs/decisions/README.md
# =============================================================================
"""Candidate ranking: 7-day window, recency decay, source weight, cluster heat, quotas."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from .dedupe import build_clusters
from .store import from_db


def rank_and_select(
    candidates: list[dict[str, Any]],
    *,
    now: datetime,
    top_n: int,
    per_source_max: int,
    max_total_chars: int = 40000,
    source_kind: dict[str, str] | None = None,
    kind_quotas: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Score clusters and apply source/kind quotas to build an enrich pool.

    Preconditions:
        candidates are normalized rows; quotas/windows are positive integers.
    Postconditions:
        Selected row dicts annotated with score and cluster source count.
    Prohibitions:
        Do not exceed the configured char budget; do not reorder sections here.
    Raises:
        None.
    """
    if not candidates:
        return []

    source_kind = source_kind or {}
    kind_quotas = kind_quotas or {}
    clusters = build_clusters(candidates)
    scored: list[tuple[float, Any]] = []

    for cluster in clusters:
        rep = candidates[cluster.rep_index]
        published = from_db(rep["published_at"])
        age_hours = max(0.0, (now - published).total_seconds() / 3600.0)
        recency = math.exp(-age_hours / 72.0)  # 3-day half-life-ish decay
        heat = 1.0 + 0.15 * (cluster.source_count - 1)
        score = float(rep.get("source_weight") or 0.5) * recency * heat
        scored.append((score, cluster))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    chosen: list[dict[str, Any]] = []
    per_source: dict[str, int] = {}
    per_kind: dict[str, int] = {}
    total_chars = 0

    for score, cluster in scored:
        if len(chosen) >= top_n:
            break
        rep = dict(candidates[cluster.rep_index])
        source_id = rep["source_id"]
        kind = source_kind.get(source_id, "")
        if per_source.get(source_id, 0) >= per_source_max:
            continue
        if kind and kind in kind_quotas and per_kind.get(kind, 0) >= kind_quotas[kind]:
            continue
        chars = len(rep.get("title") or "") + len(rep.get("summary") or "")
        if total_chars + chars > max_total_chars:
            continue
        rep["score"] = round(score, 4)
        rep["cluster_source_count"] = cluster.source_count
        chosen.append(rep)
        per_source[source_id] = per_source.get(source_id, 0) + 1
        if kind:
            per_kind[kind] = per_kind.get(kind, 0) + 1
        total_chars += chars

    return chosen


SECTION_ORDER = ("tech", "finance", "policy", "embodied")


def balance_sections(
    items: list[dict[str, Any]],
    *,
    quotas: dict[str, int],
    top_n: int,
) -> list[dict[str, Any]]:
    """Take a balanced digest slice across the four sections.

    Preconditions:
        items are enriched (section present); quotas is a mapping section -> int.
    Postconditions:
        Selected items up to top_n, preserving section quotas then filling leftovers.
    Prohibitions:
        Do not use before enrichment (section unknown).
    Raises:
        None.
    """
    if not items:
        return []
    buckets: dict[str, list[dict[str, Any]]] = {key: [] for key in SECTION_ORDER}
    for item in items:
        section = str(item.get("section") or item.get("section_hint") or "tech")
        buckets.setdefault(section if section in buckets else "tech", []).append(item)

    def rank(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            entries,
            key=lambda entry: (
                -int(entry.get("importance") or 0),
                -float(entry.get("score") or 0),
            ),
        )

    chosen: list[dict[str, Any]] = []
    used: set[str] = set()
    for section in SECTION_ORDER:
        quota = int(quotas.get(section, 0))
        for item in rank(buckets[section])[:quota]:
            chosen.append(item)
            used.add(item["id"])

    if len(chosen) < top_n:
        leftovers = rank([item for item in items if item["id"] not in used])
        chosen.extend(leftovers[: top_n - len(chosen)])
    return chosen
