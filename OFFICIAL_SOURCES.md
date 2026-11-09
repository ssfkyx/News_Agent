# 大模型厂商官方信息渠道 · 可得性调研（中美）

> 对象：中国 7 家（Kimi、MiMo、DeepSeek、GLM、StepFun、Hunyuan、Qwen）+ 美国/西方 13 家（OpenAI、Anthropic、Google、Meta、xAI、Microsoft、Mistral、Amazon、NVIDIA、Cohere、Perplexity、Ai2、Hugging Face）。
> 方法：2026-11-08 从本机用真实 HTTP 请求逐一探测（无登录、单次、低频），记录状态码、内容形态（静态 HTML / SPA 壳 / JSON / RSS / Markdown）与可解析性。
> 结论：**20 家都能拿到官方发布，但渠道结构完全不同**——中国靠 GitHub/HF/文档/静态博客，美国靠 RSS + GitHub/HF + docs changelog；公众号/微博/X 这条社媒线基本走不通，中国有 3 家官网是 SPA。

---

## 0. 一句话结论（按可得性排序）

| 渠道 | 覆盖 | 实测 | 说明 |
|---|---|---|---|
| **GitHub 组织 / releases.atom** | 7/7 ✅ | 全部 200 | 无鉴权可用，org repos API + 仓库 releases.atom；DeepSeek 的 `deepseek-harness` releases.atom 407KB |
| **HuggingFace 组织模型 API** | 7/7 ✅ | 全部 200 | `models?author=<org>&sort=createdAt`，等于「模型发布」时间线（THUDM 已迁 zai-org） |
| **文档 changelog（Mintlify / 腾讯云文档 / Docusaurus）** | 6/7 ✅ | 全部 200 | Kimi/智谱/StepFun 的 llms.txt + `.md`；DeepSeek `/updates` + sitemap；腾讯云「更新历史」「产品动态」；MiMo 无文档站 |
| **官方博客 / 研究页（静态 HTML）** | 4/7 ✅ | Kimi blog、GLM research、MiMo blog、DeepSeek news | 可直接解析标题/日期/正文（Kimi/GLM/DeepSeek 文章页也是静态） |
| **RSS** | 美国 9/13 ✅，中国 0 | 全部 200 | OpenAI 新闻 RSS 1368 条、HF Blog 899 条、Google AI 分类 30KB；中国厂商官网无 feed |
| **官网新闻页（SPA）** | 3/7 ❌ | Qwen、StepFun、Hunyuan 官网首页/新闻页都是 JS 壳 | Googlebot UA 也拿不到内容；需 Playwright 或换替代页 |
| **微信公众号** | 0/7 ❌（订阅式） | 搜狗账号搜索对 8 个厂商名全部返回「暂无官方认证订阅号」 | 文章搜索可用（见下），但只能拿到被搜到的单篇；不能订阅某个号 |
| **微博官方号** | 0/7 ❌ | 所有页面跳 Sina Visitor System / 登录 | 匿名只能拿热搜榜 |
| **X (Twitter)** | 0/7 ❌ | 需登录 / 付费 API | 官方重要发布一般会同步到官网/GitHub/HF，损失可接受 |

**公众号补充实测**：搜狗微信**文章**搜索可用——返回标题、摘要、公众号名、Unix 时间戳（`timeConvert('1793671095')`）、跳转链接；链接页用 JS 拼接真实 `mp.weixin.qq.com/s?src=11&...` 地址，还原后可抓正文（实测拿到新华社文章全文）。但结果里都是媒体号（辽沈晚报、上海证券报…），**官方公众号的文章基本搜不到**。

**美国/西方厂商额外结论**：RSS 普及率非常高——OpenAI、Google、Meta Newsroom、Microsoft、AWS、NVIDIA、Mistral、Ai2、Hugging Face 都有可用 RSS（OpenAI 新闻 RSS 一次能拿 1368 条）；Anthropic / xAI / Cohere / Perplexity 没有 RSS，但新闻页是静态 HTML，可直接解析。GitHub 与 HuggingFace 逐家都可抓（Anthropic 没有 HF 模型，属正常）。详细矩阵见 §6。

---

## 1. 跨厂商通用渠道（建议做成通用 adapter）

### 1.1 GitHub（最稳）
```http
GET https://api.github.com/orgs/{org}/repos?sort=updated&direction=desc&per_page=5
GET https://github.com/{org}/{repo}/releases.atom
```
- 8 个 org 全部 200：`deepseek-ai`、`MoonshotAI`、`zai-org`、`THUDM`、`stepfun-ai`、`Tencent-Hunyuan`、`QwenLM`、`XiaomiMiMo`
- 未鉴权 60 次/小时；一轮监控 8–16 次请求，够用；加 token 可到 5000+/h
- 特别价值：`deepseek-ai/deepseek-harness`（276k stars，2026-11-04 有 push）的 releases.atom 可直接当「DSH 更新日志」
- 注意：`zai-org` 是智谱新组织，`THUDM` 仍在但基本停更

### 1.2 HuggingFace
```http
GET https://huggingface.co/api/models?author={org}&sort=createdAt&direction=-1&limit=10
```
- 7/7 可用，返回 `id + createdAt`，天然是模型发布流
- 实测抓到的样例（2026-11）：`deepseek-ai/DeepSeek-V4.1-Flash-1017`、`moonshotai/Kimi-K3.1-Pro`、`zai-org/GLM-5.3`、`stepfun-ai/Step-5-Preview`、`XiaomiMiMo/MiMo-V2.6-*`、`tencent/Hy-Nomas-*`、`Qwen/Qwen-Image-2.1`
- `THUDM` 已空，用 `zai-org`；`tencent` 是混元/腾讯视觉模型混合 org

### 1.3 文档 changelog（Mintlify `.md` 直读，非常舒服）
- 三家都是 Mintlify 文档：`platform.kimi.com/docs`、`docs.bigmodel.cn`、`platform.stepfun.com/docs`
- 每个文档站都有 `llms.txt` 索引，且每页 URL 加 `.md` 直接返回纯 Markdown，例如：
  - `https://platform.stepfun.com/docs/zh/step-code/release-notes.md`（版本记录，实测 v0.1.7 / 2026-11-05）
  - `https://docs.bigmodel.cn/llms.txt`（含模型概览、迁移文档）
  - `https://platform.kimi.com/docs/llms.txt`
- 腾讯云文档是静态 HTML：混元「产品动态」`cloud.tencent.com/document/product/1729/97765`（917KB，按年月归档）+「更新历史」`.../1729/101849`（265KB，第 53 次发布…），均可正则解析
- DeepSeek：`api-docs.deepseek.com/updates`（Change Log）+ `sitemap.xml`（列出全部 `/news/newsYYMMDD` 文章，实测 21 篇，最新 2026-10-17）

---

## 2. 逐家矩阵

图例：✅ 静态可解析 / ⚠️ 有条件可用 / ❌ 不可用

### DeepSeek（深度求索）
| 渠道 | 端点 | 实测 |
|---|---|---|
| 官网新闻 | `api-docs.deepseek.com/news/newsYYMMDD`（sitemap 发现） | ✅ 静态，最新 `news261017`（V4.1-Flash，2026-10-17） |
| Change Log | `api-docs.deepseek.com/updates` | ✅ 静态 |
| DSH 文档 | `deepseek-harness.github.io/deepseek-harness/...` | ✅ 静态（根路径 404，注意 base path） |
| GitHub | `deepseek-ai`（含 `deepseek-harness` releases.atom） | ✅ |
| HuggingFace | `deepseek-ai` | ✅ V4.1-Flash 系列 |
| 公众号 | 官方声明：唯一官方公众号「DeepSeek」（`user_name=gh_bc02ff24ae0f`；[官方渠道说明](https://mp.weixin.qq.com/s/u5coDiS5lXKjENlu1ghcoQ)） | ⚠️ 号存在，但无法拉文章列表 |
| 微博 | 无（官方声明渠道只有公众号/小红书/X） | ❌ |

**推荐组合**：docs news + updates + GitHub(dsh releases) + HF。

### Kimi（月之暗面）
| 渠道 | 端点 | 实测 |
|---|---|---|
| 研究博客 | `www.kimi.com/blog` | ✅ 静态，文章链接可提取（`/blog/kimi-k3-1-pro` 等），文章页 336KB 静态可读 |
| 公司研究列表 | `www.moonshot.cn` | ✅ 静态，带日期（K3.1 Pro 2026-10-24） |
| API 文档 | `platform.kimi.com/docs` + `llms.txt` | ✅ Mintlify，`.md` 直读 |
| GitHub | `MoonshotAI`（Kimi-K3、kimi-code、kimi-cli） | ✅ |
| HuggingFace | `moonshotai`（Kimi-K3.1-Pro 2026-11-02） | ✅ |
| 公众号 / 微博 | 有号 | ⚠️ 公众号搜狗不可订阅；微博需登录 |

**推荐组合**：blog HTML + llms.txt + GitHub/HF。

### GLM（智谱 / Z.ai）
| 渠道 | 端点 | 实测 |
|---|---|---|
| 研究页 | `www.zhipuai.cn/zh/research` | ✅ 静态，14 条带日期（GLM-5.3-Flash 2026/08/26…） |
| 研究详情 | `www.zhipuai.cn/zh/research/155` | ✅ 静态，正文可读 |
| 文档 | `docs.bigmodel.cn` + `llms.txt` | ✅ Mintlify；`bigmodel.cn` 本身是 SPA ❌ |
| GitHub | `zai-org`（ZCode、GLM-OCR…）、`THUDM`（基本停更） | ✅ |
| HuggingFace | `zai-org`（GLM-5.3 系列） | ✅ |
| 公众号 / 微博 | 有号 | ⚠️ 同上 |

**推荐组合**：research 页 + docs llms.txt + GitHub/HF。

### StepFun（阶跃星辰）
| 渠道 | 端点 | 实测 |
|---|---|---|
| 官网 / 新闻 | `www.stepfun.com`、`/news` | ❌ 1954 字节 SPA 壳（Googlebot UA 也一样）；sitemap 只有首页 |
| 平台文档 | `platform.stepfun.com/docs` + `llms.txt` | ✅ |
| 版本记录 | `.../docs/zh/step-code/release-notes.md` | ✅ 纯 Markdown，v0.1.7（2026-11-05） |
| GitHub | `stepfun-ai`（Step-5-Preview、Step-Code…） | ✅ |
| HuggingFace | `stepfun-ai` | ✅ |
| 公众号 | 阶跃星辰 | ⚠️ |

**推荐组合**：docs 版本记录 + GitHub/HF；官网新闻留给 Playwright（可选）。

### Hunyuan（腾讯混元）
| 渠道 | 端点 | 实测 |
|---|---|---|
| 官网 | `hunyuan.tencent.com` | ❌ 6.8KB SPA 壳，`/blog` `/news` 同壳 |
| 腾讯云文档 | `cloud.tencent.com/document/product/1729` | ✅ 静态 |
| 产品动态 | `.../1729/97765` | ✅ 静态 917KB，按年月归档 |
| 更新历史 | `.../1729/101849` | ✅ 静态 265KB（第 53 次发布…） |
| GitHub | `Tencent-Hunyuan`（HunyuanVideo、Hy-Memory…） | ✅ |
| HuggingFace | `tencent`（`Hy-Nomas*`、`WeVisOne*` 等） | ✅ |
| 公众号 | 腾讯混元 | ⚠️ |

**推荐组合**：腾讯云「产品动态/更新历史」+ GitHub/HF。

### Qwen（通义千问 / 阿里云）
| 渠道 | 端点 | 实测 |
|---|---|---|
| 官网 | `qwen.ai` | ❌ SPA，任何路径都返回同一 92KB 壳 |
| 旧博客 | `qwenlm.github.io/blog` | ❌ 已公告跳转 qwen.ai |
| 阿里云新闻室 | `alibabacloud.com/zh/press-room` | ✅ 静态 291KB，Qwen 提及 18 次 |
| 百炼产品月报 | `developer.aliyun.com/article/1777815` | ✅ 静态，阿里云百炼月报（2026年10月） |
| GitHub | `QwenLM`（qwen-code、Qwen3-*） | ✅ |
| HuggingFace | `Qwen`（Qwen-Image-2.1…） | ✅ |
| 公众号 | 通义千问 | ⚠️ |

**推荐组合**：阿里云新闻室 + 百炼月报 + GitHub/HF；`qwen.ai/blog` 走 Playwright（M4 可选）。

### MiMo（小米）
| 渠道 | 端点 | 实测 |
|---|---|---|
| 官网 / 博客 | `mimo.xiaomi.com/blog`、`/zh/blog/index` | ✅ 静态 Rspress（30KB），可见文章正文（MiMo-V2-Flash 2025-12-16…）；文章 slug 需再解析 |
| GitHub | `XiaomiMiMo`（MiMo-Code、MiMo-Audio…） | ✅ |
| HuggingFace | `XiaomiMiMo`（MiMo-V2.6 系列） | ✅ |
| 公众号 | 小米 MiMo / 小米技术 | ⚠️ |

**推荐组合**：博客 HTML + GitHub/HF。

---

## 3. 对管线的建议：新增 4 个 adapter

| adapter | 数据源 | 输出 | 备注 |
|---|---|---|---|
| `github_release` | 8 个 org 的 repos API + 重点 repo 的 releases.atom | 版本号、标题、发布时间、链接 | 无鉴权 60/h，缓存 1h |
| `hf_org_models` | HF `models?author=` | 模型 ID、创建时间、链接 | 模型发布最快信号 |
| `docs_changelog` | Mintlify `llms.txt`/`.md`、DeepSeek `/updates`、腾讯云产品动态/更新历史、DeepSeek sitemap news | 文档更新条目 | 每家一个 parser，输出统一 schema |
| `html_blog_list` | Kimi blog、GLM research、MiMo blog、DeepSeek news | 标题/日期/链接/摘要 | 每站一个 CSS/正则 parser |
| `sogou_wechat_kw`（可选） | 搜狗文章搜索关键词 | 标题/摘要/公众号名/时间/链接（+可选正文） | 低频；只作补充；**不能当订阅** |
| `playwright_spa`（M4 可选） | qwen.ai、stepfun.com/news、hunyuan.tencent.com | 新闻列表 | 重、慢，先不放进 MVP |

**权重建议**：官方发布（GitHub/HF/docs/官网博客）> 官方新闻页 > 媒体转载。日报里可以单列一个「厂商官方发布」板块，按厂商分组。

**明确不做的**：公众号订阅（无公开接口）、微博官方号（登录墙）、X/Twitter（API 门槛）、小红书（风控）。

---

## 4. 风险与限制

| 风险 | 说明 | 对策 |
|---|---|---|
| GitHub 限流 | 未鉴权 60 次/小时/IP | 每轮 8–16 次 + 结果缓存 1h；可加 token |
| HF 限流 | 无鉴权有隐性频控 | 缓存、低频 |
| Mintlify 页面结构变化 | llms.txt 路径/格式可能调整 | 解析失败降级到搜索页/跳过，不阻塞 |
| 搜狗反爬 | 会弹验证码/403，抓得越勤坏得越快 | 低频、会话隔离、失败跳过、不做核心依赖 |
| SPA 站点 | Qwen/StepFun/Hunyuan 官网正文拿不到 | 用替代渠道；Playwright 放 M4 |
| 公众号/微博/X | 无法获取 | 不承诺；用户投喂或第三方服务 |
| 版权 | 厂商官方公告 | 只存标题 + 短摘要 + 链接，正文不落盘不外发 |

---

## 5. 待确认

1. 日报里是否固定加「厂商官方发布」板块？我建议加，并把它排在媒体转载之前。
2. Qwen / StepFun / Hunyuan 的 SPA 官网：先接受替代渠道，还是 M4 上 Playwright？
3. MiMo 的文章链接解析、GLM research 的详情链接解析，是否需要我继续把每站的 parser 写死？
4. 公众号是否接 wechat2rss（¥150/年，可订阅任意号）或半自动投喂？
5. 厂商名单是否就按「美国 13 家 + 中国 7 家 + Mistral」定？观察名单（§7）要不要留？
6. 无 RSS 的 Anthropic / xAI / Cohere / Perplexity：接受 HTML parser，还是先只监控有 RSS 的厂商？
7. 「厂商官方发布」板块按公司分组，还是按时间线混排？

## 6. 美国 / 西方厂商矩阵（2026-11-08 实测）

### 6.1 总览

| 厂商 | 官方新闻/博客 | RSS | 文档 changelog | GitHub | HF | 推荐主渠道 |
|---|---|---|---|---|---|---|
| **OpenAI** | `openai.com/news`（静态 390KB） | ✅ `openai.com/news/rss.xml`（**1368 条**）+ `developers.openai.com/rss.xml`（135 条） | ✅ `developers.openai.com/api/docs/changelog` + llms.txt + `.md` | ✅ `openai` | ✅ `openai` | RSS + dev changelog |
| **Anthropic** | `anthropic.com/news`（静态 354KB）+ `/engineering` | ❌ 无 RSS | ✅ `platform.claude.com/docs/en/release-notes/overview`（静态 1.28MB）+ llms.txt 97KB | ✅ `anthropics` | ⚠️ 空 | newsroom HTML + release notes |
| **Google** | `blog.google` AI 分类（静态）+ `deepmind.google/blog` | ✅ `blog.google/technology/ai/rss/`（30KB）+ developers blog feed | ✅ `aistudio.google.com/docs/changelog` + llms.txt | ✅ `google-deepmind` / `google` | ✅ `google` | AI 分类 RSS + changelog |
| **Meta** | `about.fb.com/news/tag/ai/`（静态） | ✅ `about.fb.com/news/tag/ai/feed/`（10 条） | ❌ 旧 `ai.meta.com/blog` 返回 400 | ✅ `meta-llama` | ✅ `meta-llama` | Newsroom AI RSS |
| **xAI** | `x.ai/news`（静态 250KB） | ❌ 无 RSS | ✅ `docs.x.ai/developers/release-notes`（静态 552KB）+ llms.txt | ✅ `xai-org` | ✅ `xai-org` | news HTML + release notes |
| **Microsoft** | `news.microsoft.com/source/topics/ai/`（静态） | ✅ `.../topics/ai/feed/`（10 条） | —（旧 `blogs.microsoft.com/ai/feed/` 已 410） | ✅ `microsoft` | ✅ `microsoft` | AI 分类 RSS |
| **Mistral** | `mistral.ai/news`（静态 1.28MB） | ✅ `mistral.ai/news/rss`（RSS 2.0） | ✅ `docs.mistral.ai/llms.txt`（102KB） | ✅ `mistralai` | ✅ `mistralai` | RSS |
| **Amazon** | `aws.amazon.com/blogs/aws/`（静态） | ✅ AWS News Blog feed（20 条）+ aboutamazon feed | Bedrock 文档 | ✅ `aws` | ✅ `amazon` | AWS RSS |
| **NVIDIA** | `blogs.nvidia.com`（静态） | ✅ `blogs.nvidia.com/feed/`（18 条） | — | ✅ `NVlabs` | ✅ `nvidia` | RSS |
| **Cohere** | `cohere.com/blog`（静态 1.35MB） | ❌ 无 | ⚠️ `docs.cohere.com/llms.txt` 仅 662B | ✅ `cohere-ai` | ✅ `CohereLabs` | blog HTML |
| **Perplexity** | `perplexity.ai/hub/blog`（静态 286KB） | ❌ 404 | — | — | — | blog HTML |
| **Ai2** | `allenai.org/research`（静态 1.14MB） | ✅ `allenai.org/rss.xml`（25 条） | — | ✅ `allenai` | ✅ `allenai` | RSS |
| **Hugging Face** | `huggingface.co/blog`（静态） | ✅ `huggingface.co/blog/feed.xml`（**899 条**） | — | ✅ | ✅ models API | RSS + models API |

### 6.2 关键细节

- **OpenAI**：`openai.com/news/` 是 Next.js 静态页；真正的宝藏是 **news RSS（1368 条历史）** 和**开发者 RSS**。API changelog 在 `developers.openai.com/api/docs/changelog`，支持 `llms.txt` 和每页 `.md`。HF 上是开放权重（gpt-oss 等）。
- **Anthropic**：无 RSS，但 newsroom 是静态 HTML；`docs.anthropic.com/llms.txt` 列全文档，`release-notes/overview` 是静态 1.28MB 的大页面，可直接抽版本条目。GitHub 很活跃（`skills`、`claude-plugins-official`）。
- **Google**：正确 RSS 是 `blog.google/technology/ai/rss/`（注意**不是** `rss.xml`，实测 404）；DeepMind blog 静态；Gemini API 的 release notes 在 AI Studio 文档站，`llms.txt` 可索引。
- **Meta**：旧 `ai.meta.com/blog` 现在返回 400（不稳定），官方新闻走 **Meta Newsroom 的 AI 标签 RSS**；开发者入口是 `dev.meta.ai`（Muse 模型），GitHub/HF 仍是 Llama 系。
- **xAI**：无 RSS，但 news 页和 docs release notes 都静态；页面品牌显示为 **SpaceXSI**（xAI/X 合并后的新品牌），域名仍是 `x.ai`。
- **Microsoft**：旧 AI RSS 已 410，正确地址是 `news.microsoft.com/source/topics/ai/feed/`；GitHub/HF 有 Phi 等模型。
- **Mistral / AWS / NVIDIA / Ai2 / HF**：都是干净 RSS，最省事；Cohere / Perplexity 只有静态博客（parser 可写，优先级低）。

### 6.3 中美渠道结构对比

| 维度 | 中国 7 家 | 美国/西方 13 家 |
|---|---|---|
| RSS 覆盖 | 0 家（官方站点无 feed） | **9/13** 有（OpenAI、Google、Meta、Microsoft、AWS、NVIDIA、Mistral、Ai2、HF） |
| 新闻页可解析性 | 4 家静态，3 家 SPA | 13 家新闻页均静态（Meta 旧博客 400 是唯一坑） |
| GitHub / HF | 通用可抓 | 通用可抓（Anthropic 无 HF） |
| 社媒 | 公众号/微博/X 不可 | X 不可，但有 RSS/官网/GitHub 兜底 |
| 落地成本 | 每家要写 parser | **RSS 一把梭** + GitHub/HF 兜底，成本低很多 |

---

## 7. 「还有谁」——建议纳入的厂商名单

**第一梯队（建议全接，共 21 家）**

- 美国 12：OpenAI、Anthropic、Google（Gemini/DeepMind）、Meta（Llama/Muse）、xAI（Grok）、Microsoft（Copilot/Phi）、NVIDIA（Nemotron/开源）、Amazon（Nova/Bedrock）、Cohere、Perplexity、Ai2（Olmo）、Hugging Face（生态风向标）
- 中国 7：DeepSeek、Kimi、GLM、Qwen、StepFun、Hunyuan、MiMo
- 欧洲 1：Mistral（已实测，有 RSS）
- 另：xAI 页面品牌为 SpaceXSI，可按 xAI 记录

**观察名单（按需，模型发布少但行业信号强）**

- 前沿实验室：Thinking Machines Lab、SSI（Safe Superintelligence）、Physical Intelligence
- 推理/基础设施：Together AI、Groq、Cerebras、Fireworks AI
- 多模态/消费级：Stability AI、Character.AI、Reka AI、AI21 Labs
- 中国其他（若要覆盖全）：百川智能、MiniMax、零一万物、商汤日日新、科大讯飞星火、腾讯元宝等

---

## 8. 更新后的 adapter 覆盖（中美合并）

| adapter | 覆盖 | 备注 |
|---|---|---|
| `rss` | ~10 个 feed：OpenAI news、Google AI、Meta Newsroom AI、Microsoft AI、AWS、NVIDIA、Mistral、Ai2、HF Blog、Google Dev Blog | 一行配置一个 feed，最优先 |
| `docs_changelog` | OpenAI、Anthropic、Google AI Studio、xAI、Mistral、DeepSeek、Kimi、智谱、StepFun、腾讯云混元 | `.md` 优先，HTML 兜底 |
| `github_release` | 全部 20 家（org repos + releases.atom） | 通用，无鉴权够用 |
| `hf_org_models` | 19 家（Anthropic 无） | 模型发布最快信号 |
| `html_blog_list` | Anthropic newsroom、DeepMind blog、xAI news、Cohere、Perplexity、Kimi、GLM、MiMo、DeepSeek news | 每站一个 parser |
| `sogou_wechat_kw` | 中国补充 | 低频，不做核心 |
| `playwright_spa`（M4） | qwen.ai、stepfun.com/news、hunyuan.tencent.com、dev.meta.ai | 重、慢，MVP 不做 |

**结论**：美国 13 家里有 9 家直接 RSS 解决，剩下 4 家用 HTML parser；中国 7 家全部走 docs/blog/GitHub/HF——**20 家没有一家是"完全拿不到"**。

---

## 9. 风险补充（美国）

| 风险 | 说明 | 对策 |
|---|---|---|
| 无 RSS 的四家 | Anthropic / xAI / Cohere / Perplexity 需 HTML parser，结构一变就坏 | parser 失败跳过；优先 docs/GitHub 兜底 |
| Meta 旧博客 400 | `ai.meta.com/blog` 实测不可用 | 用 `about.fb.com/news/tag/ai/feed/` |
| 大 feed 体积 | OpenAI news RSS 833KB/1368 条 | 只取最近 24–48h，别全量入库 |
| 风控 | 美国站点多走 Cloudflare/Akamai，本次都未触发 | 正常 UA/Accept 头 + 低频；失败重试一次 |
| X/Twitter | 仍不可抓 | 美国厂商重要发布在 RSS/官网/GitHub 均有备份，损失小 |

> 附：本调研脚本与原始输出未入库（临时文件），可通过 `ARCHITECTURE.md` 的 adapter 设计落地。
