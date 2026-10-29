# -*- coding: utf-8 -*-
"""
Patch pages/page_risk.py for Bugs 6 and 7:
- Remove subtitle tags: MARGIN DASHBOARD SETTINGS CORRELATION and PHASE 4 MARGIN ENGINE
- Connect loadRiskDashboard to api('risk_dashboard'), remove _mockDashboardData
"""

def patch():
    with open('pages/page_risk.py', 'r', encoding='utf-8') as f:
        src = f.read()

    # 1. Topbar subtitle tag removal (Bug 6)
    old_topbar = '''  <div class="topbar">
    <div style="display:flex;align-items:center;gap:10px;">
      <span style="font-family:Orbitron,sans-serif;font-size:1.1rem;color:var(--gold);font-weight:700;letter-spacing:2px;">⚠️ RISK MANAGEMENT</span>
      <span class="page-tag">MARGIN · DASHBOARD · SETTINGS · CORRELATION</span>
    </div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;">
      PHASE 4 · MARGIN ENGINE · PORTFOLIO PROTECTION
    </div>
  </div>'''

    new_topbar = '''  <div class="topbar">
    <div style="display:flex;align-items:center;gap:10px;">
      <span style="font-family:Orbitron,sans-serif;font-size:1.1rem;color:var(--gold);font-weight:700;letter-spacing:2px;">⚠️ RISK MANAGEMENT</span>
    </div>
  </div>'''

    assert old_topbar in src, "old_topbar not found in page_risk.py"
    src = src.replace(old_topbar, new_topbar, 1)
    print("Replaced topbar in page_risk.py")

    # 2. Risk dashboard loading & mock removal (Bug 7)
    old_rd = '''async function loadRiskDashboard() {
  try {
    const resp = await fetch('/api/risk_dashboard');
    const data = resp.ok ? await resp.json() : _mockDashboardData();
    _renderDashboard(data);
  } catch (e) {
    _renderDashboard(_mockDashboardData());
  }
}

function _mockDashboardData() {
  return {
    drawdown: -4.2,
    var_95: -2.8,
    total_exposure: 324500,
    win_rate: 62.5,
    health_score: 74,
    health_dd: 78,
    health_var: 72,
    health_div: 65,
    health_wr: 82,
    sectors: [
      { name:'IT', pct:28 }, { name:'Banking', pct:22 },
      { name:'FMCG', pct:15 }, { name:'Pharma', pct:18 },
      { name:'Auto', pct:10 }, { name:'Energy', pct:7 }
    ],
    positions: [
      { symbol:'TCS', entry:3450.5, cmp:3521.0, qty:10, days:5, sector:'IT' },
      { symbol:'HDFC', entry:1620.0, cmp:1598.5, qty:20, days:12, sector:'Banking' },
      { symbol:'ITC', entry:445.0, cmp:452.3, qty:50, days:3, sector:'FMCG' },
    ],
    daily_pnl: [
      { date:'Jun 17', pnl:1240 }, { date:'Jun 18', pnl:-560 },
      { date:'Jun 19', pnl:2100 }, { date:'Jun 20', pnl:-120 },
      { date:'Jun 21', pnl:880 },  { date:'Jun 24', pnl:1650 },
      { date:'Jun 25', pnl:-430 }, { date:'Jun 26', pnl:3200 },
      { date:'Jun 27', pnl:-200 }, { date:'Jun 28', pnl:1100 }
    ]
  };
}'''

    new_rd = '''async function loadRiskDashboard() {
  try {
    const data = await api('risk_dashboard');
    if (data && data.ok) {
      _renderDashboard(data);
    } else {
      _renderDashboard({
        max_drawdown_pct: 0, var_95_pct: 0, total_exposure: 0, win_pct: 0,
        sharpe_ratio: 0, profit_factor: 0, expectancy: 0, health_score: 100,
        health_dd: 100, health_var: 100, health_div: 100, health_wr: 100,
        sector_exposure: [], positions: [], daily_pnl: []
      });
    }
  } catch (e) {
    _renderDashboard({
      max_drawdown_pct: 0, var_95_pct: 0, total_exposure: 0, win_pct: 0,
      sharpe_ratio: 0, profit_factor: 0, expectancy: 0, health_score: 100,
      health_dd: 100, health_var: 100, health_div: 100, health_wr: 100,
      sector_exposure: [], positions: [], daily_pnl: []
    });
  }
}'''

    assert old_rd in src, "old_rd not found in page_risk.py"
    src = src.replace(old_rd, new_rd, 1)
    print("Replaced loadRiskDashboard in page_risk.py")

    with open('pages/page_risk.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print("pages/page_risk.py successfully patched!")

if __name__ == '__main__':
    patch()
