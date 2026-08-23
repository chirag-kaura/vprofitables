"""
page_natal.py — Natal Charts — transit × natal aspects

Exports:
    HTML  : Page HTML template (injected into SPA)
    JS    : Page JavaScript (injected into <script> block)

Backend endpoints for this page live in app.py (ep == "..." handlers).
To modify: edit HTML/JS here, backend logic in app.py.
"""


HTML = r"""
<!-- ═══════════ PAGE: NATAL ═══════════ -->
<div class="page" id="page-natal">
  <div class="topbar"><h2>NATAL CHARTS</h2><span class="page-tag">TRANSIT × NATAL</span></div>
  <div class="card">
    <div class="card-title">⚙ SELECT INSTRUMENT</div>
    <div class="chip-grid" id="natal-chips"></div>
    <div class="form-row">
      <label>SYMBOL</label>
      <select id="natal-sym" style="background:var(--p2);border:1px solid var(--b2);color:var(--t2);padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.8rem;outline:none;min-width:160px;"></select>
      <label>TRANSIT DATE</label>
      <input type="date" id="natal-date" style="min-width:140px;">
      <button class="btn" onclick="loadNatal()">LOAD</button>
    </div>
  </div>
  <div id="natal-loading" class="loading" style="display:none;"><div class="spinner"></div>COMPUTING...</div>
  <div id="natal-content" style="display:none;"></div>
</div>

"""


JS = r"""
async function loadNatal() {
  const sym = document.getElementById('natal-sym').value;
  const dt  = GANN_DATE;
  setDate('natal-date', dt);
  if (!sym) return;
  loading('natal-loading', true);
  show('natal-content', false);
  try {
    const d = await api('natal', {symbol:sym, date:dt});
    renderNatal(d);
  } catch(e) {
    document.getElementById('natal-loading').innerHTML = `<div class="err">${e.message}</div>`;
  }
}

function renderNatal(d) {
  loading('natal-loading', false);
  let planetRows = '';
  const rulers=[d.primary_ruler,d.secondary_ruler,d.tertiary_ruler];
  Object.entries(d.natal_planets||{}).forEach(([name,p]) => {
    const isR=rulers.includes(name);
    const ret=p.retrograde?'<span style="color:var(--red);font-size:0.68rem;">RETRO</span>':'<span style="color:var(--green);font-size:0.68rem;">DIR</span>';
    planetRows += `<div class="trow" style="grid-template-columns:90px 70px 100px 60px 60px 70px;${isR?'background:rgba(255,204,0,0.03);':''}">
      <div style="font-family:Share Tech Mono,monospace;color:${pcolor(name)};font-weight:600;">${name}</div>
      <div style="font-family:Share Tech Mono,monospace;color:var(--cyan);">${p.longitude.toFixed(2)}°</div>
      <div>${p.sign}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.75rem;">${p.sign_degree.toFixed(1)}°</div>
      <div>${ret}</div>
      <div>${isR?'<span class="badge bgo">RULER</span>':''}</div>
    </div>`;
  });
  let t2nRows = '';
  (d.transit_to_natal||[]).slice(0,12).forEach(a => {
    const nc=a.nature==='BULLISH'?'var(--green)':a.nature==='BEARISH'?'var(--red)':'var(--text)';
    t2nRows += `<div class="trow" style="grid-template-columns:110px 90px 110px 55px 70px 60px;${a.is_ruler_activated?'background:rgba(255,204,0,0.03);':''}">
      <div style="font-family:Share Tech Mono,monospace;font-size:0.75rem;color:${pcolor(a.transit_planet)};">T.${a.transit_planet}${a.transit_retrograde?' ℞':''}</div>
      <div style="font-size:0.78rem;">${a.aspect}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.75rem;color:${pcolor(a.natal_planet)};">N.${a.natal_planet}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;">${(a.orb||0).toFixed(2)}°</div>
      <div style="font-size:0.68rem;color:${nc};">${a.nature}</div>
      <div>${a.is_ruler_activated?'<span class="badge bgo" style="font-size:0.55rem;">RULER</span>':''}</div>
    </div>`;
  });
  const bullCount=(d.bull_signals||[]).length, bearCount=(d.bear_signals||[]).length;
  const biasColor=bullCount>bearCount?'var(--green)':bearCount>bullCount?'var(--red)':'var(--text)';
  document.getElementById('natal-content').innerHTML = `
    <div class="g2" style="margin-bottom:14px;">
      <div class="card">
        <div class="card-title">🔭 ${d.symbol} — NATAL CHART</div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;">
          <span class="badge bgo">PRIMARY: ${d.primary_ruler}</span>
          <span class="badge bc">SECONDARY: ${d.secondary_ruler}</span>
          <span class="badge bd">TERTIARY: ${d.tertiary_ruler}</span>
        </div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);margin-bottom:6px;">INCEPTION: ${d.inception_date} | ${d.inception_time} IST | ${d.location}</div>
        <div class="trow hdr" style="grid-template-columns:90px 70px 100px 60px 60px 70px;"><div>PLANET</div><div>LON°</div><div>SIGN</div><div>DEG</div><div>STATUS</div><div>RULER?</div></div>
        ${planetRows}
      </div>
      <div class="card">
        <div class="card-title">⚡ RULER ACTIVATIONS TODAY</div>
        <div class="g2" style="margin-bottom:10px;">
          <div class="stat"><span class="val" style="color:var(--green)">${bullCount}</span><span class="lbl">BULL SIGNALS</span></div>
          <div class="stat"><span class="val" style="color:var(--red)">${bearCount}</span><span class="lbl">BEAR SIGNALS</span></div>
        </div>
        <div style="text-align:center;padding:10px;font-family:Orbitron,sans-serif;font-size:0.95rem;color:${biasColor};">${bullCount>bearCount?'BULLISH BIAS':bearCount>bullCount?'BEARISH BIAS':'MIXED SIGNALS'}</div>
        ${(d.ruler_activations||[]).slice(0,5).map(a=>`
          <div style="display:flex;align-items:flex-start;gap:8px;padding:7px 8px;border-bottom:1px solid var(--border);">
            <span style="font-size:0.9rem;color:${pcolor(a.transit_planet)};">★</span>
            <span style="font-size:0.8rem;line-height:1.4;">
              <strong style="color:${pcolor(a.transit_planet)};">Transit ${a.transit_planet}${a.transit_retrograde?' ℞':''}</strong>
              <span style="color:${a.nature==='BULLISH'?'var(--green)':'var(--red)'}"> ${a.aspect} </span>
              <strong>Natal ${a.natal_planet}</strong>
              (orb ${(a.orb||0).toFixed(2)}°)
            </span>
          </div>`).join('')}
      </div>
    </div>
    <div class="card" style="background: linear-gradient(135deg, rgba(20,20,30,0.8), rgba(10,10,20,0.9)); border: 1px solid var(--cyan); margin-bottom: 14px;">
      <div class="card-title" style="color:var(--cyan); border-bottom: 1px solid rgba(0,255,255,0.2);">✨ ASTROLOGICAL CONTEXT: NAKSHATRA</div>
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap: 10px; margin-top: 5px;">
         <div>
             <div style="font-size: 1.4rem; font-weight: bold; color: var(--gold);">${d.transit_moon_nakshatra}</div>
             <div style="font-family:Share Tech Mono, monospace; font-size: 0.85rem; color: var(--dim);">RULING PLANET: <span style="color:var(--text);">${d.transit_moon_nakshatra_lord}</span></div>
         </div>
         <div style="text-align: right; max-width: 60%;">
             <div style="font-size: 0.8rem; color: var(--dim); margin-bottom:4px;">FAVORED SECTORS TODAY</div>
             <div style="display:flex; gap:6px; flex-wrap:wrap; justify-content:flex-end;">
                ${(d.transit_moon_nakshatra_sectors||[]).map(s => `<span class="badge bgo" style="background:rgba(0,255,255,0.1);color:var(--cyan);border:1px solid rgba(0,255,255,0.3);">${s}</span>`).join('')}
             </div>
         </div>
      </div>
      <div style="margin-top: 15px; font-size: 0.85rem; color: var(--dim); line-height: 1.6; border-top: 1px dashed rgba(255,255,255,0.1); padding-top: 10px;">
          The active lunar Nakshatra deeply influences broader market behavior and sectoral momentum. The AI Predictive Engine dynamically applies an alignment bonus if this instrument's sector (<span style="color:var(--text);">${d.sector}</span>) matches the Nakshatra's favored sectors, resulting in higher confidence for predictive signals.
      </div>
    </div>
    <div class="card">
      <div class="card-title">🔗 ALL TRANSIT × NATAL ASPECTS — ${d.transit_date}</div>
      <div class="trow hdr" style="grid-template-columns:110px 90px 110px 55px 70px 60px;"><div>TRANSIT</div><div>ASPECT</div><div>NATAL</div><div>ORB</div><div>NATURE</div><div>RULER?</div></div>
      ${t2nRows}
    </div>`;
  show('natal-content');
}

// ════════════════════════════════════════════════════════════════════
// SQ9
// ════════════════════════════════════════════════════════════════════
async function loadSq9() {
  const price = parseFloat(document.getElementById('sq9-price').value)||24500;
  const atl   = parseFloat(document.getElementById('sq9-atl').value)||900;
  try {
    const d = await api('sq9', {price, atl});
    let html = `<div class="card"><div class="card-title">⬛ SQ9 LEVELS FROM PRICE ${price.toLocaleString()}</div>
      <div class="trow hdr" style="grid-template-columns:60px 1fr 55px 1fr 55px;"><div>ROT</div><div>RESISTANCE</div><div>% ABOVE</div><div>SUPPORT</div><div>% BELOW</div></div>`;
    (d.levels||[]).forEach(l => {
      html += `<div class="trow" style="grid-template-columns:60px 1fr 55px 1fr 55px;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;">${l.rotation}×90°</div>
        <div style="font-family:Share Tech Mono,monospace;color:var(--red);font-weight:600;">${(l.above||0).toLocaleString()}</div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);">+${l.above_pct}%</div>
        <div style="font-family:Share Tech Mono,monospace;color:var(--green);font-weight:600;">${(l.below||0).toLocaleString()}</div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);">-${l.below_pct}%</div>
      </div>`;
    });
    html += '</div>';
    if (d.atl_data) {
      html += `<div class="card"><div class="card-title">📌 POSITION FROM ATL (${atl})</div>
        <div style="display:flex;gap:20px;flex-wrap:wrap;padding:4px;">
          ${Object.entries(d.atl_data).map(([k,v])=>`<div><span style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);letter-spacing:1px;">${k.toUpperCase()}: </span><span style="font-family:Share Tech Mono,monospace;color:var(--cyan);">${v}</span></div>`).join('')}
        </div></div>`;
    }
    document.getElementById('sq9-content').innerHTML = html;
  } catch(e) { document.getElementById('sq9-content').innerHTML = `<div class="err">${e.message}</div>`; }
}

// ════════════════════════════════════════════════════════════════════
// CYCLES
// ════════════════════════════════════════════════════════════════════
async function loadCycles() {
  const pivot = document.getElementById('cyc-pivot').value || today;
  try {
    const d = await api('cycles', {pivot});
    let html = `<div class="card"><div class="card-title">⏰ TIME CYCLES FROM ${pivot}</div>
      <div class="trow hdr" style="grid-template-columns:1fr 100px 65px 80px;"><div>CYCLE</div><div>TARGET DATE</div><div>DAYS</div><div>PLANET</div></div>`;
    (d.cycles||[]).forEach(c => {
      const due = Math.abs(c.days_remaining)<=7;
      const app = Math.abs(c.days_remaining)<=21;
      const col = due?'var(--gold)':app?'var(--cyan)':'var(--dim)';
      html += `<div class="trow" style="grid-template-columns:1fr 100px 65px 80px;${due?'background:rgba(255,204,0,0.04);':''}">
        <div style="font-size:0.82rem;${due?'color:var(--gold);font-weight:600;':''}">${c.label}</div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:${col};">${c.target_date}</div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:${col};">${c.days_remaining}d</div>
        <div style="font-size:0.72rem;color:${pcolor((c.planet||'').split(' ')[0])};">${c.planet||''}</div>
      </div>`;
    });
    html += '</div>';
    document.getElementById('cycles-content').innerHTML = html;
  } catch(e) { document.getElementById('cycles-content').innerHTML = `<div class="err">${e.message}</div>`; }
}

// ════════════════════════════════════════════════════════════════════
// CONFLUENCE
// ════════════════════════════════════════════════════════════════════
"""
