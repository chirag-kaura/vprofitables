"""
page_advisor.py — Investment AI Advisor — portfolio scan + single stock report

Exports:
    HTML  : Page HTML template (injected into SPA)
    JS    : Page JavaScript (injected into <script> block)

Backend endpoints for this page live in app.py (ep == "..." handlers).
To modify: edit HTML/JS here, backend logic in app.py.
"""


HTML = r"""
<!-- ═══════════ PAGE: INVESTMENT AI ADVISOR ═══════════ -->
<div class="page active" id="page-advisor">
  <div class="topbar">
    <h2>💡 INVESTMENT AI ADVISOR</h2>
    <span class="page-tag">Vprofitables · QUANT</span>
  </div>

  <!-- Input Panel -->
  <div class="g2" style="margin-bottom:16px;">
    <div class="card">
      <div class="card-title">⚙ INVESTMENT PARAMETERS</div>

      <!-- Mode Toggle -->
      <div style="display:flex;gap:0;margin-bottom:16px;border:1px solid var(--b2);border-radius:3px;overflow:hidden;width:fit-content;">
        <button id="adv-mode-portfolio" onclick="setAdvisorMode('portfolio')"
          style="padding:7px 18px;font-family:Share Tech Mono,monospace;font-size:0.68rem;letter-spacing:2px;
          cursor:pointer;border:none;background:rgba(0,212,255,0.12);color:var(--cyan);border-right:1px solid var(--b2);">
          📊 PORTFOLIO SCAN
        </button>
        <button id="adv-mode-single" onclick="setAdvisorMode('single')"
          style="padding:7px 18px;font-family:Share Tech Mono,monospace;font-size:0.68rem;letter-spacing:2px;
          cursor:pointer;border:none;background:transparent;color:var(--dim);border-right:1px solid var(--b2);">
          🔬 SINGLE STOCK REPORT
        </button>
        <button id="adv-mode-planner" onclick="setAdvisorMode('planner')"
          style="padding:7px 18px;font-family:Share Tech Mono,monospace;font-size:0.68rem;letter-spacing:2px;
          cursor:pointer;border:none;background:transparent;color:var(--dim);">
          📋 PORTFOLIO PLANNER
        </button>
      </div>

      <!-- Portfolio mode params -->
      <div id="adv-portfolio-params">
        <div class="form-row" style="flex-wrap:wrap;gap:12px;">
          <div style="display:flex;flex-direction:column;gap:4px;">
            <label style="font-size:0.65rem;color:var(--dim);letter-spacing:1px;">AMOUNT (₹)</label>
            <input type="number" id="adv-amount" value="100000" step="10000"
              style="width:130px;background:var(--p2);border:1px solid var(--b2);
              color:var(--gold);padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.85rem;outline:none;">
          </div>
          <div style="display:flex;flex-direction:column;gap:4px;">
            <label style="font-size:0.65rem;color:var(--dim);letter-spacing:1px;">INVESTMENT TYPE</label>
            <select id="adv-type"
              style="background:var(--p2);border:1px solid var(--b2);color:var(--t2);
              padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.8rem;outline:none;">
              <option value="intraday">🏎️ Intraday (Same Day)</option>
              <option value="swing">s Swing Trade (5–15 days)</option>
              <option value="short">📈 Short Term (15–45 days)</option>
              <option value="long">🏛 Long Term (3–18 months)</option>
              
            </select>
          </div>
          <div style="display:flex;flex-direction:column;gap:4px;">
            <label style="font-size:0.65rem;color:var(--dim);letter-spacing:1px;">RISK PREFERENCE</label>
            <select id="adv-risk"
              style="background:var(--p2);border:1px solid var(--b2);color:var(--t2);
              padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.8rem;outline:none;">
              <option value="low">Low Risk (capital protection)</option>
              <option value="balanced" selected>Balanced (risk/reward)</option>
              <option value="high">High Risk (max profit)</option>
            </select>
          </div>
          <div id="adv-diversify-container" style="display:flex;flex-direction:column;gap:4px;">
            <label style="font-size:0.65rem;color:var(--dim);letter-spacing:1px;">NO. OF STOCKS</label>
            <select id="adv-diversify"
              style="background:var(--p2);border:1px solid var(--b2);color:var(--t2);
              padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.8rem;outline:none;">
              <option value="1">Focus (1 stock)</option>
              <option value="2">Pair (2 stocks)</option>
              <option value="3" selected>Diversified (3 stocks)</option>
              <option value="5">Wide (5 stocks)</option>
            </select>
          </div>
          <div id="adv-sector-container" style="display:flex;flex-direction:column;gap:4px;">
            <label style="font-size:0.65rem;color:var(--dim);letter-spacing:1px;">SECTOR FILTER</label>
            <select id="adv-sector"
              style="background:var(--p2);border:1px solid var(--b2);color:var(--t2);
              padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.8rem;outline:none;">
              <option value="">All Sectors</option>
              <option value="auto" style="color:var(--cyan);font-weight:bold;">🌌 Auto Nakshatra Filter</option>
              <option value="it">IT / Technology</option>
              <option value="banking">Banking / Finance</option>
              <option value="pharma">Pharma / Healthcare</option>
              <option value="auto">Automobile</option>
              <option value="fmcg">FMCG / Consumer</option>
              <option value="energy">Energy / Oil</option>
              <option value="infra">Infrastructure</option>
            </select>
          </div>
          <div id="adv-ratio-container" style="display:none;flex-direction:column;gap:4px;">
            <label style="font-size:0.65rem;color:var(--dim);letter-spacing:1px;">ASTRO/QUANT RATIO (<span id="adv-ratio-val">50</span>/<span id="adv-ratio-val-q">50</span>)</label>
            <input type="range" id="adv-ratio" min="0" max="100" value="50" oninput="updateRatioLabel(this.value)"
              style="width:140px;background:var(--p2);accent-color:var(--cyan);outline:none;margin-top:5px;height:24px;">
          </div>
        </div>
        <div style="margin-top:14px;display:flex;gap:8px;align-items:flex-start;">
          <div style="flex:1;">
            <label style="font-size:0.65rem;color:var(--dim);letter-spacing:1px;display:block;margin-bottom:4px;">
              CHAT PROMPT (optional — or just click RUN ANALYSIS)
            </label>
            <textarea id="adv-prompt" rows="2" placeholder="e.g. I have ₹100000 for swing trade, suggest best IT stocks with low risk..."
              style="width:100%;background:var(--p2);border:1px solid var(--b2);color:var(--t2);
              padding:8px 10px;font-family:Share Tech Mono,monospace;font-size:0.75rem;
              outline:none;resize:vertical;box-sizing:border-box;"></textarea>
          </div>
          <button onclick="runAdvisor()"
            style="margin-top:20px;background:linear-gradient(135deg,rgba(0,212,255,0.15),rgba(0,212,255,0.05));
            border:1px solid var(--cyan);color:var(--cyan);padding:10px 22px;
            font-family:Orbitron,sans-serif;font-size:0.7rem;letter-spacing:2px;cursor:pointer;
            white-space:nowrap;">
            s RUN ANALYSIS
          </button>
        </div>
      </div>

      <!-- Single stock mode params -->
      <div id="adv-single-params" style="display:none;">
        <!-- Row 1: Stock + Type + Risk -->
        <div class="form-row" style="flex-wrap:wrap;gap:12px;margin-bottom:10px;">
          <div style="display:flex;flex-direction:column;gap:4px;">
            <label style="font-size:0.65rem;color:var(--dim);letter-spacing:1px;">SELECT STOCK</label>
            <select id="adv-single-sym"
              style="min-width:220px;background:var(--p2);border:1px solid var(--b2);color:var(--gold);
              padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.8rem;outline:none;">
              <option value="">— Choose a stock —</option>
            </select>
          </div>
          <div style="display:flex;flex-direction:column;gap:4px;">
            <label style="font-size:0.65rem;color:var(--dim);letter-spacing:1px;">INVESTMENT TYPE</label>
            <select id="adv-single-type"
              style="background:var(--p2);border:1px solid var(--b2);color:var(--t2);
              padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.8rem;outline:none;">
              <option value="intraday">🏎️ Intraday (Same Day)</option>
              <option value="swing">s Swing Trade (5–15 days)</option>
              <option value="short">📈 Short Term (15–45 days)</option>
              <option value="long">🏛 Long Term (3–18 months)</option>
            </select>
          </div>
          <div style="display:flex;flex-direction:column;gap:4px;">
            <label style="font-size:0.65rem;color:var(--dim);letter-spacing:1px;">RISK PREFERENCE</label>
            <select id="adv-single-risk"
              style="background:var(--p2);border:1px solid var(--b2);color:var(--t2);
              padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.8rem;outline:none;">
              <option value="low">Low Risk</option>
              <option value="balanced" selected>Balanced</option>
              <option value="high">High Risk</option>
            </select>
          </div>
        </div>
        <!-- Row 2: Chat prompt + RUN button (same as Portfolio Scan) -->
        <div style="display:flex;gap:12px;align-items:flex-end;margin-bottom:10px;">
          <div style="flex:1;display:flex;flex-direction:column;gap:4px;">
            <label style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;">
              CHAT PROMPT (optional — describe what you want to analyse)
            </label>
            <textarea id="adv-single-prompt" rows="2"
              placeholder="e.g. Is ICICIBANK a good swing trade today? or Analyse for short-term momentum..."
              style="width:100%;background:var(--p2);border:1px solid var(--b2);color:var(--t2);
              padding:8px 10px;font-family:Share Tech Mono,monospace;font-size:0.75rem;
              outline:none;resize:vertical;min-height:52px;"></textarea>
          </div>
          <button onclick="runSingleStockReport()"
            style="padding:10px 28px;background:linear-gradient(135deg,rgba(0,212,255,0.15),rgba(0,212,255,0.05));
            border:1px solid var(--cyan);color:var(--cyan);font-family:Orbitron,sans-serif;
            font-size:0.65rem;letter-spacing:2px;cursor:pointer;white-space:nowrap;height:52px;">
            s RUN ANALYSIS
          </button>
        </div>
        <!-- Auto-loading status bar -->
        <div id="adv-single-status" style="display:none;padding:10px 14px;
          background:rgba(0,212,255,0.04);border:1px solid rgba(0,212,255,0.15);
          font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--cyan);
          align-items:center;gap:10px;">
          <div class="spinner"></div>
          <span id="adv-single-status-text">Running full analysis…</span>
        </div>
      </div>
    </div>

    <!-- Portfolio summary (populated after run) -->
    <div class="card" id="adv-portfolio-card" style="display:none;">
      <div class="card-title" style="color:var(--gold);">📊 PORTFOLIO SUMMARY</div>
      <div id="adv-portfolio-stats" style="margin-bottom:10px;"></div>
      <div id="adv-planet-verdict" style="margin-bottom:10px;"></div>
      <div id="adv-alloc-table"></div>
    </div>
  </div>

  <!-- Moon Nakshatra & Timing Widget (dynamic) -->
  <div class="card" id="adv-nakshatra-card" style="display:none;margin-bottom:16px;">
    <div class="card-title" style="color:var(--cyan);display:flex;justify-content:space-between;align-items:center;">
      <span>🌌 MOON NAKSHATRA & MARKET TIMING</span>
      <span id="adv-nak-score-badge" style="font-size:0.65rem;padding:2px 8px;border-radius:3px;background:rgba(0,212,255,0.15);color:var(--cyan);font-family:Share Tech Mono,monospace;"></span>
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:16px;">
      <div style="flex:2;min-width:280px;">
        <div style="font-family:Orbitron,sans-serif;font-size:1.1rem;color:var(--gold);margin-bottom:6px;" id="adv-nak-name"></div>
        <div style="font-size:0.75rem;color:var(--t2);line-height:1.4;" id="adv-nak-behavior-desc"></div>
        <div style="margin-top:10px;font-size:0.7rem;color:var(--dim);" id="adv-nak-sectors"></div>
      </div>
      <div style="flex:1;min-width:200px;border-left:1px solid var(--b2);padding-left:16px;display:flex;flex-direction:column;gap:12px;">
        <div>
          <span style="font-size:0.65rem;color:var(--dim);display:block;letter-spacing:1px;margin-bottom:2px;">🌞 ABHIJIT MUHURAT (Auspicious Trades)</span>
          <span style="font-size:0.8rem;color:var(--green);font-family:Share Tech Mono,monospace;font-weight:bold;" id="adv-nak-muhurat"></span>
        </div>
        <div>
          <span style="font-size:0.65rem;color:var(--dim);display:block;letter-spacing:1px;margin-bottom:2px;">💀 RAHU KAAL (Avoid Action)</span>
          <span style="font-size:0.8rem;color:var(--red);font-family:Share Tech Mono,monospace;font-weight:bold;" id="adv-nak-rahu"></span>
        </div>
      </div>
    </div>
  </div>

  <!-- Loading state -->
  <div id="adv-loading" class="loading" style="display:none;">
    <div class="spinner"></div>
    <span id="adv-loading-text">Scanning all instruments with Gann + Astro + Quant...</span>
  </div>

  <!-- Error state -->
  <!-- Plain error (HTTP/network failures) -->
  <div id="adv-error" style="display:none;padding:16px;color:var(--red);font-family:Share Tech Mono,monospace;font-size:0.85rem;"></div>

  <!-- No-signal card (market conditions don't meet gate criteria) -->
  <div id="adv-no-signal" style="display:none;margin-top:8px;">
    <div class="card" style="border:1px solid var(--orange);background:rgba(255,136,0,0.05);padding:24px 28px;">
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:18px;">
        <div style="font-size:2rem;">🛡️</div>
        <div>
          <div style="font-family:Orbitron,sans-serif;font-size:1rem;color:var(--orange);letter-spacing:2px;">NO SIGNAL — MARKET IN FILTER ZONE</div>
          <div style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);margin-top:3px;letter-spacing:1px;">Vprofitables GATE SYSTEM ACTIVE</div>
        </div>
      </div>
      <div id="adv-no-signal-reason" style="font-family:Share Tech Mono,monospace;font-size:0.78rem;color:var(--t2);line-height:1.8;margin-bottom:20px;padding:12px 16px;background:rgba(0,0,0,0.3);border-left:3px solid var(--orange);border-radius:2px;"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:20px;">
        <div style="background:rgba(0,212,255,0.06);border:1px solid rgba(0,212,255,0.2);border-radius:4px;padding:12px;text-align:center;">
          <div style="font-size:1.3rem;margin-bottom:4px;">📅</div>
          <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">TRY DIFFERENT DATE</div>
          <div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--cyan);">Use the sidebar date picker to backtest a past date with stronger setups</div>
        </div>
        <div style="background:rgba(0,212,255,0.06);border:1px solid rgba(0,212,255,0.2);border-radius:4px;padding:12px;text-align:center;">
          <div style="font-size:1.3rem;margin-bottom:4px;">🔬</div>
          <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">SINGLE STOCK MODE</div>
          <div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--cyan);">Gates are bypassed for individual stock reports — analyse any symbol directly</div>
        </div>
        <div style="background:rgba(0,212,255,0.06);border:1px solid rgba(0,212,255,0.2);border-radius:4px;padding:12px;text-align:center;">
          <div style="font-size:1.3rem;margin-bottom:4px;">⏳</div>
          <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">WAIT FOR SETUP</div>
          <div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--cyan);">Gann time cycles suggest checking again in 1–3 trading sessions</div>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;padding:10px 14px;background:rgba(255,136,0,0.08);border-radius:4px;">
        <span style="color:var(--orange);font-size:0.9rem;">s</span>
        <span style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--dim);line-height:1.6;">
          The Gate System protects capital by requiring Gann Sq9 confluence, regime-RSI alignment, and volume confirmation before generating a signal. No signal = no edge = cash is the position.
        </span>
      </div>
    </div>
  </div>

  <!-- Prompt interpretation -->
  <div id="adv-prompt-interp" style="display:none;"></div>

  <!-- Results -->
  <div id="adv-results" style="display:none;">
    <!-- Planet Dashboard summary -->
    <div class="card" id="adv-planet-card" style="margin-bottom:14px;">
      <div class="card-title" style="color:var(--purple);">🌌 CURRENT PLANETARY ENVIRONMENT</div>
      <div id="adv-planet-summary" style="font-size:0.8rem;line-height:1.7;color:var(--t2);"></div>
    </div>
    <!-- Recommendation cards (dynamic) -->
    <div id="adv-recs"></div>
  </div>

  <!-- Single Stock Report Results -->
  <div id="adv-single-results" style="display:none;"></div>

  <!-- Personalized Portfolio Planner Results -->
  <div id="adv-planner-results" style="display:none;"></div>

  <!-- Shared fullscreen overlay for single stock chart expand (in DOM, not injected) -->
  <div id="single-chart-overlay" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.88);z-index:9999;cursor:pointer;align-items:center;justify-content:center;" onclick="this.style.display='none'">
    <div style="position:absolute;top:16px;right:24px;color:var(--cyan);font-size:1.8rem;cursor:pointer;z-index:10000;" onclick="document.getElementById('single-chart-overlay').style.display='none'">✕</div>
    <canvas id="single-chart-big" style="border:1px solid var(--cyan);max-width:90vw;max-height:85vh;"></canvas>
  </div>

  </div>
"""



JS = r"""
// ── Mode toggle ───────────────────────────────────────────────────
let currentAdvisorTabMode = 'portfolio';

function setAdvisorMode(mode) {
  currentAdvisorTabMode = mode;
  const isPortfolio = mode === 'portfolio';
  const isSingle = mode === 'single';
  const isPlanner = mode === 'planner';

  document.getElementById('adv-portfolio-params').style.display = (isPortfolio || isPlanner) ? '' : 'none';
  document.getElementById('adv-single-params').style.display    = isSingle ? '' : 'none';
  
  document.getElementById('adv-diversify-container').style.display = isPlanner ? 'none' : '';
  document.getElementById('adv-sector-container').style.display    = isPlanner ? 'none' : '';
  document.getElementById('adv-ratio-container').style.display     = isPlanner ? '' : 'none';

  document.getElementById('adv-results').style.display          = 'none';
  document.getElementById('adv-portfolio-card').style.display   = 'none';
  document.getElementById('adv-single-results').style.display   = 'none';
  document.getElementById('adv-planner-results').style.display  = 'none';
  document.getElementById('adv-error').style.display            = 'none';
  document.getElementById('adv-no-signal').style.display         = 'none';

  const btnP = document.getElementById('adv-mode-portfolio');
  const btnS = document.getElementById('adv-mode-single');
  const btnN = document.getElementById('adv-mode-planner');

  if (btnP) { btnP.style.background = isPortfolio ? 'rgba(0,212,255,0.12)' : 'transparent'; btnP.style.color = isPortfolio ? 'var(--cyan)' : 'var(--dim)'; }
  if (btnS) { btnS.style.background = isSingle ? 'rgba(255,204,0,0.12)' : 'transparent'; btnS.style.color = isSingle ? 'var(--gold)' : 'var(--dim)'; }
  if (btnN) { btnN.style.background = isPlanner ? 'rgba(0,255,136,0.12)' : 'transparent'; btnN.style.color = isPlanner ? 'var(--green)' : 'var(--dim)'; }

  if (isSingle) _populateSingleSymDropdown();
}

function _populateSingleSymDropdown() {
  const sel = document.getElementById('adv-single-sym');
  if (!sel || sel.options.length > 2) return; // already populated
  // Try to reuse allSymbols from shared.js, else call API
  if (typeof allSymbols !== 'undefined' && allSymbols.length) {
    _fillSingleSel(sel, allSymbols);
  } else {
    api('all_symbols').then(d => {
      const _sym = x => typeof x==='object'?x.symbol:x;
      const _lbl = x => typeof x==='object'?(x.symbol+(x.name?' — '+x.name:'')):x;
      const sel2 = document.getElementById('adv-single-sym');
      if (!sel2) return;
      sel2.innerHTML = '<option value="">— Choose a stock —</option>';
      [['Indices',d.indices],['Equities',d.equities],['Commodities',d.commodities]].forEach(([grp,syms])=>{
        const og = document.createElement('optgroup'); og.label=grp;
        (syms||[]).forEach(s=>{ const o=document.createElement('option'); o.value=_sym(s); o.textContent=_lbl(s); og.appendChild(o); });
        sel2.appendChild(og);
      });
    }).catch(()=>{});
  }
}

function _fillSingleSel(sel, symbols) {
  sel.innerHTML = '<option value="">— Choose a stock —</option>';
  symbols.forEach(s => {
    const o = document.createElement('option');
    o.value = typeof s==='object'?s.symbol:s;
    o.textContent = typeof s==='object'?(s.symbol+(s.name?' — '+s.name:'')):s;
    sel.appendChild(o);
  });
}

// ── Single Stock Report — triggered by RUN ANALYSIS button ───────
async function runSingleStockReport() {
  const sym  = document.getElementById('adv-single-sym').value;
  if (!sym) return;

  // Read dropdowns + optional prompt
  let invType = document.getElementById('adv-single-type').value;
  let risk    = document.getElementById('adv-single-risk').value;
  const prompt = (document.getElementById('adv-single-prompt')?.value || '').trim();

  // Parse prompt overrides (same logic as portfolio scan)
  if (prompt) {
    const lower = prompt.toLowerCase();
    if (/swing|2.?5 day|quick|short.?term|intraday/.test(lower))      invType = 'swing';
    else if (/short|week|fortnight|month|30 day/.test(lower))          invType = 'short';
    else if (/long.?term|year|invest|6 month|accumul/.test(lower))     invType = 'long';
    if (/low risk|safe|conservative|capital protect/.test(lower))      risk = 'low';
    else if (/high risk|aggress|maximum profit/.test(lower))           risk = 'high';
    // Update dropdowns to reflect what prompt parsed
    const typeEl = document.getElementById('adv-single-type');
    const riskEl = document.getElementById('adv-single-risk');
    if (typeEl) typeEl.value = invType;
    if (riskEl) riskEl.value = risk;
  }

  const statusBar  = document.getElementById('adv-single-status');
  const statusText = document.getElementById('adv-single-status-text');
  const resultsEl  = document.getElementById('adv-single-results');

  statusBar.style.display  = 'flex';
  resultsEl.style.display  = 'none';
  resultsEl.innerHTML      = '';
  const nakCard = document.getElementById('adv-nakshatra-card');
  if (nakCard) nakCard.style.display = 'none';

  const steps = [
    'Fetching price & history…',
    'Running Gann confluence…',
    'Computing Simons regime…',
    'Analysing natal transits…',
    'Scoring all 5 engines…',
    'Checking fundamentals…',
    'Reading sentiment & news…',
    'Building master report…',
  ];
  let si = 0;
  const iv = setInterval(() => { if(statusText) statusText.textContent = steps[si++ % steps.length]; }, 900);

  try {
    // Run advisor (for scores + entry/SL/T1/T2) and master_report (for deep analysis) in parallel
    const [advData, repData] = await Promise.all([
      api('advisor', { symbols: sym, diversify: 1, type: invType, risk: risk, amount: 100000 }),
      api('master_report', { symbol: sym, date: GANN_DATE }),
    ]);
    clearInterval(iv);
    statusBar.style.display = 'none';
    resultsEl.style.display = 'block';

    // ── Render advisor card (scores + entry/SL/T1/T2 + ML panel + reasons) ──
    const recs = advData.recommendations || [];
    const rec  = recs[0] || null;

    if (rec) {
      if (typeof _updateNakshatraWidget === 'function') {
        _updateNakshatraWidget(advData.nakshatra_today);
      }
      const cardEl = buildRecCard(rec, 0, 100000);
      resultsEl.appendChild(cardEl);
      requestAnimationFrame(() => {
        try { drawPriceProjection('adv-proj-0', rec); } catch(e) {}
        try { drawSRChart('adv-sr-0', rec); }           catch(e) {}
        try { drawPlanetChart('adv-planet-0', rec); }   catch(e) {}
      });
    } else {
      resultsEl.innerHTML = '<div class="err">⚠ No signal for ' + sym + ' with current settings. Try a different investment type or date.</div>';
      return;
    }

    // ── Append Deep Analysis (prose panels + verdict) ──
    if (repData && !repData.error) {
      const reportDiv = document.createElement('div');
      reportDiv.innerHTML = _buildSingleReportHTML(repData, rec);
      resultsEl.appendChild(reportDiv);
    }

  } catch(e) {
    clearInterval(iv);
    statusBar.style.display = 'none';
    resultsEl.style.display = 'block';
    resultsEl.innerHTML = `<div class="err">⚠ ${e.message}</div>`;
  }
}

function _buildSingleReportHTML(rep, rec) {
  // ── MASTER ANALYSIS REPORT: adds DEEP ANALYSIS below the advisor card ──
  // The advisor card (above) already shows: entry/SL/T1/T2, reasons, trigger dates, ML panel.
  // This section adds ONLY: analysis narratives + clean one-line verdict.
  // NO duplication of trade levels or reasons.

  const ts  = rep.trade_setup || {};
  const met = rep._metrics    || {};

  const entry  = rec ? rec.entry     : ts.entry;
  const sl     = rec ? rec.stop_loss : ts.stop_loss;
  const t1     = rec ? rec.target1   : ts.target1;
  const t2     = rec ? rec.target2   : ts.target2;
  const regime = rec ? rec.regime    : (met.regime||'');
  const conf   = rec ? rec.confidence: null;
  const buyDate  = rec ? (rec.buy_date||'').replace(/-/g,'/') : '';
  const sellDate = rec ? (rec.sell_date||'').replace(/-/g,'/') : '';

  // ── SINGLE SOURCE OF TRUTH FOR BIAS ─────────────────────────────────────
  let bias = 'NEUTRAL';
  if (rec && rec.confidence >= 38) bias = 'BULLISH';
  else if (rec && buyDate)         bias = 'WATCH';
  const biasCol = bias === 'BULLISH' ? 'var(--green)' : bias === 'WATCH' ? 'var(--gold)' : 'var(--dim)';

  let confLabel = conf !== null ? (conf >= 70 ? 'HIGH' : conf >= 50 ? 'MEDIUM' : 'LOW') : (ts.confidence||'LOW');
  const confCol = confLabel==='HIGH'?'var(--green)':confLabel==='LOW'?'var(--red)':'var(--gold)';
  const horizonMap = {STRONG_BULL:'3–8 days',BULL:'5–15 days',SIDEWAYS:'5–15 days (S/R swing)',
    STRONG_BEAR:'3–8 days',BEAR:'5–12 days',VOLATILE:'1–3 days (scalp)'};
  const horizon = horizonMap[regime] || ts.holding_period || '5–12 days';
  const rrStr = rec ? `1:${rec.rr_ratio}` : (ts.risk_reward||'—');

  // ── METRICS STRIP — numbers only, no duplication of levels ───────────────
  const metParts = [
    met.rsi!=null?`RSI: <b style="color:${met.rsi<30?'var(--green)':met.rsi>70?'var(--red)':'var(--gold)'}">${met.rsi}</b> ${met.rsi>70?' ⚠ overbought':met.rsi<30?' s oversold':''}`:null,
    met.ann_vol!=null?`Volatility: <b style="color:var(--gold)">${met.ann_vol}%</b> annualised`:null,
    met.vol_surge!=null?`Volume: <b style="color:var(--cyan)">${met.vol_surge}x</b> avg`:null,
    met.gann_score!=null?`Gann score: <b style="color:var(--gold)">${met.gann_score}/25</b>`:null,
    rec?`Natal: <b style="color:var(--green)">${rec.bull_signals||0}🟢</b> <b style="color:var(--red)">${rec.bear_signals||0}🔴</b>`:null,
    regime?`Regime: <b style="color:${biasCol}">${regime.replace('_',' ')}</b>`:null,
    buyDate?`Best entry window: <b style="color:var(--green)">${buyDate}</b>`:null,
    sellDate?`Exit by: <b style="color:var(--red)">${sellDate}</b>`:null,
  ].filter(Boolean);

  const metricsStrip = metParts.length ? `
    <div style="display:flex;flex-wrap:wrap;gap:14px;padding:10px 14px;
      background:rgba(0,212,255,0.04);border:1px solid var(--border);
      margin-bottom:14px;font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--dim);">
      ${metParts.map(m=>`<span>${m}</span>`).join('')}
    </div>` : '';

  // ── 6 DEEP ANALYSIS PANELS — prose from each engine ─────────────────────
  const SECTIONS = [
    {key:'technical',   icon:'📈', label:'TECHNICAL ANALYSIS',    border:'rgba(0,255,136,0.4)'},
    {key:'gann',        icon:'⬛', label:'GANN + TIME CYCLES',    border:'rgba(255,204,0,0.4)'},
    {key:'natal',       icon:'🔭', label:'NATAL CHARTS',          border:'rgba(204,136,255,0.4)'},
    {key:'simons',      icon:'🧠', label:'SIMONS QUANT / REGIME', border:'rgba(0,212,255,0.4)'},
    {key:'fundamental', icon:'📊', label:'FUNDAMENTAL ANALYSIS',  border:'rgba(255,136,0,0.4)'},
    {key:'sentiment',   icon:'🗞', label:'SENTIMENT + NEWS',       border:'rgba(100,200,255,0.4)'},
    {key:'nakshatra',   icon:'🌌', label:'NAKSHATRA MARKET TIMING', border:'rgba(0,212,255,0.4)'},
  ];
  const panelGrid = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;">
      ${SECTIONS.map(s => {
        if (s.key === 'nakshatra' && rep.nakshatra) {
          const nak = rep.nakshatra;
          let nakContent = `<div style="margin-bottom:8px;">${nak.narrative || 'No data.'}</div>`;
          if (nak.upcoming_transitions && nak.upcoming_transitions.length > 0) {
            nakContent += `<div style="margin-top:10px;"><b style="color:var(--gold);font-size:0.7rem;letter-spacing:1px;display:block;margin-bottom:4px;">🌌 UPCOMING TRANSITIONS</b>`;
            nak.upcoming_transitions.forEach(t => {
              const biasCol = t.bias === 'BULLISH' ? 'var(--green)' : t.bias === 'BEARISH' ? 'var(--red)' : t.bias === 'VOLATILE' ? 'var(--orange)' : 'var(--t2)';
              nakContent += `<div style="font-family:Share Tech Mono,monospace;font-size:0.75rem;margin-bottom:2px;">` +
                `- ${t.date.replace(/-/g,'/')} &nbsp;|&nbsp; Moon enters <b>${t.nakshatra}</b> (ruled by ${t.ruler}) &nbsp;|&nbsp; ` +
                `Bias: <span style="color:${biasCol};font-weight:bold;">${t.bias}</span> (${t.behavior})` +
                `</div>`;
            });
            nakContent += `</div>`;
          }
          if (nak.rahu_kaal_schedule && nak.rahu_kaal_schedule.length > 0) {
            nakContent += `<div style="margin-top:10px;"><b style="color:var(--red);font-size:0.7rem;letter-spacing:1px;display:block;margin-bottom:4px;">💀 RAHU KAAL WINDOWS (IST)</b>`;
            nakContent += `<div style="display:flex;flex-wrap:wrap;gap:8px;">`;
            nak.rahu_kaal_schedule.forEach(r => {
              nakContent += `<span style="background:rgba(255,68,68,0.06);border:1px solid rgba(255,68,68,0.25);border-radius:2px;padding:2px 8px;font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--red);">` +
                `${r.day}: ${r.window}` +
                `</span>`;
            });
            nakContent += `</div></div>`;
          }
          return `<div style="padding:12px 14px;background:var(--p2);border:1px solid var(--border);border-left:3px solid ${s.border};grid-column: span 2;">
            <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--cyan);letter-spacing:2px;margin-bottom:7px;">${s.icon} ${s.label}</div>
            <div style="font-family:Rajdhani,sans-serif;font-size:0.88rem;color:var(--t2);line-height:1.6;">${nakContent}</div>
          </div>`;
        }
        const text = rep[s.key] || '';
        if (!text) return '';
        return `<div style="padding:12px 14px;background:var(--p2);border:1px solid var(--border);border-left:3px solid ${s.border};">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--cyan);letter-spacing:2px;margin-bottom:7px;">${s.icon} ${s.label}</div>
          <div style="font-family:Rajdhani,sans-serif;font-size:0.88rem;color:var(--t2);line-height:1.6;">${text}</div>
        </div>`;
      }).join('')}
    </div>`;

  // ── VERDICT — cycle-aware for long type, signal-based for short/swing ────
  const fmtP = n => n ? '₹'+Number(n).toLocaleString('en-IN',{maximumFractionDigits:0}) : '—';
  const invType = rec?.inv_type || rep?.inv_type || 'short';
  const wavePct = rep?.wave_pos_pct ?? 0.5;

  let verdictText = '';
  let verdictBorderColor = biasCol;

  if (invType === 'long') {
    // ── LONG TYPE: Cycle-position verdict — never contradicts the card ───────
    // The card says BUY because cycle phase is accumulation/early markup.
    // The verdict must confirm the SAME cycle logic — not a short-term bias.
    const cyclePhaseTxt = rep.overall_verdict || '';

    // Derive cycle label from wave position
    let cycleLabel, cycleIcon, cycleColor, cycleAction;
    if (wavePct <= 0.30) {
      cycleLabel = 'ACCUMULATION ZONE'; cycleIcon = '🟢'; cycleColor = 'var(--green)'; cycleAction = 'ACCUMULATE';
    } else if (wavePct <= 0.55) {
      cycleLabel = 'EARLY MARKUP';      cycleIcon = '🟢'; cycleColor = 'var(--green)'; cycleAction = 'BUY';
    } else if (wavePct <= 0.75) {
      cycleLabel = 'MARKUP PHASE';      cycleIcon = '🟡'; cycleColor = 'var(--gold)';  cycleAction = 'HOLD & TRAIL';
    } else {
      cycleLabel = 'DISTRIBUTION ZONE'; cycleIcon = '🔴'; cycleColor = 'var(--red)';   cycleAction = 'EXIT / AVOID';
    }
    verdictBorderColor = cycleColor;

    // ALWAYS build from card values so verdict == card — never use master_report levels
    // rec = recommendation object · rep = master_report (overall_verdict pre-built in app.py)
    const cardEntry = rec?.entry      || entry;
    const cardSL    = rec?.stop_loss  || sl;
    const cardT1    = rec?.target1    || t1;
    const cardT2    = rec?.target2    || t2;
    const cardRR    = rec?.rr_ratio   ? `1:${Number(rec.rr_ratio).toFixed(2)}` : rrStr;
    const cardSym   = rec?.name       || sym;

    if (cycleAction === 'ACCUMULATE' || cycleAction === 'BUY') {
      verdictText  = `${cycleIcon} <b style="color:${cycleColor};">CYCLE PHASE: ${cycleLabel} — ${cycleAction}</b><br>`;
      verdictText += `${cardSym} is in the <b>${cycleLabel}</b> of its price-time cycle. `;
      verdictText += `This is where long-term positions are built — accumulate at support while the market looks uncertain.<br>`;
      verdictText += `<b style="color:var(--green);">📋 CYCLE PLAN:</b> `;
      verdictText += `Entry <b>${fmtP(cardEntry)}</b> · `;
      verdictText += `SL <b style="color:var(--red);">${fmtP(cardSL)}</b> (below cycle low — exit if breached) · `;
      verdictText += `T1 <b style="color:var(--green);">${fmtP(cardT1)}</b> (exit 50%, activate trailing SL) · `;
      verdictText += `T2 <b style="color:var(--green);">${fmtP(cardT2)}</b> (distribution zone — full cycle exit). `;
      verdictText += `<b>No time limit</b> — hold until trailing SL is struck. R:R <b>${cardRR}</b>.`;
    } else if (cycleAction === 'HOLD & TRAIL') {
      verdictText  = `${cycleIcon} <b style="color:${cycleColor};">CYCLE PHASE: ${cycleLabel} — ${cycleAction}</b><br>`;
      verdictText += `${cardSym} is in active markup — the positive cycle is running. `;
      verdictText += `If holding: trail SL with 7–10% step, target T1 <b>${fmtP(cardT1)}</b> → then let T2 <b>${fmtP(cardT2)}</b> run freely. `;
      verdictText += `If not yet in: wait for pullback to <b>${fmtP(cardEntry)}</b>. Do not chase price at current levels.`;
    } else {
      verdictText  = `${cycleIcon} <b style="color:${cycleColor};">CYCLE PHASE: ${cycleLabel} — ${cycleAction}</b><br>`;
      verdictText += `${cardSym} is approaching the distribution zone — cycle is maturing. `;
      verdictText += `If holding: begin trimming at T1 <b>${fmtP(cardT1)}</b>. `;
      verdictText += `New long entries are not recommended at this stage. `;
      verdictText += `Wait for the next accumulation phase before re-entering.`;
    }
    // Always append Gann date for long type
    if (buyDate) verdictText += ` <br>📅 <b>Key Gann date: ${buyDate}</b> — cycle inflection point, watch for volume + direction change.`;

  } else {
    // ── SHORT/SWING TYPE: original signal-based verdict ─────────────────────
    verdictText = rep.overall_verdict || '';
    if (bias === 'BULLISH' && entry && t1) {
      if (!verdictText) verdictText = `${rep.symbol||sym} presents a ${confLabel.toLowerCase()}-confidence BULLISH setup.`;
      verdictText += ` <b style="color:var(--green);">Trade plan:</b> `
        + `Entry ${fmtP(entry)} · T1 ${fmtP(t1)} · T2 ${fmtP(t2)} · SL ${fmtP(sl)} · R:R ${rrStr}. `
        + (buyDate ? `Enter on/after <b>${buyDate}</b>. ` : '')
        + (sellDate ? `Exit T1 or by <b>${sellDate}</b> — whichever first. ` : '')
        + `T1 hit → trail SL to cost → run to T2.`;
      if (met.rsi > 75) verdictText += ` ⚠ RSI ${met.rsi} elevated — wait for dip to entry.`;
    } else if (bias === 'BEARISH') {
      if (!verdictText) verdictText = `${rep.symbol||sym} shows bearish pressure — avoid new long entries.`;
      verdictText += ` If holding, tighten SL. Re-assess at Gann Sq9 support ${fmtP(sl)} — bounce + bullish natal = re-entry.`;
      if (buyDate) verdictText += ` Watch reversal window: <b>${buyDate}</b>.`;
    } else {
      if (!verdictText) verdictText = `${rep.symbol||sym} shows no high-conviction setup. Mixed signals — wait for breakout/breakdown.`;
      verdictText += (entry && t1) ? ` Monitor: above ${fmtP(t1)} = bullish · below ${fmtP(sl)} = avoid.` : '';
      if (buyDate) verdictText += ` Gann date <b>${buyDate}</b> may provide a directional catalyst.`;
    }
  }

  const verdict = `
    <div style="padding:18px 20px;border:2px solid ${verdictBorderColor};background:rgba(0,0,0,0.2);margin-bottom:10px;">
      <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:${verdictBorderColor};letter-spacing:3px;margin-bottom:10px;">
        ${invType === 'long' ? '🔄 CYCLE POSITION — ENTRY / HOLD / EXIT GUIDANCE' : '🎯 OVERALL VERDICT — CURRENT + FORWARD OUTLOOK'}
      </div>
      <div style="font-family:Rajdhani,sans-serif;font-size:1rem;color:var(--white);line-height:1.8;font-weight:500;">
        ${verdictText}
      </div>
      <div style="margin-top:10px;font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);">
        Generated: ${new Date().toLocaleString('en-IN')} · ${rep.symbol||''} · ₹${Number(rep.price||0).toLocaleString('en-IN')} · ${rep.date||''}
      </div>
    </div>`;

  const disclaimer = `<div style="padding:8px 12px;background:rgba(58,90,112,0.12);border-left:2px solid var(--dim);font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;line-height:1.6;">⚠ For educational purposes only. Not financial advice. All trades carry risk.</div>`;

  // ── Store rec for deploy ──────────────────────────────────────────────────
  // Must be set here so deploySingleStock() can access it regardless of when
  // the user clicks the button (after async render).
  if (rec) window._singleRec = rec;

  // ── AUTO-PILOT deploy banner (only when there's a valid bullish signal) ──
  const showDeploy = rec && rec.entry > 0 && rec.shares > 0 && bias !== 'BEARISH';
  const deployBanner = showDeploy ? `
    <div class="easy-only" style="background:rgba(41,98,255,0.10);border:1px solid var(--cyan);
      border-radius:4px;padding:14px 16px;margin-bottom:12px;">
      <div style="color:var(--cyan);font-weight:bold;margin-bottom:6px;font-family:Share Tech Mono,monospace;font-size:0.8rem;letter-spacing:1px;">
        ✨ SINGLE STOCK SIGNAL READY
      </div>
      <div style="font-family:Inter,sans-serif;font-size:0.8rem;color:var(--text);line-height:1.5;margin-bottom:10px;">
        ${rec.name || rec.symbol} has a <b style="color:${confCol};">${confLabel}-confidence</b> signal.
        Entry ₹${Number(rec.entry||0).toLocaleString('en-IN',{maximumFractionDigits:2})} ·
        SL ₹${Number(rec.stop_loss||0).toLocaleString('en-IN',{maximumFractionDigits:2})} ·
        T1 ₹${Number(rec.target1||0).toLocaleString('en-IN',{maximumFractionDigits:2})} ·
        ${rec.shares||0} shares — deploy to Paper Portfolio with one click.
      </div>
      <button onclick="deploySingleStock()"
        style="width:100%;padding:10px;background:var(--cyan);color:var(--bg);border:none;
        border-radius:4px;font-family:Share Tech Mono,monospace;font-size:0.78rem;
        font-weight:bold;letter-spacing:2px;cursor:pointer;">
        🚀 DEPLOY TO PAPER PORTFOLIO
      </button>
    </div>` : '';

  return `<div style="margin-top:20px;">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
      <div style="flex:1;height:1px;background:linear-gradient(90deg,var(--border),rgba(0,212,255,0.4),var(--border));"></div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--cyan);letter-spacing:3px;white-space:nowrap;">📊 DEEP ANALYSIS — ENGINE BREAKDOWN</div>
      <div style="flex:1;height:1px;background:linear-gradient(90deg,var(--border),rgba(0,212,255,0.4),var(--border));"></div>
    </div>
    ${metricsStrip}${panelGrid}${verdict}${deployBanner}${disclaimer}
  </div>`;
}

async function runAdvisor() {
  const amount   = parseFloat(document.getElementById('adv-amount').value)||100000;
  const invType  = document.getElementById('adv-type').value;
  const risk     = document.getElementById('adv-risk').value;
  const diversify= document.getElementById('adv-diversify').value;
  const sector   = document.getElementById('adv-sector').value;
  const prompt   = document.getElementById('adv-prompt').value;

  // Parse prompt for overrides — extract amount, type, risk, sector, symbols
  let overrides = {};
  let promptAdvice = '';
  if (prompt) {
    const lower = prompt.toLowerCase();

    // Amount
    const amtMatch = prompt.match(/[₹\$]?\s*(\d[\d,]+)/);
    if (amtMatch) overrides.amount = parseFloat(amtMatch[1].replace(/,/g,''));

    // Investment type
    if (/swing|2.5 day|short.?term|intraday/.test(lower)) overrides.type = 'swing';
    else if (/short|week|30 day|month/.test(lower)) overrides.type = 'short';
    else if (/long.?term|year|invest/.test(lower)) overrides.type = 'long';
    else if (/position|gann.*long|long.*range/.test(lower)) overrides.type = 'hedge_fund';

    // Risk
    if (/max profit|aggressive|high risk|maximum/.test(lower)) overrides.risk = 'high';
    else if (/low risk|safe|capital protect|min risk/.test(lower)) overrides.risk = 'low';

    // Sector
    if (/it |tech|software|infosys|tcs|wipro/.test(lower)) overrides.sector = 'it';
    else if (/bank|finance|hdfc|icici|sbi/.test(lower)) overrides.sector = 'banking';
    else if (/pharma|health|drug|cipla|sun/.test(lower)) overrides.sector = 'pharma';
    else if (/auto|car|maruti|bajaj/.test(lower)) overrides.sector = 'auto';

    // Diversification
    const divMatch = lower.match(/(\d+)\s*stock/);
    if (divMatch) overrides.diversify = Math.min(5, Math.max(1, parseInt(divMatch[1])));
    if (/any number|diversif/.test(lower)) overrides.diversify = 5;

    // Specific symbols
    const symbols = ['TCS','INFY','WIPRO','HCLTECH','RELIANCE','HDFC','ICICI','SBIN',
                     'NTPC','COALINDIA','TATASTEEL','MARUTI','SUNPHARMA','GOLD','NIFTY50'];
    const found = symbols.filter(s => prompt.toUpperCase().includes(s));
    if (found.length) overrides.symbols = found.join(',');
  }

  document.getElementById('adv-loading').style.display='flex';
  document.getElementById('adv-error').style.display='none';
  document.getElementById('adv-no-signal').style.display='none';
  document.getElementById('adv-results').style.display='none';
  document.getElementById('adv-portfolio-card').style.display='none';
  const nakCardReset = document.getElementById('adv-nakshatra-card');
  if (nakCardReset) nakCardReset.style.display = 'none';
  const promptInterpretEl = document.getElementById('adv-prompt-interp');
  if (promptInterpretEl) promptInterpretEl.style.display='none';

  const steps = [
    'Fetching planetary positions...',
    'Running Gann confluence analysis for all symbols...',
    'Computing Simons Lab regime scores...',
    'Analysing natal chart transits...',
    'Optimising portfolio allocation...',
    'Generating investment report...'
  ];
  let si=0;
  const stxt=document.getElementById('adv-loading-text');
  const interval=setInterval(()=>{ stxt.textContent=steps[si++ % steps.length]; },1800);

  try {
    if (currentAdvisorTabMode === 'planner') {
      const ratio = parseFloat(document.getElementById('adv-ratio').value) / 100.0;
      const d = await api('advisor_plan', {
        type: invType,
        risk: risk,
        ratio: ratio
      });
      clearInterval(interval);
      document.getElementById('adv-loading').style.display='none';
      window.currentPlannerData = d;
      renderAdvisorPlanner(d);
      return;
    }

    const params = {
      amount:    overrides.amount || amount,
      type:      overrides.type   || invType,
      risk:      overrides.risk   || risk,
      diversify: overrides.diversify || diversify,
      sector:    overrides.sector || sector,
    };
    if (overrides.symbols) params.symbols = overrides.symbols;
    const d = await api('advisor', params);
    clearInterval(interval);
    document.getElementById('adv-loading').style.display='none';
    renderAdvisor(d);
  } catch(e) {
    clearInterval(interval);
    document.getElementById('adv-loading').style.display='none';
    const msg = e.message || '';
    if (msg.includes('No suitable symbols') || msg.includes('no suitable') || msg.includes('filter')) {
      // Show rich no-signal card with reason
      const reasonEl = document.getElementById('adv-no-signal-reason');
      if (reasonEl) {
        const inv = document.getElementById('adv-type')?.value || 'short';
        const typeLabels = {swing:'Swing (5–15 days)', short:'Short Term (15–45 days)', long:'Long Term (3–18 months)', position:'Position (3–18 months)'};
        reasonEl.innerHTML =
          `<span style="color:var(--orange);">- SCAN TYPE:</span> ${typeLabels[inv] || inv}<br>` +
          `<span style="color:var(--orange);">- GATE STATUS:</span> All 40 instruments scanned — none passed the Gann + Quant + Regime filter gates<br>` +
          `<span style="color:var(--orange);">- LIKELY CAUSE:</span> Current market regime (RSI mid-range / no Sq9 confluence / volume not confirming)<br>` +
          `<span style="color:var(--orange);">- SYSTEM NOTE:</span> This is intentional — the system only signals when edge is confirmed`;
      }
      document.getElementById('adv-no-signal').style.display='block';
    } else {
      document.getElementById('adv-error').style.display='block';
      document.getElementById('adv-error').textContent='⚠ ' + msg;
    }
  }
}

function renderAdvisor(d) {
  window.currentAdvisorData = d;
  document.getElementById('adv-results').style.display='block';
  document.getElementById('adv-portfolio-card').style.display='block';

  const recs   = d.recommendations || [];
  const amount = d.amount || 100000;

  // Show what the system understood from the prompt
  const interpEl = document.getElementById('adv-prompt-interp');
  if (interpEl && d.interpreted) {
    const iv = d.interpreted;
    interpEl.style.display='block';
    interpEl.innerHTML=`<div style="padding:8px 14px;background:rgba(0,212,255,0.05);
      border-left:3px solid var(--cyan);font-family:Share Tech Mono,monospace;font-size:0.7rem;
      color:var(--t2);margin-bottom:12px;">
      <span style="color:var(--cyan);font-weight:700;">🤖 UNDERSTOOD YOUR REQUEST AS:</span>
      Amount ₹${(iv.amount||amount).toLocaleString()} · ${iv.type||'swing'} · ${iv.risk||'balanced'} risk
      ${iv.sector?' · Sector: '+iv.sector:''} ${iv.symbols?' · Symbols: '+iv.symbols:''}
    </div>`;
  }

  const TYPE_LABEL = {swing:'Swing Trade (5–15 days)',short:'Short Term (15–45 days)',long:'Long Term (3–18 months)',position:'🌊 Position Trade — Gann Absolute Wave'};
  const RISK_LABEL = {low:'Low Risk',balanced:'Balanced',high:'High Risk (Aggressive)'};

  // ── Planet environment ────────────────────────────────────────────
  const pd = d.planet_dashboard || {};
  const aspects = pd.aspects || [];
  const skyBull = aspects.filter(a=>a.direction==='BULLISH').length;
  const skyBear = aspects.filter(a=>a.direction==='BEARISH').length;
  const maleficRetro = (pd.retrograde||[]).filter(r=>['Saturn','Mars','Rahu','Ketu'].includes(r));
  const stationNear  = (pd.stations||[]).length > 0;

  let pHtml = '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;">';
  aspects.slice(0,6).forEach(a=>{
    const c=a.direction==='BULLISH'?'var(--green)':a.direction==='BEARISH'?'var(--red)':'var(--gold)';
    const bg=a.direction==='BULLISH'?'rgba(0,255,136,0.08)':a.direction==='BEARISH'?'rgba(255,68,68,0.08)':'rgba(255,204,0,0.08)';
    pHtml+=`<span style="background:${bg};border:1px solid ${c};border-radius:2px;padding:2px 8px;font-family:Share Tech Mono,monospace;font-size:0.68rem;">
      <span style="color:${c};">●</span> ${a.planets||''} <b style="color:${c};">${a.direction||''}</b> ${(a.orb||0).toFixed(2)}°</span>`;
  });
  (pd.retrograde||[]).forEach(r=>{
    const col=['Saturn','Mars','Rahu','Ketu'].includes(r)?'var(--red)':'var(--orange)';
    pHtml+=`<span style="background:rgba(255,68,68,0.08);border:1px solid ${col};border-radius:2px;padding:2px 8px;font-family:Share Tech Mono,monospace;font-size:0.68rem;color:${col};">℞ ${r}</span>`;
  });
  (pd.stations||[]).forEach(s=>{
    pHtml+=`<span style="background:rgba(255,204,0,0.1);border:1px solid var(--gold);border-radius:2px;padding:2px 8px;font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--gold);">s ${s.planet} stations in ${s.days_away}d</span>`;
  });
  pHtml += '</div>';

  // Sky verdict
  let skyVerdict='', skyColor='', skyAction='';
  if (maleficRetro.length>=2 || skyBear>=skyBull+3) {
    skyVerdict='⛔ HIGH CAUTION — Sky is predominantly BEARISH';
    skyColor='var(--red)'; skyAction='Avoid new long positions today. Wait for sky to clear.';
  } else if (maleficRetro.length>=1 || skyBear>skyBull) {
    skyVerdict='⚠ MIXED SKY — More bearish aspects than bullish';
    skyColor='var(--orange)'; skyAction='Reduce position size by 50%. Use tighter stop losses.';
  } else if (stationNear) {
    skyVerdict='s VOLATILE SKY — Planetary station nearby';
    skyColor='var(--gold)'; skyAction='Expect sharp moves. Use strict stops. Good for breakout trades.';
  } else if (skyBull>skyBear+2) {
    skyVerdict='o. BULLISH SKY — Favourable planetary environment';
    skyColor='var(--green)'; skyAction='Sky confirms buy signals. Proceed with full position size.';
  } else {
    skyVerdict='🔵 NEUTRAL SKY — Balanced aspects';
    skyColor='var(--cyan)'; skyAction='Proceed with normal position sizing. Rely on Gann + Quant signals.';
  }
  pHtml += `<div style="display:flex;align-items:center;gap:12px;padding:8px 12px;
    background:rgba(0,0,0,0.3);border-left:3px solid ${skyColor};border-radius:2px;margin-bottom:4px;">
    <div>
      <div style="font-family:Orbitron,sans-serif;font-size:0.75rem;color:${skyColor};font-weight:700;">${skyVerdict}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--t2);margin-top:3px;">
        SKY: ${skyBull} BULL · ${skyBear} BEAR · ${maleficRetro.length} malefic℞ &nbsp;|&nbsp; 
        <span style="color:${skyColor};">ACTION: ${skyAction}</span>
      </div>
    </div>
  </div>`;

  document.getElementById('adv-planet-summary').innerHTML = pHtml;

  // ── Portfolio summary stats ───────────────────────────────────────
  const confColor = d.avg_confidence>=70?'var(--green)':d.avg_confidence>=50?'var(--gold)':'var(--red)';
  const rrColor   = d.portfolio_rr>=2?'var(--green)':d.portfolio_rr>=1.5?'var(--gold)':'var(--red)';

  const allProceed = d.avg_confidence>=60 && d.portfolio_rr>=1.5 && skyBull>=skyBear && maleficRetro.length<2;
  const pCol = allProceed ? 'var(--green)' : 'var(--gold)';

  let html = `<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:15px; flex-wrap:wrap; gap:10px;">
    <div>
      <div style="font-family:'Inter',sans-serif;font-size:0.75rem;color:var(--dim);text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;font-weight:600;">PORTFOLIO VERDICT</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:1rem;color:${pCol};">${allProceed?'o. CLEAR TO DEPLOY':'⚠️ CAUTION: SUB-OPTIMAL CONDITIONS'}</div>
    </div>
    
    <div class="easy-only" style="background:rgba(41,98,255,0.1); border:1px solid var(--cyan); border-radius:4px; padding:12px; max-width:400px;">
      <div style="color:var(--cyan); font-weight:bold; margin-bottom:4px;">✨ AUTO-PILOT PORTFOLIO GENERATED</div>
      <div style="font-family:Inter,sans-serif; font-size:0.8rem; color:var(--text); line-height:1.4;">
        We have automatically selected the ${d.recommendations.length} best stocks across different sectors. 
        Your risk is spread out, and every trade has a predefined Safety Net (Stop Loss). 
        Deploy this portfolio with a single click.
      </div>
      <button onclick="deployAutoPilot()" style="margin-top:10px; width:100%; padding:10px; background:var(--cyan); color:var(--white); border:none; border-radius:4px; font-weight:bold; cursor:pointer;">
        🚀 DEPLOY PORTFOLIO TO DEMAT
      </button>
    </div>
  </div>`;

  document.getElementById('adv-portfolio-stats').innerHTML = html + `
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:8px;">
      <div class="stat"><span class="val" style="color:var(--gold);">₹${(amount).toLocaleString()}</span><span class="lbl">TOTAL CAPITAL</span></div>
      <div class="stat"><span class="val" style="color:${confColor};">${(Math.round(d.avg_confidence * 10)/10).toFixed(1)}%</span><span class="lbl">AVG CONFIDENCE</span></div>
      <div class="stat"><span class="val" style="color:${rrColor};">${d.portfolio_rr}x</span><span class="lbl">PORTFOLIO R:R</span></div>
      <div class="stat"><span class="val" style="color:var(--red);">₹${(d.total_risk||0).toLocaleString()}</span><span class="lbl">MAX RISK</span></div>
    </div>
    <div style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--dim);">
      ${TYPE_LABEL[d.inv_type]||d.inv_type} · ${RISK_LABEL[d.risk_pref]||d.risk_pref} · Analysis date: ${d.analysis_date}
    </div>`;

  // ── Portfolio verdict — smart reversal-aware guidance ───────────────
  const mo = d.market_overview || {};
  const rf = d.reversal_forecast || {};
  const swingWait = rf.swing || mo.swing_wait || 0;
  const shortWait = rf.short || mo.short_wait || 0;
  const longWait  = rf.long  || mo.long_wait  || 0;
  const invTypeNow = d.inv_type || 'swing';

  // allProceed already defined above
  const allCaution = d.avg_confidence<50 || d.portfolio_rr<1.2 || maleficRetro.length>=2 || skyBear>skyBull+1;
  const pvColor = allProceed?'var(--green)':allCaution?'var(--red)':'var(--gold)';

  let pvText = '';
  let pvDetail = '';
  if (allProceed) {
    pvText = 'o. PROCEED — Conditions favour entering trades now';
    pvDetail = 'Sky and Gann signals align. Enter with full position size per allocation below.';
  } else if (allCaution) {
    // Build specific waiting guidance per horizon
    const swingLine = swingWait<=1 ? 'Swing: market ready now' : `Swing: wait ${swingWait} days (next clear window)`;
    const shortLine = shortWait<=3 ? 'Short-term: conditions improving soon' : `Short-term: wait ${shortWait} days`;
    const longLine  = longWait<=7  ? 'Long-term: accumulate on dips' : `Long-term: wait ~${Math.round(longWait/7)} weeks`;
    pvDetail = swingLine + '  ·  ' + shortLine + '  ·  ' + longLine;
    pvText = '⛔ AVOID NEW ENTRIES — Market in bearish phase. Hold capital.';
  } else {
    pvText = '⚠ CAUTION — Proceed with 50% size and tight stops';
    const waitDays = invTypeNow==='swing'?swingWait:invTypeNow==='short'?shortWait:longWait;
    pvDetail = waitDays>2 ? `Better entry window opens in ~${waitDays} days. Consider waiting.` : 'Conditions near acceptable. Use strict stop-losses.';
  }

  document.getElementById('adv-planet-verdict').innerHTML =
    '<div style="padding:10px 14px;background:rgba(0,0,0,0.4);border:1px solid '+pvColor+';border-radius:3px;">'
    +'<div style="font-family:Orbitron,sans-serif;font-size:0.72rem;color:'+pvColor+';font-weight:700;margin-bottom:6px;">'+pvText+'</div>'
    +(pvDetail?'<div style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--t2);line-height:1.6;">'+pvDetail+'</div>':'')
    +'</div>';

  // ── Portfolio allocation table (replaces pie) ────────────────────
  const PALLOC_COLS=['var(--cyan)','var(--gold)','var(--purple)','var(--green)','var(--orange)'];
  let allocHtml = `<div style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;font-family:Share Tech Mono,monospace;margin-bottom:6px;">PORTFOLIO ALLOCATION</div>`;
  recs.forEach((r,i)=>{
    const col=PALLOC_COLS[i%PALLOC_COLS.length];
    const pct=r.allocation_pct||0;
    allocHtml+=`<div style="margin-bottom:5px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">
        <span style="font-family:Share Tech Mono,monospace;font-size:0.75rem;color:${col};font-weight:700;">${r.symbol}</span>
        <span style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--t2);">₹${(r.allocation||0).toLocaleString()} · ${pct}%</span>
      </div>
      <div style="background:rgba(0,0,0,0.4);height:6px;border-radius:3px;">
        <div style="width:${Math.min(pct,100)}%;height:100%;background:${col};border-radius:3px;transition:width 0.8s;"></div>
      </div>
    </div>`;
  });
  document.getElementById('adv-alloc-table').innerHTML = allocHtml;

  // ── Recommendation cards ──────────────────────────────────────────
  const recEl = document.getElementById('adv-recs');
  recEl.innerHTML = '';
  recs.forEach((r,idx)=> {
    const card = buildRecCard(r, idx, amount);
    recEl.appendChild(card);
    // Draw price projection chart after DOM insertion
    setTimeout(()=> drawPriceProjection(`adv-proj-${idx}`, r), 100);
    setTimeout(()=> drawSRChart(`adv-sr-${idx}`, r), 150);
    setTimeout(()=> drawPlanetChart(`adv-planet-${idx}`, r), 200);
    // Store rec data for expand modal re-draw
    if(!window._advRecs) window._advRecs = {};
    window._advRecs[idx] = r;
  });

  _updateNakshatraWidget(d.nakshatra_today);
}

function _updateNakshatraWidget(nak) {
  const nakCard = document.getElementById('adv-nakshatra-card');
  if (!nakCard) return;
  if (nak && nak.nakshatra) {
    nakCard.style.display = 'block';
    
    const nameEl = document.getElementById('adv-nak-name');
    if (nameEl) nameEl.innerHTML = `🌙 MOON IN ${nak.nakshatra.toUpperCase()} (${nak.ruler.toUpperCase()})`;
    
    const descEl = document.getElementById('adv-nak-behavior-desc');
    if (descEl) {
      descEl.innerHTML = `This lunar mansion is classified as <b>${nak.guna || 'N/A'}</b> with a <b>${nak.behavior || 'N/A'}</b> behavior profile. ` +
        `Cosmic trade recommendation: <b style="color:var(--cyan);">${nak.trade_style || 'N/A'}</b>. ${nak.market_note || ''}`;
    }
    
    const sectorsEl = document.getElementById('adv-nak-sectors');
    if (sectorsEl) {
      const favSectors = nak.fav_sectors || [];
      sectorsEl.innerHTML = `<span style="color:var(--gold);">- COSMICALLY FAVORED SECTORS:</span> ` +
        (favSectors.length > 0 ? favSectors.join(', ') : 'All sectors neutral');
    }
    
    const muhuratEl = document.getElementById('adv-nak-muhurat');
    if (muhuratEl) muhuratEl.textContent = nak.abhijit_muhurat || '—';
    
    const rahuEl = document.getElementById('adv-nak-rahu');
    if (rahuEl) rahuEl.textContent = nak.rahu_kaal || '—';
    
    const scoreBadge = document.getElementById('adv-nak-score-badge');
    if (scoreBadge) {
      scoreBadge.textContent = `BONUS: +${nak.nak_score || 0} PTS`;
    }
  } else {
    nakCard.style.display = 'none';
  }
}

function buildRecCard(r, idx, totalAmount) {
  const confColor = r.confidence>=70?'var(--green)':r.confidence>=50?'var(--gold)':'var(--orange)';
  const regColor  = {STRONG_BULL:'var(--green)',WEAK_BULL:'#8fea80',SIDEWAYS:'var(--gold)',
    WEAK_BEAR:'var(--orange)',STRONG_BEAR:'var(--red)',HIGH_VOLATILITY:'var(--orange)'}[r.regime]||'var(--t2)';
  const rrColor   = r.rr_ratio>=2?'var(--green)':r.rr_ratio>=1?'var(--gold)':'var(--red)';

  const el = document.createElement('div');
  el.style.marginBottom='20px';
  el.innerHTML = `
  <div class="card">
    <!-- Header -->
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid var(--border);">
      <div style="font-family:Orbitron,sans-serif;font-size:1.1rem;font-weight:900;color:var(--cyan);">
        #${idx+1} ${r.symbol}
      </div>
      <div style="flex:1;">
        <div style="font-size:0.8rem;color:var(--t2);">${r.name}</div>
        <div style="font-size:0.65rem;color:var(--dim);">${r.sector} · ${r.exchange} · Ruler: ${r.ruling_planet}</div>
      </div>
      <div style="display:flex;align-items:center;gap:12px;">
        <button onclick="deploySingleRecommendation(${idx})"
          style="padding:6px 14px;background:rgba(0,212,255,0.08);border:1px solid var(--cyan);
          border-radius:3px;color:var(--cyan);font-family:Share Tech Mono,monospace;font-size:0.65rem;
          font-weight:bold;cursor:pointer;letter-spacing:1px;height:fit-content;transition:all 0.2s;">
          🚀 TAKE TRADE
        </button>
        <div style="text-align:right;">
          <div style="font-family:Orbitron,sans-serif;font-size:1.4rem;font-weight:900;color:${confColor};">${Math.round(r.confidence * 10) / 10}%</div>
          <div style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;">CONFIDENCE</div>
        </div>
      </div>
    </div>

    <!-- Score breakdown -->
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:14px;">
      ${scoreBar('FUND', r.fund_score||0, 25, 'var(--gold)')}
      ${scoreBar('GANN', r.gann_score||0, 20, 'var(--cyan)')}
      ${scoreBar('QUANT', r.quant_score||0, 20, 'var(--purple)')}
      ${scoreBar('NATAL', r.natal_score||0, 20, 'var(--green)')}
      ${scoreBar('PLANET', r.planet_score||0, 15, 'var(--orange)')}
    </div>

    <!-- ── TRADE LEVELS TILE ROW ─────────────────────────────────────────── -->
    ${(()=>{
      const cmp      = r.price   || r.cmp  || 0;
      const entry    = r.entry   || 0;
      const sl       = r.stop_loss || 0;
      const t1       = r.target1 || 0;
      const t2       = r.target2 || 0;
      const rr       = r.rr_ratio ? Number(r.rr_ratio).toFixed(2) : '—';
      const shares   = r.shares  || 0;
      const maxProfit = t1 > 0 && entry > 0 && shares > 0
        ? ((t1 - entry) * shares).toLocaleString('en-IN', {maximumFractionDigits: 0})
        : '—';
      const maxLoss  = sl > 0 && entry > 0 && shares > 0
        ? ((entry - sl) * shares).toLocaleString('en-IN', {maximumFractionDigits: 0})
        : '—';
      const rrCol    = r.rr_ratio >= 2 ? 'var(--green)' : r.rr_ratio >= 1 ? 'var(--gold)' : 'var(--red)';
      const entryPct = cmp > 0 && entry > 0 ? ((entry - cmp) / cmp * 100) : 0;
      const entryPctStr = entryPct === 0 ? 'AT MARKET' : (entryPct > 0 ? '+' : '') + entryPct.toFixed(1) + '%';
      const slPct    = entry > 0 && sl > 0   ? ((sl - entry)  / entry * 100).toFixed(1) : '—';
      const t1Pct    = entry > 0 && t1 > 0   ? ((t1 - entry)  / entry * 100).toFixed(1) : '—';
      const t2Pct    = entry > 0 && t2 > 0   ? ((t2 - entry)  / entry * 100).toFixed(1) : '—';

      const fmt = v => v > 0
        ? '₹' + v.toLocaleString('en-IN', {maximumFractionDigits: 2})
        : '—';

      const tile = (label, value, sub, color, bg) =>
        '<div style="text-align:center;padding:8px 4px;background:' + bg + ';border:1px solid rgba(255,255,255,0.06);border-radius:3px;">'
        + '<div style="font-family:Share Tech Mono,monospace;font-size:0.52rem;color:var(--dim);letter-spacing:1px;margin-bottom:3px;">' + label + '</div>'
        + '<div style="font-family:Orbitron,sans-serif;font-size:0.82rem;font-weight:900;color:' + color + ';line-height:1.1;">' + value + '</div>'
        + (sub ? '<div style="font-family:Share Tech Mono,monospace;font-size:0.5rem;color:var(--dim);margin-top:2px;">' + sub + '</div>' : '')
        + '</div>';

      return '<div style="display:grid;grid-template-columns:repeat(8,1fr);gap:5px;margin-bottom:14px;">'
        + tile('CMP',        fmt(cmp),   'LIVE PRICE',               'var(--cyan)',  'rgba(0,212,255,0.04)')
        + tile('ENTRY',      fmt(entry), entryPctStr,                'var(--green)', 'rgba(0,255,136,0.04)')
        + tile('STOP LOSS',  fmt(sl),    slPct !== '—' ? slPct + '%' : '',  'var(--red)',   'rgba(255,68,68,0.04)')
        + tile('TARGET 1',   fmt(t1),    t1Pct !== '—' ? '+' + t1Pct + '%' : '', 'var(--gold)',  'rgba(255,204,0,0.04)')
        + tile('TARGET 2',   fmt(t2),    t2Pct !== '—' ? '+' + t2Pct + '%' : '', 'var(--gold)',  'rgba(255,204,0,0.04)')
        + tile('R : R',      rr !== '—' ? '1 : ' + rr : '—', 'RISK REWARD',       rrCol,         'rgba(0,0,0,0.2)')
        + tile('MAX PROFIT', maxProfit !== '—' ? '₹' + maxProfit : '—', shares > 0 ? shares + ' shares' : '', 'var(--green)', 'rgba(0,255,136,0.04)')
        + tile('MAX LOSS',   maxLoss   !== '—' ? '₹' + maxLoss   : '—', 'AT SL HIT',  'var(--red)',   'rgba(255,68,68,0.04)')
        + '</div>';
    })()}

    ${(()=>{
      if (!r.fund_grade) return '';
      const _gr=r.fund_grade||''; const _gv=r.fund_verdict||''; const _fr=r.fund_ratios||{};
      let _h='<div style="display:flex;gap:8px;align-items:center;margin-bottom:10px;flex-wrap:wrap;">';
      _h+='<span style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);">FUNDAMENTAL:</span>';
      _h+='<span style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--gold);font-weight:700;">'+_gr+' — '+_gv+'</span>';
      if(_fr.pe||_fr.roe) _h+='<span style="color:var(--dim);font-size:0.65rem;"> P/E:'+(_fr.pe||'—')+' ROE:'+(_fr.roe||'—')+' D/E:'+(_fr.de||'—')+'</span>';
      (_fr.rev_g?[_fr.rev_g]:[]).forEach(function(v){_h+=' Rev:'+v;});
      (r.fund_signals||[]).slice(0,2).forEach(function(s){_h+='<span style="background:rgba(255,204,0,0.07);border:1px solid rgba(255,204,0,0.25);padding:1px 7px;font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--gold);">'+s+'</span>';});
      _h+='</div>'; return _h;
    })()}

    <!-- Combined Signal bar — all 5 engines -->
    <div style="background:rgba(0,0,0,0.3);border:1px solid var(--b2);border-radius:3px;padding:10px 14px;margin-bottom:14px;">
      <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);letter-spacing:2px;margin-bottom:8px;">🌌 COMBINED SIGNAL — ALL ENGINES</div>
      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:8px;">
        <div style="text-align:center;background:var(--p2);border:1px solid rgba(255,204,0,0.25);padding:6px 4px;">
          <div style="font-family:Orbitron,sans-serif;font-size:1rem;color:var(--gold);font-weight:900;">${(r.fund_score||0).toFixed(0)}<span style="font-size:0.6rem;color:var(--dim);">/25</span></div>
          <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);letter-spacing:1px;margin-top:2px;">FUNDAMENTAL</div>
          <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--gold);margin-top:2px;">${r.fund_grade||'—'}</div>
        </div>
        <div style="text-align:center;background:var(--p2);border:1px solid rgba(0,212,255,0.25);padding:6px 4px;">
          <div style="font-family:Orbitron,sans-serif;font-size:1rem;color:var(--cyan);font-weight:900;">${(r.gann_score||0).toFixed(0)}<span style="font-size:0.6rem;color:var(--dim);">/20</span></div>
          <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);letter-spacing:1px;margin-top:2px;">GANN</div>
        </div>
        <div style="text-align:center;background:var(--p2);border:1px solid rgba(204,136,255,0.25);padding:6px 4px;">
          <div style="font-family:Orbitron,sans-serif;font-size:1rem;color:var(--purple);font-weight:900;">${(r.quant_score||0).toFixed(0)}<span style="font-size:0.6rem;color:var(--dim);">/20</span></div>
          <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);letter-spacing:1px;margin-top:2px;">SIMONS</div>
        </div>
        <div style="text-align:center;background:var(--p2);border:1px solid rgba(0,255,136,0.25);padding:6px 4px;">
          <div style="font-family:Orbitron,sans-serif;font-size:1rem;color:var(--green);font-weight:900;">${(r.natal_score||0).toFixed(0)}<span style="font-size:0.6rem;color:var(--dim);">/20</span></div>
          <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);letter-spacing:1px;margin-top:2px;">NATAL</div>
        </div>
        <div style="text-align:center;background:var(--p2);border:1px solid rgba(255,136,0,0.25);padding:6px 4px;">
          <div style="font-family:Orbitron,sans-serif;font-size:1rem;color:var(--orange);font-weight:900;">${(r.planet_score||0).toFixed(0)}<span style="font-size:0.6rem;color:var(--dim);">/15</span></div>
          <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);letter-spacing:1px;margin-top:2px;">PLANETS</div>
        </div>
      </div>
      <!-- Total bar -->
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);min-width:80px;">TOTAL: <span style="color:${r.confidence>=70?'var(--green)':r.confidence>=50?'var(--gold)':'var(--red)'};font-weight:700;">${Math.round(r.confidence * 10) / 10}/100</span></div>
        <div style="flex:1;background:rgba(0,0,0,0.4);height:6px;border-radius:3px;">
          <div style="width:${r.confidence}%;height:100%;background:${r.confidence>=70?'var(--green)':r.confidence>=50?'var(--gold)':'var(--red)'};border-radius:3px;transition:width 1s;"></div>
        </div>
      </div>
    </div>`;

    if (r.sector_index) {
      const sit = r.sector_index_trend || 'UNKNOWN';
      const sic = r.sector_index_chg || 0;
      const divWarn = r.sector_divergence_warning || '';
      const sitCol = sit === 'BULLISH' ? 'var(--green)' : sit === 'BEARISH' ? 'var(--red)' : 'var(--gold)';
      const sitIcon = sit === 'BULLISH' ? '\uD83D\uDFE2' : sit === 'BEARISH' ? '\uD83D\uDD34' : '\uD83D\uDFE1';
      el.innerHTML += '<div style="margin-top:12px;padding:8px;background:rgba(0,0,0,0.3);border-radius:4px;display:flex;align-items:center;gap:12px;">'
        + '<span style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);">SECTOR INDEX:</span>'
        + '<span style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--cyan);">' + (r.sector_index||'') + '</span>'
        + '<span style="font-family:Share Tech Mono,monospace;font-size:0.75rem;font-weight:700;color:' + sitCol + ';">'
        + sitIcon + ' ' + sit + ' (' + (sic >= 0 ? '+' : '') + (sic||0).toFixed(1) + '% 20d)</span>'
        + (divWarn ? '<span style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--gold);padding:1px 7px;background:rgba(255,204,0,0.07);border:1px solid rgba(255,204,0,0.25);">'
          + '&#9888; ' + divWarn + '</span>' : '')
        + '</div>';
    }

    el.innerHTML += `
<!-- 3-column details -->
    <div class="g2" style="margin-bottom:14px;">
      <!-- Buy reasons -->
      <div>
        <div style="font-size:0.65rem;color:var(--green);letter-spacing:1px;margin-bottom:6px;font-family:Share Tech Mono,monospace;">o. REASONS TO BUY</div>
        ${(r.buy_reasons||[]).map(b=>`<div style="font-size:0.75rem;color:var(--t2);padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.03);">? ${b}</div>`).join('')}
        <div style="font-size:0.65rem;color:var(--red);letter-spacing:1px;margin-top:10px;margin-bottom:6px;font-family:Share Tech Mono,monospace;">?O EXIT / SELL SIGNALS</div>
        ${(r.sell_reasons||[]).map(s=>`<div style="font-size:0.75rem;color:var(--t2);padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.03);">? ${s}</div>`).join('')}
      </div>
      <!-- Planetary -->
      <div>
        <div style="font-size:0.65rem;color:var(--purple);letter-spacing:1px;margin-bottom:6px;font-family:Share Tech Mono,monospace;">🌌 PLANETARY INFLUENCE</div>
        ${(r.planet_text||[]).map(pt=>`<div style="font-size:0.75rem;color:var(--t2);padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.03);">${pt}</div>`).join('')}
        <div style="margin-top:8px;font-size:0.7rem;">
          <span style="color:var(--green);margin-right:12px;">▲ ${r.bull_signals} BULL signals</span>
          <span style="color:var(--red);">▼ ${r.bear_signals} BEAR signals</span>
        </div>
        <div style="margin-top:8px;font-size:0.72rem;color:${regColor};">
          Market Regime: <b>${(r.regime||'').replace('_',' ')}</b>
        </div>
        <div style="margin-top:4px;font-size:0.7rem;color:var(--dim);">
          Expected hold: <span style="color:var(--cyan);">~${r.hold_days} days</span>
        </div>
      </div>
    </div>

    <!-- ── v4.0.1 ML DEEP SIGNAL ENGINE PANEL — investment-type-aware ── -->
    ${(()=>{
      // Pick the ML block matching the active investment type
      const invType = r.inv_type || 'swing';
      const mlBlock = invType === 'swing' ? (r.ml_swing || {})
                    : invType === 'short' ? (r.ml_short || {})
                    : (r.ml_long || {});

      const mlTrained = mlBlock.model_trained || r.ml_model_trained || false;
      const mlDir     = mlBlock.direction || 'NEUTRAL';
      const mlConf    = mlBlock.confidence || 0;
      const mlRevP    = mlBlock.reversal_price || 0;
      const mlRevD    = (mlBlock.reversal_date || '').replace(/-/g,'/');
      const mlDays    = mlBlock.days_to_rev || 0;
      const mlMove    = mlBlock.expected_move || 0;
      const mlSigAl   = mlBlock.signal_alignment || 0;
      const mlHorizon = mlBlock.horizon || (invType==='swing'?'5–15 days':invType==='short'?'15–45 days':'3–18 months');
      const revMap    = mlBlock.reversal_map || [];

      const horizonLabel = invType==='swing'?'SWING (5–15 DAYS)':invType==='short'?'SHORT TERM (15–45 DAYS)':'LONG TERM (3–18 MONTHS)';

      if (!mlTrained && mlConf < 0.45) {
        return '<div style="padding:8px 14px;background:rgba(0,0,0,0.2);border:1px solid rgba(255,255,255,0.06);margin-bottom:14px;">'
          + '<div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:2px;margin-bottom:4px;">🤖 ML DEEP SIGNAL ENGINE</div>'
          + '<div style="font-size:0.65rem;color:var(--dim);">Model not yet trained — click <span style="color:var(--cyan);">TRAIN MODEL</span> in the top bar to enable ML reversal predictions.</div>'
          + '</div>';
      }

      const dirCol   = mlDir==='UP'?'var(--green)':mlDir==='DOWN'?'var(--red)':'var(--gold)';
      const dirLabel = mlDir==='UP'?'▲ BULLISH':mlDir==='DOWN'?'▼ BEARISH':'━ NEUTRAL / SIDEWAYS';
      const confPct  = Math.round(mlConf * 100);
      const confCol  = confPct>=70?'var(--green)':confPct>=55?'var(--gold)':'var(--orange)';
      const revPDiff = mlRevP > 0 && r.price > 0 ? ((mlRevP - r.price)/r.price*100) : 0;
      const revPDiffStr = (revPDiff>=0?'+':'')+revPDiff.toFixed(1)+'%';
      const revPDiffCol = revPDiff>0?'var(--green)':revPDiff<0?'var(--red)':'var(--dim)';

      // ── Reversal timeline mini-chart (SVG sparkline) ──────────────────────
      function buildReversalChart(revMap, curPrice, horizon) {
        if (!revMap || revMap.length === 0) return '';
        const W = 320, H = 52, pad = 8;
        const maxDay = horizon === '5–15 days' ? 15 : horizon === '15–45 days' ? 45 : 60;
        const prices  = [curPrice, ...revMap.map(p=>p.price)];
        const pMin    = Math.min(...prices) * 0.995;
        const pMax    = Math.max(...prices) * 1.005;
        const pRng    = Math.max(pMax - pMin, curPrice * 0.01);
        const xScale  = (d) => pad + (d / maxDay) * (W - pad*2);
        const yScale  = (p) => H - pad - ((p - pMin) / pRng) * (H - pad*2);

        // Build polyline through current price (day 0) + all reversal points
        const allPts  = [{day:0, price:curPrice}, ...revMap];
        const pts     = allPts.map(p => xScale(p.day).toFixed(1)+','+yScale(p.price).toFixed(1)).join(' ');

        let svg = '<svg width="'+W+'" height="'+H+'" viewBox="0 0 '+W+' '+H+'" style="overflow:visible">';

        // Zero line (current price reference)
        const y0 = yScale(curPrice).toFixed(1);
        svg += '<line x1="'+pad+'" y1="'+y0+'" x2="'+(W-pad)+'" y2="'+y0+'" stroke="rgba(255,255,255,0.1)" stroke-width="0.5" stroke-dasharray="3,3"/>';

        // Path
        svg += '<polyline points="'+pts+'" fill="none" stroke="rgba(0,212,255,0.5)" stroke-width="1.5"/>';

        // Dots + labels at reversal points
        revMap.forEach(function(pt) {
          const cx = xScale(pt.day).toFixed(1);
          const cy = yScale(pt.price).toFixed(1);
          const col = pt.type==='HIGH' ? '#ff4d4d' : '#00cc88';
          const sym = pt.type==='HIGH' ? '▲' : '▼';
          svg += '<circle cx="'+cx+'" cy="'+cy+'" r="3" fill="'+col+'" stroke="rgba(0,0,0,0.5)" stroke-width="0.5"/>';
          const labelY = pt.type==='HIGH' ? (parseFloat(cy)-6).toFixed(1) : (parseFloat(cy)+10).toFixed(1);
          svg += '<text x="'+cx+'" y="'+labelY+'" text-anchor="middle" font-size="8" fill="'+col+'" font-family="Share Tech Mono,monospace">'+sym+' d'+pt.day+'</text>';
        });

        // Current price dot
        svg += '<circle cx="'+pad+'" cy="'+y0+'" r="3" fill="var(--cyan)"/>';
        svg += '<text x="'+(pad+5)+'" y="'+(parseFloat(y0)-4).toFixed(1)+'" font-size="8" fill="var(--cyan)" font-family="Share Tech Mono,monospace">CMP</text>';

        svg += '</svg>';
        return '<div style="margin-top:10px;padding:8px;background:rgba(0,0,0,0.2);border:1px solid rgba(255,255,255,0.06);">'
          + '<div style="font-family:Share Tech Mono,monospace;font-size:0.52rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">PREDICTED REVERSAL TIMELINE — next '+maxDay+' trading days</div>'
          + svg
          + '<div style="display:flex;gap:12px;margin-top:4px;">'
          + '<span style="font-size:0.55rem;color:#00cc88;font-family:Share Tech Mono,monospace;">▼ = cycle low (buy zone)</span>'
          + '<span style="font-size:0.55rem;color:#ff4d4d;font-family:Share Tech Mono,monospace;">▲ = cycle high (exit zone)</span>'
          + '</div>'
          + '</div>';
      }

      return '<div style="padding:12px 14px;background:rgba(0,212,255,0.04);border:1px solid rgba(0,212,255,0.2);border-left:3px solid '+confCol+';margin-bottom:14px;">'
        // Header row
        + '<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        + '<div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--cyan);letter-spacing:2px;">🤖 ML DEEP SIGNAL ENGINE v4.0</div>'
        + '<span style="font-family:Share Tech Mono,monospace;font-size:0.52rem;background:rgba(0,212,255,0.1);border:1px solid rgba(0,212,255,0.3);color:var(--cyan);padding:1px 6px;">'+horizonLabel+'</span>'
        + (mlTrained
            ? '<span style="font-family:Share Tech Mono,monospace;font-size:0.52rem;background:rgba(0,255,136,0.1);border:1px solid rgba(0,255,136,0.3);color:var(--green);padding:1px 6px;">MODEL TRAINED</span>'
            : '<span style="font-family:Share Tech Mono,monospace;font-size:0.52rem;background:rgba(255,204,0,0.1);border:1px solid rgba(255,204,0,0.3);color:var(--gold);padding:1px 6px;">RULE-BASED</span>')
        + '</div>'
        // 4-column stats grid
        + '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px;">'
        + '<div style="background:var(--p2);border:1px solid rgba(0,0,0,0.3);padding:8px 10px;text-align:center;">'
        + '<div style="font-family:Orbitron,sans-serif;font-size:0.85rem;font-weight:900;color:'+dirCol+';">'+dirLabel+'</div>'
        + '<div style="font-family:Share Tech Mono,monospace;font-size:0.52rem;color:var(--dim);letter-spacing:1px;margin-top:3px;">PREDICTED DIRECTION</div>'
        + '</div>'
        + '<div style="background:var(--p2);border:1px solid rgba(0,0,0,0.3);padding:8px 10px;text-align:center;">'
        + '<div style="font-family:Orbitron,sans-serif;font-size:0.9rem;font-weight:900;color:'+confCol+';">'+confPct+'%</div>'
        + '<div style="font-family:Share Tech Mono,monospace;font-size:0.52rem;color:var(--dim);letter-spacing:1px;margin-top:3px;">MODEL CONFIDENCE</div>'
        + '<div style="height:3px;background:rgba(255,255,255,0.06);margin-top:4px;border-radius:2px;">'
        + '<div style="width:'+confPct+'%;height:100%;background:'+confCol+';border-radius:2px;"></div></div>'
        + '</div>'
        + '<div style="background:var(--p2);border:1px solid rgba(0,0,0,0.3);padding:8px 10px;text-align:center;">'
        + '<div style="font-family:Orbitron,sans-serif;font-size:0.9rem;font-weight:900;color:var(--gold);">₹'+(mlRevP||0).toLocaleString("en-IN",{maximumFractionDigits:2})+'</div>'
        + '<div style="font-family:Share Tech Mono,monospace;font-size:0.52rem;color:var(--dim);letter-spacing:1px;margin-top:3px;">ML REVERSAL PRICE</div>'
        + (mlRevP > 0 ? '<div style="font-size:0.58rem;color:'+revPDiffCol+';margin-top:2px;">'+revPDiffStr+' from CMP</div>' : '')
        + '</div>'
        + '<div style="background:var(--p2);border:1px solid rgba(0,0,0,0.3);padding:8px 10px;text-align:center;">'
        + '<div style="font-family:Orbitron,sans-serif;font-size:0.85rem;font-weight:900;color:var(--cyan);">'+(mlRevD||'—')+'</div>'
        + '<div style="font-family:Share Tech Mono,monospace;font-size:0.52rem;color:var(--dim);letter-spacing:1px;margin-top:3px;">ML REVERSAL DATE</div>'
        + (mlDays > 0 ? '<div style="font-size:0.6rem;color:var(--dim);margin-top:2px;">in ~'+mlDays+' trading days</div>' : '')
        + '</div>'
        + '</div>'
        // Signal alignment bar + expected move
        + '<div style="display:flex;align-items:center;gap:10px;">'
        + '<div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);white-space:nowrap;">Signal alignment:</div>'
        + '<div style="flex:1;height:5px;background:rgba(255,255,255,0.06);border-radius:3px;">'
        + '<div style="width:'+(mlSigAl*100).toFixed(0)+'%;height:100%;background:'+confCol+';border-radius:3px;"></div></div>'
        + '<div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:'+confCol+';">'+(mlSigAl*100).toFixed(0)+'%</div>'
        + (mlMove > 0 ? '<div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--green);margin-left:10px;">Expected move: +'+mlMove.toFixed(1)+'%</div>' : '')
        + '</div>'
        // Reversal timeline mini-chart
        + buildReversalChart(revMap, r.price||0, mlHorizon)
        + '</div>';
    })()}

    <!-- ── Tech Momentum Panel ── -->
    ${(()=>{
      const wp = r.tech_momentum || r.wyckoff_phase || 'N/A';
      const ws = r.tech_score > 5;
      const wc = r.tech_score || 0;
      if (wp === 'N/A') return '';
      const phaseColors = {
        'PHASE_C_SPRING': 'var(--green)', 'PHASE_D_SOS': 'var(--green)',
        'PHASE_B_LATE': 'var(--gold)', 'PHASE_B_EARLY': 'var(--gold)',
        'UNFAVORABLE_REGIME': 'var(--red)', 'PHASE_A_OR_MARKUP': 'var(--dim)',
      };
      const phaseLabels = {
        'PHASE_C_SPRING': '🎯 PHASE C — Spring (ENTRY ZONE)', 'PHASE_D_SOS': 'o. PHASE D — Sign of Strength',
        'PHASE_B_LATE': '⏳ PHASE B Late — Watch', 'PHASE_B_EARLY': '⌛ PHASE B Early — Too Soon',
        'UNFAVORABLE_REGIME': '⛔ Unfavorable Regime', 'PHASE_A_OR_MARKUP': '⚠ Phase A or Markup',
      };
      const col = phaseColors[wp] || 'var(--dim)';
      const lbl = phaseLabels[wp] || wp;
      return '<div style="padding:10px 14px;background:var(--p2);border:1px solid var(--border);'
        +'border-left:3px solid '+col+';margin-bottom:14px;">'
        +'<div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;letter-spacing:2px;'
        +'margin-bottom:6px;color:var(--cyan);">📈 TECH MOMENTUM ANALYSIS</div>'
        +'<div style="font-family:Share Tech Mono,monospace;font-size:0.8rem;font-weight:700;color:'+col+';">'
        +lbl+'</div>'
        +(ws?'<div style="margin-top:4px;font-size:0.68rem;color:var(--green);">s ENTRY SIGNAL ACTIVE — Confidence '+wc.toFixed(0)+'%</div>':'')
        +'</div>';
    })()}

    <!-- ── Sentiment + Bulk/Block Deal Intelligence ── -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;">
      <!-- News Sentiment -->
      <div style="padding:10px 14px;background:var(--p2);border:1px solid var(--border);border-left:3px solid ${(()=>{const s=r.news_score;return s==null?'var(--dim)':s>=0.2?'var(--green)':s<=-0.2?'var(--red)':'var(--gold)'})()};">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;letter-spacing:2px;margin-bottom:6px;color:var(--cyan);">🗞 NEWS SENTIMENT (30d)</div>
        ${r.news_score==null
          ? '<div style="font-size:0.7rem;color:var(--dim);">No news data — run bulk_news_fetch.py</div>'
          : (() => {
              const s = r.news_score;
              const col = s>=0.2?'var(--green)':s<=-0.2?'var(--red)':'var(--gold)';
              const bw = Math.round((s+1)/2*100);
              return '<div style="display:flex;justify-content:space-between;margin-bottom:5px;">'
                + '<span style="font-family:Share Tech Mono,monospace;font-size:0.75rem;font-weight:700;color:'+col+';">'+(s>=0?'+':'')+s.toFixed(3)+'</span>'
                + '<span style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:'+col+';">'+r.news_label+'</span>'
                + '</div>'
                + '<div style="height:5px;background:rgba(255,255,255,0.06);border-radius:3px;margin-bottom:6px;">'
                + '<div style="width:'+bw+'%;height:100%;background:'+col+';border-radius:3px;"></div></div>'
                + (r.news_headline?'<div style="font-size:0.65rem;color:var(--dim);line-height:1.4;font-style:italic;">'+r.news_headline+'...</div>':'');
            })()
        }
      </div>
      <!-- Bulk/Block Deal Signal + Institutional Accumulation -->
      <div style="padding:10px 14px;background:var(--p2);border:1px solid var(--border);border-left:3px solid ${(()=>{const b=r.bulk_signal;return b==='STRONG_BUY'||b==='BUY'?'var(--green)':b==='STRONG_SELL'||b==='SELL'?'var(--red)':'var(--dim)'})()};">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;letter-spacing:2px;margin-bottom:6px;color:var(--cyan);">🏦 INSTITUTIONAL ACTIVITY</div>
        ${(()=>{
          const is = r.inst_acc_score || 0;
          const isCol = is>=70?'var(--green)':is>=40?'var(--gold)':'var(--dim)';
          const isLbl = is>=70?'STRONG ACCUMULATION':is>=40?'MODERATE':'NEUTRAL/NONE';
          const signals = r.inst_acc_signals || [];
          return '<div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
            +'<span style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:'+isCol+';font-weight:700;">'+isLbl+'</span>'
            +'<span style="font-family:Share Tech Mono,monospace;font-size:0.75rem;color:'+isCol+';font-weight:700;">'+is+'/100</span>'
            +'</div>'
            +'<div style="height:4px;background:rgba(255,255,255,0.06);border-radius:2px;margin-bottom:6px;">'
            +'<div style="width:'+is+'%;height:100%;background:'+isCol+';border-radius:2px;"></div></div>'
            +(signals.length?signals.slice(0,2).map(s=>'<div style="font-size:0.6rem;color:var(--dim);padding:1px 0;">- '+s+'</div>').join(''):'')
            +'<div style="margin-top:6px;font-family:Share Tech Mono,monospace;font-size:0.6rem;letter-spacing:1px;color:var(--cyan);">BULK/BLOCK DEALS (30d)</div>';
        })()}
        ${(()=>{
          const b = r.bulk_signal || 'NEUTRAL';
          const v = r.bulk_net_val_cr || 0;
          const col = b==='STRONG_BUY'||b==='BUY'?'var(--green)':b==='STRONG_SELL'||b==='SELL'?'var(--red)':'var(--gold)';
          const icon = b.includes('BUY')?'▲ INSTITUTIONAL BUYING':b.includes('SELL')?'▼ INSTITUTIONAL SELLING':'━ NEUTRAL / NO DEALS';
          const deals = r.bulk_deals_30d || [];
          return '<div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
            + '<span style="font-family:Share Tech Mono,monospace;font-size:0.72rem;font-weight:700;color:'+col+';">'+icon+'</span></div>'
            + '<div style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--t2);margin-bottom:4px;">'
            + 'Net capital flow: <b style="color:'+col+';">'+(v>=0?'+':'')+v.toFixed(1)+' Cr</b></div>'
            + (deals.length ? deals.slice(0,3).map(d=>'<div style="font-size:0.62rem;color:var(--dim);padding:1px 0;">'
              +'<span style="color:'+(d.type==='BUY'?'var(--green)':'var(--red)')+';">'+d.type+'</span> '
              +d.qty.toLocaleString()+' @ ₹'+d.price+' · '+d.kind+' · '+d.date+'</div>').join('')
              : '<div style="font-size:0.65rem;color:var(--dim);">No bulk/block deals in last 30 days</div>');
        })()}
      </div>
    </div>

    <!-- Gann + Simons Price & Date Trigger card -->
    <div style="background:rgba(0,0,0,0.25);border:1px solid var(--cyan);border-radius:3px;padding:12px 16px;margin-bottom:14px;">
      <div style="font-family:Orbitron,sans-serif;font-size:0.7rem;color:var(--cyan);letter-spacing:2px;margin-bottom:4px;">
        s GANN + SIMONS TRIGGER — PRICE OR DATE, WHICHEVER COMES FIRST
      </div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);margin-bottom:12px;">
        Entry: <span style="color:var(--gold);">${r.entry_source||'Sq9'}</span> &nbsp;·&nbsp;
        T1: <span style="color:var(--gold);">${r.t1_source||'Sq9'}</span> &nbsp;·&nbsp;
        SL: <span style="color:var(--gold);">${r.sl_source||'Sq9'}</span>
        ${r.fourier_r2?'&nbsp;·&nbsp; Simons FFT R²: <span style="color:var(--purple);">'+((r.fourier_r2||0)*100).toFixed(1)+'%</span>':''}
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:12px;">
        <!-- BUY trigger — FIX: show WAIT state when entry_source contains 'Reversal zone' -->
        <div style="background:${(r.entry_source||'').includes('Reversal')?'rgba(255,204,0,0.05)':'rgba(0,255,136,0.05)'};border:1px solid ${(r.entry_source||'').includes('Reversal')?'rgba(255,204,0,0.4)':'rgba(0,255,136,0.3)'};border-radius:3px;padding:10px 12px;">
          <div style="font-size:0.6rem;letter-spacing:1px;margin-bottom:8px;font-family:Share Tech Mono,monospace;color:${(r.entry_source||'').includes('Reversal')?'var(--gold)':'var(--green)'};">
            ${(r.entry_source||'').includes('Reversal') ? '⏳ WAIT — REVERSAL ZONE ENTRY' : '🟢 BUY TRIGGER'}
          </div>
          <div style="margin-bottom:8px;">
            <div style="font-size:0.55rem;color:var(--dim);margin-bottom:2px;">ENTRY PRICE (${r.entry_source||'Sq9 support'})</div>
            <div style="font-family:Orbitron,sans-serif;font-size:1.2rem;color:${(r.entry_source||'').includes('Reversal')?'var(--gold)':'var(--green)'};font-weight:900;">₹${(r.entry||0).toLocaleString('en-IN',{maximumFractionDigits:2})}</div>
            ${r.fourier_buy_price && r.fourier_buy_price < r.price ?
              '<div style="font-size:0.62rem;color:var(--purple);margin-top:2px;">📊 Simons FFT trough: ₹'+r.fourier_buy_price.toLocaleString('en-IN',{maximumFractionDigits:2})+'</div>' : ''}
          </div>
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
            <div style="font-size:0.72rem;color:var(--dim);">OR WAIT UNTIL</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.85rem;color:var(--green);font-weight:700;">${(r.buy_date||'').replace(/-/g,'/')}</div>
          </div>
          <div style="font-size:0.62rem;color:var(--dim);">🕐 ${r.buy_time||'09:20 IST'}</div>
          <div style="font-size:0.67rem;color:var(--t2);margin-top:5px;border-top:1px solid rgba(0,255,136,0.15);padding-top:5px;">${r.buy_condition||''}</div>
          <div style="font-size:0.65rem;color:var(--red);margin-top:4px;">🛡 SL: ₹${(r.stop_loss||0).toLocaleString('en-IN',{maximumFractionDigits:2})} <span style="color:var(--dim);">(${r.sl_source||'Sq9'})</span></div>
        </div>
        <!-- SELL trigger -->
        <div style="background:rgba(255,68,68,0.05);border:1px solid rgba(255,68,68,0.3);border-radius:3px;padding:10px 12px;">
          <div style="font-size:0.6rem;color:var(--red);letter-spacing:1px;margin-bottom:8px;font-family:Share Tech Mono,monospace;">🔴 SELL TRIGGER</div>
          <div style="margin-bottom:8px;">
            <div style="font-size:0.55rem;color:var(--dim);margin-bottom:2px;">T1 TARGET (${r.t1_source||'Sq9 resistance'})</div>
            <div style="font-family:Orbitron,sans-serif;font-size:1.2rem;color:var(--gold);font-weight:900;">₹${(r.target1||0).toLocaleString('en-IN',{maximumFractionDigits:2})}</div>
            ${r.fourier_sell_price && r.fourier_sell_price > r.price ?
              '<div style="font-size:0.62rem;color:var(--purple);margin-top:2px;">📊 Simons FFT peak: ₹'+r.fourier_sell_price.toLocaleString('en-IN',{maximumFractionDigits:2})+'</div>' : ''}
          </div>
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
            <div style="font-size:0.72rem;color:var(--dim);">OR EXIT ON</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.85rem;color:var(--red);font-weight:700;">${(r.sell_date||'').replace(/-/g,'/')}</div>
          </div>
          <div style="font-size:0.62rem;color:var(--dim);">🕐 ${r.sell_time||'15:10 IST'}</div>
          <div style="font-size:0.67rem;color:var(--t2);margin-top:5px;border-top:1px solid rgba(255,68,68,0.15);padding-top:5px;">${r.sell_condition||''}</div>
          <div style="font-size:0.65rem;color:var(--gold);margin-top:4px;">T2: ₹${(r.target2||0).toLocaleString('en-IN',{maximumFractionDigits:2})} — ${r.sell_condition2||''}</div>
        </div>
      </div>
      <!-- Reversal dates table -->
      ${(r.reversal_dates||[]).length>0?`
      <div style="font-size:0.6rem;color:var(--gold);letter-spacing:1px;font-family:Share Tech Mono,monospace;margin-bottom:6px;">📅 HIGH-CONFLUENCE REVERSAL TIMES IN SESSION</div>
      <div style="display:flex;flex-wrap:wrap;gap:6px;">
        ${(r.reversal_dates||[]).map(rd=>{
          const isStr = typeof rd === 'string';
          const label = isStr ? rd : (rd.date || '').replace(/-/g,'/');
          const bias  = isStr ? 'REVERSAL' : (rd.bias || 'REVERSAL');
          const bc    = bias==='BULLISH'?'rgba(0,255,136,0.1)':bias==='BEARISH'?'rgba(255,68,68,0.1)':'rgba(255,204,0,0.1)';
          const tc    = bias==='BULLISH'?'var(--green)':bias==='BEARISH'?'var(--red)':'var(--gold)';
          const tags  = isStr ? '\u23f0 ' : ((rd.cycle?'\u23f0 CYCLE ':'')+(rd.station?'\u2299 STATION ':''));
          return '<div style="background:'+bc+';border:1px solid '+tc+';border-radius:2px;padding:4px 8px;font-family:\'Share Tech Mono\',monospace;font-size:0.68rem;">'
            +'<span style="color:'+tc+';font-weight:700;">'+label+'</span>'
            +'<span style="color:var(--dim);margin-left:6px;">'+tags+'</span>'
            +'<span style="color:'+tc+';margin-left:4px;">'+bias+'</span>'
            +'</div>';
        }).join('')}
      </div>`:''}
    </div>

    <!-- Charts row — click any chart to expand -->
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:4px;">
      <div>
        <div style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;font-family:Share Tech Mono,monospace;">
          PRICE PROJECTION <span style="color:var(--cyan);cursor:pointer;" onclick="expandChart('adv-proj-${idx}','adv-proj-modal-${idx}')">⛶ EXPAND</span>
        </div>
        <div id="adv-proj-modal-${idx}" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:9999;cursor:pointer;align-items:center;justify-content:center;" onclick="this.style.display='none'">
          <canvas id="adv-proj-big-${idx}" style="max-width:90vw;max-height:85vh;border:1px solid var(--cyan);"></canvas>
          <div style="position:absolute;top:20px;right:30px;color:var(--cyan);font-size:1.5rem;cursor:pointer;">✕</div>
        </div>
        <div style="background:var(--p2);border:1px solid var(--border);height:140px;position:relative;overflow:hidden;cursor:pointer;" onclick="expandChart('adv-proj-${idx}','adv-proj-modal-${idx}')">
          <canvas id="adv-proj-${idx}" style="width:100%;height:100%;"></canvas>
        </div>
      </div>
      <div>
        <div style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;font-family:Share Tech Mono,monospace;">
          SUPPORT / RESISTANCE <span style="color:var(--cyan);cursor:pointer;" onclick="expandChart('adv-sr-${idx}','adv-sr-modal-${idx}')">⛶ EXPAND</span>
        </div>
        <div id="adv-sr-modal-${idx}" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:9999;cursor:pointer;align-items:center;justify-content:center;" onclick="this.style.display='none'">
          <canvas id="adv-sr-big-${idx}" style="max-width:90vw;max-height:85vh;border:1px solid var(--cyan);"></canvas>
          <div style="position:absolute;top:20px;right:30px;color:var(--cyan);font-size:1.5rem;cursor:pointer;">✕</div>
        </div>
        <div style="background:var(--p2);border:1px solid var(--border);height:140px;position:relative;overflow:hidden;cursor:pointer;" onclick="expandChart('adv-sr-${idx}','adv-sr-modal-${idx}')">
          <canvas id="adv-sr-${idx}" style="width:100%;height:100%;"></canvas>
        </div>
      </div>
      <div>
        <div style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;font-family:Share Tech Mono,monospace;">
          NATAL ASPECT STRENGTH <span style="color:var(--cyan);cursor:pointer;" onclick="expandChart('adv-planet-${idx}','adv-planet-modal-${idx}')">⛶ EXPAND</span>
        </div>
        <div id="adv-planet-modal-${idx}" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:9999;cursor:pointer;align-items:center;justify-content:center;" onclick="this.style.display='none'">
          <canvas id="adv-planet-big-${idx}" style="max-width:90vw;max-height:85vh;border:1px solid var(--cyan);"></canvas>
          <div style="position:absolute;top:20px;right:30px;color:var(--cyan);font-size:1.5rem;cursor:pointer;">✕</div>
        </div>
        <div style="background:var(--p2);border:1px solid var(--border);height:140px;position:relative;overflow:hidden;cursor:pointer;" onclick="expandChart('adv-planet-${idx}','adv-planet-modal-${idx}')">
          <canvas id="adv-planet-${idx}" style="width:100%;height:100%;"></canvas>
        </div>
      </div>
    </div>
  </div>`;
  return el;
}

function scoreBar(label, val, max, color) {
  const pct = Math.round(val/max*100);
  return `<div style="background:var(--p2);border:1px solid var(--border);padding:6px 8px;border-radius:2px;">
    <div style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">${label}</div>
    <div style="background:rgba(0,0,0,0.3);height:4px;border-radius:2px;margin-bottom:3px;">
      <div style="width:${pct}%;height:100%;background:${color};border-radius:2px;transition:width 0.8s;"></div>
    </div>
    <div style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:${color};">${val}/${max}</div>
  </div>`;
}

// ── Price projection chart ────────────────────────────────────────────
function drawPriceProjection(cid, r) {
  const canvas = document.getElementById(cid);
  if (!canvas) return;
  const W = canvas.parentElement.clientWidth||300, H = 140;
  canvas.width=W; canvas.height=H;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle='#071219'; ctx.fillRect(0,0,W,H);

  const hist = r.price_history || [];
  const closes = hist.map(h=>h.close);
  if (closes.length < 2) {
    ctx.fillStyle='rgba(0,212,255,0.3)'; ctx.font='9px Share Tech Mono'; ctx.textAlign='center';
    ctx.fillText('No price history', W/2, H/2); return;
  }

  // Add projection points: entry, t1, t2
  const projDates = hist.map(h=>h.date);
  const allPrices = [...closes, r.entry, r.target1, r.target2];
  const minP = Math.min(...allPrices)*0.995;
  const maxP = Math.max(...allPrices)*1.005;
  const PAD  = {t:10,r:10,b:20,l:45};
  const cW   = W-PAD.l-PAD.r, cH = H-PAD.t-PAD.b;
  const xS   = i => PAD.l + (i/(closes.length+3))*cW;
  const yS   = v => PAD.t + cH - ((v-minP)/(maxP-minP))*cH;

  // Grid
  ctx.strokeStyle='rgba(255,255,255,0.04)'; ctx.lineWidth=0.5;
  for(let i=0;i<=4;i++){
    const y=PAD.t+(i/4)*cH;
    ctx.beginPath(); ctx.moveTo(PAD.l,y); ctx.lineTo(PAD.l+cW,y); ctx.stroke();
    const v=maxP-(i/4)*(maxP-minP);
    ctx.fillStyle='#3a5a70'; ctx.font='7px Share Tech Mono'; ctx.textAlign='right';
    ctx.fillText('₹'+(v/1000).toFixed(1)+'k',PAD.l-2,y+3);
  }

  // Price history line
  ctx.beginPath(); ctx.strokeStyle='var(--cyan)'; ctx.lineWidth=1.2;
  closes.forEach((v,i)=>{ i===0?ctx.moveTo(xS(i),yS(v)):ctx.lineTo(xS(i),yS(v)); });
  ctx.stroke();

  // Entry line
  const ei = closes.length;
  ctx.setLineDash([3,3]);
  ctx.strokeStyle='var(--gold)'; ctx.lineWidth=1;
  ctx.beginPath(); ctx.moveTo(xS(ei-1),yS(r.entry)); ctx.lineTo(xS(ei+0.5),yS(r.entry)); ctx.stroke();
  // SL line
  ctx.strokeStyle='var(--red)';
  ctx.beginPath(); ctx.moveTo(xS(ei-1),yS(r.stop_loss)); ctx.lineTo(xS(ei+0.5),yS(r.stop_loss)); ctx.stroke();
  // Target lines
  ctx.strokeStyle='var(--green)';
  ctx.beginPath(); ctx.moveTo(xS(ei),yS(r.target1)); ctx.lineTo(xS(ei+2),yS(r.target1)); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(xS(ei),yS(r.target2)); ctx.lineTo(xS(ei+2),yS(r.target2)); ctx.stroke();
  ctx.setLineDash([]);

  // Labels
  ctx.font='7px Share Tech Mono'; ctx.textAlign='left';
  ctx.fillStyle='var(--gold)';  ctx.fillText('ENTRY',  xS(ei)+2, yS(r.entry)-2);
  ctx.fillStyle='var(--red)';   ctx.fillText('SL',     xS(ei)+2, yS(r.stop_loss)+8);
  ctx.fillStyle='var(--green)'; ctx.fillText('T1',     xS(ei+1), yS(r.target1)-2);
  ctx.fillStyle='#8fea80';      ctx.fillText('T2',     xS(ei+1), yS(r.target2)-2);

  // Current price dot
  const lastI = closes.length-1;
  ctx.beginPath(); ctx.arc(xS(lastI),yS(closes[lastI]),3,0,Math.PI*2);
  ctx.fillStyle='var(--cyan)'; ctx.fill();
}

// ── S/R chart ─────────────────────────────────────────────────────────
function drawSRChart(cid, r) {
  const canvas = document.getElementById(cid);
  if (!canvas) return;
  const W=canvas.parentElement.clientWidth||300, H=140;
  canvas.width=W; canvas.height=H;
  const ctx=canvas.getContext('2d');
  ctx.fillStyle='#071219'; ctx.fillRect(0,0,W,H);

  const price  = r.price;
  const sup    = r.supports||[];
  const res    = r.resistances||[];
  const levels = [...sup.map(s=>({v:s,t:'S'})), {v:price,t:'P'},
                  ...res.map(s=>({v:s,t:'R'})),
                  {v:r.stop_loss,t:'SL'},{v:r.target1,t:'T1'},{v:r.target2,t:'T2'}]
    .filter(l=>l.v>0).sort((a,b)=>a.v-b.v);
  if(levels.length<2){ctx.fillStyle='rgba(0,212,255,0.3)';ctx.font='9px Share Tech Mono';ctx.textAlign='center';ctx.fillText('No S/R data',W/2,H/2);return;}

  const vals = levels.map(l=>l.v);
  const minV = Math.min(...vals)*0.995, maxV=Math.max(...vals)*1.005;
  const PAD={t:10,r:50,b:10,l:45};
  const cH=H-PAD.t-PAD.b;
  const yS=v=>PAD.t+cH-((v-minV)/(maxV-minV))*cH;
  const COLORS={S:'var(--green)',R:'var(--red)',P:'var(--cyan)',SL:'rgba(255,68,68,0.6)',T1:'rgba(0,255,136,0.8)',T2:'rgba(0,255,136,0.5)'};

  levels.forEach(l=>{
    const y=yS(l.v);
    ctx.strokeStyle=COLORS[l.t]||'var(--dim)'; ctx.lineWidth=l.t==='P'?1.5:1;
    ctx.setLineDash(l.t==='P'?[]:[3,3]);
    ctx.beginPath(); ctx.moveTo(PAD.l,y); ctx.lineTo(W-PAD.r,y); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle=COLORS[l.t]||'var(--dim)'; ctx.font='7px Share Tech Mono';
    ctx.textAlign='right';
    ctx.fillText('₹'+(l.v/1000).toFixed(1)+'k',PAD.l-2,y+3);
    ctx.textAlign='left';
    ctx.fillText(l.t,W-PAD.r+2,y+3);
  });
  // Price area fill between SL and T1
  const slY=yS(r.stop_loss), t1Y=yS(r.target1), pY=yS(price);
  ctx.fillStyle='rgba(255,68,68,0.06)';
  ctx.fillRect(PAD.l,pY,W-PAD.l-PAD.r,slY-pY);
  ctx.fillStyle='rgba(0,255,136,0.06)';
  ctx.fillRect(PAD.l,t1Y,W-PAD.l-PAD.r,pY-t1Y);
}

// ── Natal aspect strength bar chart ──────────────────────────────────
function drawPlanetChart(cid, r) {
  const canvas=document.getElementById(cid);
  if(!canvas) return;
  const W=canvas.parentElement.clientWidth||300, H=140;
  canvas.width=W; canvas.height=H;
  const ctx=canvas.getContext('2d');
  ctx.fillStyle='#071219'; ctx.fillRect(0,0,W,H);

  const aspects=(r.natal_aspects||[]).slice(0,6);
  if(!aspects.length){
    ctx.fillStyle='rgba(204,136,255,0.3)';ctx.font='9px Share Tech Mono';ctx.textAlign='center';
    ctx.fillText('No natal aspects',W/2,H/2); return;
  }
  const PAD={t:10,r:10,b:30,l:10};
  const cW=W-PAD.l-PAD.r, cH=H-PAD.t-PAD.b;
  const barW=cW/aspects.length*0.7, gap=cW/aspects.length;
  const maxOrb=Math.max(...aspects.map(a=>a.orb||1),1);

  aspects.forEach((a,i)=>{
    const strength = Math.max(0.1, 1-(a.orb||0)/6);
    const barH = strength*cH;
    const x=PAD.l+i*gap+(gap-barW)/2;
    const y=PAD.t+cH-barH;
    const col=a.nature==='BULLISH'?'rgba(0,255,136,0.7)':a.nature==='BEARISH'?'rgba(255,68,68,0.7)':'rgba(255,204,0,0.7)';
    ctx.fillStyle=col; ctx.fillRect(x,y,barW,barH);
    ctx.fillStyle='rgba(255,255,255,0.5)'; ctx.font='6px Share Tech Mono'; ctx.textAlign='center';
    ctx.fillText((a.orb||0).toFixed(1)+'°',x+barW/2,y-2);
    ctx.fillStyle='rgba(255,255,255,0.4)'; ctx.font='6px Share Tech Mono';
    const lbl=a.transit_planet ? a.transit_planet.slice(0,3)+'→'+a.natal_planet.slice(0,3) : '';
    ctx.fillText(lbl,x+barW/2,H-PAD.b+10);
  });
  ctx.fillStyle='rgba(204,136,255,0.5)'; ctx.font='7px Share Tech Mono'; ctx.textAlign='left';
  ctx.fillText('orb strength (higher=tighter)',PAD.l+2,PAD.t+8);
}

// ── Portfolio pie chart ───────────────────────────────────────────────
function expandChart(srcId, modalId) {
  const modal  = document.getElementById(modalId);
  const srcCvs = document.getElementById(srcId);
  if (!modal || !srcCvs) return;

  // Find big canvas id — handle both adv- and single- prefixes
  const bigId = srcId
    .replace('adv-proj-','adv-proj-big-')
    .replace('adv-sr-','adv-sr-big-')
    .replace('adv-planet-','adv-planet-big-')
    .replace('single-proj-','single-proj-big-')
    .replace('single-sr-','single-sr-big-')
    .replace('single-planet-','single-planet-big-');
  const bigCvs = document.getElementById(bigId);

  modal.style.display = 'flex';

  if (bigCvs) {
    bigCvs.width  = Math.min(window.innerWidth * 0.88, 1200);
    bigCvs.height = Math.min(window.innerHeight * 0.80, 700);
    bigCvs.style.width  = bigCvs.width  + 'px';
    bigCvs.style.height = bigCvs.height + 'px';

    // Find rec data — single stock mode stores in _singleRec, portfolio in _advRecs
    const idxMatch = srcId.match(/(\d+)$/);
    const idx = idxMatch ? parseInt(idxMatch[1]) : 0;
    const r = srcId.startsWith('single-')
      ? (window._singleRec || null)
      : (window._advRecs && window._advRecs[idx]);
    if (!r) return;

    if (srcId.includes('proj'))   drawPriceProjectionBig(bigId, r, bigCvs.width, bigCvs.height);
    else if (srcId.includes('sr')) drawSRChartBig(bigId, r, bigCvs.width, bigCvs.height);
    else                           drawPlanetChartBig(bigId, r, bigCvs.width, bigCvs.height);
  }
}

function drawPriceProjectionBig(cid, r, W, H) {
  const canvas = document.getElementById(cid);
  if (!canvas) return;
  canvas.width=W; canvas.height=H;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle='#071219'; ctx.fillRect(0,0,W,H);

  const hist   = r.price_history || [];
  const closes = hist.map(h=>h.close);
  if (closes.length < 2) { ctx.fillStyle='var(--cyan)'; ctx.font='14px Share Tech Mono'; ctx.textAlign='center'; ctx.fillText('No price history',W/2,H/2); return; }

  const allP = [...closes, r.entry, r.target1, r.target2, r.stop_loss];
  const minP = Math.min(...allP)*0.993, maxP=Math.max(...allP)*1.007;
  const PAD  = {t:30,r:80,b:50,l:80};
  const cW=W-PAD.l-PAD.r, cH=H-PAD.t-PAD.b;
  const xS=i=>PAD.l+(i/(closes.length+3))*cW;
  const yS=v=>PAD.t+cH-((v-minP)/(maxP-minP))*cH;

  // Grid
  for(let i=0;i<=8;i++){
    const y=PAD.t+(i/8)*cH;
    ctx.strokeStyle='rgba(255,255,255,0.05)'; ctx.lineWidth=0.5; ctx.setLineDash([4,4]);
    ctx.beginPath(); ctx.moveTo(PAD.l,y); ctx.lineTo(PAD.l+cW,y); ctx.stroke();
    const v=maxP-(i/8)*(maxP-minP);
    ctx.setLineDash([]); ctx.fillStyle='#4a7a9b'; ctx.font='10px Share Tech Mono'; ctx.textAlign='right';
    ctx.fillText('₹'+(v>=1000?(v/1000).toFixed(1)+'k':v.toFixed(0)),PAD.l-6,y+4);
  }

  // Date labels
  const step = Math.max(1, Math.floor(closes.length/10));
  hist.forEach((h,i)=>{ if(i%step===0){ ctx.fillStyle='#3a5a70'; ctx.font='9px Share Tech Mono'; ctx.textAlign='center'; ctx.fillText(h.date.slice(5),xS(i),H-PAD.b+14); }});

  // Price line
  ctx.beginPath(); ctx.strokeStyle='#00d4ff'; ctx.lineWidth=2;
  closes.forEach((v,i)=>i===0?ctx.moveTo(xS(i),yS(v)):ctx.lineTo(xS(i),yS(v)));
  ctx.stroke();

  // Fill under line
  ctx.beginPath(); ctx.moveTo(xS(0),yS(closes[0]));
  closes.forEach((v,i)=>ctx.lineTo(xS(i),yS(v)));
  ctx.lineTo(xS(closes.length-1),H-PAD.b); ctx.lineTo(PAD.l,H-PAD.b);
  ctx.fillStyle='rgba(0,212,255,0.06)'; ctx.fill();

  // Entry/SL/Target lines
  const ei=closes.length;
  const lines=[
    {v:r.entry,     label:'ENTRY',  color:'#ffcc00'},
    {v:r.stop_loss, label:'SL',     color:'#ff4444'},
    {v:r.target1,   label:'T1',     color:'#00ff88'},
    {v:r.target2,   label:'T2',     color:'#8fea80'},
  ];
  lines.forEach(l=>{
    ctx.setLineDash([6,4]); ctx.strokeStyle=l.color; ctx.lineWidth=1.5;
    ctx.beginPath(); ctx.moveTo(xS(ei-2),yS(l.v)); ctx.lineTo(xS(ei+2),yS(l.v)); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle=l.color; ctx.font='bold 11px Share Tech Mono'; ctx.textAlign='left';
    ctx.fillText(l.label+' ₹'+l.v.toLocaleString(), xS(ei+2)+4, yS(l.v)+4);
  });

  // Current price dot
  ctx.beginPath(); ctx.arc(xS(closes.length-1),yS(closes[closes.length-1]),5,0,Math.PI*2);
  ctx.fillStyle='#00d4ff'; ctx.fill();

  // Title
  ctx.fillStyle='rgba(0,212,255,0.7)'; ctx.font='bold 12px Share Tech Mono'; ctx.textAlign='left';
  ctx.fillText(`${r.symbol} — PRICE PROJECTION  (click anywhere to close)`, PAD.l, 20);
}

function drawSRChartBig(cid, r, W, H) {
  const canvas=document.getElementById(cid); if(!canvas) return;
  canvas.width=W; canvas.height=H;
  const ctx=canvas.getContext('2d');
  ctx.fillStyle='#071219'; ctx.fillRect(0,0,W,H);

  const sup=r.supports||[], res=r.resistances||[];
  const levels=[...sup.map(s=>({v:s,t:'S'})),{v:r.price,t:'P'},{v:r.stop_loss,t:'SL'},
                {v:r.target1,t:'T1'},{v:r.target2,t:'T2'},...res.map(s=>({v:s,t:'R'}))]
    .filter(l=>l.v>0).sort((a,b)=>a.v-b.v);
  if(!levels.length) return;

  const vals=levels.map(l=>l.v);
  const minV=Math.min(...vals)*0.99, maxV=Math.max(...vals)*1.01;
  const PAD={t:30,r:160,b:30,l:80};
  const cH=H-PAD.t-PAD.b;
  const yS=v=>PAD.t+cH-((v-minV)/(maxV-minV))*cH;
  const COLORS={S:'#00ff88',R:'#ff4444',P:'#00d4ff',SL:'rgba(255,68,68,0.7)',T1:'rgba(0,255,136,0.9)',T2:'rgba(0,255,136,0.6)'};

  // Reward/risk zones
  ctx.fillStyle='rgba(255,68,68,0.06)';
  ctx.fillRect(PAD.l,yS(r.price),W-PAD.l-PAD.r,yS(r.stop_loss)-yS(r.price));
  ctx.fillStyle='rgba(0,255,136,0.06)';
  ctx.fillRect(PAD.l,yS(r.target1),W-PAD.l-PAD.r,yS(r.price)-yS(r.target1));

  levels.forEach(l=>{
    const y=yS(l.v);
    ctx.strokeStyle=COLORS[l.t]||'#4a7a9b'; ctx.lineWidth=l.t==='P'?2:1.5;
    ctx.setLineDash(l.t==='P'?[]:[6,4]);
    ctx.beginPath(); ctx.moveTo(PAD.l,y); ctx.lineTo(W-PAD.r,y); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle=COLORS[l.t]||'#4a7a9b'; ctx.font='11px Share Tech Mono'; ctx.textAlign='right';
    ctx.fillText('₹'+l.v.toLocaleString(),PAD.l-6,y+4);
    ctx.textAlign='left';
    ctx.fillText(l.t,W-PAD.r+6,y+4);
  });

  ctx.fillStyle='rgba(0,212,255,0.7)'; ctx.font='bold 12px Share Tech Mono'; ctx.textAlign='left';
  ctx.fillText(`${r.symbol} — SUPPORT / RESISTANCE  (click anywhere to close)`, PAD.l, 20);
}

function drawPlanetChartBig(cid, r, W, H) {
  const canvas=document.getElementById(cid); if(!canvas) return;
  canvas.width=W; canvas.height=H;
  const ctx=canvas.getContext('2d');
  ctx.fillStyle='#071219'; ctx.fillRect(0,0,W,H);

  const aspects=(r.natal_aspects||[]).slice(0,10);
  if(!aspects.length){ctx.fillStyle='#cc88ff';ctx.font='14px Share Tech Mono';ctx.textAlign='center';ctx.fillText('No natal aspects',W/2,H/2);return;}

  const PAD={t:40,r:20,b:60,l:20};
  const cW=W-PAD.l-PAD.r, cH=H-PAD.t-PAD.b;
  const bW=cW/aspects.length*0.6, gap=cW/aspects.length;

  aspects.forEach((a,i)=>{
    const str=Math.max(0.05, 1-(a.orb||0)/6);
    const bH=str*cH;
    const x=PAD.l+i*gap+(gap-bW)/2;
    const y=PAD.t+cH-bH;
    const col=a.nature==='BULLISH'?'rgba(0,255,136,0.8)':a.nature==='BEARISH'?'rgba(255,68,68,0.8)':'rgba(255,204,0,0.8)';
    ctx.fillStyle=col; ctx.fillRect(x,y,bW,bH);
    ctx.fillStyle='rgba(255,255,255,0.6)'; ctx.font='11px Share Tech Mono'; ctx.textAlign='center';
    ctx.fillText((a.orb||0).toFixed(2)+'°',x+bW/2,y-8);
    const lbl=(a.transit_planet||'').slice(0,3)+'→'+(a.natal_planet||'').slice(0,3);
    ctx.fillStyle='rgba(255,255,255,0.5)'; ctx.font='10px Share Tech Mono';
    ctx.fillText(lbl,x+bW/2,H-PAD.b+16);
    const nat=a.nature==='BULLISH'?'var(--green)':a.nature==='BEARISH'?'red':'gold';
    ctx.fillStyle=col; ctx.font='bold 9px Share Tech Mono';
    ctx.fillText(a.nature||'',x+bW/2,H-PAD.b+30);
  });

  ctx.fillStyle='rgba(204,136,255,0.8)'; ctx.font='bold 12px Share Tech Mono'; ctx.textAlign='left';
  ctx.fillText(`${r.symbol} — NATAL ASPECT STRENGTH  (click anywhere to close)`, PAD.l, 24);
}

// ════════════════════════════════════════════════════════════
// BACKTEST ENGINE
// ════════════════════════════════════════════════════════════

let _btData = null;

// Set default end date to today
(function() {
  const el = document.getElementById('bt-end');
  if (el) el.value = new Date().toISOString().slice(0,10);
})();


// ── v4.0 ML Engine status ──────────────────────────────────────────────────
async function loadMLStatus() {
  try {
    const d = await api('ml_status');
    const el = document.getElementById('ml-status-text');
    if (!el) return;
    if (d.status && d.status.trained) {
      const s = d.status;
      el.innerHTML = `<span style="color:var(--green);">✓ Trained</span> &nbsp;|&nbsp; `
        + `v: ${s.version} &nbsp;|&nbsp; `
        + `${(s.n_samples||0).toLocaleString()} samples &nbsp;|&nbsp; `
        + `Direction acc: <span style="color:var(--cyan);">${s.dir_accuracy}%</span> &nbsp;|&nbsp; `
        + `Timing MAE: ${s.timing_mae}d`;
    } else {
      el.innerHTML = '<span style="color:var(--gold);">⚠ Not trained yet</span> — click TRAIN MODEL to improve reversal accuracy';
    }
  } catch(e) {
    const el = document.getElementById('ml-status-text');
    if (el) el.textContent = 'ML status unavailable';
  }
}

async function trainMLModel() {
  const btn = document.getElementById('ml-train-btn');
  if (btn) { btn.textContent = '⏳ Training...'; btn.disabled = true; }
  try {
    const d = await api('ml_train', { years: 3, forward_days: 10 });
    if (btn) { btn.textContent = '✓ Training started'; }
    setTimeout(() => {
      if (btn) { btn.textContent = 's TRAIN MODEL'; btn.disabled = false; }
      loadMLStatus();
    }, 5000);
  } catch(e) {
    if (btn) { btn.textContent = '✗ Error'; btn.disabled = false; }
  }
}

// Load ML status on page init
setTimeout(() => { try { loadMLStatus(); } catch(e) {} }, 800);

// ── V4.0 Personalized Portfolio Planner rendering & execution ──
function updateRatioLabel(v) {
  const labelVal = document.getElementById('adv-ratio-val');
  const labelValQ = document.getElementById('adv-ratio-val-q');
  if (labelVal) labelVal.textContent = v;
  if (labelValQ) labelValQ.textContent = 100 - v;
}

function renderAdvisorPlanner(d) {
  const container = document.getElementById('adv-planner-results');
  if (!container) return;
  container.style.display = 'block';

  if (!d.ok || !d.plan || d.plan.length === 0) {
    container.innerHTML = `<div class="card" style="padding:20px;text-align:center;">
      <div style="font-size:1.8rem;color:var(--orange);margin-bottom:8px;">⚠️ NO PLAN GENERATED</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.75rem;color:var(--dim);">
        All candidates filtered by active Risk Gates (max positions limit or correlation limits exceeded).
      </div>
    </div>`;
    return;
  }

  const totalDeployed = d.total_deployed_capital || 0;
  const available = d.available_capital || 0;
  
  let statsHtml = `
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px;">
      <div class="stat" style="background:var(--p2);border:1px solid var(--border);border-radius:4px;padding:12px;text-align:center;">
        <span class="val" style="color:var(--green);font-size:1.25rem;font-family:Share Tech Mono,monospace;display:block;">Rs. ${totalDeployed.toLocaleString('en-IN', {maximumFractionDigits:2})}</span>
        <span class="lbl" style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;text-transform:uppercase;margin-top:4px;display:block;">DEPLOYED CAPITAL</span>
      </div>
      <div class="stat" style="background:var(--p2);border:1px solid var(--border);border-radius:4px;padding:12px;text-align:center;">
        <span class="val" style="color:var(--cyan);font-size:1.25rem;font-family:Share Tech Mono,monospace;display:block;">Rs. ${available.toLocaleString('en-IN', {maximumFractionDigits:2})}</span>
        <span class="lbl" style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;text-transform:uppercase;margin-top:4px;display:block;">AVAILABLE HEADROOM</span>
      </div>
      <div class="stat" style="background:var(--p2);border:1px solid var(--border);border-radius:4px;padding:12px;text-align:center;">
        <span class="val" style="color:var(--gold);font-size:1.25rem;font-family:Share Tech Mono,monospace;display:block;">${d.plan.length}</span>
        <span class="lbl" style="font-size:0.6rem;color:var(--dim);letter-spacing:1px;text-transform:uppercase;margin-top:4px;display:block;">SELECTED CANDIDATES</span>
      </div>
    </div>
  `;

  let validationStrip = `
    <div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:rgba(8,153,129,0.06);border:1px solid rgba(8,153,129,0.2);border-radius:4px;margin-bottom:16px;">
      <span style="color:var(--green);font-family:Share Tech Mono,monospace;font-size:0.8rem;font-weight:bold;">✓ RISK VALIDATION PASSED</span>
      <span style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);line-height:1.5;">
        All recommendations strictly audited against active limits: Max Position Count, Sector Cap Limits, Individual Weights, and Cross-Correlation Coefficients.
      </span>
    </div>
  `;

  let tableRows = '';
  d.plan.forEach((item, index) => {
    tableRows += `
      <tr style="border-bottom:1px solid var(--border);transition:background 0.2s;" onmouseover="this.style.background='var(--p2)'" onmouseout="this.style.background='transparent'">
        <td style="padding:10px 8px;font-family:Share Tech Mono,monospace;font-size:0.75rem;color:var(--cyan);font-weight:bold;cursor:pointer;" onclick="nav('chart');setTimeout(()=>loadChartSymbol('${item.symbol}'),100)">
          ${item.symbol}
          <span style="display:block;font-family:Inter,sans-serif;font-size:0.6rem;color:var(--dim);font-weight:normal;margin-top:2px;">${item.name}</span>
        </td>
        <td style="padding:10px 8px;font-family:Inter,sans-serif;font-size:0.7rem;color:var(--text);">${item.sector}</td>
        <td style="padding:10px 8px;text-align:center;">
          <span style="display:inline-block;padding:2px 6px;border-radius:3px;background:rgba(0,255,136,0.08);border:1px solid var(--green);font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--green);">
            ${item.astro_quant_score.toFixed(0)}
          </span>
        </td>
        <td style="padding:10px 8px;text-align:center;font-family:Share Tech Mono,monospace;font-size:0.8rem;color:var(--gold);font-weight:bold;">
          ${item.shares}
        </td>
        <td style="padding:10px 8px;text-align:right;font-family:Share Tech Mono,monospace;font-size:0.75rem;color:var(--text);">
          Rs. ${item.entry.toLocaleString('en-IN', {minimumFractionDigits:2})}
        </td>
        <td style="padding:10px 8px;text-align:right;font-family:Share Tech Mono,monospace;font-size:0.75rem;color:var(--red);">
          Rs. ${item.stop_loss.toLocaleString('en-IN', {minimumFractionDigits:2})}
        </td>
        <td style="padding:10px 8px;text-align:right;font-family:Share Tech Mono,monospace;font-size:0.75rem;color:var(--green);">
          Rs. ${item.target1.toLocaleString('en-IN', {minimumFractionDigits:2})}
          <span style="display:block;font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);margin-top:2px;">T2: Rs. ${item.target2.toLocaleString('en-IN', {minimumFractionDigits:2})}</span>
        </td>
        <td style="padding:10px 8px;text-align:right;font-family:Share Tech Mono,monospace;font-size:0.75rem;color:var(--orange);">
          Rs. ${item.expected_risk_val.toLocaleString('en-IN', {maximumFractionDigits:2})}
        </td>
      </tr>
    `;
  });

  let tableHtml = `
    <div class="card">
      <div class="card-title" style="color:var(--cyan);display:flex;justify-content:space-between;align-items:center;">
        <span>📋 PORTFOLIO PLANNER RECOMMENDATIONS</span>
        <button onclick="deployPlannerPlan()" style="padding:4px 12px;background:var(--cyan);color:var(--white);border:none;border-radius:3px;font-family:Share Tech Mono,monospace;font-size:0.65rem;font-weight:bold;cursor:pointer;letter-spacing:1px;box-shadow:0 0 10px rgba(0,212,255,0.25);">DEPLOY PLAN</button>
      </div>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;text-align:left;">
          <thead>
            <tr style="border-bottom:2px solid var(--border);color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.65rem;letter-spacing:1px;text-transform:uppercase;">
              <th style="padding:8px;font-weight:normal;">SYMBOL</th>
              <th style="padding:8px;font-weight:normal;">SECTOR</th>
              <th style="padding:8px;font-weight:normal;text-align:center;">SCORE</th>
              <th style="padding:8px;font-weight:normal;text-align:center;">SHARES</th>
              <th style="padding:8px;font-weight:normal;text-align:right;">ENTRY</th>
              <th style="padding:8px;font-weight:normal;text-align:right;">STOP LOSS</th>
              <th style="padding:8px;font-weight:normal;text-align:right;">TARGETS</th>
              <th style="padding:8px;font-weight:normal;text-align:right;">CAPITAL RISK</th>
            </tr>
          </thead>
          <tbody>
            ${tableRows}
          </tbody>
        </table>
      </div>
    </div>
  `;

  container.innerHTML = statsHtml + validationStrip + tableHtml;
}

async function deployPlannerPlan() {
  const data = window.currentPlannerData;
  if (!data || !data.plan || data.plan.length === 0) return;
  
  if (!confirm('Do you want to deploy these planned recommendations to your portfolio?')) return;
  
  let successCount = 0;
  for (const item of data.plan) {
    try {
      await api('portfolio_add', {
        symbol: item.symbol,
        entry_price: item.entry,
        shares: item.shares,
        stop_loss: item.stop_loss,
        target1: item.target1,
        target2: item.target2,
        inv_type: document.getElementById('adv-type').value
      });
      successCount++;
    } catch (err) {}
  }
  
  alert('Successfully deployed ' + successCount + ' out of ' + data.plan.length + ' positions!');
  nav('trading');
  setTimeout(() => { if (typeof loadDematPortfolio === 'function') loadDematPortfolio(); }, 200);
}
"""