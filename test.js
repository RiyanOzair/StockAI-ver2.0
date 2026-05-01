
/* ═══════════════════════════════════════════
  GLOBALS
═══════════════════════════════════════════ */
const API = window.location.origin;
let ws = null;
let wsConnected = false;
let pollTimer = null;
let _wsRetryCount = 0;
let _wsRetryTimer = null;
let _wsConnectTimer = null;  // timeout for stuck CONNECTING state
let state = { is_running: false, is_paused: false, day: 0, session: 0, total_days: 30, total_trades: 0, active_agents: 0 };
let configuredDays = 30; // ceiling: total days for this run, reset only on simReset
let allStocks = {};      // sym → stock meta+price
let stockHistory = {};   // sym → price array
let agents = [];
let halted = [];
let chartInstances = {};
let marketAnalytics = null;
let agentAnalyticsCache = {};
let selectedAgent = null;
let snapshotList = [];
let activeReportTab = null;
let visibleStocks = new Set(['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL']); // default: research core
let selectedForCompare = new Set(); // agent IDs selected for comparison
let priceAlerts = [];               // { sym, dir, target, id }
let runEvents = [];
let lastRunEventSeq = 0;
let activeRunId = null;

/* ═══════════════════════════════════════════
   NAVIGATION
═══════════════════════════════════════════ */
function nav(page) {
  const pageEl = document.getElementById('page-' + page);
  const navEl  = document.querySelector(`[data-page="${page}"]`);
  if (!pageEl || !navEl) return; // ignore unknown hashes
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  pageEl.classList.add('active');
  navEl.classList.add('active');
  window.location.hash = page;

  if (page === 'dashboard')      { refreshPriceChart(); }
  if (page === 'analysis')       { loadAnalysis(); }
  if (page === 'agents' && agents.length) { setTimeout(loadRaceChart, 300); }
  if (page === 'agents')         { loadAgents(); loadLoans(); }
  if (page === 'explainability') { loadExplainabilityPage(); }
  if (page === 'replay')         { loadReplayPage(); }
}

window.addEventListener('hashchange', () => {
  const p = location.hash.replace('#', '') || 'dashboard';
  if (document.getElementById('page-' + p)) nav(p);
});
if (location.hash) nav(location.hash.replace('#', ''));

/* ═══════════════════════════════════════════
   TOAST
═══════════════════════════════════════════ */
function toast(msg, color = 'var(--lime)') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.borderColor = color;
  t.style.boxShadow = `4px 4px 0 ${color}`;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

/* ═══════════════════════════════════════════
   API HELPERS
═══════════════════════════════════════════ */
const sessionID = sessionStorage.getItem('stockai_session_id') || (Date.now() + '-' + Math.random().toString(36).slice(2, 11));
sessionStorage.setItem('stockai_session_id', sessionID);

async function apiFetch(path, opts = {}) {
  try {
    opts.headers = opts.headers || {};
    opts.headers['X-Session-ID'] = sessionID;
    const r = await fetch(API + path, opts);
    if (!r.ok) throw new Error(await r.text());
    return await r.json();
  } catch (e) {
    console.warn('API error', path, e.message);
    if (e.message.includes('Simulation session lock active')) {
      toast('CONFLICT: Another research session is controlling the simulation.', 'var(--red)');
    }
    return null;
  }
}

async function apiPost(path, body = {}) {
  return apiFetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
}

/* ═══════════════════════════════════════════
   WEBSOCKET
═══════════════════════════════════════════ */
function connectWS() {
  clearTimeout(_wsRetryTimer);
  clearTimeout(_wsConnectTimer);

  // If already open, nothing to do
  if (ws && ws.readyState === WebSocket.OPEN) return;

  // If stuck connecting, force-close before making a new socket
  if (ws && ws.readyState === WebSocket.CONNECTING) {
    try { ws.close(); } catch (_) {}
  } else if (ws) {
    try { ws.close(); } catch (_) {}
  }

  // Show yellow 'connecting' state
  const dot = document.getElementById('ws-dot');
  const lbl = document.getElementById('ws-label');
  if (dot) dot.className = 'connecting';
  if (lbl) lbl.textContent = 'Connecting…';

  try {
    const wsProto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${wsProto}//${location.host}/ws`);
  } catch (e) {
    console.warn('WebSocket not available, using polling', e);
    wsConnected = false; setWsDot(false, false); startPoll();
    return;
  }

  // Kill the socket if it hasn't connected within 5 seconds
  _wsConnectTimer = setTimeout(() => {
    if (ws && ws.readyState === WebSocket.CONNECTING) {
      try { ws.close(); } catch(_) {}
      wsConnected = false; setWsDot(false, false); startPoll();
    }
  }, 5000);

  ws.onopen = () => {
    clearTimeout(_wsConnectTimer);
    wsConnected = true;
    _wsRetryCount = 0;
    setWsDot(true);
    clearInterval(pollTimer);
  };

  ws.onmessage = (e) => {
    try {
      const d = JSON.parse(e.data);
      if (d.type === 'tick')     handleTick(d);
      if (d.type === 'complete') handleComplete(d);
    } catch (_) {}
  };

  ws.onerror = () => { clearTimeout(_wsConnectTimer); wsConnected = false; setWsDot(false, true);  startPoll(); _scheduleWsRetry(); };
  ws.onclose = () => { clearTimeout(_wsConnectTimer); wsConnected = false; setWsDot(false, false); startPoll(); _scheduleWsRetry(); };
}

function _scheduleWsRetry() {
  clearTimeout(_wsRetryTimer);
  const delay = Math.min(2000 * Math.pow(2, _wsRetryCount), 30000); // 2s→4s→8s→…→30s
  _wsRetryCount++;
  _wsRetryTimer = setTimeout(() => { if (!wsConnected) connectWS(); }, delay);
}

function setWsDot(ok, err = false) {
  const d1 = document.getElementById('ws-dot');
  const d2 = document.getElementById('ws-dot2');
  const lbl = document.getElementById('ws-label');
  const sl  = document.getElementById('ws-status-label');
  const cls = ok ? 'connected' : (err ? 'error' : '');
  if (d1) d1.className = cls;
  if (d2) d2.style.background = ok ? 'var(--lime)' : (err ? 'var(--red)' : 'var(--muted)');
  const txt = ok ? 'Live' : (err ? 'Error' : 'Disconnected');
  if (lbl) lbl.textContent = txt;
  if (sl)  sl.textContent  = ok ? 'Connected ✓' : txt;
}

function startPoll() {
  clearInterval(pollTimer);
  pollTimer = setInterval(pollStatus, 2000);
}

async function pollStatus() {
  const s = await apiFetch('/simulation/status');
  if (s) handleStatus(s);
  if (s && s.run_id) loadRunEvents();
  const t = await apiFetch('/market/trades');
  if (t) renderTrades(t.slice(-20).reverse());
}

function reconnectWS() { connectWS(); toast('Reconnecting WebSocket…', 'var(--cyan)'); }

function handleTick(d) {
  // Update sidebar
  state = { ...state, ...d, total_trades: d.trades, active_agents: d.agents };
  halted = d.halted || [];
  if (d.regime) {
    marketAnalytics = marketAnalytics || {};
    marketAnalytics.regime = d.regime;
  }
  if (d.benchmark) {
    marketAnalytics = marketAnalytics || {};
    marketAnalytics.benchmark = { ...(marketAnalytics.benchmark || {}), ...d.benchmark };
  }
  updateSidebar();
  updateMetrics();
  if (d.run_id) loadRunEvents();

  // Debug: log tick data
  console.log('[handleTick] d:', d);

  // Update stock prices from tick
  if (d.prices) {
    for (const sym of Object.keys(d.prices)) {
      if (allStocks[sym]) allStocks[sym].price = d.prices[sym];
    }
    pushPriceHistory(d.prices, d.day, d.session);
    // Debug: log stockHistory after push
    console.log('[handleTick] stockHistory:', JSON.parse(JSON.stringify(stockHistory)));
    refreshPriceChart();
  }

  // Halted banner
  renderHaltedBanner(d.halted || []);

  // Events
  if (d.events && d.events.length) {
    const feed = document.getElementById('events-feed');
    d.events.forEach(ev => {
      const el = document.createElement('div');
      el.className = 'feed-item';
      el.innerHTML = `<div class="feed-item-header">
        <span class="badge sev-${ev.severity||'low'}">${ev.severity||'?'}</span>
        <span class="feed-item-name">${escHtml(ev.title||'')}</span>
        <span class="feed-item-day">Day ${d.day}</span>
      </div>`;
      feed.prepend(el);
      if (feed.children.length > 30) feed.removeChild(feed.lastChild);
    });
  }
}

function pushPriceHistory(prices, day, session) {
  const key = `${day}.${session}`;
  for (const [sym, price] of Object.entries(prices)) {
    if (!stockHistory[sym]) stockHistory[sym] = [];
    stockHistory[sym].push({ label: key, price });
    if (stockHistory[sym].length > 500) stockHistory[sym].shift();
  }
}

/* ═══════════════════════════════════════════
   STATUS + SIDEBAR
═══════════════════════════════════════════ */
function handleStatus(s) {
  if (s.run_id && s.run_id !== activeRunId) {
    activeRunId = s.run_id;
    runEvents = [];
    lastRunEventSeq = 0;
  }
  state = { ...state, ...s };
  marketAnalytics = s.market_analytics || marketAnalytics;

  // FEATURE 1: Mock-Mode Banner
  let mb = document.getElementById('mockBanner');
  if (!mb) {
    mb = document.createElement('div');
    mb.id = 'mockBanner';
    mb.style.cssText = 'display:none;position:fixed;top:0;left:0;right:0;background:var(--red,#f87171);color:#000;text-align:center;padding:8px;font:700 12px var(--mono);z-index:10000;border-bottom:2px solid #000;';
    mb.textContent = '⚠️ LLM MODE: MOCK (API KEYS MISSING) — RESEARCH RESULTS WILL REFLECT HARDCODED DEMO LOGIC ⚠️';
    document.body.prepend(mb);
  }
  mb.style.display = (state.llm_mode === 'mock') ? 'block' : 'none';

  updateSidebar();
  updateMetrics();
  renderRunContext();
}

function updateSidebar() {
  const badge = document.getElementById('sb-status');
  let cls = 'idle', txt = 'Idle';
  if (state.is_running && !state.is_paused) { cls = 'running'; txt = 'Running'; }
  else if (state.is_paused) { cls = 'paused'; txt = 'Paused'; }
  else if (!state.is_running && state.day > 0) { cls = 'stopped'; txt = 'Stopped'; }
  badge.className = 'status-badge ' + cls;
  badge.textContent = txt;

  document.getElementById('sb-day').textContent = state.day ? `DAY ${state.day}` : 'DAY —';
  const sess = state.session !== undefined ? `Session ${state.session}` : '—';
  document.getElementById('sb-session').textContent = sess;
  document.getElementById('sb-phase').textContent = state.session_phase ? String(state.session_phase).replace(/_/g, ' ') : '—';
  document.getElementById('sb-run').textContent = state.run_id ? String(state.run_id).slice(-12) : '—';
  document.getElementById('sb-trades').textContent = state.total_trades || 0;

  const pct = configuredDays ? (state.day / configuredDays * 100) : 0;
  document.getElementById('sb-progress').style.width = pct + '%';

  // Control button states
  document.getElementById('btn-start').classList.toggle('active', state.is_running && !state.is_paused);
  document.getElementById('btn-pause').classList.toggle('active', state.is_paused);
}

function updateMetrics() {
  document.getElementById('m-day').textContent = state.day || '—';
  document.getElementById('m-totaldays').textContent = `of ${configuredDays}`;
  document.getElementById('m-trades').textContent = state.total_trades || 0;
  document.getElementById('m-agents').textContent = state.active_agents || 0;
  document.getElementById('m-halted').textContent = halted.length;
  document.getElementById('m-events').textContent = snapshotList.length || 0;

  if (agents.length) {
    const best = [...agents].sort((a, b) => b.pnl - a.pnl)[0];
    document.getElementById('m-bestpnl').textContent = best ? fmtPct(best.pnl_pct) : '—';
    document.getElementById('m-bestagent').textContent = best ? best.name : '—';
  }

  if (!marketAnalytics) return;
  const benchmark = marketAnalytics.benchmark || {};
  const breadth = marketAnalytics.breadth || {};
  document.getElementById('m-regime').textContent = (marketAnalytics.regime || '—').replace(/_/g, ' ').toUpperCase();
  document.getElementById('m-regime-headline').textContent = marketAnalytics.scenario || '—';
  document.getElementById('m-benchmark').textContent = benchmark.level != null ? benchmark.level.toFixed(2) : '—';
  document.getElementById('m-benchmark-ret').textContent = benchmark.return_pct != null ? `${benchmark.return_pct >= 0 ? '+' : ''}${benchmark.return_pct.toFixed(2)}% vs base` : 'vs base 100';
  document.getElementById('m-breadth').textContent = breadth.breadth_ratio != null ? `${(breadth.breadth_ratio * 100).toFixed(0)}%` : '—';
  document.getElementById('m-breadth-sub').textContent = `${breadth.advancers || 0} up / ${breadth.decliners || 0} down`;
  document.getElementById('m-realized-vol').textContent = marketAnalytics.realized_vol_pct != null ? `${marketAnalytics.realized_vol_pct.toFixed(1)}%` : '—';
  document.getElementById('m-session-risk').textContent = marketAnalytics.session_risk || 'session risk';
  document.getElementById('m-drawdown').textContent = benchmark.drawdown_pct != null ? `${benchmark.drawdown_pct.toFixed(2)}%` : '—';
  document.getElementById('m-turnover').textContent = marketAnalytics.turnover != null ? `${(marketAnalytics.turnover * 100).toFixed(1)}%` : '—';
  document.getElementById('m-sentiment').textContent = marketAnalytics.market_sentiment || 'market sentiment';
  renderRunContext();
}

function renderRunContext() {
  const panel = document.getElementById('run-context-panel');
  if (!panel) return;
  panel.innerHTML = `
    <div><span style="color:var(--muted)">Run ID:</span> <strong style="color:var(--cyan)">${escHtml(state.run_id || '—')}</strong></div>
    <div><span style="color:var(--muted)">Phase:</span> ${escHtml((state.session_phase || '—').replace(/_/g, ' '))}</div>
    <div><span style="color:var(--muted)">Dataset:</span> ${escHtml(state.dataset_version || '—')}</div>
    <div><span style="color:var(--muted)">Scenario:</span> ${escHtml(state.scenario_id || '—')}</div>
    <div><span style="color:var(--muted)">Training:</span> ${escHtml((state.training_mode || 'hybrid').toUpperCase())}</div>
    <div><span style="color:var(--muted)">Liquidity:</span> ${escHtml(state.liquidity_model || '—')} / ${escHtml(state.liquidity_regime || '—')}</div>
    <div><span style="color:var(--muted)">Execution:</span> ${state.latency_ms != null ? `${state.latency_ms}ms` : '—'} latency / ${state.slippage_bps != null ? Number(state.slippage_bps).toFixed(2) : '—'}bps</div>
    <div><span style="color:var(--muted)">Regime Link:</span> ${escHtml(marketAnalytics?.scenario || 'Waiting for scenario analytics…')}</div>`;
}

function renderRunEvents() {
  const feed = document.getElementById('run-events-feed');
  if (!feed) return;
  if (!runEvents.length) {
    feed.innerHTML = '<div class="empty">Run-scoped execution events will appear here.</div>';
    return;
  }
  feed.innerHTML = [...runEvents].slice(-18).reverse().map(evt => {
    const payload = evt.payload || {};
    const headline = payload.title || payload.symbol || payload.order_id || payload.trade_id || evt.event_type;
    const meta = payload.price != null ? ` @ ${fmtMoney(payload.price)}` : (payload.move_pct != null ? ` · ${payload.move_pct}%` : '');
    return `<div class="feed-item">
      <div class="feed-item-header">
        <span class="badge sev-${(payload.severity || evt.event_type || 'low').toLowerCase().replace(/[^a-z]/g,'') || 'low'}">${escHtml((evt.event_type || 'event').replace(/_/g,' '))}</span>
        <span class="feed-item-name">${escHtml(headline)}</span>
        <span class="feed-item-day">#${evt.sequence}</span>
      </div>
      <div style="font-size:11px;color:var(--muted);margin-top:6px">${escHtml((evt.phase || 'phase').replace(/_/g,' '))}${escHtml(meta)}</div>
    </div>`;
  }).join('');
}

async function loadRunEvents() {
  if (!state.run_id) return;
  const rows = await apiFetch(`/runs/${state.run_id}/events?after_sequence=${lastRunEventSeq}`);
  if (!rows || !rows.length) {
    renderRunEvents();
    return;
  }
  rows.forEach(evt => {
    runEvents.push(evt);
    lastRunEventSeq = Math.max(lastRunEventSeq, evt.sequence || 0);
  });
  if (runEvents.length > 120) runEvents = runEvents.slice(-120);
  renderRunEvents();
}

/* ═══════════════════════════════════════════
   SIMULATION CONTROLS
═══════════════════════════════════════════ */
async function simStart() {
  // If paused, resume via backend (pause state is reliable)
  if (state.is_paused) {
    const r = await apiPost('/simulation/start');
    if (r) { toast('Resumed', 'var(--lime)'); pollStatus(); }
    return;
  }
  // Always delegate to simRunDays — it fetches authoritative backend state,
  // stops any in-progress run, extends by 1, and starts.
  // Never block on stale client-side is_running (WS may lag on Render).
  await simRunDays(1);
}
async function simPause() {
  const r = await apiPost('/simulation/pause');
  if (r) { toast(r.status === 'paused' ? 'Paused' : 'Resumed'); pollStatus(); }
}
async function simStop() {
  const r = await apiPost('/simulation/stop');
  if (r) { toast('Simulation stopped', 'var(--yellow)'); pollStatus(); }
}
async function simRunDays(n) {
  // Always get authoritative state from backend FIRST
  const live = await apiFetch('/simulation/status');
  if (live) handleStatus(live);
  const currentDay = live ? live.day : state.day;

  // Stop any running simulation — then wait briefly so the old background
  // task can detect is_running=False and exit before we start a new one.
  if ((live && live.is_running) || state.is_running) {
    await apiPost('/simulation/stop');
    await new Promise(r => setTimeout(r, 300));
  }

  if (currentDay >= configuredDays) {
    toast(`✓ All ${configuredDays} days complete — reset to run again`, 'var(--cyan)');
    return;
  }

  // Clamp to the configured ceiling so display never exceeds it
  const daysToRun = Math.min(n, configuredDays - currentDay);
  const ext = await apiPost('/simulation/extend', { additional_days: daysToRun });
  if (!ext) { toast('Extend failed', 'var(--red)'); return; }

  const targetDay = currentDay + daysToRun;
  const s = await apiPost('/simulation/start');
  if (s) toast(`▶ Day ${currentDay + 1}–${targetDay} of ${configuredDays}`, 'var(--lime)');
  else toast('Start failed', 'var(--red)');
  pollStatus();

  // Active polling: keep updating until the backend says the sim finished.
  // Works even if WebSocket is disconnected or Render drops the WS.
  _awaitSimCompletion(targetDay);
}

// Poll the backend until the sim stops running, updating the UI each time.
let _simPollTimer = null;
function _awaitSimCompletion(targetDay) {
  clearInterval(_simPollTimer);
  _simPollTimer = setInterval(async () => {
    const s = await apiFetch('/simulation/status');
    if (!s) return;                   // transient fetch error
    handleStatus(s);
    if (!s.is_running) {
      clearInterval(_simPollTimer);
      _simPollTimer = null;
      handleComplete({ day: s.day, total_days: s.total_days });
    }
  }, 1500);
}

function handleComplete(d) {
  state.is_running = false;
  state.day = d.day;
  state.total_days = d.total_days;
  // Don't override configuredDays — it's our ceiling, set only on reset
  updateSidebar();
  updateMetrics();
  const remaining = configuredDays - d.day;
  if (remaining <= 0) {
    toast(`✓ All ${configuredDays} days complete!`, 'var(--cyan)');
  } else {
    toast(`✓ Day ${d.day} done (${remaining} remaining)`, 'var(--cyan)');
  }
}

async function simReset() {
  if (!confirm('Reset simulation? All progress will be lost.')) return;
  const r = await apiPost('/simulation/reset');
  if (r) {
    toast('Reset complete', 'var(--cyan)');
    configuredDays = 30; // restore ceiling
    stockHistory = {}; allStocks = {}; agents = []; halted = [];
    state = { is_running: false, is_paused: false, day: 0, session: 0, total_days: 0, total_trades: 0, active_agents: 0 };
    updateSidebar(); updateMetrics();
    clearChart('priceChart'); clearChart('sectorChart'); clearChart('stockChart');
    clearChart('biasChart'); clearChart('actionChart'); clearChart('raceChart');
    document.getElementById('trade-feed').innerHTML = '';
    document.getElementById('events-feed').innerHTML = '';
    document.getElementById('forum-feed').innerHTML = '';
    pollStatus();
  }
}

/* ═══════════════════════════════════════════
   MARKET DATA
═══════════════════════════════════════════ */
async function loadMarketStocks() {
  const data = await apiFetch('/market/stocks');
  if (!data) return;
  allStocks = data;
  buildStockToggles();
  buildStockSelect();
  buildExplAgentSelect();
  loadPriceHistories();
}

async function loadPriceHistories() {
  for (const sym of [...visibleStocks]) {
    const h = await apiFetch(`/market/history/${sym}`);
    if (h && h.history && h.history.length > 0) {
      stockHistory[sym] = h.history.map(p => ({ label: `${p.day}.${p.session}`, price: p.price }));
    } else {
      // Seed a flat starting point so the chart scale is correct even before simulation runs
      const initPrice = allStocks[sym]?.price || allStocks[sym]?.initial_price || 100;
      stockHistory[sym] = [{ label: '0.0', price: initPrice }];
    }
  }
  refreshPriceChart();
}

function buildStockToggles() {
  const container = document.getElementById('stock-toggles');
  container.innerHTML = '';
  Object.entries(allStocks).forEach(([sym, s]) => {
    const btn = document.createElement('button');
    btn.className = 'stock-toggle' + (visibleStocks.has(sym) ? ' on' : '');
    btn.textContent = `${s.emoji || ''} ${s.name}`;
    btn.title = `${sym} — ${s.name}`;
    btn.onclick = () => toggleStockVis(sym, btn);
    container.appendChild(btn);
  });
}

function toggleStockVis(sym, btn) {
  if (visibleStocks.has(sym)) {
    visibleStocks.delete(sym);
    btn.classList.remove('on');
  } else {
    if (visibleStocks.size >= 8) { toast('Max 8 stocks visible', 'var(--yellow)'); return; }
    visibleStocks.add(sym);
    btn.classList.add('on');
    if (!stockHistory[sym]) {
      apiFetch(`/market/history/${sym}`).then(h => {
        if (h && h.history && h.history.length > 0) {
          stockHistory[sym] = h.history.map(p => ({ label: `${p.day}.${p.session}`, price: p.price }));
        } else {
          const initPrice = allStocks[sym]?.price || allStocks[sym]?.initial_price || 100;
          stockHistory[sym] = [{ label: '0.0', price: initPrice }];
        }
        refreshPriceChart();
      });
    }
  }
  refreshPriceChart();
}

function buildStockSelect() {
  const sel = document.getElementById('stock-select');
  sel.innerHTML = '<option value="">Select Stock…</option>';
  const alertSel = document.getElementById('alert-sym');
  if (alertSel) alertSel.innerHTML = '<option value="">Stock…</option>';
  Object.entries(allStocks).forEach(([sym, s]) => {
    sel.innerHTML += `<option value="${sym}">${s.emoji || ''} ${sym} — ${escHtml(s.name)}</option>`;
    if (alertSel) alertSel.innerHTML += `<option value="${sym}">${s.emoji || ''} ${escHtml(s.name)}</option>`;
  });
}

/* ═══════════════════════════════════════════
   PRICE CHART (Dashboard)
═══════════════════════════════════════════ */
const STOCK_COLORS = [
  '#4ade80','#e879a0','#38bdf8','#fbbf24','#f97316',
  '#c0f0ff','#f0c0ff','#f87171','#99ffcc','#ffcc99'
];

function refreshPriceChart() {
  const labels = new Set();
  visibleStocks.forEach(sym => {
    (stockHistory[sym] || []).forEach(p => labels.add(p.label));
  });
  const sortedLabels = [...labels].sort((a, b) => {
    const [da, sa] = a.split('.').map(Number);
    const [db, sb] = b.split('.').map(Number);
    return da !== db ? da - db : sa - sb;
  });

  const datasets = [];
  let ci = 0;
  visibleStocks.forEach(sym => {
    const hist = stockHistory[sym] || [];
    const map = new Map(hist.map(p => [p.label, p.price]));
    datasets.push({
      label: `${allStocks[sym]?.emoji || ''} ${sym}`,
      data: sortedLabels.map(l => map.get(l) ?? null),
      borderColor: STOCK_COLORS[ci % STOCK_COLORS.length],
      backgroundColor: 'transparent',
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.3,
      spanGaps: true,
    });
    ci++;
  });

  // Debug: log chart data
  console.log('[refreshPriceChart] sortedLabels:', sortedLabels);
  console.log('[refreshPriceChart] datasets:', datasets);

  if (chartInstances.priceChart) {
    chartInstances.priceChart.data.labels = sortedLabels;
    chartInstances.priceChart.data.datasets = datasets;
    chartInstances.priceChart.update('none');
    return;
  }

  const ctx = document.getElementById('priceChart').getContext('2d');
  chartInstances.priceChart = new Chart(ctx, {
    type: 'line',
    data: { labels: sortedLabels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { labels: { color: '#aaa', font: { family: 'JetBrains Mono', size: 10 }, boxWidth: 12 } } },
      scales: {
        x: { ticks: { color: '#555', maxTicksLimit: 8, font: { family: 'JetBrains Mono', size: 9 } }, grid: { color: '#1a1a1a' } },
        y: { ticks: { color: '#aaa', font: { family: 'JetBrains Mono', size: 10 }, callback: v => '$' + v.toFixed(0) }, grid: { color: '#1a1a1a' }, grace: '5%' }
      }
    }
  });
}

/* ═══════════════════════════════════════════
   TRADES FEED (Dashboard)
═══════════════════════════════════════════ */
async function loadTrades() {
  const data = await apiFetch('/market/trades');
  if (data) renderTrades(data.slice(-20).reverse());
}

function renderTrades(trades) {
  const feed = document.getElementById('trade-feed');
  feed.innerHTML = '';
  if (!trades.length) { feed.innerHTML = '<div class="empty">No trades yet.</div>'; return; }
  trades.forEach(t => {
    const el = document.createElement('div');
    el.className = 'feed-item';
    const side = t.buyer !== 'MARKET' ? 'buy' : 'sell';
    el.innerHTML = `<div class="feed-item-header">
      <span class="badge ${side}">${side.toUpperCase()}</span>
      <span class="feed-item-name">${allStocks[t.stock]?.emoji || ''} ${escHtml(allStocks[t.stock]?.name || t.stock)}</span>
      <span class="feed-item-day">${fmtMoney(t.price)} × ${t.quantity}</span>
    </div>
    <div class="feed-item-sub">${escHtml(t.buyer)} → ${escHtml(t.seller)}</div>`;
    feed.appendChild(el);
  });
}

/* ═══════════════════════════════════════════
   HALTED BANNER
═══════════════════════════════════════════ */
function renderHaltedBanner(haltedList) {
  const banner = document.getElementById('halted-banner');
  if (!haltedList.length) { banner.style.display = 'none'; return; }
  banner.style.display = 'block';
  banner.innerHTML = haltedList.map(sym =>
    `<div class="halted-alert">&#9889; CIRCUIT BREAKER: <strong>${sym}</strong> (${allStocks[sym]?.name || sym}) halted — price moved >10% this session</div>`
  ).join('');
}

/* ═══════════════════════════════════════════
   EVENTS FEED (Dashboard)
═══════════════════════════════════════════ */
async function loadEvents() {
  const data = await apiFetch('/data/events');
  if (!data) return;
  document.getElementById('m-events').textContent = data.length;
  const feed = document.getElementById('events-feed');
  feed.innerHTML = '';
  if (!data.length) { feed.innerHTML = '<div class="empty">No events yet.</div>'; return; }
  [...data].reverse().slice(0, 30).forEach(ev => {
    const el = document.createElement('div');
    el.className = 'feed-item';
    
    // AI Image logic
    const hasImage = ['monetary_policy', 'earnings', 'macro', 'corporate', 'regulation'].includes(ev.type);
    const imgHtml = hasImage ? `<img src="/assets/events/${ev.type}.png" style="width:100%; height:80px; object-fit:cover; border-radius:8px; margin-bottom:10px; border:1.5px solid var(--border); opacity:0.9">` : '';

    const affStr = ev.affected_stocks && ev.affected_stocks.length
      ? ev.affected_stocks.join(', ') : 'All stocks';
    el.innerHTML = `
      ${imgHtml}
      <div class="feed-item-header">
        <span class="badge sev-${ev.severity}">${ev.severity}</span>
        <span class="feed-item-name">${escHtml(ev.title)}</span>
        <span class="feed-item-day">Day ${ev.day}</span>
      </div>
      <div class="feed-item-body">${escHtml(ev.description || '')}</div>
      <div class="feed-item-sub">Impact: ${ev.impact > 0 ? '+' : ''}${ev.impact}% | Stocks: ${escHtml(affStr)}</div>`;
    feed.appendChild(el);
  });
}

/* ═══════════════════════════════════════════
   FORUM FEED (Dashboard)
═══════════════════════════════════════════ */
async function loadForum() {
  const data = await apiFetch('/data/forum');
  if (!data) return;
  const feed = document.getElementById('forum-feed');
  feed.innerHTML = '';
  if (!data.length) { feed.innerHTML = '<div class="empty">No posts yet.</div>'; return; }
  [...data].reverse().slice(0, 30).forEach(p => {
    const el = document.createElement('div');
    el.className = 'feed-item';
    const sentCls = p.sentiment === 'bullish' ? 'buy' : p.sentiment === 'bearish' ? 'sell' : 'hold';
    el.innerHTML = `<div class="feed-item-header">
      <span class="feed-item-name">${escHtml(p.agent_name)}</span>
      <span class="badge ${sentCls}">${p.sentiment}</span>
      <span class="feed-item-day">Day ${p.day}</span>
    </div>
    <div class="feed-item-body">${escHtml(p.message)}</div>`;
    feed.appendChild(el);
  });
}

/* ═══════════════════════════════════════════
   SNAPSHOT REWIND
═══════════════════════════════════════════ */
async function loadSnapshots() {
  const data = await apiFetch('/simulation/snapshots');
  if (!data || !data.length) return;
  snapshotList = data;
  const slider = document.getElementById('snapshot-slider');
  const days = data.map(s => s.day);
  slider.min = Math.min(...days);
  slider.max = Math.max(...days);
  slider.value = Math.max(...days);
  document.getElementById('snapshot-label').textContent = `Day ${slider.value}`;
}

async function snapshotSeek(day) {
  document.getElementById('snapshot-label').textContent = `Day ${day}`;
  const data = await apiFetch(`/simulation/snapshots/${day}`);
  if (!data) return;
  const info = document.getElementById('snapshot-info');
  info.style.display = 'block';
  const cards = document.getElementById('snapshot-cards');
  const topStocks = Object.entries(data.prices || {}).slice(0, 6);
  cards.innerHTML = topStocks.map(([sym, price]) =>
    `<div class="card" style="padding:10px">
      <div class="card-title" style="margin-bottom:4px">${allStocks[sym]?.emoji || ''} ${sym}</div>
      <div style="font-family:var(--mono);font-weight:700;color:var(--cyan)">${fmtMoney(price)}</div>
    </div>`
  ).join('');
}

/* ═══════════════════════════════════════════
   ANALYSIS PAGE
═══════════════════════════════════════════ */
async function loadAnalysis() {
  await loadMarketStocks();
  await loadMarketAnalytics();
  renderStocksTable();
  renderSectorChart();
  renderBenchmarkChart();
  renderBreadthChart();
  renderScenarioPanel();
  renderHeatmap();
  buildDepthSelect();
  await loadStockChart();
  loadReports();
}

async function loadMarketAnalytics() {
  const data = await apiFetch('/market/analytics');
  if (data) marketAnalytics = data;
}

function renderBenchmarkChart() {
  if (!marketAnalytics || !marketAnalytics.benchmark) return;
  clearChart('benchmarkChart');
  const ctx = document.getElementById('benchmarkChart').getContext('2d');
  const benchmark = marketAnalytics.benchmark;
  const sectors = marketAnalytics.sectors || {};
  chartInstances.benchmarkChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Benchmark', ...Object.keys(sectors)],
      datasets: [{
        label: 'Return vs Base',
        data: [benchmark.return_pct || 0, ...Object.values(sectors).map(v => v - 100)],
        backgroundColor: ['rgba(74,222,128,0.7)', ...Object.values(sectors).map(v => v >= 100 ? 'rgba(56,189,248,0.7)' : 'rgba(248,113,113,0.7)')],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#aaa', font: { family: 'JetBrains Mono', size: 10 } }, grid: { color: '#1a1a1a' } },
        y: { ticks: { color: '#aaa', font: { family: 'JetBrains Mono', size: 10 }, callback: v => `${v.toFixed(1)}%` }, grid: { color: '#1a1a1a' } }
      }
    }
  });
}

function renderBreadthChart() {
  if (!marketAnalytics || !marketAnalytics.breadth) return;
  clearChart('breadthChart');
  const ctx = document.getElementById('breadthChart').getContext('2d');
  const breadth = marketAnalytics.breadth;
  chartInstances.breadthChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Advancers', 'Decliners'],
      datasets: [{
        data: [breadth.advancers || 0, breadth.decliners || 0],
        backgroundColor: ['rgba(74,222,128,0.78)', 'rgba(248,113,113,0.78)'],
        borderColor: '#0a0a0a',
        borderWidth: 2
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#aaa', font: { family: 'JetBrains Mono', size: 10 }, boxWidth: 12 }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const total = (breadth.advancers || 0) + (breadth.decliners || 0) || 1;
              const pct = ((ctx.raw / total) * 100).toFixed(0);
              return ` ${ctx.label}: ${ctx.raw} (${pct}%)`;
            }
          }
        }
      }
    }
  });
}

function renderScenarioPanel() {
  if (!marketAnalytics) return;
  const sectors = Object.entries(marketAnalytics.sectors || {}).sort((a, b) => b[1] - a[1]);
  const leader = sectors[0];
  const laggard = sectors[sectors.length - 1];
  const breadthPct = ((marketAnalytics.breadth?.breadth_ratio || 0) * 100).toFixed(0);
  document.getElementById('scenario-panel').innerHTML = `
    <div><span style="color:var(--muted)">Regime:</span> <strong style="color:var(--lime)">${escHtml((marketAnalytics.regime || 'n/a').replace(/_/g, ' '))}</strong></div>
    <div><span style="color:var(--muted)">Scenario:</span> ${escHtml(marketAnalytics.scenario || '—')}</div>
    <div><span style="color:var(--muted)">Benchmark:</span> ${marketAnalytics.benchmark?.return_pct >= 0 ? '+' : ''}${(marketAnalytics.benchmark?.return_pct || 0).toFixed(2)}%</div>
    <div><span style="color:var(--muted)">Sentiment:</span> ${escHtml(marketAnalytics.market_sentiment || 'neutral')}</div>
    <div><span style="color:var(--muted)">Run:</span> ${escHtml(state.run_id || '—')}</div>
    <div><span style="color:var(--muted)">Phase:</span> ${escHtml((state.session_phase || '—').replace(/_/g, ' '))}</div>`;
  document.getElementById('sector-leadership').innerHTML = `
    <div><span style="color:var(--muted)">Leader:</span> <strong style="color:var(--cyan)">${leader ? `${leader[0]} (${(leader[1] - 100).toFixed(2)}%)` : '—'}</strong></div>
    <div><span style="color:var(--muted)">Laggard:</span> <strong style="color:var(--red)">${laggard ? `${laggard[0]} (${(laggard[1] - 100).toFixed(2)}%)` : '—'}</strong></div>
    <div><span style="color:var(--muted)">Breadth:</span> ${breadthPct}%</div>
    <div><span style="color:var(--muted)">Dispersion:</span> ${((marketAnalytics.breadth?.dispersion || 0) * 100).toFixed(2)}%</div>
    <div><span style="color:var(--muted)">Dataset:</span> ${escHtml(state.dataset_version || '—')}</div>
    <div><span style="color:var(--muted)">Scenario ID:</span> ${escHtml(state.scenario_id || '—')}</div>`;
  document.getElementById('risk-decomposition').innerHTML = `
    <div><span style="color:var(--muted)">Realized Vol:</span> <strong style="color:var(--yellow)">${(marketAnalytics.realized_vol_pct || 0).toFixed(2)}%</strong></div>
    <div><span style="color:var(--muted)">Drawdown:</span> ${(marketAnalytics.benchmark?.drawdown_pct || 0).toFixed(2)}%</div>
    <div><span style="color:var(--muted)">Turnover:</span> ${((marketAnalytics.turnover || 0) * 100).toFixed(2)}%</div>
    <div><span style="color:var(--muted)">Session Risk:</span> ${escHtml(marketAnalytics.session_risk || 'Normal')}</div>
    <div><span style="color:var(--muted)">Execution:</span> ${state.latency_ms != null ? `${state.latency_ms}ms` : '—'} / ${state.slippage_bps != null ? Number(state.slippage_bps).toFixed(2) : '—'}bps</div>
    <div><span style="color:var(--muted)">Liquidity:</span> ${escHtml(state.liquidity_model || '—')} / ${escHtml(state.liquidity_regime || '—')}</div>`;
}

function renderStocksTable() {
  const tbody = document.getElementById('stocks-tbody');
  const stocks = Object.entries(allStocks);
  document.getElementById('stock-count').textContent = `(${stocks.length})`;
  tbody.innerHTML = stocks.map(([sym, s]) => {
    const change = s.price - s.initial_price;
    const changePct = s.initial_price ? (change / s.initial_price * 100) : 0;
    const haltedClass = halted.includes(sym) ? '<span class="badge halted">HALTED</span>' : '<span class="badge active">Active</span>';
    const sparkSvg = buildSparkline(sym);
    return `<tr>
      <td>${s.emoji || ''}</td>
      <td><strong style="color:var(--cyan)">${sym}</strong></td>
      <td>${escHtml(s.name)}</td>
      <td><span style="color:var(--muted)">${s.sector || '—'}</span></td>
      <td style="color:var(--white);font-weight:700" data-price-sym="${sym}">${fmtMoney(s.price)}</td>
      <td class="${change >= 0 ? 'pos' : 'neg'}">${change >= 0 ? '+' : ''}${fmtMoney(change)}</td>
      <td class="${changePct >= 0 ? 'pos' : 'neg'}">${changePct >= 0 ? '+' : ''}${changePct.toFixed(2)}%</td>
      <td style="color:var(--muted)">${s.volatility ? s.volatility.toFixed(3) : '—'}</td>
      <td>${sparkSvg}</td>
      <td>${haltedClass}</td>
    </tr>`;
  }).join('');
}

function buildSparkline(sym) {
  const hist = stockHistory[sym];
  if (!hist || hist.length < 2) return '<span style="color:var(--muted);font-family:var(--mono);font-size:9px">—</span>';
  const pts = hist.slice(-30);
  const prices = pts.map(p => p.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const W = 50, H = 20;
  const coords = prices.map((p, i) => {
    const x = (i / (prices.length - 1)) * W;
    const y = H - ((p - min) / range) * H;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  const color = prices[prices.length - 1] >= prices[0] ? 'var(--lime)' : 'var(--red)';
  return `<svg class="sparkline" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><polyline points="${coords}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linejoin="round"/></svg>`;
}

function renderSectorChart() {
  const sectorData = {};
  Object.entries(allStocks).forEach(([sym, s]) => {
    const sec = s.sector || 'Other';
    if (!sectorData[sec]) sectorData[sec] = { total: 0, count: 0, init: 0 };
    sectorData[sec].total += s.price;
    sectorData[sec].init += s.initial_price || s.price;
    sectorData[sec].count++;
  });

  const labels = Object.keys(sectorData);
  const changes = labels.map(l => {
    const d = sectorData[l];
    return d.init ? ((d.total - d.init) / d.init * 100) : 0;
  });
  const colors = labels.map(l => {
    const avg = sectorData[l];
    const chg = avg.init ? ((avg.total - avg.init) / avg.init * 100) : 0;
    return chg >= 0 ? 'rgba(74,222,128,0.7)' : 'rgba(248,113,113,0.7)';
  });

  clearChart('sectorChart');
  const ctx = document.getElementById('sectorChart').getContext('2d');
  chartInstances.sectorChart = new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets: [{ label: 'Avg Change %', data: changes, backgroundColor: colors, borderWidth: 0 }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#aaa', font: { family: 'JetBrains Mono', size: 10 } }, grid: { color: '#1a1a1a' } },
        y: { ticks: { color: '#aaa', font: { family: 'JetBrains Mono', size: 10 }, callback: v => v.toFixed(1) + '%' }, grid: { color: '#1a1a1a' } }
      }
    }
  });
}

async function loadStockChart() {
  const sym = document.getElementById('stock-select').value;
  const caption = document.getElementById('stock-chart-caption');
  if (!sym) {
    clearChart('stockChart');
    if (caption) caption.textContent = 'Select a stock to view its recorded session-by-session price history.';
    return;
  }
  const h = await apiFetch(`/market/history/${sym}`);
  if (!h || !h.history) {
    clearChart('stockChart');
    if (caption) caption.textContent = `No price history is available for ${sym} yet. Run the simulation and try again.`;
    return;
  }
  const pts = h.history;
  if (pts.length < 2) {
    clearChart('stockChart');
    if (caption) caption.textContent = `${sym} needs at least 2 recorded sessions before this chart can draw a trend line. Run another session or day, then reopen Analysis.`;
    return;
  }
  const labels = pts.map(p => `${p.day}.${p.session}`);
  const prices = pts.map(p => p.price);

  // SMA-10
  const sma = prices.map((_, i) => {
    if (i < 9) return null;
    return prices.slice(i - 9, i + 1).reduce((a, b) => a + b) / 10;
  });

  clearChart('stockChart');
  const ctx = document.getElementById('stockChart').getContext('2d');
  chartInstances.stockChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: sym + ' Price', data: prices, borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,0.08)', borderWidth: 2, pointRadius: 0, tension: 0.3 },
        { label: 'SMA-10', data: sma, borderColor: '#fbbf24', backgroundColor: 'transparent', borderWidth: 1, pointRadius: 0, borderDash: [4, 4], spanGaps: true }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#aaa', font: { family: 'JetBrains Mono', size: 10 }, boxWidth: 12 } } },
      scales: {
        x: { ticks: { color: '#555', maxTicksLimit: 8, font: { family: 'JetBrains Mono', size: 9 } }, grid: { color: '#1a1a1a' } },
        y: { ticks: { color: '#aaa', font: { family: 'JetBrains Mono', size: 10 }, callback: v => '$' + v.toFixed(0) }, grid: { color: '#1a1a1a' } }
      }
    }
  });
  if (caption) {
    const start = pts[0];
    const end = pts[pts.length - 1];
    caption.textContent = `${sym} history is active. Showing ${pts.length} recorded points from Day ${start.day} Session ${start.session} through Day ${end.day} Session ${end.session}.`;
  }
}

async function loadReports() {
  const data = await apiFetch('/data/reports');
  const content = document.getElementById('report-content');
  const tabBar = document.getElementById('report-tabs');
  if (!data || !data.length) {
    content.innerHTML = '<div class="empty">No reports yet. Reports are generated on days 12, 78, 144, 210.</div>';
    tabBar.innerHTML = '';
    return;
  }

  const quarters = [...new Set(data.map(r => r.quarter))].sort();
  activeReportTab = activeReportTab || quarters[0];

  tabBar.innerHTML = quarters.map(q =>
    `<div class="tab ${q === activeReportTab ? 'active' : ''}" onclick="switchReportTab('${q}', ${JSON.stringify(data).replace(/</g,'\\u003c')})">${q}</div>`
  ).join('');

  renderReportContent(data.filter(r => r.quarter === activeReportTab));
}

function switchReportTab(q, data) {
  activeReportTab = q;
  document.querySelectorAll('#report-tabs .tab').forEach(t => t.classList.toggle('active', t.textContent === q));
  renderReportContent(data.filter(r => r.quarter === q));
}

function renderReportContent(reports) {
  const content = document.getElementById('report-content');
  if (!reports.length) { content.innerHTML = '<div class="empty">No data for this quarter.</div>'; return; }
  content.innerHTML = `<div class="tbl-wrap"><table>
    <thead><tr>
      <th>Stock</th><th>Revenue Growth</th><th>Gross Margin</th>
      <th>Net Profit (M)</th><th>Cash Flow (M)</th><th>Sentiment</th>
    </tr></thead>
    <tbody>
    ${reports.map(r => `<tr>
      <td><strong style="color:var(--cyan)">${allStocks[r.stock_symbol]?.emoji || ''} ${r.stock_symbol}</strong></td>
      <td class="${r.revenue_growth >= 0 ? 'pos' : 'neg'}">${r.revenue_growth >= 0 ? '+' : ''}${r.revenue_growth.toFixed(1)}%</td>
      <td>${r.gross_margin.toFixed(1)}%</td>
      <td class="${r.net_profit_millions >= 0 ? 'pos' : 'neg'}">${fmtMoney(r.net_profit_millions)}M</td>
      <td class="${r.cash_flow_millions >= 0 ? 'pos' : 'neg'}">${fmtMoney(r.cash_flow_millions)}M</td>
      <td style="color:var(--yellow)">${r.sentiment_score.toFixed(2)}</td>
    </tr>`).join('')}
    </tbody>
  </table></div>`;
}

/* ═══════════════════════════════════════════
   AGENTS PAGE
═══════════════════════════════════════════ */
async function loadAgents() {
  const data = await apiFetch('/agents');
  if (!data) return;
  agents = data;
  const analyticsPairs = await Promise.all(agents.map(async a => [a.id, await apiFetch(`/agents/${a.id}/analytics`)]));
  agentAnalyticsCache = Object.fromEntries(analyticsPairs.filter(([_, val]) => !!val));
  updateMetrics();
  renderAgentsTable();
  buildExplAgentSelect();
}

function renderAgentsTable() {
  const tbody = document.getElementById('agents-tbody');
  const sorted = [...agents].sort((a, b) => b.total_value - a.total_value);
  const medals = ['#1', '#2', '#3'];
  tbody.innerHTML = sorted.map((a, i) => {
    const score = agentAnalyticsCache[a.id] || {};
    const kindBadge = a.agent_kind === 'llm'
      ? '<span class="badge llm">LLM</span>'
      : '<span class="badge rule">RULE</span>';
    const pnlCls = a.pnl >= 0 ? 'pos' : 'neg';
    const checked = selectedForCompare.has(a.id) ? 'checked' : '';
    return `<tr onclick="selectAgent('${a.id}')" style="cursor:pointer">
      <td onclick="event.stopPropagation()">
        <input type="checkbox" class="cmp-checkbox" ${checked}
          title="Compare" onchange="toggleCompare('${a.id}', this)">
      </td>
      <td>${medals[i] || (i + 1)}</td>
      <td><strong>${escHtml(a.name)}</strong></td>
      <td style="color:var(--muted);font-size:11px">${escHtml(a.character_type)}</td>
      <td>${kindBadge}</td>
      <td style="font-weight:700;color:var(--white)">${fmtMoney(a.total_value)}</td>
      <td class="${pnlCls}">${a.pnl >= 0 ? '+' : ''}${fmtMoney(a.pnl)}</td>
      <td class="${pnlCls}">${fmtPct(a.pnl_pct)}</td>
      <td>${score.sharpe_ratio?.toFixed ? score.sharpe_ratio.toFixed(2) : '—'}</td>
      <td>${score.sortino_ratio?.toFixed ? score.sortino_ratio.toFixed(2) : '—'}</td>
      <td>${score.beta?.toFixed ? score.beta.toFixed(2) : '—'}</td>
      <td>${score.consistency_score?.toFixed ? score.consistency_score.toFixed(0) : (a.consistency_score || '—')}</td>
      <td>${a.trades}</td>
      <td>${fmtMoney(a.cash)}</td>
      <td class="${a.debt > 0 ? 'neg' : ''}">${a.debt > 0 ? fmtMoney(a.debt) : '—'}</td>
      <td><span class="badge ${a.status === 'active' ? 'active' : 'sev-high'}">${a.status || 'active'}</span></td>
    </tr>`;
  }).join('');
}

async function selectAgent(id) {
  selectedAgent = id;
  document.querySelectorAll('#agents-tbody tr').forEach(r => r.classList.remove('selected'));
  const agent = agents.find(a => a.id === id);
  if (!agent) return;

  const detail = document.getElementById('agent-detail');
  detail.style.display = 'block';
  document.getElementById('detail-title').textContent = `${agent.name} — ${agent.character_type}`;

  // Analytics
  const an = agentAnalyticsCache[id] || await apiFetch(`/agents/${id}/analytics`);
  if (an) agentAnalyticsCache[id] = an;
  const dc = document.getElementById('detail-analytics');
  if (an) {
    dc.innerHTML = [
      ['Sharpe Ratio', an.sharpe_ratio?.toFixed(3) ?? '—', 'var(--cyan)'],
      ['Sortino', an.sortino_ratio?.toFixed(3) ?? '—', 'var(--lime)'],
      ['Beta', an.beta?.toFixed(3) ?? '—', 'var(--magenta)'],
      ['Volatility', an.volatility != null ? fmtPct(an.volatility) : '—', 'var(--yellow)'],
      ['Max Drawdown', an.max_drawdown != null ? fmtPct(an.max_drawdown) : '—', 'var(--red)'],
      ['Win Rate',     an.win_rate     != null ? fmtPct(an.win_rate)     : '—', 'var(--lime)'],
      ['Consistency', an.consistency_score != null ? `${an.consistency_score.toFixed(0)}/100` : '—', 'var(--white)'],
      ['Concentration', an.concentration_hhi?.toFixed(3) ?? '—', 'var(--cyan)'],
      ['Cash Ratio', an.cash_ratio != null ? fmtPct(an.cash_ratio) : '—', 'var(--yellow)'],
      ['Debt Ratio', an.debt_ratio != null ? fmtPct(an.debt_ratio) : '—', agent.debt > 0 ? 'var(--red)' : 'var(--muted)'],
      ['Avg Trade $', an.avg_trade_size != null ? fmtMoney(an.avg_trade_size) : '—', 'var(--yellow)'],
      ['Total Trades', an.total_trades ?? '—', 'var(--white)'],
    ].map(([label, val, color]) => `
      <div class="card" style="padding:10px">
        <div class="card-title" style="margin-bottom:4px">${label}</div>
        <div style="font-family:var(--mono);font-weight:700;font-size:18px;color:${color}">${val}</div>
      </div>`).join('');
  }

  // Holdings
  const hbody = document.getElementById('holdings-tbody');
  const holdings = agent.holdings || {};
  if (Object.keys(holdings).length) {
    hbody.innerHTML = Object.entries(holdings).map(([sym, qty]) => {
      const price = allStocks[sym]?.price || 0;
      return `<tr>
        <td>${allStocks[sym]?.emoji || ''} <strong>${sym}</strong> — ${escHtml(allStocks[sym]?.name || sym)}</td>
        <td>${qty}</td>
        <td>${fmtMoney(price)}</td>
        <td style="color:var(--cyan);font-weight:700">${fmtMoney(price * qty)}</td>
      </tr>`;
    }).join('');
  } else {
    hbody.innerHTML = '<tr><td colspan="4" style="color:var(--muted);text-align:center">No holdings</td></tr>';
  }

  const attribution = document.getElementById('detail-attribution');
  if (an && an.attribution) {
    const sectorRows = Object.entries(an.attribution.sector_pnl || {}).map(([sector, pnl]) =>
      `<div><span style="color:var(--muted)">${escHtml(sector)}:</span> <strong class="${pnl >= 0 ? 'pos' : 'neg'}">${pnl >= 0 ? '+' : ''}${fmtMoney(pnl)}</strong></div>`
    ).join('') || '<div class="empty">No attribution yet.</div>';
    attribution.innerHTML = `
      <div class="card" style="padding:10px">
        <div class="card-title" style="margin-bottom:8px">PnL Attribution</div>
        <div style="font-family:var(--mono);font-size:11px;line-height:1.8">${sectorRows}</div>
      </div>
      <div class="card" style="padding:10px">
        <div class="card-title" style="margin-bottom:8px">Contribution Split</div>
        <div style="font-family:var(--mono);font-size:11px;line-height:1.8">
          <div><span style="color:var(--muted)">Trading:</span> ${fmtMoney(an.attribution.trading_pnl || 0)}</div>
          <div><span style="color:var(--muted)">Mark-to-market:</span> ${fmtMoney(an.attribution.mark_to_market_pnl || 0)}</div>
          <div><span style="color:var(--muted)">Best:</span> ${escHtml(an.attribution.best_contributor?.symbol || '—')} ${fmtMoney(an.attribution.best_contributor?.pnl || 0)}</div>
          <div><span style="color:var(--muted)">Worst:</span> ${escHtml(an.attribution.worst_contributor?.symbol || '—')} ${fmtMoney(an.attribution.worst_contributor?.pnl || 0)}</div>
        </div>
      </div>`;
  } else {
    attribution.innerHTML = '<div class="empty">No attribution summary yet.</div>';
  }
}

/* ═══════════════════════════════════════════
   LOANS
═══════════════════════════════════════════ */
async function loadLoans() {
  const data = await apiFetch('/data/loans');
  const tbody = document.getElementById('loans-tbody');
  if (!data || !data.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty">No loans outstanding.</td></tr>';
    return;
  }
  tbody.innerHTML = data.map(l => {
    const statusCls = l.status === 'active' ? 'active' : l.status === 'defaulted' ? 'sev-high' : 'sev-low';
    return `<tr>
      <td>${escHtml(l.agent_name)}</td>
      <td style="color:var(--yellow);font-weight:700">${fmtMoney(l.amount)}</td>
      <td>${(l.rate * 100).toFixed(1)}%</td>
      <td>${l.term} days</td>
      <td style="color:var(--cyan)">${fmtMoney(l.remaining)}</td>
      <td>Day ${l.due}</td>
      <td><span class="badge ${statusCls}">${l.status}</span></td>
    </tr>`;
  }).join('');
}

/* ═══════════════════════════════════════════
   CUSTOM AGENT
═══════════════════════════════════════════ */
function showCustomAgentForm() { openAgentModal(); }

function openAgentModal() {
  // Reset form preview
  document.getElementById('ca-name').value = '';
  document.getElementById('ca-desc').value = '';
  document.getElementById('modal-name-display').textContent = 'New Agent';
  document.getElementById('modal-avatar').textContent = '?';
  document.getElementById('agent-modal-overlay').classList.add('open');
  setTimeout(() => document.getElementById('ca-name').focus(), 50);
}

function closeAgentModal(e) {
  if (e && e.target !== document.getElementById('agent-modal-overlay')) return;
  document.getElementById('agent-modal-overlay').classList.remove('open');
}

function updateModalPreview() {
  const name = document.getElementById('ca-name').value.trim();
  document.getElementById('modal-name-display').textContent = name || 'New Agent';
  document.getElementById('modal-avatar').textContent = name ? name[0].toUpperCase() : '?';
}

function hideCustomAgentForm() { closeAgentModal(); }

async function submitCustomAgent() {
  const name = document.getElementById('ca-name').value.trim();
  const character_type = document.getElementById('ca-type').value;
  const risk_tolerance = document.getElementById('ca-risk').value;
  const description = document.getElementById('ca-desc').value.trim();

  if (!name) { toast('Agent name required', 'var(--red)'); return; }
  const r = await apiPost('/agents/custom', { name, character_type, risk_tolerance, description });
  if (r) {
    toast(`Agent "${name}" created ✓`, 'var(--lime)');
    closeAgentModal();
    loadAgents();
  } else {
    toast('Failed to create agent', 'var(--red)');
  }
}

/* ═══════════════════════════════════════════
/* ═══════════════════════════════════════════
   EXPLAINABILITY PAGE
═══════════════════════════════════════════ */

// Maps bias level strings → numeric 0-10 for radar chart
function biasLevelToNum(level) {
  const m = { 'Low':2, 'Medium':5, 'Medium-High':6.5, 'High':8, 'Very High':10 };
  return m[level] || 5;
}

let _explDecisions = [];   // cache for timeline filter
let _explFilter = '';

function buildExplAgentSelect() {
  const sel = document.getElementById('expl-agent-select');
  const cur = sel.value;
  sel.innerHTML = '<option value="">All Agents (Global View)</option>';
  agents.forEach(a => {
    sel.innerHTML += `<option value="${a.id}" ${a.id === cur ? 'selected' : ''}>${escHtml(a.name)} (${a.character_type})</option>`;
  });
}

async function loadExplainabilityPage() {
  if (!agents.length) await loadAgents();
  buildExplAgentSelect();
  await loadGlobalExplainability();
}

async function loadGlobalExplainability() {
  const data = await apiFetch('/agents/explainability');
  if (!data) return;

  const totalDec = data.total_decisions || 0;

  // ── Summary strip ──
  document.getElementById('expl-total-dec').textContent = totalDec.toLocaleString();

  const biases = data.bias_counts || {};
  const topBiasEntry = Object.entries(biases).sort((a, b) => b[1] - a[1])[0];
  document.getElementById('expl-top-bias').textContent = topBiasEntry
    ? topBiasEntry[0].replace(/_/g, ' ') + ' (' + topBiasEntry[1] + ')'
    : '—';
  document.getElementById('expl-active-agent').textContent = data.most_active_agent || '—';

  const topStocksGlobal = data.top_stocks_global || {};
  const topStkEntry = Object.entries(topStocksGlobal).sort((a, b) => b[1] - a[1])[0];
  document.getElementById('expl-top-stock').textContent = topStkEntry
    ? (allStocks[topStkEntry[0]]?.name || topStkEntry[0])
    : '—';
  document.getElementById('expl-avg-conviction').textContent = data.avg_conviction != null ? `${data.avg_conviction.toFixed(1)}/100` : '—';
  document.getElementById('expl-thesis-drift').textContent = data.thesis_drift_total ?? '—';
  document.getElementById('expl-consistency-avg').textContent = data.decision_consistency_avg != null ? `${data.decision_consistency_avg.toFixed(1)}/100` : '—';

  // ── Bias distribution chart ──
  const biasEmpty = document.getElementById('biasChart-empty');
  if (Object.keys(biases).length) {
    biasEmpty.style.display = 'none';
    clearChart('biasChart');
    const ctx = document.getElementById('biasChart').getContext('2d');
    chartInstances.biasChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: Object.keys(biases).map(k => k.replace(/_/g, ' ')),
        datasets: [{ label: 'Count', data: Object.values(biases), backgroundColor: 'rgba(232,121,160,0.75)', borderWidth: 0, borderRadius: 3 }]
      },
      options: {
        responsive: true, maintainAspectRatio: false, indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#888', font: { family: 'JetBrains Mono', size: 10 } }, grid: { color: '#181818' } },
          y: { ticks: { color: '#ccc', font: { family: 'JetBrains Mono', size: 10 } }, grid: { color: '#181818' } }
        }
      }
    });
  } else {
    biasEmpty.style.display = '';
    clearChart('biasChart');
  }

  // ── Action distribution chart ──
  const actionEmpty = document.getElementById('actionChart-empty');
  const actions = data.action_distribution || {};
  const hasActions = Object.values(actions).some(v => v > 0);
  if (hasActions) {
    actionEmpty.style.display = 'none';
    clearChart('actionChart');
    const ctx2 = document.getElementById('actionChart').getContext('2d');
    const aColors = { buy: '#4ade80', sell: '#f87171', hold: '#fbbf24' };
    chartInstances.actionChart = new Chart(ctx2, {
      type: 'doughnut',
      data: {
        labels: Object.keys(actions).map(k => k.toUpperCase()),
        datasets: [{ data: Object.values(actions), backgroundColor: Object.keys(actions).map(k => aColors[k] || '#999'), borderWidth: 2, borderColor: '#0a0a0a' }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { color: '#aaa', font: { family: 'JetBrains Mono', size: 10 }, boxWidth: 12 } },
          tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw} (${Math.round(ctx.raw/totalDec*100)}%)` } }
        }
      }
    });
  } else {
    actionEmpty.style.display = '';
    clearChart('actionChart');
  }

  // ── Bias Radar (aggregate avg of all agents) ──
  const perAgent = data.per_agent || [];
  if (perAgent.length) {
    const biasKeys = ['herding', 'loss_aversion', 'overconfidence', 'anchoring'];
    const avgBias = {};
    biasKeys.forEach(k => {
      const vals = perAgent.map(a => biasLevelToNum((a.bias_profile || {})[k] || 'Medium'));
      avgBias[k] = vals.reduce((s, v) => s + v, 0) / vals.length;
    });
    renderBiasRadar(avgBias, 'All Agents Avg');
  }

  // ── Top Stocks (global) ──
  if (Object.keys(topStocksGlobal).length) {
    renderTopStocksChart(topStocksGlobal, '(global)');
  } else {
    document.getElementById('topStocksChart-empty').style.display = '';
    document.getElementById('topstock-agent-label').textContent = '';
    clearChart('topStocksChart');
  }

  // ── All-Agents Comparison Table ──
  renderAgentComparisonTable(perAgent);
}

function renderBiasRadar(biasProfileOrValues, label) {
  const biasKeys = ['herding', 'loss_aversion', 'overconfidence', 'anchoring'];
  const labels = ['Herding', 'Loss Aversion', 'Overconfidence', 'Anchoring'];
  const values = typeof Object.values(biasProfileOrValues)[0] === 'string'
    ? biasKeys.map(k => biasLevelToNum((biasProfileOrValues || {})[k] || 'Medium'))
    : biasKeys.map(k => biasProfileOrValues[k] || 5);
  document.getElementById('radar-agent-label').textContent = label ? `— ${label}` : '';
  clearChart('biasRadarChart');
  const ctx = document.getElementById('biasRadarChart').getContext('2d');
  chartInstances.biasRadarChart = new Chart(ctx, {
    type: 'radar',
    data: {
      labels,
      datasets: [{
        label: label || 'Bias Profile',
        data: values,
        backgroundColor: 'rgba(56,189,248,0.12)',
        borderColor: 'rgba(56,189,248,0.85)',
        pointBackgroundColor: '#38bdf8',
        pointRadius: 4,
        borderWidth: 2
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        r: {
          min: 0, max: 10,
          ticks: { stepSize: 2, color: '#555', font: { size: 9 }, backdropColor: 'transparent' },
          grid: { color: '#1a1a1a' },
          pointLabels: { color: '#bbb', font: { family: 'JetBrains Mono', size: 10 } },
          angleLines: { color: '#1a1a1a' }
        }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function renderTopStocksChart(stockCounts, label) {
  const sorted = Object.entries(stockCounts).sort((a, b) => b[1] - a[1]).slice(0, 8);
  document.getElementById('topstock-agent-label').textContent = label || '';
  document.getElementById('topStocksChart-empty').style.display = 'none';
  clearChart('topStocksChart');
  const ctx = document.getElementById('topStocksChart').getContext('2d');
  const palette = ['#4ade80', '#38bdf8', '#fbbf24', '#e879a0', '#a78bfa', '#fb923c', '#34d399', '#60a5fa'];
  chartInstances.topStocksChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: sorted.map(([s]) => s),
      datasets: [{ label: 'Trades', data: sorted.map(([, c]) => c), backgroundColor: sorted.map((_, i) => palette[i % palette.length]), borderWidth: 0, borderRadius: 3 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#888', font: { family: 'JetBrains Mono', size: 10 } }, grid: { color: '#181818' } },
        y: { ticks: { color: '#ccc', font: { family: 'JetBrains Mono', size: 10 } }, grid: { color: '#181818' } }
      }
    }
  });
}

function renderAgentComparisonTable(perAgent) {
  const el = document.getElementById('agent-expl-table');
  if (!perAgent || !perAgent.length) {
    el.innerHTML = '<div class="empty" style="padding:20px">No agents found. Start a simulation first.</div>';
    return;
  }
  const biasKeys = ['herding', 'loss_aversion', 'overconfidence', 'anchoring'];
  const biasColors = { herding: '#e879a0', loss_aversion: '#f87171', overconfidence: '#fbbf24', anchoring: '#38bdf8' };

  const rows = perAgent.map(a => {
    const ac = a.action_counts || {};
    const total = (ac.buy || 0) + (ac.sell || 0) + (ac.hold || 0) || 1;
    const buyPct = Math.round((ac.buy || 0) / total * 100);
    const sellPct = Math.round((ac.sell || 0) / total * 100);
    const holdPct = 100 - buyPct - sellPct;
    const bp = a.bias_profile || {};
    const domBias = biasKeys.reduce((best, k) => biasLevelToNum(bp[k] || 'Low') >= biasLevelToNum(bp[best] || 'Low') ? k : best, biasKeys[0]);
    const kindBadge = a.kind === 'llm'
      ? '<span class="badge buy" style="font-size:9px;padding:2px 6px">LLM</span>'
      : '<span class="badge hold" style="font-size:9px;padding:2px 6px">RULE</span>';

    // Mini bias bars
    const barsHtml = biasKeys.map(k => {
      const val = biasLevelToNum(bp[k] || 'Low');
      return `<div class="bias-bar-seg" style="background:${biasColors[k]};width:${val * 10}px;opacity:0.8" title="${k.replace(/_/g,' ')}: ${bp[k]||'—'}"></div>`;
    }).join('');

    return `<tr>
      <td style="color:var(--lime);font-weight:700;white-space:nowrap">${escHtml(a.name)}</td>
      <td style="color:var(--muted)">${a.type}</td>
      <td>${kindBadge}</td>
      <td style="text-align:right;color:${a.decisions > 0 ? 'var(--cyan)' : 'var(--muted)'}">${a.decisions}</td>
      <td>
        <div style="display:flex;gap:3px;align-items:center">
          <div style="height:5px;background:var(--lime);border-radius:2px;width:${Math.round(buyPct*0.7)}px" title="Buy ${buyPct}%"></div>
          <div style="height:5px;background:var(--red);border-radius:2px;width:${Math.round(sellPct*0.7)}px" title="Sell ${sellPct}%"></div>
          <div style="height:5px;background:var(--yellow);border-radius:2px;width:${Math.round(holdPct*0.7)}px" title="Hold ${holdPct}%"></div>
          <span style="font-size:9px;color:var(--muted);margin-left:4px">${buyPct}/${sellPct}/${holdPct}</span>
        </div>
      </td>
      <td>
        <div class="bias-bar-wrap">${barsHtml}</div>
        <div style="font-size:9px;color:${biasColors[domBias]};margin-top:2px">${domBias.replace(/_/g,' ')} (${bp[domBias] || '—'})</div>
      </td>
      <td style="color:var(--muted);font-size:11px">${a.risk_tolerance || '—'} · ${a.avg_conviction?.toFixed ? a.avg_conviction.toFixed(0) : 0} cv · ${a.consistency_score?.toFixed ? a.consistency_score.toFixed(0) : 0} cs · ${a.thesis_drift_count || 0} drift</td>
    </tr>`;
  }).join('');

  el.innerHTML = `<table class="expl-table">
    <thead><tr>
      <th>AGENT</th><th>TYPE</th><th>KIND</th><th style="text-align:right">DECISIONS</th>
      <th>BUY / SELL / HOLD</th><th>BIAS PROFILE</th><th>RISK</th>
    </tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

async function loadExplainability() {
  const id = document.getElementById('expl-agent-select').value;
  if (!id) {
    // Switched back to global view
    _explDecisions = [];
    _explFilter = '';
    document.getElementById('expl-count').textContent = '';
    document.getElementById('expl-stats').innerHTML = '';
    document.getElementById('decision-timeline').innerHTML = '<div class="empty">Select an agent above to inspect its decisions.</div>';
    await loadGlobalExplainability();
    return;
  }

  const data = await apiFetch(`/agents/${id}/decisions`);
  const timeline = document.getElementById('decision-timeline');

  if (!data || !data.decisions || !data.decisions.length) {
    _explDecisions = [];
    timeline.innerHTML = '<div class="empty">No decisions logged yet for this agent. Start the simulation.</div>';
    document.getElementById('expl-count').textContent = '';
    document.getElementById('expl-stats').innerHTML = '';
    return;
  }

  _explDecisions = data.decisions;
  _explFilter = '';

  // ── Per-agent quick stats ──
  const buys  = _explDecisions.filter(d => d.action === 'buy').length;
  const sells = _explDecisions.filter(d => d.action === 'sell').length;
  const holds = _explDecisions.filter(d => d.action === 'hold').length;
  document.getElementById('expl-stats').innerHTML = [
    ['BUY Decisions',  buys,  'var(--lime)'],
    ['SELL Decisions', sells, 'var(--red)'],
    ['HOLD Decisions', holds, 'var(--yellow)'],
    ['Avg Conviction', Math.round(_explDecisions.reduce((sum, d) => sum + (d.memo?.conviction || 0), 0) / _explDecisions.length || 0), 'var(--cyan)'],
  ].map(([label, val, color]) => `
    <div class="card" style="padding:12px">
      <div class="card-title" style="margin-bottom:4px;font-size:10px">${label}</div>
      <div style="font-family:var(--mono);font-weight:800;font-size:28px;color:${color}">${val}</div>
      <div style="font-size:10px;color:var(--muted);font-family:var(--mono)">${label === 'Avg Conviction' ? 'memo quality signal' : `${Math.round(val/_explDecisions.length*100)}% of total`}</div>
    </div>`).join('');

  // ── Bias Radar for this agent ──
  const agent = agents.find(a => String(a.id) === String(id));
  if (agent && agent.bias_profile) {
    renderBiasRadar(agent.bias_profile, agent.name);
  }

  // ── Top Stocks for this agent ──
  const stockCounts = {};
  _explDecisions.forEach(d => { if (d.stock) stockCounts[d.stock] = (stockCounts[d.stock] || 0) + 1; });
  if (Object.keys(stockCounts).length) {
    renderTopStocksChart(stockCounts, `— ${agent?.name || 'Agent'}`);
  }

  document.getElementById('expl-count').textContent = `(${_explDecisions.length} total)`;
  
  // ── Update Bias Distribution Chart for this agent ──
  const agentBiases = {};
  _explDecisions.forEach(d => {
    (d.biases || []).forEach(b => {
      agentBiases[b] = (agentBiases[b] || 0) + 1;
    });
  });
  
  const biasEmpty = document.getElementById('biasChart-empty');
  if (Object.keys(agentBiases).length) {
    biasEmpty.style.display = 'none';
    clearChart('biasChart');
    const ctx = document.getElementById('biasChart').getContext('2d');
    chartInstances.biasChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: Object.keys(agentBiases).map(k => k.replace(/_/g, ' ')),
        datasets: [{ label: 'Count', data: Object.values(agentBiases), backgroundColor: 'rgba(232,121,160,0.75)', borderWidth: 0, borderRadius: 3 }]
      },
      options: {
        responsive: true, maintainAspectRatio: false, indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#888', font: { family: 'JetBrains Mono', size: 10 } }, grid: { color: '#181818' } },
          y: { ticks: { color: '#ccc', font: { family: 'JetBrains Mono', size: 10 } }, grid: { color: '#181818' } }
        }
      }
    });
  } else {
    biasEmpty.style.display = '';
    clearChart('biasChart');
  }

  renderTimeline();
}

function filterTimeline(action) {
  _explFilter = action;
  renderTimeline();
}

function renderTimeline() {
  const timeline = document.getElementById('decision-timeline');
  if (!_explDecisions.length) {
    timeline.innerHTML = '<div class="empty">Select an agent above to inspect its decisions.</div>';
    return;
  }
  const list = _explFilter
    ? _explDecisions.filter(d => d.action === _explFilter)
    : _explDecisions;
  if (!list.length) {
    timeline.innerHTML = `<div class="empty">No ${_explFilter} decisions found.</div>`;
    return;
  }
  const actionColor = { buy: 'var(--lime)', sell: 'var(--red)', hold: 'var(--yellow)' };
  timeline.innerHTML = [...list].reverse().map(d => `
    <div class="decision-entry">
      <div class="decision-header">
        <span class="decision-day">Day ${d.day} S${d.session}</span>
        <span class="badge ${d.action}">${d.action.toUpperCase()}</span>
        <strong style="color:var(--cyan)">${d.stock || '—'}</strong>
        <span style="font-family:var(--mono);font-size:11px;color:var(--muted)">${d.quantity || 0} @ ${fmtMoney(d.price)}</span>
        ${d.biases && d.biases.length ? `<span style="font-size:10px;color:var(--muted)">[${d.biases.join(', ')}]</span>` : ''}
      </div>
      ${d.reasoning ? `<div class="decision-reasoning">${escHtml(d.reasoning)}</div>` : ''}
      ${d.memo ? `<div style="margin-top:8px;font-family:var(--mono);font-size:10px;line-height:1.8;color:var(--muted)">
        <div><span style="color:var(--cyan)">Thesis:</span> ${escHtml(d.memo.thesis || '—')}</div>
        <div><span style="color:var(--yellow)">Catalyst:</span> ${escHtml(d.memo.catalyst || '—')}</div>
        <div><span style="color:var(--red)">Risk:</span> ${escHtml(d.memo.risk || '—')}</div>
        <div><span style="color:var(--lime)">Conviction:</span> ${d.memo.conviction || 0}/100 · Horizon ${d.memo.horizon_days || 0}d · ${escHtml(d.memo.exposure_impact || 'maintain')}</div>
      </div>` : ''}
    </div>`).join('');
}

/* ═══════════════════════════════════════════
   SETTINGS
═══════════════════════════════════════════ */
async function applyConfig() {
  const num_agents = parseInt(document.getElementById('cfg-agents').value);
  const num_days   = parseInt(document.getElementById('cfg-days').value);
  const use_llm    = document.getElementById('cfg-llm').checked;
  const enable_loans = document.getElementById('cfg-loans').checked;
  const volatility = document.getElementById('cfg-vol').value;
  const speed = parseFloat(document.getElementById('cfg-speed').value);
  const regime_sensitivity = parseFloat(document.getElementById('cfg-regime-sensitivity').value);
  const benchmark_mode = document.getElementById('cfg-benchmark-mode').value;
  const analytics_detail = document.getElementById('cfg-analytics-detail').value;
  const seedVal    = document.getElementById('cfg-seed').value;
  const seed       = seedVal ? parseInt(seedVal) : null;

  const r = await apiPost('/simulation/config', {
    num_agents, num_days, use_llm, enable_loans, seed,
    volatility, speed, regime_sensitivity, benchmark_mode, analytics_detail
  });
  if (r) {
    configuredDays = num_days;
    toast('Config applied ✓', 'var(--lime)');
    await loadMarketAnalytics();
    updateMetrics();
  } else toast('Failed to apply config', 'var(--red)');
}

async function injectEvent() {
  const title       = document.getElementById('ev-title').value.trim();
  const description = document.getElementById('ev-desc').value.trim();
  const severity    = document.getElementById('ev-sev').value;
  const impact_pct  = parseFloat(document.getElementById('ev-impact').value) || 0;
  const stocksRaw   = document.getElementById('ev-stocks').value.trim();
  const affected_stocks = stocksRaw ? stocksRaw.split(',').map(s => s.trim().toUpperCase()).filter(Boolean) : [];

  if (!title) { toast('Event title required', 'var(--red)'); return; }
  const r = await apiPost('/data/event', { title, description, severity, impact_pct, affected_stocks });
  if (r) {
    toast('Event injected ✓', 'var(--magenta)');
    document.getElementById('ev-title').value = '';
    document.getElementById('ev-desc').value = '';
    document.getElementById('ev-impact').value = '';
    document.getElementById('ev-stocks').value = '';
    loadEvents();
  } else {
    toast('Failed to inject event', 'var(--red)');
  }
}

async function exportData() {
  const data = await apiFetch('/data/export');
  if (!data) { toast('Export failed', 'var(--red)'); return; }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href  = url;
  a.download = `stockai_export_day${state.day || 0}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  toast('Export downloaded ✓', 'var(--cyan)');
}

/* ═══════════════════════════════════════════
   CHATBOT
═══════════════════════════════════════════ */
let chatOpen = false;
function toggleChat() {
  chatOpen = !chatOpen;
  document.getElementById('chatbot-panel').classList.toggle('open', chatOpen);
}

function getTopStock() {
  const entries = Object.entries(allStocks);
  if (!entries.length) return 'N/A';
  return entries.sort((a, b) => {
    const pa = a[1].initial_price ? ((a[1].price - a[1].initial_price) / a[1].initial_price) : 0;
    const pb = b[1].initial_price ? ((b[1].price - b[1].initial_price) / b[1].initial_price) : 0;
    return pb - pa;
  })[0][0];
}

function buildChatContext() {
  const parts = [`Day ${state.day || 0} of ${configuredDays}`];
  parts.push(`${state.active_agents || 0} agents, ${state.total_trades || 0} trades`);
  if (halted.length) parts.push(`Halted: ${halted.join(', ')}`);
  const top = getTopStock();
  if (top !== 'N/A') parts.push(`Top mover: ${top}`);
  if (agents.length) {
    const best = [...agents].sort((a, b) => b.pnl - a.pnl)[0];
    if (best) parts.push(`Best agent: ${best.name} (${best.pnl >= 0 ? '+' : ''}${(best.pnl || 0).toFixed(0)})`);
  }
  return '[Context: ' + parts.join('; ') + ']';
}

function getChatHistory() {
  try { return JSON.parse(sessionStorage.getItem('chatLog') || '[]'); } catch { return []; }
}

function loadChatHistory() {
  const hist = getChatHistory();
  if (hist.length) {
    const container = document.getElementById('chat-messages');
    container.innerHTML = '';
    hist.forEach(m => appendMsg(m.role === 'user' ? 'user' : 'bot', m.content, [], m.low_confidence));
  }
}

async function sendChat() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';

  appendMsg('user', msg);
  const hist = getChatHistory();
  hist.push({role: 'user', content: msg});
  const ctx = buildChatContext();
  const r = await apiPost('/chat', { message: msg + ' ' + ctx, history: hist.slice(-16) });
  if (r) {
    const isLow = !!r.confidence && r.confidence !== 'high';
    // suggested_followup may be a string or array — normalise to array
    const followups = Array.isArray(r.suggested_followup)
      ? r.suggested_followup
      : (r.suggested_followup ? [r.suggested_followup] : []);
    appendMsg('bot', r.response, followups, isLow);
    hist.push({role: 'assistant', content: r.response, low_confidence: isLow});
  } else {
    appendMsg('bot', 'Sorry, I could not reach the assistant right now.', [], true);
    hist.push({role: 'assistant', content: 'Sorry, I could not reach the assistant right now.', low_confidence: true});
  }
  sessionStorage.setItem('chatLog', JSON.stringify(hist.slice(-20)));
}

function askChat(q) {
  if (!chatOpen) toggleChat();
  document.getElementById('chat-input').value = q;
  sendChat();
}

function appendMsg(role, text, followups = [], isLow = false) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-msg ' + role;
  div.textContent = text;
  if (isLow && role === 'bot') {
    const badge = document.createElement('div');
    badge.style.cssText = 'margin-top:6px;font-size:10px;color:#f5c842;border:1px solid #f5c842;display:inline-block;padding:2px 6px;font-family:var(--mono);font-weight:700;';
    badge.textContent = 'LOW CONFIDENCE';
    div.appendChild(badge);
  }
  container.appendChild(div);

  if (followups && followups.length) {
    const row = document.createElement('div');
    row.className = 'chat-followup';
    followups.forEach(f => {
      const chip = document.createElement('button');
      chip.className = 'followup-chip';
      chip.textContent = f;
      chip.onclick = () => {
        document.getElementById('chat-input').value = f;
        sendChat();
      };
      row.appendChild(chip);
    });
    container.appendChild(row);
  }
  container.scrollTop = container.scrollHeight;
}

/* ═══════════════════════════════════════════
   UTILITIES
═══════════════════════════════════════════ */
function fmtMoney(v) {
  if (v == null) return '—';
  if (Math.abs(v) >= 1e6) return '$' + (v / 1e6).toFixed(2) + 'M';
  if (Math.abs(v) >= 1e3) return '$' + v.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return '$' + v.toFixed(2);
}

function fmtPct(v) {
  if (v == null) return '—';
  return (v >= 0 ? '+' : '') + v.toFixed(2) + '%';
}

function escHtml(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function clearChart(id) {
  if (chartInstances[id]) { chartInstances[id].destroy(); delete chartInstances[id]; }
}

/* ═══════════════════════════════════════════
   PERIODIC REFRESH
═══════════════════════════════════════════ */
let refreshTimer = null;
function startRefreshLoop() {
  clearInterval(refreshTimer);
  refreshTimer = setInterval(async () => {
    const page = (location.hash || '#dashboard').replace('#', '');
    if (!wsConnected) {
      await pollStatus();
    }
    if (page === 'dashboard') {
      loadTrades();
      loadEvents();
      loadForum();
      loadSnapshots();
      // Refresh stock prices & price chart
      const freshData = await apiFetch('/market/stocks');
      if (freshData) {
        allStocks = freshData;
        await loadPriceHistories();
      }
    }
    if (page === 'agents') {
      loadAgents();
      loadLoans();
    }
    if (page === 'analysis') {
      const data = await apiFetch('/market/stocks');
      if (data) {
        allStocks = data;
        renderStocksTable();
        renderSectorChart();
        renderHeatmap();
      }
    }
  }, 3000);
}

/* ═══════════════════════════════════════════
   INIT
═══════════════════════════════════════════ */
async function init() {
  try {
    connectWS();
    await pollStatus();
    await loadMarketAnalytics();
    await loadMarketStocks();
    await loadAgents();
    loadTrades();
    loadEvents();
    loadForum();
    loadSnapshots();
    loadChatHistory();
    updateMetrics();
    startRefreshLoop();
  } catch (err) {
    console.error("INIT ERROR:", err);
    alert("Init failed: " + err.message + "\n" + err.stack);
  }
}

init();

/* ═══════════════════════════════════════════
   STOCK HEATMAP
═══════════════════════════════════════════ */
const SECTOR_ORDER = ['Tech','Energy','Finance','Auto','Retail','Entertainment'];

function heatmapColor(pct) {
  // Muted palette: soft teal for gains, soft rose for losses
  const v = Math.max(-10, Math.min(10, pct));
  if (v >= 0) {
    // 0 → dark charcoal, +10 → muted teal (~#1e8c78)
    const t = v / 10;
    const r = Math.round(18 + 12 * t);
    const g = Math.round(24 + 116 * t);
    const b = Math.round(28 + 92 * t);
    return `rgb(${r},${g},${b})`;
  } else {
    // 0 → dark charcoal, -10 → muted rose (~#b43246)
    const t = -v / 10;
    const r = Math.round(18 + 162 * t);
    const g = Math.round(24 - 14 * t);
    const b = Math.round(28 + 42 * t);
    return `rgb(${r},${g},${b})`;
  }
}

function renderHeatmap() {
  const container = document.getElementById('heatmap-grid');
  if (!container) return;
  const byeSector = {};
  Object.entries(allStocks).forEach(([sym, s]) => {
    const sec = s.sector || 'Other';
    if (!byeSector[sec]) byeSector[sec] = [];
    const chgPct = s.initial_price ? ((s.price - s.initial_price) / s.initial_price * 100) : 0;
    byeSector[sec].push({ sym, s, chgPct });
  });

  const sectors = [...SECTOR_ORDER, ...Object.keys(byeSector).filter(k => !SECTOR_ORDER.includes(k))];
  container.innerHTML = sectors.filter(sec => byeSector[sec]).map(sec => {
    const stocks = byeSector[sec] || [];
    const cells = stocks.map(({ sym, s, chgPct }) => {
      const bg = heatmapColor(chgPct);
      const textColor = Math.abs(chgPct) > 4 ? '#000' : '#fff';
      return `<div class="heatmap-cell" style="background:${bg};color:${textColor}" title="${escHtml(s.name)} — ${fmtMoney(s.price)} (${chgPct >= 0 ? '+' : ''}${chgPct.toFixed(2)}%)">
        <div class="hmap-em">${s.emoji || ''}</div>
        <div class="hmap-sym">${s.name.split(' ')[0]}</div>
        <div class="hmap-pct">${chgPct >= 0 ? '+' : ''}${chgPct.toFixed(1)}%</div>
        <div class="hmap-price" data-price-sym="${sym}">${fmtMoney(s.price)}</div>
      </div>`;
    }).join('');
    return `<div class="heatmap-sector">
      <div class="heatmap-sector-label">${sec}</div>
      <div class="heatmap-row">${cells}</div>
    </div>`;
  }).join('');
}

/* ═══════════════════════════════════════════
   ORDER BOOK DEPTH CHART
═══════════════════════════════════════════ */
function buildDepthSelect() {
  const sel = document.getElementById('depth-stock-select');
  if (!sel) return;
  const cur = sel.value;
  sel.innerHTML = '<option value="">Select stock…</option>';
  Object.entries(allStocks).forEach(([sym, s]) => {
    sel.innerHTML += `<option value="${sym}" ${sym === cur ? 'selected' : ''}>${s.emoji || ''} ${sym} — ${escHtml(s.name)}</option>`;
  });
  if (cur) loadDepth();
}

async function loadDepth() {
  const sym = document.getElementById('depth-stock-select').value;
  const content = document.getElementById('depth-content');
  if (!sym) { content.innerHTML = '<div class="empty">Select a stock to view order book depth.</div>'; return; }

  const data = await apiFetch(`/market/${sym}`);
  if (!data) { content.innerHTML = '<div class="empty">No data.</div>'; return; }

  const bids = (data.bids || []).slice(0, 8);
  const asks = (data.asks || []).slice(0, 8);
  const maxBidQty = Math.max(...bids.map(b => b[1] || b.quantity || 0), 1);
  const maxAskQty = Math.max(...asks.map(a => a[1] || a.quantity || 0), 1);

  const bidRows = bids.map(b => {
    const price = b[0] != null ? b[0] : b.price;
    const qty   = b[1] != null ? b[1] : b.quantity;
    const pct = Math.round((qty / maxBidQty) * 100);
    return `<div class="depth-row" style="padding:4px 6px">
      <div class="depth-bar bid" style="width:${pct}%"></div>
      <span class="depth-price pos">${fmtMoney(price)}</span>
      <span class="depth-qty">${qty}</span>
    </div>`;
  }).join('');

  const askRows = asks.map(a => {
    const price = a[0] != null ? a[0] : a.price;
    const qty   = a[1] != null ? a[1] : a.quantity;
    const pct = Math.round((qty / maxAskQty) * 100);
    return `<div class="depth-row" style="padding:4px 6px">
      <div class="depth-bar ask" style="width:${pct}%"></div>
      <span class="depth-price neg">${fmtMoney(price)}</span>
      <span class="depth-qty">${qty}</span>
    </div>`;
  }).join('');

  const spread = (bids[0] && asks[0])
    ? fmtMoney(Math.abs((asks[0][0] ?? asks[0].price) - (bids[0][0] ?? bids[0].price)))
    : '—';

  content.innerHTML = `
    <div style="display:flex;gap:4px;align-items:center;margin-bottom:10px;font-family:var(--mono);font-size:11px">
      <span style="color:var(--muted)">Last:</span>
      <span style="color:var(--white);font-weight:700">${fmtMoney(data.last_price)}</span>
      <span style="color:var(--muted);margin-left:8px">Spread:</span>
      <span style="color:var(--yellow);font-weight:700">${spread}</span>
    </div>
    <div class="depth-wrap">
      <div class="depth-col">
        <div class="depth-col-title" style="color:var(--lime)">▲ Bids (${bids.length})</div>
        ${bidRows || '<div style="color:var(--muted);font-family:var(--mono);font-size:11px;padding:8px">No bids</div>'}
      </div>
      <div class="depth-col">
        <div class="depth-col-title" style="color:var(--red)">▼ Asks (${asks.length})</div>
        ${askRows || '<div style="color:var(--muted);font-family:var(--mono);font-size:11px;padding:8px">No asks</div>'}
      </div>
    </div>`;
}

/* ═══════════════════════════════════════════
   AGENT PORTFOLIO RACE CHART
═══════════════════════════════════════════ */
const RACE_COLORS = [
  '#4ade80','#e879a0','#38bdf8','#fbbf24','#f97316',
  '#c0f0ff','#f0c0ff','#f87171','#99ffcc','#aaaaff'
];
let raceVisible = new Set();

async function loadRaceChart() {
  if (!agents.length) await loadAgents();

  // Build race toggles (top-10 agents)
  const top10 = [...agents].sort((a, b) => b.total_value - a.total_value).slice(0, 10);
  if (!raceVisible.size) top10.slice(0, 5).forEach(a => raceVisible.add(a.id));

  const toggleRow = document.getElementById('race-toggles');
  if (toggleRow && toggleRow.children.length === 0) {
    top10.forEach((a, i) => {
      const btn = document.createElement('button');
      btn.className = 'agent-toggle' + (raceVisible.has(a.id) ? ' on' : '');
      btn.textContent = a.name;
      btn.style.setProperty('--agent-color', RACE_COLORS[i % RACE_COLORS.length]);
      btn.onclick = () => {
        if (raceVisible.has(a.id)) { raceVisible.delete(a.id); btn.classList.remove('on'); }
        else { raceVisible.add(a.id); btn.classList.add('on'); }
        drawRaceChart(top10, snapshotList);
      };
      toggleRow.appendChild(btn);
    });
  }

  // Get snapshots for data
  const snaps = await apiFetch('/simulation/snapshots');
  if (!snaps || !snaps.length) {
    clearChart('raceChart');
    return;
  }
  drawRaceChart(top10, snaps);
}

async function drawRaceChart(top10, snaps) {
  // For each snapshot day, get agent summaries
  // Snapshots basic list has: {day, trades, events}
  // We need to fetch details per day — sample max 20 to avoid overload
  const days = snaps.map(s => s.day);
  const sampleDays = days.filter((_, i) => i === 0 || i === days.length - 1 || i % Math.max(1, Math.floor(days.length / 18)) === 0);

  const dayData = {};
  await Promise.all(sampleDays.map(async (day) => {
    const d = await apiFetch(`/simulation/snapshots/${day}`);
    if (d) dayData[day] = d;
  }));

  const sortedDays = Object.keys(dayData).map(Number).sort((a, b) => a - b);
  const labels = sortedDays.map(d => `Day ${d}`);

  const datasets = [];
  top10.forEach((a, i) => {
    if (!raceVisible.has(a.id)) return;
    const color = RACE_COLORS[i % RACE_COLORS.length];
    const data = sortedDays.map(day => {
      const snap = dayData[day];
      if (!snap || !snap.agent_summaries) return null;
      const sum = snap.agent_summaries.find(s => s.id === a.id || s.name === a.name);
      return sum ? (sum.total_value ?? sum.value ?? null) : null;
    });
    datasets.push({
      label: a.name,
      data,
      borderColor: color,
      backgroundColor: 'transparent',
      borderWidth: 2,
      pointRadius: 3,
      pointBackgroundColor: color,
      tension: 0.3,
      spanGaps: true,
    });
  });

  clearChart('raceChart');
  if (!datasets.length) return;
  const ctx = document.getElementById('raceChart').getContext('2d');
  chartInstances.raceChart = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { labels: { color: '#aaa', font: { family: 'JetBrains Mono', size: 10 }, boxWidth: 12 } } },
      scales: {
        x: { ticks: { color: '#555', font: { family: 'JetBrains Mono', size: 9 } }, grid: { color: '#1a1a1a' } },
        y: { ticks: { color: '#aaa', font: { family: 'JetBrains Mono', size: 10 }, callback: v => '$' + (v/1000).toFixed(0) + 'k' }, grid: { color: '#1a1a1a' } }
      }
    }
  });
}

const TOUR_STEPS = [
  {
    title: "Welcome to StockAI",
    text: "A fully simulated stock market driven by AI agents. Prices move, events fire, agents trade — you control the clock.",
    target: null
  },
  {
    title: "Simulation Controls",
    text: "Start, Pause, or Reset the entire world from here. You can also speed up time or jump ahead by days.",
    target: ".sidebar-controls"
  },
  {
    title: "Live Metrics",
    text: "Monitor the health of the market, total trades, and active agents in real-time.",
    target: ".grid-6"
  },
  {
    title: "Activity Feeds",
    text: "Every agent decision and market event is logged here. Watch the narrative of the market unfold.",
    target: ".grid-4"
  },
  {
    title: "Neural Network",
    text: "This live graph shows how agents are connected and how their sentiment influences each other.",
    target: "#neural-container"
  },
  {
    title: "Agent Analysis",
    text: "Detailed breakdown of every agent's portfolio, logic, and recent trades.",
    target: "#page-agents"
  },
  {
    title: "Mood Engine",
    text: "The global market sentiment is tracked here. You can toggle the autonomous engine on/off.",
    target: "#marketMoodLabel"
  },
  {
    title: "Voice Briefing",
    text: "Click the shield icon for an immersive audio breakdown of the current market state.",
    target: "#voiceBriefingContainer"
  },
  {
    title: "Ready to Start?",
    text: "Hit the Play button to begin the simulation. Good luck, Commander.",
    target: "#btn-start"
  }
];



/* ═══════════════════════════════════════════
   NOTIFICATION SYSTEM
═══════════════════════════════════════════ */
let notifications = [];
let notifPanelOpen = false;

function pushNotif(icon, title, sub, color = 'var(--yellow)') {
  notifications.unshift({ icon, title, sub, color, time: Date.now() });
  if (notifications.length > 50) notifications.pop();
  renderNotifPanel();
  // Flash toast for high-priority
  toast(`${icon} ${title}`, color);
}

function renderNotifPanel() {
  const badge = document.getElementById('notif-badge');
  const list  = document.getElementById('notif-list');
  if (badge) {
    badge.textContent = notifications.length;
    badge.style.display = notifications.length ? 'flex' : 'none';
  }
  if (!list) return;
  if (!notifications.length) {
    list.innerHTML = '<div class="notif-empty">No alerts yet.</div>';
    return;
  }
  list.innerHTML = notifications.map(n => `
    <div class="notif-item">
      <div class="notif-item-icon">${n.icon}</div>
      <div class="notif-item-body">
        <div class="notif-item-title" style="color:${n.color}">${escHtml(n.title)}</div>
        <div class="notif-item-sub">${escHtml(n.sub)}</div>
      </div>
    </div>`).join('');
}

function toggleNotifPanel() {
  notifPanelOpen = !notifPanelOpen;
  document.getElementById('notif-panel').classList.toggle('open', notifPanelOpen);
}

function clearNotifs() {
  notifications = [];
  renderNotifPanel();
}

// Close notif panel on outside click
document.addEventListener('click', e => {
  const wrap = document.querySelector('.notif-bell-wrap');
  if (wrap && !wrap.contains(e.target) && notifPanelOpen) {
    notifPanelOpen = false;
    document.getElementById('notif-panel').classList.remove('open');
  }
});

// Hook notifications into existing tick handler
const _origHandleTick = handleTick;
handleTick = function(d) {
  // Circuit breaker alerts
  const prevHalted = new Set(halted);
  _origHandleTick(d);
  (d.halted || []).forEach(sym => {
    if (!prevHalted.has(sym)) {
      pushNotif('⚡', `Circuit Breaker: ${sym}`, `${allStocks[sym]?.name || sym} halted — >10% move this session`, 'var(--orange)');
    }
  });
  // Major events
  (d.events || []).forEach(ev => {
    if (ev.severity === 'high') {
      pushNotif('!', ev.title, `Severity: HIGH | Day ${d.day}`, 'var(--red)');
    }
  });
  // Price alerts
  if (d.prices) checkPriceAlerts(d.prices);
};

// Agent bankruptcy watcher (poll-based)
let prevAgentStatuses = {};
async function watchAgentStatuses() {
  const data = await apiFetch('/agents');
  if (!data) return;
  data.forEach(a => {
    const prev = prevAgentStatuses[a.id];
    if (prev && prev !== a.status && a.status === 'bankrupt') {
      pushNotif('✕', `${a.name} went bankrupt!`, `Day ${state.day} — Total value: ${fmtMoney(a.total_value)}`, 'var(--red)');
    }
    prevAgentStatuses[a.id] = a.status;
  });
}
setInterval(watchAgentStatuses, 8000);

/* ═══════════════════════════════════════════
   ONBOARDING TOUR
═══════════════════════════════════════════ */


let _tourStep = 0;
let _tourPrevTarget = null;

function tourStart() {
  _tourStep = 0;
  _tourPrevTarget = null;
  document.getElementById('tour-overlay').classList.add('active');
  document.getElementById('tour-box').style.display = 'block';
  _buildTourDots();
  _renderTourStep();
}

function tourEnd() {
  document.getElementById('tour-overlay').classList.remove('active');
  document.getElementById('tour-box').style.display = 'none';
  if (_tourPrevTarget) { _tourPrevTarget.classList.remove('tour-highlight'); _tourPrevTarget = null; }
  localStorage.setItem('stockai_tour_done', '1');
}

function tourNext() {
  _tourStep++;
  if (_tourStep >= TOUR_STEPS.length) { tourEnd(); return; }
  _renderTourStep();
}

function _buildTourDots() {
  const dots = document.getElementById('tour-dots');
  dots.innerHTML = TOUR_STEPS.map((_, i) =>
    `<div class="tour-dot" id="tdot-${i}"></div>`
  ).join('');
}

function _renderTourStep() {
  const step = TOUR_STEPS[_tourStep];

  // Un-highlight previous target
  if (_tourPrevTarget) { _tourPrevTarget.classList.remove('tour-highlight'); _tourPrevTarget = null; }

  // Update text
  document.getElementById('tour-step-num').textContent = `Step ${_tourStep + 1} of ${TOUR_STEPS.length}`;
  document.getElementById('tour-title').textContent = step.title;
  document.getElementById('tour-text').textContent  = step.text;
  document.getElementById('tour-next-btn').textContent =
    _tourStep === TOUR_STEPS.length - 1 ? 'Get started ✓' : 'Next →';

  // Dots
  document.querySelectorAll('.tour-dot').forEach((d, i) =>
    d.classList.toggle('active', i === _tourStep)
  );

  // Position tooltip
  const box = document.getElementById('tour-box');
  if (!step.target) {
    // Centred
    box.style.top  = '50%';
    box.style.left = '50%';
    box.style.transform = 'translate(-50%, -50%)';
    return;
  }
  box.style.transform = '';

  const el = document.querySelector(step.target);
  if (!el) { box.style.top = '50%'; box.style.left = '50%'; box.style.transform = 'translate(-50%,-50%)'; return; }

  // Highlight target
  el.classList.add('tour-highlight');
  _tourPrevTarget = el;
  el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });

  // Position box next to target (prefer right, then left, then below)
  const r = el.getBoundingClientRect();
  const bw = 326, bh = 200; // approx box size
  const vw = window.innerWidth, vh = window.innerHeight;
  const margin = 18;

  let top, left;
  if (r.right + bw + margin < vw) {
    // Right
    left = r.right + margin;
    top  = Math.max(margin, Math.min(r.top + r.height / 2 - bh / 2, vh - bh - margin));
  } else if (r.left - bw - margin > 0) {
    // Left
    left = r.left - bw - margin;
    top  = Math.max(margin, Math.min(r.top + r.height / 2 - bh / 2, vh - bh - margin));
  } else if (r.bottom + bh + margin < vh) {
    // Below
    top  = r.bottom + margin;
    left = Math.max(margin, Math.min(r.left + r.width / 2 - bw / 2, vw - bw - margin));
  } else {
    // Above
    top  = r.top - bh - margin;
    left = Math.max(margin, Math.min(r.left + r.width / 2 - bw / 2, vw - bw - margin));
  }

  box.style.top  = top  + 'px';
  box.style.left = left + 'px';
}

// Click overlay to advance
document.getElementById('tour-overlay').addEventListener('click', () => tourNext());

// Auto-start on first visit
if (!localStorage.getItem('stockai_tour_done')) {
  // Delay so the page has rendered and allStocks is populated
  setTimeout(tourStart, 800);
}

document.addEventListener('keydown', e => {
  const tag = e.target.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
  if (e.code === 'Space')  { e.preventDefault(); simPause(); }
  if (e.key  === '1')      { nav('dashboard'); }
  if (e.key  === '2')      { nav('analysis'); }
  if (e.key  === '3')      { nav('agents'); }
  if (e.key  === '4')      { nav('explainability'); }
  if (e.key  === '5')      { nav('settings'); }
  if (e.key  === 'r' || e.key === 'R') { simReset(); }
  if (e.key  === 'c' || e.key === 'C') { toggleChat(); }
});

/* ═══════════════════════════════════════════
   SIDEBAR SPEED CONTROL
═══════════════════════════════════════════ */
async function setSidebarSpeed(val) {
  // Sync with settings dropdown too
  const cfgSpd = document.getElementById('cfg-speed');
  if (cfgSpd) cfgSpd.value = val;
  await apiPost('/simulation/config', { });
  // Speed takes effect on next start; just show confirmation
  toast(`Speed set to ${val}x`, 'var(--cyan)');
}

/* ═══════════════════════════════════════════
   PRICE ALERTS
═══════════════════════════════════════════ */
function openAlertsPanel() {
  const panel = document.getElementById('alerts-panel');
  panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
}

function addPriceAlert() {
  const sym = document.getElementById('alert-sym').value;
  const dir = document.getElementById('alert-dir').value;
  const target = parseFloat(document.getElementById('alert-price').value);
  if (!sym || isNaN(target) || target <= 0) { toast('Select a stock and enter a target price', 'var(--red)'); return; }
  priceAlerts.push({ sym, dir, target, id: Date.now() });
  document.getElementById('alert-price').value = '';
  renderAlertRules();
  toast(`Alert set: ${sym} ${dir === 'above' ? '>' : '<'} ${fmtMoney(target)}`, 'var(--yellow)');
}

function removePriceAlert(id) {
  priceAlerts = priceAlerts.filter(a => a.id !== id);
  renderAlertRules();
}

function renderAlertRules() {
  const list = document.getElementById('alert-rules-list');
  const badge = document.getElementById('alert-badge-count');
  if (badge) badge.textContent = priceAlerts.length ? `(${priceAlerts.length})` : '';
  if (!priceAlerts.length) {
    list.innerHTML = '<div class="empty" style="padding:12px">No alerts set.</div>';
    return;
  }
  list.innerHTML = priceAlerts.map(a => `
    <div class="alert-rule">
      <strong style="color:var(--cyan);min-width:32px">${escHtml(allStocks[a.sym]?.name || a.sym)}</strong>
      <span style="color:var(--muted)">${a.dir === 'above' ? 'rises above' : 'falls below'}</span>
      <strong style="color:var(--yellow)">${fmtMoney(a.target)}</strong>
      <span style="color:var(--muted);font-size:10px">(now ${fmtMoney(allStocks[a.sym]?.price)})</span>
      <button onclick="removePriceAlert(${a.id})" style="margin-left:auto">×</button>
    </div>`).join('');
}

function checkPriceAlerts(prices) {
  priceAlerts = priceAlerts.filter(a => {
    const cur = prices[a.sym];
    if (cur == null) return true;
    const hit = a.dir === 'above' ? cur >= a.target : cur <= a.target;
    if (hit) {
      toast(`Alert: ${a.sym} ${a.dir === 'above' ? '>' : '<'} ${fmtMoney(a.target)} (now ${fmtMoney(cur)})`, 'var(--yellow)');
      pushNotif('$', `Price Alert: ${a.sym}`, `${a.dir === 'above' ? 'Rose above' : 'Fell below'} ${fmtMoney(a.target)} — now ${fmtMoney(cur)}`, 'var(--yellow)');
      return false; // remove triggered alert
    }
    return true;
  });
  renderAlertRules();
}

/* ═══════════════════════════════════════════
   EVENT TEMPLATES
═══════════════════════════════════════════ */
const EVENT_TEMPLATES = {
  'market-crash':     { title: 'Market Crash', description: 'Panic selling erupts as confidence collapses.', severity: 'high',   impact: -18, stocks: '' },
  'bull-run':         { title: 'Bull Run',     description: 'Euphoric buying wave sweeps the market upward.', severity: 'medium', impact:  15, stocks: '' },
  'earnings-beat':    { title: 'Earnings Beat (Tech)', description: 'Major tech firms report record profits.', severity: 'medium', impact:  12, stocks: 'AAPL,MSFT,NVDA,AMZN,GOOGL' },
  'flash-crash':      { title: 'Flash Crash',  description: 'Algorithmic cascade triggers instant sell-off.', severity: 'high',   impact: -30, stocks: '' },
  'sector-rotation':  { title: 'Sector Rotation', description: 'Funds rotate from tech into energy.', severity: 'medium', impact: -8, stocks: 'AAPL,MSFT,NVDA,AMZN,GOOGL' },
  'bear-trap':        { title: 'Bear Trap',    description: 'False breakdown reverses into powerful rally.', severity: 'medium', impact:  8, stocks: '' },
};

function fillEventTemplate(key) {
  const t = EVENT_TEMPLATES[key];
  if (!t) return;
  document.getElementById('ev-title').value       = t.title;
  document.getElementById('ev-desc').value        = t.description;
  document.getElementById('ev-sev').value         = t.severity;
  document.getElementById('ev-impact').value      = t.impact;
  document.getElementById('ev-stocks').value      = t.stocks;
  toast(`Template loaded: ${t.title}`, 'var(--magenta)');
}

/* ═══════════════════════════════════════════
   CSV EXPORTS
═══════════════════════════════════════════ */
function downloadCSV(filename, rows, headers) {
  const escape = v => {
    if (v == null) return '';
    const s = String(v);
    return s.includes(',') || s.includes('"') || s.includes('\n') ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const csv = [headers, ...rows].map(r => r.map(escape).join(',')).join('\n');
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
  toast(`${filename} downloaded`, 'var(--cyan)');
}

function exportAgentsCSV() {
  if (!agents.length) { toast('No agent data yet', 'var(--red)'); return; }
  const sorted = [...agents].sort((a, b) => b.total_value - a.total_value);
  downloadCSV(
    `stockai_agents_day${state.day}.csv`,
    sorted.map(a => [a.name, a.character_type, a.agent_kind, a.total_value, a.pnl, a.pnl_pct, a.trades, a.cash, a.debt, a.status]),
    ['Name','Type','Kind','Total Value','PnL','PnL%','Trades','Cash','Debt','Status']
  );
}

async function exportTradesCSV() {
  const data = await apiFetch('/market/trades');
  if (!data || !data.length) { toast('No trades yet', 'var(--red)'); return; }
  downloadCSV(
    `stockai_trades_day${state.day}.csv`,
    data.map(t => [t.day, t.session, t.stock, t.buyer, t.seller, t.price, t.quantity]),
    ['Day','Session','Stock','Buyer','Seller','Price','Quantity']
  );
}

function exportStocksCSV() {
  const stocks = Object.entries(allStocks);
  if (!stocks.length) { toast('No stock data yet', 'var(--red)'); return; }
  downloadCSV(
    `stockai_stocks_day${state.day}.csv`,
    stocks.map(([sym, s]) => [
      sym, s.name, s.sector, s.price, s.initial_price,
      s.initial_price ? ((s.price - s.initial_price) / s.initial_price * 100).toFixed(2) : 0,
      s.volatility, halted.includes(sym) ? 'halted' : 'active'
    ]),
    ['Symbol','Name','Sector','Price','Initial Price','Change%','Volatility','Status']
  );
}

/* ═══════════════════════════════════════════
   AGENT COMPARISON
═══════════════════════════════════════════ */
function toggleCompare(id, checkbox) {
  if (checkbox.checked) {
    if (selectedForCompare.size >= 2) {
      checkbox.checked = false;
      toast('Select exactly 2 agents to compare', 'var(--yellow)');
      return;
    }
    selectedForCompare.add(id);
  } else {
    selectedForCompare.delete(id);
  }
  if (selectedForCompare.size === 2) renderComparePanel();
  else document.getElementById('compare-panel').style.display = 'none';
}

function clearComparison() {
  selectedForCompare.clear();
  document.getElementById('compare-panel').style.display = 'none';
  // Uncheck all checkboxes
  document.querySelectorAll('.cmp-checkbox').forEach(cb => cb.checked = false);
}

function renderComparePanel() {
  const ids = [...selectedForCompare];
  const [a1, a2] = ids.map(id => agents.find(a => a.id === id)).filter(Boolean);
  if (!a1 || !a2) return;

  const panel = document.getElementById('compare-panel');
  const body  = document.getElementById('cmp-agents-body');
  panel.style.display = 'block';

  const metrics = [
    ['Total Value', fmtMoney(a1.total_value), fmtMoney(a2.total_value), a1.total_value > a2.total_value],
    ['PnL', fmtMoney(a1.pnl), fmtMoney(a2.pnl), a1.pnl > a2.pnl],
    ['PnL%', fmtPct(a1.pnl_pct), fmtPct(a2.pnl_pct), a1.pnl_pct > a2.pnl_pct],
    ['Trades', a1.trades, a2.trades, a1.trades > a2.trades],
    ['Cash', fmtMoney(a1.cash), fmtMoney(a2.cash), a1.cash > a2.cash],
    ['Debt', fmtMoney(a1.debt || 0), fmtMoney(a2.debt || 0), (a1.debt || 0) < (a2.debt || 0)],
    ['Kind', a1.agent_kind?.toUpperCase() || '—', a2.agent_kind?.toUpperCase() || '—', null],
  ];

  const winStyle  = 'color:var(--lime);font-weight:800';
  const loseStyle = 'color:var(--muted)';

  body.innerHTML = `
    <div class="cmp-col">
      <div class="cmp-col-name">${escHtml(a1.name)}<br><span style="color:var(--muted);font-size:10px;font-weight:400">${escHtml(a1.character_type)}</span></div>
      ${metrics.map(([, v1, , w1]) => `<div class="cmp-row"><span class="cmp-label"> </span><span class="cmp-val" style="${w1 === null ? '' : w1 ? winStyle : loseStyle}">${v1}</span></div>`).join('')}
    </div>
    <div class="cmp-vs">
      ${metrics.map(([label]) => `<div style="padding:5px 0;border-bottom:1px solid var(--border);font-size:9px;text-align:center;color:var(--muted)">${label}</div>`).join('')}
    </div>
    <div class="cmp-col">
      <div class="cmp-col-name" style="text-align:right">${escHtml(a2.name)}<br><span style="color:var(--muted);font-size:10px;font-weight:400">${escHtml(a2.character_type)}</span></div>
      ${metrics.map(([, , v2, w1]) => `<div class="cmp-row" style="flex-direction:row-reverse"><span class="cmp-label"> </span><span class="cmp-val" style="${w1 === null ? '' : !w1 ? winStyle : loseStyle}">${v2}</span></div>`).join('')}
    </div>`;
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── CUSTOM CURSOR ──
const cursorOuter = document.getElementById('customCursorOuter');
const cursorInner = document.getElementById('customCursorInner');
let curX = 0, curY = 0, targetX = 0, targetY = 0;

window.addEventListener('mousemove', e => {
    targetX = e.clientX;
    targetY = e.clientY;
});

function animateCursor() {
    curX += (targetX - curX) * 0.15;
    curY += (targetY - curY) * 0.15;
    cursorOuter.style.transform = `translate(${curX}px, ${curY}px)`;
    cursorInner.style.transform = `translate(${targetX}px, ${targetY}px)`;
    requestAnimationFrame(animateCursor);
}
animateCursor();

document.querySelectorAll('a, button, [onclick], .nav-link, .ctrl-btn, .quickrun-btn').forEach(el => {
    el.addEventListener('mouseenter', () => cursorOuter.classList.add('hover'));
    el.addEventListener('mouseleave', () => cursorOuter.classList.remove('hover'));
});

window.addEventListener('mousedown', () => cursorOuter.classList.add('click'));
window.addEventListener('mouseup', () => cursorOuter.classList.remove('click'));


/* ═══════════════════════════════════════════
   FEATURE 7 & 8: LIVE TICK INTERCEPT
═══════════════════════════════════════════ */
const _f7_oldPrices = new Map();
let _f8_lastRegime = null;

// We intercept handleTick without modifying the core function structure
const _base_handleTick = handleTick;
handleTick = function(d) {
  _base_handleTick(d);

  // FEATURE 8: Regime Banner
  if (d.regime && d.regime !== _f8_lastRegime) {
    if (_f8_lastRegime !== null) { 
      showRegimeBanner(d.regime);
    }
    _f8_lastRegime = d.regime;
  }

  // FEATURE 7: Flash Prices
  if (d.prices) {
    for (const [sym, price] of Object.entries(d.prices)) {
      const oldPrice = _f7_oldPrices.get(sym);
      if (oldPrice !== undefined && price !== oldPrice) {
        const cls = price > oldPrice ? 'flash-price-up' : 'flash-price-down';
        
        // Find tracking elements and apply flash
        const els = document.querySelectorAll(`[data-price-sym="${sym}"]`);
        els.forEach(el => {
          el.textContent = fmtMoney(price); // ensure text is updated instantly
          el.classList.remove('flash-price-up', 'flash-price-down', 'flash-transition');
          void el.offsetWidth; // trigger reflow
          el.classList.add(cls);
          setTimeout(() => {
            el.classList.add('flash-transition');
            el.classList.remove(cls);
          }, 50);
        });
      }
      _f7_oldPrices.set(sym, price);
    }
  }
};

function showRegimeBanner(newRegime) {
  let banner = document.getElementById('regime-banner');
  if (!banner) {
    banner = document.createElement('div');
    banner.id = 'regime-banner';
    document.body.appendChild(banner);
  }
  
  const formatted = newRegime.replace(/_/g, ' ').toUpperCase();
  const icon = newRegime.includes('bull') ? '🐂' : newRegime.includes('bear') ? '🐻' : newRegime.includes('crash') ? '📉' : '⚡';
  
  banner.innerHTML = `<span class="regime-icon">${icon}</span> REGIME SHIFT DETECTED: <span style="color:var(--cyan)">${formatted}</span>`;
  
  // Slide down
  banner.classList.add('show');
  
  // Auto-dismiss
  setTimeout(() => {
    banner.classList.remove('show');
  }, 4000);
}


/* ═══════════════════════════════════════════
   FEATURE 9: SESSION STORAGE CHAT OVERRIDE
═══════════════════════════════════════════ */
sendChat = async function() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';

  appendMsg('user', msg);
  const ctx = buildChatContext();
  
  let hist = [];
  try { hist = JSON.parse(sessionStorage.getItem('chatLog') || '[]'); } catch(e){}
  hist.push({role: 'user', content: msg});
  sessionStorage.setItem('chatLog', JSON.stringify(hist.slice(-20)));

  const r = await apiPost('/chat', { message: msg + ' ' + ctx, history: hist });
  if (r) {
    const followups = Array.isArray(r.suggested_followup)
      ? r.suggested_followup
      : (r.suggested_followup ? [r.suggested_followup] : []);
    appendMsg('bot', r.response || 'NO RESPONSE', followups);
    
    // Write bot back to history
    hist.push({role: 'assistant', content: r.response});
    sessionStorage.setItem('chatLog', JSON.stringify(hist.slice(-20)));
  } else {
    appendMsg('bot', 'Sorry, I could not reach the assistant right now.');
  }
};

setTimeout(() => {
  let hist = [];
  try { hist = JSON.parse(sessionStorage.getItem('chatLog') || '[]'); } catch(e){}
  if (hist.length > 0) {
    const container = document.getElementById('chat-messages');
    if(container) container.innerHTML = '';
    hist.forEach(h => {
      appendMsg(h.role === 'user' ? 'user' : 'bot', h.content || '', []);
    });
  }
}, 500);

/* ═══════════════════════════════════════════
   FEATURE 12: KEYBOARD SHORTCUTS
═══════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  const kbd = document.getElementById('kbdMap');
  let qTimer = null;
  let gPressed = false;
  
  document.addEventListener('keydown', e => {
    if(e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
      if(e.key === 'Escape' && chatOpen) {
        e.preventDefault();
        toggleChat();
        e.target.blur();
      }
      return;
    }
    
    if(e.key === '?') {
      if(!qTimer) {
        qTimer = setTimeout(() => { if(kbd) kbd.style.display = 'block'; }, 500);
      }
    }
    if(e.key.toLowerCase() === 'g') {
      gPressed = true;
      setTimeout(() => { gPressed = false; }, 1000);
    }
    if(gPressed) {
      const char = e.key.toLowerCase();
      if(char === 's') window.location.href = '/app';
      if(char === 'w') window.location.href = '/workspace';
      if(char === 'l') window.location.href = '/live-market';
      if(char === 'h') window.location.href = '/';
    }
    if(e.key === '/') {
      e.preventDefault();
      if (!chatOpen) toggleChat();
      setTimeout(() => {
        const inp = document.getElementById('chat-input');
        if(inp) inp.focus();
      }, 100);
    }
  });

  document.addEventListener('keyup', e => {
    if(e.key === '?') {
      clearTimeout(qTimer);
      qTimer = null;
      if(kbd) kbd.style.display = 'none';
    }
  });
});

/* ═══════════════════════════════════════════
   SIMULATION REPLAY FEATURE
═══════════════════════════════════════════ */
let replayEvents = [];
let replayTimeline = [];
let replayIsPlaying = false;
let replaySpeed = 2;
let replayStepIndex = 0;
let replayTimer = null;

async function loadReplayPage() {
    const runId = activeRunId || state.run_id;
    if (!runId) {
        showReplayUI(false, "NO ACTIVE RUN DETECTED. START A SIMULATION FIRST.");
        return;
    }
    
    // Fetch replay data
    toast("Loading replay timeline...", "var(--cyan)");
    const data = await apiFetch(`/runs/${runId}/replay`);
    if (!data || data.length === 0) {
        showReplayUI(false, "THIS RUN WAS RECORDED BEFORE REPLAY SUPPORT WAS ADDED. START A NEW SIMULATION TO USE REPLAY.");
        return;
    }
    
    handleReplayData(data);
}

function showReplayUI(hasData, errorMsg = "") {
    const emptyState = document.getElementById('replay-empty-state');
    const mainContent = document.getElementById('replay-main-content');
    
    if (hasData) {
        emptyState.style.display = 'none';
        mainContent.style.display = 'block';
    } else {
        emptyState.style.display = 'block';
        mainContent.style.display = 'none';
        if (errorMsg) {
            emptyState.querySelector('p').textContent = errorMsg;
        }
    }
}

function handleReplayData(events) {
    replayEvents = events;
    
    // Build timeline from market_snapshots and phase transitions
    const steps = [];
    const seen = new Set();
    
    events.forEach(ev => {
        if (ev.event_type === 'market_snapshot' || ev.event_type === 'phase_start') {
            const phase = ev.event_type === 'market_snapshot' ? 'snapshot' : (ev.payload?.phase || 'start');
            const key = `${ev.day}-${ev.session}-${phase}`;
            if (!seen.has(key)) {
                steps.push({
                    day: ev.day,
                    session: ev.session,
                    phase: phase,
                    timestamp: ev.created_at,
                    snapshot: ev.event_type === 'market_snapshot' ? ev.payload : null
                });
                seen.add(key);
            }
        }
    });
    
    // Sort steps by day, session
    steps.sort((a, b) => a.day !== b.day ? a.day - b.day : a.session - b.session);
    
    if (steps.length === 0) {
        showReplayUI(false, "THIS RUN WAS RECORDED BEFORE REPLAY SUPPORT WAS ADDED. START A NEW SIMULATION TO USE REPLAY.");
        return;
    }

    replayTimeline = steps;
    showReplayUI(true);
    
    const scrubber = document.getElementById('replay-scrubber');
    scrubber.max = steps.length - 1;
    scrubber.value = 0;
    
    replayStepIndex = 0;
    renderReplayStep(0);
}

function scrubReplay(val) {
    replayStepIndex = parseInt(val);
    renderReplayStep(replayStepIndex);
}

function toggleReplayPlayback() {
    replayIsPlaying = !replayIsPlaying;
    const btn = document.getElementById('replay-play-btn');
    btn.textContent = replayIsPlaying ? "⏸ Pause" : "▶ Play";
    if (replayIsPlaying) playNextReplayStep();
}

function setReplaySpeed(val) {
    replaySpeed = parseInt(val);
}

function playNextReplayStep() {
    if (!replayIsPlaying) return;
    if (replayStepIndex >= replayTimeline.length - 1) {
        replayIsPlaying = false;
        document.getElementById('replay-play-btn').textContent = "▶ Play";
        return;
    }
    
    replayStepIndex++;
    document.getElementById('replay-scrubber').value = replayStepIndex;
    renderReplayStep(replayStepIndex);
    
    setTimeout(playNextReplayStep, 1000 / replaySpeed);
}

function renderReplayStep(idx) {
    const step = replayTimeline[idx];
    if (!step) return;
    
    document.getElementById('replay-step-label').textContent = `${idx + 1} / ${replayTimeline.length}`;
    document.getElementById('replay-day-val').textContent = step.day;
    document.getElementById('replay-session-val').textContent = step.session;
    document.getElementById('replay-phase-val').textContent = step.phase;
    
    // Find the latest snapshot up to this point
    let lastSnap = step.snapshot;
    if (!lastSnap) {
        for (let i = idx; i >= 0; i--) {
            if (replayTimeline[i].snapshot) {
                lastSnap = replayTimeline[i].snapshot;
                break;
            }
        }
    }
    
    // 1. Render Prices
    const priceTable = document.getElementById('replay-price-table').querySelector('tbody');
    priceTable.innerHTML = '';
    if (lastSnap && lastSnap.prices) {
        Object.entries(lastSnap.prices).forEach(([sym, p]) => {
            priceTable.innerHTML += `<tr>
                <td><strong>${sym}</strong></td>
                <td style="color:var(--cyan)">${fmtMoney(p)}</td>
                <td style="color:var(--muted);font-size:10px">${lastSnap.regime || '—'}</td>
            </tr>`;
        });
    } else {
        priceTable.innerHTML = '<tr><td colspan="3" class="empty">No price data at this step</td></tr>';
    }
    
    // 2. Filter Events and Decisions for this specific day/session
    const currentEvents = replayEvents.filter(e => e.day === step.day && e.session === step.session);
    
    // 3. Render Decisions feed
    const decisionFeed = document.getElementById('replay-decision-feed');
    decisionFeed.innerHTML = '';
    const decisions = currentEvents.filter(e => e.event_type === 'agent_decision');
    if (decisions.length) {
        decisions.forEach(d => {
            const p = d.payload;
            const sideCls = p.action === 'BUY' ? 'buy' : p.action === 'SELL' ? 'sell' : 'hold';
            decisionFeed.innerHTML += `<div class="feed-item">
                <div class="feed-item-header">
                    <span class="badge ${sideCls}">${p.action}</span>
                    <span class="feed-item-name">${escHtml(p.agent_name)}</span>
                    <span class="feed-item-day">${p.stock}</span>
                </div>
                <div class="feed-item-body" style="font-size:11px;color:var(--muted)">${escHtml(p.reasoning)}</div>
                <div class="feed-item-sub">Qty: ${p.quantity} | P: ${fmtMoney(p.price)}</div>
            </div>`;
        });
    } else {
        decisionFeed.innerHTML = '<div class="empty">No decisions recorded in this session</div>';
    }
    
    // 4. Render Sentiment Heatbars
    const sentimentGrid = document.getElementById('replay-sentiment-grid');
    sentimentGrid.innerHTML = '';
    if (decisions.length) {
        const agentSentiment = {};
        decisions.forEach(d => {
            agentSentiment[d.payload.agent_name] = d.payload.bias;
        });
        
        Object.entries(agentSentiment).forEach(([name, bias]) => {
            const hasBias = bias !== undefined && bias !== null;
            const bVal = hasBias ? bias : 0;
            const color = !hasBias ? '#444' : (bVal > 0 ? `rgba(74,222,128,${Math.abs(bVal)})` : `rgba(248,113,113,${Math.abs(bVal)})`);
            
            sentimentGrid.innerHTML += `<div>
                <div style="display:flex;justify-content:space-between;font-size:10px;margin-bottom:2px">
                    <span>${escHtml(name)}</span>
                    <span>${hasBias ? bVal.toFixed(2) : 'N/A'}</span>
                </div>
                <div style="height:4px;background:#222;border-radius:2px;overflow:hidden">
                    <div style="height:100%;width:${(hasBias ? Math.abs(bVal) : 1) * 100}%;background:${color};margin-left:${bVal < 0 ? 0 : 'auto'}"></div>
                </div>
            </div>`;
        });
    } else {
        sentimentGrid.innerHTML = '<div class="empty">No sentiment data</div>';
    }
    
    // 5. Render Events log
    const eventFeed = document.getElementById('replay-event-feed');
    eventFeed.innerHTML = '';
    const logs = currentEvents.filter(e => !['market_snapshot', 'agent_decision', 'phase_start'].includes(e.event_type));
    if (logs.length) {
        logs.forEach(l => {
            const hasImage = ['monetary_policy', 'earnings', 'macro', 'corporate', 'regulation'].includes(l.event_type);
            const imgHtml = hasImage ? `<img src="/assets/events/${l.event_type}.png" style="width:100%; height:60px; object-fit:cover; border-radius:4px; margin-bottom:4px; border:1px solid var(--border); opacity:0.8">` : '';
            
            eventFeed.innerHTML += `<div class="feed-item" style="padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.05)">
                ${imgHtml}
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px">
                    <span style="color:var(--lime); font-size:9px; font-family:var(--mono)">[${l.event_type.toUpperCase().replace('_', ' ')}]</span>
                    <span style="color:var(--muted); font-size:9px">${new Date().toLocaleTimeString()}</span>
                </div>
                <div style="font-size:11px; line-height:1.4">${escHtml(typeof l.payload === 'string' ? l.payload : (l.payload.title || JSON.stringify(l.payload).slice(0, 60)))}</div>
            </div>`;
        });
    } else {
        eventFeed.innerHTML = '<div class="empty">No other events recorded</div>';
    }
}


// ── CUSTOM CURSOR ──
document.addEventListener('DOMContentLoaded', () => {
    const cursorOuter = document.getElementById('customCursorOuter');
    const cursorInner = document.getElementById('customCursorInner');
    let curX = window.innerWidth / 2, curY = window.innerHeight / 2;
    let targetX = curX, targetY = curY;

    window.addEventListener('mousemove', e => {
        targetX = e.clientX;
        targetY = e.clientY;
    });

    function animateCursor() {
        curX += (targetX - curX) * 0.15;
        curY += (targetY - curY) * 0.15;
        cursorOuter.style.transform = `translate(${curX}px, ${curY}px)`;
        cursorInner.style.transform = `translate(${targetX}px, ${targetY}px)`;
        document.documentElement.classList.add('custom-cursor-active');
        requestAnimationFrame(animateCursor);
    }
    animateCursor();

    const updateHovers = () => {
        document.querySelectorAll('a, button, [onclick], .nav-link, .ctrl-btn, .quickrun-btn').forEach(el => {
            if (el.dataset.cursorBound) return;
            el.dataset.cursorBound = "true";
            el.addEventListener('mouseenter', () => cursorOuter.classList.add('hover'));
            el.addEventListener('mouseleave', () => cursorOuter.classList.remove('hover'));
        });
    };
    updateHovers();
    setInterval(updateHovers, 1000);

    window.addEventListener('mousedown', () => cursorOuter.classList.add('click'));
    window.addEventListener('mouseup', () => cursorOuter.classList.remove('click'));
});


    document.addEventListener('DOMContentLoaded', () => {
       const header = document.querySelector('.inline-flex');
       if (header) {
         const container = document.createElement('div');
         container.style.cssText = 'display:inline-flex; align-items:center; margin-left:20px;';
         
         const moodLabel = document.createElement('span');
         moodLabel.id = 'marketMoodLabel';
         moodLabel.style.cssText = 'font-family:var(--mono); font-size:10px; border:1px solid var(--border); padding:2px 8px; border-radius:4px; vertical-align:middle; text-transform:uppercase;';
         moodLabel.textContent = 'NEUTRAL';
         
         const toggleBtn = document.createElement('button');
         toggleBtn.innerHTML = '⏻';
         toggleBtn.title = 'Toggle Mood Engine';
         toggleBtn.style.cssText = 'background:transparent; border:1px solid var(--border); color:var(--muted); font-size:10px; cursor:pointer; padding:2px 6px; border-radius:4px; margin-left:6px; vertical-align:middle; transition:all 0.2s;';
         toggleBtn.onclick = () => {
             const isOff = window.moodController.toggleMoodEngine();
             toggleBtn.style.color = isOff ? '#ef4e63' : 'var(--muted)';
             toggleBtn.style.borderColor = isOff ? '#ef4e63' : 'var(--border)';
         };
         
         // Initial state
         if (window.moodController.disabled) {
             toggleBtn.style.color = '#ef4e63';
             toggleBtn.style.borderColor = '#ef4e63';
         }
         
         container.appendChild(moodLabel);
         container.appendChild(toggleBtn);
         header.appendChild(container);
       }
     });
  

  // ── 3D BUBBLE ANIMATION ──
  (function() {
    const canvas = document.getElementById('bubbleCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let width, height, bubbles = [];

    function init() {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width;
      canvas.height = height;
      bubbles = [];
      for (let i = 0; i < 40; i++) {
        bubbles.push({
          x: Math.random() * width,
          y: Math.random() * height,
          r: 2 + Math.random() * 4,
          vx: (Math.random() - 0.5) * 0.5,
          vy: (Math.random() - 0.5) * 0.5,
          alpha: 0.1 + Math.random() * 0.3
        });
      }
    }

    function animate() {
      ctx.clearRect(0, 0, width, height);
      bubbles.forEach(b => {
        b.x += b.vx;
        b.y += b.vy;
        if (b.x < 0) b.x = width;
        if (b.x > width) b.x = 0;
        if (b.y < 0) b.y = height;
        if (b.y > height) b.y = 0;

        ctx.beginPath();
        ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(74, 222, 128, ${b.alpha})`;
        ctx.fill();
        
        // Connect nearby bubbles
        bubbles.forEach(b2 => {
          const dx = b.x - b2.x;
          const dy = b.y - b2.y;
          const dist = Math.sqrt(dx*dx + dy*dy);
          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(b.x, b.y);
            ctx.lineTo(b2.x, b2.y);
            ctx.strokeStyle = `rgba(74, 222, 128, ${(1 - dist/120) * 0.1})`;
            ctx.stroke();
          }
        });
      });
      requestAnimationFrame(animate);
    }

    window.addEventListener('resize', init);
    init();
    animate();
  })();
  