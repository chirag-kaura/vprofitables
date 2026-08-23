# -*- coding: utf-8 -*-
"""
page_fundamentals.py — Fundamental Analysis — PE, ROE, DCF, Graham score

Exports:
    HTML  : Page HTML template (injected into SPA)
    JS    : Page JavaScript (injected into <script> block)

Backend endpoints for this page live in app.py (ep == "..." handlers).
To modify: edit HTML/JS here, backend logic in app.py.
"""


HTML = r"""
<!-- ═══════════ PAGE: FUNDAMENTALS ═══════════ -->
<div class="page" id="page-fundamentals">
  <!-- Top bar with symbol selector inline -->
  <div class="topbar" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
    <div style="display:flex;align-items:center;gap:6px;">
      <h2 style="margin:0;">📊 FUNDAMENTAL ANALYSIS</h2>
      <span class="page-tag">VALUATION + SCORING</span>
    </div>
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
      <select id="fund-sym" style="min-width:220px;background:var(--p2);border:1px solid var(--b2);color:var(--t2);padding:5px 8px;font-family:Share Tech Mono,monospace;font-size:0.75rem;outline:none;">
        <option value="">— Select equity —</option>
      </select>
      <button class="btn" onclick="loadFundamentals()" style="padding:5px 14px;">⚡ ANALYSE</button>
      <button class="btn" onclick="loadFundamentals(true)" style="padding:5px 14px;background:linear-gradient(135deg,rgba(255,204,0,0.12),rgba(255,204,0,0.04));color:var(--gold);border-color:rgba(255,204,0,0.35);">🔄 REFRESH</button>
      <span id="fund-cache-note" style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);"></span>
    </div>
  </div>

  <div style="width:100%;">
  <div id="fund-loading" style="display:none;" class="loading"><div class="spinner"></div>FETCHING FUNDAMENTALS FROM YFINANCE...</div>
  <div id="fund-error" style="display:none;" class="err"></div>

  <div id="fund-results" style="display:none;width:100%;">

    <!-- ── Row 1: Name + Score headline ── -->
    <div class="card" style="margin-bottom:12px;padding:14px 18px;">
      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">
        <div>
          <div id="fund-name" style="font-family:Orbitron,sans-serif;font-size:1.3rem;color:var(--white);font-weight:900;"></div>
          <div id="fund-sector" style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);letter-spacing:2px;margin-top:4px;"></div>
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;">
          <div class="stat" style="min-width:70px;text-align:center;">
            <span class="val" id="fund-grade" style="font-size:2.4rem;"></span>
            <span class="lbl">GRADE</span>
          </div>
          <div class="stat" style="min-width:80px;text-align:center;">
            <span class="val" id="fund-total" style="color:var(--cyan);font-size:1.6rem;"></span>
            <span class="lbl">SCORE /100</span>
          </div>
          <div class="stat" style="min-width:70px;text-align:center;">
            <span class="val" id="fund-rank" style="color:var(--gold);font-size:1.4rem;"></span>
            <span class="lbl">PEER RANK</span>
          </div>
          <div class="stat" style="min-width:80px;text-align:center;">
            <span class="val" id="fund-verdict" style="font-size:0.85rem;letter-spacing:1px;"></span>
            <span class="lbl">VERDICT</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Row 2: Score breakdown + Key ratios (2 col) ── -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;width:100%;">
      <div class="card">
        <div class="card-title">📊 SCORE BREAKDOWN (0–100 each)</div>
        <div id="fund-score-bars"></div>
      </div>
      <div class="card">
        <div class="card-title">📋 KEY RATIOS</div>
        <div id="fund-key-ratios"></div>
      </div>
    </div>

    <!-- ── Row 3: Full fundamentals ── -->
    <div class="card" style="margin-bottom:12px;">
      <div class="card-title">🔢 FULL FUNDAMENTAL DATA</div>
      <div id="fund-ratios-table"></div>
    </div>

    <!-- ── Row 4: Peer comparison ── -->
    <div class="card" style="margin-bottom:12px;">
      <div class="card-title">⚖ PEER COMPARISON — <span id="fund-sector-label" style="color:var(--gold);letter-spacing:2px;"></span></div>
      <div style="overflow-x:auto;margin-bottom:16px;">
        <div id="fund-peer-table"></div>
      </div>
      <div class="card-title" style="margin-top:8px;font-size:0.65rem;">
        📊 PERCENTILE RANK VS SECTOR PEERS
        <span style="font-size:0.58rem;font-weight:400;color:var(--dim);margin-left:8px;">
          100% = best in sector, 0% = worst
        </span>
      </div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);margin-bottom:10px;">
        <span style="color:var(--green);">■</span> Top 30% &nbsp;
        <span style="color:var(--cyan);">■</span> Above avg &nbsp;
        <span style="color:var(--gold);">■</span> Below avg &nbsp;
        <span style="color:var(--red);">■</span> Bottom 30%
      </div>
      <canvas id="fund-peer-chart" style="width:100%;display:block;"></canvas>
    </div>

    <!-- ── Row 5: Big Players ── -->
    <div class="card" id="fund-inst-card" style="margin-bottom:12px;">
      <div class="card-title" style="color:var(--purple);">🏦 BIG PLAYERS — INSTITUTIONAL ACTIVITY</div>
      <div id="fund-inst-loading" class="loading" style="display:none;">
        <div class="spinner"></div>
        <span style="font-family:Share Tech Mono,monospace;font-size:0.72rem;">Loading institutional data...</span>
      </div>
      <div id="fund-inst-content" style="display:none;"></div>
      <div id="fund-inst-empty" style="display:none;padding:14px;font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--dim);"></div>
    </div>

  </div>
  </div>

</div>


"""


JS = r"""
async function loadFundamentals(forceRefresh) {
  const sym = document.getElementById('fund-sym').value;
  if (!sym) return;

  document.getElementById('fund-results').style.display = 'none';
  document.getElementById('fund-error').style.display   = 'none';
  document.getElementById('fund-loading').style.display = 'flex';

  try {
    const params = {symbol: sym};
    if (forceRefresh) params.refresh = '1';
    const d = await api('fundamentals', params);

    document.getElementById('fund-loading').style.display = 'none';
    document.getElementById('fund-results').style.display = 'block';
    renderFundamentals(d);
    // Load institutional data in background (non-blocking)
    loadInstitutionalData(sym);
  } catch(e) {
    document.getElementById('fund-loading').style.display = 'none';
    document.getElementById('fund-error').style.display = 'block';
    document.getElementById('fund-error').textContent = '⚠ ' + e.message;
  }
}

function renderFundamentals(d) {
  const t  = d.target || {};
  const sc = t.scores || {};
  const pr = d.peers   || [];
  const cm = d.comparison || [];

  // Header
  document.getElementById('fund-name').textContent = t.name || d.symbol;
  document.getElementById('fund-sector').textContent = (d.sector || '') + '  ·  NSE EQUITY';

  const gradeColor = {'A+':'var(--green)','A':'var(--green)','B':'var(--cyan)','C':'var(--gold)','D':'var(--red)'}[sc.grade] || 'var(--text)';
  const grade = document.getElementById('fund-grade');
  grade.textContent = sc.grade || '—';
  grade.style.color = gradeColor;

  const total = document.getElementById('fund-total');
  total.textContent = (sc.total_score || 0).toFixed(1);
  total.style.color = sc.total_score >= 70 ? 'var(--green)' : sc.total_score >= 50 ? 'var(--cyan)' : 'var(--red)';

  document.getElementById('fund-rank').textContent = d.peer_rank + ' / ' + d.peer_total;
  const vEl = document.getElementById('fund-verdict');
  vEl.textContent = sc.verdict || '—';
  vEl.style.color = gradeColor;

  // Score bars
  const dims = [
    ['Quality',  sc.quality_score,  'var(--green)',  '30%'],
    ['Growth',   sc.growth_score,   'var(--cyan)',   '25%'],
    ['Value',    sc.value_score,    'var(--gold)',   '20%'],
    ['Momentum', sc.momentum_score, 'var(--purple)', '15%'],
    ['Promoter', sc.promoter_score, 'var(--orange)', '10%'],
  ];
  let barsHtml = '';
  dims.forEach(([label, val, color, wt]) => {
    const pct = Math.max(0, Math.min(100, val || 0));
    barsHtml += `<div style="margin-bottom:10px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
        <span style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:${color};">${label} <span style="color:var(--dim);font-size:0.58rem;">(wt ${wt})</span></span>
        <span style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:${color};font-weight:700;">${pct.toFixed(1)}</span>
      </div>
      <div style="background:rgba(0,0,0,0.4);height:8px;border-radius:4px;">
        <div style="width:${pct}%;height:100%;background:${color};border-radius:4px;transition:width 0.8s;opacity:0.85;"></div>
      </div>
    </div>`;
  });
  document.getElementById('fund-score-bars').innerHTML = barsHtml;

  // Key ratios grid
  const kr = t.ratios || {};
  const fmt = t.formatted || {};
  const KEY = [
    ['P/E (TTM)',    'trailingPE'],    ['P/E (Fwd)',     'forwardPE'],
    ['P/B',         'priceToBook'],   ['EV/EBITDA',     'enterpriseToEbitda'],
    ['ROE',         'returnOnEquity'],['Net Margin',     'profitMargins'],
    ['Debt/Equity', 'debtToEquity'],  ['Current Ratio', 'currentRatio'],
    ['Rev Growth',  'revenueGrowth'], ['EPS Growth',    'earningsGrowth'],
    ['Div Yield',   'dividendYield'], ['Promoter %',    'heldPercentInsiders'],
    ['Beta',        'beta'],          ['Mkt Cap',       'marketCap'],
  ];
  let krHtml = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">';
  KEY.forEach(([label, field]) => {
    const raw = kr[field];
    let displayVal = fmt[field] || '—';
    let col = 'var(--t2)';
    // Colour coding
    if (field === 'returnOnEquity' && raw != null) {
      col = raw > 0.15 ? 'var(--green)' : raw < 0.05 ? 'var(--red)' : 'var(--t2)';
    }
    if (field === 'debtToEquity' && raw != null) {
      const deRatio = raw * 0.01;  // yfinance stores as %, convert to ratio for colour
      col = deRatio > 1.5 ? 'var(--red)' : deRatio < 0.5 ? 'var(--green)' : 'var(--gold)';
    }
    if (field === 'revenueGrowth' && raw != null) {
      col = raw > 0.10 ? 'var(--green)' : raw < 0 ? 'var(--red)' : 'var(--t2)';
    }
    if (field === 'earningsGrowth' && raw != null) {
      col = raw > 0.15 ? 'var(--green)' : raw < 0 ? 'var(--red)' : 'var(--t2)';
    }
    if (field === 'profitMargins' && raw != null) {
      col = raw > 0.15 ? 'var(--green)' : raw < 0.05 ? 'var(--red)' : 'var(--t2)';
    }
    if (field === 'trailingPE' && raw != null) {
      col = raw < 15 ? 'var(--green)' : raw > 40 ? 'var(--red)' : 'var(--t2)';
    }
    krHtml += '<div style="background:var(--p2);border:1px solid var(--border);padding:7px 10px;">'
      + '<div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;">'+label+'</div>'
      + '<div style="font-family:Share Tech Mono,monospace;font-size:0.85rem;color:'+col+';font-weight:700;margin-top:2px;">'+displayVal+'</div>'
      + '</div>';
  });
  krHtml += '</div>';
  document.getElementById('fund-key-ratios').innerHTML = krHtml;

  // Full ratios table
  const ALL_LABELS = {
    trailingPE:'P/E (TTM)',forwardPE:'P/E (Forward)',priceToBook:'P/B Ratio',
    trailingEps:'EPS (TTM)',forwardEps:'EPS (Forward)',revenueGrowth:'Revenue Growth YoY',
    earningsGrowth:'EPS Growth YoY',returnOnEquity:'ROE',returnOnAssets:'ROA',
    debtToEquity:'Debt/Equity',currentRatio:'Current Ratio',freeCashflow:'Free Cash Flow',
    grossMargins:'Gross Margin',operatingMargins:'Op Margin',profitMargins:'Net Margin',
    marketCap:'Market Cap',enterpriseToEbitda:'EV/EBITDA',dividendYield:'Div Yield',
    fiftyTwoWeekHigh:'52W High',fiftyTwoWeekLow:'52W Low',
    fiftyDayAverage:'50D SMA',twoHundredDayAverage:'200D SMA',
    heldPercentInsiders:'Promoter %',heldPercentInstitutions:'Institution %',
    beta:'Beta',pegRatio:'PEG Ratio',priceToSalesTrailing12Months:'P/S Ratio',
    week52_position_pct:'52W Position',vs_sma200_pct:'vs 200 SMA',
  };
  let rtHtml = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:4px;">';
  Object.entries(ALL_LABELS).forEach(([field, label]) => {
    const val = fmt[field];
    if (!val) return;
    rtHtml += `<div style="background:var(--p2);border:1px solid var(--border);padding:5px 8px;">
      <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);">${label}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.75rem;color:var(--t2);">${val}</div>
    </div>`;
  });
  rtHtml += '</div>';
  document.getElementById('fund-ratios-table').innerHTML = rtHtml;

  // Sector label
  document.getElementById('fund-sector-label').textContent = d.sector || 'SECTOR';

  // Peer comparison table
  const allScores = d.all_scores || [];
  let peerHtml = '<div class="trow hdr" style="grid-template-columns:80px 1fr 70px 70px 70px 70px 70px 70px;">'
    + '<div>SYMBOL</div><div>NAME</div><div>SCORE</div><div>GRADE</div>'
    + '<div>P/E</div><div>ROE</div><div>D/E</div><div>REV GR</div></div>';

  allScores.forEach(item => {
    const isTgt = item.symbol === d.symbol;
    const peer  = pr.find(p => p.symbol === item.symbol) || {};
    const ps    = peer.scores || {};
    const pr2   = peer.ratios || {};
    const pf    = (field) => {
      const v = pr2[field];
      if (v == null) return '—';
      if (['returnOnEquity','revenueGrowth','profitMargins','earningsGrowth'].includes(field))
        return (v*100).toFixed(1)+'%';
      if (field === 'debtToEquity') return (v*0.01).toFixed(2)+'x';
      if (field === 'trailingPE') return v.toFixed(1)+'x';
      return v.toFixed(2);
    };
    const sc2   = isTgt ? sc : ps;
    const score = isTgt ? sc.total_score : item.score;
    const grade = sc2.grade || '—';
    const gColor = {'A+':'var(--green)','A':'var(--green)','B':'var(--cyan)','C':'var(--gold)','D':'var(--red)'}[grade] || 'var(--text)';

    // Clickable for peers — opens their full analysis
    const clickAttr = isTgt ? '' : `onclick="fundLoadPeer('${item.symbol}')" title="Click to analyse ${item.symbol}"`;
    const cursorStyle = isTgt ? '' : 'cursor:pointer;';
    const hoverClass  = isTgt ? '' : 'peer-clickable';

    peerHtml += `<div class="trow ${hoverClass}" ${clickAttr}
      style="grid-template-columns:80px 1fr 70px 70px 70px 70px 70px 70px;${cursorStyle}
      ${isTgt?'background:rgba(0,212,255,0.06);border-left:2px solid var(--cyan);':''}">
      <div style="font-family:Share Tech Mono,monospace;font-size:0.8rem;
        color:${isTgt?'var(--cyan)':'var(--gold)'};font-weight:${isTgt?700:500};">
        ${item.symbol}${isTgt?'':' <span style="font-size:0.55rem;color:var(--dim);">↗</span>'}
      </div>
      <div style="font-size:0.75rem;">${isTgt ? (t.name||item.symbol) : (peer.name||item.symbol)}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.8rem;
        color:${score>=70?'var(--green)':score>=50?'var(--cyan)':'var(--red)'};">${score.toFixed(1)}</div>
      <div style="color:${gColor};font-family:Share Tech Mono,monospace;font-size:0.8rem;font-weight:700;">${grade}</div>
      <div style="font-size:0.75rem;">${isTgt?(fmt.trailingPE||'—'):pf('trailingPE')}</div>
      <div style="font-size:0.75rem;">${isTgt?(fmt.returnOnEquity||'—'):pf('returnOnEquity')}</div>
      <div style="font-size:0.75rem;">${isTgt?(fmt.debtToEquity||'—'):pf('debtToEquity')}</div>
      <div style="font-size:0.75rem;">${isTgt?(fmt.revenueGrowth||'—'):pf('revenueGrowth')}</div>
    </div>`;
  });
  document.getElementById('fund-peer-table').innerHTML = peerHtml;

  // Peer percentile bar chart
  renderFundPeerChart(cm, d.symbol);

  // Combined signal card
  renderFundCombined(d);
}

function renderFundPeerChart(comparison, symbol) {
  const canvas = document.getElementById('fund-peer-chart');
  if (!canvas || !comparison.length) return;

  // Use setTimeout so the canvas has a proper offsetWidth after DOM paint
  setTimeout(function() {
    const N    = comparison.length;
    const PAD  = {left: 52, right: 16, top: 28, bottom: 72};
    const BAR_GAP = 8;
    const W    = Math.max(canvas.offsetWidth || 700, N * 80);
    const barW = Math.floor((W - PAD.left - PAD.right - (N-1)*BAR_GAP) / N);
    const chartH = 180;
    const H    = chartH + PAD.top + PAD.bottom;

    canvas.width  = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d');

    // Background
    ctx.fillStyle = '#050d14';
    ctx.fillRect(0, 0, W, H);

    // Grid lines at 0%, 25%, 50%, 75%, 100%
    [0, 25, 50, 75, 100].forEach(pct => {
      const y = PAD.top + chartH - Math.round(pct / 100 * chartH);
      ctx.strokeStyle = pct === 50 ? 'rgba(0,212,255,0.15)' : 'rgba(58,90,112,0.2)';
      ctx.lineWidth = pct === 50 ? 1 : 0.5;
      ctx.setLineDash(pct === 50 ? [4,4] : []);
      ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(W - PAD.right, y); ctx.stroke();
      ctx.setLineDash([]);
      // Y-axis labels
      ctx.fillStyle = 'rgba(58,90,112,0.9)';
      ctx.font = '10px Share Tech Mono';
      ctx.textAlign = 'right';
      ctx.fillText(pct + '%', PAD.left - 6, y + 4);
    });

    // Bars
    comparison.forEach((cm, i) => {
      const x   = PAD.left + i * (barW + BAR_GAP);
      const pct = cm.percentile || 0;
      const h   = Math.round(pct / 100 * chartH);
      const y   = PAD.top + chartH - h;
      const col = pct >= 70 ? '#00ff88' : pct >= 50 ? '#00d4ff' : pct >= 30 ? '#ffcc00' : '#ff3355';

      // Bar fill
      ctx.fillStyle = col + '28';
      ctx.fillRect(x, y, barW, h);
      // Bar border
      ctx.strokeStyle = col;
      ctx.lineWidth = 1.5;
      ctx.strokeRect(x, y, barW, h);
      // Top highlight
      ctx.fillStyle = col + '60';
      ctx.fillRect(x, y, barW, 3);

      // Percentile value above bar
      ctx.fillStyle = col;
      ctx.font = 'bold 11px Share Tech Mono';
      ctx.textAlign = 'center';
      const labelY = h > 14 ? y - 5 : y - 14;
      ctx.fillText(pct.toFixed(0) + '%', x + barW/2, labelY);

      // BEST / WORST badge
      if (cm.is_best) {
        ctx.fillStyle = '#00ff88';
        ctx.font = 'bold 9px Share Tech Mono';
        ctx.fillText('★ BEST', x + barW/2, PAD.top - 10);
      } else if (cm.is_worst) {
        ctx.fillStyle = '#ff3355';
        ctx.font = 'bold 9px Share Tech Mono';
        ctx.fillText('▼ WORST', x + barW/2, PAD.top - 10);
      }

      // X-axis label — wrap onto 2 lines if needed
      const lbl = cm.label || cm.field || '';
      const words = lbl.split(' ');
      ctx.fillStyle = 'rgba(120,168,192,0.9)';
      ctx.font = '10px Share Tech Mono';
      ctx.textAlign = 'center';
      const baseY = PAD.top + chartH + 16;
      if (words.length <= 1) {
        ctx.fillText(lbl, x + barW/2, baseY);
      } else if (words.length === 2) {
        ctx.fillText(words[0], x + barW/2, baseY);
        ctx.fillText(words[1], x + barW/2, baseY + 13);
      } else {
        ctx.fillText(words[0] + ' ' + words[1], x + barW/2, baseY);
        ctx.fillText(words.slice(2).join(' '), x + barW/2, baseY + 13);
      }

      // Peer avg line (horizontal tick at 50%)
      const avgY = PAD.top + chartH - Math.round(50 / 100 * chartH);
      ctx.strokeStyle = 'rgba(0,212,255,0.4)';
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x, avgY); ctx.lineTo(x + barW, avgY); ctx.stroke();
    });

    // Y-axis border
    ctx.strokeStyle = 'rgba(58,90,112,0.4)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(PAD.left, PAD.top);
    ctx.lineTo(PAD.left, PAD.top + chartH);
    ctx.stroke();
  }, 120);
}

function renderFundCombined(d) {
  const sc = (d.target || {}).scores || {};
  const fs = sc.total_score || 0;
  const fundAdv = Math.round(fs / 4);
  const sigs = (d.fundamental_signals || []);
  const sym = d.symbol || '';

  // Show just the fundamental contribution + signals + link hint
  let html = '<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:10px;">';
  html += '<div class="stat" style="min-width:100px;"><span class="val" style="color:var(--gold);font-size:1.6rem;">'+sc.grade+'</span><span class="lbl">FUND GRADE</span></div>';
  html += '<div class="stat" style="min-width:100px;"><span class="val" style="color:var(--cyan);">'+fundAdv+'/25</span><span class="lbl">ADVISOR SCORE</span></div>';
  html += '<div style="flex:1;">';

  if (sigs.length) {
    html += '<div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:6px;">';
    sigs.forEach(s => {
      const isBull = !s.toLowerCase().includes('high debt') && !s.toLowerCase().includes('expensive');
      const col = isBull ? 'var(--green)' : 'var(--red)';
      const bg  = isBull ? 'rgba(0,255,136,0.07)' : 'rgba(255,51,85,0.07)';
      html += '<span style="background:'+bg+';border:1px solid '+col+';border-radius:2px;padding:2px 8px;font-family:Share Tech Mono,monospace;font-size:0.65rem;color:'+col+';">'+s+'</span>';
    });
    html += '</div>';
  }
  html += '<div style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--dim);">Fundamental score contributes <b style="color:var(--gold);">'+fundAdv+'/25</b> to the full 100-point combined score in Investment Advisor.</div>';
  html += '</div></div>';

  // Preview bar
  const pct = Math.min(100, fs);
  const col = fs>=70?'var(--green)':fs>=50?'var(--gold)':'var(--red)';
  html += '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">';
  html += '<span style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);min-width:120px;">FUNDAMENTAL SCORE</span>';
  html += '<div style="flex:1;background:rgba(0,0,0,0.4);height:8px;border-radius:4px;">';
  html += '<div style="width:'+pct+'%;height:100%;background:'+col+';border-radius:4px;transition:width 1s;"></div>';
  html += '</div>';
  html += '<span style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:'+col+';font-weight:700;min-width:40px;text-align:right;">'+fs.toFixed(1)+'</span>';
  html += '</div>';

  const previewEl = document.getElementById('fund-combined-preview');
  if (previewEl) previewEl.innerHTML = html;
}


// ── Standalone chart window initializer ─────────────────────────
(function() {
  if (window.location.search.indexOf('chartWindow=1') === -1) return;

  // Hide main app
  document.body.style.background = '#060f16';
  document.body.style.margin = '0';
  document.body.style.overflow = 'hidden';

  // Wait for DOM + all TV* functions to be ready, then take over
  window.addEventListener('load', function() {
    // Load state from sessionStorage
    let state;
    try {
      state = JSON.parse(sessionStorage.getItem('tvChartState') || 'null');
    } catch(e) {}
    if (!state) {
      document.body.innerHTML = '<div style="color:#ef5350;font-family:Share Tech Mono,monospace;padding:40px;font-size:1rem;">No chart data — draw a chart in main window first, then click ⛶ Expand.</div>';
      return;
    }

    // Define helper functions globally for the new UI tools
    window.cwSelectTool = function(tool, groupClass, svgCode) {
      const group = document.querySelector('.' + groupClass);
      if (group) {
        const btn = group.querySelector('.tv-group-btn');
        if (btn) {
          btn.id = 'tv-tool-' + tool;
          btn.innerHTML = svgCode + '<div class="tv-arrow-hint"></div>';
          btn.setAttribute('onclick', "tvSetTool('" + tool + "')");
        }
      }
      tvSetTool(tool);
    };
    window.cwToggleBtn = function(btn) {
      if (btn.style.color === 'var(--cyan)') {
        btn.style.color = '#6a8fa8';
        btn.style.background = 'transparent';
      } else {
        btn.style.color = 'var(--cyan)';
        btn.style.background = 'rgba(0,212,255,0.12)';
      }
    };
    window.cwSwitchRightTab = function(btn, panelId) {
      const rp = document.getElementById('tv-right-panel');
      const isExpanded = rp.classList.contains('expanded');
      const isActive = btn.classList.contains('active');
      
      document.querySelectorAll('.tv-sidebar-right .tv-btn').forEach(b => b.classList.remove('active'));
      
      if (isExpanded && isActive) {
        rp.classList.remove('expanded');
      } else {
        rp.classList.add('expanded');
        btn.classList.add('active');
        document.querySelectorAll('.tv-right-content-view').forEach(v => v.style.display = 'none');
        const view = document.getElementById('tv-panel-' + panelId);
        if (view) view.style.display = 'flex';
      }
      setTimeout(() => { tvRedraw(); }, 250);
    };

    let _cwOrderSide = 'BUY';
    let _cwOpenPos = null;

    window.cwShowOrder = function(side) {
      _cwOrderSide = side;
      const inp = document.getElementById('cw-sym-input');
      const sym = inp ? inp.value.trim().toUpperCase() : '';
      if (!sym) { alert('Enter or load a symbol first'); return; }
      
      const cmpVal = TV.data && TV.data.currentPrice ? TV.data.currentPrice : 0;
      
      const entry = cmpVal;
      const sl = cmpVal > 0 ? parseFloat((cmpVal * 0.97).toFixed(2)) : 0;
      const t1 = cmpVal > 0 ? parseFloat((cmpVal * 1.05).toFixed(2)) : 0;
      const t2 = cmpVal > 0 ? parseFloat((cmpVal * 1.10).toFixed(2)) : 0;

      document.getElementById('cw-modal-sym').textContent = sym;
      document.getElementById('cw-modal-cmp').textContent = '₹' + cmpVal.toFixed(2);
      document.getElementById('cw-modal-entry').value = entry;
      document.getElementById('cw-modal-sl').value = sl;
      document.getElementById('cw-modal-t1').value = t1;
      document.getElementById('cw-modal-t2').value = t2;
      document.getElementById('cw-modal-qty').value = 1;
      document.getElementById('cw-modal-err').style.display = 'none';

      cwSetOrderSide(side);
      cwUpdateOrderCost();

      document.getElementById('cw-order-modal').style.display = 'flex';
    };

    window.cwCloseOrder = function() {
      document.getElementById('cw-order-modal').style.display = 'none';
    };

    window.cwSetOrderSide = function(side) {
      _cwOrderSide = side;
      const buyTab = document.getElementById('cw-modal-buy-tab');
      const sellTab = document.getElementById('cw-modal-sell-tab');
      const placeBtn = document.getElementById('cw-modal-place-btn');
      if (side === 'BUY') {
        buyTab.style.background = '#089981';
        buyTab.style.color = '#fff';
        sellTab.style.background = 'transparent';
        sellTab.style.color = '#787b86';
        placeBtn.style.background = '#089981';
        placeBtn.textContent = 'PLACE BUY ORDER';
      } else {
        sellTab.style.background = '#f23645';
        sellTab.style.color = '#fff';
        buyTab.style.background = 'transparent';
        buyTab.style.color = '#787b86';
        placeBtn.style.background = '#f23645';
        placeBtn.textContent = 'PLACE SELL ORDER';
      }
    };

    window.cwUpdateOrderCost = function() {
      const qty = parseInt(document.getElementById('cw-modal-qty').value || 1) || 1;
      const entry = parseFloat(document.getElementById('cw-modal-entry').value || 0) || 0;
      const sl = parseFloat(document.getElementById('cw-modal-sl').value || 0) || 0;
      const t1 = parseFloat(document.getElementById('cw-modal-t1').value || 0) || 0;

      const cost = qty * entry;
      const profit = t1 > 0 ? (t1 - entry) * qty : 0;
      const loss = sl > 0 ? (entry - sl) * qty : 0;
      const rr = loss > 0 ? (profit / loss).toFixed(2) : '—';

      const fmt = v => '₹' + Math.abs(v).toLocaleString('en-IN', {maximumFractionDigits: 2});
      document.getElementById('cw-modal-cost').textContent = fmt(cost);
      document.getElementById('cw-modal-profit').textContent = profit > 0 ? fmt(profit) : '—';
      document.getElementById('cw-modal-loss').textContent = loss > 0 ? fmt(loss) : '—';
      document.getElementById('cw-modal-rr').textContent = rr !== '—' ? '1 : ' + rr : '—';
    };

    window.cwPlaceOrder = async function() {
      const sym = document.getElementById('cw-modal-sym').textContent;
      const qty = parseInt(document.getElementById('cw-modal-qty').value || 0);
      const entry = parseFloat(document.getElementById('cw-modal-entry').value || 0);
      const sl = parseFloat(document.getElementById('cw-modal-sl').value || 0);
      const t1 = parseFloat(document.getElementById('cw-modal-t1').value || 0);
      const t2 = parseFloat(document.getElementById('cw-modal-t2').value || 0);
      const itype = document.getElementById('cw-modal-type').value || 'swing';
      const errEl = document.getElementById('cw-modal-err');

      if (!sym || qty < 1 || entry <= 0) {
        errEl.textContent = 'Symbol, quantity and entry price are required.';
        errEl.style.display = 'block'; return;
      }

      const btn = document.getElementById('cw-modal-place-btn');
      btn.disabled = true;
      btn.textContent = 'PLACING…';
      errEl.style.display = 'none';

      try {
        const url = '/api/portfolio_add?symbol=' + encodeURIComponent(sym) +
                    '&inv_type=' + encodeURIComponent(itype) +
                    '&entry_price=' + entry +
                    '&shares=' + qty +
                    '&stop_loss=' + sl +
                    '&target1=' + t1 +
                    '&target2=' + t2;
        const res = await fetch(url).then(r => r.json());
        if (res && res.ok) {
          cwCloseOrder();
          _cwOpenPos = { id: res.trade_id || res.id, symbol: sym, entry_price: entry, shares: qty, stop_loss: sl, target1: t1, target2: t2, cmp: entry };
          cwUpdatePosBadge();
          tvRedraw();
        } else {
          errEl.textContent = (res && res.error) || 'Order failed.';
          errEl.style.display = 'block';
        }
      } catch(e) {
        errEl.textContent = 'Error: ' + e.message;
        errEl.style.display = 'block';
      } finally {
        btn.disabled = false;
        btn.textContent = _cwOrderSide === 'BUY' ? 'PLACE BUY ORDER' : 'PLACE SELL ORDER';
      }
    };

    window.cwUpdatePosBadge = async function() {
      const badge = document.getElementById('cw-pos-badge');
      const inp = document.getElementById('cw-sym-input');
      const sym = inp ? inp.value.trim().toUpperCase() : '';
      if (!sym || !badge) { if(badge) badge.style.display = 'none'; return; }

      try {
        const res = await fetch('/api/portfolio_get').then(r => r.json());
        if (!res || !res.ok) return;
        const pos = (res.trades || []).find(t => t.symbol === sym && t.status !== 'CLOSED');
        if (!pos) { badge.style.display = 'none'; _cwOpenPos = null; return; }

        let cmp = pos.entry_price;
        try {
          const px = await fetch('/api/price?symbol=' + sym).then(r => r.json());
          cmp = px.close || px.price || cmp;
        } catch(e) {}

        _cwOpenPos = { ...pos, cmp };
        const pnl = (cmp - pos.entry_price) * pos.shares;
        const pnlPct = pos.entry_price > 0 ? (pnl / (pos.entry_price * pos.shares) * 100).toFixed(2) : 0;
        const color = pnl >= 0 ? '#089981' : '#f23645';
        const sign = pnl >= 0 ? '+' : '';

        document.getElementById('cw-pos-sym').textContent = sym;
        document.getElementById('cw-pos-qty').textContent = pos.shares + ' shares';
        document.getElementById('cw-pos-pnl').textContent = sign + '₹' + Math.abs(pnl).toFixed(2) + ' (' + sign + pnlPct + '%)';
        document.getElementById('cw-pos-pnl').style.color = color;
        badge.style.display = 'flex';
      } catch(e) {
        console.error(e);
      }
    };

    window.cwSquareOff = async function() {
      if (!_cwOpenPos) return;
      const sym = _cwOpenPos.symbol;
      const cmp = _cwOpenPos.cmp || _cwOpenPos.entry_price;
      if (!confirm('Square off ' + sym + ' @ ₹' + cmp.toFixed(2) + '?')) return;
      try {
        const res = await fetch('/api/portfolio_close?id=' + _cwOpenPos.id + '&exit_price=' + cmp).then(r => r.json());
        if (res && res.ok) {
          _cwOpenPos = null;
          document.getElementById('cw-pos-badge').style.display = 'none';
          tvRedraw();
          alert('Position closed.');
        } else {
          alert('Close failed.');
        }
      } catch(e) {
        alert('Error: ' + e.message);
      }
    };

    window.cwDrawPositionLines = function() {
      const cvs = document.getElementById('price-canvas');
      if (!cvs || !_cwOpenPos || !window._chartPriceData) return;
      const ctx = cvs.getContext('2d');
      const pos = _cwOpenPos;
      const pr = window._chartPriceData;
      if (!pr || !pr.minP || !pr.maxP) return;

      const H = cvs.height;
      const W = cvs.width;
      const pad = pr.padTop || 30;
      const drawH = H - pad - (pr.padBot || 20);
      const range = pr.maxP - pr.minP;
      const p2y = price => range > 0 ? pad + drawH * (1 - (price - pr.minP) / range) : H / 2;

      const drawLine = (price, color, label) => {
        if (!price || price <= 0) return;
        const y = p2y(price);
        if (y < 0 || y > H) return;
        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.2;
        ctx.setLineDash([6, 4]);
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
        ctx.fillStyle = color;
        ctx.font = 'bold 11px -apple-system,BlinkMacSystemFont,sans-serif';
        ctx.fillText(label + ' ₹' + price.toFixed(2), W - 120, y - 3);
        ctx.restore();
      };

      drawLine(pos.entry_price, '#089981', 'ENTRY');
      drawLine(pos.stop_loss,   '#f23645', 'SL');
      drawLine(pos.target1,     '#ff9800', 'T1');
      drawLine(pos.target2,     '#ff9800', 'T2');
    };


    // Build fullscreen shell that reuses the exact same HTML structure as the main chart
    document.body.innerHTML = '';
    const shell = document.createElement('div');
    shell.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:var(--tv-color-bg);display:flex;flex-direction:column;font-family:-apple-system,BlinkMacSystemFont,"Trebuchet MS",Roboto,Ubuntu,sans-serif;';
    shell.innerHTML = `
      <style>
      /* TradingView Light Theme Variables */
      :root {
        --tv-color-bg: #ffffff;
        --tv-color-text-primary: #131722;
        --tv-color-text-secondary: #787b86;
        --tv-color-border: #e0e3eb;
        --tv-color-hover: #f0f3fa;
        --tv-color-active: #2962ff;
        --tv-color-bull: #089981;
        --tv-color-bear: #f23645;
        --tv-font-sans: -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif;
      }

      /* Reset and base */
      * { box-sizing: border-box; font-family: var(--tv-font-sans); }
      .tv-sidebar {
        width: 52px; flex-shrink: 0; background: var(--tv-color-bg); border-right: 1px solid var(--tv-color-border);
        display: flex; flex-direction: column; align-items: center; padding: 8px 0; gap: 4px; z-index: 100;
      }
      .tv-sidebar-right {
        width: 52px; flex-shrink: 0; background: var(--tv-color-bg); border-left: 1px solid var(--tv-color-border);
        display: flex; flex-direction: column; align-items: center; padding: 8px 0; gap: 4px; z-index: 100;
      }
      .tv-btn {
        width: 36px; height: 36px; border-radius: 4px; border: none; background: transparent; color: var(--tv-color-text-secondary);
        cursor: pointer; display: flex; align-items: center; justify-content: center; position: relative;
        transition: all 0.1s;
      }
      .tv-btn:hover { background: var(--tv-color-hover); color: var(--tv-color-text-primary); }
      .tv-btn.active { color: var(--tv-color-active); }
      .tv-btn svg { width: 22px; height: 22px; fill: currentColor; stroke: none; }

      /* Popout Menu Logic */
      .tv-tool-group { position: relative; }
      .tv-tool-group > .tv-popout-menu {
        display: none; position: absolute; left: 100%; top: 0; margin-left: 4px;
        background: var(--tv-color-bg); border: 1px solid var(--tv-color-border); border-radius: 6px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.15); z-index: 1000; min-width: 180px; padding: 6px 0;
      }
      .tv-tool-group:hover > .tv-popout-menu { display: block; }

      .tv-popout-item {
        display: flex; align-items: center; gap: 12px; padding: 6px 16px;
        color: var(--tv-color-text-primary); cursor: pointer; text-decoration: none; font-size: 13px;
      }
      .tv-popout-item:hover { background: var(--tv-color-hover); }
      .tv-popout-item svg { width: 18px; height: 18px; fill: currentColor; }

      .tv-divider { width: 24px; height: 1px; background: var(--tv-color-border); margin: 6px 0; }
      .tv-arrow-hint {
        position: absolute; right: 2px; bottom: 2px;
        border: solid transparent; border-width: 3px; border-bottom-color: var(--tv-color-text-secondary); border-right-color: var(--tv-color-text-secondary);
      }

      /* Right panel expanded */
      #tv-right-panel {
        width: 0; min-width: 0; flex-shrink: 0; white-space: nowrap; overflow: hidden; background: var(--tv-color-bg); border-left: 1px solid var(--tv-color-border);
        display: flex; flex-direction: column; transition: width 0.2s; z-index: 100;
      }
      #tv-right-panel.expanded { width: 340px; }
      .tv-right-panel-header {
        padding: 12px 16px; border-bottom: 1px solid var(--tv-color-border);
        display: flex; justify-content: space-between; align-items: center;
      }
      .tv-right-panel-title { color: var(--tv-color-text-primary); font-weight: 600; font-size: 14px; }
      </style>

      <div style="display:flex;flex:1;min-height:0;position:relative;">
        <!-- Left toolbar -->
        <div class="tv-sidebar" id="tv-left-sidebar">

          <!-- Cursors -->
          <div class="tv-tool-group grp-cursor">
            <button id="tv-tool-cursor" class="tv-btn tv-group-btn active" title="Crosshair" onclick="tvSetTool('cursor')">
              <svg viewBox="0 0 24 24"><path d="M11 5v6H5v2h6v6h2v-6h6v-2h-6V5h-2z" fill="currentColor"/></svg>
              <div class="tv-arrow-hint"></div>
            </button>
            <div class="tv-popout-menu">
              <div class="tv-popout-item" onclick="cwSelectTool('cursor', 'grp-cursor', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M11 5v6H5v2h6v6h2v-6h6v-2h-6V5h-2z" fill="currentColor"/></svg>Crosshair</div>
              <div class="tv-popout-item" onclick="cwSelectTool('dot', 'grp-cursor', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="2" fill="currentColor"/></svg>Dot</div>
              <div class="tv-popout-item" onclick="cwSelectTool('arrow', 'grp-cursor', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M7 10l5-5 5 5H7z" fill="currentColor"/></svg>Arrow</div>
              <div class="tv-popout-item" onclick="cwSelectTool('eraser', 'grp-cursor', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M15 4l5 5-10 10-5-5L15 4z" fill="currentColor"/></svg>Eraser</div>
            </div>
          </div>
          
          <div class="tv-divider"></div>
          
          <!-- Lines Group -->
          <div class="tv-tool-group grp-lines">
            <button id="tv-tool-trendline" class="tv-btn tv-group-btn" title="Trend Line Tools" onclick="tvSetTool('trendline')">
              <svg viewBox="0 0 24 24"><path d="M5.5 17L17 5.5 18.5 7 7 18.5z" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>
              <div class="tv-arrow-hint"></div>
            </button>
            <div class="tv-popout-menu">
              <div class="tv-popout-item" onclick="cwSelectTool('trendline', 'grp-lines', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M5.5 17L17 5.5 18.5 7 7 18.5z" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>Trendline</div>
              <div class="tv-popout-item" onclick="cwSelectTool('ray', 'grp-lines', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M5 19L19 5M19 5v4M19 5h-4" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>Ray</div>
              <div class="tv-popout-item" onclick="cwSelectTool('infoline', 'grp-lines', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M5 19L19 5M14 10l-4 4" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>Info line</div>
              <div class="tv-popout-item" onclick="cwSelectTool('extline', 'grp-lines', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M3 21l18-18" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>Extended line</div>
              <div class="tv-divider"></div>
              <div class="tv-popout-item" onclick="cwSelectTool('hline', 'grp-lines', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M3 12h18" stroke="currentColor" stroke-width="1.2"/></svg>Horizontal line</div>
              <div class="tv-popout-item" onclick="cwSelectTool('hray', 'grp-lines', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M12 12h9M12 12v-2M12 12v2" stroke="currentColor" stroke-width="1.2"/></svg>Horizontal ray</div>
              <div class="tv-popout-item" onclick="cwSelectTool('vline', 'grp-lines', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M12 3v18" stroke="currentColor" stroke-width="1.2"/></svg>Vertical line</div>
              <div class="tv-popout-item" onclick="cwSelectTool('crossline', 'grp-lines', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M12 3v18M3 12h18" stroke="currentColor" stroke-width="1.2"/></svg>Cross line</div>
            </div>
          </div>

          <!-- Gann/Fib Group -->
          <div class="tv-tool-group grp-fib">
            <button id="tv-tool-fib" class="tv-btn tv-group-btn" title="Gann and Fibonacci Tools" onclick="tvSetTool('fib')">
              <svg viewBox="0 0 24 24"><path d="M4 6h16M4 10h16M4 14h16M4 18h16M4 18L20 6" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>
              <div class="tv-arrow-hint"></div>
            </button>
            <div class="tv-popout-menu">
              <div style="padding:4px 16px;font-size:10px;color:var(--tv-color-text-secondary);letter-spacing:0.5px;">FIBONACCI</div>
              <div class="tv-popout-item" onclick="cwSelectTool('fib', 'grp-fib', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M4 6h16M4 10h16M4 14h16M4 18h16M4 18L20 6" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>Fib Retracement</div>
              <div class="tv-popout-item" onclick="cwSelectTool('fibext', 'grp-fib', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16M4 18l6-6-6-6" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>Trend-based fib extension</div>
              <div class="tv-popout-item" onclick="cwSelectTool('fibtz', 'grp-fib', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M6 4v16M12 4v16M18 4v16M4 12l16-6" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>Fib time zone</div>
              <div class="tv-divider"></div>
              <div style="padding:4px 16px;font-size:10px;color:var(--tv-color-text-secondary);letter-spacing:0.5px;">GANN</div>
              <div class="tv-popout-item" onclick="cwSelectTool('gannbox', 'grp-fib', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><rect x="5" y="5" width="14" height="14" stroke="currentColor" stroke-width="1.2" fill="none"/><path d="M5 12h14M12 5v14M5 5l14 14M19 5L5 19" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>Gann box</div>
              <div class="tv-popout-item" onclick="cwSelectTool('gannfan', 'grp-fib', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M4 20L20 4M4 20L20 12M4 20l8-16M4 20h16M4 20V4" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>Gann fan</div>
            </div>
          </div>

          <!-- Shapes Group -->
          <div class="tv-tool-group grp-shapes">
            <button id="tv-tool-rect" class="tv-btn tv-group-btn" title="Geometric Shapes" onclick="tvSetTool('rect')">
              <svg viewBox="0 0 24 24"><rect x="4" y="6" width="16" height="12" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>
              <div class="tv-arrow-hint"></div>
            </button>
            <div class="tv-popout-menu">
              <div class="tv-popout-item" onclick="cwSelectTool('brush', 'grp-shapes', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M7 16c-1 0-2 .5-2 1.5S6 20 7 20s3-1 3-3-2-2-3-2zm5-11l-7 7 2 2 7-7-2-2z" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>Brush</div>
              <div class="tv-popout-item" onclick="cwSelectTool('rect', 'grp-shapes', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><rect x="4" y="6" width="16" height="12" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>Rectangle</div>
              <div class="tv-popout-item" onclick="cwSelectTool('ellipse', 'grp-shapes', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><ellipse cx="12" cy="12" rx="8" ry="5" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>Ellipse</div>
              <div class="tv-popout-item" onclick="cwSelectTool('triangle', 'grp-shapes', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M12 5l8 14H4z" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>Triangle</div>
            </div>
          </div>

          <!-- Text Group -->
          <div class="tv-tool-group grp-text">
            <button id="tv-tool-text" class="tv-btn tv-group-btn" title="Text Tools" onclick="tvSetTool('text')">
              <svg viewBox="0 0 24 24"><path d="M6 7h12M12 7v11" stroke="currentColor" stroke-width="2" fill="none"/></svg>
              <div class="tv-arrow-hint"></div>
            </button>
            <div class="tv-popout-menu">
              <div class="tv-popout-item" onclick="cwSelectTool('text', 'grp-text', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M6 7h12M12 7v11" stroke="currentColor" stroke-width="2" fill="none"/></svg>Text</div>
            </div>
          </div>

          <!-- Patterns Group (New) -->
          <div class="tv-tool-group grp-patterns">
            <button id="tv-tool-patterns" class="tv-btn tv-group-btn" title="Patterns" onclick="tvSetTool('patterns')">
              <svg viewBox="0 0 24 24"><path d="M4 12l4-6 6 8 6-4" stroke="currentColor" stroke-width="1.2" fill="none"/><circle cx="4" cy="12" r="1.5" fill="currentColor"/><circle cx="8" cy="6" r="1.5" fill="currentColor"/><circle cx="14" cy="14" r="1.5" fill="currentColor"/><circle cx="20" cy="10" r="1.5" fill="currentColor"/></svg>
              <div class="tv-arrow-hint"></div>
            </button>
            <div class="tv-popout-menu">
              <div style="padding:4px 16px;font-size:10px;color:var(--tv-color-text-secondary);letter-spacing:0.5px;">CHART PATTERNS</div>
              <div class="tv-popout-item" onclick="cwSelectTool('xabcd', 'grp-patterns', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M4 12l4-6 6 8 6-4" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>XABCD Pattern</div>
              <div class="tv-popout-item" onclick="cwSelectTool('hns', 'grp-patterns', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M4 16l3-6 3 4 2-8 3 8 3-4 2 6" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>Head and shoulders</div>
              <div class="tv-divider"></div>
              <div style="padding:4px 16px;font-size:10px;color:var(--tv-color-text-secondary);letter-spacing:0.5px;">ELLIOTT WAVES</div>
              <div class="tv-popout-item" onclick="cwSelectTool('ewimpulse', 'grp-patterns', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M3 18l4-8 3 4 5-10 6 6" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>Elliott impulse wave (12345)</div>
            </div>
          </div>

          <!-- Measurement Group -->
          <div class="tv-tool-group grp-measure">
            <button id="tv-tool-measure" class="tv-btn tv-group-btn" title="Prediction and Measurement Tools" onclick="tvSetTool('measure')">
              <svg viewBox="0 0 24 24"><path d="M4 12h16M12 4v16" stroke="currentColor" stroke-width="1.2" fill="none"/><circle cx="12" cy="12" r="3" fill="currentColor"/></svg>
              <div class="tv-arrow-hint"></div>
            </button>
            <div class="tv-popout-menu">
              <div class="tv-popout-item" onclick="cwSelectTool('measure', 'grp-measure', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><path d="M4 12h16M12 4v16" stroke="currentColor" stroke-width="1.2" fill="none"/><circle cx="12" cy="12" r="3" fill="currentColor"/></svg>Measure</div>
              <div class="tv-popout-item" onclick="cwSelectTool('longpos', 'grp-measure', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><rect x="6" y="4" width="12" height="6" fill="var(--tv-color-bull)" opacity="0.4"/><rect x="6" y="10" width="12" height="10" fill="var(--tv-color-bear)" opacity="0.4"/><path d="M6 10h12" stroke="currentColor" stroke-width="1"/></svg>Long Position</div>
              <div class="tv-popout-item" onclick="cwSelectTool('shortpos', 'grp-measure', this.querySelector('svg').outerHTML)"><svg viewBox="0 0 24 24"><rect x="6" y="4" width="12" height="10" fill="var(--tv-color-bear)" opacity="0.4"/><rect x="6" y="14" width="12" height="6" fill="var(--tv-color-bull)" opacity="0.4"/><path d="M6 14h12" stroke="currentColor" stroke-width="1"/></svg>Short Position</div>
            </div>
          </div>

          <div class="tv-divider"></div>
          <div style="flex:1;"></div>
          
          <!-- Action tools -->
          <button class="tv-btn" id="btn-magnet" title="Magnet Mode" onclick="cwToggleBtn(this); TV.magnet = !TV.magnet; tvSaveChartState();">
            <svg viewBox="0 0 24 24"><path d="M6 10a6 6 0 1 0 12 0V6h-3v4a3 3 0 1 1-6 0V6H6v4z" fill="currentColor"/><path d="M6 6h3v4H6zM15 6h3v4h-3z" fill="#ef5350"/></svg>
          </button>
          <button class="tv-btn" id="btn-stay-drawing" title="Stay in Drawing Mode" onclick="cwToggleBtn(this); TV.stayInDrawingMode = !TV.stayInDrawingMode; tvSaveChartState();">
            <svg viewBox="0 0 24 24"><path d="M15.5 12h4m-4 4h4m-4-8h4M5 14h6v6H5z" stroke="currentColor" stroke-width="1.5" fill="none"/></svg>
          </button>
          <button class="tv-btn" id="btn-lock-drawings" title="Lock All Drawings" onclick="cwToggleBtn(this); TV.lockDrawings = !TV.lockDrawings; tvSaveChartState();">
            <svg viewBox="0 0 24 24"><rect x="7" y="10" width="10" height="8" rx="2" stroke="currentColor" stroke-width="1.5" fill="none"/><path d="M9 10V7a3 3 0 0 1 6 0v3" stroke="currentColor" stroke-width="1.5" fill="none"/></svg>
          </button>
          <button class="tv-btn" title="Hide All Drawings" onclick="cwToggleBtn(this); TV.drawingsHidden = !TV.drawingsHidden; tvRedraw();">
            <svg viewBox="0 0 24 24"><path d="M12 8c-3.5 0-6.5 2.5-8 6 1.5 3.5 4.5 6 8 6s6.5-2.5 8-6c-1.5-3.5-4.5-6-8-6z" stroke="currentColor" stroke-width="1.5" fill="none"/><circle cx="12" cy="14" r="2.5" fill="currentColor"/></svg>
          </button>
          <button class="tv-btn" title="Remove Drawings" onclick="tvClearDrawings()">
            <svg viewBox="0 0 24 24"><path d="M6 6h12l-1 12H7L6 6zM9 6V4h6v2M10 9v6M14 9v6" stroke="currentColor" stroke-width="1.5" fill="none"/></svg>
          </button>

        </div>

        <!-- Main chart area -->
        <div style="flex:1;min-width:0;display:flex;flex-direction:column;position:relative;" id="tv-chart-card">
          <!-- Top Toolbar -->
          <div style="display:flex;align-items:center;gap:12px;padding:6px 12px;border-bottom:1px solid var(--tv-color-border);background:var(--tv-color-bg);height:42px;">
            <!-- Editable symbol search -->
            <div style="position:relative;flex-shrink:0;display:flex;align-items:center;">
              <svg width="20" height="20" viewBox="0 0 24 24" style="fill:var(--tv-color-text-secondary);margin-right:6px;"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
              <input id="cw-sym-input" value="" placeholder="Symbol Search"
                style="background:transparent;border:none;color:var(--tv-color-text-primary);font-size:16px;font-weight:600;width:160px;outline:none;"
                onkeydown="cwSymKeyNav(event)" oninput="cwFilterSymSuggestions(this.value)">
              <div id="cw-sym-suggestions" style="display:none;position:absolute;top:100%;left:0;margin-top:8px;
                background:var(--tv-color-bg);border:1px solid var(--tv-color-border);border-radius:6px;box-shadow:0 4px 10px rgba(0,0,0,0.1);z-index:400;min-width:260px;max-height:300px;overflow-y:auto;padding:8px 0;">
              </div>
              <span id="cw-sym-loading" style="display:none;position:absolute;right:0;font-size:12px;color:var(--tv-color-text-secondary);">⟳</span>
            </div>
            
            <div style="width:1px;height:24px;background:var(--tv-color-border);"></div>
            
            <span id="tv-sym-label" style="display:none;"></span>
            
            <!-- Timeframe selector -->
            <div style="position:relative;flex-shrink:0;">
              <div id="cw-tf-btn" onclick="cwToggleTfMenu()"
                style="padding:6px 12px;font-size:13px;font-weight:500;cursor:pointer;border-radius:4px;color:var(--tv-color-text-primary);display:flex;align-items:center;gap:6px;transition:background 0.1s;"
                onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'">
                <span id="cw-tf-label">1D</span>
                <svg width="10" height="6" viewBox="0 0 10 6" style="fill:currentColor;"><path d="M0 0h10L5 6z"/></svg>
              </div>
              <div id="cw-tf-menu" style="display:none;position:absolute;top:100%;left:0;margin-top:4px;
                background:var(--tv-color-bg);border:1px solid var(--tv-color-border);border-radius:6px;box-shadow:0 2px 5px rgba(0,0,0,0.1);z-index:300;min-width:120px;padding:6px 0;">
                <div onclick="cwSetTimeframe('1D','1 day')"  style="padding:8px 16px;font-size:13px;cursor:pointer;color:var(--tv-color-text-primary);" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'">1 day</div>
                <div onclick="cwSetTimeframe('1W','1 week')" style="padding:8px 16px;font-size:13px;cursor:pointer;color:var(--tv-color-text-primary);" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'">1 week</div>
                <div onclick="cwSetTimeframe('1M','1 month')"style="padding:8px 16px;font-size:13px;cursor:pointer;color:var(--tv-color-text-primary);" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'">1 month</div>
              </div>
            </div>
            
            <div style="width:1px;height:24px;background:var(--tv-color-border);"></div>

            <!-- Chart Type selector -->
            <div style="position:relative;">
              <div id="ct-dropdown-btn" onclick="tvToggleChartTypeMenu()"
                style="padding:6px 12px;font-size:13px;font-weight:500;cursor:pointer;border-radius:4px;color:var(--tv-color-text-primary);display:flex;align-items:center;gap:6px;transition:background 0.1s;"
                onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'">
                <span id="ct-label" style="display:flex;align-items:center;gap:6px;"><svg width="18" height="18" viewBox="0 0 24 24"><path d="M9 4H7v2H5v12h2v2h2v-2h2V6H9V4zm10 4h-2V6h-2v12h2v2h2v-2h2V8h-2z" fill="currentColor"/></svg> Candles</span>
                <svg width="10" height="6" viewBox="0 0 10 6" style="fill:currentColor;"><path d="M0 0h10L5 6z"/></svg>
              </div>
              <div id="ct-menu" style="display:none;position:absolute;top:100%;left:0;margin-top:4px;background:var(--tv-color-bg);border:1px solid var(--tv-color-border);border-radius:6px;box-shadow:0 2px 5px rgba(0,0,0,0.1);z-index:300;min-width:140px;padding:6px 0;">
                <div onclick="setChartType('candle');tvToggleChartTypeMenu()" style="padding:8px 16px;font-size:13px;cursor:pointer;color:var(--tv-color-text-primary);display:flex;align-items:center;gap:8px;" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'"><svg width="18" height="18" viewBox="0 0 24 24"><path d="M9 4H7v2H5v12h2v2h2v-2h2V6H9V4zm10 4h-2V6h-2v12h2v2h2v-2h2V8h-2z" fill="currentColor"/></svg> Candles</div>
                <div onclick="setChartType('line');tvToggleChartTypeMenu()" style="padding:8px 16px;font-size:13px;cursor:pointer;color:var(--tv-color-text-primary);display:flex;align-items:center;gap:8px;" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'"><svg width="18" height="18" viewBox="0 0 24 24"><path d="M22 7l-7 7-4-4L2 19" stroke="currentColor" stroke-width="2" fill="none"/></svg> Line</div>
                <div onclick="setChartType('bar');tvToggleChartTypeMenu()" style="padding:8px 16px;font-size:13px;cursor:pointer;color:var(--tv-color-text-primary);display:flex;align-items:center;gap:8px;" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'"><svg width="18" height="18" viewBox="0 0 24 24"><path d="M6 4v16M6 8h4M6 16H2M18 4v16M18 8h4M18 16h-4" stroke="currentColor" stroke-width="2"/></svg> Bars</div>
              </div>
            </div>
            
            <div style="width:1px;height:24px;background:var(--tv-color-border);"></div>

            <!-- Indicators Button -->
            <div onclick="tvShowIndicatorPopup()" style="padding:6px 12px;font-size:13px;font-weight:500;cursor:pointer;border-radius:4px;color:var(--tv-color-text-primary);display:flex;align-items:center;gap:6px;transition:background 0.1s;" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'">
              <svg width="18" height="18" viewBox="0 0 24 24"><path d="M3 21h18v-2H3v2zM3 13h4v4H3v-4zm7-6h4v10h-4V7zm7 3h4v7h-4v-7z" fill="currentColor"/></svg>
              Indicators
            </div>

            <div style="width:1px;height:24px;background:var(--tv-color-border);"></div>

            <!-- ── BUY / SELL buttons (Zerodha-style) ── -->
            <button onclick="cwShowOrder('BUY')"
              style="padding:6px 18px;background:#089981;border:none;border-radius:4px;
              color:#fff;font-size:13px;font-weight:600;cursor:pointer;letter-spacing:0.3px;">
              BUY
            </button>
            <button onclick="cwShowOrder('SELL')"
              style="padding:6px 18px;background:#f23645;border:none;border-radius:4px;
              color:#fff;font-size:13px;font-weight:600;cursor:pointer;letter-spacing:0.3px;">
              SELL
            </button>

            <span id="tv-ohlcv-bar" style="color:var(--tv-color-text-secondary);flex:1;overflow:hidden;white-space:nowrap;font-size:12px;margin-left:12px;"></span>
          </div>

          <!-- ── ORDER TICKET MODAL (chartWindow) ── -->
          <div id="cw-order-modal" style="display:none;position:fixed;inset:0;
            background:rgba(0,0,0,0.55);z-index:9999;align-items:center;justify-content:center;">
            <div style="background:#ffffff;border-radius:8px;padding:24px;width:400px;
              max-width:95vw;box-shadow:0 8px 32px rgba(0,0,0,0.18);position:relative;
              font-family:-apple-system,BlinkMacSystemFont,'Trebuchet MS',Roboto,Ubuntu,sans-serif;">

              <!-- Header -->
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
                <div>
                  <div id="cw-modal-sym" style="font-size:16px;font-weight:700;color:#131722;"></div>
                  <div style="display:flex;gap:8px;margin-top:3px;align-items:center;">
                    <span style="font-size:12px;color:#787b86;">NSE</span>
                    <span id="cw-modal-cmp" style="font-size:14px;font-weight:700;color:#089981;"></span>
                  </div>
                </div>
                <div style="display:flex;gap:6px;">
                  <button id="cw-modal-buy-tab" onclick="cwSetOrderSide('BUY')"
                    style="padding:6px 18px;border-radius:4px;border:none;background:#089981;
                    color:#fff;font-size:13px;font-weight:600;cursor:pointer;">B</button>
                  <button id="cw-modal-sell-tab" onclick="cwSetOrderSide('SELL')"
                    style="padding:6px 18px;border-radius:4px;border:1px solid #e0e3eb;
                    background:transparent;color:#787b86;font-size:13px;cursor:pointer;">S</button>
                </div>
                <button onclick="cwCloseOrder()"
                  style="background:transparent;border:none;color:#787b86;font-size:18px;cursor:pointer;padding:4px 8px;">✕</button>
              </div>

              <!-- Order type tabs -->
              <div style="display:flex;gap:0;border-bottom:2px solid #e0e3eb;margin-bottom:16px;">
                <div style="padding:6px 14px;font-size:13px;color:#2962ff;border-bottom:2px solid #2962ff;margin-bottom:-2px;cursor:pointer;">Regular</div>
                <div style="padding:6px 14px;font-size:13px;color:#787b86;cursor:pointer;">Stop Loss</div>
                <div style="padding:6px 14px;font-size:13px;color:#787b86;cursor:pointer;">GTT</div>
              </div>

              <!-- Fields -->
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px;">
                <div>
                  <div style="font-size:11px;color:#787b86;margin-bottom:4px;font-weight:500;">QTY / SHARES</div>
                  <input id="cw-modal-qty" type="number" value="1" min="1"
                    style="width:100%;border:1px solid #e0e3eb;border-radius:4px;padding:8px 10px;
                    font-size:14px;color:#131722;outline:none;box-sizing:border-box;"
                    oninput="cwUpdateOrderCost()"/>
                </div>
                <div>
                  <div style="font-size:11px;color:#787b86;margin-bottom:4px;font-weight:500;">ENTRY PRICE ₹</div>
                  <input id="cw-modal-entry" type="number" step="0.05"
                    style="width:100%;border:1px solid #e0e3eb;border-radius:4px;padding:8px 10px;
                    font-size:14px;color:#131722;outline:none;box-sizing:border-box;"
                    oninput="cwUpdateOrderCost()"/>
                </div>
                <div>
                  <div style="font-size:11px;color:#787b86;margin-bottom:4px;font-weight:500;">STOP LOSS ₹</div>
                  <input id="cw-modal-sl" type="number" step="0.05"
                    style="width:100%;border:1px solid #e0e3eb;border-radius:4px;padding:8px 10px;
                    font-size:14px;color:#131722;outline:none;box-sizing:border-box;"
                    oninput="cwUpdateOrderCost()"/>
                </div>
                <div>
                  <div style="font-size:11px;color:#787b86;margin-bottom:4px;font-weight:500;">TARGET 1 ₹</div>
                  <input id="cw-modal-t1" type="number" step="0.05"
                    style="width:100%;border:1px solid #e0e3eb;border-radius:4px;padding:8px 10px;
                    font-size:14px;color:#131722;outline:none;box-sizing:border-box;"
                    oninput="cwUpdateOrderCost()"/>
                </div>
                <div>
                  <div style="font-size:11px;color:#787b86;margin-bottom:4px;font-weight:500;">TARGET 2 ₹</div>
                  <input id="cw-modal-t2" type="number" step="0.05"
                    style="width:100%;border:1px solid #e0e3eb;border-radius:4px;padding:8px 10px;
                    font-size:14px;color:#131722;outline:none;box-sizing:border-box;"/>
                </div>
                <div>
                  <div style="font-size:11px;color:#787b86;margin-bottom:4px;font-weight:500;">TYPE</div>
                  <select id="cw-modal-type"
                    style="width:100%;border:1px solid #e0e3eb;border-radius:4px;padding:8px 10px;
                    font-size:13px;color:#131722;outline:none;box-sizing:border-box;background:#fff;">
                    <option value="intraday">Intraday</option>
                    <option value="swing">Swing</option>
                    <option value="short">Short-term</option>
                    <option value="long">Long-term</option>
                  </select>
                </div>
              </div>

              <!-- Cost summary -->
              <div style="background:#f0f3fa;border-radius:6px;padding:10px 14px;margin-bottom:16px;">
                <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
                  <span style="font-size:12px;color:#787b86;">Required capital</span>
                  <span id="cw-modal-cost"   style="font-size:13px;font-weight:600;color:#131722;">₹0</span>
                </div>
                <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
                  <span style="font-size:12px;color:#787b86;">Max profit (T1)</span>
                  <span id="cw-modal-profit" style="font-size:13px;font-weight:600;color:#089981;">₹0</span>
                </div>
                <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
                  <span style="font-size:12px;color:#787b86;">Max loss (SL)</span>
                  <span id="cw-modal-loss"   style="font-size:13px;font-weight:600;color:#f23645;">₹0</span>
                </div>
                <div style="display:flex;justify-content:space-between;">
                  <span style="font-size:12px;color:#787b86;">Risk : Reward</span>
                  <span id="cw-modal-rr"     style="font-size:13px;font-weight:600;color:#131722;">—</span>
                </div>
              </div>

              <!-- Place button -->
              <button id="cw-modal-place-btn" onclick="cwPlaceOrder()"
                style="width:100%;padding:12px;border:none;border-radius:4px;
                background:#089981;color:#fff;font-size:14px;font-weight:700;
                cursor:pointer;letter-spacing:0.5px;">
                PLACE BUY ORDER
              </button>
              <div id="cw-modal-err" style="display:none;margin-top:8px;font-size:12px;
                color:#f23645;text-align:center;"></div>

            </div>
          </div>

          <!-- Indicator values row -->
          <div id="tv-ind-values" style="display:none;padding:4px 12px;border-bottom:1px solid var(--tv-color-border);font-size:12px;background:var(--tv-color-bg);color:var(--tv-color-text-secondary);position:absolute;top:42px;left:0;right:0;z-index:10;pointer-events:none;">
            <span id="tv-sma-vals"></span><span id="tv-ema-vals" style="margin-left:14px;"></span><span id="tv-bb-vals" style="margin-left:14px;"></span><span id="tv-rsi-vals" style="margin-left:14px;"></span>
          </div>
          <!-- Draw tip -->
          <div id="tv-draw-tip" style="display:none;position:absolute;top:50px;left:50%;transform:translateX(-50%);background:var(--tv-color-text-primary);border-radius:12px;padding:4px 12px;font-size:12px;color:var(--tv-color-bg);pointer-events:none;z-index:50;white-space:nowrap;box-shadow:0 2px 5px rgba(0,0,0,0.2);"></div>
          <!-- Float nav (bottom controls) -->
          <div style="position:absolute;bottom:24px;left:50%;transform:translateX(-50%);display:flex;gap:1px;z-index:20;background:var(--tv-color-bg);border-radius:6px;box-shadow:0 2px 5px rgba(0,0,0,0.15);padding:2px;">
            <button onclick="tvZoom(-1)" style="width:30px;height:30px;border:none;background:transparent;color:var(--tv-color-text-secondary);cursor:pointer;font-size:16px;border-radius:4px;" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'">−</button>
            <button onclick="tvZoom(1)"  style="width:30px;height:30px;border:none;background:transparent;color:var(--tv-color-text-secondary);cursor:pointer;font-size:16px;border-radius:4px;" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'">+</button>
            <div style="width:1px;background:var(--tv-color-border);margin:4px 2px;"></div>
            <button onclick="tvPan(-1)"  style="width:30px;height:30px;border:none;background:transparent;color:var(--tv-color-text-secondary);cursor:pointer;font-size:16px;border-radius:4px;" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'">‹</button>
            <button onclick="tvPan(1)"   style="width:30px;height:30px;border:none;background:transparent;color:var(--tv-color-text-secondary);cursor:pointer;font-size:16px;border-radius:4px;" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'">›</button>
            <div style="width:1px;background:var(--tv-color-border);margin:4px 2px;"></div>
            <button onclick="tvResetView()" style="width:30px;height:30px;border:none;background:transparent;color:var(--tv-color-text-secondary);cursor:pointer;font-size:16px;border-radius:4px;" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'">↺</button>
          </div>
          <!-- Canvas -->
          <canvas id="price-canvas" style="display:block;cursor:crosshair;width:100%;flex:1;background:var(--tv-color-bg);"></canvas>
          <!-- Hidden state spans -->
          <span id="ind-sma" style="display:none;"></span><span id="ind-bb" style="display:none;"></span>
          <span id="ind-vol" style="display:none;"></span><span id="ind-rsi" style="display:none;"></span>
          <span id="ind-macd" style="display:none;"></span><span id="ind-adx" style="display:none;"></span>
          <span id="ind-sr" style="display:none;"></span>
          <!-- Sub-panels with drag-to-resize handles -->
          <div id="sub-panel-vol"  style="display:none;flex-shrink:0;position:relative;">
            <div class="sp-resize-handle" data-panel="vol"  style="height:4px;background:rgba(255,255,255,0.04);cursor:row-resize;border-top:1px solid rgba(255,255,255,0.08);" onmousedown="cwStartResize(event,'vol')"></div>
            <canvas id="vol-canvas"  style="display:block;width:100%;height:80px;"></canvas>
          </div>
          <div id="sub-panel-rsi"  style="display:none;flex-shrink:0;position:relative;">
            <div class="sp-resize-handle" data-panel="rsi"  style="height:4px;background:rgba(255,255,255,0.04);cursor:row-resize;border-top:1px solid rgba(255,255,255,0.08);" onmousedown="cwStartResize(event,'rsi')"></div>
            <canvas id="rsi-canvas"  style="display:block;width:100%;height:100px;"></canvas>
          </div>
          <div id="sub-panel-macd" style="display:none;flex-shrink:0;position:relative;">
            <div class="sp-resize-handle" data-panel="macd" style="height:4px;background:rgba(255,255,255,0.04);cursor:row-resize;border-top:1px solid rgba(255,255,255,0.08);" onmousedown="cwStartResize(event,'macd')"></div>
            <canvas id="macd-canvas" style="display:block;width:100%;height:100px;"></canvas>
          </div>
          <div id="sub-panel-adx"  style="display:none;flex-shrink:0;position:relative;">
            <div class="sp-resize-handle" data-panel="adx"  style="height:4px;background:rgba(255,255,255,0.04);cursor:row-resize;border-top:1px solid rgba(255,255,255,0.08);" onmousedown="cwStartResize(event,'adx')"></div>
            <canvas id="adx-canvas"  style="display:block;width:100%;height:100px;"></canvas>
          </div>
          
          <!-- Context Menu -->
          <div id="tv-context-menu" style="display:none;position:absolute;background:var(--tv-color-bg);border:1px solid var(--tv-color-border);border-radius:6px;box-shadow:0 4px 12px rgba(0,0,0,0.15);z-index:1000;min-width:180px;padding:6px 0;font-size:13px;color:var(--tv-color-text-primary);">
            <div onclick="tvContextAction('reset')" style="padding:8px 16px;cursor:pointer;display:flex;align-items:center;gap:8px;" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'"><svg width="18" height="18" viewBox="0 0 24 24"><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z" fill="currentColor"/></svg> Reset Chart View</div>
            <div onclick="tvContextAction('clear_drawings')" style="padding:8px 16px;cursor:pointer;display:flex;align-items:center;gap:8px;" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'"><svg width="18" height="18" viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" fill="currentColor"/></svg> Remove All Drawings</div>
            <div style="height:1px;background:var(--tv-color-border);margin:4px 0;"></div>
            <div onclick="tvContextAction('settings')" style="padding:8px 16px;cursor:pointer;display:flex;align-items:center;gap:8px;" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'"><svg width="18" height="18" viewBox="0 0 24 24"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.73 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .43-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.49-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z" fill="currentColor"/></svg> Settings...</div>
          </div>
          <!-- Bottom Timeline Range Selector -->
          <div style="height:32px;border-top:1px solid var(--tv-color-border);display:flex;align-items:center;padding:0 8px;background:var(--tv-color-bg);font-size:12px;font-family:Share Tech Mono,monospace;gap:4px;user-select:none;justify-content:space-between;">
            <div style="display:flex;gap:2px;">
              <button onclick="tvSetTimeRange('1D')" class="tv-range-btn" style="background:transparent;border:none;color:var(--tv-color-text-secondary);cursor:pointer;padding:4px 8px;border-radius:3px;">1D</button>
              <button onclick="tvSetTimeRange('5D')" class="tv-range-btn" style="background:transparent;border:none;color:var(--tv-color-text-secondary);cursor:pointer;padding:4px 8px;border-radius:3px;">5D</button>
              <button onclick="tvSetTimeRange('1M')" class="tv-range-btn" style="background:transparent;border:none;color:var(--tv-color-text-secondary);cursor:pointer;padding:4px 8px;border-radius:3px;">1M</button>
              <button onclick="tvSetTimeRange('3M')" class="tv-range-btn" style="background:transparent;border:none;color:var(--tv-color-text-secondary);cursor:pointer;padding:4px 8px;border-radius:3px;">3M</button>
              <button onclick="tvSetTimeRange('6M')" class="tv-range-btn" style="background:transparent;border:none;color:var(--tv-color-text-secondary);cursor:pointer;padding:4px 8px;border-radius:3px;">6M</button>
              <button onclick="tvSetTimeRange('YTD')" class="tv-range-btn" style="background:transparent;border:none;color:var(--tv-color-text-secondary);cursor:pointer;padding:4px 8px;border-radius:3px;">YTD</button>
              <button onclick="tvSetTimeRange('1Y')" class="tv-range-btn" style="background:transparent;border:none;color:var(--tv-color-text-secondary);cursor:pointer;padding:4px 8px;border-radius:3px;">1Y</button>
              <button onclick="tvSetTimeRange('5Y')" class="tv-range-btn" style="background:transparent;border:none;color:var(--tv-color-text-secondary);cursor:pointer;padding:4px 8px;border-radius:3px;">5Y</button>
              <button onclick="tvSetTimeRange('ALL')" class="tv-range-btn" style="background:transparent;border:none;color:var(--tv-color-text-secondary);cursor:pointer;padding:4px 8px;border-radius:3px;">All</button>
            </div>
            <div style="color:var(--tv-color-text-secondary);padding-right:8px;font-size:11px;">UTC+5:30</div>
          </div>
        </div>

        <!-- Right expanded panel (Multiple views supported) -->
        <div id="tv-right-panel" class="expanded">
          
          <!-- WATCHLIST VIEW -->
          <div id="tv-panel-watchlist" class="tv-right-content-view" style="display:flex;flex-direction:column;flex:1;min-height:0;background:var(--tv-color-bg);">
            <div class="tv-right-panel-header" style="display:flex;align-items:center;padding:12px 16px;">
              <span class="tv-right-panel-title" style="display:flex;align-items:center;gap:6px;flex:1;font-size:16px;font-weight:600;color:var(--tv-color-text-primary);cursor:pointer;">Watchlist <svg width="10" height="6" viewBox="0 0 10 6" style="fill:var(--tv-color-text-secondary);"><path d="M0 0h10L5 6z"/></svg></span>
              <div style="display:flex;gap:8px;color:var(--tv-color-text-secondary);align-items:center;">
                <div onclick="tvAddWatchlistSymbol()" title="Add Symbol" style="width:32px;height:32px;border:2px solid #2962ff;border-radius:6px;display:flex;align-items:center;justify-content:center;color:#2962ff;cursor:pointer;font-size:20px;font-weight:300;transition:all 0.1s;" onmouseover="this.style.background='rgba(41,98,255,0.05)'" onmouseout="this.style.background='transparent'">+</div>
                <div style="width:32px;height:32px;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:background 0.1s;border-radius:4px;" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'">
                  <svg width="22" height="22" viewBox="0 0 24 24" style="fill:currentColor;"><path d="M4 6h7v12H4V6zm9 0h7v5h-7V6zm0 7h7v5h-7v-5z" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>
                </div>
                <div style="width:32px;height:32px;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:background 0.1s;border-radius:4px;" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'">
                  <svg width="22" height="22" viewBox="0 0 24 24" style="fill:currentColor;"><circle cx="6" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="18" cy="12" r="1.5"/></svg>
                </div>
              </div>
            </div>
            <!-- Column Headers -->
            <div style="display:flex;font-size:12px;font-weight:400;color:var(--tv-color-text-secondary);padding:6px 16px;border-bottom:1px solid var(--tv-color-border);">
              <span style="flex:1;">Symbol</span>
              <span style="width:60px;text-align:right;">Last</span>
              <span style="width:50px;text-align:right;">Chg</span>
              <span style="width:50px;text-align:right;">Chg%</span>
            </div>
            <!-- INDICES Header (Static for now, dynamic inside tvRenderWatchlist) -->
            <div style="padding:4px 16px;background:#f8f9fb;border-bottom:1px solid var(--tv-color-border);font-size:11px;color:var(--tv-color-text-secondary);display:flex;align-items:center;gap:6px;">
               <svg width="8" height="5" viewBox="0 0 10 6" style="fill:currentColor;"><path d="M0 0h10L5 6z"/></svg> INDICES
            </div>
            <div id="tv-watchlist-list" style="flex:1;overflow-y:auto;min-height:100px;">
              <!-- Dynamic watchlist items populated by tvRenderWatchlist() -->
            </div>
            
            <!-- Details widget at bottom -->
            <div style="border-top:1px solid var(--tv-color-border);padding:16px;flex:1;overflow-y:auto;background:var(--tv-color-bg);">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:12px;">
                  <div style="width:32px;height:32px;background:#131722;border-radius:16px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:16px;font-weight:bold;">
                    <span id="tv-panel-sym-initial">A</span>
                  </div>
                  <span id="tv-panel-sym-text" style="font-size:18px;font-weight:600;color:var(--tv-color-text-primary);">AAPL</span>
                </div>
                
                <!-- Action Icons -->
                <div style="display:flex;gap:4px;color:var(--tv-color-text-secondary);">
                  <div style="width:28px;height:28px;display:flex;align-items:center;justify-content:center;cursor:pointer;border-radius:4px;" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'"><svg width="20" height="20" viewBox="0 0 24 24"><path d="M4 6h7v12H4V6zm9 0h7v5h-7V6zm0 7h7v5h-7v-5z" fill="none" stroke="currentColor" stroke-width="1.5"/></svg></div>
                  <div style="width:28px;height:28px;display:flex;align-items:center;justify-content:center;cursor:pointer;border-radius:4px;" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M16 4l4 4-11 11H5v-4L16 4z"/></svg></div>
                  <div style="width:28px;height:28px;display:flex;align-items:center;justify-content:center;cursor:pointer;border-radius:4px;" onmouseover="this.style.background='var(--tv-color-hover)'" onmouseout="this.style.background='transparent'"><svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><circle cx="6" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="18" cy="12" r="1.5"/></svg></div>
                </div>
              </div>
              
              <div style="font-size:12px;color:var(--tv-color-text-primary);margin-bottom:4px;">
                <span id="tv-panel-company">Apple Inc</span> <span style="color:var(--tv-color-text-secondary);margin:0 4px;">•</span> <span style="color:var(--tv-color-text-secondary);">NASDAQ</span>
              </div>
              <div id="tv-panel-sector" style="font-size:12px;color:var(--tv-color-text-secondary);margin-bottom:16px;">
                Electronic Technology • Telecommunications Equipment
              </div>
              
              <div style="display:flex;align-items:baseline;gap:8px;margin-bottom:6px;">
                <span id="tv-panel-price" style="font-size:32px;color:var(--tv-color-text-primary);font-weight:600;letter-spacing:-0.5px;">293.52</span>
                <span style="font-size:12px;color:var(--tv-color-text-primary);font-weight:600;">USD</span>
                <span id="tv-panel-change" style="font-size:16px;color:#089981;font-weight:500;margin-left:4px;">+6.08 +2.12%</span>
              </div>
              <div style="font-size:12px;color:#089981;margin-bottom:16px;display:flex;align-items:center;gap:6px;">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#089981;"></span> <span id="tv-panel-market-status">Market open</span>
              </div>
              
              <div style="background:#f0e6ff;border-radius:8px;padding:16px;margin-bottom:24px;display:flex;gap:12px;align-items:flex-start;position:relative;">
                <span style="color:#7e57c2;font-size:18px;line-height:1;">✦</span>
                <div id="tv-panel-news" style="font-size:13px;color:#131722;line-height:1.5;padding-right:16px;">
                  Apple named John Ternus CEO, replacing Tim Cook. After the April 20 announcement, AAPL jumped over 5%. Traders noted focus on system-level execution and stronger technical leadership under Ternus.
                </div>
                <div style="position:absolute;right:12px;top:50%;transform:translateY(-50%);color:#7e57c2;font-size:16px;">›</div>
              </div>

              <div style="font-size:15px;font-weight:600;color:var(--tv-color-text-primary);margin-bottom:16px;">Key stats</div>
              <div style="display:flex;flex-direction:column;gap:12px;font-size:13px;">
                <div style="display:flex;justify-content:space-between;color:var(--tv-color-text-secondary);"><span>Next earnings report</span><span id="tv-panel-earnings" style="color:var(--tv-color-text-primary);">—</span></div>
                <div style="display:flex;justify-content:space-between;color:var(--tv-color-text-secondary);"><span>Volume</span><span id="tv-panel-vol" style="color:var(--tv-color-text-primary);">—</span></div>
                <div style="display:flex;justify-content:space-between;color:var(--tv-color-text-secondary);"><span>Average Volume (30D)</span><span id="tv-panel-avg-vol" style="color:var(--tv-color-text-primary);">—</span></div>
                <div style="display:flex;justify-content:space-between;color:var(--tv-color-text-secondary);"><span>Market capitalization</span><span id="tv-panel-mkt-cap" style="color:var(--tv-color-text-primary);">—</span></div>
              </div>
            </div>
          </div>
          
          <!-- ALERTS VIEW -->
          <div id="tv-panel-alerts" class="tv-right-content-view" style="display:none;flex-direction:column;flex:1;min-height:0;background:var(--tv-color-bg);">
            <div class="tv-right-panel-header"><span class="tv-right-panel-title">Alerts</span></div>
            <div style="padding:40px 20px;text-align:center;color:var(--tv-color-text-secondary);font-size:13px;">
              <svg viewBox="0 0 24 24" style="width:48px;height:48px;fill:none;stroke:currentColor;stroke-width:1;margin-bottom:12px;"><path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg><br>
              No active alerts.
            </div>
          </div>
          
          <!-- DATA WINDOW VIEW -->
          <div id="tv-panel-data" class="tv-right-content-view" style="display:none;flex-direction:column;flex:1;min-height:0;background:var(--tv-color-bg);">
            <div class="tv-right-panel-header"><span class="tv-right-panel-title">Data Window</span></div>
            <div style="padding:16px;font-size:13px;color:var(--tv-color-text-primary);">
              <div id="dw-sym" style="color:#7aa8c0;font-weight:bold;margin-bottom:8px;">WIPRO</div>
              <div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="color:#4a7090;">Date</span><span id="dw-date">—</span></div>
              <div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="color:#4a7090;">Open</span><span id="dw-open">—</span></div>
              <div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="color:#4a7090;">High</span><span id="dw-high">—</span></div>
              <div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="color:#4a7090;">Low</span><span id="dw-low">—</span></div>
              <div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="color:#4a7090;">Close</span><span id="dw-close">—</span></div>
              <div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="color:#4a7090;">Volume</span><span id="dw-vol">—</span></div>
            </div>
          </div>
          
          <!-- HOTLISTS VIEW -->
          <div id="tv-panel-hotlists" class="tv-right-content-view" style="display:none;flex-direction:column;flex:1;min-height:0;background:var(--tv-color-bg);">
            <div class="tv-right-panel-header"><span class="tv-right-panel-title">Hotlists</span></div>
            <div style="padding:20px;text-align:center;color:var(--tv-color-text-secondary);font-size:13px;">No hotlists available.</div>
          </div>
          
          <!-- CALENDAR VIEW -->
          <div id="tv-panel-calendar" class="tv-right-content-view" style="display:none;flex-direction:column;flex:1;min-height:0;background:var(--tv-color-bg);">
            <div class="tv-right-panel-header"><span class="tv-right-panel-title">Economic Calendar</span></div>
            <div style="padding:20px;text-align:center;color:var(--tv-color-text-secondary);font-size:13px;">No major events today.</div>
          </div>
          
          <!-- ASTRO OVERLAYS VIEW -->
          <div id="tv-panel-astro" class="tv-right-content-view" style="display:none;flex-direction:column;flex:1;min-height:0;background:var(--tv-color-bg);font-family:Share Tech Mono,monospace;">
            <div class="tv-right-panel-header" style="display:flex;align-items:center;padding:12px 16px;border-bottom:1px solid var(--tv-color-border);">
              <span class="tv-right-panel-title" style="font-size:16px;font-weight:600;color:var(--tv-color-text-primary);">Astro Overlays</span>
            </div>
            <div style="padding:16px;overflow-y:auto;display:flex;flex-direction:column;gap:16px;">
              <div>
                <div style="font-size:11px;color:var(--tv-color-text-secondary);margin-bottom:8px;letter-spacing:0.5px;">PLANETS SELECT</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;color:var(--tv-color-text-primary);font-size:12px;">
                  <label style="display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="checkbox" id="astro-chk-Sun" checked onchange="tvTogglePlanet('Sun')"> Sun</label>
                  <label style="display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="checkbox" id="astro-chk-Moon" checked onchange="tvTogglePlanet('Moon')"> Moon</label>
                  <label style="display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="checkbox" id="astro-chk-Mercury" checked onchange="tvTogglePlanet('Mercury')"> Mercury</label>
                  <label style="display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="checkbox" id="astro-chk-Venus" checked onchange="tvTogglePlanet('Venus')"> Venus</label>
                  <label style="display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="checkbox" id="astro-chk-Mars" checked onchange="tvTogglePlanet('Mars')"> Mars</label>
                  <label style="display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="checkbox" id="astro-chk-Jupiter" checked onchange="tvTogglePlanet('Jupiter')"> Jupiter</label>
                  <label style="display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="checkbox" id="astro-chk-Saturn" checked onchange="tvTogglePlanet('Saturn')"> Saturn</label>
                  <label style="display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="checkbox" id="astro-chk-Rahu" onchange="tvTogglePlanet('Rahu')"> Rahu</label>
                  <label style="display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="checkbox" id="astro-chk-Ketu" onchange="tvTogglePlanet('Ketu')"> Ketu</label>
                </div>
              </div>
              
              <div style="border-top:1px solid var(--tv-color-border);padding-top:12px;">
                <div style="font-size:11px;color:var(--tv-color-text-secondary);margin-bottom:8px;letter-spacing:0.5px;">COORDINATE TYPE</div>
                <div style="display:flex;flex-direction:column;gap:6px;color:var(--tv-color-text-primary);font-size:12px;">
                  <label style="display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="radio" name="astro-coord" value="longitude" checked onchange="tvSetAstroCoord('longitude')"> Longitude (Zodiac Deg)</label>
                  <label style="display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="radio" name="astro-coord" value="latitude" onchange="tvSetAstroCoord('latitude')"> Latitude (Declination)</label>
                  <label style="display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="radio" name="astro-coord" value="speed" onchange="tvSetAstroCoord('speed')"> Speed (Retrograde check)</label>
                </div>
              </div>

              <div style="border-top:1px solid var(--tv-color-border);padding-top:12px;">
                <div style="font-size:11px;color:var(--tv-color-text-secondary);margin-bottom:8px;letter-spacing:0.5px;">DISPLAY PROPERTIES</div>
                <div style="display:flex;flex-direction:column;gap:6px;color:var(--tv-color-text-primary);font-size:12px;">
                  <label style="display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="checkbox" id="astro-chk-aspects" onchange="tvToggleAstroAspects()"> Show Harmonics/Aspects</label>
                  <label style="display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="checkbox" id="astro-chk-nakshatra" onchange="tvToggleAstroNakshatra()"> Nakshatra Divisions</label>
                </div>
              </div>
              
              <div style="border-top:1px solid var(--tv-color-border);padding-top:12px;display:flex;flex-direction:column;gap:8px;">
                <button onclick="tvFetchEphemeris()" style="width:100%;padding:8px;background:#2962ff;color:#fff;border:none;border-radius:4px;cursor:pointer;font-family:Share Tech Mono,monospace;font-size:12px;font-weight:600;">CALCULATE EPHEMERIS</button>
                <div id="astro-status" style="font-size:10px;color:var(--tv-color-text-secondary);text-align:center;">No ephemeris loaded.</div>
              </div>
            </div>
          </div>

          <!-- OBJECT TREE VIEW -->
          <div id="tv-panel-tree" class="tv-right-content-view" style="display:none;flex-direction:column;flex:1;min-height:0;background:var(--tv-color-bg);font-family:Share Tech Mono,monospace;">
            <div class="tv-right-panel-header" style="display:flex;align-items:center;padding:12px 16px;border-bottom:1px solid var(--tv-color-border);">
              <span class="tv-right-panel-title" style="font-size:16px;font-weight:600;color:var(--tv-color-text-primary);">Object Tree</span>
            </div>
            <div id="tv-object-tree-list" style="overflow-y:auto;flex:1;padding:8px 0;">
              <div style="padding:20px;text-align:center;color:var(--tv-color-text-secondary);font-size:13px;">No drawings on chart.</div>
            </div>
          </div>
        </div>

        <!-- Right toolbar -->
        <div class="tv-sidebar-right">
          <button class="tv-btn active" title="Watchlist and details" onclick="cwSwitchRightTab(this, 'watchlist')">
            <svg viewBox="0 0 28 28" width="22" height="22" fill="none"><path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M7.5 5A2.5 2.5 0 0 0 5 7.5v13A2.5 2.5 0 0 0 7.5 23h13a2.5 2.5 0 0 0 2.5-2.5v-13A2.5 2.5 0 0 0 20.5 5h-13zM6 7.5C6 6.672 6.672 6 7.5 6h13c.828 0 1.5.672 1.5 1.5v13c0 .828-.672 1.5-1.5 1.5h-13A1.5 1.5 0 0 1 6 20.5v-13z"/><path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M10 8h8v1H10V8zm0 3h8v1H10v-1zm0 3h8v1H10v-1z"/></svg>
          </button>
          <button class="tv-btn" title="Alerts" onclick="cwSwitchRightTab(this, 'alerts')">
            <svg viewBox="0 0 28 28" width="22" height="22" fill="none"><path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M14 23a9 9 0 1 0 0-18 9 9 0 0 0 0 18zm0-1a8 8 0 1 0 0-16 8 8 0 0 0 0 16z"/><path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M14.5 10v4.793l2.854 2.853-.708.708L13.5 15.207V10h1z"/><path fill="currentColor" d="M8 7.5l-4-4 .707-.707 4 4L8 7.5zM20 7.5l4-4-.707-.707-4 4L20 7.5z"/></svg>
          </button>
          <button class="tv-btn" title="Data Window" onclick="cwSwitchRightTab(this, 'data')">
            <svg viewBox="0 0 28 28" width="22" height="22" fill="none"><path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M14 6l9 4.5L14 15l-9-4.5L14 6zM6.5 10.5L14 14l7.5-3.5L14 7l-7.5 3.5z"/><path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M22.5 14L14 18.5 5.5 14l-.5 1 9 4.5 9-4.5-.5-1z"/><path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M22.5 17.5L14 22l-8.5-4.5-.5 1 9 4.5 9-4.5-.5-1z"/></svg>
          </button>
          <button class="tv-btn" title="Hotlists" onclick="cwSwitchRightTab(this, 'hotlists')">
            <svg viewBox="0 0 28 28" width="22" height="22" fill="none"><circle cx="14" cy="14" r="8" stroke="currentColor" stroke-width="1"/><path fill="currentColor" d="M14 10L12 14H16L14 18V10Z"/></svg>
          </button>
          <button class="tv-btn" title="Calendar" onclick="cwSwitchRightTab(this, 'calendar')">
            <svg viewBox="0 0 28 28" width="22" height="22" fill="none"><path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M7 8v1h14V8H7zm0 2h14v11H7V10zm-1-3h16v15H6V7zm11-1V4h1v2h-1zm-9 0V4h1v2H8z"/></svg>
          </button>
          <button class="tv-btn" title="Astro Overlays" onclick="cwSwitchRightTab(this, 'astro')">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M12 3v6M12 15v6M3 12h6M15 12h6" stroke="currentColor" stroke-width="1.5"/></svg>
          </button>
          <div style="flex:1;"></div>
          <button class="tv-btn" title="Object Tree" onclick="cwSwitchRightTab(this, 'tree')">
            <svg viewBox="0 0 28 28" width="22" height="22" fill="none"><path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M10 7H7v3h3V7zm-4-1h5v5H6V6zm15 1h-3v3h3V7zm-4-1h5v5h-5V6zM10 18H7v3h3v-3zm-4-1h5v5H6v-5zm15 1h-3v3h3v-3zm-4-1h5v5h-5v-5z"/><path fill="currentColor" d="M14 9h2v1h-2V9zM14 20h2v1h-2v-1zM9 14h1v2H9v-2zM20 14h1v2h-1v-2z"/><path fill="currentColor" d="M12 14h4v1h-4v-1z"/></svg>
          </button>
          <button class="tv-btn" title="Help" onclick="alert('Help center coming soon!')">
            <svg viewBox="0 0 28 28" width="22" height="22" fill="none"><path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M14 23a9 9 0 1 0 0-18 9 9 0 0 0 0 18zm0-1a8 8 0 1 0 0-16 8 8 0 0 0 0 16z"/><path fill="currentColor" d="M14.5 19v-2h-1v2h1zm-2.8-5.3c0-1.8 1.4-2.8 2.8-2.8s2.8 1 2.8 2.3c0 .8-.5 1.5-1.1 2.1-.5.5-.9 1-.9 1.7v.5h-1v-.5c0-1.1.5-1.7 1-2.2.5-.4 1-.9 1-1.6 0-.8-.8-1.3-1.8-1.3-1.1 0-1.8.8-1.8 1.8h-1z"/></svg>
          </button>
        </div>
      </div>`;
    document.body.appendChild(shell);

    // ── Restore full TV state from sessionStorage ──
    TV.data           = state.data;
    TV.chartType      = state.chartType || 'candle';
    TV.indicators     = Object.assign({sma:false,ema:false,bb:false,vol:true,rsi:false,macd:false,adx:false,sr:false,astro:false}, state.indicators);
    TV.params         = Object.assign({smaP:[20,50,200],emaP:[9,21,50],bbP:20,bbStd:2,rsiP:14,rsiOB:70,rsiOS:30,macdFast:12,macdSlow:26,macdSig:9,adxP:14}, state.params);
    TV.params.smaP    = [...(state.params.smaP || [20,50,200])];
    TV.params.emaP    = [...(state.params.emaP || [9,21,50])];
    TV.view           = {...state.view};
    TV.yRange         = {min:null, max:null};
    TV.drawings       = [];
    TV.drawState      = null;
    TV.selectedDrawing = null;
    TV._eventsAttached = false;
    TV._resizeObserver = null;

    // Sync action tools buttons highlight state on load
    if (TV.magnet) {
      const btn = document.getElementById('btn-magnet');
      if (btn) { btn.style.color = 'var(--cyan)'; btn.style.background = 'rgba(0,212,255,0.12)'; }
    }
    if (TV.stayInDrawingMode) {
      const btn = document.getElementById('btn-stay-drawing');
      if (btn) { btn.style.color = 'var(--cyan)'; btn.style.background = 'rgba(0,212,255,0.12)'; }
    }
    if (TV.lockDrawings) {
      const btn = document.getElementById('btn-lock-drawings');
      if (btn) { btn.style.color = 'var(--cyan)'; btn.style.background = 'rgba(0,212,255,0.12)'; }
    }

    // Sync chart type label in dropdown
    const _ctLabels = {candle:'🕯 CANDLE', line:'📈 LINE', bar:'▮▮ OHLC'};
    const _ctLbl = document.getElementById('ct-label');
    if (_ctLbl) _ctLbl.textContent = _ctLabels[TV.chartType] || TV.chartType.toUpperCase();

    // Set sym label from data
    const _symLbl = document.getElementById('tv-sym-label');
    if (_symLbl) _symLbl.textContent = state.sym || (TV.data.dates ? TV.data.dates.length + ' bars' : '');

    // Show/hide sub-panels based on indicators state
    const _subMap = {vol:'sub-panel-vol', rsi:'sub-panel-rsi', macd:'sub-panel-macd', adx:'sub-panel-adx'};
    Object.keys(_subMap).forEach(k => {
      const el = document.getElementById(_subMap[k]);
      if (el) el.style.display = TV.indicators[k] ? 'block' : 'none';
    });

    // Calculate correct mainH: window height minus toolbar (~32px) minus sub-panels minus infobar (~26px)
    function _calcMainH() {
      const subH = Object.keys(_subMap).reduce((sum, k) => {
        if (!TV.indicators[k]) return sum;
        const c = document.getElementById(k+'-canvas');
        return sum + (c ? (c.offsetHeight||( k==='vol'?80:100)) : (k==='vol'?80:100));
      }, 0);
      const indRow = document.getElementById('tv-ind-values');
      const indH = (indRow && indRow.style.display !== 'none') ? indRow.offsetHeight : 0;
      return Math.max(200, window.innerHeight - 32 - 26 - indH - subH - 2);
    }

    // Draw after browser has laid out the shell
    // Store raw daily data before any aggregation
    TV._rawDailyData = TV.data;
    TV.cwTimeframe = '1D';
    // Sync button label to match actual state
    const _tfLblInit = document.getElementById('cw-tf-label');
    if (_tfLblInit) _tfLblInit.textContent = '1D';

    requestAnimationFrame(() => {
      TV.mainH = _calcMainH();
      // Apply default 1D view: last 252 bars
      const total = TV.data.closes.length;
      TV.view.start = Math.max(0, total - 252);
      TV.view.end   = total;
      TV.yRange     = {min:null, max:null};
      tvRedraw();
      tvSetupInteraction();
    });

    // Re-calc on resize
    window.addEventListener('resize', () => {
      if (TV.data) { TV.mainH = _calcMainH(); tvRedraw(); }
    });

    // ── Timeframe selector ────────────────────────────────────────────

    window.cwToggleTfMenu = function() {
      const m = document.getElementById('cw-tf-menu');
      if (!m) return;
      m.style.display = m.style.display === 'none' ? 'block' : 'none';
      if (m.style.display === 'block') {
        setTimeout(() => {
          const close = e => {
            const btn = document.getElementById('cw-tf-btn');
            if (btn && !btn.contains(e.target) && !m.contains(e.target)) {
              m.style.display = 'none';
              document.removeEventListener('click', close);
            }
          };
          document.addEventListener('click', close);
        }, 10);
      }
    };

    // ── OHLCV aggregation: club daily bars into weekly/monthly candles ──
    function cwAggregate(rawData, groupBy) {
      // groupBy: 'D'=daily, 'W'=weekly, 'M'=monthly, '3M'=quarterly, '6M'=semi-annual, '1Y'=annual
      if (groupBy === 'D') return rawData; // no change
      const {dates, opens, highs, lows, closes, volumes} = rawData;
      const N = dates.length;
      if (!N) return rawData;

      // Determine group key for each bar
      function getKey(dateStr) {
        const dt = new Date(dateStr);
        const y = dt.getFullYear(), m = dt.getMonth(), d = dt.getDate();
        if (groupBy === 'W') {
          // ISO week: Monday = start of week
          const day = dt.getDay(); // 0=Sun
          const diff = (day === 0 ? -6 : 1) - day;
          const mon = new Date(dt); mon.setDate(d + diff);
          return mon.getFullYear()+'-'+String(mon.getMonth()+1).padStart(2,'0')+'-'+String(mon.getDate()).padStart(2,'0');
        } else if (groupBy === 'M') {
          return y+'-'+String(m+1).padStart(2,'0');
        } else if (groupBy === '3M') {
          return y+'-Q'+Math.floor(m/3);
        } else if (groupBy === '6M') {
          return y+'-H'+(m<6?1:2);
        } else if (groupBy === '1Y') {
          return String(y);
        }
        return dateStr;
      }

      // Group bars
      const groups = {};
      const groupOrder = [];
      for (let i=0; i<N; i++) {
        const key = getKey(dates[i]);
        if (!groups[key]) {
          groups[key] = {date:dates[i], open:opens[i], high:highs[i], low:lows[i], close:closes[i], volume:volumes[i]||0};
          groupOrder.push(key);
        } else {
          const g = groups[key];
          g.high   = Math.max(g.high, highs[i]);
          g.low    = Math.min(g.low, lows[i]);
          g.close  = closes[i]; // last close of period
          g.volume += (volumes[i]||0);
        }
      }

      return {
        dates:   groupOrder.map(k => groups[k].date),
        opens:   groupOrder.map(k => groups[k].open),
        highs:   groupOrder.map(k => groups[k].high),
        lows:    groupOrder.map(k => groups[k].low),
        closes:  groupOrder.map(k => groups[k].close),
        volumes: groupOrder.map(k => groups[k].volume),
        sr:      rawData.sr,
        currentPrice: rawData.currentPrice,
        _aggregated: groupBy,
        _rawData: rawData // keep reference to restore daily
      };
    }

    // Store the original daily data so we can switch back
    TV._rawDailyData = null;

    window.cwSetTimeframe = function(tf, label) {
      TV.cwTimeframe = tf;
      // Update button label
      const lbl = document.getElementById('cw-tf-label');
      if (lbl) lbl.textContent = tf;
      // Close menu
      const m = document.getElementById('cw-tf-menu');
      if (m) m.style.display = 'none';
      // Highlight active
      document.querySelectorAll('#cw-tf-menu div[onclick]').forEach(d => {
        const isActive = d.getAttribute('onclick') && d.getAttribute('onclick').includes("'"+tf+"'");
        d.style.color = isActive ? '#00d4ff' : '#c8e0ed';
        d.style.fontWeight = isActive ? '700' : 'normal';
      });

      if (!TV.data) return;

      // Restore to daily data first (always aggregate from raw)
      const rawData = TV._rawDailyData || TV.data;
      if (!TV._rawDailyData) TV._rawDailyData = TV.data;

      // Determine aggregation period
      let groupBy = 'D';
      if      (tf === '1W') groupBy = 'W';
      else if (tf === '1M') groupBy = 'M';
      else if (tf === '3M') groupBy = '3M';
      else if (tf === '6M') groupBy = '6M';
      else if (tf === '1Y') groupBy = '1Y';

      // Aggregate data
      const aggData = cwAggregate(rawData, groupBy);
      TV.data = aggData;

      const total = aggData.closes.length;
      // 1D: show last 252 bars (1 year) — user can pan left for history
      // Aggregated (W/M/3M/6M/1Y): show all bars (there aren't many)
      // Set sensible default view per timeframe
      // D=last 252 bars(1yr), W=last 52(1yr), M=last 36(3yr), 3M=all, 6M=all, 1Y=all
      if (groupBy === 'D') {
        TV.view.start = Math.max(0, total - 252);
      } else if (groupBy === 'W') {
        TV.view.start = Math.max(0, total - 52);  // last 1 year of weekly
      } else if (groupBy === 'M') {
        TV.view.start = Math.max(0, total - 36);  // last 3 years of monthly
      } else {
        TV.view.start = 0; // 3M/6M/1Y: show all
      }
      TV.view.end = total;
      TV.yRange     = {min:null, max:null};
      TV.drawings   = []; // clear drawings (they won't map correctly after aggregation)
      TV.measureResult = null;
      TV.mainH = _calcMainH();
      tvRedraw();
    };

    // ── Symbol search for CW ──
    // Populate symbol list from sessionStorage state or fetch
    const _allSyms = (function() {
      try { return JSON.parse(sessionStorage.getItem('allSymbols') || '[]'); } catch(e) { return []; }
    })();

    // Symbol dropdown state
    let _cwSelectedIdx = -1;
    let _cwMatches = [];

    window.cwSymKeyNav = function(e) {
      const box = document.getElementById('cw-sym-suggestions');
      const rows = box ? box.querySelectorAll('.cw-sym-row') : [];
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        _cwSelectedIdx = Math.min(_cwSelectedIdx + 1, rows.length - 1);
        cwHighlightSym(rows);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        _cwSelectedIdx = Math.max(_cwSelectedIdx - 1, -1);
        cwHighlightSym(rows);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (_cwSelectedIdx >= 0 && rows[_cwSelectedIdx]) {
          const sym = rows[_cwSelectedIdx].dataset.sym;
          if (sym) cwLoadSymbol(sym);
        } else {
          const inp = document.getElementById('cw-sym-input');
          if (inp) cwLoadSymbol(inp.value.trim().toUpperCase());
        }
      } else if (e.key === 'Escape') {
        if (box) box.style.display = 'none';
        _cwSelectedIdx = -1;
      }
    };

    function cwHighlightSym(rows) {
      rows.forEach((r, i) => {
        r.style.background = i === _cwSelectedIdx ? 'rgba(0,212,255,0.15)' : 'transparent';
        r.style.color = i === _cwSelectedIdx ? '#00d4ff' : '#c8e0ed';
      });
      if (_cwSelectedIdx >= 0 && rows[_cwSelectedIdx]) {
        rows[_cwSelectedIdx].scrollIntoView({block:'nearest'});
      }
    }

    // Fetch full instrument list if _allSyms is empty
    async function _ensureSymList() {
      if (_allSyms.length > 0) return;
      try {
        const r = await fetch('/api/all_symbols');
        const d = await r.json();
        const syms = [...(d.indices||[]), ...(d.equities||[]), ...(d.commodities||[])];
        _allSyms.push(...syms.map(s => typeof s==='object' ? s.symbol : s));
        try { sessionStorage.setItem('allSymbols', JSON.stringify(_allSyms)); } catch(e) {}
      } catch(e) {}
    }
    _ensureSymList();

    window.cwFilterSymSuggestions = async function(q) {
      const box = document.getElementById('cw-sym-suggestions');
      if (!box) return;
      _cwSelectedIdx = -1;
      if (!q || q.length < 1) { box.style.display='none'; return; }
      await _ensureSymList();
      const qu = q.toUpperCase();
      // Match by starts-with first, then contains
      const startsWith = _allSyms.filter(s => s.toUpperCase().startsWith(qu));
      const contains   = _allSyms.filter(s => !s.toUpperCase().startsWith(qu) && s.toUpperCase().includes(qu));
      const matches = [...startsWith, ...contains].slice(0, 15);
      if (!matches.length) { box.style.display='none'; return; }
      box.innerHTML = matches.map((s,i) =>
        `<div class="cw-sym-row" data-sym="${s}" onclick="cwLoadSymbol('${s}')"
          style="padding:7px 12px;font-family:Share Tech Mono,monospace;font-size:0.72rem;
          cursor:pointer;color:#c8e0ed;border-bottom:1px solid rgba(255,255,255,0.04);
          display:flex;align-items:center;gap:8px;"
          onmouseover="this.style.background='rgba(0,212,255,0.08)'"
          onmouseout="if(${i}!==_cwSelectedIdx)this.style.background='transparent'">
          <span style="color:#00d4ff;font-weight:700;min-width:80px;">${s}</span>
        </div>`
      ).join('');
      box.style.display = 'block';
      // Close on outside click
      setTimeout(() => {
        const close = e => {
          const inp2 = document.getElementById('cw-sym-input');
          if (!box.contains(e.target) && e.target!==inp2) {
            box.style.display='none'; _cwSelectedIdx=-1;
            document.removeEventListener('mousedown', close);
          }
        };
        document.addEventListener('mousedown', close);
      }, 10);
    };

    window.cwLoadSymbol = async function(sym) {
      if (!sym) return;
      const inp = document.getElementById('cw-sym-input');
      const spin = document.getElementById('cw-sym-loading');
      const box = document.getElementById('cw-sym-suggestions');
      if (inp) inp.value = sym;
      if (box) box.style.display = 'none';
      if (spin) spin.style.display = 'inline';
      try {
        // Fetch price first
        // Use correct API URL format — /api/endpoint?params
        const today2 = new Date().toISOString().slice(0,10);
        const pxResp = await fetch('/api/price?symbol=' + sym + '&date=' + today2);
        if (!pxResp.ok) throw new Error('HTTP ' + pxResp.status);
        const px = await pxResp.json();
        if (px.error) throw new Error(px.error);
        const price = px.close || px.price || 0;
        // Fetch full quant data
        const qUrl = '/api/quant?symbol=' + sym + '&date=' + today2 + (price ? '&price=' + price : '');
        const resp = await fetch(qUrl);
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const d = await resp.json();
        if (d.error) throw new Error(d.error);
        const chart = d.chart || {};
        const sr = d.support_resistance || {};
        const cur = sr.current_price || d.current_price || price;
        const closes = chart.closes || [];
        const _rawOpens = chart.opens || [];
        const opens = (_rawOpens.length===closes.length) ? _rawOpens : closes.map((c,i)=>i>0?closes[i-1]:c);
        TV.data = {
          dates: chart.dates||[], opens, highs: chart.highs||closes.map(c=>c*1.005),
          lows: chart.lows||closes.map(c=>c*0.995), closes, volumes: chart.volumes||closes.map(()=>0),
          sr, currentPrice: cur
        };
        TV.yRange = {min:null, max:null};
        TV.drawings = []; TV.drawState = null; TV.selectedDrawing = null;
        TV.measureResult = null; TV.ewAnalysis = null;
        TV._rawDailyData = TV.data; // save raw daily for timeframe switching
        TV.cwTimeframe = '1D'; // reset to daily on new symbol
        const tfLbl = document.getElementById('cw-tf-label');
        if (tfLbl) tfLbl.textContent = '1D';
        const total = closes.length;
        TV.view.start = Math.max(0, total-252); TV.view.end = total;
        // Update sym label in infobar
        const lbl = document.getElementById('tv-sym-label');
        if (lbl) lbl.textContent = sym;
        
        // ── Update Right Panel (Watchlist Details) ──
        const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        setTxt('tv-panel-sym-initial', sym.charAt(0).toUpperCase());
        setTxt('tv-panel-sym-text', sym);
        setTxt('tv-panel-sector', d.sector || 'EQUITY');
        setTxt('tv-panel-price', Number(price).toLocaleString('en-IN', {minimumFractionDigits: 2}));
        
        const chgVal = px.change_pct || 0;
        const chgCol = chgVal >= 0 ? '#26a69a' : '#ef5350';
        const chgStr = (chgVal >= 0 ? '+' : '') + chgVal.toFixed(2) + '%';
        const chgEl = document.getElementById('tv-panel-change');
        if (chgEl) { chgEl.textContent = chgStr; chgEl.style.color = chgCol; }
        
        const now = new Date();
        setTxt('tv-panel-update-time', 'Last update at ' + now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}));
        
        const fmtVol = (v) => {
            if (!v) return '—';
            if (v >= 1e7) return (v/1e7).toFixed(2) + 'Cr';
            if (v >= 1e5) return (v/1e5).toFixed(2) + 'L';
            if (v >= 1000) return (v/1000).toFixed(1) + 'K';
            return v.toString();
        };
        const curVol = chart.volumes && chart.volumes.length ? chart.volumes[chart.volumes.length-1] : 0;
        setTxt('tv-panel-vol', fmtVol(curVol));
        setTxt('tv-panel-avg-vol', (d.regime && d.regime.metrics && d.regime.metrics.annual_vol_pct) ? d.regime.metrics.annual_vol_pct + '%' : '—');
        
        // Data Window default
        setTxt('dw-sym', sym);

        // ── Update browser URL and tab title ──
        const chg = px.change_pct != null ? (px.change_pct>=0?'+':'')+px.change_pct.toFixed(2)+'%' : '';
        document.title = 'Vprofitables · ' + sym + (chg ? ' ' + chg : '');
        // Update URL without reloading — shows symbol in address bar
        const newUrl = '/?chartWindow=1&symbol=' + encodeURIComponent(sym);
        window.history.replaceState({sym}, document.title, newUrl);

        // Update sessionStorage for next expand
        try {
          const saved = JSON.parse(sessionStorage.getItem('tvChartState')||'{}');
          saved.sym = sym; saved.data = TV.data; saved.view = TV.view;
          sessionStorage.setItem('tvChartState', JSON.stringify(saved));
        } catch(e) {}
        TV.mainH = _calcMainH();
        tvRedraw(); tvSetupInteraction();
      } catch(e) {
        alert('Failed to load ' + sym + ': ' + e.message);
      } finally {
        if (spin) spin.style.display = 'none';
      }
    };

    // Set initial symbol in input + URL/title
    const _symInp = document.getElementById('cw-sym-input');
    if (_symInp && state.sym) _symInp.value = state.sym;
    if (state.sym) {
      document.title = 'Vprofitables · ' + state.sym;
      window.history.replaceState({sym:state.sym}, document.title,
        '/?chartWindow=1&symbol=' + encodeURIComponent(state.sym));
    }

    // ── Sub-panel resize ──
    let _resizeState = null;
    window.cwStartResize = function(e, panelId) {
      e.preventDefault();
      const cvs = document.getElementById(panelId+'-canvas');
      if (!cvs) return;
      _resizeState = { panelId, startY: e.clientY, startH: cvs.offsetHeight };
      document.body.style.cursor = 'row-resize';
      document.body.style.userSelect = 'none';
    };
    document.addEventListener('mousemove', function(e) {
      if (!_resizeState) return;
      const delta = e.clientY - _resizeState.startY;
      const newH = Math.max(40, Math.min(300, _resizeState.startH + delta));
      const cvs = document.getElementById(_resizeState.panelId+'-canvas');
      if (cvs) { cvs.style.height = newH+'px'; cvs.height = newH; }
      TV.mainH = _calcMainH();
      tvRedraw();
    });
    document.addEventListener('mouseup', function() {
      if (_resizeState) {
        _resizeState = null;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        TV.mainH = _calcMainH();
        tvRedraw();
      }
    });

    // Also hook tvToggleIndFromPopup to update sub-panel visibility and recalc height in CW
    const _origToggle = window.tvToggleIndFromPopup;
    window.tvToggleIndFromPopup = function(id) {
      _origToggle(id);
      const el = document.getElementById(_subMap[id]);
      if (el) el.style.display = TV.indicators[id] ? 'block' : 'none';
      TV.mainH = _calcMainH();
      tvRedraw();
    };

    // ── Watchlist Management ──
    const defaultWatchlist = ['NIFTY', 'BANKNIFTY', 'CNXIT'];
    window.tvGetWatchlist = function() {
        try {
            const stored = localStorage.getItem('tvWatchlist');
            if (stored) return JSON.parse(stored);
        } catch(e) {}
        return defaultWatchlist;
    };
    window.tvSaveWatchlist = function(list) {
        localStorage.setItem('tvWatchlist', JSON.stringify(list));
    };
    window.tvAddWatchlistSymbol = function() {
        const sym = prompt("Enter symbol to add to Watchlist:");
        if (sym && sym.trim()) {
            const cleanSym = sym.trim().toUpperCase();
            const list = tvGetWatchlist();
            if (!list.includes(cleanSym)) {
                list.push(cleanSym);
                tvSaveWatchlist(list);
                tvRenderWatchlist();
            }
        }
    };
    window.tvRemoveWatchlistSymbol = function(e, sym) {
        e.stopPropagation();
        let list = tvGetWatchlist();
        list = list.filter(s => s !== sym);
        tvSaveWatchlist(list);
        tvRenderWatchlist();
    };
    window.tvRenderWatchlist = async function() {
        const listEl = document.getElementById('tv-watchlist-list');
        if (!listEl) return;
        const list = tvGetWatchlist();
        
        const today2 = new Date().toISOString().slice(0,10);
        const reqs = list.map(sym => fetch('/api/price?symbol=' + sym + '&date=' + today2).then(r=>r.json()).catch(()=>null));
        const resps = await Promise.all(reqs);
        
        let html = '';
        list.forEach((sym, i) => {
            const px = resps[i] || {};
            const last = px.close || px.price || 0;
            const chgVal = px.change_pct || 0;
            const chgCol = chgVal >= 0 ? '#26a69a' : '#ef5350';
            const chgAbs = (last * chgVal / 100).toFixed(2);
            
            // Generate icon
            let iconHtml = `<span style="display:inline-block;width:16px;height:16px;border-radius:8px;background:#3a5a70;color:#fff;text-align:center;line-height:16px;font-size:0.5rem;margin-right:6px;vertical-align:text-top;">${sym.charAt(0)}</span>`;
            if (sym === 'NIFTY') iconHtml = `<span style="display:inline-block;width:16px;height:16px;border-radius:8px;background:#3a5a70;color:#fff;text-align:center;line-height:16px;font-size:0.5rem;margin-right:6px;vertical-align:text-top;">50</span>`;
            else if (sym === 'BANKNIFTY') iconHtml = `<span style="display:inline-block;width:16px;height:16px;border-radius:8px;background:#1a3a60;color:#fff;text-align:center;line-height:16px;font-size:0.5rem;margin-right:6px;vertical-align:text-top;font-family:sans-serif;">🏛</span>`;
            else if (sym === 'CNXIT') iconHtml = `<span style="display:inline-block;width:16px;height:16px;border-radius:8px;background:#26a69a;color:#fff;text-align:center;line-height:16px;font-size:0.5rem;margin-right:6px;vertical-align:text-top;font-family:sans-serif;">T</span>`;

            html += `
              <div style="display:flex;padding:8px 16px;font-size:0.75rem;cursor:pointer;position:relative;" class="wl-item" onmouseover="this.style.background='rgba(255,255,255,0.03)';this.querySelector('.wl-del').style.display='block'" onmouseout="this.style.background='transparent';this.querySelector('.wl-del').style.display='none'" onclick="cwLoadSymbol('${sym}')">
                <span class="wl-del" title="Remove" style="display:none;position:absolute;left:4px;color:#ef5350;font-size:0.9rem;line-height:16px;" onclick="tvRemoveWatchlistSymbol(event, '${sym}')">×</span>
                <span style="flex:1;color:#c8e0ed;font-weight:700;">${iconHtml}${sym}</span>
                <span style="width:60px;text-align:right;color:#c8e0ed;">${last ? last.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '—'}</span>
                <span style="width:50px;text-align:right;color:${chgCol};">${(chgVal>=0?'+':'')}${last ? chgAbs : '—'}</span>
                <span style="width:50px;text-align:right;color:${chgCol};">${(chgVal>=0?'+':'')}${chgVal.toFixed(2)}%</span>
              </div>
            `;
        });
        listEl.innerHTML = html;
    };
    
    // Initial render
    tvRenderWatchlist();

  });
})();

// ════════════════════════════════════════════════════════════════════
// INSTITUTIONAL / BIG PLAYERS — Fundamentals page card
// ════════════════════════════════════════════════════════════════════

async function loadInstitutionalData(sym) {
  const loadEl    = document.getElementById('fund-inst-loading');
  const contentEl = document.getElementById('fund-inst-content');
  const emptyEl   = document.getElementById('fund-inst-empty');
  if (!loadEl) return;

  loadEl.style.display    = 'flex';
  contentEl.style.display = 'none';
  emptyEl.style.display   = 'none';

  try {
    const d = await api('institutional', { symbol: sym, days: 730 });
    loadEl.style.display = 'none';

    // Show content if ANY data available — volume anomalies always present after volume-refresh
    const hasData = d.has_deals || d.has_shareholding || d.has_anomalies ||
                    (d.anomalies && d.anomalies.length > 0);
    if (!hasData) {
      emptyEl.style.display = 'block';
      emptyEl.innerHTML = `
        <b style="color:var(--cyan);">No institutional data yet.</b><br><br>
        Run these commands to populate:<br>
        <code style="color:var(--gold);">python core/fetch_institutional.py --volume-refresh</code>
        &nbsp;&nbsp;(volume anomalies — instant, uses your price history)<br>
        <code style="color:var(--gold);">python core/fetch_institutional.py --bulk-only --days 30</code>
        &nbsp;&nbsp;(bulk/block deals from NSE)`;
      return;
    }
    contentEl.style.display = 'block';
    contentEl.innerHTML = _renderInstCard(d);
  } catch(e) {
    if (loadEl) loadEl.style.display = 'none';
    if (emptyEl) {
      emptyEl.style.display = 'block';
      emptyEl.innerHTML = `
        <b style="color:var(--red);">⚠ Error loading institutional data: ${e.message}</b><br><br>
        Fix: Run <code style="color:var(--cyan);">python db_patch.py</code> then restart the app.<br>
        Then: <code style="color:var(--cyan);">python core/fetch_institutional.py --volume-refresh</code>`;
    }
  }
}

function _renderInstCard(d) {
  let html = '';

  // ── Shareholding trend ─────────────────────────────────────────
  if (d.shareholding && d.shareholding.length) {
    const sh     = d.shareholding;
    const latest = sh[sh.length - 1];
    const signal = d.sh_signal || 'NEUTRAL';
    const sigCol = signal.includes('ACCUM') || signal.includes('INC') ? 'var(--green)'
                 : signal.includes('RED')  || signal.includes('EXIT') ? 'var(--red)'
                 : signal.includes('DII')  ? 'var(--purple)' : 'var(--dim)';
    const sigIcon= signal.includes('ACCUM') || signal.includes('INC') ? '▲'
                 : signal.includes('RED')  || signal.includes('EXIT') ? '▼' : '●';

    html += `<div style="margin-bottom:18px;">
      <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--purple);letter-spacing:2px;margin-bottom:10px;">
        📊 QUARTERLY SHAREHOLDING PATTERN
        <span style="margin-left:10px;color:${sigCol};">${sigIcon} ${signal.replace(/_/g,' ')}</span>
      </div>

      <!-- 4 stat boxes -->
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px;">
        ${[
          {lbl:'FII / FPI',    val:latest.fii_pct,      chg:latest.fii_change, col:'var(--cyan)'},
          {lbl:'DII (MF+Ins)', val:latest.dii_pct,      chg:latest.dii_change, col:'var(--purple)'},
          {lbl:'PROMOTER',     val:latest.promoter_pct, chg:0,                 col:'var(--gold)'},
          {lbl:'RETAIL/OTHER', val:latest.retail_pct,   chg:0,                 col:'var(--dim)'},
        ].map(item => {
          const chgVal = item.chg || 0;
          const chgStr = chgVal !== 0
            ? `<div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;
                color:${chgVal>0?'var(--green)':'var(--red)'};">
                ${chgVal>0?'▲':'▼'} ${Math.abs(chgVal).toFixed(2)}% QoQ
               </div>` : '';
          return `<div style="background:var(--p2);border:1px solid var(--border);padding:10px;text-align:center;">
            <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);letter-spacing:1px;margin-bottom:4px;">${item.lbl}</div>
            <div style="font-family:Orbitron,sans-serif;font-size:1.05rem;font-weight:700;color:${item.col};">${(item.val||0).toFixed(2)}%</div>
            ${chgStr}
          </div>`;
        }).join('')}
      </div>

      <!-- Stacked ownership bar -->
      <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;margin-bottom:5px;">OWNERSHIP BREAKDOWN</div>
      <div style="display:flex;height:18px;border-radius:2px;overflow:hidden;margin-bottom:4px;">
        ${[
          {val:latest.fii_pct,col:'#00d4ff',lbl:'FII'},
          {val:latest.dii_pct,col:'#cc88ff',lbl:'DII'},
          {val:latest.promoter_pct,col:'#ffcc00',lbl:'PROMO'},
          {val:latest.retail_pct,col:'#3a5a70',lbl:'RETAIL'},
        ].map(s=>`<div style="flex:${(s.val||0).toFixed(2)};background:${s.col};min-width:${(s.val||0)>0?'2px':'0'};"></div>`).join('')}
      </div>
      <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px;">
        ${[
          {val:latest.fii_pct,col:'#00d4ff',lbl:'FII'},
          {val:latest.dii_pct,col:'#cc88ff',lbl:'DII'},
          {val:latest.promoter_pct,col:'#ffcc00',lbl:'PROMOTER'},
          {val:latest.retail_pct,col:'#3a5a70',lbl:'RETAIL'},
        ].map(s=>`<span style="font-family:Share Tech Mono,monospace;font-size:0.6rem;">
          <span style="display:inline-block;width:8px;height:8px;background:${s.col};border-radius:50%;margin-right:3px;vertical-align:middle;"></span>
          <span style="color:${s.col};">${s.lbl}</span> <span style="color:var(--t2);">${(s.val||0).toFixed(1)}%</span>
        </span>`).join('')}
      </div>`;

    // FII trend chart — only if >1 quarter
    if (sh.length > 1) {
      const recent = sh.slice(-8);
      const maxFii = Math.max(...recent.map(r => r.fii_pct||0), 0.1);
      const minFii = Math.min(...recent.map(r => r.fii_pct||0), maxFii);
      const range  = maxFii - minFii || 0.1;

      html += `<div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;margin-bottom:6px;">
        FII HOLDING TREND — last ${recent.length} quarters
        <span style="margin-left:10px;color:${sigCol};">${sigIcon} ${(latest.fii_change||0)>0?'+':''}${(latest.fii_change||0).toFixed(2)}% latest change</span>
      </div>
      <div style="display:flex;gap:4px;align-items:flex-end;height:60px;padding-bottom:2px;margin-bottom:4px;">`;

      recent.forEach((r, i) => {
        const pct   = Math.round(((r.fii_pct||0) - minFii) / range * 100);
        const barH  = Math.max(6, Math.round(pct * 0.5)) + 6;
        const chg   = r.fii_change || 0;
        const barCol = chg > 0.1  ? '#00d4ff'
                     : chg < -0.1 ? '#ff3355' : '#3a5a70';
        html += `<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;min-width:0;">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.5rem;color:${barCol};white-space:nowrap;">
            ${(r.fii_pct||0).toFixed(1)}%
          </div>
          <div style="width:100%;background:${barCol};opacity:0.8;height:${barH}px;border-radius:2px 2px 0 0;
            border:1px solid ${barCol}55;min-height:4px;"></div>
        </div>`;
      });

      html += `</div>
      <div style="display:flex;gap:4px;">
        ${recent.map(r=>`<div style="flex:1;font-family:Share Tech Mono,monospace;font-size:0.48rem;color:var(--dim);
          text-align:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;">
          ${(r.quarter||'').replace(/20(\d\d)/,'$1')}
        </div>`).join('')}
      </div>`;
    } else {
      html += `<div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);padding:8px 0;">
        Run shareholding fetch to see multi-quarter trend:
        <code style="color:var(--cyan);">python core/fetch_institutional.py --shareholding-only</code>
      </div>`;
    }

    html += `</div>`;
  }

  // ── Recent bulk/block deals ────────────────────────────────────
  if (d.deals && d.deals.length) {
    // Group by date for summary header
    const byDate = {};
    d.deals.forEach(dl => {
      if (!byDate[dl.deal_date]) byDate[dl.deal_date] = {buy:0,sell:0,count:0};
      if (dl.deal_type==='BUY') byDate[dl.deal_date].buy += (dl.quantity||0);
      else byDate[dl.deal_date].sell += (dl.quantity||0);
      byDate[dl.deal_date].count++;
    });
    const totalVal = d.deals.reduce((s,dl)=>s+(dl.quantity||0)*(dl.price||0),0);

    html += `<div style="margin-bottom:16px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--gold);letter-spacing:2px;">
          📦 BULK / BLOCK DEALS — ${d.deals.length} TRANSACTIONS
        </div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);">
          Value: <span style="color:var(--cyan);">₹${(totalVal/1e7).toFixed(1)} Cr</span>
        </div>
      </div>
      <!-- NSE-style table matching official website -->
      <div style="border:1px solid var(--border);overflow:hidden;">
        <div style="display:grid;grid-template-columns:88px 70px 1fr 1fr 52px 100px 80px 52px;
             background:rgba(0,0,0,0.4);padding:5px 8px;
             font-family:Share Tech Mono,monospace;font-size:0.52rem;color:var(--dim);letter-spacing:1px;">
          <div>DATE</div>
          <div>SYMBOL</div>
          <div>SECURITY NAME</div>
          <div>CLIENT</div>
          <div>B/S</div>
          <div>QTY TRADED</div>
          <div>PRICE ₹</div>
          <div>KIND</div>
        </div>
        ${d.deals.slice(0,20).map(dl => {
          const buy = dl.deal_type === 'BUY';
          const qty = (dl.quantity||0).toLocaleString('en-IN');
          const price = (dl.price||0).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2});
          const val = ((dl.quantity||0)*(dl.price||0)/1e7).toFixed(2);
          return `<div style="display:grid;grid-template-columns:88px 70px 1fr 1fr 52px 100px 80px 52px;
               padding:5px 8px;border-top:1px solid var(--border);
               background:${buy?'rgba(0,255,136,0.02)':'rgba(255,51,85,0.02)'};
               align-items:center;">
            <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);">${dl.deal_date}</div>
            <div style="font-family:Orbitron,sans-serif;font-size:0.62rem;color:var(--cyan);font-weight:700;">${dl.symbol||''}</div>
            <div style="font-size:0.68rem;color:var(--t2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${dl.security_name||''}">${dl.security_name||dl.symbol||''}</div>
            <div style="font-size:0.65rem;color:var(--dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${dl.client_name||''}">${dl.client_name||'—'}</div>
            <div>
              <span style="font-family:Share Tech Mono,monospace;font-size:0.65rem;font-weight:700;
                padding:2px 6px;border-radius:2px;
                background:${buy?'rgba(0,255,136,0.12)':'rgba(255,51,85,0.12)'};
                color:${buy?'var(--green)':'var(--red)'};">
                ${buy?'BUY':'SELL'}
              </span>
            </div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.68rem;
                 color:${buy?'var(--green)':'var(--red)'};">
              ${qty}
            </div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--cyan);">
              ${price}
            </div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;
                 color:${dl.deal_kind==='BULK'?'var(--gold)':'var(--purple)'};">
              ${dl.deal_kind||'—'}
            </div>
          </div>`;
        }).join('')}
      </div>
      ${d.deals.length > 20 ? `<div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);padding:4px 8px;text-align:right;">Showing 20 of ${d.deals.length} deals</div>` : ''}
    </div>`;
  }

  // ── Volume anomalies ───────────────────────────────────────────
  if (d.anomalies && d.anomalies.length) {
    const SIG = {
      BULL_SPIKE:   {lbl:'Bull Spike',   col:'var(--green)', icon:'🟢'},
      BEAR_SPIKE:   {lbl:'Bear Spike',   col:'var(--red)',   icon:'🔴'},
      ACCUMULATION: {lbl:'Accumulation', col:'#00cc88',      icon:'▲'},
      DISTRIBUTION: {lbl:'Distribution', col:'var(--red)',   icon:'▼'},
      ABSORPTION:   {lbl:'Absorption',   col:'var(--gold)',  icon:'⊕'},
    };
    const counts = {};
    d.anomalies.forEach(a => { counts[a.signal] = (counts[a.signal]||0)+1; });
    const cutoff30 = new Date(); cutoff30.setDate(cutoff30.getDate()-30);
    const recent = d.anomalies.filter(a => new Date(a.trade_date) >= cutoff30);
    const all    = d.anomalies;

    html += `<div style="margin-bottom:16px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--cyan);letter-spacing:2px;">
          📊 VOLUME ANOMALIES — SMART MONEY FOOTPRINT
        </div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);">
          ${all.length} total · ${recent.length} last 30d
        </div>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;">
        ${Object.entries(counts).map(([sig,cnt]) => {
          const s = SIG[sig]||{lbl:sig,col:'var(--dim)',icon:'●'};
          const rc = recent.filter(a=>a.signal===sig).length;
          return `<div style="background:var(--p2);border:1px solid var(--border);padding:8px 14px;min-width:90px;text-align:center;">
            <div style="font-size:1.2rem;">${s.icon}</div>
            <div style="font-family:Orbitron,sans-serif;font-size:1.2rem;color:var(--gold);font-weight:700;">${cnt}</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:${s.col};">${s.lbl}</div>
            ${rc?`<div style="font-family:Share Tech Mono,monospace;font-size:0.52rem;color:var(--cyan);">${rc} recent</div>`:''}
          </div>`;
        }).join('')}
      </div>
      ${recent.length ? `
      <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--gold);letter-spacing:2px;margin-bottom:6px;">RECENT (LAST 30 DAYS)</div>
      <div style="border:1px solid var(--border);margin-bottom:12px;">
        <div style="display:grid;grid-template-columns:90px 110px 70px 80px 70px;padding:4px 8px;
             background:rgba(0,0,0,0.4);font-family:Share Tech Mono,monospace;font-size:0.52rem;color:var(--dim);">
          <div>DATE</div><div>SIGNAL</div><div>VOL×</div><div>CANDLE</div><div>PRICE Δ</div>
        </div>
        ${recent.slice(0,8).map(a => {
          const s = SIG[a.signal]||{lbl:a.signal,col:'var(--dim)'};
          const cc = (a.price_change_pct||0)>=0?'var(--green)':'var(--red)';
          return `<div style="display:grid;grid-template-columns:90px 110px 70px 80px 70px;padding:5px 8px;border-top:1px solid var(--border);">
            <div style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);">${a.trade_date}</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:${s.col};font-weight:700;">${s.lbl}</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--gold);">${(a.vol_ratio||0).toFixed(1)}×</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);">${a.candle_type||'—'}</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:${cc};">${(a.price_change_pct||0)>=0?'+':''}${(a.price_change_pct||0).toFixed(2)}%</div>
          </div>`;
        }).join('')}
      </div>` : `<div style="padding:8px;font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);border:1px solid var(--border);margin-bottom:10px;">No anomalies in last 30 days. ${all.length} historical events on record.</div>`}
      <details style="cursor:pointer;">
        <summary style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:2px;padding:4px 0;list-style:none;">
          ▶ ALL HISTORICAL SIGNALS (${all.length})
        </summary>
        <div style="border:1px solid var(--border);margin-top:6px;max-height:280px;overflow-y:auto;">
          <div style="display:grid;grid-template-columns:90px 110px 70px 80px 70px;padding:4px 8px;
               background:rgba(0,0,0,0.4);font-family:Share Tech Mono,monospace;font-size:0.52rem;color:var(--dim);position:sticky;top:0;">
            <div>DATE</div><div>SIGNAL</div><div>VOL×</div><div>CANDLE</div><div>PRICE Δ</div>
          </div>
          ${all.slice(0,150).map(a => {
            const s = SIG[a.signal]||{lbl:a.signal,col:'var(--dim)'};
            const cc = (a.price_change_pct||0)>=0?'var(--green)':'var(--red)';
            return `<div style="display:grid;grid-template-columns:90px 110px 70px 80px 70px;padding:4px 8px;border-top:1px solid rgba(255,255,255,0.04);">
              <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);">${a.trade_date}</div>
              <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:${s.col};">${s.lbl}</div>
              <div style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--gold);">${(a.vol_ratio||0).toFixed(1)}×</div>
              <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);">${a.candle_type||'—'}</div>
              <div style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:${cc};">${(a.price_change_pct||0)>=0?'+':''}${(a.price_change_pct||0).toFixed(2)}%</div>
            </div>`;
          }).join('')}
          ${all.length>150?`<div style="padding:6px 8px;font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);">... ${all.length-150} more</div>`:''}
        </div>
      </details>
    </div>`;
  }

  if (!html) {
    html = `<div style="padding:12px;font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--dim);line-height:2;">
      <b style="color:var(--cyan);">Step 1:</b> <code style="color:var(--gold);">python db_patch.py</code> — fix DB schema<br>
      <b style="color:var(--cyan);">Step 2:</b> <code style="color:var(--gold);">python core/fetch_institutional.py --volume-refresh</code> — compute anomalies<br>
      <b style="color:var(--cyan);">Step 3:</b> <code style="color:var(--gold);">python core/fetch_institutional.py --bulk-only --days 30</code> — bulk deals
    </div>`;
  }
  return html;
}
"""