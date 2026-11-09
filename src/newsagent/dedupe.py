# =============================================================================
# Module: newsagent.dedupe
# Responsibilities: Near-duplicate detection and union-find clustering.
# Dependencies: none
# Dependents: select
# ADRs: ADR-0004
# Traceability: docs/decisions/README.md
# =============================================================================
"""Near-duplicate detection / clustering for the 7-day candidate pool."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]")


def _title_tokens(title: str) -> set[str]:
    lowered = (title or "").lower()
    tokens = set(TOKEN_RE.findall(lowered))
    if not tokens:
        return set()
    # Chinese text benefits from character bigrams as well
    cjk = "".join(re.findall(r"[\u4e00-\u9fff]", lowered))
    if len(cjk) >= 2:
        tokens.update(cjk[i:i + 2] for i in range(len(cjk) - 1))
    return tokens


def jaccard(left: set[str], right: set[str]) -> float:
    """Jaccard similarity of two token sets.

    Preconditions:
        left/right are sets of strings and may be empty.
    Postconditions:
        Float in [0.0, 1.0] (FP64); 0.0 when either side is empty.
    Prohibitions:
        Do not mutate the input sets.
    Raises:
        None.
    """
    if not left or not right:
        return 0.0
    union = len(left | right)
    return len(left & right) / union if union else 0.0


def hamming(left: int, right: int) -> int:
    # Stored simhash may be signed 64-bit (SQLite); mask to the 64-bit pattern.
    """Hamming distance between two 64-bit simhash values.

    Preconditions:
        left/right are integers; signed SQLite storage is allowed.
    Postconditions:
        Integer in [0, 64].
    Prohibitions:
        Do not pass values wider than 64 bits.
    Raises:
        None.
    """
    return ((left ^ right) & 0xFFFFFFFFFFFFFFFF).bit_count()


@dataclass
class Cluster:
    rep_index: int
    indices: list[int] = field(default_factory=list)
    source_count: int = 1


def build_clusters(items: list[dict[str, Any]]) -> list[Cluster]:
    """Cluster items by exact URL/hash, simhash and title similarity.

    Preconditions:
        items are normalized row dicts containing canonical_url, content_hash, simhash, title, source_id.
    Postconditions:
        Clusters with a representative index and distinct source count.
    Prohibitions:
        Do not call on more than a few hundred candidates (O(n^2)).
    Raises:
        KeyError when required keys are missing.
    """
    n = len(items)
    parent = list(range(n))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    tokens = [_title_tokens(item.get("title") or "") for item in items]

    for i, j in combinations(range(n), 2):
        left, right = items[i], items[j]
        if left["canonical_url"] == right["canonical_url"] or left["content_hash"] == right["content_hash"]:
            union(i, j)
            continue
        if hamming(int(left["simhash"]), int(right["simhash"])) <= 3 and jaccard(tokens[i], tokens[j]) >= 0.5:
            union(i, j)
            continue
        if jaccard(tokens[i], tokens[j]) >= 0.8:
            union(i, j)

    groups: dict[int, list[int]] = {}
    for index in range(n):
        groups.setdefault(find(index), []).append(index)

    clusters: list[Cluster] = []
    for indices in groups.values():
        sources = {items[index]["source_id"] for index in indices}
        # Representative: highest source weight, then earliest published
        rep = max(
            indices,
            key=lambda index: (float(items[index].get("source_weight") or 0), items[index].get("published_at") or ""),
        )
        clusters.append(Cluster(rep_index=rep, indices=indices, source_count=len(sources)))
    return clusters
