import re

def patch_page_advisor():
    with open("pages/page_advisor.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. adv-portfolio-card
    t_port = '<div class="card" id="adv-portfolio-card" style="display:none;">'
    r_port = '<div class="card admin-gated-section" id="adv-portfolio-card" data-feature-id="adv_portfolio_summary" data-feature-name="Portfolio Summary & Allocation" data-feature-page="advisor" style="position:relative; display:none;">'
    content = content.replace(t_port, r_port)

    # 2. adv-nakshatra-card
    t_nak = '<div class="card" id="adv-nakshatra-card" style="display:none;margin-bottom:16px;">'
    r_nak = '<div class="card admin-gated-section" id="adv-nakshatra-card" data-feature-id="adv_nakshatra_timing" data-feature-name="Moon Nakshatra & Timing Widget" data-feature-page="advisor" style="position:relative; display:none;margin-bottom:16px;">'
    content = content.replace(t_nak, r_nak)

    # 3. adv-planet-card
    t_planet = '<div class="card" id="adv-planet-card" style="margin-bottom:14px;">'
    r_planet = '<div class="card admin-gated-section" id="adv-planet-card" data-feature-id="adv_planetary_env" data-feature-name="Current Planetary Environment" data-feature-page="advisor" style="position:relative; margin-bottom:14px;">'
    content = content.replace(t_planet, r_planet)

    # 4. Header of recommendation card in buildRecCard
    t_hdr = '    <!-- Header -->\n    <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid var(--border);">'
    r_hdr = '    <!-- Header -->\n    <div class="admin-gated-section" data-feature-id="adv_rec_header" data-feature-name="Recommendation Header & Conviction" data-feature-page="advisor" style="position:relative; display:flex;align-items:center;gap:12px;margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid var(--border);">'
    content = content.replace(t_hdr, r_hdr)
    content = content.replace(t_hdr.replace('\n', '\r\n'), r_hdr.replace('\n', '\r\n'))

    # 5. Score breakdown (5 bars)
    t_scores = '    <!-- Score breakdown -->\n    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:14px;">'
    r_scores = '    <!-- Score breakdown -->\n    <div class="admin-gated-section" data-feature-id="adv_score_bars" data-feature-name="5-Engine Score Bars" data-feature-page="advisor" style="position:relative; margin-bottom:14px;">\n      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:6px;">'
    content = content.replace(t_scores, r_scores)
    content = content.replace(t_scores.replace('\n', '\r\n'), r_scores.replace('\n', '\r\n'))
    
    # Close wrapper after planet scoreBar
    t_scores_end = "      ${scoreBar('PLANET', r.planet_score||0, 15, 'var(--orange)')}\n    </div>"
    r_scores_end = "      ${scoreBar('PLANET', r.planet_score||0, 15, 'var(--orange)')}\n      </div>\n    </div>"
    content = content.replace(t_scores_end, r_scores_end)
    content = content.replace(t_scores_end.replace('\n', '\r\n'), r_scores_end.replace('\n', '\r\n'))

    # 6. Trade levels tile row (CMP, Entry, SL, Targets, R:R, Max Profit/Loss)
    # Replace static alpha-veil-container with dynamic admin-gated-section
    t_tiles = """      return '<div class="alpha-veil-container" style="margin-bottom:14px;">'
        + '<div class="alpha-blurred" style="display:grid;grid-template-columns:repeat(8,1fr);gap:5px;">'"""
    r_tiles = """      return '<div class="admin-gated-section" data-feature-id="adv_trade_levels" data-feature-name="Actionable Trade Corridor & P&L" data-feature-page="advisor" style="position:relative; margin-bottom:14px;">'
        + '<div style="display:grid;grid-template-columns:repeat(8,1fr);gap:5px;">'"""
    
    t_tiles_crlf = t_tiles.replace("\n", "\r\n")
    r_tiles_crlf = r_tiles.replace("\n", "\r\n")
    if t_tiles in content:
        content = content.replace(t_tiles, r_tiles, 1)
    elif t_tiles_crlf in content:
        content = content.replace(t_tiles_crlf, r_tiles_crlf, 1)

    # Remove static overlay from tile row since dynamic controller handles it
    t_overlay_block = """        + '</div>'
        + '<div class="alpha-veil-overlay">'
        + '  <div style="font-family:Orbitron,sans-serif;font-size:0.85rem;font-weight:700;color:var(--white);letter-spacing:1px;margin-bottom:3px;">🔒 INSTITUTIONAL CORRIDOR LOCKED</div>'
        + '  <div style="font-size:0.68rem;color:var(--dim);margin-bottom:8px;max-width:380px;">Actionable Entry Corridor, Stop Loss, and Targets are reserved for Institutional Pass subscribers.</div>'
        + '  <button onclick="openUpgradeModal()" class="btn-gold" style="font-size:0.68rem;padding:5px 14px;border-radius:3px;font-weight:700;cursor:pointer;">⚡ UNLOCK INSTITUTIONAL PASS</button>'
        + '</div>'
        + '</div>';"""
    r_overlay_block = """        + '</div>'
        + '</div>';"""

    t_overlay_block_crlf = t_overlay_block.replace("\n", "\r\n")
    r_overlay_block_crlf = r_overlay_block.replace("\n", "\r\n")
    if t_overlay_block in content:
        content = content.replace(t_overlay_block, r_overlay_block, 1)
    elif t_overlay_block_crlf in content:
        content = content.replace(t_overlay_block_crlf, r_overlay_block_crlf, 1)

    # 7. Combined Signal bar
    t_comb = '    <!-- Combined Signal bar — all 5 engines -->\n    <div style="background:rgba(0,0,0,0.3);border:1px solid var(--b2);border-radius:3px;padding:10px 14px;margin-bottom:14px;">'
    r_comb = '    <!-- Combined Signal bar — all 5 engines -->\n    <div class="admin-gated-section" data-feature-id="adv_combined_signal" data-feature-name="Combined Signal Matrix" data-feature-page="advisor" style="position:relative; background:rgba(0,0,0,0.3);border:1px solid var(--b2);border-radius:3px;padding:10px 14px;margin-bottom:14px;">'
    content = content.replace(t_comb, r_comb)
    content = content.replace(t_comb.replace('\n', '\r\n'), r_comb.replace('\n', '\r\n'))

    # 8. Sector index
    t_sec = "el.innerHTML += '<div style=\"margin-top:12px;padding:8px;background:rgba(0,0,0,0.3);border-radius:4px;display:flex;align-items:center;gap:12px;\">'"
    r_sec = "el.innerHTML += '<div class=\"admin-gated-section\" data-feature-id=\"adv_sector_index\" data-feature-name=\"Sector Index & Divergence\" data-feature-page=\"advisor\" style=\"position:relative; margin-top:12px;padding:8px;background:rgba(0,0,0,0.3);border-radius:4px;display:flex;align-items:center;gap:12px;\">'"
    content = content.replace(t_sec, r_sec)

    # 9. Reasons to buy & planetary influence (3-column details)
    t_reasons = '<!-- 3-column details -->\n    <div class="g2" style="margin-bottom:14px;">'
    r_reasons = '<!-- 3-column details -->\n    <div class="g2 admin-gated-section" data-feature-id="adv_reasons_regime" data-feature-name="Buy/Sell Signals & Planetary Regime" data-feature-page="advisor" style="position:relative; margin-bottom:14px;">'
    content = content.replace(t_reasons, r_reasons)
    content = content.replace(t_reasons.replace('\n', '\r\n'), r_reasons.replace('\n', '\r\n'))

    # 10. ML Deep Signal Engine (Continuation & Reversal)
    t_ml_cont = "return '<div style=\"padding:12px 14px;background:rgba(255,140,0,0.04);border:1px solid rgba(255,140,0,0.25);border-left:3px solid #ff9900;margin-bottom:14px;\">'"
    r_ml_cont = "return '<div class=\"admin-gated-section\" data-feature-id=\"adv_ml_deep_signal\" data-feature-name=\"ML Deep Signal & Continuation Engine\" data-feature-page=\"advisor\" style=\"position:relative; padding:12px 14px;background:rgba(255,140,0,0.04);border:1px solid rgba(255,140,0,0.25);border-left:3px solid #ff9900;margin-bottom:14px;\">'"
    content = content.replace(t_ml_cont, r_ml_cont)

    t_ml_rev = "return '<div style=\"padding:12px 14px;background:rgba(0,212,255,0.04);border:1px solid rgba(0,212,255,0.2);border-left:3px solid '+confCol+';margin-bottom:14px;\">'"
    r_ml_rev = "return '<div class=\"admin-gated-section\" data-feature-id=\"adv_ml_deep_signal\" data-feature-name=\"ML Deep Signal & Continuation Engine\" data-feature-page=\"advisor\" style=\"position:relative; padding:12px 14px;background:rgba(0,212,255,0.04);border:1px solid rgba(0,212,255,0.2);border-left:3px solid '+confCol+';margin-bottom:14px;\">'"
    content = content.replace(t_ml_rev, r_ml_rev)

    # 11. Tech momentum
    t_tech = "return '<div style=\"padding:10px 14px;background:var(--p2);border:1px solid var(--border);'+\n        'border-left:3px solid '+col+';margin-bottom:14px;\">'"
    t_tech_alt = "return '<div style=\"padding:10px 14px;background:var(--p2);border:1px solid var(--border);'\n        +'border-left:3px solid '+col+';margin-bottom:14px;\">'"
    r_tech = "return '<div class=\"admin-gated-section\" data-feature-id=\"adv_tech_momentum\" data-feature-name=\"Tech Momentum & Wyckoff Accumulation\" data-feature-page=\"advisor\" style=\"position:relative; padding:10px 14px;background:var(--p2);border:1px solid var(--border);'\n        +'border-left:3px solid '+col+';margin-bottom:14px;\">'"
    content = content.replace(t_tech, r_tech)
    content = content.replace(t_tech.replace('\n', '\r\n'), r_tech.replace('\n', '\r\n'))
    content = content.replace(t_tech_alt, r_tech)
    content = content.replace(t_tech_alt.replace('\n', '\r\n'), r_tech.replace('\n', '\r\n'))

    # 12. News & Institutional Deals
    t_news = '    <!-- ── Sentiment + Bulk/Block Deal Intelligence ── -->\n    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;">'
    r_news = '    <!-- ── Sentiment + Bulk/Block Deal Intelligence ── -->\n    <div class="admin-gated-section" data-feature-id="adv_news_institutional" data-feature-name="FinBERT News & Bulk/Block Deals" data-feature-page="advisor" style="position:relative; display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;">'
    content = content.replace(t_news, r_news)
    content = content.replace(t_news.replace('\n', '\r\n'), r_news.replace('\n', '\r\n'))

    # 13. Gann + Simons Trigger
    t_trig = '    <!-- Gann + Simons Price & Date Trigger card -->\n    <div style="background:rgba(0,0,0,0.25);border:1px solid var(--cyan);border-radius:3px;padding:12px 16px;margin-bottom:14px;">'
    r_trig = '    <!-- Gann + Simons Price & Date Trigger card -->\n    <div class="admin-gated-section" data-feature-id="adv_gann_simons_trigger" data-feature-name="Gann + Simons Trigger & Session Reversals" data-feature-page="advisor" style="position:relative; background:rgba(0,0,0,0.25);border:1px solid var(--cyan);border-radius:3px;padding:12px 16px;margin-bottom:14px;">'
    content = content.replace(t_trig, r_trig)
    content = content.replace(t_trig.replace('\n', '\r\n'), r_trig.replace('\n', '\r\n'))

    # 14. Projections Charts Row
    t_charts = '    <!-- Charts row — click any chart to expand -->\n    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:4px;">'
    r_charts = '    <!-- Charts row — click any chart to expand -->\n    <div class="admin-gated-section" data-feature-id="adv_charts_projections" data-feature-name="Projections & S/R Charts" data-feature-page="advisor" style="position:relative; display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:4px;">'
    content = content.replace(t_charts, r_charts)
    content = content.replace(t_charts.replace('\n', '\r\n'), r_charts.replace('\n', '\r\n'))

    # 15. Single Stock Report Deep Analysis
    t_single_deep = "function _buildSingleReportHTML(rep, rec) {"
    r_single_deep = "function _buildSingleReportHTML(rep, rec) {\n  let _wrapStart = '<div class=\"admin-gated-section\" data-feature-id=\"adv_single_deep_analysis\" data-feature-name=\"Single Stock Deep Analysis Synthesis\" data-feature-page=\"advisor\" style=\"position:relative;\">';"
    content = content.replace(t_single_deep, r_single_deep)
    content = content.replace(t_single_deep.replace('\n', '\r\n'), r_single_deep.replace('\n', '\r\n'))

    t_single_ret = "return `\n    <div class=\"card\""
    r_single_ret = "return _wrapStart + `\n    <div class=\"card\""
    content = content.replace(t_single_ret, r_single_ret)
    content = content.replace(t_single_ret.replace('\n', '\r\n'), r_single_ret.replace('\n', '\r\n'))

    t_single_end = "</div>\n    </div>`;"
    r_single_end = "</div>\n    </div>` + '</div>';"
    content = content.replace(t_single_end, r_single_end)
    content = content.replace(t_single_end.replace('\n', '\r\n'), r_single_end.replace('\n', '\r\n'))

    with open("pages/page_advisor.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully patched pages/page_advisor.py with all 14 granular features!")
    return True

if __name__ == "__main__":
    patch_page_advisor()
