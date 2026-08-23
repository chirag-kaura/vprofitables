"""
page_gann.py — Gann Analysis — Square of Nine, angles, time cycles

Exports:
    HTML  : Page HTML template (injected into SPA)
    JS    : Page JavaScript (injected into <script> block)

Backend endpoints for this page live in app.py (ep == "..." handlers).
To modify: edit HTML/JS here, backend logic in app.py.
"""


HTML = r"""
<!-- ═══════════ PAGE: GANN ANALYZE ═══════════ -->
<div class="page" id="page-analyze">
  <div class="topbar"><h2>GANN + ASTRO ANALYSIS</h2><span class="page-tag">FULL CONFLUENCE</span></div>
  <div class="card">
    <div class="card-title">⚙ PARAMETERS</div>
    <div class="chip-grid" id="analyze-chips"></div>

    <!-- Row 1: Symbol + Price -->
    <div class="form-row">
      <label>SYMBOL</label>
      <select id="az-sym" onchange="onAzSymChange()" style="background:var(--p2);border:1px solid var(--b2);color:var(--t2);padding:6px 10px;font-family:Share Tech Mono,monospace;font-size:0.8rem;outline:none;min-width:160px;"></select>
      <label>CURRENT PRICE</label>
      <div style="display:flex;align-items:center;gap:6px;">
        <input type="number" id="az-price" value="" step="0.01" style="min-width:120px;">
        <span id="az-price-badge" style="font-family:Share Tech Mono,monospace;font-size:0.58rem;padding:2px 7px;border-radius:1px;display:none;"></span>
      </div>
    </div>

    <!-- Row 2: Pivot selector + price + date + analyse all in one row -->
    <div class="form-row" style="align-items:center;gap:10px;flex-wrap:wrap;">
      <label>PIVOT VIEW</label>
      <select id="az-pivot-select" onchange="onPivotSelectChange()"
        style="background:var(--p2);border:1px solid var(--b2);color:var(--t2);
               padding:6px 10px;font-family:Share Tech Mono,monospace;
               font-size:0.8rem;outline:none;min-width:260px;flex:1;">
        <option value="">— select pivot view —</option>
      </select>

      <label>PIVOT PRICE</label>
      <input type="number" id="az-pivot" value="" placeholder="auto"
             oninput="onManualPivotEdit()"
             style="min-width:110px;width:110px;">

      <label>PIVOT DATE</label>
      <input type="date" id="az-pdate"
             oninput="onManualPivotEdit()"
             style="min-width:140px;">

      <button class="btn-gold btn" onclick="loadAnalyze()">ANALYSE</button>
      <span id="az-pivot-desc" style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);margin-left:6px;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"></span>
    </div>

    <!-- Row 3: Save custom pivot -->
    <div id="az-save-pivot-row" style="display:none;margin-top:10px;
         padding:10px 14px;background:rgba(255,204,0,0.04);
         border:1px solid rgba(255,204,0,0.15);
         font-family:Share Tech Mono,monospace;font-size:0.72rem;
         display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
      <span style="color:var(--gold);">⚡ CUSTOM PIVOT</span>
      <input type="text" id="az-custom-label" placeholder="Label (e.g. COVID LOW)"
             style="background:var(--p2);border:1px solid var(--b2);color:var(--t2);
                    padding:4px 8px;font-family:Share Tech Mono,monospace;
                    font-size:0.72rem;width:160px;outline:none;">
      <button class="btn" onclick="saveCustomPivot()"
              style="font-size:0.65rem;padding:4px 12px;">SAVE PIVOT</button>
      <span id="az-save-confirm" style="color:var(--green);display:none;">✓ SAVED</span>
    </div>
  </div>
  <div id="az-loading" class="loading" style="display:none;"><div class="spinner"></div>COMPUTING...</div>
  <div id="az-content" style="display:none;"></div>
</div>

"""


JS = r"""
async function loadAnalyze() {
  const sym   = document.getElementById('az-sym').value;
  const price = parseFloat(document.getElementById('az-price').value)||0;
  const pivot = parseFloat(document.getElementById('az-pivot').value)||0;
  const pdate = document.getElementById('az-pdate').value || today;
  if (!sym) return;
  loading('az-loading', true);
  show('az-content', false);
  try {
    const [d, track] = await Promise.all([
      api('analyze', {symbol:sym, price, pivot_price:pivot, pivot_date:pdate}),
      api('gann_track_record', {symbol:sym})
    ]);
    renderAnalyze(d, track);
  } catch(e) {
    document.getElementById('az-loading').innerHTML = `<div class="err">${e.message}</div>`;
  }
}

function renderAnalyze(d, d_track) {
  loading('az-loading', false);
  const c = d.confluence||{};
  const sc = c.score||0;
  const scColor = sc>=12?'var(--red)':sc>=8?'var(--gold)':sc>=5?'var(--green)':'var(--dim)';
  const gm = d.gann_math||{};
  const pl = d.planetary||{};
  const nc = d.natal_chart||{};
  const track = d_track && d_track.track_record ? d_track.track_record : {};

  let sq9html = '';
  (gm.sq9_levels||[]).forEach(l => {
    sq9html += `<div class="trow" style="grid-template-columns:60px 1fr 50px 1fr 50px;">
      <div style="font-family:Share Tech Mono,monospace;font-size:0.72rem;">${l.rotation}×90°</div>
      <div style="font-family:Share Tech Mono,monospace;color:var(--red);font-weight:600;">${(l.above||0).toLocaleString()}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);">${l.above_pct}%↑</div>
      <div style="font-family:Share Tech Mono,monospace;color:var(--green);font-weight:600;">${(l.below||0).toLocaleString()}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);">${l.below_pct}%↓</div>
    </div>`;
  });

  let cyclHtml = '';
  (gm.time_cycles_due||[]).concat(gm.time_cycles_approaching||[]).slice(0,8).forEach(cy => {
    const due = Math.abs(cy.days_remaining)<=7;
    cyclHtml += `<div class="trow" style="grid-template-columns:1fr 90px 60px 70px;">
      <div style="font-size:0.8rem;">${cy.label}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--dim);">${cy.target_date}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:${due?'var(--gold)':'var(--text)'};">${cy.days_remaining}d</div>
      <div style="font-size:0.72rem;color:${pcolor((cy.planet||'').split(' ')[0])};">${cy.planet||''}</div>
    </div>`;
  });

  let t2nHtml = '';
  (nc.transit_to_natal||[]).slice(0,8).forEach(a => {
    const nc2 = a.nature==='BULLISH'?'var(--green)':a.nature==='BEARISH'?'var(--red)':'var(--text)';
    const ruler = a.is_ruler_activated ? '<span class="badge bgo" style="font-size:0.55rem;">RULER</span>' : '';
    t2nHtml += `<div class="trow" style="grid-template-columns:100px 90px 100px 55px 70px 60px;${a.is_ruler_activated?'background:rgba(255,204,0,0.03);':''}">
      <div style="font-family:Share Tech Mono,monospace;font-size:0.75rem;color:${pcolor(a.transit_planet)};">T.${a.transit_planet}${a.transit_retrograde?' ℞':''}</div>
      <div style="font-size:0.78rem;">${a.aspect}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.75rem;color:${pcolor(a.natal_planet)};">N.${a.natal_planet}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;">${(a.orb||0).toFixed(2)}°</div>
      <div style="font-size:0.68rem;color:${nc2};">${a.nature}</div>
      <div>${ruler}</div>
    </div>`;
  });

  let upcomingHtml = '';
  (d.upcoming_signals||[]).slice(0,8).forEach(s => {
    const sc2 = s.score>=8?'var(--red)':s.score>=6?'var(--gold)':'var(--green)';
    upcomingHtml += `<div style="display:flex;gap:12px;padding:8px 10px;border-bottom:1px solid var(--border);">
      <div style="min-width:70px;font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--gold);">${s.date}</div>
      <div style="min-width:24px;font-family:Share Tech Mono,monospace;font-size:0.75rem;font-weight:600;color:${sc2};">${s.score}</div>
      <div style="flex:1;font-size:0.8rem;color:var(--t2);">${(s.signals||[]).slice(0,2).join(' · ')}</div>
    </div>`;
  });

  // Track record summary table
  let trackHtml = '';
  const trackKeys = Object.keys(track);
  if (trackKeys.length > 0) {
    trackHtml = `
      <div class="card" style="margin-top:14px;">
        <div class="card-title">📈 GANN SIGNAL PERFORMANCE HISTORY</div>
        <div class="trow hdr" style="grid-template-columns: 1.5fr 1fr 1fr;">
          <div>SUBTYPE</div><div>HIT RATE</div><div>AVG RETURN</div>
        </div>
    `;
    trackKeys.forEach(k => {
      const rec = track[k];
      const name = k.replace(/_/g, ' ').toUpperCase();
      trackHtml += `
        <div class="trow" style="grid-template-columns: 1.5fr 1fr 1fr; font-family:Share Tech Mono,monospace; font-size:0.75rem;">
          <div>${name} (n=${rec.sample_size})</div>
          <div style="color:var(--green);font-weight:600;">${rec.hit_rate_pct}%</div>
          <div style="color:${rec.avg_return_pct>=0?'var(--green)':'var(--red)'};">${rec.avg_return_pct>=0?'+':''}${rec.avg_return_pct}%</div>
        </div>
      `;
    });
    trackHtml += `</div>`;
  }

  // Map signals list with inline WR hit rates
  const signalsHtml = (c.signals||[]).map(s => {
    let statText = "";
    if (s.includes("Sq9") && track.sq9_proximity) {
      statText = ` <span style="color:var(--gold);font-size:0.7rem;font-weight:normal;">(${track.sq9_proximity.hit_rate_pct}% WR, n=${track.sq9_proximity.sample_size})</span>`;
    } else if (s.includes("Time cycle") && track.time_cycle_due) {
      statText = ` <span style="color:var(--gold);font-size:0.7rem;font-weight:normal;">(${track.time_cycle_due.hit_rate_pct}% WR, n=${track.time_cycle_due.sample_size})</span>`;
    } else if (s.includes("Gann") && track.angle_test) {
      statText = ` <span style="color:var(--gold);font-size:0.7rem;font-weight:normal;">(${track.angle_test.hit_rate_pct}% WR, n=${track.angle_test.sample_size})</span>`;
    } else if (s.includes("Planetary aspect") && track.planetary) {
      statText = ` <span style="color:var(--gold);font-size:0.7rem;font-weight:normal;">(${track.planetary.hit_rate_pct}% WR, n=${track.planetary.sample_size})</span>`;
    }
    return `<div style="padding:5px 8px;border-bottom:1px solid var(--border);font-size:0.8rem;color:var(--t2);">▸ ${s}${statText}</div>`;
  }).join('');

  document.getElementById('az-content').innerHTML = `
    <div class="g2" style="margin-bottom:14px;">
      <div class="score-big">
        <span class="score-num" style="color:${scColor}">${sc}</span>
        <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;letter-spacing:3px;color:var(--dim);">/ 42 POINTS</span>
        <span class="score-lbl" style="color:${scColor}">${c.verdict||'--'}</span>
      </div>
      <div class="card" style="margin:0;">
        <div class="card-title">CONFLUENCE SIGNALS</div>
        ${signalsHtml}
        ${trackHtml}
      </div>
    </div>
    <div class="g2">
      <div class="card">
        <div class="card-title">⬛ SQ9 LEVELS</div>
        <div class="trow hdr" style="grid-template-columns:60px 1fr 50px 1fr 50px;"><div>ROT</div><div>RESIST</div><div>%</div><div>SUPPORT</div><div>%</div></div>
        ${sq9html}
      </div>
      <div class="card">
        <div class="card-title">⏰ ACTIVE TIME CYCLES</div>
        <div class="trow hdr" style="grid-template-columns:1fr 90px 60px 70px;"><div>CYCLE</div><div>DATE</div><div>DAYS</div><div>PLANET</div></div>
        ${cyclHtml}
      </div>
    </div>
    <div class="g2">
      <div class="card">
        <div class="card-title">🌌 TRANSIT × NATAL ASPECTS</div>
        <div class="trow hdr" style="grid-template-columns:100px 90px 100px 55px 70px 60px;"><div>TRANSIT</div><div>ASPECT</div><div>NATAL</div><div>ORB</div><div>NATURE</div><div></div></div>
        ${t2nHtml}
      </div>
      <div class="card">
        <div class="card-title">🔮 UPCOMING HIGH-CONFLUENCE DATES</div>
        ${upcomingHtml}
      </div>
    </div>`;
  show('az-content');
}

// ════════════════════════════════════════════════════════════════════
// NATAL
// ════════════════════════════════════════════════════════════════════
"""
