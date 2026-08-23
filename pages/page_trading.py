"""
page_trading.py — Unified Trading Execution Page (v4.0)
Sections:
  1. BACKTESTING — Paper Trade Simulation (Gann+Technical+Natal+Fundamental+Sentiment)
  2. ORDER BOOK   — Live paper_portfolio open/closed orders with actions
  3. TRADE HISTORY — Closed trade log with CSV export
  4. SIGNAL NOTIFICATIONS — Email + WhatsApp configuration
  5. FORWARD SIGNAL — Scan all equities / single symbol + send live recommendations
  6. FORWARD TESTING REPORT — Live trade tracker with daily auto-update
  7. DEMAT PORTFOLIO — Full Zerodha-style portfolio view
  8. ML ENGINE — Machine learning signal engine
"""

HTML = r"""
<!-- ═══════════ PAGE: TRADING EXECUTION ═══════════ -->
<div class="page" id="page-trading">
  <div class="topbar">
    <div style="display:flex;align-items:center;gap:10px;">
      <span style="font-family:Orbitron,sans-serif;font-size:1.1rem;color:var(--gold);font-weight:700;letter-spacing:2px;">⚡ TRADING EXECUTION</span>
      <span class="page-tag">BACKTEST · ORDER BOOK · TRADE HISTORY · SIGNALS · FORWARD TESTING</span>
    </div>
    <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;">
      LOGIC: GANN + TECHNICAL + NATAL + FUNDAMENTAL + SENTIMENT
    </div>
  </div>

  <!-- ══════════════════════════════════════════════════════════ -->
  <!-- TAB NAVIGATION                                             -->
  <!-- ══════════════════════════════════════════════════════════ -->
  <div style="display:flex;gap:0;margin-bottom:20px;border-bottom:1px solid var(--border);flex-wrap:wrap;">
    <button id="tab-bt"   onclick="tradingTab('backtest')"
      style="padding:8px 20px;background:rgba(0,212,255,0.12);border:1px solid var(--cyan);border-bottom:none;
             color:var(--cyan);font-family:Share Tech Mono,monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;">
      📊 BACKTEST
    </button>
    <button id="tab-ob"   onclick="tradingTab('orderbook')"
      style="padding:8px 20px;background:transparent;border:1px solid var(--border);border-bottom:none;
             color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;">
      📒 ORDER BOOK
    </button>
    <button id="tab-th"   onclick="tradingTab('tradehistory')"
      style="padding:8px 20px;background:transparent;border:1px solid var(--border);border-bottom:none;
             color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;">
      📜 TRADE HISTORY
    </button>
    <button id="tab-sig"  onclick="tradingTab('signals')"
      style="padding:8px 20px;background:transparent;border:1px solid var(--border);border-bottom:none;
             color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;">
      🔔 NOTIFICATIONS
    </button>
    <button id="tab-fwd"  onclick="tradingTab('forward')"
      style="padding:8px 20px;background:transparent;border:1px solid var(--border);border-bottom:none;
             color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;">
      📡 FORWARD SIGNALS
    </button>
    <button id="tab-ftr"  onclick="tradingTab('ftr')"
      style="padding:8px 20px;background:transparent;border:1px solid var(--border);border-bottom:none;
             color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;">
      📋 LIVE TRACKER
    </button>
    <button id="tab-ptf"  onclick="tradingTab('ptf')"
      style="padding:8px 20px;background:transparent;border:1px solid rgba(255,165,0,0.4);border-bottom:none;
             color:orange;font-family:Share Tech Mono,monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;">
      💼 DEMAT PORTFOLIO
    </button>
    <button id="tab-ml"  onclick="tradingTab('ml')"
      style="padding:8px 20px;background:transparent;border:1px solid rgba(0,255,136,0.4);border-bottom:none;
             color:var(--green);font-family:Share Tech Mono,monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;">
      🤖 ML ENGINE
    </button>
  </div>

  <!-- ══════════════════════════════════════════════════════════ -->
  <!-- TAB 1: BACKTESTING                                         -->
  <!-- ══════════════════════════════════════════════════════════ -->
  <div id="trading-backtest" class="trading-tab">
    <div class="card" style="margin-bottom:16px;">
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
  <!-- TAB 2: ORDER BOOK                                          -->
  <!-- ══════════════════════════════════════════════════════════ -->
  <style>
    .ob-row {
      display:grid;
      grid-template-columns:90px 55px 80px 72px 80px 80px 55px 68px 85px 1fr;
      gap:0;
      padding:8px 14px;
      border-bottom:1px solid rgba(255,255,255,0.04);
      align-items:center;
      transition:background 0.15s;
      font-family:'JetBrains Mono',monospace;
      font-size:0.72rem;
    }
    .ob-row:hover { background:rgba(255,255,255,0.025); }
    .ob-row.ob-editing { background:rgba(41,98,255,0.07); }
    .ob-input {
      width:70px;
      background:var(--bg);
      border:1px solid var(--cyan);
      color:var(--gold);
      padding:3px 6px;
      font-family:'JetBrains Mono',monospace;
      font-size:0.72rem;
      outline:none;
      border-radius:2px;
    }
    /* Partial exit modal */
    #ob-partial-modal {
      display:none;
      position:fixed;
      top:0;left:0;right:0;bottom:0;
      background:rgba(0,0,0,0.72);
      z-index:9999;
      align-items:center;
      justify-content:center;
    }
    #ob-partial-modal.active { display:flex; }
    .ob-modal-box {
      background:var(--panel);
      border:1px solid var(--cyan);
      border-radius:8px;
      padding:28px 32px;
      min-width:340px;
      max-width:420px;
    }
  </style>

  <div id="trading-orderbook" class="trading-tab" style="display:none;">
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

  <!-- Partial Exit Modal (global, outside tab divs) -->
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

  <!-- ══════════════════════════════════════════════════════════ -->
  <!-- TAB 3: TRADE HISTORY                                       -->
  <!-- ══════════════════════════════════════════════════════════ -->
  <style>
    .th-row {
      display:grid;
      grid-template-columns:90px 85px 80px 85px 80px 55px 90px 70px 55px 60px 1fr;
      gap:0;
      padding:7px 14px;
      border-bottom:1px solid rgba(255,255,255,0.04);
      align-items:center;
      font-family:'JetBrains Mono',monospace;
      font-size:0.7rem;
      transition:background 0.12s;
    }
    .th-row:hover { background:rgba(255,255,255,0.02); }
    .th-row.th-totals {
      background:rgba(41,98,255,0.06);
      border-top:1px solid var(--border);
      font-weight:700;
    }
  </style>

  <div id="trading-tradehistory" class="trading-tab" style="display:none;">
    <div style="background:var(--p2);border:1px solid var(--border);border-radius:8px;margin-bottom:16px;">
      <!-- Header toolbar -->
      <div style="display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--border);flex-wrap:wrap;gap:8px;">
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="font-family:Orbitron,sans-serif;font-size:0.88rem;color:var(--gold);font-weight:700;letter-spacing:2px;">📜 TRADE HISTORY</span>
          <span id="th-count-badge" style="background:rgba(255,152,0,0.15);color:var(--gold);font-size:0.68rem;font-weight:700;padding:2px 8px;border-radius:12px;font-family:'JetBrains Mono',monospace;">0</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
          <button onclick="loadTradeHistory()"
            style="padding:5px 12px;background:transparent;border:1px solid var(--border);border-radius:4px;
            color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.68rem;cursor:pointer;">↻ REFRESH</button>
          <button onclick="exportTradeCSV()"
            style="padding:5px 16px;background:rgba(8,153,129,0.1);border:1px solid var(--green);border-radius:4px;
            color:var(--green);font-family:Share Tech Mono,monospace;font-size:0.68rem;letter-spacing:1px;cursor:pointer;">
            ⬇ EXPORT CSV
          </button>
        </div>
      </div>

      <!-- Summary tiles -->
      <div id="th-summary" style="display:none;padding:12px 18px;border-bottom:1px solid var(--border);
           display:flex;gap:20px;flex-wrap:wrap;align-items:center;"></div>

      <!-- Column header -->
      <div class="th-row" style="padding:8px 14px;background:var(--bg);font-family:Share Tech Mono,monospace;
           font-size:0.6rem;color:var(--dim);letter-spacing:1px;border-bottom:1px solid var(--border);">
        <div>SYMBOL</div>
        <div>ENTRY DATE</div>
        <div style="text-align:right;">ENTRY ₹</div>
        <div>EXIT DATE</div>
        <div style="text-align:right;">EXIT ₹</div>
        <div style="text-align:right;">QTY</div>
        <div style="text-align:right;">P&amp;L ₹</div>
        <div style="text-align:right;">P&amp;L %</div>
        <div style="text-align:right;">R:R</div>
        <div style="text-align:right;">HOLD</div>
        <div>REASON</div>
      </div>

      <!-- Rows injected here -->
      <div id="th-list" style="min-height:80px;">
        <div style="padding:32px;text-align:center;color:var(--dim);font-size:0.8rem;">Loading trade history…</div>
      </div>

      <!-- Totals row (injected dynamically) -->
      <div id="th-totals" style="display:none;"></div>
    </div>
  </div>

  <!-- ══════════════════════════════════════════════════════════ -->
  <!-- TAB 4: NOTIFICATIONS                                       -->
  <!-- ══════════════════════════════════════════════════════════ -->
  <div id="trading-signals" class="trading-tab" style="display:none;">
    <div class="card" style="margin-bottom:16px;">
      <div class="card-title" style="color:var(--gold);">📧 EMAIL NOTIFICATIONS</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
        <div>
          <label style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;display:block;margin-bottom:4px;">RECIPIENT EMAIL</label>
          <input type="email" id="cfg-email-to" placeholder="your@email.com"
            style="width:100%;box-sizing:border-box;background:var(--p2);border:1px solid var(--b2);color:var(--t2);
            padding:7px 10px;font-family:Share Tech Mono,monospace;font-size:0.78rem;outline:none;">
        </div>
        <div>
          <label style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;display:block;margin-bottom:4px;">SENDER EMAIL (Gmail)</label>
          <input type="email" id="cfg-email-from" placeholder="sender@gmail.com"
            style="width:100%;box-sizing:border-box;background:var(--p2);border:1px solid var(--b2);color:var(--t2);
            padding:7px 10px;font-family:Share Tech Mono,monospace;font-size:0.78rem;outline:none;">
        </div>
        <div>
          <label style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;display:block;margin-bottom:4px;">GMAIL APP PASSWORD</label>
          <input type="password" id="cfg-email-pass" placeholder="xxxx xxxx xxxx xxxx"
            style="width:100%;box-sizing:border-box;background:var(--p2);border:1px solid var(--b2);color:var(--t2);
            padding:7px 10px;font-family:Share Tech Mono,monospace;font-size:0.78rem;outline:none;">
        </div>
        <div style="display:flex;align-items:center;gap:10px;padding-top:18px;">
          <input type="checkbox" id="cfg-email-enabled" style="width:16px;height:16px;cursor:pointer;">
          <label for="cfg-email-enabled" style="font-family:Share Tech Mono,monospace;font-size:0.75rem;
            color:var(--t2);cursor:pointer;">Enable Email Notifications</label>
        </div>
      </div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);margin-bottom:12px;">
        Get Gmail App Password at: myaccount.google.com/apppasswords (requires 2FA enabled)
      </div>
    </div>

    <div class="card" style="margin-bottom:16px;">
      <div class="card-title" style="color:var(--green);">💬 WHATSAPP NOTIFICATIONS</div>
      <div style="margin-bottom:10px;">
        <label style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;display:block;margin-bottom:6px;">METHOD</label>
        <select id="cfg-wa-method" onchange="updateWaFields()"
          style="background:var(--p2);border:1px solid var(--b2);color:var(--t2);
          padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.78rem;outline:none;min-width:200px;">
          <option value="none">None — Disabled</option>
          <option value="callmebot">CallMeBot (Free)</option>
          <option value="twilio">Twilio (Paid)</option>
        </select>
      </div>
      <div id="wa-callmebot-fields" style="display:none;display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div>
          <label style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;display:block;margin-bottom:4px;">YOUR WHATSAPP NUMBER (+91...)</label>
          <input type="text" id="cfg-cb-phone" placeholder="+919876543210"
            style="width:100%;box-sizing:border-box;background:var(--p2);border:1px solid var(--b2);color:var(--t2);
            padding:7px 10px;font-family:Share Tech Mono,monospace;font-size:0.78rem;outline:none;">
        </div>
        <div>
          <label style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;display:block;margin-bottom:4px;">CALLMEBOT API KEY</label>
          <input type="text" id="cfg-cb-key" placeholder="get free at api.callmebot.com"
            style="width:100%;box-sizing:border-box;background:var(--p2);border:1px solid var(--b2);color:var(--t2);
            padding:7px 10px;font-family:Share Tech Mono,monospace;font-size:0.78rem;outline:none;">
        </div>
      </div>
    </div>

    <div style="display:flex;gap:10px;flex-wrap:wrap;">
      <button onclick="saveNotifyConfig()"
        style="padding:8px 20px;background:rgba(0,255,136,0.08);border:1px solid var(--green);
        color:var(--green);font-family:Share Tech Mono,monospace;font-size:0.7rem;cursor:pointer;">
        💾 SAVE SETTINGS
      </button>
      <button onclick="testNotification()"
        style="padding:8px 20px;background:var(--p2);border:1px solid var(--b2);
        color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.7rem;cursor:pointer;">
        📤 SEND TEST
      </button>
    </div>
    <div id="notify-status" style="display:none;margin-top:10px;" class="err"></div>
  </div>

  <!-- ══════════════════════════════════════════════════════════ -->
  <!-- TAB 5: FORWARD SIGNALS                                     -->
  <!-- ══════════════════════════════════════════════════════════ -->
  <div id="trading-forward" class="trading-tab" style="display:none;">
    <div class="card" style="margin-bottom:16px;">
      <div class="card-title" style="color:var(--gold);">📡 FORWARD SIGNAL — LIVE RECOMMENDATIONS</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);margin-bottom:14px;">
        Leave SYMBOL blank to scan all equities. Signals are saved to Live Tracker and sent via configured channels.
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
  <!-- TAB 6: FORWARD TESTING REPORT                             -->
  <!-- ══════════════════════════════════════════════════════════ -->
  <div id="trading-ftr" class="trading-tab" style="display:none;">
    <div class="card" style="margin-bottom:16px;">
      <div class="card-title" style="color:var(--purple);">📋 LIVE TRADE TRACKER — FORWARD TESTING REPORT</div>
      <div style="display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;margin-bottom:12px;">
        <select id="ftr-status" style="background:var(--p2);border:1px solid var(--b2);color:var(--t2);
          padding:5px 10px;font-family:Share Tech Mono,monospace;font-size:0.78rem;outline:none;">
          <option value="all">All Signals</option>
          <option value="OPEN">🟢 Open</option>
          <option value="T2_HIT">🎯 T2 Hit</option>
          <option value="T1_HIT">✅ T1 Hit</option>
          <option value="TRAILING_SL">🔒 Trailing SL</option>
          <option value="SL_HIT">🔴 SL Hit</option>
          <option value="EXPIRED">⏰ Expired</option>
        </select>
        <input type="text" id="ftr-sym" placeholder="Filter symbol..."
          style="width:120px;background:var(--p2);border:1px solid var(--b2);color:var(--gold);
          padding:5px 10px;font-family:Share Tech Mono,monospace;font-size:0.78rem;outline:none;text-transform:uppercase;">
        <button onclick="loadForwardReport()"
          style="padding:5px 16px;background:var(--p2);border:1px solid var(--purple);
          color:var(--purple);font-family:Share Tech Mono,monospace;font-size:0.7rem;cursor:pointer;">
          🔄 REFRESH
        </button>
        <button onclick="updateForwardTests()"
          style="padding:5px 16px;background:rgba(255,204,0,0.08);border:1px solid var(--gold);
          color:var(--gold);font-family:Share Tech Mono,monospace;font-size:0.7rem;cursor:pointer;">
          ⚡ UPDATE LIVE STATUS
        </button>
      </div>
      <div id="ftr-summary" style="display:none;display:flex;gap:16px;flex-wrap:wrap;margin-bottom:12px;"></div>
      <div id="ftr-loading" style="display:none;" class="loading"><div class="spinner"></div>Loading report...</div>
      <div id="ftr-table" style="overflow-x:auto;"></div>
      <div id="ftr-deploy-banner" style="display:none;"></div>
    </div>
  </div>


  <!-- TAB 7: DEMAT PORTFOLIO -->
  <style>
    .ptf-row {
      display:grid;
      grid-template-columns:2fr 1fr 1fr 1fr 1fr 1.2fr 1.2fr 1fr;
      gap:0;
      padding:12px 18px;
      border-bottom:1px solid rgba(255,255,255,0.04);
      align-items:center;
      transition:background 0.15s;
    }
    .ptf-row:hover { background:rgba(255,255,255,0.028); }
  </style>
  <div id="trading-ptf" class="trading-tab" style="display:none;">

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
      <div style="display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--border);">
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="font-size:1rem;font-weight:600;color:var(--text);">Holdings</span>
          <span id="ptf-count" style="background:rgba(0,212,255,0.15);color:var(--cyan);font-size:0.7rem;font-weight:700;padding:2px 8px;border-radius:12px;">0</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
          <input id="ptf-search" type="text" placeholder="🔍 Search for stock or company"
            oninput="ptfFilterHoldings()"
            style="padding:6px 12px;background:var(--bg);border:1px solid var(--border);border-radius:6px;
            color:var(--text);font-size:0.78rem;width:240px;outline:none;"/>
          <button onclick="ptfToggleSelectExit()"
            style="padding:6px 14px;background:transparent;border:1px solid var(--border);
            border-radius:6px;color:var(--cyan);font-size:0.75rem;cursor:pointer;">
            SELECT &amp; EXIT
          </button>
          <button onclick="ptfGroupBy()"
            style="padding:6px 14px;background:transparent;border:1px solid var(--border);
            border-radius:6px;color:var(--text);font-size:0.75rem;cursor:pointer;">
            GROUP BY ▾
          </button>
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
        <div style="font-size:0.78rem;font-weight:600;color:var(--text);margin-bottom:8px;">All Sector Returns</div>
        <div style="font-size:0.68rem;color:var(--dim);margin-bottom:10px;">Which sectors are giving you the best returns</div>
        <div id="ptf-sector-bars" style="display:flex;flex-direction:column;gap:8px;"></div>
      </div>

      <!-- Top Drivers -->
      <div style="background:var(--p2);border:1px solid var(--border);border-radius:8px;padding:16px 18px;">
        <div style="font-size:0.9rem;font-weight:600;color:var(--text);margin-bottom:4px;">Top Drivers</div>
        <div style="font-size:0.68rem;color:var(--dim);margin-bottom:12px;">Which stocks are giving you the best and worst returns</div>
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
          <div style="text-align:right;">52 W/H</div>
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

  <!-- TAB 8: ML ENGINE -->
  <div id="trading-ml" class="trading-tab" style="display:none;">
    <div class="card" style="margin-bottom:16px;">
      <div class="card-title" style="color:var(--cyan);">🤖 ML DEEP SIGNAL ENGINE — v4.0</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);margin-bottom:14px;line-height:1.6;">
        Trained on your NSE price history · 32 features per bar · Predicts reversal price + date ·
        RandomForest (direction) + GradientBoost (timing) · Improves automatically with more data
      </div>

      <!-- Status -->
      <div style="padding:14px;background:var(--p2);border:1px solid var(--border);margin-bottom:16px;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:8px;">MODEL STATUS</div>
        <div id="ml-full-status-content" style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--dim);">Click Refresh Status to load.</div>
      </div>

      <!-- Controls -->
      <div style="display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end;margin-bottom:20px;">
        <div style="display:flex;flex-direction:column;gap:4px;">
          <label style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;">LOOKBACK YEARS</label>
          <select id="ml-years" style="background:var(--p2);border:1px solid var(--b2);color:var(--t2);padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.78rem;outline:none;">
            <option value="2">2 years</option>
            <option value="3" selected>3 years</option>
            <option value="5">5 years</option>
          </select>
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;">
          <label style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;">PREDICTION HORIZON</label>
          <select id="ml-fwd" style="background:var(--p2);border:1px solid var(--b2);color:var(--t2);padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.78rem;outline:none;">
            <option value="5">5 days (swing)</option>
            <option value="10" selected>10 days (short)</option>
            <option value="20">20 days (long)</option>
          </select>
        </div>
        <button onclick="trainML()"
          style="padding:8px 24px;background:linear-gradient(135deg,rgba(0,255,136,0.15),rgba(0,255,136,0.05));border:1px solid var(--green);color:var(--green);font-family:Orbitron,sans-serif;font-size:0.65rem;letter-spacing:2px;cursor:pointer;">
          ⚡ TRAIN MODEL
        </button>
        <button onclick="loadMLFullStatus()"
          style="padding:8px 16px;background:var(--p2);border:1px solid var(--b2);color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.65rem;cursor:pointer;">
          🔄 REFRESH STATUS
        </button>
      </div>

      <!-- Feature breakdown -->
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:16px;">
        <div style="padding:12px;background:var(--p2);border:1px solid rgba(0,212,255,0.2);border-top:2px solid var(--cyan);">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--cyan);letter-spacing:1px;margin-bottom:8px;">📊 TECHNICAL (14 features)</div>
          <div style="font-size:0.65rem;color:var(--dim);line-height:1.7;">RSI(14) · MACD · Bollinger %B · ATR · SMA trend ratios · Returns 5/10/20d · Volume ratio</div>
        </div>
        <div style="padding:12px;background:var(--p2);border:1px solid rgba(255,204,0,0.2);border-top:2px solid var(--gold);">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--gold);letter-spacing:1px;margin-bottom:8px;">🔺 GANN + WAVE (6 features)</div>
          <div style="font-size:0.65rem;color:var(--dim);line-height:1.7;">Sq9 distance to support · Sq9 distance to resistance · On-level flag · Wave position (0=low,1=high) · From swing low/high</div>
        </div>
        <div style="padding:12px;background:var(--p2);border:1px solid rgba(204,136,255,0.2);border-top:2px solid var(--purple);">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--purple);letter-spacing:1px;margin-bottom:8px;">🌌 ASTRO + SIGNALS (12 features)</div>
          <div style="font-size:0.65rem;color:var(--dim);line-height:1.7;">Fourier phase · Days to trough · R² · Natal bull/bear · Ruler activated · News score · Bulk deal signal · Institutional score · Volume surge</div>
        </div>
      </div>

      <!-- Where to see ML results -->
      <div style="padding:12px 14px;background:rgba(0,255,136,0.04);border:1px solid rgba(0,255,136,0.2);margin-bottom:16px;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--green);letter-spacing:1px;margin-bottom:8px;">📖 WHERE TO SEE ML RESULTS</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;font-size:0.65rem;color:var(--t2);line-height:1.8;">
          <div>
            <b style="color:var(--cyan);">Investment Advisor cards</b> — Every rec card shows a
            4-column ML panel: Direction · Confidence % · ML Reversal Price · ML Reversal Date.
            When ML Reversal Price coincides with Gann Sq9 level AND Simons Fourier peak — very high confidence.<br><br>
            <b style="color:var(--cyan);">ML Confidence %</b> — Above 70% = act on it.
            55–70% = wait for price confirmation. Below 55% = rule-based only.
          </div>
          <div>
            <b style="color:var(--gold);">Backtest Excel report</b> — 3 ML columns:
            ML Direction · ML Confidence · ML Reversal Price. Compare ML Rev Price
            to actual exit price to measure model accuracy over time.<br><br>
            <b style="color:var(--gold);">Forward Signals</b> — ML prediction appears as the
            first reason on each signal card when confidence &gt; 60%.
          </div>
        </div>
      </div>

      <!-- Training log -->
      <div class="card-title" style="color:var(--green);">⚡ TRAINING LOG</div>
      <div id="ml-train-log"
        style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);
        line-height:1.8;min-height:80px;background:rgba(0,0,0,0.3);padding:12px;border:1px solid var(--border);">
        Click TRAIN MODEL to start. Runs in background (~30–90 seconds).<br>
        · Needs 500+ bars of price history in your DB<br>
        · 3 years lookback gives best results<br>
        · Re-train weekly as new data accumulates
      </div>
    </div>
  </div>

</div>
"""


JS = r"""
// ══════════════════════════════════════════════════════════════
// TRADING PAGE — Tab switcher (updated for ORDER BOOK + TRADE HISTORY)
// ══════════════════════════════════════════════════════════════
function tradingTab(tab) {
  const TAB_MAP = {
    backtest:     { el: 'trading-backtest',     btn: 'tab-bt'  },
    orderbook:    { el: 'trading-orderbook',    btn: 'tab-ob'  },
    tradehistory: { el: 'trading-tradehistory', btn: 'tab-th'  },
    signals:      { el: 'trading-signals',      btn: 'tab-sig' },
    forward:      { el: 'trading-forward',      btn: 'tab-fwd' },
    ftr:          { el: 'trading-ftr',          btn: 'tab-ftr' },
    ptf:          { el: 'trading-ptf',          btn: 'tab-ptf' },
    ml:           { el: 'trading-ml',           btn: 'tab-ml'  },
  };

  Object.entries(TAB_MAP).forEach(([key, cfg]) => {
    const el  = document.getElementById(cfg.el);
    const btn = document.getElementById(cfg.btn);
    if (!el || !btn) return;
    const active = key === tab;
    el.style.display = active ? '' : 'none';

    // Determine accent colour per tab
    let accent = 'var(--cyan)';
    if (key === 'ml')           accent = 'var(--green)';
    else if (key === 'ptf')     accent = 'orange';
    else if (key === 'tradehistory') accent = 'var(--gold)';
    else if (key === 'orderbook')    accent = 'var(--cyan)';

    btn.style.background  = active ? `rgba(41,98,255,0.12)` : 'transparent';
    btn.style.color       = active ? accent : 'var(--dim)';
    btn.style.borderColor = active ? accent : 'var(--border)';
  });

  if (tab === 'signals')      loadNotifyConfig();
  if (tab === 'ml')           loadMLFullStatus();
  if (tab === 'ftr')          loadForwardReport();
  if (tab === 'ptf')          loadPortfolio();
  if (tab === 'orderbook')    loadOrderBook();
  if (tab === 'tradehistory') loadTradeHistory();
}

// ── Backtest ──────────────────────────────────────────────────
async function runBacktest() {
  const sym   = (document.getElementById('bt-symbol')?.value||'').trim().toUpperCase();
  const type  = document.getElementById('bt-type')?.value || 'swing';
  const start = document.getElementById('bt-start')?.value || '2024-01-01';
  const end   = document.getElementById('bt-end')?.value || GANN_DATE;

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

    // Verify we got an xlsx, not a JSON error wrapped in 200
    const ct = resp.headers.get('Content-Type') || '';
    if (!ct.includes('spreadsheet') && !ct.includes('octet')) {
      const d = await resp.json().catch(()=>({error:'Invalid response from server'}));
      _showBtError(d.error||'Unexpected response — not an Excel file', type, start, end); return;
    }

    // It's an Excel download
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
    const typeLabels = {swing:'Swing (2–5 days)', short:'Short Term (15–45 days)', long:'Long Term (3–18 months)', position:'Position (1–3 years)'};
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

// ══════════════════════════════════════════════════════════════
// ORDER BOOK — loadOrderBook, modifyOrder, closeOrder,
//              partialExit, saveOrderModify, confirmPartialExit
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
          <button onclick="modifyOrder(${t.id})"
            style="padding:3px 8px;background:transparent;border:1px solid var(--cyan);color:var(--cyan);
            font-size:0.6rem;cursor:pointer;border-radius:2px;font-family:Share Tech Mono,monospace;margin-right:3px;">✎ MOD</button>
          <button onclick="partialExit(${t.id},'${t.symbol}',${t.shares || 0})"
            style="padding:3px 8px;background:transparent;border:1px solid var(--gold);color:var(--gold);
            font-size:0.6rem;cursor:pointer;border-radius:2px;font-family:Share Tech Mono,monospace;margin-right:3px;">½ PART</button>
          <button onclick="closeOrder(${t.id},${t.entry_price || 0})"
            style="padding:3px 8px;background:transparent;border:1px solid var(--red);color:var(--red);
            font-size:0.6rem;cursor:pointer;border-radius:2px;font-family:Share Tech Mono,monospace;margin-right:3px;">✕ CLOSE</button>
          <button onclick="deleteOrder(${t.id})"
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
  } catch(e) {
    if (listEl) listEl.innerHTML = `<div class="err">Error: ${e.message}</div>`;
  }
}

function modifyOrder(id) {
  // Find the row and replace non-action cells with inline inputs
  const row = document.getElementById('ob-row-' + id);
  if (!row) return;
  if (row.classList.contains('ob-editing')) return; // already editing

  // Read current values from rendered text
  const cells = row.querySelectorAll('div');
  // cells[3]=SL, [4]=T1, [5]=T2
  const slText  = cells[3].textContent.replace('₹','').trim();
  const t1Text  = cells[4].textContent.replace('₹','').trim();
  const t2Text  = cells[5].textContent.replace('₹','').trim();

  row.classList.add('ob-editing');
  cells[3].innerHTML = `<input class="ob-input" id="ob-sl-${id}" value="${slText}" type="number" step="0.05">`;
  cells[4].innerHTML = `<input class="ob-input" id="ob-t1-${id}" value="${t1Text}" type="number" step="0.05">`;
  cells[5].innerHTML = `<input class="ob-input" id="ob-t2-${id}" value="${t2Text}" type="number" step="0.05">`;
  cells[9].innerHTML = `
    <button onclick="saveOrderModify(${id})"
      style="padding:3px 8px;background:rgba(41,98,255,0.2);border:1px solid var(--cyan);color:var(--cyan);
      font-size:0.62rem;cursor:pointer;border-radius:2px;font-family:Share Tech Mono,monospace;margin-right:3px;">✓ SAVE</button>
    <button onclick="cancelOrderModify(${id})"
      style="padding:3px 8px;background:transparent;border:1px solid var(--border);color:var(--dim);
      font-size:0.62rem;cursor:pointer;border-radius:2px;font-family:Share Tech Mono,monospace;">✕ CANCEL</button>`;
}

function cancelOrderModify(id) {
  loadOrderBook(); // just reload to restore
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
  const price = parseFloat(prompt(`Exit price for order #${id} (Market price):`, cmp) || '');
  if (isNaN(price) || price <= 0) return;
  if (!confirm(`Close order #${id} at ₹${price}?`)) return;
  try {
    const res = await api('portfolio_close', { id, exit_price: price });
    if (res && res.ok) {
      loadOrderBook();
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
    } else {
      alert('Delete failed: ' + ((res && res.error) || 'Unknown'));
    }
  } catch(e) {
    alert('Error: ' + e.message);
  }
}

// Partial Exit — opens modal
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
    const res = await api('portfolio_partial_exit', { id, shares: qty });
    if (res && res.ok) {
      closePartialModal();
      loadOrderBook();
    } else {
      alert('Partial exit failed: ' + ((res && res.error) || 'Unknown'));
    }
  } catch(e) {
    alert('Error: ' + e.message);
  }
}

// ══════════════════════════════════════════════════════════════
// TRADE HISTORY — loadTradeHistory, exportTradeCSV
// ══════════════════════════════════════════════════════════════
async function loadTradeHistory() {
  const listEl  = document.getElementById('th-list');
  const totEl   = document.getElementById('th-totals');
  const summEl  = document.getElementById('th-summary');
  const badgeEl = document.getElementById('th-count-badge');
  if (!listEl) return;
  listEl.innerHTML = '<div style="padding:32px;text-align:center;color:var(--dim);font-size:0.8rem;">Loading trade history…</div>';
  if (totEl) totEl.style.display = 'none';

  try {
    const res = await api('portfolio_get', { filter: 'CLOSED' });
    if (!res || !res.ok) {
      listEl.innerHTML = `<div class="err">${(res && res.error) || 'Failed to load trade history'}</div>`;
      return;
    }

    const trades = (res.trades || []).filter(t => t.status === 'CLOSED');
    if (badgeEl) badgeEl.textContent = trades.length;

    if (trades.length === 0) {
      listEl.innerHTML = '<div style="padding:32px;text-align:center;color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.78rem;">No closed trades yet. Close positions from the Order Book to see history here.</div>';
      if (summEl) summEl.style.display = 'none';
      return;
    }

    // Summary stats
    let totalPnl = 0, totalPnlPct = 0, wins = 0, losses = 0;
    trades.forEach(t => {
      const pnl = t.realized_pnl || 0;
      totalPnl += pnl;
      if (pnl >= 0) wins++; else losses++;
      const ep = t.entry_price || 0;
      const sh = t.shares || 0;
      const inv = ep * sh;
      if (inv > 0) totalPnlPct += (pnl / inv * 100);
    });
    const avgPnlPct = trades.length > 0 ? totalPnlPct / trades.length : 0;
    const winRate   = trades.length > 0 ? (wins / trades.length * 100).toFixed(1) : '0.0';

    if (summEl) {
      summEl.style.display = 'flex';
      const pnlCol = totalPnl >= 0 ? 'var(--green)' : 'var(--red)';
      summEl.innerHTML = `
        <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);letter-spacing:1px;">TRADES: <span style="color:var(--text);font-weight:700;">${trades.length}</span></div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);letter-spacing:1px;">WINS: <span style="color:var(--green);font-weight:700;">${wins}</span></div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);letter-spacing:1px;">LOSSES: <span style="color:var(--red);font-weight:700;">${losses}</span></div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);letter-spacing:1px;">WIN RATE: <span style="color:${wins >= losses ? 'var(--green)' : 'var(--red)'};font-weight:700;">${winRate}%</span></div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:var(--dim);letter-spacing:1px;">TOTAL P&L: <span style="color:${pnlCol};font-weight:700;">${totalPnl >= 0 ? '+' : ''}₹${Math.abs(totalPnl).toLocaleString('en-IN',{maximumFractionDigits:2})}</span></div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:var(--dim);letter-spacing:1px;">AVG P&L%: <span style="color:${avgPnlPct >= 0 ? 'var(--green)' : 'var(--red)'};font-weight:700;">${avgPnlPct >= 0 ? '+' : ''}${avgPnlPct.toFixed(2)}%</span></div>`;
    }

    const fmt2 = v => v != null ? v.toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2}) : '—';
    const fmtD = d => d ? String(d).slice(0, 10) : '—';

    let html = '';
    let sumPnl = 0, sumQty = 0;
    trades.forEach(t => {
      const ep  = t.entry_price  || 0;
      const xp  = t.exit_price   || 0;
      const sh  = t.shares       || 0;
      const pnl = t.realized_pnl || 0;
      const inv = ep * sh;
      const pnlPct  = inv > 0 ? (pnl / inv * 100) : 0;
      const sl      = t.stop_loss || 0;
      const risk    = sl > 0 && ep > 0 ? Math.abs(ep - sl) * sh : 0;
      const rr      = risk > 0 ? Math.abs(pnl / risk) : 0;
      const ed  = fmtD(t.entry_date);
      const xd  = fmtD(t.exit_date);
      const holdMs = (t.entry_date && t.exit_date)
        ? (new Date(t.exit_date) - new Date(t.entry_date)) / 86400000
        : 0;
      const holdDays = holdMs > 0 ? Math.round(holdMs) : '—';
      const pnlCol  = pnl >= 0 ? 'var(--green)' : 'var(--red)';
      const rrCol   = rr >= 1.5 ? 'var(--green)' : rr >= 1 ? 'var(--gold)' : 'var(--red)';

      sumPnl += pnl;
      sumQty += sh;

      html += `<div class="th-row">
        <div style="color:var(--gold);font-weight:700;">${t.symbol}</div>
        <div style="color:var(--dim);">${ed}</div>
        <div style="text-align:right;">₹${fmt2(ep)}</div>
        <div style="color:var(--dim);">${xd}</div>
        <div style="text-align:right;">₹${fmt2(xp)}</div>
        <div style="text-align:right;">${sh}</div>
        <div style="text-align:right;color:${pnlCol};font-weight:600;">${pnl >= 0 ? '+' : ''}₹${fmt2(Math.abs(pnl))}</div>
        <div style="text-align:right;color:${pnlCol};">${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%</div>
        <div style="text-align:right;color:${rrCol};">${rr > 0 ? rr.toFixed(2) + ':1' : '—'}</div>
        <div style="text-align:right;">${holdDays}${typeof holdDays === 'number' ? 'd' : ''}</div>
        <div style="color:var(--dim);font-size:0.62rem;">${t.exit_reason || '—'}</div>
      </div>`;
    });
    listEl.innerHTML = html;

    // Totals row
    if (totEl) {
      const sumCol = sumPnl >= 0 ? 'var(--green)' : 'var(--red)';
      totEl.style.display = 'block';
      totEl.innerHTML = `<div class="th-row th-totals" style="background:rgba(41,98,255,0.07);border-top:1px solid var(--border);">
        <div style="color:var(--cyan);font-family:Share Tech Mono,monospace;font-size:0.6rem;letter-spacing:1px;">TOTAL / AVG</div>
        <div></div><div></div><div></div><div></div>
        <div style="text-align:right;color:var(--text);">${sumQty}</div>
        <div style="text-align:right;color:${sumCol};font-weight:700;">${sumPnl >= 0 ? '+' : ''}₹${fmt2(Math.abs(sumPnl))}</div>
        <div style="text-align:right;color:${sumCol};">${avgPnlPct >= 0 ? '+' : ''}${avgPnlPct.toFixed(2)}%</div>
        <div></div><div></div><div style="color:var(--dim);font-size:0.6rem;">${trades.length} trades · ${winRate}% win rate</div>
      </div>`;
    }
  } catch(e) {
    if (listEl) listEl.innerHTML = `<div class="err">Error: ${e.message}</div>`;
  }
}

function exportTradeCSV() {
  window.location = '/api/portfolio_csv';
}

// ── Notifications ─────────────────────────────────────────────
async function loadNotifyConfig() {
  try {
    const d = await api('notify_config_load');
    if (!d.ok || !d.config) return;
    const c = d.config;
    const _s = (id, val) => { const el=document.getElementById(id); if(el) el.value=val||''; };
    _s('cfg-email-to',   c.EMAIL_TO);
    _s('cfg-email-from', c.EMAIL_FROM);
    _s('cfg-email-pass', c.EMAIL_PASS);
    const enEl = document.getElementById('cfg-email-enabled');
    if (enEl) enEl.checked = !!c.EMAIL_ENABLED;
    const mEl = document.getElementById('cfg-wa-method');
    if (mEl) { mEl.value = c.WA_METHOD || 'none'; updateWaFields(); }
    _s('cfg-cb-phone', c.WA_PHONE);
    _s('cfg-cb-key',   c.WA_KEY);
  } catch(e) { /* silent */ }
}

function updateWaFields() {
  const method = document.getElementById('cfg-wa-method')?.value || 'none';
  const cbFields = document.getElementById('wa-callmebot-fields');
  if (cbFields) cbFields.style.display = (method === 'callmebot') ? 'grid' : 'none';
}

async function saveNotifyConfig() {
  const cfg = {
    EMAIL_TO:      document.getElementById('cfg-email-to')?.value   || '',
    EMAIL_FROM:    document.getElementById('cfg-email-from')?.value  || '',
    EMAIL_PASS:    document.getElementById('cfg-email-pass')?.value  || '',
    EMAIL_ENABLED: document.getElementById('cfg-email-enabled')?.checked || false,
    WA_METHOD:     document.getElementById('cfg-wa-method')?.value   || 'none',
    WA_PHONE:      document.getElementById('cfg-cb-phone')?.value    || '',
    WA_KEY:        document.getElementById('cfg-cb-key')?.value      || '',
  };
  try {
    const d = await api('notify_config_save', { config: cfg });
    const el = document.getElementById('notify-status');
    if (el) {
      el.style.display = 'block';
      el.style.color   = d.ok ? 'var(--green)' : 'var(--red)';
      el.textContent   = d.ok ? '✓ Settings saved.' : ('Error: ' + (d.error||'Unknown'));
    }
  } catch(e) {
    const el = document.getElementById('notify-status');
    if (el) { el.style.display='block'; el.textContent='Error: '+e.message; }
  }
}

async function testNotification() {
  try {
    const d = await api('notify_test', {});
    alert(d.ok ? '✓ Test sent successfully!' : ('Error: ' + (d.error||'Unknown')));
  } catch(e) { alert('Error: ' + e.message); }
}

// ── Forward Signals rendering helpers ─────────────────────────
function _buildFwdDeployBanner(signals) {
  if (!signals || signals.length === 0) return '';
  return `<div style="margin-top:14px;padding:12px 16px;background:rgba(41,98,255,0.08);
    border:1px solid var(--cyan);font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--cyan);">
    ✨ ${signals.length} signal${signals.length>1?'s':''} ready — switch to Live Tracker to deploy to Order Book.
  </div>`;
}

function _renderSignalCard(s, notify, sendNow) {
  const c_col  = s.confidence >= 75 ? 'var(--green)' : s.confidence >= 60 ? 'var(--gold)' : 'var(--red)';
  const rr_col = (s.rr_ratio || 0) >= 2 ? 'var(--green)' : (s.rr_ratio || 0) >= 1.5 ? 'var(--gold)' : 'var(--red)';
  const scoreHtml = s.scores
    ? Object.entries(s.scores).map(([k,v]) =>
        `<div style="font-size:0.62rem;padding:2px 0;border-bottom:1px solid rgba(255,255,255,0.04);">
           <span style="color:var(--dim);">${k}:</span>
           <span style="float:right;color:var(--cyan);">${v}</span></div>`).join('')
    : '';
  const analysisHtml = s.analysis
    ? `<div style="font-size:0.65rem;color:var(--dim);padding:8px 0;border-top:1px solid rgba(255,255,255,0.06);line-height:1.7;">${s.analysis}</div>`
    : '';
  const notifyHtml = (notify && notify.ok)
    ? `<div style="padding:6px 10px;background:rgba(0,255,136,0.04);border:1px solid rgba(0,255,136,0.2);
         font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--green);margin-top:8px;">
         ✓ Signal sent via configured channels</div>`
    : (sendNow && notify && !notify.ok
        ? `<div style="padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.62rem;
             color:var(--dim);margin-top:8px;">Configure email/WhatsApp in Notifications tab.</div>`
        : '');

  return `<div style="margin-bottom:12px;padding:16px;background:rgba(0,0,0,0.2);
    border:1px solid rgba(255,255,255,0.07);border-left:3px solid ${c_col};">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;flex-wrap:wrap;gap:6px;">
      <div>
        <div style="font-family:Orbitron,sans-serif;font-size:0.85rem;color:var(--gold);font-weight:700;">📡 ${s.symbol} — ${s.name||''}</div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:2px;margin-top:2px;">
          ${(s.sector||'').toUpperCase()} · ${(s.inv_type||'').replace('_',' ').toUpperCase()} · Ruler: ${s.ruling_planet||'—'}</div>
      </div>
      <div style="text-align:right;">
        <div style="font-family:Orbitron,sans-serif;font-size:1.4rem;color:${c_col};font-weight:900;">${s.confidence||0}%</div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);">CONFIDENCE</div>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:10px;">
      <div class="stat"><span class="val" style="color:var(--t2);font-size:0.8rem;">₹${(s.price||0).toLocaleString('en-IN',{maximumFractionDigits:2})}</span><span class="lbl">CMP</span></div>
      <div class="stat"><span class="val" style="color:var(--cyan);font-size:0.8rem;">₹${(s.entry||0).toLocaleString('en-IN',{maximumFractionDigits:2})}</span><span class="lbl">ENTRY</span></div>
      <div class="stat"><span class="val" style="color:var(--red);font-size:0.8rem;">₹${(s.stop_loss||0).toLocaleString('en-IN',{maximumFractionDigits:2})}</span><span class="lbl">SL</span></div>
      <div class="stat"><span class="val" style="color:var(--green);font-size:0.8rem;">₹${(s.target1||0).toLocaleString('en-IN',{maximumFractionDigits:2})}</span><span class="lbl">T1</span></div>
      <div class="stat"><span class="val" style="color:var(--green);font-size:0.8rem;">₹${(s.target2||0).toLocaleString('en-IN',{maximumFractionDigits:2})}</span><span class="lbl">T2</span></div>
      <div class="stat"><span class="val" style="color:${rr_col};">${(s.rr_ratio||0).toFixed(2)}:1</span><span class="lbl">R:R</span></div>
      <div class="stat"><span class="val">${s.hold_days||0}d</span><span class="lbl">HOLD</span></div>
      <div class="stat"><span class="val" style="font-size:0.6rem;">${s.regime||'—'}</span><span class="lbl">REGIME</span></div>
      <div class="stat"><span class="val" style="font-size:0.6rem;color:var(--cyan);">${s.news_sentiment||'N/A'}</span><span class="lbl">NEWS</span></div>
      <div class="stat"><span class="val" style="font-size:0.6rem;color:var(--gold);">${s.bulk_signal||'NEUTRAL'}</span><span class="lbl">BULK</span></div>
    </div>
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
  const minConf = document.getElementById('fs-min-conf')?.value || '60';
  const isAll   = !sym;

  const loadEl = document.getElementById('fs-loading');
  const msgEl  = document.getElementById('fs-loading-msg');
  if (msgEl) msgEl.textContent = isAll
    ? 'Scanning all equities — this may take 2–4 minutes...'
    : `Generating signal for ${sym}...`;

  loadEl.style.display = 'flex';
  document.getElementById('fs-error').style.display  = 'none';
  document.getElementById('fs-result').style.display = 'none';

  try {
    const params = { type, send: sendNow, date: GANN_DATE, min_confidence: minConf };
    if (sym) params.symbol = sym;
    const d = await api('forward_signal', params);
    loadEl.style.display = 'none';

    if (!d.ok) {
      const e = document.getElementById('fs-error');
      e.style.display='block'; e.textContent = '⚠ ' + (d.error||'No signal'); return;
    }

    const resEl = document.getElementById('fs-result');
    resEl.style.display = 'block';

    if (d.mode === 'single') {
      resEl.innerHTML = _renderSignalCard(d.signal, d.notify, sendNow);
      window._fwdSignals = [d.signal];
      resEl.innerHTML += _buildFwdDeployBanner([d.signal]);
      return;
    }

    const sigs = d.signals || [];
    if (sigs.length === 0) {
      resEl.innerHTML = `<div style="padding:14px;font-family:Share Tech Mono,monospace;font-size:0.78rem;color:var(--dim);">
        No signals met confidence threshold (${minConf}%) on ${d.date}.<br>
        Try lowering MIN CONFIDENCE or changing investment type.</div>`;
      return;
    }
    sigs.sort((a,b) => (b.confidence||0) - (a.confidence||0));
    const notifyInfo = d.notify && d.notify.ok
      ? `<div style="padding:8px 12px;margin-bottom:10px;background:rgba(0,255,136,0.05);border:1px solid rgba(0,255,136,0.3);
           font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--green);">
           ✓ Combined Excel report sent via email — ${sigs.length} signals in one email</div>`
      : (sendNow ? `<div style="padding:6px 12px;margin-bottom:10px;font-family:Share Tech Mono,monospace;
           font-size:0.65rem;color:var(--dim);">Configure email/WhatsApp in Notifications tab to send reports.</div>` : '');
    const summary = `<div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:12px;padding:10px 14px;
      background:rgba(0,212,255,0.04);border:1px solid var(--cyan);">
      <div class="stat"><span class="val" style="color:var(--cyan);">${sigs.length}</span><span class="lbl">SIGNALS</span></div>
      <div class="stat"><span class="val" style="color:var(--green);">${Math.round(sigs.reduce((s,x)=>s+(x.confidence||0),0)/sigs.length)}%</span><span class="lbl">AVG CONF</span></div>
      <div class="stat"><span class="val" style="color:var(--gold);">${d.inv_type?.replace('_',' ').toUpperCase()}</span><span class="lbl">TYPE</span></div>
      <div class="stat"><span class="val">${d.date}</span><span class="lbl">DATE</span></div>
    </div>`;
    window._fwdSignals = sigs;
    resEl.innerHTML = notifyInfo + summary + sigs.map(s => _renderSignalCard(s, null, false)).join('') + _buildFwdDeployBanner(sigs);
  } catch(e) {
    document.getElementById('fs-loading').style.display = 'none';
    const er = document.getElementById('fs-error');
    er.style.display='block'; er.textContent = '⚠ ' + e.message;
  }
}

// ── Forward Testing Report ─────────────────────────────────────
async function loadForwardReport() {
  const status = document.getElementById('ftr-status')?.value || 'all';
  const sym    = (document.getElementById('ftr-sym')?.value || '').trim().toUpperCase();
  document.getElementById('ftr-loading').style.display = 'flex';
  document.getElementById('ftr-table').innerHTML = '';
  const sumEl = document.getElementById('ftr-summary');
  if (sumEl) sumEl.style.display = 'none';
  try {
    const d = await api('forward_test_report', { status, symbol: sym, days: 90 });
    document.getElementById('ftr-loading').style.display = 'none';
    if (!d.ok || !d.signals) return;

    if (sumEl) {
      sumEl.style.display = 'flex';
      sumEl.innerHTML = `
        <div class="stat"><span class="val">${d.total}</span><span class="lbl">TOTAL</span></div>
        <div class="stat"><span class="val" style="color:var(--cyan);">${d.open}</span><span class="lbl">OPEN</span></div>
        <div class="stat"><span class="val" style="color:var(--green);">${d.wins}</span><span class="lbl">WINS</span></div>
        <div class="stat"><span class="val" style="color:var(--red);">${d.losses}</span><span class="lbl">LOSSES</span></div>
        <div class="stat"><span class="val" style="color:${d.win_rate>=50?'var(--green)':'var(--red)'};">${d.win_rate}%</span><span class="lbl">WIN RATE</span></div>
        <div class="stat"><span class="val" style="color:${d.avg_pnl_pct>=0?'var(--green)':'var(--red)'};">${d.avg_pnl_pct>0?'+':''}${d.avg_pnl_pct}%</span><span class="lbl">AVG P&L</span></div>`;
    }

    if (d.signals.length === 0) {
      document.getElementById('ftr-table').innerHTML =
        '<div style="padding:14px;font-family:Share Tech Mono,monospace;font-size:0.75rem;color:var(--dim);">No signals found. Generate signals using the Forward Signals tab above.</div>';
      return;
    }

    const STATUS_COL  = {OPEN:'var(--cyan)',T2_HIT:'var(--green)',T1_HIT:'var(--green)',TRAILING_SL:'var(--gold)',SL_HIT:'var(--red)',EXPIRED:'var(--dim)'};
    const STATUS_ICON = {OPEN:'🟢',T2_HIT:'🎯',T1_HIT:'✅',TRAILING_SL:'🔒',SL_HIT:'🔴',EXPIRED:'⏰'};

    let html = `<div style="display:grid;grid-template-columns:70px 55px 80px 80px 80px 80px 60px 90px 1fr;
      gap:4px;padding:6px 8px;background:var(--p2);font-family:Share Tech Mono,monospace;
      font-size:0.6rem;color:var(--dim);letter-spacing:1px;border-bottom:1px solid var(--border);">
      <div>DATE</div><div>SYM</div><div>ENTRY</div><div>SL</div><div>T1</div><div>T2</div>
      <div>R:R</div><div>STATUS</div><div>EXIT / P&L</div></div>`;

    d.signals.forEach(s => {
      const scol = STATUS_COL[s.status]||'var(--dim)';
      const pnl  = s.pnl_pct!=null ? `${s.pnl_pct>=0?'+':''}${s.pnl_pct.toFixed(1)}%` : '—';
      const pnlCol= (s.pnl_pct||0)>=0 ? 'var(--green)' : 'var(--red)';
      const exitInfo = s.status!=='OPEN'
        ? `<span style="color:${pnlCol};">${pnl}</span> · ${s.exit_reason||''}`
        : `<span style="color:var(--dim);">trail ₹${(s.trailing_sl||s.stop_loss||0).toFixed(2)}</span>`;
      html += `<div style="display:grid;grid-template-columns:70px 55px 80px 80px 80px 80px 60px 90px 1fr;
        gap:4px;padding:6px 8px;border-bottom:1px solid rgba(255,255,255,0.04);
        font-family:Share Tech Mono,monospace;font-size:0.68rem;align-items:center;
        background:${s.status==='OPEN'?'rgba(0,212,255,0.02)':'transparent'};">
        <div style="color:var(--dim);">${(s.signal_date||'').slice(5)}</div>
        <div style="color:var(--gold);font-weight:700;">${s.symbol}</div>
        <div>₹${(s.entry||0).toFixed(2)}</div>
        <div style="color:var(--red);">₹${(s.stop_loss||0).toFixed(2)}</div>
        <div style="color:var(--green);">₹${(s.target1||0).toFixed(2)}</div>
        <div style="color:var(--green);">₹${(s.target2||0).toFixed(2)}</div>
        <div style="color:${(s.rr_ratio||0)>=1.5?'var(--green)':'var(--gold)'};">${(s.rr_ratio||0).toFixed(1)}:1</div>
        <div style="color:${scol};">${STATUS_ICON[s.status]||''} ${s.status}</div>
        <div>${exitInfo}</div>
      </div>`;
    });
    document.getElementById('ftr-table').innerHTML = html;

    // ── AUTO-PILOT: Deploy all OPEN signals to Paper Portfolio ────────────
    const openSignals = d.signals.filter(s => s.status === 'OPEN');
    const deployEl = document.getElementById('ftr-deploy-banner');
    if (deployEl) {
      if (openSignals.length > 0) {
        deployEl.style.display = 'block';
        deployEl.innerHTML = `
          <div class="easy-only" style="background:rgba(41,98,255,0.10);border:1px solid var(--cyan);
            border-radius:4px;padding:14px 16px;margin-top:14px;">
            <div style="color:var(--cyan);font-weight:bold;margin-bottom:6px;
              font-family:Share Tech Mono,monospace;font-size:0.8rem;letter-spacing:1px;">
              ✨ AUTO-PILOT — ${openSignals.length} OPEN SIGNAL${openSignals.length > 1 ? 'S' : ''} READY
            </div>
            <div style="font-family:Inter,sans-serif;font-size:0.8rem;color:var(--text);line-height:1.5;margin-bottom:10px;">
              Deploy all ${openSignals.length} open forward-test signal${openSignals.length > 1 ? 's' : ''} to your Paper Portfolio automatically.
              Each trade uses the exact Entry, SL, T1 and T2 already computed by the system.
            </div>
            <button onclick="deployForwardSignals()"
              style="width:100%;padding:10px;background:var(--cyan);color:var(--bg);border:none;
              border-radius:4px;font-family:Share Tech Mono,monospace;font-size:0.78rem;
              font-weight:bold;letter-spacing:2px;cursor:pointer;">
              🚀 DEPLOY ${openSignals.length} SIGNAL${openSignals.length > 1 ? 'S' : ''} TO PAPER PORTFOLIO
            </button>
          </div>`;
        window._ftrOpenSignals = openSignals;
      } else {
        deployEl.style.display = 'none';
        window._ftrOpenSignals = [];
      }
    }
  } catch(e) {
    document.getElementById('ftr-loading').style.display = 'none';
    document.getElementById('ftr-table').innerHTML =
      `<div style="padding:10px;font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--red);">Error: ${e.message}</div>`;
  }
}

async function updateForwardTests() {
  try {
    const d = await api('forward_test_update', {});
    if (d.ok) {
      alert(`Updated: ${d.exited} signals exited out of ${d.open_checked} open positions`);
      loadForwardReport();
    }
  } catch(e) { alert('Update error: ' + e.message); }
}

// Investment type descriptions for backtest
const BT_TYPE_DESCS = {
  swing:    "Gann Sq9 levels + RSI momentum. Entry at price level, exit within 5 days.",
  short:    "Simons Fourier cycle trough-to-peak. Hold 15–45 days.",
  long:     "Fundamental quality + Gann structure. Hold 3–18 months.",
  position: "🌊 Gann Absolute Wave: Accumulation Low → Distribution High. Entry at wave base, exit at wave peak. Hold 6 months–3 years. Max profit from complete wave.",
};

function onBtTypeChange() {
  const v = document.getElementById('bt-type')?.value || 'swing';
  const d = document.getElementById('bt-type-desc');
  if (d) { d.textContent = BT_TYPE_DESCS[v] || ''; d.style.color = v==='position'?'var(--cyan)':'var(--dim)'; }
}

// ── v4.0 ML Engine ─────────────────────────────────────────────────────────
async function loadMLFullStatus() {
  const el = document.getElementById('ml-full-status-content');
  if (!el) return;
  el.innerHTML = '<span style="color:var(--dim);">Loading...</span>';
  try {
    const d = await api('ml_status');
    const s = d.status || {};
    if (s.trained) {
      const accCol = s.dir_accuracy >= 65 ? 'var(--green)' : s.dir_accuracy >= 55 ? 'var(--gold)' : 'var(--red)';
      const maeCol = s.timing_mae <= 3 ? 'var(--green)' : s.timing_mae <= 6 ? 'var(--gold)' : 'var(--red)';
      el.innerHTML = `
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:10px;">
          <div>
            <div style="font-size:0.55rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">VERSION</div>
            <div style="color:var(--cyan);font-weight:700;">${s.version || '—'}</div>
          </div>
          <div>
            <div style="font-size:0.55rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">TRAINED ON</div>
            <div style="color:var(--gold);font-weight:700;">${(s.n_samples || 0).toLocaleString()} bars</div>
          </div>
          <div>
            <div style="font-size:0.55rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">DIRECTION ACCURACY</div>
            <div style="color:${accCol};font-weight:900;font-size:1.2rem;">${s.dir_accuracy}%</div>
          </div>
          <div>
            <div style="font-size:0.55rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">TIMING MAE</div>
            <div style="color:${maeCol};font-weight:900;font-size:1.2rem;">${s.timing_mae} days</div>
          </div>
        </div>
        <div style="font-size:0.62rem;color:var(--dim);">
          Trained: ${s.trained_at || '—'} &nbsp;·&nbsp;
          ${s.dir_accuracy >= 65
            ? '<span style="color:var(--green);">✓ Model performing well — ML predictions active</span>'
            : '<span style="color:var(--gold);">⚠ Collect more data and retrain for better accuracy</span>'}
        </div>`;
    } else {
      el.innerHTML = `<span style="color:var(--gold);">⚠ Not trained yet.</span>
        Select Lookback + Horizon above and click TRAIN MODEL.<br>
        Needs at least 500 bars of price history across your tracked symbols.`;
    }
  } catch(e) {
    if (el) el.textContent = 'Error: ' + (e.message || String(e));
  }
}

async function trainML() {
  const years = document.getElementById('ml-years')?.value || '3';
  const fwd   = document.getElementById('ml-fwd')?.value   || '10';
  const log   = document.getElementById('ml-train-log');
  if (log) log.innerHTML =
    '⏳ Training started...<br>'
    + 'Lookback: ' + years + ' years · Horizon: ' + fwd + ' days<br>'
    + 'Running in background. Auto-refresh status in ~90 seconds.';
  try {
    await api('ml_train', { years, forward_days: fwd });
    if (log) log.innerHTML += '<br>✓ Training request sent successfully.';
    setTimeout(() => loadMLFullStatus(), 90000);
  } catch(e) {
    if (log) log.innerHTML += '<br>✗ Error: ' + (e.message || String(e));
  }
}

// --- Portfolio Management JS ---
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

    // ── Use date from shared.js (defined globally) ─────────────────────
    const _today = (typeof today !== 'undefined') ? today
      : new Date().toISOString().slice(0, 10);

    // ── Fetch all CMPs — never let one failure kill the whole render ────
    const cmpMap  = {};
    const prevMap = {};
    await Promise.all(open.map(async t => {
      try {
        const px = await api('price', { symbol: t.symbol, date: _today });
        // Use close price; fall back to entry_price if missing or zero
        const close = px && px.close && px.close > 0 ? px.close : null;
        const prev  = px && px.prev_close && px.prev_close > 0 ? px.prev_close : null;
        cmpMap[t.symbol]  = close  || (t.entry_price > 0 ? t.entry_price : null);
        prevMap[t.symbol] = prev;
      } catch {
        cmpMap[t.symbol]  = t.entry_price > 0 ? t.entry_price : null;
        prevMap[t.symbol] = null;
      }
    }));

    // ── Compute totals ─────────────────────────────────────────────────
    let invested = 0, current = 0, unrealized = 0, realized = 0, todayGain = 0;
    const rows = [];
    for (const t of open) {
      const entryPx = t.entry_price || 0;
      const cmp     = cmpMap[t.symbol] || entryPx;
      const prev    = prevMap[t.symbol] || cmp;
      const shares  = t.shares || 0;
      const inv     = entryPx * shares;
      const cur     = cmp * shares;
      const pnl     = cur - inv;
      const pnlPct  = inv > 0 ? (pnl / inv * 100) : 0;
      const tg      = prev > 0 ? (cmp - prev) * shares : 0;
      invested  += inv;
      current   += cur;
      unrealized += pnl;
      todayGain += tg;
      rows.push({ t, cmp, inv, cur, pnl, pnlPct, tg });
    }
    for (const t of closed) realized += (t.realized_pnl || 0);

    // ── Sorting state ─────────────────────────────────────────────────────
    window._ptfRows    = rows;
    window._ptfSort    = window._ptfSort || { key: 'name', dir: 1 };
    window._ptfFilter  = '';
    window._ptfView    = window._ptfView || 'sector';
    window._ptfDrivers = window._ptfDrivers || 'gainers';

    // ── Update summary tiles ──────────────────────────────────────────────
    const fmt = v => '₹' + Math.abs(v).toLocaleString('en-IN', { maximumFractionDigits: 2 });
    const pct = (v, base) => base > 0 ? (v/base*100).toFixed(2) + '%' : '0%';

    document.getElementById('ptf-invested').textContent = fmt(invested);
    document.getElementById('ptf-current').textContent  = fmt(current);
    document.getElementById('ptf-count').textContent    = open.length;
    document.getElementById('ptf-realized').textContent = fmt(realized);
    document.getElementById('ptf-realized').style.color = realized >= 0 ? 'var(--green)' : 'var(--red)';

    const unrEl    = document.getElementById('ptf-unrealized');
    const unrPctEl = document.getElementById('ptf-unrealized-pct');
    unrEl.textContent    = (unrealized >= 0 ? '+' : '-') + fmt(unrealized);
    unrEl.style.color    = unrealized >= 0 ? 'var(--green)' : 'var(--red)';
    if (unrPctEl) {
      unrPctEl.textContent = (unrealized >= 0 ? '+' : '') + pct(unrealized, invested);
      unrPctEl.style.color = unrealized >= 0 ? 'var(--green)' : 'var(--red)';
    }
    const todayEl    = document.getElementById('ptf-today');
    const todayPctEl = document.getElementById('ptf-today-pct');
    if (todayEl) {
      todayEl.textContent  = (todayGain >= 0 ? '+' : '-') + fmt(todayGain);
      todayEl.style.color  = todayGain >= 0 ? 'var(--green)' : 'var(--red)';
    }
    if (todayPctEl) {
      todayPctEl.textContent = (todayGain >= 0 ? '+' : '') + pct(todayGain, current);
      todayPctEl.style.color = todayGain >= 0 ? 'var(--green)' : 'var(--red)';
    }

    ptfRenderTable();
    ptfRenderSectors();
    ptfRenderDrivers();

    if (open.length === 0) {
      listEl.innerHTML = '<div style="padding:32px;text-align:center;color:var(--dim);font-size:0.82rem;">' +
        'No open positions. Run the Advisor or Scanner and deploy trades to see them here.</div>';
    }
  } catch (e) {
    listEl.innerHTML = '<div class="err">' + e.message + '</div>';
  }
}

// ── RENDER HOLDINGS TABLE ─────────────────────────────────────────────────────
function ptfRenderTable() {
  const listEl = document.getElementById('ptf-list');
  if (!listEl || !window._ptfRows) return;

  const q    = (window._ptfFilter || '').toLowerCase();
  const rows = window._ptfRows.filter(r =>
    !q || r.t.symbol.toLowerCase().includes(q) ||
    (r.t.name || '').toLowerCase().includes(q)
  );

  // Sort
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
      // Col 1: Name + sub-line
      '<div>' +
        '<div style="font-weight:600;font-size:0.82rem;color:var(--text);">' + t.symbol + badge + typeTag + '</div>' +
        '<div style="font-size:0.62rem;color:var(--dim);margin-top:2px;">' +
          (sl  > 0 ? 'SL ₹' + fmt2(sl)  + ' &nbsp;·&nbsp; ' : '') +
          (t1  > 0 ? 'T1 ₹' + fmt2(t1)  + ' &nbsp;·&nbsp; ' : '') +
          (t2  > 0 ? 'T2 ₹' + fmt2(t2)  : '') +
          (t.entry_date ? '<span style="margin-left:6px;opacity:0.5;">' + (t.entry_date||'').slice(0,10) + '</span>' : '') +
        '</div>' +
      '</div>' +
      // Col 2-7: numeric columns
      '<div style="text-align:right;font-size:0.82rem;color:var(--text);">' + fmtR(sh) + '</div>' +
      '<div style="text-align:right;font-size:0.82rem;color:var(--text);">₹' + (ep > 0 ? fmt2(ep) : '—') + '</div>' +
      '<div style="text-align:right;font-size:0.82rem;color:var(--text);">₹' + (exitCmp > 0 ? fmt2(exitCmp) : '—') + '</div>' +
      '<div style="text-align:right;font-size:0.82rem;color:var(--text);">' + (inv > 0 ? '₹' + fmtR(inv) : '—') + '</div>' +
      '<div style="text-align:right;font-size:0.82rem;color:var(--text);">' + (cur > 0 ? '₹' + fmtR(cur) : '—') + '</div>' +
      // P&L col
      '<div style="text-align:right;">' +
        '<div style="font-size:0.82rem;font-weight:600;color:' + color(pnl) + ';">' +
          sign(pnl) + '₹' + fmt2(pnlAbs) +
        '</div>' +
        '<div style="font-size:0.62rem;color:' + color(pnl) + ';">' + sign(pnlPct) + pnlPct.toFixed(2) + '%</div>' +
      '</div>' +
      // Exit button
      '<div style="text-align:right;">' +
        '<button onclick="closePosition(' + t.id + ',' + exitCmp + ')" ' +
          'style="padding:4px 10px;background:transparent;border:1px solid var(--red);' +
          'color:var(--red);border-radius:4px;font-size:0.65rem;cursor:pointer;">Exit</button>' +
      '</div>' +
    '</div>';
  }
  listEl.innerHTML = html;
}

// ── FILTER + SORT helpers ─────────────────────────────────────────────────────
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

// ── SECTOR ALLOCATION ─────────────────────────────────────────────────────────
function ptfSetView(v) {
  window._ptfView = v;
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

  // Group by sector (use inv_type as proxy if sector missing)
  const sectorMap = {};
  for (const { t, inv, cur, pnl } of rows) {
    const sec = t.sector || t.inv_type || 'Other';
    if (!sectorMap[sec]) sectorMap[sec] = { inv: 0, cur: 0, pnl: 0 };
    sectorMap[sec].inv += inv;  sectorMap[sec].cur += cur;  sectorMap[sec].pnl += pnl;
  }
  const totalInv = rows.reduce((s, r) => s + r.inv, 0) || 1;

  // Colour palette
  const pal = ['#6C4FB3','#A855F7','#EC4899','#3B82F6','#10B981','#F59E0B','#EF4444','#06B6D4'];

  // Stacked bar
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

  // Sector return bars
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
  listEl.innerHTML = lHTML || '<div style="color:var(--dim);font-size:0.75rem;">No sector data.</div>';
}

// ── TOP DRIVERS ───────────────────────────────────────────────────────────────
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
  if(!confirm(`Square off position at ₹${cmp}?`)) return;
  try {
    const res = await api('portfolio_close', {id: id, exit_price: cmp});
    if(res.ok) {
      alert("Position Squared Off!");
      loadPortfolio();
    } else {
      alert("Error: " + res.error);
    }
  } catch(e) {
    alert("Error: " + e.message);
  }
}

async function executePaperTrade(sym, type, cmp, shares, sl, t1, t2) {
  if(!confirm(`Execute PAPER TRADE for ${sym}?
Shares: ${shares}
Entry: ₹${cmp}
Stop Loss: ₹${sl}
Target: ₹${t2}`)) return;

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
      nav('trading');
      setTimeout(()=>tradingTab('ptf'), 100);
    } else {
      alert("Error executing trade: " + res.error);
    }
  } catch(e) {
    alert("System Error: " + e.message);
  }
}

// Init trading page defaults — called by nav() when Trading Desk is opened
function initTradingPage() {
  const el = document.getElementById('bt-end');
  if (el && !el.value) el.value = new Date().toISOString().slice(0,10);
  onBtTypeChange();
  // Also load notify config and forward report
  try { loadNotifyConfig(); } catch(e) {}
}

initTradingPage();
"""