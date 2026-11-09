# =============================================================================
# Module: tests.test_report_fp64
# Responsibilities: Unit tests for Report projection and the FP64 numeric policy.
# Dependencies: newsagent.report
# Dependents: CI/verification
# ADRs: ADR-0008, ADR-0012
# Traceability: docs/decisions/README.md
# =============================================================================
"""FP64 policy + Report object unit tests."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newsagent.report import build_report  # noqa: E402

NOW = datetime(2026, 11, 8, 20, 0, tzinfo=timezone.utc)


def item(**overrides):
    base = {
        "id": "a1", "title": "OpenAI releases model", "title_zh": "OpenAI 发布模型",
        "summary": "sum", "summary_zh": "摘要", "url": "https://example.com/a",
        "source_name": "OpenAI News", "published_at": "2026-11-08T10:00:00Z",
        "topic": "模型发布", "company": "OpenAI", "importance": 3,
        "section": "tech", "score": 1.25,
    }
    base.update(overrides)
    return base


class FP64PolicyTest(unittest.TestCase):
    def test_python_float_is_fp64(self) -> None:
        # Requirement: floating point numbers must be FP64 uniformly.
        self.assertEqual(sys.float_info.mant_dig, 53)
        self.assertEqual(sys.float_info.max_exp, 1024)

    def test_report_scores_are_fp64(self) -> None:
        report = build_report([item(importance=5, score=0.1 + 0.2)], now=NOW,
                              window_days=7, stats={}, degraded=False)
        for view in report["leads"]:
            self.assertIsInstance(view["score"], float)
            self.assertEqual(view["score"], 0.1 + 0.2)  # binary64 keeps this value


class ReportTest(unittest.TestCase):
    def test_leads_are_top_importance_first(self) -> None:
        report = build_report(
            [item(id="low", importance=2), item(id="high", importance=5, section="policy")],
            now=NOW, window_days=7, stats={}, degraded=False,
        )
        self.assertEqual(report["leads"][0]["id"], "high")

    def test_four_sections_are_present(self) -> None:
        report = build_report([item()], now=NOW, window_days=7, stats={}, degraded=False)
        self.assertEqual([section["key"] for section in report["sections"]],
                         ["tech", "finance", "policy", "embodied"])

    def test_section_items_are_routed_by_section_field(self) -> None:
        report = build_report(
            [item(id="f", section="finance"), item(id="p", section="policy"),
             item(id="e", section="embodied")],
            now=NOW, window_days=7, stats={}, degraded=False,
        )
        mapping = {section["key"]: [view["id"] for view in section["items"]]
                   for section in report["sections"]}
        self.assertEqual(mapping["finance"], ["f"])
        self.assertEqual(mapping["policy"], ["p"])
        self.assertEqual(mapping["embodied"], ["e"])


if __name__ == "__main__":
    unittest.main()
