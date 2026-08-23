"""
page_sentiment.py — Sentiment Analysis — hybrid market emotion model

Exports:
    HTML  : Page HTML template (injected into SPA)
    JS    : Page JavaScript (injected into <script> block)

Backend endpoints for this page live in app.py (ep == "..." handlers).
To modify: edit HTML/JS here, backend logic in app.py.
"""


HTML = r"""
<!-- ═══════════ PAGE: SENTIMENT ═══════════ -->
<div class="page" id="page-sentiment">
  <div class="topbar">
    <h2>🧠 SENTIMENT + EMOTIONAL ANALYSIS</h2>
    <span class="page-tag">HYBRID SENTIMENT MODEL</span>
  </div>

  <!-- Toolbar -->
  <div class="card" style="padding:10px 14px;margin-bottom:10px;">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
      <label style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;flex-shrink:0;">SYMBOL</label>
      <select id="sent-sym"
        style="background:var(--p2);border:1px solid var(--b2);color:var(--gold);padding:4px 8px;
        font-family:Share Tech Mono,monospace;font-size:0.82rem;font-weight:700;outline:none;min-width:200px;flex:1;">
        <option value="">🌐 MARKET OVERVIEW (MARKET BRAIN)</option>
      </select>
      <label style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;flex-shrink:0;">LOOKBACK</label>
      <select id="sent-period"
        style="background:var(--p2);border:1px solid var(--b2);color:var(--cyan);padding:4px 8px;
        font-family:Share Tech Mono,monospace;font-size:0.75rem;outline:none;width:120px;">
        <option value="20">20 days</option>
        <option value="60" selected>60 days</option>
        <option value="120">120 days</option>
        <option value="252">1 year</option>
      </select>
      <button class="btn-gold btn" onclick="loadSentiment()" style="padding:6px 20px;font-size:0.72rem;flex-shrink:0;">⚡ ANALYSE</button>
      <button class="btn" onclick="showGeneralOverview()" style="padding:6px 20px;font-size:0.72rem;flex-shrink:0;background:var(--p2);border:1px solid var(--border);color:var(--cyan);">🌐 OVERVIEW</button>
    </div>
  </div>

  <div id="sent-loading" class="loading" style="display:none;"><div class="spinner"></div>COMPUTING SENTIMENT...</div>
  <div id="sent-error" style="display:none;padding:14px;color:var(--red);font-family:Share Tech Mono,monospace;"></div>

  <!-- General Market Brain View -->
  <div id="sent-general-view" style="display:none;margin-top:10px;">
    <!-- Row 1: Narrative & Mood Gauge -->
    <div style="display:grid;grid-template-columns:280px 1fr;gap:14px;margin-bottom:14px;">
      <!-- Mood gauge -->
      <div class="card" style="padding:18px;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:220px;text-align:center;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);letter-spacing:2px;margin-bottom:12px;">GLOBAL MARKET MOOD</div>
        <canvas id="mb-gauge" width="200" height="120" style="display:block;"></canvas>
        <div id="mb-mood-label" style="font-family:Orbitron,sans-serif;font-size:1.6rem;font-weight:900;margin-top:8px;text-transform:uppercase;">—</div>
        <div id="mb-mood-rationale" style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);margin-top:6px;line-height:1.4;max-width:240px;">—</div>
      </div>

      <!-- Narrative digest -->
      <div class="card" style="padding:18px;display:flex;flex-direction:column;justify-content:space-between;min-height:220px;">
        <div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <span class="card-title" style="margin-bottom:0;">TODAY'S MARKET NARRATIVE</span>
            <span id="mb-confidence-badge" class="badge bc" style="margin-left:auto;padding:2px 8px;">Confidence —</span>
          </div>
          <p id="mb-narrative-text" style="font-size:0.85rem;line-height:1.7;color:var(--text);margin-top:8px;"></p>
        </div>
        <div style="font-size:0.6rem;color:var(--dim);border-top:1px solid var(--border);padding-top:10px;margin-top:10px;display:flex;justify-content:space-between;">
          <span>METHODOLOGY: 100% OFFLINE DATABASE-SUPERVISED AGGREGATION</span>
          <span id="mb-digest-date">Date: --</span>
        </div>
      </div>
    </div>

    <!-- Row 2: Ask Market Brain Q&A Interface -->
    <div class="card" style="padding:16px;margin-bottom:14px;background:linear-gradient(135deg, rgba(21,25,36,0.9), rgba(30,34,45,0.7));border:1px solid rgba(41,98,255,0.25);">
      <div class="card-title" style="color:var(--cyan);letter-spacing:2px;">💬 ASK MARKET BRAIN Q&A</div>
      <div style="display:flex;gap:10px;margin-bottom:12px;">
        <input type="text" id="mb-query-input" placeholder="Ask how specific global events or interest rates affect sectors... e.g. How does the Fed rate hike affect Bank Nifty?"
          style="flex:1;background:var(--p2);border:1px solid var(--border);color:var(--white);padding:10px 14px;font-family:'JetBrains Mono',monospace;font-size:0.8rem;outline:none;"
          onkeypress="if(event.key==='Enter')askMarketBrain()">
        <button class="btn btn-gold" onclick="askMarketBrain()" style="padding:10px 24px;font-weight:700;">⚡ ASK BRAIN</button>
      </div>
      <div id="mb-qa-loading" class="loading" style="display:none;"><div class="spinner"></div>ANALYSING NEWS CHANNELS & CAUSAL LOOPS...</div>
      <div id="mb-qa-result" class="card" style="display:none;background:rgba(0,0,0,0.2);padding:14px;border:1px solid var(--border);font-size:0.8rem;line-height:1.6;color:var(--text);max-height:400px;overflow-y:auto;font-family:'Inter',sans-serif;"></div>
    </div>

    <!-- Row 3: Sector Sentiment Board & Key Events -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
      <!-- Sector Grid -->
      <div class="card" style="padding:16px;">
        <div class="card-title">📊 SECTOR SENTIMENT BOARD</div>
        <div id="mb-sectors-grid" style="display:flex;flex-direction:column;gap:8px;">
          <div class="loading"><div class="spinner"></div>COMPUTING SECTOR RATINGS...</div>
        </div>
      </div>

      <!-- Key timeline events -->
      <div class="card" style="padding:16px;">
        <div class="card-title">📰 HIGHEST IMPACT NEWS FLOW (TIMELINE)</div>
        <div id="mb-events-timeline" style="display:flex;flex-direction:column;gap:10px;max-height:450px;overflow-y:auto;">
          <div class="loading"><div class="spinner"></div>ANALYSING NEWS FLOW...</div>
        </div>
      </div>
    </div>
  </div>

  <div id="sent-content" style="display:none;">

    <!-- Composite score gauge -->
    <div style="display:grid;grid-template-columns:280px 1fr;gap:12px;margin-bottom:12px;">

      <!-- Score gauge card -->
      <div class="card" style="padding:18px;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:200px;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);letter-spacing:2px;margin-bottom:12px;">COMPOSITE SENTIMENT</div>
        <canvas id="sent-gauge" width="200" height="120" style="display:block;"></canvas>
        <div id="sent-score-label" style="font-family:Orbitron,sans-serif;font-size:2rem;font-weight:900;margin-top:8px;">—</div>
        <div id="sent-verdict" style="font-family:Share Tech Mono,monospace;font-size:0.75rem;letter-spacing:2px;margin-top:4px;">—</div>
        <div id="sent-score-detail" style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);margin-top:6px;text-align:center;line-height:1.5;"></div>
      </div>

      <!-- Component breakdown -->
      <div class="card" style="padding:16px;">
        <div class="card-title" style="margin-bottom:14px;">📊 COMPONENT BREAKDOWN</div>
        <div id="sent-components" style="display:flex;flex-direction:column;gap:10px;"></div>
      </div>
    </div>

    <!-- Candlestick psychology + price action -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
      <div class="card">

        <div class="card-title" style="color:#ffcc00;">🕯 CANDLESTICK PSYCHOLOGY</div>
        <div id="sent-candles" style="font-family:Share Tech Mono,monospace;font-size:0.72rem;line-height:1.8;"></div>
      </div>
      <div class="card">
        <div class="card-title" style="color:#00d4ff;">📐 PIVOT INTERACTIONS</div>
        <div id="sent-pivots" style="font-family:Share Tech Mono,monospace;font-size:0.72rem;line-height:1.8;"></div>
      </div>
    </div>

    <!-- Volatility + regime -->
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:12px;">
      <div class="card">
        <div class="card-title" style="color:#ef5350;">⚡ VOLATILITY INDEX</div>
        <div id="sent-vol" style="font-family:Share Tech Mono,monospace;font-size:0.72rem;line-height:1.8;"></div>
      </div>
      <div class="card">
        <div class="card-title" style="color:#26a69a;">📈 TREND EMOTION</div>
        <div id="sent-trend" style="font-family:Share Tech Mono,monospace;font-size:0.72rem;line-height:1.8;"></div>
      </div>
      <div class="card">
        <div class="card-title" style="color:#cc88ff;">🌌 MARKET EMOTION STATE</div>
        <div id="sent-emotion" style="font-family:Share Tech Mono,monospace;font-size:0.72rem;line-height:1.8;"></div>
      </div>
    </div>

    <!-- Sentiment history chart -->
    <div class="card" style="padding:0;margin-bottom:12px;">
      <div class="card-title" style="padding:12px 16px 0;">📉 SENTIMENT SCORE HISTORY (rolling 14-day)</div>
      <div style="height:160px;padding:0 8px 8px;">
        <canvas id="sent-history-chart" style="display:block;width:100%;height:150px;"></canvas>
      </div>
    </div>

    <!-- Actionable signal -->
    <div id="sent-signal-card" class="card" style="padding:16px;border-left:4px solid var(--cyan);">
      <div class="card-title" style="margin-bottom:10px;">🎯 SENTIMENT SIGNAL FOR THIS SYMBOL</div>
      <div id="sent-signal-text" style="font-family:Share Tech Mono,monospace;font-size:0.8rem;line-height:1.8;"></div>
    </div>


    <!-- ── EXTERNAL SENTIMENT: News + Analyst ─────────────────── -->
    <div id="sent-external-section" style="margin-top:4px;">

      <!-- Header bar with refresh button -->
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--cyan);letter-spacing:3px;display:flex;align-items:center;gap:8px;">
          📰 EXTERNAL SENTIMENT — NEWS + ANALYST
          <span id="ext-total-badge" style="background:rgba(0,212,255,0.08);border:1px solid rgba(0,212,255,0.2);padding:1px 8px;border-radius:2px;font-size:0.6rem;"></span>
        </div>
        <button onclick="loadExternalSentiment()" id="ext-refresh-btn"
          style="background:var(--p2);border:1px solid var(--b2);color:var(--cyan);padding:3px 14px;
          font-family:Share Tech Mono,monospace;font-size:0.62rem;cursor:pointer;letter-spacing:1px;">
          ⟳ REFRESH
        </button>
      </div>

      <div id="ext-loading" style="display:none;padding:12px 0;font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--cyan);display:flex;align-items:center;gap:8px;">
        <div class="spinner"></div>FETCHING NEWS + ANALYST DATA...
      </div>
      <div id="ext-error" style="display:none;padding:10px;color:var(--red);font-family:Share Tech Mono,monospace;font-size:0.72rem;"></div>

      <div id="ext-content" style="display:none;">

        <!-- Row 1: Score cards + Narrative -->
        <div style="display:grid;grid-template-columns:320px 1fr;gap:12px;margin-bottom:12px;">

          <!-- External score + source breakdown -->
          <div class="card" style="padding:16px;">
            <div class="card-title">🌐 EXTERNAL SCORE</div>
            <div id="ext-score-display" style="text-align:center;padding:14px 0 10px;"></div>
            <!-- Source breakdown bars -->
            <div id="ext-source-bars" style="display:flex;flex-direction:column;gap:8px;margin-top:8px;"></div>
          </div>

          <!-- AI LLM Earnings Extraction panel -->
          <div class="card" style="padding:16px;" id="ext-llm-panel" style="display:none;">
          </div>

          <!-- Narrative: WHY is the score this -->
          <div class="card" style="padding:16px;">
            <div class="card-title">💬 MARKET NARRATIVE — WHY THIS SCORE?</div>
            <div id="ext-narrative" style="font-size:0.8rem;line-height:1.7;color:var(--t2);"></div>
          </div>
        </div>

        <!-- Row 2: Headlines feed -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">

          <!-- All headlines sorted by sentiment -->
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
                color:var(--cyan);cursor:pointer;font-family:Share Tech Mono,monospace;letter-spacing:1px;">
                🕐 SORT: DATE
              </button>
            </div>
            <div id="ext-headlines" style="max-height:420px;overflow-y:auto;"></div>
          </div>

          <!-- Analyst intelligence -->
          <div style="display:flex;flex-direction:column;gap:12px;">
            <div class="card" style="padding:16px;">
              <div class="card-title">📊 ANALYST CONSENSUS</div>
              <div id="ext-analyst-summary" style="margin-bottom:12px;"></div>
              <div id="ext-analyst-actions" style="max-height:180px;overflow-y:auto;"></div>
            </div>
            <div class="card" style="padding:16px;">
              <div class="card-title">🏷 KEY THEMES IN CURRENT NEWS</div>
              <div id="ext-themes" style="display:flex;flex-wrap:wrap;gap:6px;padding-top:4px;"></div>
            </div>
          </div>
        </div>

        <!-- Row 3: Blended score explanation -->
        <div class="card" style="padding:16px;" id="ext-blend-card">
          <div class="card-title">⚡ BLENDED VERDICT — OHLC + NEWS + ANALYST</div>
          <div id="ext-blend-text" style="font-size:0.82rem;line-height:1.8;color:var(--t2);"></div>
        </div>


    <!-- ── SYNCHRONIZED 3-CHART: BULK DEALS + NEWS SENTIMENT + PRICE ── -->
    <div class="card" style="margin-top:14px;" id="sent-triple-card">
      <div class="card-title">📊 PRICE · NEWS SENTIMENT · BULK/BLOCK DEALS — UNIFIED VIEW</div>
      <div id="sent-triple-loading" class="loading" style="display:none;"><div class="spinner"></div>Loading chart...</div>
      <div id="sent-triple-content" style="display:none;">
        <div style="display:flex;gap:20px;flex-wrap:wrap;padding:4px 0 10px;font-family:Share Tech Mono,monospace;font-size:0.62rem;align-items:center;">
          <span><span style="display:inline-block;width:22px;height:3px;background:#26a69a;margin-right:5px;vertical-align:middle;"></span>Price (left axis)</span>
          <span><span style="display:inline-block;width:22px;height:2px;border-top:2px dashed #00d4ff;margin-right:5px;vertical-align:middle;"></span>News Score (right axis)</span>
          <span><span style="display:inline-block;width:10px;height:10px;background:#cc88ff;border-radius:1px;margin-right:5px;vertical-align:middle;"></span>BD Buy</span>
          <span><span style="display:inline-block;width:10px;height:10px;background:#ff3355;border-radius:1px;margin-right:5px;vertical-align:middle;"></span>BD Sell</span>
          <span style="color:var(--dim);font-size:0.55rem;">Bulk deal bars = net qty on right axis · hover to compare all 3</span>
        </div>
        <div style="background:var(--p2);border:1px solid var(--border);position:relative;">
          <canvas id="unified-chart-canvas" style="width:100%;height:320px;display:block;cursor:crosshair;"></canvas>
          <div id="unified-tooltip" style="display:none;position:absolute;top:8px;left:50%;transform:translateX(-50%);
            font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--gold);
            background:rgba(6,12,20,0.92);border:1px solid rgba(255,204,0,0.3);padding:4px 14px;
            pointer-events:none;white-space:nowrap;z-index:10;"></div>
        </div>
        <div style="display:flex;gap:6px;padding:6px 0 2px;font-family:Share Tech Mono,monospace;font-size:0.6rem;align-items:center;">
          <span style="color:var(--dim);">PERIOD:</span>
          <span onclick="reloadTripleChart(30)"  id="tc-p-30"  style="cursor:pointer;padding:2px 10px;border:1px solid var(--border);color:var(--dim);">30D</span>
          <span onclick="reloadTripleChart(60)"  id="tc-p-60"  style="cursor:pointer;padding:2px 10px;border:1px solid var(--border);color:var(--dim);">60D</span>
          <span onclick="reloadTripleChart(90)"  id="tc-p-90"  style="cursor:pointer;padding:2px 10px;border:1px solid var(--border);color:var(--cyan);">90D</span>
          <span onclick="reloadTripleChart(180)" id="tc-p-180" style="cursor:pointer;padding:2px 10px;border:1px solid var(--border);color:var(--dim);">180D</span>
        </div>

        <!-- ── Bulk Deal Chart Interpretation Guide ── -->
        <div style="margin-top:12px;padding:12px 14px;background:rgba(0,0,0,0.25);border:1px solid rgba(0,212,255,0.12);border-radius:2px;">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--cyan);letter-spacing:2px;margin-bottom:10px;">📖 HOW TO READ THIS CHART</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-family:Share Tech Mono,monospace;font-size:0.68rem;">
            <div>
              <div style="color:var(--gold);margin-bottom:6px;font-weight:700;">PRICE LINE (green/red)</div>
              <div style="color:var(--t2);line-height:1.7;">Shows closing price on the left axis. Green = stock rising over the period. Red = falling. The shaded area under the line shows the trend magnitude.</div>
            </div>
            <div>
              <div style="color:#00d4ff;margin-bottom:6px;font-weight:700;">NEWS LINE (dashed blue)</div>
              <div style="color:var(--t2);line-height:1.7;">Weighted news sentiment score on the right axis (−1 to +1). Rising above 0 = positive news flow. Divergence from price is a key signal — bullish news + falling price = potential reversal up.</div>
            </div>
            <div>
              <div style="color:#cc88ff;margin-bottom:6px;font-weight:700;">BD BARS (purple = buy, red = sell)</div>
              <div style="color:var(--t2);line-height:1.7;">Weighted net capital flow from Bulk/Block deals. Bar height = ₹ value (qty × price) not just share count. Purple bars above midline = institutions buying. Red bars below = distributing.</div>
            </div>
            <div>
              <div style="color:var(--gold);margin-bottom:6px;font-weight:700;">KEY INTERPRETATIONS</div>
              <div style="color:var(--t2);line-height:1.7;">
                <span style="color:var(--green);">▲ BULLISH:</span> Price rising + news positive + BD bars purple<br>
                <span style="color:var(--red);">▼ BEARISH:</span> Price falling + news negative + BD bars red<br>
                <span style="color:#ffcc00;">⚡ REVERSAL:</span> BD purple while price still falling = accumulation. BD red while price still rising = distribution (sell signal).<br>
                <span style="color:#cc88ff;">🎯 DIVERGENCE:</span> News bullish but price dropping = buy zone. News bearish but price rising = exit zone.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
        <div class="card-title" style="margin-bottom:0;">🗄 TRAINING DATA — market_data_v2.db</div>
        <div style="display:flex;gap:8px;">
          <button onclick="loadSentimentDbStats()" id="db-refresh-btn"
            style="font-family:Share Tech Mono,monospace;font-size:0.6rem;padding:3px 12px;
            background:var(--p2);border:1px solid var(--b2);color:var(--cyan);cursor:pointer;">
            ⟳ REFRESH STATS
          </button>
          <button onclick="fetchAllSymbolsNews()" id="db-fetchall-btn"
            style="font-family:Share Tech Mono,monospace;font-size:0.6rem;padding:3px 12px;
            background:linear-gradient(135deg,rgba(0,255,136,0.1),rgba(0,255,136,0.04));
            border:1px solid rgba(0,255,136,0.3);color:#00ff88;cursor:pointer;">
            ⬇ FETCH ALL SYMBOLS
          </button>
          <button onclick="testSentimentDb()" id="db-test-btn"
            style="font-family:Share Tech Mono,monospace;font-size:0.6rem;padding:3px 12px;
            background:var(--p2);border:1px solid rgba(255,204,0,0.3);color:var(--gold);cursor:pointer;">
            ⚡ TEST DB WRITE
          </button>
        </div>
      </div>
      <div id="db-status-content">
        <div style="color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.72rem;">
          Click REFRESH STATS to check DB status
        </div>
      </div>
    </div>

  </div>
</div>
</div>
"""


JS = r"""
async function loadSentiment() {
  const sym    = document.getElementById('sent-sym')?.value;
  const period = document.getElementById('sent-period')?.value || 60;
  if (!sym) {
    showGeneralOverview();
    return;
  }

  document.getElementById('sent-loading').style.display='flex';
  document.getElementById('sent-error').style.display='none';
  document.getElementById('sent-content').style.display='none';
  document.getElementById('sent-general-view').style.display='none';

  try {
    const d = await api('sentiment', {symbol:sym, period});
    document.getElementById('sent-loading').style.display='none';
    renderSentiment(d);
    // Auto-load external sentiment after OHLC renders
    setTimeout(loadExternalSentiment, 200);
    // Load synchronized triple chart
    setTimeout(() => loadTripleChart(sym), 400);
  } catch(e) {
    document.getElementById('sent-loading').style.display='none';
    const err = document.getElementById('sent-error');
    err.style.display='block'; err.textContent='⚠ '+e.message;
  }
}

function renderSentiment(d) {
  document.getElementById('sent-content').style.display='block';

  const score = d.composite || 0;
  const pct   = Math.round((score+1)/2*100); // 0-100 scale

  // ── Gauge ──
  const gc = document.getElementById('sent-gauge');
  if (gc) {
    const gctx = gc.getContext('2d');
    const dpr = window.devicePixelRatio||1;
    gc.width=200*dpr; gc.height=120*dpr;
    gc.style.width='200px'; gc.style.height='120px';
    gctx.scale(dpr,dpr);
    const cx=100, cy=105, r=80;
    // Background arc
    gctx.beginPath(); gctx.arc(cx,cy,r,Math.PI,2*Math.PI);
    gctx.strokeStyle='rgba(255,255,255,0.08)'; gctx.lineWidth=14; gctx.stroke();
    // Colour zones
    const zones = [
      {from:0,   to:0.2,  col:'#cc00ff'},  // extreme fear
      {from:0.2, to:0.35, col:'#ef5350'},  // fear
      {from:0.35,to:0.45, col:'#ffcc00'},  // caution
      {from:0.45,to:0.55, col:'#7aa8c0'},  // neutral
      {from:0.55,to:0.65, col:'#7FFFD4'},  // optimism
      {from:0.65,to:0.80, col:'#26a69a'},  // greed
      {from:0.80,to:1.0,  col:'#ff4444'},  // extreme greed
    ];
    zones.forEach(z => {
      const a1 = Math.PI + z.from*Math.PI;
      const a2 = Math.PI + z.to  *Math.PI;
      gctx.beginPath(); gctx.arc(cx,cy,r,a1,a2);
      gctx.strokeStyle=z.col; gctx.lineWidth=10; gctx.stroke();
    });
    // Needle
    const angle = Math.PI + ((score+1)/2)*Math.PI;
    gctx.save(); gctx.translate(cx,cy);
    gctx.rotate(angle);
    gctx.beginPath(); gctx.moveTo(0,4); gctx.lineTo(r-6,0); gctx.lineTo(0,-4);
    gctx.fillStyle='#fff'; gctx.fill();
    gctx.restore();
    gctx.beginPath(); gctx.arc(cx,cy,7,0,Math.PI*2);
    gctx.fillStyle='#fff'; gctx.fill();
    // Labels
    gctx.fillStyle='#3a5a70'; gctx.font='8px Share Tech Mono'; gctx.textAlign='center';
    gctx.fillText('FEAR',18,cy-2); gctx.fillText('NEUTRAL',cx,34); gctx.fillText('GREED',182,cy-2);
  }

  // Score label + verdict
  const scoreEl = document.getElementById('sent-score-label');
  if (scoreEl) { scoreEl.textContent=score.toFixed(2); scoreEl.style.color=d.emotion_color||'#7aa8c0'; }
  const verdictEl = document.getElementById('sent-verdict');
  if (verdictEl) { verdictEl.textContent=d.emotion||''; verdictEl.style.color=d.emotion_color||'#7aa8c0'; }
  const detailEl = document.getElementById('sent-score-detail');
  if (detailEl) detailEl.innerHTML=`RSI: ${d.rsi||'—'}  ·  Vol: ${d.vol_pct||'—'}%  ·  Range: ${d.range_pct||'—'}%<br>${d.name||d.symbol} · ${d.period||60}d window`;

  // ── Component bars ──
  const compEl = document.getElementById('sent-components');
  if (compEl && d.components) {
    const comps = [
      {key:'pivot',     label:'Pivot Interactions',  ico:'📐'},
      {key:'trend',     label:'Trend / RSI',         ico:'📈'},
      {key:'candle',    label:'Candlestick Pattern', ico:'🕯'},
      {key:'volatility',label:'Volatility Index',    ico:'⚡'},
      {key:'volume',    label:'Volume Emotion',      ico:'📊'},
    ];
    compEl.innerHTML = comps.map(c => {
      const comp = d.components[c.key]||{};
      const s    = comp.score||0;
      const barW = Math.round((s+1)/2*100);
      const col  = s>0.3?'#26a69a':s>0.1?'#7FFFD4':s<-0.3?'#ef5350':s<-0.1?'#ffcc00':'#7aa8c0';
      return `<div>
        <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
          <span style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--t2);">${c.ico} ${c.label} <span style="color:var(--dim);font-size:0.55rem;">(${comp.weight||0}%)</span></span>
          <span style="font-family:Share Tech Mono,monospace;font-size:0.62rem;font-weight:700;color:${col};">${s>=0?'+':''}${s.toFixed(2)}</span>
        </div>
        <div style="height:6px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden;">
          <div style="height:100%;width:${barW}%;background:${col};border-radius:3px;transition:width 0.4s;"></div>
        </div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);margin-top:2px;">${comp.label||''}</div>
      </div>`;
    }).join('');
  }

  // ── Candlestick patterns ──
  const candleEl = document.getElementById('sent-candles');
  if (candleEl && d.candle_signals) {
    candleEl.innerHTML = d.candle_signals.map(c =>
      `<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);">
        <span style="color:${c.color||'var(--t2)'};">${c.pattern}</span>
        <span style="color:var(--dim);font-size:0.62rem;">${c.date}</span>
      </div>
      <div style="font-size:0.6rem;color:var(--dim);margin-bottom:4px;">${c.emotion}</div>`
    ).join('') || '<div style="color:var(--dim);">No strong patterns in window</div>';
  }

  // ── Pivot interactions ──
  const pivEl = document.getElementById('sent-pivots');
  if (pivEl && d.pivot_details) {
    pivEl.innerHTML = d.pivot_details.map(l=>`<div style="padding:3px 0;color:var(--t2);">${l}</div>`).join('')
      + `<div style="margin-top:8px;padding:6px 8px;background:rgba(0,0,0,0.2);border-left:3px solid ${d.components?.pivot?.score>0?'#26a69a':'#ef5350'};">
        ${d.components?.pivot?.label||''}</div>`;
  }

  // ── Volatility ──
  const volEl = document.getElementById('sent-vol');
  if (volEl) {
    const vd = d.components?.volatility || {};
    volEl.innerHTML = (vd.details||[]).map(l=>`<div style="padding:2px 0;color:var(--t2);">${l}</div>`).join('')
      + `<div style="margin-top:8px;padding:6px 8px;background:rgba(0,0,0,0.2);border-left:3px solid ${vd.score>0?'#26a69a':'#ef5350'};">${vd.label||''}</div>`;
  }

  // ── Trend ──
  const trendEl = document.getElementById('sent-trend');
  if (trendEl) {
    const td = d.components?.trend||{};
    trendEl.innerHTML = (td.details||[]).map(l=>`<div style="padding:2px 0;color:var(--t2);">${l}</div>`).join('')
      + `<div style="margin-top:8px;padding:6px 8px;background:rgba(0,0,0,0.2);border-left:3px solid ${td.score>0?'#26a69a':'#ef5350'};">${td.label||''}</div>`;
  }

  // ── Emotion state ──
  const emoEl = document.getElementById('sent-emotion');
  if (emoEl) {
    emoEl.innerHTML = `<div style="font-family:Orbitron,sans-serif;font-size:1.2rem;color:${d.emotion_color};font-weight:900;margin-bottom:10px;">${d.emotion}</div>`
      + `<div style="color:var(--t2);">Composite: <b style="color:${d.emotion_color};">${(d.composite||0).toFixed(3)}</b></div>`
      + `<div style="color:var(--dim);font-size:0.65rem;margin-top:4px;">-1.0 = EXTREME FEAR · 0 = NEUTRAL · +1.0 = EXTREME GREED</div>`;
  }

  // ── Sentiment history chart ──
  const hcvs = document.getElementById('sent-history-chart');
  if (hcvs && d.history && d.history.length > 1) {
    const W = hcvs.offsetWidth||700, H=148;
    const dpr2=window.devicePixelRatio||1;
    hcvs.width=W*dpr2; hcvs.height=H*dpr2;
    hcvs.style.width=W+'px'; hcvs.style.height=H+'px';
    const hctx=hcvs.getContext('2d'); hctx.scale(dpr2,dpr2);
    const hist=d.history, nH=hist.length;
    const PAD={t:10,r:8,b:20,l:36};
    const cW=W-PAD.l-PAD.r, cH=H-PAD.t-PAD.b;
    hctx.fillStyle='#060f16'; hctx.fillRect(0,0,W,H);
    // Zero line
    const y0=PAD.t+cH/2;
    hctx.strokeStyle='rgba(255,255,255,0.1)'; hctx.lineWidth=0.5; hctx.setLineDash([4,4]);
    hctx.beginPath(); hctx.moveTo(PAD.l,y0); hctx.lineTo(W-PAD.r,y0); hctx.stroke(); hctx.setLineDash([]);
    // +0.3 / -0.3 lines
    [0.3,-0.3].forEach(v=>{
      const y=PAD.t+cH*(1-(v+1)/2);
      hctx.strokeStyle='rgba(255,255,255,0.05)'; hctx.lineWidth=0.5; hctx.setLineDash([2,4]);
      hctx.beginPath(); hctx.moveTo(PAD.l,y); hctx.lineTo(W-PAD.r,y); hctx.stroke();
    }); hctx.setLineDash([]);
    // Y labels
    hctx.fillStyle='#3a5a70'; hctx.font='8px Share Tech Mono'; hctx.textAlign='right';
    hctx.fillText('+1',PAD.l-2,PAD.t+4); hctx.fillText('0',PAD.l-2,y0+3); hctx.fillText('-1',PAD.l-2,H-PAD.b);
    // Line
    const xS=i=>PAD.l+i/(nH-1)*cW, yS=v=>PAD.t+cH*(1-(v+1)/2);
    hctx.beginPath();
    hist.forEach((h2,i)=>i===0?hctx.moveTo(xS(i),yS(h2.score)):hctx.lineTo(xS(i),yS(h2.score)));
    hctx.strokeStyle='rgba(0,212,255,0.8)'; hctx.lineWidth=1.5; hctx.stroke();
    // Fill
    hctx.lineTo(xS(nH-1),y0); hctx.lineTo(xS(0),y0); hctx.closePath();
    hctx.fillStyle='rgba(0,212,255,0.07)'; hctx.fill();
    // Dots for extremes
    hist.forEach((h2,i)=>{
      if(Math.abs(h2.score)>0.5){
        hctx.fillStyle=h2.score>0?'#26a69a':'#ef5350';
        hctx.beginPath(); hctx.arc(xS(i),yS(h2.score),3,0,Math.PI*2); hctx.fill();
      }
    });
  }

  // ── Signal card ──
  const sigCard = document.getElementById('sent-signal-card');
  const sigText = document.getElementById('sent-signal-text');
  if (sigCard && sigText) {
    sigCard.style.borderLeftColor = d.signal_color||'var(--cyan)';
    sigText.innerHTML=`<div style="color:${d.signal_color||'var(--cyan)'};margin-bottom:8px;font-size:0.82rem;">${d.signal||''}</div>`
      +`<div style="color:var(--dim);font-size:0.7rem;border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;margin-top:4px;">${d.signal_action||''}</div>`;
  }
}

async function initFundamentalsPage() {
  const sel = document.getElementById('fund-sym');
  if (sel.options.length > 1) return;
  try {
    const d = await api('all_symbols');
    const syms = (d.equities || []).sort((a,b) => a.symbol.localeCompare(b.symbol));
    syms.forEach(s => {
      const o = document.createElement('option');
      o.value = s.symbol;
      o.textContent = s.symbol + ' — ' + (s.name || '');
      sel.appendChild(o);
    });
  } catch(e) {}
}

function fundLoadPeer(sym) {
  // Set the dropdown to the peer symbol and load its analysis
  const sel = document.getElementById('fund-sym');
  if (!sel) return;
  // If the option exists, select it
  let found = false;
  for (let i = 0; i < sel.options.length; i++) {
    if (sel.options[i].value === sym) {
      sel.selectedIndex = i;
      found = true;
      break;
    }
  }
  // If not in dropdown yet (dropdown may not be populated), set value directly
  if (!found) sel.value = sym;
  // Scroll to top of the page content
  const pg = document.getElementById('page-fundamentals');
  if (pg) pg.scrollTop = 0;
  loadFundamentals();
}
function initSentimentPage() {
  var sel = document.getElementById('sent-sym');
  if (!sel || sel.options.length > 1) return;
  api('all_symbols').then(function(d) {
    var all = (d.indices||[]).concat(d.equities||[]).concat(d.commodities||[]);
    all.forEach(function(s) {
      var o = document.createElement('option');
      o.value = typeof s==='object' ? s.symbol : s;
      o.textContent = typeof s==='object' ? s.symbol+(s.name?' — '+s.name:'') : s;
      sel.appendChild(o);
    });
  }).catch(function(){});
}

// ════════════════════════════════════════════════════════════════
// EXTERNAL SENTIMENT — News + Analyst NLP
// ════════════════════════════════════════════════════════════════

let _extData = null;       // cache last fetch
let _allHeadlines = [];    // for filtering

async function loadExternalSentiment() {
  const sym = document.getElementById('sent-sym')?.value;
  if (!sym) return;

  const loadEl   = document.getElementById('ext-loading');
  const errEl    = document.getElementById('ext-error');
  const contEl   = document.getElementById('ext-content');
  const btnEl    = document.getElementById('ext-refresh-btn');

  if (loadEl)  { loadEl.style.display = 'flex'; }
  if (errEl)   { errEl.style.display  = 'none'; }
  if (contEl)  { contEl.style.display = 'none'; }
  if (btnEl)   { btnEl.textContent = '⟳ LOADING...'; btnEl.disabled = true; }

  try {
    const d = await api('external_sentiment', {symbol: sym});
    _extData = d;
    _allHeadlines = d.all_headlines || [];
    renderExternalSentiment(d);
  } catch(e) {
    if (errEl) { errEl.style.display='block'; errEl.textContent='⚠ '+e.message; }
  } finally {
    if (loadEl) loadEl.style.display = 'none';
    if (btnEl)  { btnEl.textContent = '⟳ REFRESH'; btnEl.disabled = false; }
  }
}

function renderExternalSentiment(d) {
  const contEl = document.getElementById('ext-content');
  if (!contEl) return;
  contEl.style.display = 'block';

  const score  = d.external_score || 0;
  const color  = d.external_color || '#7aa8c0';
  const label  = d.external_label || 'NEUTRAL';
  const total  = d.total_items || 0;

  // Badge
  const badge = document.getElementById('ext-total-badge');
  if (badge) badge.textContent = total + ' articles analysed';

  // ── External score display ──────────────────────────────────
  const scoreEl = document.getElementById('ext-score-display');
  if (scoreEl) {
    const barW = Math.round((score + 1) / 2 * 100);
    scoreEl.innerHTML = `
      <div style="font-family:Orbitron,sans-serif;font-size:2.2rem;font-weight:900;
                  color:${color};text-shadow:0 0 20px ${color}44;margin-bottom:4px;">
        ${score >= 0 ? '+' : ''}${score.toFixed(3)}
      </div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:${color};
                  letter-spacing:2px;margin-bottom:10px;">${label}</div>
      <div style="height:8px;background:rgba(255,255,255,0.06);border-radius:4px;overflow:hidden;">
        <div style="width:${barW}%;height:100%;background:${color};border-radius:4px;transition:width 0.8s;"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-family:Share Tech Mono,monospace;
                  font-size:0.58rem;color:var(--dim);margin-top:3px;">
        <span>BEARISH −1</span><span>NEUTRAL 0</span><span>+1 BULLISH</span>
      </div>`;
  }

  // ── Source breakdown bars (incl. LLM mgmt_tone) ─────────────
  const srcEl = document.getElementById('ext-source-bars');
  if (srcEl && d.source_scores) {
    const sources = [
      {key:'yahoo',     label:'Yahoo Finance News',  icon:'📰'},
      {key:'google',    label:'Google News (India)', icon:'🌐'},
      {key:'analyst',   label:'Analyst Consensus',   icon:'📊'},
      {key:'mgmt_tone', label:'Mgmt Tone (AI/LLM)',  icon:'🤖'},
    ];
    srcEl.innerHTML = sources.map(s => {
      const sc = d.source_scores[s.key];
      if (sc === null || sc === undefined) return `
        <div style="display:flex;justify-content:space-between;font-family:Share Tech Mono,monospace;font-size:0.62rem;">
          <span style="color:var(--dim);">${s.icon} ${s.label}</span>
          <span style="color:var(--dim);">NO DATA</span>
        </div>`;
      const col2 = sc>=0.1?'#26a69a':sc<=-0.1?'#ef5350':'#7aa8c0';
      const bw   = Math.round((sc+1)/2*100);
      return `<div>
        <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
          <span style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--t2);">${s.icon} ${s.label}</span>
          <span style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:${col2};font-weight:700;">${sc>=0?'+':''}${sc.toFixed(3)}</span>
        </div>
        <div style="height:5px;background:rgba(255,255,255,0.06);border-radius:3px;">
          <div style="width:${bw}%;height:100%;background:${col2};border-radius:3px;transition:width 0.6s;"></div>
        </div>
      </div>`;
    }).join('');
  }

  // ── LLM Earnings Extraction panel ───────────────────────────
  const llmEl = document.getElementById('ext-llm-panel');
  if (llmEl) {
    const llm = d.llm_extraction;
    if (llm && (llm.mgmt_tone !== null && llm.mgmt_tone !== undefined)) {
      const tone    = llm.mgmt_tone || 0;
      const toneCol = tone >= 0.2 ? '#26a69a' : tone <= -0.2 ? '#ef5350' : '#7aa8c0';
      const tonePct = Math.round(((tone + 1) / 2) * 100);
      const toneLabel = tone >= 0.3 ? 'POSITIVE' : tone <= -0.3 ? 'NEGATIVE' : 'NEUTRAL';
      const guidCol = {raised:'#26a69a', lowered:'#ef5350', maintained:'#7aa8c0', none:'#555'}[llm.guidance_direction||'none'] || '#555';
      const guidIcon = {raised:'⬆', lowered:'⬇', maintained:'➡', none:'—'}[llm.guidance_direction||'none'] || '—';
      const risks = (llm.key_risks || []).slice(0, 4);
      const method = llm.extractor_method || 'rules';
      const methodBadge = {ollama:'🟢 Ollama (Llama-3)', llama_cpp:'🟡 llama-cpp (GGUF)', rules:'🔵 Rule-based NLP', cached:'📦 Cached'}[method] || method;

      llmEl.style.display = 'block';
      llmEl.innerHTML = `
        <div style="background:rgba(41,98,255,0.06);border:1px solid rgba(0,212,255,0.2);border-radius:6px;padding:12px 14px;margin-bottom:14px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
            <div style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--cyan);letter-spacing:1px;">🤖 AI EARNINGS EXTRACTION</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);">${methodBadge}</div>
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:10px;">
            <div style="text-align:center;">
              <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);margin-bottom:3px;">MGMT TONE</div>
              <div style="font-size:1rem;font-weight:700;color:${toneCol};">${tone >= 0 ? '+' : ''}${tone.toFixed(2)}</div>
              <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:${toneCol};">${toneLabel}</div>
            </div>
            <div style="text-align:center;">
              <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);margin-bottom:3px;">GUIDANCE</div>
              <div style="font-size:1rem;font-weight:700;color:${guidCol};">${guidIcon}</div>
              <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:${guidCol};">${(llm.guidance_direction||'none').toUpperCase()}</div>
            </div>
            <div style="text-align:center;">
              <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);margin-bottom:3px;">EPS BEAT</div>
              <div style="font-size:1rem;font-weight:700;color:${(llm.eps_beat_pct||0)>=0?'#26a69a':'#ef5350'};">
                ${llm.eps_beat_pct !== null && llm.eps_beat_pct !== undefined ? (llm.eps_beat_pct >= 0 ? '+' : '') + llm.eps_beat_pct.toFixed(1) + '%' : 'N/A'}
              </div>
              <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);">VS ESTIMATE</div>
            </div>
          </div>

          <div style="margin-bottom:8px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
              <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);">MANAGEMENT TONE GAUGE</span>
              <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:${toneCol};">${tonePct}%</span>
            </div>
            <div style="position:relative;height:6px;background:linear-gradient(90deg,#ef5350,rgba(255,255,255,0.1),#26a69a);border-radius:3px;">
              <div style="position:absolute;top:-3px;left:${tonePct}%;width:2px;height:12px;background:white;border-radius:1px;transform:translateX(-50%);"></div>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:3px;">
              <span style="font-family:Share Tech Mono,monospace;font-size:0.5rem;color:#ef5350;">NEGATIVE −1.0</span>
              <span style="font-family:Share Tech Mono,monospace;font-size:0.5rem;color:var(--dim);">NEUTRAL 0</span>
              <span style="font-family:Share Tech Mono,monospace;font-size:0.5rem;color:#26a69a;">POSITIVE +1.0</span>
            </div>
          </div>

          ${llm.revenue_growth_yoy !== null && llm.revenue_growth_yoy !== undefined ? `
          <div style="display:flex;justify-content:space-between;padding:4px 0;border-top:1px solid rgba(255,255,255,0.04);">
            <span style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);">Revenue Growth YoY</span>
            <span style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:${(llm.revenue_growth_yoy||0)>=0?'#26a69a':'#ef5350'};font-weight:700;">
              ${(llm.revenue_growth_yoy >= 0 ? '+' : '') + llm.revenue_growth_yoy.toFixed(1)}%
            </span>
          </div>` : ''}

          ${risks.length > 0 ? `
          <div style="margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.04);">
            <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);margin-bottom:5px;">⚠ KEY RISKS IDENTIFIED</div>
            ${risks.map(r => `
              <div style="display:flex;gap:6px;margin-bottom:3px;font-size:0.72rem;line-height:1.3;">
                <span style="color:#ef5350;margin-top:1px;">•</span>
                <span style="color:var(--text);">${r}</span>
              </div>`).join('')}
          </div>` : ''}
        </div>`;
    } else {
      llmEl.style.display = 'none';
    }
  }

  // ── Narrative WHY ────────────────────────────────────────────
  const narEl = document.getElementById('ext-narrative');
  if (narEl && d.narrative) {
    const n = d.narrative;
    let html = `<div style="padding:8px 12px;margin-bottom:12px;background:rgba(0,0,0,0.3);
                border-left:3px solid ${color};font-family:Share Tech Mono,monospace;
                font-size:0.72rem;color:${color};letter-spacing:1px;">
                ${n.why}</div>`;
    html += (n.paragraphs||[]).map(p =>
      `<p style="margin-bottom:10px;font-size:0.8rem;">${p}</p>`
    ).join('');
    narEl.innerHTML = html;
  }

  // ── Headlines ────────────────────────────────────────────────
  _hlSort = 'date';  // default to date sort
  renderHeadlines('all');

  // ── Analyst ──────────────────────────────────────────────────
  const analyst = d.analyst || {};
  const sumEl = document.getElementById('ext-analyst-summary');
  if (sumEl) {
    if (analyst.not_applicable) {
      sumEl.innerHTML = `<div style="padding:14px;font-family:Share Tech Mono,monospace;font-size:0.72rem;
        color:var(--dim);text-align:center;border:1px solid var(--border);background:var(--p2);">
        ℹ Analyst ratings are not applicable for indices and commodities.<br>
        <span style="color:var(--cyan);font-size:0.65rem;">Select an individual equity stock (e.g. RELIANCE, TCS, HDFC)</span>
      </div>`;
    } else if (analyst.analyst_count > 0) {
      const upside = analyst.upside_pct;
      const upCol  = upside >= 0 ? '#00ff88' : '#ef5350';
      sumEl.innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">
          <div class="stat" style="padding:10px;">
            <span class="val" style="color:${analyst.color};font-size:1.4rem;">${analyst.recommendation||'—'}</span>
            <span class="lbl">CONSENSUS</span>
          </div>
          <div class="stat" style="padding:10px;">
            <span class="val" style="color:var(--gold);font-size:1.2rem;">${analyst.analyst_count}</span>
            <span class="lbl">ANALYSTS</span>
          </div>
        </div>
        ${analyst.target_price ? `
        <div style="display:flex;justify-content:space-between;padding:6px 10px;
             background:var(--p2);border:1px solid var(--border);font-family:Share Tech Mono,monospace;font-size:0.72rem;margin-bottom:6px;">
          <span style="color:var(--dim);">AVG TARGET</span>
          <span style="color:var(--gold);font-weight:700;">₹${analyst.target_price.toLocaleString('en-IN')}</span>
        </div>` : ''}
        ${upside !== null ? `
        <div style="display:flex;justify-content:space-between;padding:6px 10px;
             background:var(--p2);border:1px solid var(--border);font-family:Share Tech Mono,monospace;font-size:0.72rem;">
          <span style="color:var(--dim);">UPSIDE / DOWNSIDE</span>
          <span style="color:${upCol};font-weight:700;">${upside>=0?'+':''}${upside}%</span>
        </div>` : ''}`;
    } else {
      sumEl.innerHTML = `<div style="padding:14px;color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.72rem;text-align:center;border:1px solid var(--border);background:var(--p2);">
        No analyst coverage found for this symbol on Yahoo Finance</div>`;
    }
  }

  // Analyst recent actions
  const actEl = document.getElementById('ext-analyst-actions');
  if (actEl && analyst.recent_actions && analyst.recent_actions.length > 0) {
    actEl.innerHTML = `<div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);
      letter-spacing:2px;padding:4px 0 8px;">RECENT RATING CHANGES</div>` +
      analyst.recent_actions.map(a => `
        <div style="display:flex;align-items:center;gap:8px;padding:5px 0;
             border-bottom:1px solid var(--border);font-size:0.75rem;">
          <span style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);min-width:72px;">${a.date}</span>
          <span style="flex:1;color:var(--t2);">${a.firm}</span>
          <span style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:${a.color};font-weight:700;">${a.grade}</span>
        </div>`).join('');
  }

  // ── Themes ────────────────────────────────────────────────────
  const themesEl = document.getElementById('ext-themes');
  const themeColors = {
    earnings:'#26a69a', management:'#ffcc00', expansion:'#00d4ff',
    regulatory:'#ef5350', debt:'#ff8800', dividend:'#cc88ff',
    outlook:'#7FFFD4', macro:'#B5B5FF',
  };
  if (themesEl && d.narrative && d.narrative.themes) {
    if (d.narrative.themes.length === 0) {
      themesEl.innerHTML = '<span style="color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.65rem;">No dominant themes detected</span>';
    } else {
      themesEl.innerHTML = d.narrative.themes.map(t => {
        const col = themeColors[t] || '#7aa8c0';
        return `<span style="font-family:Share Tech Mono,monospace;font-size:0.65rem;letter-spacing:1px;
          padding:3px 10px;border:1px solid ${col}44;color:${col};background:${col}11;">
          ${t.toUpperCase()}</span>`;
      }).join('');
    }
  }

  // ── Blend verdict ─────────────────────────────────────────────
  const blendEl = document.getElementById('ext-blend-text');
  if (blendEl) {
    const ohlcScore  = parseFloat(document.getElementById('sent-score-label')?.textContent||0);
    const newsScore  = score;
    const blended    = isNaN(ohlcScore) ? newsScore : (ohlcScore * 0.65 + newsScore * 0.35);
    const blendCol   = blended>=0.2?'#00ff88':blended>=-0.2?'#7aa8c0':'#ef5350';
    const agreement  = (ohlcScore >= 0 && newsScore >= 0) || (ohlcScore < 0 && newsScore < 0);
    const divergence = Math.abs((isNaN(ohlcScore)?0:ohlcScore) - newsScore);

    blendEl.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px;">
        <div class="stat" style="padding:10px;">
          <span class="val" style="font-size:1.1rem;color:var(--cyan);">${isNaN(ohlcScore)?'—':ohlcScore>=0?'+'+ohlcScore.toFixed(2):ohlcScore.toFixed(2)}</span>
          <span class="lbl">OHLC SCORE</span>
        </div>
        <div class="stat" style="padding:10px;">
          <span class="val" style="font-size:1.1rem;color:${color};">${newsScore>=0?'+':''}${newsScore.toFixed(3)}</span>
          <span class="lbl">NEWS SCORE</span>
        </div>
        <div class="stat" style="padding:10px;">
          <span class="val" style="font-size:1.1rem;color:${blendCol};">${blended>=0?'+':''}${blended.toFixed(3)}</span>
          <span class="lbl">BLENDED</span>
        </div>
      </div>
      <div style="padding:10px 14px;background:${agreement?'rgba(0,255,136,0.05)':'rgba(255,204,0,0.05)'};
           border-left:3px solid ${agreement?'#26a69a':'#ffcc00'};font-size:0.8rem;line-height:1.6;">
        ${agreement
          ? `<b style="color:#26a69a">SIGNALS ALIGNED</b> — Both price action and news sentiment point in the same direction.
             This strengthens conviction in the current market direction for this symbol.`
          : `<b style="color:#ffcc00">DIVERGENCE DETECTED</b> — Price action and news sentiment are giving conflicting signals
             (divergence: ${divergence.toFixed(2)}). This often signals a potential reversal or consolidation phase.
             Exercise caution and wait for alignment before taking a position.`}
      </div>`;
  }
}

// ── Headline sort/filter state ───────────────────────────────────
let _hlFilter = 'all';
let _hlSort   = 'date';   // 'date' | 'score'

function toggleHlSort() {
  _hlSort = _hlSort === 'date' ? 'score' : 'date';
  const btn = document.getElementById('hl-sort-btn');
  if (btn) btn.textContent = _hlSort === 'date' ? '🕐 SORT: DATE' : '📊 SORT: SCORE';
  renderHeadlines(_hlFilter);
}

function renderHeadlines(filter) {
  _hlFilter = filter || 'all';
  const el = document.getElementById('ext-headlines');
  if (!el) return;

  // Update filter button states
  ['all','bull','bear','neut'].forEach(f => {
    const btn = document.getElementById('hl-btn-'+f);
    if (btn) btn.style.background = f===filter ? 'rgba(0,212,255,0.12)' : 'transparent';
  });

  // Filter
  let items = [..._allHeadlines];
  if (filter === 'bull') items = items.filter(h => h.score >= 0.10);
  if (filter === 'bear') items = items.filter(h => h.score <= -0.10);
  if (filter === 'neut') items = items.filter(h => h.score > -0.10 && h.score < 0.10);

  // Sort
  if (_hlSort === 'date') {
    items.sort((a, b) => {
      const da = a.published || ''; const db = b.published || '';
      return db.localeCompare(da);  // newest first
    });
  } else {
    items.sort((a, b) => Math.abs(b.score) - Math.abs(a.score));  // most opinionated first
  }

  if (!items.length) {
    el.innerHTML = `<div style="padding:20px;color:var(--dim);font-family:Share Tech Mono,monospace;
      font-size:0.72rem;text-align:center;">No ${filter} headlines found</div>`;
    return;
  }

  el.innerHTML = items.map(h => {
    const col  = h.color || '#7aa8c0';
    const barW = Math.round((h.score + 1) / 2 * 100);
    const hasUrl = h.url && h.url.startsWith('http');
    const badgeClass = h.score >= 0.1 ? 'bg' : h.score <= -0.1 ? 'br' : 'bd';
    return `<div style="background:var(--p2);border:1px solid var(--border);border-radius:6px;padding:12px 16px;margin:8px 12px;
                 border-left:4px solid ${col};transition:all 0.2s;cursor:${hasUrl?'pointer':'default'};box-shadow:0 2px 6px rgba(0,0,0,0.15);"
              onclick="${hasUrl ? `window.open('${h.url.replace(/'/g,"\'")}','_blank')` : ''}"
              onmouseover="this.style.borderColor='${col}';this.style.transform='translateY(-1px)';"
              onmouseout="this.style.borderColor='var(--border)';this.style.transform='none';">
      <!-- Top Meta Info -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;font-family:Share Tech Mono,monospace;font-size:0.62rem;">
        <span style="color:var(--dim);">📰 ${h.source || 'Yahoo Finance'}</span>
        <span class="badge ${badgeClass}" style="padding:1px 6px;font-size:0.55rem;">${h.label}</span>
      </div>
      <!-- Title -->
      <h4 style="font-size:0.8rem;line-height:1.4;font-weight:600;margin-bottom:6px;color:var(--white);">${h.title}</h4>
      <!-- Snippet -->
      ${h.snippet ? `<p style="font-size:0.68rem;color:var(--t2);line-height:1.4;margin-bottom:8px;">${h.snippet}</p>` : ''}
      
      <!-- Bottom Progress Bar & Score -->
      <div style="display:flex;align-items:center;gap:10px;margin-top:6px;">
        <span style="font-family:Share Tech Mono,monospace;font-size:0.68rem;font-weight:700;color:${col};min-width:48px;">
          ${h.icon} ${h.score>=0?'+':''}${h.score.toFixed(2)}
        </span>
        <div style="flex:1;height:4px;background:rgba(255,255,255,0.04);border-radius:2px;overflow:hidden;">
          <div style="width:${barW}%;height:100%;background:${col};border-radius:2px;"></div>
        </div>
        <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);">${h.published || ''}</span>
      </div>
    </div>`;
  }).join('');
}


function filterHeadlines(filter) {
  renderHeadlines(filter);
}


// ════════════════════════════════════════════════════════════════════
// SENTIMENT DB — Stats + Labelling
// ════════════════════════════════════════════════════════════════════

async function testSentimentDb() {
  const btn = document.getElementById('db-test-btn');
  if (btn) { btn.textContent = '⟳ TESTING...'; btn.disabled = true; }
  try {
    const d = await api('sentiment_db_test');
    const el = document.getElementById('db-status-content');
    if (d.ok) {
      el.innerHTML = `<div style="padding:10px;background:rgba(0,255,136,0.05);border:1px solid rgba(0,255,136,0.2);
        font-family:Share Tech Mono,monospace;font-size:0.72rem;">
        <span style="color:#00ff88;">✓ DB WRITE SUCCESSFUL</span><br>
        <span style="color:var(--dim);">Path: ${d.db_path}</span><br>
        <span style="color:var(--cyan);">Total rows in news_sentiment: ${d.total_rows}</span><br>
        <span style="color:var(--dim);font-size:0.65rem;">Now analyse a stock — headlines will be saved automatically.</span>
      </div>`;
    } else {
      el.innerHTML = `<div style="padding:10px;background:rgba(255,51,85,0.05);border:1px solid rgba(255,51,85,0.2);
        font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--red);">
        ✗ DB WRITE FAILED: ${d.error}<br>
        <pre style="font-size:0.6rem;color:var(--dim);white-space:pre-wrap;">${d.trace||''}</pre>
      </div>`;
    }
  } catch(e) {
    const el = document.getElementById('db-status-content');
    if (el) el.innerHTML = `<div class="err">Test failed: ${e.message}</div>`;
  } finally {
    if (btn) { btn.textContent = '⚡ TEST DB WRITE'; btn.disabled = false; }
  }
}

async function loadSentimentDbStats() {
  const sym = document.getElementById('sent-sym')?.value || '';
  const btn = document.getElementById('db-refresh-btn');
  if (btn) { btn.textContent = 'LOADING...'; btn.disabled = true; }
  try {
    const [statsRes, accRes] = await Promise.allSettled([
      api('sentiment_db_stats', {symbol: sym}),
      api('market_feedback',    {action: 'report', ...(sym ? {symbol: sym} : {})}),
    ]);
    const d  = statsRes.status  === 'fulfilled' ? statsRes.value  : {};
    const ac = accRes.status === 'fulfilled' ? accRes.value : null;
    renderDbStats(d, ac);
  } catch(e) {
    const el = document.getElementById('db-status-content');
    if (el) el.innerHTML = `<div class="err">Stats error: ${e.message}</div>`;
  } finally {
    if (btn) { btn.textContent = 'REFRESH STATS'; btn.disabled = false; }
  }
}

function renderDbStats(d, accuracy) {
  const el = document.getElementById('db-status-content');
  if (!el) return;
  const s       = d.stats || {};
  const total   = s.total_headlines  || 0;
  const syms    = s.unique_symbols   || 0;
  const mktLbl  = s.market_labelled  || 0;
  const calib   = s.calibrated       || 0;
  const predAcc = s.prediction_accuracy;

  // ── Accuracy section ──────────────────────────────────────────────
  let accHtml = '';
  if (accuracy && !accuracy.error && accuracy.total_labelled) {
    const vAcc = accuracy.vader_accuracy || 0;
    const cAcc = accuracy.calibrated_accuracy;
    const imp  = accuracy.improvement_pp;
    const mae  = accuracy.vader_mae;
    const vPct = Math.round(vAcc*100);
    const cPct = cAcc ? Math.round(cAcc*100) : null;
    const vCol = vAcc >= 0.65 ? 'var(--green)' : vAcc >= 0.55 ? 'var(--gold)' : 'var(--red)';
    const cCol = (cAcc && cAcc > vAcc) ? 'var(--green)' : 'var(--gold)';

    accHtml = `<div style="margin-bottom:14px;">
      <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--cyan);letter-spacing:2px;margin-bottom:10px;">
        MARKET FEEDBACK ACCURACY (${accuracy.total_labelled} labelled · ${accuracy.period||''})
      </div>
      <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:10px;">
        <div>
          <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
            <span style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);">VADER direction accuracy</span>
            <span style="font-family:Share Tech Mono,monospace;font-size:0.75rem;font-weight:700;color:${vCol};">${vPct}%</span>
          </div>
          <div style="height:8px;background:rgba(255,255,255,0.06);border-radius:4px;overflow:hidden;">
            <div style="width:${vPct}%;height:100%;background:${vCol};border-radius:4px;"></div>
          </div>
          <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);margin-top:2px;">
            ${vAcc<0.55?'Below chance — market model will improve significantly':vAcc<0.65?'Moderate — model is calibrating':'Good baseline accuracy'}
          </div>
        </div>
        ${cAcc ? `<div>
          <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
            <span style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);">Market-trained model accuracy</span>
            <span style="font-family:Share Tech Mono,monospace;font-size:0.75rem;font-weight:700;color:${cCol};">
              ${cPct}% <span style="font-size:0.6rem;color:${imp>=0?'var(--green)':'var(--red)'};">(${imp>=0?'+':''}${imp}pp)</span>
            </span>
          </div>
          <div style="height:8px;background:rgba(255,255,255,0.06);border-radius:4px;overflow:hidden;">
            <div style="width:${cPct}%;height:100%;background:${cCol};border-radius:4px;"></div>
          </div>
        </div>` : `<div style="padding:7px 10px;background:rgba(255,204,0,0.04);border:1px solid rgba(255,204,0,0.15);font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--gold);">
          Model not trained yet. Run: <code style="color:var(--cyan);">python core/market_feedback.py --train-only</code>
        </div>`}
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px;">
        <div class="stat" style="padding:8px;"><span class="val" style="font-size:1rem;color:var(--gold);">${accuracy.total_labelled}</span><span class="lbl">MKT LABELLED</span></div>
        <div class="stat" style="padding:8px;"><span class="val" style="font-size:1rem;color:var(--cyan);">${mae?mae.toFixed(4):'—'}</span><span class="lbl">VADER MAE</span></div>
        <div class="stat" style="padding:8px;"><span class="val" style="font-size:1rem;color:${predAcc>=0.65?'var(--green)':'var(--gold)'};">${predAcc?Math.round(predAcc*100)+'%':'—'}</span><span class="lbl">MODEL ACC</span></div>
      </div>
      ${accuracy.avg_returns_by_label && Object.keys(accuracy.avg_returns_by_label).length ? `
      <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">VADER LABEL vs ACTUAL 5-DAY MARKET RETURN</div>
      <div style="border:1px solid var(--border);">
        <div style="display:grid;grid-template-columns:1fr 50px 80px 60px;padding:4px 8px;background:rgba(0,0,0,0.3);font-family:Share Tech Mono,monospace;font-size:0.52rem;color:var(--dim);letter-spacing:1px;">
          <div>VADER SAID</div><div>N</div><div>AVG 5D RETURN</div><div>HIT RATE</div>
        </div>
        ${['STRONGLY BULLISH','BULLISH','NEUTRAL','BEARISH','STRONGLY BEARISH'].map(lbl=>{
          const x = accuracy.avg_returns_by_label[lbl];
          if (!x) return '';
          const ret=x.avg_5d||0;
          const lc=lbl.includes('BULL')?'var(--green)':lbl.includes('BEAR')?'var(--red)':'var(--dim)';
          const hc=x.hit_rate>=0.6?'var(--green)':x.hit_rate>=0.5?'var(--gold)':'var(--red)';
          return `<div style="display:grid;grid-template-columns:1fr 50px 80px 60px;padding:4px 8px;border-top:1px solid var(--border);">
            <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:${lc};">${lbl}</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);">${x.count}</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:${ret>0?'var(--green)':'var(--red)'}">${ret>0?'▲':'▼'}${Math.abs(ret).toFixed(2)}%</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:${hc};">${Math.round(x.hit_rate*100)}%</div>
          </div>`;
        }).join('')}
      </div>` : ''}
    </div>`;
  } else {
    accHtml = `<div style="padding:10px 12px;background:rgba(255,204,0,0.04);border:1px solid rgba(255,204,0,0.15);font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--gold);margin-bottom:14px;">
      MARKET FEEDBACK: No labelled data yet.<br>
      <span style="color:var(--dim);">Run: </span><code style="color:var(--cyan);">python core/market_feedback.py --label-only</code>
      <span style="color:var(--dim);"> (needs headlines older than 7 days)</span>
    </div>`;
  }

  // ── DB stats ─────────────────────────────────────────────────────────
  const dist   = s.label_distribution || [];
  const maxCnt = Math.max(...dist.map(x=>x.cnt), 1);
  const distH  = dist.map(r=>{
    const c=r.label==='STRONGLY BULLISH'?'#00ff88':r.label==='BULLISH'?'#26a69a':r.label==='STRONGLY BEARISH'?'#ef5350':r.label==='BEARISH'?'#ffcc00':'#7aa8c0';
    return `<div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;">
      <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;min-width:135px;color:${c};">${r.label}</span>
      <div style="flex:1;height:5px;background:rgba(255,255,255,0.06);border-radius:3px;">
        <div style="width:${Math.round(r.cnt/maxCnt*100)}%;height:100%;background:${c};border-radius:3px;"></div>
      </div>
      <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);min-width:32px;text-align:right;">${r.cnt}</span>
    </div>`;
  }).join('');

  const topH = (s.top_symbols||[]).slice(0,8).map(r=>
    `<span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;padding:2px 7px;background:rgba(0,212,255,0.06);border:1px solid rgba(0,212,255,0.15);color:var(--cyan);">
    ${r.symbol} <span style="color:var(--dim);">${r.total}${r.labelled?'/'+r.labelled+'✓':''}</span></span>`
  ).join('');

  el.innerHTML = `${accHtml}
    <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:2px;margin-bottom:8px;">DATABASE SUMMARY</div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px;">
      <div class="stat" style="padding:8px;"><span class="val" style="color:var(--gold);font-size:1.1rem;">${total.toLocaleString()}</span><span class="lbl">HEADLINES</span></div>
      <div class="stat" style="padding:8px;"><span class="val" style="color:var(--cyan);font-size:1.1rem;">${syms}</span><span class="lbl">SYMBOLS</span></div>
      <div class="stat" style="padding:8px;"><span class="val" style="color:var(--green);font-size:1.1rem;">${mktLbl}</span><span class="lbl">MKT LABELLED</span></div>
      <div class="stat" style="padding:8px;"><span class="val" style="color:var(--purple);font-size:1.1rem;">${calib}</span><span class="lbl">CALIBRATED</span></div>
    </div>
    ${distH}
    ${topH?`<div style="display:flex;gap:5px;flex-wrap:wrap;margin-top:8px;">${topH}</div>`:''}
    <div style="margin-top:10px;padding:8px 12px;background:rgba(0,0,0,0.2);border:1px solid var(--border);font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);line-height:1.8;">
      <b style="color:var(--cyan);">MARKET SELF-IMPROVING LOOP:</b> Headlines saved with VADER score → 7 days later price reaction measured → market_label assigned → model trains → calibrated_score improves future predictions<br>
      <span style="font-size:0.55rem;">Latest fetch: ${s.latest_fetch||'—'} · Latest market label: ${s.latest_market_label||'never'}</span>
    </div>`;
}
// Label a headline directly from the UI
async function labelHeadline(symbol, title, label) {
  try {
    const d = await api('sentiment_label', {symbol, title, label});
    if (d.ok) {
      console.log('[LABEL] Saved:', label, 'for', title.substring(0,40));
      // Refresh stats
      loadSentimentDbStats();
    }
  } catch(e) { console.error('[LABEL] Error:', e.message); }
}


async function fetchAllSymbolsNews() {
  const btn = document.getElementById('db-fetchall-btn');
  if (btn) { btn.textContent = '⬇ FETCHING ALL... (see terminal)'; btn.disabled = true; }
  try {
    const d = await api('sentiment_fetch_all', {});
    const el = document.getElementById('db-status-content');
    if (el) {
      el.innerHTML = `<div style="padding:10px;background:rgba(0,255,136,0.04);
        border:1px solid rgba(0,255,136,0.2);font-family:Share Tech Mono,monospace;font-size:0.72rem;">
        <b style="color:#00ff88;">✓ ${d.message}</b><br>
        <span style="color:var(--dim);">Watch your terminal window for live progress.</span><br>
        <span style="color:var(--dim);">Click REFRESH STATS in ~2 minutes to see the results.</span>
      </div>`;
      // Auto-refresh stats after 90 seconds
      setTimeout(loadSentimentDbStats, 90000);
    }
  } catch(e) {
    const el = document.getElementById('db-status-content');
    if (el) el.innerHTML = `<div class="err">Fetch error: ${e.message}</div>`;
  } finally {
    setTimeout(() => {
      if (btn) { btn.textContent = '⬇ FETCH ALL SYMBOLS'; btn.disabled = false; }
    }, 5000);
  }
}


// ═══════════════════════════════════════════════════════════════════
// SYNCHRONIZED 3-CHART: BULK/BLOCK DEALS + NEWS SENTIMENT + PRICE
// ═══════════════════════════════════════════════════════════════
// UNIFIED CHART: PRICE + NEWS SENTIMENT + BULK/BLOCK DEALS
// Single canvas, dual Y-axes, shared time axis, crosshair hover
// ═══════════════════════════════════════════════════════════════

let _tcSym = '', _tcDays = 90;

function reloadTripleChart(days) {
  _tcDays = days;
  [30,60,90,180].forEach(d => {
    const el = document.getElementById('tc-p-'+d);
    if (el) el.style.color = d===days ? 'var(--cyan)' : 'var(--dim)';
  });
  if (_tcSym) loadTripleChart(_tcSym);
}

async function loadTripleChart(sym) {
  if (!sym) return;
  _tcSym = sym;

  // FIX: Make the card and its ancestor containers visible before fetching.
  // The triple card sits inside ext-content which may still be hidden.
  // We force-show the card wrapper so offsetWidth is valid when canvas draws.
  const card = document.getElementById('sent-triple-card');
  if (card) card.style.display = 'block';

  // Also ensure ext-content is visible (in case external sentiment hasn't loaded yet)
  const extContent = document.getElementById('ext-content');
  if (extContent) extContent.style.display = 'block';

  const tl = document.getElementById('sent-triple-loading');
  const tc = document.getElementById('sent-triple-content');
  if (tl) tl.style.display = 'flex';
  if (tc) tc.style.display = 'none';

  try {
    // FIX: Fetch all 3 data sources in parallel — await ALL before drawing
    const [instRes, newsRes, priceRes] = await Promise.allSettled([
      api('institutional',   {symbol: sym, days: _tcDays}),
      api('sentiment_trend', {symbol: sym, days: _tcDays}),
      api('price_history',   {symbol: sym, days: _tcDays}),
    ]);

    if (tl) tl.style.display = 'none';

    // FIX: Show container THEN use triple rAF to guarantee layout is complete
    // before reading offsetWidth for canvas sizing
    if (tc) tc.style.display = 'block';

    const instD  = instRes.status  === 'fulfilled' ? instRes.value  : {};
    const newsD  = newsRes.status  === 'fulfilled' ? newsRes.value  : {};
    const priceD = priceRes.status === 'fulfilled' ? priceRes.value : {};

    // Guard: if price data empty show placeholder and return
    if (!priceD.dates || priceD.dates.length < 3) {
      const cvs = document.getElementById('unified-chart-canvas');
      if (cvs) {
        const ctx = cvs.getContext('2d');
        ctx.fillStyle = '#060f16'; ctx.fillRect(0, 0, cvs.offsetWidth || 600, 320);
        ctx.fillStyle = '#3a5a70'; ctx.font = '12px Share Tech Mono'; ctx.textAlign = 'center';
        ctx.fillText('No price data — fetch history first (Download History page)', (cvs.offsetWidth||600)/2, 160);
      }
      return;
    }

    // Triple rAF: first rAF queues after paint, second rAF runs after layout recalc
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          _drawUnifiedChart(instD, newsD, priceD);
        });
      });
    });

  } catch(e) {
    if (tl) tl.style.display = 'none';
    if (tc) tc.style.display = 'block';
    console.error('[UNIFIED CHART ERROR]', e);
  }
}

function _computeWeightedDeals(instD, dates) {
  // Build weighted net value map: BUY_value - SELL_value per date
  // Value = quantity × avg_price — gives true capital flow (not just share count)
  const weightedMap = {};
  const dealMap = instD.deal_map || {};
  Object.entries(dealMap).forEach(([dt, dm]) => {
    const deals = dm.deals || [];
    let buyVal = 0, sellVal = 0;
    deals.forEach(d => {
      const val = (d.qty || 0) * (d.price || 0);
      if (d.type === 'BUY') buyVal += val;
      else sellVal += val;
    });
    weightedMap[dt] = { buyVal, sellVal, net: buyVal - sellVal };
  });

  // Compute 5-day rolling cumulative pressure index (normalized -1 to +1)
  const pressureMap = {};
  const window5 = 5;
  const netVals  = dates.map(d => (weightedMap[d] || {}).net || 0);
  const maxAbsVal = Math.max(...netVals.map(Math.abs), 1);
  dates.forEach((d, i) => {
    const slice = netVals.slice(Math.max(0, i - window5 + 1), i + 1);
    const cumSum = slice.reduce((a, b) => a + b, 0);
    pressureMap[d] = cumSum / (maxAbsVal * window5);  // normalised
  });

  return { weightedMap, pressureMap, maxAbsVal };
}

function _drawUnifiedChart(instD, newsD, priceD) {
  const cvs = document.getElementById('unified-chart-canvas');
  if (!cvs) return;

  const container = cvs.parentElement;
  let W = 0;
  if (container) {
    W = container.getBoundingClientRect().width || container.offsetWidth;
  }
  if (W < 200) {
    W = Math.max(600, window.innerWidth - 260);
  }
  const H   = 320;
  const dpr = window.devicePixelRatio || 1;

  cvs.width  = Math.round(W * dpr);
  cvs.height = Math.round(H * dpr);
  cvs.style.width  = W + 'px';
  cvs.style.height = H + 'px';
  const ctx = cvs.getContext('2d');
  ctx.scale(dpr, dpr);

  // Store data for resize redraws
  cvs._chartData = {instD, newsD, priceD};

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
    ctx.fillText('No price data — select a symbol and click ANALYSE', W/2, H/2);
    return;
  }

  const dealMap = {};
  Object.entries(instD.deal_map || {}).forEach(([dt, dm]) => {
    dealMap[dt] = (dm.buy_qty||0) - (dm.sell_qty||0);
  });
  const anomMap = {};
  (instD.anomalies || []).forEach(a => { anomMap[a.trade_date] = a; });
  const newsMap = {};
  (newsD.trend || []).forEach(r => {
    newsMap[r.pub_date] = r.avg_effective != null ? r.avg_effective : (r.avg_raw || 0);
  });

  const xOf = i => PAD.l + (i / (N-1)) * CW;

  const minP = Math.min(...prices) * 0.997;
  const maxP = Math.max(...prices) * 1.003;
  const yPrice = v => PAD.t + CH * (1 - (v - minP) / (maxP - minP));

  const dealVals  = dates.map(d => dealMap[d] || 0);
  const maxDealAbs= Math.max(...dealVals.map(Math.abs), 1);
  // Right axis: news [-1,+1] normalized, BD shown as bars in same space
  // Map news score: +1 → top, -1 → bottom
  const yRight = v => PAD.t + CH * (1 - (v + 1) / 2);  // news [-1,1] → canvas
  // BD bars: scale maxDealAbs to fill ±30% of chart height
  const bdScale = (CH * 0.3) / maxDealAbs;
  const midY = PAD.t + CH / 2;

  // ── Grid lines ───────────────────────────────────────────────
  ctx.strokeStyle = 'rgba(255,255,255,0.04)';
  ctx.lineWidth   = 0.5;
  for (let i = 0; i <= 4; i++) {
    const y = PAD.t + (CH / 4) * i;
    ctx.beginPath(); ctx.moveTo(PAD.l, y); ctx.lineTo(PAD.l + CW, y); ctx.stroke();
  }
  // Zero line for news/BD (mid)
  ctx.strokeStyle = 'rgba(255,255,255,0.08)';
  ctx.lineWidth   = 0.5;
  ctx.setLineDash([4, 4]);
  ctx.beginPath(); ctx.moveTo(PAD.l, midY); ctx.lineTo(PAD.l + CW, midY); ctx.stroke();
  ctx.setLineDash([]);

  // ── BD BARS (behind everything) ──────────────────────────────
  const barW = Math.max(1.5, (CW / N) * 0.55);
  dealVals.forEach((v, i) => {
    if (v === 0) {
      // Volume anomaly dot
      const an = anomMap[dates[i]];
      if (an) {
        ctx.fillStyle = an.signal?.includes('BULL') ? 'rgba(0,255,136,0.3)' : 'rgba(255,204,0,0.25)';
        ctx.fillRect(xOf(i) - barW/2, midY - 2, barW, 4);
      }
      return;
    }
    const barH = Math.abs(v) * bdScale;
    ctx.fillStyle = v > 0 ? 'rgba(204,136,255,0.55)' : 'rgba(255,51,85,0.55)';
    ctx.fillRect(xOf(i) - barW/2, v > 0 ? midY - barH : midY, barW, barH);
  });

  // ── NEWS LINE (dashed, right axis) ──────────────────────────
  const newsVals = dates.map(d => newsMap[d] != null ? newsMap[d] : null);
  ctx.strokeStyle = '#00d4ff';
  ctx.lineWidth   = 1.5;
  ctx.setLineDash([5, 3]);
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

  // ── PRICE AREA + LINE (left axis) ───────────────────────────
  const isUp  = prices[N-1] >= prices[0];
  const pCol  = isUp ? '#26a69a' : '#ef5350';
  const pColA = isUp ? 'rgba(38,166,154,0.12)' : 'rgba(239,83,80,0.12)';

  // Area fill
  const grad = ctx.createLinearGradient(0, PAD.t, 0, PAD.t + CH);
  grad.addColorStop(0, isUp ? 'rgba(38,166,154,0.18)' : 'rgba(239,83,80,0.18)');
  grad.addColorStop(1, 'rgba(6,15,22,0.01)');
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.moveTo(xOf(0), yPrice(prices[0]));
  prices.forEach((v, i) => ctx.lineTo(xOf(i), yPrice(v)));
  ctx.lineTo(xOf(N-1), PAD.t + CH);
  ctx.lineTo(xOf(0),   PAD.t + CH);
  ctx.closePath(); ctx.fill();

  // Price line
  ctx.strokeStyle = pCol; ctx.lineWidth = 2;
  ctx.beginPath();
  prices.forEach((v, i) => i === 0 ? ctx.moveTo(xOf(i), yPrice(v)) : ctx.lineTo(xOf(i), yPrice(v)));
  ctx.stroke();

  // BD deal date vertical markers on price
  dates.forEach((d, i) => {
    const net = dealMap[d];
    if (!net) return;
    ctx.strokeStyle = net > 0 ? 'rgba(204,136,255,0.4)' : 'rgba(255,51,85,0.4)';
    ctx.lineWidth   = 1;
    ctx.setLineDash([3, 4]);
    ctx.beginPath();
    ctx.moveTo(xOf(i), PAD.t);
    ctx.lineTo(xOf(i), PAD.t + CH);
    ctx.stroke();
    ctx.setLineDash([]);
  });

  // ── LEFT Y-AXIS LABELS (Price) ───────────────────────────────
  ctx.fillStyle = '#26a69a'; ctx.font = '9px Share Tech Mono'; ctx.textAlign = 'right';
  const pSteps = 5;
  for (let i = 0; i <= pSteps; i++) {
    const v = minP + (maxP - minP) * (1 - i/pSteps);
    const y = PAD.t + CH * (i/pSteps);
    ctx.fillText('₹' + v.toLocaleString('en-IN', {maximumFractionDigits:0}), PAD.l - 4, y + 3);
    ctx.strokeStyle = 'rgba(38,166,154,0.06)'; ctx.lineWidth = 0.5;
    ctx.beginPath(); ctx.moveTo(PAD.l, y); ctx.lineTo(PAD.l + CW, y); ctx.stroke();
  }

  // ── RIGHT Y-AXIS LABELS (News score) ─────────────────────────
  ctx.fillStyle = '#00d4ff'; ctx.textAlign = 'left';
  [1.0, 0.5, 0, -0.5, -1.0].forEach(v => {
    const y = yRight(v);
    ctx.fillText(v.toFixed(1), PAD.l + CW + 4, y + 3);
  });
  // Right axis label
  ctx.save();
  ctx.fillStyle = '#00d4ff'; ctx.font = '8px Share Tech Mono';
  ctx.translate(W - 10, H/2);
  ctx.rotate(-Math.PI/2);
  ctx.textAlign = 'center';
  ctx.fillText('NEWS / BD', 0, 0);
  ctx.restore();

  // ── DATE AXIS ───────────────────────────────────────────────
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const step   = Math.max(1, Math.round(N / 8));
  ctx.fillStyle = '#3a5a70'; ctx.font = '8px Share Tech Mono'; ctx.textAlign = 'center';
  dates.forEach((d, i) => {
    if (i % step !== 0) return;
    const lbl = MONTHS[parseInt(d.slice(5,7))-1] + ' ' + d.slice(8,10);
    ctx.fillText(lbl, xOf(i), H - 6);
  });

  // ── LAST PRICE TAG ───────────────────────────────────────────
  const lp   = prices[N-1];
  const lpY  = yPrice(lp);
  const tag  = '₹' + lp.toLocaleString('en-IN', {maximumFractionDigits:0});
  ctx.fillStyle = pCol;
  ctx.fillRect(PAD.l + CW + 1, lpY - 9, PAD.r - 2, 18);
  ctx.fillStyle = '#fff'; ctx.font = 'bold 9px Share Tech Mono'; ctx.textAlign = 'left';
  ctx.fillText(tag, PAD.l + CW + 4, lpY + 4);

  // ── CHART LABELS ─────────────────────────────────────────────
  ctx.fillStyle = '#26a69a'; ctx.font = 'bold 9px Share Tech Mono'; ctx.textAlign = 'left';
  ctx.fillText('PRICE', PAD.l + 4, PAD.t + 14);
  ctx.fillStyle = '#00d4ff';
  ctx.fillText('── NEWS', PAD.l + 50, PAD.t + 14);
  ctx.fillStyle = '#cc88ff';
  ctx.fillText('▌BD', PAD.l + 110, PAD.t + 14);

  // Save base for crosshair
  cvs._base = ctx.getImageData(0, 0, cvs.width, cvs.height);
  cvs._data = { dates, prices, dealMap, newsMap, N, xOf, PAD, W, H, dpr, CW, CH };

  // ── CROSSHAIR HOVER ──────────────────────────────────────────
  cvs.onmousemove = e => {
    if (!cvs._base || !cvs._data) return;
    const { dates, prices, dealMap, newsMap, N, xOf, PAD, W, H, dpr, CW, CH } = cvs._data;
    const rect = cvs.getBoundingClientRect();
    const mx   = e.clientX - rect.left;
    const frac = Math.max(0, Math.min(1, (mx - PAD.l) / CW));
    const idx  = Math.max(0, Math.min(N-1, Math.round(frac * (N-1))));
    const cx   = xOf(idx) * dpr;

    ctx.putImageData(cvs._base, 0, 0);
    ctx.save();
    ctx.strokeStyle = 'rgba(255,204,0,0.35)'; ctx.lineWidth = dpr * 0.8;
    ctx.setLineDash([3*dpr, 3*dpr]);
    ctx.beginPath();
    ctx.moveTo(cx, PAD.t * dpr);
    ctx.lineTo(cx, (PAD.t + CH) * dpr);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();

    const dt    = dates[idx];
    const price = prices[idx];
    const deal  = dealMap[dt] || 0;
    const news  = newsMap[dt];
    const tip   = document.getElementById('unified-tooltip');
    if (tip) {
      const parts = [`<b>${dt}</b>`];
      if (price) parts.push(`Price: <b style="color:#26a69a">₹${price.toLocaleString('en-IN',{maximumFractionDigits:0})}</b>`);
      if (news  != null) parts.push(`News: <b style="color:#00d4ff">${news>=0?'+':''}${news.toFixed(3)}</b>`);
      if (deal !== 0) parts.push(`BD Net: <b style="color:${deal>0?'#cc88ff':'#ff3355'}">${deal>0?'+':''}${deal.toLocaleString()}</b>`);
      tip.innerHTML = parts.join('  |  ');
      tip.style.display = 'block';
    }
  };
  cvs.onmouseleave = () => {
    if (cvs._base) ctx.putImageData(cvs._base, 0, 0);
    const tip = document.getElementById('unified-tooltip');
    if (tip) tip.style.display = 'none';
  };

  // Redraw on resize
  if (!cvs._resizeObserver) {
    cvs._resizeObserver = new ResizeObserver(() => {
      if (cvs._chartData) _drawUnifiedChart(cvs._chartData.instD, cvs._chartData.newsD, cvs._chartData.priceD);
    });
    cvs._resizeObserver.observe(cvs.parentElement || cvs);
  }
}

// Label a headline directly from the UI
async function labelHeadline(symbol, title, label) {
  try {
    const d = await api('sentiment_label', {symbol, title, label});
    if (d.ok) {
      console.log('[LABEL] Saved:', label, 'for', title.substring(0,40));
      // Refresh stats
      loadSentimentDbStats();
    }
  } catch(e) { console.error('[LABEL] Error:', e.message); }
}


async function fetchAllSymbolsNews() {
  const btn = document.getElementById('db-fetchall-btn');
  if (btn) { btn.textContent = '⬇ FETCHING ALL... (see terminal)'; btn.disabled = true; }
  try {
    const d = await api('sentiment_fetch_all', {});
    const el = document.getElementById('db-status-content');
    if (el) {
      el.innerHTML = `<div style="padding:10px;background:rgba(0,255,136,0.04);
        border:1px solid rgba(0,255,136,0.2);font-family:Share Tech Mono,monospace;font-size:0.72rem;">
        <b style="color:#00ff88;">✓ ${d.message}</b><br>
        <span style="color:var(--dim);">Watch your terminal window for live progress.</span><br>
        <span style="color:var(--dim);">Click REFRESH STATS in ~2 minutes to see the results.</span>
      </div>`;
      // Auto-refresh stats after 90 seconds
      setTimeout(loadSentimentDbStats, 90000);
    }
  } catch(e) {
    const el = document.getElementById('db-status-content');
    if (el) el.innerHTML = `<div class="err">Fetch error: ${e.message}</div>`;
  } finally {
    setTimeout(() => {
      if (btn) { btn.textContent = '⬇ FETCH ALL SYMBOLS'; btn.disabled = false; }
    }, 5000);
  }
}

// ── MARKET OVERVIEW (MARKET BRAIN) LOGIC ──
async function showGeneralOverview() {
  const sel = document.getElementById('sent-sym');
  if (sel) sel.value = "";
  
  document.getElementById('sent-loading').style.display='none';
  document.getElementById('sent-error').style.display='none';
  document.getElementById('sent-content').style.display='none';
  
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
  document.getElementById('mb-digest-date').textContent = "Date: " + d.digest_date;
  document.getElementById('mb-narrative-text').innerHTML = parseMarkdownLocal(d.narrative);
  
  const confBadge = document.getElementById('mb-confidence-badge');
  if (confBadge) confBadge.textContent = "Confidence: " + Math.round(d.confidence * 100) + "%";

  // Render Gauge
  const gc = document.getElementById('mb-gauge');
  if (gc) {
    const gctx = gc.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    gc.width = 200 * dpr; gc.height = 120 * dpr;
    gc.style.width = '200px'; gc.style.height = '120px';
    gctx.scale(dpr, dpr);
    const cx = 100, cy = 105, r = 80;
    
    // Background arc
    gctx.beginPath(); gctx.arc(cx, cy, r, Math.PI, 2*Math.PI);
    gctx.strokeStyle = 'rgba(255,255,255,0.08)'; gctx.lineWidth = 14; gctx.stroke();

    // Color zones
    const zones = [
      {from:0,   to:0.25, col:'#ef5350'},  // Bearish / Panic
      {from:0.25,to:0.45, col:'#ffcc00'},  // Cautious
      {from:0.45,to:0.55, col:'#7aa8c0'},  // Neutral
      {from:0.55,to:0.75, col:'#7FFFD4'},  // Optimistic
      {from:0.75,to:1.0,  col:'#26a69a'}   // Bullish / Greed
    ];
    zones.forEach(z => {
      const a1 = Math.PI + z.from * Math.PI;
      const a2 = Math.PI + z.to * Math.PI;
      gctx.beginPath(); gctx.arc(cx, cy, r, a1, a2);
      gctx.strokeStyle = z.col; gctx.lineWidth = 10; gctx.stroke();
    });

    // Needle
    const scoreVal = d.mood_score || 0; // -1 to 1
    const angle = Math.PI + ((scoreVal + 1) / 2) * Math.PI;
    gctx.save(); gctx.translate(cx, cy);
    gctx.rotate(angle);
    gctx.beginPath(); gctx.moveTo(0, 4); gctx.lineTo(r - 6, 0); gctx.lineTo(0, -4);
    gctx.fillStyle = '#fff'; gctx.fill();
    gctx.restore();
    
    gctx.beginPath(); gctx.arc(cx, cy, 7, 0, Math.PI * 2);
    gctx.fillStyle = '#fff'; gctx.fill();

    // Labels
    gctx.fillStyle = '#3a5a70'; gctx.font = '8px Share Tech Mono'; gctx.textAlign = 'center';
    gctx.fillText('FEAR', 18, cy - 2); gctx.fillText('NEUTRAL', cx, 34); gctx.fillText('GREED', 182, cy - 2);
  }

  // Set Mood labels
  const moodEl = document.getElementById('mb-mood-label');
  if (moodEl) {
    moodEl.textContent = d.mood_state;
    moodEl.style.color = d.mood_color || '#7aa8c0';
  }
  const ratEl = document.getElementById('mb-mood-rationale');
  if (ratEl) ratEl.textContent = d.mood_rationale;

  // Render Sector Board
  const sectorsGrid = document.getElementById('mb-sectors-grid');
  if (sectorsGrid && d.sector_sentiments) {
    sectorsGrid.innerHTML = d.sector_sentiments.map(s => {
      let badgeClass = "bd";
      let col = "var(--dim)";
      if (s.bias === "POSITIVE") { badgeClass = "bg"; col = "var(--green)"; }
      else if (s.bias === "NEGATIVE") { badgeClass = "br"; col = "var(--red)"; }
      else if (s.bias === "NEUTRAL") { badgeClass = "bo"; col = "var(--gold)"; }

      const pctW = Math.round((s.score + 1) / 2 * 100);

      return `
        <div style="display:flex;flex-direction:column;background:var(--p2);border:1px solid var(--border);padding:10px;border-radius:4px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;font-weight:700;color:var(--white);">${s.sector}</span>
            <div style="display:flex;align-items:center;gap:8px;">
              <span class="badge ${badgeClass}">${s.bias}</span>
              <span style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:${col};font-weight:700;">${s.score >= 0 ? '+' : ''}${s.score.toFixed(2)}</span>
            </div>
          </div>
          <div style="font-size:0.65rem;color:var(--dim);line-height:1.4;margin-bottom:6px;">${s.rationale}</div>
          <div style="height:4px;background:rgba(255,255,255,0.04);border-radius:2px;overflow:hidden;">
            <div style="height:100%;width:${pctW}%;background:${col};transition:width 0.4s;"></div>
          </div>
        </div>
      `;
    }).join('');
  }

  // Render Key Events Timeline
  const timelineEl = document.getElementById('mb-events-timeline');
  if (timelineEl && d.key_events) {
    if (d.key_events.length === 0) {
      timelineEl.innerHTML = '<div class="loading">No high impact events today.</div>';
    } else {
      timelineEl.innerHTML = d.key_events.map(ev => {
        let col = ev.score >= 0.1 ? 'var(--green)' : ev.score <= -0.1 ? 'var(--red)' : 'var(--t2)';
        let emo = ev.score >= 0.1 ? '▲' : ev.score <= -0.1 ? '▼' : '●';
        return `
          <div style="background:var(--p2);border:1px solid var(--border);padding:10px;border-radius:4px;position:relative;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
              <span class="badge bd" style="font-size:0.6rem;background:rgba(41,98,255,0.08);color:var(--cyan);border:1px solid rgba(41,98,255,0.25);">${ev.sector}</span>
              <span style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);">${ev.date}</span>
            </div>
            <h4 style="font-size:0.75rem;color:var(--white);font-weight:600;line-height:1.4;margin-bottom:4px;">${ev.title}</h4>
            <p style="font-size:0.65rem;color:var(--dim);line-height:1.4;">${ev.snippet}</p>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px;font-family:Share Tech Mono,monospace;font-size:0.65rem;">
              <span>Source: ${ev.source}</span>
              <span style="color:${col};font-weight:700;">${emo} ${ev.score >= 0 ? '+' : ''}${ev.score.toFixed(3)}</span>
            </div>
          </div>
        `;
      }).join('');
    }
  }
}

async function askMarketBrain() {
  const query = document.getElementById('mb-query-input')?.value;
  if (!query) return;
  
  const loading = document.getElementById('mb-qa-loading');
  const result = document.getElementById('mb-qa-result');
  
  if (loading) loading.style.display = 'flex';
  if (result) result.style.display = 'none';
  
  try {
    const d = await api('ask_market_brain', {query});
    if (loading) loading.style.display = 'none';
    if (result) {
      result.style.display = 'block';
      result.innerHTML = parseMarkdownLocal(d.response);
    }
  } catch(e) {
    if (loading) loading.style.display = 'none';
    if (result) {
      result.style.display = 'block';
      result.innerHTML = `<span style="color:var(--red);">Error evaluating query: ${e.message}</span>`;
    }
  }
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

// Hook navigation for general overview
const _sentOrigNav = window._resNavHook;
window._resNavHook = function(page) {
  if (_sentOrigNav) _sentOrigNav(page);
  if (page === 'sentiment') {
    setTimeout(showGeneralOverview, 200);
  }
};
"""