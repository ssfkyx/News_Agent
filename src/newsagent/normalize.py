# =============================================================================
# Module: newsagent.normalize
# Responsibilities: Text/URL normalization, language detection, 64-bit simhash, 7-day freshness gate.
# Dependencies: models
# Dependents: pipeline, fetch.rss
# ADRs: ADR-0002, ADR-0004
# Traceability: docs/decisions/README.md
# =============================================================================
"""Normalization: clean fields, canonical URL, language, simhash, 7-day gate."""

from __future__ import annotations

import hashlib
import html as html_lib
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .models import NormalizedItem, RawItem

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "fbclid", "gclid", "ref", "ref_src", "spm", "from",
    "mc_cid", "mc_eid", "igshid", "__twitter_impression",
}
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
TAG_RE = re.compile(r"<[^>]+>")


def clean_text(text: str | None) -> str:
    """Unescape HTML entities, strip tags and collapse whitespace.

    Preconditions:
        Input may be None or any object convertible to str.
    Postconditions:
        Single-line cleaned string (empty for empty input).
    Prohibitions:
        Do not expect HTML structure to survive.
    Raises:
        None.
    """
    if not text:
        return ""
    text = html_lib.unescape(str(text))
    text = TAG_RE.sub(" ", text)
    return " ".join(text.split())


def canonical_url(url: str) -> str:
    """Normalize a URL for identity comparisons.

    Preconditions:
        url is an absolute URL or arbitrary string.
    Postconditions:
        Lowercased scheme/host, no fragment, tracking parameters removed.
    Prohibitions:
        Do not use the result for display; it is an identity key only.
    Raises:
        None.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url.strip()
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS and not key.lower().startswith("utm_")
    ]
    path = parsed.path.rstrip("/") or "/"
    return urlunparse(
        (parsed.scheme.lower(), parsed.netloc.lower(), path, "", urlencode(query), "")
    )


def detect_lang(*texts: str) -> str:
    """Heuristically detect zh vs en from CJK character ratio.

    Preconditions:
        Any number of text fragments; empty input allowed.
    Postconditions:
        'zh', 'en' or 'unknown'.
    Prohibitions:
        Do not use for multilingual classification beyond zh/en.
    Raises:
        None.
    """
    joined = " ".join(text for text in texts if text)
    if not joined:
        return "unknown"
    cjk = len(CJK_RE.findall(joined))
    return "zh" if cjk / max(len(joined), 1) > 0.15 else "en"


def simhash64(text: str) -> int:
    """Compute a 64-bit SimHash of the given text.

    Preconditions:
        text is a string (titles/summaries).
    Postconditions:
        Unsigned 64-bit integer (0 for empty token sets).
    Prohibitions:
        Do not persist directly as SQLite INTEGER; convert via store._sql_int64.
    Raises:
        None.
    """
    tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", text.lower())[:300]
    if not tokens:
        return 0
    weights = [0] * 64
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        for bit in range(64):
            weights[bit] += 1 if (value >> bit) & 1 else -1
    result = 0
    for bit, weight in enumerate(weights):
        if weight > 0:
            result |= 1 << bit
    return result


def build_item(
    raw: RawItem,
    *,
    now: datetime,
    max_age_days: int,
    future_tolerance_minutes: int,
) -> tuple[NormalizedItem | None, str]:
    """Normalize a raw item and apply the freshness gate.

    Preconditions:
        raw has a non-empty title/url; now is timezone-aware UTC; max_age_days >= 0.
    Postconditions:
        (NormalizedItem, 'ok') when accepted; (None, reason) when rejected.
    Prohibitions:
        Do not bypass this gate for news sources; do not pass naive datetimes.
    Raises:
        None (validation failures are returned as reasons).
    """
    title = clean_text(raw.title)
    url = (raw.url or "").strip()
    if not title or not url:
        return None, "missing_title_or_url"

    published = raw.published_at
    estimated = False
    if published is None:
        published = now
        estimated = True
    else:
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        published = published.astimezone(timezone.utc)
        if published > now + timedelta(minutes=future_tolerance_minutes):
            return None, "future_date"
        if now - published > timedelta(days=max_age_days):
            return None, "too_old"

    summary = clean_text(raw.summary)[:500]
    canonical = canonical_url(url)
    item_id = hashlib.sha1(f"{raw.source_id}|{canonical}".encode("utf-8")).hexdigest()[:16]
    content_hash = hashlib.sha1(
        f"{title}|{summary}|{canonical}".encode("utf-8")
    ).hexdigest()

    return NormalizedItem(
        id=item_id,
        source_id=raw.source_id,
        source_name=raw.source_name,
        source_weight=float(raw.source_weight),
        title=title[:300],
        summary=summary,
        url=url,
        canonical_url=canonical,
        published_at=published,
        date_estimated=estimated,
        first_seen_at=now,
        last_seen_at=now,
        lang=detect_lang(title, summary),
        content_hash=content_hash,
        simhash=simhash64(f"{title} {summary}"),
        section_hint=raw.section_hint or "tech",
    ), "ok"
