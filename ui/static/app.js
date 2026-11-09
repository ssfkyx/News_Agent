/*
 * Module: ui.static.app
 * Responsibilities: Client-side rendering of report/trend API data and run controls (appearance only).
 * Dependencies: browser fetch API
 * Dependents: ui/index.html
 * ADRs: ADR-0010
 * Traceability: docs/decisions/README.md
*/
/* AI News Agent · UI logic (appearance only; all data comes from /api/*). */

const THEME_KEY = "ai-news-agent-theme";
const state = { report: null, reports: [], pollTimer: null, trendDays: 7 };

const $ = (selector) => document.querySelector(selector);

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({ error: response.statusText }));
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data;
}

function fmtTime(value) {
  if (!value) return "时间未知";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

function fmtDay(value) {
  if (!value) return "时间未知";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "时间未知";
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function itemNode(item) {
  const node = el("article", "item");
  const title = el("h4", "item-title");
  if (item.url) {
    const link = el("a", "item-title-link", item.title_zh || item.title || "(无标题)");
    link.href = item.url;
    link.target = "_blank";
    link.rel = "noopener";
    title.append(link);
  } else {
    title.textContent = item.title_zh || item.title || "(无标题)";
  }
  node.append(title);
  const summary = item.summary_zh || item.summary || "";
  if (summary) node.append(el("p", "item-summary", summary));
  node.append(el("div", "item-meta", fmtDay(item.published_at)));
  return node;
}

function renderStats(report) {
  const box = $("#stats");
  box.innerHTML = "";
  const counts = { tech: 0, finance: 0, policy: 0, embodied: 0 };
  (report.sections || []).forEach((section) => {
    counts[section.key] = (section.items || []).length;
  });
  const windows = report.windows || { tech: report.window_days || 7, finance: 30, policy: 90, embodied: 7 };
  const cards = [
    [String(counts.tech), "科技与产品"],
    [String(counts.finance), "财务与资本"],
    [String(counts.policy), "政策与监管"],
    [String(counts.embodied), "具身智能"],
    [`${windows.tech}/${windows.finance}/${windows.policy}/${windows.embodied} 天`, "窗口"],
    [report.model || "off", "整理模型"],
  ];
  cards.forEach(([num, label]) => {
    const card = el("div", "stat");
    card.append(el("div", "num", num), el("div", "label", label));
    box.append(card);
  });
}

function renderLeads(leads) {
  const box = $("#leads");
  box.innerHTML = "";
  if (!leads || !leads.length) {
    box.append(el("div", "empty", "本期没有头条。"));
    return;
  }
  leads.forEach((item, index) => {
    const card = el("article", "lead");
    const head = el("div", "lead-head");
    head.append(el("span", "lead-rank", String(index + 1)));
    const heading = el("h3", "lead-title");
    if (item.url) {
      const link = el("a", "item-title-link", item.title_zh || item.title || "(无标题)");
      link.href = item.url;
      link.target = "_blank";
      link.rel = "noopener";
      heading.append(link);
    } else {
      heading.textContent = item.title_zh || item.title || "(无标题)";
    }
    head.append(heading);
    card.append(head);
    card.append(el("p", "lead-summary", item.summary_zh || item.summary || ""));
    card.append(el("div", "lead-meta", fmtDay(item.published_at)));
    box.append(card);
  });
}

function renderSections(sections) {
  const box = $("#sections");
  box.innerHTML = "";
  (sections || []).forEach((section) => {
    const wrapper = el("section", "section");
    const head = el("div", "section-head");
    head.append(el("h2", "", section.title || section.key));
    head.append(el("span", "count", `${(section.items || []).length} 条`));
    wrapper.append(head);

    if (!section.items || !section.items.length) {
      wrapper.append(el("div", "empty", "近 7 天没有符合条件的新内容。"));
      box.append(wrapper);
      return;
    }

    const groups = new Map();
    section.items.forEach((item) => {
      const company = item.company || "其他";
      if (!groups.has(company)) groups.set(company, []);
      groups.get(company).push(item);
    });
    groups.forEach((items, company) => {
      const group = el("div", "company");
      group.append(el("h3", "", company));
      items.forEach((item) => group.append(itemNode(item)));
      wrapper.append(group);
    });
    box.append(wrapper);
  });
}

function renderHistory(reports) {
  const list = $("#history");
  list.innerHTML = "";
  (reports || []).forEach((report) => {
    const item = el("li", "");
    item.append(el("span", "date", report.date));
    item.append(el("span", "count", `${report.item_count} 条`));
    if (state.report && state.report.date === report.date) item.classList.add("active");
    item.addEventListener("click", () => loadReport(report.date));
    list.append(item);
  });
  if (!reports || !reports.length) {
    list.append(el("li", "empty", "暂无历史报告"));
  }
}

function sparkline(points) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "spark");
  svg.setAttribute("viewBox", "0 0 220 64");
  svg.setAttribute("preserveAspectRatio", "none");
  const values = (points || []).map((point) => Number(point.close)).filter(Number.isFinite);
  if (values.length < 2) return svg;
  const width = 220;
  const height = 64;
  const pad = 4;
  const low = Math.min(...values);
  const high = Math.max(...values);
  const span = (high - low) || 1;
  const step = (width - 2 * pad) / (values.length - 1);
  const coordinates = values.map((close, index) => {
    const x = pad + index * step;
    const y = pad + (height - 2 * pad) * (1 - (close - low) / span);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const polyline = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  polyline.setAttribute("points", coordinates.join(" "));
  svg.append(polyline);
  return svg;
}

function marketCard(item) {
  const card = el("article", "mcard");
  const head = el("div", "mhead");
  head.append(el("span", "mname", item.name || ""));
  head.append(el("span", "mcode", `${item.market || ""} · ${item.code || ""}`));
  card.append(head, el("div", "mprice", Number(item.latest || 0).toFixed(2)),
    sparkline(item.points || []), el("div", "mrange", item.latest_date || ""));
  return card;
}

function renderMarket(market) {
  const panel = $("#market-panel");
  const grid = $("#market-grid");
  if (!panel || !grid) return;
  const robotGrid = $("#robot-grid");
  const subhead = $("#robot-subhead");
  grid.innerHTML = "";
  if (robotGrid) robotGrid.innerHTML = "";
  const items = (market && market.items) || [];
  if (!items.length) {
    panel.classList.add("hidden");
    return;
  }
  panel.classList.remove("hidden");
  const count = $("#market-count");
  if (count) count.textContent = `${items.length} 家`;
  const mainItems = items.filter((item) => item.group !== "robot");
  const robotItems = items.filter((item) => item.group === "robot");
  mainItems.forEach((item) => grid.append(marketCard(item)));
  if (subhead && robotGrid) {
    if (robotItems.length) {
      subhead.classList.remove("hidden");
      const robotCount = $("#robot-count");
      if (robotCount) robotCount.textContent = `${robotItems.length} 家`;
      robotItems.forEach((item) => robotGrid.append(marketCard(item)));
    } else {
      subhead.classList.add("hidden");
    }
  }
}

function renderReport(report) {
  state.report = report;
  $("#report-date").textContent =
    `${report.date} · 近 ${report.window_days} 天窗口 · ${report.degraded ? "降级输出" : "正常"}`;
  renderStats(report);
  renderLeads(report.leads);
  renderSections(report.sections);
  renderMarket(report.market);
  renderHistory(state.reports);
}

async function loadReport(date) {
  try {
    const path = date ? `/api/report/${date}` : "/api/report/latest";
    const data = await api(path);
    renderReport(data.report);
  } catch (error) {
    $("#report-date").textContent = `暂无报告：${error.message}`;
    $("#leads").innerHTML = "";
    $("#sections").innerHTML = "";
    const panel = $("#market-panel");
    if (panel) panel.classList.add("hidden");
  }
}

async function loadHistory() {
  try {
    const data = await api("/api/reports");
    state.reports = data.reports || [];
    renderHistory(state.reports);
  } catch (error) {
    console.warn("history failed", error);
  }
}

function setStatus(text, stateName) {
  const status = $("#status");
  status.dataset.state = stateName;
  $("#status-text").textContent = text;
}

async function refreshStatus() {
  const data = await api("/api/status");
  const status = data.status;
  if (status.running) {
    setStatus(`生成中…（${fmtTime(status.started_at)} 开始）`, "running");
    schedulePoll();
    return true;
  }
  if (status.error) {
    setStatus(`上次失败：${status.error}`, "error");
    return false;
  }
  if (status.finished_at) {
    setStatus(`上次完成：${fmtTime(status.finished_at)}`, "done");
    return false;
  }
  setStatus("空闲", "idle");
  return false;
}

function schedulePoll() {
  if (state.pollTimer) return;
  state.pollTimer = window.setInterval(async () => {
    const running = await refreshStatus().catch(() => false);
    if (!running) {
      window.clearInterval(state.pollTimer);
      state.pollTimer = null;
      $("#btn-run").disabled = false;
      $("#btn-run").textContent = "生成日报";
      await loadHistory();
      await loadReport();
    }
  }, 2000);
}

async function runReport() {
  const button = $("#btn-run");
  button.disabled = true;
  button.textContent = "生成中…";
  try {
    await api("/api/run", { method: "POST", body: JSON.stringify({}) });
    setStatus("已启动，等待结果…", "running");
    schedulePoll();
  } catch (error) {
    setStatus(`启动失败：${error.message}`, "error");
    button.disabled = false;
    button.textContent = "生成日报";
  }
}

/* ---------- trend analysis: 7 / 14 / 30 day ranges, latest persisted ---------- */

function setTrendRange(days) {
  state.trendDays = days;
  document.querySelectorAll(".range-btn").forEach((button) => {
    button.classList.toggle("active", Number(button.dataset.days) === days);
  });
}

function renderTrend(trend) {
  const body = $("#trend-body");
  if (trend && trend.content) {
    body.textContent = trend.content;
    if (trend.window_days) setTrendRange(Number(trend.window_days));
  } else {
    body.textContent = "暂无趋势分析；点击「重新分析」生成。";
  }
}

async function loadLatestTrend() {
  try {
    const data = await api("/api/trend/latest");
    renderTrend(data.trend);
  } catch (error) {
    renderTrend(null);
  }
}

async function runTrend(days) {
  setTrendRange(days || state.trendDays);
  const body = $("#trend-body");
  body.textContent = "正在基于历史报告分析趋势…（约 10–30 秒）";
  try {
    const data = await api("/api/trend", { method: "POST", body: JSON.stringify({ days: state.trendDays }) });
    const trend = data.trend || {};
    if (trend.status === "ok") {
      renderTrend({ ...trend, window_days: state.trendDays });
    } else if (trend.status === "no_key") {
      body.textContent = "未配置 DEEPSEEK_API_KEY，无法生成趋势分析。";
    } else {
      body.textContent = "历史报告不足，暂时无法生成趋势分析。";
    }
  } catch (error) {
    body.textContent = `趋势分析失败：${error.message}`;
  }
}

function applyTheme(theme) {
  document.getElementById("theme-link").href = `/themes/${theme}.css`;
  localStorage.setItem(THEME_KEY, theme);
}

function toggleTheme() {
  const current = localStorage.getItem(THEME_KEY) || "dark";
  applyTheme(current === "light" ? "dark" : "light");
}

async function loadSetup() {
  try {
    const data = await api("/api/setup");
    if (!(data.llm_configured ?? data.deepseek_configured)) {
      const banner = $("#setup-banner");
      banner.textContent = `首次使用：未配置 LLM API Key（默认 DeepSeek）。请编辑 ${data.keys_file} 中的 `
        + "LLM_API_KEY，保存后重启界面（也兼容 DEEPSEEK_API_KEY / OPENAI_API_KEY / .env / ds_key.txt）。";
      banner.classList.remove("hidden");
    }
  } catch (error) {
    console.warn("setup check failed", error);
  }
}

async function init() {
  applyTheme(localStorage.getItem(THEME_KEY) || "dark");
  $("#btn-run").addEventListener("click", runReport);
  $("#btn-trend").addEventListener("click", () => {
    $("#trend-panel").scrollIntoView({ behavior: "smooth", block: "start" });
    runTrend(state.trendDays);
  });
  $("#btn-theme").addEventListener("click", toggleTheme);
  $("#btn-trend-refresh").addEventListener("click", () => runTrend(state.trendDays));
  document.querySelectorAll(".range-btn").forEach((button) => {
    button.addEventListener("click", () => runTrend(Number(button.dataset.days)));
  });
  await loadSetup();
  await loadHistory();
  await refreshStatus();
  await loadReport();
  await loadLatestTrend();
}

document.addEventListener("DOMContentLoaded", init);
