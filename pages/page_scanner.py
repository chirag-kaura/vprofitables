# -*- coding: utf-8 -*-
"""
page_scanner.py — Market Scanner — daily opportunity scan

Exports:
    HTML  : Page HTML template (injected into SPA)
    JS    : Page JavaScript (injected into <script> block)

Backend endpoints for this page live in app.py (ep == "..." handlers).
To modify: edit HTML/JS here, backend logic in app.py.
"""


HTML = r"""
<!-- ═══════════ PAGE: SCANNER ═══════════ -->
<div class="page" id="page-scanner">
  <div class="topbar">
    <h2>MARKET SCANNER</h2>
    <div style="display:flex;gap:8px;align-items:center;">
      <select id="scan-exchange" onchange="loadScanner()" style="background:var(--p2);border:1px solid var(--b2);color:var(--t2);padding:5px 8px;font-family:Share Tech Mono,monospace;font-size:0.7rem;outline:none;">
        <option value="">ALL EXCHANGES</option>
        <option value="NSE">NSE</option>
        <option value="BSE">BSE</option>
        <option value="MCX">MCX</option>
      </select>
      <button class="btn" onclick="loadScanner()">⟳ SCAN</button>
    </div>
  </div>
  <div class="card">
    <div class="card-title">📡 SIGNAL STRENGTH RANKING</div>
    <div id="scanner-loading" class="loading"><div class="spinner"></div>SCANNING...</div>
    <div id="scanner-table" style="display:none;"></div>
  </div>
</div>

"""


JS = r"""
async function loadScanner() {
  loading('scanner-loading', true);
  show('scanner-table', false);
  try {
    const d = await api('scanner');
    renderScanner(d);
  } catch(e) {
    document.getElementById('scanner-loading').innerHTML = `<div class="err">${e.message}</div>`;
  }
}

function renderScanner(d) {
  loading('scanner-loading', false);
  const el = document.getElementById('scanner-table');
  const exchange = document.getElementById('scan-exchange').value;
  const items = (d.results||[]).filter(r => !exchange || r.exchange === exchange);
  let html = backtestBanner()+`<div class="trow hdr" style="grid-template-columns:80px 1fr 70px 70px 80px 80px 70px;">
    <div>SYMBOL</div><div>NAME</div><div>EXCHANGE</div><div>SECTOR</div><div>RULER</div><div>SIGNAL</div><div>ALERT</div>
  </div>`;
  items.forEach(r => {
    const alert = r.signal_score >= 6
      ? `<span class="badge bgo">ALERT ${r.signal_score}</span>`
      : `<span style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--dim);">${r.signal_score}</span>`;
    const sc = r.signal_score >= 8 ? 'var(--red)' : r.signal_score >= 6 ? 'var(--gold)' : 'var(--green)';
    html += `<div class="trow" style="grid-template-columns:80px 1fr 70px 70px 80px 80px 70px;cursor:pointer;"
      onclick="jumpToChart('${r.symbol}', ${r.current_price||0})">
      <div style="font-family:Share Tech Mono,monospace;color:var(--cyan);font-size:0.78rem;">${r.symbol}</div>
      <div style="font-size:0.8rem;">${r.name}</div>
      <div class="badge bc" style="font-size:0.58rem;">${r.exchange}</div>
      <div style="font-size:0.75rem;color:var(--text);">${(r.sector||'').substring(0,12)}</div>
      <div style="color:${pcolor(r.ruling_planet)};font-family:Share Tech Mono,monospace;font-size:0.75rem;">${r.ruling_planet}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.8rem;font-weight:600;color:${sc};">${r.signal_score}</div>
      <div>${alert}</div>
    </div>`;
  });
  el.innerHTML = html;
  show('scanner-table');
}

function jumpToChart(sym, price) {
  nav('chart');
  document.getElementById('chart-sym').value = sym;
  if (price) document.getElementById('chart-price').value = price;
  loadChart();
}

// ════════════════════════════════════════════════════════════════════
// CHART + S/R
// ════════════════════════════════════════════════════════════════
// TRADINGVIEW-STYLE INTERACTIVE CHART ENGINE
// ════════════════════════════════════════════════════════════════

// ── State ────────────────────────────────────────────────────────
const TV = {
  data: null,
  fiiData: null,          // institutional data loaded on demand
  chartType: 'candle',
  indicators: { sma:false, ema:false, bb:false, vol:true, rsi:false, macd:false, adx:false, sr:false, ew:false, fii:false, astro:false },
  params: { smaP:[20,50,200], emaP:[9,21,50], bbP:20, bbStd:2, rsiP:14, rsiOB:70, rsiOS:30,
            macdFast:12, macdSlow:26, macdSig:9, adxP:14 },
  view: { start:0, end:0 },
  drag: { active:false, startX:0, startY:0, startStart:0, startEnd:0,
          yDrag:false, startMinV:0, startMaxV:0 },
  yRange: { min:null, max:null },   // null = auto-fit
  crosshair: { x:-1, y:-1, barIdx:-1 },
  mainH: 460,
  _eventsAttached: false,
};

// ── Indicator math ────────────────────────────────────────────────
function calcSMA(arr, p) {
  return arr.map((_,i) => {
    if (i < p-1) return null;
    let s=0; for(let j=i-p+1;j<=i;j++) s+=arr[j]; return s/p;
  });
}
function calcBB(arr, p, std) {
  const sma = calcSMA(arr, p);
  return arr.map((_,i) => {
    if (sma[i]===null) return {mid:null,upper:null,lower:null};
    let v=0; for(let j=i-p+1;j<=i;j++) v+=(arr[j]-sma[i])**2;
    const sd=Math.sqrt(v/p);
    return {mid:sma[i], upper:sma[i]+std*sd, lower:sma[i]-std*sd};
  });
}
function calcRSI(arr, p) {
  const r=Array(arr.length).fill(null);
  if (arr.length < p+1) return r;
  let g=0,l=0;
  for(let i=1;i<=p;i++){const d=arr[i]-arr[i-1]; if(d>0)g+=d; else l-=d;}
  let ag=g/p, al=l/p;
  r[p]=100-100/(1+(al===0?Infinity:ag/al));
  for(let i=p+1;i<arr.length;i++){
    const d=arr[i]-arr[i-1];
    ag=(ag*(p-1)+Math.max(d,0))/p;
    al=(al*(p-1)+Math.max(-d,0))/p;
    r[i]=100-100/(1+(al===0?Infinity:ag/al));
  }
  return r;
}
function calcEMA(arr, p) {
  const k=2/(p+1), e=Array(arr.length).fill(null);
  let seed=-1;
  for(let i=0;i<arr.length;i++){
    if(arr[i]===null||arr[i]===undefined) continue;
    if(seed<0){e[i]=arr[i];seed=i;} else e[i]=arr[i]*k+e[i-1]*(1-k);
  }
  return e;
}
function calcMACD(arr,fast,slow,sig){
  const ef=calcEMA(arr,fast),es=calcEMA(arr,slow);
  const ml=ef.map((v,i)=>v!==null&&es[i]!==null?v-es[i]:null);
  const sl=calcEMA(ml,sig);
  const hl=ml.map((v,i)=>v!==null&&sl[i]!==null?v-sl[i]:null);
  return {macdLine:ml,signalLine:sl,histogram:hl};
}
function calcADX(highs,lows,closes,p){
  const n=closes.length,adx=Array(n).fill(null),dp=Array(n).fill(null),dm=Array(n).fill(null);
  if(n<p*2) return {adx,diPlus:dp,diMinus:dm};
  const tr=[],dpp=[],dmm=[];
  for(let i=1;i<n;i++){
    tr.push(Math.max(highs[i]-lows[i],Math.abs(highs[i]-closes[i-1]),Math.abs(lows[i]-closes[i-1])));
    const u=highs[i]-highs[i-1],d=lows[i-1]-lows[i];
    dpp.push(u>d&&u>0?u:0); dmm.push(d>u&&d>0?d:0);
  }
  let atr=tr.slice(0,p).reduce((a,b)=>a+b,0);
  let dP=dpp.slice(0,p).reduce((a,b)=>a+b,0);
  let dM=dmm.slice(0,p).reduce((a,b)=>a+b,0);
  const dx=[];
  for(let i=p;i<tr.length;i++){
    atr=atr-atr/p+tr[i]; dP=dP-dP/p+dpp[i]; dM=dM-dM/p+dmm[i];
    const dip=atr>0?(dP/atr)*100:0,dim=atr>0?(dM/atr)*100:0;
    const dxv=(dip+dim)>0?Math.abs(dip-dim)/(dip+dim)*100:0;
    const idx=i+1; dp[idx]=dip; dm[idx]=dim; dx.push(dxv);
  }
  let av=dx.slice(0,p).reduce((a,b)=>a+b,0)/p; adx[p*2]=av;
  for(let i=p;i<dx.length;i++){av=(av*(p-1)+dx[i])/p; adx[i+p+1]=av;}
  return {adx,diPlus:dp,diMinus:dm};
}

// ── Popup helpers ─────────────────────────────────────────────────
function tvShowIndicatorPopup() {
  let el = document.getElementById('tv-ind-popup');
  if (!el) {
    el = document.createElement('div');
    el.id = 'tv-ind-popup';
    el.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);'
      +'width:520px;max-height:80vh;background:#0d1e2c;border:1px solid rgba(0,212,255,0.25);'
      +'border-radius:4px;z-index:9999;display:flex;flex-direction:column;'
      +'box-shadow:0 20px 60px rgba(0,0,0,0.7);font-family:Share Tech Mono,monospace;';
    document.body.appendChild(el);
  }
  const indList = [
    {id:'sma',  label:'Simple Moving Average (SMA)',     color:'#7FFFD4', desc:'Trend following, customisable periods'},
    {id:'ema',  label:'Exponential Moving Average (EMA)', color:'#cc88ff', desc:'Weighted moving average emphasizing recent data'},
    {id:'bb',   label:'Bollinger Bands (BB)',             color:'#cc88ff', desc:'Volatility bands based on std deviation'},
    {id:'vol',  label:'Volume',                           color:'#00d4ff', desc:'Bar chart of traded volume'},
    {id:'rsi',  label:'Relative Strength Index (RSI)',   color:'#ffcc00', desc:'Momentum oscillator 0-100'},
    {id:'macd', label:'MACD',                             color:'#ff8800', desc:'Moving average convergence divergence'},
    {id:'adx',  label:'Average Directional Index (ADX)', color:'#ff3355', desc:'Trend strength indicator'},
    {id:'sr',   label:'Support / Resistance Levels',     color:'#00ff88', desc:'Auto-detected S/R from price history'},
    {id:'ew',   label:'Elliott Wave (Auto)',               color:'#ffcc00', desc:'Auto-detected 5-wave Elliott Wave pattern'},
    {id:'fii',  label:'Big Players (FII/DII/Inst.)',      color:'#cc88ff', desc:'Bulk/block deals + volume anomaly highlights'},
    {id:'astro',label:'Astro Overlays',                   color:'#00ff88', desc:'Overlay planet coordinates on chart'},
  ];
  el.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid rgba(255,255,255,0.07);">
      <div style="font-size:0.9rem;color:#c8e0ed;letter-spacing:1px;">INDICATORS</div>
      <div style="display:flex;align-items:center;gap:10px;">
        <input placeholder="Search..." oninput="tvFilterInd(this.value)"
          style="background:rgba(0,0,0,0.3);border:1px solid rgba(100,160,200,0.25);color:#c8e0ed;
          padding:4px 10px;font-family:Share Tech Mono,monospace;font-size:0.72rem;outline:none;width:160px;">
        <span onclick="document.getElementById('tv-ind-popup').style.display='none'"
          style="cursor:pointer;color:#4a7090;font-size:1.2rem;line-height:1;">✕</span>
      </div>
    </div>
    <div id="tv-ind-list" style="overflow-y:auto;flex:1;padding:8px 0;">
      ${indList.map(ind => {
        const on = TV.indicators[ind.id];
        return `<div class="tv-ind-row" data-id="${ind.id}" onclick="tvToggleIndFromPopup('${ind.id}')"
          style="display:flex;align-items:center;gap:12px;padding:10px 18px;cursor:pointer;
          border-bottom:1px solid rgba(255,255,255,0.03);transition:background 0.15s;"
          onmouseover="this.style.background='rgba(0,212,255,0.04)'"
          onmouseout="this.style.background='transparent'">
          <div style="width:10px;height:10px;border-radius:50%;background:${ind.color};flex-shrink:0;
            box-shadow:0 0 6px ${ind.color}66;opacity:${on?1:0.3};"></div>
          <div style="flex:1;">
            <div style="font-size:0.75rem;color:${on?'#c8e0ed':'#4a7090'};margin-bottom:2px;">${ind.label}</div>
            <div style="font-size:0.62rem;color:#3a5a70;">${ind.desc}</div>
          </div>
          <div style="font-size:0.62rem;color:${on?ind.color:'#3a5a70'};letter-spacing:1px;">${on?'ON':'OFF'}</div>
          ${!['vol','sr'].includes(ind.id) ? `<div onclick="event.stopPropagation();tvShowSettings('${ind.id}')"
            style="padding:3px 8px;border:1px solid rgba(100,160,200,0.25);color:#4a7090;font-size:0.6rem;cursor:pointer;border-radius:2px;"
            onmouseover="this.style.borderColor='rgba(0,212,255,0.4)';this.style.color='#00d4ff'"
            onmouseout="this.style.borderColor='rgba(100,160,200,0.25)';this.style.color='#4a7090'">⚙</div>` : ''}
        </div>`;
      }).join('')}
    </div>
    <div style="padding:10px 18px;border-top:1px solid rgba(255,255,255,0.07);font-size:0.62rem;color:#3a5a70;">
      Click to toggle · ⚙ to edit parameters · Changes apply immediately
    </div>`;
  el.style.display = 'flex';
}

function tvFilterInd(q) {
  const rows = document.querySelectorAll('.tv-ind-row');
  rows.forEach(r => {
    r.style.display = r.textContent.toLowerCase().includes(q.toLowerCase()) ? 'flex' : 'none';
  });
}

function tvToggleIndFromPopup(id) {
  TV.indicators[id] = !TV.indicators[id];
  tvUpdateIndButton(id);
  // Update popup row
  const row = document.querySelector(`.tv-ind-row[data-id="${id}"]`);
  if (row) {
    const on = TV.indicators[id];
    const dot = row.querySelector('div:first-child');
    const lbl = row.querySelectorAll('div')[2];
    const status = row.querySelector('div:last-child');
    if (dot) dot.style.opacity = on ? '1' : '0.3';
    if (lbl) lbl.style.color = on ? '#c8e0ed' : '#4a7090';
    row.querySelectorAll('div').forEach(d => {
      if (d.textContent === 'ON' || d.textContent === 'OFF') {
        const indColors = {sma:'#7FFFD4',ema:'#cc88ff',bb:'#cc88ff',vol:'#00d4ff',rsi:'#ffcc00',macd:'#ff8800',adx:'#ff3355',sr:'#00ff88',fii:'#cc88ff',astro:'#00ff88'};
        d.textContent = on ? 'ON' : 'OFF';
        d.style.color = on ? (indColors[id]||'#00d4ff') : '#3a5a70';
      }
    });
  }
  // Show/hide sub-panel
  const panels = {vol:'sub-panel-vol',rsi:'sub-panel-rsi',macd:'sub-panel-macd',adx:'sub-panel-adx'};
  if (panels[id]) {
    const p = document.getElementById(panels[id]);
    if (p) p.style.display = TV.indicators[id] ? 'block' : 'none';
  }
  // FII indicator — fetch data when turned on
  if (id === 'fii' && TV.indicators.fii) {
    tvLoadFIIData();
  }
  if (TV.data) tvRedraw();
}

function tvShowSettings(id) {
  let el = document.getElementById('tv-settings-popup');
  if (!el) {
    el = document.createElement('div');
    el.id = 'tv-settings-popup';
    el.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);'
      +'min-width:360px;background:#0d1e2c;border:1px solid rgba(0,212,255,0.25);'
      +'border-radius:4px;z-index:10000;box-shadow:0 20px 60px rgba(0,0,0,0.8);'
      +'font-family:Share Tech Mono,monospace;';
    document.body.appendChild(el);
  }

  const indColors = {sma:'#7FFFD4',ema:'#cc88ff',bb:'#cc88ff',rsi:'#ffcc00',macd:'#ff8800',adx:'#ff3355'};
  const col = indColors[id] || '#00d4ff';

  const fields = {
    sma: [
      {id:'sma-p1', label:'Period 1', val: TV.params.smaP[0], min:2, max:500, step:1},
      {id:'sma-p2', label:'Period 2', val: TV.params.smaP[1], min:2, max:500, step:1},
      {id:'sma-p3', label:'Period 3', val: TV.params.smaP[2], min:2, max:500, step:1},
    ],
    ema: [
      {id:'ema-p1', label:'Period 1', val: TV.params.emaP[0], min:2, max:500, step:1},
      {id:'ema-p2', label:'Period 2', val: TV.params.emaP[1], min:2, max:500, step:1},
      {id:'ema-p3', label:'Period 3', val: TV.params.emaP[2], min:2, max:500, step:1},
    ],
    bb: [
      {id:'bb-period', label:'Length',         val: TV.params.bbP,   min:2,  max:200, step:1},
      {id:'bb-std',    label:'Std Dev',         val: TV.params.bbStd, min:0.1,max:5,   step:0.1},
    ],
    rsi: [
      {id:'rsi-period', label:'Length',          val: TV.params.rsiP,  min:2,  max:100, step:1},
      {id:'rsi-ob',     label:'Overbought',       val: TV.params.rsiOB, min:50, max:90,  step:1},
      {id:'rsi-os',     label:'Oversold',         val: TV.params.rsiOS, min:10, max:50,  step:1},
    ],
    macd: [
      {id:'macd-fast', label:'Fast Length',   val: TV.params.macdFast, min:2,  max:50,  step:1},
      {id:'macd-slow', label:'Slow Length',   val: TV.params.macdSlow, min:2,  max:200, step:1},
      {id:'macd-sig',  label:'Signal Length', val: TV.params.macdSig,  min:2,  max:50,  step:1},
    ],
    adx: [
      {id:'adx-period', label:'ADX Smoothing', val: TV.params.adxP, min:2, max:50, step:1},
    ],
  };

  const names = {sma:'Simple Moving Average',ema:'Exponential Moving Average',bb:'Bollinger Bands',rsi:'RSI',macd:'MACD',adx:'ADX'};

  el.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid rgba(255,255,255,0.07);">
      <div style="font-size:0.82rem;color:${col};letter-spacing:1px;">${names[id]||id.toUpperCase()} — SETTINGS</div>
      <span onclick="document.getElementById('tv-settings-popup').style.display='none'"
        style="cursor:pointer;color:#4a7090;font-size:1.2rem;">✕</span>
    </div>
    <div style="padding:20px 18px;">
      ${(fields[id]||[]).map(f => `
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
          <label style="font-size:0.72rem;color:#7aa8c0;min-width:120px;">${f.label}</label>
          <div style="display:flex;align-items:center;gap:8px;">
            <button onclick="tvAdjustParam('${f.id}',-${f.step})"
              style="width:26px;height:26px;border:1px solid rgba(100,160,200,0.3);background:transparent;color:#7aa8c0;cursor:pointer;font-size:1rem;display:flex;align-items:center;justify-content:center;">−</button>
            <input type="number" id="${f.id}" value="${f.val}" min="${f.min}" max="${f.max}" step="${f.step}"
              oninput="tvUpdateParam('${f.id}')"
              style="width:80px;text-align:center;background:rgba(0,0,0,0.3);border:1px solid rgba(100,160,200,0.25);
              color:#c8e0ed;padding:4px;font-family:Share Tech Mono,monospace;font-size:0.82rem;outline:none;">
            <button onclick="tvAdjustParam('${f.id}',${f.step})"
              style="width:26px;height:26px;border:1px solid rgba(100,160,200,0.3);background:transparent;color:#7aa8c0;cursor:pointer;font-size:1rem;display:flex;align-items:center;justify-content:center;">+</button>
          </div>
        </div>`).join('')}
    </div>
    <div style="display:flex;gap:8px;justify-content:flex-end;padding:12px 18px;border-top:1px solid rgba(255,255,255,0.07);">
      <button onclick="document.getElementById('tv-settings-popup').style.display='none'"
        style="padding:6px 16px;border:1px solid rgba(100,160,200,0.3);background:transparent;color:#7aa8c0;cursor:pointer;font-family:Share Tech Mono,monospace;font-size:0.68rem;">CANCEL</button>
      <button onclick="tvApplySettings('${id}')"
        style="padding:6px 16px;border:1px solid rgba(0,212,255,0.4);background:rgba(0,212,255,0.1);color:#00d4ff;cursor:pointer;font-family:Share Tech Mono,monospace;font-size:0.68rem;">✓ APPLY</button>
    </div>`;
  el.style.display = 'block';
}

function tvAdjustParam(fieldId, delta) {
  const inp = document.getElementById(fieldId);
  if (!inp) return;
  const newVal = parseFloat(inp.value) + delta;
  inp.value = Math.max(parseFloat(inp.min||0), Math.min(parseFloat(inp.max||9999), newVal));
}

function tvUpdateParam(fieldId) {
  // live preview — apply immediately as user types
}

function tvApplySettings(id) {
  const g = id2 => { const el = document.getElementById(id2); return el ? parseFloat(el.value)||0 : 0; };
  if (id==='sma') TV.params.smaP = [g('sma-p1'), g('sma-p2'), g('sma-p3')].map(v=>Math.max(2,v));
  if (id==='ema') TV.params.emaP = [g('ema-p1'), g('ema-p2'), g('ema-p3')].map(v=>Math.max(2,v));
  if (id==='bb')  { TV.params.bbP = Math.max(2,g('bb-period')); TV.params.bbStd = Math.max(0.1,g('bb-std')); }
  if (id==='rsi') { TV.params.rsiP = Math.max(2,g('rsi-period')); TV.params.rsiOB = g('rsi-ob'); TV.params.rsiOS = g('rsi-os'); }
  if (id==='macd'){ TV.params.macdFast = Math.max(2,g('macd-fast')); TV.params.macdSlow = Math.max(2,g('macd-slow')); TV.params.macdSig = Math.max(2,g('macd-sig')); }
  if (id==='adx') TV.params.adxP = Math.max(2,g('adx-period'));
  document.getElementById('tv-settings-popup').style.display = 'none';
  if (TV.data) tvRedraw();
}

function tvUpdateIndButton(id) { /* badges removed — state managed via popup only */ }

function tvToggleChartTypeMenu() {
  const m = document.getElementById('ct-menu');
  if (m) m.style.display = m.style.display === 'none' ? 'block' : 'none';
  // Close on outside click
  setTimeout(() => {
    const close = (e) => {
      const btn = document.getElementById('ct-dropdown-btn');
      if (btn && !btn.contains(e.target)) {
        const m2 = document.getElementById('ct-menu');
        if (m2) m2.style.display = 'none';
        document.removeEventListener('click', close);
      }
    };
    document.addEventListener('click', close);
  }, 10);
}

function setChartType(t) {
  TV.chartType = t;
  // Update dropdown label
  const labels = {candle:'🕯 CANDLE', line:'📈 LINE', bar:'▮▮ OHLC'};
  const lbl = document.getElementById('ct-label');
  if (lbl) lbl.textContent = labels[t] || t.toUpperCase();
  if (TV.data) tvRedraw();
}

function toggleIndicator(id) { tvToggleIndFromPopup(id); }
function toggleIndicatorSettings() { tvShowIndicatorPopup(); }
function applyIndicatorSettings() {}  // no-op, handled per-indicator

window.tvContextAction = function(action) {
  const menu = document.getElementById('tv-context-menu');
  if (menu) menu.style.display = 'none';
  if (action === 'reset') {
    tvResetView();
  } else if (action === 'clear_drawings') {
    tvClearDrawings();
  } else if (action === 'settings') {
    tvShowIndicatorPopup(); // For now, map settings to indicators
  }
};

// ── Canvas setup ──────────────────────────────────────────────────
function tvSetup(id, w, h) {
  const c = document.getElementById(id);
  if (!c) return null;
  c.width  = w;
  c.height = h;
  c.style.height = h + 'px';
  const ctx = c.getContext('2d');
  ctx.fillStyle='#060f16'; ctx.fillRect(0,0,w,h);
  return ctx;
}

// ── Drawing tools ─────────────────────────────────────────────────
TV.tool = 'cursor';      // active tool
TV.editDrag = null;    // {drawingIdx, handle:'p1'|'p2'|'body', startX, startY, origDrawing}
TV.selectedDrawing = null; // index of selected drawing (-1 = none)
TV.drawings = [];        // [{type, points:[{x,y,price,barIdx}], color, ...}]
TV.drawState = null;     // in-progress drawing
TV.magnet = false;
TV.stayInDrawingMode = false;
TV.lockDrawings = false;
TV.drawingsHidden = false;
TV.astroOverlays = { planets: { Sun: true, Moon: true, Mercury: true, Venus: true, Mars: true, Jupiter: true, Saturn: true, Rahu: false, Ketu: false }, coord: 'longitude', aspects: false, nakshatra: false };
TV.indicators = TV.indicators || { sma: true, ema: false, astro: false };
TV.indicatorSettings = TV.indicatorSettings || { smaP: [20, 50, 200], emaP: [9, 21, 50] };
TV.ephemerisData = null;

function tvSetTool(t) {
  TV.tool = t;
  const cvs = document.getElementById('price-canvas');
  const tip = document.getElementById('tv-draw-tip');
  // Update toolbar button highlight
  document.querySelectorAll('[id^="tv-tool-"]').forEach(b => {
    b.style.background = 'transparent';
    b.style.borderColor = 'rgba(100,160,200,0.2)';
    b.style.color = '#6a8fa8';
  });
  const activeBtn = document.getElementById('tv-tool-'+t);
  if (activeBtn) {
    activeBtn.style.background = 'rgba(0,212,255,0.12)';
    activeBtn.style.borderColor = 'var(--cyan)';
    activeBtn.style.color = 'var(--cyan)';
  }
  if (cvs) cvs.style.cursor = 'crosshair';
  TV.drawState = null;
  // Show tip
  const tips = {
    trendline: 'Click start point, click end point',
    ray: 'Click start point, click second point to cast ray',
    infoline: 'Click start point, click end point to measure trend',
    extline: 'Click first point, click second point to extend line',
    hline: 'Click to place horizontal line',
    hray: 'Click to place horizontal ray',
    vline: 'Click to place vertical line',
    crossline: 'Click to place cross lines',
    fib: 'Click high point, click low point',
    fibext: 'Click wave start, wave peak, and retracement low',
    fibtz: 'Click start point, click second point for timezone spacing',
    gannbox: 'Click start corner, click end corner',
    gannfan: 'Click start point, click second point to project fan',
    brush: 'Click and drag to draw freehand',
    rect: 'Click start corner, click end corner',
    ellipse: 'Click start, drag to define bounding ellipse',
    triangle: 'Click three points to draw triangle',
    text: 'Click to place text label',
    xabcd: 'Click 5 points to draw X-A-B-C-D pattern',
    hns: 'Click 5 points (Left, Neck1, Head, Neck2, Right)',
    ewimpulse: 'Click 6 points (0, 1, 2, 3, 4, 5) to label wave',
    measure: 'Click start, click end to measure price range',
    longpos: 'Click entry point, drag to adjust target/stop loss',
    shortpos: 'Click entry point, drag to adjust target/stop loss',
    eraser: 'Click on any drawing to erase it'
  };
  if (tip) { tip.textContent = tips[t]||''; tip.style.display = tips[t] ? 'block' : 'none'; }
}

function tvSaveChartState() {
  const state = {
    drawings: TV.drawings,
    magnet: TV.magnet,
    stayInDrawingMode: TV.stayInDrawingMode,
    lockDrawings: TV.lockDrawings,
    drawingsHidden: TV.drawingsHidden,
    indicators: TV.indicators,
    indicatorSettings: TV.indicatorSettings,
    astroOverlays: TV.astroOverlays
  };
  localStorage.setItem('tvExtendedChartState_' + (TV.symbol || 'default'), JSON.stringify(state));
}

function tvLoadChartState() {
  try {
    const loaded = JSON.parse(localStorage.getItem('tvExtendedChartState_' + (TV.symbol || 'default')) || 'null');
    if (loaded) {
      if (loaded.drawings) TV.drawings = loaded.drawings;
      if (loaded.magnet !== undefined) TV.magnet = loaded.magnet;
      if (loaded.stayInDrawingMode !== undefined) TV.stayInDrawingMode = loaded.stayInDrawingMode;
      if (loaded.lockDrawings !== undefined) TV.lockDrawings = loaded.lockDrawings;
      if (loaded.drawingsHidden !== undefined) TV.drawingsHidden = loaded.drawingsHidden;
      if (loaded.indicators !== undefined) TV.indicators = loaded.indicators;
      if (loaded.indicatorSettings !== undefined) TV.indicatorSettings = loaded.indicatorSettings;
      if (loaded.astroOverlays !== undefined) TV.astroOverlays = loaded.astroOverlays;
    }
  } catch (e) {
    console.error('Failed to load chart state', e);
  }
}

function tvClearDrawings() {
  TV.drawings = []; TV.drawState = null;
  tvSaveChartState();
  if (TV.data) tvRedraw();
  tvUpdateObjectTree();
}

function tvUpdateObjectTree() {
  const container = document.getElementById('tv-object-tree-list');
  if (!container) return;
  container.innerHTML = '';
  if (!TV.drawings || !TV.drawings.length) {
    container.innerHTML = '<div style="color:#6a8fa8;padding:12px;font-size:0.85rem;text-align:center;">No drawings on chart.</div>';
    return;
  }
  TV.drawings.forEach((d, idx) => {
    const item = document.createElement('div');
    item.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:6px 12px;border-bottom:1px solid rgba(100,160,200,0.1);font-family:Share Tech Mono,monospace;font-size:0.85rem;color:#c8e0ed;';
    const nameMap = {
      trendline: 'Trendline', ray: 'Ray', infoline: 'Info Line', extline: 'Extended Line',
      hline: 'Horizontal Line', hray: 'Horizontal Ray', vline: 'Vertical Line', crossline: 'Cross Line',
      fib: 'Fib Retracement', fibext: 'Fib Extension', fibtz: 'Fib Time Zone',
      gannbox: 'Gann Box', gannfan: 'Gann Fan', brush: 'Brush', rect: 'Rectangle',
      ellipse: 'Ellipse', triangle: 'Triangle', text: 'Text Label', xabcd: 'XABCD Pattern',
      hns: 'Head & Shoulders', ewimpulse: 'Elliott Wave', longpos: 'Long Position', shortpos: 'Short Position'
    };
    const name = nameMap[d.type] || d.type;
    const isSelected = TV.selectedDrawing === idx;
    item.style.background = isSelected ? 'rgba(0,212,255,0.08)' : 'transparent';
    item.innerHTML = `
      <span style="flex:1;cursor:pointer;${isSelected?'color:var(--cyan);font-weight:bold;':''}" onclick="TV.selectedDrawing = (TV.selectedDrawing === ${idx}) ? null : ${idx}; tvRedraw(); tvUpdateObjectTree();">${name} [${idx}]</span>
      <div style="display:flex;gap:8px;align-items:center;">
        <button style="background:transparent;border:none;color:#6a8fa8;cursor:pointer;font-size:0.9rem;" title="Toggle Visibility" onclick="event.stopPropagation(); TV.drawings[${idx}].hidden = !TV.drawings[${idx}].hidden; tvRedraw(); this.innerHTML = TV.drawings[${idx}].hidden ? '👁️‍🗨️' : '👁️';">${d.hidden ? '👁️‍🗨️' : '👁️'}</button>
        <button style="background:transparent;border:none;color:#ef5350;cursor:pointer;font-size:0.9rem;" title="Delete" onclick="event.stopPropagation(); TV.drawings.splice(${idx}, 1); TV.selectedDrawing = null; tvSaveChartState(); tvRedraw(); tvUpdateObjectTree();">✕</button>
      </div>
    `;
    container.appendChild(item);
  });
}

const TV_PAD = {t:28, r:68, b:26, l:8};

function tvPxToPrice(yPx) {
  const cvs = document.getElementById('price-canvas');
  if (!cvs) return 0;
  const {minV, maxV} = tvGetYRange();
  const cH = cvs.height - TV_PAD.t - TV_PAD.b;
  return maxV - (yPx - TV_PAD.t) / cH * (maxV - minV);
}

function tvPxToBarIdx(xPx) {
  const cvs = document.getElementById('price-canvas');
  if (!cvs || !TV.data) return -1;
  const cW = cvs.width - TV_PAD.l - TV_PAD.r;
  const N = TV.view.end - TV.view.start;
  const slotW = cW / N;
  const i = (xPx - TV_PAD.l) / slotW - 0.5;
  return TV.view.start + Math.max(0, Math.min(N-1, Math.round(i)));
}

function tvBarToPrice(barIdx, yPx) { return tvPxToPrice(yPx); }

function tvSnapToOHLC(barIdx, price) {
  if (!TV.magnet || !TV.data || barIdx < 0 || barIdx >= TV.data.closes.length) return price;
  const o = TV.data.opens[barIdx];
  const h = TV.data.highs[barIdx];
  const l = TV.data.lows[barIdx];
  const c = TV.data.closes[barIdx];
  const levels = [o, h, l, c].filter(v => v !== undefined && v !== null);
  if (!levels.length) return price;
  let best = price;
  let minDist = Infinity;
  levels.forEach(v => {
    const dist = Math.abs(v - price);
    if (dist < minDist) {
      minDist = dist;
      best = v;
    }
  });
  return best;
}

function tvEraseDrawingAt(xPx, yPx) {
  const cvs = document.getElementById('price-canvas');
  if (!cvs) return;
  const {start, end} = TV.view;
  const N = end - start;
  const cW = cvs.width - TV_PAD.l - TV_PAD.r;
  const slotW = cW / N;
  const xOf = i => TV_PAD.l + (i - start + 0.5) * slotW;
  const {minV, maxV} = tvGetYRange();
  const cH = cvs.height - TV_PAD.t - TV_PAD.b;
  const yOf = v => TV_PAD.t + cH * (1 - (v - minV) / (maxV - minV));
  const THRESH = 15;

  let best = null, bestDist = Infinity;
  TV.drawings.forEach((d, idx) => {
    let dist = Infinity;
    if (d.type === 'hline') {
      const y = yOf(d.price); dist = Math.abs(yPx - y);
    } else if (d.type === 'vline') {
      const x = xOf(d.barIdx); dist = Math.abs(xPx - x);
    } else if ((d.type === 'trendline' || d.type === 'ray' || d.type === 'infoline' || d.type === 'extline' || d.type === 'hray' || d.type === 'fib' || d.type === 'fibext') && d.p2) {
      const x1=xOf(d.p1.barIdx),y1=yOf(d.p1.price),x2=xOf(d.p2.barIdx),y2=yOf(d.p2.price);
      const len=Math.hypot(x2-x1,y2-y1);
      if(len>0) dist=Math.abs((y2-y1)*xPx-(x2-x1)*yPx+x2*y1-y2*x1)/len;
    } else if ((d.type === 'rect' || d.type === 'gannbox' || d.type === 'ellipse' || d.type === 'longpos' || d.type === 'shortpos') && d.p2) {
      const x1=xOf(d.p1.barIdx),y1=yOf(d.p1.price),x2=xOf(d.p2.barIdx),y2=yOf(d.p2.price);
      const inX=xPx>=Math.min(x1,x2)-THRESH&&xPx<=Math.max(x1,x2)+THRESH;
      const inY=yPx>=Math.min(y1,y2)-THRESH&&yPx<=Math.max(y1,y2)+THRESH;
      if(inX&&inY) dist=0;
    } else if (d.type === 'triangle' && d.points && d.points.length === 3) {
      const pts = d.points;
      const d1 = Math.hypot(xPx - xOf(pts[0].barIdx), yPx - yOf(pts[0].price));
      const d2 = Math.hypot(xPx - xOf(pts[1].barIdx), yPx - yOf(pts[1].price));
      const d3 = Math.hypot(xPx - xOf(pts[2].barIdx), yPx - yOf(pts[2].price));
      dist = Math.min(d1, d2, d3);
    } else if (d.type === 'brush' && d.points) {
      d.points.forEach(pt => {
        const d_pt = Math.hypot(xPx - xOf(pt.barIdx), yPx - yOf(pt.price));
        if (d_pt < dist) dist = d_pt;
      });
    }
    if (dist < bestDist) { bestDist = dist; best = idx; }
  });

  if (best !== null && bestDist < THRESH) {
    TV.drawings.splice(best, 1);
    TV.selectedDrawing = null;
    tvSaveChartState();
    tvRedraw();
    tvUpdateObjectTree();
  }
}

function tvHandleDrawClick(xPx, yPx) {
  if (TV.lockDrawings) return;
  if (TV.tool === 'cursor') {
    tvSelectDrawingAt(xPx, yPx);
    return;
  }
  if (TV.tool === 'eraser') {
    tvEraseDrawingAt(xPx, yPx);
    return;
  }

  const rawPrice = tvPxToPrice(yPx);
  const barIdx = tvPxToBarIdx(xPx);
  const price = tvSnapToOHLC(barIdx, rawPrice);
  let finalYPx = yPx;
  if (TV.magnet && TV.data) {
    const {minV, maxV} = tvGetYRange();
    const cvs = document.getElementById('price-canvas');
    if (cvs) {
      const cH = cvs.height - TV_PAD.t - TV_PAD.b;
      finalYPx = TV_PAD.t + cH * (1 - (price - minV) / (maxV - minV));
    }
  }

  const pt = {xPx, yPx: finalYPx, price, barIdx};
  const colors = {
    trendline:'#2962ff', ray:'#2962ff', infoline:'#ff9800', extline:'#2962ff',
    hline:'#2a9d8f', hray:'#2a9d8f', vline:'rgba(197,203,206,0.5)', crossline:'#e76f51',
    rect:'rgba(41,98,255,0.15)', fib:'#7e57c2', fibext:'#9c27b0', fibtz:'#3f51b5',
    gannbox:'rgba(0,150,136,0.15)', gannfan:'#009688', brush:'#4caf50',
    ellipse:'rgba(233,30,99,0.15)', triangle:'rgba(156,39,176,0.15)',
    text:'#eceff1', xabcd:'rgba(255,152,0,0.15)', hns:'rgba(3,169,244,0.15)',
    ewimpulse:'rgba(7,169,244,0.15)', longpos:'rgba(76,175,80,0.15)', shortpos:'rgba(244,67,54,0.15)',
    measure:'rgba(41,98,255,0.2)'
  };
  const col = colors[TV.tool] || '#2962ff';

  if (TV.tool === 'hline') {
    TV.drawings.push({type:'hline', price, color:col, id:Date.now()});
    tvSaveChartState();
    tvRedraw();
    tvUpdateObjectTree();
    if (!TV.stayInDrawingMode) tvSetTool('cursor');
    return;
  }
  if (TV.tool === 'vline') {
    TV.drawings.push({type:'vline', barIdx, color:col, id:Date.now()});
    tvSaveChartState();
    tvRedraw();
    tvUpdateObjectTree();
    if (!TV.stayInDrawingMode) tvSetTool('cursor');
    return;
  }
  if (TV.tool === 'crossline') {
    TV.drawings.push({type:'hline', price, color:col, id:Date.now()}, {type:'vline', barIdx, color:col, id:Date.now()});
    tvSaveChartState();
    tvRedraw();
    tvUpdateObjectTree();
    if (!TV.stayInDrawingMode) tvSetTool('cursor');
    return;
  }

  if (TV.tool === 'text') {
    tvShowTextInput(xPx, finalYPx, price, barIdx);
    return;
  }

  if (TV.tool === 'brush') {
    return;
  }

  if (TV.tool === 'triangle') {
    if (!TV.drawState) {
      TV.drawState = {type:'triangle', points:[pt], color:col};
      tvRedraw();
    } else if (TV.drawState.points.length === 1) {
      TV.drawState.points.push(pt);
      tvRedraw();
    } else {
      TV.drawings.push({...TV.drawState, points:[...TV.drawState.points, pt], id:Date.now()});
      TV.drawState = null;
      tvSaveChartState();
      tvRedraw();
      tvUpdateObjectTree();
      if (!TV.stayInDrawingMode) tvSetTool('cursor');
    }
    return;
  }

  if (TV.tool === 'fibext') {
    if (!TV.drawState) {
      TV.drawState = {type:'fibext', points:[pt], color:col};
      tvRedraw();
    } else if (TV.drawState.points.length === 1) {
      TV.drawState.points.push(pt);
      tvRedraw();
    } else {
      TV.drawings.push({...TV.drawState, points:[...TV.drawState.points, pt], id:Date.now()});
      TV.drawState = null;
      tvSaveChartState();
      tvRedraw();
      tvUpdateObjectTree();
      if (!TV.stayInDrawingMode) tvSetTool('cursor');
    }
    return;
  }

  if (['xabcd', 'hns'].includes(TV.tool)) {
    if (!TV.drawState) {
      TV.drawState = {type:TV.tool, points:[pt], color:col};
      tvRedraw();
    } else if (TV.drawState.points.length < 4) {
      TV.drawState.points.push(pt);
      tvRedraw();
    } else {
      TV.drawings.push({...TV.drawState, points:[...TV.drawState.points, pt], id:Date.now()});
      TV.drawState = null;
      tvSaveChartState();
      tvRedraw();
      tvUpdateObjectTree();
      if (!TV.stayInDrawingMode) tvSetTool('cursor');
    }
    return;
  }

  if (TV.tool === 'ewimpulse') {
    if (!TV.drawState) {
      TV.drawState = {type:'ewimpulse', points:[pt], color:col};
      tvRedraw();
    } else if (TV.drawState.points.length < 5) {
      TV.drawState.points.push(pt);
      tvRedraw();
    } else {
      TV.drawings.push({...TV.drawState, points:[...TV.drawState.points, pt], id:Date.now()});
      TV.drawState = null;
      tvSaveChartState();
      tvRedraw();
      tvUpdateObjectTree();
      if (!TV.stayInDrawingMode) tvSetTool('cursor');
    }
    return;
  }

  if (TV.tool === 'measure') {
    if (!TV.drawState) {
      TV.drawState = {type:'measure', p1:pt, color:col};
      tvRedraw();
    } else {
      TV.measureResult = {p1:TV.drawState.p1, p2:pt};
      TV.drawState = null;
      tvRedraw();
    }
    return;
  }

  if (!TV.drawState) {
    TV.drawState = {type:TV.tool, p1:pt, color:col};
    tvRedraw();
  } else {
    TV.drawings.push({...TV.drawState, p2:pt, id:Date.now()});
    TV.drawState = null;
    tvSaveChartState();
    tvRedraw();
    tvUpdateObjectTree();
    if (!TV.stayInDrawingMode) tvSetTool('cursor');
  }
}

function tvShowTextInput(xPx, yPx, price, barIdx) {
  const existing = document.getElementById('tv-text-input-wrap');
  if (existing) existing.remove();

  const cvs = document.getElementById('price-canvas');
  if (!cvs) return;
  const parent = cvs.parentElement;
  const rect = cvs.getBoundingClientRect();
  const scaleX = rect.width / cvs.width;
  const scaleY = rect.height / cvs.height;

  const wrap = document.createElement('div');
  wrap.id = 'tv-text-input-wrap';
  wrap.style.cssText = `position:absolute;left:${xPx*scaleX}px;top:${yPx*scaleY - 14}px;z-index:200;`;

  const inp = document.createElement('input');
  inp.type = 'text';
  inp.placeholder = 'Type label...';
  inp.style.cssText = 'background:#ffffff;border:1px solid #2962ff;color:#131722;'
    + 'font-family:-apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif;font-size:12px;padding:4px 8px;outline:none;'
    + 'min-width:100px;border-radius:4px;box-shadow:0 2px 5px rgba(0,0,0,0.1);';

  const commit = () => {
    const val = inp.value.trim();
    wrap.remove();
    if (val) {
      TV.drawings.push({type:'text', barIdx, price, text:val, color:'#ffffff', id:Date.now()});
      tvSaveChartState();
      tvRedraw();
      tvUpdateObjectTree();
    }
    if (!TV.stayInDrawingMode) tvSetTool('cursor');
  };

  inp.addEventListener('keydown', e => {
    if (e.key === 'Enter') commit();
    if (e.key === 'Escape') { wrap.remove(); tvSetTool('cursor'); }
  });
  inp.addEventListener('blur', commit);

  wrap.appendChild(inp);
  parent.style.position = 'relative';
  parent.appendChild(wrap);
  inp.focus();
}

function tvSelectDrawingAt(xPx, yPx) {
  const cvs = document.getElementById('price-canvas');
  if (!cvs) return;
  const {start, end} = TV.view;
  const N = end - start;
  const cW = cvs.width - TV_PAD.l - TV_PAD.r;
  const slotW = cW / N;
  const xOf = i => TV_PAD.l + (i - start + 0.5) * slotW;
  const {minV, maxV} = tvGetYRange();
  const cH = cvs.height - TV_PAD.t - TV_PAD.b;
  const yOf = v => TV_PAD.t + cH * (1 - (v - minV) / (maxV - minV));
  const THRESH = 12; // px hit threshold

  let best = null, bestDist = Infinity;
  TV.drawings.forEach((d, idx) => {
    if (d.hidden) return;
    let dist = Infinity;
    if (d.type === 'hline') {
      dist = Math.abs(yPx - yOf(d.price));
    } else if (d.type === 'vline') {
      dist = Math.abs(xPx - xOf(d.barIdx));
    } else if (d.type === 'hray' && d.p1) {
      const x1 = xOf(d.p1.barIdx), y1 = yOf(d.p1.price);
      if (xPx >= x1 - THRESH) dist = Math.abs(yPx - y1);
    } else if ((d.type === 'trendline' || d.type === 'fib' || d.type === 'infoline') && d.p2) {
      const x1 = xOf(d.p1.barIdx), y1 = yOf(d.p1.price);
      const x2 = xOf(d.p2.barIdx), y2 = yOf(d.p2.price);
      const len = Math.hypot(x2 - x1, y2 - y1);
      if (len > 0) {
        const dx = x2 - x1, dy = y2 - y1;
        const t = Math.max(0, Math.min(1, ((xPx - x1) * dx + (yPx - y1) * dy) / (dx * dx + dy * dy)));
        dist = Math.hypot(xPx - (x1 + t * dx), yPx - (y1 + t * dy));
      }
    } else if (d.type === 'ray' && d.p2) {
      const x1 = xOf(d.p1.barIdx), y1 = yOf(d.p1.price);
      const x2 = xOf(d.p2.barIdx), y2 = yOf(d.p2.price);
      const len = Math.hypot(x2 - x1, y2 - y1);
      if (len > 0) {
        const dx = x2 - x1, dy = y2 - y1;
        const t = Math.max(0, ((xPx - x1) * dx + (yPx - y1) * dy) / (dx * dx + dy * dy));
        dist = Math.hypot(xPx - (x1 + t * dx), yPx - (y1 + t * dy));
      }
    } else if (d.type === 'extline' && d.p2) {
      const x1 = xOf(d.p1.barIdx), y1 = yOf(d.p1.price);
      const x2 = xOf(d.p2.barIdx), y2 = yOf(d.p2.price);
      const len = Math.hypot(x2 - x1, y2 - y1);
      if (len > 0) {
        dist = Math.abs((y2 - y1) * xPx - (x2 - x1) * yPx + x2 * y1 - y2 * x1) / len;
      }
    } else if ((d.type === 'rect' || d.type === 'gannbox') && d.p2) {
      const x1 = xOf(d.p1.barIdx), y1 = yOf(d.p1.price);
      const x2 = xOf(d.p2.barIdx), y2 = yOf(d.p2.price);
      const minX = Math.min(x1, x2), maxX = Math.max(x1, x2);
      const minY = Math.min(y1, y2), maxY = Math.max(y1, y2);
      const inX = xPx >= minX - THRESH && xPx <= maxX + THRESH;
      const inY = yPx >= minY - THRESH && yPx <= maxY + THRESH;
      if (inX && inY) {
        const onBorderX = Math.abs(xPx - minX) <= THRESH || Math.abs(xPx - maxX) <= THRESH;
        const onBorderY = Math.abs(yPx - minY) <= THRESH || Math.abs(yPx - maxY) <= THRESH;
        if (onBorderX || onBorderY) dist = 0;
      }
    } else if (d.type === 'ellipse' && d.p2) {
      const x1 = xOf(d.p1.barIdx), y1 = yOf(d.p1.price);
      const x2 = xOf(d.p2.barIdx), y2 = yOf(d.p2.price);
      const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;
      const rx = Math.abs(x2 - x1) / 2, ry = Math.abs(y2 - y1) / 2;
      if (rx > 0 && ry > 0) {
        const dx = xPx - cx, dy = yPx - cy;
        const norm = Math.hypot(dx / rx, dy / ry);
        dist = Math.abs(norm - 1) * Math.min(rx, ry);
      }
    } else if (['triangle', 'xabcd', 'hns', 'ewimpulse'].includes(d.type) && d.points) {
      for (let i = 0; i < d.points.length - 1; i++) {
        const x1 = xOf(d.points[i].barIdx), y1 = yOf(d.points[i].price);
        const x2 = xOf(d.points[i+1].barIdx), y2 = yOf(d.points[i+1].price);
        const dx = x2 - x1, dy = y2 - y1;
        const len2 = dx * dx + dy * dy;
        if (len2 > 0) {
          const t = Math.max(0, Math.min(1, ((xPx - x1) * dx + (yPx - y1) * dy) / len2));
          const sd = Math.hypot(xPx - (x1 + t * dx), yPx - (y1 + t * dy));
          if (sd < dist) dist = sd;
        }
      }
      if (d.type === 'triangle' && d.points.length >= 3) {
        const x1 = xOf(d.points[2].barIdx), y1 = yOf(d.points[2].price);
        const x2 = xOf(d.points[0].barIdx), y2 = yOf(d.points[0].price);
        const dx = x2 - x1, dy = y2 - y1;
        const len2 = dx * dx + dy * dy;
        if (len2 > 0) {
          const t = Math.max(0, Math.min(1, ((xPx - x1) * dx + (yPx - y1) * dy) / len2));
          const sd = Math.hypot(xPx - (x1 + t * dx), yPx - (y1 + t * dy));
          if (sd < dist) dist = sd;
        }
      }
    } else if ((d.type === 'longpos' || d.type === 'shortpos') && d.p2) {
      const x1 = xOf(d.p1.barIdx), y1 = yOf(d.p1.price);
      const x2 = xOf(d.p2.barIdx), y2 = yOf(d.p2.price);
      const minX = Math.min(x1, x2), maxX = Math.max(x1, x2);
      const minY = Math.min(y1, y2), maxY = Math.max(y1, y2);
      const inX = xPx >= minX - THRESH && xPx <= maxX + THRESH;
      const inY = yPx >= minY - THRESH && yPx <= maxY + THRESH;
      if (inX && inY) dist = 0;
    } else if (d.type === 'text') {
      const x = xOf(d.barIdx), y = yOf(d.price);
      dist = Math.hypot(xPx - x, yPx - y);
    } else if (d.type === 'gannfan' && d.p2) {
      const x1 = xOf(d.p1.barIdx), y1 = yOf(d.p1.price);
      const x2 = xOf(d.p2.barIdx), y2 = yOf(d.p2.price);
      const dx = x2 - x1, dy = y2 - y1;
      const slopes = [1/8, 1/4, 1/3, 1/2, 1, 2, 3, 4, 8];
      slopes.forEach(s => {
        const rx1 = dx, ry1 = dy * s;
        const len1 = Math.hypot(rx1, ry1);
        if (len1 > 0) {
          const t1 = Math.max(0, ((xPx - x1) * rx1 + (yPx - y1) * ry1) / (len1 * len1));
          const d1 = Math.hypot(xPx - (x1 + t1 * rx1), yPx - (y1 + t1 * ry1));
          if (d1 < dist) dist = d1;
        }
        const rx2 = dx * s, ry2 = dy;
        const len2 = Math.hypot(rx2, ry2);
        if (len2 > 0) {
          const t2 = Math.max(0, ((xPx - x1) * rx2 + (yPx - y1) * ry2) / (len2 * len2));
          const d2 = Math.hypot(xPx - (x1 + t2 * rx2), yPx - (y1 + t2 * ry2));
          if (d2 < dist) dist = d2;
        }
      });
    } else if (d.type === 'fibext' && d.points && d.points.length >= 3) {
      const pts = d.points;
      const x1 = xOf(pts[0].barIdx), y1 = yOf(pts[0].price);
      const x2 = xOf(pts[1].barIdx), y2 = yOf(pts[1].price);
      const x3 = xOf(pts[2].barIdx), y3 = yOf(pts[2].price);
      const segs = [[x1, y1, x2, y2], [x2, y2, x3, y3]];
      segs.forEach(([sx1, sy1, sx2, sy2]) => {
        const sdx = sx2 - sx1, sdy = sy2 - sy1;
        const slen2 = sdx * sdx + sdy * sdy;
        if (slen2 > 0) {
          const t = Math.max(0, Math.min(1, ((xPx - sx1) * sdx + (yPx - sy1) * sdy) / slen2));
          const sd = Math.hypot(xPx - (sx1 + t * sdx), yPx - (sy1 + t * sdy));
          if (sd < dist) dist = sd;
        }
      });
      const range = pts[1].price - pts[0].price;
      const levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.618, 2.618];
      if (xPx >= x3 - THRESH) {
        levels.forEach(l => {
          const price = pts[2].price + l * range;
          const y = yOf(price);
          const yd = Math.abs(yPx - y);
          if (yd < dist) dist = yd;
        });
      }
    } else if (d.type === 'fibtz' && d.p2) {
      const idx1 = d.p1.barIdx;
      const idx2 = d.p2.barIdx;
      const D = Math.max(1, Math.abs(idx2 - idx1));
      const fibs = [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233];
      fibs.forEach(f => {
        const x = xOf(idx1 + f * D);
        const xd = Math.abs(xPx - x);
        if (xd < dist) dist = xd;
      });
    } else if (d.type === 'brush' && d.points) {
      for (let i = 0; i < d.points.length - 1; i++) {
        const x1 = xOf(d.points[i].barIdx), y1 = yOf(d.points[i].price);
        const x2 = xOf(d.points[i+1].barIdx), y2 = yOf(d.points[i+1].price);
        const dx = x2 - x1, dy = y2 - y1;
        const len2 = dx * dx + dy * dy;
        if (len2 > 0) {
          const t = Math.max(0, Math.min(1, ((xPx - x1) * dx + (yPx - y1) * dy) / len2));
          const sd = Math.hypot(xPx - (x1 + t * dx), yPx - (y1 + t * dy));
          if (sd < dist) dist = sd;
        }
      }
    }
    if (dist < bestDist) { bestDist = dist; best = idx; }
  });

  if (best !== null && bestDist < THRESH) {
    TV.selectedDrawing = (TV.selectedDrawing === best) ? null : best;
  } else {
    TV.selectedDrawing = null;
  }
  tvRedraw();
}

function tvDrawAllDrawings(ctx, W, H, PAD, xOf, yOf) {
  if (TV.drawingsHidden) return;
  const {minV, maxV} = tvGetYRange();
  const {start, end} = TV.view;
  const N = end - start;
  const cW = W - PAD.l - PAD.r, cH = H - PAD.t - PAD.b;

  TV.drawings.forEach((d, idx) => {
    if (d.hidden) return;
    ctx.save();
    const isSelected = (TV.selectedDrawing === idx);
    const selGlow = isSelected ? 3 : 0;
    
    ctx.strokeStyle = d.color;
    ctx.lineWidth = isSelected ? 2.5 : 1.2;
    ctx.fillStyle = d.color;

    if (d.type === 'hline') {
      if (d.price < minV || d.price > maxV) { ctx.restore(); return; }
      const y = yOf(d.price);
      if (isSelected) { ctx.strokeStyle='rgba(255,255,255,0.4)'; ctx.lineWidth=4; ctx.beginPath(); ctx.moveTo(PAD.l,y); ctx.lineTo(W-PAD.r,y); ctx.stroke(); }
      ctx.strokeStyle = d.color; ctx.lineWidth = isSelected?2:1; ctx.setLineDash([5,3]);
      ctx.beginPath(); ctx.moveTo(PAD.l, y); ctx.lineTo(W-PAD.r, y); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = d.color; ctx.font = '9px Share Tech Mono'; ctx.textAlign = 'left';
      ctx.fillText(d.price.toFixed(2), W-PAD.r+3, y+3);
      if (isSelected) { ctx.fillStyle='rgba(255,51,85,0.8)'; ctx.font='11px Share Tech Mono'; ctx.fillText('✕', W-PAD.r-16, y+4); }
    }
    else if (d.type === 'vline') {
      const i = d.barIdx - start;
      if (i < 0 || i >= N) { ctx.restore(); return; }
      const x = xOf(i);
      if (isSelected) { ctx.strokeStyle='rgba(255,255,255,0.4)'; ctx.lineWidth=3; ctx.beginPath(); ctx.moveTo(x,PAD.t); ctx.lineTo(x,PAD.t+cH); ctx.stroke(); }
      ctx.strokeStyle = d.color; ctx.lineWidth = 1; ctx.setLineDash([5,3]);
      ctx.beginPath(); ctx.moveTo(x, PAD.t); ctx.lineTo(x, PAD.t+cH); ctx.stroke();
      ctx.setLineDash([]);
    }
    else if (d.type === 'trendline' && d.p2) {
      const x1 = xOf(d.p1.barIdx), y1 = yOf(d.p1.price);
      const x2 = xOf(d.p2.barIdx), y2 = yOf(d.p2.price);
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
      ctx.beginPath(); ctx.arc(x1, y1, 3, 0, Math.PI*2); ctx.fill();
      ctx.beginPath(); ctx.arc(x2, y2, 3, 0, Math.PI*2); ctx.fill();
    }
    else if (d.type === 'ray' && d.p2) {
      const x1 = xOf(d.p1.barIdx), y1 = yOf(d.p1.price);
      const x2 = xOf(d.p2.barIdx), y2 = yOf(d.p2.price);
      const dx = x2 - x1, dy = y2 - y1;
      let tx = W - PAD.r;
      if (dx < 0) tx = PAD.l;
      const ty = dx !== 0 ? y1 + (dy / dx) * (tx - x1) : y2;
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(tx, ty); ctx.stroke();
      ctx.beginPath(); ctx.arc(x1, y1, 3, 0, Math.PI*2); ctx.fill();
      ctx.beginPath(); ctx.arc(x2, y2, 3, 0, Math.PI*2); ctx.fill();
    }
    else if (d.type === 'infoline' && d.p2) {
      const x1 = xOf(d.p1.barIdx), y1 = yOf(d.p1.price);
      const x2 = xOf(d.p2.barIdx), y2 = yOf(d.p2.price);
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
      ctx.beginPath(); ctx.arc(x1, y1, 3, 0, Math.PI*2); ctx.fill();
      ctx.beginPath(); ctx.arc(x2, y2, 3, 0, Math.PI*2); ctx.fill();
      
      const midX = (x1 + x2) / 2;
      const midY = (y1 + y2) / 2;
      const barDiff = d.p2.barIdx - d.p1.barIdx;
      const priceDiff = d.p2.price - d.p1.price;
      const pct = d.p1.price !== 0 ? (priceDiff / d.p1.price * 100).toFixed(2) : '0.00';
      const txt = `${barDiff} bars | Diff: ${priceDiff.toFixed(2)} (${pct}%)`;
      ctx.font = '9px Share Tech Mono';
      const tw = ctx.measureText(txt).width + 10;
      ctx.fillStyle = 'rgba(10, 24, 32, 0.85)';
      ctx.fillRect(midX - tw/2, midY - 6, tw, 14);
      ctx.strokeStyle = d.color; ctx.strokeRect(midX - tw/2, midY - 6, tw, 14);
      ctx.fillStyle = '#ffffff'; ctx.textAlign = 'center'; ctx.fillText(txt, midX, midY + 4);
    }
    else if (d.type === 'extline' && d.p2) {
      const x1 = xOf(d.p1.barIdx), y1 = yOf(d.p1.price);
      const x2 = xOf(d.p2.barIdx), y2 = yOf(d.p2.price);
      const dx = x2 - x1, dy = y2 - y1;
      if (dx !== 0) {
        const yL = y1 + (dy / dx) * (PAD.l - x1);
        const yR = y1 + (dy / dx) * (W - PAD.r - x1);
        ctx.beginPath(); ctx.moveTo(PAD.l, yL); ctx.lineTo(W - PAD.r, yR); ctx.stroke();
      } else {
        ctx.beginPath(); ctx.moveTo(x1, PAD.t); ctx.lineTo(x1, H - PAD.b); ctx.stroke();
      }
      ctx.beginPath(); ctx.arc(x1, y1, 3, 0, Math.PI*2); ctx.fill();
      ctx.beginPath(); ctx.arc(x2, y2, 3, 0, Math.PI*2); ctx.fill();
    }
    else if (d.type === 'hray' && d.p2) {
      const x1 = xOf(d.p1.barIdx), y1 = yOf(d.p1.price);
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(W - PAD.r, y1); ctx.stroke();
      ctx.beginPath(); ctx.arc(x1, y1, 3, 0, Math.PI*2); ctx.fill();
    }
    else if (d.type === 'rect' && d.p2) {
      const x1 = xOf(d.p1.barIdx), y1 = yOf(d.p1.price);
      const x2 = xOf(d.p2.barIdx), y2 = yOf(d.p2.price);
      ctx.strokeStyle = d.color.replace('0.15','0.6'); ctx.lineWidth = 1;
      ctx.fillStyle = d.color;
      ctx.fillRect(Math.min(x1,x2), Math.min(y1,y2), Math.abs(x2-x1), Math.abs(y2-y1));
      ctx.strokeRect(Math.min(x1,x2), Math.min(y1,y2), Math.abs(x2-x1), Math.abs(y2-y1));
    }
    else if (d.type === 'fib' && d.p2) {
      const x1 = xOf(d.p1.barIdx);
      const x2 = xOf(d.p2.barIdx);
      const hi = Math.max(d.p1.price,d.p2.price), lo=Math.min(d.p1.price,d.p2.price);
      const range = hi - lo;
      const fibs = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];
      const fibCols = ['#ff3355','#ff8800','#ffcc00','#7FFFD4','#00d4ff','#cc88ff','#ff3355'];
      fibs.forEach((f, fi) => {
        const price = lo + range * (1 - f);
        if (price < minV || price > maxV) return;
        const y = yOf(price);
        ctx.strokeStyle = fibCols[fi] || '#7aa8c0'; ctx.lineWidth = 0.8; ctx.setLineDash([4,3]);
        ctx.beginPath(); ctx.moveTo(Math.min(x1,x2), y); ctx.lineTo(Math.max(x1,x2), y); ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = fibCols[fi] || '#7aa8c0'; ctx.font = '8px Share Tech Mono'; ctx.textAlign = 'left';
        ctx.fillText(f.toFixed(3) + ' (' + price.toFixed(2) + ')', Math.max(x1,x2)+3, y+3);
      });
    }
    else if (d.type === 'fibext' && d.points && d.points.length >= 3) {
      const pts = d.points;
      const x1 = xOf(pts[0].barIdx), y1 = yOf(pts[0].price);
      const x2 = xOf(pts[1].barIdx), y2 = yOf(pts[1].price);
      const x3 = xOf(pts[2].barIdx), y3 = yOf(pts[2].price);
      ctx.strokeStyle = d.color; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.lineTo(x3, y3); ctx.stroke();
      
      const range = pts[1].price - pts[0].price;
      const levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.618, 2.618];
      const colors = ['#ff3355','#ff8800','#ffcc00','#7FFFD4','#00d4ff','#cc88ff','#ff3355','#ff00ff','#00ffff'];
      levels.forEach((l, li) => {
        const price = pts[2].price + l * range;
        if (price < minV || price > maxV) return;
        const y = yOf(price);
        ctx.strokeStyle = colors[li] || '#7aa8c0'; ctx.setLineDash([4,3]);
        ctx.beginPath(); ctx.moveTo(x3, y); ctx.lineTo(W - PAD.r, y); ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = colors[li] || '#7aa8c0'; ctx.font = '8px Share Tech Mono'; ctx.textAlign = 'left';
        ctx.fillText(`Ext ${l.toFixed(3)} (${price.toFixed(2)})`, x3 + 5, y - 2);
      });
    }
    else if (d.type === 'fibtz' && d.p2) {
      const idx1 = d.p1.barIdx;
      const idx2 = d.p2.barIdx;
      const D = Math.max(1, Math.abs(idx2 - idx1));
      const fibs = [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233];
      ctx.strokeStyle = d.color; ctx.lineWidth = 0.8;
      fibs.forEach(f => {
        const targetIdx = idx1 + f * D;
        if (targetIdx >= start && targetIdx < end) {
          const x = xOf(targetIdx);
          ctx.setLineDash([3, 3]);
          ctx.beginPath(); ctx.moveTo(x, PAD.t); ctx.lineTo(x, H - PAD.b); ctx.stroke();
          ctx.setLineDash([]);
          ctx.fillStyle = d.color; ctx.font = '8px Share Tech Mono'; ctx.textAlign = 'center';
          ctx.fillText(f.toString(), x, PAD.t - 4);
        }
      });
    }
    else if (d.type === 'gannbox' && d.p2) {
      const x1 = xOf(d.p1.barIdx), y1 = yOf(d.p1.price);
      const x2 = xOf(d.p2.barIdx), y2 = yOf(d.p2.price);
      ctx.strokeStyle = d.color; ctx.lineWidth = 1;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.moveTo(x1, y2); ctx.lineTo(x2, y1); ctx.stroke();
      
      const ratios = [0.25, 0.382, 0.5, 0.618, 0.75];
      ratios.forEach(r => {
        const y = y1 + r * (y2 - y1);
        ctx.strokeStyle = 'rgba(100, 160, 200, 0.2)';
        ctx.beginPath(); ctx.moveTo(x1, y); ctx.lineTo(x2, y); ctx.stroke();
        const x = x1 + r * (x2 - x1);
        ctx.beginPath(); ctx.moveTo(x, y1); ctx.lineTo(x, y2); ctx.stroke();
      });
    }
    else if (d.type === 'gannfan' && d.p2) {
      const x1 = xOf(d.p1.barIdx), y1 = yOf(d.p1.price);
      const x2 = xOf(d.p2.barIdx), y2 = yOf(d.p2.price);
      const dx = x2 - x1, dy = y2 - y1;
      const slopes = [1/8, 1/4, 1/3, 1/2, 1, 2, 3, 4, 8];
      ctx.strokeStyle = d.color; ctx.lineWidth = 0.8;
      slopes.forEach(s => {
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x1 + dx, y1 + dy * s); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x1 + dx * s, y1 + dy); ctx.stroke();
      });
    }
    else if (d.type === 'brush' && d.points) {
      if (d.points.length > 1) {
        ctx.strokeStyle = d.color || '#4caf50'; ctx.lineWidth = 2.5; ctx.lineJoin = 'round'; ctx.lineCap = 'round';
        ctx.beginPath();
        ctx.moveTo(xOf(d.points[0].barIdx), yOf(d.points[0].price));
        for(let i=1; i<d.points.length; i++) {
          ctx.lineTo(xOf(d.points[i].barIdx), yOf(d.points[i].price));
        }
        ctx.stroke();
      }
    }
    else if (d.type === 'ellipse' && d.p2) {
      const x1 = xOf(d.p1.barIdx), y1 = yOf(d.p1.price);
      const x2 = xOf(d.p2.barIdx), y2 = yOf(d.p2.price);
      const cx = (x1 + x2) / 2;
      const cy = (y1 + y2) / 2;
      const rx = Math.abs(x2 - x1) / 2;
      const ry = Math.abs(y2 - y1) / 2;
      ctx.strokeStyle = d.color; ctx.lineWidth = 1.2;
      ctx.fillStyle = d.color.replace('0.15', '0.05');
      ctx.beginPath();
      ctx.ellipse(cx, cy, rx, ry, 0, 0, 2*Math.PI);
      ctx.fill(); ctx.stroke();
    }
    else if (d.type === 'triangle' && d.points && d.points.length >= 3) {
      const x1 = xOf(d.points[0].barIdx), y1 = yOf(d.points[0].price);
      const x2 = xOf(d.points[1].barIdx), y2 = yOf(d.points[1].price);
      const x3 = xOf(d.points[2].barIdx), y3 = yOf(d.points[2].price);
      ctx.strokeStyle = d.color; ctx.lineWidth = 1;
      ctx.fillStyle = d.color.replace('0.15', '0.06');
      ctx.beginPath();
      ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.lineTo(x3, y3); ctx.closePath();
      ctx.fill(); ctx.stroke();
    }
    else if (d.type === 'xabcd' && d.points && d.points.length >= 5) {
      const pts = d.points.map(p => ({x: xOf(p.barIdx), y: yOf(p.price)}));
      ctx.strokeStyle = d.color; ctx.lineWidth = 1.2;
      ctx.fillStyle = d.color.replace('0.15', '0.06');
      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      for(let i=1; i<5; i++) ctx.lineTo(pts[i].x, pts[i].y);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y); ctx.lineTo(pts[1].x, pts[1].y); ctx.lineTo(pts[2].x, pts[2].y); ctx.closePath();
      ctx.fill();
      ctx.beginPath();
      ctx.moveTo(pts[2].x, pts[2].y); ctx.lineTo(pts[3].x, pts[3].y); ctx.lineTo(pts[4].x, pts[4].y); ctx.closePath();
      ctx.fill();

      const labels = ['X', 'A', 'B', 'C', 'D'];
      pts.forEach((p, pi) => {
        ctx.fillStyle = '#1e222d'; ctx.beginPath(); ctx.arc(p.x, p.y, 7, 0, 2*Math.PI); ctx.fill();
        ctx.strokeStyle = '#ffffff'; ctx.stroke();
        ctx.fillStyle = '#ffffff'; ctx.font = 'bold 9px Arial'; ctx.textAlign = 'center';
        ctx.fillText(labels[pi], p.x, p.y + 3);
      });
    }
    else if (d.type === 'hns' && d.points && d.points.length >= 5) {
      const pts = d.points.map(p => ({x: xOf(p.barIdx), y: yOf(p.price)}));
      ctx.strokeStyle = d.color; ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      for(let i=1; i<5; i++) ctx.lineTo(pts[i].x, pts[i].y);
      ctx.stroke();

      ctx.strokeStyle = '#ffb703'; ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(pts[1].x, pts[1].y); ctx.lineTo(pts[3].x, pts[3].y); ctx.stroke();
      ctx.setLineDash([]);

      const labels = ['Left Shoulder', 'Neck 1', 'Head', 'Neck 2', 'Right Shoulder'];
      pts.forEach((p, pi) => {
        ctx.fillStyle = '#1e222d'; ctx.beginPath(); ctx.arc(p.x, p.y, 6, 0, 2*Math.PI); ctx.fill();
        ctx.strokeStyle = '#ffffff'; ctx.stroke();
        if (pi % 2 === 0) {
          ctx.fillStyle = '#ffb703'; ctx.font = '8px Share Tech Mono'; ctx.textAlign = 'center';
          ctx.fillText(labels[pi], p.x, p.y - 10);
        }
      });
    }
    else if (d.type === 'ewimpulse' && d.points && d.points.length >= 6) {
      const pts = d.points.map(p => ({x: xOf(p.barIdx), y: yOf(p.price)}));
      ctx.strokeStyle = d.color; ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      for(let i=1; i<6; i++) ctx.lineTo(pts[i].x, pts[i].y);
      ctx.stroke();

      pts.forEach((p, pi) => {
        ctx.fillStyle = '#1e222d'; ctx.beginPath(); ctx.arc(p.x, p.y, 6, 0, 2*Math.PI); ctx.fill();
        ctx.strokeStyle = '#ffffff'; ctx.stroke();
        ctx.fillStyle = '#ffffff'; ctx.font = 'bold 8px Arial'; ctx.textAlign = 'center';
        ctx.fillText(pi.toString(), p.x, p.y + 3);
      });
    }
    else if ((d.type === 'longpos' || d.type === 'shortpos') && d.p2) {
      const x1 = xOf(d.p1.barIdx), y1 = yOf(d.p1.price);
      const x2 = xOf(d.p2.barIdx), y2 = yOf(d.p2.price);
      const isLong = d.type === 'longpos';
      const entryPrice = d.p1.price;
      const targetPrice = d.p2.price;
      const targetDiff = targetPrice - entryPrice;
      const stopPrice = isLong ? entryPrice - targetDiff / 1.5 : entryPrice + targetDiff / 1.5;
      const targetY = yOf(targetPrice);
      const stopY = yOf(stopPrice);
      const minX = Math.min(x1, x2), maxX = Math.max(x1, x2);
      const w = maxX - minX;

      ctx.fillStyle = isLong ? 'rgba(76, 175, 80, 0.2)' : 'rgba(244, 67, 54, 0.2)';
      ctx.fillRect(minX, Math.min(y1, targetY), w, Math.abs(y1 - targetY));
      ctx.strokeStyle = isLong ? '#4caf50' : '#f44336';
      ctx.strokeRect(minX, Math.min(y1, targetY), w, Math.abs(y1 - targetY));

      ctx.fillStyle = isLong ? 'rgba(244, 67, 54, 0.2)' : 'rgba(76, 175, 80, 0.2)';
      ctx.fillRect(minX, Math.min(y1, stopY), w, Math.abs(y1 - stopY));
      ctx.strokeStyle = isLong ? '#f44336' : '#4caf50';
      ctx.strokeRect(minX, Math.min(y1, stopY), w, Math.abs(y1 - stopY));

      const targetPct = ((targetPrice - entryPrice) / entryPrice * 100).toFixed(2);
      const stopPct = ((stopPrice - entryPrice) / entryPrice * 100).toFixed(2);
      const detailTxt = `R/R: 1.50 | Target: ${targetPct}% | Stop: ${stopPct}%`;
      ctx.font = '8px Share Tech Mono';
      const tw = ctx.measureText(detailTxt).width + 8;
      ctx.fillStyle = 'rgba(10, 24, 32, 0.85)';
      ctx.fillRect(minX + w/2 - tw/2, y1 - 6, tw, 13);
      ctx.strokeStyle = '#ffffff'; ctx.strokeRect(minX + w/2 - tw/2, y1 - 6, tw, 13);
      ctx.fillStyle = '#ffffff'; ctx.textAlign = 'center'; ctx.fillText(detailTxt, minX + w/2, y1 + 3);
    }
    else if (d.type === 'text') {
      const i1 = d.barIdx - start;
      if (i1 < 0 || i1 >= N) { ctx.restore(); return; }
      const x = xOf(i1), y = yOf(d.price);
      ctx.font = '11px Share Tech Mono';
      const tw = ctx.measureText(d.text).width + 12;
      ctx.fillStyle = 'rgba(10,24,32,0.85)';
      ctx.fillRect(x - 2, y - 13, tw, 17);
      ctx.strokeStyle = isSelected ? '#fff' : d.color; ctx.lineWidth = isSelected ? 1.5 : 0.8;
      ctx.strokeRect(x - 2, y - 13, tw, 17);
      ctx.fillStyle = isSelected ? '#fff' : d.color;
      ctx.textAlign = 'left';
      ctx.fillText(d.text, x + 4, y);
      ctx.fillStyle = d.color; ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI*2); ctx.fill();
    }
    ctx.restore();
  });

  // ── Draw in-progress tool preview (follows cursor precisely) ──
  if (TV.drawState && TV.drawState.p1 && TV._mousePos) {
    const ds = TV.drawState;
    const i1 = ds.p1.barIdx - start;
    if (i1 >= 0 && i1 < N) {
      const x1 = xOf(i1);
      const y1 = yOf(ds.p1.price);
      const mx = TV._mousePos.xPx;
      const my = TV._mousePos.yPx;

      ctx.save();
      ctx.globalAlpha = 0.75;
      ctx.strokeStyle = ds.color || '#00d4ff';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([5, 4]);

      if (ds.type === 'rect' || ds.type === 'gannbox' || ds.type === 'ellipse' || ds.type === 'longpos' || ds.type === 'shortpos') {
        ctx.beginPath(); ctx.rect(x1, y1, mx - x1, my - y1); ctx.stroke();
      } else if (ds.type === 'triangle' && ds.points) {
        ctx.beginPath();
        ctx.moveTo(xOf(ds.points[0].barIdx), yOf(ds.points[0].price));
        if (ds.points.length > 1) ctx.lineTo(xOf(ds.points[1].barIdx), yOf(ds.points[1].price));
        ctx.lineTo(mx, my); ctx.closePath(); ctx.stroke();
      } else if (ds.type === 'fibext' && ds.points) {
        ctx.beginPath();
        ctx.moveTo(xOf(ds.points[0].barIdx), yOf(ds.points[0].price));
        if (ds.points.length > 1) {
          ctx.lineTo(xOf(ds.points[1].barIdx), yOf(ds.points[1].price));
          ctx.moveTo(xOf(ds.points[1].barIdx), yOf(ds.points[1].price));
        }
        ctx.lineTo(mx, my); ctx.stroke();
      } else if (['xabcd', 'hns', 'ewimpulse'].includes(ds.type) && ds.points) {
        ctx.beginPath();
        ctx.moveTo(xOf(ds.points[0].barIdx), yOf(ds.points[0].price));
        for(let pi=1; pi<ds.points.length; pi++) {
          ctx.lineTo(xOf(ds.points[pi].barIdx), yOf(ds.points[pi].price));
        }
        ctx.lineTo(mx, my); ctx.stroke();
      } else {
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(mx, my); ctx.stroke();
      }
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;
      ctx.fillStyle = ds.color || '#00d4ff';
      ctx.beginPath(); ctx.arc(x1, y1, 4, 0, Math.PI*2); ctx.fill();
      ctx.restore();
    }
  }
}

// ════════════════════════════════════════════════════════════════
// ELLIOTT WAVE ENGINE v2 — 5-Wave Impulse + ABC Corrective
// Full Rules: R1 W2≠origin, R2 W3 not shortest, R3 W4≠W1 overlap
// ABC Rules: A=impulse, B<A, C≥A (zigzag) or Flat/Triangle
// ════════════════════════════════════════════════════════════════
TV.ewAnalysis = null;

function ewZigZag(highs, lows, thresh) {
  const N = highs.length;
  const pivots = [];
  let dir = 0, lastH = highs[0], lastL = lows[0], lastHi = 0, lastLi = 0;
  for (let i = 1; i < N; i++) {
    if (dir >= 0) {
      if (highs[i] > lastH) { lastH = highs[i]; lastHi = i; }
      if (lows[i] < lastH * (1 - thresh)) {
        pivots.push({idx:lastHi, price:lastH, type:'H'});
        dir = -1; lastL = lows[i]; lastLi = i;
      }
    }
    if (dir <= 0) {
      if (lows[i] < lastL) { lastL = lows[i]; lastLi = i; }
      if (highs[i] > lastL * (1 + thresh)) {
        pivots.push({idx:lastLi, price:lastL, type:'L'});
        dir = 1; lastH = highs[i]; lastHi = i;
      }
    }
  }
  if (dir > 0 && lastHi > (pivots[pivots.length-1]?.idx||0))
    pivots.push({idx:lastHi, price:lastH, type:'H'});
  else if (dir < 0 && lastLi > (pivots[pivots.length-1]?.idx||0))
    pivots.push({idx:lastLi, price:lastL, type:'L'});
  return pivots;
}

function ewValidateImpulse(pts) {
  if (pts.length < 6) return {valid:false, score:0, violations:['Insufficient pivots'], guidelines:[]};
  const [p0,p1,p2,p3,p4,p5] = pts;
  const violations = [], guidelines = [];
  const up = p1.price > p0.price;
  const w1=Math.abs(p1.price-p0.price), w2=Math.abs(p2.price-p1.price);
  const w3=Math.abs(p3.price-p2.price), w4=Math.abs(p4.price-p3.price);
  const w5=Math.abs(p5.price-p4.price);
  // 3 Hard Rules
  if ( up && p2.price <= p0.price) violations.push('W2 retraces beyond W1 origin');
  if (!up && p2.price >= p0.price) violations.push('W2 retraces beyond W1 origin');
  if (w3 < w1 && w3 < w5)          violations.push('W3 is shortest impulse (invalid)');
  if ( up && p4.price <= p1.price) violations.push('W4 overlaps W1 territory (invalid)');
  if (!up && p4.price >= p1.price) violations.push('W4 overlaps W1 territory (invalid)');
  // Guidelines
  const w2ret=w2/w1, w4ret=w4/w3;
  if (w2ret>=0.50&&w2ret<=0.618) guidelines.push('W2: golden ratio retracement (0.618)');
  if (w2ret>=0.382&&w2ret<0.50)  guidelines.push('W2: deep retracement (0.382-0.5)');
  if (w4ret>=0.236&&w4ret<=0.382) guidelines.push('W4: shallow retracement (0.236-0.382)');
  if (w3>=w1*1.618)               guidelines.push('W3 extended: '+((w3/w1).toFixed(2))+'× W1');
  if (Math.abs(w5-w1)/w1<0.15)   guidelines.push('W5 ≈ W1 equality');
  if (w3>=w1&&w3>=w5)             guidelines.push('W3 longest impulse ✓');
  const score = violations.length===0 ? Math.min(100, 55+guidelines.length*9) : Math.max(0, 40-violations.length*18);
  return {valid:violations.length===0, violations, guidelines, score, w1,w2,w3,w4,w5, up};
}

function ewValidateABC(pts, impulseUp) {
  // pts = [A0, A1, B, C] — 3-wave correction after 5-wave impulse
  if (pts.length < 4) return {valid:false, type:'?', score:0};
  const [a0, a1, b, c] = pts;
  const violations=[], guidelines=[];
  const corrDown = !impulseUp; // correction goes against impulse
  const wA=Math.abs(a1.price-a0.price);
  const wB=Math.abs(b.price-a1.price);
  const wC=Math.abs(c.price-b.price);
  // ABC Rules
  if (wB >= wA*1.0) violations.push('B >= A (B should not exceed A origin)');
  if (wC < wA*0.618) violations.push('C shorter than 0.618×A (weak C)');
  // Detect type
  let type = 'Zigzag (5-3-5)'; // most common
  if (Math.abs(wB/wA-1.0)<0.05) type = 'Flat (3-3-5)';
  if (wC<wA*0.5) type = 'Running Correction';
  if (Math.abs(wC-wA)/wA<0.1) guidelines.push('C = A equality (common target)');
  if (Math.abs(wC-wA*1.618)/wA<0.1) guidelines.push('C = 1.618×A (extended)');
  const score = violations.length===0 ? 60+guidelines.length*15 : 30;
  return {valid:violations.length===0, type, violations, guidelines, score, wA,wB,wC};
}

function calcElliottWaves(highs, lows, closes, start, end) {
  const hl=highs.slice(start,end), ll=lows.slice(start,end), sl=closes.slice(start,end);
  const N=hl.length;
  const thresh = N>500?0.07:N>200?0.045:N>80?0.025:0.015;
  const pivots = ewZigZag(hl, ll, thresh);
  if (pivots.length < 4) return null;

  // ── Find best 5-wave impulse (look at recent 14 pivots) ──
  let bestImpulse=null, bestImpulseScore=-1, bestImpulsePts=null;
  for (let w=Math.max(0,pivots.length-14); w<=pivots.length-6; w++) {
    const win=pivots.slice(w,w+6);
    const r=ewValidateImpulse(win);
    if (r.score>bestImpulseScore) { bestImpulseScore=r.score; bestImpulse=r; bestImpulsePts=win; }
  }

  // ── ABC correction detection after impulse ──
  let abcPts=null, abcResult=null, abcInProgress=false, abcPhase='';
  if (bestImpulsePts) {
    const impEnd = bestImpulsePts[5]; // W5 endpoint
    const postW5 = pivots.filter(p => p.idx > impEnd.idx);
    const up = bestImpulse.up;

    // Helper: find the most extreme price in a slice of closes
    const extremeInRange = (fromIdx, toIdx, findLow) => {
      let best = findLow ? Infinity : -Infinity, bestI = fromIdx;
      for (let i=fromIdx; i<=Math.min(toIdx, N-1); i++) {
        const v = findLow ? ll[i] : hl[i];
        if (findLow ? v < best : v > best) { best=v; bestI=i; }
      }
      return {idx:bestI, price:best, type:findLow?'L':'H'};
    };

    if (postW5.length >= 3) {
      // A, B, C all confirmed by ZigZag
      // C endpoint = extend to the most extreme price from B to last bar
      const bPt = postW5[1];
      const cExtreme = extremeInRange(bPt.idx+1, N-1, up); // C goes opposite to B bounce
      const abcWin = [impEnd, postW5[0], bPt, cExtreme];
      abcResult = ewValidateABC(abcWin, up);
      abcPts = abcWin;
      // If C extreme is the last bar, still in progress
      abcInProgress = (cExtreme.idx >= N-3);
      abcPhase = abcInProgress ? 'C_inprogress' : 'complete';
    } else if (postW5.length === 2) {
      // A done, B done — C not yet confirmed by ZigZag
      // Stretch C to the most extreme low/high from B to last bar
      const bPt = postW5[1];
      const cExtreme = extremeInRange(bPt.idx+1, N-1, up);
      abcPts = [impEnd, postW5[0], bPt, cExtreme];
      abcInProgress = true;
      abcPhase = 'C_inprogress';
      abcResult = ewValidateABC(abcPts, up);
    } else if (postW5.length === 1) {
      // A done — B in progress (current price is B bounce)
      const aPt = postW5[0];
      const bExtreme = extremeInRange(aPt.idx+1, N-1, !up); // B bounces back
      abcPts = [impEnd, aPt, bExtreme];
      abcInProgress = true;
      abcPhase = 'B_inprogress';
    } else if (postW5.length === 0 && bestImpulse.valid) {
      // W5 just confirmed — A starting (stretch to current extreme)
      const aExtreme = extremeInRange(impEnd.idx+1, N-1, up);
      if (Math.abs(aExtreme.price - impEnd.price) / impEnd.price > 0.005) {
        abcPts = [impEnd, aExtreme];
        abcInProgress = true;
        abcPhase = 'A_inprogress';
      }
    }
  }

  // ── Current wave status ──
  let currentWave;
  if (!bestImpulsePts || bestImpulseScore < 15) {
    currentWave = {wave:'?', description:'Pattern unclear — zoom in or change timeframe', bullish:null, score:0};
  } else {
    const up = bestImpulse.up;
    if (!abcPts) {
      currentWave = {wave:'⑤', description:'Wave 5 complete — watching for ABC reversal', bullish:up, score:bestImpulseScore, pattern:'12345'};
    } else if (abcPhase === 'A_inprogress') {
      currentWave = {wave:'A', description:'Wave A in progress — first corrective leg after impulse', bullish:!up, score:55, pattern:'12345·A…'};
    } else if (abcPhase === 'B_inprogress') {
      currentWave = {wave:'B', description:'Wave B in progress — corrective bounce, watch for C', bullish:up, score:60, pattern:'12345·AB…'};
    } else if (abcPhase === 'C_inprogress') {
      const cPt  = abcPts[abcPts.length-1];
      const cChg = ((cPt.price - abcPts[0].price) / abcPts[0].price * 100).toFixed(1);
      currentWave = {
        wave:'C',
        description:`Wave C in progress (${cChg}%) — watch REVERSAL DAYS for new 1·2·3·4·5 cycle`,
        bullish:!up, score:72, pattern:'12345·ABC↩',
        targetNote: `C target ≈ ${up ? 'below' : 'above'} A endpoint at ${abcPts[1].price.toFixed(0)}`
      };
    } else if (abcPhase === 'complete') {
      currentWave = {wave:'C✓', description:'ABC complete — NEW impulse cycle 1·2·3·4·5 may be starting', bullish:up, score:85, pattern:'12345·ABC·NEW↑'};
    } else {
      currentWave = {wave:'⑤', description:'Impulse complete — awaiting ABC', bullish:up, score:bestImpulseScore, pattern:'12345'};
    }
  }

  const mapPts = pts => pts.map(p=>({...p, barIdx:p.idx}));
  return {
    impulsePts:    bestImpulsePts ? mapPts(bestImpulsePts) : null,
    abcPts:        abcPts         ? mapPts(abcPts)         : null,
    abcInProgress,
    impulseVal:    bestImpulse,
    abcVal:        abcResult,
    currentWave,
    thresh,
    allPivots:     mapPts(pivots)
  };
}

function drawElliottWaves(ctx, W, H, PAD, xOf, yOf, closes, highs, lows, start, end) {
  const result = calcElliottWaves(highs, lows, closes, start, end);
  if (!result) return;
  TV.ewAnalysis = result;

  const {impulsePts, abcPts, impulseVal, currentWave} = result;
  const N = end - start;
  ctx.save();

  // ── Draw 5-wave impulse ──
  if (impulsePts && impulsePts.length >= 2) {
    // Wave segment colors: W1=teal, W2=orange, W3=teal, W4=orange, W5=teal
    const impulseColors = ['#26a69a','#ff8800','#26a69a','#ff8800','#26a69a'];
    for (let i=0; i<impulsePts.length-1; i++) {
      const p1=impulsePts[i], p2=impulsePts[i+1];
      const bi1=p1.barIdx, bi2=p2.barIdx;
      if (bi1<0||bi2<0||bi1>=N||bi2>=N) continue;
      const x1=xOf(bi1),y1=yOf(p1.price),x2=xOf(bi2),y2=yOf(p2.price);
      const isImpulseWave = (i%2===0); // 0=W1, 2=W3, 4=W5 are impulse
      ctx.strokeStyle = impulseColors[i]; ctx.lineWidth = isImpulseWave ? 2 : 1.4;
      ctx.setLineDash(isImpulseWave ? [] : [5,3]);
      ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke();
      ctx.setLineDash([]);
    }
    // Draw wave labels (circled numbers)
    const impulseLabels = ['0','①','②','③','④','⑤'];
    impulsePts.forEach((p, pi) => {
      const bi=p.barIdx;
      if (bi<0||bi>=N) return;
      const x=xOf(bi), y=yOf(p.price);
      const isH=p.type==='H';
      // Dot
      ctx.fillStyle = isH?'#ef5350':'#26a69a';
      ctx.beginPath(); ctx.arc(x,y,4,0,Math.PI*2); ctx.fill();
      // Circled number label
      const lx=x, ly=isH?y-16:y+20;
      ctx.fillStyle='rgba(15,30,45,0.9)';
      ctx.beginPath(); ctx.arc(lx,ly,9,0,Math.PI*2); ctx.fill();
      ctx.strokeStyle = pi%2===1?'#ff8800':'#26a69a'; ctx.lineWidth=1.2;
      ctx.beginPath(); ctx.arc(lx,ly,9,0,Math.PI*2); ctx.stroke();
      ctx.fillStyle='#fff'; ctx.font='bold 9px Share Tech Mono'; ctx.textAlign='center';
      ctx.fillText(pi===0?'0':String(pi), lx, ly+3);
    });
  }

  // ── Draw ABC correction ──
  if (abcPts && abcPts.length >= 2) {
    const abcColors = ['#ef5350','#7FFFD4','#ef5350']; // A=red, B=cyan, C=red
    const abcLabels = ['A','B','C'];
    const inProg    = result.abcInProgress;

    for (let i=0; i<abcPts.length-1; i++) {
      const p1=abcPts[i], p2=abcPts[i+1];
      const bi1=p1.barIdx, bi2=p2.barIdx;
      if (bi1<0||bi2<0||bi1>=N||bi2>=N) continue;
      const x1=xOf(bi1),y1=yOf(p1.price),x2=xOf(bi2),y2=yOf(p2.price);
      const col = abcColors[Math.min(i, abcColors.length-1)];
      const isLastSeg = (i === abcPts.length - 2);
      // Last segment dashed if in-progress (C not confirmed yet)
      const dash = (i===1) || (isLastSeg && inProg) ? [5,3] : [];
      ctx.strokeStyle=col; ctx.lineWidth=1.8;
      ctx.setLineDash(dash);
      ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke();
      ctx.setLineDash([]);
    }

    // Draw labels for completed pivots, skip synthetic last point
    const labelPts = inProg ? abcPts.slice(1, -1) : abcPts.slice(1);
    labelPts.forEach((p, pi) => {
      const bi=p.barIdx;
      if (bi<0||bi>=N) return;
      const x=xOf(bi), y=yOf(p.price);
      const isH=p.type==='H';
      ctx.fillStyle=abcColors[pi];
      ctx.beginPath(); ctx.arc(x,y,5,0,Math.PI*2); ctx.fill();
      ctx.strokeStyle='#060f16'; ctx.lineWidth=1;
      ctx.beginPath(); ctx.arc(x,y,5,0,Math.PI*2); ctx.stroke();
      const lx=x, ly=isH?y-17:y+21;
      ctx.fillStyle='rgba(15,30,45,0.9)';
      ctx.beginPath(); ctx.arc(lx,ly,10,0,Math.PI*2); ctx.fill();
      ctx.strokeStyle=abcColors[pi]; ctx.lineWidth=1.3;
      ctx.beginPath(); ctx.arc(lx,ly,10,0,Math.PI*2); ctx.stroke();
      ctx.fillStyle='#fff'; ctx.font='bold 10px Share Tech Mono'; ctx.textAlign='center';
      ctx.fillText(abcLabels[pi], lx, ly+4);
    });

    // If in progress, show dashed line to current price with ? label
    if (inProg && TV._mousePos) {
      const lastConfirmed = abcPts[abcPts.length-2];
      if (lastConfirmed && lastConfirmed.barIdx>=0 && lastConfirmed.barIdx<N) {
        const x0=xOf(lastConfirmed.barIdx), y0=yOf(lastConfirmed.price);
        const x1=TV._mousePos.xPx, y1=TV._mousePos.yPx;
        ctx.strokeStyle='rgba(255,204,0,0.4)'; ctx.lineWidth=1;
        ctx.setLineDash([3,4]);
        ctx.beginPath(); ctx.moveTo(x0,y0); ctx.lineTo(x1,y1); ctx.stroke();
        ctx.setLineDash([]);
      }
    }
  }

  // ── Current wave status banner ──
  if (currentWave && currentWave.wave !== '?') {
    const bul = currentWave.bullish;
    const bannerCol = bul===null?'rgba(60,60,70,0.88)':bul?'rgba(38,166,154,0.88)':'rgba(239,83,80,0.88)';
    const mainTxt = `Wave ${currentWave.wave}  ${(currentWave.description||'')}`;
    ctx.font = 'bold 9px Share Tech Mono';
    let lineY = PAD.t + 16;
    const bw = Math.min(W-PAD.l-PAD.r-10, ctx.measureText(mainTxt).width+20);

    // Main banner
    ctx.fillStyle=bannerCol;
    ctx.fillRect(PAD.l+4, lineY, bw, 18);
    ctx.fillStyle='#fff'; ctx.textAlign='left';
    ctx.fillText(mainTxt, PAD.l+10, lineY+12);
    lineY += 22;

    // Target note (C wave)
    if (currentWave.targetNote) {
      ctx.fillStyle='rgba(255,204,0,0.85)';
      ctx.font='8px Share Tech Mono';
      ctx.fillText('🎯 '+currentWave.targetNote, PAD.l+4, lineY);
      lineY += 14;
    }

    // EW Score
    if (impulseVal) {
      const sc=impulseVal.score;
      const scCol=sc>=75?'#26a69a':sc>=50?'#ffcc00':'#ef5350';
      ctx.fillStyle=scCol; ctx.font='9px Share Tech Mono';
      ctx.fillText(`EW Score: ${sc}/100  Pattern: ${currentWave.pattern||''}`, PAD.l+4, lineY);
    }
  }

  ctx.restore();
}

// ── Measure tool state ────────────────────────────────────────────
TV.measureState = null; // {p1: {barIdx, price}, p2: {barIdx, price}} | null (in-progress)
TV.measureResult = null; // completed measure rectangle

// ── Get current Y range (auto or manual) ─────────────────────────
function tvGetYRange() {
  if(!TV.data) return {minV:0, maxV:100};
  if(TV.yRange.min!==null && TV.yRange.max!==null)
    return {minV:TV.yRange.min, maxV:TV.yRange.max};
  const {highs,lows,closes,opens} = TV.data;
  const {start,end} = TV.view;
  const ll=lows.slice(start,end), hl=highs.slice(start,end);
  let minV=Math.min(...ll), maxV=Math.max(...hl);
  const margin=(maxV-minV)*0.04;
  return {minV:minV-margin, maxV:maxV+margin};
}

// ── Main redraw ────────────────────────────────────────────────────
function tvRedraw() {
  if (!TV.data) return;
  const { dates, opens, highs, lows, closes, volumes } = TV.data;
  const { start, end } = TV.view;
  const N = end - start;
  if (N < 2) return;

  const sl=closes.slice(start,end), hl=highs.slice(start,end);
  const ll=lows.slice(start,end),   ol=opens.slice(start,end);
  const vl=volumes.slice(start,end), dl=dates.slice(start,end);
  const sr = TV.data.sr || {};

  // Read actual rendered canvas width (CSS 100% already applied)
  const cvsMeasure = document.getElementById('price-canvas');
  const wrap = document.getElementById('tv-chart-card');
  const W = cvsMeasure ? (cvsMeasure.offsetWidth||Math.floor((wrap||{clientWidth:900}).getBoundingClientRect?.()?.width||900)) : 900;
  const H = TV.mainH;
  const ctx = tvSetup('price-canvas', W, H);
  if (!ctx) return;

  const PAD = {t:28, r:68, b:26, l:8};  // right Y-axis: labels on right side
  const cW = W-PAD.l-PAD.r, cH = H-PAD.t-PAD.b;

  // Price range
  let minV=Math.min(...ll), maxV=Math.max(...hl);
  if (TV.indicators.bb) {
    const bb=calcBB(closes, TV.params.bbP, TV.params.bbStd).slice(start,end);
    bb.forEach(b=>{if(b.upper)maxV=Math.max(maxV,b.upper);if(b.lower)minV=Math.min(minV,b.lower);});
  }
  // Use manual Y range if user has panned Y axis, else auto-fit with 4% margin
  if (TV.yRange.min !== null && TV.yRange.max !== null) {
    minV = TV.yRange.min;
    maxV = TV.yRange.max;
  } else {
    const margin=(maxV-minV)*0.04;
    minV-=margin; maxV+=margin;
  }
  window._chartPriceData = { minP: minV, maxP: maxV, padTop: PAD.t, padBot: PAD.b };


  // ── Candle geometry (TradingView style) ──
  // Each bar occupies exactly cW/N pixels, candle body is 80% of that, max 20px wide
  const slotW   = cW / N;
  const candleW = Math.max(1, Math.min(20, Math.floor(slotW * 0.8)));
  const xOf     = i => PAD.l + (i + 0.5) * slotW;   // centre x of bar i
  const yOf     = v => PAD.t + cH*(1-(v-minV)/(maxV-minV));

  // ── Background ──
  ctx.fillStyle='#ffffff'; ctx.fillRect(0,0,W,H);

  // ── Grid ──
  ctx.lineWidth=0.5;
  const nGridH=8, nGridV=8;
  for(let i=0;i<=nGridH;i++){
    const y=PAD.t+(i/nGridH)*cH;
    ctx.strokeStyle='rgba(19,23,34,0.05)';
    ctx.beginPath();ctx.moveTo(PAD.l,y);ctx.lineTo(W-PAD.r,y);ctx.stroke();
    const v=maxV-(i/nGridH)*(maxV-minV);
    // Y labels on RIGHT side
    ctx.fillStyle='#131722'; ctx.font='11px -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif'; ctx.textAlign='left';
    ctx.fillText(v>=1000?v.toFixed(0):v.toFixed(2), W-PAD.r+6, y+4);
  }
  // ── X-axis: TradingView-style smart date labels ──
  // Show month name normally; show YEAR prominently at Jan boundary
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const slotPx = cW / N;  // pixels per bar
  // How many bars per label — aim for ~80px spacing between labels
  const labelEvery = Math.max(1, Math.round(80 / slotPx));
  let lastLabelX = -999;
  ctx.textAlign = 'center';

  for (let i = 0; i < N; i++) {
    const dateStr = dl[i];
    if (!dateStr) continue;
    const x = xOf(i);

    // Parse date
    const yr  = parseInt(dateStr.slice(0,4));
    const mon = parseInt(dateStr.slice(5,7)) - 1; // 0-indexed
    const day = parseInt(dateStr.slice(8,10));

    // Decide if this bar starts a new month or year
    const prevDateStr = i > 0 ? dl[i-1] : null;
    const prevMon = prevDateStr ? parseInt(prevDateStr.slice(5,7)) : -1;
    const prevYr  = prevDateStr ? parseInt(prevDateStr.slice(0,4)) : -1;
    const isNewMonth = mon !== prevMon - 1 && !(mon === 0 && prevMon === 12);
    const monthChanged = !prevDateStr || parseInt(prevDateStr.slice(5,7)) !== mon+1;
    const yearChanged  = !prevDateStr || parseInt(prevDateStr.slice(0,4)) !== yr;

    // Draw grid line for every label position
    if (x - lastLabelX >= labelEvery * slotPx - 2) {
      ctx.strokeStyle = 'rgba(255,255,255,0.025)'; ctx.lineWidth = 0.5;
      ctx.beginPath(); ctx.moveTo(x, PAD.t); ctx.lineTo(x, PAD.t+cH); ctx.stroke();
    }

    // Only label at month boundaries, and only if enough space since last label
    if (!monthChanged) continue;
    if (x - lastLabelX < 44) continue;  // min 44px between labels

    if (yearChanged && mon === 0) {
      // Jan + year changed → show YEAR prominently
      ctx.fillStyle = '#131722';
      ctx.font = 'bold 12px -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif';
      ctx.fillText(String(yr), x, H - 6);
      // Stronger grid line at year boundary
      ctx.strokeStyle = 'rgba(19,23,34,0.12)'; ctx.lineWidth = 0.8;
      ctx.beginPath(); ctx.moveTo(x, PAD.t); ctx.lineTo(x, PAD.t+cH); ctx.stroke();
    } else {
      // Regular month label
      ctx.fillStyle = '#787b86';
      ctx.font = '11px -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif';
      ctx.fillText(MONTHS[mon], x, H - 6);
    }
    lastLabelX = x;
  }

  // ── Watermark ──
  const symbolLabel = (document.getElementById('tv-sym-label') && document.getElementById('tv-sym-label').textContent) || 'SYMBOL';
  const tfLabel = TV.cwTimeframe || '1D';
  ctx.fillStyle = 'rgba(19, 23, 34, 0.03)';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = 'bold 120px -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif';
  ctx.fillText(symbolLabel, PAD.l + cW/2, PAD.t + cH/2 - 40);
  ctx.font = 'bold 60px -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif';
  ctx.fillText(tfLabel, PAD.l + cW/2, PAD.t + cH/2 + 60);
  ctx.textBaseline = 'alphabetic';

  // ── S/R levels — filter out clustered levels (min 0.3% gap) ──
  if (TV.indicators.sr) {
    const priceRange = maxV - minV;
    const minGap = priceRange * 0.003;  // 0.3% of visible range minimum gap between lines
    const minPxGap = 12;                // also min 12px gap between lines on screen

    const drawSRLevels = (levels, bullish) => {
      // Sort by price, filter visible, then de-cluster
      const visible = levels
        .filter(s => s.price >= minV && s.price <= maxV)
        .sort((a,b) => a.price - b.price);

      // De-cluster: keep STRONG ones, skip WEAK/MODERATE if too close to a nearby level
      const kept = [];
      visible.forEach(s => {
        const tooClose = kept.some(k => Math.abs(k.price - s.price) < minGap);
        if (!tooClose || s.strength === 'STRONG') {
          // Remove weaker nearby level if this is STRONG
          if (s.strength === 'STRONG') {
            const nearIdx = kept.findIndex(k => Math.abs(k.price - s.price) < minGap && k.strength !== 'STRONG');
            if (nearIdx >= 0) kept.splice(nearIdx, 1);
          }
          if (!kept.some(k => Math.abs(k.price - s.price) < minGap)) kept.push(s);
        }
      });

      kept.forEach(s => {
        const y = yOf(s.price);
        const strong = s.strength === 'STRONG';
        const col = bullish ? (strong?'rgba(0,255,136,0.55)':'rgba(0,255,136,0.25)') 
                            : (strong?'rgba(255,51,85,0.55)':'rgba(255,51,85,0.25)');
        const txtCol = bullish ? 'rgba(0,255,136,0.85)' : 'rgba(255,80,80,0.85)';
        ctx.strokeStyle = col;
        ctx.lineWidth = strong ? 1.2 : 0.6;
        ctx.setLineDash(strong ? [5,3] : [3,5]);
        ctx.beginPath(); ctx.moveTo(PAD.l,y); ctx.lineTo(W-PAD.r,y); ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = txtCol;
        ctx.font = strong ? 'bold 9px Share Tech Mono' : '9px Share Tech Mono';
        ctx.textAlign = 'left';
        ctx.fillText(s.price.toFixed(0), W-PAD.r+3, y+3);
      });
    };

    drawSRLevels(sr.supports||[], true);
    drawSRLevels(sr.resistances||[], false);
  }

  // ── SMAs ──
  if (TV.indicators.sma) {
    const cols=['#7FFFD4','#B5B5FF','#DEB887'];
    TV.params.smaP.forEach((p,pi)=>{
      const sma=calcSMA(closes,p).slice(start,end);
      ctx.strokeStyle=cols[pi%cols.length]; ctx.globalAlpha=0.75; ctx.lineWidth=1.3;
      ctx.beginPath(); let first=true;
      sma.forEach((v,i)=>{if(!v)return; first?ctx.moveTo(xOf(i),yOf(v)):ctx.lineTo(xOf(i),yOf(v)); first=false;});
      ctx.stroke(); ctx.globalAlpha=1;
    });
  }

  // ── EMAs ──
  if (TV.indicators.ema) {
    const cols=['#ff8800','#00ff88','#ff3355'];
    TV.params.emaP.forEach((p,pi)=>{
      const ema=calcEMA(closes,p).slice(start,end);
      ctx.strokeStyle=cols[pi%cols.length]; ctx.globalAlpha=0.75; ctx.lineWidth=1.3;
      ctx.beginPath(); let first=true;
      ema.forEach((v,i)=>{if(!v)return; first?ctx.moveTo(xOf(i),yOf(v)):ctx.lineTo(xOf(i),yOf(v)); first=false;});
      ctx.stroke(); ctx.globalAlpha=1;
    });
  }

  // ── Bollinger Bands ──
  if (TV.indicators.bb) {
    const bb=calcBB(closes,TV.params.bbP,TV.params.bbStd).slice(start,end);
    ctx.fillStyle='rgba(204,136,255,0.06)';
    ctx.beginPath();
    let fu=true;
    bb.forEach((b,i)=>{if(!b.upper)return;fu?ctx.moveTo(xOf(i),yOf(b.upper)):ctx.lineTo(xOf(i),yOf(b.upper));fu=false;});
    for(let i=bb.length-1;i>=0;i--){if(bb[i].lower)ctx.lineTo(xOf(i),yOf(bb[i].lower));}
    ctx.closePath(); ctx.fill();
    [['upper','rgba(204,136,255,0.4)',0.8],['mid','rgba(204,136,255,0.6)',1],['lower','rgba(204,136,255,0.4)',0.8]].forEach(([k,col,lw])=>{
      ctx.strokeStyle=col; ctx.lineWidth=lw; ctx.beginPath(); let f=true;
      bb.forEach((b,i)=>{if(!b[k])return;f?ctx.moveTo(xOf(i),yOf(b[k])):ctx.lineTo(xOf(i),yOf(b[k]));f=false;});
      ctx.stroke();
    });
  }

  // ── Price bars ──
  if (TV.chartType==='line') {
    ctx.strokeStyle='#00d4ff'; ctx.lineWidth=1.6;
    ctx.shadowColor='#00d4ff'; ctx.shadowBlur=2;
    ctx.beginPath();
    sl.forEach((c,i)=>i===0?ctx.moveTo(xOf(i),yOf(c)):ctx.lineTo(xOf(i),yOf(c)));
    ctx.stroke(); ctx.shadowBlur=0;
    ctx.fillStyle='rgba(0,212,255,0.06)';
    ctx.beginPath(); ctx.moveTo(xOf(0),yOf(sl[0]));
    sl.forEach((c,i)=>ctx.lineTo(xOf(i),yOf(c)));
    ctx.lineTo(xOf(N-1),PAD.t+cH); ctx.lineTo(xOf(0),PAD.t+cH); ctx.closePath(); ctx.fill();
  } else if (TV.chartType==='bar') {
    for(let i=0;i<N;i++){
      const bull=sl[i]>=ol[i],col=bull?'#26a69a':'#ef5350',x=xOf(i),hw=Math.max(2,candleW/2);
      ctx.strokeStyle=col; ctx.lineWidth=Math.max(1,Math.min(2,candleW*0.15));
      ctx.beginPath();ctx.moveTo(x,yOf(hl[i]));ctx.lineTo(x,yOf(ll[i]));ctx.stroke();
      ctx.beginPath();ctx.moveTo(x-hw,yOf(ol[i]));ctx.lineTo(x,yOf(ol[i]));ctx.stroke();
      ctx.beginPath();ctx.moveTo(x,yOf(sl[i]));ctx.lineTo(x+hw,yOf(sl[i]));ctx.stroke();
    }
  } else {
    // Candlesticks — TradingView green/red
    for(let i=0;i<N;i++){
      const o=ol[i],c=sl[i],h=hl[i],l=ll[i];
      const bull=c>=o;
      const bodyTop=yOf(Math.max(o,c)), bodyBot=yOf(Math.min(o,c));
      const bodyH=Math.max(1, bodyBot-bodyTop);
      const x=xOf(i), hw=candleW/2;
      const bullCol='#089981', bearCol='#f23645';
      const col=bull?bullCol:bearCol;
      // Wick
      ctx.strokeStyle=col; ctx.lineWidth=Math.max(1,Math.min(1.5,candleW*0.12));
      ctx.beginPath(); ctx.moveTo(x,yOf(h)); ctx.lineTo(x,yOf(l)); ctx.stroke();
      // Body — solid filled for both bull and bear (TradingView solid mode)
      ctx.fillStyle = bull ? bullCol : bearCol;
      ctx.fillRect(x - hw, bodyTop, candleW, bodyH);
      // Thin border for definition when candles are wide
      if (candleW > 4) {
        ctx.strokeStyle = bull ? '#089981' : '#f23645';
        ctx.lineWidth = 0.5;
        ctx.strokeRect(x - hw, bodyTop, candleW, bodyH);
      }
    }
  }

  // ── Draw all user drawings (trendlines, H-lines etc) ──
  tvDrawAllDrawings(ctx, W, H, PAD, xOf, yOf);

  // ── Draw Astro Overlays ──
  drawAstroOverlays(ctx, W, H, PAD, xOf, yOf, dl, start, end, minV, maxV);

  // ── Elliott Wave indicator ──
  if (TV.indicators.ew) {
    drawElliottWaves(ctx, W, H, PAD, xOf, yOf, closes, highs, lows, start, end);
  }

  // ── Big Players (FII/DII) overlay ──
  if (TV.indicators.fii && TV.fiiData) {
    drawFIIOverlay(ctx, W, H, PAD, xOf, yOf, dl, sl, hl, ll, ol, vl, start, end, candleW);
    drawFIILegend(ctx, PAD);
  }

  // ── Measure tool result overlay ──
  if (TV.measureResult) {
    const mr = TV.measureResult;
    const x1=xOf(mr.p1.barIdx-start), x2=xOf(mr.p2.barIdx-start);
    const y1=yOf(mr.p1.price), y2=yOf(mr.p2.price);
    const bars=Math.abs(mr.p2.barIdx-mr.p1.barIdx);
    const priceDiff=mr.p2.price-mr.p1.price;
    const pct=(priceDiff/mr.p1.price*100).toFixed(2);
    const col=priceDiff>=0?'rgba(38,166,154,0.18)':'rgba(239,83,80,0.18)';
    const borderCol=priceDiff>=0?'#26a69a':'#ef5350';
    // Shaded rectangle
    ctx.fillStyle=col;
    ctx.fillRect(Math.min(x1,x2),Math.min(y1,y2),Math.abs(x2-x1),Math.abs(y2-y1));
    ctx.strokeStyle=borderCol; ctx.lineWidth=1; ctx.setLineDash([]);
    ctx.strokeRect(Math.min(x1,x2),Math.min(y1,y2),Math.abs(x2-x1),Math.abs(y2-y1));
    // Arrow from p1 to p2
    ctx.strokeStyle=borderCol; ctx.lineWidth=1.5;
    ctx.beginPath(); ctx.moveTo((x1+x2)/2,y1); ctx.lineTo((x1+x2)/2,y2); ctx.stroke();
    const arrowDir=priceDiff>=0?-6:6;
    ctx.beginPath(); ctx.moveTo((x1+x2)/2-5,y2+arrowDir); ctx.lineTo((x1+x2)/2,y2); ctx.lineTo((x1+x2)/2+5,y2+arrowDir); ctx.stroke();
    // Info box
    const infoX=Math.min(x1,x2)+Math.abs(x2-x1)/2;
    const infoY=Math.max(y1,y2)+12;
    const line1=`${priceDiff>=0?'+':''}${priceDiff.toFixed(0)} (${pct}%)`;
    const line2=`${bars} bars`;
    const boxW=Math.max(ctx.measureText(line1).width,ctx.measureText(line2).width)+20;
    const boxH=40; const boxX=infoX-boxW/2; const boxYStart=Math.min(infoY,PAD.t+cH-boxH-4);
    ctx.fillStyle=priceDiff>=0?'rgba(38,166,154,0.9)':'rgba(239,83,80,0.9)';
    ctx.beginPath(); ctx.roundRect?ctx.roundRect(boxX,boxYStart,boxW,boxH,3):ctx.rect(boxX,boxYStart,boxW,boxH); ctx.fill();
    ctx.fillStyle='#fff'; ctx.font='bold 10px Share Tech Mono'; ctx.textAlign='center';
    ctx.fillText(line1, infoX, boxYStart+14);
    ctx.font='9px Share Tech Mono';
    ctx.fillText(line2, infoX, boxYStart+28);
  }

  // ── "More history" hint — shown when older bars exist to the left ──
  if (TV.view.start > 0) {
    ctx.fillStyle = 'rgba(0,212,255,0.5)';
    ctx.font = '9px Share Tech Mono';
    ctx.textAlign = 'left';
    // 'more bars' indicator removed
  }

  // ── Current price line ──
  const cur=TV.data.currentPrice||sl[sl.length-1];
  if(cur&&cur>=minV&&cur<=maxV){
    const cy=yOf(cur);
    const prevC = sl.length>1 ? sl[sl.length-2] : cur;
    const curCol = cur >= prevC ? '#089981' : '#f23645';
    ctx.strokeStyle=curCol; ctx.lineWidth=1; ctx.setLineDash([2,3]);
    ctx.beginPath();ctx.moveTo(PAD.l,cy);ctx.lineTo(W-PAD.r,cy);ctx.stroke();
    ctx.setLineDash([]);
    // Price tag on right axis
    const priceStr=cur.toLocaleString('en-IN',{maximumFractionDigits:2});
    const tagW=Math.max(50, priceStr.length*7+12);
    ctx.fillStyle=curCol;
    ctx.fillRect(W-PAD.r, cy-10, PAD.r, 20);
    ctx.fillStyle='#ffffff'; ctx.font='bold 11px -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif'; ctx.textAlign='left';
    ctx.fillText(priceStr, W-PAD.r+6, cy+4);
  }

  // ── Crosshair ──
  if(TV.crosshair.barIdx>=0 && TV.crosshair.barIdx<N){
    const ci=TV.crosshair.barIdx, cx=xOf(ci);
    const cv=sl[ci]||0;
    const dateStr = dl[ci] || '';

    ctx.strokeStyle='rgba(19,23,34,0.4)'; ctx.lineWidth=0.5; ctx.setLineDash([3,3]);
    // Vertical line
    ctx.beginPath();ctx.moveTo(cx,PAD.t);ctx.lineTo(cx,PAD.t+cH);ctx.stroke();
    // Horizontal line
    if(cv>=minV&&cv<=maxV){
      const cy2=yOf(cv);
      ctx.beginPath();ctx.moveTo(PAD.l,cy2);ctx.lineTo(W-PAD.r,cy2);ctx.stroke();
      ctx.setLineDash([]);
      // Price tag on right Y-axis
      ctx.fillStyle='#131722';
      ctx.fillRect(W-PAD.r, cy2-10, PAD.r+24, 20);
      ctx.fillStyle='#ffffff'; ctx.font='11px -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif'; ctx.textAlign='left';
      ctx.fillText(cv.toFixed(2), W-PAD.r+6, cy2+4);
    }
    ctx.setLineDash([]);

    // ── X-axis date label at crosshair position (TradingView style) ──
    if (dateStr) {
      const MONTHS2 = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      const yr2  = dateStr.slice(0,4);
      const mo2  = parseInt(dateStr.slice(5,7)) - 1;
      const dy2  = dateStr.slice(8,10);
      const dayNames = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
      const dateObj  = new Date(dateStr);
      const dayName  = isNaN(dateObj) ? '' : dayNames[dateObj.getDay()];
      const label    = `${dayName} ${dy2} ${MONTHS2[mo2]} '${yr2.slice(2)}`;
      ctx.font = '11px -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif';
      const labelW   = ctx.measureText(label).width + 16;
      const lx = Math.max(PAD.l + labelW/2 + 2, Math.min(W - PAD.r - labelW/2 - 2, cx));
      ctx.fillStyle = '#131722';
      ctx.fillRect(lx - labelW/2, H - PAD.b, labelW, 20);
      ctx.fillStyle = '#ffffff'; ctx.textAlign = 'center';
      ctx.fillText(label, lx, H - PAD.b + 14);
    }

    // ── FII tooltip on crosshair ──
    if (TV.indicators.fii && TV.fiiData && dateStr) {
      const fiiLines = getFIITooltip(dateStr);
      if (fiiLines && fiiLines.length) {
        const boxW   = 280;
        const lineH  = 13;
        const boxH   = fiiLines.length * lineH + 12;
        const boxX   = Math.min(cx + 10, W - PAD.r - boxW - 4);
        const boxY   = PAD.t + 6;
        ctx.fillStyle   = 'rgba(6,12,20,0.92)';
        ctx.strokeStyle = 'rgba(204,136,255,0.6)';
        ctx.lineWidth   = 1;
        ctx.beginPath();
        ctx.roundRect
          ? ctx.roundRect(boxX, boxY, boxW, boxH, 3)
          : ctx.rect(boxX, boxY, boxW, boxH);
        ctx.fill(); ctx.stroke();
        ctx.textAlign = 'left';
        fiiLines.forEach((line, li) => {
          const isHeader = li === 0;
          ctx.fillStyle = isHeader ? '#cc88ff' : '#8ab0c8';
          ctx.font = `${isHeader ? 'bold ' : ''}${isHeader ? 8 : 7.5}px Share Tech Mono`;
          ctx.fillText(line.slice(0, 42), boxX + 7, boxY + 10 + li * lineH);
        });
      }
    }
  }

  // ── Update indicator values row (separate div, not on canvas) ──
  const indValRow = document.getElementById('tv-ind-values');
  const smaValsEl = document.getElementById('tv-sma-vals');
  const bbValsEl  = document.getElementById('tv-bb-vals');
  const rsiValsEl = document.getElementById('tv-rsi-vals');
  let hasIndVals = false;

  if(TV.indicators.sma && smaValsEl){
    const cols=['#7FFFD4','#B5B5FF','#DEB887'];
    const smaHtml = TV.params.smaP.map((p,pi)=>{
      const smaArr=calcSMA(closes,p).slice(start,end);
      const last=smaArr.filter(v=>v).pop();
      return last?`<span style="color:${cols[pi]};margin-right:12px;">SMA${p}:<b>${last.toFixed(0)}</b></span>`:'';
    }).filter(Boolean).join('');
    smaValsEl.innerHTML = smaHtml;
    if(smaHtml) hasIndVals=true;
  } else if(smaValsEl) smaValsEl.innerHTML='';

  const emaValsEl = document.getElementById('tv-ema-vals');
  if(TV.indicators.ema && emaValsEl){
    const cols=['#ff8800','#00ff88','#ff3355'];
    const emaHtml = TV.params.emaP.map((p,pi)=>{
      const emaArr=calcEMA(closes,p).slice(start,end);
      const last=emaArr.filter(v=>v).pop();
      return last?`<span style="color:${cols[pi]};margin-right:12px;">EMA${p}:<b>${last.toFixed(0)}</b></span>`:'';
    }).filter(Boolean).join('');
    emaValsEl.innerHTML = emaHtml;
    if(emaHtml) hasIndVals=true;
  } else if(emaValsEl) emaValsEl.innerHTML='';

  if(TV.indicators.bb && bbValsEl){
    const bb=calcBB(closes,TV.params.bbP,TV.params.bbStd).slice(start,end);
    const last=bb.filter(b=>b.mid).pop();
    if(last){
      bbValsEl.innerHTML=`<span style="color:#cc88ff">BB:</span><span style="color:#cc88ff88;margin-right:6px;">${last.upper?.toFixed(0)||'—'}</span><span style="color:#cc88ff">${last.mid?.toFixed(0)||'—'}</span><span style="color:#cc88ff88;margin-left:6px;">${last.lower?.toFixed(0)||'—'}</span>`;
      hasIndVals=true;
    }
  } else if(bbValsEl) bbValsEl.innerHTML='';

  if(TV.indicators.rsi && rsiValsEl){
    const rsiArr=calcRSI(closes,TV.params.rsiP).slice(start,end);
    const last=rsiArr.filter(v=>v!==null).pop();
    if(last!==undefined){
      const rc=last>TV.params.rsiOB?'#ef5350':last<TV.params.rsiOS?'#26a69a':'#ffcc00';
      rsiValsEl.innerHTML=`<span style="color:${rc}">RSI(${TV.params.rsiP}):<b>${last.toFixed(1)}</b></span>`;
      hasIndVals=true;
    }
  } else if(rsiValsEl) rsiValsEl.innerHTML='';

  if(indValRow) indValRow.style.display = hasIndVals ? 'block' : 'none';

  // ── Sub panels ──
  if(TV.indicators.vol)  tvDrawVolume(volumes,starts=start,end,W);
  if(TV.indicators.rsi)  tvDrawRSI(closes,start,end,W);
  if(TV.indicators.macd) tvDrawMACD(closes,start,end,W);
  if(TV.indicators.adx)  tvDrawADX(highs,lows,closes,start,end,W);
  if (typeof window.tvOnRedraw === 'function') {
    try { window.tvOnRedraw(); } catch(e) {}
  }
}

function tvDrawSubBg(ctx,W,H,PAD,label,col){
  ctx.fillStyle='#ffffff'; ctx.fillRect(0,0,W,H);
  ctx.lineWidth=0.5;
  for(let i=0;i<=4;i++){const y=PAD.t+(i/4)*(H-PAD.t-PAD.b);ctx.strokeStyle='rgba(19,23,34,0.05)';ctx.beginPath();ctx.moveTo(PAD.l,y);ctx.lineTo(W-PAD.r,y);ctx.stroke();}
  ctx.fillStyle=col||'#131722'; ctx.font='11px -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif'; ctx.textAlign='left';
  ctx.fillText(label, PAD.l+6, 14);
}

function tvDrawVolume(volumes,start,end,W){
  const vl=volumes.slice(start,end), cl=TV.data.closes.slice(start,end), N=vl.length;
  const _volCvs=document.getElementById('vol-canvas'); const H=_volCvs?(_volCvs.offsetHeight||80):80;
  const ctx=tvSetup('vol-canvas',W,H); if(!ctx)return;
  const PAD={t:14,r:68,b:14,l:8};
  tvDrawSubBg(ctx,W,H,PAD,'VOL','#131722');
  const cW=W-PAD.l-PAD.r,cH=H-PAD.t-PAD.b;
  const maxV=Math.max(...vl.filter(Boolean))||1;
  const slotW=cW/N, bW=Math.max(1,Math.min(20,Math.floor(slotW*0.8)));
  vl.forEach((v,i)=>{
    if(!v)return;
    const bull=i>0?cl[i]>=cl[i-1]:true;
    const bh=Math.max(1,(v/maxV)*cH), x=PAD.l+(i+0.5)*slotW, y=PAD.t+cH-bh;
    ctx.fillStyle=bull?'rgba(8,153,129,0.5)':'rgba(242,54,69,0.5)';
    ctx.fillRect(x-bW/2,y,bW,bh);
  });
  ctx.fillStyle='#131722'; ctx.font='11px -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif'; ctx.textAlign='left';
  ctx.fillText((maxV/1e6).toFixed(1)+'M', W-PAD.r+6, PAD.t+8);
}

function tvDrawRSI(closes,start,end,W){
  const rsi=calcRSI(closes,TV.params.rsiP).slice(start,end), N=rsi.length;
  const OB=TV.params.rsiOB, OS=TV.params.rsiOS;
  const _rsiCvs=document.getElementById('rsi-canvas'); const H=_rsiCvs?(_rsiCvs.offsetHeight||100):100;
  const ctx=tvSetup('rsi-canvas',W,H); if(!ctx)return;
  const PAD={t:14,r:68,b:14,l:8};
  tvDrawSubBg(ctx,W,H,PAD,'RSI('+TV.params.rsiP+')','#b22833');
  const cW=W-PAD.l-PAD.r, cH=H-PAD.t-PAD.b;
  const xS=i=>PAD.l+(i/(N-1||1))*cW, yS=v=>PAD.t+cH*(1-v/100);
  // OB/OS zones
  ctx.fillStyle='rgba(242,54,69,0.07)'; ctx.fillRect(PAD.l,yS(100),cW,yS(OB)-yS(100));
  ctx.fillStyle='rgba(8,153,129,0.07)'; ctx.fillRect(PAD.l,yS(OS),cW,yS(0)-yS(OS));
  // Level lines
  [[OB,'rgba(242,54,69,0.45)'],[OS,'rgba(8,153,129,0.45)'],[50,'rgba(19,23,34,0.08)']].forEach(([v,c])=>{
    const y=yS(v); ctx.strokeStyle=c; ctx.lineWidth=0.7; ctx.setLineDash([3,3]);
    ctx.beginPath();ctx.moveTo(PAD.l,y);ctx.lineTo(PAD.l+cW,y);ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle=c.replace('0.45','0.8').replace('0.08','0.4'); ctx.font='11px -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif'; ctx.textAlign='left';
    ctx.fillText(v, W-PAD.r+6, y+4);
  });
  ctx.strokeStyle='#7e57c2'; ctx.lineWidth=1.4; ctx.beginPath(); let f=true;
  rsi.forEach((v,i)=>{if(v===null)return;f?ctx.moveTo(xS(i),yS(v)):ctx.lineTo(xS(i),yS(v));f=false;});
  ctx.stroke();
  const last=rsi.filter(v=>v!==null).pop();
  if(last){const lc=last>OB?'#f23645':last<OS?'#089981':'#7e57c2';ctx.fillStyle=lc;ctx.font='bold 11px -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif';ctx.textAlign='left';ctx.fillText(last.toFixed(1),W-PAD.r+6,yS(last)+4);}
}

function tvDrawMACD(closes,start,end,W){
  const {macdLine,signalLine,histogram}=calcMACD(closes,TV.params.macdFast,TV.params.macdSlow,TV.params.macdSig);
  const ml=macdLine.slice(start,end),sl=signalLine.slice(start,end),hl=histogram.slice(start,end),N=ml.length;
  const vals=[...ml,...sl,...hl].filter(v=>v!==null);
  if(!vals.length)return;
  const minV=Math.min(...vals),maxV=Math.max(...vals);
  const _macdCvs=document.getElementById('macd-canvas'); const H=_macdCvs?(_macdCvs.offsetHeight||100):100;
  const ctx=tvSetup('macd-canvas',W,H); if(!ctx)return;
  const PAD={t:14,r:68,b:14,l:8};
  tvDrawSubBg(ctx,W,H,PAD,'MACD('+TV.params.macdFast+','+TV.params.macdSlow+','+TV.params.macdSig+')','#2962ff');
  const cW=W-PAD.l-PAD.r, cH=H-PAD.t-PAD.b;
  const xS=i=>PAD.l+(i/(N-1||1))*cW, yS=v=>PAD.t+cH*(1-(v-minV)/(maxV-minV||1));
  const z=yS(0);
  ctx.strokeStyle='rgba(19,23,34,0.1)'; ctx.lineWidth=0.5;
  ctx.beginPath();ctx.moveTo(PAD.l,z);ctx.lineTo(PAD.l+cW,z);ctx.stroke();
  const slotW=cW/N, bW=Math.max(1,Math.min(20,Math.floor(slotW*0.8)));
  hl.forEach((v,i)=>{if(v===null)return;const y=yS(v),bh=Math.abs(y-z),x=PAD.l+(i+0.5)*slotW;ctx.fillStyle=v>=0?'rgba(8,153,129,0.55)':'rgba(242,54,69,0.55)';ctx.fillRect(x-bW/2,Math.min(y,z),bW,Math.max(1,bh));});
  [[ml,'#2962ff',1.4],[sl,'#ff9800',1]].forEach(([arr,col,lw])=>{ctx.strokeStyle=col;ctx.lineWidth=lw;ctx.beginPath();let f=true;arr.forEach((v,i)=>{if(v===null)return;f?ctx.moveTo(xS(i),yS(v)):ctx.lineTo(xS(i),yS(v));f=false;});ctx.stroke();});
  const lm=ml.filter(v=>v!==null).pop(),ls=sl.filter(v=>v!==null).pop();
  if(lm){ctx.fillStyle='#2962ff';ctx.font='11px -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif';ctx.textAlign='left';ctx.fillText(lm.toFixed(1),W-PAD.r+6,yS(lm)+4);}
}

function tvDrawADX(highs,lows,closes,start,end,W){
  const {adx,diPlus,diMinus}=calcADX(highs,lows,closes,TV.params.adxP);
  const al=adx.slice(start,end),dpl=diPlus.slice(start,end),dml=diMinus.slice(start,end),N=al.length;
  const _adxCvs=document.getElementById('adx-canvas'); const H=_adxCvs?(_adxCvs.offsetHeight||100):100;
  const ctx=tvSetup('adx-canvas',W,H); if(!ctx)return;
  const PAD={t:14,r:68,b:14,l:8};
  tvDrawSubBg(ctx,W,H,PAD,'ADX('+TV.params.adxP+')','#f23645');
  const cW=W-PAD.l-PAD.r, cH=H-PAD.t-PAD.b;
  const xS=i=>PAD.l+(i/(N-1||1))*cW, yS=v=>PAD.t+cH*(1-Math.min(v,100)/100);
  const y25=yS(25);
  ctx.strokeStyle='rgba(19,23,34,0.12)'; ctx.lineWidth=0.5; ctx.setLineDash([3,3]);
  ctx.beginPath();ctx.moveTo(PAD.l,y25);ctx.lineTo(PAD.l+cW,y25);ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle='rgba(19,23,34,0.3)';ctx.font='11px -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif';ctx.textAlign='left';ctx.fillText('25',W-PAD.r+6,y25+4);
  [[al,'#f23645',1.5,'ADX'],[dpl,'#089981',1,'+DI'],[dml,'#ff9800',1,'-DI']].forEach(([arr,col,lw,lbl])=>{
    ctx.strokeStyle=col;ctx.lineWidth=lw;ctx.beginPath();let f=true;
    arr.forEach((v,i)=>{if(v===null)return;f?ctx.moveTo(xS(i),yS(v)):ctx.lineTo(xS(i),yS(v));f=false;});
    ctx.stroke();
  });
  const la=al.filter(v=>v!==null).pop();
  if(la){ctx.fillStyle='#f23645';ctx.font='bold 11px -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif';ctx.textAlign='left';ctx.fillText(la.toFixed(1),W-PAD.r+6,yS(la)+4);}
}

// ── Zoom / Pan button helpers ─────────────────────────────────────
function tvZoom(dir) {
  // dir=-1 zoom in (fewer bars), dir=1 zoom out (more bars)
  if(!TV.data)return;
  const N=TV.view.end-TV.view.start;
  const delta=Math.max(3,Math.round(N*0.15));
  const mid=Math.round((TV.view.start+TV.view.end)/2);
  const total=TV.data.closes.length;
  if(dir<0){
    // zoom in around centre
    TV.view.start=Math.min(TV.view.start+delta, mid-5);
    TV.view.end=Math.max(TV.view.end-delta, mid+5);
  } else {
    // zoom out
    TV.view.start=Math.max(0,TV.view.start-delta);
    TV.view.end=Math.min(total,TV.view.end+delta);
  }
  if(TV.view.end-TV.view.start<5) TV.view.end=TV.view.start+5;
  tvRedraw();
}

function tvPan(dir) {
  // dir=-1 go left (older), dir=1 go right (newer)
  if(!TV.data)return;
  const N=TV.view.end-TV.view.start;
  const step=Math.max(1,Math.round(N*0.2));
  const total=TV.data.closes.length;
  let ns=TV.view.start+dir*step, ne=TV.view.end+dir*step;
  if(ns<0){ne-=ns;ns=0;}
  if(ne>total){ns-=(ne-total);ne=total;}
  TV.view.start=Math.max(0,ns); TV.view.end=Math.min(total,ne);
  tvRedraw();
}

function tvResetView() {
  if(!TV.data)return;
  const total=TV.data.closes.length;
  TV.view.start=Math.max(0,total-252);
  TV.view.end=total;
  tvRedraw();
}

// ── Sub-panel resize for main chart ──────────────────────────────
let _tvResizeState = null;
function tvStartSubResize(e, panelId) {
  e.preventDefault(); e.stopPropagation();
  const cvs = document.getElementById(panelId+'-canvas');
  if (!cvs) return;
  _tvResizeState = {panelId, startY:e.clientY, startH:cvs.offsetHeight};
  document.body.style.cursor='row-resize'; document.body.style.userSelect='none';
  const onMove = (ev) => {
    if (!_tvResizeState) return;
    const newH = Math.max(40, Math.min(300, _tvResizeState.startH + (ev.clientY - _tvResizeState.startY)));
    const c2 = document.getElementById(_tvResizeState.panelId+'-canvas');
    if (c2) { c2.style.height=newH+'px'; c2.height=newH; }
    if (TV.data) tvRedraw();
  };
  const onUp = () => {
    _tvResizeState=null;
    document.body.style.cursor=''; document.body.style.userSelect='';
    document.removeEventListener('mousemove',onMove);
    document.removeEventListener('mouseup',onUp);
    if (TV.data) tvRedraw();
  };
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
}

// ════════════════════════════════════════════════════════════════════
// BIG PLAYERS (FII / DII / INSTITUTIONAL) INDICATOR
// ════════════════════════════════════════════════════════════════════

async function tvLoadFIIData() {
  const sym = (document.getElementById('chart-sym') || document.getElementById('simons-sym') || {}).value;
  if (!sym) return;
  try {
    TV.fiiData = await api('institutional', { symbol: sym, days: 730 });
    console.log('[FII] Data loaded:', Object.keys(TV.fiiData.deal_map||{}).length, 'deal dates,',
      Object.keys(TV.fiiData.anomaly_map||{}).length, 'anomaly dates');
    if (TV.data) tvRedraw();
  } catch(e) {
    console.warn('[FII] Load error:', e.message);
    TV.fiiData = { deal_map:{}, anomaly_map:{}, anomalies:[], deals:[], shareholding:[] };
    if (TV.data) tvRedraw();
  }
}

function drawFIIOverlay(ctx, W, H, PAD, xOf, yOf, dl, sl, hl, ll, ol, vl, start, end, candleW) {
  if (!TV.fiiData) return;
  const dealMap    = TV.fiiData.deal_map    || {};
  const anomalyMap = TV.fiiData.anomaly_map || {};
  const cH = H - PAD.t - PAD.b;

  // Signal colours
  const SIG_COLORS = {
    FII_BUY:          { bg:'rgba(0,255,136,0.13)', border:'rgba(0,255,136,0.7)', badge:'#00ff88', label:'F↑' },
    PARTIAL_BUY:      { bg:'rgba(0,255,136,0.06)', border:'rgba(0,255,136,0.4)', badge:'#00cc66', label:'f↑' },
    FII_SELL:         { bg:'rgba(255,51,85,0.13)',  border:'rgba(255,51,85,0.7)',  badge:'#ff3355', label:'F↓' },
    MIXED:            { bg:'rgba(0,212,255,0.08)',  border:'rgba(0,212,255,0.5)',  badge:'#00d4ff', label:'F±' },
    ACCUMULATION:     { bg:'rgba(0,255,136,0.07)', border:'rgba(0,255,136,0.3)', badge:'#00bb55', label:'A' },
    DISTRIBUTION:     { bg:'rgba(255,51,85,0.07)',  border:'rgba(255,51,85,0.3)',  badge:'#cc2244', label:'D' },
    BULL_SPIKE:       { bg:'rgba(0,255,136,0.10)', border:'rgba(0,255,136,0.5)', badge:'#00ff88', label:'B★' },
    BEAR_SPIKE:       { bg:'rgba(255,51,85,0.10)',  border:'rgba(255,51,85,0.5)',  badge:'#ff3355', label:'S★' },
    ABSORPTION:       { bg:'rgba(255,204,0,0.08)', border:'rgba(255,204,0,0.5)', badge:'#ffcc00', label:'⊕' },
  };

  const N = end - start;
  const slotW = (W - PAD.l - PAD.r) / N;
  const badgeH = 12;

  for (let i = 0; i < N; i++) {
    const date = dl[i];
    if (!date) continue;
    const x = xOf(i);

    const deal   = dealMap[date];
    const anomaly= anomalyMap[date];
    if (!deal && !anomaly) continue;

    // Priority: bulk/block deal > volume anomaly
    const sig = deal ? deal.signal : (anomaly ? anomaly.signal : null);
    if (!sig) continue;

    const col = SIG_COLORS[sig] || SIG_COLORS['MIXED'];
    const hw  = Math.max(candleW / 2 + 1, 3);

    // Highlight column behind candle
    ctx.fillStyle = col.bg;
    ctx.fillRect(x - hw, PAD.t, hw * 2, cH);

    // Vertical border lines on sides of column
    ctx.strokeStyle = col.border;
    ctx.lineWidth = 0.8;
    ctx.setLineDash([2, 3]);
    ctx.beginPath();
    ctx.moveTo(x - hw, PAD.t);
    ctx.lineTo(x - hw, PAD.t + cH);
    ctx.moveTo(x + hw, PAD.t);
    ctx.lineTo(x + hw, PAD.t + cH);
    ctx.stroke();
    ctx.setLineDash([]);

    // Badge above candle (only when bars are wide enough)
    if (slotW >= 5) {
      const candleTop = yOf(hl[i]);
      const badgeY    = Math.max(PAD.t + 2, candleTop - badgeH - 3);
      const label     = deal ? col.label : (col.label.length > 1 ? col.label : col.label.toLowerCase());

      // Badge pill
      const badgeW = Math.max(14, label.length * 6 + 6);
      ctx.fillStyle = col.badge + '22';
      ctx.strokeStyle = col.badge;
      ctx.lineWidth = 0.7;
      ctx.beginPath();
      ctx.roundRect
        ? ctx.roundRect(x - badgeW/2, badgeY, badgeW, badgeH, 2)
        : ctx.rect(x - badgeW/2, badgeY, badgeW, badgeH);
      ctx.fill(); ctx.stroke();

      ctx.fillStyle = col.badge;
      ctx.font = `bold ${slotW > 10 ? 8 : 7}px Share Tech Mono`;
      ctx.textAlign = 'center';
      ctx.fillText(label, x, badgeY + badgeH - 2);
    }

    // For bulk/block deals: show deal count dot at bottom
    if (deal && deal.deals && deal.deals.length > 0 && slotW >= 4) {
      const botY = PAD.t + cH - 6;
      ctx.beginPath();
      ctx.arc(x, botY, 3, 0, Math.PI * 2);
      ctx.fillStyle = col.badge;
      ctx.globalAlpha = 0.8;
      ctx.fill();
      ctx.globalAlpha = 1;
    }
  }
}

// FII legend overlay (shown when indicator is on, top-left corner)
function drawFIILegend(ctx, PAD) {
  const items = [
    { col:'#00ff88', label:'F↑  Bulk/Block Buy (FII/Inst.)' },
    { col:'#ff3355', label:'F↓  Bulk/Block Sell' },
    { col:'#00d4ff', label:'F±  Mixed Deals' },
    { col:'#00bb55', label:'A   Vol Anomaly — Accumulation' },
    { col:'#cc2244', label:'D   Vol Anomaly — Distribution' },
    { col:'#ffcc00', label:'⊕  Vol Anomaly — Absorption' },
    { col:'#00ff88', label:'B★  Bull Volume Spike' },
    { col:'#ff3355', label:'S★  Bear Volume Spike' },
  ];
  const x0 = PAD.l + 6, y0 = PAD.t + 6;
  const boxH = items.length * 14 + 10;
  ctx.fillStyle = 'rgba(6,15,22,0.82)';
  ctx.strokeStyle = 'rgba(204,136,255,0.3)';
  ctx.lineWidth = 0.8;
  ctx.fillRect(x0, y0, 210, boxH);
  ctx.strokeRect(x0, y0, 210, boxH);
  ctx.fillStyle = '#cc88ff';
  ctx.font = 'bold 8px Share Tech Mono';
  ctx.textAlign = 'left';
  ctx.fillText('BIG PLAYERS (FII/DII/INST.)', x0 + 8, y0 + 10);
  items.forEach((it, i) => {
    const y = y0 + 18 + i * 14;
    ctx.beginPath();
    ctx.arc(x0 + 14, y + 3, 3, 0, Math.PI * 2);
    ctx.fillStyle = it.col;
    ctx.fill();
    ctx.fillStyle = 'rgba(200,220,240,0.75)';
    ctx.font = '7.5px Share Tech Mono';
    ctx.fillText(it.label, x0 + 22, y + 6);
  });
}

// FII crosshair tooltip — called from tvRedraw crosshair section
function getFIITooltip(date) {
  if (!TV.fiiData) return null;
  const deal   = (TV.fiiData.deal_map    || {})[date];
  const anomaly= (TV.fiiData.anomaly_map || {})[date];
  if (!deal && !anomaly) return null;

  const lines = [];
  if (deal) {
    lines.push(`📦 ${deal.deals.length} deal(s) registered`);
    deal.deals.slice(0, 3).forEach(d => {
      lines.push(`  ${d.type==='BUY'?'🟢':'🔴'} ${d.client.slice(0,22)} ${d.type} ${(d.qty||0).toLocaleString()} @ ₹${d.price}`);
    });
    const net = (deal.buy_qty||0) - (deal.sell_qty||0);
    lines.push(`  Net: ${net > 0 ? '+' : ''}${net.toLocaleString()} shares`);
  }
  if (anomaly) {
    lines.push(`📊 Vol ${anomaly.vol_ratio}× avg — ${anomaly.signal} (${anomaly.candle_type})`);
  }
  return lines;
}

// ── Interaction ───────────────────────────────────────────────────
function tvSetupInteraction() {
  const cvs = document.getElementById('price-canvas');
  if (!cvs || TV._eventsAttached) return;
  TV._eventsAttached = true;

  function getBar(clientX) {
    const rect = cvs.getBoundingClientRect();
    const scaleX = cvs.width / rect.width;
    const relX = (clientX - rect.left) * scaleX - TV_PAD.l;
    const cW   = cvs.width - TV_PAD.l - TV_PAD.r;
    const N    = TV.view.end - TV.view.start;
    const slotW = cW / N;
    const i = (relX / slotW) - 0.5;
    return Math.max(0, Math.min(N-1, Math.round(i)));
  }

  function getCanvasXY(e) {
    const rect = cvs.getBoundingClientRect();
    const scaleX = cvs.width / rect.width;
    const scaleY = cvs.height / rect.height;
    return {
      xPx: (e.clientX - rect.left) * scaleX,
      yPx: (e.clientY - rect.top)  * scaleY
    };
  }

  // Mousemove — crosshair + infobar
  cvs.addEventListener('mousemove', e=>{
    // Always track mouse position for drawing tool previews
    TV._mousePos = getCanvasXY(e);
    if (TV.magnet && TV.data) {
      const bi = getBar(e.clientX);
      const ai = TV.view.start + bi;
      if (ai >= 0 && ai < TV.data.closes.length) {
        const rawP = tvPxToPrice(TV._mousePos.yPx);
        const snappedP = tvSnapToOHLC(ai, rawP);
        const {minV, maxV} = tvGetYRange();
        const cH = cvs.height - TV_PAD.t - TV_PAD.b;
        TV._mousePos.yPx = TV_PAD.t + cH * (1 - (snappedP - minV) / (maxV - minV));
      }
    }
    if(!TV.data)return;
    // Change cursor when hovering over Y axis area
    const rect0=cvs.getBoundingClientRect();
    const lx0=(e.clientX-rect0.left)*(cvs.width/rect0.width);
    if(lx0 > cvs.width - 68 && !TV.drag.active) { cvs.style.cursor='ns-resize'; }
    else if(!TV.drag.active && !TV.drag.yDrag) { cvs.style.cursor='crosshair'; }
    const bi=getBar(e.clientX);
    TV.crosshair.barIdx=bi;
    const ai=TV.view.start+bi;
    const d=TV.data;
    if(ai<d.dates.length){
      const o=d.opens[ai],h=d.highs[ai],l=d.lows[ai],c=d.closes[ai],v=d.volumes[ai];
      const chg=ai>0?((c-d.closes[ai-1])/d.closes[ai-1]*100).toFixed(2):'0.00';
      const col=parseFloat(chg)>=0?'#26a69a':'#ef5350';
      const bar=document.getElementById('tv-ohlcv-bar');
      if(bar) bar.innerHTML=
        `<span style="color:#4a7090">${d.dates[ai]}</span>  `
        +`<span style="color:#4a7090">O:<b style="color:#c8e0ed">${o?.toFixed(2)||'—'}</b></span>  `
        +`<span style="color:#4a7090">H:<b style="color:#26a69a">${h?.toFixed(2)||'—'}</b></span>  `
        +`<span style="color:#4a7090">L:<b style="color:#ef5350">${l?.toFixed(2)||'—'}</b></span>  `
        +`<span style="color:#4a7090">C:<b style="color:${col}">${c?.toFixed(2)||'—'}</b> <b style="color:${col}">(${chg}%)</b></span>  `
        +`<span style="color:#4a7090">V:<b style="color:#00d4ff">${v?(v/1e6).toFixed(2)+'M':'—'}</b></span>`;
        
      // Update Data Window in right panel if it exists
      const setTxt = (id, val) => { const el = document.getElementById(id); if (el && val !== undefined) el.textContent = val; };
      setTxt('dw-date', d.dates[ai] || '—');
      setTxt('dw-open', o ? o.toFixed(2) : '—');
      setTxt('dw-high', h ? h.toFixed(2) : '—');
      setTxt('dw-low', l ? l.toFixed(2) : '—');
      setTxt('dw-close', c ? c.toFixed(2) : '—');
      const fmtV = (vol) => {
        if (!vol) return '—';
        if (vol >= 1e7) return (vol/1e7).toFixed(2) + 'Cr';
        if (vol >= 1e5) return (vol/1e5).toFixed(2) + 'L';
        if (vol >= 1000) return (vol/1000).toFixed(1) + 'K';
        return vol.toString();
      };
      setTxt('dw-vol', fmtV(v));

      // Update Astro Panel in right panel if ephemeris exists
      if (TV.ephemerisData) {
        const dateStr = d.dates[ai];
        const ephem = TV.ephemerisData[dateStr];
        const hoverDateEl = document.getElementById('astro-hover-date');
        const hoverCoordsEl = document.getElementById('astro-hover-coords');
        if (hoverDateEl) hoverDateEl.textContent = dateStr;
        if (hoverCoordsEl) {
          if (ephem) {
            const planetNames = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu"];
            hoverCoordsEl.innerHTML = planetNames.map(p => {
              const lon = ephem[p + '_lon'] || 0;
              const sign = ephem[p + '_sign'] || '';
              const speed = ephem[p + '_speed'] || 0;
              const retro = ephem[p + '_retro'] ? 'Rx' : 'Dir';
              
              const deg = Math.floor(lon);
              const min = Math.floor((lon - deg) * 60);
              
              return `<div style="display:flex;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,0.03);padding:2px 0;font-size:11px;">
                <span style="color:#ffffff;font-weight:bold;">${p}</span>
                <span style="color:var(--cyan);">${deg}°${min}' (${sign})</span>
                <span style="color:${speed < 0 ? '#ff3355' : 'var(--tv-color-text-secondary)'};">${speed.toFixed(2)}°/d [${retro}]</span>
              </div>`;
            }).join('');
          } else {
            hoverCoordsEl.innerHTML = '<div style="color:var(--tv-color-text-secondary);">No ephemeris for this date</div>';
          }
        }
      }

      // Update SMA values in indicator row + stat cards on hover
      const smaEl=document.getElementById('tv-sma-vals');
      const smaIds=['stat-sma20','stat-sma50','stat-sma200'];
      const smaCols=['#7FFFD4','#B5B5FF','#DEB887'];
      if(TV.indicators.sma){
        const smaHtmlParts=TV.params.smaP.map((p,pi)=>{
          const arr=calcSMA(d.closes,p); const v2=arr[ai];
          // Also update stat card if period matches default
          if(p===20||p===50||p===200){
            const cardId=p===20?'stat-sma20':p===50?'stat-sma50':'stat-sma200';
            const cardEl=document.getElementById(cardId);
            if(cardEl&&v2) cardEl.textContent=v2.toFixed(0);
          }
          return v2?`<span style="color:${smaCols[pi]};margin-right:12px;">SMA${p}:<b>${v2.toFixed(0)}</b></span>`:'';
        }).filter(Boolean).join('');
        if(smaEl) smaEl.innerHTML=smaHtmlParts;
        const indValRow=document.getElementById('tv-ind-values');
        if(indValRow&&smaHtmlParts) indValRow.style.display='block';
      }
    }
    tvRedraw();
  });

  cvs.addEventListener('mouseleave',()=>{
    TV.crosshair.barIdx=-1;
    const bar=document.getElementById('tv-ohlcv-bar');
    if(bar&&TV.data){
      const d=TV.data,last=d.closes.length-1;
      const chg=last>0?((d.closes[last]-d.closes[last-1])/d.closes[last-1]*100).toFixed(2):'0.00';
      const col=parseFloat(chg)>=0?'#26a69a':'#ef5350';
      bar.innerHTML=`CMP: <b style="color:${col}">${d.closes[last]?.toFixed(2)||'—'}</b> <b style="color:${col}">(${chg}%)</b>`;
      
      // Reset Data Window to last candle
      const setTxt = (id, val) => { const el = document.getElementById(id); if (el && val !== undefined) el.textContent = val; };
      setTxt('dw-date', d.dates[last] || '—');
      setTxt('dw-open', d.opens[last] ? d.opens[last].toFixed(2) : '—');
      setTxt('dw-high', d.highs[last] ? d.highs[last].toFixed(2) : '—');
      setTxt('dw-low', d.lows[last] ? d.lows[last].toFixed(2) : '—');
      setTxt('dw-close', d.closes[last] ? d.closes[last].toFixed(2) : '—');
      const fmtV = (vol) => {
        if (!vol) return '—';
        if (vol >= 1e7) return (vol/1e7).toFixed(2) + 'Cr';
        if (vol >= 1e5) return (vol/1e5).toFixed(2) + 'L';
        if (vol >= 1000) return (vol/1000).toFixed(1) + 'K';
        return vol.toString();
      };
      setTxt('dw-vol', fmtV(d.volumes[last]));
    }
    tvRedraw();
  });

  // Drawing tool clicks
  cvs.addEventListener('click', e=>{
    const {xPx, yPx} = getCanvasXY(e);
    tvHandleDrawClick(xPx, yPx);
  });

  // Context Menu
  cvs.addEventListener('contextmenu', e => {
    e.preventDefault();
    const menu = document.getElementById('tv-context-menu');
    if (!menu) return;
    menu.style.display = 'block';
    let x = e.pageX;
    let y = e.pageY;
    if (x + 180 > window.innerWidth) x = window.innerWidth - 180;
    if (y + 150 > window.innerHeight) y = window.innerHeight - 150;
    menu.style.left = x + 'px';
    menu.style.top = y + 'px';
    
    const hideMenu = (evt) => {
      if (!menu.contains(evt.target)) {
        menu.style.display = 'none';
        document.removeEventListener('click', hideMenu);
        document.removeEventListener('contextmenu', hideMenu);
      }
    };
    setTimeout(() => {
      document.addEventListener('click', hideMenu);
      document.addEventListener('contextmenu', hideMenu);
    }, 10);
  });

  // _mousePos is updated in the main mousemove handler below

  // Drag to pan — left 72px = Y-axis drag, rest = X-axis pan
  cvs.addEventListener('mousedown',e=>{
    const rect=cvs.getBoundingClientRect();
    const localX=(e.clientX-rect.left)*(cvs.width/rect.width);
    const PAD_R=68;

    if (TV.tool === 'brush' && !TV.lockDrawings) {
      e.stopPropagation();
      const my = (e.clientY - rect.top) * (cvs.height / rect.height);
      const rawPrice = tvPxToPrice(my);
      const barIdx = tvPxToBarIdx(localX);
      const price = tvSnapToOHLC(barIdx, rawPrice);
      TV.drawState = {type:'brush', points:[{barIdx, price}], color:'#4caf50'};
      TV._brushDrawing = true;
      return;
    }

    // ── Check if clicking a handle on a selected drawing ──
    if (TV.tool === 'cursor' && TV.selectedDrawing !== null) {
      const d = TV.drawings[TV.selectedDrawing];
      if (d) {
        const {start, end} = TV.view;
        const N = end - start;
        const cW2 = cvs.width - TV_PAD.l - TV_PAD.r;
        const slotW2 = cW2 / N;
        const xOf2 = i => TV_PAD.l + (i - start + 0.5) * slotW2;
        const {minV, maxV} = tvGetYRange();
        const cH2 = cvs.height - TV_PAD.t - TV_PAD.b;
        const yOf2 = v => TV_PAD.t + cH2 * (1-(v-minV)/(maxV-minV));
        const pxToPrice = py => minV + (1-(py-TV_PAD.t)/cH2)*(maxV-minV);
        const pxToBar   = px => Math.round((px - TV_PAD.l) / slotW2 - 0.5) + start;
        const mx = localX;
        const my = (e.clientY - rect.top) * (cvs.height / rect.height);
        const HIT = 12;
        let handle = null;

        if (d.type === 'trendline' || d.type === 'fib') {
          const hx1=xOf2(d.p1.barIdx), hy1=yOf2(d.p1.price);
          const hx2=xOf2(d.p2.barIdx), hy2=yOf2(d.p2.price);
          if (Math.hypot(mx-hx1,my-hy1)<HIT) handle='p1';
          else if (Math.hypot(mx-hx2,my-hy2)<HIT) handle='p2';
          else {
            // Click on line body — move whole line
            const len=Math.hypot(hx2-hx1,hy2-hy1);
            const dist=len>0?Math.abs((hy2-hy1)*mx-(hx2-hx1)*my+hx2*hy1-hy2*hx1)/len:Infinity;
            if (dist < HIT) handle='body';
          }
        } else if (d.type === 'rect' && d.p2) {
          const hx1=xOf2(d.p1.barIdx),hy1=yOf2(d.p1.price);
          const hx2=xOf2(d.p2.barIdx),hy2=yOf2(d.p2.price);
          if (Math.hypot(mx-hx1,my-hy1)<HIT) handle='p1';
          else if (Math.hypot(mx-hx2,my-hy2)<HIT) handle='p2';
          else if (Math.hypot(mx-hx1,my-hy2)<HIT) handle='p1y2';
          else if (Math.hypot(mx-hx2,my-hy1)<HIT) handle='p2y1';
          else {
            const inX=mx>=Math.min(hx1,hx2)&&mx<=Math.max(hx1,hx2);
            const inY=my>=Math.min(hy1,hy2)&&my<=Math.max(hy1,hy2);
            if(inX&&inY) handle='body';
          }
        } else if (d.type === 'hline') {
          const hy=yOf2(d.price);
          if (Math.abs(my-hy)<HIT) handle='body';
        } else if (d.type === 'vline') {
          const hx=xOf2(d.barIdx);
          if (Math.abs(mx-hx)<HIT) handle='body';
        } else if (d.type === 'text') {
          const hx=xOf2(d.barIdx), hy=yOf2(d.price);
          if (Math.hypot(mx-hx,my-hy)<HIT*2) handle='body';
        }

        if (handle) {
          e.stopPropagation();
          TV.editDrag = {
            idx: TV.selectedDrawing, handle,
            startX:e.clientX, startY:e.clientY,
            orig: JSON.parse(JSON.stringify(d)),
            pxToPrice, pxToBar, xOf2, yOf2
          };
          cvs.style.cursor = handle==='body' ? 'move' : 'crosshair';
          return;
        }
      }
    }

    if(localX > cvs.width - PAD_R) {
      TV.drag.active=false; TV.drag.yDrag=true; TV.drag.startY=e.clientY;
      const {minV, maxV} = tvGetYRange();
      TV.drag.startMinV=minV; TV.drag.startMaxV=maxV;
      cvs.style.cursor='ns-resize';
    } else {
      TV.drag.active=true; TV.drag.yDrag=false; TV.drag.startX=e.clientX;
      TV.drag.startStart=TV.view.start; TV.drag.startEnd=TV.view.end;
      cvs.style.cursor='grabbing';
    }
  });
  window.addEventListener('mouseup',()=>{
    if (TV._brushDrawing && TV.drawState) {
      TV.drawings.push({...TV.drawState, id:Date.now()});
      TV.drawState = null;
      TV._brushDrawing = false;
      tvSaveChartState();
      tvRedraw();
      tvUpdateObjectTree();
      if (!TV.stayInDrawingMode) tvSetTool('cursor');
    }
    TV.editDrag=null;TV.drag.active=false;TV.drag.yDrag=false;
    const c=document.getElementById('price-canvas');
    if(c)c.style.cursor='crosshair';
  });
  window.addEventListener('mousemove',e=>{
    if (TV._brushDrawing && TV.drawState) {
      const cvs = document.getElementById('price-canvas');
      if (cvs) {
        const rect2 = cvs.getBoundingClientRect();
        const mx = (e.clientX - rect2.left)*(cvs.width/rect2.width);
        const my = (e.clientY - rect2.top)*(cvs.height/rect2.height);
        const rawP = tvPxToPrice(my);
        const barIdx = tvPxToBarIdx(mx);
        const price = tvSnapToOHLC(barIdx, rawP);
        const lastPt = TV.drawState.points[TV.drawState.points.length - 1];
        if (!lastPt || lastPt.barIdx !== barIdx || Math.abs(lastPt.price - price) > 0.001) {
          TV.drawState.points.push({barIdx, price});
          tvRedraw();
        }
      }
      return;
    }
    // ── Handle endpoint/body dragging of selected drawing ──
    if (TV.editDrag) {
      const ed = TV.editDrag;
      const d  = TV.drawings[ed.idx];
      if (!d) { TV.editDrag=null; return; }
      const cvs2 = document.getElementById('price-canvas');
      const rect2 = cvs2.getBoundingClientRect();
      const mx = (e.clientX - rect2.left)*(cvs2.width/rect2.width);
      const my = (e.clientY - rect2.top)*(cvs2.height/rect2.height);
      const newPrice = ed.pxToPrice(my);
      const newBar   = ed.pxToBar(mx);
      const dx = e.clientX - ed.startX; // CSS px delta for body moves
      const dy = e.clientY - ed.startY;

      if (d.type === 'trendline' || d.type === 'fib') {
        if (ed.handle==='p1') { d.p1 = {...d.p1, barIdx:newBar, price:newPrice, xPx:mx, yPx:my}; }
        else if (ed.handle==='p2') { d.p2 = {...d.p2, barIdx:newBar, price:newPrice, xPx:mx, yPx:my}; }
        else { // body — move whole line
          const barDelta = newBar - ed.orig.p1.barIdx - Math.round(ed._bodyBarOff||0);
          if (!ed._bodyStart) { ed._bodyStart=true; ed._startBar1=d.p1.barIdx; ed._startBar2=d.p2.barIdx; ed._startP1=d.p1.price; ed._startP2=d.p2.price; }
          const bDelta = newBar - ed.pxToBar(ed.startX*(cvs2.width/rect2.width)||mx);
          const priceDelta = newPrice - ed.pxToPrice(ed.startY*(cvs2.height/rect2.height)||my);
          d.p1 = {...d.p1, barIdx:ed._startBar1+bDelta, price:ed._startP1+priceDelta};
          d.p2 = {...d.p2, barIdx:ed._startBar2+bDelta, price:ed._startP2+priceDelta};
        }
      } else if (d.type === 'hline') {
        d.price = newPrice;
      } else if (d.type === 'vline') {
        d.barIdx = newBar;
      } else if (d.type === 'rect' && d.p2) {
        if (ed.handle==='p1') { d.p1={...d.p1,barIdx:newBar,price:newPrice}; }
        else if (ed.handle==='p2') { d.p2={...d.p2,barIdx:newBar,price:newPrice}; }
        else if (ed.handle==='p1y2') { d.p1={...d.p1,barIdx:newBar}; d.p2={...d.p2,price:newPrice}; }
        else if (ed.handle==='p2y1') { d.p2={...d.p2,barIdx:newBar}; d.p1={...d.p1,price:newPrice}; }
        else { // body
          if (!ed._bodyStart) { ed._bodyStart=true; ed._startBar1=d.p1.barIdx; ed._startBar2=d.p2.barIdx; ed._startP1=d.p1.price; ed._startP2=d.p2.price; }
          const bD=newBar-ed.pxToBar((e.clientX-rect2.left-dx)*(cvs2.width/rect2.width));
          const pD=newPrice-ed.pxToPrice((e.clientY-rect2.top-dy)*(cvs2.height/rect2.height));
          d.p1={...d.p1,barIdx:ed._startBar1+bD,price:ed._startP1+pD};
          d.p2={...d.p2,barIdx:ed._startBar2+bD,price:ed._startP2+pD};
        }
      } else if (d.type === 'text') {
        d.barIdx=newBar; d.price=newPrice;
      }
      tvRedraw();
      return;
    }
    if(TV.drag.yDrag && TV.data) {
      // Y-axis drag: move price range up/down
      const {minV, maxV} = {minV:TV.drag.startMinV, maxV:TV.drag.startMaxV};
      const range = maxV - minV;
      const pxPerUnit = (TV.mainH - 54) / range;
      const deltaY = (e.clientY - TV.drag.startY) / pxPerUnit;
      TV.yRange.min = minV + deltaY;
      TV.yRange.max = maxV + deltaY;
      tvRedraw();
      return;
    }
    if(!TV.drag.active||!TV.data)return;
    const cW2=cvs.width-(TV_PAD.l+TV_PAD.r);
    const N=TV.view.end-TV.view.start;
    const pxPerBar=cW2/N;
    const delta=Math.round((TV.drag.startX-e.clientX)/pxPerBar);
    const total=TV.data.closes.length;
    let ns=TV.drag.startStart+delta,ne=TV.drag.startEnd+delta;
    if(ns<0){ne-=ns;ns=0;} if(ne>total){ns-=(ne-total);ne=total;}
    ns=Math.max(0,ns); ne=Math.min(total,ne);
    if(ne-ns>1){
      TV.view.start=ns; TV.view.end=ne;
      // Auto-reset Y range when panning X so candles always fill the view
      TV.yRange.min=null; TV.yRange.max=null;
      tvRedraw();
    }
  });

  // Unified wheel handler:
  // Left 72px (Y-axis) + Ctrl held = zoom Y range
  // Chart area = zoom X (bars visible) around cursor
  cvs.addEventListener('wheel', e=>{
    if(!TV.data) return;
    e.preventDefault();
    const rect=cvs.getBoundingClientRect();
    const localX=(e.clientX-rect.left)*(cvs.width/rect.width);
    const onYAxis = localX < 72;

    if(onYAxis || e.ctrlKey) {
      // Y-axis zoom: zoom in/out on price range
      const {minV, maxV} = tvGetYRange();
      const range = maxV - minV;
      const zoomFactor = e.deltaY > 0 ? 1.15 : 0.87;
      // Zoom around the cursor's price level
      const rect2=cvs.getBoundingClientRect();
      const localY=(e.clientY-rect2.top)*(cvs.height/rect2.height);
      const PAD_t=28, PAD_b=26, cH2=TV.mainH-PAD_t-PAD_b;
      const priceFrac = Math.max(0, Math.min(1, 1-(localY-PAD_t)/cH2));
      const focusPrice = minV + priceFrac*(maxV-minV);
      TV.yRange.min = focusPrice - (focusPrice-minV)*zoomFactor;
      TV.yRange.max = focusPrice + (maxV-focusPrice)*zoomFactor;
      tvRedraw();
      return;
    }

    // X-axis zoom: zoom bars around cursor position
    const total=TV.data.closes.length;
    const N=TV.view.end-TV.view.start;
    const zoomIn=e.deltaY<0;
    const delta=Math.max(1,Math.round(N*0.1));
    const frac=Math.max(0.05,Math.min(0.95,(localX-TV_PAD.l)/(cvs.width-TV_PAD.l-TV_PAD.r)));
    let ns = zoomIn ? TV.view.start+Math.round(delta*frac)   : TV.view.start-Math.round(delta*frac);
    let ne = zoomIn ? TV.view.end-Math.round(delta*(1-frac)) : TV.view.end+Math.round(delta*(1-frac));
    if(ne-ns<5) return;
    TV.view.start=Math.max(0,ns); TV.view.end=Math.min(total,ne);
    // Reset Y so candles auto-fit after zoom
    TV.yRange.min=null; TV.yRange.max=null;
    tvRedraw();
  },{passive:false});

  // Touch pan
  let _touchX=0,_touchStart=0,_touchEnd=0;
  let _pinchDist=0;
  cvs.addEventListener('touchstart',e=>{
    if(e.touches.length===1){TV.drag.active=true;_touchX=e.touches[0].clientX;_touchStart=TV.view.start;_touchEnd=TV.view.end;}
    else if(e.touches.length===2){TV.drag.active=false;const dx=e.touches[0].clientX-e.touches[1].clientX;_pinchDist=Math.abs(dx);}
  });
  cvs.addEventListener('touchmove',e=>{
    e.preventDefault();
    if(e.touches.length===1&&TV.drag.active&&TV.data){
      const cW2=cvs.width-144,N=TV.view.end-TV.view.start,pxPB=cW2/N;
      const delta=Math.round((_touchX-e.touches[0].clientX)/pxPB);
      const total=TV.data.closes.length;
      let ns=_touchStart+delta,ne=_touchEnd+delta;
      if(ns<0){ne-=ns;ns=0;} if(ne>total){ns-=(ne-total);ne=total;}
      TV.view.start=Math.max(0,ns);TV.view.end=Math.min(total,ne);tvRedraw();
    } else if(e.touches.length===2&&TV.data){
      const dx=e.touches[0].clientX-e.touches[1].clientX,dist=Math.abs(dx);
      const ratio=_pinchDist/dist;
      const N=TV.view.end-TV.view.start,newN=Math.max(5,Math.min(TV.data.closes.length,Math.round(N*ratio)));
      const mid=Math.round((TV.view.start+TV.view.end)/2);
      TV.view.start=Math.max(0,mid-Math.round(newN/2));TV.view.end=Math.min(TV.data.closes.length,TV.view.start+newN);
      _pinchDist=dist;tvRedraw();
    }
  },{passive:false});
  cvs.addEventListener('touchend',()=>{TV.drag.active=false;TV.drag.yDrag=false;});

  // ── Keyboard shortcuts ──
  document.addEventListener('keydown', e => {
    // Only handle if chart is visible
    if (!TV.data) return;

    // Esc — cancel active drawing / clear measure / return to cursor
    if (e.key === 'Escape') {
      TV.drawState = null;
      TV.selectedDrawing = null;
      TV.measureResult = null;   // clear measure overlay
      tvSetTool('cursor');
      tvRedraw();
      return;
    }

    // Ctrl+Z — undo last action
    if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
      e.preventDefault();
      if (TV.drawState) {
        TV.drawState = null;         // cancel in-progress drawing
      } else if (TV.measureResult) {
        TV.measureResult = null;     // clear measure overlay first
      } else if (TV.drawings.length > 0) {
        TV.drawings.pop();           // remove last completed drawing
      }
      TV.selectedDrawing = null;
      tvRedraw();
      return;
    }

    // Delete / Backspace — remove selected drawing
    if ((e.key === 'Delete' || e.key === 'Backspace') && TV.selectedDrawing !== null) {
      e.preventDefault();
      TV.drawings.splice(TV.selectedDrawing, 1);
      TV.selectedDrawing = null;
      tvRedraw();
      return;
    }
  });

  // Double-click: if measure active clear it, else reset Y range
  cvs.addEventListener('dblclick',()=>{
    if (TV.measureResult) {
      TV.measureResult = null;
    } else {
      TV.yRange.min=null; TV.yRange.max=null;
    }
    tvRedraw();
  });
}

// ── loadChart & renderChart ────────────────────────────────────────
// ── Astro Overlays and UI bindings ──

function tvFetchEphemeris() {
  if (!TV.data || !TV.data.dates || !TV.data.dates.length) {
    alert('Please load chart data first.');
    return;
  }
  const statusEl = document.getElementById('astro-status');
  if (statusEl) statusEl.textContent = 'Fetching ephemeris...';
  
  const start_date = TV.data.dates[0];
  const end_date = TV.data.dates[TV.data.dates.length - 1];
  
  fetch(`/api/ephemeris_range?start_date=${start_date}&end_date=${end_date}`)
    .then(r => r.json())
    .then(res => {
      if (res && res.range) {
        TV.ephemerisData = {};
        res.range.forEach(r => {
          TV.ephemerisData[r.date] = r;
        });
        if (statusEl) statusEl.textContent = 'Ephemeris loaded successfully.';
        tvRedraw();
      } else {
        if (statusEl) statusEl.textContent = 'Failed to load ephemeris.';
      }
    })
    .catch(e => {
      console.error(e);
      if (statusEl) statusEl.textContent = 'Error: ' + e.message;
    });
}

function tvTogglePlanet(planet) {
  if (!TV.astroOverlays) TV.astroOverlays = {};
  if (!TV.astroOverlays.planets) {
    TV.astroOverlays.planets = { Sun: true, Moon: true, Mercury: true, Venus: true, Mars: true, Jupiter: true, Saturn: true, Rahu: false, Ketu: false };
  }
  TV.astroOverlays.planets[planet] = !TV.astroOverlays.planets[planet];
  tvRedraw();
}

function tvSetAstroCoord(coord) {
  if (!TV.astroOverlays) TV.astroOverlays = {};
  TV.astroOverlays.coord = coord;
  tvRedraw();
}

function tvToggleAstroAspects() {
  if (!TV.astroOverlays) TV.astroOverlays = {};
  TV.astroOverlays.aspects = !TV.astroOverlays.aspects;
  tvRedraw();
}

function tvToggleAstroNakshatra() {
  if (!TV.astroOverlays) TV.astroOverlays = {};
  TV.astroOverlays.nakshatra = !TV.astroOverlays.nakshatra;
  tvRedraw();
}

function drawAstroOverlays(ctx, W, H, PAD, xOf, yOf, dl, start, end, minV, maxV) {
  if (!TV.ephemerisData || !TV.astroOverlays) return;
  
  const planets = TV.astroOverlays.planets || { Sun: true, Moon: true, Mercury: true, Venus: true, Mars: true, Jupiter: true, Saturn: true, Rahu: false, Ketu: false };
  const coord = TV.astroOverlays.coord || 'longitude';
  const showAspects = TV.astroOverlays.aspects;
  const showNakshatra = TV.astroOverlays.nakshatra;
  
  const planetColors = {
    Sun: '#ffcc00', Moon: '#ffffff', Mercury: '#00d4ff', Venus: '#ff88ff',
    Mars: '#ff3355', Jupiter: '#ff8800', Saturn: '#6a8fa8', Rahu: '#b5b5ff', Ketu: '#deb887'
  };
  
  const activePlanets = Object.keys(planets).filter(p => planets[p]);
  if (!activePlanets.length) return;
  
  const planetVals = {};
  activePlanets.forEach(p => {
    planetVals[p] = [];
  });
  
  const N = end - start;
  for (let i = 0; i < N; i++) {
    const dateStr = dl[i];
    const ephem = TV.ephemerisData[dateStr];
    activePlanets.forEach(p => {
      if (ephem) {
        const lon = ephem[p + '_lon'] || 0;
        let val = lon;
        if (coord === 'latitude') {
          val = Math.asin(Math.sin(lon * Math.PI / 180) * Math.sin(23.44 * Math.PI / 180)) * 180 / Math.PI;
        } else if (coord === 'speed') {
          val = ephem[p + '_speed'] || 0;
        }
        planetVals[p].push(val);
      } else {
        planetVals[p].push(null);
      }
    });
  }
  
  activePlanets.forEach(p => {
    const vals = planetVals[p];
    const cleanVals = vals.filter(v => v !== null);
    if (!cleanVals.length) return;
    
    const pMin = Math.min(...cleanVals);
    const pMax = Math.max(...cleanVals);
    const pRange = pMax - pMin || 1;
    
    ctx.strokeStyle = planetColors[p] || '#00d4ff';
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    let first = true;
    
    for (let i = 0; i < N; i++) {
      const val = vals[i];
      if (val === null) continue;
      const mappedPrice = minV + ((val - pMin) / pRange) * (maxV - minV);
      const x = xOf(i);
      const y = yOf(mappedPrice);
      
      if (first) {
        ctx.moveTo(x, y);
        first = false;
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();
    
    const lastVal = vals[vals.length - 1];
    if (lastVal !== null) {
      const lastMapped = minV + ((lastVal - pMin) / pRange) * (maxV - minV);
      ctx.fillStyle = planetColors[p] || '#00d4ff';
      ctx.font = 'bold 9px Share Tech Mono';
      ctx.textAlign = 'left';
      ctx.fillText(p, W - PAD.r + 3, yOf(lastMapped) + 3);
    }
  });

  if (showAspects) {
    for (let i = 1; i < N; i++) {
      const dateStr = dl[i];
      const prevDateStr = dl[i-1];
      const ephem = TV.ephemerisData[dateStr];
      const prevEphem = TV.ephemerisData[prevDateStr];
      if (!ephem || !prevEphem) continue;
      
      const x = xOf(i);
      
      if (planets.Moon && planets.Sun) {
        const diff = (ephem['Moon_lon'] - ephem['Sun_lon'] + 360) % 360;
        const prevDiff = (prevEphem['Moon_lon'] - prevEphem['Sun_lon'] + 360) % 360;
        
        let label = '';
        if (prevDiff > 355 && diff < 5) label = '● New Moon';
        else if (prevDiff < 180 && diff >= 180) label = '○ Full Moon';
        
        if (label) {
          ctx.strokeStyle = 'rgba(255,255,255,0.2)';
          ctx.lineWidth = 1;
          ctx.setLineDash([4,4]);
          ctx.beginPath();
          ctx.moveTo(x, PAD.t);
          ctx.lineTo(x, H - PAD.b);
          ctx.stroke();
          ctx.setLineDash([]);
          
          ctx.fillStyle = 'rgba(255,255,255,0.6)';
          ctx.font = '8px Share Tech Mono';
          ctx.textAlign = 'center';
          ctx.fillText(label, x, PAD.t + 10);
        }
      }
      
      activePlanets.forEach(p => {
        const retro = ephem[p + '_retro'];
        const prevRetro = prevEphem[p + '_retro'];
        if (retro !== undefined && prevRetro !== undefined && retro !== prevRetro) {
          const label = p + (retro ? ' Rx' : ' Dir');
          ctx.strokeStyle = 'rgba(255,136,0,0.25)';
          ctx.lineWidth = 1;
          ctx.setLineDash([2,2]);
          ctx.beginPath();
          ctx.moveTo(x, PAD.t);
          ctx.lineTo(x, H - PAD.b);
          ctx.stroke();
          ctx.setLineDash([]);
          
          ctx.fillStyle = 'rgba(255,136,0,0.7)';
          ctx.font = '8px Share Tech Mono';
          ctx.textAlign = 'center';
          ctx.fillText(label, x, H - PAD.b - 8);
        }
      });
    }
  }

  if (showNakshatra) {
    const naks = [
      "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha",
      "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
      "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
    ];
    
    const degInterval = 360 / 27;
    ctx.strokeStyle = 'rgba(0, 255, 136, 0.08)';
    ctx.lineWidth = 0.8;
    
    for (let j = 0; j <= 27; j++) {
      const deg = j * degInterval;
      const mappedPrice = minV + (deg / 360) * (maxV - minV);
      const y = yOf(mappedPrice);
      
      ctx.beginPath();
      ctx.moveTo(PAD.l, y);
      ctx.lineTo(W - PAD.r, y);
      ctx.stroke();
      
      if (j < 27) {
        ctx.fillStyle = 'rgba(0, 255, 136, 0.3)';
        ctx.font = '8px Share Tech Mono';
        ctx.textAlign = 'left';
        const nextMapped = minV + (((j + 1) * degInterval) / 360) * (maxV - minV);
        const midY = (y + yOf(nextMapped)) / 2;
        if (midY > PAD.t && midY < H - PAD.b) {
          ctx.fillText(naks[j], PAD.l + 5, midY + 3);
        }
      }
    }
  }
}

function tvSetTimeRange(range) {
  if (!TV.data || !TV.data.closes) return;
  const N = TV.data.closes.length;
  let count = N;
  
  if (range === '1D') count = 5;
  else if (range === '5D') count = 5;
  else if (range === '1M') count = 20;
  else if (range === '3M') count = 60;
  else if (range === '6M') count = 120;
  else if (range === 'YTD') {
    if (TV.data.dates && TV.data.dates.length) {
      const lastYear = new Date(TV.data.dates[N-1]).getFullYear();
      let firstIdx = 0;
      for (let i = 0; i < N; i++) {
        if (new Date(TV.data.dates[i]).getFullYear() === lastYear) {
          firstIdx = i;
          break;
        }
      }
      count = N - firstIdx;
    } else {
      count = 120;
    }
  }
  else if (range === '1Y') count = 252;
  else if (range === '5Y') count = 1260;
  else if (range === 'ALL') count = N;
  
  TV.view.end = N;
  TV.view.start = Math.max(0, N - count);
  
  const btns = document.querySelectorAll('.tv-range-btn');
  btns.forEach(btn => {
    if (btn.textContent.toUpperCase() === range) {
      btn.style.color = 'var(--cyan)';
      btn.style.background = 'rgba(0,212,255,0.08)';
    } else {
      btn.style.color = 'var(--tv-color-text-secondary)';
      btn.style.background = 'transparent';
    }
  });
  
  tvRedraw();
}
"""
