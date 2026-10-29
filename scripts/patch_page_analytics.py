# -*- coding: utf-8 -*-
"""
Patch pages/page_analytics.py for Bugs 1, 2, 3, 4, 5:
- Remove subtitle tags: ZERODHA CONSOLE STYLE and PHASE 5 LIVE P&L INTELLIGENCE
- Connect calendar to api('analytics_data', {type: 'calendar'}), remove mock
- Connect equity curve to api('analytics_data', {type: 'equity_curve'}), remove mock
- Connect statistics to api('analytics_data', {type: 'statistics'}), remove mock
- Connect best/worst to api('analytics_data', {type: 'best_worst'}), remove mock
- Connect sector pnl to api('analytics_data', {type: 'sector_pnl'}), handle losses safely and clean empty state
"""

def patch():
    with open('pages/page_analytics.py', 'r', encoding='utf-8') as f:
        src = f.read()

    # 1. Subtitle tag removal (Bug 5)
    old_topbar = '''  <div class="topbar" style="background:var(--panel);border-bottom:1px solid var(--border);padding:12px 20px;display:flex;justify-content:space-between;align-items:center;">
    <div style="display:flex;align-items:center;gap:12px;">
      <span style="font-family:Orbitron,sans-serif;font-size:1.1rem;color:var(--gold);font-weight:700;letter-spacing:2px;">📊 PERFORMANCE ANALYTICS</span>
      <span class="page-tag" style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1.5px;border:1px solid var(--border);padding:2px 8px;border-radius:3px;">ZERODHA CONSOLE STYLE</span>
    </div>
    <div style="font-family:'Share Tech Mono',monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;">
      Vprofitables · PHASE 5 · LIVE P&amp;L INTELLIGENCE
    </div>
  </div>'''

    new_topbar = '''  <div class="topbar" style="background:var(--panel);border-bottom:1px solid var(--border);padding:12px 20px;display:flex;justify-content:space-between;align-items:center;">
    <div style="display:flex;align-items:center;gap:12px;">
      <span style="font-family:Orbitron,sans-serif;font-size:1.1rem;color:var(--gold);font-weight:700;letter-spacing:2px;">📊 PERFORMANCE ANALYTICS</span>
    </div>
  </div>'''

    assert old_topbar in src, "old_topbar not found in page_analytics.py"
    src = src.replace(old_topbar, new_topbar, 1)
    print("Replaced topbar in page_analytics.py")

    # 2. Tab 1 Calendar
    old_cal = '''// ════════════════════════════════════════════════════
//  TAB 1: P&L CALENDAR HEATMAP
// ════════════════════════════════════════════════════
async function loadCalendar() {
  try {
    let url = '/api/analytics_data?type=calendar';
    const resp = await fetch(url);
    const data = resp.ok ? await resp.json() : null;
    _calData = data || _mockCalendarData();
    drawCalendarHeatmap(_calData);
  } catch(e) {
    _calData = _mockCalendarData();
    drawCalendarHeatmap(_calData);
  }
}

function _mockCalendarData() {
  // Generate a year of mock P&L data
  const days = {};
  const now  = new Date();
  const start = new Date(now.getFullYear(), 0, 1);
  for (let d = new Date(start); d <= now; d.setDate(d.getDate() + 1)) {
    const dow = d.getDay();
    if (dow === 0 || dow === 6) continue; // skip weekends
    const key = d.toISOString().slice(0, 10);
    if (Math.random() < 0.65) { // 65% of trading days have trades
      const pnl = (Math.random() - 0.38) * 25000;
      days[key] = { pnl: Math.round(pnl), trades: Math.ceil(Math.random() * 6) };
    }
  }
  // Compute stats
  const vals = Object.values(days).map(d => d.pnl);
  const total = vals.reduce((a,b) => a+b, 0);
  const bestDay  = Math.max(...vals);
  const worstDay = Math.min(...vals);
  const profitableDays = vals.filter(v => v > 0).length;
  return { days, total, best_day: bestDay, worst_day: worstDay, profitable_pct: Math.round(profitableDays/vals.length*100) };
}'''

    new_cal = '''// ════════════════════════════════════════════════════
//  TAB 1: P&L CALENDAR HEATMAP
// ════════════════════════════════════════════════════
async function loadCalendar() {
  try {
    const data = await api('analytics_data', {type: 'calendar'});
    _calData = (data && data.ok) ? data : { days:{}, total:0, best_day:0, worst_day:0, profitable_pct:0 };
    drawCalendarHeatmap(_calData);
  } catch(e) {
    _calData = { days:{}, total:0, best_day:0, worst_day:0, profitable_pct:0 };
    drawCalendarHeatmap(_calData);
  }
}'''

    assert old_cal in src, "old_cal not found in page_analytics.py"
    src = src.replace(old_cal, new_cal, 1)
    print("Replaced loadCalendar in page_analytics.py")

    # 3. Tab 2 Equity Curve
    old_eq = '''// ════════════════════════════════════════════════════
//  TAB 2: EQUITY CURVE
// ════════════════════════════════════════════════════
async function loadEquityCurve() {
  try {
    const resp = await fetch('/api/analytics_data?type=equity_curve');
    const data = resp.ok ? await resp.json() : null;
    _eqData = data || _mockEquityData();
    drawEquityCurve(_eqData);
  } catch(e) {
    _eqData = _mockEquityData();
    drawEquityCurve(_eqData);
  }
}

function _mockEquityData() {
  const pts = 252; // ~1 trading year
  const dates = [];
  const portfolio = [];
  const nifty     = [];
  let pVal = 500000, nVal = 500000;
  let d = new Date();
  d.setFullYear(d.getFullYear() - 1);
  for (let i = 0; i < pts; i++) {
    while ([0,6].includes(d.getDay())) d.setDate(d.getDate() + 1);
    dates.push(d.toISOString().slice(0,10));
    const pr = (Math.random() - 0.44) * 0.018;
    const nr = (Math.random() - 0.46) * 0.014;
    pVal *= (1 + pr);
    nVal *= (1 + nr);
    portfolio.push(Math.round(pVal));
    nifty.push(Math.round(nVal));
    d.setDate(d.getDate() + 1);
  }
  const ret      = ((portfolio.at(-1) - 500000) / 500000 * 100).toFixed(2);
  const niftyRet = ((nifty.at(-1) - 500000) / 500000 * 100).toFixed(2);
  // Approx Sharpe: annualized return / std dev of daily returns
  const daily = portfolio.map((v,i) => i===0 ? 0 : (v - portfolio[i-1]) / portfolio[i-1]);
  const mean  = daily.slice(1).reduce((a,b)=>a+b,0) / (daily.length-1);
  const std   = Math.sqrt(daily.slice(1).reduce((a,b)=>a+(b-mean)**2,0)/(daily.length-2));
  const sharpe = (mean / std * Math.sqrt(252)).toFixed(2);
  // Max drawdown
  let peak = portfolio[0], maxDD = 0;
  portfolio.forEach(v => { if(v>peak) peak=v; const dd=(peak-v)/peak; if(dd>maxDD) maxDD=dd; });

  return { dates, portfolio, nifty, total_return: +ret, nifty_return: +niftyRet, sharpe: +sharpe, max_drawdown: +(maxDD*100).toFixed(2) };
}'''

    new_eq = '''// ════════════════════════════════════════════════════
//  TAB 2: EQUITY CURVE
// ════════════════════════════════════════════════════
async function loadEquityCurve() {
  try {
    const data = await api('analytics_data', {type: 'equity_curve'});
    _eqData = (data && data.ok) ? data : { curve:[], total_return:0, nifty_return:0, sharpe:0, max_drawdown:0 };
    drawEquityCurve(_eqData);
  } catch(e) {
    _eqData = { curve:[], total_return:0, nifty_return:0, sharpe:0, max_drawdown:0 };
    drawEquityCurve(_eqData);
  }
}'''

    assert old_eq in src, "old_eq not found in page_analytics.py"
    src = src.replace(old_eq, new_eq, 1)
    print("Replaced loadEquityCurve in page_analytics.py")

    # 4. Tab 3 Statistics
    old_stats = '''// ════════════════════════════════════════════════════
//  TAB 3: STATISTICS
// ════════════════════════════════════════════════════
async function loadStatistics() {
  try {
    const resp = await fetch('/api/analytics_data?type=statistics');
    const data = resp.ok ? await resp.json() : null;
    _renderStats(data || _mockStatsData());
  } catch(e) {
    _renderStats(_mockStatsData());
  }
}

function _mockStatsData() {
  return {
    total_trades: 87,
    win_pct: 61.0,
    loss_pct: 39.0,
    avg_win: 8420,
    avg_loss: 4380,
    profit_factor: 3.31,
    expectancy: 3426,
    avg_rr: 2.18,
    avg_hold_days: 4.2,
    best_rr: 8.4,
    worst_rr: -1.0,
    max_consec_wins: 7,
    max_consec_losses: 4,
    recent_streak: ['W','W','L','W','W','W','L','L','W','W','W','W','L','W','W'],
    monthly_pnl: [
      { month: 'Jan', pnl: -3200 },
      { month: 'Feb', pnl: 14500 },
      { month: 'Mar', pnl: 8700  },
      { month: 'Apr', pnl: -1200 },
      { month: 'May', pnl: 22000 },
      { month: 'Jun', pnl: 11300 },
    ],
    weekday: [
      { day: 'Mon', wins: 14, losses: 8  },
      { day: 'Tue', wins: 18, losses: 6  },
      { day: 'Wed', wins: 12, losses: 11 },
      { day: 'Thu', wins: 16, losses: 7  },
      { day: 'Fri', wins: 13, losses: 2  },
    ]
  };
}'''

    new_stats = '''// ════════════════════════════════════════════════════
//  TAB 3: STATISTICS
// ════════════════════════════════════════════════════
async function loadStatistics() {
  try {
    const data = await api('analytics_data', {type: 'statistics'});
    const s = (data && data.ok) ? data : {
      total_trades: 0, win_pct: 0, loss_pct: 0, avg_win: 0, avg_loss: 0,
      profit_factor: 0, expectancy: 0, avg_rr: 0, avg_hold_days: 0,
      best_rr: 0, worst_rr: 0, max_consec_wins: 0, max_consec_losses: 0,
      recent_streak: [], monthly_pnl: [], weekday: []
    };
    _renderStats(s);
  } catch(e) {
    _renderStats({
      total_trades: 0, win_pct: 0, loss_pct: 0, avg_win: 0, avg_loss: 0,
      profit_factor: 0, expectancy: 0, avg_rr: 0, avg_hold_days: 0,
      best_rr: 0, worst_rr: 0, max_consec_wins: 0, max_consec_losses: 0,
      recent_streak: [], monthly_pnl: [], weekday: []
    });
  }
}'''

    assert old_stats in src, "old_stats not found in page_analytics.py"
    src = src.replace(old_stats, new_stats, 1)
    print("Replaced loadStatistics in page_analytics.py")

    # 5. Tab 4 Best/Worst
    old_bw = '''async function loadBestWorst(type) {
  _bwMode = type;

  // Update toggle button styles
  const btnBest  = document.getElementById('bw-btn-best');
  const btnWorst = document.getElementById('bw-btn-worst');
  if (btnBest && btnWorst) {
    if (type === 'best') {
      btnBest.style.background  = 'rgba(8,153,129,0.25)';
      btnBest.style.color       = '#089981';
      btnWorst.style.background = 'transparent';
      btnWorst.style.color      = '#6C7284';
    } else {
      btnWorst.style.background = 'rgba(242,54,69,0.2)';
      btnWorst.style.color      = '#F23645';
      btnBest.style.background  = 'transparent';
      btnBest.style.color       = '#6C7284';
    }
  }

  try {
    const resp = await fetch('/api/analytics_data?type=best_worst&mode=' + type);
    const data = resp.ok ? await resp.json() : null;
    _bwData = data || _mockBWData(type);
    _renderBWTable(_bwData, type);
  } catch(e) {
    _bwData = _mockBWData(type);
    _renderBWTable(_bwData, type);
  }
}

function _mockBWData(type) {
  const syms   = ['RELIANCE','TCS','INFY','HDFC','ICICI','SBIN','WIPRO','BAJAJ','MARUTI','HDFCBANK'];
  const trades = syms.map((sym, i) => {
    const entry = 1200 + Math.random() * 2000;
    const mul   = type === 'best' ? (1 + Math.random() * 0.25) : (1 - Math.random() * 0.15);
    const exit  = entry * mul;
    const pnl   = Math.round((exit - entry) * (10 + Math.floor(Math.random()*40)));
    const pct   = ((exit - entry) / entry * 100).toFixed(2);
    const rr    = type === 'best' ? (2 + Math.random() * 5).toFixed(2) : (-0.2 - Math.random()).toFixed(2);
    const eDate = '2025-' + String(Math.floor(Math.random()*11)+1).padStart(2,'0') + '-' + String(Math.floor(Math.random()*27)+1).padStart(2,'0');
    const xDate = '2025-' + String(Math.floor(Math.random()*11)+1).padStart(2,'0') + '-' + String(Math.floor(Math.random()*27)+1).padStart(2,'0');
    return { rank: i+1, symbol: sym, entry: entry.toFixed(2), exit: exit.toFixed(2), entry_date: eDate, exit_date: xDate, pnl, pct, rr, inv_type: Math.random()>0.5?'LONG':'SHORT' };
  });
  return { trades };
}

function _renderBWTable(data, type) {
  const body = document.getElementById('bw-table-body');
  if (!body) return;
  const isGood = type === 'best';
  body.innerHTML = (data.trades || []).map((t, i) => {'''

    new_bw = '''async function loadBestWorst(type) {
  _bwMode = type;

  // Update toggle button styles
  const btnBest  = document.getElementById('bw-btn-best');
  const btnWorst = document.getElementById('bw-btn-worst');
  if (btnBest && btnWorst) {
    if (type === 'best') {
      btnBest.style.background  = 'rgba(8,153,129,0.25)';
      btnBest.style.color       = '#089981';
      btnWorst.style.background = 'transparent';
      btnWorst.style.color      = '#6C7284';
    } else {
      btnWorst.style.background = 'rgba(242,54,69,0.2)';
      btnWorst.style.color      = '#F23645';
      btnBest.style.background  = 'transparent';
      btnBest.style.color       = '#6C7284';
    }
  }

  try {
    const data = await api('analytics_data', {type: 'best_worst', mode: type});
    _bwData = (data && data.ok) ? data : { trades: [] };
    _renderBWTable(_bwData, type);
  } catch(e) {
    _bwData = { trades: [] };
    _renderBWTable(_bwData, type);
  }
}

function _renderBWTable(data, type) {
  const body = document.getElementById('bw-table-body');
  if (!body) return;
  if (!data.trades || data.trades.length === 0) {
    body.innerHTML = '<div style="padding:24px;text-align:center;color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.75rem;">No closed trades recorded yet.</div>';
    return;
  }
  const isGood = type === 'best';
  body.innerHTML = (data.trades || []).map((t, i) => {'''

    assert old_bw in src, "old_bw not found in page_analytics.py"
    src = src.replace(old_bw, new_bw, 1)
    print("Replaced loadBestWorst in page_analytics.py")

    # 6. Tab 5 Sector P&L
    old_sector = '''// ════════════════════════════════════════════════════
//  TAB 5: SECTOR P&L
// ════════════════════════════════════════════════════
async function loadSectorPnl() {
  try {
    const resp = await fetch('/api/analytics_data?type=sector_pnl');
    const data = resp.ok ? await resp.json() : null;
    if (!data || !data.sectors || data.sectors.length === 0) {
      throw new Error("No closed trade records found");
    }
    _sectorData = data;
    _renderSectorTab(_sectorData);
  } catch(e) {
    _renderSectorError(e.message);
  }
}

function _renderSectorError(msg) {
  const tableBody = document.getElementById('sector-table-body');
  if (tableBody) {
    tableBody.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:24px;color:var(--red);font-family:Share Tech Mono,monospace;font-size:0.75rem;">⚠ Sector statistics unavailable: ${msg}</div>`;
  }
  const legend = document.getElementById('sector-donut-legend');
  if (legend) legend.innerHTML = '';
  const canvas = document.getElementById('sector-donut-canvas');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0,0,280,280);
    ctx.beginPath();
    ctx.arc(140, 130, 100, 0, Math.PI*2);
    ctx.strokeStyle = '#2B3139';
    ctx.lineWidth = 32;
    ctx.stroke();
    ctx.font = 'bold 12px JetBrains Mono, monospace';
    ctx.fillStyle = '#6C7284';
    ctx.textAlign = 'center';
    ctx.fillText('NO DATA', 140, 130);
  }
}'''

    new_sector = '''// ════════════════════════════════════════════════════
//  TAB 5: SECTOR P&L
// ════════════════════════════════════════════════════
async function loadSectorPnl() {
  try {
    const data = await api('analytics_data', {type: 'sector_pnl'});
    if (!data || !data.ok || !data.sectors || data.sectors.length === 0) {
      _renderSectorEmpty();
      return;
    }
    _sectorData = data;
    _renderSectorTab(_sectorData);
  } catch(e) {
    _renderSectorEmpty();
  }
}

function _renderSectorEmpty() {
  const tableBody = document.getElementById('sector-table-body');
  if (tableBody) {
    tableBody.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:30px;color:var(--dim);font-family:Share Tech Mono,monospace;font-size:0.75rem;">No closed trades recorded yet. Complete positions in your portfolio to generate sector analytics.</div>`;
  }
  const legend = document.getElementById('sector-donut-legend');
  if (legend) legend.innerHTML = '';
  const canvas = document.getElementById('sector-donut-canvas');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0,0,280,280);
    ctx.beginPath();
    ctx.arc(140, 130, 100, 0, Math.PI*2);
    ctx.strokeStyle = '#2B3139';
    ctx.lineWidth = 32;
    ctx.stroke();
    ctx.font = 'bold 12px JetBrains Mono, monospace';
    ctx.fillStyle = '#6C7284';
    ctx.textAlign = 'center';
    ctx.fillText('NO DATA', 140, 130);
  }
  const barCanvas = document.getElementById('sector-bar-canvas');
  if (barCanvas) {
    const ctx = barCanvas.getContext('2d');
    ctx.clearRect(0,0,barCanvas.width,barCanvas.height);
  }
}'''

    assert old_sector in src, "old_sector not found in page_analytics.py"
    src = src.replace(old_sector, new_sector, 1)
    print("Replaced loadSectorPnl in page_analytics.py")

    # Fix sector bar calculations to prevent NaN when losses is missing or 0
    old_bars = 'const maxT = Math.max(...sectors.map(s => s.wins + s.losses), 1);'
    new_bars = 'const maxT = Math.max(...sectors.map(s => (s.wins || 0) + (s.losses !== undefined ? s.losses : Math.max(0, s.trades - s.wins))), 1) || 1;'
    assert old_bars in src, "old_bars not found in page_analytics.py"
    src = src.replace(old_bars, new_bars, 1)

    old_losses_bar = 'const lH = (s.losses / maxT) * (midY - 20);'
    new_losses_bar = 'const lLosses = s.losses !== undefined ? s.losses : Math.max(0, s.trades - s.wins);\n    const lH = (lLosses / maxT) * (midY - 20);'
    assert old_losses_bar in src, "old_losses_bar not found in page_analytics.py"
    src = src.replace(old_losses_bar, new_losses_bar, 1)
    print("Fixed sector bars calculations in page_analytics.py")

    with open('pages/page_analytics.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print("pages/page_analytics.py successfully patched!")

if __name__ == '__main__':
    patch()
