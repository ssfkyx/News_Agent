# =============================================================================
# Module: tests.test_notify
# Responsibilities: Unit tests for email rendering (no SMTP network calls).
# Dependencies: newsagent.notify, newsagent.report
# Dependents: CI/verification
# ADRs: ADR-0013
# Traceability: docs/decisions/README.md
# =============================================================================
"""Email rendering tests (no SMTP network calls)."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newsagent.config import load_config  # noqa: E402
from newsagent.notify import build_email  # noqa: E402
from newsagent.report import build_report  # noqa: E402

NOW = datetime(2026, 11, 8, 20, 0, tzinfo=timezone.utc)


def item(**overrides):
    base = {
        "id": "a1", "title": "OpenAI releases model", "title_zh": "OpenAI 发布新模型",
        "summary": "sum", "summary_zh": "一句话摘要", "url": "https://example.com/a",
        "source_name": "OpenAI News", "published_at": "2026-11-08T10:00:00Z",
        "topic": "模型发布", "company": "OpenAI", "importance": 4,
        "section": "tech", "score": 1.0, "also_reported": 1,
    }
    base.update(overrides)
    return base


class EmailTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config()
        self.report = build_report(
            [
                item(),
                item(id="f1", section="finance", company="Meta", title_zh="Meta 提交 8-K"),
                item(id="p1", section="policy", company="美国政府", title_zh="政策更新"),
            ],
            now=NOW, window_days=7, stats={"model": "deepseek-flash"}, degraded=False,
            max_leads=10, windows={"tech": 7, "finance": 30, "policy": 90},
        )

    def test_recipient_and_subject(self) -> None:
        message = build_email(self.config, self.report, "# markdown")
        self.assertEqual(message["To"], "your-email@example.com")
        self.assertIn("AI 新闻日报", message["Subject"])
        self.assertIn("2026-11-08", message["Subject"])

    def test_html_body_contains_sections_and_lead(self) -> None:
        message = build_email(self.config, self.report, "# markdown")
        html = ""
        for part in message.walk():
            if part.get_content_type() == "text/html":
                html = part.get_payload(decode=True).decode("utf-8")
                break
        self.assertIn("科技与产品", html)
        self.assertIn("财务与资本", html)
        self.assertIn("政府与监管", html)
        self.assertIn("OpenAI 发布新模型", html)
        self.assertIn("另有 1 家报道", html)

    def test_plain_text_fallback_present(self) -> None:
        message = build_email(self.config, self.report, "# markdown report")
        plain = ""
        for part in message.walk():
            if part.get_content_type() == "text/plain":
                plain = part.get_payload(decode=True).decode("utf-8")
                break
        self.assertIn("markdown report", plain)


if __name__ == "__main__":
    unittest.main()
