# =============================================================================
# Module: tests.test_traceability
# Responsibilities: Enforce file headers, ADR references, structured public docstrings and ADR integrity.
# Dependencies: ast, pathlib, unittest, the repository layout.
# Dependents: CI/verification (run with `python -m unittest discover -s tests`).
# ADRs: ADR-0001, ADR-0014
# Traceability: docs/decisions/README.md
# =============================================================================
"""Traceability constraints enforced as executable checks.

Coding Phase #2 requires: every code/config file has a traceability header,
every public function in `src/` (plus tools and docs helpers) has a structured
docstring, and every ADR is complete, sequential and referenced from code.

Preconditions:
    The repository layout matches the documented structure (src/, ui/, scripts/,
    config/, tests/, tools/, docs/decisions/).
Postconditions:
    Assertion failures identify the offending file/function/ADR.
Prohibitions:
    Do not weaken these checks to make the suite pass; fix the code instead.
Raises:
    AssertionError for any violated traceability rule.
"""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECISIONS = ROOT / "docs" / "decisions"

PUBLIC_SOURCES = [
    *sorted((ROOT / "src").rglob("*.py")),
    ROOT / "tools" / "sitecustomize.py",
    ROOT / "docs" / "make_ui_mockup.py",
]

HEADER_FILES = [
    *sorted((ROOT / "src").rglob("*.py")),
    *sorted((ROOT / "ui").rglob("*.*")),
    *sorted((ROOT / "scripts").glob("*")),
    *sorted((ROOT / "config").glob("*.yaml")),
    *sorted((ROOT / "tests").glob("*.py")),
    ROOT / "tools" / "sitecustomize.py",
    ROOT / "docs" / "make_ui_mockup.py",
    ROOT / "pyproject.toml",
]

REQUIRED_HEADER_FIELDS = ("Module:", "Responsibilities:", "Dependencies:", "Dependents:", "ADRs:")
ADR_REF_RE = re.compile(r"ADR-\d{4}")


def _public_functions(tree: ast.Module):
    """Yield (qualname, node) for public module functions and class methods.

    Preconditions:
        tree is a parsed Python module.
    Postconditions:
        Yields module-level functions and methods of top-level and nested classes,
        skipping names starting with an underscore.
    Prohibitions:
        Do not descend into function-local definitions (they are implementation details).
    Raises:
        None.
    """
    def walk(body, prefix=""):
        for node in body:
            if isinstance(node, ast.ClassDef):
                yield from walk(node.body, prefix + node.name + ".")
            elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                yield prefix + node.name, node

    yield from walk(tree.body)


class HeaderTest(unittest.TestCase):
    """Verify every code/config/UI file carries a traceability header."""

    def test_headers_exist_and_reference_existing_adrs(self) -> None:
        """Each file header lists the required fields and references existing ADRs.

        Preconditions:
            HEADER_FILES points at existing repository files.
        Postconditions:
            All headers contain Module/Responsibilities/Dependencies/Dependents/ADRs and
            every referenced ADR file exists under docs/decisions/.
        Prohibitions:
            Do not skip files silently; missing files fail the assertion.
        Raises:
            AssertionError listing offending files.
        """
        errors = []
        existing = {path.name[:8] for path in DECISIONS.glob("ADR-*.md")}
        for path in HEADER_FILES:
            text = path.read_text(encoding="utf-8")
            head = text[:1600]
            missing = [field for field in REQUIRED_HEADER_FIELDS if field not in head]
            if "Traceability: docs/decisions/README.md" not in head:
                missing.append("Traceability footer")
            refs = set(ADR_REF_RE.findall(head))
            unknown = sorted(ref for ref in refs if ref not in existing)
            if missing or unknown:
                errors.append(f"{path.relative_to(ROOT)}: missing={missing} unknown_adrs={unknown}")
        self.assertEqual([], errors, "\n".join(errors))


class DocstringTest(unittest.TestCase):
    """Verify structured docstrings for public functions in production code."""

    def test_public_functions_have_structured_docstrings(self) -> None:
        """Every public function in src/tools/docs has summary + pre/post/prohibitions/raises.

        Preconditions:
            PUBLIC_SOURCES lists the production/helper Python files.
        Postconditions:
            No violations; failed functions are reported with file and qualname.
        Prohibitions:
            Test methods are excluded because tests are verification code, not public API.
        Raises:
            AssertionError listing offending functions.
        """
        required = ["Preconditions:", "Postconditions:", "Prohibitions:", "Raises:"]
        errors = []
        for path in PUBLIC_SOURCES:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for qualname, node in _public_functions(tree):
                doc = ast.get_docstring(node) or ""
                if not doc.strip():
                    errors.append(f"{path.relative_to(ROOT)}::{qualname}: missing docstring")
                    continue
                missing = [section for section in required if section not in doc]
                if missing:
                    errors.append(f"{path.relative_to(ROOT)}::{qualname}: missing {missing}")
        self.assertEqual([], errors, "\n".join(errors))


class AdrTest(unittest.TestCase):
    """Verify ADR numbering, required sections and bidirectional references."""

    def test_adr_files_are_sequential_and_complete(self) -> None:
        """ADR files are numbered 0001..N without gaps and contain the required sections.

        Preconditions:
            docs/decisions/ADR-*.md exists.
        Postconditions:
            Filenames are sequential and each ADR has Status/Context/Decision/Rationale/
            Consequences/Code locations sections.
        Prohibitions:
            Do not allow unnumbered or duplicate ADR numbers.
        Raises:
            AssertionError listing offending ADRs.
        """
        files = sorted(DECISIONS.glob("ADR-*.md"))
        self.assertTrue(files, "no ADR files found")
        numbers = [int(path.name[4:8]) for path in files]
        self.assertEqual(list(range(1, len(numbers) + 1)), numbers, "ADR numbering must be sequential")
        required = ["## Context", "## Decision", "## Rationale", "## Consequences (Costs)",
                    "## Code locations (traceability)"]
        errors = []
        for path in files:
            text = path.read_text(encoding="utf-8")
            missing = [section for section in required if section not in text]
            if "**Status:** Accepted" not in text:
                missing.append("Status: Accepted")
            if missing:
                errors.append(f"{path.name}: missing {missing}")
        self.assertEqual([], errors, "\n".join(errors))

    def test_every_adr_is_referenced_from_code(self) -> None:
        """Each ADR is cited by at least one source/config/script/UI header.

        Preconditions:
            HEADER_FILES and ADR files exist.
        Postconditions:
            For each ADR id, at least one header in HEADER_FILES references it.
        Prohibitions:
            Do not satisfy this by adding references to ADR files themselves.
        Raises:
            AssertionError listing unreferenced ADRs.
        """
        referenced = set()
        for path in HEADER_FILES:
            referenced.update(ADR_REF_RE.findall(path.read_text(encoding="utf-8")[:1600]))
        adr_ids = {path.name[:8] for path in DECISIONS.glob("ADR-*.md")}
        missing = sorted(adr_ids - referenced)
        self.assertEqual([], missing, f"ADRs not referenced from code headers: {missing}")


if __name__ == "__main__":
    unittest.main()
