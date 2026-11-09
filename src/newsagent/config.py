# =============================================================================
# Module: newsagent.config
# Responsibilities: Settings/sources/secrets loading and the Config value object.
# Dependencies: yaml, os
# Dependents: pipeline, enrich, notify, trend, cli, web.server
# ADRs: ADR-0014
# Traceability: docs/decisions/README.md
# =============================================================================
"""Config loading: settings.yaml + sources.yaml + secrets from env/.env/"ds_key.txt"."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .keys import read_key_values

ROOT = Path(__file__).resolve().parents[2]


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@dataclass
class Config:
    root: Path
    settings: dict[str, Any]
    sources: list[dict[str, Any]]
    secrets: dict[str, str]

    def get(self, dotted: str, default: Any = None) -> Any:
        """Read a nested settings value by dotted path.

        Preconditions:
            dotted is a non-empty 'a.b.c' string; default is returned when any segment is missing.
        Postconditions:
            The nested value or the supplied default.
        Prohibitions:
            Do not use for secrets (use Config.secret instead).
        Raises:
            None (returns default instead of raising).
        """
        current: Any = self.settings
        for part in dotted.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def path(self, dotted: str, default: str) -> Path:
        """Resolve a dotted settings path to an absolute path under the project root.

        Preconditions:
            dotted names a string path configuration value; default is a fallback path string.
        Postconditions:
            Absolute Path under Config.root.
        Prohibitions:
            Do not use with untrusted absolute paths that could escape the project.
        Raises:
            None.
        """
        return self.root / str(self.get(dotted, default))

    @property
    def db_path(self) -> Path:
        """Absolute path of the SQLite database.

        Preconditions:
            settings.paths.db_path exists (default data/news.db).
        Postconditions:
            Path under project root.
        Prohibitions:
            Do not open the file from here.
        Raises:
            None.
        """
        return self.root / str(self.get("paths.db_path", "data/news.db"))

    @property
    def out_dir(self) -> Path:
        """Absolute path of the report output directory.

        Preconditions:
            settings.paths.out_dir exists (default out).
        Postconditions:
            Path under project root.
        Prohibitions:
            Do not create the directory inside this property.
        Raises:
            None.
        """
        return self.root / str(self.get("paths.out_dir", "out"))

    @property
    def raw_dir(self) -> Path:
        """Absolute path reserved for raw fetch snapshots.

        Preconditions:
            settings.paths.raw_dir exists (default data/raw).
        Postconditions:
            Path under project root.
        Prohibitions:
            Do not assume the directory exists.
        Raises:
            None.
        """
        return self.root / str(self.get("paths.raw_dir", "data/raw"))

    @property
    def prompt_path(self) -> Path:
        """Absolute path of the versioned enrich prompt file.

        Preconditions:
            llm.prompt_version is configured (default enrich_v2).
        Postconditions:
            Path of config/prompts/<version>.md.
        Prohibitions:
            Do not write to the prompt from runtime code.
        Raises:
            None.
        """
        version = str(self.get("llm.prompt_version", "enrich_v1"))
        return self.root / "config" / "prompts" / f"{version}.md"

    def secret(self, name: str, fallback_file: str | None = None) -> str | None:
        """Resolve a secret from keys.txt/.env/environment, then an optional fallback file.

        Preconditions:
            name is an environment-style key; fallback_file is relative to the project root when provided.
        Postconditions:
            Secret string, or None when nothing is configured.
        Prohibitions:
            Never log, print, persist or commit the returned secret.
        Raises:
            OSError if a configured fallback file cannot be read.
        """
        value = self.secrets.get(name)
        if value:
            return value
        if fallback_file:
            path = self.root / fallback_file
            if path.exists():
                text = path.read_text(encoding="utf-8").strip()
                if text:
                    return text.splitlines()[0].strip()
        return None

    def llm_api_key(self) -> str | None:
        """Resolve the key for any OpenAI-compatible LLM endpoint.

        Preconditions:
            keys.txt/.env/environment may define LLM_API_KEY, DEEPSEEK_API_KEY or
            OPENAI_API_KEY; a local ds_key.txt is an optional last resort.
        Postconditions:
            The first configured key in that priority order, or None when missing.
        Prohibitions:
            Do not assume a specific provider; DeepSeek is only the default base_url.
        Raises:
            OSError when a configured fallback file cannot be read.
        """
        return (
            self.secret("LLM_API_KEY")
            or self.secret("DEEPSEEK_API_KEY", fallback_file="ds_key.txt")
            or self.secret("OPENAI_API_KEY")
        )


def load_config(root: Path | None = None) -> Config:
    """Load YAML settings/sources and merge secrets from env/.env/keys.txt.

    Preconditions:
        root points at the project root containing config/settings.yaml and config/sources.yaml.
    Postconditions:
        Config with settings dict, sources list and secrets mapping; precedence is
        environment > .env > keys.txt.
    Prohibitions:
        Do not mutate the returned dicts in place; treat configuration as immutable.
    Raises:
        FileNotFoundError for missing YAML; yaml.YAMLError for malformed YAML.
    """
    base = root or ROOT
    settings = yaml.safe_load((base / "config" / "settings.yaml").read_text(encoding="utf-8")) or {}
    sources_doc = yaml.safe_load((base / "config" / "sources.yaml").read_text(encoding="utf-8")) or {}

    secrets = read_key_values(base / "keys.txt")  # local keys.txt (lowest precedence)
    secrets.update(_read_env_file(base / ".env"))  # .env overrides keys.txt
    for key in (
        "LLM_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY",
        "GITHUB_TOKEN", "SMTP_USER", "SMTP_PASSWORD",
    ):
        if os.environ.get(key):
            secrets[key] = os.environ[key].strip()  # real environment overrides everything

    return Config(
        root=base,
        settings=settings,
        sources=list(sources_doc.get("sources") or []),
        secrets=secrets,
    )
