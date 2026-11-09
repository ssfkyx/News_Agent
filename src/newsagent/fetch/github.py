# =============================================================================
# Module: newsagent.fetch.github
# Responsibilities: GitHub organization activity adapter.
# Dependencies: base
# Dependents: fetch.__init__
# ADRs: ADR-0003
# Traceability: docs/decisions/README.md
# =============================================================================
"""GitHub organization activity adapter (recent pushes, optional token)."""

from __future__ import annotations

from typing import Any

from ..models import RawItem
from .base import Adapter, FetchContext, parse_iso, source_base


class GithubOrgAdapter(Adapter):
    type = "github_org"

    def fetch(self, source: dict[str, Any], ctx: FetchContext) -> list[RawItem]:
        """Fetch recent repository activity for one GitHub organization.

        Preconditions:
            source.org is a valid org; optional GITHUB_TOKEN secret.
        Postconditions:
            Raw items for the most recently pushed repos.
        Prohibitions:
            Do not poll faster than the token/quota allows.
        Raises:
            RuntimeError on non-200 or unexpected payloads.
        """
        base = source_base(source)
        token = ctx.secrets.get("GITHUB_TOKEN")
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        url = (
            f"https://api.github.com/orgs/{source['org']}/repos"
            "?sort=pushed&direction=desc&per_page=5"
        )
        repos = ctx.client.get_json(url, headers=headers)
        if not isinstance(repos, list):
            raise RuntimeError(f"GitHub {source['org']} -> unexpected payload")

        items: list[RawItem] = []
        limit = int(source.get("max_items", 2))
        for repo in repos[:limit]:
            pushed = parse_iso(repo.get("pushed_at"))
            if pushed is None:
                continue
            description = (repo.get("description") or "").strip()
            title = f"{repo['full_name']}：{description}" if description else f"{repo['full_name']} 仓库更新"
            items.append(RawItem(
                **base,
                title=title,
                url=repo["html_url"],
                summary=f"最近 push {repo.get('pushed_at', '')}，stars {repo.get('stargazers_count', 0)}",
                published_at=pushed,
                raw={"repo": repo["full_name"], "pushed_at": repo.get("pushed_at")},
            ))
        return items
