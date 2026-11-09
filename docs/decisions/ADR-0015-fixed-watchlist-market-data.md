# ADR-0015: Fixed-watchlist market data (90-day close charts)

- **Status:** Accepted
- **Date:** 2026-11-09
- **Deciders:** Project owner + implementation agent
- **Supersedes:** —
- **Related ADRs:** ADR-0008 (report snapshot), ADR-0010 (UI), ADR-0012 (FP64)

## Context
The owner wants a visual stock-price trend for the companies they follow, with no
extra information or analysis. The digest covers many private AI companies, but only
listed companies have prices. A market layer must not add heavy dependencies, must
survive occasional upstream failures, and must stay cheap for a weekly run.

## Decision
- Keep a **fixed watchlist** in `config/market.yaml` (24 listed companies across
  US / HK / A-shares); it is not derived from the news of the day.
- Fetch the last **90 trading days of daily close prices** from Eastmoney's public
  kline endpoint (`push2his.eastmoney.com`), using a per-market `secid`
  (`105/106` US, `116` HK, `1/0` Shanghai/Shenzhen). No API key is required.
- Cache the result as `data/market_cache.json` for 12 hours; a weekly run, the HTML
  exporter and the UI reuse it. Per-ticker failures are collected as `errors` and
  never raise; a stale cache is reused if every fetch fails.
- Attach the snapshot to the Report as `report.market` (also persisted in
  `report.json`). Both the standalone HTML and the interactive UI render an inline
  SVG sparkline plus the latest close; no averages, volume, change rates,
  predictions or LLM analysis are added.
- Display order is deterministic and computed by `sort_watchlist`: China (HK/A)
  before the US, then within the US NVIDIA is pinned first, and all remaining
  companies are sorted by `sort_name` A-Z (pinyin for Chinese companies, English
  names for US companies). The YAML file order is documentation only and does not
  control the chart order.
- Stocks tagged `group: robot` are rendered as a separate "机器人 / 具身智能"
  sub-sector below the main AI-company grid, so the added robotics companies do not
  mix with the original watchlist.
- Unlisted companies (OpenAI, Anthropic, DeepSeek, Moonshot, xAI, ByteDance, …) are
  simply absent, because no price exists.

## Rationale
- One free source covers US/HK/A-shares and the newly listed 智谱 (`02513.HK`) and
  MiniMax (`00100.HK`), avoiding multiple providers and keys.
- Caching turns 24 requests into at most one refresh per week and keeps the static
  HTML export offline-capable because the data is embedded in `report.json`.
- Fail-soft behaviour protects the primary news report: a broken quote endpoint only
  removes charts, never the report.

## Consequences (Costs)
- Eastmoney's endpoint is unofficial and may change or rate-limit; cached data can be
  stale and the site has no SLA. Prices are delayed and unsuitable for trading.
- The fixed list must be maintained in `config/market.yaml`; adding a ticker requires
  verifying its Eastmoney `secid`.
- `report.json` grows by roughly 20–30 KB (24 × 90 closes).
- Only daily closes: no intraday chart, no splits/dividend adjustment beyond `fqt=1`.

## Code locations (traceability)
- `src/newsagent/market.py :: load_market_config, sort_watchlist, parse_klines, build_market_item, sparkline_points, fetch_market`
- `config/market.yaml` (fixed 24-company watchlist + cache settings)
- `src/newsagent/pipeline.py :: run_pipeline` (fetch and attach `report.market`)
- `src/newsagent/standalone.py :: _decorate_market, render_standalone_html`
- `src/newsagent/cli.py :: main` (`market` command)
- `ui/standalone/report.html` (market grid + sparkline CSS)
- `ui/static/app.js :: renderMarket, sparkline`; `ui/static/app.css` (market styles)
- `tests/test_market.py`
