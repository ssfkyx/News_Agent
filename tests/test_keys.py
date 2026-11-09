# =============================================================================
# Module: tests.test_keys
# Responsibilities: Unit tests for keys.txt parsing, first-run bootstrap and no-overwrite behaviour.
# Dependencies: newsagent.keys, shutil, unittest, uuid
# Dependents: CI/verification
# ADRs: ADR-0014
# Traceability: docs/decisions/README.md
# =============================================================================
"""Tests for the local key-file bootstrap.

Temporary directories are created with default permissions under the workspace
`.tmp/` directory; `tempfile.TemporaryDirectory` is avoided because its 0700
mode hits a restrictive DACL inside the DSH sandbox.
"""

from __future__ import annotations

import shutil
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from newsagent.keys import ensure_key_file, read_key_values  # noqa: E402

WORKSPACE_TMP = ROOT / ".tmp"


class KeyFileTest(unittest.TestCase):
    def setUp(self) -> None:
        WORKSPACE_TMP.mkdir(parents=True, exist_ok=True)
        self.root = WORKSPACE_TMP / f"test-keys-{uuid.uuid4().hex}"
        self.root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_read_key_values_skips_comments_blank_and_empty(self) -> None:
        path = self.root / "keys.txt"
        path.write_text(
            "# comment\n\nDEEPSEEK_API_KEY=sk-test-123\nGITHUB_TOKEN=\nEMPTY =  \n",
            encoding="utf-8",
        )
        values = read_key_values(path)
        self.assertEqual({"DEEPSEEK_API_KEY": "sk-test-123"}, values)

    def test_missing_file_returns_empty_dict(self) -> None:
        values = read_key_values(self.root / "definitely-not-here-keys.txt")
        self.assertEqual({}, values)

    def test_ensure_creates_template_once_and_never_overwrites(self) -> None:
        (self.root / "config").mkdir()
        (self.root / "config" / "keys.example.txt").write_text(
            "# template\nDEEPSEEK_API_KEY=\n", encoding="utf-8"
        )
        path, created = ensure_key_file(self.root)
        self.assertTrue(created)
        self.assertTrue(path.exists())
        path.write_text("DEEPSEEK_API_KEY=user-value\n", encoding="utf-8")
        again, created_again = ensure_key_file(self.root)
        self.assertEqual(path, again)
        self.assertFalse(created_again)
        self.assertIn("user-value", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
