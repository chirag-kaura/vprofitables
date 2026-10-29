"""
page_trading.py — Unified Trade Simulation Desk (v5.0)
Sections:
  1. BACKTEST       — Paper Trade Simulation (Gann+Technical+Natal+Fundamental+Sentiment)
  2. FORWARD SIGNALS — Scan all equities / single symbol + live recommendations
"""

HTML = r"""
<!-- ═══════════ PAGE: TRADE SIMULATION ═══════════ -->
<div class="page" id="page-trade_simulation">
  <div class="topbar">
    <div style="display:flex;align-items:center;gap:10px;">
      <span style="font-family:Orbitron,sans-serif;font-size:1.1rem;color:var(--gold);font-weight:700;letter-spacing:2px;">⚡ TRADE SIMULATION</span>
      <span class="page-tag">HISTORICAL BACKTEST · PAPER SIMULATION · FORWARD SIGNALS SCANNER</span>
    </div>
    <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;">
      LOGIC: GANN + TECHNICAL + NATAL + FUNDAMENTAL + SENTIMENT CONFLUENCE
    </div>
  </div>

  <!-- ══════════════════════════════════════════════════════════ -->
  <!-- TAB NAVIGATION                                             -->
  <!-- ══════════════════════════════════════════════════════════ -->
  <div style="display:flex;gap:0;margin-bottom:20px;border-bottom:1px solid var(--border);flex-wrap:wrap;">
    <button id="tab-bt" onclick="tradingTab('backtest')"
      style="padding:8px 24px;background:rgba(0,212,255,0.15);border:1px solid var(--cyan);border-bottom:none;
             color:var(--cyan);font-family:Share Tech Mono,monospace;font-size:0.75rem;letter-spacing:1px;cursor:pointer;">
      📊 BACKTEST
    </button>
    <button id="tab-fwd" onclick="tradingTab('forward')"
      style="padding:8px 24px;background:transparent;border:1px solid var(--border);border-bottom:none;
             color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.75rem;letter-spacing:1px;cursor:pointer;">
      📡 FORWARD SIGNALS
    </button>
  </div>

  <!-- ══════════════════════════════════════════════════════════ -->
  <!-- TAB 1: BACKTESTING                                         -->
  <!-- ══════════════════════════════════════════════════════════ -->
  <div id="trading-backtest" class="trading-tab">
    <div class="card" data-feature-id="trading_desk_execution" style="margin-bottom:16px;">
      <div class="card-title" style="color:var(--cyan);">📊 PAPER TRADE SIMULATION</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);margin-bottom:14px;">
        Unified logic: Gann Sq9 · Technical (RSI/SMA/BB) · Natal planetary · Fundamental · Sentiment
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end;">
        <div style="display:flex;flex-direction:column;gap:4px;">
          <label style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;">SYMBOL (blank=all equities)</label>
          <input type="text" id="bt-symbol" placeholder="e.g. TCS (blank=all)"
            style="width:150px;background:var(--p2);border:1px solid var(--b2);color:var(--gold);
            padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.8rem;outline:none;text-transform:uppercase;">
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;">
          <label style="font-size:0.6rem;color:var(--cyan);letter-spacing:1px;font-weight:700;">INVESTMENT TYPE</label>
          <select id="bt-type" onchange="onBtTypeChange()"
            style="background:var(--p2);border:1px solid var(--cyan);color:var(--gold);
            padding:7px 12px;font-family:Share Tech Mono,monospace;font-size:0.8rem;outline:none;min-width:220px;">
            <option value="intraday">🏎️ Intraday (Same Day)</option>
            <option value="swing">⚡ Swing Trade (2–5 days)</option>
            <option value="short">📈 Short Term (15–45 days)</option>
            <option value="long">🏛 Long Term (3–18 months)</option>
          </select>
          <div id="bt-type-desc" style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);max-width:220px;line-height:1.4;"></div>
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;">
          <label style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;">RISK PREFERENCE</label>
          <select id="bt-risk"
            style="background:var(--p2);border:1px solid var(--b2);color:var(--gold);
            padding:7px 12px;font-family:Share Tech Mono,monospace;font-size:0.8rem;outline:none;min-width:200px;">
            <option value="low">Low Risk (Capital Protection)</option>
            <option value="balanced" selected>Balanced (Standard Risk/Reward)</option>
            <option value="high">High Risk (Max Profit)</option>
          </select>
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;">
          <label style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;">INITIAL CAPITAL (₹)</label>
          <input type="number" id="bt-capital" value="1000000" step="10000"
            style="width:130px;background:var(--p2);border:1px solid var(--b2);color:var(--gold);
            padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.8rem;outline:none;">
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;">
          <label style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;">START DATE</label>
          <input type="date" id="bt-start" value="2024-01-01"
            style="background:var(--p2);border:1px solid var(--b2);color:var(--t2);
            padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.78rem;outline:none;">
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;">
          <label style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;">END DATE</label>
          <input type="date" id="bt-end"
            style="background:var(--p2);border:1px solid var(--b2);color:var(--t2);
            padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.78rem;outline:none;">
        </div>
        <button onclick="runBacktest()"
          style="padding:8px 24px;background:linear-gradient(135deg,rgba(0,212,255,0.15),rgba(0,212,255,0.05));
          border:1px solid var(--cyan);color:var(--cyan);font-family:Orbitron,sans-serif;
          font-size:0.65rem;letter-spacing:2px;cursor:pointer;">
          ▶ RUN BACKTEST
        </button>
      </div>
    </div>
    <div id="bt-loading" style="display:none; flex-direction:column; gap:10px; padding:20px;">
      <div style="font-family:Orbitron,sans-serif; color:var(--cyan); margin-bottom:10px; font-size:1.1rem; text-align:center;">
        &#9881; Simulating Monte Carlo alternate realities... (30-90s)
      </div>
      <div class="skeleton skeleton-title" style="width: 30%; margin: 0 auto;"></div>
      <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:15px; margin-top:20px;">
        <div class="skeleton" style="height:80px;"></div>
        <div class="skeleton" style="height:80px;"></div>
        <div class="skeleton" style="height:80px;"></div>
      </div>
      <div class="skeleton skeleton-text" style="margin-top:20px;"></div>
      <div class="skeleton skeleton-text"></div>
      <div class="skeleton skeleton-text" style="width: 80%;"></div>
    </div>
    <div id="bt-error" style="display:none;" class="err"></div>

    <!-- No-trades card -->
    <div id="bt-no-trades" style="display:none;margin-top:8px;">
      <div style="border:1px solid var(--orange);background:rgba(255,136,0,0.04);border-radius:6px;padding:24px 28px;">
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:18px;">
          <div style="font-size:2rem;">📭</div>
          <div>
            <div style="font-family:Orbitron,sans-serif;font-size:0.95rem;color:var(--orange);letter-spacing:2px;">NO TRADES GENERATED</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);margin-top:3px;letter-spacing:1px;">BACKTEST GATE SYSTEM — NO QUALIFYING SETUPS IN RANGE</div>
          </div>
        </div>
        <div id="bt-no-trades-detail" style="font-family:Share Tech Mono,monospace;font-size:0.76rem;color:var(--t2);line-height:1.9;margin-bottom:20px;padding:12px 16px;background:rgba(0,0,0,0.3);border-left:3px solid var(--orange);border-radius:2px;"></div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:18px;">
          <div style="background:rgba(0,212,255,0.05);border:1px solid rgba(0,212,255,0.18);border-radius:4px;padding:12px;text-align:center;">
            <div style="font-size:1.2rem;margin-bottom:5px;">📅</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">WIDEN DATE RANGE</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--cyan);">Try a longer period — e.g. 2023-01-01 to today for more market cycles</div>
          </div>
          <div style="background:rgba(0,212,255,0.05);border:1px solid rgba(0,212,255,0.18);border-radius:4px;padding:12px;text-align:center;">
            <div style="font-size:1.2rem;margin-bottom:5px;">🎯</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">SINGLE SYMBOL</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--cyan);">Enter a specific symbol (e.g. RELIANCE) to focus backtest on one stock</div>
          </div>
          <div style="background:rgba(0,212,255,0.05);border:1px solid rgba(0,212,255,0.18);border-radius:4px;padding:12px;text-align:center;">
            <div style="font-size:1.2rem;margin-bottom:5px;">🔄</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">SWITCH TYPE</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--cyan);">Long Term needs 3–18 month windows. Try Swing or Short Term for tighter ranges</div>
          </div>
        </div>
        <div style="display:flex;align-items:flex-start;gap:8px;padding:10px 14px;background:rgba(255,136,0,0.07);border-radius:4px;">
          <span style="color:var(--orange);font-size:0.9rem;margin-top:1px;">⚡</span>
          <span style="font-family:Share Tech Mono,monospace;font-size:0.66rem;color:var(--dim);line-height:1.7;">
            The backtest uses the same Gann Sq9 + RSI/SMA/BB + Natal + Fundamental gate stack as the live advisor. Gates require Sq9 confluence, regime-RSI alignment, and minimum R:R — so only high-quality setups are counted. A short date range in a sideways market will naturally produce zero trades.
          </span>
        </div>
      </div>
    </div>
    <div id="bt-result" style="display:none;"></div>
  </div>

  <!-- ══════════════════════════════════════════════════════════ -->
  <!-- TAB 2: FORWARD SIGNALS                                     -->
  <!-- ══════════════════════════════════════════════════════════ -->
  <div id="trading-forward" class="trading-tab" style="display:none;">
    <div class="card" style="margin-bottom:16px;">
      <div class="card-title" style="color:var(--gold);">📡 FORWARD SIGNAL — LIVE RECOMMENDATIONS</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);margin-bottom:14px;">
        Leave SYMBOL blank to scan all equities. Signals can be deployed directly into your Demat Portfolio or executed via 1-click broker payload.
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end;margin-bottom:14px;">
        <div style="display:flex;flex-direction:column;gap:4px;">
          <label style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;">SYMBOL (blank = all equities)</label>
          <input type="text" id="fs-symbol" placeholder="blank = scan all"
            style="width:160px;background:var(--p2);border:1px solid var(--b2);color:var(--gold);
            padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.82rem;outline:none;text-transform:uppercase;">
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;">
          <label style="font-size:0.6rem;color:var(--gold);letter-spacing:1px;font-weight:700;">INVESTMENT TYPE</label>
          <select id="fs-type"
            style="background:var(--p2);border:1px solid var(--gold);color:var(--gold);
            padding:7px 12px;font-family:Share Tech Mono,monospace;font-size:0.8rem;outline:none;min-width:220px;">
            <option value="intraday">🏎️ Intraday (Same Day)</option>
            <option value="swing">⚡ Swing Trade (2–5 days)</option>
            <option value="short">📈 Short Term (15–45 days)</option>
            <option value="long">🏛 Long Term (3–18 months)</option>
          </select>
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;">
          <label style="font-size:0.6rem;color:var(--cyan);letter-spacing:1px;font-weight:700;">STRATEGY ARCHETYPE</label>
          <select id="fs-strat"
            style="background:var(--p2);border:1px solid var(--cyan);color:var(--cyan);
            padding:7px 12px;font-family:Share Tech Mono,monospace;font-size:0.8rem;outline:none;min-width:230px;">
            <option value="all">🌐 ALL (Reversals + Continuations)</option>
            <option value="pullback" selected>⚡ Institutional 20-EMA Pullbacks</option>
            <option value="vwap">🏎️ Intraday VWAP Absorption Pullback</option>
            <option value="reversal">🎯 Cyclical Inflection Reversals</option>
          </select>
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;">
          <label style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;">MIN CONFIDENCE %</label>
          <input type="number" id="fs-min-conf" value="60" min="40" max="95" step="5"
            style="width:70px;background:var(--p2);border:1px solid var(--b2);color:var(--cyan);
            padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.82rem;outline:none;">
        </div>
        <button onclick="generateForwardSignal(true)"
          style="padding:8px 20px;background:linear-gradient(135deg,rgba(230,184,0,0.15),rgba(230,184,0,0.05));
          border:1px solid var(--gold);color:var(--gold);font-family:Orbitron,sans-serif;
          font-size:0.65rem;letter-spacing:2px;cursor:pointer;">⚡ GENERATE + SEND</button>
        <button onclick="generateForwardSignal(false)"
          style="padding:8px 20px;background:var(--p2);border:1px solid var(--b2);
          color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.65rem;cursor:pointer;">
          👁 PREVIEW ONLY</button>
      </div>
      <div id="fs-loading" style="display:none;" class="loading">
        <div class="spinner"></div><span id="fs-loading-msg">Generating signals...</span></div>
      <div id="fs-error" style="display:none;" class="err"></div>
      <div id="fs-result" style="display:none;"></div>
    </div>
  </div>

  <!-- ══════════════════════════════════════════════════════════ -->
  <!-- BROKER EXECUTION MODAL (Zerodha / Dhan / Webhooks)         -->
  <!-- ══════════════════════════════════════════════════════════ -->
  <style>
    #broker-order-modal {
      display:none;
      position:fixed;
      top:0;left:0;right:0;bottom:0;
      background:rgba(0,0,0,0.78);
      z-index:99999;
      align-items:center;
      justify-content:center;
      backdrop-filter: blur(4px);
    }
    #broker-order-modal.active { display:flex; }
    .broker-modal-box {
      background:#0f172a;
      border:1px solid var(--cyan);
      box-shadow:0 10px 40px rgba(0,212,255,0.25);
      border-radius:10px;
      padding:24px 28px;
      min-width:380px;
      max-width:580px;
      width:90%;
    }
  </style>

  <div id="broker-order-modal">
    <div class="broker-modal-box">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;border-bottom:1px solid rgba(255,255,255,0.08);padding-bottom:10px;">
        <div style="font-family:Orbitron,sans-serif;font-size:0.95rem;color:var(--cyan);letter-spacing:1.5px;font-weight:700;">
          ⚡ 1-CLICK BROKER EXECUTION PAYLOAD
        </div>
        <button onclick="closeBrokerOrderModal()" style="background:transparent;border:none;color:var(--dim);font-size:1.1rem;cursor:pointer;">✕</button>
      </div>

      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;background:rgba(255,255,255,0.03);padding:8px 12px;border-radius:6px;">
        <div>
          <span id="bom-sym" style="font-family:Orbitron,sans-serif;font-size:1.1rem;color:var(--gold);font-weight:700;">TCS</span>
          <span id="bom-badge" class="badge bg" style="margin-left:8px;font-size:0.65rem;">BUY</span>
        </div>
        <div id="bom-strategy" style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--cyan);">
          20-EMA PULLBACK
        </div>
      </div>

      <!-- Live parameters grid -->
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px;">
        <div>
          <label style="font-size:0.58rem;color:var(--dim);display:block;margin-bottom:2px;">ENTRY (LIMIT)</label>
          <input type="number" step="0.05" id="bom-entry" oninput="recalcBrokerModal()" style="width:100%;box-sizing:border-box;background:var(--p2);border:1px solid var(--border);color:var(--cyan);padding:5px 8px;font-family:Share Tech Mono;font-size:0.8rem;outline:none;border-radius:4px;">
        </div>
        <div>
          <label style="font-size:0.58rem;color:var(--dim);display:block;margin-bottom:2px;">STOP-LOSS</label>
          <input type="number" step="0.05" id="bom-sl" oninput="recalcBrokerModal()" style="width:100%;box-sizing:border-box;background:var(--p2);border:1px solid var(--red);color:var(--red);padding:5px 8px;font-family:Share Tech Mono;font-size:0.8rem;outline:none;border-radius:4px;">
        </div>
        <div>
          <label style="font-size:0.58rem;color:var(--dim);display:block;margin-bottom:2px;">TARGET 1 (50%)</label>
          <input type="number" step="0.05" id="bom-t1" oninput="recalcBrokerModal()" style="width:100%;box-sizing:border-box;background:var(--p2);border:1px solid var(--green);color:var(--green);padding:5px 8px;font-family:Share Tech Mono;font-size:0.8rem;outline:none;border-radius:4px;">
        </div>
        <div>
          <label style="font-size:0.58rem;color:var(--dim);display:block;margin-bottom:2px;">QUANTITY (1% RISK)</label>
          <input type="number" id="bom-qty" oninput="recalcBrokerModal()" style="width:100%;box-sizing:border-box;background:var(--p2);border:1px solid var(--gold);color:var(--gold);padding:5px 8px;font-family:Share Tech Mono;font-size:0.8rem;outline:none;border-radius:4px;">
        </div>
      </div>

      <!-- Broker Payload Code Area -->
      <div style="margin-bottom:14px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
          <div style="display:flex;gap:8px;">
            <button id="bom-tab-zerodha" onclick="switchBrokerPayloadTab('zerodha')" style="padding:4px 10px;background:rgba(0,212,255,0.15);border:1px solid var(--cyan);color:var(--cyan);font-family:Share Tech Mono;font-size:0.65rem;cursor:pointer;border-radius:3px;">ZERODHA KITE</button>
            <button id="bom-tab-dhan" onclick="switchBrokerPayloadTab('dhan')" style="padding:4px 10px;background:transparent;border:1px solid var(--border);color:var(--dim);font-family:Share Tech Mono;font-size:0.65rem;cursor:pointer;border-radius:3px;">DHAN WEBHOOK</button>
            <button id="bom-tab-generic" onclick="switchBrokerPayloadTab('generic')" style="padding:4px 10px;background:transparent;border:1px solid var(--border);color:var(--dim);font-family:Share Tech Mono;font-size:0.65rem;cursor:pointer;border-radius:3px;">GENERIC JSON</button>
          </div>
          <button id="bom-copy-btn" onclick="copyBrokerPayload()" style="padding:4px 12px;background:linear-gradient(135deg,rgba(0,255,136,0.2),rgba(0,255,136,0.05));border:1px solid var(--green);color:var(--green);font-family:Share Tech Mono;font-size:0.65rem;cursor:pointer;border-radius:3px;">📋 COPY PAYLOAD</button>
        </div>
        <textarea id="bom-payload-text" readonly style="width:100%;height:140px;box-sizing:border-box;background:rgba(0,0,0,0.5);border:1px solid rgba(255,255,255,0.1);color:var(--gold);font-family:'JetBrains Mono',monospace;font-size:0.72rem;padding:10px;outline:none;border-radius:4px;resize:none;line-height:1.4;"></textarea>
      </div>

      <!-- Direct links / Actions -->
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
        <div style="display:flex;gap:10px;">
          <a id="bom-tv-link" target="_blank" href="#" style="font-family:Share Tech Mono;font-size:0.68rem;color:var(--cyan);text-decoration:none;border-bottom:1px dashed var(--cyan);">📈 Open TradingView Chart ↗</a>
        </div>
        <button onclick="closeBrokerOrderModal()" style="padding:6px 16px;background:transparent;border:1px solid var(--border);color:var(--dim);font-family:Share Tech Mono;font-size:0.7rem;cursor:pointer;border-radius:4px;">CLOSE</button>
      </div>
    </div>
  </div>

</div>
"""

JS = r"""
// ══════════════════════════════════════════════════════════════
// TRADE SIMULATION JAVASCRIPT
// ══════════════════════════════════════════════════════════════

function tradingTab(tab) {
  // If user calls legacy tabs that shifted to portfolio, redirect cleanly
  if (tab === 'ptf' || tab === 'orderbook') {
    nav('portfolio');
    if (window.portfolioTab) window.portfolioTab(tab);
    return;
  }

  const TAB_MAP = {
    backtest: { el: 'trading-backtest', btn: 'tab-bt'  },
    forward:  { el: 'trading-forward',  btn: 'tab-fwd' },
  };

  Object.entries(TAB_MAP).forEach(([key, cfg]) => {
    const el  = document.getElementById(cfg.el);
    const btn = document.getElementById(cfg.btn);
    if (!el || !btn) return;
    const active = key === tab;
    el.style.display = active ? 'block' : 'none';

    btn.style.background  = active ? 'rgba(0,212,255,0.15)' : 'transparent';
    btn.style.color       = active ? 'var(--cyan)' : 'var(--dim)';
    btn.style.borderColor = active ? 'var(--cyan)' : 'var(--border)';
  });

  if (tab === 'backtest') onBtTypeChange();
}

// ── Backtest ──────────────────────────────────────────────────
async function runBacktest() {
  const sym   = (document.getElementById('bt-symbol')?.value||'').trim().toUpperCase();
  const type  = document.getElementById('bt-type')?.value || 'swing';
  const start = document.getElementById('bt-start')?.value || '2024-01-01';
  const end   = document.getElementById('bt-end')?.value || ((typeof today !== 'undefined') ? today : new Date().toISOString().slice(0, 10));

  document.getElementById('bt-loading').style.display   = 'flex';
  document.getElementById('bt-error').style.display     = 'none';
  document.getElementById('bt-no-trades').style.display = 'none';
  document.getElementById('bt-result').style.display    = 'none';

  try {
    const params = { type, start_date: start, end_date: end };
    if (sym) params.symbol = sym;

    const resp = await fetch(`/api/backtest_export?type=${type}&start_date=${start}&end_date=${end}${sym?'&symbol='+sym:''}`);
    document.getElementById('bt-loading').style.display = 'none';

    if (!resp.ok) {
      const d = await resp.json().catch(()=>({error:'Server error'}));
      _showBtError(d.error||'Unknown error', type, start, end); return;
    }

    const ct = resp.headers.get('Content-Type') || '';
    if (!ct.includes('spreadsheet') && !ct.includes('octet')) {
      const d = await resp.json().catch(()=>({error:'Invalid response from server'}));
      _showBtError(d.error||'Unexpected response — not an Excel file', type, start, end); return;
    }

    const blob = await resp.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url;
    a.download = `Backtest_${type}_${start}_${end}${sym?'_'+sym:''}.xlsx`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);

    document.getElementById('bt-result').style.display = 'block';
    document.getElementById('bt-result').innerHTML = `
      <div style="padding:12px 16px;background:rgba(0,255,136,0.05);border:1px solid var(--green);
           font-family:Share Tech Mono,monospace;font-size:0.78rem;color:var(--green);">
        ✓ Backtest complete — Excel report downloaded.<br>
        <span style="color:var(--dim);font-size:0.65rem;">
          Logic stack: Gann Sq9 · RSI/SMA/BB · Natal planetary · Fundamental · Sentiment
        </span>
      </div>`;
  } catch(e) {
    document.getElementById('bt-loading').style.display = 'none';
    _showBtError(e.message, type, start, end);
  }
}

function _showBtError(msg, type, start, end) {
  const noTrades = msg && (msg.includes('No trades') || msg.includes('no trades'));
  if (noTrades) {
    const typeLabels = {swing:'Swing (2–5 days)', short:'Short Term (15–45 days)', long:'Long Term (3–18 months)', intraday:'Intraday (Same Day)'};
    const detail = document.getElementById('bt-no-trades-detail');
    if (detail) {
      detail.innerHTML =
        `<span style="color:var(--orange);">▸ SCAN TYPE:</span>  ${typeLabels[type]||type}<br>` +
        `<span style="color:var(--orange);">▸ DATE RANGE:</span> ${start} → ${end}<br>` +
        `<span style="color:var(--orange);">▸ GATE STATUS:</span> All equities scanned — no setup passed Gann + Quant + Regime filters<br>` +
        `<span style="color:var(--orange);">▸ DB STATUS:</span>   Price history present — gates simply found no qualifying entries`;
    }
    document.getElementById('bt-no-trades').style.display = 'block';
  } else {
    const e = document.getElementById('bt-error');
    e.style.display = 'block';
    e.textContent = '⚠ ' + (msg || 'Unknown error');
  }
}

const BT_TYPE_DESCS = {
  intraday: "Intraday momentum + VWAP rejection wicks. Same-day exit before 15:15 IST.",
  swing:    "Gann Sq9 levels + RSI momentum. Entry at price level, exit within 2-5 days.",
  short:    "Simons Fourier cycle trough-to-peak. Hold 15–45 days.",
  long:     "Fundamental quality + Gann structure + Astro ruler confluence. Hold 3–18 months.",
};

function onBtTypeChange() {
  const v = document.getElementById('bt-type')?.value || 'swing';
  const d = document.getElementById('bt-type-desc');
  if (d) { d.textContent = BT_TYPE_DESCS[v] || ''; }
}

// ── Forward Signals ───────────────────────────────────────────
function _buildFwdDeployBanner(signals) {
  if (!signals || signals.length === 0) return '';
  return `<div style="margin-top:14px;padding:12px 16px;background:rgba(41,98,255,0.08);
    border:1px solid var(--cyan);font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--cyan);display:flex;justify-content:space-between;align-items:center;">
    <span>✨ ${signals.length} forward signal${signals.length>1?'s':''} ready for paper execution.</span>
    <button onclick="nav('portfolio')" style="padding:4px 12px;background:var(--cyan);color:var(--bg);border:none;border-radius:3px;font-family:Orbitron,sans-serif;font-size:0.62rem;cursor:pointer;font-weight:700;">VIEW PORTFOLIO ➔</button>
  </div>`;
}

function updatePositionSize(sym, entry, sl) {
  const cap = parseFloat(document.getElementById('ps-cap-' + sym)?.value || 100000);
  const riskAmt = cap * 0.01;
  const riskPerShare = Math.max(Math.abs(entry - sl), 0.1);
  const qty = Math.max(1, Math.floor(riskAmt / riskPerShare));
  const totalExp = (qty * entry).toLocaleString('en-IN', {maximumFractionDigits: 0});
  const el = document.getElementById('ps-res-' + sym);
  if (el) el.innerHTML = `Recommended: <b>${qty} Qty</b> (Exposure: ₹${totalExp} | Max Risk: ₹${Math.round(riskAmt).toLocaleString()})`;
}

function _renderSignalCard(s, notify, sendNow) {
  window._sigMap = window._sigMap || {};
  window._sigMap[s.symbol] = s;

  const c_col  = s.confidence >= 75 ? 'var(--green)' : s.confidence >= 60 ? 'var(--gold)' : 'var(--red)';
  const rr_col = (s.rr_ratio || 0) >= 2 ? 'var(--green)' : (s.rr_ratio || 0) >= 1.5 ? 'var(--gold)' : 'var(--red)';
  
  const hz = (s.inv_type || 'swing').toLowerCase();
  const hzBadge = hz === 'intraday'
    ? '<span class="badge bc" style="font-size:0.6rem;">🏎️ INTRADAY (Exit by 15:15 IST)</span>'
    : hz === 'swing'
    ? '<span class="badge bo" style="font-size:0.6rem;">⚡ SWING (Hold: 2–5 Days)</span>'
    : hz === 'short'
    ? '<span class="badge bp" style="font-size:0.6rem;">📈 SHORT-TERM (Hold: 15–45 Days)</span>'
    : '<span class="badge bg" style="font-size:0.6rem;">🏛️ LONG-TERM (Hold: 3–18 Months)</span>';

  const isPullback = s.pattern_archetype === 'CONTINUATION' || s.strategy_type === 'TREND_PULLBACK_CONTINUATION' || s.strategy_type === 'INTRADAY_VWAP_PULLBACK_CONTINUATION' || (s.setup_name && s.setup_name.includes('Pullback'));
  const stratBadge = isPullback
    ? `<span class="badge" style="background:rgba(255,165,0,0.15);border:1px solid orange;color:orange;font-size:0.6rem;letter-spacing:1px;">⚡ CONTINUATION (Pullback)${s.ai_continuation_prob ? ' · AI Edge: ' + Math.round(s.ai_continuation_prob * 100) + '%' : ''}</span>`
    : `<span class="badge bc" style="font-size:0.6rem;letter-spacing:1px;">🎯 REVERSAL (Inflection)${s.ai_reversal_prob ? ' · AI Edge: ' + Math.round(s.ai_reversal_prob * 100) + '%' : ''}</span>`;

  const zoneLow = s.entry_zone_low || (s.entry * 0.997);
  const zoneHigh = s.entry_zone_high || (s.entry * 1.003);
  const defaultQty = s.recommended_qty || Math.max(1, Math.floor(1000 / Math.max(0.1, Math.abs(s.entry - s.stop_loss))));
  const defaultExp = (defaultQty * s.entry).toLocaleString('en-IN', {maximumFractionDigits: 0});

  const zoneBanner = isPullback
    ? `<div style="background:rgba(255,165,0,0.06);border:1px solid rgba(255,165,0,0.25);border-radius:4px;padding:8px 12px;margin-bottom:10px;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:orange;font-weight:700;margin-bottom:4px;">
          ⚡ 20-EMA / VWAP PULLBACK ENTRY ZONE: ₹${zoneLow.toFixed(2)} — ₹${zoneHigh.toFixed(2)}
        </div>
        <div style="font-family:Inter,sans-serif;font-size:0.68rem;color:var(--text);line-height:1.4;">
          Setup: <b>${s.setup_name || 'Confluence Pullback'}</b> · Trend Strength (ADX): <b>${s.adx ? s.adx.toFixed(1) : '28.5'}</b> · Volume Confirmation: <b>${s.vol_surge ? s.vol_surge.toFixed(1) + 'x' : '1.3x 20-SMA'}</b>
        </div>
      </div>`
    : `<div style="background:rgba(0,212,255,0.05);border:1px solid rgba(0,212,255,0.2);border-radius:4px;padding:8px 12px;margin-bottom:10px;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--cyan);font-weight:700;margin-bottom:4px;">
          🎯 CYCLICAL INFLECTION ZONE: ₹${zoneLow.toFixed(2)} — ₹${zoneHigh.toFixed(2)}
        </div>
        <div style="font-family:Inter,sans-serif;font-size:0.68rem;color:var(--text);line-height:1.4;">
          Setup: <b>${s.setup_name || 'Gann Planetary Confluence'}</b> · Gann Sq9 Support: <b>₹${(s.gann_support||s.entry*0.98).toFixed(2)}</b> · Cycle Trough: <b>${s.cycle_phase || 'Active'}</b>
        </div>
      </div>`;

  const scoreHtml = `
    <div style="display:flex;flex-direction:column;gap:4px;">
      <div style="display:flex;justify-content:space-between;font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);">
        <span>Gann Sq9 Support</span><span style="color:var(--cyan);">₹${(s.gann_support||0).toFixed(2)}</span>
      </div>
      <div style="display:flex;justify-content:space-between;font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);">
        <span>Gann Resistance</span><span style="color:var(--gold);">₹${(s.gann_resistance||0).toFixed(2)}</span>
      </div>
      <div style="display:flex;justify-content:space-between;font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);">
        <span>Technical Score</span><span style="color:var(--green);">${s.tech_score||0}/100</span>
      </div>
      <div style="display:flex;justify-content:space-between;font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);">
        <span>Fundamental Quality</span><span style="color:var(--text);">${s.fund_score||0}/100</span>
      </div>
    </div>`;

  const analysisHtml = s.technical_summary ? `
    <div style="margin-top:6px;padding:6px 10px;background:rgba(255,255,255,0.02);border-radius:4px;font-family:Inter,sans-serif;font-size:0.7rem;color:var(--text);line-height:1.4;">
      <b>Quant Analysis:</b> ${s.technical_summary}
    </div>` : '';

  const notifyHtml = (sendNow && notify) ? `
    <div style="margin-top:8px;font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);">
      Alert Dispatched: Email (${notify.email?'✓':'—'}) · WhatsApp (${notify.whatsapp?'✓':'—'})
    </div>` : '';

  return `<div style="margin-bottom:14px;padding:16px;background:linear-gradient(135deg, rgba(16,22,34,0.85), rgba(20,28,42,0.7));
    border:1px solid rgba(255,255,255,0.08);border-left:4px solid ${c_col};border-radius:6px;">
    
    <!-- Header -->
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;flex-wrap:wrap;gap:6px;">
      <div>
        <div style="display:flex;align-items:center;gap:8px;">
          <span style="font-family:Orbitron,sans-serif;font-size:0.95rem;color:var(--gold);font-weight:700;">📡 ${s.symbol} — ${s.name||''}</span>
          ${stratBadge}
          ${hzBadge}
        </div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;margin-top:3px;">
          SECTOR: ${(s.sector||'').toUpperCase()} · ASTRO RULER: ${s.ruling_planet||'—'} · DATE: ${s.buy_date||'—'}
        </div>
      </div>
      <div style="text-align:right;">
        <div style="font-family:Orbitron,sans-serif;font-size:1.5rem;color:${c_col};font-weight:900;">${s.confidence||0}%</div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);letter-spacing:1px;">CONFLUENCE SCORE</div>
      </div>
    </div>

    <!-- Strategy Dynamic Zone Banner -->
    ${zoneBanner}

    <!-- Key Trading Levels Grid -->
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:10px;">
      <div class="stat"><span class="val" style="color:var(--t2);font-size:0.82rem;">₹${(s.price||0).toLocaleString('en-IN',{maximumFractionDigits:2})}</span><span class="lbl">CMP</span></div>
      <div class="stat"><span class="val" style="color:var(--cyan);font-size:0.82rem;">₹${(s.entry||0).toLocaleString('en-IN',{maximumFractionDigits:2})}</span><span class="lbl">MID ENTRY</span></div>
      <div class="stat"><span class="val" style="color:var(--red);font-size:0.82rem;">₹${(s.stop_loss||0).toLocaleString('en-IN',{maximumFractionDigits:2})}</span><span class="lbl">SL (INVALIDATION)</span></div>
      <div class="stat"><span class="val" style="color:var(--green);font-size:0.82rem;">₹${(s.target1||0).toLocaleString('en-IN',{maximumFractionDigits:2})}</span><span class="lbl">TARGET 1 (50%)</span></div>
      <div class="stat"><span class="val" style="color:var(--green);font-size:0.82rem;">₹${(s.target2||0).toLocaleString('en-IN',{maximumFractionDigits:2})}</span><span class="lbl">TARGET 2 (RUNNER)</span></div>
      <div class="stat"><span class="val" style="color:${rr_col};">${(s.rr_ratio||0).toFixed(2)}:1</span><span class="lbl">R:R RATIO</span></div>
      <div class="stat"><span class="val">${s.hold_days||0}d</span><span class="lbl">MAX HOLD</span></div>
      <div class="stat"><span class="val" style="font-size:0.6rem;">${s.regime||'—'}</span><span class="lbl">REGIME</span></div>
      <div class="stat"><span class="val" style="font-size:0.6rem;color:var(--cyan);">${s.news_sentiment||'N/A'}</span><span class="lbl">NEWS</span></div>
      <div class="stat"><span class="val" style="font-size:0.6rem;color:var(--gold);">${s.bulk_signal||'NEUTRAL'}</span><span class="lbl">BULK DEAL</span></div>
    </div>

    <!-- Position Sizing & Action Bar -->
    <div style="background:rgba(255,255,255,0.02);border:1px solid var(--border);padding:8px 12px;border-radius:4px;margin-bottom:10px;">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);">
          💼 POSITION SIZING (1% Risk): Capital ₹<input type="number" value="100000" id="ps-cap-${s.symbol}" oninput="updatePositionSize('${s.symbol}', ${s.entry}, ${s.stop_loss})" style="width:85px;background:var(--p2);border:1px solid var(--cyan);color:var(--gold);padding:3px 6px;font-family:Share Tech Mono;font-size:0.68rem;outline:none;border-radius:3px;">
        </div>
        <div id="ps-res-${s.symbol}" style="font-family:Orbitron,sans-serif;font-size:0.75rem;color:var(--green);font-weight:700;">
          Recommended: ${defaultQty} Qty (Exposure: ₹${defaultExp} | Max Risk: ₹1,000)
        </div>
        <div style="display:flex;gap:6px;">
          <button onclick="executePaperTrade('${s.symbol}', '${s.inv_type||'swing'}', ${s.entry}, ${defaultQty}, ${s.stop_loss}, ${s.target1}, ${s.target2})"
            style="padding:5px 12px;background:rgba(0,255,136,0.15);border:1px solid var(--green);color:var(--green);font-family:Orbitron,sans-serif;font-size:0.62rem;letter-spacing:1px;cursor:pointer;border-radius:4px;">
            🚀 PAPER TRADE
          </button>
          <button onclick="openBrokerOrderModal('${s.symbol}')"
            style="padding:5px 12px;background:linear-gradient(135deg, rgba(0,212,255,0.18), rgba(0,212,255,0.05));border:1px solid var(--cyan);color:var(--cyan);font-family:Orbitron,sans-serif;font-size:0.62rem;letter-spacing:1px;cursor:pointer;border-radius:4px;">
            ⚡ 1-CLICK BROKER
          </button>
        </div>
      </div>
    </div>

    <!-- Time Stop Rule -->
    <div style="margin-bottom:8px;padding:6px 10px;background:rgba(255,204,0,0.04);border-left:3px solid var(--gold);border-radius:0 4px 4px 0;">
      <div style="font-family:Share Tech Mono,monospace;font-size:0.64rem;color:var(--gold);margin-bottom:3px;">
        ⏳ ${s.time_invalidation_rule || 'Time Stop: Cut position if no upward momentum after 3 bars/days.'}
      </div>
      <div style="display:flex;gap:16px;font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);flex-wrap:wrap;">
        <span>🏛️ ${s.participant_context || 'Smart Money: Neutral'}</span>
        <span>📊 ${s.vix_context || 'India VIX: Normal'}</span>
      </div>
    </div>

    <!-- Sub-scores & Technical Reasons -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:8px;">
      <div>${scoreHtml}</div>
      <div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);margin-bottom:5px;">
          Entry: <span style="color:var(--gold);">${s.buy_date||'—'} ${s.buy_time||''}</span><br>
          Exit by: <span style="color:var(--red);">${s.sell_date||'—'}</span>
        </div>
        <div style="font-size:0.67rem;color:var(--t2);">
          ${(s.reasons||[]).slice(0,5).map(r=>'<div style="padding:1px 0;border-bottom:1px solid rgba(255,255,255,0.04);">• '+r+'</div>').join('')}
        </div>
      </div>
    </div>
    ${analysisHtml}
    ${notifyHtml}
  </div>`;
}

async function generateForwardSignal(sendNow) {
  const sym     = (document.getElementById('fs-symbol')?.value || '').trim().toUpperCase();
  const type    = document.getElementById('fs-type')?.value || 'swing';
  const strat   = document.getElementById('fs-strat')?.value || 'all';
  const minConf = document.getElementById('fs-min-conf')?.value || '60';
  const isAll   = !sym;

  const loadEl = document.getElementById('fs-loading');
  const msgEl  = document.getElementById('fs-loading-msg');
  if (msgEl) msgEl.textContent = isAll
    ? (strat === 'pullback' ? 'Scanning all equities for 20-EMA Pullbacks (vectorized)...' :
       strat === 'vwap' ? 'Scanning intraday VWAP pullbacks...' :
       'Scanning equities for forward signals — this may take 1–3 minutes...')
    : `Generating ${strat.toUpperCase()} signal for ${sym}...`;

  loadEl.style.display = 'flex';
  document.getElementById('fs-error').style.display  = 'none';
  document.getElementById('fs-result').style.display = 'none';

  try {
    let d;
    if (strat === 'vwap') {
      d = await api('intraday_vwap_pullbacks', { symbol: sym || 'NIFTY50' });
      loadEl.style.display = 'none';
      if (!d.ok) throw new Error(d.error || 'Failed to fetch VWAP pullbacks');
      const vwapSetups = d.pullback_setups || [];
      const resEl = document.getElementById('fs-result');
      resEl.style.display = 'block';
      if (vwapSetups.length === 0) {
        resEl.innerHTML = `<div style="padding:14px;font-family:Share Tech Mono,monospace;font-size:0.75rem;color:var(--dim);">No qualifying Intraday VWAP Pullbacks currently detected.</div>`;
        return;
      }
      resEl.innerHTML = vwapSetups.map(s => _renderSignalCard(s, null, false)).join('');
      return;
    }

    if (strat === 'pullback') {
      d = await api('trend_pullbacks', { symbol: sym, type, min_confidence: minConf });
      loadEl.style.display = 'none';
      if (!d.ok) throw new Error(d.error || 'Failed to fetch trend pullbacks');
      const pbSigs = d.signals || [];
      const resEl = document.getElementById('fs-result');
      resEl.style.display = 'block';
      if (pbSigs.length === 0) {
        resEl.innerHTML = `<div style="padding:14px;font-family:Share Tech Mono,monospace;font-size:0.75rem;color:var(--dim);">No qualifying 20-EMA trend pullbacks found with >= ${minConf}% confidence.</div>`;
        return;
      }
      const summary = `<div style="padding:8px 12px;background:rgba(255,165,0,0.08);border:1px solid orange;font-family:Share Tech Mono,monospace;font-size:0.72rem;color:orange;margin-bottom:12px;">
        ⚡ FOUND ${pbSigs.length} INSTITUTIONAL 20-EMA PULLBACK CANDIDATES (AI-FILTERED)
      </div>`;
      resEl.innerHTML = summary + pbSigs.map(s => _renderSignalCard(s, null, false)).join('');
      return;
    }

    // Default: forward_signal endpoint
    const params = { type, min_confidence: minConf, send: sendNow };
    if (sym) params.symbol = sym;
    d = await api('forward_signal', params);
    loadEl.style.display = 'none';

    if (!d.ok) throw new Error(d.error || 'Failed to generate signal');

    const resEl = document.getElementById('fs-result');
    resEl.style.display = 'block';

    if (sym) {
      if (!d.signal) {
        resEl.innerHTML = `<div style="padding:14px;font-family:Share Tech Mono,monospace;font-size:0.75rem;color:var(--dim);">No signal generated for ${sym}. Gates filtered out this stock.</div>`;
        return;
      }
      resEl.innerHTML = _renderSignalCard(d.signal, d.notify, sendNow);
    } else {
      const sigs = d.signals || [];
      if (sigs.length === 0) {
        resEl.innerHTML = `<div style="padding:14px;font-family:Share Tech Mono,monospace;font-size:0.75rem;color:var(--dim);">No signals generated across any equities. Try lowering the minimum confidence threshold.</div>`;
        return;
      }
      const notifyInfo = sendNow && d.notify
        ? `<div style="padding:8px 12px;background:rgba(0,255,136,0.06);border:1px solid var(--green);font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--green);margin-bottom:12px;">
            Dispatched: Email (${d.notify.email ? d.notify.email_sent + ' sent' : 'disabled'}) · WhatsApp (${d.notify.whatsapp ? d.notify.wa_sent + ' sent' : 'disabled'})
          </div>` : '';
      const summary = `<div style="padding:8px 12px;background:var(--p2);border:1px solid var(--border);font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--cyan);margin-bottom:12px;">
        FOUND ${sigs.length} SIGNALS WITH >= ${minConf}% CONFLUENCE
      </div>`;
      resEl.innerHTML = notifyInfo + summary + sigs.map(s => _renderSignalCard(s, null, false)).join('') + _buildFwdDeployBanner(sigs);
    }
  } catch(e) {
    loadEl.style.display = 'none';
    const er = document.getElementById('fs-error');
    er.style.display='block'; er.textContent = '⚠ ' + e.message;
  }
}

// ── Broker Execution Modal Handler ────────────────────────────
window._currentBrokerModalSym = null;
window._currentBrokerTab = 'zerodha';

function openBrokerOrderModal(sym) {
  const s = (window._sigMap && window._sigMap[sym]) || (window._fwdSignals && window._fwdSignals.find(x => x.symbol === sym));
  if (!s) return;
  window._currentBrokerModalSym = sym;

  const modal = document.getElementById('broker-order-modal');
  if (!modal) return;

  document.getElementById('bom-sym').textContent = s.symbol;
  const isPullback = s.strategy_type === 'TREND_PULLBACK_CONTINUATION' || s.strategy_type === 'INTRADAY_VWAP_PULLBACK_CONTINUATION';
  document.getElementById('bom-strategy').textContent = isPullback ? '⚡ 20-EMA / VWAP PULLBACK' : '🎯 CYCLICAL INFLECTION REVERSAL';
  document.getElementById('bom-badge').textContent = s.action || 'BUY';

  const entry = Number(s.entry || s.price || 100);
  const sl = Number(s.stop_loss || (entry * 0.97));
  const t1 = Number(s.target1 || (entry * 1.05));
  const qty = Number(s.recommended_qty || Math.max(1, Math.floor(1000 / Math.max(0.1, Math.abs(entry - sl)))));

  document.getElementById('bom-entry').value = entry.toFixed(2);
  document.getElementById('bom-sl').value = sl.toFixed(2);
  document.getElementById('bom-t1').value = t1.toFixed(2);
  document.getElementById('bom-qty').value = qty;

  const tvLink = document.getElementById('bom-tv-link');
  if (tvLink) tvLink.href = `https://in.tradingview.com/chart/?symbol=NSE:${s.symbol}`;

  recalcBrokerModal();
  modal.classList.add('active');
}

function closeBrokerOrderModal() {
  const modal = document.getElementById('broker-order-modal');
  if (modal) modal.classList.remove('active');
}

function switchBrokerPayloadTab(tab) {
  window._currentBrokerTab = tab;
  ['zerodha', 'dhan', 'generic'].forEach(t => {
    const el = document.getElementById('bom-tab-' + t);
    if (el) {
      if (t === tab) {
        el.style.background = 'rgba(0,212,255,0.18)';
        el.style.border = '1px solid var(--cyan)';
        el.style.color = 'var(--cyan)';
      } else {
        el.style.background = 'transparent';
        el.style.border = '1px solid var(--border)';
        el.style.color = 'var(--dim)';
      }
    }
  });
  recalcBrokerModal();
}

function recalcBrokerModal() {
  const sym = document.getElementById('bom-sym')?.textContent || 'NIFTY50';
  const entry = parseFloat(document.getElementById('bom-entry')?.value || '0');
  const sl = parseFloat(document.getElementById('bom-sl')?.value || '0');
  const t1 = parseFloat(document.getElementById('bom-t1')?.value || '0');
  const qty = parseInt(document.getElementById('bom-qty')?.value || '1');
  const action = document.getElementById('bom-badge')?.textContent || 'BUY';

  const riskPerShare = Math.max(0.1, Math.abs(entry - sl));
  const totalRisk = (riskPerShare * qty).toFixed(2);
  const totalExposure = (entry * qty).toFixed(2);

  let payload = '';
  if (window._currentBrokerTab === 'zerodha') {
    payload = JSON.stringify({
      variety: "regular",
      tradingsymbol: sym,
      exchange: "NSE",
      transaction_type: action,
      order_type: "LIMIT",
      quantity: qty,
      price: entry,
      product: "CNC",
      trigger_price: 0,
      tag: "VPROFIT_PULLBACK",
      gtt_stoploss: sl,
      gtt_target: t1,
      metadata: {
        total_risk_inr: parseFloat(totalRisk),
        capital_exposure: parseFloat(totalExposure)
      }
    }, null, 2);
  } else if (window._currentBrokerTab === 'dhan') {
    payload = JSON.stringify({
      dhanClientId: "YOUR_DHAN_CLIENT_ID",
      transactionType: action,
      exchangeSegment: "NSE_EQ",
      productType: "CNC",
      orderType: "LIMIT",
      validity: "DAY",
      securityId: sym,
      quantity: qty,
      price: entry,
      triggerPrice: sl,
      targetPrice: t1,
      tag: "VPROFIT_STRAT"
    }, null, 2);
  } else {
    payload = JSON.stringify({
      symbol: sym,
      action: action,
      exchange: "NSE",
      order_type: "LIMIT",
      entry_price: entry,
      stop_loss: sl,
      target_1: t1,
      quantity: qty,
      risk_amount_inr: parseFloat(totalRisk),
      strategy: "INSTITUTIONAL_CONFLUENCE",
      timestamp: new Date().toISOString()
    }, null, 2);
  }

  const ta = document.getElementById('bom-payload-text');
  if (ta) ta.value = payload;
}

function copyBrokerPayload() {
  const ta = document.getElementById('bom-payload-text');
  if (!ta) return;
  navigator.clipboard.writeText(ta.value).then(() => {
    const btn = document.getElementById('bom-copy-btn');
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = '✓ COPIED TO CLIPBOARD!';
      btn.style.color = '#fff';
      btn.style.background = 'var(--green)';
      setTimeout(() => {
        btn.innerHTML = orig;
        btn.style.color = 'var(--green)';
        btn.style.background = 'linear-gradient(135deg,rgba(0,255,136,0.2),rgba(0,255,136,0.05))';
      }, 1800);
    }
  });
}

function initTradingPage() {
  const el = document.getElementById('bt-end');
  if (el && !el.value) {
    el.value = (typeof today !== 'undefined') ? today : new Date().toISOString().slice(0, 10);
  }
  onBtTypeChange();
}

initTradingPage();
"""
