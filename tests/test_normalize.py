# =============================================================================
# Module: tests.test_normalize
# Responsibilities: Unit tests for canonical URLs, freshness gate, simhash and clustering.
# Dependencies: newsagent.normalize, newsagent.dedupe
# Dependents: CI/verification
# ADRs: ADR-0002, ADR-0004
# Traceability: docs/decisions/README.md
# =============================================================================
"""Unit tests for normalization / freshness gate / dedupe."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newsagent.dedupe import build_clusters, hamming  # noqa: E402
from newsagent.models import RawItem  # noqa: E402
from newsagent.normalize import build_item, canonical_url, simhash64  # noqa: E402

NOW = datetime(2026, 11, 8, 20, 0, tzinfo=timezone.utc)


def raw(**overrides) -> RawItem:
    base = dict(
        source_id="openai-news",
        source_name="OpenAI News",
        source_weight=1.3,
        tier="fast",
        title="OpenAI releases a new model",
        url="https://openai.com/index/new-model?utm_source=rss&ref=home",
        summary="A new frontier model with better reasoning.",
        published_at=NOW - timedelta(days=1),
    )
    base.update(overrides)
    return RawItem(**base)


class CanonicalUrlTest(unittest.TestCase):
    def test_strips_tracking_params(self) -> None:
        self.assertEqual(
            canonical_url("https://OpenAI.com/index/x?utm_source=rss&id=7&fbclid=abc#frag"),
            "https://openai.com/index/x?id=7",
        )


class FreshnessGateTest(unittest.TestCase):
    def test_accepts_fresh_item(self) -> None:
        item, reason = build_item(raw(), now=NOW, max_age_days=7, future_tolerance_minutes=60)
        self.assertIsNotNone(item)
        self.assertEqual(reason, "ok")
        self.assertFalse(item.date_estimated)

    def test_rejects_older_than_seven_days(self) -> None:
        item, reason = build_item(
            raw(published_at=NOW - timedelta(days=8)),
            now=NOW, max_age_days=7, future_tolerance_minutes=60,
        )
        self.assertIsNone(item)
        self.assertEqual(reason, "too_old")

    def test_rejects_future_date(self) -> None:
        item, reason = build_item(
            raw(published_at=NOW + timedelta(hours=5)),
            now=NOW, max_age_days=7, future_tolerance_minutes=60,
        )
        self.assertIsNone(item)
        self.assertEqual(reason, "future_date")

    def test_missing_date_falls_back_to_first_seen(self) -> None:
        item, reason = build_item(
            raw(published_at=None), now=NOW, max_age_days=7, future_tolerance_minutes=60,
        )
        self.assertIsNotNone(item)
        self.assertTrue(item.date_estimated)
        self.assertEqual(item.published_at, NOW)

    def test_id_is_stable_for_same_canonical_url(self) -> None:
        first, _ = build_item(raw(), now=NOW, max_age_days=7, future_tolerance_minutes=60)
        second, _ = build_item(
            raw(url="https://openai.com/index/new-model"),
            now=NOW, max_age_days=7, future_tolerance_minutes=60,
        )
        self.assertEqual(first.id, second.id)


class SimhashTest(unittest.TestCase):
    def test_near_duplicate_titles_are_close(self) -> None:
        left = simhash64("OpenAI releases GPT-6 model with better reasoning")
        right = simhash64("OpenAI releases GPT-6 model with better reasoning ability")
        self.assertLessEqual(hamming(left, right), 12)
        self.assertGreater(hamming(left, simhash64("NVIDIA ships a new GPU")), 12)


class DedupeTest(unittest.TestCase):
    def test_same_canonical_url_clusters(self) -> None:
        items = [
            {"canonical_url": "https://a.com/x", "content_hash": "h1", "simhash": 0,
             "title": "Same story", "source_id": "s1", "source_weight": 1.0, "published_at": "2026-11-07T00:00:00Z"},
            {"canonical_url": "https://a.com/x", "content_hash": "h2", "simhash": 1,
             "title": "Same story", "source_id": "s2", "source_weight": 0.9, "published_at": "2026-11-07T01:00:00Z"},
        ]
        clusters = build_clusters(items)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].source_count, 2)


if __name__ == "__main__":
    unittest.main()
