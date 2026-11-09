# =============================================================================
# Module: newsagent.keys
# Responsibilities: Read the local keys.txt file and bootstrap it from the template on first run.
# Dependencies: none (stdlib only)
# Dependents: config, cli, web.server
# ADRs: ADR-0014
# Traceability: docs/decisions/README.md
# =============================================================================
"""Local key-file reader and first-run bootstrap.

Users put their own API keys in a git-ignored `keys.txt` at the project root.
On first run the file is created from `config/keys.example.txt` with empty
values, so the software never ships credentials.
"""

from __future__ import annotations

from pathlib import Path

KEY_FILENAME = "keys.txt"
TEMPLATE_RELPATH = Path("config") / "keys.example.txt"

DEFAULT_TEMPLATE = """# AI News Agent 本地密钥文件（本文件已被 .gitignore 忽略，请勿提交到 git）
# 每行 KEY=VALUE；= 后面直接写 key，不要加引号或空格。

# DeepSeek API Key（必填，用于生成日报摘要；以 sk- 开头）
DEEPSEEK_API_KEY=

# GitHub 只读 token（可选但建议；用于提高 API 限额）
GITHUB_TOKEN=
"""


def read_key_values(path: Path) -> dict[str, str]:
    """Read KEY=VALUE pairs from a local key file.

    Preconditions:
        path points to an optional text file in `KEY=VALUE` format; it may not exist.
    Postconditions:
        A dict of non-empty keys to values; comments, blank lines and empty values
        are ignored. A missing file yields an empty dict.
    Prohibitions:
        Do not log or return values through any user-facing report; callers must
        treat these values as secrets.
    Raises:
        OSError when the file exists but cannot be read.
    """
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value:
            values[key] = value
    return values


def ensure_key_file(root: Path) -> tuple[Path, bool]:
    """Create the local `keys.txt` from the template when it does not exist yet.

    Preconditions:
        root is the project root directory and is writable.
    Postconditions:
        Returns (keys.txt path, created). When created=True a template with empty
        values has been written; existing files are never overwritten.
    Prohibitions:
        Do not overwrite an existing keys.txt and never embed real credentials in
        the template.
    Raises:
        OSError when the template or target cannot be read/written.
    """
    target = root / KEY_FILENAME
    if target.exists():
        return target, False
    template = root / TEMPLATE_RELPATH
    content = template.read_text(encoding="utf-8-sig") if template.exists() else DEFAULT_TEMPLATE
    target.write_text(content, encoding="utf-8")
    return target, True
