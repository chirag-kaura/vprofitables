"""
page_tools.py — Tools — Square of Nine, Time Cycles, Confluence, Instruments

Exports:
    HTML  : Page HTML template (injected into SPA)
    JS    : Page JavaScript (injected into <script> block)

Backend endpoints for this page live in app.py (ep == "..." handlers).
To modify: edit HTML/JS here, backend logic in app.py.
"""


HTML = r"""
<!-- ═══════════ PAGE: SQ9 ═══════════ -->
<div class="page" id="page-sq9">
  <div class="topbar"><h2>SQUARE OF NINE</h2><span class="page-tag">GANN SQ9</span></div>
  <div class="card">
    <div class="card-title">⚙ INPUT</div>
    <div class="form-row">
      <label>CURRENT PRICE</label><input type="number" id="sq9-price" value="24500">
      <label>ALL-TIME LOW</label><input type="number" id="sq9-atl" value="900">
      <button class="btn-gold btn" onclick="loadSq9()">CALCULATE</button>
    </div>
  </div>
  <div id="sq9-content"></div>
</div>

<!-- ═══════════ PAGE: CYCLES ═══════════ -->
<div class="page" id="page-cycles">
  <div class="topbar"><h2>TIME CYCLES</h2><span class="page-tag">GANN CYCLES</span></div>
  <div class="card">
    <div class="card-title">⚙ PIVOT DATE</div>
    <div class="form-row">
      <label>PIVOT DATE</label><input type="date" id="cyc-pivot">
      <button class="btn-gold btn" onclick="loadCycles()">CALCULATE</button>
    </div>
  </div>
  <div id="cycles-content"></div>
</div>

<!-- ═══════════ PAGE: CONFLUENCE ═══════════ -->
<div class="page" id="page-confluence">
  <div class="topbar"><h2>CONFLUENCE SCORER</h2><span class="page-tag">MANUAL</span></div>
  <div id="confluence-content"></div>
</div>

<!-- ═══════════ PAGE: SCHEDULER ═══════════ -->
<div class="page" id="page-scheduler">
  <div class="topbar">
    <h2>AUTO-UPDATE SCHEDULER</h2>
    <div style="display:flex;gap:8px;">
      <button class="btn" onclick="triggerUpdate()">⟳ RUN NOW</button>
      <span class="page-tag">15:35 IST DAILY</span>
    </div>
  </div>
  <div id="sched-content" class="loading"><div class="spinner"></div>LOADING...</div>
</div>


<!-- ═══════════ PAGE: INSTRUMENTS DB ═══════════ -->
<div class="page" id="page-instruments">

  <!-- ══ HEADER ══════════════════════════════════════════════════════════ -->
  <div style="margin-bottom:20px;padding-bottom:16px;border-bottom:2px solid #0d2438;">
    <div style="display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:10px;">
      <div>
        <div style="font-family:Orbitron,monospace;font-size:1.7rem;font-weight:900;
                    color:#e8f4ff;letter-spacing:3px;line-height:1;
                    text-shadow:0 0 30px rgba(0,212,255,0.25);">INSTRUMENTS DATABASE</div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.78rem;
                    letter-spacing:5px;margin-top:8px;display:flex;gap:8px;align-items:center;">
          <span style="color:#00d4ff;">NSE</span>
          <span style="color:#163248;">·</span>
          <span style="color:#ffcc00;">BSE</span>
          <span style="color:#163248;">·</span>
          <span style="color:#ff8c00;">MCX</span>
        </div>
      </div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <span id="inst-count" style="font-family:Share Tech Mono,monospace;font-size:0.6rem;
              letter-spacing:2px;color:#00d4ff;background:rgba(0,212,255,0.07);
              border:1px solid rgba(0,212,255,0.2);padding:5px 14px;">257 INSTRUMENTS</span>
        <span id="inst-match-count" style="display:none;font-family:Share Tech Mono,monospace;
              font-size:0.6rem;letter-spacing:2px;color:#ffcc00;
              background:rgba(255,204,0,0.07);border:1px solid rgba(255,204,0,0.25);
              padding:5px 14px;"></span>
      </div>
    </div>
  </div>

  <!-- ══ SEARCH BAR ═══════════════════════════════════════════════════════ -->
  <div style="display:flex;align-items:stretch;margin-bottom:20px;
              border:2px solid #1a3a55;background:#03080e;position:relative;">

    <!-- top gradient line -->
    <div style="position:absolute;top:0;left:0;right:0;height:2px;
         background:linear-gradient(90deg,#00d4ff,#ffcc00,#ff8c00,#00d4ff);
         background-size:300%;animation:gradientShift 4s linear infinite;"></div>

    <!-- icon -->
    <div style="display:flex;align-items:center;padding:0 20px;
                color:#00d4ff;font-size:1.5rem;flex-shrink:0;
                border-right:1px solid #1a3a55;background:#03080e;
                pointer-events:none;">⌕</div>

    <!-- input -->
    <input type="text" id="inst-global-search"
      placeholder="Search all 257 instruments — type any symbol, name, sector or ruling planet..."
      oninput="globalInstSearch(this.value)"
      autocomplete="off" spellcheck="false"
      style="flex:1;min-width:0;
             background:#03080e !important;
             border:none !important;
             outline:none !important;
             box-shadow:none !important;
             color:#ffffff !important;
             -webkit-text-fill-color:#ffffff !important;
             caret-color:#00d4ff;
             font-family:Share Tech Mono,monospace;
             font-size:0.95rem;
             padding:16px 18px;
             letter-spacing:0.5px;">

    <!-- pills -->
    <div style="display:flex;align-items:center;gap:6px;padding:0 14px;
                border-left:1px solid #1a3a55;background:#03080e;flex-shrink:0;">
      <span id="pill-all"  onclick="instTypeFilter('')"
        style="font-family:Share Tech Mono,monospace;font-size:0.6rem;padding:5px 11px;
               cursor:pointer;border:1px solid rgba(255,255,255,0.15);color:#e8f4ff;
               background:rgba(255,255,255,0.08);letter-spacing:1px;transition:all 0.15s;
               font-weight:700;">ALL</span>
      <span id="pill-idx"  onclick="instTypeFilter('INDEX')"
        style="font-family:Share Tech Mono,monospace;font-size:0.6rem;padding:5px 11px;
               cursor:pointer;border:1px solid rgba(0,212,255,0.3);color:#00d4ff;
               background:rgba(0,212,255,0.06);letter-spacing:1px;transition:all 0.15s;">IDX</span>
      <span id="pill-eq"   onclick="instTypeFilter('EQUITY')"
        style="font-family:Share Tech Mono,monospace;font-size:0.6rem;padding:5px 11px;
               cursor:pointer;border:1px solid rgba(255,204,0,0.3);color:#ffcc00;
               background:rgba(255,204,0,0.06);letter-spacing:1px;transition:all 0.15s;">EQ</span>
      <span id="pill-mcx"  onclick="instTypeFilter('COMMODITY')"
        style="font-family:Share Tech Mono,monospace;font-size:0.6rem;padding:5px 11px;
               cursor:pointer;border:1px solid rgba(255,140,0,0.3);color:#ff8c00;
               background:rgba(255,140,0,0.06);letter-spacing:1px;transition:all 0.15s;">MCX</span>
    </div>

    <!-- clear -->
    <div onclick="instClear()"
      style="display:flex;align-items:center;padding:0 18px;color:#1a3a55;font-size:1.1rem;
             cursor:pointer;border-left:1px solid #1a3a55;background:#03080e;flex-shrink:0;
             transition:color 0.15s;"
      onmouseover="this.style.color='#ff3355'"
      onmouseout="this.style.color='#1a3a55'">✕</div>
  </div>

  <!-- ══ TABLE ════════════════════════════════════════════════════════════ -->
  <div style="border:1px solid #0d2438;background:#020a12;overflow:hidden;">

    <!-- sticky column headers — 10 cols, no ASPECTS -->
    <div id="inst-thead" style="display:grid;
         grid-template-columns:155px 52px 155px 105px 78px 96px 112px 130px 155px;column-gap:8px;
         gap:0;padding:9px 16px;background:#010608;
         border-bottom:1px solid #0d2438;position:sticky;top:0;z-index:20;">
      <div style="font-family:Share Tech Mono,monospace;font-size:0.54rem;color:#3a5a72;letter-spacing:2px;">SYMBOL</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.54rem;color:#3a5a72;letter-spacing:2px;">EXCH</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.54rem;color:#3a5a72;letter-spacing:2px;">SECTOR</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.54rem;color:#3a5a72;letter-spacing:2px;">RULER ♄</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.54rem;color:#3a5a72;letter-spacing:2px;text-align:right;">ATL</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.54rem;color:#3a5a72;letter-spacing:2px;text-align:right;">ATH</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.54rem;color:#3a5a72;letter-spacing:2px;">INCEPTION</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.54rem;color:#3a5a72;letter-spacing:2px;text-align:right;">CLOSE</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.54rem;color:#3a5a72;letter-spacing:2px;">SIGNAL</div>
    </div>

    <!-- scrollable rows -->
    <div id="inst-main-table"
         style="height:calc(100vh - 340px);min-height:380px;overflow-y:auto;overflow-x:hidden;">
      <div style="display:flex;align-items:center;justify-content:center;height:120px;
                  gap:14px;color:#3a5a72;font-family:Share Tech Mono,monospace;font-size:0.8rem;">
        <div class="spinner"></div> LOADING INSTRUMENTS...
      </div>
    </div>

    <!-- footer -->
    <div style="padding:8px 16px;border-top:1px solid #0d2438;background:#010608;
         display:flex;justify-content:space-between;align-items:center;">
      <span id="inst-footer-count" style="font-family:Share Tech Mono,monospace;
            font-size:0.58rem;color:#3a5a72;letter-spacing:2px;"></span>
      <span style="font-family:Share Tech Mono,monospace;font-size:0.56rem;color:#1a3a55;">
        CLICK ANY ROW → CHART + ANALYSIS</span>
    </div>
  </div>
</div>

"""


JS = r"""
function initConfluence() {
  const checks = [
    {cat:'GANN MATH',items:[
      {label:'Price within 0.75% of Sq9 level',pts:2},
      {label:'Price on Gann angle (1×1, 2×1, etc)',pts:2},
      {label:'90 / 180 / 270 / 360-day cycle due within 7 days',pts:2},
      {label:'Anniversary of major high or low (1yr, 2yr)',pts:3},
    ]},
    {cat:'PLANETARY',items:[
      {label:'Jupiter–Saturn aspect within 5 days',pts:2},
      {label:'Transit hits natal planet degree (±2°)',pts:3},
      {label:'Ruling planet turns retrograde or direct (station)',pts:3},
      {label:'Solar/Lunar eclipse within 15 days',pts:3},
      {label:'Ruling planet in major aspect today',pts:2},
      {label:'Full Moon or New Moon within 3 days',pts:1},
    ]},
    {cat:'PRICE ACTION',items:[
      {label:'Volume spike (>2× 20-day average)',pts:2},
      {label:'Reversal candle (hammer, engulfing, doji)',pts:1},
      {label:'Gap opening at key level',pts:2},
    ]},
  ];
  let score = 0, maxScore = checks.reduce((a,c)=>a+c.items.reduce((b,i)=>b+i.pts,0),0);
  const update = () => {
    const pts = Array.from(document.querySelectorAll('.conf-chk:checked')).reduce((a,el)=>a+parseInt(el.dataset.pts),0);
    const pct = Math.round(pts/maxScore*100);
    const col = pts>=12?'var(--red)':pts>=8?'var(--gold)':pts>=5?'var(--green)':'var(--dim)';
    const verdict = pts>=12?'EXTREME CONFLUENCE — ACT NOW':pts>=8?'STRONG SIGNAL — HIGH PROBABILITY':pts>=5?'MODERATE — WATCH CLOSELY':'WEAK — WAIT FOR MORE';
    document.getElementById('conf-score-num').textContent = pts;
    document.getElementById('conf-score-num').style.color = col;
    document.getElementById('conf-score-lbl').textContent = verdict;
    document.getElementById('conf-score-lbl').style.color = col;
    document.getElementById('conf-bar').style.width = pct+'%';
    document.getElementById('conf-bar').style.background = col;
  };

  let html = '';
  checks.forEach(cat => {
    html += `<div class="card"><div class="card-title">${cat.cat}</div>`;
    cat.items.forEach(item => {
      html += `<label style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-bottom:1px solid var(--border);cursor:pointer;transition:background 0.12s;" onmouseover="this.style.background='rgba(0,212,255,0.03)'" onmouseout="this.style.background=''">
        <input type="checkbox" class="conf-chk" data-pts="${item.pts}" onchange="document.getElementById('conf-update').click()">
        <span style="flex:1;font-size:0.83rem;">${item.label}</span>
        <span class="badge bgo">+${item.pts}</span>
      </label>`;
    });
    html += '</div>';
  });

  document.getElementById('confluence-content').innerHTML = `
    <div class="card" style="margin-bottom:14px;">
      <div class="score-big">
        <span class="score-num" id="conf-score-num" style="color:var(--dim);">0</span>
        <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:3px;">/ ${maxScore} POINTS</span>
        <div style="height:4px;background:var(--border);margin:10px 0;"><div id="conf-bar" style="height:100%;width:0%;transition:all 0.3s;"></div></div>
        <span id="conf-score-lbl" class="score-lbl" style="color:var(--dim);">CHECK CONDITIONS BELOW</span>
      </div>
    </div>
    <button id="conf-update" onclick="" style="display:none;"></button>
    ${html}`;

  document.getElementById('conf-update').addEventListener('click', update);
}

// ════════════════════════════════════════════════════════════════════
// SCHEDULER
// ════════════════════════════════════════════════════════════════════
async function loadScheduler() {
  try {
    const d = await api('scheduler_status');
    renderScheduler(d);
  } catch(e) {
    document.getElementById('sched-content').innerHTML = `<div class="err">${e.message}</div>`;
  }
}

function renderScheduler(d) {
  const st = d.status||{};
  const prices = d.cached_prices||{};
  const logs = d.logs||[];
  const priceCount = Object.keys(prices).length;
  const lastSyms = Object.keys(prices).slice(0,5).join(', ');

  let logHtml = '';
  logs.forEach(l => {
    logHtml += `<div class="trow" style="grid-template-columns:160px 80px 50px 50px 60px 1fr;">
      <div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--dim);">${(l.run_at||'').slice(0,16)}</div>
      <div class="badge bc" style="font-size:0.55rem;">${l.type}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--green);">${l.ok||0} ok</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:${l.err>0?'var(--red)':'var(--dim)'};">${l.err||0} err</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;">${(l.duration_s||0).toFixed(1)}s</div>
      <div style="font-size:0.75rem;color:var(--text);">${l.notes||''}</div>
    </div>`;
  });

  // Price snapshot
  let priceHtml = '';
  Object.entries(prices).slice(0,20).forEach(([sym,p]) => {
    const chg = p.change_pct||0;
    const col = chg>=0?'var(--green)':'var(--red)';
    priceHtml += `<div class="trow" style="grid-template-columns:80px 90px 60px 70px 80px;">
      <div style="font-family:Share Tech Mono,monospace;color:var(--cyan);font-size:0.78rem;">${sym}</div>
      <div style="font-family:Share Tech Mono,monospace;font-weight:600;">${(p.close||0).toLocaleString()}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:${col};">${chg>=0?'+':''}${chg.toFixed(2)}%</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--dim);">H:${(p.high||0).toFixed(0)}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--dim);">L:${(p.low||0).toFixed(0)}</div>
    </div>`;
  });

  document.getElementById('sched-content').innerHTML = `
    <div class="g4" style="margin-bottom:14px;">
      <div class="stat"><span class="val" style="color:${st.running?'var(--gold)':'var(--green)'};">${st.running?'RUNNING':'IDLE'}</span><span class="lbl">SCHEDULER</span></div>
      <div class="stat"><span class="val">${priceCount}</span><span class="lbl">CACHED PRICES</span></div>
      <div class="stat"><span class="val" style="font-size:0.75rem;">${(st.last_run||'never').slice(0,16)}</span><span class="lbl">LAST RUN</span></div>
      <div class="stat"><span class="val" style="font-size:0.75rem;">15:35 IST</span><span class="lbl">NEXT SCHEDULED</span></div>
    </div>
    <div class="card" style="background:rgba(0,212,255,0.02);border-color:rgba(0,212,255,0.15);margin-bottom:14px;">
      <div class="card-title">ℹ HOW THE SCHEDULER WORKS</div>
      <div style="font-size:0.82rem;line-height:1.7;color:var(--t2);">
        The scheduler runs automatically in the background while the app is open.
        <strong style="color:var(--cyan);">At 15:35 IST</strong> every market day (Mon–Fri), it:
        <br>1. Fetches end-of-day prices from NSE/BSE/MCX via <span class="badge bc">yfinance</span>
        <br>2. Runs Fourier + regime + S/R analysis for priority instruments
        <br>3. Caches everything to <span class="badge bgo">market_data_v2.db</span> (SQLite) so the UI loads instantly
        <br>4. Without yfinance, uses synthetic price models — install with <code style="color:var(--cyan);">pip install yfinance</code>
      </div>
    </div>
    <div class="g2">
      <div class="card">
        <div class="card-title">📋 RUN LOG</div>
        ${logHtml || '<div style="padding:10px;color:var(--dim);">No runs yet — click RUN NOW to start</div>'}
      </div>
      <div class="card">
        <div class="card-title">💰 CACHED PRICE SNAPSHOT</div>
        ${priceHtml || '<div style="padding:10px;color:var(--dim);">No prices cached yet — yfinance not installed or RUN NOW not triggered</div>'}
      </div>
    </div>`;
}

async function triggerUpdate() {
  try {
    await api('scheduler_trigger');
    setTimeout(loadScheduler, 2000);
  } catch(e) {}
}

// ════════════════════════════════════════════════════════════════════
// SIDEBAR STATUS UPDATE
// ════════════════════════════════════════════════════════════════════
function updateSidebar() {
  // Date/time in IST — format: 2026-03-19 18:29 IST
  const now = new Date();
  const ist = new Date(now.getTime() + (5.5*60*60*1000));
  const pad = n => String(n).padStart(2,'0');
  const dateStr = ist.getUTCFullYear()+'-'+pad(ist.getUTCMonth()+1)+'-'+pad(ist.getUTCDate())
    +' '+pad(ist.getUTCHours())+':'+pad(ist.getUTCMinutes())+' IST';
  const dateEl = document.getElementById('sideDate');
  if (dateEl) dateEl.textContent = dateStr;

  // EOD NIFTY price — uses price API which reads from scheduler cache
  api('price', {symbol:'NIFTY50', date:today}).then(d => {
    const price = d.close || d.price;
    const chgPct = typeof d.change_pct === 'number' ? d.change_pct : null;
    const niftyEl = document.getElementById('sideNifty');
    if (!niftyEl) return;
    if (!price) { niftyEl.textContent = '· EOD NIFTY --'; return; }
    const chgStr = chgPct != null ? (chgPct>=0?' +':' ') + chgPct.toFixed(2) + '%' : '';
    const col = chgPct == null ? 'var(--dim)' : chgPct >= 0 ? '#26a69a' : '#ef5350';
    niftyEl.innerHTML = '· EOD NIFTY <b style="color:var(--cyan)">'
      + Number(price).toLocaleString('en-IN') + '</b>'
      + ' <b style="color:'+col+'">' + chgStr + '</b>';
  }).catch(() => {
    const el = document.getElementById('sideNifty');
    if (el) el.textContent = '· EOD NIFTY --';
  });
}

// ════════════════════════════════════════════════════════════════════
// INSTRUMENTS DATABASE
// ════════════════════════════════════════════════════════════════════
// ── INSTRUMENTS DB — 3-section layout ──────────────────────────────
// ══ INSTRUMENTS DB — unified table, search, signal, aspects ════════
// ════════════════════════════════════════════════════════════════════
// INSTRUMENTS DB
// ════════════════════════════════════════════════════════════════════
let _instPrices  = {};
let _instAll     = [];
let _instLoaded  = false;
let _instFilter  = '';
let _instType    = '';

async function loadInstrumentsPage() {
  if (_instLoaded) { instRender(); return; }
  // Show loading spinner while fetching
  const el = document.getElementById('inst-main-table');
  if (el) el.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:120px;' +
    'gap:14px;color:#3a5a72;font-family:\'Share Tech Mono\',monospace;font-size:0.8rem;">' +
    '<div class="spinner"></div> LOADING INSTRUMENTS...</div>';
  try {
    const d     = await api('instruments_full');
    _instAll    = d.instruments || [];
    _instPrices = d.prices || {};
    _instLoaded = true;
    const cntEl = document.getElementById('inst-count');
    if (cntEl) cntEl.textContent = _instAll.length + ' INSTRUMENTS';
    instRender();
  } catch(e) {
    _instLoaded = false;  // allow retry on next nav
    const el2 = document.getElementById('inst-main-table');
    if (el2) el2.innerHTML =
      `<div style="padding:32px;color:var(--red);font-family:Share Tech Mono,monospace;font-size:0.8rem;cursor:pointer" onclick="loadInstrumentsPage()">` +
      `&#9888; ERROR: ${e.message} — Click to retry</div>`;
  }
}

function globalInstSearch(raw) {
  _instFilter = (raw||'').toLowerCase().trim();
  instRender();
}

function instTypeFilter(type) {
  _instType = type;
  // Reset all pills
  ['pill-all','pill-idx','pill-eq','pill-mcx'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.style.opacity = '0.4';
    el.style.fontWeight = '400';
    el.style.borderWidth = '1px';
  });
  // Activate selected pill
  const aid = type==='INDEX'?'pill-idx':type==='EQUITY'?'pill-eq':type==='COMMODITY'?'pill-mcx':'pill-all';
  const a = document.getElementById(aid);
  if (a) { a.style.opacity='1'; a.style.fontWeight='700'; a.style.borderWidth='2px'; }
  instRender();
}

function instClear() {
  _instFilter = ''; _instType = '';
  const inp = document.getElementById('inst-global-search');
  if (inp) inp.value = '';
  const mc = document.getElementById('inst-match-count');
  if (mc) mc.style.display = 'none';
  instTypeFilter('');
}

function instRender() {
  const words = _instFilter ? _instFilter.split(/\s+/).filter(Boolean) : [];
  const typeOrder = {INDEX:0, EQUITY:1, COMMODITY:2};

  const rows = _instAll
    .filter(i => {
      if (_instType && i.instrument_type !== _instType) return false;
      if (!words.length) return true;
      const hay = (i.symbol+' '+i.name+' '+i.sector+' '+i.ruling_planet+' '+
                   i.exchange+' '+i.instrument_type).toLowerCase();
      return words.every(w => hay.includes(w));
    })
    .sort((a,b)=>(typeOrder[a.instrument_type]||9)-(typeOrder[b.instrument_type]||9));

  // Update match badge
  const mc = document.getElementById('inst-match-count');
  if (mc) {
    if (_instFilter||_instType) {
      mc.textContent = rows.length + ' MATCH' + (rows.length!==1?'ES':'');
      mc.style.display = 'inline';
    } else { mc.style.display = 'none'; }
  }
  const fc = document.getElementById('inst-footer-count');
  if (fc) fc.textContent = 'SHOWING ' + rows.length + ' OF ' + _instAll.length + ' INSTRUMENTS';

  const el = document.getElementById('inst-main-table');
  if (!el) return;

  if (!rows.length) {
    el.innerHTML = '<div style="padding:48px;text-align:center;color:var(--dim);' +
      'font-family:\'Share Tech Mono\',monospace;font-size:0.8rem;letter-spacing:2px;">NO INSTRUMENTS MATCH</div>';
    return;
  }

  // ── Signal helpers ──────────────────────────────────────────────
  function sigColor(s) {
    if (s>=18) return '#ff3355';
    if (s>=12) return '#ffcc00';
    if (s>=7)  return '#00d4ff';
    return '#3a5a72';
  }
  function sigLabel(s) {
    if (s>=18) return 'EXTREME';
    if (s>=12) return 'STRONG';
    if (s>=7)  return 'ACTIVE';
    return 'WEAK';
  }
  function starsHtml(n) {
    const f = Math.min(5,Math.max(0,n||0));
    return '<span style="color:#ffcc00;font-size:0.65rem;">' + '★'.repeat(f) + '</span>' +
           '<span style="color:#1a3a4a;font-size:0.65rem;">' + '★'.repeat(5-f) + '</span>';
  }

  // ── Type colours ────────────────────────────────────────────────
  const TC  = {INDEX:'#00d4ff', EQUITY:'#ffcc00', COMMODITY:'#ff8c00'};
  const TBG = {INDEX:'rgba(0,212,255,0.07)', EQUITY:'rgba(255,204,0,0.06)', COMMODITY:'rgba(255,140,0,0.06)'};
  const TLB = {INDEX:'NSE INDICES', EQUITY:'NSE EQUITIES', COMMODITY:'MCX COMMODITIES'};

  // Column grid — 10 cols, no ASPECTS
  // SYMBOL | NAME | EXCH | SECTOR | RULER | ATL | ATH | INCEPTION | CLOSE | SIGNAL
  const G = '155px 52px 155px 105px 78px 96px 112px 130px 155px';
  const GGAP = 'column-gap:8px;';

  let html = '';
  let lastType = null;

  rows.forEach(inst => {
    // ── Section header ───────────────────────────────────────────
    if (inst.instrument_type !== lastType) {
      lastType = inst.instrument_type;
      const cnt = rows.filter(r=>r.instrument_type===lastType).length;
      html += `
        <div style="display:flex;align-items:center;gap:10px;padding:9px 16px;
          background:${TBG[lastType]};border-top:1px solid var(--b2);
          border-bottom:1px solid var(--b2);
          position:sticky;top:0;z-index:10;backdrop-filter:blur(4px);">
          <span style="font-family:Share Tech Mono,monospace;font-size:0.6rem;
            letter-spacing:3px;color:${TC[lastType]};font-weight:700;">${TLB[lastType]}</span>
          <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;
            color:var(--dim);background:rgba(0,0,0,0.3);border:1px solid var(--border);
            padding:1px 8px;border-radius:1px;">${cnt}</span>
        </div>`;
    }

    // ── Price ─────────────────────────────────────────────────────
    const p     = _instPrices[inst.symbol] || {};
    const hasPx = p.price!=null && p.source==='EOD_CACHE';
    const price = hasPx
      ? p.price.toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2})
      : '—';
    const chg    = hasPx && p.change_pct!=null ? p.change_pct : null;
    const chgStr = chg!=null ? (chg>=0?'▲':'▼')+Math.abs(chg).toFixed(2)+'%' : '';
    const chgCol = chg==null?'#2a4a62':chg>=0?'#00ff88':'#ff3355';
    const pxCol  = hasPx ? '#ffffff' : '#2a4a62';

    // ── ATL / ATH ─────────────────────────────────────────────────
    const atlStr = inst.atl!=null ? Number(inst.atl).toLocaleString('en-IN',{maximumFractionDigits:0}) : '—';
    const athStr = inst.ath!=null ? Number(inst.ath).toLocaleString('en-IN',{maximumFractionDigits:0}) : '—';

    // ── Signal ────────────────────────────────────────────────────
    const sc    = inst.signal_score || 0;
    const sCol  = sigColor(sc);
    const sLbl  = sigLabel(sc);
    const sStrs = starsHtml(inst.signal_stars||0);
    const showBadge = sc >= 7;

    html += `
      <div style="display:grid;grid-template-columns:${G};${GGAP}
        align-items:center;padding:8px 16px;
        border-bottom:1px solid rgba(10,28,44,0.9);
        cursor:pointer;transition:background 0.1s;"
        onmouseover="this.style.background='rgba(0,212,255,0.04)'"
        onmouseout="this.style.background=''"
        onclick="instJump('${inst.symbol}',${p.price||0})">

        <!-- SYMBOL — hover shows full name -->
        <div style="font-family:Share Tech Mono,monospace;font-size:0.88rem;
             font-weight:700;color:${TC[inst.instrument_type]||'#00d4ff'};
             overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-right:10px;"
             title="${inst.symbol} — ${inst.name}">${inst.symbol}</div>

        <!-- EXCH -->
        <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;
             color:var(--dim);">${inst.exchange}</div>

        <!-- SECTOR -->
        <div style="font-size:0.7rem;color:#6a9db8;overflow:hidden;
             text-overflow:ellipsis;white-space:nowrap;padding-right:8px;"
             title="${inst.sector}">${inst.sector||'—'}</div>

        <!-- RULER -->
        <div style="font-family:Share Tech Mono,monospace;font-size:0.72rem;
             color:${PC[inst.ruling_planet]||'#FFA500'};
             overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
             ${inst.ruling_planet}</div>

        <!-- ATL -->
        <div style="font-family:Share Tech Mono,monospace;font-size:0.72rem;
             color:#00cc66;text-align:right;">${atlStr}</div>

        <!-- ATH -->
        <div style="font-family:Share Tech Mono,monospace;font-size:0.72rem;
             color:#ff5566;text-align:right;">${athStr}</div>

        <!-- INCEPTION -->
        <div style="font-family:Share Tech Mono,monospace;font-size:0.64rem;
             color:#3a6a8a;">${inst.inception_date||'—'}</div>

        <!-- CLOSE + CHANGE -->
        <div style="text-align:right;">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.8rem;
               font-weight:700;color:${pxCol};">${price}</div>
          ${chgStr ? `<div style="font-size:0.6rem;color:${chgCol};margin-top:1px;">${chgStr}</div>` : ''}
        </div>

        <!-- SIGNAL -->
        <div>
          ${sc > 0 ? `
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;flex-wrap:wrap;">
            <span style="font-family:Share Tech Mono,monospace;font-size:0.86rem;
                 font-weight:700;color:${sCol};">${sc}</span>
            <span style="font-family:Share Tech Mono,monospace;font-size:0.52rem;
                 color:#2a4a62;">/25</span>
            ${showBadge ? `<span style="font-family:Share Tech Mono,monospace;
                 font-size:0.5rem;padding:2px 7px;color:${sCol};
                 border:1px solid ${sCol};background:${sCol}18;
                 letter-spacing:1px;white-space:nowrap;">${sLbl}</span>` : ''}
          </div>
          <div style="margin-top:1px;">${sStrs}</div>
          ` : `<span style="color:#1e3a4a;font-family:Share Tech Mono,monospace;
               font-size:0.75rem;">—</span>`}
        </div>

      </div>`;
  });

  el.innerHTML = html;
}

function instJump(sym, price) {
  nav('chart');
  const s = document.getElementById('chart-sym');
  if (s) s.value = sym;
  if (price) { const p2 = document.getElementById('chart-price'); if(p2) p2.value = price; }
  loadChart();
}

// Legacy aliases
function jumpFromInstrumentsDB(sym, price) { instJump(sym, price); }
function quickFilter(t) { instTypeFilter(t); }
function clearGlobalSearch() { instClear(); }

// ════════════════════════════════════════════════════════════════════
// INIT
// ════════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded',async()=>{
  // In chartWindow mode the fullscreen chart IIFE (page_fundamentals.JS) takes over.
  // Skip the main SPA bootstrap entirely so it doesn't fight the chart renderer.
  if (window.location.search.indexOf('chartWindow=1') !== -1) return;

  setGlobalDate(today); syncDateFields();
  setDate('az-pdate',new Date(Date.now()-120*24*3600*1000).toISOString().split('T')[0]);
  setDate('cyc-pivot',new Date(Date.now()-180*24*3600*1000).toISOString().split('T')[0]);
  initSymbols().catch(function(e){console.warn('initSymbols:',e);setTimeout(initSymbols,3000);});
  setTimeout(function(){ nav("advisor"); },300);
  if(typeof initConfluence==='function') initConfluence();
  if(typeof updateSidebar==='function')  updateSidebar();
  setInterval(function(){if(typeof updateSidebar==='function')updateSidebar();},60000);
});


// ════════════════════════════════════════════════════════════════════
// INVESTMENT AI ADVISOR
// ════════════════════════════════════════════════════════════════════

// ── Advisor mode toggle ──────────────────────────────────────────────────
let _advMode = 'portfolio';

function setAdvisorMode(mode) {
  _advMode = mode;
  const portBtn = document.getElementById('adv-mode-portfolio');
  const singleBtn = document.getElementById('adv-mode-single');
  const portParams = document.getElementById('adv-portfolio-params');
  const singleParams = document.getElementById('adv-single-params');
  if (mode === 'portfolio') {
    portBtn.style.background = 'rgba(0,212,255,0.12)';
    portBtn.style.color = 'var(--cyan)';
    singleBtn.style.background = 'transparent';
    singleBtn.style.color = 'var(--dim)';
    portParams.style.display = 'block';
    singleParams.style.display = 'none';
  } else {
    singleBtn.style.background = 'rgba(255,204,0,0.12)';
    singleBtn.style.color = 'var(--gold)';
    portBtn.style.background = 'transparent';
    portBtn.style.color = 'var(--dim)';
    portParams.style.display = 'none';
    singleParams.style.display = 'block';
    // Populate dropdown if empty
    const sel = document.getElementById('adv-single-sym');
    if (sel && sel.options.length <= 1) {
      api('all_symbols').then(d => {
        const syms = (d.equities || []).sort((a,b) => a.symbol.localeCompare(b.symbol));
        syms.forEach(s => {
          const o = document.createElement('option');
          o.value = s.symbol;
          o.textContent = s.symbol + ' — ' + (s.name || '');
          sel.appendChild(o);
        });
      }).catch(()=>{});
    }
  }
  // Hide previous results
  document.getElementById('adv-results').style.display = 'none';
  document.getElementById('adv-single-results').style.display = 'none';
  document.getElementById('adv-portfolio-card').style.display = 'none';
  document.getElementById('adv-error').style.display = 'none';
}

async function runSingleStockReport() {
  const sym    = document.getElementById('adv-single-sym').value;
  const type   = document.getElementById('adv-single-type').value;
  const amount = parseFloat(document.getElementById('adv-single-amount').value) || 100000;
  const risk   = document.getElementById('adv-single-risk').value;

  if (!sym) {
    document.getElementById('adv-error').style.display = 'block';
    document.getElementById('adv-error').textContent = '⚠ Please select a stock first.';
    return;
  }

  document.getElementById('adv-error').style.display = 'none';
  document.getElementById('adv-single-results').style.display = 'none';
  document.getElementById('adv-results').style.display = 'none';
  document.getElementById('adv-portfolio-card').style.display = 'none';
  document.getElementById('adv-loading').style.display = 'flex';

  const steps = [
    'Fetching planetary positions for ' + sym + '...',
    'Running Gann Sq9 + Time Cycles...',
    'Computing Simons FFT + Fourier analysis...',
    'Reading natal chart transits...',
    'Fetching fundamental ratios...',
    'Building full stock report...'
  ];
  let si = 0;
  const stxt = document.getElementById('adv-loading-text');
  const interval = setInterval(() => { stxt.textContent = steps[si++ % steps.length]; }, 1600);

  try {
    // Run advisor with this single stock forced
    const d = await api('advisor', {
      amount:    amount,
      type:      type,
      risk:      risk,
      diversify: 1,
      symbols:   sym,
      sector:    '',
    });
    clearInterval(interval);
    document.getElementById('adv-loading').style.display = 'none';
    renderSingleStockReport(d, sym, type, amount);
  } catch(e) {
    clearInterval(interval);
    document.getElementById('adv-loading').style.display = 'none';
    document.getElementById('adv-error').style.display = 'block';
    document.getElementById('adv-error').textContent = '⚠ ' + e.message;
  }
}

function expandSingleChart(srcId, chartType) {
  const overlay = document.getElementById('single-chart-overlay');
  const bigCvs  = document.getElementById('single-chart-big');
  if (!overlay || !bigCvs) return;

  const r = window._singleRec;
  if (!r) return;

  // Size to 90% of viewport
  const W = Math.min(window.innerWidth  * 0.90, 1300);
  const H = Math.min(window.innerHeight * 0.82, 720);
  bigCvs.width  = W;
  bigCvs.height = H;
  bigCvs.style.width  = W + 'px';
  bigCvs.style.height = H + 'px';

  overlay.style.display = 'flex';

  if (chartType === 'proj')   drawPriceProjectionBig('single-chart-big', r, W, H);
  else if (chartType === 'sr') drawSRChartBig('single-chart-big', r, W, H);
  else                        drawPlanetChartBig('single-chart-big', r, W, H);
}

function renderSingleStockReport(d, sym, invType, amount) {
  const el = document.getElementById('adv-single-results');
  const recs = d.recommendations || [];
  const r    = recs[0];

  if (!r) {
    el.innerHTML = '<div class="err">No data returned for ' + sym + '. The stock may score below the threshold for current market conditions.</div>';
    el.style.display = 'block';
    return;
  }

  const pd = d.planet_dashboard || {};
  const mo = d.market_overview || {};
  const rf = d.reversal_forecast || {};

  // Verdict logic — comprehensive
  const conf = r.confidence || 0;
  const regime = r.regime || '';
  const fundGrade = r.fund_grade || 'B';
  const bullSignals = r.bull_signals || 0;
  const bearSignals = r.bear_signals || 0;
  const maleficRetro = (pd.retrograde || []).filter(p => ['Saturn','Mars','Rahu','Ketu'].includes(p)).length;

  let verdict = '', verdictColor = '', verdictBg = '', verdictDetail = '';

  if (conf >= 65 && ['STRONG_BULL','WEAK_BULL'].includes(regime) && maleficRetro < 2) {
    verdict = 'STRONG BUY';
    verdictColor = '#00ff88';
    verdictBg = 'rgba(0,255,136,0.08)';
    verdictDetail = 'All engines align. High-confidence entry. Gann + Simons + Natal + Fundamental all bullish.';
  } else if (conf >= 50 && !['STRONG_BEAR'].includes(regime) && maleficRetro < 2) {
    verdict = 'BUY / ACCUMULATE';
    verdictColor = '#00d4ff';
    verdictBg = 'rgba(0,212,255,0.08)';
    verdictDetail = 'Conditions favour entry with standard position size. Monitor for Gann trigger date.';
  } else if (conf >= 40 && maleficRetro < 3) {
    verdict = 'HOLD / WATCH';
    verdictColor = '#ffcc00';
    verdictBg = 'rgba(255,204,0,0.08)';
    verdictDetail = 'Mixed signals. If already holding, maintain position with tight stop. Do not add fresh.';
  } else if (regime === 'STRONG_BEAR' || maleficRetro >= 3) {
    verdict = 'AVOID / EXIT';
    verdictColor = '#ff3355';
    verdictBg = 'rgba(255,51,85,0.08)';
    verdictDetail = 'Bearish regime + malefic stations. If holding, consider booking profits or cutting losses.';
  } else {
    verdict = 'WEAK / WAIT';
    verdictColor = '#ff8800';
    verdictBg = 'rgba(255,136,0,0.08)';
    verdictDetail = 'Below threshold. Wait for better planetary window or Gann time cycle to complete.';
  }

  const confColor = conf>=70?'#00ff88':conf>=50?'#00d4ff':'#ff8800';
  const regColor  = {STRONG_BULL:'#00ff88',WEAK_BULL:'#8fea80',SIDEWAYS:'#ffcc00',WEAK_BEAR:'#ff8800',STRONG_BEAR:'#ff3355',HIGH_VOLATILITY:'#ff8800'}[regime]||'#7aa8c0';

  let html = '';

  // ── Verdict banner ──
  html += '<div style="background:'+verdictBg+';border:2px solid '+verdictColor+';border-radius:4px;padding:18px 20px;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">'
    + '<div>'
    + '<div style="font-family:Orbitron,sans-serif;font-size:1.4rem;color:'+verdictColor+';font-weight:900;letter-spacing:3px;margin-bottom:4px;">'+verdict+'</div>'
    + '<div style="font-family:Share Tech Mono,monospace;font-size:0.78rem;color:var(--t2);">'+verdictDetail+'</div>'
    + '</div>'
    + '<div style="text-align:right;">'
    + '<div style="font-family:Orbitron,sans-serif;font-size:2rem;color:'+confColor+';font-weight:900;">'+(Math.round(conf*100)/100).toFixed(1)+'<span style="font-size:0.9rem;color:var(--dim);">/100</span></div>'
    + '<div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:2px;">CONFIDENCE</div>'
    + '</div>'
    + '</div>';

  // ── 5-engine score breakdown ──
  html += '<div class="card" style="margin-bottom:14px;">'
    + '<div class="card-title">🌌 COMBINED ENGINE SCORES — ALL 5 LAYERS</div>'
    + '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:12px;">';

  const engines = [
    ['FUNDAMENTAL', r.fund_score||0, 25, '#ffcc00', r.fund_grade||'—'],
    ['GANN',        r.gann_score||0, 20, '#00d4ff', ''],
    ['SIMONS',      r.quant_score||0, 20, '#cc88ff', ''],
    ['NATAL',       r.natal_score||0, 20, '#00ff88', ''],
    ['PLANETS',     r.planet_score||0, 15, '#ff8800', ''],
  ];
  engines.forEach(([label, score, max, col, sub]) => {
    const pct = Math.round(score / max * 100);
    html += '<div style="background:var(--p2);border:1px solid rgba(255,255,255,0.06);padding:10px 8px;text-align:center;">'
      + '<div style="font-family:Orbitron,sans-serif;font-size:1.1rem;color:'+col+';font-weight:900;">'+score.toFixed(0)+'<span style="font-size:0.6rem;color:var(--dim);">/'+max+'</span></div>'
      + (sub ? '<div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:'+col+';margin-bottom:2px;">Grade: '+sub+'</div>' : '')
      + '<div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);letter-spacing:1px;margin-bottom:6px;">'+label+'</div>'
      + '<div style="background:rgba(0,0,0,0.4);height:4px;border-radius:2px;">'
      + '<div style="width:'+pct+'%;height:100%;background:'+col+';border-radius:2px;"></div>'
      + '</div>'
      + '</div>';
  });

  html += '</div>';

  // Fundamental signals row
  if ((r.fund_signals||[]).length) {
    html += '<div style="display:flex;flex-wrap:wrap;gap:5px;">';
    (r.fund_signals||[]).forEach(s => {
      const isBull = !s.toLowerCase().includes('high debt') && !s.toLowerCase().includes('expensive');
      const c = isBull ? '#00ff88' : '#ff3355';
      const bg = isBull ? 'rgba(0,255,136,0.06)' : 'rgba(255,51,85,0.06)';
      html += '<span style="background:'+bg+';border:1px solid '+c+';padding:2px 10px;font-family:Share Tech Mono,monospace;font-size:0.65rem;color:'+c+';">'+s+'</span>';
    });
    html += '</div>';
  }
  html += '</div>';

  // ── Regime + Market context ──
  html += '<div class="g2" style="margin-bottom:14px;">'
    + '<div class="card">'
    + '<div class="card-title">📈 MARKET REGIME — ' + sym + '</div>'
    + '<div style="font-family:Orbitron,sans-serif;font-size:1rem;color:'+regColor+';font-weight:700;margin-bottom:8px;">'+regime.replace('_',' ')+'</div>'
    + '<div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--dim);margin-bottom:8px;">Bull signals: <span style="color:#00ff88;">'+bullSignals+'</span> &nbsp; Bear signals: <span style="color:#ff3355;">'+bearSignals+'</span> &nbsp; Malefic℞: <span style="color:#ff8800;">'+maleficRetro+'</span></div>'
    + '<div style="display:flex;flex-wrap:wrap;gap:5px;">'
    + (pd.retrograde||[]).filter(p=>['Saturn','Mars','Rahu','Ketu'].includes(p)).map(p =>
        '<span style="background:rgba(255,51,85,0.08);border:1px solid rgba(255,51,85,0.3);padding:2px 8px;font-family:Share Tech Mono,monospace;font-size:0.65rem;color:#ff3355;">℞ '+p+'</span>'
    ).join('')
    + '</div>'
    + '</div>'

    // Reversal forecast
    + '<div class="card">'
    + '<div class="card-title">⏰ REVERSAL WINDOW FORECAST</div>'
    + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;">'
    + '<div class="stat"><span class="val" style="color:var(--cyan);font-size:1rem;">'+(rf.swing<=1?'Now':rf.swing+' days')+'</span><span class="lbl">SWING ENTRY</span></div>'
    + '<div class="stat"><span class="val" style="color:var(--purple);font-size:1rem;">'+(rf.short<=3?'Soon':rf.short+' days')+'</span><span class="lbl">SHORT TERM</span></div>'
    + '<div class="stat"><span class="val" style="color:var(--gold);font-size:1rem;">'+(rf.long<=7?'Accumulate':Math.round(rf.long/7)+' wks')+'</span><span class="lbl">LONG TERM</span></div>'
    + '</div>'
    + '</div>'
    + '</div>';

  // ── Trade Setup stat bars (CMP / Entry / SL / T1 / T2) ──
  const rrColor2 = r.rr_ratio>=2?'#00ff88':r.rr_ratio>=1?'#ffcc00':'#ff3355';
  html += '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:10px;">'
    + '<div class="stat"><span class="val" style="color:var(--t2);">₹'+( r.price||0).toLocaleString('en-IN',{maximumFractionDigits:2})+'</span><span class="lbl">CMP</span></div>'
    + '<div class="stat"><span class="val" style="color:#00d4ff;">₹'+( r.entry||0).toLocaleString('en-IN',{maximumFractionDigits:2})+'</span><span class="lbl">ENTRY</span></div>'
    + '<div class="stat"><span class="val" style="color:#ff3355;">₹'+( r.stop_loss||0).toLocaleString('en-IN',{maximumFractionDigits:2})+'</span><span class="lbl">STOP LOSS</span></div>'
    + '<div class="stat"><span class="val" style="color:#00ff88;">₹'+( r.target1||0).toLocaleString('en-IN',{maximumFractionDigits:2})+'</span><span class="lbl">TARGET 1</span></div>'
    + '<div class="stat"><span class="val" style="color:#00ff88;">₹'+( r.target2||0).toLocaleString('en-IN',{maximumFractionDigits:2})+'</span><span class="lbl">TARGET 2</span></div>'
    + '</div>';
  html += '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:14px;">'
    + '<div class="stat"><span class="val" style="color:var(--gold);">₹'+( r.allocation||0).toLocaleString('en-IN',{maximumFractionDigits:0})+'</span><span class="lbl">ALLOCATE</span></div>'
    + '<div class="stat"><span class="val">'+(r.allocation_pct||0)+'%</span><span class="lbl">OF PORTFOLIO</span></div>'
    + '<div class="stat"><span class="val">'+(r.shares||0)+'</span><span class="lbl">SHARES</span></div>'
    + '<div class="stat"><span class="val" style="color:'+rrColor2+';">'+(r.rr_ratio||0)+'x</span><span class="lbl">RISK:REWARD</span></div>'
    + '<div class="stat"><span class="val" style="color:#ff3355;">'+(r.risk_pct||0)+'%</span><span class="lbl">RISK/TRADE</span></div>'
    + '</div>';

  // ── Gann Trigger card ──
  const buyDateFmt = (r.buy_date||'').replace(/-/g,'/');
  const sellDateFmt = (r.sell_date||'').replace(/-/g,'/');
  const invTypeLabel = {'swing':'SWING TRADE (5-15 days)','short':'SHORT TERM (15-45 days)','long':'LONG TERM (3-18 months)'}[r.inv_type]||r.inv_type||'TRADE';
  const upT1 = r.entry&&r.target1 ? '+'+((r.target1-r.entry)/r.entry*100).toFixed(1)+'%' : '';
  const upT2 = r.entry&&r.target2 ? '+'+((r.target2-r.entry)/r.entry*100).toFixed(1)+'%' : '';
  const dwSL = r.entry&&r.stop_loss ? '-'+((r.entry-r.stop_loss)/r.entry*100).toFixed(1)+'%' : '';
  html += '<div style="background:rgba(0,0,0,0.25);border:1px solid var(--cyan);border-radius:3px;padding:14px 18px;margin-bottom:14px;">'
    + '<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">'
    + '<div style="font-family:Orbitron,sans-serif;font-size:0.72rem;color:var(--cyan);letter-spacing:2px;">⚡ GANN + SIMONS TRIGGER</div>'
    + '<div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--gold);background:rgba(255,204,0,0.1);border:1px solid rgba(255,204,0,0.3);padding:2px 8px;border-radius:2px;">'+invTypeLabel+'</div>'
    + '</div>'
    + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">'
    // Buy
    + '<div style="background:rgba(0,255,136,0.05);border:1px solid rgba(0,255,136,0.3);border-radius:3px;padding:12px;">'
    + '<div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:#00ff88;letter-spacing:1px;margin-bottom:8px;">🟢 BUY TRIGGER</div>'
    + '<div style="font-size:0.55rem;color:var(--dim);margin-bottom:3px;">ENTRY — '+(r.entry_source||'Sq9')+'</div>'
    + '<div style="font-family:Orbitron,sans-serif;font-size:1.3rem;color:#00ff88;font-weight:900;margin-bottom:4px;">₹'+(r.entry||0).toLocaleString('en-IN',{maximumFractionDigits:2})+'</div>'
    + (r.entry&&r.price&&r.inv_type!=='swing'?'<div style="font-size:0.62rem;color:var(--dim);">CMP ₹'+r.price.toLocaleString('en-IN',{maximumFractionDigits:0})+' → Entry ₹'+r.entry.toLocaleString('en-IN',{maximumFractionDigits:0})+' ('+(((r.entry-r.price)/r.price*100).toFixed(1))+'%)</div>':'')
    + '<div style="font-size:0.7rem;color:var(--dim);margin-top:6px;">OR WAIT UNTIL &nbsp;<span style="color:#00ff88;font-weight:700;">'+buyDateFmt+'</span></div>'
    + '<div style="font-size:0.65rem;color:var(--dim);margin-top:2px;">🕐 '+(r.buy_time||'09:20 IST')+'</div>'
    + '<div style="font-size:0.67rem;color:var(--t2);margin-top:6px;border-top:1px solid rgba(0,255,136,0.15);padding-top:6px;">'+(r.buy_condition||'')+'</div>'
    + '<div style="font-size:0.65rem;color:#ff3355;margin-top:6px;">🛡 SL: ₹'+(r.stop_loss||0).toLocaleString('en-IN',{maximumFractionDigits:2})+' <span style="color:var(--dim);">'+dwSL+'</span></div>'
    + '</div>'
    // Sell
    + '<div style="background:rgba(255,68,68,0.05);border:1px solid rgba(255,68,68,0.3);border-radius:3px;padding:12px;">'
    + '<div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:#ff3355;letter-spacing:1px;margin-bottom:8px;">🔴 SELL TRIGGER</div>'
    + '<div style="font-size:0.55rem;color:var(--dim);margin-bottom:3px;">TARGET 1 — '+(r.t1_source||'Sq9')+'</div>'
    + '<div style="font-family:Orbitron,sans-serif;font-size:1.3rem;color:#ffcc00;font-weight:900;margin-bottom:2px;">₹'+(r.target1||0).toLocaleString('en-IN',{maximumFractionDigits:2})+'</div>'
    + '<div style="font-size:0.62rem;color:#26a69a;margin-bottom:4px;">'+upT1+' upside</div>'
    + '<div style="font-size:0.7rem;color:var(--dim);">EXIT ON &nbsp;<span style="color:#ff3355;font-weight:700;">'+sellDateFmt+'</span></div>'
    + '<div style="font-size:0.67rem;color:var(--t2);margin-top:6px;border-top:1px solid rgba(255,68,68,0.15);padding-top:6px;">'+(r.sell_condition||'')+'</div>'
    + '<div style="font-size:0.65rem;color:var(--gold);margin-top:4px;">T2: ₹'+(r.target2||0).toLocaleString('en-IN',{maximumFractionDigits:2})+' <span style="color:var(--dim);">'+upT2+'</span> — '+(r.t2_source||'extended target')+'</div>'
    + '</div>'
    + '</div>'
    + '</div>';

  // ── Buy/Sell reasons ──
  html += '<div class="g2" style="margin-bottom:14px;">'
    + '<div class="card">'
    + '<div class="card-title" style="color:#00ff88;">✅ WHY TO BUY</div>';
  (r.buy_reasons||[]).forEach(b => {
    html += '<div style="font-size:0.78rem;color:var(--t2);padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);">• '+b+'</div>';
  });
  html += '</div>'
    + '<div class="card">'
    + '<div class="card-title" style="color:#ff3355;">⚠ RISKS / EXIT SIGNALS</div>';
  (r.sell_reasons||[]).forEach(s => {
    html += '<div style="font-size:0.78rem;color:var(--t2);padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);">• '+s+'</div>';
  });
  html += '</div></div>';

  // ── Charts row — use expandSingleChart() which targets the shared DOM overlay ──
  html += '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:14px;">';

  [['PRICE PROJECTION','single-proj-0','proj'],
   ['SUPPORT / RESISTANCE','single-sr-0','sr'],
   ['NATAL ASPECT STRENGTH','single-planet-0','planet']].forEach(function([title, cid, type]) {
    html += '<div>'
      + '<div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">'
      + title + ' <span style="color:var(--cyan);cursor:pointer;" onclick="expandSingleChart(\''+cid+'\',\''+type+'\')">⛶ EXPAND</span></div>'
      + '<div style="background:var(--p2);border:1px solid var(--border);height:160px;position:relative;overflow:hidden;cursor:pointer;" onclick="expandSingleChart(\''+cid+'\',\''+type+'\')">'
      + '<canvas id="'+cid+'" style="width:100%;height:100%;display:block;"></canvas>'
      + '</div></div>';
  });

  html += '</div>';

  // ── Planetary influence ──
  html += '<div class="card" style="margin-bottom:14px;">'
    + '<div class="card-title" style="color:var(--purple);">🌌 PLANETARY INFLUENCE ON ' + sym + '</div>'
    + '<div style="display:flex;flex-wrap:wrap;gap:6px;">';
  const aspects = (pd.aspects||[]).slice(0,8);
  aspects.forEach(a => {
    const c = a.direction==='BULLISH'?'#00ff88':a.direction==='BEARISH'?'#ff3355':'#ffcc00';
    const bg = a.direction==='BULLISH'?'rgba(0,255,136,0.07)':a.direction==='BEARISH'?'rgba(255,51,85,0.07)':'rgba(255,204,0,0.07)';
    html += '<span style="background:'+bg+';border:1px solid '+c+';padding:3px 10px;font-family:Share Tech Mono,monospace;font-size:0.68rem;color:'+c+';">'+( a.planets||'')+'  <b>'+( a.direction||'')+'</b>  '+(a.orb||0).toFixed(2)+'°</span>';
  });
  html += '</div>';
  (r.planet_text||[]).forEach(pt => {
    html += '<div style="font-size:0.75rem;color:var(--t2);padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.03);">'+pt+'</div>';
  });
  html += '</div>';

  // ── Reversal dates ──
  if ((r.reversal_dates||[]).length) {
    html += '<div class="card" style="margin-bottom:14px;">'
      + '<div class="card-title">📅 HIGH-CONFLUENCE REVERSAL DATES IN WINDOW</div>'
      + '<div style="display:flex;flex-wrap:wrap;gap:8px;">';
    (r.reversal_dates||[]).forEach(rd => {
      const bc = rd.bias==='BULLISH'?'rgba(0,255,136,0.1)':rd.bias==='BEARISH'?'rgba(255,68,68,0.1)':'rgba(255,204,0,0.1)';
      const tc = rd.bias==='BULLISH'?'#00ff88':rd.bias==='BEARISH'?'#ff3355':'#ffcc00';
      const tags = (rd.cycle?'⏰ Cycle ':'')+( rd.station?'⚡ Station ':'');
      html += '<div style="background:'+bc+';border:1px solid '+tc+';border-radius:3px;padding:8px 12px;font-family:Share Tech Mono,monospace;font-size:0.7rem;">'
        + '<div style="color:'+tc+';font-weight:700;font-size:0.8rem;">'+rd.date.replace(/-/g,'/')+'</div>'
        + '<div style="color:var(--dim);margin-top:2px;">'+tags+' <span style="color:'+tc+';">'+rd.bias+'</span></div>'
        + '</div>';
    });
    html += '</div></div>';
  }

  el.innerHTML = html;
  el.style.display = 'block';
  el.scrollIntoView({behavior:'smooth', block:'start'});

  // Store rec data for expand modal
  window._singleRec = r;
  if (!window._advRecs) window._advRecs = {};
  window._advRecs[0] = r;

  // Draw the 3 inline charts after DOM paint (needs offsetWidth)
  setTimeout(function() {
    ['single-proj-0','single-sr-0','single-planet-0'].forEach(function(cid) {
      const cvs = document.getElementById(cid);
      if (cvs) {
        // Set physical pixel dimensions from CSS layout
        cvs.width  = cvs.offsetWidth  || cvs.parentElement.offsetWidth  || 320;
        cvs.height = cvs.offsetHeight || 160;
      }
    });
    drawPriceProjection('single-proj-0', r);
    drawSRChart('single-sr-0', r);
    drawPlanetChart('single-planet-0', r);
  }, 200);
}

"""
