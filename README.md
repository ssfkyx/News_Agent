# AI News Agent

个人 AI 新闻 Agent：多来源抓取 → 7 天时效闸门 → AI 整理/合并 → 头条 + 四板块日报（科技/财务/政策/具身智能） → 本地 HTML 界面 + 趋势分析。

> ⚠️ **重要：需要一个 LLM API Key（默认 DeepSeek，但兼容任意 OpenAI 格式接口）**
>
> 本项目通过 **OpenAI 兼容协议**调用大模型，并不绑定 DeepSeek。抓取、去重、股价图和原始标题不需要 key；
> 但**标题翻译、摘要、四板块分类、重要度、同事件合并依赖 LLM API**。
> 默认配置指向 DeepSeek（`llm.base_url: https://api.deepseek.com`、`llm.model: deepseek-flash`），
> 你也可以把 `base_url` / `model` 换成 OpenAI、OpenRouter、硅基流动、Ollama、vLLM 等任意兼容服务。
>
> DeepSeek 成本参考：一次完整日报约 8k–10k 输入 + 2k–3k 输出 token，约 **$0.003–0.01**；其他服务按各自价格。
> 没有 key 时只能用 `run --no-llm` 输出原始标题，日报基本不可读。
>
> `GITHUB_TOKEN` 是**可选**的：只用于把 GitHub API 限额从 60 次/小时提高，不填也能跑。

## 前置要求

- Windows 10/11
- Python 3.11+（推荐 3.12）
- 可访问外网（抓取新闻 + 调用 LLM API）

## 安装

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 第一次使用：配置 API Key

1. 生成密钥文件（任意命令都会自动创建；也可以手动复制 `config/keys.example.txt` 为 `keys.txt`）：

```bat
scripts\run.cmd doctor
```

2. 打开项目根目录的 `keys.txt`，填写：

```
LLM_API_KEY=你的key
GITHUB_TOKEN=github_pat_你的token   # 可选
```

兼容旧名称：`DEEPSEEK_API_KEY`、`OPENAI_API_KEY` 也可以直接用；本地 `ds_key.txt` 仍然有效。

3. 自检并生成第一份日报：

```bat
scripts\run.cmd doctor
scripts\run.cmd run
```

看到 `LLM_API_KEY: ok` 即配置成功。

**没有 API Key 时**：仍可运行 `scripts\run.cmd run --no-llm` 查看原始标题，或 `scripts\run.cmd market` / `html` 使用股价与已有报告功能；但无法生成正式日报。

**安全提醒**：`keys.txt`、`.env`、`ds_key.txt` 均已加入 `.gitignore`，不要提交或分享；泄露后请立即在平台吊销。

## 使用其他 OpenAI 兼容 API

默认是 DeepSeek，但代码只依赖 OpenAI 兼容协议。换成别的服务只需改两处：

1. `config/settings.yaml`：

```yaml
llm:
  base_url: https://api.openai.com/v1   # 或 OpenRouter / 硅基流动 / 本地 vLLM / Ollama
  model: gpt-4o-mini
  json_mode: true                       # 服务不支持 JSON mode 时改为 false
  thinking: default                     # 非 DeepSeek 保持 default
  send_thinking: false                  # 默认只有 base_url 含 deepseek 才发送 thinking 参数
```

2. `keys.txt` 填对应服务的 key：

```
LLM_API_KEY=你的key
```

常见服务示例：

| 服务 | base_url | 说明 |
|---|---|---|
| DeepSeek（默认） | `https://api.deepseek.com` | 本项目默认；成本低 |
| OpenAI | `https://api.openai.com/v1` | 模型填 `gpt-4o-mini` 等 |
| OpenRouter | `https://openrouter.ai/api/v1` | 一个 key 访问多家模型 |
| 硅基流动 | `https://api.siliconflow.cn/v1` | 国内可访问 |
| Ollama / vLLM（本地） | `http://127.0.0.1:11434/v1` 等 | key 随便填一个非空值即可 |

注意：不同服务对 `response_format` / `thinking` 的支持不同；本项目默认只在 DeepSeek 地址发送 `thinking` 参数，JSON mode 可通过 `json_mode: false` 关闭。

## 快速开始

**双击项目根目录的 `启动软件.cmd` 即可打开软件界面**（自动启动本地服务并打开 http://127.0.0.1:8765）。

其他一键脚本：

| 文件 | 作用 |
|---|---|
| `启动软件.cmd` | 启动本地界面并打开浏览器（打开时自动检查并刷新旧数据） |
| `停止软件.cmd` | 停止本地界面（8765 端口进程） |
| `查看最新日报.cmd` | 用默认程序打开最新 Markdown 日报 |
| `更新并查看报告.cmd` | **先完整刷新一次，再打开静态 HTML**（适合不想开界面时） |
| `最新报告.html` | **静态 HTML 日报**（离线快照；本身不会自动联网刷新） |

命令行方式（等价）：

```bat
:: 安装依赖后，以下命令在项目根目录执行
scripts\run.cmd doctor
scripts\run.cmd run --no-llm        :: 不调 LLM，出原始标题日报
scripts\run.cmd run                 :: 完整日报（需要 LLM_API_KEY）
scripts\run.cmd web                 :: 启动本地界面 http://127.0.0.1:8765
```

兼容旧配置：已有的 `.env` / `ds_key.txt` 继续有效，优先级为
`环境变量 > .env > keys.txt > ds_key.txt`；查看当前密钥状态：`scripts\run.cmd keys`。

## 数据什么时候刷新？

- **打开交互界面（`启动软件.cmd`）**：页面会检查最新报告的生成时间；超过
  `web.auto_refresh_minutes`（默认 60 分钟）就在后台自动跑一次完整刷新，状态栏显示进度，完成后自动加载新报告。
  同一个页面只自动触发一次；也可以随时点「生成日报」强制刷新。
- **静态 `最新报告.html`**：这是离线快照，浏览器打开时**不会**联网抓取。
  想“打开就是最新”请用 **`更新并查看报告.cmd`**（先跑完整刷新，再打开 HTML），或者直接用交互界面。
- **没有交互时**：Windows 计划任务每周一 07:30 自动跑一次（全量刷新）；电脑需开机，错过会在开机后补跑。
- 每次完整刷新会调用一次 LLM，成本参考上文（约 $0.003–0.01）；自动刷新有 60 分钟节流，不会每次刷新页面都花钱。

## 定时自动更新（每周一次，全量刷新）

Windows 任务计划每周后台跑「抓取 → 整理 → 报告」；每次都是**全量刷新**：重新抓取所有渠道，且不排除上次已展示过的条目，报告是最新窗口的完整快照（不是增量）。

**在项目目录下**（或使用下面的完整路径）执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\path\to\AI News Agent\scripts\install_schedule.ps1" -DaysOfWeek Monday -Time 07:30
```

如果提示找不到 scripts\install_schedule.ps1，说明当前目录不是项目目录；用上面带完整路径的命令即可。

```powershell
# 立即手动触发一次（验证）
powershell -NoProfile -Command "Start-ScheduledTask -TaskName 'AI News Agent Weekly'"

# 查看下次运行时间 / 上次结果
powershell -NoProfile -Command "Get-ScheduledTaskInfo -TaskName 'AI News Agent Weekly'"

# 卸载
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\path\to\AI News Agent\scripts\uninstall_schedule.ps1"
```

如果 `Register-ScheduledTask` 仍报错，可用 Windows 自带 schtasks 作为备用（在 PowerShell 里执行）：

```powershell
schtasks /Create /TN "AI News Agent Weekly" /TR '\"C:\path\to\AI News Agent\scripts\auto_run.cmd\"' /SC WEEKLY /D MON /ST 07:30 /F
```

说明：
- 任务执行 `scripts\auto_run.cmd`，日志写 `logs\auto.log`；每周一 07:30 运行（可用 `-DaysOfWeek` / `-Time` 改）。
- 已开启 **StartWhenAvailable**：电脑关机/睡眠错过时间，开机后自动补跑；仍需电脑开机才能执行。
- 全量刷新由 `settings.yaml` 的 `digest.full_refresh: true` 控制；财务/政策窗口仍为 30/90 天硬信息。
- **本开发环境的文件沙箱没有创建计划任务的权限**（`New-ScheduledTaskAction` 返回拒绝访问），所以任务需要你在自己的 PowerShell 里执行上面的安装命令。
- 如果之前装过旧的每日任务，请先卸载旧任务再装新的：`Unregister-ScheduledTask -TaskName 'AI News Agent Daily' -Confirm:$false`。

## 邮件推送（已停用）

按你的要求停用推送：`settings.yaml` 的 `email.enabled: false`，定时任务不再带 `--email`。
代码与邮件模板还在（`src/newsagent/notify.py`、`ui/email/report.html`），以后想恢复只需把 `enabled` 改回 `true`、配置 `SMTP_PASSWORD`，并在 `auto_run.cmd` 里加回 `--email`。手动预览仍可用：`scripts\run.cmd email-preview`。

## 命令

| 命令 | 说明 |
|---|---|
| `run` | 抓取 → 7d 闸门 → 去重 → 7d 排名 → LLM 整理/合并 → `out/<date>/digest.md` + `report.json` |
| `run --email` | 同上，并把日报邮件发送到配置的邮箱 |
| `run --no-llm` | 跳过 LLM，输出原始标题（排查抓取用） |
| `run --top 22 --window-days 7 --sources openai-news,hf-qwen` | 自定义条数/窗口/来源 |
| `fetch` | 只抓取入库，不生成日报 |
| `web` | 启动本地 HTML 界面（默认 `127.0.0.1:8765`） |
| `email-preview` | 生成邮件 HTML 预览（不发送） |
| `html` | 从最新报告重新导出 `最新报告.html`（不抓取） |
| `market` | 刷新固定关注列表的 90 天股价数据（有 12 小时缓存） |
| `keys` | 查看本地密钥状态；首次运行会自动生成 `keys.txt` 模板 |
| `doctor` | 自检配置、密钥、数据库 |

## 当前状态

- ✅ **60 个渠道**：科技/政策/财务原有 53 个，新增 7 个具身智能源（The Robot Report、IEEE Spectrum Robotics、TechCrunch Robotics、NVIDIA Robotics、Google News 具身智能中英查询、国务院政策·人形机器人）
- ✅ **首次使用密钥文件**：自动生成 `keys.txt` 模板；界面缺 key 时显示提示；兼容 `.env` / `ds_key.txt`
- ✅ **固定关注股价**：38 家已上市公司（美股 13 / 港股 11 / A 股 14）近 90 天收盘价折线图，仅显示最新价；股票区分两档：原有 AI 公司在上，机器人/具身智能 14 家作为新档位列在下方；排序为「中国在前 → 美国在后；美国组英伟达第一，其余按 A-Z」；12 小时缓存、失败自动跳过；配置在 `config/market.yaml`
- ✅ **四大板块**：科技与产品 / AI 公司财务与资本 / 政府与监管 AI 政策 / 具身智能（LLM 分类 + 配额精选 9/4/4/5；具身智能作为第四板块正常展示）
- ✅ **语言路由**：中国公司用中文源（中文媒体、Google News zh-CN、国务院/网信办），美国公司用英文源（官方 RSS、Google News en-US、NIST/EU/DOJ）
- ✅ **7 天硬闸门**：超窗拒收；无日期源用 first_seen；未来日期（changelog 下线日期）拒绝
- ✅ **去重**：抓取后聚类去重 + LLM 同事件归并（保留信息最完整的一条，标注「另有 N 家报道」）
- ✅ **头条最多 10 条**（重要度/分数排序），后面接四板块明细
- ✅ **财务/政策只留硬信息**：媒体解读条目即使被 LLM 判为 finance/policy，也会强制回科技板块；财务窗口 30 天、政策窗口 90 天（科技/具身智能 7 天，可在 settings 调整；具身智能允许媒体报道）
- ✅ **趋势分析 7/14/30 天可切换**，最近一次结果长期置顶展示（输入为全部 `report.json`）
- ✅ **HTML 界面**（stdlib `http.server`）：头条 + 四板块 + 固定关注股价 + 历史报告 + 后台生成 + 趋势分析 + 明暗主题
- ✅ **每周全量刷新**：Windows 任务计划每周一 07:30 后台跑；每次重新抓取全部渠道，且不排除历史已展示条目（`digest.full_refresh: true`）
- ✅ **静态 HTML 报告**：`最新报告.html` 数据内嵌、可离线双击查看（主题可切换），每次运行自动刷新
- ✅ **邮件推送已停用**（代码保留，可再开启）
- ✅ FP64：score/权重等浮点全部 IEEE-754 双精度（`tests/test_report_fp64.py` 断言）
- ✅ 单元测试 29 项通过；实测一次 22 条日报约 8k 输入 + 2.5k 输出 token（约 $0.003）
- ⏳ 待做：M5 投资/市场分析（设计已留存 [MARKET_INVESTMENT.md](MARKET_INVESTMENT.md)，需要时再接入；当前不自动运行）

**已知限制**：
- Google News 链接是跳转链接（可打开，非原站直链）；
- 财务/政策只留硬信息后，条数可能偏少（“少而硬”的取舍）；
- 港交所公告用东方财富接口（官方交易所的镜像），国务院政策库搜索结果需要在适配器里做关键词过滤。

## 结构

```
config/settings.yaml      全局配置（时效、日报条数、板块配额、LLM、web）
config/sources.yaml       渠道清单（rss / github / huggingface / docs / google_news / sec_8k / gov_policy / html_list / eastmoney_ann）
config/market.yaml        固定关注股价列表（38 家公司 + 90 天窗口/缓存配置）
config/prompts/           enrich_v3 + merge_v1 prompt
src/newsagent/            fetch → normalize → dedupe → select → enrich → merge → report → render
  web/server.py           本地 HTTP 接口（stdlib http.server）
ui/                       HTML 外壳 + JS + CSS + 明暗主题（外观层）
out/<date>/digest.md      日报
out/<date>/report.json    Report 快照（历史数据 / 趋势分析输入）
data/news.db              SQLite（items / digests / digest_items / llm_cache / llm_calls / runs / trend_reports）
scripts/                  run.cmd / auto_run.cmd / install_schedule.ps1
docs/ui-design.png        UI 设计图
```

## 已实现的规则

- **7 天硬闸门**：`published_at` 超窗拒收；无日期源用 `first_seen_at`；未来日期拒绝；详见 `FRESHNESS.md`。
- **7 天排名**：日报在 7d 窗口内按 `source_weight × recency × cluster_heat` 排名。
- **不重复**：`digest_items` 记录已展示 item，同一内容只出现一次。
- **硬信息约束**：财务/政策板块只允许 `hard_info: true` 的来源；媒体解读强制归科技板块。
- **LLM 降级**：坏 JSON / 空 content / 超时 → 重试一次 → 仍失败回退原文；merge 失败不影响主流程。
- **thinking 关闭（仅 DeepSeek）**：DeepSeek 默认 thinking 会吃掉输出预算，请求里已关闭；其他 OpenAI 兼容服务默认不发送该参数。

## 代码规范与可追溯（Coding Phase #2）

本项目按“文件头 + 结构化 docstring + ADR 双向追溯”执行：

- **文件头**：`src/`、`ui/`、`scripts/`、`config/*.yaml`、`tests/`、`tools/` 等每个代码/配置/脚本/UI 文件开头都有
  `Module / Responsibilities / Dependencies / Dependents / ADRs / Traceability` 块（47 个文件）。
- **公开函数 docstring**：`src/`、`tools/`、`docs/make_ui_mockup.py` 的公开函数/方法都包含
  `Preconditions / Postconditions / Prohibitions / Raises` 四段契约（26 个文件、约 90 个函数）。
- **行内注释**只解释“为什么”（约束、坑、不变量）；禁止代码复述、死代码和无条件 TODO。
- **ADR**：16 条，位于 `docs/decisions/`，状态/上下文/决策/理由/代价/代码位置齐全；
  代码头引用 ADR，ADR 反列文件与函数，索引见 `docs/decisions/README.md`。
- **自动校验**：`tests/test_traceability.py` 检查文件头、ADR 完整性/顺序/双向引用、docstring 结构；
  全套 **29 项测试通过**。

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_traceability.py" -v
```

## 文档

- `pre_architecture.md`：Trace Bullet 记录、Mermaid 类图、分层与接口、已确认决策
- `docs/ui-design.png`：HTML 界面设计图（`docs/make_ui_mockup.py` 生成）
- `ARCHITECTURE.md`：总体架构、数据模型、里程碑
- `OFFICIAL_SOURCES.md`：中美厂商官方渠道矩阵
- `MARKET_INVESTMENT.md`：股票/投资数据层方案（M5）
- `FRESHNESS.md`：渠道及时性实测 + 7 天闸门设计
