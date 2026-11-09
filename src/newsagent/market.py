# =============================================================================
# Module: newsagent.market
# Responsibilities: Fixed watchlist stock prices (90-day daily close) with JSON cache and fail-soft fetching.
# Dependencies: yaml, config, http
# Dependents: pipeline, cli, standalone, web UI (report.market)
# ADRs: ADR-0015
# Traceability: docs/decisions/README.md
# =============================================================================
"""Market-data layer for the fixed watchlist.

Only daily close prices are fetched (no indicators, no analysis). Data comes
from Eastmoney's public kline endpoint and is cached in data/market_cache.json
so weekly runs and HTML exports stay cheap and resilient.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .config import Config
from .http import HttpClient

MARKET_CONFIG_REL = Path("config") / "market.yaml"
CACHE_REL = Path("data") / "market_cache.json"

KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
KLINE_UT = "fa5fd1943c7b386f172d6893dbfba10b"
KLINE_FIELDS1 = "f1,f2,f3,f4,f5,f6"
KLINE_FIELDS2 = "f51,f52,f53,f54,f55,f56,f57,f58"
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)
COUNTRY_ORDER = {"CN": 0, "US": 1}


def load_market_config(config: Config) -> dict[str, Any]:
    """Load the fixed watchlist and market settings.

    Preconditions:
        config.root contains config/market.yaml with a `watchlist` list.
    Postconditions:
        Parsed dict with enabled/window_days/cache_hours/watchlist.
    Prohibitions:
        Do not add stocks at runtime; the list is fixed by configuration only.
    Raises:
        FileNotFoundError when config/market.yaml is missing; yaml.YAMLError on invalid YAML.
    """
    path = config.root / MARKET_CONFIG_REL
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return document if isinstance(document, dict) else {}


def sort_watchlist(watchlist: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order the watchlist for display.

    Preconditions:
        watchlist entries carry `country` (CN/US) and `sort_name`; `pinned` is optional.
    Postconditions:
        China before the US; within each country pinned entries first, then the
        remaining entries by `sort_name` A-Z (case-insensitive); ties keep file order.
    Prohibitions:
        Do not reorder by live performance or news; ordering is a stable design rule.
    Raises:
        None.
    """
    def country_of(watch: dict[str, Any]) -> str:
        explicit = str(watch.get("country") or "").upper()
        if explicit in COUNTRY_ORDER:
            return explicit
        return "US" if str(watch.get("market")) == "美股" else "CN"

    def sort_key(pair: tuple[int, dict[str, Any]]) -> tuple[int, int, str, int]:
        index, watch = pair
        country_rank = COUNTRY_ORDER.get(country_of(watch), 1)
        pinned_rank = 0 if watch.get("pinned") else 1
        sort_name = str(watch.get("sort_name") or watch.get("name") or "").lower()
        return (country_rank, pinned_rank, sort_name, index)

    return [watch for _, watch in sorted(enumerate(watchlist), key=sort_key)]


def _order_items(items: list[dict[str, Any]], watchlist: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {watch.get("id"): index for index, watch in enumerate(sort_watchlist(watchlist))}
    return sorted(items, key=lambda item: order.get(item.get("id"), len(order) + 1))


def _attach_groups(items: list[dict[str, Any]], watchlist: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = {watch.get("id"): str(watch.get("group") or "ai") for watch in watchlist}
    for item in items:
        item["group"] = groups.get(item.get("id"), "ai")
    return items


def parse_klines(payload: dict[str, Any], days: int = 90) -> list[dict[str, Any]]:
    """Extract the last `days` daily closes from an Eastmoney kline payload.

    Preconditions:
        payload is the decoded JSON response of the Eastmoney kline endpoint.
    Postconditions:
        A list of {date, close} dicts in chronological order (at most `days`);
        an empty list when the API returns no data.
    Prohibitions:
        Do not guess missing prices; malformed rows are skipped.
    Raises:
        None.
    """
    data = (payload or {}).get("data") or {}
    points: list[dict[str, Any]] = []
    for line in data.get("klines") or []:
        parts = str(line).split(",")
        if len(parts) < 3:
            continue
        try:
            close = float(parts[2])
        except (TypeError, ValueError):
            continue
        points.append({"date": parts[0], "close": close})
    return points[-max(1, days):]


def build_market_item(watch: dict[str, Any], points: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Build one display item (latest close + points) from parsed closes.

    Preconditions:
        watch is one watchlist entry; points is chronological and may be empty.
    Postconditions:
        Dict with watch fields plus latest/latest_date/points, or None when there
        are no prices.
    Prohibitions:
        Do not fabricate prices for missing/unlisted companies.
    Raises:
        None.
    """
    if not points:
        return None
    latest = points[-1]
    return {
        "id": watch.get("id"),
        "name": watch.get("name"),
        "code": watch.get("code"),
        "market": watch.get("market"),
        "currency": watch.get("currency"),
        "group": str(watch.get("group") or "ai"),
        "latest": float(latest["close"]),
        "latest_date": latest["date"],
        "points": points,
    }


def sparkline_points(points: list[dict[str, Any]], width: int = 220, height: int = 64, pad: int = 4) -> str:
    """Convert closes into an SVG polyline point string.

    Preconditions:
        points are the {date, close} entries of one market item; width/height/pad > 0.
    Postconditions:
        Space-separated "x,y" coordinates scaled into the viewBox; empty for no points.
    Prohibitions:
        Do not draw axes, labels or indicators; this is only a sparkline geometry helper.
    Raises:
        None.
    """
    closes = [float(point.get("close") or 0.0) for point in points]
    if not closes:
        return ""
    if len(closes) == 1:
        return f"{width / 2:.1f},{height / 2:.1f}"
    low, high = min(closes), max(closes)
    step = (width - 2 * pad) / (len(closes) - 1)
    coordinates = []
    for index, close in enumerate(closes):
        x = pad + index * step
        if high == low:
            y = height / 2
        else:
            y = pad + (height - 2 * pad) * (1.0 - (close - low) / (high - low))
        coordinates.append(f"{x:.1f},{y:.1f}")
    return " ".join(coordinates)


def _read_cache(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _cache_is_fresh(path: Path, hours: int) -> bool:
    try:
        return (time.time() - path.stat().st_mtime) < hours * 3600
    except OSError:
        return False


def _fetch_one(client: HttpClient, watch: dict[str, Any], days: int) -> dict[str, Any] | None:
    payload = client.get_json(KLINE_URL, params={
        "secid": watch.get("secid"),
        "fields1": KLINE_FIELDS1,
        "fields2": KLINE_FIELDS2,
        "klt": "101",
        "fqt": "1",
        "beg": "0",
        "end": "20500101",
        "lmt": str(days),
        "ut": KLINE_UT,
    })
    return build_market_item(watch, parse_klines(payload, days))


def fetch_market(config: Config, *, refresh: bool = False) -> dict[str, Any]:
    """Fetch (or reuse cached) 90-day closes for the fixed watchlist.

    Preconditions:
        config/market.yaml exists; network access is available unless a fresh cache exists.
    Postconditions:
        Dict with enabled/as_of/window_days/items/errors. Per-ticker failures are
        recorded in errors and never raise; a stale cache is reused if every fetch fails.
    Prohibitions:
        Do not block the report for market data; do not invent values for unlisted companies.
    Raises:
        None for network/ticker failures (errors are collected); yaml/file errors propagate.
    """
    settings = load_market_config(config)
    window_days = int(settings.get("window_days") or 90)
    cache_hours = int(settings.get("cache_hours") or 12)
    cache_path = config.root / CACHE_REL
    watchlist = settings.get("watchlist") or []

    cached = _read_cache(cache_path)
    if cached:
        cached_ids = {item.get("id") for item in cached.get("items") or []}
        watch_ids = {watch.get("id") for watch in watchlist}
        if cached_ids != watch_ids:
            cached = None  # watchlist changed: refetch so added/removed stocks are reflected
    if not refresh and cached and cached.get("items") and _cache_is_fresh(cache_path, cache_hours):
        ordered = dict(cached)
        ordered["items"] = _attach_groups(_order_items(cached.get("items") or [], watchlist), watchlist)
        return ordered
    if not settings.get("enabled", True):
        return {"enabled": False, "as_of": None, "window_days": window_days, "items": [], "errors": []}

    items: list[dict[str, Any]] = []
    errors: list[str] = []
    client = HttpClient(timeout=20.0, retries=2, user_agent=BROWSER_UA, interval_seconds=0.35)
    try:
        for watch in sort_watchlist(watchlist):
            try:
                item = _fetch_one(client, watch, window_days)
                if item:
                    items.append(item)
                else:
                    errors.append(f"{watch.get('code')}: no data")
            except Exception as exc:  # noqa: BLE001 - one bad ticker must not break the list
                errors.append(f"{watch.get('code')}: {exc}")
    finally:
        client.close()

    if not items and cached and cached.get("items"):
        stale = dict(cached)
        stale["items"] = _attach_groups(_order_items(cached.get("items") or [], watchlist), watchlist)
        stale["errors"] = list(cached.get("errors") or []) + errors + ["using stale cache"]
        return stale

    result = {
        "enabled": True,
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": window_days,
        "items": _attach_groups(_order_items(items, watchlist), watchlist),
        "errors": errors,
    }
    if items:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result
