"""
page_portfolio.py — Demat Portfolio & Order Book Management
Sections:
  1. DEMAT PORTFOLIO — Full Zerodha-style portfolio view, holdings, margins, P&L
  2. ORDER BOOK      — Open/Closed orders, bracket modifications, partial exits, CSV export
"""

HTML = r"""
<!-- ═══════════ PAGE: PORTFOLIO & EXECUTION ═══════════ -->
<div class="page" id="page-portfolio">
  <div class="topbar">
    <div style="display:flex;align-items:center;gap:10px;">
      <span style="font-family:Orbitron,sans-serif;font-size:1.1rem;color:var(--gold);font-weight:700;letter-spacing:2px;">💼 DEMAT PORTFOLIO & ORDER BOOK</span>
    </div>
  </div>

  <!-- ══════════════════════════════════════════════════════════ -->
  <!-- TAB NAVIGATION                                             -->
  <!-- ══════════════════════════════════════════════════════════ -->
  <div style="display:flex;gap:0;margin-bottom:20px;border-bottom:1px solid var(--border);flex-wrap:wrap;">
    <button id="ptf-tab-holdings" onclick="portfolioTab('ptf')"
      style="padding:8px 24px;background:rgba(255,165,0,0.15);border:1px solid orange;border-bottom:none;
             color:orange;font-family:Share Tech Mono,monospace;font-size:0.75rem;letter-spacing:1px;cursor:pointer;">
      💼 DEMAT PORTFOLIO
    </button>
    <button id="ptf-tab-ob" onclick="portfolioTab('orderbook')"
      style="padding:8px 24px;background:transparent;border:1px solid var(--border);border-bottom:none;
             color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.75rem;letter-spacing:1px;cursor:pointer;">
      📒 ORDER BOOK
    </button>
  </div>

  <!-- ══════════════════════════════════════════════════════════ -->
  <!-- TAB 1: DEMAT PORTFOLIO                                     -->
  <!-- ══════════════════════════════════════════════════════════ -->
  <style>
    .ptf-row {
      display:grid;
      grid-template-columns:minmax(170px,2fr) repeat(6,minmax(90px,1fr)) minmax(96px,0.8fr);
      gap:0;
      padding:12px 18px;
      border-bottom:1px solid rgba(255,255,255,0.04);
      align-items:center;
      transition:background 0.15s;
    }
    .ptf-row:hover { background:rgba(255,255,255,0.028); }
    @media(max-width:900px) {
      #ptf-table-header { display:none !important; }
      .ptf-row { grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; padding:14px; }
      .ptf-row > div { text-align:left !important; }
      .ptf-row > div:first-child,.ptf-row > div:last-child { grid-column:1/-1; }
    }
  </style>

  <div id="ptf-section-holdings" class="ptf-tab-content">
    <!-- ── TOP SUMMARY TILES (Zerodha-style) ───────────────────────────── -->
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px;">
      <div style="background:var(--p2);border:1px solid var(--border);border-radius:8px;padding:16px 20px;">
        <div style="font-size:0.68rem;color:var(--dim);margin-bottom:6px;">💼 Invested Amount</div>
        <div id="ptf-invested" style="font-size:1.4rem;font-weight:700;color:var(--text);">₹0</div>
      </div>
      <div style="background:var(--p2);border:1px solid var(--border);border-radius:8px;padding:16px 20px;">
        <div style="font-size:0.68rem;color:var(--dim);margin-bottom:6px;">📈 Current Value</div>
        <div id="ptf-current" style="font-size:1.4rem;font-weight:700;color:var(--cyan);">₹0</div>
      </div>
      <div style="background:var(--p2);border:1px solid var(--border);border-radius:8px;padding:16px 20px;">
        <div style="font-size:0.68rem;color:var(--dim);margin-bottom:6px;">📊 Overall P&L</div>
        <div id="ptf-unrealized" style="font-size:1.4rem;font-weight:700;">₹0</div>
        <div id="ptf-unrealized-pct" style="font-size:0.72rem;margin-top:2px;color:var(--dim);"></div>
      </div>
      <div style="background:var(--p2);border:1px solid var(--border);border-radius:8px;padding:16px 20px;">
        <div style="font-size:0.68rem;color:var(--dim);margin-bottom:6px;">⚡ Today's Gain</div>
        <div id="ptf-today" style="font-size:1.4rem;font-weight:700;">₹0</div>
        <div id="ptf-today-pct" style="font-size:0.72rem;margin-top:2px;color:var(--dim);"></div>
      </div>
    </div>

    <!-- ── HOLDINGS TABLE ───────────────────────────────────────────────── -->
    <div style="background:var(--p2);border:1px solid var(--border);border-radius:8px;margin-bottom:16px;">
      <div style="display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--border);flex-wrap:wrap;gap:8px;">
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="font-size:1rem;font-weight:600;color:var(--text);">Holdings</span>
          <span id="ptf-count" style="background:rgba(0,212,255,0.15);color:var(--cyan);font-size:0.7rem;font-weight:700;padding:2px 8px;border-radius:12px;">0</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
          <input id="ptf-search" type="text" placeholder="🔍 Search for stock or company"
            oninput="ptfFilterHoldings()"
            style="padding:6px 12px;background:var(--bg);border:1px solid var(--border);border-radius:6px;
            color:var(--text);font-size:0.78rem;width:240px;outline:none;"/>
          <button onclick="loadPortfolio()"
            style="padding:6px 12px;background:transparent;border:1px solid var(--border);
            border-radius:6px;color:var(--dim);font-size:0.75rem;cursor:pointer;" title="Refresh">
            ↻
          </button>
        </div>
      </div>

      <!-- Table header -->
      <div id="ptf-table-header" style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr 1.2fr 1.2fr 1fr;
        gap:0;padding:10px 18px;border-bottom:1px solid var(--border);
        font-size:0.68rem;color:var(--dim);font-weight:600;">
        <div style="display:flex;align-items:center;gap:4px;cursor:pointer;" onclick="ptfSort('name')">
          Name <span style="font-size:0.5rem;">⬆⬇</span>
        </div>
        <div style="text-align:right;cursor:pointer;" onclick="ptfSort('qty')">Quantity <span style="font-size:0.5rem;">⬆⬇</span></div>
        <div style="text-align:right;">Avg. Price</div>
        <div style="text-align:right;">LTP</div>
        <div style="text-align:right;cursor:pointer;" onclick="ptfSort('inv')">Inv. Amt. <span style="font-size:0.5rem;">⬆⬇</span></div>
        <div style="text-align:right;cursor:pointer;" onclick="ptfSort('cur')">Current Val. <span style="font-size:0.5rem;">⬆⬇</span></div>
        <div style="text-align:right;cursor:pointer;" onclick="ptfSort('pnl')">Overall G/L <span style="font-size:0.5rem;">⬆⬇</span></div>
        <div style="text-align:right;">Action</div>
      </div>

      <!-- Holdings rows -->
      <div id="ptf-list" style="min-height:60px;">
        <div style="padding:24px;text-align:center;color:var(--dim);font-size:0.8rem;">Loading portfolio…</div>
      </div>
    </div>

    <!-- ── PORTFOLIO ANALYTICS (Sector + Top Drivers) ───────────────────── -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">
      <!-- Sector Allocation -->
      <div style="background:var(--p2);border:1px solid var(--border);border-radius:8px;padding:16px 18px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
          <div style="font-size:0.9rem;font-weight:600;color:var(--text);">Portfolio Allocation</div>
          <div style="display:flex;gap:6px;">
            <button id="ptf-view-sector" onclick="ptfSetView('sector')"
              style="padding:4px 10px;border-radius:4px;border:1px solid var(--cyan);
              background:rgba(0,212,255,0.15);color:var(--cyan);font-size:0.68rem;cursor:pointer;">
              View as Sector
            </button>
            <button id="ptf-view-cap" onclick="ptfSetView('cap')"
              style="padding:4px 10px;border-radius:4px;border:1px solid var(--border);
              background:transparent;color:var(--dim);font-size:0.68rem;cursor:pointer;">
              View as Market Cap
            </button>
          </div>
        </div>
        <!-- Stacked allocation bar -->
        <div id="ptf-alloc-bar" style="height:36px;border-radius:6px;overflow:hidden;display:flex;margin-bottom:14px;"></div>
        <!-- Sector returns list -->
        <div id="ptf-allocation-title" style="font-size:0.78rem;font-weight:600;color:var(--text);margin-bottom:8px;">Sector Allocation</div>
        <div id="ptf-allocation-subtitle" style="font-size:0.68rem;color:var(--dim);margin-bottom:10px;">Portfolio weight and unrealized return by sector</div>
        <div id="ptf-sector-bars" style="display:flex;flex-direction:column;gap:8px;"></div>
      </div>

      <!-- Top Drivers -->
      <div style="background:var(--p2);border:1px solid var(--border);border-radius:8px;padding:16px 18px;">
        <div style="font-size:0.9rem;font-weight:600;color:var(--text);margin-bottom:4px;">Top Drivers</div>
        <div style="display:flex;gap:8px;margin-bottom:14px;">
          <button id="ptf-btn-gainers" onclick="ptfShowDrivers('gainers')"
            style="padding:5px 14px;border-radius:20px;border:1px solid var(--cyan);
            background:rgba(0,212,255,0.15);color:var(--cyan);font-size:0.72rem;cursor:pointer;font-weight:600;">
            Top Gainers
          </button>
          <button id="ptf-btn-losers" onclick="ptfShowDrivers('losers')"
            style="padding:5px 14px;border-radius:20px;border:1px solid var(--border);
            background:transparent;color:var(--dim);font-size:0.72rem;cursor:pointer;">
            Top Losers
          </button>
        </div>
        <!-- Header -->
        <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:0;
          padding:6px 0;border-bottom:1px solid var(--border);
          font-size:0.65rem;color:var(--dim);font-weight:600;">
          <div>Stock</div>
          <div style="text-align:right;">52W High</div>
          <div style="text-align:right;">LTP</div>
          <div style="text-align:right;">Day's Gain</div>
        </div>
        <div id="ptf-drivers" style="display:flex;flex-direction:column;gap:0;"></div>
      </div>
    </div>

    <!-- ── REALIZED P&L FOOTER ────────────────────────────────────────────── -->
    <div style="background:var(--p2);border:1px solid var(--border);border-radius:8px;padding:14px 18px;
      display:flex;align-items:center;justify-content:space-between;">
      <span style="font-size:0.78rem;color:var(--dim);">Realized P&L (Closed Trades)</span>
      <span id="ptf-realized" style="font-size:1rem;font-weight:700;color:var(--green);">₹0</span>
    </div>
  </div>

  <!-- ══════════════════════════════════════════════════════════ -->
  <!-- TAB 2: ORDER BOOK                                          -->
  <!-- ══════════════════════════════════════════════════════════ -->
  <style>
    .ob-row {
      display:grid;
      grid-template-columns:90px 70px 85px 85px 85px 85px 60px 80px 100px 1fr;
      gap:4px;
      padding:8px 14px;
      border-bottom:1px solid rgba(255,255,255,0.04);
      align-items:center;
      font-family:'JetBrains Mono',monospace;
      font-size:0.72rem;
      transition:background 0.15s;
    }
    .ob-row:hover { background:rgba(255,255,255,0.025); }
    .ob-row.ob-editing { background:rgba(0,212,255,0.05); }
    .ob-input {
      width:75px;
      background:var(--bg);
      border:1px solid var(--cyan);
      color:var(--text);
      padding:2px 4px;
      font-family:'JetBrains Mono',monospace;
      font-size:0.7rem;
      outline:none;
      border-radius:3px;
    }
    #ob-partial-modal {
      display:none;
      position:fixed;top:0;left:0;width:100%;height:100%;
      background:rgba(0,0,0,0.7);z-index:9999;
      align-items:center;justify-content:center;
    }
    #ob-partial-modal.active { display:flex; }
    .ob-modal-box {
      background:var(--p1);border:1px solid var(--cyan);
      border-radius:8px;padding:24px 28px;min-width:320px;max-width:400px;
      box-shadow:0 8px 32px rgba(0,0,0,0.6);
    }
  </style>

  <div id="ptf-section-orderbook" class="ptf-tab-content" style="display:none;">
    <div style="background:var(--p2);border:1px solid var(--border);border-radius:8px;margin-bottom:16px;">
      <!-- Header toolbar -->
      <div style="display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--border);flex-wrap:wrap;gap:8px;">
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="font-family:Orbitron,sans-serif;font-size:0.88rem;color:var(--cyan);font-weight:700;letter-spacing:2px;">📒 ORDER BOOK</span>
          <span id="ob-count-badge" style="background:rgba(41,98,255,0.18);color:var(--cyan);font-size:0.68rem;font-weight:700;padding:2px 8px;border-radius:12px;font-family:'JetBrains Mono',monospace;">0</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
          <!-- Status filter -->
          <div style="display:flex;gap:0;border:1px solid var(--border);border-radius:4px;overflow:hidden;">
            <button id="ob-filter-OPEN" onclick="obSetFilter('OPEN')"
              style="padding:5px 14px;background:rgba(41,98,255,0.15);border:none;border-right:1px solid var(--border);
              color:var(--cyan);font-family:Share Tech Mono,monospace;font-size:0.65rem;letter-spacing:1px;cursor:pointer;">OPEN</button>
            <button id="ob-filter-CLOSED" onclick="obSetFilter('CLOSED')"
              style="padding:5px 14px;background:transparent;border:none;border-right:1px solid var(--border);
              color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.65rem;letter-spacing:1px;cursor:pointer;">CLOSED</button>
            <button id="ob-filter-ALL" onclick="obSetFilter('ALL')"
              style="padding:5px 14px;background:transparent;border:none;
              color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.65rem;letter-spacing:1px;cursor:pointer;">ALL</button>
          </div>
          <button onclick="loadOrderBook()"
            style="padding:5px 12px;background:transparent;border:1px solid var(--border);border-radius:4px;
            color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.68rem;cursor:pointer;" title="Refresh">↻ REFRESH</button>
          <button onclick="exportTradeCSV()"
            style="padding:5px 16px;background:rgba(8,153,129,0.1);border:1px solid var(--green);border-radius:4px;
            color:var(--green);font-family:Share Tech Mono,monospace;font-size:0.68rem;letter-spacing:1px;cursor:pointer;" title="Export Closed Trades to CSV">
            ⬇ EXPORT CSV
          </button>
        </div>
      </div>

      <!-- Column header -->
      <div class="ob-row" style="padding:8px 14px;background:var(--bg);font-family:Share Tech Mono,monospace;
           font-size:0.6rem;color:var(--dim);letter-spacing:1px;border-bottom:1px solid var(--border);">
        <div>SYMBOL</div>
        <div>TYPE</div>
        <div style="text-align:right;">ENTRY</div>
        <div style="text-align:right;">SL</div>
        <div style="text-align:right;">T1</div>
        <div style="text-align:right;">T2</div>
        <div style="text-align:right;">QTY</div>
        <div style="text-align:center;">STATUS</div>
        <div style="text-align:right;">P&amp;L</div>
        <div style="text-align:right;">ACTIONS</div>
      </div>

      <!-- Rows injected here -->
      <div id="ob-list" style="min-height:80px;">
        <div style="padding:32px;text-align:center;color:var(--dim);font-size:0.8rem;">Loading order book…</div>
      </div>
    </div>

    <!-- Summary footer -->
    <div id="ob-summary-bar" style="display:none;background:var(--p2);border:1px solid var(--border);border-radius:8px;
         padding:12px 18px;display:flex;gap:24px;flex-wrap:wrap;align-items:center;">
    </div>
  </div>

  <!-- Partial Exit Modal (global) -->
  <div id="ob-partial-modal">
    <div class="ob-modal-box">
      <div style="font-family:Orbitron,sans-serif;font-size:0.85rem;color:var(--cyan);letter-spacing:2px;margin-bottom:18px;">⚡ PARTIAL EXIT</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--dim);margin-bottom:6px;">
        Trade: <span id="ob-pe-symbol" style="color:var(--gold);font-weight:700;"></span>
        &nbsp;|&nbsp; Total Qty: <span id="ob-pe-total-qty" style="color:var(--text);"></span>
      </div>
      <div style="margin-bottom:18px;">
        <label style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;display:block;margin-bottom:6px;">EXIT QUANTITY</label>
        <input type="number" id="ob-pe-qty" min="1"
          style="width:100%;box-sizing:border-box;background:var(--bg);border:1px solid var(--cyan);
          color:var(--gold);padding:8px 12px;font-family:'JetBrains Mono',monospace;font-size:1rem;outline:none;border-radius:4px;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);margin-top:6px;">Default: 50% of position. Market exit price will be used.</div>
      </div>
      <div style="display:flex;gap:10px;">
        <button id="ob-pe-confirm-btn" onclick="confirmPartialExit()"
          style="flex:1;padding:10px;background:linear-gradient(135deg,rgba(41,98,255,0.2),rgba(41,98,255,0.08));
          border:1px solid var(--cyan);color:var(--cyan);font-family:Share Tech Mono,monospace;
          font-size:0.72rem;letter-spacing:1px;cursor:pointer;border-radius:4px;">✓ CONFIRM EXIT</button>
        <button onclick="closePartialModal()"
          style="padding:10px 20px;background:transparent;border:1px solid var(--border);
          color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.72rem;cursor:pointer;border-radius:4px;">CANCEL</button>
      </div>
    </div>
  </div>

</div>
"""

JS = r"""
// ══════════════════════════════════════════════════════════════
// PORTFOLIO & ORDER BOOK JAVASCRIPT
// ══════════════════════════════════════════════════════════════

function portfolioTab(tab) {
  const tabs = {
    ptf:       { el: 'ptf-section-holdings',  btn: 'ptf-tab-holdings' },
    orderbook: { el: 'ptf-section-orderbook', btn: 'ptf-tab-ob' },
  };
  Object.keys(tabs).forEach(k => {
    const c = tabs[k];
    const el = document.getElementById(c.el);
    const btn = document.getElementById(c.btn);
    if (!el || !btn) return;
    if (k === tab) {
      el.style.display = 'block';
      btn.style.background = k === 'ptf' ? 'rgba(255,165,0,0.15)' : 'rgba(41,98,255,0.15)';
      btn.style.borderColor = k === 'ptf' ? 'orange' : 'var(--cyan)';
      btn.style.color = k === 'ptf' ? 'orange' : 'var(--cyan)';
    } else {
      el.style.display = 'none';
      btn.style.background = 'transparent';
      btn.style.borderColor = 'var(--border)';
      btn.style.color = 'var(--dim)';
    }
  });
  if (tab === 'ptf') loadPortfolio();
  if (tab === 'orderbook') loadOrderBook();
}

// ── Export CSV ────────────────────────────────────────────────
function exportTradeCSV() {
  window.location = '/api/portfolio_csv';
}

// ══════════════════════════════════════════════════════════════
// ORDER BOOK FUNCTIONS
// ══════════════════════════════════════════════════════════════
window._obFilter = 'OPEN';
window._obCurrentId = null;

function obSetFilter(f) {
  window._obFilter = f;
  ['OPEN','CLOSED','ALL'].forEach(k => {
    const btn = document.getElementById('ob-filter-' + k);
    if (!btn) return;
    const active = k === f;
    btn.style.background  = active ? 'rgba(41,98,255,0.15)' : 'transparent';
    btn.style.color       = active ? 'var(--cyan)' : 'var(--dim)';
  });
  loadOrderBook();
}

function managePosition(id) {
  window._obFilter = 'OPEN';
  window._obManageTarget = { id: String(id) };
  ['OPEN','CLOSED','ALL'].forEach(k => {
    const btn = document.getElementById('ob-filter-' + k);
    if (!btn) return;
    const active = k === 'OPEN';
    btn.style.background = active ? 'rgba(41,98,255,0.15)' : 'transparent';
    btn.style.color = active ? 'var(--cyan)' : 'var(--dim)';
  });
  portfolioTab('orderbook');
}

async function loadOrderBook() {
  const listEl = document.getElementById('ob-list');
  const summEl = document.getElementById('ob-summary-bar');
  if (!listEl) return;
  listEl.innerHTML = '<div style="padding:32px;text-align:center;color:var(--dim);font-size:0.8rem;">Loading…</div>';

  try {
    const filter = window._obFilter || 'OPEN';
    const endpoint = filter === 'CLOSED' ? 'portfolio_get?filter=CLOSED' : 'portfolio_get';
    const res = await api(endpoint.replace('?filter=CLOSED',''), filter === 'CLOSED' ? {filter:'CLOSED'} : {});
    if (!res || !res.ok) {
      listEl.innerHTML = `<div class="err">${(res && res.error) || 'Failed to load order book'}</div>`;
      return;
    }

    let trades = res.trades || [];
    if (filter === 'OPEN')   trades = trades.filter(t => t.status !== 'CLOSED');
    if (filter === 'CLOSED') trades = trades.filter(t => t.status === 'CLOSED');

    // Update badge
    const badge = document.getElementById('ob-count-badge');
    if (badge) badge.textContent = trades.length;

    if (trades.length === 0) {
      listEl.innerHTML = `<div style="padding:32px;text-align:center;color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.78rem;">
        No ${filter !== 'ALL' ? filter.toLowerCase() + ' ' : ''}orders found.</div>`;
      if (summEl) summEl.style.display = 'none';
      return;
    }

    // Compute summary
    let totalPnl = 0, openCount = 0, closedCount = 0;
    trades.forEach(t => {
      totalPnl += (t.realized_pnl || 0);
      if (t.status === 'CLOSED') closedCount++; else openCount++;
    });

    if (summEl) {
      summEl.style.display = 'flex';
      const pnlCol = totalPnl >= 0 ? 'var(--green)' : 'var(--red)';
      summEl.innerHTML = `
        <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);letter-spacing:1px;">TOTAL: <span style="color:var(--text);font-weight:700;">${trades.length}</span></div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);letter-spacing:1px;">OPEN: <span style="color:var(--cyan);font-weight:700;">${openCount}</span></div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);letter-spacing:1px;">CLOSED: <span style="color:var(--dim);font-weight:700;">${closedCount}</span></div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:var(--dim);letter-spacing:1px;">REALIZED P&L: <span style="color:${pnlCol};font-weight:700;">${totalPnl >= 0 ? '+' : ''}₹${Math.abs(totalPnl).toLocaleString('en-IN',{maximumFractionDigits:2})}</span></div>`;
    }

    const fmt2 = v => v != null ? v.toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2}) : '—';
    let html = '';
    trades.forEach(t => {
      // Position IDs are UUID strings; serialize them as JavaScript string literals
      // before embedding them in the inline action handlers.
      const jsId = JSON.stringify(String(t.id));
      const jsSymbol = JSON.stringify(String(t.symbol || ''));
      const isClosed = t.status === 'CLOSED';
      const pnl = isClosed ? (t.realized_pnl || 0) : 0;
      const pnlCol = pnl >= 0 ? 'var(--green)' : 'var(--red)';
      const pnlStr = isClosed
        ? `<span style="color:${pnlCol};font-weight:700;">${pnl >= 0 ? '+' : ''}₹${fmt2(Math.abs(pnl))}</span>`
        : '<span style="color:var(--dim);">—</span>';

      const statusColor = isClosed ? 'var(--dim)' : 'var(--cyan)';
      const statusBg    = isClosed ? 'rgba(255,255,255,0.05)' : 'rgba(41,98,255,0.12)';
      const typeTag     = (t.inv_type || 'swing').toUpperCase().slice(0,3);

      // Action buttons — disabled for closed
      let actionHtml = '';
      if (!isClosed) {
        actionHtml = `
          <button onclick="modifyOrder(${jsId})"
            style="padding:3px 8px;background:transparent;border:1px solid var(--cyan);color:var(--cyan);
            font-size:0.6rem;cursor:pointer;border-radius:2px;font-family:Share Tech Mono,monospace;margin-right:3px;">✎ MOD</button>
          <button onclick="partialExit(${jsId},${jsSymbol},${Number(t.shares) || 0})"
            style="padding:3px 8px;background:transparent;border:1px solid var(--gold);color:var(--gold);
            font-size:0.6rem;cursor:pointer;border-radius:2px;font-family:Share Tech Mono,monospace;margin-right:3px;">½ PART</button>
          <button onclick="closeOrder(${jsId},${Number(t.entry_price) || 0})"
            style="padding:3px 8px;background:transparent;border:1px solid var(--red);color:var(--red);
            font-size:0.6rem;cursor:pointer;border-radius:2px;font-family:Share Tech Mono,monospace;margin-right:3px;">✕ CLOSE</button>
          <button onclick="deleteOrder(${jsId})"
            style="padding:3px 8px;background:transparent;border:1px solid rgba(255,255,255,0.15);color:var(--dim);
            font-size:0.6rem;cursor:pointer;border-radius:2px;font-family:Share Tech Mono,monospace;">🗑</button>`;
      } else {
        actionHtml = `<span style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);">CLOSED</span>`;
      }

      html += `<div class="ob-row" id="ob-row-${t.id}">
        <div style="color:var(--gold);font-weight:700;">${t.symbol}</div>
        <div><span style="font-size:0.58rem;padding:2px 5px;background:rgba(255,255,255,0.07);border-radius:2px;color:var(--dim);">${typeTag}</span></div>
        <div style="text-align:right;">₹${fmt2(t.entry_price)}</div>
        <div style="text-align:right;color:var(--red);">₹${fmt2(t.stop_loss)}</div>
        <div style="text-align:right;color:var(--green);">₹${fmt2(t.target1)}</div>
        <div style="text-align:right;color:var(--green);">₹${fmt2(t.target2)}</div>
        <div style="text-align:right;">${t.shares || 0}</div>
        <div style="text-align:center;"><span style="font-size:0.6rem;padding:2px 6px;background:${statusBg};color:${statusColor};border-radius:3px;">${t.status || 'OPEN'}</span></div>
        <div style="text-align:right;">${pnlStr}</div>
        <div style="text-align:right;">${actionHtml}</div>
      </div>`;
    });
    listEl.innerHTML = html;
    const manageTarget = window._obManageTarget;
    if (manageTarget) {
      const targetRow = document.getElementById('ob-row-' + manageTarget.id);
      if (targetRow) {
        targetRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
        targetRow.style.outline = '2px solid var(--cyan)';
        targetRow.style.outlineOffset = '3px';
      }
      window._obManageTarget = null;
    }
  } catch(e) {
    if (listEl) listEl.innerHTML = `<div class="err">Error: ${e.message}</div>`;
  }
}

function modifyOrder(id) {
  const row = document.getElementById('ob-row-' + id);
  if (!row) return;
  if (row.classList.contains('ob-editing')) return;

  const cells = row.querySelectorAll('div');
  const slText  = cells[3].textContent.replace('₹','').trim();
  const t1Text  = cells[4].textContent.replace('₹','').trim();
  const t2Text  = cells[5].textContent.replace('₹','').trim();

  row.classList.add('ob-editing');
  cells[3].innerHTML = `<input class="ob-input" id="ob-sl-${id}" value="${slText}" type="number" step="0.05">`;
  cells[4].innerHTML = `<input class="ob-input" id="ob-t1-${id}" value="${t1Text}" type="number" step="0.05">`;
  cells[5].innerHTML = `<input class="ob-input" id="ob-t2-${id}" value="${t2Text}" type="number" step="0.05">`;
  cells[9].innerHTML = `
    <button onclick="saveOrderModify(${JSON.stringify(String(id))})"
      style="padding:3px 8px;background:rgba(41,98,255,0.2);border:1px solid var(--cyan);color:var(--cyan);
      font-size:0.62rem;cursor:pointer;border-radius:2px;font-family:Share Tech Mono,monospace;margin-right:3px;">✓ SAVE</button>
    <button onclick="cancelOrderModify(${JSON.stringify(String(id))})"
      style="padding:3px 8px;background:transparent;border:1px solid var(--border);color:var(--dim);
      font-size:0.62rem;cursor:pointer;border-radius:2px;font-family:Share Tech Mono,monospace;">✕ CANCEL</button>`;
}

function cancelOrderModify(id) {
  loadOrderBook();
}

async function saveOrderModify(id) {
  const sl = parseFloat(document.getElementById('ob-sl-' + id)?.value || '0');
  const t1 = parseFloat(document.getElementById('ob-t1-' + id)?.value || '0');
  const t2 = parseFloat(document.getElementById('ob-t2-' + id)?.value || '0');
  if (!sl || !t1 || !t2) { alert('Please enter valid SL, T1 and T2 values.'); return; }
  try {
    const res = await api('portfolio_modify', { id, stop_loss: sl, target1: t1, target2: t2 });
    if (res && res.ok) {
      loadOrderBook();
    } else {
      alert('Modify failed: ' + ((res && res.error) || 'Unknown error'));
    }
  } catch(e) {
    alert('Error: ' + e.message);
  }
}

async function closeOrder(id, cmp) {
  const fallback = Number(cmp) || 0;
  try {
    const row = document.getElementById('ob-row-' + id);
    const symbol = row?.firstElementChild?.textContent?.trim() || '';
    let price = 0;
    if (symbol) {
      const quote = await api('price', {symbol});
      price = Number(quote && (quote.price || quote.close || quote.ltp)) || 0;
    }
    price = price || fallback;
    if (!Number.isFinite(price) || price <= 0) { alert('Market price unavailable. Refresh the order book and retry.'); return; }
    if (!confirm(`Close order #${id} (${symbol || 'position'}) at market price ₹${price.toFixed(2)}?`)) return;
    const res = await api('portfolio_close', { id, exit_price: price });
    if (res && res.ok) {
      await Promise.all([loadOrderBook(), loadPortfolio()]);
    } else {
      alert('Close failed: ' + ((res && res.error) || 'Unknown'));
    }
  } catch(e) {
    alert('Error: ' + e.message);
  }
}

async function deleteOrder(id) {
  if (!confirm(`Permanently delete order #${id}? This cannot be undone.`)) return;
  try {
    const res = await api('portfolio_delete', { id });
    if (res && res.ok) {
      loadOrderBook();
      loadPortfolio();
    } else {
      alert('Delete failed: ' + ((res && res.error) || 'Unknown'));
    }
  } catch(e) {
    alert('Error: ' + e.message);
  }
}

function partialExit(id, symbol, totalQty) {
  window._obCurrentId = id;
  const modal = document.getElementById('ob-partial-modal');
  if (!modal) return;
  document.getElementById('ob-pe-symbol').textContent    = symbol;
  document.getElementById('ob-pe-total-qty').textContent = totalQty;
  const qtyInput = document.getElementById('ob-pe-qty');
  qtyInput.value = Math.max(1, Math.floor(totalQty / 2));
  qtyInput.max   = totalQty;
  modal.classList.add('active');
}

function closePartialModal() {
  const modal = document.getElementById('ob-partial-modal');
  if (modal) modal.classList.remove('active');
  window._obCurrentId = null;
}

async function confirmPartialExit() {
  const id    = window._obCurrentId;
  const qty   = parseInt(document.getElementById('ob-pe-qty')?.value || '0');
  if (!id || !qty || qty <= 0) { alert('Invalid quantity.'); return; }
  try {
    const pos = (window._ptfRows || []).find(r => String(r.t.id) === String(id));
    let exitPrice = pos && Number(pos.cmp);
    if (!exitPrice || !Number.isFinite(exitPrice)) {
      const symbol = document.getElementById('ob-pe-symbol')?.textContent || '';
      const price = await api('price', {symbol});
      exitPrice = Number(price && (price.close || price.price || price.ltp));
    }
    if (!exitPrice || !Number.isFinite(exitPrice) || exitPrice <= 0) { alert('Could not get a valid market exit price. Refresh and try again.'); return; }
    const res = await api('portfolio_partial_exit', { id: String(id), shares: qty, exit_price: exitPrice });
    if (res && res.ok) {
      closePartialModal();
      await Promise.all([loadOrderBook(), loadPortfolio()]);
    } else {
      alert('Partial exit failed: ' + ((res && res.error) || 'Unknown'));
    }
  } catch(e) {
    alert('Error: ' + e.message);
  }
}

// ══════════════════════════════════════════════════════════════
// DEMAT PORTFOLIO FUNCTIONS
// ══════════════════════════════════════════════════════════════
async function loadPortfolio() {
  const listEl = document.getElementById('ptf-list');
  if (!listEl) return;
  listEl.innerHTML = '<div style="padding:24px;text-align:center;color:var(--dim);font-size:0.8rem;">Loading portfolio…</div>';

  try {
    const res = await api('portfolio_get', {});
    if (!res || !res.ok) {
      listEl.innerHTML = '<div class="err">' + ((res && res.error) || 'Failed to load portfolio') + '</div>';
      return;
    }

    const trades = res.trades || [];
    const open   = trades.filter(t => t.status !== 'CLOSED');
    const closed = trades.filter(t => t.status === 'CLOSED');

    const _today = (typeof today !== 'undefined') ? today : new Date().toISOString().slice(0, 10);

    const cmpMap  = {};
    const prevMap = {};
    await Promise.all(open.map(async t => {
      try {
        const px = await api('price', { symbol: t.symbol, date: _today });
        const close = px && px.close && px.close > 0 ? px.close : null;
        const pct = px && Number(px.change_pct);
        const derivedPrev = close && Number.isFinite(pct) && (1 + pct / 100) > 0
          ? close / (1 + pct / 100) : null;
        const prev  = px && px.prev_close && px.prev_close > 0 ? px.prev_close : derivedPrev;
        cmpMap[t.symbol]  = close  || (t.entry_price > 0 ? t.entry_price : null);
        prevMap[t.symbol] = prev;
      } catch {
        cmpMap[t.symbol]  = t.entry_price > 0 ? t.entry_price : null;
        prevMap[t.symbol] = null;
      }
    }));

    let invested = 0, current = 0, unrealized = 0, realized = 0, todayGain = 0;
    const rows = [];
    for (const t of open) {
      const entryPx = t.entry_price || 0;
      const cmp     = cmpMap[t.symbol] || entryPx;
      const prev    = prevMap[t.symbol] || cmp;
      const shares  = t.shares || 0;
      const inv     = entryPx * shares;
      const cur     = cmp * shares;
      const direction = (t.inv_type || '').toLowerCase() === 'short' ? -1 : 1;
      const pnl     = (cmp - entryPx) * shares * direction;
      const pnlPct  = inv > 0 ? (pnl / inv * 100) : 0;
      const tg      = prev > 0 ? (cmp - prev) * shares * direction : 0;
      invested   += inv;
      current    += cur;
      unrealized += pnl;
      todayGain  += tg;
      rows.push({ t, cmp, inv, cur, pnl, pnlPct, tg });
    }
    for (const t of closed) realized += (t.realized_pnl || 0);

    window._ptfRows    = rows;
    window._ptfSort    = window._ptfSort || { key: 'name', dir: 1 };
    window._ptfFilter  = window._pendingPortfolioReview?.symbol || '';
    const searchEl = document.getElementById('ptf-search');
    if (searchEl && window._ptfFilter) searchEl.value = window._ptfFilter;
    window._ptfView    = window._ptfView || 'sector';
    window._ptfDrivers = window._ptfDrivers || 'gainers';

    const fmt = v => '₹' + Math.abs(v).toLocaleString('en-IN', { maximumFractionDigits: 2 });
    const pct = (v, base) => base > 0 ? (v/base*100).toFixed(2) + '%' : '0%';

    const invEl = document.getElementById('ptf-invested');
    const curEl = document.getElementById('ptf-current');
    const cntEl = document.getElementById('ptf-count');
    const relEl = document.getElementById('ptf-realized');
    if (invEl) invEl.textContent = fmt(invested);
    if (curEl) curEl.textContent  = fmt(current);
    if (cntEl) cntEl.textContent    = open.length;
    if (relEl) {
      relEl.textContent = fmt(realized);
      relEl.style.color = realized >= 0 ? 'var(--green)' : 'var(--red)';
    }

    const unrEl    = document.getElementById('ptf-unrealized');
    const unrPctEl = document.getElementById('ptf-unrealized-pct');
    if (unrEl) {
      unrEl.textContent = (unrealized >= 0 ? '+' : '-') + fmt(unrealized);
      unrEl.style.color = unrealized >= 0 ? 'var(--green)' : 'var(--red)';
    }
    if (unrPctEl) {
      unrPctEl.textContent = (unrealized >= 0 ? '+' : '') + pct(unrealized, invested);
      unrPctEl.style.color = unrealized >= 0 ? 'var(--green)' : 'var(--red)';
    }
    const todayEl    = document.getElementById('ptf-today');
    const todayPctEl = document.getElementById('ptf-today-pct');
    if (todayEl) {
      todayEl.textContent = (todayGain >= 0 ? '+' : '-') + fmt(todayGain);
      todayEl.style.color = todayGain >= 0 ? 'var(--green)' : 'var(--red)';
    }
    if (todayPctEl) {
      todayPctEl.textContent = (todayGain >= 0 ? '+' : '') + pct(todayGain, current);
      todayPctEl.style.color = todayGain >= 0 ? 'var(--green)' : 'var(--red)';
    }

    ptfRenderTable();
    if (window._pendingPortfolioReview) window._pendingPortfolioReview = null;
    ptfRenderSectors();
    ptfRenderDrivers();

    if (open.length === 0) {
      listEl.innerHTML = '<div style="padding:32px;text-align:center;color:var(--dim);font-size:0.82rem;">' +
        'No open positions. Run the Advisor, Scanner, or Trade Simulation to deploy trades.</div>';
    }
  } catch (e) {
    listEl.innerHTML = '<div class="err">' + e.message + '</div>';
  }
}

function ptfRenderTable() {
  const listEl = document.getElementById('ptf-list');
  if (!listEl || !window._ptfRows) return;

  const q    = (window._ptfFilter || '').toLowerCase();
  const rows = window._ptfRows.filter(r =>
    !q || r.t.symbol.toLowerCase().includes(q) ||
    (r.t.name || '').toLowerCase().includes(q)
  );

  const { key, dir } = window._ptfSort;
  rows.sort((a, b) => {
    let va, vb;
    if (key === 'name') { va = a.t.symbol; vb = b.t.symbol; return dir * va.localeCompare(vb); }
    if (key === 'qty')  { va = a.t.shares;  vb = b.t.shares; }
    if (key === 'inv')  { va = a.inv;        vb = b.inv; }
    if (key === 'cur')  { va = a.cur;        vb = b.cur; }
    if (key === 'pnl')  { va = a.pnl;        vb = b.pnl; }
    return dir * (va - vb);
  });

  if (rows.length === 0) {
    listEl.innerHTML = '<div style="padding:24px;text-align:center;color:var(--dim);font-size:0.8rem;">No matching holdings.</div>';
    return;
  }

  const fmt2  = v => v.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const fmtR  = v => v.toLocaleString('en-IN', { maximumFractionDigits: 0 });
  const color = v => v >= 0 ? 'var(--green)' : 'var(--red)';
  const sign  = v => v >= 0 ? '+' : '';

  let html = '';
  for (const { t, cmp, inv, cur, pnl, pnlPct } of rows) {
    const badge = t.protected
      ? '<span style="font-size:0.5rem;background:rgba(0,255,136,0.1);color:var(--green);padding:1px 4px;border:1px solid var(--green);border-radius:2px;margin-left:4px;">🛡</span>'
      : '';
    const typeTag = '<span style="font-size:0.55rem;background:rgba(255,255,255,0.06);color:var(--dim);padding:1px 5px;border-radius:3px;margin-left:4px;">' + (t.inv_type||'swing').toUpperCase() + '</span>';
    const sl  = t.stop_loss  || 0;
    const t1  = t.target1    || 0;
    const t2  = t.target2    || 0;
    const ep  = t.entry_price|| 0;
    const sh  = t.shares     || 0;
    const pnlAbs = Math.abs(pnl);
    const exitCmp = cmp > 0 ? cmp : ep;
    html += '<div class="ptf-row">' +
      '<div>' +
        '<div style="font-weight:600;font-size:0.82rem;color:var(--text);">' +
          '<button type="button" onclick="event.stopPropagation();openSymbolChart(' + JSON.stringify(String(t.symbol || '')) + ')" ' +
            'style="padding:0;border:0;background:none;color:inherit;font:inherit;font-weight:inherit;cursor:pointer;text-decoration:underline;text-decoration-color:rgba(255,255,255,0.25);">' +
            t.symbol + '</button>' + badge + typeTag + '</div>' +
        '<div style="font-size:0.62rem;color:var(--dim);margin-top:2px;">' +
          (sl  > 0 ? 'SL ₹' + fmt2(sl)  + ' &nbsp;·&nbsp; ' : '') +
          (t1  > 0 ? 'T1 ₹' + fmt2(t1)  + ' &nbsp;·&nbsp; ' : '') +
          (t2  > 0 ? 'T2 ₹' + fmt2(t2)  : '') +
          (t.entry_date ? '<span style="margin-left:6px;opacity:0.5;">' + (t.entry_date||'').slice(0,10) + '</span>' : '') +
        '</div>' +
      '</div>' +
      '<div style="text-align:right;font-size:0.82rem;color:var(--text);">' + fmtR(sh) + '</div>' +
      '<div style="text-align:right;font-size:0.82rem;color:var(--text);">₹' + (ep > 0 ? fmt2(ep) : '—') + '</div>' +
      '<div style="text-align:right;font-size:0.82rem;color:var(--text);">₹' + (exitCmp > 0 ? fmt2(exitCmp) : '—') + '</div>' +
      '<div style="text-align:right;font-size:0.82rem;color:var(--text);">' + (inv > 0 ? '₹' + fmtR(inv) : '—') + '</div>' +
      '<div style="text-align:right;font-size:0.82rem;color:var(--text);">' + (cur > 0 ? '₹' + fmtR(cur) : '—') + '</div>' +
      '<div style="text-align:right;">' +
        '<div style="font-size:0.82rem;font-weight:600;color:' + color(pnl) + ';">' +
          sign(pnl) + '₹' + fmt2(pnlAbs) +
        '</div>' +
        '<div style="font-size:0.62rem;color:' + color(pnl) + ';">' + sign(pnlPct) + pnlPct.toFixed(2) + '%</div>' +
      '</div>' +
      '<div style="text-align:right;">' +
        '<button onclick="closePosition(' + JSON.stringify(String(t.id)) + ',' + exitCmp + ')" ' +
          'style="padding:5px 10px;background:rgba(239,68,68,0.12);border:1px solid var(--red);' +
          'color:var(--red);border-radius:4px;font-size:0.68rem;font-weight:700;cursor:pointer;margin-right:4px;">EXIT</button>' +
        '<button onclick="managePosition(' + JSON.stringify(String(t.id)) + ')" ' +
          'style="padding:5px 8px;background:transparent;border:1px solid var(--border);' +
          'color:var(--cyan);border-radius:4px;font-size:0.65rem;cursor:pointer;">MANAGE</button>' +
      '</div>' +
    '</div>';
  }
  listEl.innerHTML = html;
}

function ptfFilterHoldings() {
  window._ptfFilter = (document.getElementById('ptf-search') || {}).value || '';
  ptfRenderTable();
}

function ptfSort(key) {
  if (!window._ptfSort) window._ptfSort = { key, dir: 1 };
  else if (window._ptfSort.key === key) window._ptfSort.dir *= -1;
  else window._ptfSort = { key, dir: 1 };
  ptfRenderTable();
}

function ptfToggleSelectExit() {
  alert('Select & Exit: click individual Exit buttons or use Square-Off on each row.');
}

function ptfGroupBy() {
  alert('Group By: positions are shown individually. Sector view is in Portfolio Analytics below.');
}

function ptfSetView(v) {
  window._ptfView = v;
  const title = document.getElementById('ptf-allocation-title');
  const subtitle = document.getElementById('ptf-allocation-subtitle');
  if (title) title.textContent = v === 'cap' ? 'Market Cap Allocation' : 'Sector Allocation';
  if (subtitle) subtitle.textContent = v === 'cap'
    ? 'Portfolio weight and unrealized return by available company market-cap data'
    : 'Portfolio weight and unrealized return by instrument sector';
  const s = document.getElementById('ptf-view-sector');
  const c = document.getElementById('ptf-view-cap');
  if (s) { s.style.background = v==='sector' ? 'rgba(0,212,255,0.15)' : 'transparent'; s.style.color = v==='sector' ? 'var(--cyan)' : 'var(--dim)'; s.style.borderColor = v==='sector' ? 'var(--cyan)' : 'var(--border)'; }
  if (c) { c.style.background = v==='cap'    ? 'rgba(0,212,255,0.15)' : 'transparent'; c.style.color = v==='cap'    ? 'var(--cyan)' : 'var(--dim)'; c.style.borderColor = v==='cap'    ? 'var(--cyan)' : 'var(--border)'; }
  ptfRenderSectors();
}

function ptfRenderSectors() {
  const rows   = window._ptfRows || [];
  const barEl  = document.getElementById('ptf-alloc-bar');
  const listEl = document.getElementById('ptf-sector-bars');
  if (!barEl || !listEl || rows.length === 0) {
    if (listEl) listEl.innerHTML = '<div style="color:var(--dim);font-size:0.75rem;">No holdings to analyse.</div>';
    return;
  }

  const sectorMap = {};
  const byMarketCap = window._ptfView === 'cap';
  for (const { t, inv, cur, pnl } of rows) {
    const sec = byMarketCap
      ? (t.market_cap_band || 'Market cap unavailable')
      : (t.sector || 'Sector unavailable');
    if (!sectorMap[sec]) sectorMap[sec] = { inv: 0, cur: 0, pnl: 0 };
    sectorMap[sec].inv += inv;  sectorMap[sec].cur += cur;  sectorMap[sec].pnl += pnl;
  }
  const totalInv = rows.reduce((s, r) => s + r.inv, 0) || 1;
  const pal = ['#6C4FB3','#A855F7','#EC4899','#3B82F6','#10B981','#F59E0B','#EF4444','#06B6D4'];

  let barHTML = '';
  let i = 0;
  for (const [sec, d] of Object.entries(sectorMap)) {
    const w = (d.inv / totalInv * 100).toFixed(1);
    barHTML += `<div style="width:${w}%;background:${pal[i%pal.length]};display:flex;align-items:center;
      justify-content:center;font-size:0.58rem;color:white;font-weight:600;overflow:hidden;white-space:nowrap;padding:0 4px;"
      title="${sec}: ${w}%">${w}% ${sec}</div>`;
    i++;
  }
  barEl.innerHTML = barHTML;

  const sectors = Object.entries(sectorMap)
    .map(([sec, d], idx) => ({ sec, ...d, pct: d.inv > 0 ? d.pnl / d.inv * 100 : 0, col: pal[idx % pal.length] }))
    .sort((a, b) => b.pct - a.pct);

  let lHTML = '';
  for (const s of sectors) {
    const pctStr = (s.pct >= 0 ? '+' : '') + s.pct.toFixed(2) + '%';
    const col    = s.pct >= 0 ? 'var(--green)' : 'var(--red)';
    const barW   = Math.min(Math.abs(s.pct) * 2, 100);
    lHTML += `
      <div style="margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
          <span style="font-size:0.72rem;color:var(--text);">${s.sec}</span>
          <span style="font-size:0.72rem;color:${col};font-weight:600;">${pctStr}</span>
        </div>
        <div style="display:flex;gap:4px;align-items:center;">
          <div style="height:6px;width:${barW}%;background:${s.col};border-radius:2px;opacity:0.9;"></div>
          <div style="height:6px;width:${barW * 0.7}%;background:${s.col};border-radius:2px;opacity:0.4;"></div>
        </div>
      </div>`;
  }
  listEl.innerHTML = lHTML || '<div style="color:var(--dim);font-size:0.75rem;">No allocation data.</div>';
}

function ptfShowDrivers(mode) {
  window._ptfDrivers = mode;
  const g = document.getElementById('ptf-btn-gainers');
  const l = document.getElementById('ptf-btn-losers');
  if (g) { g.style.background = mode==='gainers' ? 'rgba(0,212,255,0.15)' : 'transparent'; g.style.color = mode==='gainers' ? 'var(--cyan)' : 'var(--dim)'; g.style.borderColor = mode==='gainers' ? 'var(--cyan)' : 'var(--border)'; }
  if (l) { l.style.background = mode==='losers'  ? 'rgba(239,83,80,0.15)' : 'transparent'; l.style.color = mode==='losers'  ? 'var(--red)'  : 'var(--dim)'; l.style.borderColor = mode==='losers'  ? 'var(--red)'  : 'var(--border)'; }
  ptfRenderDrivers();
}

function ptfRenderDrivers() {
  const el   = document.getElementById('ptf-drivers');
  const rows = window._ptfRows || [];
  if (!el) return;

  const mode    = window._ptfDrivers || 'gainers';
  const sorted  = [...rows].sort((a, b) => mode === 'gainers' ? b.pnlPct - a.pnlPct : a.pnlPct - b.pnlPct);
  const display = sorted.slice(0, 5);

  let html = '';
  for (const { t, cmp, pnlPct } of display) {
    const col    = pnlPct >= 0 ? 'var(--green)' : 'var(--red)';
    const wh52   = t.week52_high ? t.week52_high.toFixed(2) : '—';
    const pctStr = (pnlPct >= 0 ? '+' : '') + pnlPct.toFixed(2) + '%';
    html += `
      <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:0;
        padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.04);align-items:center;">
        <div style="font-weight:600;font-size:0.8rem;color:var(--text);">${t.symbol}</div>
        <div style="text-align:right;font-size:0.78rem;color:var(--cyan);">${wh52}</div>
        <div style="text-align:right;font-size:0.78rem;color:var(--text);">${cmp.toFixed(2)}</div>
        <div style="text-align:right;font-size:0.78rem;font-weight:600;color:${col};">${pctStr}</div>
      </div>`;
  }
  el.innerHTML = html || '<div style="color:var(--dim);font-size:0.75rem;padding:12px 0;">No positions to display.</div>';
}

async function closePosition(id, cmp) {
  const holding = (window._ptfRows || []).find(r => String(r.t.id) === String(id));
  const symbol = holding && holding.t.symbol;
  let price = 0;
  if (symbol) {
    try {
      const quote = await api('price', {symbol});
      price = Number(quote && (quote.price || quote.close || quote.ltp)) || 0;
    } catch (_) {}
  }
  price = price || Number(cmp);
  if(!Number.isFinite(price) || price <= 0) { alert('A valid market exit price is not available. Refresh holdings and try again.'); return; }
  if(!confirm(`Square off position at ₹${price.toFixed(2)}?`)) return;
  try {
    const res = await api('portfolio_close', {id: String(id), exit_price: price});
    if(res && res.ok) {
      if (typeof showToast === 'function') showToast(`Position closed. Realized P&L: ₹${Number(res.realized_pnl || 0).toLocaleString('en-IN',{minimumFractionDigits:2})}`, 'success');
      await Promise.all([loadPortfolio(), loadOrderBook()]);
    } else {
      alert("Exit failed: " + ((res && res.error) || 'The server did not confirm the exit.'));
    }
  } catch(e) {
    alert("Error: " + e.message);
  }
}

async function executePaperTrade(sym, type, cmp, shares, sl, t1, t2) {
  if(!confirm(`Execute PAPER TRADE for ${sym}?\nShares: ${shares}\nEntry: ₹${cmp}\nStop Loss: ₹${sl}\nTarget: ₹${t2}`)) return;

  try {
    const res = await api('portfolio_add', {
      symbol: sym,
      inv_type: type,
      entry_price: cmp,
      shares: shares,
      stop_loss: sl,
      target1: t1,
      target2: t2
    });
    if(res.ok) {
      alert("Trade Successfully Added to Demat Portfolio!");
      nav('portfolio');
      setTimeout(()=>portfolioTab('ptf'), 100);
    } else {
      alert("Error executing trade: " + res.error);
    }
  } catch(e) {
    alert("System Error: " + e.message);
  }
}

function initPortfolioPage() {
  loadPortfolio();
}
"""
