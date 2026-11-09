# ADR-0016: Fourth section "具身智能" (embodied intelligence) with dedicated sources and stocks

- **Status:** Accepted
- **Date:** 2026-11-09
- **Deciders:** Project owner + implementation agent
- **Supersedes:** —
- **Related ADRs:** ADR-0002 (windows), ADR-0005 (ranking/quotas), ADR-0011 (sections/hard info), ADR-0015 (watchlist market charts)

## Context
The owner wants a fourth report section dedicated to embodied intelligence / humanoid
robots, separate from general technology. Existing sources are general AI/tech media
and company blogs; robotics-specific coverage is thin and would otherwise be buried in
the tech section. The market watchlist also needs listed robotics companies so the
90-day trend charts cover this theme.

## Decision
- Add a fourth section key `embodied` (display title "四、具身智能") with a **7-day
  window** (same as tech), media allowed. The existing finance/policy hard-information
  rule is unchanged: only finance and policy are restricted to `hard_info: true` sources.
  It is a normal section alongside tech/finance/policy; the stock watchlist is rendered
  separately as a distinct block at the bottom of the HTML report and web UI.
- Add verified sources: The Robot Report, IEEE Spectrum Robotics, TechCrunch Robotics,
  NVIDIA Robotics Blog (official), two Google News queries (Chinese: 具身智能/人形机器人/
  宇树/优必选/智元机器人; English: humanoid robot/embodied AI/Figure AI/Boston Dynamics),
  plus a State Council policy query for 人形机器人 (classified to policy, hard info).
- Add `embodied` to the LLM taxonomy via prompt `enrich_v3`: robots/physical AI/
  humanoids/actuators/embodied models go to `embodied`; robotics funding still goes to
  finance and robotics regulation to policy. Section aliases accept 具身智能/机器人/
  人形机器人/robotics.
- Rebalance quotas to 22 items: tech 9 / finance 4 / policy 4 / embodied 5; raise the
  enrich pool to 48 and relax rss/google_news kind quotas to fit the added sources.
- Extend the fixed stock watchlist by 14 listed embodied-intelligence companies:
  US: Serve Robotics (SERV), Symbotic (SYM), Richtech Robotics (RR);
  HK: 优必选 (09880), 越疆 (02432), 速腾聚创 (02498), 地平线机器人 (09660);
  A-share: 埃斯顿 (002747), 新松机器人 (300024), 绿的谐波 (688017), 三花智控 (002050),
  拓普集团 (601689), 兆威机电 (003021), 奥比中光 (688322).
  Chart order remains: China first, US after; NVIDIA first in the US group; others A-Z.
  The 14 added stocks are tagged `group: robot` and rendered as a separate
  "机器人 / 具身智能" sub-sector below the original AI-company stock grid.

## Rationale
- Robotics-specific feeds plus targeted Google News queries produce enough fresh items
  without scraping JS-heavy company sites (Unitree/UBTECH/Figure pages have no stable RSS).
- A dedicated LLM label keeps humanoid/robot-body news out of the generic tech list and
  makes the section readable, while finance/policy routing preserves the existing rules.
- Media sources are allowed in this section because product demos, launches and
  deployments are usually reported by media before official filings; hard info remains
  mandatory only for finance/policy.

## Consequences (Costs)
- Source count grows from 53 to 60; the weekly run makes more requests and LLM input
  grows (pool 48). Quotas reduce tech from 12 to 9 items.
- The embodied/tech/policy boundary is judgement-based; some model releases with robot
  demos may move between tech and embodied across runs.
- The stock watchlist grows to 38 cards, making the market section longer; 14 more
  tickers are fetched per refresh (cached for 12h).
- Market coverage is still limited to listed companies; private robotics startups
  (Figure, Agility, Unitree, 智元) have no stock chart.

## Code locations (traceability)
- `config/sources.yaml` (7 new sources, `section_hint: embodied` / policy)
- `config/settings.yaml` (`embodied_window_days`, quotas, pool, prompt version)
- `config/prompts/enrich_v3.md` (four-section classification)
- `src/newsagent/models.py :: SECTION_ALIASES`
- `src/newsagent/pipeline.py :: run_pipeline` (windows, counts, quotas)
- `src/newsagent/select.py :: SECTION_ORDER, balance_sections`
- `src/newsagent/report.py :: SECTION_META`
- `src/newsagent/render.py`, `ui/standalone/report.html`, `ui/static/app.js` (four-section headers/cards)
- `config/market.yaml` (14 new stocks), `src/newsagent/market.py :: sort_watchlist`
- `tests/test_report_fp64.py`
