"""
page_dashboard.py — Planet Dashboard — live planetary positions

Exports:
    HTML  : Page HTML template (injected into SPA)
    JS    : Page JavaScript (injected into <script> block)

Backend endpoints for this page live in app.py (ep == "..." handlers).
To modify: edit HTML/JS here, backend logic in app.py.
"""


HTML = r"""
<!-- ═══════════ PAGE: DASHBOARD ═══════════ -->
<div class="page" id="page-dashboard">
  <div class="topbar">
    <h2>PLANETARY DASHBOARD</h2>
    <div style="display:flex;gap:8px;align-items:center;">
      <input type="date" id="dash-date" style="display:none;">
      <span id="dash-date-label" style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--cyan);">{today_str}</span>
      <span class="page-tag" id="dash-live-tag">LIVE</span>
    </div>
  </div>
  <div id="dash-loading" class="loading"><div class="spinner"></div>COMPUTING PLANETARY POSITIONS...</div>
  <div id="dash-content" style="display:none;">
    <div class="g4" id="dash-stats" style="margin-bottom:14px;"></div>
    <div class="g2">
      <div>
        <div class="card">
          <div class="card-title">🪐 PLANET POSITIONS</div>
          <div class="trow hdr" style="grid-template-columns:90px 70px 100px 60px 75px 70px;">
            <div>PLANET</div><div>LON°</div><div>SIGN</div><div>DEG</div><div>SPEED</div><div>STATUS</div>
          </div>
          <div id="planet-table"></div>
        </div>
        <div class="card">
          <div class="card-title">🔴 RETROGRADES & STATIONS</div>
          <div id="retro-list"></div>
        </div>
      </div>
      <div>
        <div class="card">
          <div class="card-title">🔗 ACTIVE ASPECTS</div>
          <div id="aspect-list"></div>
        </div>
        <div class="card">
          <div class="card-title">⚡ STATION ALERTS</div>
          <div id="station-list"></div>
        </div>
      </div>
    </div>
  </div>
</div>

"""


JS = r"""
async function loadDashboard() {
  const dt = GANN_DATE;
  setDate('dash-date', dt);
  const lbl=document.getElementById('dash-date-label'); if(lbl) lbl.textContent=dt;
  const tag=document.getElementById('dash-live-tag'); if(tag){tag.textContent=dt===today?'LIVE':'BACKTEST';tag.style.color=dt===today?'':'var(--orange)';}
  loading('dash-loading', true);
  show('dash-content', false);
  try {
    const d = await api('dashboard', {date: dt});
    if (d && d.error) throw new Error(d.error);
    renderDashboard(d);
  } catch(e) {
    var _ld = document.getElementById('dash-loading');
    if (_ld) _ld.innerHTML = '<div class="err" onclick="loadDashboard()" style="cursor:pointer">&#9888; ' + e.message + ' - Click to retry</div>';
  }
}

function renderDashboard(d) {
  loading('dash-loading', false);
  show('dash-content');

  // Stats row
  const retros = d.retrograde_planets || [];
  const stations = (d.stations||[]);
  document.getElementById('dash-stats').innerHTML=backtestBanner()+`
    <div class="stat"><span class="val">${d.aspects?.length||0}</span><span class="lbl">ACTIVE ASPECTS</span></div>
    <div class="stat"><span class="val" style="color:var(--red)">${retros.length}</span><span class="lbl">RETROGRADE</span></div>
    <div class="stat"><span class="val" style="color:var(--gold)">${stations.length}</span><span class="lbl">STATIONS</span></div>
    <div class="stat"><span class="val" style="color:var(--green)">${(d.aspects||[]).filter(a=>(a.direction||a.bullish_bearish)==='BULLISH').length}</span><span class="lbl">BULL ASPECTS</span></div>`;

  // Planet table
  let pt = '';
  for (const [name, p] of Object.entries(d.planets||{})) {
    const col = pcolor(name);
    const retro = p.retrograde ? '<span style="color:var(--red);font-size:0.68rem;">RETRO</span>' : '<span style="color:var(--green);font-size:0.68rem;">DIR</span>';
    pt += `<div class="trow" style="grid-template-columns:90px 70px 100px 60px 75px 70px;">
      <div style="font-family:Share Tech Mono,monospace;color:${col};font-weight:600;">${name}</div>
      <div style="font-family:Share Tech Mono,monospace;color:var(--cyan);">${p.longitude.toFixed(2)}°</div>
      <div>${p.sign}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.75rem;">${p.sign_degree.toFixed(1)}°</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:${p.speed<0?'var(--red)':'var(--dim)'};">${p.speed.toFixed(3)}</div>
      <div>${retro}</div>
    </div>`;
  }
  document.getElementById('planet-table').innerHTML = pt;

  // Retrograde list
  let rl = '';
  if (retros.length === 0) {
    rl = '<div style="padding:10px;color:var(--dim);font-size:0.82rem;">No retrograde planets today</div>';
  } else {
    retros.forEach(p => {
      rl += `<div style="padding:8px 10px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px;">
        <span style="color:${pcolor(p)};font-family:Share Tech Mono,monospace;font-size:0.8rem;font-weight:600;">${p}</span>
        <span class="badge br">RETROGRADE</span>
        <span style="font-size:0.8rem;color:var(--text);">Market confusion / delays in ${p} sectors</span>
      </div>`;
    });
  }
  document.getElementById('retro-list').innerHTML = rl;

  // Aspects
  let al = '';
  (d.aspects||[]).slice(0,12).forEach(a => {
    const nc = natureClass(a.direction||a.bullish_bearish||'NEUTRAL');
    al += `<div style="display:flex;align-items:center;gap:10px;padding:7px 10px;border-bottom:1px solid var(--border);font-size:0.82rem;">
      <div style="min-width:180px;font-weight:600;font-family:Share Tech Mono,monospace;font-size:0.78rem;color:var(--cyan);">${a.planets||''}</div>
      <div style="min-width:70px;font-family:Share Tech Mono,monospace;font-size:0.72rem;">${a.symbol||''}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--dim);">orb ${(a.orb||0).toFixed(2)}°</div>
      <div class="${nc}" style="font-family:Share Tech Mono,monospace;font-size:0.68rem;">${a.bullish_bearish||a.direction}</div>
    </div>`;
  });
  document.getElementById('aspect-list').innerHTML = al || '<div style="padding:10px;color:var(--dim);">No active aspects</div>';

  // Stations
  let sl = '';
  if (stations.length === 0) {
    sl = '<div style="padding:10px;color:var(--dim);font-size:0.82rem;">No stations within 5 days</div>';
  } else {
    stations.forEach(s => {
      sl += `<div style="padding:8px 10px;border-bottom:1px solid var(--border);">
        <span class="badge bgo" style="margin-right:8px;">${s.planet||s}</span>
        <span style="font-size:0.82rem;color:var(--gold);">Station point detected — HIGH VOLATILITY zone</span>
      </div>`;
    });
  }
  document.getElementById('station-list').innerHTML = sl;
}

// ════════════════════════════════════════════════════════════════════
// SCANNER
// ════════════════════════════════════════════════════════════════════
"""
