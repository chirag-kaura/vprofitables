"""
page_chart.py — Chart + S/R — TradingView-style chart with support/resistance

Exports:
    HTML  : Page HTML template (injected into SPA)
    JS    : Page JavaScript (injected into <script> block)

Backend endpoints for this page live in app.py (ep == "..." handlers).
To modify: edit HTML/JS here, backend logic in app.py.
"""


HTML = r"""
<!-- ═══════════ PAGE: CHART + S/R ═══════════ -->
<div class="page" id="page-chart">
  <div class="topbar">
    <h2>📈 CHART + SUPPORT/RESISTANCE</h2>
    <span class="page-tag">TECHNICAL ANALYSIS</span>
  </div>

  <!-- ── TOOLBAR: Symbol + Draw ── -->
  <div class="card" style="margin-bottom:8px;padding:6px 12px;">
    <div style="display:flex;align-items:center;gap:8px;">
      <select id="chart-sym" onchange="autoFetchPrice('chart-sym','chart-price','chart-price-badge')"
        style="background:var(--p2);border:1px solid var(--b2);color:var(--gold);padding:4px 8px;
        font-family:Share Tech Mono,monospace;font-size:0.82rem;outline:none;min-width:220px;font-weight:700;flex:1;"></select>
      <span id="chart-price-badge" style="display:none;"></span>
      <input type="number" id="chart-price" style="display:none;">
      <span id="ind-sma" style="display:none;"></span><span id="ind-bb" style="display:none;"></span>
      <span id="ind-vol" style="display:none;"></span><span id="ind-rsi" style="display:none;"></span>
      <span id="ind-macd" style="display:none;"></span><span id="ind-adx" style="display:none;"></span>
      <span id="ind-sr" style="display:none;"></span>
      <button class="btn-gold btn" onclick="loadChart()" style="padding:6px 20px;font-size:0.72rem;">⚡ DRAW</button>
    </div>
    <!-- Hidden settings panel kept for JS compatibility -->
    <div id="ind-settings" style="display:none;">
      <input type="number" id="sma-p1" value="20" style="display:none;">
      <input type="number" id="sma-p2" value="50" style="display:none;">
      <input type="number" id="sma-p3" value="200" style="display:none;">
      <input type="number" id="bb-period" value="20" style="display:none;">
      <input type="number" id="bb-std" value="2" style="display:none;">
      <input type="number" id="rsi-period" value="14" style="display:none;">
      <input type="number" id="rsi-ob" value="70" style="display:none;">
      <input type="number" id="rsi-os" value="30" style="display:none;">
      <input type="number" id="macd-fast" value="12" style="display:none;">
      <input type="number" id="macd-slow" value="26" style="display:none;">
      <input type="number" id="macd-sig" value="9" style="display:none;">
      <input type="number" id="adx-period" value="14" style="display:none;">
    </div>
  </div>

  <div id="chart-loading" class="loading" style="display:none;"><div class="spinner"></div>LOADING CHART DATA...</div>

  <div id="chart-content" style="display:none;">

    <!-- ── TRADINGVIEW-STYLE SUMMARY CARD ── -->
    <div class="card" style="padding:0;margin-bottom:10px;position:relative;overflow:hidden;">

      <!-- Header: symbol name + price + change -->
      <div style="display:flex;align-items:flex-start;justify-content:space-between;padding:14px 18px 10px;">
        <div>
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
            <span id="tv-summary-sym" style="font-family:Share Tech Mono,monospace;font-size:1.1rem;font-weight:700;color:var(--gold);letter-spacing:1px;"></span>
            <span id="tv-summary-name" style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--dim);"></span>
          </div>
          <div style="display:flex;align-items:baseline;gap:10px;">
            <span id="tv-summary-price" style="font-family:Share Tech Mono,monospace;font-size:2rem;font-weight:700;color:var(--t2);"></span>
            <span id="tv-summary-change" style="font-family:Share Tech Mono,monospace;font-size:0.9rem;font-weight:600;"></span>
            <span id="tv-summary-curr" style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--dim);">INR</span>
          </div>
        </div>
        <!-- Expand to full chart button -->
        <button onclick="openChartWindow()"
          style="padding:6px 14px;font-family:Share Tech Mono,monospace;font-size:0.68rem;cursor:pointer;
          border:1px solid rgba(0,212,255,0.4);background:rgba(0,212,255,0.08);color:var(--cyan);border-radius:2px;
          display:flex;align-items:center;gap:6px;white-space:nowrap;">
          ⛶ Full Chart
        </button>
      </div>

      <!-- BUY / SELL action buttons + open position badge -->
      <div style="display:flex;align-items:center;gap:10px;padding:0 18px 10px;">
        <button id="chart-buy-btn" onclick="chartShowOrder('BUY')"
          style="padding:7px 22px;background:#1B5E35;border:1.5px solid #26a269;color:#4ade80;
          font-family:Share Tech Mono,monospace;font-size:0.75rem;font-weight:700;
          letter-spacing:1px;cursor:pointer;border-radius:4px;">
          BUY
        </button>
        <button id="chart-sell-btn" onclick="chartShowOrder('SELL')"
          style="padding:7px 22px;background:#5C1A1A;border:1.5px solid #c0392b;color:#f87171;
          font-family:Share Tech Mono,monospace;font-size:0.75rem;font-weight:700;
          letter-spacing:1px;cursor:pointer;border-radius:4px;">
          SELL
        </button>
        <div id="chart-pos-badge" style="display:none;flex:1;display:flex;align-items:center;
          gap:10px;background:rgba(0,212,255,0.06);border:1px solid rgba(0,212,255,0.2);
          border-radius:4px;padding:6px 12px;">
          <span style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);">OPEN POSITION</span>
          <span id="chart-pos-sym"  style="font-family:Share Tech Mono,monospace;font-size:0.75rem;color:var(--gold);font-weight:700;"></span>
          <span id="chart-pos-qty"  style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--dim);"></span>
          <span id="chart-pos-pnl"  style="font-family:Share Tech Mono,monospace;font-size:0.82rem;font-weight:700;"></span>
          <button onclick="chartSquareOff()"
            style="margin-left:auto;padding:3px 10px;background:transparent;border:1px solid var(--red);
            color:var(--red);font-family:Share Tech Mono,monospace;font-size:0.62rem;cursor:pointer;border-radius:3px;">
            EXIT
          </button>
        </div>
      </div>

      <!-- Summary line chart canvas -->
      <div style="position:relative;padding:0 18px 0;">
        <canvas id="summary-canvas" style="display:block;width:100%;height:180px;cursor:crosshair;"></canvas>
        <div id="summary-hover" style="display:none;position:absolute;top:4px;left:22px;font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);pointer-events:none;"></div>
      </div>

      <!-- Order ticket modal (hidden by default) -->
      <div id="chart-order-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;
        background:rgba(0,0,0,0.6);z-index:9999;align-items:center;justify-content:center;">
        <div style="background:var(--bg);border:1px solid var(--border);border-radius:8px;
          padding:24px;width:380px;max-width:95vw;position:relative;">
          <!-- Header -->
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
            <div>
              <div id="modal-sym" style="font-family:Share Tech Mono,monospace;font-size:1rem;font-weight:700;color:var(--gold);"></div>
              <div style="display:flex;gap:8px;margin-top:4px;">
                <span id="modal-exch" style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);">NSE</span>
                <span id="modal-cmp"  style="font-family:Share Tech Mono,monospace;font-size:0.75rem;font-weight:700;color:var(--cyan);"></span>
              </div>
            </div>
            <div style="display:flex;gap:6px;">
              <button id="modal-buy-tab"  onclick="chartSetSide('BUY')"
                style="padding:6px 16px;border-radius:4px;border:1.5px solid #26a269;
                background:#1B5E35;color:#4ade80;font-family:Share Tech Mono,monospace;
                font-size:0.72rem;font-weight:700;cursor:pointer;">B</button>
              <button id="modal-sell-tab" onclick="chartSetSide('SELL')"
                style="padding:6px 16px;border-radius:4px;border:1px solid var(--border);
                background:transparent;color:var(--dim);font-family:Share Tech Mono,monospace;
                font-size:0.72rem;cursor:pointer;">S</button>
            </div>
            <button onclick="chartCloseModal()"
              style="background:transparent;border:none;color:var(--dim);font-size:1.2rem;cursor:pointer;">✕</button>
          </div>

          <!-- Order type tabs -->
          <div style="display:flex;gap:0;border-bottom:1px solid var(--border);margin-bottom:16px;">
            <button style="padding:6px 14px;background:transparent;border:none;border-bottom:2px solid var(--cyan);
              color:var(--cyan);font-family:Share Tech Mono,monospace;font-size:0.7rem;cursor:pointer;">Regular</button>
            <button style="padding:6px 14px;background:transparent;border:none;border-bottom:2px solid transparent;
              color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.7rem;cursor:pointer;">Stop Loss</button>
            <button style="padding:6px 14px;background:transparent;border:none;border-bottom:2px solid transparent;
              color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.7rem;cursor:pointer;">GTT</button>
          </div>

          <!-- Fields grid -->
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px;">
            <div>
              <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);margin-bottom:4px;letter-spacing:1px;">QTY / SHARES</div>
              <input id="modal-qty" type="number" value="1" min="1"
                style="width:100%;background:var(--p2);border:1px solid var(--border);color:var(--text);
                padding:7px 10px;font-family:Share Tech Mono,monospace;font-size:0.82rem;border-radius:4px;box-sizing:border-box;outline:none;"
                oninput="chartUpdateCost()"/>
            </div>
            <div>
              <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);margin-bottom:4px;letter-spacing:1px;">ENTRY PRICE</div>
              <input id="modal-entry" type="number" step="0.05"
                style="width:100%;background:var(--p2);border:1px solid var(--border);color:var(--text);
                padding:7px 10px;font-family:Share Tech Mono,monospace;font-size:0.82rem;border-radius:4px;box-sizing:border-box;outline:none;"
                oninput="chartUpdateCost()"/>
            </div>
            <div>
              <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);margin-bottom:4px;letter-spacing:1px;">STOP LOSS ₹</div>
              <input id="modal-sl" type="number" step="0.05"
                style="width:100%;background:var(--p2);border:1px solid var(--border);color:var(--text);
                padding:7px 10px;font-family:Share Tech Mono,monospace;font-size:0.82rem;border-radius:4px;box-sizing:border-box;outline:none;"
                oninput="chartUpdateCost()"/>
            </div>
            <div>
              <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);margin-bottom:4px;letter-spacing:1px;">TARGET 1 ₹</div>
              <input id="modal-t1" type="number" step="0.05"
                style="width:100%;background:var(--p2);border:1px solid var(--border);color:var(--text);
                padding:7px 10px;font-family:Share Tech Mono,monospace;font-size:0.82rem;border-radius:4px;box-sizing:border-box;outline:none;"
                oninput="chartUpdateCost()"/>
            </div>
            <div>
              <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);margin-bottom:4px;letter-spacing:1px;">TARGET 2 ₹</div>
              <input id="modal-t2" type="number" step="0.05"
                style="width:100%;background:var(--p2);border:1px solid var(--border);color:var(--text);
                padding:7px 10px;font-family:Share Tech Mono,monospace;font-size:0.82rem;border-radius:4px;box-sizing:border-box;outline:none;"/>
            </div>
            <div>
              <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);margin-bottom:4px;letter-spacing:1px;">TYPE</div>
              <select id="modal-type"
                style="width:100%;background:var(--p2);border:1px solid var(--border);color:var(--text);
                padding:7px 10px;font-family:Share Tech Mono,monospace;font-size:0.78rem;border-radius:4px;box-sizing:border-box;outline:none;">
                <option value="intraday">Intraday</option>
                <option value="swing">Swing</option>
                <option value="short">Short-term</option>
                <option value="long">Long-term</option>
              </select>
            </div>
          </div>

          <!-- Cost summary -->
          <div style="background:rgba(0,212,255,0.04);border:1px solid rgba(0,212,255,0.12);
            border-radius:4px;padding:10px 12px;margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
              <span style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);">Required capital</span>
              <span id="modal-cost" style="font-family:Share Tech Mono,monospace;font-size:0.75rem;font-weight:700;color:var(--text);">₹0</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
              <span style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);">Max profit (T1)</span>
              <span id="modal-profit" style="font-family:Share Tech Mono,monospace;font-size:0.75rem;font-weight:700;color:#26a269;">₹0</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
              <span style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);">Max loss (SL)</span>
              <span id="modal-loss" style="font-family:Share Tech Mono,monospace;font-size:0.75rem;font-weight:700;color:#f87171;">₹0</span>
            </div>
            <div style="display:flex;justify-content:space-between;">
              <span style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);">Risk : Reward</span>
              <span id="modal-rr" style="font-family:Share Tech Mono,monospace;font-size:0.75rem;font-weight:700;color:var(--gold);">—</span>
            </div>
          </div>

          <!-- Place order button -->
          <button id="modal-place-btn" onclick="chartPlaceOrder()"
            style="width:100%;padding:11px;background:#1B5E35;border:1.5px solid #26a269;
            color:#4ade80;font-family:Share Tech Mono,monospace;font-size:0.82rem;
            font-weight:700;letter-spacing:2px;cursor:pointer;border-radius:4px;">
            PLACE BUY ORDER
          </button>
          <div id="modal-err" style="display:none;margin-top:8px;font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--red);text-align:center;"></div>
        </div>
      </div>

      <!-- Period return cards (click to select period) -->
      <div id="tv-period-cards" style="display:grid;grid-template-columns:repeat(9,1fr);gap:0;border-top:1px solid rgba(255,255,255,0.05);">
        <!-- populated by JS -->
      </div>

      <!-- SMA stat row -->
      <div id="chart-stat-cards" style="display:none;border-top:1px solid rgba(255,255,255,0.05);padding:10px 18px;">
        <div style="display:flex;gap:24px;flex-wrap:wrap;">
          <div><span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;">SMA 20</span><br><span id="stat-sma20" style="font-family:Share Tech Mono,monospace;font-size:0.88rem;font-weight:700;color:#7FFFD4;">—</span></div>
          <div><span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;">SMA 50</span><br><span id="stat-sma50" style="font-family:Share Tech Mono,monospace;font-size:0.88rem;font-weight:700;color:#B5B5FF;">—</span></div>
          <div><span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;">SMA 200</span><br><span id="stat-sma200" style="font-family:Share Tech Mono,monospace;font-size:0.88rem;font-weight:700;color:#DEB887;">—</span></div>
          <div><span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;">20D RETURN</span><br><span id="stat-ret20" style="font-family:Share Tech Mono,monospace;font-size:0.88rem;font-weight:700;">—</span></div>
          <div><span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;">ANN VOL</span><br><span id="stat-vol" style="font-family:Share Tech Mono,monospace;font-size:0.88rem;font-weight:700;color:var(--gold);">—</span></div>
        </div>
      </div>
    </div>

    <!-- S/R levels -->
    <div class="g2" style="margin-top:10px;">
      <div class="card">
        <div class="card-title">🟢 SUPPORT LEVELS</div>
        <div id="support-table"></div>
      </div>
      <div class="card">
        <div class="card-title">🔴 RESISTANCE LEVELS</div>
        <div id="resistance-table"></div>
      </div>
    </div>

    <!-- Volatility + Trend Emotion -->
    <div class="g2" style="margin-top:10px;">

      <!-- VOLATILITY INDEX -->
      <div class="card">
        <div class="card-title">⚡ VOLATILITY INDEX</div>
        <div style="display:flex;flex-direction:column;gap:10px;padding:4px 0;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--dim);letter-spacing:1px;">Annual vol:</span>
            <span id="vi-annual" style="font-family:Share Tech Mono,monospace;font-size:0.82rem;color:var(--gold);font-weight:600;">—</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--dim);letter-spacing:1px;">Recent 21d vol:</span>
            <span id="vi-recent" style="font-family:Share Tech Mono,monospace;font-size:0.82rem;color:var(--cyan);font-weight:600;">—</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--dim);letter-spacing:1px;">Vol ratio:</span>
            <span id="vi-ratio" style="font-family:Share Tech Mono,monospace;font-size:0.82rem;color:var(--t2);font-weight:600;">—</span>
          </div>
          <!-- Vol gauge bar -->
          <div style="margin-top:4px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
              <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);">CALM</span>
              <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);">ELEVATED</span>
              <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);">EXTREME</span>
            </div>
            <div style="height:5px;background:var(--p2);border:1px solid var(--b2);border-radius:2px;overflow:hidden;">
              <div id="vi-bar" style="height:100%;width:0%;background:var(--green);border-radius:2px;transition:width 0.6s ease,background 0.4s;"></div>
            </div>
          </div>
          <!-- Verdict -->
          <div id="vi-verdict" style="margin-top:6px;padding:8px 12px;border-left:3px solid var(--green);background:rgba(0,255,136,0.04);font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--green);letter-spacing:1px;">—</div>
        </div>
      </div>

      <!-- TREND EMOTION -->
      <div class="card">
        <div class="card-title">📈 TREND EMOTION</div>
        <div style="display:flex;flex-direction:column;gap:10px;padding:4px 0;">
          <!-- RSI row with mini gauge -->
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--dim);letter-spacing:1px;">RSI(14):</span>
            <span id="te-rsi" style="font-family:Share Tech Mono,monospace;font-size:0.88rem;font-weight:700;color:var(--gold);">—</span>
          </div>
          <!-- RSI bar -->
          <div style="position:relative;height:5px;background:linear-gradient(90deg,var(--green) 0%,var(--green) 30%,var(--gold) 30%,var(--gold) 70%,var(--red) 70%,var(--red) 100%);border-radius:2px;opacity:0.35;">
            <div id="te-rsi-needle" style="position:absolute;top:-3px;width:3px;height:11px;background:var(--white);border-radius:1px;left:50%;transition:left 0.5s ease;"></div>
          </div>
          <div style="display:flex;justify-content:space-between;margin-top:-6px;">
            <span style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);">0 — Oversold</span>
            <span style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);">Overbought — 100</span>
          </div>
          <!-- SMA context -->
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--dim);letter-spacing:1px;">Price vs SMA20:</span>
            <span id="te-vs-sma20" style="font-family:Share Tech Mono,monospace;font-size:0.8rem;font-weight:600;">—</span>
          </div>
          <div style="display:flex;gap:16px;">
            <div>
              <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;">SMA20</span><br>
              <span id="te-sma20" style="font-family:Share Tech Mono,monospace;font-size:0.82rem;font-weight:600;color:#7FFFD4;">—</span>
            </div>
            <div>
              <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;">SMA50</span><br>
              <span id="te-sma50" style="font-family:Share Tech Mono,monospace;font-size:0.82rem;font-weight:600;color:#B5B5FF;">—</span>
            </div>
          </div>
          <!-- SMA position label -->
          <div id="te-sma-pos" style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--dim);letter-spacing:1px;">— SMA — · — SMA —</div>
          <!-- Trend verdict -->
          <div id="te-verdict" style="margin-top:2px;padding:8px 12px;border-left:3px solid var(--green);background:rgba(0,255,136,0.04);font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--green);letter-spacing:1px;">—</div>
        </div>
      </div>

    </div><!-- end g2 vol+trend -->

    <!-- Nakshatra Alignment -->
    <div class="card" style="margin-top:10px; background: linear-gradient(135deg, rgba(20,20,30,0.8), rgba(10,10,20,0.9)); border: 1px solid var(--gold);">
      <div class="card-title" style="color:var(--gold); border-bottom: 1px solid rgba(255,204,0,0.2);">✨ NAKSHATRA ALIGNMENT</div>
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap: 10px; margin-top: 5px;">
         <div style="flex: 1; min-width: 200px;">
             <div style="font-size: 1.4rem; font-weight: bold; color: var(--gold);" id="chart-nakshatra-name">—</div>
             <div style="font-family:Share Tech Mono, monospace; font-size: 0.85rem; color: var(--dim);">RULING PLANET: <span style="color:var(--text);" id="chart-nakshatra-lord">—</span></div>
         </div>
         <div style="flex: 2; text-align: right; min-width: 200px;">
             <div style="font-size: 0.8rem; color: var(--dim); margin-bottom:4px;">FAVORED SECTORS TODAY</div>
             <div style="display:flex; gap:6px; flex-wrap:wrap; justify-content:flex-end;" id="chart-nakshatra-sectors">
             </div>
         </div>
      </div>
      <div style="margin-top: 15px; font-size: 0.85rem; color: var(--dim); line-height: 1.6; border-top: 1px dashed rgba(255,255,255,0.1); padding-top: 10px; display: flex; align-items: center; justify-content: space-between;">
          <div style="flex: 1;">
              Instrument Sector: <span style="color:var(--text); font-weight: bold;" id="chart-nakshatra-inst-sector">—</span>
          </div>
          <div id="chart-nakshatra-verdict" style="padding: 6px 12px; font-family: Share Tech Mono, monospace; font-weight: bold; border-radius: 2px;">
              —
          </div>
      </div>
    </div>

  </div><!-- end chart-content -->
</div><!-- end page-chart -->


"""


JS = r"""
async function loadChart() {
  const sym=document.getElementById('chart-sym').value;
  let price=parseFloat(document.getElementById('chart-price').value)||0;
  if(!sym)return;
  if(!price||GANN_DATE!==today){
    try{const px=await api('price',{symbol:sym,date:GANN_DATE});if(px.close){price=px.close;document.getElementById('chart-price').value=price;}}catch(e){}
  }
  loading('chart-loading',true); show('chart-content',false);
  try {
    const d=await api('quant',{symbol:sym,price:price||''});
    try {
      const ptfRes = await api('portfolio_get', {symbol: sym});
      if(ptfRes.ok && ptfRes.trades) {
        const openTrades = ptfRes.trades.filter(t => t.status === 'OPEN');
        if(openTrades.length > 0) {
          if(!d.support_resistance) d.support_resistance = {};
          if(!d.support_resistance.levels) d.support_resistance.levels = [];
          
          const t = openTrades[0];
          d.support_resistance.levels.push({price: t.entry_price, label: "ENTRY", strength: 1.0, type: "pivot"});
          d.support_resistance.levels.push({price: t.target1, label: "T1", strength: 1.0, type: "res"});
          d.support_resistance.levels.push({price: t.target2, label: "T2", strength: 1.0, type: "res"});
          d.support_resistance.levels.push({price: t.stop_loss, label: "SL", strength: 1.0, type: "sup"});
        }
      }
    } catch(e) {}
    renderChart(d);
  } catch(e) {
    document.getElementById('chart-loading').innerHTML=`<div class="err">${e.message}</div>`;
  }
}

// ── Period selector state ─────────────────────────────────────────
TV.period = '1Y';

function tvSetPeriod(p) {
  TV.period = p;
  if (TV.data) {
    tvDrawSummaryChart();
    tvBuildPeriodCards(); // rebuild to update active state
  }
}

function tvGetPeriodDates(period, dates) {
  // Return start index for each period
  if (!dates || !dates.length) return 0;
  const last = new Date(dates[dates.length-1]);
  let cutoff;
  const y=last.getFullYear(), m=last.getMonth(), d=last.getDate();
  if      (period==='1D')  cutoff = new Date(y,m,d-1);
  else if (period==='5D')  cutoff = new Date(y,m,d-7);
  else if (period==='1M')  cutoff = new Date(y,m-1,d);
  else if (period==='6M')  cutoff = new Date(y,m-6,d);
  else if (period==='YTD') cutoff = new Date(y,0,1);
  else if (period==='1Y')  cutoff = new Date(y-1,m,d);
  else if (period==='5Y')  cutoff = new Date(y-5,m,d);
  else if (period==='10Y') cutoff = new Date(y-10,m,d);
  else                     return 0; // ALL
  const ts = cutoff.getTime();
  for (let i=0; i<dates.length; i++) {
    if (new Date(dates[i]).getTime() >= ts) return i;
  }
  return 0;
}

function tvCalcReturn(closes, fromIdx) {
  if (fromIdx >= closes.length-1) return null;
  const start = closes[fromIdx], end = closes[closes.length-1];
  return ((end - start) / start * 100);
}

function tvDrawSummaryChart() {
  const cvs = document.getElementById('summary-canvas');
  if (!cvs || !TV.data) return;
  const dpr = window.devicePixelRatio || 1;
  const W = cvs.offsetWidth || 800;
  const H = 180;
  cvs.width  = Math.round(W * dpr);
  cvs.height = Math.round(H * dpr);
  cvs.style.width = W+'px'; cvs.style.height = H+'px';
  const ctx = cvs.getContext('2d');
  ctx.scale(dpr, dpr);

  const {closes, dates} = TV.data;
  const fromIdx = tvGetPeriodDates(TV.period, dates);
  const sl = closes.slice(fromIdx);
  const N = sl.length;
  if (N < 2) return;

  const minV = Math.min(...sl) * 0.998;
  const maxV = Math.max(...sl) * 1.002;
  const PAD = {t:10, r:0, b:24, l:0};
  const cW = W-PAD.l-PAD.r, cH = H-PAD.t-PAD.b;
  const xS = i => PAD.l + (i/(N-1)) * cW;
  const yS = v => PAD.t + cH*(1-(v-minV)/(maxV-minV));

  const ret = tvCalcReturn(closes, fromIdx);
  const isUp = ret === null || ret >= 0;
  const lineCol  = isUp ? '#26a69a' : '#ef5350';
  const fillCol  = isUp ? 'rgba(38,166,154,' : 'rgba(239,83,80,';

  // Background
  ctx.fillStyle = '#060f16'; ctx.fillRect(0,0,W,H);

  // Area fill with gradient
  const grad = ctx.createLinearGradient(0,PAD.t,0,PAD.t+cH);
  grad.addColorStop(0, fillCol+'0.18)');
  grad.addColorStop(1, fillCol+'0.01)');
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.moveTo(xS(0), yS(sl[0]));
  sl.forEach((v,i) => ctx.lineTo(xS(i), yS(v)));
  ctx.lineTo(xS(N-1), PAD.t+cH); ctx.lineTo(xS(0), PAD.t+cH);
  ctx.closePath(); ctx.fill();

  // Line
  ctx.strokeStyle = lineCol; ctx.lineWidth = 1.5;
  ctx.beginPath();
  sl.forEach((v,i) => i===0 ? ctx.moveTo(xS(i),yS(v)) : ctx.lineTo(xS(i),yS(v)));
  ctx.stroke();

  // Baseline (start price)
  const baseY = yS(sl[0]);
  ctx.strokeStyle = 'rgba(255,255,255,0.06)'; ctx.lineWidth=0.5; ctx.setLineDash([4,4]);
  ctx.beginPath(); ctx.moveTo(0,baseY); ctx.lineTo(W,baseY); ctx.stroke(); ctx.setLineDash([]);

  // X-axis date labels
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  ctx.fillStyle='#3a5a70'; ctx.font=`9px Share Tech Mono`; ctx.textAlign='center';
  const step = Math.max(1, Math.floor(N/6));
  for (let i=0; i<N; i+=step) {
    const ds = dates[fromIdx+i];
    if (!ds) continue;
    const mo = parseInt(ds.slice(5,7))-1;
    const yr = ds.slice(2,4);
    const lbl = N > 250 ? MONTHS[mo]+String.fromCharCode(39)+yr : MONTHS[mo]+' '+parseInt(ds.slice(8));
    ctx.fillText(lbl, xS(i), H-6);
  }

  // Hover line
  cvs._fromIdx = fromIdx;
  cvs._sl = sl;
  cvs._xS = xS; cvs._yS = yS;
  cvs._cH = cH; cvs._PAD = PAD;
}

function tvBuildPeriodCards() {
  const el = document.getElementById('tv-period-cards');
  if (!el || !TV.data) return;
  const {closes, dates} = TV.data;
  const periods = ['1D','5D','1M','6M','YTD','1Y','5Y','10Y','ALL'];
  const labels  = ['1 day','5 days','1 month','6 months','Year to date','1 year','5 years','10 years','All time'];
  el.innerHTML = periods.map((p,pi) => {
    const idx = tvGetPeriodDates(p, dates);
    const ret = tvCalcReturn(closes, idx);
    const col = ret === null ? 'var(--dim)' : ret >= 0 ? '#26a69a' : '#ef5350';
    const val = ret === null ? '—' : (ret>=0?'+':'')+ret.toFixed(2)+'%';
    const isActive = p === TV.period;
    return `<div id="period-${p}" onclick="tvSetPeriod('${p}')"
      style="padding:10px 4px;text-align:center;border-right:1px solid rgba(255,255,255,0.04);cursor:pointer;
      background:${isActive?'rgba(0,212,255,0.08)':'transparent'};
      border-bottom:${isActive?'2px solid var(--cyan)':'2px solid transparent'};
      transition:all 0.15s;"
      onmouseover="this.style.background='rgba(255,255,255,0.04)'"
      onmouseout="this.style.background='${isActive?'rgba(0,212,255,0.08)':'transparent'}'">
      <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:${isActive?'var(--cyan)':'var(--dim)'};margin-bottom:4px;letter-spacing:0.5px;">${labels[pi]}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.85rem;font-weight:700;color:${col};">${val}</div>
    </div>`;
  }).join('');
}

function renderChart(d) {
  loading('chart-loading',false); show('chart-content');
  window._chartGexProfile = d.gex_profile || null;
  const reg=d.regime||{}, m=reg.metrics||{}, sr=d.support_resistance||{};
  const cur=sr.current_price||d.current_price;
  const chart=d.chart||{};

  // ── Populate TradingView summary card ──
  const sel2 = document.getElementById('chart-sym');
  const symName = sel2 ? (sel2.options[sel2.selectedIndex]?.text||'').split('—')[0].trim() : '';
  const symFull = sel2 ? (sel2.options[sel2.selectedIndex]?.text||'') : '';
  const symNameEl = document.getElementById('tv-summary-sym');
  const symFullEl = document.getElementById('tv-summary-name');
  if (symNameEl) symNameEl.textContent = symName;
  if (symFullEl) symFullEl.textContent = symFull.includes('—') ? symFull.split('—')[1]?.trim() : '';
  // Price + change
  const priceEl  = document.getElementById('tv-summary-price');
  const changeEl = document.getElementById('tv-summary-change');
  if (priceEl && cur) priceEl.textContent = cur.toLocaleString('en-IN');
  if (changeEl) {
    const ret=m.ret_20d||0; const col=ret>=0?'#26a69a':'#ef5350';
    changeEl.textContent=(ret>=0?'+':'')+ret+'%';
    changeEl.style.color=col;
  }

  // Info bar (hidden infobar still needed for full chart)
  const symEl=document.getElementById('tv-sym-label');
  if(symEl){const sel=document.getElementById('chart-sym');if(sel)symEl.textContent=(sel.options[sel.selectedIndex]?.text||'').split('—')[0].trim();}
  const bar=document.getElementById('tv-ohlcv-bar');
  if(bar&&cur){
    const ret=m.ret_20d||0;const col=ret>=0?'#26a69a':'#ef5350';
    bar.innerHTML=`CMP: <b style="color:${col}">${cur.toLocaleString()}</b>  `
      +`<span style="color:#4a7090">20D:<b style="color:${col}">${ret>=0?'+':''}${ret}%</b>  `
      +`Vol:<b style="color:#7aa8c0">${m.annual_vol_pct||'--'}%</b>  `
      +`SMA200:<b style="color:#7FFFD4">${m.sma200||'--'}</b></span>`;
  }

  // ── Populate stat cards under header ──
  const _sc = document.getElementById('chart-stat-cards');
  if(_sc) _sc.style.display='block';
  const _ret=m.ret_20d||0, _retCol=_ret>=0?'#26a69a':'#ef5350';
  const _setCard=(id,val,col)=>{ const el=document.getElementById(id); if(el){el.textContent=val;if(col)el.style.color=col;} };
  _setCard('stat-sma20',  m.sma20  ? Number(m.sma20).toLocaleString('en-IN')  : '—', '#7FFFD4');
  _setCard('stat-sma50',  m.sma50  ? Number(m.sma50).toLocaleString('en-IN')  : '—', '#B5B5FF');
  _setCard('stat-sma200', m.sma200 ? Number(m.sma200).toLocaleString('en-IN') : '—', '#DEB887');
  _setCard('stat-ret20',  _ret!==0 ? (_ret>=0?'+':'')+_ret+'%' : '—', _retCol);
  _setCard('stat-vol',    m.annual_vol_pct ? m.annual_vol_pct+'%' : '—', 'var(--gold)');

  // Store data
  const closes=chart.closes||[];
  const _rawOpens=chart.opens||[];
  const opens=(_rawOpens.length===closes.length)?_rawOpens:closes.map((c,i)=>i>0?closes[i-1]:c);
  const highs=chart.highs||closes.map(c=>c*1.005),lows=chart.lows||closes.map(c=>c*0.995);
  const volumes=chart.volumes||closes.map(()=>0),dates=chart.dates||[];
  TV.data={dates,opens,highs,lows,closes,volumes,sr,currentPrice:cur};

  const total=closes.length;
  TV.mainH=460; TV._eventsAttached=false; TV.yRange={min:null,max:null}; TV.measureResult=null; TV.measureState=null;

  // Size canvas — use RAF to ensure DOM has fully laid out before measuring
  const _sizeAndDraw = () => {
    const wrap2=document.getElementById('tv-chart-card');
    if(wrap2){
      const W2=Math.floor(wrap2.getBoundingClientRect().width)||wrap2.scrollWidth||1100;
      const cvs2=document.getElementById('price-canvas');
      if(cvs2){
        cvs2.width=W2; cvs2.style.width=W2+'px';
        cvs2.height=TV.mainH; cvs2.style.height=TV.mainH+'px';
      }
    }
    tvRedraw();
  };
  // Add resize observer so chart fills width whenever window resizes
  if (!TV._resizeObserver && typeof ResizeObserver !== 'undefined') {
    const card = document.getElementById('tv-chart-card');
    if (card) {
      TV._resizeObserver = new ResizeObserver(() => { if(TV.data) tvRedraw(); });
      TV._resizeObserver.observe(card);
    }
  }
  requestAnimationFrame(_sizeAndDraw);
  // Initial view: last 252 trading days (~1 year).
  // Full history is stored in TV.data — panning left reveals older bars.
  const INITIAL_BARS = 252;
  TV.view.start = Math.max(0, total - INITIAL_BARS);
  TV.view.end   = total;

  // ── Draw summary line chart + period cards ──
  requestAnimationFrame(() => {
    tvSetPeriod(TV.period || '1Y');
    tvBuildPeriodCards();
    // Summary canvas hover
    const sumCvs = document.getElementById('summary-canvas');
    if (sumCvs && !sumCvs._hoverAttached) {
      sumCvs._hoverAttached = true;
      sumCvs.addEventListener('mousemove', e => {
        if (!sumCvs._sl) return;
        const rect = sumCvs.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const N = sumCvs._sl.length;
        const i = Math.max(0, Math.min(N-1, Math.round(x / rect.width * (N-1))));
        const absI = (sumCvs._fromIdx||0) + i;
        const v = sumCvs._sl[i];
        const ret2 = v && sumCvs._sl[0] ? ((v - sumCvs._sl[0]) / sumCvs._sl[0] * 100).toFixed(2) : '0.00';
        const col2 = parseFloat(ret2)>=0 ? '#26a69a' : '#ef5350';
        const hover = document.getElementById('summary-hover');
        if (hover) {
          hover.style.display = 'block';
          hover.innerHTML = `<span style="color:#4a7090">${TV.data.dates[absI]||''}</span>  `
            +`<b style="color:#c8e0ed">${v?.toFixed(0)||'—'}</b>  `
            +`<b style="color:${col2}">${parseFloat(ret2)>=0?'+':''}${ret2}%</b>`;
        }
        tvDrawSummaryChart();
        const ctx2 = sumCvs.getContext('2d');
        const dpr2 = window.devicePixelRatio||1;
        ctx2.scale(dpr2,dpr2);
        if (sumCvs._xS && sumCvs._yS) {
          const cx2=sumCvs._xS(i), cy2=sumCvs._yS(v);
          ctx2.strokeStyle='rgba(200,200,200,0.3)'; ctx2.lineWidth=0.7;
          ctx2.beginPath();ctx2.moveTo(cx2,sumCvs._PAD.t);ctx2.lineTo(cx2,sumCvs._PAD.t+sumCvs._cH);ctx2.stroke();
          ctx2.fillStyle='rgba(200,200,200,0.9)';
          ctx2.beginPath();ctx2.arc(cx2,cy2,3,0,Math.PI*2);ctx2.fill();
        }
      });
      sumCvs.addEventListener('mouseleave', () => {
        const hover = document.getElementById('summary-hover');
        if (hover) hover.style.display='none';
        tvDrawSummaryChart();
      });
    }
  });


  requestAnimationFrame(() => { _sizeAndDraw(); tvSetupInteraction(); });


  // S/R tables
  const srRow=(lvl,isS)=>{
    const dc=lvl.distance_pct<1?'var(--gold)':lvl.distance_pct<3?'var(--orange)':'var(--text)';
    const sc={'STRONG':'bg','MODERATE':'bgo','WEAK':'bd'}[lvl.strength]||'bd';
    return `<div class="trow" style="grid-template-columns:1fr 60px 50px 60px;">
      <div style="font-family:Share Tech Mono,monospace;font-weight:600;color:${isS?'var(--green)':'var(--red)'};">${lvl.price.toLocaleString()}</div>
      <div style="color:${dc};font-family:Share Tech Mono,monospace;font-size:0.75rem;">${lvl.distance_pct}%</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--dim);">${lvl.touches}x</div>
      <div><span class="badge ${sc}">${lvl.strength}</span></div></div>`;
  };
  const hdr=`<div class="trow hdr" style="grid-template-columns:1fr 60px 50px 60px;"><div>LEVEL</div><div>DIST%</div><div>HITS</div><div>STR</div></div>`;
  document.getElementById('support-table').innerHTML=hdr+(sr.supports||[]).map(l=>srRow(l,true)).join('')||'<div style="padding:10px;color:var(--dim);">None found</div>';
  document.getElementById('resistance-table').innerHTML=hdr+(sr.resistances||[]).map(l=>srRow(l,false)).join('')||'<div style="padding:10px;color:var(--dim);">None found</div>';

  // ── Volatility Index ──────────────────────────────────────────────
  const annVol    = parseFloat(m.annual_vol_pct) || 0;
  const chart2    = d.chart || {};
  const closes2   = chart2.closes || [];
  // compute 21-day realised vol from closes if available
  let vol21 = 0;
  if (closes2.length >= 22) {
    const tail = closes2.slice(-22);
    const rets = tail.slice(1).map((c,i) => Math.log(c / tail[i]));
    const mean = rets.reduce((a,b)=>a+b,0)/rets.length;
    const variance = rets.reduce((a,r)=>a+(r-mean)**2,0)/(rets.length-1);
    vol21 = Math.round(Math.sqrt(variance * 252) * 1000) / 10;
  }
  const volRatio = (annVol > 0 && vol21 > 0) ? Math.round(vol21 / annVol * 100) / 100 : null;

  const _set = (id, val) => { const el=document.getElementById(id); if(el) el.textContent=val; };
  const _setStyle = (id, prop, val) => { const el=document.getElementById(id); if(el) el.style[prop]=val; };

  _set('vi-annual',  annVol ? annVol+'%' : '—');
  _set('vi-recent',  vol21  ? vol21+'%'  : '—');
  _set('vi-ratio',   volRatio ? volRatio+'x' : '—');

  // Gauge bar: annVol mapped 0%→0px, 50%→100%
  const barPct = Math.min(100, Math.round(annVol / 50 * 100));
  const barCol  = annVol < 20 ? 'var(--green)' : annVol < 35 ? 'var(--gold)' : 'var(--red)';
  _setStyle('vi-bar', 'width',      barPct+'%');
  _setStyle('vi-bar', 'background', barCol);

  // Verdict
  let viText = '', viBorder = '', viBg = '', viColor = '';
  if (annVol < 20) {
    viText='CALM — Below-average volatility'; viBorder='var(--green)'; viBg='rgba(0,255,136,0.04)'; viColor='var(--green)';
  } else if (annVol < 30) {
    viText='NORMAL — Average volatility range'; viBorder='var(--cyan)'; viBg='rgba(0,212,255,0.04)'; viColor='var(--cyan)';
  } else if (annVol < 45) {
    viText='ELEVATED — Above-average volatility'; viBorder='var(--gold)'; viBg='rgba(255,204,0,0.04)'; viColor='var(--gold)';
  } else {
    viText='EXTREME — High-risk volatility zone'; viBorder='var(--red)'; viBg='rgba(255,51,85,0.04)'; viColor='var(--red)';
  }
  const viEl = document.getElementById('vi-verdict');
  if (viEl) { viEl.textContent=viText; viEl.style.borderLeftColor=viBorder; viEl.style.background=viBg; viEl.style.color=viColor; }

  // ── Trend Emotion ─────────────────────────────────────────────────
  // Compute RSI(14) from closes
  let rsi = 0;
  if (closes2.length >= 15) {
    const tail14 = closes2.slice(-15);
    let gains = 0, losses = 0;
    for (let _i=1; _i<tail14.length; _i++) {
      const chg = tail14[_i] - tail14[_i-1];
      if (chg > 0) gains += chg; else losses -= chg;
    }
    const avgG = gains / 14, avgL = losses / 14;
    rsi = avgL === 0 ? 100 : Math.round((100 - 100 / (1 + avgG / avgL)) * 10) / 10;
  }
  const sma20v  = parseFloat(m.sma20)  || 0;
  const sma50v  = parseFloat(m.sma50)  || 0;
  const cmpv    = parseFloat(cur) || 0;
  const vsSma20 = (sma20v && cmpv) ? Math.round((cmpv - sma20v) / sma20v * 1000) / 10 : null;

  _set('te-rsi',  rsi ? rsi.toFixed(1) : '—');
  const rsiNeedle = document.getElementById('te-rsi-needle');
  if (rsiNeedle && rsi) {
    rsiNeedle.style.left = Math.min(99, Math.max(1, rsi))+'%';
    rsiNeedle.style.background = rsi < 30 ? 'var(--green)' : rsi > 70 ? 'var(--red)' : 'var(--gold)';
  }
  const rsiEl = document.getElementById('te-rsi');
  if (rsiEl && rsi) rsiEl.style.color = rsi < 30 ? 'var(--green)' : rsi > 70 ? 'var(--red)' : 'var(--gold)';

  _set('te-vs-sma20', vsSma20 !== null ? (vsSma20>=0?'+':'')+vsSma20+'%' : '—');
  const vsEl = document.getElementById('te-vs-sma20');
  if (vsEl && vsSma20 !== null) vsEl.style.color = vsSma20 >= 0 ? 'var(--green)' : 'var(--red)';

  _set('te-sma20', sma20v ? '₹'+Number(sma20v).toLocaleString('en-IN') : '—');
  _set('te-sma50', sma50v ? '₹'+Number(sma50v).toLocaleString('en-IN') : '—');

  // SMA position labels
  const abv20 = cmpv >= sma20v;
  const abv50 = cmpv >= sma50v;
  const pos20 = abv20 ? '<span style="color:var(--green);">Above SMA20</span>' : '<span style="color:var(--red);">Below SMA20</span>';
  const pos50 = abv50 ? '<span style="color:var(--green);">Above SMA50</span>' : '<span style="color:var(--red);">Below SMA50</span>';
  const smaPos = document.getElementById('te-sma-pos');
  if (smaPos) smaPos.innerHTML = pos20 + ' · ' + pos50;

  // Trend verdict
  let teText='', teBorder='', teBg='', teColor='';
  if (rsi > 70) {
    teText='OVERBOUGHT — RSI '+rsi.toFixed(0)+' (Extended)'; teBorder='var(--red)'; teBg='rgba(255,51,85,0.04)'; teColor='var(--red)';
  } else if (rsi > 55 && abv20 && abv50) {
    teText='BULLISH — RSI '+rsi.toFixed(0)+' (Strong)'; teBorder='var(--green)'; teBg='rgba(0,255,136,0.04)'; teColor='var(--green)';
  } else if (rsi >= 45) {
    teText='NEUTRAL — RSI '+rsi.toFixed(0)+' (Consolidating)'; teBorder='var(--cyan)'; teBg='rgba(0,212,255,0.04)'; teColor='var(--cyan)';
  } else if (rsi >= 30) {
    teText='BEARISH — RSI '+rsi.toFixed(0)+' (Weak)'; teBorder='var(--orange)'; teBg='rgba(255,136,0,0.04)'; teColor='var(--orange)';
  } else {
    teText='OVERSOLD — RSI '+rsi.toFixed(0)+' (Capitulation)'; teBorder='var(--green)'; teBg='rgba(0,255,136,0.06)'; teColor='var(--green)';
  }
  const teEl = document.getElementById('te-verdict');
  if (teEl) { teEl.textContent=teText; teEl.style.borderLeftColor=teBorder; teEl.style.background=teBg; teEl.style.color=teColor; }

  // ── Nakshatra Alignment ───────────────────────────────────────────
  const nakName = d.transit_moon_nakshatra || "—";
  const nakLord = d.transit_moon_nakshatra_lord || "—";
  const nakSectors = d.transit_moon_nakshatra_sectors || [];
  const instSector = d.instrument_sector || "—";

  _set('chart-nakshatra-name', nakName);
  _set('chart-nakshatra-lord', nakLord);
  _set('chart-nakshatra-inst-sector', instSector);

  const secEl = document.getElementById('chart-nakshatra-sectors');
  if (secEl) {
    secEl.innerHTML = nakSectors.map(s => `<span class="badge bgo" style="background:rgba(255,204,0,0.1);color:var(--gold);border:1px solid rgba(255,204,0,0.3);">${s}</span>`).join('');
  }

  const verEl = document.getElementById('chart-nakshatra-verdict');
  if (verEl) {
    let isAligned = false;
    for (let s of nakSectors) {
        if (instSector && instSector !== "—" && (s.toLowerCase().includes(instSector.toLowerCase()) || instSector.toLowerCase().includes(s.toLowerCase()))) {
            isAligned = true;
            break;
        }
    }

    if (isAligned) {
      verEl.textContent = "ALIGNED: +CONFIDENCE";
      verEl.style.color = "var(--green)";
      verEl.style.background = "rgba(0, 255, 136, 0.1)";
      verEl.style.border = "1px solid rgba(0, 255, 136, 0.3)";
    } else {
      verEl.textContent = "NEUTRAL ALIGNMENT";
      verEl.style.color = "var(--dim)";
      verEl.style.background = "rgba(255, 255, 255, 0.05)";
      verEl.style.border = "1px solid rgba(255, 255, 255, 0.1)";
    }
  }
}

// ── Expand to new window ───────────────────────────────────────────
function openChartWindow() {
  if(!TV.data){alert('Draw a chart first.');return;}
  try{
    const _sel=document.getElementById('chart-sym');
    const _symName=_sel?(_sel.options[_sel.selectedIndex]?.text||'').split('—')[0].trim():'';
    sessionStorage.setItem('tvChartState',JSON.stringify({
      sym:_symName,
      data:{dates:TV.data.dates,opens:TV.data.opens,highs:TV.data.highs,lows:TV.data.lows,
            closes:TV.data.closes,volumes:TV.data.volumes,currentPrice:TV.data.currentPrice,sr:TV.data.sr},
      chartType:TV.chartType,indicators:{...TV.indicators},
      params:{...TV.params,smaP:[...TV.params.smaP]},view:{...TV.view}
    }));
  }catch(e){alert('Error: '+e.message);return;}
  window.open('http://localhost:5050/?chartWindow=1', '_blank');
}


// ════════════════════════════════════════════════════════════════════
// SIMONS LAB
// ════════════════════════════════════════════════════════════════════

// ══════════════════════════════════════════════════════════════════════════════
// CHART ORDER PANEL — BUY/SELL overlay + order ticket + position lines
// ══════════════════════════════════════════════════════════════════════════════

let _chartOrderSide = 'BUY';
let _chartOpenPos   = null;   // {id, symbol, entry_price, shares, stop_loss, target1, target2, inv_type}

// ── Open order modal ──────────────────────────────────────────────────────────
function chartShowOrder(side) {
  _chartOrderSide = side;
  const sym  = document.getElementById('chart-sym')?.value || '';
  const cmp  = parseFloat(document.getElementById('chart-price')?.value || 0) || 0;
  if (!sym || !cmp) { alert('Load a chart first (click DRAW).'); return; }

  // Pre-fill fields with GANN signal data if available
  const entry = cmp;
  const sl    = cmp > 0 ? parseFloat((cmp * 0.97).toFixed(2)) : 0;   // 3% SL default
  const t1    = cmp > 0 ? parseFloat((cmp * 1.05).toFixed(2)) : 0;   // 5% T1 default
  const t2    = cmp > 0 ? parseFloat((cmp * 1.10).toFixed(2)) : 0;   // 10% T2 default

  document.getElementById('modal-sym').textContent   = sym;
  document.getElementById('modal-cmp').textContent   = '₹' + cmp.toFixed(2);
  document.getElementById('modal-entry').value        = entry;
  document.getElementById('modal-sl').value           = sl;
  document.getElementById('modal-t1').value           = t1;
  document.getElementById('modal-t2').value           = t2;
  document.getElementById('modal-qty').value          = 1;
  document.getElementById('modal-err').style.display  = 'none';

  chartSetSide(side);
  chartUpdateCost();

  const modal = document.getElementById('chart-order-modal');
  modal.style.display = 'flex';
}

// ── Toggle BUY/SELL side in modal ─────────────────────────────────────────────
function chartSetSide(side) {
  _chartOrderSide = side;
  const buyTab  = document.getElementById('modal-buy-tab');
  const sellTab = document.getElementById('modal-sell-tab');
  const placeBtn = document.getElementById('modal-place-btn');

  if (side === 'BUY') {
    buyTab.style.background    = '#1B5E35';
    buyTab.style.borderColor   = '#26a269';
    buyTab.style.color         = '#4ade80';
    sellTab.style.background   = 'transparent';
    sellTab.style.borderColor  = 'var(--border)';
    sellTab.style.color        = 'var(--dim)';
    placeBtn.style.background  = '#1B5E35';
    placeBtn.style.borderColor = '#26a269';
    placeBtn.style.color       = '#4ade80';
    placeBtn.textContent       = 'PLACE BUY ORDER';
  } else {
    sellTab.style.background   = '#5C1A1A';
    sellTab.style.borderColor  = '#c0392b';
    sellTab.style.color        = '#f87171';
    buyTab.style.background    = 'transparent';
    buyTab.style.borderColor   = 'var(--border)';
    buyTab.style.color         = 'var(--dim)';
    placeBtn.style.background  = '#5C1A1A';
    placeBtn.style.borderColor = '#c0392b';
    placeBtn.style.color       = '#f87171';
    placeBtn.textContent       = 'PLACE SELL ORDER';
  }
}

// ── Update cost summary in real time ─────────────────────────────────────────
function chartUpdateCost() {
  const qty   = parseInt(document.getElementById('modal-qty')?.value   || 1)   || 1;
  const entry = parseFloat(document.getElementById('modal-entry')?.value || 0) || 0;
  const sl    = parseFloat(document.getElementById('modal-sl')?.value   || 0)  || 0;
  const t1    = parseFloat(document.getElementById('modal-t1')?.value   || 0)  || 0;

  const cost   = qty * entry;
  const profit = t1 > 0 ? (t1 - entry) * qty : 0;
  const loss   = sl  > 0 ? (entry - sl)  * qty : 0;
  const rr     = loss > 0 ? (profit / loss).toFixed(2) : '—';

  const fmt = v => '₹' + Math.abs(v).toLocaleString('en-IN', {maximumFractionDigits: 2});
  document.getElementById('modal-cost').textContent   = fmt(cost);
  document.getElementById('modal-profit').textContent = profit > 0 ? fmt(profit) : '—';
  document.getElementById('modal-loss').textContent   = loss   > 0 ? fmt(loss)   : '—';
  document.getElementById('modal-rr').textContent     = rr !== '—' ? '1 : ' + rr : '—';
  document.getElementById('modal-rr').style.color     = parseFloat(rr) >= 2
    ? 'var(--green)' : parseFloat(rr) >= 1 ? 'var(--gold)' : 'var(--red)';
}

// ── Close modal ───────────────────────────────────────────────────────────────
function chartCloseModal() {
  document.getElementById('chart-order-modal').style.display = 'none';
}

// ── Place order → fires portfolio_add ────────────────────────────────────────
async function chartPlaceOrder() {
  const sym    = document.getElementById('modal-sym').textContent;
  const qty    = parseInt(document.getElementById('modal-qty')?.value   || 0);
  const entry  = parseFloat(document.getElementById('modal-entry')?.value || 0);
  const sl     = parseFloat(document.getElementById('modal-sl')?.value   || 0);
  const t1     = parseFloat(document.getElementById('modal-t1')?.value   || 0);
  const t2     = parseFloat(document.getElementById('modal-t2')?.value   || 0);
  const itype  = document.getElementById('modal-type')?.value || 'swing';
  const errEl  = document.getElementById('modal-err');

  if (!sym || qty < 1 || entry <= 0) {
    errEl.textContent = 'Symbol, quantity and entry price are required.';
    errEl.style.display = 'block'; return;
  }

  const btn = document.getElementById('modal-place-btn');
  btn.disabled = true;
  btn.textContent = 'PLACING…';
  errEl.style.display = 'none';

  try {
    const res = await api('portfolio_add', {
      symbol:      sym,
      inv_type:    itype,
      entry_price: entry,
      shares:      qty,
      stop_loss:   sl,
      target1:     t1,
      target2:     t2,
    });

    if (res && res.ok) {
      chartCloseModal();
      // Store open position and show badge + lines
      _chartOpenPos = { id: res.trade_id || res.id, symbol: sym,
        entry_price: entry, shares: qty, stop_loss: sl, target1: t1,
        target2: t2, inv_type: itype, cmp: entry };
      chartUpdatePosBadge();
      chartDrawPositionLines();
      // Show success toast
      const toast = document.createElement('div');
      toast.textContent = (_chartOrderSide === 'BUY' ? '✅ BUY' : '✅ SELL') +
        ' order placed — ' + sym + ' × ' + qty + ' @ ₹' + entry.toFixed(2);
      toast.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);' +
        'background:#1B5E35;color:#4ade80;padding:10px 20px;border-radius:6px;' +
        'font-family:Share Tech Mono,monospace;font-size:0.78rem;z-index:99999;';
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 3500);
    } else {
      errEl.textContent = (res && res.error) || 'Order failed — check server logs.';
      errEl.style.display = 'block';
    }
  } catch(e) {
    errEl.textContent = 'Network error: ' + (e.message || String(e));
    errEl.style.display = 'block';
  } finally {
    btn.disabled = false;
    btn.textContent = _chartOrderSide === 'BUY' ? 'PLACE BUY ORDER' : 'PLACE SELL ORDER';
  }
}

// ── Update open position badge ────────────────────────────────────────────────
async function chartUpdatePosBadge() {
  const badge = document.getElementById('chart-pos-badge');
  const sym   = document.getElementById('chart-sym')?.value || '';
  if (!sym) { if(badge) badge.style.display = 'none'; return; }

  // Check if this symbol has an open position in the portfolio
  try {
    const res = await api('portfolio_get', {});
    if (!res || !res.ok) return;
    const pos = (res.trades || []).find(t => t.symbol === sym && t.status !== 'CLOSED');
    if (!pos) { badge.style.display = 'none'; _chartOpenPos = null; return; }

    // Fetch CMP
    const _today = (typeof today !== 'undefined') ? today : new Date().toISOString().slice(0,10);
    let cmp = pos.entry_price;
    try { const px = await api('price', {symbol: sym, date: _today}); cmp = px.close || cmp; } catch {}

    _chartOpenPos = { ...pos, cmp };
    const pnl    = (cmp - pos.entry_price) * pos.shares;
    const pnlPct = pos.entry_price > 0 ? (pnl / (pos.entry_price * pos.shares) * 100).toFixed(2) : 0;
    const color  = pnl >= 0 ? '#4ade80' : '#f87171';
    const sign   = pnl >= 0 ? '+' : '';

    document.getElementById('chart-pos-sym').textContent  = sym;
    document.getElementById('chart-pos-qty').textContent  = pos.shares + ' shares';
    document.getElementById('chart-pos-pnl').textContent  = sign + '₹' + Math.abs(pnl).toFixed(2) + ' (' + sign + pnlPct + '%)';
    document.getElementById('chart-pos-pnl').style.color  = color;
    badge.style.display = 'flex';

    chartDrawPositionLines();
  } catch(e) {
    console.error('chartUpdatePosBadge', e);
  }
}

// ── Square-off from chart badge ───────────────────────────────────────────────
async function chartSquareOff() {
  if (!_chartOpenPos) return;
  const sym = _chartOpenPos.symbol;
  const cmp = _chartOpenPos.cmp || _chartOpenPos.entry_price;
  if (!confirm('Square off ' + sym + ' @ ₹' + cmp.toFixed(2) + '?')) return;
  try {
    const res = await api('portfolio_close', { id: _chartOpenPos.id, exit_price: cmp });
    if (res && res.ok) {
      _chartOpenPos = null;
      document.getElementById('chart-pos-badge').style.display = 'none';
      chartDrawPositionLines();   // clears the lines
      alert('Position closed. P&L recorded in Demat Portfolio.');
    } else {
      alert('Close failed: ' + ((res && res.error) || 'unknown error'));
    }
  } catch(e) {
    alert('Error: ' + e.message);
  }
}

// ── Draw Entry / SL / T1 / T2 horizontal lines on the price canvas ───────────
function chartDrawPositionLines() {
  const cvs = document.getElementById('price-canvas');
  if (!cvs || !window._chartPriceData) return;

  // Re-render chart then overlay lines
  const ctx = cvs.getContext('2d');
  const pos = _chartOpenPos;

  // Get price→y mapping from the cached chart render params
  const pr = window._chartPriceData;
  if (!pr || !pr.minP || !pr.maxP) return;

  const H     = cvs.height;
  const W     = cvs.width;
  const pad   = pr.padTop || 30;
  const drawH = H - pad - (pr.padBot || 20);
  const range = pr.maxP - pr.minP;
  const p2y   = price => range > 0 ? pad + drawH * (1 - (price - pr.minP) / range) : H / 2;

  const drawLine = (price, color, label, dash) => {
    if (!price || price <= 0) return;
    const y = p2y(price);
    if (y < 0 || y > H) return;
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth   = 1;
    ctx.globalAlpha = 0.85;
    if (dash) ctx.setLineDash([6, 4]);
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = 1;
    ctx.fillStyle = color;
    ctx.font = '10px Share Tech Mono, monospace';
    ctx.fillText(label + ' ₹' + price.toFixed(2), W - 110, y - 3);
    ctx.restore();
  };

  if (pos) {
    drawLine(pos.entry_price, '#26a269', 'ENTRY', true);
    drawLine(pos.stop_loss,   '#ef4444', 'SL',    true);
    drawLine(pos.target1,     '#f59e0b', 'T1',    true);
    drawLine(pos.target2,     '#f59e0b', 'T2',    true);
  }

  // Draw Options GEX walls if available (Synergy v4.3)
  const gex = window._chartGexProfile;
  if (gex) {
    if (gex.max_gamma_wall) {
      drawLine(gex.max_gamma_wall, '#a855f7', 'MAX GEX CEILING', true);
    }
    if (gex.zero_gamma_level) {
      drawLine(gex.zero_gamma_level, '#3b82f6', 'ZERO GEX FLOOR', true);
    }
  }
}

// ── Auto-refresh badge whenever chart symbol changes ──────────────────────────
(function() {
  const sel = document.getElementById('chart-sym');
  if (sel) sel.addEventListener('change', () => setTimeout(chartUpdatePosBadge, 500));
})();

// Register global redraw hook for position lines
window.tvOnRedraw = function() {
  const activePage = document.querySelector('.page.active');
  if (activePage && activePage.id === 'page-chart') {
    chartDrawPositionLines();
  } else if (window.location.search.indexOf('chartWindow=1') !== -1) {
    if (typeof cwDrawPositionLines === 'function') {
      cwDrawPositionLines();
    }
  }
};

// Close modal on backdrop click
document.addEventListener('click', e => {
  const modal = document.getElementById('chart-order-modal');
  if (modal && e.target === modal) chartCloseModal();
});

"""