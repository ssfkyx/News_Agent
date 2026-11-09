# 股票与投资数据层 · 方案设计

> 目标：在「AI 新闻日报」之上加一层**市场/投资视角**——既能追踪**未上市 AI 公司的融资与收入**，也能把**上市公司的 AI 业务与股价**放在一起分析（SPCX、META、GOOGL 是重点）。
> 原则：不替代行情终端、不做投资建议；只做「官方信息 + 公开行情 + 可复核的统计」，所有数字标注来源与时间。

---

## 0. 先厘清：谁上市、谁没上市（2026-11 现状）

| 公司 | 状态 | 标的 / 备注 |
|---|---|---|
| **SpaceX（含 xAI/Grok）** | ✅ 已上市 | **SPCX**（Nasdaq，2026-06-12 上市，史上最大 IPO；x.ai 官网品牌已显示 SpaceXSI，AI 业务并入） |
| **Meta** | ✅ 上市 | META（AI 嵌入广告/推荐 + Llama + 巨额 capex） |
| **Google** | ✅ 上市 | GOOGL / GOOG（Gemini、Cloud、TPU） |
| **Microsoft** | ✅ 上市 | MSFT（Azure/OpenAI 合作、Copilot） |
| **NVIDIA** | ✅ 上市 | NVDA（AI 算力，接近 pure-play） |
| **Amazon** | ✅ 上市 | AMZN（AWS、Nova、Trainium） |
| **智谱 GLM** | ✅ 港股上市 + A 股在途 | **02513.HK**（2026-01-08 上市；2026-06 科创板 IPO「辅导验收」，拟募资 150 亿） |
| **MiniMax** | ✅ 港股上市 | **00100.HK**（2026-01-09 上市，发行价 HK$165，首日 +64%） |
| **阿里 / 腾讯 / 小米 / 百度 / 讯飞 / 商汤** | ✅ 上市 | 9988.HK / 0700.HK / 1810.HK / 9888.HK / 002230.SZ / 0020.HK（大模型是子公司或业务线） |
| **OpenAI** | ❌ 未上市 | 2026-11 估值 $1.25T、融资 $11B；公开报道称最晚 2027 完成 IPO |
| **Anthropic** | ❌ 未上市 | 报道称「临近 IPO」，尚无公开交易价格 |
| **Mistral / Cohere / Perplexity / Hugging Face / Ai2** | ❌ 未上市 | Mistral/Cohere/Perplexity 私有；HF 私有；Ai2 非营利 |
| **DeepSeek / Kimi（月之暗面）/ StepFun / MiMo（小米子公司）** | ❌ 未上市 | DeepSeek 背靠幻方；Kimi/StepFun 私有；MiMo 属小米 |

**关键结论**：美国不是「基本都上市」——上市的只有大厂；纯模型公司（OpenAI、Anthropic）都还是私有。中国正好相反：**智谱、MiniMax 已经上市**，DeepSeek/Kimi/StepFun 还是私有，所以中国部分的重点是**融资/估值/收入披露**，美国部分是**私有公司估值跟踪 + 大厂 AI×股价**两条线。

---

## 1. 数据源清单（已实测，2026-11-08）

### 1.1 行情（Quotes）

| 用途 | 数据源 | 实测 | 说明 |
|---|---|---|---|
| 美股日线 | **Yahoo Finance chart API** `query1.finance.yahoo.com/v8/finance/chart/{sym}` | ✅ META/GOOGL/SPCX 均 200 | 免 key、非官方；需缓存 + 正常 UA；有延迟 |
| 港股/A 股日线 | **东方财富** `push2his.eastmoney.com/api/qt/stock/kline/get?secid=...` | ✅ 00700.HK 返回日期+OHLCV | `secid`：`116.00700`（HK）、`1.600519`（SH）、`116.02513`（智谱） |
| 实时快照 | 东方财富 `push2.eastmoney.com/api/qt/stock/get` | ✅ 00700/600519/META/GOOGL/NVDA/SPCX/02513 全 200 | 含涨跌幅 |
| 美股（备选） | 东方财富 US：`secid=105.META` 等 | ✅ | 与 Yahoo 互为备份 |
| A 股备选 | 新浪 `hq.sinajs.cn`（需 Referer） | ✅ | GB18030 编码；只做兜底 |
| 历史数据（失败） | Stooq CSV | ❌ 已加 JS 人机验证 | 不再使用 |
| 港股（失败） | 腾讯 `qt.gtimg.cn` | ❌ 连接被重置 | 不用 |

> 注意：Yahoo 对部分港股（如 02513.HK）无数据，港股统一走东方财富；SPCX 在 Yahoo/东方财富都能取到。

### 1.2 财报与公告（Filings）

| 用途 | 数据源 | 实测 | 说明 |
|---|---|---|---|
| 美股全部 filings | **SEC EDGAR submissions** `data.sec.gov/submissions/CIK##########.json` | ✅ Meta 最近 8-K/424B5/Form 4 可列 | 需要 `User-Agent: 名字 邮箱` |
| 美股财务数据 | **SEC XBRL companyfacts** | ✅ 拉到 Meta 2026 年 revenue $181.7B、capex $83.1B、R&D $59.4B | 直接算 AI capex 强度 |
| 公告订阅 | **EDGAR 8-K Atom** `browse-edgar?...&type=8-K&output=atom` | ✅ | 可当日更 |
| 全市场检索 | EDGAR full-text search `efts.sec.gov/LATEST/search-index?q=...` | ✅ | 用于 Form D、S-1、并购 |
| A 股公告 | 东方财富公告 API `np-anotice-stock.eastmoney.com/api/security/ann` | ✅ | 官方版可换巨潮（本次巨潮参数返回 0，需再调） |
| 港股公告 | HKEXnews | 未实测 | 官方入口，IPO/年报/招股书都在这里 |
| 私有公司融资 | **EDGAR Form D**（走 full-text search） | ✅ OpenAI 相关 47 条、Anthropic 121 条、xAI 96 条、Mistral 5 条 | 注意：很多是 SPV/基金，不是公司本体 |

### 1.3 私有公司估值与新闻

| 来源 | 用途 | 可用性 |
|---|---|---|
| 官方公告 / 公众号 / X | 融资轮次、估值、收入披露 | ⚠️ 社媒不可抓（见 OFFICIAL_SOURCES.md）；官方新闻页/博客可抓 |
| SEC Form D | 美国私有公司融资备案（金额、发行日期） | ✅ 可检索 |
| 招股书（S-1 / HKEX 招股书） | 收入、亏损、股权、分部数据 | ✅ 上市时可得，M5 接 |
| TechCrunch / 36Kr / IT桔子 / 烯牛数据 | 融资新闻（中国为主） | RSS 免费部分可用；IT桔子/烯牛为付费库 |
| 企查查 / 天眼查 | 中国工商变更、股权 | ❌ 反爬 + ToS，不做自动抓取 |

---

## 2. 核心方案：AI 业务 × 股价，怎么分析

分四层，从「事件→价格」到「分部估值」，全部可自动化、可复核。

### 2.1 第一层：事件研究（Event Study）——量化「AI 消息」对股价的影响

- **事件来源**：日报管线里的新闻/公告，经 LLM 打标（公司、事件类型、AI 主题、影响方向、重要性）。
- **事件类型**：模型发布、产品发布、财报/指引、capex/算力、合作/客户、监管/诉讼、融资/IPO、人事、其他。
- **方法**（标准市场模型）：
  1. 估计窗口 `[-250, -30]` 交易日，基准指数：美股 SPY/QQQ、港股恒生科技、A 股沪深 300；
  2. 事件窗口 `[-1, +1]` 与 `[0, +5]`；
  3. 超额收益 AR = 实际收益 − 市场模型预测收益；累计 CAR；
  4. t 检验 + 按事件类型聚合（例如「capex 上调」对 META 的 CAR 是否显著大于「模型发布」）。
- **输出**：`公司 × 事件类型 × CAR` 表；「哪类 AI 消息真的能推动股价」的结论只认统计显著的部分。
- **注意**：单条软新闻（如模型 demo）通常不显著；**财报、capex 指引、监管、并购**才是硬事件。事件日要处理盘后发布 → 用下一交易日。

### 2.2 第二层：AI 叙事指数（Narrative Index）——把「新闻热度」变成可比较的指标

- 用 enrich 阶段的 LLM 输出：每家公司每周的 AI 相关新闻条数、情绪、重要性加权 → `AI 叙事强度指数`。
- 与股价/成交量/估值做相关性：例如「META 的 AI 新闻热度 vs 未来 5 日超额收益」。
- 同时从**财报电话会/8-K**里抽「AI 提及次数、capex 指引、AI 收入表述」→ 区分「市场叙事」和「公司口径」。

### 2.3 第三层：分部剥离与 SOTP——回答「股价里 AI 值多少钱」

对 META、GOOGL、SPCX 这类「AI 只是部分业务」的公司：

1. **AI 代理指标**（来自 XBRL / 财报）：
   - META：capex/收入、R&D/收入、广告收入增速（AI 推荐驱动）；
   - GOOGL：Google Cloud 收入增速、capex、TPU 相关表述；
   - SPCX：按 S-1/10-K 披露的 Launch / Starlink / AI（xAI）分部收入与 capex。
2. **SOTP 估值**：核心业务给可比 P/E（广告/搜索/电信），AI/云业务给 EV/Sales（参考纯 AI 公司或一级市场估值），得到**隐含 AI 价值**；再与当前市值比较：
   - `市场隐含 AI 价值 = 市值 − 核心业务估值`
   - 输出保守/中性/乐观三档，所有倍数和假设明示。
3. **趋势跟踪**：「AI 溢价率」按周记录，观察模型发布、财报、IPO 事件前后的变化。

> 对 SPCX 特别说明：xAI/Grok 并入 SpaceX 后，「火箭+星链+AI」三块在一个标的里；先用招股书/10-K 的分部披露做 SOTP，若分部披露不足，就只做**事件研究**（Grok 发布 vs 星舰发射分别对 SPCX 的 CAR），不做估值拆分，并标注数据限制。

### 2.4 第四层：私有公司估值追踪——没有股价，就追踪「估值事件」

- **美国**：Form D（金额、日期）+ 官方融资公告 + 二级市场估值报道 → 估值时间线；与模型发布、收入披露对齐（例：OpenAI $1.25T、Anthropic 临近 IPO）。
- **中国**：招股书/年报（智谱 2025 收入 7.24 亿元、亏损 47.18 亿元；MiniMax 2025 前三季收入 $53.4M、+174.7%）、融资新闻、工商变更（人工/低频）。
- **输出**：「AI 一级市场估值表」+「估值 vs 模型发布」时间线；对已上市纯模型公司（智谱 02513.HK、MiniMax 00100.HK）直接用 EV/Sales、PS、现金消耗做横向对比。

---

## 3. 管线扩展（M5 模块）

```
现有管线: Fetch → Normalize → Dedup → Select → LLM Enrich → Render
新增:                                    │
                                         ▼
                            4.5 Market Join（实体→标的→行情/财报）
                                         ▼
                            4.6 Analysis（事件研究 / AI 指数 / SOTP / 私有估值）
                                         ▼
                                Render 增加「AI 资本 & 股价」板块
```

### 3.1 新表

```sql
CREATE TABLE companies (      -- 实体与标的映射
  id TEXT PRIMARY KEY, name TEXT, aliases_json TEXT, country TEXT,
  listing_type TEXT,          -- us / hk / cn / private / nonprofit
  tickers_json TEXT,          -- {"us":"SPCX","hk":"02513","cn":"002230"}
  cik TEXT, ai_exposure TEXT, -- pure / major / minor
  segments_json TEXT);

CREATE TABLE quotes_daily (   -- 行情
  ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL,
  adj_close REAL, volume INTEGER, source TEXT,
  PRIMARY KEY (ticker, date));

CREATE TABLE filings (        -- 公告/财报
  id TEXT PRIMARY KEY, company_id TEXT, form TEXT, filed_at TEXT,
  title TEXT, url TEXT, accession TEXT, source TEXT);

CREATE TABLE financials (     -- 财务指标（XBRL / 年报）
  company_id TEXT, period TEXT, metric TEXT, value REAL, unit TEXT,
  source TEXT);

CREATE TABLE funding_rounds ( -- 私有公司融资
  id TEXT PRIMARY KEY, company_id TEXT, announced_at TEXT,
  amount_usd REAL, valuation_usd REAL, investors TEXT, source TEXT, url TEXT);

CREATE TABLE events (         -- 与新闻对齐的 AI 事件
  id TEXT PRIMARY KEY, item_id TEXT, company_id TEXT, event_type TEXT,
  ai_theme TEXT, materiality INTEGER, event_date TEXT);

CREATE TABLE event_returns (  -- 事件研究结果
  event_id TEXT, benchmark TEXT, ar_1d REAL, car_3d REAL, car_5d REAL,
  t_stat REAL, method TEXT);

CREATE TABLE ai_narrative (   -- 叙事指数
  company_id TEXT, week TEXT, mention_count INTEGER, sentiment REAL,
  score REAL);
```

### 3.2 新 adapter

| adapter | 源 | 说明 |
|---|---|---|
| `yahoo_quote` | Yahoo chart | 美股日线，缓存 1h |
| `eastmoney_quote` | 东方财富 push2/push2his | 港股/A 股（+美股备选） |
| `sec_edgar` | data.sec.gov / efts.sec.gov | filings、XBRL、Form D；需 UA 带邮箱 |
| `hkex_filings` | HKEXnews | 港股 IPO/年报/招股书（官方） |
| `funding_feed` | TechCrunch/36Kr RSS + Form D | 融资新闻 + 备案 |
| `fx_rate` | Yahoo/Eastmoney | USD/HKD/CNY 换算 |

### 3.3 CLI

```bash
python -m newsagent market sync --tickers SPCX,META,GOOGL,2513.HK,0100.HK
python -m newsagent market filings --company META --forms 8-K,10-Q
python -m newsagent market study --company META --event-type capex
python -m newsagent market sotp --company GOOGL
python -m newsagent market private --company OpenAI
```

---

## 4. 日报里的「AI 资本 & 股价」板块

**A. AI 资本动态（每日）**
- 融资/并购/IPO/财报/指引/回购/监管罚款，一条一行；
- 每条标注：公司、是否上市、若上市给 `1 日 / 5 日涨跌幅`；
- 私有公司给「最新估值 / 融资轮次」状态。

**B. AI × 股价（每周或事件驱动）**
- 本周 AI 事件 CAR Top N（只列统计显著）；
- META / GOOGL / SPCX 的「AI 溢价」快照与变化；
- AI 叙事指数 vs 股价相关性；
- 一级市场估值变化（OpenAI/Anthropic/DeepSeek/Kimi…）。

**C. 免责声明（固定文案）**
- 数据延迟、来源（Yahoo/东方财富/SEC/HKEX）、非投资建议、不构成任何推荐。

---

## 5. 风险与合规

| 风险 | 说明 | 对策 |
|---|---|---|
| 行情源非官方 | Yahoo/东方财富均非官方、有延迟、可能限流 | 缓存、双源兜底、不对外分发原始数据 |
| SEC 限制 | 需 UA 带联系方式；10 req/s | 合规请求头、低频 |
| 事件研究方法偏差 | 财报/宏观事件混淆、盘后发布、样本少 | 排除财报窗口、用下一交易日、报告置信度 |
| 私有公司数据缺失 | Form D 可能是 SPV；中国融资额常不披露 | 标注来源与「未披露」，不编数 |
| 中概/港股流动性 | 智谱/MiniMax 波动大，事件窗口噪声高 | 用更宽窗口 + 显著性检验 |
| 数据许可 | 行情/新闻版权 | 个人研究用途；不转售、不公开分发原始数据 |
| 非投资建议 | 任何「AI 溢价」都是估算 | 固定免责声明 + 假设明示 |

---

## 6. 里程碑

| 阶段 | 内容 | 验收 |
|---|---|---|
| **M5a** | `companies.yaml` + 行情 adapter（Yahoo/东财）+ quotes_daily | 能取 SPCX/META/GOOGL/02513.HK/00100.HK 日线 |
| **M5b** | SEC EDGAR adapter（submissions/companyfacts/8-K/Form D） | 能拉 Meta/MiniMax 财报指标与最新公告 |
| **M5c** | 事件研究（市场模型 + CAR + t 检验） | 对 10 个 AI 硬事件输出 CAR 表 |
| **M5d** | 私有估值追踪 + 日报「AI 资本」板块 | 每周输出融资/估值表 |
| **M5e**（可选） | SOTP / AI 溢价模型 + 图表 | META/GOOGL/SPCX 三档估值表 |

---

## 7. 需要你确认

1. **上市标的范围**：只做「AI 是核心变量」的标的（SPCX、META、GOOGL、智谱、MiniMax），还是把 MSFT/NVDA/AMZN/阿里/腾讯/小米也纳入事件研究？
2. **私有公司范围**：OpenAI/Anthropic + 中国 DeepSeek/Kimi/StepFun，够不够？要不要加 Mistral/Cohere/Perplexity？
3. **分析输出**：事件研究 + AI 溢价（偏统计），还是只要「AI 资本动态」新闻列表（轻量）？
4. **数据合规**：行情用非官方免费源（个人研究），还是要接入付费数据（Alpha Vantage/Finnhub/Tushare）？
5. **SPCX 的 AI 拆分**：先做事件研究（不拆估值），还是等 S-1/10-K 分部数据再上 SOTP？
