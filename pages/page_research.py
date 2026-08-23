"""
page_research.py  —  Professional Equity Research Report
Clean white-background institutional format.
Rating drives the entire report — no contradictions.
"""

HTML = r"""
<!-- ═══════════ PAGE: EQUITY RESEARCH REPORT ═══════════ -->
<div class="page" id="page-research">
  <div class="topbar">
    <h2 style="font-family:Georgia,serif;font-size:1rem;">Equity Research</h2>
    <span class="page-tag" style="font-family:Georgia,serif;">INSTITUTIONAL RESEARCH</span>
  </div>

  <div class="card" id="res-controls" style="margin-bottom:14px;">
    <div style="display:flex;flex-wrap:wrap;align-items:flex-end;gap:14px;">
      <div style="display:flex;flex-direction:column;gap:4px;">
        <label style="font-size:0.6rem;color:var(--dim);letter-spacing:2px;
          font-family:Share Tech Mono,monospace;">SELECT COMPANY</label>
        <select id="res-symbol" style="min-width:180px;background:var(--p2);
          border:1px solid var(--b2);color:var(--white);padding:8px 12px;
          font-family:Share Tech Mono,monospace;font-size:0.82rem;outline:none;cursor:pointer;">
          <option value="">Loading…</option>
        </select>
      </div>
      <button onclick="runResearch()" id="res-run-btn"
        style="padding:9px 32px;background:var(--gold);color:#000;
        font-family:Share Tech Mono,monospace;font-size:0.75rem;font-weight:700;
        letter-spacing:2px;border:none;cursor:pointer;">
        ▶ GENERATE REPORT
      </button>
      <button onclick="window.print()"
        style="padding:9px 18px;background:transparent;color:var(--dim);
        font-family:Share Tech Mono,monospace;font-size:0.7rem;letter-spacing:1px;
        border:1px solid var(--b2);cursor:pointer;">⎙ PRINT / PDF
      </button>
    </div>
  </div>

  <div id="res-loading" style="display:none;text-align:center;padding:80px 20px;">
    <div style="font-family:Georgia,serif;font-size:1.1rem;color:var(--dim);margin-bottom:10px;">
      Generating research report…</div>
    <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);
      letter-spacing:3px;">FETCHING DATA · RUNNING MODELS · WRITING REPORT</div>
    <div style="margin-top:16px;height:2px;background:var(--p2);max-width:280px;
      margin-left:auto;margin-right:auto;">
      <div id="res-pbar" style="height:100%;width:0;background:var(--gold);transition:width 0.5s;"></div>
    </div>
  </div>

  <div id="res-error" style="display:none;padding:14px 18px;border-left:3px solid var(--red);
    background:rgba(255,59,59,0.06);margin-bottom:14px;">
    <span style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--red);">
      ERROR: </span>
    <span id="res-error-msg" style="font-size:0.82rem;color:var(--text);"></span>
  </div>

  <div id="res-output"></div>
</div>

<style>
/* ── Print: white paper, black ink ── */
@media print {
  body, .main-content, .page, #page-research { background: #fff !important; color: #000 !important; }
  .sidebar, .topbar, #res-controls, .ticker-bar, .mobile-header { display:none !important; }
  #res-output { padding: 0 !important; }
  .rpt-cover, .rpt-section { break-inside: avoid; }
}
/* ── Report skin (white paper look on screen too) ── */
#research-report {
  background: #fff;
  color: #1a1a1a;
  font-family: Georgia, 'Times New Roman', serif;
  border-radius: 2px;
  box-shadow: 0 2px 24px rgba(0,0,0,0.35);
}
#research-report * { box-sizing: border-box; }
#research-report a { color: #0066cc; }
.rpt-mono { font-family: 'Share Tech Mono', 'Courier New', monospace; }
.rpt-head {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.56rem; letter-spacing: 2px;
  color: #666; text-transform: uppercase;
}
.rpt-divider {
  display: flex; align-items: center; gap: 12px;
  margin: 28px 0 14px; padding-bottom: 8px;
  border-bottom: 1.5px solid #222;
}
.rpt-divider .rpt-num {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.58rem; color: #666;
  background: #f4f4f4; border: 1px solid #ddd;
  padding: 2px 8px; letter-spacing: 1px;
}
.rpt-divider h2 {
  font-family: Georgia, serif; font-size: 1rem;
  font-weight: 600; color: #111; margin: 0; letter-spacing: 0.2px;
}
.rpt-cell {
  padding: 11px 13px; border: 1px solid #e0e0e0;
  background: #fafafa;
}
.rpt-cell .rpt-head { margin-bottom: 4px; }
.rpt-cell .rpt-val {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.9rem; font-weight: 700; color: #111;
}
.rpt-cell .rpt-sub {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.6rem; color: #888; margin-top: 2px;
}
table.rpt-table { border-collapse: collapse; width: 100%; }
table.rpt-table th {
  background: #f0f0f0; font-family: 'Share Tech Mono', monospace;
  font-size: 0.56rem; letter-spacing: 1.5px; color: #555;
  padding: 8px 11px; border: 1px solid #ddd;
  font-weight: normal; text-align: left;
}
table.rpt-table td {
  padding: 9px 11px; border: 1px solid #e4e4e4;
  font-size: 0.83rem; vertical-align: top;
}
</style>
"""

JS = r"""
(function() {

// ── Symbol dropdown ────────────────────────────────────
function initResearch() {
  const sel = document.getElementById('res-symbol');
  if (!sel) return;
  // Only run if dropdown is still empty (has 0 or 1 placeholder option)
  if (sel.options.length > 1) return;

  fetch('/api/all_symbols')
    .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(d => {
      sel.innerHTML = '';

      // API returns {equities:[{symbol,name}], indices:[...], commodities:[...]}
      // We want only equities for research reports (no indices/commodities)
      let equities = [];
      if (d.equities && Array.isArray(d.equities)) {
        equities = d.equities.map(x => x.symbol || x).filter(Boolean);
      } else if (Array.isArray(d)) {
        equities = d.map(x => typeof x === 'object' ? (x.symbol || x) : x).filter(Boolean);
      } else if (d.symbols) {
        equities = d.symbols;
      }

      if (!equities.length) throw new Error('empty symbol list');

      equities.sort().forEach(s => {
        const o = document.createElement('option');
        o.value = s; o.textContent = s;
        if (s === 'HDFCBANK') o.selected = true;
        sel.appendChild(o);
      });
    })
    .catch(() => {
      // Fallback list — covers all 29 equities in instruments.py
      const fb = [
        'AXISBANK','BAJFINANCE','BHARTIARTL','DIVISLAB','DRREDDY',
        'HCLTECH','HDFCBANK','HDFCLIFE','HINDALCO','HINDUNILVR',
        'ICICIBANK','INFY','ITC','KOTAKBANK','M&M','MARUTI',
        'NTPC','ONGC','POWERGRID','RELIANCE','SBIN','SBILIFE',
        'SUNPHARMA','TATAMOTORS','TATASTEEL','TCS','TECHM','WIPRO','LT'
      ];
      sel.innerHTML = fb.map(s =>
        `<option value="${s}"${s==='HDFCBANK'?' selected':''}>${s}</option>`).join('');
    });
}

// Run immediately and again after short delay (handles SPA navigation timing)
initResearch();
setTimeout(initResearch, 400);
setTimeout(initResearch, 1200);

// Re-run whenever the user navigates to the research page via the SPA nav()
const _resOrigNav = window.nav;
window._resNavHook = function(page) {
  if (page === 'research') {
    // Reset dropdown and re-fetch on every navigation to this page
    const sel = document.getElementById('res-symbol');
    if (sel && sel.options.length <= 1) {
      setTimeout(initResearch, 200);
    }
  }
};
// Patch nav() safely after DOM is ready (nav is defined in _shared.js)
setTimeout(function() {
  if (typeof window.nav === 'function') {
    const _origNav = window.nav;
    window.nav = function(page) {
      _origNav(page);
      window._resNavHook(page);
    };
  }
}, 100);

// ── Progress ──────────────────────────────────────────
let _pt = null;
function startProg() {
  let p = 0;
  clearInterval(_pt);
  _pt = setInterval(() => {
    p = Math.min(p + Math.random()*9, 88);
    const b = document.getElementById('res-pbar');
    if (b) b.style.width = p + '%';
  }, 320);
}
function endProg() {
  clearInterval(_pt);
  const b = document.getElementById('res-pbar');
  if (b) { b.style.width = '100%'; setTimeout(() => b.style.width='0', 700); }
}

// ── Run ───────────────────────────────────────────────
window.runResearch = function() {
  const sym  = (document.getElementById('res-symbol')?.value || '').trim();
  const date = document.getElementById('analysis-date')?.value
             || new Date().toISOString().slice(0,10);
  if (!sym) {
    showErr('Please select a company.');
    return;
  }
  document.getElementById('res-loading').style.display = 'block';
  document.getElementById('res-output').innerHTML = '';
  document.getElementById('res-error').style.display = 'none';
  startProg();

  Promise.all([
    fetch(`/api/advisor?symbols=${sym}&diversify=1&type=long&risk=balanced&amount=1000000&date=${date}`)
      .then(r => r.json()),
    fetch(`/api/master_report?symbol=${sym}&date=${date}&inv_type=long`)
      .then(r => r.json()),
    fetch(`/api/shareholding?symbol=${sym}`)
      .then(r => r.json()).catch(() => ({})),
  ])
  .then(([adv, rpt, own]) => {
    endProg();
    document.getElementById('res-loading').style.display = 'none';
    const rec = (adv.recommendations || [])[0];
    if (!rec) {
      showErr(adv.error || 'No data returned. Try a different symbol or date.');
      return;
    }
    rpt.shareholding = own.ok ? own : {};
    renderReport(rec, rpt, date, sym);
  })
  .catch(e => {
    endProg();
    document.getElementById('res-loading').style.display = 'none';
    showErr(e.message || 'Unexpected error.');
  });
};

function showErr(msg) {
  document.getElementById('res-error-msg').textContent = msg;
  document.getElementById('res-error').style.display = 'block';
}

// ── Formatters ─────────────────────────────────────────
function inr(n, d) {
  d = d == null ? 2 : d;
  if (n == null || isNaN(n)) return '—';
  return '₹' + Number(n).toLocaleString('en-IN',{minimumFractionDigits:d,maximumFractionDigits:d});
}
function pct(n, d) {
  d = d == null ? 1 : d;
  if (n == null || isNaN(n)) return '—';
  return (Number(n) >= 0 ? '+' : '') + Number(n).toFixed(d) + '%';
}
function xfmt(n, suffix, d) {
  d = d == null ? 2 : d;
  if (n == null || isNaN(n) || !isFinite(n)) return '—';
  return Number(n).toFixed(d) + (suffix || '');
}

// ── Rating — single source of truth ───────────────────
// Driven entirely by advisor confidence score.
// The whole report must be consistent with this.
function getRating(conf) {
  if (conf >= 62) return {label:'BUY',         col:'#005c2e', bg:'#e6f4ed', border:'#005c2e'};
  if (conf >= 50) return {label:'OUTPERFORM',  col:'#1a6b00', bg:'#edf7e6', border:'#1a6b00'};
  if (conf >= 38) return {label:'NEUTRAL',     col:'#7a5c00', bg:'#fdf8e6', border:'#7a5c00'};
  if (conf >= 25) return {label:'UNDERPERFORM',col:'#8b2000', bg:'#fdf0ec', border:'#8b2000'};
  return               {label:'SELL',          col:'#b00000', bg:'#fde8e8', border:'#b00000'};
}

// ── Build section divider ──────────────────────────────
function sec(n, title) {
  return `<div class="rpt-divider"><span class="rpt-num">${String(n).padStart(2,'0')}</span>
    <h2>${title}</h2></div>`;
}

// ── Scenario price-path chart (SVG) ───────────────────
// Draws 3 scenario lines from CMP over hold_days
// bull = target2, base = target1, bear = stop_loss
function scenarioChart(cmp, entry, t1, t2, sl, holdDays, dateStr) {
  const W = 560, H = 220, padL = 54, padR = 20, padT = 20, padB = 36;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;

  const today = new Date(dateStr); // analysis date
  // Add trading-day milestones along x axis
  const totalDays = Math.max(holdDays || 60, 30);
  const xPts = [0, Math.round(totalDays*0.25), Math.round(totalDays*0.5),
                Math.round(totalDays*0.75), totalDays];

  // Price range with 5% padding
  const allP = [cmp, entry, t1, t2, sl].filter(v=>v>0);
  const pMin = Math.min(...allP) * 0.97;
  const pMax = Math.max(...allP) * 1.03;
  const pRng = pMax - pMin;

  const xS = d => padL + (d / totalDays) * plotW;
  const yS = p => padT + plotH - ((p - pMin) / pRng) * plotH;

  // Scenario paths: bull rises to t2, base rises to t1, bear falls to sl
  // Each path: linear segments [day0=cmp, dayMid, dayEnd]
  function pathPts(endPrice) {
    const pts = xPts.map((d,i) => {
      const frac = d / totalDays;
      // Slight curve: slow start then accelerate
      const curved = frac * frac * (3 - 2*frac); // smoothstep
      const p = cmp + (endPrice - cmp) * curved;
      return `${xS(d).toFixed(1)},${yS(p).toFixed(1)}`;
    });
    return pts.join(' ');
  }

  const bullPts = pathPts(t2);
  const basePts = pathPts(t1);
  const bearPts = pathPts(sl);

  // Y-axis labels
  const yLabels = [sl, cmp, t1, t2].filter(v=>v>0)
    .sort((a,b)=>a-b)
    .map(p => ({p, y: yS(p).toFixed(1), label: '₹'+Math.round(p).toLocaleString('en-IN')}));

  // X-axis date labels
  const xLabels = xPts.map(d => {
    const dt = new Date(today);
    // Add ~1.4 calendar days per trading day
    dt.setDate(dt.getDate() + Math.round(d * 1.4));
    return {d, x: xS(d).toFixed(1),
      label: dt.toLocaleDateString('en-IN',{day:'2-digit',month:'short'})};
  });

  // Build SVG
  let svg = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" style="overflow:visible;display:block;max-width:100%;">`;

  // Background grid
  for (let i = 1; i <= 4; i++) {
    const y = (padT + (i/5) * plotH).toFixed(1);
    svg += `<line x1="${padL}" y1="${y}" x2="${W-padR}" y2="${y}"
      stroke="#f0f0f0" stroke-width="1"/>`;
  }

  // Filled areas (very light)
  svg += `<polygon points="${xS(0).toFixed(1)},${yS(cmp).toFixed(1)} ${bullPts} ${xS(totalDays).toFixed(1)},${yS(cmp).toFixed(1)}"
    fill="#006633" opacity="0.06"/>`;
  svg += `<polygon points="${xS(0).toFixed(1)},${yS(cmp).toFixed(1)} ${bearPts} ${xS(totalDays).toFixed(1)},${yS(cmp).toFixed(1)}"
    fill="#cc0000" opacity="0.06"/>`;

  // Scenario lines
  svg += `<polyline points="${bullPts}" fill="none" stroke="#006633" stroke-width="2"
    stroke-dasharray="none" stroke-linejoin="round"/>`;
  svg += `<polyline points="${basePts}" fill="none" stroke="#0055aa" stroke-width="1.5"
    stroke-dasharray="5,3" stroke-linejoin="round"/>`;
  svg += `<polyline points="${bearPts}" fill="none" stroke="#cc0000" stroke-width="1.5"
    stroke-dasharray="3,3" stroke-linejoin="round"/>`;

  // CMP horizontal reference
  svg += `<line x1="${padL}" y1="${yS(cmp).toFixed(1)}" x2="${W-padR}" y2="${yS(cmp).toFixed(1)}"
    stroke="#888" stroke-width="0.8" stroke-dasharray="2,4"/>`;

  // Entry marker (dot on day 0 for entry price if different from cmp)
  if (Math.abs(entry - cmp) > 1) {
    svg += `<circle cx="${xS(0).toFixed(1)}" cy="${yS(entry).toFixed(1)}" r="4"
      fill="#0055aa" stroke="#fff" stroke-width="1.5"/>`;
    svg += `<text x="${(xS(0)+6).toFixed(1)}" y="${(parseFloat(yS(entry))-4).toFixed(1)}"
      font-size="9" fill="#0055aa" font-family="monospace">Entry ${inr(entry,0)}</text>`;
  }

  // End-point labels
  const endX = xS(totalDays);
  svg += `<circle cx="${endX.toFixed(1)}" cy="${yS(t2).toFixed(1)}" r="4" fill="#006633" stroke="#fff" stroke-width="1.5"/>`;
  svg += `<text x="${(endX+6).toFixed(1)}" y="${(parseFloat(yS(t2))+4).toFixed(1)}"
    font-size="10" fill="#006633" font-weight="bold" font-family="monospace">
    T2 ${inr(t2,0)}</text>`;

  svg += `<circle cx="${endX.toFixed(1)}" cy="${yS(t1).toFixed(1)}" r="4" fill="#0055aa" stroke="#fff" stroke-width="1.5"/>`;
  svg += `<text x="${(endX+6).toFixed(1)}" y="${(parseFloat(yS(t1))+4).toFixed(1)}"
    font-size="10" fill="#0055aa" font-family="monospace">
    T1 ${inr(t1,0)}</text>`;

  svg += `<circle cx="${endX.toFixed(1)}" cy="${yS(sl).toFixed(1)}" r="4" fill="#cc0000" stroke="#fff" stroke-width="1.5"/>`;
  svg += `<text x="${(endX+6).toFixed(1)}" y="${(parseFloat(yS(sl))+4).toFixed(1)}"
    font-size="10" fill="#cc0000" font-family="monospace">
    SL ${inr(sl,0)}</text>`;

  // CMP start dot
  svg += `<circle cx="${padL}" cy="${yS(cmp).toFixed(1)}" r="5" fill="#333" stroke="#fff" stroke-width="1.5"/>`;
  svg += `<text x="${(padL-4).toFixed(1)}" y="${(parseFloat(yS(cmp))-8).toFixed(1)}"
    font-size="9" fill="#333" font-family="monospace" text-anchor="middle">CMP</text>`;

  // Y-axis labels
  yLabels.forEach(({p, y, label}) => {
    svg += `<text x="${(padL-4).toFixed(1)}" y="${y}" font-size="9" fill="#666"
      font-family="monospace" text-anchor="end" dominant-baseline="middle">${label}</text>`;
    svg += `<line x1="${(padL-2).toFixed(1)}" y1="${y}" x2="${padL}" y2="${y}"
      stroke="#bbb" stroke-width="1"/>`;
  });

  // X-axis labels
  xLabels.forEach(({x, label}) => {
    svg += `<text x="${x}" y="${(H-6).toFixed(1)}" font-size="9" fill="#666"
      font-family="monospace" text-anchor="middle">${label}</text>`;
    svg += `<line x1="${x}" y1="${(padT+plotH).toFixed(1)}" x2="${x}"
      y2="${(padT+plotH+4).toFixed(1)}" stroke="#bbb" stroke-width="1"/>`;
  });

  // Legend
  svg += `<rect x="${padL}" y="${(H-padB+16).toFixed(1)}" width="10" height="3" fill="#006633"/>`;
  svg += `<text x="${(padL+13).toFixed(1)}" y="${(H-padB+20).toFixed(1)}" font-size="9"
    fill="#006633" font-family="monospace">Bull scenario (T2)</text>`;
  svg += `<line x1="${(padL+110).toFixed(1)}" y1="${(H-padB+19).toFixed(1)}"
    x2="${(padL+126).toFixed(1)}" y2="${(H-padB+19).toFixed(1)}"
    stroke="#0055aa" stroke-width="1.5" stroke-dasharray="4,2"/>`;
  svg += `<text x="${(padL+129).toFixed(1)}" y="${(H-padB+22).toFixed(1)}" font-size="9"
    fill="#0055aa" font-family="monospace">Base scenario (T1)</text>`;
  svg += `<line x1="${(padL+235).toFixed(1)}" y1="${(H-padB+19).toFixed(1)}"
    x2="${(padL+251).toFixed(1)}" y2="${(H-padB+19).toFixed(1)}"
    stroke="#cc0000" stroke-width="1.5" stroke-dasharray="2,2"/>`;
  svg += `<text x="${(padL+254).toFixed(1)}" y="${(H-padB+22).toFixed(1)}" font-size="9"
    fill="#cc0000" font-family="monospace">Bear scenario (SL)</text>`;

  svg += '</svg>';
  return svg;
}

// ── Rating explainer — plain English ─────────────────
function ratingExplainer(conf, isBuy, isSell, r) {
  const rt = getRating(conf);
  const fundGood = (r.fund_grade||'').match(/A/i);
  const cycleLow = (r.cycle_phase||'').match(/ACCUM|MARKUP/i);
  const bearDom  = (r.bear_signals||0) > (r.bull_signals||0);
  const regimeBad= (r.regime||'').match(/BEAR|SIDE/i);

  // Explain why signals conflict
  const conflicts = [];
  if (fundGood && isSell)
    conflicts.push(`The company's <strong>fundamentals are strong (${r.fund_grade})</strong>, but short-term planetary signals are bearish. This is common near accumulation bottoms — the business is fine, the timing is cautious.`);
  if (cycleLow && isSell)
    conflicts.push(`The cycle model sees price near a <strong>long-term low (accumulation zone)</strong>, but the 25-signal composite score is low because of current bearish planetary pressure. Wait for planetary alignment before entry.`);
  if (bearDom)
    conflicts.push(`<strong>${r.bear_signals} bear vs ${r.bull_signals} bull</strong> planetary signals currently active — this is the primary reason for the cautious rating. These signals typically resolve within 2–6 weeks.`);

  // Build meter
  const signals = [
    {label:'Fundamentals', score:r.fund_score||0, max:25, col:'#0055aa'},
    {label:'Gann / Sq9',   score:r.gann_score||0, max:20, col:'#660099'},
    {label:'Natal / Astro',score:r.natal_score||0, max:20, col:'#cc5500'},
    {label:'Planetary',    score:r.planet_score||0,max:15, col:'#cc0000'},
    {label:'Simons/Quant', score:r.simons_100!=null?r.simons_100/5:0, max:20, col:'#006633'},
  ];

  const meters = signals.map(s => {
    const pct = Math.min(100, (s.score/s.max)*100);
    const col = pct>=70?'#006633':pct>=45?'#7a5c00':'#cc0000';
    return `<div style="margin-bottom:10px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
        <span style="font-family:'Share Tech Mono',monospace;font-size:0.65rem;color:#555;">${s.label}</span>
        <span style="font-family:'Share Tech Mono',monospace;font-size:0.7rem;font-weight:700;color:${col};">
          ${s.score.toFixed(0)} / ${s.max}
        </span>
      </div>
      <div style="height:7px;background:#eee;border-radius:3px;overflow:hidden;">
        <div style="width:${pct}%;height:100%;background:${col};border-radius:3px;transition:width 0.8s;"></div>
      </div>
    </div>`;
  }).join('');

  const verdict = isBuy  ? 'The combination of signals is net-positive — more engines are bullish than bearish at current levels.'
                : isSell ? 'The combination of signals is net-negative — the weight of evidence (particularly planetary) suggests caution now.'
                : 'Signals are mixed — not enough conviction in either direction at current price.';

  return `
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
    <!-- Left: score breakdown -->
    <div>
      <div class="rpt-head" style="margin-bottom:12px;">WHY THIS RATING?  —  SIGNAL BREAKDOWN</div>
      ${meters}
      <p style="font-family:Georgia,serif;font-size:0.82rem;line-height:1.7;color:#333;
        margin:10px 0 0;padding:10px;background:#f8f8f8;border-left:3px solid ${rt.col};">
        ${verdict}
      </p>
    </div>
    <!-- Right: conflicts explained -->
    <div>
      <div class="rpt-head" style="margin-bottom:12px;">WHY DO SOME SIGNALS CONFLICT?</div>
      ${conflicts.length
        ? conflicts.map(c=>`<p style="font-family:Georgia,serif;font-size:0.83rem;
            line-height:1.72;color:#222;padding:10px 12px;margin-bottom:8px;
            background:#fafafa;border-left:3px solid #ccc;">${c}</p>`).join('')
        : `<p style="font-family:Georgia,serif;font-size:0.83rem;color:#555;line-height:1.7;">
            Signals are broadly consistent with the ${rt.label} rating.</p>`}
      <div style="margin-top:14px;padding:12px;background:${rt.bg};border:1px solid ${rt.border};">
        <div class="rpt-head" style="color:${rt.col};margin-bottom:6px;">BOTTOM LINE</div>
        <p style="font-family:Georgia,serif;font-size:0.85rem;line-height:1.7;color:#222;margin:0;">
          ${isBuy
            ? `Signal strength is sufficient for a long position. Risk is well-defined — stop at ${inr(r.stop_loss)}.`
            : isSell
            ? `Wait for the signal score to improve above 40/100 before buying. The business may be fine but the <em>timing</em> is unfavourable.`
            : `No strong edge either way. Existing holders: hold with trailing stop. New buyers: wait for a cleaner entry signal.`}
        </p>
      </div>
    </div>
  </div>`;
}

// ── ML Plain-English explainer ────────────────────────
function mlExplainer(ml, cmp, isBuy) {
  const conf   = Math.round((ml.confidence||0)*100);
  const dir    = ml.direction||'NEUTRAL';
  const revP   = ml.reversal_price||cmp;
  const revD   = (ml.reversal_date||'').replace(/-/g,'/');
  const days   = ml.days_to_rev||0;
  const align  = Math.round((ml.signal_alignment||0)*100);
  const trained= ml.model_trained;
  const diff   = cmp?((revP-cmp)/cmp*100).toFixed(1):'0';

  // Plain English direction
  const dirTxt = dir==='UP'
    ? 'The model expects the stock to <strong>move upward</strong> from current levels.'
    : dir==='DOWN'
    ? 'The model expects the stock to <strong>move downward</strong> from current levels.'
    : 'The model sees <strong>no clear directional edge</strong> right now — the stock may chop sideways.';

  // Plain English confidence
  const confTxt = conf>=70 ? 'High confidence — multiple signals agree strongly.'
    : conf>=55 ? 'Moderate confidence — more signals agree than disagree.'
    : conf>=40 ? 'Low-moderate confidence — signals are mixed.'
    : 'Low confidence — treat as a weak signal only.';

  // Plain English reversal
  const revTxt = dir==='NEUTRAL'
    ? `The nearest price inflection point is around <strong>${inr(revP,0)}</strong> — this is where the model expects the next significant move to begin (either direction), approximately <strong>${days} trading days</strong> from today.`
    : `The model targets <strong>${inr(revP,0)}</strong> as the price where momentum reversal is most likely, approximately <strong>${days} trading days</strong> from now (around <strong>${revD}</strong>).`;

  // Alignment explanation
  const alignTxt = align>=80 ? 'Fourier cycles, news, and planetary signals all point in the same direction — very high agreement.'
    : align>=60 ? 'Most supporting signals agree with the ML direction.'
    : align>=40 ? 'Signals are partially aligned — some disagreement between engines.'
    : 'Low signal alignment — the ML direction is not yet confirmed by other engines.';

  const dirCol = dir==='UP'?'#006633':dir==='DOWN'?'#cc0000':'#7a5c00';
  const confCol= conf>=60?'#006633':conf>=45?'#7a5c00':'#cc0000';

  return `
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
    <!-- Left: visual gauges -->
    <div>
      <!-- Direction indicator -->
      <div style="text-align:center;padding:20px;background:#f8f8f8;border:1px solid #e0e0e0;margin-bottom:12px;">
        <div style="font-size:2.4rem;color:${dirCol};margin-bottom:6px;">
          ${dir==='UP'?'↑':dir==='DOWN'?'↓':'↔'}
        </div>
        <div style="font-family:'Share Tech Mono',monospace;font-size:0.7rem;
          color:${dirCol};font-weight:700;letter-spacing:1px;">
          ${dir==='UP'?'BULLISH':dir==='DOWN'?'BEARISH':'SIDEWAYS / NEUTRAL'}
        </div>
        <div style="font-family:Georgia,serif;font-size:0.78rem;color:#555;margin-top:6px;">
          ML predicted direction  ·  ${ml.horizon||'Long term'}
        </div>
      </div>

      <!-- Confidence gauge -->
      <div style="margin-bottom:12px;">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
          <span class="rpt-head">MODEL CONFIDENCE</span>
          <span style="font-family:'Share Tech Mono',monospace;font-size:0.78rem;
            font-weight:700;color:${confCol};">${conf}%</span>
        </div>
        <div style="height:10px;background:#eee;border-radius:5px;overflow:hidden;">
          <div style="width:${conf}%;height:100%;background:${confCol};border-radius:5px;"></div>
        </div>
        <div style="font-family:Georgia,serif;font-size:0.75rem;color:#666;margin-top:4px;">
          ${confTxt}
        </div>
      </div>

      <!-- Signal alignment gauge -->
      <div style="margin-bottom:12px;">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
          <span class="rpt-head">SIGNAL ALIGNMENT</span>
          <span style="font-family:'Share Tech Mono',monospace;font-size:0.78rem;
            font-weight:700;color:${align>=60?'#006633':align>=40?'#7a5c00':'#cc0000'};">${align}%</span>
        </div>
        <div style="height:10px;background:#eee;border-radius:5px;overflow:hidden;">
          <div style="width:${align}%;height:100%;
            background:${align>=60?'#006633':align>=40?'#7a5c00':'#cc0000'};border-radius:5px;"></div>
        </div>
        <div style="font-family:Georgia,serif;font-size:0.75rem;color:#666;margin-top:4px;">
          ${alignTxt}
        </div>
      </div>

      <!-- Key dates -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1px;">
        <div class="rpt-cell">
          <div class="rpt-head">ML REVERSAL PRICE</div>
          <div class="rpt-val" style="color:#7a5c00;">${inr(revP,0)}</div>
          <div class="rpt-sub">${parseFloat(diff)>=0?'+':''}${diff}% from CMP</div>
        </div>
        <div class="rpt-cell">
          <div class="rpt-head">ML REVERSAL DATE</div>
          <div class="rpt-val" style="color:#0055aa;font-size:0.78rem;">${revD||'—'}</div>
          <div class="rpt-sub">${days?'in ~'+days+' trading days':''}</div>
        </div>
      </div>
    </div>

    <!-- Right: plain English explanation -->
    <div>
      <div class="rpt-head" style="margin-bottom:12px;">WHAT DOES THIS MEAN IN PLAIN ENGLISH?</div>

      <div style="padding:12px 14px;background:#fafafa;border-left:3px solid ${dirCol};
        margin-bottom:10px;">
        <div class="rpt-head" style="color:${dirCol};margin-bottom:5px;">DIRECTION</div>
        <p style="font-family:Georgia,serif;font-size:0.85rem;line-height:1.72;color:#222;margin:0;">
          ${dirTxt}
        </p>
      </div>

      <div style="padding:12px 14px;background:#fafafa;border-left:3px solid #0055aa;
        margin-bottom:10px;">
        <div class="rpt-head" style="color:#0055aa;margin-bottom:5px;">REVERSAL PRICE &amp; DATE</div>
        <p style="font-family:Georgia,serif;font-size:0.85rem;line-height:1.72;color:#222;margin:0;">
          ${revTxt}
        </p>
      </div>

      <div style="padding:12px 14px;background:#fafafa;border-left:3px solid #660099;
        margin-bottom:10px;">
        <div class="rpt-head" style="color:#660099;margin-bottom:5px;">HOW RELIABLE IS THIS?</div>
        <p style="font-family:Georgia,serif;font-size:0.85rem;line-height:1.72;color:#222;margin:0;">
          ${trained
            ? `This prediction comes from a <strong>trained machine learning model</strong> built on historical price data for this stock. It has learned patterns from past cycles. Confidence ${conf}% means ${conf>=60?'the model is reasonably certain':'the model sees conflicting signals'}.`
            : `This prediction uses rule-based analysis (model not yet trained on this stock). Treat with more caution than a trained-model prediction.`}
        </p>
      </div>

      <div style="padding:10px 12px;background:${dir==='NEUTRAL'?'#fffbe6':dir==='UP'?'#f0faf4':'#fff5f5'};
        border:1px solid ${dir==='NEUTRAL'?'#f0d060':dir==='UP'?'#c8e6c9':'#ffcdd2'};">
        <div class="rpt-head" style="margin-bottom:5px;">ACTIONABLE TAKEAWAY</div>
        <p style="font-family:Georgia,serif;font-size:0.84rem;line-height:1.7;color:#222;margin:0;">
          ${dir==='NEUTRAL'
            ? `The ML model is not giving a buy or sell signal. This is actually useful information — it confirms the cautious rating. <strong>Do not force a trade.</strong> Watch the ${revD} date for a potential breakout signal.`
            : dir==='UP'
            ? `ML supports a long bias. Combined with a BUY/OUTPERFORM rating, this adds conviction. Entry near ${inr(revP,0)} is the model's preferred zone.`
            : `ML is pointing down — consistent with the cautious rating. Avoid new long positions. If already long, tighten your stop loss.`}
        </p>
      </div>
    </div>
  </div>`;
}

// ── Stat cell ──────────────────────────────────────────
function cell(label, val, col, sub) {
  return `<div class="rpt-cell">
    <div class="rpt-head">${label}</div>
    <div class="rpt-val" style="color:${col||'#111'};">${val}</div>
    ${sub ? `<div class="rpt-sub">${sub}</div>` : ''}
  </div>`;
}

// ── Sparkline ──────────────────────────────────────────
function spark(history, w, h) {
  w = w||340; h = h||54;
  const pts = (history||[]).slice(-60);
  if (pts.length < 5) return '';
  const vals = pts.map(p => typeof p==='object' ? (p.close||0) : p).filter(v=>v>0);
  if (!vals.length) return '';
  const mn=Math.min(...vals), mx=Math.max(...vals), rng=mx-mn||1;
  const pad=4;
  const xs = vals.map((_,i) => pad + i/(vals.length-1)*(w-pad*2));
  const ys = vals.map(v => h-pad-(v-mn)/rng*(h-pad*2));
  const poly = xs.map((x,i)=>`${x.toFixed(1)},${ys[i].toFixed(1)}`).join(' ');
  const area = `${xs[0].toFixed(1)},${h} ${poly} ${xs[xs.length-1].toFixed(1)},${h}`;
  const col = vals[vals.length-1] >= vals[0] ? '#006633' : '#cc0000';
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" style="overflow:visible;display:block">
    <defs><linearGradient id="sg2" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${col}" stop-opacity="0.18"/>
      <stop offset="100%" stop-color="${col}" stop-opacity="0"/>
    </linearGradient></defs>
    <polygon points="${area}" fill="url(#sg2)"/>
    <polyline points="${poly}" fill="none" stroke="${col}" stroke-width="1.6" stroke-linejoin="round"/>
    <circle cx="${xs[xs.length-1].toFixed(1)}" cy="${ys[ys.length-1].toFixed(1)}"
      r="3" fill="${col}" stroke="#fff" stroke-width="1.5"/>
  </svg>`;
}

// ── Strip emojis + "Confidence: XXXX%" artefacts ──────
function clean(txt) {
  if (!txt) return '';
  return txt
    .replace(/[\u{1F300}-\u{1FFFF}]/gu, '')   // emoji
    .replace(/[\u2600-\u27BF]/g, '')           // misc symbols
    .replace(/Confidence:\s*\d+%/gi, '')       // "Confidence: 6000%"
    .replace(/NaN[×x%]?/gi, '—')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

// ══════════════════════════════════════════════════════
//  RENDER
// ══════════════════════════════════════════════════════
function renderReport(r, rpt, dateStr, sym) {
  const conf   = r.confidence || 0;
  const rt     = getRating(conf);
  const fr     = r.fund_ratios || {};
  const m      = rpt._metrics || {};
  const own    = rpt.shareholding || {};
  const upT1   = r.upside_t1_pct || 0;
  const upT2   = r.upside_t2_pct || 0;
  const dnSL   = r.price > 0 ? ((r.stop_loss - r.price)/r.price*100) : 0;
  const isBuy  = rt.label === 'BUY' || rt.label === 'OUTPERFORM';
  const isSell = rt.label === 'SELL' || rt.label === 'UNDERPERFORM';

  // ── Narratives (emoji-stripped) ──────────────────────
  const techTxt  = clean(rpt.technical  || '');
  const gannTxt  = clean(rpt.gann       || '');
  const natalTxt = clean(rpt.natal      || '');
  const simTxt   = clean(rpt.simons     || '');
  const fundTxt  = clean(rpt.fundamental|| '');
  const sentTxt  = clean(rpt.sentiment  || '');
  const verdict  = clean(rpt.overall_verdict || '');

  // ── Rating-consistent thesis points ──────────────────
  // Bull case: only shown when BUY/OUTPERFORM/NEUTRAL
  // Bear case: only shown when SELL/UNDERPERFORM/NEUTRAL
  const bullReasons = (r.buy_reasons || []).map(clean).filter(Boolean);
  const sellReasons = (r.sell_reasons|| []).map(clean).filter(Boolean);

  // Risks always shown, adjusted by rating
  const risks = [];
  if (isSell || !isBuy) {
    if ((r.bear_signals||0) > (r.bull_signals||0))
      risks.push(`Adverse planetary configuration — ${r.bear_signals} bear vs ${r.bull_signals} bull signals active.`);
    if ((r.regime||'').match(/BEAR|DOWN/i))
      risks.push(`Market regime classified as <strong>${r.regime}</strong> — trend headwinds limit upside.`);
    if ((r.news_score||0) < -0.1)
      risks.push(`News sentiment is negative (score ${((r.news_score||0)*100).toFixed(0)}%) — headline risk elevated.`);
  }
  if (r.bulk_signal === 'SELL')
    risks.push('Institutional block/bulk deal data indicates distribution pressure.');
  risks.push(`Thesis invalidated on a decisive close below <strong>${inr(r.stop_loss)}</strong> — exit without averaging.`);
  if ((m.ann_vol||0) > 40)
    risks.push(`Annualised volatility ${(m.ann_vol||0).toFixed(1)}% is elevated — size positions conservatively.`);

  // ── Catalyst dates ────────────────────────────────────
  const cats = [];
  if (r.buy_date)  cats.push({date:r.buy_date,  event: isBuy?'Entry Window':'Review Date', type: isBuy?'ENTRY':'REVIEW', note:r.buy_condition||''});
  if (r.sell_date) cats.push({date:r.sell_date, event:'Target / Exit Window', type:'EXIT', note:r.sell_condition||''});
  (r.reversal_dates||[]).slice(0,5).forEach(rd =>
    cats.push({date:rd.date||rd, event:rd.label||'Reversal Date', type:'CYCLE', note:rd.reason||`Score ${rd.score||''}`}));

  const nak = rpt.nakshatra || {};
  if (nak.upcoming_transitions && nak.upcoming_transitions.length > 0) {
    nak.upcoming_transitions.forEach(t => {
      cats.push({
        date: t.date,
        event: `Moon enters ${t.nakshatra}`,
        type: 'COSMIC',
        note: `Ruler: ${t.ruler} | Bias: ${t.bias} (${t.behavior})`
      });
    });
  }

  // Sort dates chronologically
  cats.sort((a, b) => {
    if (!a.date) return 1;
    if (!b.date) return -1;
    return a.date.localeCompare(b.date);
  });

  const sups = (r.supports||[]).filter(v=>v>0).slice(0,4);
  const ress = (r.resistances||[]).filter(v=>v>0).slice(0,4);

  // ── Rating-driven recommendation summary ──────────────
  function makeExecPara() {
    const nameStr = `<strong>${r.name||sym}</strong>`;
    const rtStr   = `<strong style="color:${rt.col};">${rt.label}</strong>`;
    const cmpStr  = inr(r.price);
    if (isBuy) {
      return `We initiate coverage of ${nameStr} with an ${rtStr} rating and a 12-month
        price target of <strong>${inr(r.target2)}</strong> (${pct(upT2)} upside from CMP of ${cmpStr}).
        A first-stage target of <strong>${inr(r.target1)}</strong> (${pct(upT1)}) is anticipated
        within ${r.hold_days||'—'} trading days. Entry is recommended at <strong>${inr(r.entry)}</strong>
        with a hard stop at <strong>${inr(r.stop_loss)}</strong>.
        The composite signal score of <strong>${conf.toFixed(1)}/100</strong> is supported by
        ${r.bull_signals||0} bullish planetary configurations, a Gann confluence score of
        ${r.gann_score||0}/20, and a fundamental grade of <strong>${r.fund_grade||'—'}</strong>.`;
    }
    if (isSell) {
      return `We initiate coverage of ${nameStr} with a ${rtStr} rating.
        The stock trades at ${cmpStr} with a composite signal score of only
        <strong>${conf.toFixed(1)}/100</strong>, reflecting ${r.bear_signals||0} active
        bearish planetary configurations against ${r.bull_signals||0} bullish, a Gann
        confluence score of ${r.gann_score||0}/20, and a market regime of
        <strong>${r.regime||'SIDEWAYS'}</strong>. We recommend existing holders
        reduce exposure or exit at market on any rally toward ${inr(r.resistances?.[0]||r.price*1.02)}.
        New positions are not recommended until the signal score recovers above 40/100.
        Risk-takers may consider a defined-risk short below ${inr(r.stop_loss)} with a cover target
        near ${inr(r.supports?.[0]||r.price*0.95)}.`;
    }
    // NEUTRAL
    return `We initiate coverage of ${nameStr} with a ${rtStr} rating.
      At a CMP of ${cmpStr} the composite signal score of <strong>${conf.toFixed(1)}/100</strong>
      does not provide sufficient directional conviction for an outright long or short position.
      We recommend existing holders maintain positions with trailing stops at ${inr(r.stop_loss)}.
      Prospective buyers should wait for a pullback toward ${inr(r.entry)} before initiating.
      Key catalysts to watch: entry window ${r.buy_date||'—'} and reversal dates in the
      catalyst calendar below.`;
  }

  // ── Trade section — adjusts for rating ───────────────
  function makeTradeSection() {
    if (isBuy) {
      return `<table class="rpt-table" style="margin-bottom:2px;">
        <thead><tr>
          <th style="width:120px;">LEVEL</th><th>PRICE</th><th>vs CMP</th>
          <th>RECOMMENDED ACTION</th><th>TRIGGER / RATIONALE</th>
        </tr></thead>
        <tbody>
          <tr>
            <td class="rpt-mono" style="color:#0055aa;font-weight:600;font-size:0.65rem;">ENTRY</td>
            <td class="rpt-mono" style="font-weight:700;color:#0055aa;">${inr(r.entry)}</td>
            <td class="rpt-mono" style="color:${r.entry<=r.price?'#006633':'#cc7700'};">
              ${r.entry>0&&r.price>0?pct((r.entry-r.price)/r.price*100):'—'}</td>
            <td style="color:#006633;">Initiate long position</td>
            <td style="color:#555;font-size:0.78rem;">${clean(r.entry_source)||'Simons Fourier trough / Gann Sq9 support'}</td>
          </tr>
          <tr style="background:#f9fdf9;">
            <td class="rpt-mono" style="color:#006633;font-weight:600;font-size:0.65rem;">TARGET 1</td>
            <td class="rpt-mono" style="font-weight:700;color:#006633;">${inr(r.target1)}</td>
            <td class="rpt-mono" style="color:#006633;">${pct(upT1)}</td>
            <td style="color:#006633;">Exit 50% of position; activate trailing stop on balance</td>
            <td style="color:#555;font-size:0.78rem;">${clean(r.t1_source)||'Cycle T1 resistance'}</td>
          </tr>
          <tr style="background:#f6fbf6;">
            <td class="rpt-mono" style="color:#338800;font-weight:600;font-size:0.65rem;">TARGET 2</td>
            <td class="rpt-mono" style="font-weight:700;color:#338800;">${inr(r.target2)}</td>
            <td class="rpt-mono" style="color:#338800;">${pct(upT2)}</td>
            <td style="color:#338800;">Exit remaining; distribution zone — full cycle exit</td>
            <td style="color:#555;font-size:0.78rem;">${clean(r.t2_source)||'Wave peak / Cycle T2'}</td>
          </tr>
          <tr style="background:#fff8f8;">
            <td class="rpt-mono" style="color:#cc0000;font-weight:600;font-size:0.65rem;">STOP LOSS</td>
            <td class="rpt-mono" style="font-weight:700;color:#cc0000;">${inr(r.stop_loss)}</td>
            <td class="rpt-mono" style="color:#cc0000;">${pct(dnSL)}</td>
            <td style="color:#cc0000;">Hard exit — thesis invalidated. No averaging down.</td>
            <td style="color:#555;font-size:0.78rem;">${clean(r.sl_source)||'Below wave structure / Gann cycle low'}</td>
          </tr>
        </tbody>
      </table>`;
    }
    if (isSell) {
      const reduceTarget = r.supports?.[0] || (r.price * 0.93);
      const avoidAbove   = r.resistances?.[0] || (r.price * 1.05);
      return `<table class="rpt-table" style="margin-bottom:2px;">
        <thead><tr>
          <th style="width:120px;">LEVEL</th><th>PRICE</th><th>vs CMP</th>
          <th>RECOMMENDED ACTION</th><th>RATIONALE</th>
        </tr></thead>
        <tbody>
          <tr style="background:#fff8f8;">
            <td class="rpt-mono" style="color:#cc0000;font-weight:600;font-size:0.65rem;">REDUCE / EXIT</td>
            <td class="rpt-mono" style="font-weight:700;color:#cc0000;">${inr(r.price)}</td>
            <td class="rpt-mono" style="color:#555;">At market</td>
            <td style="color:#cc0000;">Reduce exposure or exit long positions on rallies</td>
            <td style="color:#555;font-size:0.78rem;">Composite score ${conf.toFixed(0)}/100 — insufficient bullish conviction</td>
          </tr>
          <tr>
            <td class="rpt-mono" style="color:#cc7700;font-weight:600;font-size:0.65rem;">AVOID ABOVE</td>
            <td class="rpt-mono" style="font-weight:700;color:#cc7700;">${inr(avoidAbove)}</td>
            <td class="rpt-mono" style="color:#cc7700;">${r.price?pct((avoidAbove-r.price)/r.price*100):'—'}</td>
            <td style="color:#cc7700;">Do not initiate new long positions above this level</td>
            <td style="color:#555;font-size:0.78rem;">Key resistance — bearish signal strengthens above</td>
          </tr>
          <tr style="background:#f9fbff;">
            <td class="rpt-mono" style="color:#0055aa;font-weight:600;font-size:0.65rem;">SUPPORT / WATCH</td>
            <td class="rpt-mono" style="font-weight:700;color:#0055aa;">${inr(reduceTarget)}</td>
            <td class="rpt-mono" style="color:#0055aa;">${r.price?pct((reduceTarget-r.price)/r.price*100):'—'}</td>
            <td style="color:#0055aa;">Re-evaluate thesis if price reaches this support</td>
            <td style="color:#555;font-size:0.78rem;">Key support — may signal reversal and rating upgrade</td>
          </tr>
          <tr style="background:#fff8f8;">
            <td class="rpt-mono" style="color:#cc0000;font-weight:600;font-size:0.65rem;">STOP (SHORT)</td>
            <td class="rpt-mono" style="font-weight:700;color:#cc0000;">${inr(r.resistances?.[1]||avoidAbove*1.02)}</td>
            <td class="rpt-mono" style="color:#cc0000;">—</td>
            <td style="color:#cc0000;">Cover / stop for risk-takers with short positions</td>
            <td style="color:#555;font-size:0.78rem;">Above this level bearish thesis is invalidated</td>
          </tr>
        </tbody>
      </table>`;
    }
    // NEUTRAL
    return `<table class="rpt-table" style="margin-bottom:2px;">
      <thead><tr>
        <th style="width:120px;">LEVEL</th><th>PRICE</th><th>vs CMP</th>
        <th>RECOMMENDED ACTION</th><th>RATIONALE</th>
      </tr></thead>
      <tbody>
        <tr>
          <td class="rpt-mono" style="color:#0055aa;font-weight:600;font-size:0.65rem;">WAIT / WATCH</td>
          <td class="rpt-mono" style="font-weight:700;color:#0055aa;">${inr(r.entry)}</td>
          <td class="rpt-mono">${r.entry&&r.price?pct((r.entry-r.price)/r.price*100):'—'}</td>
          <td style="color:#0055aa;">Initiate only on pullback to this level</td>
          <td style="color:#555;font-size:0.78rem;">Insufficient signal conviction at current price</td>
        </tr>
        <tr style="background:#f9fbf9;">
          <td class="rpt-mono" style="color:#006633;font-weight:600;font-size:0.65rem;">TARGET</td>
          <td class="rpt-mono" style="font-weight:700;color:#006633;">${inr(r.target1)}</td>
          <td class="rpt-mono" style="color:#006633;">${pct(upT1)}</td>
          <td style="color:#006633;">First exit level if long from lower entry</td>
          <td style="color:#555;font-size:0.78rem;">${clean(r.t1_source)||'Cycle resistance'}</td>
        </tr>
        <tr style="background:#fff8f8;">
          <td class="rpt-mono" style="color:#cc0000;font-weight:600;font-size:0.65rem;">STOP LOSS</td>
          <td class="rpt-mono" style="font-weight:700;color:#cc0000;">${inr(r.stop_loss)}</td>
          <td class="rpt-mono" style="color:#cc0000;">${pct(dnSL)}</td>
          <td style="color:#cc0000;">Exit any position — signal turns bearish below</td>
          <td style="color:#555;font-size:0.78rem;">${clean(r.sl_source)||'Wave structure invalidation'}</td>
        </tr>
      </tbody>
    </table>`;
  }

  // ══════════════════════════════════════════════════
  //  HTML
  // ══════════════════════════════════════════════════
  const html = `
<div id="research-report" style="max-width:960px;margin:0 auto;padding:0 0 32px;">

<!-- ═════════════════════════════════════
     COVER
════════════════════════════════════= -->
<div class="rpt-cover" style="padding:32px 36px 24px;border-bottom:2px solid #111;">

  <!-- Firm bar -->
  <div style="display:flex;justify-content:space-between;align-items:center;
    margin-bottom:22px;padding-bottom:10px;border-bottom:1px solid #ccc;">
    <div class="rpt-head" style="font-size:0.62rem;letter-spacing:3px;">
      Vprofitables RESEARCH &nbsp;·&nbsp; EQUITY RESEARCH
    </div>
    <div class="rpt-head">RESEARCH NOTE &nbsp;·&nbsp; ${dateStr}</div>
  </div>

  <!-- Company + rating -->
  <div style="display:flex;justify-content:space-between;align-items:flex-start;
    gap:28px;flex-wrap:wrap;margin-bottom:24px;">
    <div style="flex:1;min-width:260px;">
      <h1 style="font-family:Georgia,serif;font-size:2.2rem;font-weight:700;
        color:#111;margin:0 0 6px;letter-spacing:0.2px;">${r.name||sym}</h1>
      <div class="rpt-mono" style="font-size:0.65rem;color:#666;letter-spacing:1px;margin-bottom:14px;">
        ${sym} &nbsp;·&nbsp; ${r.exchange||'NSE'} &nbsp;·&nbsp; ${r.sector||''} &nbsp;·&nbsp; Ruling planet: ${r.ruling_planet||'—'}
      </div>
      <!-- One-sentence thesis, rating-consistent -->
      <p style="font-family:Georgia,serif;font-size:0.95rem;line-height:1.72;
        color:#222;max-width:500px;margin:0;">
        ${isBuy
          ? `We initiate coverage with a <strong style="color:${rt.col};">${rt.label}</strong> rating.
             Price targets of ${inr(r.target1)} and ${inr(r.target2)} represent
             ${pct(upT1)} and ${pct(upT2)} upside from current levels.`
          : isSell
          ? `We initiate coverage with a <strong style="color:${rt.col};">${rt.label}</strong> rating.
             Composite signal score of ${conf.toFixed(1)}/100 with ${r.bear_signals||0} active
             bearish signals — we recommend reducing exposure.`
          : `We initiate coverage with a <strong style="color:${rt.col};">${rt.label}</strong> rating.
             Insufficient directional conviction at current levels —
             wait for pullback to ${inr(r.entry)} before initiating.`}
      </p>
    </div>

    <!-- Rating box -->
    <div style="text-align:center;min-width:150px;">
      <div style="border:2.5px solid ${rt.border};background:${rt.bg};
        padding:14px 30px;margin-bottom:8px;">
        <div style="font-family:Georgia,serif;font-size:2.4rem;font-weight:700;
          color:${rt.col};letter-spacing:1px;line-height:1;">${rt.label}</div>
      </div>
      <div class="rpt-head" style="margin-bottom:4px;">ANALYST RATING</div>
      <div class="rpt-mono" style="font-size:0.85rem;font-weight:700;color:#111;">${inr(r.price)}</div>
      <div class="rpt-head">CURRENT MARKET PRICE</div>
    </div>
  </div>

  <!-- Key metrics strip -->
  <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:1px;margin-bottom:18px;">
    ${cell('Price Target (T1)', inr(r.target1), isBuy?'#006633':'#555', pct(upT1)+' upside')}
    ${cell('Price Target (T2)', inr(r.target2), isBuy?'#338800':'#555', pct(upT2)+' upside')}
    ${cell('Stop Loss', inr(r.stop_loss), '#cc0000', pct(dnSL)+' downside')}
    ${cell('Risk / Reward', xfmt(r.rr_ratio,null,1)+'×', '#111', xfmt(r.hold_days,null,0)+' day hold')}
    ${cell('Signal Score', conf.toFixed(1)+'/100', rt.col, rt.label)}
    ${cell('Market Regime', r.regime||'—',
      (r.regime||'').match(/BULL/i)?'#006633':(r.regime||'').match(/BEAR/i)?'#cc0000':'#7a5c00',
      'Current regime')}
  </div>

  <!-- Sparkline + score bar -->
  <div style="display:flex;gap:28px;flex-wrap:wrap;align-items:flex-start;">
    <div>
      <div class="rpt-head" style="margin-bottom:6px;">60-DAY PRICE HISTORY</div>
      ${spark(r.price_history)}
    </div>
    <div style="flex:1;min-width:200px;">
      <div class="rpt-head" style="margin-bottom:6px;">
        COMPOSITE SIGNAL STRENGTH &nbsp;·&nbsp; ${conf.toFixed(1)} / 100
      </div>
      <div style="height:8px;background:#eee;border:1px solid #ddd;">
        <div style="width:${Math.min(conf,100)}%;height:100%;background:${rt.col};"></div>
      </div>
      <div style="display:flex;justify-content:space-between;margin-top:6px;">
        ${[
          ['Fundamental', r.fund_score||0, 25],
          ['Gann', r.gann_score||0, 20],
          ['Natal', r.natal_score||0, 20],
          ['Planetary', r.planet_score||0, 15],
        ].map(([l,v,mx])=>`<span class="rpt-mono" style="font-size:0.58rem;color:#666;">
          ${l}: ${v}/${mx}</span>`).join('')}
      </div>
    </div>
  </div>
</div><!-- /cover -->

<div style="padding:0 36px;">

<!-- ═══════════ 01 INVESTMENT THESIS ═══════════ -->
${sec(1,'Investment Thesis')}
<div style="display:grid;grid-template-columns:1fr 1fr;gap:2px;margin-bottom:4px;">

  <div style="border-left:3px solid #006633;border:1px solid #c8e6c9;
    border-left-width:3px;border-left-color:#006633;padding:16px 18px;background:#fafff9;">
    <div class="rpt-head" style="color:#006633;margin-bottom:12px;">
      BULL CASE &nbsp;/&nbsp; ${isBuy?'REASONS TO BUY':'POTENTIAL UPSIDE CATALYSTS'}
    </div>
    ${bullReasons.length
      ? bullReasons.map(b=>`<p style="font-family:Georgia,serif;font-size:0.83rem;
          line-height:1.7;color:#222;margin:0 0 8px;padding-bottom:8px;
          border-bottom:1px solid #e8f5e9;">
          <span style="color:#006633;margin-right:6px;">›</span>${b}</p>`).join('')
      : `<p style="font-family:Georgia,serif;font-size:0.83rem;color:#666;">
          Insufficient bullish signals at current levels.</p>`}
  </div>

  <div style="border:1px solid #ffcdd2;border-left:3px solid #cc0000;padding:16px 18px;background:#fff9f9;">
    <div class="rpt-head" style="color:#cc0000;margin-bottom:12px;">
      BEAR CASE &nbsp;/&nbsp; KEY RISKS
    </div>
    ${risks.map(rk=>`<p style="font-family:Georgia,serif;font-size:0.83rem;
        line-height:1.7;color:#222;margin:0 0 8px;padding-bottom:8px;
        border-bottom:1px solid #ffebee;">
        <span style="color:#cc0000;margin-right:6px;">›</span>${rk}</p>`).join('')}
  </div>
</div>

<!-- ═══════════ RATING EXPLAINER ═══════════ -->
${sec('★','Why This Rating?  —  Signal Explainer')}
${ratingExplainer(conf, isBuy, isSell, r)}

<!-- ═══════════ 02 VALUATION & FUNDAMENTALS ═══════════ -->
${sec(2,'Valuation  &  Fundamentals')}
<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:1px;margin-bottom:4px;">
  ${cell('P/E Ratio',    fr.pe!=null&&isFinite(fr.pe) ? xfmt(fr.pe,null,1)+'×' : '—', fr.pe<20?'#006633':fr.pe>35?'#cc0000':'#7a5c00', 'Price / Earnings')}
  ${cell('ROE',          fr.roe!=null&&isFinite(fr.roe) ? xfmt(fr.roe,null,1)+'%' : '—', fr.roe>15?'#006633':'#555', 'Return on Equity')}
  ${cell('D/E Ratio',    fr.de!=null&&isFinite(fr.de) ? xfmt(fr.de,null,2) : '—', fr.de<1?'#006633':fr.de>2?'#cc0000':'#7a5c00', 'Debt / Equity')}
  ${cell('Rev. Growth',  fr.revenue_growth!=null&&isFinite(fr.revenue_growth) ? pct(fr.revenue_growth) : '—', (fr.revenue_growth||0)>0?'#006633':'#cc0000', 'YoY Revenue')}
  ${cell('Fund. Grade',  r.fund_grade||'—', r.fund_grade==='A'?'#006633':r.fund_grade==='B'?'#7a5c00':'#555', r.fund_verdict||'')}
</div>
<div style="border:1px solid #ddd;padding:16px 18px;background:#fdfdfd;margin-bottom:4px;">
  <div class="rpt-head" style="margin-bottom:8px;">FUNDAMENTAL COMMENTARY</div>
  <p style="font-family:Georgia,serif;font-size:0.85rem;line-height:1.78;color:#222;margin:0;">
    ${fundTxt || 'Fundamental analysis data not available for this period.'}</p>
</div>

<!-- ═══════════ 03 PRICE TARGETS & TRADE STRUCTURE ═══════════ -->
${sec(3, isBuy ? 'Price Targets  &  Trade Structure' : isSell ? 'Recommendation  &  Exit Strategy' : 'Trade Structure  &  Key Levels')}
${makeTradeSection()}
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1px;margin-bottom:4px;">
  ${cell('Est. Hold Period',  xfmt(r.hold_days,null,0)+' days', '#555', 'Approximate horizon')}
  ${cell('Risk per Trade',    pct(r.risk_pct||0,1), '#cc0000', 'Max drawdown to stop')}
  ${cell('Sector Index',      r.sector_index||'—', '#555', r.sector_index_trend||'')}
  ${cell('Sector Trend (20d)',r.sector_index_trend||'—',
    (r.sector_index_trend||'').match(/BULL/i)?'#006633':(r.sector_index_trend||'').match(/BEAR/i)?'#cc0000':'#7a5c00',
    r.sector_index_chg!=null?pct(r.sector_index_chg)+' (20d)':'')}
</div>

<!-- ═══════════ SCENARIO PRICE CHART ═══════════ -->
${sec('▶','Price Scenario Projections  —  3 Paths from Today')}
<div style="padding:16px 0 8px;">
  <div style="display:flex;gap:16px;margin-bottom:12px;flex-wrap:wrap;">
    <div style="flex:1;padding:10px 14px;background:#f0faf4;border:1px solid #c8e6c9;min-width:140px;">
      <div class="rpt-head" style="color:#006633;margin-bottom:4px;">BULL SCENARIO</div>
      <div style="font-family:'Share Tech Mono',monospace;font-size:0.9rem;font-weight:700;color:#006633;">${inr(r.target2,0)}</div>
      <div style="font-family:Georgia,serif;font-size:0.78rem;color:#555;margin-top:3px;">
        Target 2 — ${pct(upT2)} upside. Stock follows Gann cycle to distribution zone. All engines aligned.
      </div>
    </div>
    <div style="flex:1;padding:10px 14px;background:#f0f6ff;border:1px solid #bbdefb;min-width:140px;">
      <div class="rpt-head" style="color:#0055aa;margin-bottom:4px;">BASE SCENARIO</div>
      <div style="font-family:'Share Tech Mono',monospace;font-size:0.9rem;font-weight:700;color:#0055aa;">${inr(r.target1,0)}</div>
      <div style="font-family:Georgia,serif;font-size:0.78rem;color:#555;margin-top:3px;">
        Target 1 — ${pct(upT1)} upside. Stock reaches T1 resistance; exit 50%, trail rest.
      </div>
    </div>
    <div style="flex:1;padding:10px 14px;background:#fff5f5;border:1px solid #ffcdd2;min-width:140px;">
      <div class="rpt-head" style="color:#cc0000;margin-bottom:4px;">BEAR SCENARIO</div>
      <div style="font-family:'Share Tech Mono',monospace;font-size:0.9rem;font-weight:700;color:#cc0000;">${inr(r.stop_loss,0)}</div>
      <div style="font-family:Georgia,serif;font-size:0.78rem;color:#555;margin-top:3px;">
        Stop loss hit — ${pct(dnSL)} drawdown. Thesis invalidated. Hard exit, no averaging.
      </div>
    </div>
  </div>
  <div style="background:#fdfdfd;border:1px solid #e0e0e0;padding:16px 12px;overflow-x:auto;">
    ${scenarioChart(r.price, r.entry||r.price, r.target1, r.target2, r.stop_loss, r.hold_days||60, dateStr)}
  </div>
</div>

<!-- ═══════════ 04 CATALYST CALENDAR ═══════════ -->
${sec(4,'Catalyst Calendar')}
${cats.length ? `
<table class="rpt-table" style="margin-bottom:4px;">
  <thead><tr>
    <th style="width:110px;">DATE</th>
    <th>EVENT</th>
    <th style="width:80px;">TYPE</th>
    <th>DETAIL  /  CONDITION</th>
  </tr></thead>
  <tbody>
    ${cats.map((c,i) => {
      const col = c.type==='ENTRY'?'#0055aa':c.type==='EXIT'?'#006633':c.type==='COSMIC'?'#660099':c.type==='REVIEW'?'#7a5c00':'#7a5c00';
      return `<tr style="${i%2===1?'background:#f9f9f9':''}">
        <td class="rpt-mono" style="color:#0055aa;">${c.date||'—'}</td>
        <td style="font-family:Georgia,serif;">${c.event}</td>
        <td><span class="rpt-mono" style="font-size:0.58rem;color:${col};
          background:${col}15;padding:2px 8px;border:1px solid ${col}40;">${c.type}</span></td>
        <td style="color:#555;font-family:Georgia,serif;font-size:0.8rem;">${clean(c.note)}</td>
      </tr>`;
    }).join('')}
  </tbody>
</table>` : `<div style="padding:12px;border:1px solid #ddd;color:#888;
  font-family:Georgia,serif;font-size:0.84rem;">No catalyst dates available.</div>`}

<!-- ═══════════ 05 TECHNICAL ANALYSIS ═══════════ -->
${sec(5,'Technical Analysis')}
<div style="display:grid;grid-template-columns:1fr 1fr;gap:2px;margin-bottom:4px;">
  <div style="border:1px solid #ddd;padding:14px 16px;background:#fafafa;">
    <div class="rpt-head" style="color:#006633;margin-bottom:10px;">SUPPORT LEVELS</div>
    ${sups.map((s,i)=>`<div style="display:flex;justify-content:space-between;
      padding:7px 0;${i<sups.length-1?'border-bottom:1px solid #f0f0f0':''}">
      <span class="rpt-mono" style="font-size:0.65rem;color:#888;">S${i+1}</span>
      <span class="rpt-mono" style="font-size:0.88rem;font-weight:700;color:#006633;">${inr(s)}</span>
      <span class="rpt-mono" style="font-size:0.65rem;color:${s<r.price?'#006633':'#cc0000'};">
        ${r.price?pct((s-r.price)/r.price*100):'—'}</span>
    </div>`).join('') || '<p style="color:#888;font-size:0.82rem;">No support levels identified</p>'}
  </div>
  <div style="border:1px solid #ddd;padding:14px 16px;background:#fafafa;">
    <div class="rpt-head" style="color:#cc0000;margin-bottom:10px;">RESISTANCE LEVELS</div>
    ${ress.map((rs,i)=>`<div style="display:flex;justify-content:space-between;
      padding:7px 0;${i<ress.length-1?'border-bottom:1px solid #f0f0f0':''}">
      <span class="rpt-mono" style="font-size:0.65rem;color:#888;">R${i+1}</span>
      <span class="rpt-mono" style="font-size:0.88rem;font-weight:700;color:#cc0000;">${inr(rs)}</span>
      <span class="rpt-mono" style="font-size:0.65rem;color:${rs>r.price?'#cc0000':'#006633'};">
        ${r.price?pct((rs-r.price)/r.price*100):'—'}</span>
    </div>`).join('') || '<p style="color:#888;font-size:0.82rem;">No resistance levels identified</p>'}
  </div>
</div>
<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:1px;margin-bottom:4px;">
  ${cell('RSI (14)', m.rsi?xfmt(m.rsi,null,1):'—', m.rsi<30?'#006633':m.rsi>70?'#cc0000':'#7a5c00', m.rsi<30?'Oversold':m.rsi>70?'Overbought':'Neutral')}
  ${cell('Ann. Volatility', m.ann_vol?xfmt(m.ann_vol,null,1)+'%':'—', m.ann_vol>40?'#cc0000':'#555', m.ann_vol>40?'Elevated':'Normal')}
  ${cell('Volume Signal', m.vol_surge?'SURGE':'NORMAL', m.vol_surge?'#cc7700':'#555', 'vs 20d average')}
  ${cell('Candle Pattern', (m.candle_patterns||[]).slice(0,1)[0]||'None', '#555', 'Latest signal')}
  ${cell('Tech. Momentum', r.tech_momentum||'NEUTRAL', (r.tech_momentum||'').match(/BULL/i)?'#006633':(r.tech_momentum||'').match(/BEAR/i)?'#cc0000':'#7a5c00', 'Momentum signal')}
</div>
<div style="border:1px solid #ddd;padding:15px 18px;background:#fdfdfd;margin-bottom:4px;">
  <p style="font-family:Georgia,serif;font-size:0.85rem;line-height:1.78;color:#222;margin:0;">
    ${techTxt||'Technical analysis data not available.'}</p>
</div>

<!-- ═══════════ 06 GANN & CYCLE ANALYSIS ═══════════ -->
${sec(6,'Gann  &  Cycle Analysis')}
<div style="display:grid;grid-template-columns:1fr 1fr;gap:2px;margin-bottom:4px;">
  <div style="border:1px solid #ddd;padding:15px 18px;background:#fdfdfd;">
    <div class="rpt-head" style="color:#0055aa;margin-bottom:10px;">GANN ANALYSIS</div>
    <p style="font-family:Georgia,serif;font-size:0.85rem;line-height:1.78;color:#222;margin:0;">
      ${gannTxt||'Gann analysis data not available.'}</p>
  </div>
  <div style="border:1px solid #ddd;padding:15px 18px;background:#fdfdfd;">
    <div class="rpt-head" style="color:#660099;margin-bottom:10px;">SIMONS / FOURIER CYCLE</div>
    <p style="font-family:Georgia,serif;font-size:0.85rem;line-height:1.78;color:#222;margin:0;">
      ${simTxt||'Cycle analysis data not available.'}</p>
  </div>
</div>
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1px;margin-bottom:4px;">
  ${cell('Gann Score',     xfmt(r.gann_score,null,0)+'/20', '#0055aa', 'Sq9 confluence')}
  ${cell('Simons Score',   xfmt(r.simons_100,null,0)+'/100', '#660099', 'Quant regime')}
  ${cell('Best Entry Date',r.buy_date||'—', '#0055aa', r.buy_time||'')}
  ${cell('Best Exit Date', r.sell_date||'—', '#cc0000', r.sell_time||'')}
</div>

<!-- ═══════════ 07 NATAL & PLANETARY ANALYSIS ═══════════ -->
${sec(7,'Natal  &  Planetary Analysis')}
<div style="display:grid;grid-template-columns:1fr 1fr;gap:2px;margin-bottom:4px;">
  <div style="border:1px solid #ddd;padding:15px 18px;background:#fdfdfd;">
    <div class="rpt-head" style="color:#880066;margin-bottom:10px;">NATAL CHART ANALYSIS</div>
    <p style="font-family:Georgia,serif;font-size:0.85rem;line-height:1.78;color:#222;margin:0 0 10px;">
      ${natalTxt||'Natal analysis data not available.'}</p>
    <div style="display:flex;gap:18px;">
      <span class="rpt-mono" style="font-size:0.65rem;color:#006633;">
        ▲ ${r.bull_signals||0} Bull signals</span>
      <span class="rpt-mono" style="font-size:0.65rem;color:#cc0000;">
        ▼ ${r.bear_signals||0} Bear signals</span>
      <span class="rpt-mono" style="font-size:0.65rem;color:#555;">
        Ruler: ${r.ruling_planet||'—'}</span>
    </div>
  </div>
  <div style="border:1px solid #ddd;padding:15px 18px;background:#fdfdfd;">
    <div class="rpt-head" style="color:#cc5500;margin-bottom:10px;">ACTIVE PLANETARY ASPECTS</div>
    ${(r.natal_aspects||[]).length
      ? r.natal_aspects.map(a => {
          const txt = clean(typeof a==='string'?a:(a.description||a.aspect||''));
          const bull = txt.match(/trine|sextile|bull|conjunct.*jup/i);
          return txt ? `<div style="font-family:Georgia,serif;font-size:0.81rem;
            line-height:1.65;color:#222;padding:4px 0;border-bottom:1px solid #f0f0f0;">
            <span style="color:${bull?'#006633':'#cc0000'};margin-right:5px;">
              ${bull?'↑':'↓'}</span>${txt}</div>` : '';
        }).filter(Boolean).join('')
      : `<p style="font-family:Georgia,serif;font-size:0.82rem;color:#888;margin:0;">
          ${(r.planet_text||[]).map(clean).join(' ') || 'No active aspects data available.'}</p>`}
  </div>
</div>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1px;margin-bottom:4px;">
  ${cell('Natal Score',  xfmt(r.natal_score,null,1)+'/20', '#880066', 'Natal strength')}
  ${cell('Planet Score', xfmt(r.planet_score,null,1)+'/15', '#cc5500', 'Sky aspects')}
  ${cell('Sky Bull/Bear',`${r.sky_bull||0}B / ${r.sky_bear||0}R`,
    (r.sky_bull||0)>(r.sky_bear||0)?'#006633':'#cc0000', 'Current sky')}
</div>

<!-- ═══════════ 07B NAKSHATRA MARKET TIMING ═══════════ -->
${sec('07B','Nakshatra Market Timing')}
${(()=>{
  const nak = rpt.nakshatra || {};
  if (!nak.nakshatra) return '<div style="padding:12px;border:1px solid #ddd;color:#888;font-family:Georgia,serif;font-size:0.84rem;margin-bottom:4px;">Nakshatra timing data not available.</div>';
  
  const favSectors = nak.fav_sectors || [];
  const trans = nak.upcoming_transitions || [];
  const rahuSched = nak.rahu_kaal_schedule || [];
  
  let html = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:2px;margin-bottom:4px;">`
    + `<div style="border:1px solid #ddd;padding:15px 18px;background:#fdfdfd;">`
    + `<div class="rpt-head" style="color:#0055aa;margin-bottom:10px;">LUNAR MANSION PROFILE</div>`
    + `<p style="font-family:Georgia,serif;font-size:0.85rem;line-height:1.78;color:#222;margin:0 0 10px;">`
    + `Moon occupies the Nakshatra <strong>${nak.nakshatra.toUpperCase()}</strong> (ruled by ${nak.ruler.toUpperCase()}). `
    + `Classified as <strong>${nak.guna || 'N/A'}</strong> with a <strong>${nak.behavior || 'N/A'}</strong> profile. `
    + `Cosmic trade style recommendation is <strong style="color:#0055aa;">${nak.trade_style || 'N/A'}</strong>. `
    + `Today's score bonus: <strong style="color:#006633;">+${nak.nak_score || 0} pts</strong>.`
    + `</p>`
    + `<div style="margin-top:12px;padding:10px 12px;background:#fcfcfa;border-left:2px solid #e5c158;font-size:0.82rem;line-height:1.6;color:#333;">`
    + `<strong>Market Timing Note:</strong> ${nak.market_note || ''}`
    + `</div>`
    + `</div>`
    + `<div style="border:1px solid #ddd;padding:15px 18px;background:#fdfdfd;display:flex;flex-direction:column;gap:12px;">`
    + `<div class="rpt-head" style="color:#cc5500;margin-bottom:4px;">DAILY MUHURAT WINDOWS (IST)</div>`
    + `<div><span class="rpt-mono" style="font-size:0.6rem;color:#666;display:block;margin-bottom:2px;">🌞 ABHIJIT MUHURAT (AUSPICIOUS ENTRY)</span>`
    + `<span class="rpt-mono" style="font-size:0.88rem;font-weight:700;color:#006633;">${nak.abhijit_muhurat || '—'}</span></div>`
    + `<div><span class="rpt-mono" style="font-size:0.6rem;color:#666;display:block;margin-bottom:2px;">💀 RAHU KAAL (AVOID TRADING WINDOW)</span>`
    + `<span class="rpt-mono" style="font-size:0.88rem;font-weight:700;color:#cc0000;">${nak.rahu_kaal || '—'}</span></div>`
    + `</div>`
    + `</div>`;
    
  if (trans.length > 0) {
    html += `<div style="border:1px solid #ddd;padding:15px 18px;background:#fafafa;margin-bottom:4px;">`
      + `<div class="rpt-head" style="color:#0055aa;margin-bottom:8px;">🌌 UPCOMING MOON-NAKSHATRA TRANSITIONS</div>`
      + `<table class="rpt-table">`
      + `<thead><tr><th>DATE</th><th>NAKSHATRA</th><th>RULER</th><th>BIAS</th><th>BEHAVIOR PROFILE</th></tr></thead>`
      + `<tbody>`
      + trans.map(t => {
          const biasCol = t.bias === 'BULLISH' ? '#006633' : t.bias === 'BEARISH' ? '#cc0000' : t.bias === 'VOLATILE' ? '#cc7700' : '#333';
          return `<tr>`
            + `<td class="rpt-mono">${t.date.replace(/-/g,'/')}</td>`
            + `<td><strong>${t.nakshatra}</strong></td>`
            + `<td class="rpt-mono">${t.ruler}</td>`
            + `<td class="rpt-mono" style="color:${biasCol};font-weight:700;">${t.bias}</td>`
            + `<td>${t.behavior}</td>`
            + `</tr>`;
        }).join('')
      + `</tbody>`
      + `</table>`
      + `</div>`;
  }
  
  if (rahuSched.length > 0) {
    html += `<div style="border:1px solid #ddd;padding:15px 18px;background:#fafafa;margin-bottom:4px;">`
      + `<div class="rpt-head" style="color:#cc0000;margin-bottom:8px;">💀 WEEKLY RAHU KAAL SCHEDULE (IST)</div>`
      + `<div style="display:flex;flex-wrap:wrap;gap:8px;">`
      + rahuSched.map(rs => {
          return `<span style="background:rgba(204,0,0,0.05);border:1px solid rgba(204,0,0,0.2);padding:4px 10px;font-family:'Share Tech Mono',monospace;font-size:0.75rem;color:#cc0000;">`
            + `<strong>${rs.day}</strong>: ${rs.window}`
            + `</span>`;
        }).join('')
      + `</div>`
      + `</div>`;
  }
  
  return html;
})()}

<!-- ═══════════ 08 ML SIGNAL ENGINE ═══════════ -->
${sec(8,'ML Signal Engine  \u2014  Plain English Explanation')}
${mlExplainer(r.ml_long || r.ml_short || {}, r.price, isBuy)}

<!-- ═══════════ 09 SENTIMENT & INSTITUTIONAL ═══════════ -->
${sec(9,'Sentiment  &  Institutional Activity')}
<div style="display:grid;grid-template-columns:1fr 1fr;gap:2px;margin-bottom:4px;">
  <div style="border:1px solid #ddd;padding:15px 18px;background:#fdfdfd;">
    <div class="rpt-head" style="color:#7a5c00;margin-bottom:10px;">MARKET SENTIMENT</div>
    <p style="font-family:Georgia,serif;font-size:0.85rem;line-height:1.78;color:#222;margin:0 0 10px;">
      ${sentTxt||'Sentiment data not available.'}</p>
    ${r.news_headline?`<blockquote style="border-left:2px solid #ccc;margin:10px 0 0;
      padding:8px 14px;font-family:Georgia,serif;font-style:italic;
      font-size:0.8rem;color:#555;">"${clean(r.news_headline)}"</blockquote>`:''}
  </div>
  <div style="border:1px solid #ddd;padding:15px 18px;background:#fdfdfd;">
    <div class="rpt-head" style="color:#7a5c00;margin-bottom:10px;">INSTITUTIONAL ACTIVITY</div>
    <div class="rpt-mono" style="font-size:0.82rem;font-weight:700;margin-bottom:8px;
      color:${r.bulk_signal==='BUY'?'#006633':r.bulk_signal==='SELL'?'#cc0000':'#555'};">
      ${r.bulk_signal==='BUY'?'▲ Institutional Buying':r.bulk_signal==='SELL'?'▼ Institutional Selling':'━ Neutral Activity'}
    </div>
    <div class="rpt-mono" style="font-size:0.75rem;color:#333;margin-bottom:12px;">
      Net capital flow (30d):
      <strong style="color:${(r.bulk_net_val_cr||0)>0?'#006633':'#cc0000'};">
        ₹${xfmt(r.bulk_net_val_cr,null,1)} Cr</strong>
    </div>
    <div class="rpt-head" style="margin-bottom:8px;">SHAREHOLDING PATTERN (LATEST)</div>
    ${[
      {l:'FII / FPI', v:own.fii_pct,      chg:own.fii_change, col:'#0055aa'},
      {l:'DII',       v:own.dii_pct,      chg:own.dii_change, col:'#7a5c00'},
      {l:'Promoter',  v:own.promoter_pct, col:'#550099'},
      {l:'Retail',    v:own.retail_pct,   col:'#555'},
    ].filter(o=>o.v!=null).map(o=>`
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <span class="rpt-mono" style="font-size:0.6rem;color:#666;width:66px;">${o.l}</span>
        <div style="flex:1;height:3px;background:#eee;">
          <div style="width:${Math.min(o.v||0,100)}%;height:100%;background:${o.col};"></div>
        </div>
        <span class="rpt-mono" style="font-size:0.64rem;color:${o.col};">
          ${xfmt(o.v,null,1)}%
          ${o.chg!=null&&o.chg!==0?`<span style="color:${o.chg>0?'#006633':'#cc0000'};">
            (${o.chg>0?'+':''}${xfmt(o.chg,null,1)}%)</span>`:''}
        </span>
      </div>`).join('') ||
      '<p style="color:#888;font-size:0.8rem;margin:0;">Data not available</p>'}
  </div>
</div>

<!-- ═══════════ 10 EXECUTIVE SUMMARY ═══════════ -->
${sec(10,'Executive Summary')}
<div style="border:2px solid ${rt.border};background:${rt.bg};padding:24px 26px;margin-bottom:4px;">
  <div style="display:flex;align-items:center;gap:20px;margin-bottom:16px;flex-wrap:wrap;">
    <div style="font-family:Georgia,serif;font-size:2.4rem;font-weight:700;
      color:${rt.col};line-height:1;">${rt.label}</div>
    <div>
      <div style="font-family:Georgia,serif;font-size:1.05rem;font-weight:600;color:#111;">
        ${r.name||sym}
        <span style="font-size:0.8rem;font-weight:400;color:#666;margin-left:6px;">${sym}</span>
      </div>
      <div class="rpt-mono" style="font-size:0.6rem;color:#666;margin-top:4px;letter-spacing:1px;">
        Price Target: ${inr(r.target1)} / ${inr(r.target2)} &nbsp;·&nbsp;
        Stop Loss: ${inr(r.stop_loss)} &nbsp;·&nbsp;
        R:R ${xfmt(r.rr_ratio,null,1)}× &nbsp;·&nbsp;
        Score: ${conf.toFixed(1)}/100 &nbsp;·&nbsp; ${dateStr}
      </div>
    </div>
  </div>
  <p style="font-family:Georgia,serif;font-size:0.9rem;line-height:1.84;color:#222;margin:0 0 14px;">
    ${makeExecPara()}
  </p>
  ${verdict ? `<p style="font-family:Georgia,serif;font-size:0.9rem;line-height:1.84;color:#222;margin:0;">
    ${verdict}</p>` : ''}
</div>

<!-- Disclosure -->
<div style="padding:16px 20px;border:1px solid #e0e0e0;background:#f7f7f7;
  font-family:Georgia,serif;font-size:0.62rem;color:#555;
  line-height:1.75;margin-top:2px;">
  <strong style="font-family:'Share Tech Mono',monospace;letter-spacing:1px;font-size:0.65rem;color:#222;display:block;margin-bottom:6px;">IMPORTANT DISCLOSURES & MODEL UNCERTAINTY WARNING:</strong>
  This research note is produced by Vprofitables Research and is for informational purposes only.
  It does not constitute financial advice, an offer, or a solicitation to buy or sell any security.
  <strong>Model Uncertainty Warning:</strong> All financial forecasting models—including Discounted Cash Flow (DCF) valuations, Simons Quant Fourier cycles, machine learning trend predictors, Gann Square of Nine geometric targets, and Astro-Natal alignments—are <strong>probabilistic in nature</strong>. While these tools construct high-probability zones based on historical price-time patterns, they are subject to statistical errors and <strong>cannot guarantee future performance or absolute correctness</strong>. Real-world financial markets are complex adaptive systems influenced by unpredictable macroeconomic factors, regulatory decisions, corporate disclosures, and global black swan events. Investors must apply strict risk-management protocols, leverage appropriate position sizing, and utilize stop-loss levels to mitigate downside risk.
  &nbsp;·&nbsp; <span style="font-family:'Share Tech Mono',monospace;font-size:0.58rem;">Generated: ${new Date().toLocaleString('en-IN')} &nbsp;·&nbsp; Data as of: ${dateStr} &nbsp;·&nbsp; Vprofitables</span>
</div>

<!-- ═══════════ AI EARNINGS INTELLIGENCE ═══════════ -->
<div id="res-ai-section" style="margin:18px 0 0 0;"></div>

</div><!-- /padded body -->
</div><!-- /research-report -->
`;

  document.getElementById('res-output').innerHTML = html;

  // ── Load AI Earnings Extraction after report renders ─────────
  _loadAIEarnings(sym);
}

// ── AI Earnings + Q&A ─────────────────────────────────────────
async function _loadAIEarnings(sym) {
  const el = document.getElementById('res-ai-section');
  if (!el) return;

  el.innerHTML = `
    <div style="background:rgba(41,98,255,0.06);border:1px solid rgba(0,212,255,0.25);
      border-radius:6px;padding:16px;margin-bottom:4px;">
      <div style="color:var(--cyan);font-family:Share Tech Mono,monospace;font-size:0.78rem;
        letter-spacing:1px;margin-bottom:12px;">🤖 AI EARNINGS INTELLIGENCE — LLM EXTRACTION</div>
      <div style="font-size:0.78rem;color:var(--dim);">Loading AI analysis…</div>
    </div>`;

  let d = null;
  try {
    d = await api('llm_extract', { symbol: sym });
  } catch(e) {
    el.innerHTML = '';
    return;
  }

  // ── Handle background extraction in progress ──────────────────
  if (d && d.status === 'extracting') {
    el.innerHTML = `
      <div style="background:rgba(41,98,255,0.06);border:1px solid rgba(0,212,255,0.25);
        border-radius:6px;padding:14px 16px;margin-bottom:4px;">
        <div style="color:var(--cyan);font-family:Share Tech Mono,monospace;
          font-size:0.72rem;letter-spacing:1px;margin-bottom:8px;">🤖 AI EARNINGS INTELLIGENCE</div>
        <div style="display:flex;align-items:center;gap:10px;">
          <div class="spinner" style="width:16px;height:16px;border-width:2px;"></div>
          <span style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--dim);">
            Analysing earnings data for ${sym}… auto-refreshing in 5s
          </span>
        </div>
      </div>`;
    // Auto-poll once after 5 seconds
    setTimeout(() => _loadAIEarnings(sym), 5000);
    return;
  }

  const llm = d && d.extraction;
  if (!llm) { el.innerHTML = ''; return; }

  const tone     = llm.mgmt_tone || 0;
  const toneCol  = tone >= 0.2 ? '#26a69a' : tone <= -0.2 ? '#ef5350' : '#7aa8c0';
  const tonePct  = Math.round(((tone + 1) / 2) * 100);
  const guidCol  = {raised:'#26a69a', lowered:'#ef5350', maintained:'#7aa8c0', none:'#555'}[llm.guidance_direction||'none'] || '#555';
  const guidIcon = {raised:'⬆ RAISED', lowered:'⬇ LOWERED', maintained:'➡ MAINTAINED', none:'— N/A'}[llm.guidance_direction||'none'] || '—';
  const method   = {ollama:'🟢 Ollama Llama-3', llama_cpp:'🟡 llama-cpp GGUF', rules:'🔵 Rule-based NLP', cached:'📦 Cached'}[llm.extractor_method||'rules'] || llm.extractor_method;
  const risks    = (llm.key_risks || []).slice(0, 5);
  const history  = (d.history || []).slice(0, 3);

  // ── History table ──────────────────────────────────────────
  const histTable = history.length > 1 ? `
    <div style="margin-top:12px;padding-top:12px;border-top:1px solid rgba(255,255,255,0.06);">
      <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);margin-bottom:6px;">EXTRACTION HISTORY</div>
      <table style="width:100%;border-collapse:collapse;font-family:Share Tech Mono,monospace;font-size:0.6rem;">
        <tr style="color:var(--dim);border-bottom:1px solid rgba(255,255,255,0.06);">
          <th style="text-align:left;padding:3px 6px;">Period</th>
          <th style="text-align:center;">EPS Beat</th>
          <th style="text-align:center;">Rev YoY</th>
          <th style="text-align:center;">Tone</th>
          <th style="text-align:center;">Guidance</th>
        </tr>
        ${history.map(h => {
          const tc = (h.mgmt_tone||0) >= 0.1 ? '#26a69a' : (h.mgmt_tone||0) <= -0.1 ? '#ef5350' : '#7aa8c0';
          const gc = {raised:'#26a69a',lowered:'#ef5350',maintained:'#7aa8c0',none:'#555'}[h.guidance_direction||'none']||'#555';
          return `<tr style="border-bottom:1px solid rgba(255,255,255,0.03);">
            <td style="padding:4px 6px;color:var(--t2);">${h.fiscal_period || h.extracted_at?.slice(0,10) || '—'}</td>
            <td style="text-align:center;color:${(h.eps_beat_pct||0)>=0?'#26a69a':'#ef5350'};">
              ${h.eps_beat_pct !== null && h.eps_beat_pct !== undefined ? (h.eps_beat_pct>=0?'+':'')+h.eps_beat_pct.toFixed(1)+'%' : '—'}
            </td>
            <td style="text-align:center;color:${(h.revenue_growth_yoy||0)>=0?'#26a69a':'#ef5350'};">
              ${h.revenue_growth_yoy !== null && h.revenue_growth_yoy !== undefined ? (h.revenue_growth_yoy>=0?'+':'')+h.revenue_growth_yoy.toFixed(1)+'%' : '—'}
            </td>
            <td style="text-align:center;color:${tc};">${(h.mgmt_tone||0).toFixed(2)}</td>
            <td style="text-align:center;color:${gc};">${(h.guidance_direction||'none').toUpperCase()}</td>
          </tr>`;
        }).join('')}
      </table>
    </div>` : '';

  el.innerHTML = `
    <div style="background:rgba(41,98,255,0.06);border:1px solid rgba(0,212,255,0.25);
      border-radius:6px;padding:16px;margin-bottom:12px;">

      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
        <div style="color:var(--cyan);font-family:Share Tech Mono,monospace;font-size:0.78rem;letter-spacing:1px;">
          🤖 AI EARNINGS INTELLIGENCE
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
          <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);">${method}</span>
          <button onclick="_triggerRAGIngest('${sym}')"
            style="padding:3px 8px;background:rgba(0,212,255,0.1);border:1px solid var(--cyan);
            border-radius:3px;font-family:Share Tech Mono,monospace;font-size:0.58rem;
            color:var(--cyan);cursor:pointer;">⚙ RE-INGEST</button>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px;">
        <div style="text-align:center;">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);margin-bottom:4px;">MGMT TONE</div>
          <div style="font-size:1.1rem;font-weight:700;color:${toneCol};">${tone >= 0 ? '+' : ''}${tone.toFixed(2)}</div>
        </div>
        <div style="text-align:center;">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);margin-bottom:4px;">GUIDANCE</div>
          <div style="font-size:0.8rem;font-weight:700;color:${guidCol};">${guidIcon}</div>
        </div>
        <div style="text-align:center;">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);margin-bottom:4px;">EPS BEAT</div>
          <div style="font-size:1.1rem;font-weight:700;color:${(llm.eps_beat_pct||0)>=0?'#26a69a':'#ef5350'};">
            ${llm.eps_beat_pct !== null && llm.eps_beat_pct !== undefined ? (llm.eps_beat_pct>=0?'+':'')+llm.eps_beat_pct.toFixed(1)+'%' : 'N/A'}
          </div>
        </div>
        <div style="text-align:center;">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);margin-bottom:4px;">REV YoY</div>
          <div style="font-size:1.1rem;font-weight:700;color:${(llm.revenue_growth_yoy||0)>=0?'#26a69a':'#ef5350'};">
            ${llm.revenue_growth_yoy !== null && llm.revenue_growth_yoy !== undefined ? (llm.revenue_growth_yoy>=0?'+':'')+llm.revenue_growth_yoy.toFixed(1)+'%' : 'N/A'}
          </div>
        </div>
      </div>

      <!-- Tone gauge bar -->
      <div style="margin-bottom:12px;">
        <div style="position:relative;height:6px;background:linear-gradient(90deg,#ef5350 0%,rgba(255,255,255,0.08) 50%,#26a69a 100%);border-radius:3px;">
          <div style="position:absolute;top:-4px;left:${tonePct}%;width:2px;height:14px;background:white;border-radius:1px;transform:translateX(-50%);box-shadow:0 0 4px rgba(255,255,255,0.6);"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:3px;">
          <span style="font-family:Share Tech Mono,monospace;font-size:0.5rem;color:#ef5350;">BEARISH −1</span>
          <span style="font-family:Share Tech Mono,monospace;font-size:0.5rem;color:var(--dim);">NEUTRAL</span>
          <span style="font-family:Share Tech Mono,monospace;font-size:0.5rem;color:#26a69a;">BULLISH +1</span>
        </div>
      </div>

      ${risks.length > 0 ? `
      <div style="padding:10px;background:rgba(239,83,80,0.05);border:1px solid rgba(239,83,80,0.15);border-radius:4px;margin-bottom:12px;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:#ef5350;margin-bottom:6px;">⚠ KEY RISKS IDENTIFIED BY AI</div>
        ${risks.map(r => `<div style="display:flex;gap:6px;font-size:0.75rem;line-height:1.4;margin-bottom:2px;">
          <span style="color:#ef5350;margin-top:1px;">•</span><span style="color:var(--t2);">${r}</span>
        </div>`).join('')}
      </div>` : ''}

      ${histTable}

      <!-- Q&A search box -->
      <div style="margin-top:12px;padding-top:12px;border-top:1px solid rgba(255,255,255,0.06);">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--cyan);margin-bottom:6px;">
          💬 ASK AI ABOUT ${sym} EARNINGS
        </div>
        <div style="display:flex;gap:6px;">
          <input id="rag-qa-input" type="text"
            placeholder='e.g. "What did management say about margin pressure?"'
            style="flex:1;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:3px;
            padding:7px 10px;font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--text);outline:none;"
            onkeydown="if(event.key==='Enter') _ragQA('${sym}')"/>
          <button onclick="_ragQA('${sym}')"
            style="padding:7px 12px;background:var(--cyan);color:var(--bg);border:none;border-radius:3px;
            font-family:Share Tech Mono,monospace;font-size:0.7rem;font-weight:bold;cursor:pointer;">ASK</button>
        </div>
        <div id="rag-qa-answer" style="margin-top:8px;font-size:0.78rem;line-height:1.5;color:var(--t2);display:none;"></div>
      </div>

    </div>`;
}

async function _ragQA(sym) {
  // Use current sym from input's data attribute if not passed (handles dynamic cards)
  const inp = document.getElementById('rag-qa-input');
  const ans = document.getElementById('rag-qa-answer');
  if (!inp || !ans) return;
  const q = (inp.value || '').trim();
  if (!q) return;
  ans.style.display = 'block';
  ans.innerHTML = '<span style="color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.65rem;">🤖 Thinking…</span>';
  try {
    const d = await api('rag_qa', { symbol: sym, query: q });
    if (!d || d.error) {
      ans.innerHTML = '<span style="color:#ef5350;">Error: ' + ((d && d.error) || 'No response') + '</span>';
      return;
    }
    const methodLabel = {ollama:'🟢 Ollama', llama_cpp:'🟡 llama-cpp', rules:'🔵 Rule-based', none:'—'}[d.method||'rules'] || d.method;
    const srcs = (d.sources||[]).filter(s => s.doc_type).map(s => s.doc_type + (s.fiscal_period ? ' '+s.fiscal_period : '')).join(', ');
    ans.innerHTML = `
      <div style="background:rgba(0,212,255,0.04);border-left:2px solid var(--cyan);
        padding:10px 12px;border-radius:0 4px 4px 0;margin-top:4px;">
        <div style="font-size:0.8rem;line-height:1.6;color:var(--text);margin-bottom:6px;">
          ${d.answer || 'No answer generated.'}
        </div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);">
          ${methodLabel} · ${d.chunks_used||0} chunks · ${srcs ? 'Sources: '+srcs : 'No indexed docs — click RE-INGEST first'}
        </div>
      </div>`;
  } catch(e) {
    ans.innerHTML = '<span style="color:#ef5350;">Network error: ' + (e.message||String(e)) + '</span>';
  }
}
window._ragQA = _ragQA;   // expose globally so onclick="..." can reach it

async function _triggerRAGIngest(sym) {
  const btn = event && event.target;
  if (btn) { btn.disabled = true; btn.textContent = '⏳ INGESTING…'; }
  try {
    const d = await api('rag_ingest', { symbol: sym });
    const msg = d.ok !== false
      ? '✅ Ingest complete: ' + (d.new_chunks||0) + ' new chunks added (' + (d.skipped_docs||0) + ' docs skipped as duplicates).'
      : '⚠ Ingest error: ' + (d.error || d.reason || 'unknown');
    alert(msg);
    if (d.ok !== false) _loadAIEarnings(sym);
  } catch(e) {
    alert('⚠ Network error: ' + (e.message || String(e)));
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '⚙ RE-INGEST'; }
  }
}
window._triggerRAGIngest = _triggerRAGIngest;   // expose globally

window._loadAIEarnings = _loadAIEarnings;       // expose globally

})();
"""