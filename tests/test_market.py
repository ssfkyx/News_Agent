# =============================================================================
# Module: tests.test_market
# Responsibilities: Unit tests for kline parsing, change calculation and sparkline geometry.
# Dependencies: newsagent.market, unittest
# Dependents: CI/verification
# ADRs: ADR-0015
# Traceability: docs/decisions/README.md
# =============================================================================
"""Tests for the fixed-watchlist market layer (no network calls)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from newsagent.market import build_market_item, parse_klines, sort_watchlist, sparkline_points  # noqa: E402


class MarketParseTest(unittest.TestCase):
    def test_sort_watchlist_china_then_us_with_nvidia_first_in_us(self) -> None:
        watchlist = [
            {"id": "tsla", "country": "US", "sort_name": "Tesla"},
            {"id": "msft", "country": "US", "sort_name": "Microsoft"},
            {"id": "amzn", "country": "US", "sort_name": "Amazon"},
            {"id": "nvda", "country": "US", "sort_name": "NVIDIA", "pinned": True},
            {"id": "tencent", "country": "CN", "sort_name": "Tengxun Konggu"},
            {"id": "alibaba", "country": "CN", "sort_name": "Alibaba"},
            {"id": "zhipu", "country": "CN", "sort_name": "Zhipu"},
            {"id": "baidu", "country": "CN", "sort_name": "Baidu"},
        ]
        ordered = [watch["id"] for watch in sort_watchlist(watchlist)]
        self.assertEqual(
            ["alibaba", "baidu", "tencent", "zhipu", "nvda", "amzn", "msft", "tsla"],
            ordered,
        )

    def test_parse_klines_returns_last_n_closes(self) -> None:
        payload = {"data": {"klines": [
            "2026-11-06,100.0,101.5,102.0,99.0,10,1000",
            "2026-11-09,101.0,103.0,104.0,100.0,11,1100",
        ]}}
        points = parse_klines(payload, days=1)
        self.assertEqual([{"date": "2026-11-09", "close": 103.0}], points)

    def test_parse_klines_ignores_malformed_rows(self) -> None:
        payload = {"data": {"klines": ["bad", "2026-11-09,101.0,103.0,104.0,100.0,11,1100"]}}
        self.assertEqual(1, len(parse_klines(payload)))

    def test_build_item_exposes_latest_close_and_date(self) -> None:
        watch = {"id": "nvda", "name": "英伟达", "code": "NVDA", "market": "美股", "currency": "USD"}
        points = [{"date": "2026-11-06", "close": 100.0}, {"date": "2026-11-09", "close": 110.0}]
        item = build_market_item(watch, points)
        self.assertIsNotNone(item)
        self.assertEqual(110.0, item["latest"])
        self.assertEqual("2026-11-09", item["latest_date"])
        self.assertEqual("NVDA", item["code"])
        self.assertNotIn("change_pct", item)

    def test_build_item_returns_none_without_points(self) -> None:
        self.assertIsNone(build_market_item({"id": "x"}, []))

    def test_sparkline_flat_line_is_vertical_center(self) -> None:
        points = [{"date": "d1", "close": 100.0}, {"date": "d2", "close": 100.0},
                  {"date": "d3", "close": 100.0}]
        coordinates = sparkline_points(points, width=220, height=64, pad=4).split()
        self.assertEqual(3, len(coordinates))
        ys = [float(pair.split(",")[1]) for pair in coordinates]
        self.assertTrue(all(abs(y - 32.0) < 0.01 for y in ys))
        xs = [float(pair.split(",")[0]) for pair in coordinates]
        self.assertAlmostEqual(4.0, xs[0], places=1)
        self.assertAlmostEqual(216.0, xs[-1], places=1)


if __name__ == "__main__":
    unittest.main()
