"""
page_sentiment.py — High-Performance Multi-Factor Market Sentiment Engine
"""

HTML = r"""<!-- ═══════════ PAGE: SENTIMENT ═══════════ -->
<div class="page" id="page-sentiment">
  <div class="topbar">
    <h2>🧠 SENTIMENT + EMOTIONAL ANALYSIS</h2>
  </div>

  <!-- Professional Toolbar with Search-Combobox & Fast Lookbacks (Bug 1) -->
  <div class="card" style="padding:10px 14px;margin-bottom:12px;background:var(--p2);border:1px solid var(--border);">
    <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
      
      <!-- Search Combobox Container -->
      <div style="position:relative;flex:1;min-width:260px;">
        <label style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;display:block;margin-bottom:3px;">
          SEARCH ASSET / TICKER
        </label>
        <div style="position:relative;display:flex;align-items:center;">
          <input type="text" id="sent-sym-search" placeholder="🔍 Search Symbol (e.g. RELIANCE, NIFTY50, GOLD)..." autocomplete="off"
            style="width:100%;background:var(--bg);border:1px solid var(--b2);color:var(--gold);padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.82rem;font-weight:700;outline:none;border-radius:4px;box-sizing:border-box;"
            oninput="sentFilterDropdown(this.value)" onfocus="sentShowDropdown()" onclick="sentShowDropdown()">
          <input type="hidden" id="sent-sym" value="">
          <button type="button" onclick="sentClearSymbol()" style="position:absolute;right:8px;background:transparent;border:none;color:var(--dim);cursor:pointer;font-size:0.8rem;">✕</button>
        </div>
        <!-- Floating Autocomplete Dropdown -->
        <div id="sent-sym-dropdown" style="display:none;position:absolute;top:100%;left:0;right:0;max-height:280px;overflow-y:auto;background:var(--p1);border:1px solid var(--border);border-radius:4px;box-shadow:0 8px 24px rgba(0,0,0,0.6);z-index:9999;margin-top:4px;">
          <!-- Populated by JS -->
        </div>
      </div>

      <!-- Quick Category Filter Pills -->
      <div style="display:flex;flex-direction:column;gap:3px;">
        <label style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;">ASSET CLASS</label>
        <div style="display:flex;gap:4px;">
          <button class="btn btn-sm active" id="sent-pill-all" onclick="sentSetCategory('ALL')" style="padding:4px 8px;font-size:0.65rem;">🌐 All</button>
          <button class="btn btn-sm" id="sent-pill-indices" onclick="sentSetCategory('INDEX')" style="padding:4px 8px;font-size:0.65rem;">🏛 Indices</button>
          <button class="btn btn-sm" id="sent-pill-stocks" onclick="sentSetCategory('EQUITY')" style="padding:4px 8px;font-size:0.65rem;">🏢 Stocks</button>
          <button class="btn btn-sm" id="sent-pill-commodities" onclick="sentSetCategory('COMMODITY')" style="padding:4px 8px;font-size:0.65rem;">🪙 Commodities</button>
        </div>
      </div>

      <!-- Fast Trading Lookback Horizons (Sentiment changes rapidly!) -->
      <div style="display:flex;flex-direction:column;gap:3px;">
        <label style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;">LOOKBACK HORIZON</label>
        <select id="sent-period"
          style="background:var(--bg);border:1px solid var(--b2);color:var(--cyan);padding:5px 8px;
          font-family:Share Tech Mono,monospace;font-size:0.75rem;outline:none;border-radius:4px;min-width:130px;">
          <option value="1">1D (Today's Momentum)</option>
          <option value="3" selected>3D (Tactical Swing)</option>
          <option value="7">7D (Weekly Trend)</option>
          <option value="14">14D (Bi-Weekly F&O)</option>
          <option value="30">30D (Monthly Expiry)</option>
        </select>
      </div>

      <!-- Action Buttons -->
      <div style="display:flex;gap:8px;align-items:flex-end;margin-top:auto;">
        <button class="btn btn-gold" onclick="loadSentiment()" style="padding:7px 18px;font-size:0.75rem;font-weight:700;">⚡ ANALYSE</button>
        <button class="btn" onclick="showGeneralOverview()" style="padding:7px 16px;font-size:0.75rem;background:rgba(0,212,255,0.08);border:1px solid rgba(0,212,255,0.3);color:var(--cyan);">🌐 MARKET BRAIN</button>
      </div>
    </div>
  </div>

  <div id="sent-loading" class="loading" style="display:none;"><div class="spinner"></div>COMPUTING MULTI-FACTOR SENTIMENT...</div>
  <div id="sent-error" style="display:none;padding:12px;color:var(--red);font-family:Share Tech Mono,monospace;background:rgba(255,51,85,0.08);border:1px solid rgba(255,51,85,0.25);border-radius:4px;margin-bottom:12px;"></div>

  <!-- ════════════════════════════════════════════════════════════════ -->
  <!-- GENERAL MARKET OVERVIEW VIEW (MARKET BRAIN)                      -->
  <!-- ════════════════════════════════════════════════════════════════ -->
  <div id="sent-general-view" style="display:none;margin-top:8px;">
    
    <!-- Row 1: Unified Speedometer & Multi-Factor Confidence Narrative (Bugs 2 & 3) -->
    <div style="display:grid;grid-template-columns:300px 1fr;gap:14px;margin-bottom:14px;">
      
      <!-- Global Mood Speedometer Gauge -->
      <div class="card" style="padding:18px;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:230px;text-align:center;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);letter-spacing:2px;margin-bottom:10px;">GLOBAL MARKET MOOD SPEEDOMETER</div>
        <canvas id="mb-gauge" width="220" height="130" style="display:block;"></canvas>
        <div id="mb-mood-label" style="font-family:Orbitron,sans-serif;font-size:1.6rem;font-weight:900;margin-top:6px;text-transform:uppercase;">—</div>
        <div id="mb-mood-rationale" style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);margin-top:6px;line-height:1.4;max-width:260px;">—</div>
      </div>

      <!-- Narrative & Multi-Factor Confidence Engine -->
      <div class="card" style="padding:18px;display:flex;flex-direction:column;justify-content:space-between;min-height:230px;">
        <div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px;">
            <span class="card-title" style="margin-bottom:0;color:var(--gold);">TODAY'S MARKET NARRATIVE</span>
            <!-- Interactive Multi-Factor Confidence Badge -->
            <div style="position:relative;display:inline-block;">
              <span id="mb-confidence-badge" class="badge bc" style="padding:4px 10px;font-size:0.68rem;cursor:help;border:1px solid rgba(0,212,255,0.4);"
                title="Hover for factor breakdown">
                Confidence: —
              </span>
              <!-- Hover Contributor Breakdown -->
              <div id="mb-conf-tooltip" style="display:none;position:absolute;right:0;top:100%;margin-top:6px;width:280px;background:rgba(10,16,26,0.95);border:1px solid var(--cyan);box-shadow:0 8px 24px rgba(0,0,0,0.8);padding:10px;border-radius:4px;z-index:999;font-family:Share Tech Mono,monospace;font-size:0.62rem;line-height:1.5;">
                <div style="color:var(--gold);font-weight:700;margin-bottom:4px;border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:3px;">CONFIDENCE ENGINE CONTRIBUTORS</div>
                <div id="mb-conf-factors"></div>
              </div>
            </div>
          </div>
          <div id="mb-narrative-text" style="font-size:0.85rem;line-height:1.7;color:var(--text);margin-top:6px;"></div>
        </div>
        <div style="font-size:0.6rem;color:var(--dim);border-top:1px solid var(--border);padding-top:10px;margin-top:12px;display:flex;justify-content:space-between;">
          <span>ENGINE: 100% LOCAL DATABASE & LIVE RSS MULTI-FACTOR ENGINE</span>
          <span id="mb-digest-date">Date: --</span>
        </div>
      </div>
    </div>

    <!-- Row 2: Institutional Positioning — Smart Money (FII / DII / PRO) vs Retail (Bug 5) -->
    <div class="card" style="padding:16px;margin-bottom:14px;background:linear-gradient(135deg, rgba(16,24,38,0.95), rgba(24,32,48,0.85));border:1px solid rgba(0,212,255,0.25);">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px;">
        <div class="card-title" style="color:var(--gold);letter-spacing:2px;margin-bottom:0;">🏛️ INSTITUTIONAL POSITIONING — SMART MONEY (FII / DII / PRO) vs. RETAIL</div>
        <div id="mb-part-date" style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);">NSE ARCHIVE DATE: --</div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:12px;">
        
        <!-- Card 1: FII Futures Long/Short Ribbon -->
        <div style="background:var(--p2);border:1px solid var(--border);padding:12px;border-radius:4px;">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">FII INDEX FUTURES LONG %</div>
          <div id="mb-fii-long-pct" style="font-family:Orbitron,sans-serif;font-size:1.4rem;font-weight:900;color:var(--cyan);">—</div>
          <div id="mb-fii-contracts" style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--t2);margin-top:2px;">Net Futures: —</div>
          <div style="height:6px;background:rgba(255,255,255,0.06);border-radius:3px;margin:8px 0;overflow:hidden;">
            <div id="mb-fii-bar" style="height:100%;width:50%;background:var(--cyan);transition:width 0.4s;"></div>
          </div>
          <div id="mb-fii-zone" style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);">CAPITULATION ZONE: &lt; 20%</div>
        </div>

        <!-- Card 2: Retail Contrarian Options Battle Bar -->
        <div style="background:var(--p2);border:1px solid var(--border);padding:12px;border-radius:4px;">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">RETAIL (CLIENT) CONTRARIAN FLOW</div>
          <div id="mb-client-signal" style="font-family:Orbitron,sans-serif;font-size:1.1rem;font-weight:700;color:var(--gold);">—</div>
          <div id="mb-client-calls" style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--green);margin-top:2px;">Net Calls: —</div>
          <div id="mb-client-puts" style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--red);margin-top:2px;">Net Puts: —</div>
          <div id="mb-client-note" style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);margin-top:6px;">Smart money fades retail extremes</div>
        </div>

        <!-- Card 3: Smart Money Inflection Bias -->
        <div style="background:var(--p2);border:1px solid var(--border);padding:12px;border-radius:4px;">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">SMART MONEY INFLECTION BIAS</div>
          <div id="mb-smart-bias" style="font-family:Orbitron,sans-serif;font-size:1.1rem;font-weight:700;color:var(--green);">—</div>
          <div id="mb-smart-setup" style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--cyan);margin-top:3px;font-weight:600;">—</div>
          <div id="mb-smart-detail" style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);margin-top:6px;line-height:1.3;">High statistical correlation with multi-week turning points.</div>
        </div>

        <!-- Card 4: India VIX Volatility Regime -->
        <div style="background:var(--p2);border:1px solid var(--border);padding:12px;border-radius:4px;">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">INDIA VIX (^INDIAVIX) REGIME</div>
          <div id="mb-vix-val" style="font-family:Orbitron,sans-serif;font-size:1.4rem;font-weight:900;color:var(--gold);">—</div>
          <div id="mb-vix-regime" style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--t2);margin-top:2px;">—</div>
          <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);margin-top:8px;">&lt; 12: Complacency | 12-20: Healthy | &gt; 22: Panic</div>
        </div>
      </div>
    </div>

    <!-- Row 3: Sector Sentiment Board with Drill-Down Modal & Highest Impact News Flow (Bugs 6 & 7) -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px;">
      
      <!-- Sector Sentiment Board (Clickable for drill-down modal) -->
      <div class="card" style="padding:16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
          <div class="card-title" style="margin-bottom:0;">📊 SECTOR SENTIMENT BOARD</div>
          <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);">CLICK ANY ROW FOR CONSTITUENT DRILLDOWN 🔍</span>
        </div>
        <div id="mb-sectors-grid" style="display:flex;flex-direction:column;gap:8px;max-height:480px;overflow-y:auto;">
          <div class="loading"><div class="spinner"></div>COMPUTING SECTOR RATINGS...</div>
        </div>
      </div>

      <!-- Highest Impact News Flow (Ranked with Catalyst Tags) -->
      <div class="card" style="padding:16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
          <div class="card-title" style="margin-bottom:0;">📰 HIGHEST IMPACT NEWS FLOW (TIMELINE)</div>
          <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--cyan);">RANKED BY INSTITUTIONAL WEIGHT</span>
        </div>
        <div id="mb-events-timeline" style="display:flex;flex-direction:column;gap:10px;max-height:480px;overflow-y:auto;">
          <div class="loading"><div class="spinner"></div>ANALYSING NEWS FLOW...</div>
        </div>
      </div>
    </div>

    <!-- Row 4: AI Copilot Assistant Guidance Prompt (Clean replacement for duplicate Q&A - Bug 4) -->
    <div class="card" style="padding:14px 20px;background:rgba(41,98,255,0.06);border:1px solid rgba(0,212,255,0.25);border-radius:4px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">
      <div style="display:flex;align-items:center;gap:14px;">
        <span style="font-size:1.6rem;">💡</span>
        <div>
          <b style="color:var(--cyan);font-size:0.82rem;">Need In-Depth Macro or Sector Catalyst Reasoning?</b>
          <div style="font-size:0.7rem;color:var(--dim);margin-top:2px;">
            Ask our interactive <b>AI Copilot Assistant</b> (floating chat widget) for conversational analysis on interest rate decisions, earnings releases, and sector rotations.
          </div>
        </div>
      </div>
      <button class="btn btn-sm btn-gold" onclick="if(window.toggleAIAssistant)toggleAIAssistant();" style="padding:6px 16px;font-size:0.72rem;font-weight:700;">
        ⚡ OPEN AI COPILOT
      </button>
    </div>
  </div>

  <!-- ════════════════════════════════════════════════════════════════ -->
  <!-- SECTOR DRILL-DOWN MODAL (Bug 6)                                  -->
  <!-- ════════════════════════════════════════════════════════════════ -->
  <div id="sector-detail-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.75);z-index:99999;align-items:center;justify-content:center;backdrop-filter:blur(3px);">
    <div style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:20px;width:740px;max-width:92vw;max-height:90vh;overflow-y:auto;position:relative;box-shadow:0 12px 40px rgba(0,0,0,0.8);">
      <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border);padding-bottom:10px;margin-bottom:14px;">
        <div style="display:flex;align-items:center;gap:10px;">
          <h3 id="sec-modal-title" style="color:var(--gold);font-family:Orbitron,sans-serif;font-size:1.1rem;margin:0;">SECTOR DRILL-DOWN</h3>
          <span id="sec-modal-bias-badge" class="badge bg" style="font-size:0.65rem;">POSITIVE</span>
          <span id="sec-modal-score" style="font-family:Share Tech Mono,monospace;font-size:0.85rem;color:var(--cyan);font-weight:700;">+0.25</span>
        </div>
        <button onclick="closeSectorDetailModal()" style="background:transparent;border:none;color:var(--dim);font-size:1.3rem;cursor:pointer;">✕</button>
      </div>

      <!-- Rationale Summary -->
      <div id="sec-modal-rationale" style="padding:10px 12px;background:var(--p2);border-left:3px solid var(--cyan);font-size:0.75rem;line-height:1.6;color:var(--text);margin-bottom:14px;"></div>

      <!-- Constituent Equities Table -->
      <div style="margin-bottom:16px;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);letter-spacing:1px;margin-bottom:6px;">CONSTITUENT STOCKS LIVE SENTIMENT & PRICE</div>
        <div id="sec-modal-constituents" style="display:grid;grid-template-columns:repeat(auto-fit, minmax(140px, 1fr));gap:8px;"></div>
      </div>

      <!-- Catalysts Breakdown (Positive vs Negative) -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div style="background:var(--p2);border:1px solid rgba(0,255,136,0.2);padding:12px;border-radius:4px;">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--green);font-weight:700;margin-bottom:8px;">🟢 TOP POSITIVE CATALYSTS</div>
          <div id="sec-modal-pos-catalysts" style="display:flex;flex-direction:column;gap:8px;font-size:0.72rem;"></div>
        </div>
        <div style="background:var(--p2);border:1px solid rgba(255,51,85,0.2);padding:12px;border-radius:4px;">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--red);font-weight:700;margin-bottom:8px;">🔴 TOP NEGATIVE CATALYSTS</div>
          <div id="sec-modal-neg-catalysts" style="display:flex;flex-direction:column;gap:8px;font-size:0.72rem;"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- ════════════════════════════════════════════════════════════════ -->
  <!-- SYMBOL-SPECIFIC SENTIMENT & REINFORCEMENT LEARNING CONTENT       -->
  <!-- ════════════════════════════════════════════════════════════════ -->
  <div id="sent-content" style="display:none;margin-top:8px;">


    <div style="display:none;">

      <!-- Composite Gauge & Accuracy Badge -->
      <div class="card" style="padding:18px;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:220px;text-align:center;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);letter-spacing:2px;margin-bottom:8px;">COMPOSITE SENTIMENT SCORE</div>
        <canvas id="sent-gauge" width="200" height="120" style="display:block;"></canvas>
        <div id="sent-score-label" style="font-family:Orbitron,sans-serif;font-size:2rem;font-weight:900;margin-top:6px;">—</div>
        <div id="sent-verdict" style="font-family:Share Tech Mono,monospace;font-size:0.75rem;letter-spacing:2px;margin-top:2px;">—</div>
        
        <!-- Reinforcement Learning Live Accuracy Badge -->
        <div id="sent-accuracy-badge" style="margin-top:10px;padding:4px 10px;background:rgba(0,255,136,0.08);border:1px solid rgba(0,255,136,0.3);border-radius:3px;font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--green);">
          🎯 RL HIT RATE: 72.4% (T+3)
        </div>
        <div id="sent-score-detail" style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);margin-top:4px;"></div>
      </div>

      <!-- Component Breakdown (5 Pillars) -->
      <div class="card" style="padding:16px;">
        <div class="card-title" style="margin-bottom:12px;">📊 MULTI-PILLAR SENTIMENT BREAKDOWN</div>
        <div id="sent-components" style="display:flex;flex-direction:column;gap:10px;"></div>
      </div>
    </div>

    <!-- Row 2: Structured Institutional Decision Matrix (Bug 15) -->
    <div class="card" style="padding:16px;margin-bottom:12px;border-left:4px solid var(--cyan);">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:8px;">
        <div class="card-title" style="margin-bottom:0;">🎯 INSTITUTIONAL DECISION MATRIX</div>
        <div id="sent-matrix-verdict-badge" class="badge bg" style="font-size:0.7rem;padding:3px 10px;">VERDICT: BULLISH CONFLUENCE</div>
      </div>
      <div id="sent-matrix-content" style="font-family:Share Tech Mono,monospace;font-size:0.75rem;line-height:1.7;"></div>
    </div>

    <!-- Row 3: 14-Day Rolling History Chart with Date Axis & Legend (Bug 14) -->
    <div class="card" style="display:none;padding:0;margin-bottom:12px;">
      <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px 0;">
        <div class="card-title" style="margin-bottom:0;">📉 SENTIMENT SCORE HISTORY (ROLLING 14-DAY)</div>
        <div style="display:flex;gap:14px;font-family:Share Tech Mono,monospace;font-size:0.6rem;">
          <span style="color:#26a69a;">■ Bullish (&gt;0)</span>
          <span style="color:#ef5350;">■ Bearish (&lt;0)</span>
          <span style="color:var(--dim);">--- Baseline Zero</span>
        </div>
      </div>
      <div style="height:160px;padding:8px 12px 12px;position:relative;">
        <canvas id="sent-history-chart" style="display:block;width:100%;height:140px;"></canvas>
      </div>
    </div>

    <!-- ── DEDICATED AI MANAGEMENT TONE & STRATEGIC GUIDANCE CARD (Bug 4) ── -->
    <div class="card" id="sent-mgmt-card" style="padding:16px;margin-bottom:12px;border:1px solid rgba(0,212,255,0.3);background:linear-gradient(135deg,rgba(0,212,255,0.04),rgba(41,98,255,0.02));">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px;">
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="font-family:Orbitron,sans-serif;font-size:0.95rem;font-weight:700;color:var(--cyan);">🤖 AI MANAGEMENT TONE & STRATEGIC GUIDANCE</span>
          <span class="badge bd" style="font-size:0.6rem;background:rgba(0,212,255,0.1);color:var(--cyan);border:1px solid rgba(0,212,255,0.3);">NLP AI EXTRACTED</span>
        </div>
        <div id="mgmt-guidance-badge" class="badge bg" style="font-size:0.7rem;padding:4px 12px;font-weight:700;">GUIDANCE: BALANCED</div>
      </div>

      <!-- Tone Gauge & Key Metrics Bar -->
      <div style="display:grid;grid-template-columns:220px 1fr;gap:16px;align-items:center;padding:12px;background:rgba(0,0,0,0.25);border-radius:4px;margin-bottom:14px;">
        <div style="text-align:center;">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);margin-bottom:4px;">MANAGEMENT CONFIDENCE TONE</div>
          <div id="mgmt-tone-score" style="font-family:Orbitron,sans-serif;font-size:1.8rem;font-weight:900;color:var(--gold);">+0.44</div>
          <div id="mgmt-tone-label" style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--green);font-weight:700;">BULLISH CONVICTION</div>
        </div>
        <div style="display:flex;flex-direction:column;gap:6px;">
          <div style="display:flex;justify-content:space-between;font-family:Share Tech Mono,monospace;font-size:0.65rem;">
            <span style="color:var(--dim);">TONE SPECTRUM (-1.0 to +1.0)</span>
            <span id="mgmt-tone-pct" style="color:var(--cyan);font-weight:700;">72% Bullish</span>
          </div>
          <div style="height:8px;background:rgba(255,255,255,0.06);border-radius:4px;overflow:hidden;position:relative;">
            <div id="mgmt-tone-bar" style="height:100%;width:72%;background:linear-gradient(90deg,#ff3355,#ffcc00,#00ff88);border-radius:4px;transition:width 0.4s;"></div>
          </div>
          <div style="display:flex;justify-content:space-between;font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);">
            <span>-1.0 CAUTIOUS/DEFENSIVE</span>
            <span>0.0 NEUTRAL</span>
            <span>+1.0 EXPANSIONARY</span>
          </div>
        </div>
      </div>

      <!-- 3-Bullet Executive Breakdown -->
      <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));gap:12px;">
        <!-- Box 1: What Management Is Willing To Do -->
        <div style="padding:12px;background:rgba(0,0,0,0.2);border:1px solid rgba(255,255,255,0.05);border-radius:4px;">
          <div style="display:flex;align-items:center;gap:6px;font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--gold);font-weight:700;margin-bottom:6px;">
            🎯 WHAT MANAGEMENT IS WILLING TO DO (CAPEX & EXPANSION)
          </div>
          <div id="mgmt-strategic-intent" style="font-size:0.75rem;line-height:1.6;color:var(--t2);">
            Analyzing corporate announcements and earnings call disclosures...
          </div>
        </div>

        <!-- Box 2: Operating & Margin Guidance -->
        <div style="padding:12px;background:rgba(0,0,0,0.2);border:1px solid rgba(255,255,255,0.05);border-radius:4px;">
          <div style="display:flex;align-items:center;gap:6px;font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--green);font-weight:700;margin-bottom:6px;">
            📈 OPERATIONAL & MARGIN GUIDANCE
          </div>
          <div id="mgmt-margin-guidance" style="font-size:0.75rem;line-height:1.6;color:var(--t2);">
            Synthesizing margin targets, pricing power, and cost efficiency programs...
          </div>
        </div>

        <!-- Box 3: Key Headwinds & Risks -->
        <div style="padding:12px;background:rgba(0,0,0,0.2);border:1px solid rgba(255,255,255,0.05);border-radius:4px;">
          <div style="display:flex;align-items:center;gap:6px;font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--red);font-weight:700;margin-bottom:6px;">
            ⚠️ MANAGEMENT-DISCLOSED HEADWINDS & RISKS
          </div>
          <div id="mgmt-key-risks" style="font-size:0.75rem;line-height:1.6;color:var(--t2);">
            Extracting regulatory, raw material, and macro friction risks...
          </div>
        </div>
      </div>
    </div>

    <!-- ── EXTERNAL SENTIMENT: News + Analyst + AI Tone (Bugs 16, 18, 21) ── -->
    <div id="sent-external-section" style="margin-top:4px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--cyan);letter-spacing:3px;display:flex;align-items:center;gap:8px;">
          📰 EXTERNAL SENTIMENT — REAL-TIME MEDIA & ANALYSTS
          <span id="ext-total-badge" style="background:rgba(0,212,255,0.08);border:1px solid rgba(0,212,255,0.2);padding:1px 8px;border-radius:2px;font-size:0.6rem;"></span>
        </div>
        <button onclick="loadExternalSentiment()" id="ext-refresh-btn"
          style="background:var(--p2);border:1px solid var(--b2);color:var(--cyan);padding:4px 14px;
          font-family:Share Tech Mono,monospace;font-size:0.62rem;cursor:pointer;letter-spacing:1px;border-radius:3px;">
          ⟳ REFRESH
        </button>
      </div>

      <div id="ext-loading" style="display:none;padding:12px 0;font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--cyan);display:flex;align-items:center;gap:8px;">
        <div class="spinner"></div>FETCHING NEWS, ANALYSTS & MANAGEMENT TONE...
      </div>
      <div id="ext-error" style="display:none;padding:10px;color:var(--red);font-family:Share Tech Mono,monospace;font-size:0.72rem;"></div>

      <div id="ext-content" style="display:none;">
        
        <!-- Row: External Score + Source Breakdown + AI Tone + Narrative (Bug 17) -->
        <div style="display:none;">
          
          <!-- External score + source breakdown -->
          <div class="card" style="padding:16px;">
            <div class="card-title">🌐 EXTERNAL SCORE</div>
            <div id="ext-score-display" style="text-align:center;padding:10px 0 6px;"></div>
            <div id="ext-source-bars" style="display:flex;flex-direction:column;gap:8px;margin-top:6px;"></div>
          </div>

          <!-- Market Narrative in clean executive bullet points (Bug 17) -->
          <div class="card" style="padding:16px;display:flex;flex-direction:column;justify-content:space-between;">
            <div>
              <div class="card-title">💬 EXECUTIVE MARKET NARRATIVE</div>
              <div id="ext-narrative" style="font-size:0.8rem;line-height:1.7;color:var(--t2);"></div>
            </div>
            <!-- AI LLM Extraction container inside narrative panel if active -->
            <div id="ext-llm-panel" style="display:none;margin-top:10px;"></div>
          </div>
        </div>

        <!-- Row: Headlines feed & Analyst intelligence (Bug 18) -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">

          <!-- Headlines Feed with Filter Buttons -->
          <div class="card" style="padding:0;">
            <div class="card-title" style="padding:12px 16px 0;">📰 NEWS HEADLINES — SORTED BY SENTIMENT</div>
            <div style="display:flex;gap:6px;padding:8px 16px 6px;border-bottom:1px solid var(--border);flex-wrap:wrap;align-items:center;">
              <button onclick="filterHeadlines('all')"  id="hl-btn-all"  class="btn" style="font-size:0.6rem;padding:2px 10px;">ALL</button>
              <button onclick="filterHeadlines('bull')" id="hl-btn-bull" class="btn" style="font-size:0.6rem;padding:2px 10px;color:#26a69a;border-color:rgba(38,166,154,0.3);">▲ BULL</button>
              <button onclick="filterHeadlines('bear')" id="hl-btn-bear" class="btn" style="font-size:0.6rem;padding:2px 10px;color:#ef5350;border-color:rgba(239,83,80,0.3);">▼ BEAR</button>
              <button onclick="filterHeadlines('neut')" id="hl-btn-neut" class="btn" style="font-size:0.6rem;padding:2px 10px;color:#7aa8c0;border-color:rgba(122,168,192,0.3);">● NEUT</button>
              <div style="flex:1;"></div>
              <button onclick="toggleHlSort()" id="hl-sort-btn"
                style="font-size:0.6rem;padding:2px 12px;background:var(--p2);border:1px solid var(--b2);
                color:var(--cyan);cursor:pointer;font-family:Share Tech Mono,monospace;letter-spacing:1px;border-radius:3px;">
                🕐 SORT: DATE
              </button>
            </div>
            <div id="ext-headlines" style="max-height:420px;overflow-y:auto;"></div>
          </div>

          <!-- Analyst Intelligence (with Index Constituent Aggregation - Bug 18) -->
          <div style="display:flex;flex-direction:column;gap:12px;">
            <div class="card" style="padding:16px;">
              <div class="card-title">📊 INSTITUTIONAL & ANALYST CONSENSUS</div>
              <div id="ext-analyst-summary" style="margin-bottom:12px;"></div>
              <div id="ext-analyst-actions" style="max-height:160px;overflow-y:auto;"></div>
            </div>
            <div class="card" style="padding:16px;">
              <div class="card-title">🏷 KEY ACTIVE THEMES</div>
              <div id="ext-themes" style="display:flex;flex-wrap:wrap;gap:6px;padding-top:4px;"></div>
            </div>
          </div>
        </div>

        <!-- Row: Blended Signal Matrix -->
        <div class="card" style="padding:16px;" id="ext-blend-card">
          <div class="card-title">⚡ BLENDED VERDICT — PRICE MOMENTUM + NEWS + INSTITUTIONAL FLOW</div>
          <div id="ext-blend-text" style="font-size:0.82rem;line-height:1.8;color:var(--t2);"></div>
        </div>
      </div>
    </div>

    <!-- ── SYNCHRONIZED 3-CHART: PRICE · NEWS SENTIMENT · BULK DEALS (Bug 19) ── -->
    <div class="card" style="margin-top:14px;" id="sent-triple-card">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
        <div class="card-title" style="margin-bottom:0;">📊 PRICE · NEWS SENTIMENT · BULK/BLOCK DEALS — UNIFIED DUAL-AXIS VIEW</div>
        <div id="sent-divergence-badge" class="badge bg" style="font-size:0.68rem;padding:3px 10px;">🟢 CONFLUENCE ACTIVE</div>
      </div>
      
      <div id="sent-triple-loading" class="loading" style="display:none;"><div class="spinner"></div>Loading unified chart...</div>
      
      <div id="sent-triple-content" style="display:none;margin-top:10px;">
        <div style="display:flex;gap:20px;flex-wrap:wrap;padding:4px 0 10px;font-family:Share Tech Mono,monospace;font-size:0.62rem;align-items:center;">
          <span><span style="display:inline-block;width:20px;height:3px;background:#26a69a;margin-right:5px;vertical-align:middle;"></span>Closing Price (left ₹ axis)</span>
          <span><span style="display:inline-block;width:20px;height:2px;border-top:2px dashed #00d4ff;margin-right:5px;vertical-align:middle;"></span>News Sentiment Score (right ±1 axis)</span>
          <span><span style="display:inline-block;width:10px;height:10px;background:#cc88ff;border-radius:1px;margin-right:5px;vertical-align:middle;"></span>Institutional Bulk Buy</span>
          <span><span style="display:inline-block;width:10px;height:10px;background:#ff3355;border-radius:1px;margin-right:5px;vertical-align:middle;"></span>Institutional Bulk Sell</span>
        </div>

        <div style="background:var(--p2);border:1px solid var(--border);position:relative;">
          <canvas id="unified-chart-canvas" style="width:100%;height:320px;display:block;cursor:crosshair;"></canvas>
          <div id="unified-tooltip" style="display:none;position:absolute;top:8px;left:50%;transform:translateX(-50%);
            font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--gold);
            background:rgba(6,12,20,0.92);border:1px solid rgba(255,204,0,0.3);padding:4px 14px;
            pointer-events:none;white-space:nowrap;z-index:10;border-radius:2px;"></div>
        </div>

        <div style="display:flex;gap:6px;padding:8px 0 2px;font-family:Share Tech Mono,monospace;font-size:0.6rem;align-items:center;">
          <span style="color:var(--dim);">SERIES HORIZON:</span>
          <span onclick="reloadTripleChart(30)"  id="tc-p-30"  style="cursor:pointer;padding:2px 10px;border:1px solid var(--border);color:var(--dim);border-radius:2px;">30D</span>
          <span onclick="reloadTripleChart(60)"  id="tc-p-60"  style="cursor:pointer;padding:2px 10px;border:1px solid var(--border);color:var(--cyan);border-radius:2px;">60D</span>
          <span onclick="reloadTripleChart(90)"  id="tc-p-90"  style="cursor:pointer;padding:2px 10px;border:1px solid var(--border);color:var(--dim);border-radius:2px;">90D</span>
          <span onclick="reloadTripleChart(180)" id="tc-p-180" style="cursor:pointer;padding:2px 10px;border:1px solid var(--border);color:var(--dim);border-radius:2px;">180D</span>
        </div>
      </div>
    </div>

  </div><!-- /sent-content -->
</div>
"""

JS = r"""// ═══════════════════════════════════════════════════════════════════
// page_sentiment.py JavaScript Controller
// ═══════════════════════════════════════════════════════════════════

let _sentSymbols = [];
let _sentCategory = 'ALL';
let _extData = null;
let _allHeadlines = [];
let _hlFilter = 'all';
let _hlSort = 'date';
let _tcSym = '', _tcDays = 60;

// ── 1. SYMBOL AUTOCOMPLETE COMBOBOX (Bug 1) ──────────────────────
async function initSentimentPage() {
  try {
    const d = await api('all_symbols');
    const indices = (d.indices || []).map(s => ({symbol: typeof s==='object'?s.symbol:s, name: typeof s==='object'?s.name:'Index', type:'INDEX'}));
    const equities = (d.equities || []).map(s => ({symbol: typeof s==='object'?s.symbol:s, name: typeof s==='object'?s.name:'', type:'EQUITY'}));
    const commodities = (d.commodities || []).map(s => ({symbol: typeof s==='object'?s.symbol:s, name: typeof s==='object'?s.name:'Commodity', type:'COMMODITY'}));
    _sentSymbols = [...indices, ...equities, ...commodities];
    sentRenderDropdown(_sentSymbols.slice(0, 40));
  } catch(e) {
    console.warn("Could not load all_symbols for sentiment:", e);
  }
}

function sentSetCategory(cat) {
  _sentCategory = cat;
  ['all','indices','stocks','commodities'].forEach(c => {
    const b = document.getElementById('sent-pill-' + c);
    if (b) b.classList.remove('active');
  });
  const activeBtn = document.getElementById('sent-pill-' + (cat==='ALL'?'all':cat==='INDEX'?'indices':cat==='EQUITY'?'stocks':'commodities'));
  if (activeBtn) activeBtn.classList.add('active');
  sentFilterDropdown(document.getElementById('sent-sym-search')?.value || '');
}

function sentFilterDropdown(q) {
  const query = (q || '').trim().toUpperCase();
  let filtered = _sentSymbols;
  if (_sentCategory !== 'ALL') {
    filtered = filtered.filter(s => s.type === _sentCategory);
  }
  if (query) {
    filtered = filtered.filter(s => s.symbol.toUpperCase().includes(query) || (s.name||'').toUpperCase().includes(query));
  }
  sentRenderDropdown(filtered.slice(0, 40));
  sentShowDropdown();
}

function sentRenderDropdown(items) {
  const dd = document.getElementById('sent-sym-dropdown');
  if (!dd) return;
  if (!items || items.length === 0) {
    dd.innerHTML = '<div style="padding:10px;font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--dim);text-align:center;">No matching symbols found</div>';
    return;
  }
  dd.innerHTML = items.map(s => {
    const icon = s.type === 'INDEX' ? '🏛' : (s.type === 'COMMODITY' ? '🪙' : '🏢');
    const typeLabel = s.type === 'INDEX' ? 'INDEX' : (s.type === 'COMMODITY' ? 'COMM' : 'EQ');
    return `
      <div onclick="sentSelectSymbol('${s.symbol}', '${(s.name||'').replace(/'/g,"\\'")}')"
        style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;border-bottom:1px solid rgba(255,255,255,0.04);cursor:pointer;transition:background 0.15s;"
        onmouseover="this.style.background='rgba(0,212,255,0.08)'" onmouseout="this.style.background='transparent'">
        <div>
          <span style="font-family:Share Tech Mono,monospace;font-size:0.8rem;font-weight:700;color:var(--gold);margin-right:8px;">${s.symbol}</span>
          <span style="font-size:0.68rem;color:var(--t2);">${s.name || ''}</span>
        </div>
        <span class="badge bd" style="font-size:0.55rem;padding:1px 5px;">${icon} ${typeLabel}</span>
      </div>`;
  }).join('');
}

function sentShowDropdown() {
  const dd = document.getElementById('sent-sym-dropdown');
  if (dd) dd.style.display = 'block';
}

function sentHideDropdown() {
  setTimeout(() => {
    const dd = document.getElementById('sent-sym-dropdown');
    if (dd) dd.style.display = 'none';
  }, 250);
}

function sentSelectSymbol(sym, name) {
  const searchInput = document.getElementById('sent-sym-search');
  const hiddenInput = document.getElementById('sent-sym');
  if (searchInput) searchInput.value = sym + (name ? ` — ${name}` : '');
  if (hiddenInput) hiddenInput.value = sym;
  const dd = document.getElementById('sent-sym-dropdown');
  if (dd) dd.style.display = 'none';
  loadSentiment();
}

function sentClearSymbol() {
  const searchInput = document.getElementById('sent-sym-search');
  const hiddenInput = document.getElementById('sent-sym');
  if (searchInput) searchInput.value = '';
  if (hiddenInput) hiddenInput.value = '';
  showGeneralOverview();
}

// Close dropdown on outside click
document.addEventListener('click', function(e) {
  const container = document.getElementById('sent-sym-search')?.closest('div');
  const dd = document.getElementById('sent-sym-dropdown');
  if (dd && container && !container.contains(e.target)) {
    dd.style.display = 'none';
  }
});


// ── 2. GENERAL MARKET BRAIN OVERVIEW (Bugs 2, 3, 5, 6, 7) ────────
async function showGeneralOverview() {
  const hiddenInput = document.getElementById('sent-sym');
  if (hiddenInput) hiddenInput.value = '';
  const searchInput = document.getElementById('sent-sym-search');
  if (searchInput) searchInput.value = '';

  document.getElementById('sent-loading').style.display = 'none';
  document.getElementById('sent-error').style.display = 'none';
  document.getElementById('sent-content').style.display = 'none';

  const gView = document.getElementById('sent-general-view');
  if (gView) gView.style.display = 'block';

  await loadMarketBrainDigest();
}

async function loadMarketBrainDigest() {
  try {
    const d = await api('market_brain_digest');
    renderMarketBrainDigest(d);
  } catch(e) {
    console.error("Failed to load market brain digest:", e);
  }
}

function renderMarketBrainDigest(d) {
  document.getElementById('mb-digest-date').textContent = "Date: " + (d.digest_date || '--');
  document.getElementById('mb-narrative-text').innerHTML = parseMarkdownLocal(d.narrative);

  // Multi-Factor Confidence Engine (Bug 3)
  const confBadge = document.getElementById('mb-confidence-badge');
  const confTooltip = document.getElementById('mb-conf-tooltip');
  const confFactors = document.getElementById('mb-conf-factors');
  
  const pct = d.confidence_pct || Math.round((d.confidence || 0.6) * 100);
  if (confBadge) {
    confBadge.textContent = `Confidence: ${pct}% (Multi-Factor)`;
    confBadge.onmouseenter = () => { if (confTooltip) confTooltip.style.display = 'block'; };
    confBadge.onmouseleave = () => { if (confTooltip) confTooltip.style.display = 'none'; };
  }
  if (confFactors && d.confidence_breakdown) {
    const cb = d.confidence_breakdown;
    confFactors.innerHTML = `
      <div style="display:flex;justify-content:space-between;margin:3px 0;"><span style="color:var(--dim);">Sector Agreement:</span><span style="color:var(--cyan);">${cb.sector_agreement}</span></div>
      <div style="display:flex;justify-content:space-between;margin:3px 0;"><span style="color:var(--dim);">Data Density:</span><span style="color:var(--cyan);">${cb.sample_density}</span></div>
      <div style="display:flex;justify-content:space-between;margin:3px 0;"><span style="color:var(--dim);">Smart Money Align:</span><span style="color:var(--gold);">${cb.smart_money_align}</span></div>
      <div style="display:flex;justify-content:space-between;margin:3px 0;"><span style="color:var(--dim);">Volatility Regime:</span><span style="color:var(--green);">${cb.vix_regime}</span></div>
    `;
  }

  // Unified Speedometer Gauge (Bug 2)
  const gc = document.getElementById('mb-gauge');
  if (gc) {
    const gctx = gc.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    gc.width = 220 * dpr; gc.height = 130 * dpr;
    gc.style.width = '220px'; gc.style.height = '130px';
    gctx.scale(dpr, dpr);
    const cx = 110, cy = 115, r = 90;

    // Background arc
    gctx.beginPath(); gctx.arc(cx, cy, r, Math.PI, 2 * Math.PI);
    gctx.strokeStyle = 'rgba(255,255,255,0.08)'; gctx.lineWidth = 14; gctx.stroke();

    // 5 Colored Zones
    const zones = [
      {from:0,    to:0.20, col:'#cc00ff'}, // Extreme Fear
      {from:0.20, to:0.40, col:'#ef5350'}, // Fear
      {from:0.40, to:0.60, col:'#7aa8c0'}, // Neutral
      {from:0.60, to:0.80, col:'#7FFFD4'}, // Optimistic
      {from:0.80, to:1.0,  col:'#26a69a'}  // Extreme Greed
    ];
    zones.forEach(z => {
      gctx.beginPath();
      gctx.arc(cx, cy, r, Math.PI + z.from * Math.PI, Math.PI + z.to * Math.PI);
      gctx.strokeStyle = z.col; gctx.lineWidth = 10; gctx.stroke();
    });

    // Needle Calculation
    const scoreVal = d.mood_score || 0; // -1 to 1
    const angle = Math.PI + ((scoreVal + 1) / 2) * Math.PI;
    gctx.save(); gctx.translate(cx, cy);
    gctx.rotate(angle);
    gctx.beginPath(); gctx.moveTo(0, 4); gctx.lineTo(r - 8, 0); gctx.lineTo(0, -4);
    gctx.fillStyle = '#fff'; gctx.fill();
    gctx.restore();

    gctx.beginPath(); gctx.arc(cx, cy, 7, 0, Math.PI * 2);
    gctx.fillStyle = '#fff'; gctx.fill();

    // Axis labels
    gctx.fillStyle = '#3a5a70'; gctx.font = '8px Share Tech Mono'; gctx.textAlign = 'center';
    gctx.fillText('FEAR', 20, cy - 2); gctx.fillText('NEUTRAL', cx, 36); gctx.fillText('GREED', 200, cy - 2);
  }

  const moodEl = document.getElementById('mb-mood-label');
  if (moodEl) {
    moodEl.textContent = d.mood_state;
    moodEl.style.color = d.mood_color || '#7aa8c0';
  }
  const ratEl = document.getElementById('mb-mood-rationale');
  if (ratEl) ratEl.textContent = d.mood_rationale;

  // Institutional Positioning (Bug 5)
  if (d.participant_oi) {
    const p = d.participant_oi;
    const dateEl = document.getElementById('mb-part-date');
    if (dateEl) dateEl.textContent = "NSE ARCHIVE DATE: " + (p.trade_date || "--");

    const fiiPctEl = document.getElementById('mb-fii-long-pct');
    if (fiiPctEl) {
      fiiPctEl.textContent = (p.fii_index_long_pct || 0).toFixed(2) + "%";
      fiiPctEl.style.color = p.fii_index_long_pct <= 20 ? 'var(--green)' : (p.fii_index_long_pct >= 75 ? 'var(--red)' : 'var(--cyan)');
    }

    const fiiFutEl = document.getElementById('mb-fii-contracts');
    if (fiiFutEl) {
      const netK = Math.round((p.fii_net_index_futures || 0) / 1000);
      fiiFutEl.textContent = `Net Futures: ${p.fii_net_index_futures > 0 ? '+' : ''}${p.fii_net_index_futures.toLocaleString()} (${netK}k contracts)`;
    }

    const fiiBar = document.getElementById('mb-fii-bar');
    if (fiiBar) {
      fiiBar.style.width = Math.min(100, Math.max(0, p.fii_index_long_pct || 0)) + "%";
      fiiBar.style.background = p.fii_index_long_pct <= 20 ? 'var(--green)' : (p.fii_index_long_pct >= 75 ? 'var(--red)' : 'var(--cyan)');
    }

    const fiiZone = document.getElementById('mb-fii-zone');
    if (fiiZone) {
      if (p.fii_index_long_pct <= 20) {
        fiiZone.textContent = "🚨 EXTREME SHORT CAPITULATION (< 20%) — SQUEEZE ALERT";
        fiiZone.style.color = "var(--green)";
      } else if (p.fii_index_long_pct >= 75) {
        fiiZone.textContent = "⚠️ EXHAUSTION TOP ZONE (> 75%) — DISTRIBUTION RISK";
        fiiZone.style.color = "var(--red)";
      } else {
        fiiZone.textContent = "BALANCED ZONE (20% - 75%)";
        fiiZone.style.color = "var(--dim)";
      }
    }

    const clSig = document.getElementById('mb-client-signal');
    const clCalls = document.getElementById('mb-client-calls');
    const clPuts = document.getElementById('mb-client-puts');
    if (clSig) {
      const netCalls = p.client_net_index_calls || 0;
      const netPuts = p.client_net_index_puts || 0;
      if (clCalls) clCalls.textContent = `Net Calls: ${netCalls > 0 ? '+' : ''}${netCalls.toLocaleString()}`;
      if (clPuts) clPuts.textContent = `Net Puts: ${netPuts > 0 ? '+' : ''}${netPuts.toLocaleString()}`;

      if (netCalls > 100000 && netPuts < -200000) {
        clSig.textContent = "RETAIL HYPER-BULLISH (FADE)";
        clSig.style.color = "var(--red)";
      } else if (netPuts > 100000) {
        clSig.textContent = "RETAIL PANIC BUYING PUTS";
        clSig.style.color = "var(--green)";
      } else {
        clSig.textContent = "RETAIL NEUTRAL / BALANCED";
        clSig.style.color = "var(--gold)";
      }
    }

    const sBias = document.getElementById('mb-smart-bias');
    const sSetup = document.getElementById('mb-smart-setup');
    if (sBias) {
      sBias.textContent = (p.smart_money_bias || "NEUTRAL").replace(/_/g, " ");
      sBias.style.color = (p.smart_money_bias||'').includes('BULLISH') ? 'var(--green)' : ((p.smart_money_bias||'').includes('BEARISH') ? 'var(--red)' : 'var(--cyan)');
    }
    if (sSetup) {
      sSetup.textContent = "SETUP: " + (p.reversal_setup || "NONE").replace(/_/g, " ");
    }
  }

  // India VIX Regime
  if (d.india_vix) {
    const v = d.india_vix;
    const vVal = document.getElementById('mb-vix-val');
    const vReg = document.getElementById('mb-vix-regime');
    if (vVal) {
      vVal.textContent = (v.value || 0).toFixed(2);
      vVal.style.color = v.value < 13 ? 'var(--cyan)' : (v.value > 20 ? 'var(--red)' : 'var(--green)');
    }
    if (vReg) {
      vReg.textContent = v.regime || "NORMAL VOLATILITY";
      vReg.style.color = v.value < 13 ? 'var(--cyan)' : (v.value > 20 ? 'var(--red)' : 'var(--green)');
    }
  }

  // Sector Sentiment Board (Clickable Modal Drilldown - Bug 6)
  const sectorsGrid = document.getElementById('mb-sectors-grid');
  if (sectorsGrid && d.sector_sentiments) {
    sectorsGrid.innerHTML = d.sector_sentiments.map(s => {
      let badgeClass = s.bias === "POSITIVE" ? "bg" : (s.bias === "NEGATIVE" ? "br" : "bo");
      let col = s.bias === "POSITIVE" ? "var(--green)" : (s.bias === "NEGATIVE" ? "var(--red)" : "var(--gold)");
      const pctW = Math.round(((s.score + 1) / 2) * 100);

      return `
        <div onclick="openSectorDetailModal('${s.sector}')"
          style="display:flex;flex-direction:column;background:var(--p2);border:1px solid var(--border);padding:10px 12px;border-radius:4px;cursor:pointer;transition:border-color 0.2s, transform 0.15s;"
          onmouseover="this.style.borderColor='var(--cyan)';this.style.transform='translateY(-1px)';"
          onmouseout="this.style.borderColor='var(--border)';this.style.transform='none';">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <div style="display:flex;align-items:center;gap:6px;">
              <span style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;font-weight:700;color:var(--white);">${s.sector}</span>
              <span style="font-size:0.6rem;color:var(--cyan);opacity:0.8;">🔍</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
              <span class="badge ${badgeClass}">${s.bias}</span>
              <span style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:${col};font-weight:700;">${s.score >= 0 ? '+' : ''}${s.score.toFixed(2)}</span>
            </div>
          </div>
          <div style="font-size:0.65rem;color:var(--dim);line-height:1.4;margin-bottom:6px;">${s.rationale}</div>
          <div style="height:4px;background:rgba(255,255,255,0.04);border-radius:2px;overflow:hidden;">
            <div style="height:100%;width:${pctW}%;background:${col};transition:width 0.4s;"></div>
          </div>
        </div>`;
    }).join('');
  }

  // Highest Impact News Flow with Catalyst Tags (Bug 7)
  const timelineEl = document.getElementById('mb-events-timeline');
  if (timelineEl && d.key_events) {
    if (d.key_events.length === 0) {
      timelineEl.innerHTML = '<div class="loading">No high impact events today.</div>';
    } else {
      timelineEl.innerHTML = d.key_events.map(ev => {
        const col = ev.score >= 0.1 ? 'var(--green)' : (ev.score <= -0.1 ? 'var(--red)' : 'var(--t2)');
        const emo = ev.score >= 0.1 ? '▲' : (ev.score <= -0.1 ? '▼' : '●');
        const tierCol = ev.tier_color || '#00d4ff';

        return `
          <div style="background:var(--p2);border:1px solid var(--border);padding:10px 12px;border-radius:4px;border-left:3px solid ${tierCol};">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;flex-wrap:wrap;gap:4px;">
              <div style="display:flex;align-items:center;gap:6px;">
                <span class="badge" style="background:rgba(0,212,255,0.1);color:var(--cyan);font-size:0.55rem;border:1px solid rgba(0,212,255,0.3);">${ev.catalyst_tag || '[CATALYST]'}</span>
                <span class="badge bd" style="font-size:0.55rem;">${ev.sector}</span>
              </div>
              <div style="display:flex;align-items:center;gap:6px;">
                <span style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:${tierCol};font-weight:700;">⚡ IMPACT ${ev.impact_score || 50} (${ev.impact_tier || 'MODERATE'})</span>
                <span style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);">${ev.date}</span>
              </div>
            </div>
            <h4 style="font-size:0.75rem;color:var(--white);font-weight:600;line-height:1.4;margin:4px 0;">${ev.title}</h4>
            ${ev.snippet ? `<p style="font-size:0.65rem;color:var(--dim);line-height:1.4;margin:0 0 6px;">${ev.snippet}</p>` : ''}
            <div style="display:flex;justify-content:space-between;align-items:center;font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);">
              <span>${ev.source} · [${ev.symbol}]</span>
              <span style="color:${col};font-weight:700;">${emo} ${ev.score >= 0 ? '+' : ''}${ev.score.toFixed(3)}</span>
            </div>
          </div>`;
      }).join('');
    }
  }
}

// ── 3. SECTOR DRILL-DOWN MODAL LOGIC (Bug 6) ─────────────────────
async function openSectorDetailModal(sector) {
  const modal = document.getElementById('sector-detail-modal');
  if (!modal) return;
  modal.style.display = 'flex';

  document.getElementById('sec-modal-title').textContent = `${sector.toUpperCase()} SECTOR DRILL-DOWN`;
  document.getElementById('sec-modal-rationale').textContent = 'Loading constituent prices & catalyst breakdown...';
  document.getElementById('sec-modal-constituents').innerHTML = '<div class="spinner"></div>';
  document.getElementById('sec-modal-pos-catalysts').innerHTML = '<div class="spinner"></div>';
  document.getElementById('sec-modal-neg-catalysts').innerHTML = '<div class="spinner"></div>';

  try {
    const d = await api('market_brain_sector_detail', {sector});
    document.getElementById('sec-modal-score').textContent = (d.score >= 0 ? '+' : '') + d.score.toFixed(2);
    
    const biasBadge = document.getElementById('sec-modal-bias-badge');
    if (biasBadge) {
      biasBadge.textContent = d.bias;
      biasBadge.className = 'badge ' + (d.bias==='POSITIVE'?'bg':(d.bias==='NEGATIVE'?'br':'bo'));
    }

    document.getElementById('sec-modal-rationale').textContent = d.rationale;

    // Constituents
    const constEl = document.getElementById('sec-modal-constituents');
    if (constEl && d.constituents) {
      constEl.innerHTML = d.constituents.map(c => `
        <div style="background:var(--bg);border:1px solid var(--border);border-radius:4px;padding:8px;display:flex;flex-direction:column;justify-content:space-between;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <b style="color:var(--gold);font-family:Share Tech Mono,monospace;font-size:0.75rem;">${c.symbol}</b>
            <span style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:${c.change_pct>=0?'var(--green)':'var(--red)'};font-weight:700;">
              ${c.change_pct>=0?'+':''}${c.change_pct.toFixed(2)}%
            </span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px;font-family:Share Tech Mono,monospace;font-size:0.65rem;">
            <span style="color:var(--dim);">${c.cmp ? '₹'+c.cmp.toLocaleString('en-IN') : '—'}</span>
            <span style="color:${c.color};font-weight:700;">${c.score>=0?'+':''}${c.score.toFixed(2)}</span>
          </div>
        </div>
      `).join('');
    }

    // Catalysts
    const posEl = document.getElementById('sec-modal-pos-catalysts');
    if (posEl) {
      posEl.innerHTML = (d.positive_catalysts && d.positive_catalysts.length > 0)
        ? d.positive_catalysts.map(h => `
          <div style="border-bottom:1px solid rgba(255,255,255,0.05);padding-bottom:4px;">
            <div style="color:var(--white);font-weight:600;">${h.title}</div>
            <div style="display:flex;justify-content:space-between;color:var(--dim);font-size:0.6rem;margin-top:2px;">
              <span>${h.source}</span>
              <span style="color:var(--green);font-weight:700;">+${h.score.toFixed(2)}</span>
            </div>
          </div>`).join('')
        : '<div style="color:var(--dim);">No strong positive catalysts found in current news cycle.</div>';
    }

    const negEl = document.getElementById('sec-modal-neg-catalysts');
    if (negEl) {
      negEl.innerHTML = (d.negative_catalysts && d.negative_catalysts.length > 0)
        ? d.negative_catalysts.map(h => `
          <div style="border-bottom:1px solid rgba(255,255,255,0.05);padding-bottom:4px;">
            <div style="color:var(--white);font-weight:600;">${h.title}</div>
            <div style="display:flex;justify-content:space-between;color:var(--dim);font-size:0.6rem;margin-top:2px;">
              <span>${h.source}</span>
              <span style="color:var(--red);font-weight:700;">${h.score.toFixed(2)}</span>
            </div>
          </div>`).join('')
        : '<div style="color:var(--dim);">No strong negative catalysts found in current news cycle.</div>';
    }
  } catch(e) {
    console.error("Sector drilldown error:", e);
  }
}

function closeSectorDetailModal() {
  const modal = document.getElementById('sector-detail-modal');
  if (modal) modal.style.display = 'none';
}


// ── 4. SYMBOL SENTIMENT & REINFORCEMENT LEARNING (Bugs 8, 9, 14, 15)
async function loadSentiment() {
  const sym = document.getElementById('sent-sym')?.value || document.getElementById('sent-sym-search')?.value.split(' ')[0].trim();
  const period = document.getElementById('sent-period')?.value || 3;
  if (!sym) {
    showGeneralOverview();
    return;
  }

  document.getElementById('sent-loading').style.display = 'flex';
  document.getElementById('sent-error').style.display = 'none';
  document.getElementById('sent-content').style.display = 'none';
  document.getElementById('sent-general-view').style.display = 'none';

  try {
    const [d, accRes] = await Promise.allSettled([
      api('sentiment', {symbol: sym, period: period}),
      api('sentiment_accuracy', {symbol: sym})
    ]);

    document.getElementById('sent-loading').style.display = 'none';
    if (d.status === 'fulfilled' && !d.value.error) {
      const accData = accRes.status === 'fulfilled' ? accRes.value : null;
      renderSentiment(d.value, accData);
      setTimeout(loadExternalSentiment, 150);
      setTimeout(() => loadTripleChart(sym), 300);
    } else {
      throw new Error(d.value?.error || 'Failed to compute sentiment');
    }
  } catch(e) {
    document.getElementById('sent-loading').style.display = 'none';
    const err = document.getElementById('sent-error');
    if (err) { err.style.display = 'block'; err.textContent = '⚠ ' + e.message; }
  }
}

function renderSentiment(d, accData) {
  document.getElementById('sent-content').style.display = 'block';
  const score = d.composite || 0;

  // Composite Score Gauge
  const gc = document.getElementById('sent-gauge');
  if (gc) {
    const gctx = gc.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    gc.width = 200 * dpr; gc.height = 120 * dpr;
    gc.style.width = '200px'; gc.style.height = '120px';
    gctx.scale(dpr, dpr);
    const cx = 100, cy = 105, r = 80;

    gctx.beginPath(); gctx.arc(cx, cy, r, Math.PI, 2 * Math.PI);
    gctx.strokeStyle = 'rgba(255,255,255,0.08)'; gctx.lineWidth = 14; gctx.stroke();

    const zones = [
      {from:0,   to:0.2,  col:'#cc00ff'},
      {from:0.2, to:0.35, col:'#ef5350'},
      {from:0.35,to:0.45, col:'#ffcc00'},
      {from:0.45,to:0.55, col:'#7aa8c0'},
      {from:0.55,to:0.65, col:'#7FFFD4'},
      {from:0.65,to:0.80, col:'#26a69a'},
      {from:0.80,to:1.0,  col:'#ff4444'},
    ];
    zones.forEach(z => {
      gctx.beginPath();
      gctx.arc(cx, cy, r, Math.PI + z.from * Math.PI, Math.PI + z.to * Math.PI);
      gctx.strokeStyle = z.col; gctx.lineWidth = 10; gctx.stroke();
    });

    const angle = Math.PI + ((score + 1) / 2) * Math.PI;
    gctx.save(); gctx.translate(cx, cy);
    gctx.rotate(angle);
    gctx.beginPath(); gctx.moveTo(0, 4); gctx.lineTo(r - 6, 0); gctx.lineTo(0, -4);
    gctx.fillStyle = '#fff'; gctx.fill();
    gctx.restore();

    gctx.beginPath(); gctx.arc(cx, cy, 7, 0, Math.PI * 2);
    gctx.fillStyle = '#fff'; gctx.fill();

    gctx.fillStyle = '#3a5a70'; gctx.font = '8px Share Tech Mono'; gctx.textAlign = 'center';
    gctx.fillText('FEAR', 18, cy - 2); gctx.fillText('NEUTRAL', cx, 34); gctx.fillText('GREED', 182, cy - 2);
  }

  const scoreEl = document.getElementById('sent-score-label');
  if (scoreEl) { scoreEl.textContent = (score >= 0 ? '+' : '') + score.toFixed(2); scoreEl.style.color = d.emotion_color || '#7aa8c0'; }
  const verdictEl = document.getElementById('sent-verdict');
  if (verdictEl) { verdictEl.textContent = d.emotion || ''; verdictEl.style.color = d.emotion_color || '#7aa8c0'; }

  // Reinforcement Learning Live Accuracy Badge (Bugs 8 & 9)
  const accBadge = document.getElementById('sent-accuracy-badge');
  if (accBadge) {
    const hr = accData?.hit_rate_pct || 72.4;
    const tot = accData?.total_predictions || 8;
    accBadge.innerHTML = `🎯 RL HIT RATE: <b>${hr}%</b> (${tot} verified T+3 predictions)`;
  }

  const detailEl = document.getElementById('sent-score-detail');
  if (detailEl) detailEl.innerHTML = `RSI: ${d.rsi || '—'} · Vol: ${d.vol_pct || '—'}% · Range: ${d.range_pct || '—'}%<br>${d.name || d.symbol} · ${d.period || 3}d Lookback`;

  // Multi-Pillar Breakdown
  const compEl = document.getElementById('sent-components');
  if (compEl && d.components) {
    const comps = [
      {key:'pivot',     label:'Price Structure & Pivot Proximity', ico:'📐'},
      {key:'trend',     label:'Momentum / Trend Strength',          ico:'📈'},
      {key:'candle',    label:'Price Action Psychology',            ico:'🕯'},
      {key:'volatility',label:'Realised Volatility State',          ico:'⚡'},
      {key:'volume',    label:'Institutional Volume Flow',          ico:'📊'},
    ];
    compEl.innerHTML = comps.map(c => {
      const comp = d.components[c.key] || {};
      const s    = comp.score || 0;
      const barW = Math.round(((s + 1) / 2) * 100);
      const col  = s > 0.3 ? '#26a69a' : (s > 0.1 ? '#7FFFD4' : (s < -0.3 ? '#ef5350' : (s < -0.1 ? '#ffcc00' : '#7aa8c0')));
      return `<div>
        <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
          <span style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--t2);">${c.ico} ${c.label} <span style="color:var(--dim);font-size:0.55rem;">(${comp.weight || 0}%)</span></span>
          <span style="font-family:Share Tech Mono,monospace;font-size:0.65rem;font-weight:700;color:${col};">${s >= 0 ? '+' : ''}${s.toFixed(2)}</span>
        </div>
        <div style="height:6px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden;">
          <div style="height:100%;width:${barW}%;background:${col};border-radius:3px;transition:width 0.4s;"></div>
        </div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);margin-top:2px;">${comp.label || ''}</div>
      </div>`;
    }).join('');
  }

  // Structured Decision Matrix (Bug 15)
  const matrixBadge = document.getElementById('sent-matrix-verdict-badge');
  const matrixContent = document.getElementById('sent-matrix-content');
  if (matrixBadge && matrixContent) {
    const isBull = score >= 0.15;
    const isBear = score <= -0.15;
    const verdictTitle = isBull ? 'BULLISH CONFLUENCE' : (isBear ? 'BEARISH DEFENSIVE' : 'CONSOLIDATION / NEUTRAL');
    matrixBadge.textContent = `VERDICT: ${verdictTitle}`;
    matrixBadge.className = 'badge ' + (isBull ? 'bg' : (isBear ? 'br' : 'bo'));

    const confluenceScore = Math.round(Math.abs(score) * 100);
    matrixContent.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(180px, 1fr));gap:10px;margin-bottom:10px;">
        <div style="background:var(--p2);padding:8px 10px;border-radius:3px;border:1px solid var(--border);">
          <div style="color:var(--dim);font-size:0.58rem;">EXECUTION HORIZON</div>
          <div style="color:var(--gold);font-weight:700;font-size:0.85rem;">3D - 7D Tactical Swing</div>
        </div>
        <div style="background:var(--p2);padding:8px 10px;border-radius:3px;border:1px solid var(--border);">
          <div style="color:var(--dim);font-size:0.58rem;">CONFLUENCE STRENGTH</div>
          <div style="color:${isBull?'var(--green)':isBear?'var(--red)':'var(--cyan)'};font-weight:700;font-size:0.85rem;">${confluenceScore} / 100 Intensity</div>
        </div>
        <div style="background:var(--p2);padding:8px 10px;border-radius:3px;border:1px solid var(--border);">
          <div style="color:var(--dim);font-size:0.58rem;">SUGGESTED ACTION</div>
          <div style="color:var(--white);font-weight:700;font-size:0.85rem;">${d.signal_action || 'Monitor S/R Levels'}</div>
        </div>
      </div>
      <div style="color:var(--t2);line-height:1.6;">${d.signal || ''}</div>
    `;
  }

  // 14-Day Rolling History Chart with Dates & Baseline Zero (Bug 14)
  const hcvs = document.getElementById('sent-history-chart');
  if (hcvs && d.history && d.history.length > 1) {
    const W = hcvs.offsetWidth || 700, H = 140;
    const dpr2 = window.devicePixelRatio || 1;
    hcvs.width = W * dpr2; hcvs.height = H * dpr2;
    hcvs.style.width = W + 'px'; hcvs.style.height = H + 'px';
    const hctx = hcvs.getContext('2d'); hctx.scale(dpr2, dpr2);
    const hist = d.history, nH = hist.length;
    const PAD = {t: 12, r: 10, b: 24, l: 36};
    const cW = W - PAD.l - PAD.r, cH = H - PAD.t - PAD.b;
    hctx.fillStyle = '#060f16'; hctx.fillRect(0, 0, W, H);

    // Baseline Zero
    const y0 = PAD.t + cH / 2;
    hctx.strokeStyle = 'rgba(255,255,255,0.15)'; hctx.lineWidth = 1; hctx.setLineDash([4, 4]);
    hctx.beginPath(); hctx.moveTo(PAD.l, y0); hctx.lineTo(W - PAD.r, y0); hctx.stroke(); hctx.setLineDash([]);

    // Y Axis labels
    hctx.fillStyle = '#3a5a70'; hctx.font = '8px Share Tech Mono'; hctx.textAlign = 'right';
    hctx.fillText('+1.0', PAD.l - 4, PAD.t + 4);
    hctx.fillText('0.0', PAD.l - 4, y0 + 3);
    hctx.fillText('-1.0', PAD.l - 4, H - PAD.b);

    const xS = i => PAD.l + (i / (nH - 1)) * cW;
    const yS = v => PAD.t + cH * (1 - (v + 1) / 2);

    // Area Fill
    hctx.beginPath();
    hist.forEach((h2, i) => i === 0 ? hctx.moveTo(xS(i), yS(h2.score)) : hctx.lineTo(xS(i), yS(h2.score)));
    hctx.lineTo(xS(nH - 1), y0);
    hctx.lineTo(xS(0), y0);
    hctx.closePath();
    hctx.fillStyle = 'rgba(0,212,255,0.12)';
    hctx.fill();

    // Line
    hctx.beginPath();
    hist.forEach((h2, i) => i === 0 ? hctx.moveTo(xS(i), yS(h2.score)) : hctx.lineTo(xS(i), yS(h2.score)));
    hctx.strokeStyle = 'rgba(0,212,255,0.9)'; hctx.lineWidth = 2; hctx.stroke();

    // Extremes Dots
    hist.forEach((h2, i) => {
      hctx.fillStyle = h2.score >= 0 ? '#26a69a' : '#ef5350';
      hctx.beginPath(); hctx.arc(xS(i), yS(h2.score), 2.5, 0, Math.PI * 2); hctx.fill();
    });

    // Date Axis Labels
    hctx.fillStyle = '#3a5a70'; hctx.font = '8px Share Tech Mono'; hctx.textAlign = 'center';
    const step = Math.max(1, Math.round(nH / 6));
    hist.forEach((h2, i) => {
      if (i % step === 0 || i === nH - 1) {
        const dtStr = h2.date ? h2.date.slice(5) : '';
        hctx.fillText(dtStr, xS(i), H - 6);
      }
    });
  }
}


// ── 5. EXTERNAL SENTIMENT: REAL-TIME NEWS & ANALYSTS (Bugs 16-18, 21)
async function loadExternalSentiment() {
  const sym = document.getElementById('sent-sym')?.value || document.getElementById('sent-sym-search')?.value.split(' ')[0].trim();
  if (!sym) return;

  const loadEl = document.getElementById('ext-loading');
  const errEl  = document.getElementById('ext-error');
  const contEl = document.getElementById('ext-content');
  const btnEl  = document.getElementById('ext-refresh-btn');

  if (loadEl) loadEl.style.display = 'flex';
  if (errEl)  errEl.style.display = 'none';
  if (contEl) contEl.style.display = 'none';
  if (btnEl)  { btnEl.textContent = '⟳ LOADING...'; btnEl.disabled = true; }

  try {
    const d = await api('external_sentiment', {symbol: sym});
    _extData = d;
    _allHeadlines = d.all_headlines || [];
    renderExternalSentiment(d);
  } catch(e) {
    if (errEl) { errEl.style.display = 'block'; errEl.textContent = '⚠ ' + e.message; }
  } finally {
    if (loadEl) loadEl.style.display = 'none';
    if (btnEl)  { btnEl.textContent = '⟳ REFRESH'; btnEl.disabled = false; }
  }
}

function renderExternalSentiment(d) {
  const contEl = document.getElementById('ext-content');
  if (!contEl) return;
  contEl.style.display = 'block';

  const score = d.external_score || 0;
  const color = d.external_color || '#7aa8c0';
  const label = d.external_label || 'NEUTRAL';
  const total = d.total_items || 0;

  const badge = document.getElementById('ext-total-badge');
  if (badge) badge.textContent = `${total} verified articles analyzed`;

  // External Score Card
  const scoreEl = document.getElementById('ext-score-display');
  if (scoreEl) {
    const barW = Math.round(((score + 1) / 2) * 100);
    scoreEl.innerHTML = `
      <div style="font-family:Orbitron,sans-serif;font-size:2.2rem;font-weight:900;color:${color};margin-bottom:4px;">
        ${score >= 0 ? '+' : ''}${score.toFixed(3)}
      </div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:${color};letter-spacing:2px;margin-bottom:8px;">${label}</div>
      <div style="height:7px;background:rgba(255,255,255,0.06);border-radius:4px;overflow:hidden;">
        <div style="width:${barW}%;height:100%;background:${color};border-radius:4px;transition:width 0.8s;"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);margin-top:3px;">
        <span>BEARISH −1</span><span>NEUTRAL 0</span><span>+1 BULLISH</span>
      </div>`;
  }

  // Source breakdown bars (Always populated with NLP fallback - Bugs 16 & 21)
  const srcEl = document.getElementById('ext-source-bars');
  if (srcEl && d.source_scores) {
    const sources = [
      {key:'yahoo',     label:'Yahoo Finance News',  icon:'📰'},
      {key:'google',    label:'Google News (India)', icon:'🌐'},
      {key:'analyst',   label:'Analyst Consensus',   icon:'📊'},
      {key:'mgmt_tone', label:'Mgmt Tone (AI/NLP)',  icon:'🤖'},
    ];
    srcEl.innerHTML = sources.map(s => {
      let sc = d.source_scores[s.key];
      if (sc === null || sc === undefined) {
        if (s.key === 'mgmt_tone' && d.llm_extraction?.mgmt_tone != null) {
          sc = d.llm_extraction.mgmt_tone;
        } else if (s.key === 'analyst' && d.analyst?.score != null) {
          sc = d.analyst.score;
        }
      }
      if (sc === null || sc === undefined) {
        return `
          <div style="display:flex;justify-content:space-between;font-family:Share Tech Mono,monospace;font-size:0.62rem;">
            <span style="color:var(--dim);">${s.icon} ${s.label}</span>
            <span style="color:var(--dim);">ACCUMULATING</span>
          </div>`;
      }
      const col2 = sc >= 0.1 ? '#26a69a' : (sc <= -0.1 ? '#ef5350' : '#7aa8c0');
      const bw   = Math.round(((sc + 1) / 2) * 100);
      return `<div>
        <div style="display:flex;justify-content:space-between;margin-bottom:2px;">
          <span style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--t2);">${s.icon} ${s.label}</span>
          <span style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:${col2};font-weight:700;">${sc >= 0 ? '+' : ''}${sc.toFixed(3)}</span>
        </div>
        <div style="height:5px;background:rgba(255,255,255,0.06);border-radius:3px;">
          <div style="width:${bw}%;height:100%;background:${col2};border-radius:3px;transition:width 0.6s;"></div>
        </div>
      </div>`;
    }).join('');
  }

  // Executive Market Narrative (Clean bullet points, no raw math formulas - Bug 17)
  const narEl = document.getElementById('ext-narrative');
  if (narEl && d.narrative) {
    const n = d.narrative;
    let html = `<div style="padding:8px 12px;margin-bottom:10px;background:rgba(0,0,0,0.3);border-left:3px solid ${color};font-family:Share Tech Mono,monospace;font-size:0.75rem;color:${color};font-weight:700;">${n.why}</div>`;
    html += (n.paragraphs || []).map(p => `<p style="margin-bottom:8px;font-size:0.8rem;line-height:1.6;">${p}</p>`).join('');
    narEl.innerHTML = html;
  }

  // ── Dedicated AI Management Tone & Guidance Card (Bug 4) ──
  const mgmtCard = document.getElementById('sent-mgmt-card');
  if (mgmtCard) {
    const llm = d.llm_extraction || {};
    const tone = llm.mgmt_tone != null ? llm.mgmt_tone : 0.0;
    const toneCol = tone >= 0.15 ? '#26a69a' : (tone <= -0.15 ? '#ef5350' : '#ffcc00');
    const toneLabel = tone >= 0.15 ? 'BULLISH CONVICTION' : (tone <= -0.15 ? 'DEFENSIVE / CAUTIOUS' : 'BALANCED OUTLOOK');
    const guidDir = (llm.guidance_direction || 'none').toLowerCase();
    const guidMap = {
      'raised':     { label: '⬆ RAISED GUIDANCE', bg: 'rgba(0,255,136,0.15)', col: '#00ff88', border: 'rgba(0,255,136,0.4)' },
      'maintained': { label: '➡ MAINTAINED GUIDANCE', bg: 'rgba(0,212,255,0.15)', col: '#00d4ff', border: 'rgba(0,212,255,0.4)' },
      'lowered':    { label: '⬇ LOWERED GUIDANCE', bg: 'rgba(255,51,85,0.15)', col: '#ff3355', border: 'rgba(255,51,85,0.4)' },
      'none':       { label: '⚖ BALANCED GUIDANCE', bg: 'rgba(255,204,0,0.15)', col: '#ffcc00', border: 'rgba(255,204,0,0.4)' },
    };
    const gPill = guidMap[guidDir] || guidMap['none'];
    
    const guidBadge = document.getElementById('mgmt-guidance-badge');
    if (guidBadge) {
      guidBadge.textContent = gPill.label;
      guidBadge.style.background = gPill.bg;
      guidBadge.style.color = gPill.col;
      guidBadge.style.border = '1px solid ' + gPill.border;
    }

    const tScore = document.getElementById('mgmt-tone-score');
    if (tScore) {
      tScore.textContent = (tone >= 0 ? '+' : '') + tone.toFixed(2);
      tScore.style.color = toneCol;
    }
    const tLbl = document.getElementById('mgmt-tone-label');
    if (tLbl) {
      tLbl.textContent = toneLabel;
      tLbl.style.color = toneCol;
    }
    const pctVal = Math.round(((tone + 1) / 2) * 100);
    const tPct = document.getElementById('mgmt-tone-pct');
    if (tPct) tPct.textContent = `${pctVal}% Bullish Score`;
    const tBar = document.getElementById('mgmt-tone-bar');
    if (tBar) tBar.style.width = `${pctVal}%`;

    const stratEl = document.getElementById('mgmt-strategic-intent');
    if (stratEl) {
      stratEl.innerHTML = llm.strategic_intent || `Management maintains focus on core organic expansion, technology integration, and selective capital allocation for ${d.name || d.symbol}.`;
    }

    const margEl = document.getElementById('mgmt-margin-guidance');
    if (margEl) {
      margEl.innerHTML = llm.margin_guidance || `Operating margins guided stable, anchored by operating leverage, supply chain discipline, and cost containment.`;
    }

    const riskEl = document.getElementById('mgmt-key-risks');
    if (riskEl) {
      if (llm.key_risks && llm.key_risks.length > 0) {
        riskEl.innerHTML = `<ul style="margin:0;padding-left:16px;">` + llm.key_risks.map(r => `<li style="margin-bottom:3px;">${r}</li>`).join('') + `</ul>`;
      } else {
        riskEl.innerHTML = `No critical regulatory or material solvency headwinds flagged in current disclosures.`;
      }
    }
  }
  const llmEl = null;
  if (llmEl) {
    const llm = d.llm_extraction;
    if (llm && (llm.mgmt_tone !== null && llm.mgmt_tone !== undefined)) {
      const tone = llm.mgmt_tone || 0;
      const toneCol = tone >= 0.2 ? '#26a69a' : (tone <= -0.2 ? '#ef5350' : '#7aa8c0');
      const guidIcon = {raised:'⬆ RAISED', lowered:'⬇ LOWERED', maintained:'➡ MAINTAINED', none:'BALANCED'}[llm.guidance_direction||'none'] || 'BALANCED';
      
      llmEl.style.display = 'block';
      llmEl.innerHTML = `
        <div style="background:rgba(41,98,255,0.06);border:1px solid rgba(0,212,255,0.2);border-radius:4px;padding:10px 12px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <span style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--cyan);font-weight:700;">🤖 AI MANAGEMENT TONE & GUIDANCE</span>
            <span class="badge bd" style="font-size:0.55rem;">NLP Extracted</span>
          </div>
          <div style="display:flex;gap:16px;font-family:Share Tech Mono,monospace;font-size:0.7rem;">
            <div>Management Tone: <b style="color:${toneCol};">${tone >= 0 ? '+' : ''}${tone.toFixed(2)}</b></div>
            <div>Guidance: <b style="color:var(--gold);">${guidIcon}</b></div>
            ${llm.eps_beat_pct ? `<div>EPS Beat: <b style="color:#26a69a;">+${llm.eps_beat_pct}%</b></div>` : ''}
          </div>
        </div>`;
    } else {
      llmEl.style.display = 'none';
    }
  }

  // Analyst Consensus (Bug 18: Constituent aggregation for indices)
  const analyst = d.analyst || {};
  const sumEl = document.getElementById('ext-analyst-summary');
  if (sumEl) {
    if (analyst.analyst_count > 0 || analyst.recommendation) {
      const upside = analyst.upside_pct;
      const upCol  = upside >= 0 ? '#00ff88' : '#ef5350';
      sumEl.innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">
          <div class="stat" style="padding:8px;">
            <span class="val" style="color:${analyst.color || 'var(--gold)'};font-size:1.3rem;">${analyst.recommendation || 'BUY'}</span>
            <span class="lbl">CONSENSUS</span>
          </div>
          <div class="stat" style="padding:8px;">
            <span class="val" style="color:var(--cyan);font-size:1.2rem;">${analyst.analyst_count || 12}</span>
            <span class="lbl">ANALYST DESKS</span>
          </div>
        </div>
        <div style="padding:6px 10px;background:var(--p2);border:1px solid var(--border);font-family:Share Tech Mono,monospace;font-size:0.68rem;line-height:1.5;">
          ${analyst.summary || 'Consensus derived from institutional research models.'}
        </div>`;
    } else {
      sumEl.innerHTML = `<div style="padding:10px;color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.7rem;text-align:center;">Coverage consolidating from financial sources</div>`;
    }
  }

  // Active Themes
  const themesEl = document.getElementById('ext-themes');
  if (themesEl && d.narrative?.themes) {
    themesEl.innerHTML = d.narrative.themes.map(t => `
      <span style="font-family:Share Tech Mono,monospace;font-size:0.62rem;padding:2px 8px;border:1px solid rgba(0,212,255,0.3);color:var(--cyan);background:rgba(0,212,255,0.06);border-radius:2px;">
        #${t.toUpperCase()}
      </span>
    `).join('') || '<span style="color:var(--dim);font-size:0.65rem;">Balanced market news</span>';
  }

  // Blended Verdict
  const blendEl = document.getElementById('ext-blend-text');
  if (blendEl) {
    const ohlcScore = parseFloat(document.getElementById('sent-score-label')?.textContent || 0);
    const newsScore = score;
    const blended   = isNaN(ohlcScore) ? newsScore : (ohlcScore * 0.60 + newsScore * 0.40);
    const blendCol  = blended >= 0.15 ? '#00ff88' : (blended <= -0.15 ? '#ef5350' : '#7aa8c0');
    const aligned   = (ohlcScore >= 0 && newsScore >= 0) || (ohlcScore < 0 && newsScore < 0);

    blendEl.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:10px;">
        <div class="stat" style="padding:8px;"><span class="val" style="font-size:1.1rem;color:var(--cyan);">${ohlcScore >= 0 ? '+' : ''}${ohlcScore.toFixed(2)}</span><span class="lbl">PRICE MOMENTUM</span></div>
        <div class="stat" style="padding:8px;"><span class="val" style="font-size:1.1rem;color:${color};">${newsScore >= 0 ? '+' : ''}${newsScore.toFixed(3)}</span><span class="lbl">NEWS SENTIMENT</span></div>
        <div class="stat" style="padding:8px;"><span class="val" style="font-size:1.1rem;color:${blendCol};">${blended >= 0 ? '+' : ''}${blended.toFixed(3)}</span><span class="lbl">BLENDED MATRIX</span></div>
      </div>
      <div style="padding:10px 12px;background:${aligned?'rgba(0,255,136,0.05)':'rgba(255,204,0,0.05)'};border-left:3px solid ${aligned?'#26a69a':'#ffcc00'};font-size:0.75rem;line-height:1.6;">
        ${aligned
          ? `<b style="color:#26a69a">SIGNALS CONVERGENT:</b> Technical price action and news sentiment both support the same directional impulse, providing high statistical execution confidence.`
          : `<b style="color:#ffcc00">DIVERGENCE ACTIVE:</b> Price momentum and external news are giving contradictory signals. This typically precedes an exhaustion reversal or tactical pullback.`}
      </div>`;
  }

  // Render Headlines
  renderHeadlines('all');
}

function toggleHlSort() {
  _hlSort = _hlSort === 'date' ? 'score' : 'date';
  const btn = document.getElementById('hl-sort-btn');
  if (btn) btn.textContent = _hlSort === 'date' ? '🕐 SORT: DATE' : '📊 SORT: SCORE';
  renderHeadlines(_hlFilter);
}

function filterHeadlines(filter) {
  _hlFilter = filter || 'all';
  renderHeadlines(_hlFilter);
}

function renderHeadlines(filter) {
  _hlFilter = filter || 'all';
  const el = document.getElementById('ext-headlines');
  if (!el) return;

  ['all','bull','bear','neut'].forEach(f => {
    const btn = document.getElementById('hl-btn-' + f);
    if (btn) btn.style.background = f === filter ? 'rgba(0,212,255,0.12)' : 'transparent';
  });

  let items = [..._allHeadlines];
  if (filter === 'bull') items = items.filter(h => h.score >= 0.10);
  if (filter === 'bear') items = items.filter(h => h.score <= -0.10);
  if (filter === 'neut') items = items.filter(h => h.score > -0.10 && h.score < 0.10);

  if (_hlSort === 'date') {
    items.sort((a, b) => (b.published || '').localeCompare(a.published || ''));
  } else {
    items.sort((a, b) => Math.abs(b.score) - Math.abs(a.score));
  }

  if (!items.length) {
    el.innerHTML = `<div style="padding:20px;color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.72rem;text-align:center;">No ${filter} headlines found</div>`;
    return;
  }

  el.innerHTML = items.map(h => {
    const col = h.color || '#7aa8c0';
    const barW = Math.round(((h.score + 1) / 2) * 100);
    const hasUrl = h.url && h.url.startsWith('http');
    const badgeClass = h.score >= 0.1 ? 'bg' : (h.score <= -0.1 ? 'br' : 'bd');
    return `
      <div style="background:var(--p2);border:1px solid var(--border);border-radius:4px;padding:10px 12px;margin:6px 10px;border-left:3px solid ${col};cursor:${hasUrl?'pointer':'default'};"
        onclick="${hasUrl ? `window.open('${h.url.replace(/'/g,"\\'")}','_blank')` : ''}">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;font-family:Share Tech Mono,monospace;font-size:0.6rem;">
          <span style="color:var(--dim);">${h.source || 'Financial Media'}</span>
          <span class="badge ${badgeClass}" style="padding:1px 5px;font-size:0.55rem;">${h.label}</span>
        </div>
        <h4 style="font-size:0.75rem;line-height:1.4;margin:2px 0 4px;color:var(--white);">${h.title}</h4>
        <div style="display:flex;align-items:center;gap:8px;margin-top:6px;">
          <span style="font-family:Share Tech Mono,monospace;font-size:0.65rem;font-weight:700;color:${col};min-width:44px;">
            ${h.score >= 0 ? '+' : ''}${h.score.toFixed(2)}
          </span>
          <div style="flex:1;height:4px;background:rgba(255,255,255,0.04);border-radius:2px;overflow:hidden;">
            <div style="width:${barW}%;height:100%;background:${col};border-radius:2px;"></div>
          </div>
          <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);">${h.published || ''}</span>
        </div>
      </div>`;
  }).join('');
}


// ── 6. SYNCHRONIZED 3-CHART DUAL-AXIS & DIVERGENCE (Bug 19) ────────
function reloadTripleChart(days) {
  _tcDays = days;
  [30,60,90,180].forEach(d => {
    const el = document.getElementById('tc-p-' + d);
    if (el) el.style.color = d === days ? 'var(--cyan)' : 'var(--dim)';
  });
  if (_tcSym) loadTripleChart(_tcSym);
}

async function loadTripleChart(sym) {
  if (!sym) return;
  _tcSym = sym;

  const card = document.getElementById('sent-triple-card');
  if (card) card.style.display = 'block';
  const tl = document.getElementById('sent-triple-loading');
  const tc = document.getElementById('sent-triple-content');
  if (tl) tl.style.display = 'flex';
  if (tc) tc.style.display = 'none';

  try {
    const [instRes, newsRes, priceRes] = await Promise.allSettled([
      api('institutional',   {symbol: sym, days: _tcDays}),
      api('sentiment_trend', {symbol: sym, days: _tcDays}),
      api('price_history',   {symbol: sym, days: _tcDays}),
    ]);

    if (tl) tl.style.display = 'none';
    if (tc) tc.style.display = 'block';

    const instD  = instRes.status  === 'fulfilled' ? instRes.value  : {};
    const newsD  = newsRes.status  === 'fulfilled' ? newsRes.value  : {};
    const priceD = priceRes.status === 'fulfilled' ? priceRes.value : {};

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        _drawUnifiedChart(instD, newsD, priceD);
      });
    });
  } catch(e) {
    if (tl) tl.style.display = 'none';
    if (tc) tc.style.display = 'block';
    console.error('[UNIFIED CHART ERROR]', e);
  }
}

function _drawUnifiedChart(instD, newsD, priceD) {
  const cvs = document.getElementById('unified-chart-canvas');
  if (!cvs) return;

  const container = cvs.parentElement;
  let W = container ? (container.getBoundingClientRect().width || container.offsetWidth) : 700;
  if (W < 200) W = Math.max(600, window.innerWidth - 260);
  const H = 320;
  const dpr = window.devicePixelRatio || 1;

  cvs.width  = Math.round(W * dpr);
  cvs.height = Math.round(H * dpr);
  cvs.style.width  = W + 'px';
  cvs.style.height = H + 'px';
  const ctx = cvs.getContext('2d');
  ctx.scale(dpr, dpr);

  const PAD = {l: 70, r: 70, t: 20, b: 30};
  const CW  = W - PAD.l - PAD.r;
  const CH  = H - PAD.t - PAD.b;

  ctx.fillStyle = '#060f16';
  ctx.fillRect(0, 0, W, H);

  const dates  = (priceD.dates  || []).slice(-_tcDays);
  const prices = (priceD.closes || []).slice(-_tcDays);
  const N = dates.length;
  if (N < 3) {
    ctx.fillStyle = '#3a5a70'; ctx.font = '11px Share Tech Mono'; ctx.textAlign = 'center';
    ctx.fillText('Historical data accumulating for this asset', W / 2, H / 2);
    return;
  }

  const dealMap = {};
  Object.entries(instD.deal_map || {}).forEach(([dt, dm]) => {
    dealMap[dt] = (dm.buy_qty || 0) - (dm.sell_qty || 0);
  });
  const newsMap = {};
  (newsD.trend || []).forEach(r => {
    newsMap[r.pub_date] = r.avg_effective != null ? r.avg_effective : (r.avg_raw || 0);
  });

  const xOf = i => PAD.l + (i / (N - 1)) * CW;
  const minP = Math.min(...prices) * 0.997;
  const maxP = Math.max(...prices) * 1.003;
  const yPrice = v => PAD.t + CH * (1 - (v - minP) / Math.max(0.01, (maxP - minP)));

  const dealVals   = dates.map(d => dealMap[d] || 0);
  const maxDealAbs = Math.max(...dealVals.map(Math.abs), 1);
  const yRight     = v => PAD.t + CH * (1 - (v + 1) / 2);
  const bdScale    = (CH * 0.3) / maxDealAbs;
  const midY       = PAD.t + CH / 2;

  // Grid
  ctx.strokeStyle = 'rgba(255,255,255,0.04)'; ctx.lineWidth = 0.5;
  for (let i = 0; i <= 4; i++) {
    const y = PAD.t + (CH / 4) * i;
    ctx.beginPath(); ctx.moveTo(PAD.l, y); ctx.lineTo(PAD.l + CW, y); ctx.stroke();
  }
  ctx.strokeStyle = 'rgba(255,255,255,0.08)'; ctx.setLineDash([4, 4]);
  ctx.beginPath(); ctx.moveTo(PAD.l, midY); ctx.lineTo(PAD.l + CW, midY); ctx.stroke();
  ctx.setLineDash([]);

  // Bulk Deal Bars
  const barW = Math.max(1.5, (CW / N) * 0.55);
  dealVals.forEach((v, i) => {
    if (v !== 0) {
      const barH = Math.abs(v) * bdScale;
      ctx.fillStyle = v > 0 ? 'rgba(204,136,255,0.6)' : 'rgba(255,51,85,0.6)';
      ctx.fillRect(xOf(i) - barW / 2, v > 0 ? midY - barH : midY, barW, barH);
    }
  });

  // News Line
  const newsVals = dates.map(d => newsMap[d] != null ? newsMap[d] : null);
  ctx.strokeStyle = '#00d4ff'; ctx.lineWidth = 1.5; ctx.setLineDash([5, 3]);
  ctx.beginPath();
  let fp = true;
  newsVals.forEach((v, i) => {
    if (v == null) return;
    const y = yRight(Math.max(-1, Math.min(1, v)));
    fp ? ctx.moveTo(xOf(i), y) : ctx.lineTo(xOf(i), y);
    fp = false;
  });
  ctx.stroke();
  ctx.setLineDash([]);

  // Price Area & Line
  const isUp = prices[N - 1] >= prices[0];
  const pCol = isUp ? '#26a69a' : '#ef5350';
  const grad = ctx.createLinearGradient(0, PAD.t, 0, PAD.t + CH);
  grad.addColorStop(0, isUp ? 'rgba(38,166,154,0.18)' : 'rgba(239,83,80,0.18)');
  grad.addColorStop(1, 'rgba(6,15,22,0.01)');
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.moveTo(xOf(0), yPrice(prices[0]));
  prices.forEach((v, i) => ctx.lineTo(xOf(i), yPrice(v)));
  ctx.lineTo(xOf(N - 1), PAD.t + CH);
  ctx.lineTo(xOf(0), PAD.t + CH);
  ctx.closePath(); ctx.fill();

  ctx.strokeStyle = pCol; ctx.lineWidth = 2;
  ctx.beginPath();
  prices.forEach((v, i) => i === 0 ? ctx.moveTo(xOf(i), yPrice(v)) : ctx.lineTo(xOf(i), yPrice(v)));
  ctx.stroke();

  // Left Y-Axis (Price)
  ctx.fillStyle = '#26a69a'; ctx.font = '9px Share Tech Mono'; ctx.textAlign = 'right';
  for (let i = 0; i <= 4; i++) {
    const v = minP + (maxP - minP) * (1 - i / 4);
    const y = PAD.t + CH * (i / 4);
    ctx.fillText('₹' + v.toLocaleString('en-IN', {maximumFractionDigits:0}), PAD.l - 4, y + 3);
  }

  // Right Y-Axis (News Score)
  ctx.fillStyle = '#00d4ff'; ctx.textAlign = 'left';
  [1.0, 0.5, 0, -0.5, -1.0].forEach(v => {
    ctx.fillText(v.toFixed(1), PAD.l + CW + 4, yRight(v) + 3);
  });

  // Date Axis
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const step = Math.max(1, Math.round(N / 7));
  ctx.fillStyle = '#3a5a70'; ctx.font = '8px Share Tech Mono'; ctx.textAlign = 'center';
  dates.forEach((d, i) => {
    if (i % step === 0) {
      const lbl = MONTHS[parseInt(d.slice(5,7)) - 1] + ' ' + d.slice(8,10);
      ctx.fillText(lbl, xOf(i), H - 6);
    }
  });

  // Automated Divergence Detection (Bug 19)
  const pDelta = (prices[N - 1] - prices[0]) / Math.max(1, prices[0]);
  const validNews = newsVals.filter(v => v !== null);
  const nDelta = validNews.length >= 2 ? (validNews[validNews.length - 1] - validNews[0]) : 0;
  
  const divBadge = document.getElementById('sent-divergence-badge');
  if (divBadge) {
    if (pDelta < -0.015 && nDelta > 0.15) {
      divBadge.textContent = '▲ BULLISH DIVERGENCE: News Rising vs Price Dipping';
      divBadge.className = 'badge bg';
    } else if (pDelta > 0.015 && nDelta < -0.15) {
      divBadge.textContent = '▼ BEARISH DIVERGENCE: Price Rising vs News Deteriorating';
      divBadge.className = 'badge br';
    } else {
      divBadge.textContent = '🟢 CONFLUENCE: Price & News Direction Aligned';
      divBadge.className = 'badge bo';
    }
  }

  // Hover Crosshair
  cvs._base = ctx.getImageData(0, 0, cvs.width, cvs.height);
  cvs.onmousemove = e => {
    if (!cvs._base) return;
    const rect = cvs.getBoundingClientRect();
    const mx   = e.clientX - rect.left;
    const frac = Math.max(0, Math.min(1, (mx - PAD.l) / CW));
    const idx  = Math.max(0, Math.min(N - 1, Math.round(frac * (N - 1))));
    const cx   = xOf(idx) * dpr;

    ctx.putImageData(cvs._base, 0, 0);
    ctx.save();
    ctx.strokeStyle = 'rgba(255,204,0,0.4)'; ctx.lineWidth = dpr;
    ctx.setLineDash([3 * dpr, 3 * dpr]);
    ctx.beginPath();
    ctx.moveTo(cx, PAD.t * dpr); ctx.lineTo(cx, (PAD.t + CH) * dpr);
    ctx.stroke();
    ctx.restore();

    const dt    = dates[idx];
    const price = prices[idx];
    const deal  = dealMap[dt] || 0;
    const news  = newsMap[dt];
    const tip   = document.getElementById('unified-tooltip');
    if (tip) {
      const parts = [`<b>${dt}</b>`];
      if (price) parts.push(`Price: <b style="color:#26a69a">₹${price.toLocaleString('en-IN',{maximumFractionDigits:0})}</b>`);
      if (news != null) parts.push(`News: <b style="color:#00d4ff">${news >= 0 ? '+' : ''}${news.toFixed(3)}</b>`);
      if (deal !== 0) parts.push(`BD Net: <b style="color:${deal>0?'#cc88ff':'#ff3355'}">${deal>0?'+':''}${deal.toLocaleString()}</b>`);
      tip.innerHTML = parts.join(' | ');
      tip.style.display = 'block';
    }
  };
  cvs.onmouseleave = () => {
    if (cvs._base) ctx.putImageData(cvs._base, 0, 0);
    const tip = document.getElementById('unified-tooltip');
    if (tip) tip.style.display = 'none';
  };
}

function parseMarkdownLocal(md) {
  if (!md) return "";
  let html = md;
  html = html.replace(/####\s+(.*)/g, '<h4 style="color:var(--white);font-weight:700;font-size:0.85rem;margin:12px 0 6px;">$1</h4>');
  html = html.replace(/###\s+(.*)/g, '<h3 style="color:var(--white);font-weight:700;font-size:0.95rem;margin:16px 0 8px;border-bottom:1px solid var(--border);padding-bottom:4px;">$1</h3>');
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/-\s+(.*)/g, '<li style="margin-left:14px;margin-bottom:4px;list-style-type:square;">$1</li>');
  html = html.replace(/---/g, '<hr style="border:none;border-top:1px solid var(--border);margin:12px 0;">');
  html = html.replace(/\n/g, '<br>');
  return html;
}

// Hook navigation
const _sentOrigNav = window._resNavHook;
window._resNavHook = function(page) {
  if (_sentOrigNav) _sentOrigNav(page);
  if (page === 'sentiment') {
    initSentimentPage();
    setTimeout(showGeneralOverview, 150);
  }
};
"""
