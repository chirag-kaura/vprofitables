# -*- coding: utf-8 -*-
"""
Patch script for Bugs 8 - 14:
- Bug 8: page_portfolio.py topbar subtitle removal
- Bug 9: page_advisor.py topbar subtitle removal
- Bug 10: page_sentiment.py topbar subtitle removal
- Bug 11: page_chart.py topbar subtitle removal
- Bug 12a: page_simons.py topbar subtitle removal
- Bug 12b: page_gann.py topbar subtitle removal
- Bug 13: page_natal.py topbar subtitle removal
- Bug 14: page_fundamentals.py topbar subtitle removal + _shared.js fund-sym strictly equities
"""

def patch_file(path, old_text, new_text):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert old_text in content, f"Target text not found in {path}"
    content = content.replace(old_text, new_text, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Patched {path}")

def run():
    # Bug 8: page_portfolio.py
    old_ptf = '''  <div class="topbar">
    <div style="display:flex;align-items:center;gap:10px;">
      <span style="font-family:Orbitron,sans-serif;font-size:1.1rem;color:var(--gold);font-weight:700;letter-spacing:2px;">💼 DEMAT PORTFOLIO & ORDER BOOK</span>
      <span class="page-tag">HOLDINGS · ACTIVE POSITIONS · BRACKET ORDERS · EXECUTION</span>
    </div>
    <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;">
      REAL-TIME POSITIONS & CAPITAL AUDIT
    </div>
  </div>'''

    new_ptf = '''  <div class="topbar">
    <div style="display:flex;align-items:center;gap:10px;">
      <span style="font-family:Orbitron,sans-serif;font-size:1.1rem;color:var(--gold);font-weight:700;letter-spacing:2px;">💼 DEMAT PORTFOLIO & ORDER BOOK</span>
    </div>
  </div>'''
    patch_file('pages/page_portfolio.py', old_ptf, new_ptf)

    # Bug 9: page_advisor.py
    old_adv = '''  <div class="topbar">
    <h2>💡 INVESTMENT AI ADVISOR</h2>
    <span class="page-tag">Vprofitables · QUANT</span>
  </div>'''

    new_adv = '''  <div class="topbar">
    <h2>💡 INVESTMENT AI ADVISOR</h2>
  </div>'''
    patch_file('pages/page_advisor.py', old_adv, new_adv)

    # Bug 10: page_sentiment.py
    old_sent = '''  <div class="topbar">
    <h2>🧠 SENTIMENT + EMOTIONAL ANALYSIS</h2>
    <span class="page-tag">MULTI-FACTOR MACRO & REAL-TIME INTELLIGENCE</span>
  </div>'''

    new_sent = '''  <div class="topbar">
    <h2>🧠 SENTIMENT + EMOTIONAL ANALYSIS</h2>
  </div>'''
    patch_file('pages/page_sentiment.py', old_sent, new_sent)

    # Bug 11: page_chart.py
    old_chart = '''  <div class="topbar">
    <h2>📈 CHART + SUPPORT/RESISTANCE</h2>
    <span class="page-tag">TECHNICAL ANALYSIS</span>
  </div>'''

    new_chart = '''  <div class="topbar">
    <h2>📈 CHART + SUPPORT/RESISTANCE</h2>
  </div>'''
    patch_file('pages/page_chart.py', old_chart, new_chart)

    # Bug 12a: page_simons.py
    old_simons = '''  <div class="topbar">
    <h2>SIMONS QUANT LAB</h2>
    <span class="page-tag">FFT · AUTOCORRELATION · REGIME · BACKTEST</span>
  </div>'''

    new_simons = '''  <div class="topbar">
    <h2>SIMONS QUANT LAB</h2>
  </div>'''
    patch_file('pages/page_simons.py', old_simons, new_simons)

    # Bug 12b: page_gann.py
    old_gann = '''<div class="topbar"><h2>GANN + ASTRO ANALYSIS</h2><span class="page-tag">FULL CONFLUENCE</span></div>'''
    new_gann = '''<div class="topbar"><h2>GANN + ASTRO ANALYSIS</h2></div>'''
    patch_file('pages/page_gann.py', old_gann, new_gann)

    # Bug 13: page_natal.py
    old_natal = '''<div class="topbar"><h2>NATAL CHARTS</h2><span class="page-tag">TRANSIT × NATAL</span></div>'''
    new_natal = '''<div class="topbar"><h2>NATAL CHARTS</h2></div>'''
    patch_file('pages/page_natal.py', old_natal, new_natal)

    # Bug 14: page_fundamentals.py
    old_fund = '''  <div class="topbar" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
    <div style="display:flex;align-items:center;gap:6px;">
      <h2 style="margin:0;">📊 FUNDAMENTAL ANALYSIS</h2>
      <span class="page-tag">VALUATION + SCORING</span>
    </div>'''

    new_fund = '''  <div class="topbar" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
    <div style="display:flex;align-items:center;gap:6px;">
      <h2 style="margin:0;">📊 FUNDAMENTAL ANALYSIS</h2>
    </div>'''
    patch_file('pages/page_fundamentals.py', old_fund, new_fund)

    # Bug 14: _shared.js - strictly equities in fund-sym
    with open('pages/_shared.js', 'r', encoding='utf-8') as f:
        shared_src = f.read()

    target_loop = "[['Indices', d.indices], ['Equities', d.equities], ['Commodities', d.commodities]].forEach(([grp, syms]) => {"
    assert target_loop in shared_src, "target_loop not found in _shared.js"
    repl_loop = """const _groups = id === 'fund-sym'
        ? [['Equities', d.equities]]
        : [['Indices', d.indices], ['Equities', d.equities], ['Commodities', d.commodities]];
      _groups.forEach(([grp, syms]) => {"""
    shared_src = shared_src.replace(target_loop, repl_loop, 1)

    with open('pages/_shared.js', 'w', encoding='utf-8') as f:
        f.write(shared_src)
    print("Patched pages/_shared.js for fund-sym equities only")

if __name__ == '__main__':
    run()
