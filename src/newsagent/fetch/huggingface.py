# =============================================================================
# Module: newsagent.fetch.huggingface
# Responsibilities: HuggingFace organization model-release adapter.
# Dependencies: base
# Dependents: fetch.__init__
# ADRs: ADR-0003
# Traceability: docs/decisions/README.md
# =============================================================================
"""HuggingFace organization model-release adapter."""

from __future__ import annotations

from typing import Any

from ..models import RawItem
from .base import Adapter, FetchContext, parse_iso, source_base


class HuggingFaceOrgAdapter(Adapter):
    type = "hf_org"

    def fetch(self, source: dict[str, Any], ctx: FetchContext) -> list[RawItem]:
        """Fetch newly created HuggingFace models for one organization.

        Preconditions:
            source.org is a valid HF author; max_items >= 1.
        Postconditions:
            Raw items for models sorted by createdAt desc.
        Prohibitions:
            Do not call without a reasonable max_items.
        Raises:
            RuntimeError on non-200 or unexpected payloads.
        """
        base = source_base(source)
        limit = int(source.get("max_items", 5))
        url = (
            f"https://huggingface.co/api/models?author={source['org']}"
            f"&sort=createdAt&direction=-1&limit={limit}"
        )
        models = ctx.client.get_json(url)
        if not isinstance(models, list):
            raise RuntimeError(f"HF {source['org']} -> unexpected payload")

        items: list[RawItem] = []
        for model in models:
            created = parse_iso(model.get("createdAt"))
            model_id = model.get("id") or model.get("modelId")
            if created is None or not model_id:
                continue
            items.append(RawItem(
                **base,
                title=f"新模型：{model_id}",
                url=f"https://huggingface.co/{model_id}",
                summary="HuggingFace 模型发布（权重/卡片已上线）",
                published_at=created,
                raw={"model_id": model_id},
            ))
        return items
