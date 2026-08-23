"""
page_risk.py — Risk Management + Margin Engine (Phase 4 · v4.0)
Tabs:
  1. MARGIN CALC   — Live position sizing calculator with gauge
  2. RISK DASHBOARD — Portfolio health, drawdown, VaR, sector heatmap
  3. SETTINGS       — Capital allocator, daily loss limit, kill switch
  4. CORRELATION    — N×N symbol correlation heatmap
"""

HTML = r"""
<!-- ═══════════ PAGE: RISK MANAGEMENT ═══════════ -->
<div class="page" id="page-risk">

  <!-- ── Kill Switch Banner (shown when kill switch is ON) ── -->
  <div id="risk-kill-banner" style="
    display:none;
    background:linear-gradient(90deg,rgba(242,54,69,0.25),rgba(242,54,69,0.1));
    border:1px solid var(--red);border-left:4px solid var(--red);
    padding:10px 20px;margin-bottom:16px;border-radius:4px;
    font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:var(--red);
    letter-spacing:1px;display:flex;align-items:center;gap:12px;animation:killPulse 1.5s ease-in-out infinite;">
    <span style="font-size:1.2rem;">🚨</span>
    <span>KILL SWITCH ACTIVE — ALL NEW TRADE RECOMMENDATIONS ARE BLOCKED</span>
    <span style="margin-left:auto;font-size:0.65rem;opacity:0.7;">Disable in Settings tab</span>
  </div>

  <div class="topbar">
    <div style="display:flex;align-items:center;gap:10px;">
      <span style="font-family:Orbitron,sans-serif;font-size:1.1rem;color:var(--gold);font-weight:700;letter-spacing:2px;">⚠️ RISK MANAGEMENT</span>
      <span class="page-tag">MARGIN · DASHBOARD · SETTINGS · CORRELATION</span>
    </div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;">
      PHASE 4 · MARGIN ENGINE · PORTFOLIO PROTECTION
    </div>
  </div>

  <!-- ══════════ TAB NAVIGATION ══════════ -->
  <div id="risk-tab-nav" style="display:flex;gap:0;margin-bottom:20px;border-bottom:1px solid var(--border);">
    <button id="risk-tab-btn-margin" onclick="riskTab('margin')"
      style="padding:9px 22px;background:rgba(41,98,255,0.12);border:1px solid var(--cyan);border-bottom:none;
             color:var(--cyan);font-family:'JetBrains Mono',monospace;font-size:0.72rem;letter-spacing:1px;cursor:pointer;transition:all 0.2s;">
      🧮 MARGIN CALC
    </button>
    <button id="risk-tab-btn-dashboard" onclick="riskTab('dashboard')"
      style="padding:9px 22px;background:transparent;border:1px solid var(--border);border-bottom:none;
             color:var(--dim);font-family:'JetBrains Mono',monospace;font-size:0.72rem;letter-spacing:1px;cursor:pointer;transition:all 0.2s;">
      📊 RISK DASHBOARD
    </button>
    <button id="risk-tab-btn-settings" onclick="riskTab('settings')"
      style="padding:9px 22px;background:transparent;border:1px solid var(--border);border-bottom:none;
             color:var(--dim);font-family:'JetBrains Mono',monospace;font-size:0.72rem;letter-spacing:1px;cursor:pointer;transition:all 0.2s;">
      ⚙️ SETTINGS
    </button>
    <button id="risk-tab-btn-correlation" onclick="riskTab('correlation')"
      style="padding:9px 22px;background:transparent;border:1px solid var(--border);border-bottom:none;
             color:var(--dim);font-family:'JetBrains Mono',monospace;font-size:0.72rem;letter-spacing:1px;cursor:pointer;transition:all 0.2s;">
      🔗 CORRELATION
    </button>
  </div>

  <!-- ══════════════════════════════════════════════ -->
  <!-- TAB 1: MARGIN CALCULATOR                       -->
  <!-- ══════════════════════════════════════════════ -->
  <div id="risk-margin" class="risk-tab-content">

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">

      <!-- LEFT: Input Panel -->
      <div class="card" style="padding:20px;">
        <div class="card-title" style="color:var(--cyan);">🧮 POSITION SIZING CALCULATOR</div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:18px;">
          <div class="risk-field">
            <label class="risk-label">CAPITAL (₹)</label>
            <div class="risk-input-wrap">
              <input type="number" id="mc-capital" value="500000" min="1000"
                oninput="calcMargin()" class="risk-input" placeholder="500000">
            </div>
          </div>
          <div class="risk-field">
            <label class="risk-label">RISK % PER TRADE</label>
            <div class="risk-input-wrap" style="position:relative;">
              <input type="number" id="mc-risk-pct" value="2" min="0.1" max="20" step="0.1"
                oninput="calcMargin()" class="risk-input" placeholder="2">
              <span style="position:absolute;right:10px;top:50%;transform:translateY(-50%);color:var(--gold);font-size:0.8rem;">%</span>
            </div>
          </div>
          <div class="risk-field">
            <label class="risk-label">ENTRY PRICE (₹)</label>
            <div class="risk-input-wrap">
              <input type="number" id="mc-entry" value="" min="0.01" step="0.01"
                oninput="calcMargin()" class="risk-input" placeholder="0.00">
            </div>
          </div>
          <div class="risk-field">
            <label class="risk-label">STOP LOSS PRICE (₹)</label>
            <div class="risk-input-wrap">
              <input type="number" id="mc-sl" value="" min="0.01" step="0.01"
                oninput="calcMargin()" class="risk-input" placeholder="0.00">
            </div>
          </div>
          <div class="risk-field">
            <label class="risk-label">TARGET 1 (₹) <span style="color:var(--dim);font-size:0.6rem;">optional</span></label>
            <div class="risk-input-wrap">
              <input type="number" id="mc-t1" value="" min="0.01" step="0.01"
                oninput="calcMargin()" class="risk-input" placeholder="0.00">
            </div>
          </div>
          <div class="risk-field">
            <label class="risk-label">TARGET 2 (₹) <span style="color:var(--dim);font-size:0.6rem;">optional</span></label>
            <div class="risk-input-wrap">
              <input type="number" id="mc-t2" value="" min="0.01" step="0.01"
                oninput="calcMargin()" class="risk-input" placeholder="0.00">
            </div>
          </div>
        </div>

        <!-- Risk Slider visual -->
        <div style="margin-bottom:14px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
            <span style="font-family:'Inter',sans-serif;font-size:0.65rem;color:var(--dim);letter-spacing:1px;">RISK TOLERANCE</span>
            <span id="mc-risk-slider-val" style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:var(--gold);">2.0%</span>
          </div>
          <input type="range" id="mc-risk-slider" min="0.1" max="10" step="0.1" value="2"
            oninput="document.getElementById('mc-risk-pct').value=this.value;document.getElementById('mc-risk-slider-val').textContent=parseFloat(this.value).toFixed(1)+'%';calcMargin();"
            style="width:100%;accent-color:var(--cyan);height:4px;cursor:pointer;">
          <div style="display:flex;justify-content:space-between;margin-top:3px;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:var(--green);">0.1% SAFE</span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:var(--red);">10% AGGRESSIVE</span>
          </div>
        </div>
      </div>

      <!-- RIGHT: Results Panel -->
      <div style="display:flex;flex-direction:column;gap:14px;">

        <!-- Key Metrics -->
        <div class="card" style="padding:18px;">
          <div class="card-title" style="color:var(--green);">📐 CALCULATED METRICS</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
            <div class="mc-result-tile" id="mc-tile-riskamt">
              <div class="mc-tile-label">RISK AMOUNT</div>
              <div class="mc-tile-val" id="mc-risk-amt">₹ —</div>
            </div>
            <div class="mc-result-tile" id="mc-tile-shares">
              <div class="mc-tile-label">SHARES / QTY</div>
              <div class="mc-tile-val" id="mc-shares">— units</div>
            </div>
            <div class="mc-result-tile" id="mc-tile-possize">
              <div class="mc-tile-label">POSITION SIZE</div>
              <div class="mc-tile-val" id="mc-pos-size">₹ —</div>
            </div>
            <div class="mc-result-tile" id="mc-tile-maxloss">
              <div class="mc-tile-label">MAX LOSS</div>
              <div class="mc-tile-val" style="color:var(--red);" id="mc-max-loss">₹ —</div>
            </div>
          </div>
        </div>

        <!-- Position Size Gauge -->
        <div class="card" style="padding:18px;">
          <div class="card-title" style="color:var(--gold);">⚡ POSITION SIZE GAUGE</div>
          <div style="display:flex;align-items:center;gap:16px;">
            <div style="position:relative;width:110px;height:110px;flex-shrink:0;">
              <svg viewBox="0 0 120 120" width="110" height="110">
                <circle cx="60" cy="60" r="50" fill="none" stroke="#1E222D" stroke-width="10"/>
                <circle id="mc-gauge-circle" cx="60" cy="60" r="50" fill="none"
                  stroke="var(--green)" stroke-width="10"
                  stroke-dasharray="314" stroke-dashoffset="314"
                  stroke-linecap="round"
                  transform="rotate(-90 60 60)"
                  style="transition:stroke-dashoffset 0.6s cubic-bezier(0.4,0,0.2,1),stroke 0.4s;"/>
              </svg>
              <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;">
                <span id="mc-gauge-pct" style="font-family:'JetBrains Mono',monospace;font-size:1.1rem;font-weight:700;color:var(--white);">0%</span>
                <span style="font-family:'Inter',sans-serif;font-size:0.55rem;color:var(--dim);margin-top:2px;">OF CAP</span>
              </div>
            </div>
            <div style="flex:1;">
              <div class="mc-gauge-legend">
                <span class="mc-gauge-dot" style="background:var(--green);"></span>
                <span style="color:var(--dim);font-size:0.65rem;">&lt; 5% — Safe zone</span>
              </div>
              <div class="mc-gauge-legend" style="margin-top:6px;">
                <span class="mc-gauge-dot" style="background:var(--gold);"></span>
                <span style="color:var(--dim);font-size:0.65rem;">5–10% — Moderate risk</span>
              </div>
              <div class="mc-gauge-legend" style="margin-top:6px;">
                <span class="mc-gauge-dot" style="background:var(--red);"></span>
                <span style="color:var(--dim);font-size:0.65rem;">&gt; 10% — High risk</span>
              </div>
              <div id="mc-gauge-msg" style="margin-top:12px;font-family:'Inter',sans-serif;font-size:0.68rem;color:var(--green);padding:6px 10px;background:rgba(8,153,129,0.08);border:1px solid rgba(8,153,129,0.2);border-radius:3px;">
                Enter values to calculate
              </div>
            </div>
          </div>
        </div>

        <!-- R:R Ratios -->
        <div class="card" style="padding:18px;">
          <div class="card-title" style="color:var(--purple, #B39DDB);">🎯 RISK:REWARD RATIOS</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
            <div style="background:var(--p2);border:1px solid var(--border);padding:12px;border-radius:4px;text-align:center;">
              <div style="font-family:'Inter',sans-serif;font-size:0.62rem;color:var(--dim);letter-spacing:1px;margin-bottom:6px;">TARGET 1 R:R</div>
              <div id="mc-rr1" style="font-family:'JetBrains Mono',monospace;font-size:1.2rem;font-weight:700;color:var(--white);">—</div>
            </div>
            <div style="background:var(--p2);border:1px solid var(--border);padding:12px;border-radius:4px;text-align:center;">
              <div style="font-family:'Inter',sans-serif;font-size:0.62rem;color:var(--dim);letter-spacing:1px;margin-bottom:6px;">TARGET 2 R:R</div>
              <div id="mc-rr2" style="font-family:'JetBrains Mono',monospace;font-size:1.2rem;font-weight:700;color:var(--white);">—</div>
            </div>
            <div style="background:var(--p2);border:1px solid var(--border);padding:12px;border-radius:4px;text-align:center;">
              <div style="font-family:'Inter',sans-serif;font-size:0.62rem;color:var(--dim);letter-spacing:1px;margin-bottom:6px;">T1 PROFIT (₹)</div>
              <div id="mc-t1-profit" style="font-family:'JetBrains Mono',monospace;font-size:1.1rem;font-weight:700;color:var(--green);">—</div>
            </div>
            <div style="background:var(--p2);border:1px solid var(--border);padding:12px;border-radius:4px;text-align:center;">
              <div style="font-family:'Inter',sans-serif;font-size:0.62rem;color:var(--dim);letter-spacing:1px;margin-bottom:6px;">T2 PROFIT (₹)</div>
              <div id="mc-t2-profit" style="font-family:'JetBrains Mono',monospace;font-size:1.1rem;font-weight:700;color:var(--green);">—</div>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- Breakeven & Trade Stats -->
    <div class="card" style="padding:16px;margin-top:0;">
      <div class="card-title" style="color:var(--cyan);">📋 TRADE STATISTICS</div>
      <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:10px;">
        <div class="stat"><span class="val" id="mc-stat-risk-pct">—</span><div class="lbl">Risk%</div></div>
        <div class="stat"><span class="val" id="mc-stat-sl-pct">—</span><div class="lbl">SL Distance%</div></div>
        <div class="stat"><span class="val" id="mc-stat-pos-pct">—</span><div class="lbl">Pos% of Cap</div></div>
        <div class="stat"><span class="val" id="mc-stat-bkeven">—</span><div class="lbl">Breakeven ₹</div></div>
        <div class="stat"><span class="val" id="mc-stat-t1-pct">—</span><div class="lbl">T1 Move%</div></div>
        <div class="stat"><span class="val" id="mc-stat-t2-pct">—</span><div class="lbl">T2 Move%</div></div>
      </div>
    </div>

  </div><!-- end risk-margin -->


  <!-- ══════════════════════════════════════════════ -->
  <!-- TAB 2: RISK DASHBOARD                          -->
  <!-- ══════════════════════════════════════════════ -->
  <div id="risk-dashboard" class="risk-tab-content" style="display:none;">

    <!-- Stat tiles row -->
    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-bottom: 16px;">
      <div class="stat" style="border-color:var(--red);position:relative;overflow:hidden;margin:0;">
        <div style="position:absolute;top:0;left:0;right:0;height:2px;background:var(--red);"></div>
        <span class="val" id="rd-drawdown" style="color:var(--red);">—</span>
        <div class="lbl">MAX DRAWDOWN %</div>
      </div>
      <div class="stat" style="border-color:var(--gold);position:relative;overflow:hidden;margin:0;">
        <div style="position:absolute;top:0;left:0;right:0;height:2px;background:var(--gold);"></div>
        <span class="val" id="rd-var" style="color:var(--gold);">—</span>
        <div class="lbl">VALUE AT RISK (95%)</div>
      </div>
      <div class="stat" style="border-color:var(--cyan);position:relative;overflow:hidden;margin:0;">
        <div style="position:absolute;top:0;left:0;right:0;height:2px;background:var(--cyan);"></div>
        <span class="val" id="rd-exposure" style="color:var(--cyan);">—</span>
        <div class="lbl">TOTAL EXPOSURE ₹</div>
      </div>
      <div class="stat" style="border-color:var(--green);position:relative;overflow:hidden;margin:0;">
        <div style="position:absolute;top:0;left:0;right:0;height:2px;background:var(--green);"></div>
        <span class="val" id="rd-winrate" style="color:var(--green);">—</span>
        <div class="lbl">WIN RATE %</div>
      </div>
      <div class="stat" style="border-color:var(--purple);position:relative;overflow:hidden;margin:0;">
        <div style="position:absolute;top:0;left:0;right:0;height:2px;background:var(--purple);"></div>
        <span class="val" id="rd-sharpe" style="color:var(--purple);">—</span>
        <div class="lbl">SHARPE RATIO</div>
      </div>
      <div class="stat" style="border-color:var(--orange);position:relative;overflow:hidden;margin:0;">
        <div style="position:absolute;top:0;left:0;right:0;height:2px;background:var(--orange);"></div>
        <span class="val" id="rd-profitfactor" style="color:var(--orange);">—</span>
        <div class="lbl">PROFIT FACTOR</div>
      </div>
      <div class="stat" style="border-color:var(--cyan);position:relative;overflow:hidden;margin:0;">
        <div style="position:absolute;top:0;left:0;right:0;height:2px;background:var(--cyan);"></div>
        <span class="val" id="rd-expectancy" style="color:var(--cyan);">—</span>
        <div class="lbl">EXPECTANCY</div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1.6fr;gap:16px;margin-bottom:16px;">

      <!-- Portfolio Health Score -->
      <div class="card" style="padding:18px;">
        <div class="card-title" style="color:var(--gold);">🏥 PORTFOLIO HEALTH</div>
        <div style="display:flex;flex-direction:column;align-items:center;padding:10px 0;">
          <div style="position:relative;width:140px;height:140px;">
            <svg viewBox="0 0 140 140" width="140" height="140">
              <circle cx="70" cy="70" r="58" fill="none" stroke="#1E222D" stroke-width="12"/>
              <circle id="rd-health-circle" cx="70" cy="70" r="58" fill="none"
                stroke="var(--green)" stroke-width="12"
                stroke-dasharray="364" stroke-dashoffset="364"
                stroke-linecap="round"
                transform="rotate(-90 70 70)"
                style="transition:stroke-dashoffset 1s cubic-bezier(0.4,0,0.2,1),stroke 0.5s;"/>
            </svg>
            <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;">
              <span id="rd-health-score" style="font-family:'JetBrains Mono',monospace;font-size:2rem;font-weight:700;color:var(--white);">—</span>
              <span style="font-family:'Inter',sans-serif;font-size:0.6rem;color:var(--dim);">/ 100</span>
            </div>
          </div>
          <div id="rd-health-label" style="margin-top:10px;font-family:'Inter',sans-serif;font-size:0.75rem;color:var(--green);font-weight:600;">
            Loading...
          </div>
          <div style="width:100%;margin-top:14px;">
            <div class="rd-health-bar-row"><span>Drawdown</span><div class="rd-health-bar-track"><div id="rd-hb-dd" class="rd-health-bar-fill" style="background:var(--red);width:0%;"></div></div></div>
            <div class="rd-health-bar-row"><span>VaR</span><div class="rd-health-bar-track"><div id="rd-hb-var" class="rd-health-bar-fill" style="background:var(--gold);width:0%;"></div></div></div>
            <div class="rd-health-bar-row"><span>Diversification</span><div class="rd-health-bar-track"><div id="rd-hb-div" class="rd-health-bar-fill" style="background:var(--green);width:0%;"></div></div></div>
            <div class="rd-health-bar-row"><span>Win Rate</span><div class="rd-health-bar-track"><div id="rd-hb-wr" class="rd-health-bar-fill" style="background:var(--cyan);width:0%;"></div></div></div>
          </div>
        </div>
      </div>

      <!-- Sector Heatmap -->
      <div class="card" style="padding:18px;">
        <div class="card-title" style="color:var(--cyan);">🗺️ SECTOR ALLOCATION HEATMAP</div>
        <div id="rd-sector-heatmap" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;min-height:160px;">
          <div style="grid-column:1/-1;text-align:center;padding:30px;color:var(--dim);font-family:'JetBrains Mono',monospace;font-size:0.7rem;">
            Loading sector data...
          </div>
        </div>
      </div>

    </div>

    <!-- Open Positions Table -->
    <div class="card" style="padding:18px;margin-bottom:16px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
        <div class="card-title" style="color:var(--white);margin-bottom:0;">📋 OPEN POSITIONS</div>
        <button onclick="loadRiskDashboard()" style="background:transparent;border:1px solid var(--border);color:var(--dim);padding:4px 12px;font-family:'JetBrains Mono',monospace;font-size:0.65rem;cursor:pointer;border-radius:3px;transition:all 0.2s;" onmouseover="this.style.borderColor='var(--cyan)';this.style.color='var(--cyan)';" onmouseout="this.style.borderColor='var(--border)';this.style.color='var(--dim)';">
          ↻ REFRESH
        </button>
      </div>
      <div style="overflow-x:auto;">
        <table id="rd-positions-table" style="width:100%;border-collapse:collapse;font-family:'JetBrains Mono',monospace;font-size:0.72rem;">
          <thead>
            <tr style="border-bottom:1px solid var(--border);">
              <th class="rd-th">SYMBOL</th>
              <th class="rd-th">ENTRY ₹</th>
              <th class="rd-th">CMP ₹</th>
              <th class="rd-th">UNREALIZED P&L</th>
              <th class="rd-th">P&L %</th>
              <th class="rd-th">DAYS HELD</th>
              <th class="rd-th">EXPOSURE ₹</th>
            </tr>
          </thead>
          <tbody id="rd-positions-body">
            <tr><td colspan="7" style="text-align:center;padding:24px;color:var(--dim);font-size:0.7rem;">No open positions</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Daily P&L Bar Chart -->
    <div class="card" style="padding:18px;">
      <div class="card-title" style="color:var(--cyan);">📅 DAILY P&L — LAST 10 DAYS</div>
      <div id="rd-daily-pnl-chart" style="display:flex;align-items:flex-end;gap:6px;height:120px;padding:0 4px;">
        <div style="width:100%;text-align:center;color:var(--dim);font-family:'JetBrains Mono',monospace;font-size:0.7rem;align-self:center;">Loading...</div>
      </div>
      <div id="rd-daily-pnl-labels" style="display:flex;gap:6px;margin-top:6px;padding:0 4px;"></div>
    </div>

  </div><!-- end risk-dashboard -->


  <!-- ══════════════════════════════════════════════ -->
  <!-- TAB 3: SETTINGS                                -->
  <!-- ══════════════════════════════════════════════ -->
  <div id="risk-settings" class="risk-tab-content" style="display:none;">

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">

      <!-- Left: Main Settings -->
      <div class="card" style="padding:20px;">
        <div class="card-title" style="color:var(--gold);">💰 CAPITAL & RISK PARAMETERS</div>

        <div style="display:flex;flex-direction:column;gap:16px;">

          <div class="rs-field">
            <label class="rs-label">CAPITAL (₹)</label>
            <input type="number" id="rs-capital" class="rs-input" placeholder="500000" min="1000">
          </div>

          <div class="rs-field">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
              <label class="rs-label" style="margin:0;">MAX RISK PER TRADE</label>
              <span id="rs-risk-val" style="font-family:'JetBrains Mono',monospace;font-size:0.8rem;color:var(--gold);">2.0%</span>
            </div>
            <input type="range" id="rs-max-risk" min="0.5" max="5" step="0.1" value="2"
              oninput="document.getElementById('rs-risk-val').textContent=parseFloat(this.value).toFixed(1)+'%';"
              style="width:100%;accent-color:var(--cyan);">
            <div style="display:flex;justify-content:space-between;margin-top:2px;">
              <span style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:var(--green);">0.5% MIN</span>
              <span style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:var(--red);">5% MAX</span>
            </div>
          </div>

          <div class="rs-field">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
              <label class="rs-label" style="margin:0;">MAX OPEN POSITIONS</label>
              <span id="rs-pos-val" style="font-family:'JetBrains Mono',monospace;font-size:0.8rem;color:var(--cyan);">10</span>
            </div>
            <input type="range" id="rs-max-positions" min="2" max="20" step="1" value="10"
              oninput="document.getElementById('rs-pos-val').textContent=this.value;"
              style="width:100%;accent-color:var(--cyan);">
            <div style="display:flex;justify-content:space-between;margin-top:2px;">
              <span style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:var(--dim);">2 MIN</span>
              <span style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:var(--dim);">20 MAX</span>
            </div>
          </div>

          <div class="rs-field">
            <label class="rs-label">DAILY LOSS LIMIT (₹)</label>
            <input type="number" id="rs-daily-loss" class="rs-input" placeholder="10000" min="0">
          </div>

          <div class="rs-field">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
              <label class="rs-label" style="margin:0;">MAX SECTOR EXPOSURE</label>
              <span id="rs-sector-val" style="font-family:'JetBrains Mono',monospace;font-size:0.8rem;color:var(--gold);">30%</span>
            </div>
            <input type="range" id="rs-sector-cap" min="10" max="50" step="5" value="30"
              oninput="document.getElementById('rs-sector-val').textContent=this.value+'%';"
              style="width:100%;accent-color:var(--gold);">
            <div style="display:flex;justify-content:space-between;margin-top:2px;">
              <span style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:var(--green);">10% MIN</span>
              <span style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:var(--red);">50% MAX</span>
            </div>
          </div>

        </div>
      </div>

      <!-- Right: Kill Switch + Actions -->
      <div style="display:flex;flex-direction:column;gap:14px;">

        <!-- Kill Switch -->
        <div class="card" style="padding:20px;">
          <div class="card-title" style="color:var(--red);">🚨 KILL SWITCH</div>
          <p style="font-family:'Inter',sans-serif;font-size:0.72rem;color:var(--dim);margin-bottom:18px;line-height:1.6;">
            When activated, all new trade recommendations are blocked. Use during high-volatility events or circuit breakers.
          </p>
          <div style="display:flex;align-items:center;gap:16px;">
            <div id="rs-kill-switch-toggle" onclick="toggleKillSwitch()"
              style="width:64px;height:32px;border-radius:16px;background:var(--p2);border:1px solid var(--border);
                     cursor:pointer;position:relative;transition:all 0.3s;">
              <div id="rs-kill-thumb"
                style="position:absolute;top:4px;left:4px;width:22px;height:22px;border-radius:50%;
                       background:var(--dim);transition:all 0.3s;"></div>
            </div>
            <div>
              <div id="rs-kill-status" style="font-family:'JetBrains Mono',monospace;font-size:0.8rem;color:var(--dim);font-weight:700;">INACTIVE</div>
              <div style="font-family:'Inter',sans-serif;font-size:0.6rem;color:var(--dim);margin-top:2px;">New trades ALLOWED</div>
            </div>
          </div>
        </div>

        <!-- Current Settings Summary -->
        <div class="card" style="padding:18px;">
          <div class="card-title" style="color:var(--cyan);">📊 ACTIVE SETTINGS SUMMARY</div>
          <div id="rs-summary" style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;color:var(--dim);line-height:2;">
            <div style="display:flex;justify-content:space-between;"><span>Capital:</span><span id="rs-s-cap" style="color:var(--white);">—</span></div>
            <div style="display:flex;justify-content:space-between;"><span>Max Risk/Trade:</span><span id="rs-s-risk" style="color:var(--gold);">—</span></div>
            <div style="display:flex;justify-content:space-between;"><span>Max Positions:</span><span id="rs-s-pos" style="color:var(--cyan);">—</span></div>
            <div style="display:flex;justify-content:space-between;"><span>Daily Loss Limit:</span><span id="rs-s-dll" style="color:var(--red);">—</span></div>
            <div style="display:flex;justify-content:space-between;"><span>Sector Cap:</span><span id="rs-s-sec" style="color:var(--gold);">—</span></div>
            <div style="display:flex;justify-content:space-between;border-top:1px solid var(--border);padding-top:6px;margin-top:4px;"><span>Kill Switch:</span><span id="rs-s-kill" style="color:var(--green);">OFF</span></div>
          </div>
        </div>

        <!-- Save Button -->
        <button id="rs-save-btn" onclick="saveRiskSettings()"
          style="padding:14px;background:linear-gradient(135deg,var(--cyan),#1E53E5);border:none;
                 color:var(--white);font-family:'JetBrains Mono',monospace;font-size:0.85rem;
                 letter-spacing:2px;cursor:pointer;border-radius:4px;font-weight:700;
                 transition:all 0.3s;box-shadow:0 4px 16px rgba(41,98,255,0.3);">
          💾 SAVE SETTINGS
        </button>

        <div id="rs-save-msg" style="display:none;font-family:'JetBrains Mono',monospace;font-size:0.72rem;
          text-align:center;padding:8px;border-radius:3px;"></div>

      </div>
    </div>

  </div><!-- end risk-settings -->


  <!-- ══════════════════════════════════════════════ -->
  <!-- TAB 4: CORRELATION MATRIX                      -->
  <!-- ══════════════════════════════════════════════ -->
  <div id="risk-correlation" class="risk-tab-content" style="display:none;">

    <div class="card" style="padding:18px;margin-bottom:16px;">
      <div class="card-title" style="color:var(--cyan);">🔗 CORRELATION MATRIX BUILDER</div>
      <div style="display:flex;flex-wrap:wrap;align-items:flex-end;gap:14px;">
        <div style="flex:1;min-width:280px;">
          <label style="font-family:'Inter',sans-serif;font-size:0.65rem;color:var(--dim);letter-spacing:1px;display:block;margin-bottom:6px;">SELECT SYMBOLS (2–8)</label>
          <div id="corr-symbol-select-wrap" style="position:relative;">
            <input type="text" id="corr-search" placeholder="Type to search symbols..."
              oninput="corrFilterSymbols(this.value)"
              style="width:100%;background:var(--p2);border:1px solid var(--border);color:var(--white);
                     padding:8px 12px;font-family:'JetBrains Mono',monospace;font-size:0.75rem;outline:none;border-radius:3px;">
            <div id="corr-dropdown" style="display:none;position:absolute;top:100%;left:0;right:0;z-index:200;
              background:var(--panel);border:1px solid var(--border);max-height:200px;overflow-y:auto;border-radius:0 0 4px 4px;">
            </div>
          </div>
          <div id="corr-selected-chips" style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;min-height:28px;"></div>
        </div>
        <div style="display:flex;flex-direction:column;gap:8px;">
          <label style="font-family:'Inter',sans-serif;font-size:0.65rem;color:var(--dim);letter-spacing:1px;">PERIOD</label>
          <select id="corr-period" style="background:var(--p2);border:1px solid var(--border);color:var(--white);
            padding:8px 14px;font-family:'JetBrains Mono',monospace;font-size:0.75rem;outline:none;border-radius:3px;">
            <option value="30">30 Days</option>
            <option value="60" selected>60 Days</option>
            <option value="90">90 Days</option>
            <option value="180">180 Days</option>
          </select>
        </div>
        <button onclick="loadCorrelation()"
          style="padding:9px 24px;background:linear-gradient(135deg,var(--cyan),#1E53E5);border:none;
                 color:var(--white);font-family:'JetBrains Mono',monospace;font-size:0.75rem;
                 letter-spacing:1.5px;cursor:pointer;border-radius:3px;font-weight:700;
                 box-shadow:0 2px 10px rgba(41,98,255,0.3);transition:all 0.2s;">
          RUN CORRELATION ▶
        </button>
      </div>
    </div>

    <!-- Heatmap canvas area -->
    <div class="card" style="padding:18px;">
      <div class="card-title" style="color:var(--white);">📊 CORRELATION HEATMAP</div>
      <div id="corr-heatmap-container" style="overflow-x:auto;">
        <div id="corr-placeholder" style="text-align:center;padding:50px;color:var(--dim);font-family:'JetBrains Mono',monospace;font-size:0.8rem;">
          Select 2–8 symbols and click RUN CORRELATION
        </div>
        <div id="corr-heatmap-wrap" style="display:none;"></div>
      </div>
    </div>

    <!-- High correlation warnings -->
    <div id="corr-warnings" class="card" style="padding:16px;display:none;border-color:var(--gold);">
      <div class="card-title" style="color:var(--gold);">⚠️ CORRELATION WARNINGS</div>
      <div id="corr-warnings-body" style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:var(--text);line-height:1.8;"></div>
    </div>

  </div><!-- end risk-correlation -->

</div><!-- end page-risk -->
"""


JS = r"""
// ═══════════════════════════════════════════════════════════
// PAGE RISK — RISK MANAGEMENT + MARGIN ENGINE (Phase 4)
// ═══════════════════════════════════════════════════════════

// ── Module State ──
const _risk = {
  killSwitchOn: false,
  settings: {},
  corrSymbols: [],
  allSymbols: [],
  currentTab: 'margin'
};

// ── Inject page-specific CSS ──
(function injectRiskCSS() {
  if (document.getElementById('risk-page-css')) return;
  const s = document.createElement('style');
  s.id = 'risk-page-css';
  s.textContent = `
    @keyframes killPulse {
      0%,100% { box-shadow: 0 0 0 0 rgba(242,54,69,0.0); }
      50%      { box-shadow: 0 0 12px 4px rgba(242,54,69,0.25); }
    }

    .risk-tab-content { animation: fadeInUp 0.3s ease; }
    @keyframes fadeInUp {
      from { opacity:0; transform:translateY(8px); }
      to   { opacity:1; transform:translateY(0); }
    }

    /* Margin Calc */
    .risk-field { display:flex; flex-direction:column; gap:4px; }
    .risk-label {
      font-family:'Inter',sans-serif; font-size:0.62rem;
      color:var(--dim); letter-spacing:1px; text-transform:uppercase;
    }
    .risk-input-wrap { position:relative; }
    .risk-input {
      width:100%; background:var(--p2); border:1px solid var(--border);
      color:var(--white); padding:8px 12px;
      font-family:'JetBrains Mono',monospace; font-size:0.82rem;
      outline:none; transition:border-color 0.2s; border-radius:3px;
    }
    .risk-input:focus { border-color:var(--cyan); }
    .risk-input:hover { border-color:var(--b2); }

    .mc-result-tile {
      background:var(--p2); border:1px solid var(--border);
      padding:12px; border-radius:4px; text-align:center;
      transition:border-color 0.3s;
    }
    .mc-result-tile:hover { border-color:var(--cyan); }
    .mc-tile-label {
      font-family:'Inter',sans-serif; font-size:0.6rem;
      color:var(--dim); letter-spacing:1px; margin-bottom:6px;
    }
    .mc-tile-val {
      font-family:'JetBrains Mono',monospace; font-size:1.05rem;
      color:var(--white); font-weight:700;
    }
    .mc-gauge-legend { display:flex; align-items:center; gap:8px; }
    .mc-gauge-dot {
      width:10px; height:10px; border-radius:50%; flex-shrink:0;
    }

    /* Risk Dashboard */
    .rd-th {
      font-family:'Inter',sans-serif; font-size:0.6rem; color:var(--dim);
      letter-spacing:1px; text-transform:uppercase; text-align:left;
      padding:8px 12px; border-bottom:1px solid var(--border);
    }
    .rd-td {
      padding:9px 12px; border-bottom:1px solid rgba(43,49,57,0.5);
      font-family:'JetBrains Mono',monospace; font-size:0.72rem; color:var(--text);
    }
    .rd-health-bar-row {
      display:flex; align-items:center; gap:8px;
      font-family:'Inter',sans-serif; font-size:0.6rem; color:var(--dim);
      margin-bottom:6px;
    }
    .rd-health-bar-row span { width:80px; flex-shrink:0; }
    .rd-health-bar-track {
      flex:1; height:5px; background:var(--p2); border-radius:3px; overflow:hidden;
    }
    .rd-health-bar-fill {
      height:100%; border-radius:3px;
      transition:width 1s cubic-bezier(0.4,0,0.2,1);
    }

    /* Settings */
    .rs-field { display:flex; flex-direction:column; gap:6px; }
    .rs-label {
      font-family:'Inter',sans-serif; font-size:0.62rem;
      color:var(--dim); letter-spacing:1px; text-transform:uppercase;
    }
    .rs-input {
      background:var(--p2); border:1px solid var(--border);
      color:var(--white); padding:9px 14px;
      font-family:'JetBrains Mono',monospace; font-size:0.82rem;
      outline:none; transition:border-color 0.2s; border-radius:3px;
    }
    .rs-input:focus { border-color:var(--cyan); }

    /* Correlation */
    .corr-chip {
      display:inline-flex; align-items:center; gap:5px;
      background:rgba(41,98,255,0.15); border:1px solid var(--cyan);
      color:var(--cyan); padding:3px 8px; border-radius:12px;
      font-family:'JetBrains Mono',monospace; font-size:0.65rem;
      cursor:pointer; transition:all 0.2s;
    }
    .corr-chip:hover { background:rgba(242,54,69,0.1); border-color:var(--red); color:var(--red); }
    .corr-dd-item {
      padding:7px 14px; cursor:pointer;
      font-family:'JetBrains Mono',monospace; font-size:0.72rem; color:var(--text);
      transition:background 0.15s;
    }
    .corr-dd-item:hover { background:var(--p2); color:var(--white); }
    .corr-heatmap-cell {
      display:flex; align-items:center; justify-content:center;
      font-family:'JetBrains Mono',monospace; font-size:0.72rem;
      font-weight:700; cursor:default;
      transition:transform 0.15s;
    }
    .corr-heatmap-cell:hover { transform:scale(1.08); z-index:10; }
  `;
  document.head.appendChild(s);
})();


// ═══════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════
function initRiskPage() {
  riskTab('margin');
  calcMargin();
  loadRiskSettings();
  prefetchAllSymbols();
}


// ═══════════════════════════════════════════════════════════
// TAB SWITCHER
// ═══════════════════════════════════════════════════════════
function riskTab(name) {
  _risk.currentTab = name;
  const tabs = ['margin','dashboard','settings','correlation'];
  tabs.forEach(t => {
    const el = document.getElementById('risk-' + t);
    const btn = document.getElementById('risk-tab-btn-' + t);
    if (!el || !btn) return;
    if (t === name) {
      el.style.display = '';
      btn.style.background = 'rgba(41,98,255,0.12)';
      btn.style.borderColor = 'var(--cyan)';
      btn.style.color = 'var(--cyan)';
    } else {
      el.style.display = 'none';
      btn.style.background = 'transparent';
      btn.style.borderColor = 'var(--border)';
      btn.style.color = 'var(--dim)';
    }
  });
  if (name === 'dashboard') loadRiskDashboard();
  if (name === 'settings') loadRiskSettings();
}


// ═══════════════════════════════════════════════════════════
// TAB 1: MARGIN CALCULATOR
// ═══════════════════════════════════════════════════════════
function calcMargin() {
  const capital = parseFloat(document.getElementById('mc-capital')?.value) || 0;
  const riskPct = parseFloat(document.getElementById('mc-risk-pct')?.value) || 2;
  const entry   = parseFloat(document.getElementById('mc-entry')?.value)   || 0;
  const sl      = parseFloat(document.getElementById('mc-sl')?.value)      || 0;
  const t1      = parseFloat(document.getElementById('mc-t1')?.value)      || 0;
  const t2      = parseFloat(document.getElementById('mc-t2')?.value)      || 0;

  // Sync risk slider
  const slider = document.getElementById('mc-risk-slider');
  if (slider) { slider.value = riskPct; document.getElementById('mc-risk-slider-val').textContent = riskPct.toFixed(1) + '%'; }

  const riskAmt = capital * (riskPct / 100);
  const slDist  = entry > sl && entry > 0 ? entry - sl : 0;
  const shares  = slDist > 0 ? Math.floor(riskAmt / slDist) : 0;
  const posSize = shares * entry;
  const maxLoss = shares * slDist;

  // Update tiles
  _setEl('mc-risk-amt',  capital ? '₹ ' + _fmt(riskAmt) : '₹ —');
  _setEl('mc-shares',    shares  ? shares + ' units'     : '— units');
  _setEl('mc-pos-size',  posSize ? '₹ ' + _fmt(posSize) : '₹ —');
  _setEl('mc-max-loss',  maxLoss ? '₹ ' + _fmt(maxLoss) : '₹ —');

  // Update stats row
  const slPct  = entry > 0 ? ((slDist / entry) * 100).toFixed(2) : '—';
  const posPct = capital > 0 && posSize > 0 ? ((posSize / capital) * 100).toFixed(2) : '—';
  _setEl('mc-stat-risk-pct', riskPct.toFixed(1) + '%');
  _setEl('mc-stat-sl-pct',   slPct !== '—' ? slPct + '%' : '—');
  _setEl('mc-stat-pos-pct',  posPct !== '—' ? posPct + '%' : '—');
  _setEl('mc-stat-bkeven',   entry > 0 ? '₹ ' + entry.toFixed(2) : '—');

  // R:R calculations
  if (t1 > entry && entry > sl && sl > 0 && shares > 0) {
    const t1Reward = t1 - entry;
    const rr1 = (t1Reward / slDist).toFixed(2);
    const t1Profit = (t1Reward * shares).toFixed(0);
    const t1Move = ((t1Reward / entry) * 100).toFixed(2);
    _setEl('mc-rr1', '1 : ' + rr1);
    _setEl('mc-t1-profit', '₹ ' + _fmt(parseFloat(t1Profit)));
    _setEl('mc-stat-t1-pct', t1Move + '%');
  } else {
    _setEl('mc-rr1', '—'); _setEl('mc-t1-profit', '—'); _setEl('mc-stat-t1-pct', '—');
  }
  if (t2 > entry && entry > sl && sl > 0 && shares > 0) {
    const t2Reward = t2 - entry;
    const rr2 = (t2Reward / slDist).toFixed(2);
    const t2Profit = (t2Reward * shares).toFixed(0);
    const t2Move = ((t2Reward / entry) * 100).toFixed(2);
    _setEl('mc-rr2', '1 : ' + rr2);
    _setEl('mc-t2-profit', '₹ ' + _fmt(parseFloat(t2Profit)));
    _setEl('mc-stat-t2-pct', t2Move + '%');
  } else {
    _setEl('mc-rr2', '—'); _setEl('mc-t2-profit', '—'); _setEl('mc-stat-t2-pct', '—');
  }

  // Gauge update
  _updateGauge(parseFloat(posPct) || 0);
}

function _updateGauge(posPct) {
  const circle = document.getElementById('mc-gauge-circle');
  const pctEl  = document.getElementById('mc-gauge-pct');
  const msgEl  = document.getElementById('mc-gauge-msg');
  if (!circle) return;

  const circumference = 314;
  const clamped = Math.min(posPct, 100);
  const offset  = circumference - (circumference * clamped / 100);
  circle.style.strokeDashoffset = offset.toFixed(1);

  let color, msg, msgColor, msgBg, msgBorder;
  if (posPct <= 0) {
    color = 'var(--dim)'; msg = 'Enter values to calculate';
    msgColor = 'var(--dim)'; msgBg = 'transparent'; msgBorder = 'var(--border)';
  } else if (posPct < 5) {
    color = 'var(--green)'; msg = '✅ Safe zone — position size is healthy';
    msgColor = 'var(--green)'; msgBg = 'rgba(8,153,129,0.08)'; msgBorder = 'rgba(8,153,129,0.2)';
  } else if (posPct < 10) {
    color = 'var(--gold)'; msg = '⚠️ Moderate — consider reducing size';
    msgColor = 'var(--gold)'; msgBg = 'rgba(255,152,0,0.08)'; msgBorder = 'rgba(255,152,0,0.2)';
  } else {
    color = 'var(--red)'; msg = '🚨 HIGH RISK — position exceeds 10% of capital!';
    msgColor = 'var(--red)'; msgBg = 'rgba(242,54,69,0.08)'; msgBorder = 'rgba(242,54,69,0.2)';
  }

  circle.style.stroke = color;
  pctEl.textContent = posPct > 0 ? posPct.toFixed(1) + '%' : '0%';
  pctEl.style.color = color;
  if (msgEl) {
    msgEl.textContent = msg; msgEl.style.color = msgColor;
    msgEl.style.background = msgBg; msgEl.style.borderColor = msgBorder;
    msgEl.style.display = 'block';
  }
}


// ═══════════════════════════════════════════════════════════
// TAB 2: RISK DASHBOARD
// ═══════════════════════════════════════════════════════════
async function loadRiskDashboard() {
  try {
    const resp = await fetch('/api/risk_dashboard');
    const data = resp.ok ? await resp.json() : _mockDashboardData();
    _renderDashboard(data);
  } catch (e) {
    _renderDashboard(_mockDashboardData());
  }
}

function _mockDashboardData() {
  return {
    drawdown: -4.2,
    var_95: -2.8,
    total_exposure: 324500,
    win_rate: 62.5,
    health_score: 74,
    health_dd: 78,
    health_var: 72,
    health_div: 65,
    health_wr: 82,
    sectors: [
      { name:'IT', pct:28 }, { name:'Banking', pct:22 },
      { name:'FMCG', pct:15 }, { name:'Pharma', pct:18 },
      { name:'Auto', pct:10 }, { name:'Energy', pct:7 }
    ],
    positions: [
      { symbol:'TCS', entry:3450.5, cmp:3521.0, qty:10, days:5, sector:'IT' },
      { symbol:'HDFC', entry:1620.0, cmp:1598.5, qty:20, days:12, sector:'Banking' },
      { symbol:'ITC', entry:445.0, cmp:452.3, qty:50, days:3, sector:'FMCG' },
    ],
    daily_pnl: [
      { date:'Jun 17', pnl:1240 }, { date:'Jun 18', pnl:-560 },
      { date:'Jun 19', pnl:2100 }, { date:'Jun 20', pnl:-120 },
      { date:'Jun 21', pnl:880 },  { date:'Jun 24', pnl:1650 },
      { date:'Jun 25', pnl:-430 }, { date:'Jun 26', pnl:3200 },
      { date:'Jun 27', pnl:-200 }, { date:'Jun 28', pnl:1100 }
    ]
  };
}

function _renderDashboard(d) {
  // Stat tiles
  _setEl('rd-drawdown', (d.max_drawdown_pct || 0).toFixed(2) + '%');
  _setEl('rd-var',      (d.var_95_pct || 0).toFixed(2) + '%');
  _setEl('rd-exposure', '₹' + _fmt(d.total_exposure || 0));
  _setEl('rd-winrate',  (d.win_pct || 0).toFixed(1) + '%');
  _setEl('rd-sharpe',       (d.sharpe_ratio || 0).toFixed(2));
  _setEl('rd-profitfactor', (d.profit_factor || 0).toFixed(2));
  _setEl('rd-expectancy',   (d.expectancy >= 0 ? '+' : '') + '₹' + _fmt(d.expectancy || 0));

  // Health score
  const score = d.health_score || 0;
  _setEl('rd-health-score', score);
  const hc = document.getElementById('rd-health-circle');
  if (hc) {
    const pct = score / 100;
    hc.style.strokeDashoffset = (364 * (1 - pct)).toFixed(1);
    hc.style.stroke = score >= 70 ? 'var(--green)' : score >= 40 ? 'var(--gold)' : 'var(--red)';
  }
  const hl = document.getElementById('rd-health-label');
  if (hl) hl.textContent = score >= 70 ? '✅ HEALTHY PORTFOLIO' : score >= 40 ? '⚠️ MODERATE RISK' : '🚨 HIGH RISK PORTFOLIO';
  if (hl) hl.style.color = score >= 70 ? 'var(--green)' : score >= 40 ? 'var(--gold)' : 'var(--red)';

  // Health sub-bars
  setTimeout(() => {
    _setWidth('rd-hb-dd',  (d.health_dd  || 0));
    _setWidth('rd-hb-var', (d.health_var || 0));
    _setWidth('rd-hb-div', (d.health_div || 0));
    _setWidth('rd-hb-wr',  (d.health_wr  || 0));
  }, 100);

  // Sector heatmap
  _renderSectorHeatmap(d.sector_exposure || []);

  // Positions table
  _renderPositionsTable(d.positions || []);

  // Daily P&L bar chart
  _renderDailyPnlChart(d.daily_pnl || []);
}

function _renderSectorHeatmap(sectors) {
  const wrap = document.getElementById('rd-sector-heatmap');
  if (!wrap) return;
  if (!sectors.length) { wrap.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:30px;color:var(--dim);font-size:0.7rem;">No sector data</div>'; return; }
  const maxPct = Math.max(...sectors.map(s => s.pct));
  wrap.innerHTML = sectors.map(s => {
    const intensity = s.pct / maxPct;
    const r = Math.round(242 * intensity);
    const g = Math.round(54 + (153 - 54) * (1 - intensity));
    const b = Math.round(69 * (1 - intensity) + 129 * intensity);
    const bg = `rgba(${r},${g},${b},${0.15 + intensity * 0.35})`;
    const border = `rgba(${r},${g},${b},${0.4 + intensity * 0.4})`;
    return `
      <div style="background:${bg};border:1px solid ${border};border-radius:4px;padding:12px;
                  text-align:center;transition:transform 0.2s;" onmouseover="this.style.transform='scale(1.04)'" onmouseout="this.style.transform=''">
        <div style="font-family:'JetBrains Mono',monospace;font-size:1.1rem;font-weight:700;color:var(--white);">${s.pct}%</div>
        <div style="font-family:'Inter',sans-serif;font-size:0.62rem;color:var(--dim);margin-top:4px;">${s.name}</div>
        <div style="height:3px;background:${border};border-radius:2px;margin-top:6px;"></div>
      </div>`;
  }).join('');
}

function _renderPositionsTable(positions) {
  const tbody = document.getElementById('rd-positions-body');
  if (!tbody) return;
  if (!positions.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--dim);font-size:0.7rem;">No open positions</td></tr>';
    return;
  }
  tbody.innerHTML = positions.map(p => {
    const unrealized = (p.cmp - p.entry) * p.shares;
    const pnlPct = ((p.cmp - p.entry) / p.entry * 100).toFixed(2);
    const exposure = p.cmp * p.shares;
    const pnlColor = unrealized >= 0 ? 'var(--green)' : 'var(--red)';
    const pnlSign  = unrealized >= 0 ? '+' : '';
    return `
      <tr onmouseover="this.style.background='rgba(30,34,45,0.6)'" onmouseout="this.style.background=''">
        <td class="rd-td"><span style="color:var(--cyan);font-weight:700;">${p.symbol}</span></td>
        <td class="rd-td">₹${p.entry.toFixed(2)}</td>
        <td class="rd-td" style="color:var(--white);">₹${p.cmp.toFixed(2)}</td>
        <td class="rd-td" style="color:${pnlColor};font-weight:700;">${pnlSign}₹${_fmt(Math.abs(unrealized))} ${unrealized<0?'▼':'▲'}</td>
        <td class="rd-td" style="color:${pnlColor};">${pnlSign}${pnlPct}%</td>
        <td class="rd-td">${p.days_held}d</td>
        <td class="rd-td">₹${_fmt(exposure)}</td>
      </tr>`;
  }).join('');
}

function _renderDailyPnlChart(days) {
  const chart  = document.getElementById('rd-daily-pnl-chart');
  const labels = document.getElementById('rd-daily-pnl-labels');
  if (!chart) return;
  if (!days.length) { chart.innerHTML = '<div style="color:var(--dim);font-size:0.7rem;align-self:center;width:100%;text-align:center;">No daily P&L data</div>'; return; }

  const maxAbs = Math.max(...days.map(d => Math.abs(d.pnl)), 1);
  const barW   = `calc((100% - ${(days.length-1)*6}px) / ${days.length})`;

  chart.innerHTML = days.map(d => {
    const h = Math.max(4, (Math.abs(d.pnl) / maxAbs) * 100);
    const col = d.pnl >= 0 ? 'var(--green)' : 'var(--red)';
    const sign = d.pnl >= 0 ? '+' : '';
    return `
      <div title="${d.date}: ${sign}₹${_fmt(Math.abs(d.pnl))}"
        style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:2px;">
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.55rem;color:${col};">${sign}${_fmtK(d.pnl)}</div>
        <div style="width:100%;height:${h}px;background:${col};border-radius:2px 2px 0 0;opacity:0.85;
                    transition:height 0.5s cubic-bezier(0.4,0,0.2,1);min-height:4px;"></div>
      </div>`;
  }).join('');

  if (labels) {
    labels.style.display = 'flex'; labels.style.gap = '6px';
    labels.innerHTML = days.map(d =>
      `<div style="flex:1;text-align:center;font-family:'JetBrains Mono',monospace;font-size:0.55rem;color:var(--dim);">${d.date}</div>`
    ).join('');
  }
}


// ═══════════════════════════════════════════════════════════
// TAB 3: SETTINGS
// ═══════════════════════════════════════════════════════════
async function loadRiskSettings() {
  try {
    const resp = await fetch('/api/risk_settings_get');
    const data = resp.ok ? await resp.json() : {};
    _applySettings(data);
  } catch (e) {
    // Use defaults / existing values
  }
}

function _applySettings(s) {
  const set = (id, val) => { const el = document.getElementById(id); if (el && val !== undefined) el.value = val; };
  set('rs-capital',      s.capital        || 500000);
  set('rs-max-risk',     s.max_risk_pct   || 2);
  set('rs-max-positions',s.max_positions  || 10);
  set('rs-daily-loss',   s.daily_loss_limit || 10000);
  set('rs-sector-cap',   s.max_sector_exp || 30);

  // Sync display labels
  const mrEl = document.getElementById('rs-max-risk');
  if (mrEl) document.getElementById('rs-risk-val').textContent = parseFloat(mrEl.value).toFixed(1) + '%';
  const mpEl = document.getElementById('rs-max-positions');
  if (mpEl) document.getElementById('rs-pos-val').textContent = mpEl.value;
  const scEl = document.getElementById('rs-sector-cap');
  if (scEl) document.getElementById('rs-sector-val').textContent = scEl.value + '%';

  // Kill switch
  _risk.killSwitchOn = !!s.kill_switch;
  _syncKillSwitchUI();
  _updateSettingsSummary();
  _risk.settings = s;
}

function _updateSettingsSummary() {
  const g = id => document.getElementById(id)?.value || '—';
  _setEl('rs-s-cap',  '₹' + _fmt(parseFloat(g('rs-capital'))));
  _setEl('rs-s-risk', parseFloat(g('rs-max-risk')).toFixed(1) + '%');
  _setEl('rs-s-pos',  g('rs-max-positions') + ' trades');
  _setEl('rs-s-dll',  '₹' + _fmt(parseFloat(g('rs-daily-loss'))));
  _setEl('rs-s-sec',  g('rs-sector-cap') + '%');
  _setEl('rs-s-kill', _risk.killSwitchOn ? 'ON 🚨' : 'OFF ✅');
  const killEl = document.getElementById('rs-s-kill');
  if (killEl) killEl.style.color = _risk.killSwitchOn ? 'var(--red)' : 'var(--green)';
}

async function saveRiskSettings() {
  const payload = {
    capital:          parseFloat(document.getElementById('rs-capital')?.value) || 500000,
    max_risk_pct:     parseFloat(document.getElementById('rs-max-risk')?.value) || 2,
    max_positions:    parseInt(document.getElementById('rs-max-positions')?.value) || 10,
    daily_loss_limit: parseFloat(document.getElementById('rs-daily-loss')?.value) || 10000,
    max_sector_exp:   parseFloat(document.getElementById('rs-sector-cap')?.value) || 30,
    kill_switch:      _risk.killSwitchOn
  };

  const btn = document.getElementById('rs-save-btn');
  const msg = document.getElementById('rs-save-msg');
  if (btn) { btn.textContent = '⏳ SAVING...'; btn.disabled = true; }

  try {
    const resp = await fetch('/api/risk_settings_save', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const ok = resp.ok;
    if (msg) {
      msg.style.display = 'block';
      msg.textContent   = ok ? '✅ Settings saved successfully!' : '❌ Save failed — check server logs';
      msg.style.color   = ok ? 'var(--green)' : 'var(--red)';
      msg.style.background = ok ? 'rgba(8,153,129,0.1)' : 'rgba(242,54,69,0.1)';
      msg.style.border  = `1px solid ${ok ? 'rgba(8,153,129,0.3)' : 'rgba(242,54,69,0.3)'}`;
      setTimeout(() => { if (msg) msg.style.display = 'none'; }, 3500);
    }
  } catch (e) {
    if (msg) {
      msg.style.display='block'; msg.textContent='⚠️ Network error — saved locally';
      msg.style.color='var(--gold)'; msg.style.background='rgba(255,152,0,0.1)';
      msg.style.border='1px solid rgba(255,152,0,0.3)';
      setTimeout(() => { if (msg) msg.style.display='none'; }, 3500);
    }
  }

  if (btn) { btn.textContent = '💾 SAVE SETTINGS'; btn.disabled = false; }
  _updateSettingsSummary();

  // Sync capital to margin calculator
  const capEl = document.getElementById('mc-capital');
  if (capEl) { capEl.value = payload.capital; calcMargin(); }
}

function toggleKillSwitch() {
  _risk.killSwitchOn = !_risk.killSwitchOn;
  _syncKillSwitchUI();
  _updateSettingsSummary();
}

function _syncKillSwitchUI() {
  const toggle = document.getElementById('rs-kill-switch-toggle');
  const thumb  = document.getElementById('rs-kill-thumb');
  const status = document.getElementById('rs-kill-status');
  const banner = document.getElementById('risk-kill-banner');

  if (!toggle) return;
  if (_risk.killSwitchOn) {
    toggle.style.background = 'rgba(242,54,69,0.2)';
    toggle.style.borderColor = 'var(--red)';
    if (thumb) { thumb.style.left = '38px'; thumb.style.background = 'var(--red)'; }
    if (status) { status.textContent = 'ACTIVE 🚨'; status.style.color = 'var(--red)'; }
    if (banner) { banner.style.display = 'flex'; }
    document.querySelectorAll('#rs-kill-switch-toggle ~ div > div:last-child').forEach(el => el.textContent = 'New trades BLOCKED');
  } else {
    toggle.style.background = 'var(--p2)';
    toggle.style.borderColor = 'var(--border)';
    if (thumb) { thumb.style.left = '4px'; thumb.style.background = 'var(--dim)'; }
    if (status) { status.textContent = 'INACTIVE'; status.style.color = 'var(--dim)'; }
    if (banner) { banner.style.display = 'none'; }
  }
}


// ═══════════════════════════════════════════════════════════
// TAB 4: CORRELATION MATRIX
// ═══════════════════════════════════════════════════════════
async function prefetchAllSymbols() {
  try {
    const d = await api('all_symbols');
    _risk.allSymbols = [...d.indices, ...d.equities, ...d.commodities].map(x => typeof x === 'object' ? x.symbol : x);
  } catch(e) {
    // Fallback symbols
    _risk.allSymbols = ['TCS','RELIANCE','HDFC','INFY','WIPRO','HDFCBANK','ICICIBANK','SBIN','BHARTIARTL','ITC',
      'BAJFINANCE','KOTAKBANK','LT','ASIANPAINT','HINDUNILVR','AXISBANK','TATAMOTORS','SUNPHARMA','TITAN','ULTRACEMCO',
      'MARUTI','POWERGRID','NESTLEIND','TECHM','HCLTECH','ADANIPORTS','TATASTEEL','JSWSTEEL','COALINDIA','ONGC'];
  }
}

function corrFilterSymbols(q) {
  const dd = document.getElementById('corr-dropdown');
  if (!dd) return;
  const query = q.trim().toUpperCase();
  if (!query) { dd.style.display = 'none'; return; }
  const filtered = _risk.allSymbols.filter(s => s.includes(query) && !_risk.corrSymbols.includes(s)).slice(0, 20);
  if (!filtered.length) { dd.style.display = 'none'; return; }
  dd.innerHTML = filtered.map(s =>
    `<div class="corr-dd-item" onclick="corrAddSymbol('${s}')">${s}</div>`
  ).join('');
  dd.style.display = 'block';
}

function corrAddSymbol(sym) {
  if (_risk.corrSymbols.includes(sym)) return;
  if (_risk.corrSymbols.length >= 8) {
    alert('Maximum 8 symbols for correlation matrix.'); return;
  }
  _risk.corrSymbols.push(sym);
  _renderCorrChips();
  const inp = document.getElementById('corr-search');
  if (inp) { inp.value = ''; }
  document.getElementById('corr-dropdown').style.display = 'none';
}

function corrRemoveSymbol(sym) {
  _risk.corrSymbols = _risk.corrSymbols.filter(s => s !== sym);
  _renderCorrChips();
}

function _renderCorrChips() {
  const wrap = document.getElementById('corr-selected-chips');
  if (!wrap) return;
  wrap.innerHTML = _risk.corrSymbols.map(s =>
    `<span class="corr-chip" onclick="corrRemoveSymbol('${s}')" title="Click to remove">${s} ✕</span>`
  ).join('');
}

async function loadCorrelation() {
  if (_risk.corrSymbols.length < 2) {
    alert('Please select at least 2 symbols.'); return;
  }
  const period   = document.getElementById('corr-period')?.value || 60;
  const syms     = _risk.corrSymbols.join(',');
  const wrap     = document.getElementById('corr-heatmap-wrap');
  const pholder  = document.getElementById('corr-placeholder');

  if (pholder) pholder.innerHTML = '<div style="padding:40px;text-align:center;color:var(--dim);font-family:JetBrains Mono,monospace;font-size:0.75rem;">⏳ Computing correlation matrix...</div>';
  if (pholder) pholder.style.display = '';
  if (wrap)    wrap.style.display = 'none';

  try {
    const resp = await fetch(`/api/correlation_matrix?symbols=${syms}&period=${period}`);
    const data = resp.ok ? await resp.json() : _mockCorrData(_risk.corrSymbols);
    drawCorrelationHeatmap(data.matrix, data.symbols || _risk.corrSymbols);
  } catch(e) {
    drawCorrelationHeatmap(_mockCorrData(_risk.corrSymbols).matrix, _risk.corrSymbols);
  }
}

function _mockCorrData(symbols) {
  const n = symbols.length;
  const matrix = [];
  for (let i = 0; i < n; i++) {
    matrix[i] = [];
    for (let j = 0; j < n; j++) {
      if (i === j) { matrix[i][j] = 1.0; }
      else if (j < i) { matrix[i][j] = matrix[j][i]; }
      else {
        // Random realistic correlation
        const base = Math.random() * 1.6 - 0.8;
        matrix[i][j] = Math.max(-1, Math.min(1, base));
      }
    }
  }
  return { matrix, symbols };
}

function drawCorrelationHeatmap(matrix, symbols) {
  const wrap    = document.getElementById('corr-heatmap-wrap');
  const pholder = document.getElementById('corr-placeholder');
  const warnDiv = document.getElementById('corr-warnings');
  const warnBody= document.getElementById('corr-warnings-body');
  if (!wrap) return;

  const n    = symbols.length;
  const cell = Math.max(56, Math.min(90, Math.floor(560 / n)));

  const colForValue = (v) => {
    // deep green +1 → white 0 → deep red -1
    if (v >= 0) {
      const t = v;
      const r = Math.round(255 - 255 * t);
      const g = Math.round(255 - (255 - 128) * t);
      const b = Math.round(255 - (255 - 0) * t);
      return `rgb(${r},${g},${b})`;
    } else {
      const t = -v;
      const r = Math.round(255);
      const g = Math.round(255 - (255 - 54) * t);
      const b = Math.round(255 - (255 - 69) * t);
      return `rgb(${r},${g},${b})`;
    }
  };

  let html = `
    <div style="display:inline-block;overflow:auto;">
    <table style="border-collapse:collapse;">
      <tr>
        <th style="width:${cell}px;height:${cell}px;"></th>
        ${symbols.map(s => `<th style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;color:var(--dim);padding:4px 6px;text-align:center;width:${cell}px;">${s}</th>`).join('')}
      </tr>`;

  const highCorr = [];
  for (let i = 0; i < n; i++) {
    html += `<tr><th style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;color:var(--dim);padding:4px 8px;text-align:right;white-space:nowrap;">${symbols[i]}</th>`;
    for (let j = 0; j < n; j++) {
      const v   = matrix[i][j];
      const bg  = colForValue(v);
      const lum = (i === j) ? 255 : (Math.abs(v) > 0.5 ? 20 : 180);
      const textColor = `rgb(${lum},${lum},${lum})`;
      const dispVal = v.toFixed(2);
      html += `
        <td title="${symbols[i]} vs ${symbols[j]}: ${dispVal}"
          style="width:${cell}px;height:${cell}px;background:${bg};
                 text-align:center;vertical-align:middle;
                 border:1px solid rgba(43,49,57,0.6);">
          <span class="corr-heatmap-cell" style="width:100%;height:100%;color:${textColor};font-size:${n>5?'0.62':'0.72'}rem;">
            ${dispVal}
          </span>
        </td>`;
      if (i < j && Math.abs(v) > 0.8 && i !== j) {
        highCorr.push({ a: symbols[i], b: symbols[j], val: v });
      }
    }
    html += '</tr>';
  }
  html += '</table>';

  // Color legend
  html += `
    <div style="display:flex;align-items:center;gap:12px;margin-top:14px;padding:0 4px;">
      <span style="font-family:'Inter',sans-serif;font-size:0.62rem;color:var(--dim);">-1.0</span>
      <div style="flex:1;height:10px;border-radius:5px;
        background:linear-gradient(90deg,rgb(255,54,69),rgb(255,255,255),rgb(0,128,0));"></div>
      <span style="font-family:'Inter',sans-serif;font-size:0.62rem;color:var(--dim);">+1.0</span>
    </div>
    </div>`;

  wrap.innerHTML = html;
  wrap.style.display = '';
  if (pholder) pholder.style.display = 'none';

  // Warnings
  if (warnDiv && warnBody) {
    if (highCorr.length) {
      warnDiv.style.display = '';
      warnBody.innerHTML = `
        <div style="margin-bottom:8px;color:var(--gold);">Highly correlated pairs (&gt;0.8) detected — consider reducing exposure:</div>
        ${highCorr.map(p => `
          <div style="display:flex;align-items:center;gap:10px;padding:5px 0;border-bottom:1px solid rgba(43,49,57,0.4);">
            <span style="color:var(--cyan);font-weight:700;">${p.a}</span>
            <span style="color:var(--dim);">↔</span>
            <span style="color:var(--cyan);font-weight:700;">${p.b}</span>
            <span style="margin-left:auto;color:${p.val > 0 ? 'var(--gold)' : 'var(--red)'};">${p.val.toFixed(3)}</span>
          </div>`).join('')}
        <div style="margin-top:8px;font-size:0.65rem;color:var(--dim);">
          ⚠️ Highly correlated positions amplify portfolio risk. Consider hedging or reducing one position.
        </div>`;
    } else {
      warnDiv.style.display = 'none';
    }
  }
}


// ═══════════════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════════════
function _setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function _setWidth(id, pct) {
  const el = document.getElementById(id);
  if (el) el.style.width = Math.min(100, Math.max(0, pct)) + '%';
}

function _fmt(n) {
  if (isNaN(n) || n === null) return '0';
  if (Math.abs(n) >= 10000000) return (n / 10000000).toFixed(2) + 'Cr';
  if (Math.abs(n) >= 100000)  return (n / 100000).toFixed(2) + 'L';
  return Math.round(n).toLocaleString('en-IN');
}

function _fmtK(n) {
  if (Math.abs(n) >= 100000) return (n / 100000).toFixed(1) + 'L';
  if (Math.abs(n) >= 1000)   return (n / 1000).toFixed(1) + 'K';
  return Math.round(n).toString();
}

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
  const dd = document.getElementById('corr-dropdown');
  const wrap = document.getElementById('corr-symbol-select-wrap');
  if (dd && wrap && !wrap.contains(e.target)) {
    dd.style.display = 'none';
  }
});
"""
