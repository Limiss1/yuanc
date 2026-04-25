const state = {
  overview: null,
  selectedReport: null,
  selectedJobId: null,
  jobPoller: null,
  tradingPoller: null,
};

const qs = (selector) => document.querySelector(selector);

function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return `${Number(value).toFixed(2)}%`;
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return Number(value).toFixed(digits);
}

function formatDate(value) {
  if (!value) return "--";
  const date = new Date(value);
  return date.toLocaleString("zh-CN", { hour12: false });
}

function reportTitle(report) {
  return report?.payload?.symbol || report?.name || "未命名报告";
}

function drawPerformanceCanvas(backtests = []) {
  const canvas = qs("#performanceCanvas");
  const ctx = canvas.getContext("2d");
  const { width, height } = canvas;

  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = "rgba(255,255,255,0.08)";
  ctx.lineWidth = 1;

  for (let i = 1; i < 5; i += 1) {
    const y = (height / 5) * i;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  const series = backtests
    .slice()
    .reverse()
    .map((item) => Number(item.payload?.total_return_pct || 0));

  if (!series.length) {
    ctx.fillStyle = "rgba(137,160,179,0.8)";
    ctx.font = "14px Inter";
    ctx.fillText("等待回测报告...", 24, 36);
    return;
  }

  const min = Math.min(...series, 0);
  const max = Math.max(...series, 0);
  const span = Math.max(max - min, 0.1);

  ctx.beginPath();
  series.forEach((value, index) => {
    const x = 20 + (index * (width - 40)) / Math.max(series.length - 1, 1);
    const y = height - 22 - ((value - min) / span) * (height - 44);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });

  ctx.strokeStyle = "#52b3ff";
  ctx.lineWidth = 3;
  ctx.stroke();

  ctx.lineTo(width - 20, height - 22);
  ctx.lineTo(20, height - 22);
  ctx.closePath();
  ctx.fillStyle = "rgba(82,179,255,0.14)";
  ctx.fill();

  ctx.fillStyle = "#e7eff7";
  ctx.font = "12px Inter";
  ctx.fillText(`Recent returns (${series.length})`, 22, 20);
}

function renderMetricTiles(overview) {
  const training = overview.latest_training;
  const backtest = overview.latest_backtest;

  qs("#latestAccuracy").textContent = training ? formatPercent(training.metrics?.accuracy * 100) : "--";
  qs("#latestTrainMeta").textContent = training
    ? `${training.symbol} · ${training.period} · ${training.feature_count} features`
    : "等待训练报告";

  qs("#latestReturn").textContent = backtest ? formatPercent(backtest.total_return_pct) : "--";
  qs("#latestBacktestMeta").textContent = backtest
    ? `${backtest.symbol} · ${backtest.trade_count} trades`
    : "等待回测报告";

  qs("#latestDrawdown").textContent = backtest ? formatPercent(backtest.max_drawdown_pct) : "--";
  qs("#latestRiskMeta").textContent = backtest
    ? `Win rate ${formatPercent(backtest.win_rate * 100)}`
    : "风险尚未计算";

  qs("#latestTrades").textContent = backtest ? String(backtest.trade_count) : "--";
  qs("#latestTradeMeta").textContent = backtest
    ? `${backtest.win_count} wins / ${backtest.loss_count} losses`
    : "尚无交易明细";
}

function makeReportItem(report, kind) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "report-item";
  button.innerHTML = `
    <h4>${reportTitle(report)}</h4>
    <div class="report-meta">
      <span>${kind === "training" ? "Training" : "Backtest"}</span>
      <span>${formatDate(report.updated_at)}</span>
    </div>
  `;
  button.addEventListener("click", () => selectReport(kind, report.name, button));
  return button;
}

function renderReportLists(overview) {
  const trainingList = qs("#trainingList");
  const backtestList = qs("#backtestList");
  trainingList.innerHTML = "";
  backtestList.innerHTML = "";

  qs("#trainingCount").textContent = overview.training_reports.length;
  qs("#backtestCount").textContent = overview.backtest_reports.length;

  overview.training_reports.forEach((report) => trainingList.appendChild(makeReportItem(report, "training")));
  overview.backtest_reports.forEach((report) => backtestList.appendChild(makeReportItem(report, "backtest")));
}

function buildDetailStats(payload, kind) {
  if (!payload) return [];
  if (kind === "training") {
    return [
      { label: "Accuracy", value: formatPercent((payload.metrics?.accuracy || 0) * 100) },
      { label: "F1", value: formatPercent((payload.metrics?.f1 || 0) * 100) },
      { label: "Train Size", value: payload.metrics?.train_size ?? "--" },
      { label: "Features", value: payload.feature_count ?? "--" },
    ];
  }
  return [
    { label: "Return", value: formatPercent(payload.total_return_pct) },
    { label: "Drawdown", value: formatPercent(payload.max_drawdown_pct) },
    { label: "Trades", value: payload.trade_count ?? "--" },
    { label: "Win Rate", value: formatPercent((payload.win_rate || 0) * 100) },
  ];
}

function renderDetailStats(stats) {
  const container = qs("#detailStats");
  container.innerHTML = "";
  stats.forEach((item) => {
    const article = document.createElement("article");
    article.className = "detail-stat";
    article.innerHTML = `<label>${item.label}</label><strong>${item.value}</strong>`;
    container.appendChild(article);
  });
}

function renderTrades(trades) {
  const container = qs("#tradeTable");
  if (!trades?.length) {
    container.className = "trade-table empty";
    container.textContent = "暂无逐笔成交";
    return;
  }

  const columns = ["timestamp", "side", "position_side", "amount", "price", "margin", "leverage"];
  const head = columns.map((item) => `<th>${item}</th>`).join("");
  const rows = trades
    .slice(-40)
    .reverse()
    .map(
      (row) => `
        <tr>
          ${columns.map((column) => `<td>${row[column] ?? ""}</td>`).join("")}
        </tr>
      `
    )
    .join("");

  container.className = "trade-table";
  container.innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table>`;
}

async function selectReport(kind, name, sourceButton) {
  document.querySelectorAll(".report-item").forEach((item) => item.classList.remove("active"));
  if (sourceButton) sourceButton.classList.add("active");

  const response = await fetch(`/api/reports/${kind}/${name}`);
  const report = await response.json();
  state.selectedReport = report;

  qs("#detailSubtitle").textContent = `${kind === "training" ? "训练" : "回测"}报告 · ${name}`;
  renderDetailStats(buildDetailStats(report.payload, kind));
  qs("#detailJson").textContent = JSON.stringify(report.payload, null, 2);
  renderTrades(report.trades);
}

function makeJobItem(job) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "job-item";
  if (job.id === state.selectedJobId) button.classList.add("active");
  button.innerHTML = `
    <h4>${job.action.toUpperCase()} · ${job.params.symbol || "--"}</h4>
    <div class="job-meta">
      <span class="status-pill ${job.status}">${job.status}</span>
      <span>${formatDate(job.updated_at)}</span>
    </div>
  `;
  button.addEventListener("click", () => {
    state.selectedJobId = job.id;
    renderJobs(state.lastJobs || []);
    renderJobLog(job);
  });
  return button;
}

function renderJobLog(job) {
  const log = qs("#jobLog");
  if (!job) {
    log.textContent = "等待任务…";
    return;
  }
  const parts = [
    `# ${job.action.toUpperCase()} (${job.status})`,
    "",
    ...(job.logs || []),
  ];
  if (job.error) {
    parts.push("", `ERROR: ${job.error}`);
  }
  log.textContent = parts.join("\n");
}

function renderJobs(jobs) {
  state.lastJobs = jobs;
  const list = qs("#jobList");
  list.innerHTML = "";
  jobs.forEach((job) => list.appendChild(makeJobItem(job)));

  if (!state.selectedJobId && jobs[0]) {
    state.selectedJobId = jobs[0].id;
  }
  renderJobLog(jobs.find((job) => job.id === state.selectedJobId) || jobs[0]);
}

async function loadJobs() {
  const response = await fetch("/api/jobs");
  const payload = await response.json();
  renderJobs(payload.jobs || []);
}

function renderTradingStatus(payload) {
  qs("#tradingRunningState").textContent = payload.running ? "RUNNING" : "STOPPED";
  const pill = qs("#tradingModePill");
  pill.textContent = payload.mode || "paper";
  pill.className = `status-pill ${payload.running ? "running" : "queued"}`;
  qs("#tradingEquity").textContent = formatNumber(payload.portfolio?.equity);
  qs("#tradingPnl").textContent = formatNumber(payload.portfolio?.total_pnl);
  qs("#tradingTradeCount").textContent = payload.trade_count ?? "--";
  qs("#tradingWinRate").textContent = formatPercent((payload.win_rate || 0) * 100);

  const lines = [
    `Symbol: ${payload.symbol || "--"}`,
    `Mode: ${payload.mode || "--"}`,
    `Started: ${payload.started_at ? formatDate(payload.started_at) : "--"}`,
    "",
    ...((payload.logs || []).slice(-80)),
  ];
  qs("#tradingLog").textContent = lines.join("\n");
}

async function loadTradingStatus() {
  const response = await fetch("/api/trading/status");
  const payload = await response.json();
  renderTradingStatus(payload);
}

async function submitTradingForm(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = {
    mode: form.get("tradeMode"),
    symbol: form.get("tradeSymbol"),
    balance: Number(form.get("tradeBalance") || 10000),
    leverage: Number(form.get("tradeLeverage") || 10),
    confidence: Number(form.get("tradeConfidence") || 0.6),
    interval: Number(form.get("tradeInterval") || 60),
    stop_loss_pct: Number(form.get("tradeSl") || 0.0015),
    take_profit_pct: Number(form.get("tradeTp") || 0.003),
    confirm_live: qs("#confirmLive").checked,
  };

  const response = await fetch("/api/trading/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok) {
    qs("#tradingLog").textContent = `启动失败: ${result.error || "unknown error"}`;
    return;
  }
  renderTradingStatus(result);
}

async function stopTrading() {
  const response = await fetch("/api/trading/stop", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  const result = await response.json();
  renderTradingStatus(result);
}

async function loadOverview() {
  const response = await fetch("/api/overview");
  const overview = await response.json();
  state.overview = overview;

  qs("#refreshStamp").textContent = formatDate(overview.generated_at);
  renderMetricTiles(overview);
  renderReportLists(overview);
  drawPerformanceCanvas(overview.backtest_reports || []);
}

async function submitRunForm(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());
  payload.days = Number(payload.days || 1);

  const response = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  state.selectedJobId = data.job_id;
  await loadJobs();

  if (state.jobPoller) clearInterval(state.jobPoller);
  state.jobPoller = setInterval(async () => {
    await loadJobs();
    const current = (state.lastJobs || []).find((job) => job.id === state.selectedJobId);
    if (current && ["completed", "failed"].includes(current.status)) {
      clearInterval(state.jobPoller);
      state.jobPoller = null;
      await loadOverview();
    }
  }, 2000);
}

async function init() {
  qs("#runForm").addEventListener("submit", submitRunForm);
  qs("#tradingForm").addEventListener("submit", submitTradingForm);
  qs("#stopTradingButton").addEventListener("click", stopTrading);
  qs("#refreshButton").addEventListener("click", async () => {
    await loadOverview();
    await loadJobs();
    await loadTradingStatus();
  });

  await loadOverview();
  await loadJobs();
  await loadTradingStatus();
  state.tradingPoller = setInterval(loadTradingStatus, 3000);
}

init();
