# =============================================================================
# Module: newsagent.fetch
# Responsibilities: Adapter registry (type -> adapter instance).
# Dependencies: all fetch adapters
# Dependents: pipeline
# ADRs: ADR-0003
# Traceability: docs/decisions/README.md
# =============================================================================
"""Adapter registry."""

from __future__ import annotations

from .base import Adapter
from .docs import DocsMdAdapter
from .eastmoney_ann import EastmoneyAnnAdapter
from .github import GithubOrgAdapter
from .google_news import GoogleNewsAdapter
from .gov_policy import GovPolicyAdapter
from .html_list import HtmlListAdapter
from .huggingface import HuggingFaceOrgAdapter
from .rss import RssAdapter
from .sec import Sec8kAdapter

_ADAPTERS: dict[str, Adapter] = {
    adapter.type: adapter
    for adapter in (
        RssAdapter(),
        GithubOrgAdapter(),
        HuggingFaceOrgAdapter(),
        DocsMdAdapter(),
        GoogleNewsAdapter(),
        Sec8kAdapter(),
        GovPolicyAdapter(),
        EastmoneyAnnAdapter(),
        HtmlListAdapter(),
    )
}


def get_adapter(kind: str) -> Adapter:
    """Return the singleton adapter for a source type.

    Preconditions:
        kind is one of the registered adapter types.
    Postconditions:
        Adapter instance implementing fetch(source, ctx).
    Prohibitions:
        Do not instantiate adapters directly outside tests.
    Raises:
        ValueError for unknown source types.
    """
    try:
        return _ADAPTERS[kind]
    except KeyError as exc:
        raise ValueError(f"unknown source type: {kind}") from exc
