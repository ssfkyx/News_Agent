# 渠道及时性与 7 天时效闸门

> 需求：**只采集「请求时间前 7 天内」的信息**，因为 AI 变化太快。
> 方法：2026-11-08 18:30 UTC 逐渠道实测「最新一条的年龄」，并区分「发布时间」与「我们能不能及时看到」两件事。
> 结论：**7 天窗口可行**——主流 RSS/新闻页、GitHub、SEC、搜狗搜索都能落进窗口；但国内几家官方博客本身就是月更/季更，7 天内没新内容是正常的；另有 4 个坑必须处理（见 §5）。

---

## 0. 两个概念先分清

| 指标 | 含义 | 取决于 |
|---|---|---|
| **最新条目年龄**（本文实测值） | 该渠道最新一条内容是多久以前发布的 | 厂商**发布节奏**（低频渠道天然大） |
| **发现延迟**（我们多快能看到） | 从发布到进入我们库的时间 | **轮询间隔** + 源站索引延迟（RSS 分钟级、搜狗索引小时级、GitHub 分钟级） |

> 「7 天内没抓到这个渠道的新内容」≠ 抓取失败；低频渠道多数天为 0 是正常现象，需要监控区分「无更新」和「抓取失败」。

---

## 1. 实测：最新条目年龄（2026-11-08 18:30 UTC）

### 1.1 官方 RSS / 新闻页（主力，健康）

| 渠道 | 最新条目 | 年龄 | 7d 内通常有货 |
|---|---|---|---|
| OpenAI News RSS | 2026-11-06 08:00 | **2.4d** | ✅ |
| Meta Newsroom AI RSS | 2026-11-06 18:00 | **2.0d** | ✅ |
| Google AI 分类 RSS | 2026-11-05 17:00 | **3.1d** | ✅ |
| NVIDIA Blog RSS | 2026-11-06 16:00 | **2.1d** | ✅ |
| HuggingFace Blog RSS | 2026-11-06 14:00 | **2.2d** | ✅ |
| Ai2 Research RSS | 2026-11-06 08:00 | **2.4d** | ✅ |
| Mistral News RSS | 2026-11-05 12:00 | **3.3d** | ✅ |
| AWS News Blog RSS | 2026-11-04 23:34 | **3.8d** | ✅ |
| Microsoft Source AI RSS | 2026-10-21 | 18.1d | ⚠️ 稀疏（AI 专题更新慢，需补源） |
| Google Developers Blog RSS | 条目**无 pubDate** | ? | ⚠️ 需 first_seen 兜底 |
| OpenAI Developers RSS | 2026-05-05 | 187.8d | ❌ 已停更，弃用 |

### 1.2 文档 / 官方博客 / 研究页（低频多）

| 渠道 | 最新条目 | 年龄 | 7d 内通常有货 |
|---|---|---|---|
| StepFun 版本记录（.md） | 2026-11-05 | **3.8d** | ✅ |
| xAI Release Notes | 2026-11-02 | **6.8d** | ✅ 边缘 |
| DeepSeek Change Log | 2026-10-17 | 22.8d | ⚠️ 稀疏（重大版本才更） |
| Kimi 研究博客 | 2026-10-24 | 15.8d | ⚠️ 稀疏 |
| GLM 研究页 | 2026-09-10 | 59.8d | ⚠️ 月更 |
| 腾讯混元 产品动态 | 2026-06-22 | 139.8d | ❌ 季更（GitHub/HF 补） |
| 腾讯混元 更新历史 | 2026-09-23 | 46.8d | ⚠️ |
| MiMo Blog | 2025-12-16 | 327.8d | ❌ 停更（GitHub/HF 补） |
| OpenAI API Changelog | 解析到**未来日期**（2027-02-26） | ? | ⚠️ 需结构化解析（§5） |
| Anthropic Release Notes | 解析到未来日期（2026-11-30） | ? | ⚠️ 同上 |
| Google AI Studio Changelog | 解析到未来日期（2026-12-31） | ? | ⚠️ 同上 |

### 1.3 代码 / 模型发布信号（最快）

| 渠道 | 最新活动 | 年龄 |
|---|---|---|
| GitHub QwenLM / openai / microsoft / google-deepmind | push | **0–9 分钟** |
| GitHub xAI / Anthropic / Moonshot / DeepSeek | push | **2–7 小时** |
| GitHub StepFun / Tencent-Hunyuan / Mistral | push | 16–30 小时 |
| GitHub zai-org / XiaomiMiMo / meta-llama | push | 2.7 / 3.5 / 9 天 |
| HF 模型：tencent | 2026-11-07 | 28.2h |
| HF 模型：moonshotai | 2026-11-02 | 6.6d |
| HF 模型：其他 org | 22–205 天 | 事件驱动（发布时才刷新） |

> GitHub 是**最快**的机器信号（分钟级），但「push」≠「发布公告」，需要规则过滤（release/tag/README 变更）或 LLM 判断。

### 1.4 中国社媒 / 搜索 / 行情

| 渠道 | 实测 | 说明 |
|---|---|---|
| 微博热搜（ajax） | **实时**（51 条，0 分钟） | 免登录可抓；与 7d 窗口兼容 |
| 搜狗微信文章搜索 | 最新 **2.6h**，10 条里 6 条在 7 天内 | 内容很新，但反爬限制轮询频率（建议 4–8 次/天） |
| 东方财富 00700.HK | 最后交易日 2026-11-06（2.8d） | 周末正常；交易时段可拿实时 |
| Yahoo SPCX | 2026-11-06 21:00 UTC（45.5h） | 同上 |
| SEC Meta 最新 filings | 2026-11-06（424B5/Form 4，2.8d） | 8-K 11-05；官方源小时级可发现 |

---

## 2. 时效分级与轮询建议

| 层级 | 渠道 | 轮询间隔 | 预期发现延迟 | 约束 |
|---|---|---|---|---|
| **L0 实时** | GitHub releases/push（重点 repo）、微博热搜、行情（交易时段）、SEC EDGAR 8-K | 5–15 min | 分钟级 | GitHub 未鉴权 60/h：14 org × 4/h = 56/h，**必须加 token 或降到 30 min** |
| **L1 快** | OpenAI/Meta/Google/NVIDIA/HF/Ai2/Mistral/AWS 等 RSS、官方新闻页 | 30–60 min | ≈ 轮询间隔（RSS 无索引延迟） | 单站并发 ≤2、UA 正常、失败退避 |
| **L2 标准** | docs changelog、官方研究博客、搜狗关键词、StepFun 文档 | 3–6 h | 3–6h（搜狗另有索引延迟） | 搜狗每天 ≤8 次，随机抖动，命中验证码即暂停 |
| **L3 低频** | 月更/季更官方页（GLM research、混元产品动态、MiMo blog、Kimi 博客） | 24 h | ≤24h | 内容 hash 变化检测，`first_seen_at` 兜底 |

> 发现延迟 ≈ `轮询间隔 + 源站索引延迟`。例如搜狗：轮询 6h + 微信搜索索引延迟（小时级）→ 最坏 6–12h，仍远小于 7d。

---

## 3. 7 天时效闸门（核心设计）

### 3.1 数据字段

```python
published_at   # 源站给出的发布时间（UTC，可能缺失/错误）
first_seen_at  # 我们第一次抓到这个 URL/内容的时间（UTC）
last_seen_at   # 最近一次在源站看到它的时间
content_hash   # 标题+摘要+正文 hash，用于判断“页面内容变了”
```

### 3.2 入闸逻辑（伪代码）

```python
MAX_AGE = timedelta(days=7)
FUTURE_TOLERANCE = timedelta(hours=1)

def accept(item, now):
    ts = item.published_at or item.first_seen_at
    if item.published_at:
        if item.published_at > now + FUTURE_TOLERANCE:
            return False          # 未来日期：丢弃或修正（changelog 的“下线日期”不是发布时间）
        if now - item.published_at > MAX_AGE:
            return False          # 一周以外，不抓、不入库
    else:
        # 无日期源（如 Google Developers Blog RSS、部分列表页）：
        # 只接受“第一次见到”在 7 天内的新 URL/新内容 hash
        if now - item.first_seen_at > MAX_AGE:
            return False
    return True
```

- **无日期源**：用 `first_seen_at`；旧文章首次出现也算新（因为无法判断），但按 URL 去重，不会反复入库。
- **内容变更**：已存在条目内容 hash 变化 → 更新 `last_seen_at`，不算新条目（避免“老文置顶”反复入日报）。
- **时区**：统一存 UTC；源站无时区的按站点默认时区解析（RSS 常见 GMT/UTC，中国站点 +08:00）；展示时再转本地。
- **未来日期**：直接拒绝或回退到 `first_seen_at`，绝不进入 7d 窗口（§5 有实测踩坑）。

### 3.3 展示规则（7 天窗口内不重复）

- 候选池 = `published_at ∈ [now-7d, now]` 且 `未在历史日报展示过` 的条目；
- **日报（每天，已确认）**：直接在 **7 天窗口内按排名取 top N**（不是只看 24h 新增），这样低频渠道一周内的好内容不会漏；排序见 §2 与 `select` 规则；
- `digest_items` 表记录已展示 item_id，**同一内容只出现一次**（即使 7d 窗口内反复被选中）；
- 旧条目在窗口外自动过期，不再进入候选。

### 3.4 保留与清理

- `items` / `raw`：7 天后标记 `expired`，可清理（保留 digest 的标题/链接快照）；
- `quotes_daily`、`filings`、`market` 数据**不受 7d 限制**（分析需要历史）；
- 断档：若上次成功运行超过 7 天，仍然只回补 7 天，并写 `runs.gap=true` + 告警（明确告知可能有遗漏）。

### 3.5 配置样例

```yaml
freshness:
  max_age_days: 7
  future_tolerance_minutes: 60
  timezone: Asia/Shanghai       # 展示用；库内存 UTC
  digest:
    window_days: 7              # 已确认：日报在 7d 窗口内排名
    top_n: 20
    never_repeat: true
  purge_expired: true

sources:
  - id: openai-news
    tier: fast                  # L1：30–60min
    max_age_days: 7
  - id: github-qwen
    tier: realtime              # L0：5–15min（须配 GH token）
  - id: glm-research
    tier: daily                 # L3：24h，低频页
    undated: first_seen
    max_age_days: 7
```

---

## 4. 时效监控（区分“没更新”和“挂了”）

| 指标 | 用途 |
|---|---|
| `last_success_at` / 连续失败次数 | 抓取故障告警 |
| `newest_item_age`（最新条目年龄） | 趋势图；突然变老 → 源站改版/解析坏了 |
| `items_ingested_7d` | 该源 7 天内贡献条数；连续 14d=0 检查是否该降级/换源 |
| `parse_error_rate`、`future_date_rejections` | 数据质量告警（未来日期异常升高说明源站格式变了） |
| `run_gap_days` | >7d 断档告警 |

---

## 5. 实测踩到的坑（必须写进实现）

1. **changelog 里的“未来日期”不是发布时间**：OpenAI API changelog 解析到 2027-02-26、Anthropic 到 2026-11-30、Google AI Studio 到 2026-12-31——这些是**模型下线/生效日期**。必须按条目结构取日期字段，并过滤 `> now + 1h` 的日期；naive 正则取 max 会直接污染日报。
2. **无日期 feed**：Google Developers Blog RSS 的 item 没有 pubDate → 必须 `first_seen_at` 兜底。
3. **sitemap 无 lastmod**：DeepSeek 的 sitemap 只有 URL 列表 → 需要抓具体新闻页的日期字段。
4. **低频/停更渠道**：Kimi 博客 15.8d、GLM 研究页 59.8d、混元产品动态 139.8d、MiMo 博客 327.8d——7d 窗口内经常为 0，属正常；用 GitHub/HF/文档 changelog 补。
5. **行情周末不更新**：11-08 是周日，最后收盘是 11-06；日报要写「截至上周五收盘」，不要误报为“数据过期”。
6. **搜狗反爬**：内容很新（2.6h）但轮询不能快；建议每天 4–8 次、随机抖动、命中验证码立即暂停。

---

## 6. 结论：7 天窗口怎么落地

- **硬门槛**：所有新闻条目统一 `max_age_days=7`，入库前卡掉窗口外条目；无日期源用 `first_seen_at`；
- **保证新鲜**：L0/L1 渠道高频轮询（GitHub 需 token），保证 7d 窗口内的信息在数小时内出现；
- **接受稀疏**：低频官方博客 7 天内没内容很正常，靠 GitHub/HF/docs 补位，不强行“凑数”；
- **永不重复**：7d 窗口 + `never_repeat`，同一条内容只上一次日报；
- **断档友好**：超过 7 天没运行 → 只回补 7d + 告警，不静默丢数据；
- **市场数据例外**：行情/财报/融资记录不受 7d 限制，事件研究需要历史。

---

## 7. 已确认决策（2026-11-08）

1. **时效窗口**：新闻类渠道**严格 7 天**；公告/财报/行情数据不受 7d 限制（事件研究需要历史）。✅
2. **日报展示**：**在 7d 窗口内按排名取 top N**（不再只看 24h 新增）；同一条内容只出现一次。✅
3. **低频渠道**：**不保留**——GLM research、混元产品动态、MiMo blog 等低频/停更页面不接；用 GitHub、HuggingFace、文档 changelog 替代。✅
4. **GitHub token**：**配置只读 token**（`GITHUB_TOKEN`），避免 14 个 org 高频轮询打满未鉴权 60/h 限制。✅
