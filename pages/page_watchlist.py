"""
page_watchlist.py — Phase 3: Watchlist + Market Depth + Price Alerts + Multi-Chart
"""

HTML = r"""
<!-- ═══════════ PAGE: WATCHLIST ═══════════ -->
<div class="page" id="page-watchlist">
  <div class="topbar">
    <div style="display:flex;align-items:center;gap:10px;">
      <span style="font-family:Orbitron,sans-serif;font-size:1.1rem;color:var(--cyan);font-weight:700;letter-spacing:2px;">👁 WATCHLIST</span>
      <span class="page-tag">LIVE · DEPTH · ALERTS · MULTI-CHART</span>
    </div>
    <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;">LIVE MARKET MONITORING</div>
  </div>

  <!-- TAB NAV -->
  <div style="display:flex;gap:0;margin-bottom:20px;border-bottom:1px solid var(--border);">
    <button id="wl-tab-watchlist" onclick="wlTab('watchlist')"
      style="padding:8px 20px;background:rgba(41,98,255,0.12);border:1px solid var(--cyan);border-bottom:none;
             color:var(--cyan);font-family:Share Tech Mono,monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;">
      👁 WATCHLIST
    </button>
    <button id="wl-tab-depth" onclick="wlTab('depth')"
      style="padding:8px 20px;background:transparent;border:1px solid var(--border);border-bottom:none;
             color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;">
      📊 MARKET DEPTH
    </button>
    <button id="wl-tab-alerts" onclick="wlTab('alerts')"
      style="padding:8px 20px;background:transparent;border:1px solid var(--border);border-bottom:none;
             color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;">
      🔔 PRICE ALERTS
    </button>
    <button id="wl-tab-chart" onclick="wlTab('chart')"
      style="padding:8px 20px;background:transparent;border:1px solid var(--border);border-bottom:none;
             color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;">
      📉 MULTI-CHART
    </button>
  </div>

  <!-- ═══ WATCHLIST PANE ═══ -->
  <div id="watchlist-pane">
    <!-- Search + Add bar -->
    <div style="display:flex;gap:10px;align-items:center;margin-bottom:16px;">
      <div style="position:relative;flex:1;max-width:400px;">
        <input id="wl-search" type="text" placeholder="Search symbol to add (e.g. RELIANCE, TCS)..."
          style="width:100%;background:var(--p2);border:1px solid var(--border);border-radius:4px;
                 color:var(--white);padding:8px 12px 8px 36px;font-family:'JetBrains Mono',monospace;
                 font-size:0.82rem;outline:none;"
          oninput="wlFilterSymbols(this.value)"
          onkeydown="if(event.key==='Enter')addToWatchlist(document.getElementById('wl-search').value.toUpperCase().trim())">
        <span style="position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--dim);font-size:0.9rem;">🔍</span>
        <div id="wl-dropdown" style="display:none;position:absolute;top:100%;left:0;right:0;background:var(--panel);
             border:1px solid var(--border);border-top:none;border-radius:0 0 4px 4px;z-index:200;max-height:200px;overflow-y:auto;"></div>
      </div>
      <button onclick="addToWatchlist(document.getElementById('wl-search').value.toUpperCase().trim())"
        class="btn" style="white-space:nowrap;">+ ADD</button>
      <button onclick="loadWatchlist()" style="background:var(--p2);border:1px solid var(--border);
        color:var(--dim);border-radius:4px;padding:8px 14px;cursor:pointer;font-family:Inter,sans-serif;font-size:0.75rem;">
        ⟳ REFRESH
      </button>
      <div id="wl-refresh-timer" style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:var(--dim);"></div>
    </div>

    <!-- Watchlist table -->
    <div class="card" style="padding:0;">
      <div class="trow hdr" style="grid-template-columns:140px 90px 70px 80px 80px 90px 80px 70px 60px;">
        <span>Symbol</span><span>CMP</span><span>Chg%</span><span>High</span><span>Low</span>
        <span>Sector</span><span>Signal</span><span>Sparkline</span><span>Action</span>
      </div>
      <div id="wl-list">
        <div class="loading"><div class="spinner"></div>Loading watchlist...</div>
      </div>
    </div>
    <div id="wl-status" style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:var(--dim);margin-top:8px;"></div>
  </div>

  <!-- ═══ MARKET DEPTH PANE ═══ -->
  <div id="depth-pane" style="display:none;">
    <div class="card">
      <div style="display:flex;gap:12px;align-items:center;margin-bottom:16px;">
        <select id="depth-sym-sel" onchange="loadMarketDepth(this.value)"
          style="background:var(--p2);border:1px solid var(--border);color:var(--white);
                 padding:7px 12px;font-family:'JetBrains Mono',monospace;font-size:0.85rem;border-radius:4px;outline:none;">
          <option value="">Select Symbol...</option>
        </select>
        <div id="depth-cmp" style="font-family:'JetBrains Mono',monospace;font-size:1.2rem;color:var(--white);font-weight:700;"></div>
        <div id="depth-chg" style="font-family:'JetBrains Mono',monospace;font-size:0.85rem;"></div>
        <div style="margin-left:auto;font-family:Inter,sans-serif;font-size:0.65rem;color:var(--dim);">
          Auto-refresh: <span id="depth-timer" style="color:var(--cyan);">10s</span>
        </div>
      </div>

      <div class="g2" style="gap:20px;">
        <!-- Bid/Ask Ladder -->
        <div>
          <div style="font-family:Inter,sans-serif;font-size:0.65rem;color:var(--dim);letter-spacing:1px;margin-bottom:10px;font-weight:600;text-transform:uppercase;">Order Book</div>
          <div style="display:grid;grid-template-columns:80px 1fr 90px 60px;gap:4px;margin-bottom:4px;
            font-family:Inter,sans-serif;font-size:0.6rem;color:var(--dim);text-transform:uppercase;font-weight:600;">
            <span>Price</span><span>Volume Bar</span><span>Qty</span><span>Orders</span>
          </div>
          <div id="depth-asks"></div>
          <div id="depth-mid" style="background:var(--p2);border:1px solid var(--border);padding:6px 8px;
            font-family:'JetBrains Mono',monospace;font-size:0.85rem;color:var(--white);text-align:center;font-weight:700;margin:4px 0;"></div>
          <div id="depth-bids"></div>
        </div>

        <!-- Stats panel -->
        <div>
          <div style="font-family:Inter,sans-serif;font-size:0.65rem;color:var(--dim);letter-spacing:1px;margin-bottom:10px;font-weight:600;text-transform:uppercase;">Depth Summary</div>
          <div id="depth-stats" style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px;"></div>
          <div style="font-family:Inter,sans-serif;font-size:0.65rem;color:var(--dim);letter-spacing:1px;margin-bottom:8px;font-weight:600;text-transform:uppercase;">Bid vs Ask Volume</div>
          <div id="depth-imbalance-bar" style="height:24px;border-radius:4px;overflow:hidden;display:flex;margin-bottom:8px;"></div>
          <div id="depth-imbalance-label" style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:var(--text);"></div>
          <div style="margin-top:16px;padding:10px;background:rgba(255,152,0,0.08);border:1px solid rgba(255,152,0,0.2);border-radius:4px;
            font-family:Inter,sans-serif;font-size:0.65rem;color:var(--gold);">
            ⚠ Simulated depth (indicative only). Real Level-2 requires a broker API subscription.
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ═══ PRICE ALERTS PANE ═══ -->
  <div id="alerts-pane" style="display:none;">
    <div class="g2" style="gap:16px;">
      <!-- Create alert form -->
      <div class="card">
        <div class="card-title">🔔 CREATE PRICE ALERT</div>
        <div class="form-row">
          <label>Symbol</label>
          <input id="al-sym" type="text" placeholder="e.g. RELIANCE"
            style="text-transform:uppercase;" oninput="this.value=this.value.toUpperCase()">
        </div>
        <div class="form-row">
          <label>Condition</label>
          <select id="al-cond" style="background:var(--p2);border:1px solid var(--border);color:var(--white);
            padding:6px 10px;font-family:'JetBrains Mono',monospace;font-size:0.82rem;outline:none;border-radius:4px;">
            <option value="ABOVE">Price Rises Above ▲</option>
            <option value="BELOW">Price Falls Below ▼</option>
            <option value="PCT_UP">Change% ≥ +%</option>
            <option value="PCT_DOWN">Change% ≤ -%</option>
          </select>
        </div>
        <div class="form-row">
          <label>Threshold</label>
          <input id="al-thresh" type="number" step="0.01" placeholder="e.g. 2500.00">
        </div>
        <div class="form-row" style="gap:20px;">
          <label style="display:flex;align-items:center;gap:8px;min-width:auto;cursor:pointer;">
            <input type="checkbox" id="al-browser" checked> Browser Push
          </label>
          <label style="display:flex;align-items:center;gap:8px;min-width:auto;cursor:pointer;">
            <input type="checkbox" id="al-wa"> WhatsApp
          </label>
        </div>
        <button class="btn" onclick="createAlert()" style="width:100%;">🔔 SET ALERT</button>
        <div id="al-msg" style="margin-top:10px;font-family:'JetBrains Mono',monospace;font-size:0.75rem;"></div>
      </div>

      <!-- Alerts table -->
      <div class="card" style="padding:0;">
        <div style="display:flex;align-items:center;justify-content:space-between;padding:14px 16px 10px;">
          <div class="card-title" style="margin:0;">📋 ACTIVE ALERTS</div>
          <button onclick="loadAlerts()" style="background:transparent;border:none;color:var(--dim);cursor:pointer;font-size:0.75rem;">⟳ REFRESH</button>
        </div>
        <div class="trow hdr" style="grid-template-columns:110px 70px 90px 90px 70px 50px;">
          <span>Symbol</span><span>Condition</span><span>Threshold</span><span>Created</span><span>Status</span><span>Del</span>
        </div>
        <div id="alerts-list">
          <div class="loading"><div class="spinner"></div>Loading alerts...</div>
        </div>
      </div>
    </div>
  </div>

  <!-- ═══ MULTI-CHART PANE ═══ -->
  <div id="multichart-pane" style="display:none;">
    <div style="display:flex;gap:10px;align-items:center;margin-bottom:14px;">
      <span style="font-family:Inter,sans-serif;font-size:0.75rem;color:var(--text);font-weight:600;">2×2 MULTI-CHART VIEW</span>
      <button onclick="syncAllCharts()" class="btn" style="background:var(--p2);color:var(--cyan);border:1px solid var(--cyan);">⟲ SYNC ALL</button>
      <select id="mc-range" onchange="syncAllCharts()"
        style="background:var(--p2);border:1px solid var(--border);color:var(--white);padding:6px 10px;
               font-family:'JetBrains Mono',monospace;font-size:0.8rem;border-radius:4px;outline:none;">
        <option value="30">30 days</option>
        <option value="60" selected>60 days</option>
        <option value="90">90 days</option>
        <option value="180">180 days</option>
      </select>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
      <div class="card" style="padding:10px;" id="mc-card-0">
        <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
          <select id="mc-sym-0" onchange="loadMiniChart(0)"
            style="flex:1;background:var(--p2);border:1px solid var(--border);color:var(--white);
                   padding:5px 8px;font-family:'JetBrains Mono',monospace;font-size:0.78rem;border-radius:4px;outline:none;">
            <option value="">Select Symbol...</option>
          </select>
          <div id="mc-cmp-0" style="font-family:'JetBrains Mono',monospace;font-size:0.85rem;color:var(--white);font-weight:700;min-width:70px;text-align:right;"></div>
        </div>
        <canvas id="mc-canvas-0" width="400" height="180" style="width:100%;height:180px;display:block;"></canvas>
      </div>
      <div class="card" style="padding:10px;" id="mc-card-1">
        <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
          <select id="mc-sym-1" onchange="loadMiniChart(1)"
            style="flex:1;background:var(--p2);border:1px solid var(--border);color:var(--white);
                   padding:5px 8px;font-family:'JetBrains Mono',monospace;font-size:0.78rem;border-radius:4px;outline:none;">
            <option value="">Select Symbol...</option>
          </select>
          <div id="mc-cmp-1" style="font-family:'JetBrains Mono',monospace;font-size:0.85rem;color:var(--white);font-weight:700;min-width:70px;text-align:right;"></div>
        </div>
        <canvas id="mc-canvas-1" width="400" height="180" style="width:100%;height:180px;display:block;"></canvas>
      </div>
      <div class="card" style="padding:10px;" id="mc-card-2">
        <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
          <select id="mc-sym-2" onchange="loadMiniChart(2)"
            style="flex:1;background:var(--p2);border:1px solid var(--border);color:var(--white);
                   padding:5px 8px;font-family:'JetBrains Mono',monospace;font-size:0.78rem;border-radius:4px;outline:none;">
            <option value="">Select Symbol...</option>
          </select>
          <div id="mc-cmp-2" style="font-family:'JetBrains Mono',monospace;font-size:0.85rem;color:var(--white);font-weight:700;min-width:70px;text-align:right;"></div>
        </div>
        <canvas id="mc-canvas-2" width="400" height="180" style="width:100%;height:180px;display:block;"></canvas>
      </div>
      <div class="card" style="padding:10px;" id="mc-card-3">
        <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
          <select id="mc-sym-3" onchange="loadMiniChart(3)"
            style="flex:1;background:var(--p2);border:1px solid var(--border);color:var(--white);
                   padding:5px 8px;font-family:'JetBrains Mono',monospace;font-size:0.78rem;border-radius:4px;outline:none;">
            <option value="">Select Symbol...</option>
          </select>
          <div id="mc-cmp-3" style="font-family:'JetBrains Mono',monospace;font-size:0.85rem;color:var(--white);font-weight:700;min-width:70px;text-align:right;"></div>
        </div>
        <canvas id="mc-canvas-3" width="400" height="180" style="width:100%;height:180px;display:block;"></canvas>
      </div>
    </div>
  </div>

</div><!-- /page-watchlist -->
"""

JS = r"""
// ══════════════════════════════════════════════════════════════
// WATCHLIST PAGE — Page 3: Watchlist + Market Depth + Alerts + Multi-Chart
// ══════════════════════════════════════════════════════════════

let _wlInitDone = false;
let _wlRefreshTimer = null;
let _depthTimer = null;
let _depthCountdown = 10;
let _wlAllSymbols = [];
let _wlItems = [];
let _wlAutoRefreshSecs = 30;
let _wlCountdown = 30;
let _wlCountTimer = null;

function initWatchlist() {
  if (!_wlInitDone) {
    _wlInitDone = true;
    // Load all symbols for autocomplete
    api('all_symbols').then(d => {
      _wlAllSymbols = [
        ...(d.indices || []),
        ...(d.equities || []),
        ...(d.commodities || [])
      ];
      // Populate multi-chart dropdowns
      [0,1,2,3].forEach(i => {
        const sel = document.getElementById('mc-sym-' + i);
        if (!sel) return;
        _wlAllSymbols.forEach(s => {
          const opt = document.createElement('option');
          opt.value = s.symbol;
          opt.textContent = s.symbol + ' — ' + (s.name || '');
          sel.appendChild(opt);
        });
      });
      // Also populate depth selector
      loadWatchlist();
    }).catch(() => loadWatchlist());

    // Request browser notification permission
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }

    // Start auto-refresh
    _wlStartAutoRefresh();
  } else {
    loadWatchlist();
  }
  wlTab('watchlist');
}

function _wlStartAutoRefresh() {
  if (_wlCountTimer) clearInterval(_wlCountTimer);
  _wlCountdown = _wlAutoRefreshSecs;
  _wlCountTimer = setInterval(() => {
    _wlCountdown--;
    const el = document.getElementById('wl-refresh-timer');
    if (el) el.textContent = 'Auto-refresh in ' + _wlCountdown + 's';
    if (_wlCountdown <= 0) {
      _wlCountdown = _wlAutoRefreshSecs;
      const pane = document.getElementById('watchlist-pane');
      if (pane && pane.style.display !== 'none') loadWatchlist();
    }
  }, 1000);
}

function wlTab(tab) {
  ['watchlist','depth','alerts','chart'].forEach(t => {
    const pane = document.getElementById(t === 'chart' ? 'multichart-pane' : t + '-pane');
    const btn  = document.getElementById('wl-tab-' + t);
    if (pane) pane.style.display = (t === tab) ? '' : 'none';
    if (btn) {
      if (t === tab) {
        btn.style.background = 'rgba(41,98,255,0.12)';
        btn.style.borderColor = 'var(--cyan)';
        btn.style.color = 'var(--cyan)';
      } else {
        btn.style.background = 'transparent';
        btn.style.borderColor = 'var(--border)';
        btn.style.color = 'var(--dim)';
      }
    }
  });
  if (tab === 'alerts') loadAlerts();
  if (tab === 'chart') initMultiChart();
  if (tab === 'depth') {
    populateDepthDropdown();
    const sel = document.getElementById('depth-sym-sel');
    if (sel && sel.value) loadMarketDepth(sel.value);
  }
}

// ── WATCHLIST ─────────────────────────────────────────────────

async function loadWatchlist() {
  const el = document.getElementById('wl-list');
  if (!el) return;
  try {
    const d = await api('watchlist_get');
    _wlItems = d.items || [];
    if (_wlItems.length === 0) {
      el.innerHTML = '<div style="padding:24px;text-align:center;color:var(--dim);font-family:Inter,sans-serif;font-size:0.85rem;">' +
        '📋 Your watchlist is empty. Search for a symbol above and click + ADD.</div>';
      return;
    }
    el.innerHTML = _wlItems.map((item, idx) => {
      const pnl = item.change_pct || 0;
      const pnlColor = pnl > 0 ? 'var(--green)' : pnl < 0 ? 'var(--red)' : 'var(--text)';
      const pnlArrow = pnl > 0 ? '▲' : pnl < 0 ? '▼' : '─';
      const sig = Math.abs(pnl) > 2 ? (pnl > 0 ? 'BULL' : 'BEAR') : 'NEUT';
      const sigCss = sig === 'BULL' ? 'bg' : sig === 'BEAR' ? 'br' : 'bd';
      const price = item.price ? item.price.toLocaleString('en-IN', {minimumFractionDigits:2}) : '—';
      const high = item.high ? item.high.toFixed(2) : '—';
      const low  = item.low  ? item.low.toFixed(2)  : '—';
      return `<div class="trow" style="grid-template-columns:140px 90px 70px 80px 80px 90px 80px 70px 60px;cursor:pointer;"
               onclick="wlGoToChart('${item.symbol}')">
        <span style="color:var(--white);font-weight:600;">${item.symbol}<br>
          <span style="color:var(--dim);font-family:Inter,sans-serif;font-size:0.65rem;font-weight:400;">${(item.name||'').substring(0,20)}</span>
        </span>
        <span style="color:var(--white);font-weight:700;">₹${price}</span>
        <span style="color:${pnlColor};font-weight:600;">${pnlArrow}${Math.abs(pnl).toFixed(2)}%</span>
        <span style="color:var(--green);">₹${high}</span>
        <span style="color:var(--red);">₹${low}</span>
        <span style="color:var(--dim);font-size:0.7rem;">${(item.sector||'').substring(0,12)}</span>
        <span><span class="badge ${sigCss}">${sig}</span></span>
        <span><canvas id="wl-spark-${idx}" width="60" height="28" style="display:inline-block;vertical-align:middle;"></canvas></span>
        <span onclick="event.stopPropagation();removeFromWatchlist('${item.symbol}')"
          style="color:var(--red);cursor:pointer;font-size:1.1rem;" title="Remove">✕</span>
      </div>`;
    }).join('');
    // Draw sparklines
    _wlItems.forEach((item, idx) => {
      api('price_history', {symbol: item.symbol, days: 7}).then(ph => {
        const closes = ph.closes || ph.prices || [];
        if (closes.length >= 2) {
          drawSparkline('wl-spark-' + idx, closes, (item.change_pct||0) >= 0);
        }
      }).catch(() => {});
    });
    // Update depth dropdown
    populateDepthDropdown();
    const st = document.getElementById('wl-status');
    if (st) st.textContent = `${_wlItems.length} symbols · updated ${new Date().toLocaleTimeString()}`;
  } catch(e) {
    if (el) el.innerHTML = `<div class="err">Failed to load watchlist: ${e.message}</div>`;
  }
}

function wlGoToChart(sym) {
  const el = document.getElementById('chart-sym');
  if (el) { el.value = sym; }
  if (typeof nav === 'function') nav('chart');
}

function drawSparkline(canvasId, data, isUp) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || data.length < 2) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);
  const min = Math.min(...data), max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => ({
    x: (i / (data.length - 1)) * (W - 2) + 1,
    y: H - 4 - ((v - min) / range) * (H - 8)
  }));
  ctx.strokeStyle = isUp ? '#089981' : '#F23645';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  pts.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
  ctx.stroke();
  // Fill
  ctx.fillStyle = isUp ? 'rgba(8,153,129,0.15)' : 'rgba(242,54,69,0.15)';
  ctx.beginPath();
  pts.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
  ctx.lineTo(pts[pts.length-1].x, H);
  ctx.lineTo(pts[0].x, H);
  ctx.closePath();
  ctx.fill();
}

function wlFilterSymbols(q) {
  const dd = document.getElementById('wl-dropdown');
  if (!dd) return;
  q = q.trim().toUpperCase();
  if (!q || q.length < 1) { dd.style.display = 'none'; return; }
  const matches = _wlAllSymbols.filter(s =>
    s.symbol.startsWith(q) || (s.name || '').toUpperCase().includes(q)
  ).slice(0, 12);
  if (!matches.length) { dd.style.display = 'none'; return; }
  dd.innerHTML = matches.map(s =>
    `<div onclick="document.getElementById('wl-search').value='${s.symbol}';document.getElementById('wl-dropdown').style.display='none';"
      style="padding:7px 12px;cursor:pointer;font-family:'JetBrains Mono',monospace;font-size:0.8rem;
             color:var(--text);border-bottom:1px solid var(--border);"
      onmouseover="this.style.background='var(--p2)'" onmouseout="this.style.background=''">
      <b style="color:var(--white);">${s.symbol}</b>
      <span style="color:var(--dim);font-size:0.7rem;margin-left:8px;">${(s.name||'').substring(0,30)}</span>
    </div>`
  ).join('');
  dd.style.display = 'block';
}

async function addToWatchlist(sym) {
  sym = (sym || '').toUpperCase().trim();
  if (!sym) { alert('Enter a symbol first'); return; }
  const dd = document.getElementById('wl-dropdown');
  if (dd) dd.style.display = 'none';
  const inp = document.getElementById('wl-search');
  if (inp) inp.value = '';
  try {
    const d = await api('watchlist_add', {symbol: sym});
    if (d.ok) {
      loadWatchlist();
    } else {
      alert('Error: ' + (d.error || 'Unknown'));
    }
  } catch(e) {
    alert('Failed to add: ' + e.message);
  }
}

async function removeFromWatchlist(sym) {
  if (!confirm(`Remove ${sym} from watchlist?`)) return;
  try {
    await api('watchlist_remove', {symbol: sym});
    loadWatchlist();
  } catch(e) {
    alert('Failed to remove: ' + e.message);
  }
}

// ── MARKET DEPTH ─────────────────────────────────────────────

function populateDepthDropdown() {
  const sel = document.getElementById('depth-sym-sel');
  if (!sel) return;
  const prevVal = sel.value;
  const opts = ['<option value="">Select Symbol...</option>'];
  _wlItems.forEach(item => {
    opts.push(`<option value="${item.symbol}"${item.symbol===prevVal?' selected':''}>${item.symbol} — ${(item.name||'').substring(0,25)}</option>`);
  });
  // Also add some popular symbols if watchlist is empty
  if (_wlItems.length === 0) {
    ['NIFTY50','RELIANCE','TCS','INFY','HDFCBANK'].forEach(s => {
      opts.push(`<option value="${s}">${s}</option>`);
    });
  }
  sel.innerHTML = opts.join('');
}

function _startDepthAutoRefresh(sym) {
  if (_depthTimer) clearInterval(_depthTimer);
  _depthCountdown = 10;
  _depthTimer = setInterval(() => {
    _depthCountdown--;
    const el = document.getElementById('depth-timer');
    if (el) el.textContent = _depthCountdown + 's';
    if (_depthCountdown <= 0) {
      _depthCountdown = 10;
      const pane = document.getElementById('depth-pane');
      if (pane && pane.style.display !== 'none') loadMarketDepth(sym);
    }
  }, 1000);
}

async function loadMarketDepth(sym) {
  if (!sym) return;
  if (_depthTimer) clearInterval(_depthTimer);
  const asksEl = document.getElementById('depth-asks');
  const bidsEl = document.getElementById('depth-bids');
  const midEl  = document.getElementById('depth-mid');
  const statsEl = document.getElementById('depth-stats');
  const imbalBar = document.getElementById('depth-imbalance-bar');
  const imbalLbl = document.getElementById('depth-imbalance-label');
  if (!asksEl) return;
  try {
    const d = await api('market_depth', {symbol: sym});
    if (!d.ok) throw new Error(d.error || 'Failed');

    // CMP display
    const cmpEl = document.getElementById('depth-cmp');
    const chgEl = document.getElementById('depth-chg');
    if (cmpEl) cmpEl.textContent = '₹' + (d.cmp || 0).toLocaleString('en-IN', {minimumFractionDigits:2});

    // Find max qty for bar scaling
    const allQty = [...(d.asks||[]), ...(d.bids||[])].map(x => x.qty);
    const maxQty = Math.max(...allQty, 1);

    // Asks (red, price ascending — reverse order to show highest ask at top)
    const asksRev = [...(d.asks||[])].reverse();
    asksEl.innerHTML = asksRev.map(ask => {
      const barW = Math.round((ask.qty / maxQty) * 100);
      return `<div style="display:grid;grid-template-columns:80px 1fr 90px 60px;gap:4px;
              padding:4px 6px;border-bottom:1px solid rgba(242,54,69,0.1);align-items:center;">
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.8rem;color:var(--red);">₹${ask.price.toFixed(2)}</span>
        <div style="background:rgba(242,54,69,0.15);height:8px;border-radius:2px;overflow:hidden;">
          <div style="width:${barW}%;height:100%;background:rgba(242,54,69,0.5);"></div>
        </div>
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:var(--text);text-align:right;">${ask.qty.toLocaleString()}</span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:var(--dim);text-align:right;">${ask.orders}</span>
      </div>`;
    }).join('');

    // Mid row
    if (midEl) {
      midEl.textContent = '● LTP: ₹' + (d.cmp||0).toLocaleString('en-IN', {minimumFractionDigits:2});
      midEl.style.color = 'var(--white)';
    }

    // Bids (green)
    bidsEl.innerHTML = (d.bids||[]).map(bid => {
      const barW = Math.round((bid.qty / maxQty) * 100);
      return `<div style="display:grid;grid-template-columns:80px 1fr 90px 60px;gap:4px;
              padding:4px 6px;border-bottom:1px solid rgba(8,153,129,0.1);align-items:center;">
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.8rem;color:var(--green);">₹${bid.price.toFixed(2)}</span>
        <div style="background:rgba(8,153,129,0.15);height:8px;border-radius:2px;overflow:hidden;">
          <div style="width:${barW}%;height:100%;background:rgba(8,153,129,0.5);"></div>
        </div>
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:var(--text);text-align:right;">${bid.qty.toLocaleString()}</span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:var(--dim);text-align:right;">${bid.orders}</span>
      </div>`;
    }).join('');

    // Stats
    const totalBid = d.total_bid_qty || 0;
    const totalAsk = d.total_ask_qty || 0;
    const imb = d.imbalance_pct || 0;
    if (statsEl) statsEl.innerHTML = `
      <div class="stat"><span class="val" style="color:var(--green);">${totalBid.toLocaleString()}</span><span class="lbl">Total Bid Qty</span></div>
      <div class="stat"><span class="val" style="color:var(--red);">${totalAsk.toLocaleString()}</span><span class="lbl">Total Ask Qty</span></div>
      <div class="stat"><span class="val" style="font-size:1rem;color:${d.cmp?'var(--text)':'var(--dim)'};">₹${(d.high||0).toFixed(2)}</span><span class="lbl">Day High</span></div>
      <div class="stat"><span class="val" style="font-size:1rem;color:${d.cmp?'var(--text)':'var(--dim)'};">₹${(d.low||0).toFixed(2)}</span><span class="lbl">Day Low</span></div>`;

    // Imbalance bar
    const bidPct = Math.round(totalBid / Math.max(totalBid + totalAsk, 1) * 100);
    const askPct = 100 - bidPct;
    if (imbalBar) imbalBar.innerHTML = `
      <div style="flex:${bidPct};background:var(--green);display:flex;align-items:center;justify-content:center;
        font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:#000;font-weight:700;">${bidPct}% BID</div>
      <div style="flex:${askPct};background:var(--red);display:flex;align-items:center;justify-content:center;
        font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:#fff;font-weight:700;">ASK ${askPct}%</div>`;
    if (imbalLbl) imbalLbl.textContent = `Imbalance: ${imb > 0 ? '+' : ''}${imb}% (${imb > 5 ? 'BUY pressure' : imb < -5 ? 'SELL pressure' : 'Balanced'})`;

    _startDepthAutoRefresh(sym);
  } catch(e) {
    if (asksEl) asksEl.innerHTML = `<div class="err">Depth load failed: ${e.message}</div>`;
    if (bidsEl) bidsEl.innerHTML = '';
  }
}

// ── PRICE ALERTS ──────────────────────────────────────────────

async function createAlert() {
  const sym   = (document.getElementById('al-sym')?.value || '').toUpperCase().trim();
  const cond  = document.getElementById('al-cond')?.value || 'ABOVE';
  const thresh= parseFloat(document.getElementById('al-thresh')?.value || 0);
  const nb    = document.getElementById('al-browser')?.checked ? 1 : 0;
  const nwa   = document.getElementById('al-wa')?.checked ? 1 : 0;
  const msgEl = document.getElementById('al-msg');
  if (!sym || !thresh) {
    if (msgEl) { msgEl.textContent = '⚠ Symbol and threshold are required'; msgEl.style.color='var(--red)'; }
    return;
  }
  try {
    const d = await api('alert_set', {symbol:sym, condition:cond, threshold:thresh, notify_browser:nb, notify_whatsapp:nwa});
    if (d.ok) {
      if (msgEl) { msgEl.textContent = `✅ Alert set: ${sym} ${cond} ₹${thresh}`; msgEl.style.color='var(--green)'; }
      // Request browser push permission if needed
      if (nb && 'Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
      }
      document.getElementById('al-thresh').value = '';
      loadAlerts();
    } else {
      if (msgEl) { msgEl.textContent = '⚠ ' + (d.error || 'Error'); msgEl.style.color='var(--red)'; }
    }
  } catch(e) {
    if (msgEl) { msgEl.textContent = '⚠ ' + e.message; msgEl.style.color='var(--red)'; }
  }
}

async function loadAlerts() {
  const el = document.getElementById('alerts-list');
  if (!el) return;
  try {
    const d = await api('alert_get');
    const alerts = d.alerts || [];
    if (!alerts.length) {
      el.innerHTML = '<div style="padding:20px;text-align:center;color:var(--dim);font-family:Inter,sans-serif;font-size:0.85rem;">No alerts set.</div>';
      return;
    }
    el.innerHTML = alerts.map(a => {
      const stColor = a.status === 'TRIGGERED' ? 'var(--green)' : a.status === 'ACTIVE' ? 'var(--cyan)' : 'var(--dim)';
      const condLabel = {ABOVE:'▲ Above', BELOW:'▼ Below', PCT_UP:'%▲', PCT_DOWN:'%▼'}[a.condition] || a.condition;
      return `<div class="trow" style="grid-template-columns:110px 70px 90px 90px 70px 50px;">
        <span style="color:var(--white);font-weight:600;">${a.symbol}</span>
        <span style="color:var(--text);font-size:0.75rem;">${condLabel}</span>
        <span style="color:var(--gold);">₹${a.threshold}</span>
        <span style="color:var(--dim);font-size:0.7rem;">${(a.created_at||'').substring(0,10)}</span>
        <span style="color:${stColor};">${a.status}</span>
        <span onclick="deleteAlert(${a.id})" style="color:var(--red);cursor:pointer;font-size:1.1rem;" title="Delete">✕</span>
      </div>`;
    }).join('');
    // Check for triggered alerts and push browser notifications
    _checkAlertTriggers(alerts);
  } catch(e) {
    if (el) el.innerHTML = `<div class="err">Failed: ${e.message}</div>`;
  }
}

function _checkAlertTriggers(alerts) {
  if (!('Notification' in window) || Notification.permission !== 'granted') return;
  const triggered = alerts.filter(a => a.status === 'TRIGGERED' && a.triggered_at);
  // Only notify for recently triggered (within last 5 min)
  const cutoff = Date.now() - 5 * 60 * 1000;
  triggered.forEach(a => {
    if (a.triggered_at && new Date(a.triggered_at).getTime() > cutoff) {
      try {
        new Notification(`🔔 Vprofitables Alert: ${a.symbol}`, {
          body: `${a.symbol} hit ₹${a.threshold} (${a.condition})`,
          icon: '/favicon.svg'
        });
      } catch(e) {}
    }
  });
}

async function deleteAlert(id) {
  if (!confirm('Delete this alert?')) return;
  try {
    await api('alert_delete', {id: id});
    loadAlerts();
  } catch(e) {
    alert('Delete failed: ' + e.message);
  }
}

// ── MULTI-CHART ───────────────────────────────────────────────

function initMultiChart() {
  // Populate watchlist symbols in all 4 dropdowns
  _wlItems.forEach((item, wIdx) => {
    [0,1,2,3].forEach(i => {
      const sel = document.getElementById('mc-sym-' + i);
      if (!sel) return;
      // Check if already populated from watchlist
      const existing = Array.from(sel.options).find(o => o.value === item.symbol);
      if (!existing) {
        const opt = document.createElement('option');
        opt.value = item.symbol;
        opt.textContent = item.symbol;
        sel.appendChild(opt);
      }
    });
  });
  // Auto-load first 4 symbols from watchlist
  _wlItems.slice(0, 4).forEach((item, i) => {
    const sel = document.getElementById('mc-sym-' + i);
    if (sel) { sel.value = item.symbol; loadMiniChart(i); }
  });
}

async function loadMiniChart(idx) {
  const sel = document.getElementById('mc-sym-' + idx);
  if (!sel || !sel.value) return;
  const sym = sel.value;
  const days = parseInt(document.getElementById('mc-range')?.value || 60);
  const cmpEl = document.getElementById('mc-cmp-' + idx);
  const card = document.getElementById('mc-card-' + idx);
  try {
    const d = await api('price_history', {symbol: sym, days: days});
    const closes = d.closes || d.prices || [];
    const dates  = d.dates || [];
    if (closes.length < 2) {
      drawMiniChart('mc-canvas-' + idx, [], dates, sym);
      if (cmpEl) cmpEl.textContent = '—';
      return;
    }
    const last = closes[closes.length - 1];
    const prev = closes[closes.length - 2];
    const chg  = ((last - prev) / prev * 100).toFixed(2);
    const chgColor = chg >= 0 ? 'var(--green)' : 'var(--red)';
    if (cmpEl) cmpEl.innerHTML = `₹${last.toLocaleString('en-IN',{minimumFractionDigits:2})} <span style="color:${chgColor};font-size:0.72rem;">${chg>0?'+':''}${chg}%</span>`;
    drawMiniChart('mc-canvas-' + idx, closes, dates, sym);
    if (card) card.style.borderColor = chg >= 0 ? 'rgba(8,153,129,0.3)' : 'rgba(242,54,69,0.3)';
  } catch(e) {
    if (cmpEl) cmpEl.textContent = 'Error';
    drawMiniChart('mc-canvas-' + idx, [], [], sym);
  }
}

function drawMiniChart(canvasId, data, dates, sym) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.offsetWidth || canvas.width;
  const H = canvas.height;
  canvas.width = W;
  ctx.clearRect(0, 0, W, H);

  // Background
  ctx.fillStyle = '#0B0E14';
  ctx.fillRect(0, 0, W, H);

  if (!data || data.length < 2) {
    ctx.fillStyle = '#363A45';
    ctx.font = '12px Inter';
    ctx.textAlign = 'center';
    ctx.fillText('No price data', W/2, H/2);
    return;
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pad = 20;
  const isUp = data[data.length-1] >= data[0];
  const lineColor = isUp ? '#089981' : '#F23645';
  const fillColor = isUp ? 'rgba(8,153,129,0.12)' : 'rgba(242,54,69,0.12)';

  const toX = (i) => pad + (i / (data.length - 1)) * (W - pad*2);
  const toY = (v) => (H - pad) - ((v - min) / range) * (H - pad*2);

  // Grid lines
  ctx.strokeStyle = '#2B3139';
  ctx.lineWidth = 0.5;
  for (let i = 0; i < 4; i++) {
    const y = pad + (i / 3) * (H - pad*2);
    ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(W - pad, y); ctx.stroke();
  }

  // Area fill
  ctx.beginPath();
  ctx.moveTo(toX(0), toY(data[0]));
  data.forEach((v, i) => { if (i > 0) ctx.lineTo(toX(i), toY(v)); });
  ctx.lineTo(toX(data.length-1), H - pad);
  ctx.lineTo(toX(0), H - pad);
  ctx.closePath();
  ctx.fillStyle = fillColor;
  ctx.fill();

  // Line
  ctx.beginPath();
  ctx.moveTo(toX(0), toY(data[0]));
  data.forEach((v, i) => { if (i > 0) ctx.lineTo(toX(i), toY(v)); });
  ctx.strokeStyle = lineColor;
  ctx.lineWidth = 1.5;
  ctx.stroke();

  // Symbol label
  ctx.fillStyle = '#787B86';
  ctx.font = '600 11px Inter';
  ctx.textAlign = 'left';
  ctx.fillText(sym || '', pad + 2, pad - 4);

  // Last price label
  const lastY = toY(data[data.length-1]);
  ctx.fillStyle = lineColor;
  ctx.font = '600 10px JetBrains Mono, monospace';
  ctx.textAlign = 'right';
  ctx.fillText('₹' + data[data.length-1].toFixed(0), W - pad - 2, Math.min(lastY - 4, H - pad - 4));
}

function syncAllCharts() {
  [0,1,2,3].forEach(i => {
    const sel = document.getElementById('mc-sym-' + i);
    if (sel && sel.value) loadMiniChart(i);
  });
}

// Close dropdown when clicking outside
document.addEventListener('click', function(e) {
  const dd = document.getElementById('wl-dropdown');
  const inp = document.getElementById('wl-search');
  if (dd && inp && !inp.contains(e.target) && !dd.contains(e.target)) {
    dd.style.display = 'none';
  }
});
"""
