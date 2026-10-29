def patch_overview():
    with open("pages/page_overview.py", "r", encoding="utf-8") as f:
        c = f.read()

    # 1. Market Status Banner
    t1 = '<!-- 1. Market Status Banner -->\n          <div style="display:flex; gap:16px; margin-bottom:24px; flex-wrap:wrap;">'
    r1 = '<!-- 1. Market Status Banner -->\n          <div class="admin-gated-section" data-feature-id="ov_status_summary" data-feature-name="Portfolio Value & Market Status" data-feature-page="overview" style="position:relative; display:flex; gap:16px; margin-bottom:24px; flex-wrap:wrap;">'
    c = c.replace(t1, r1).replace(t1.replace('\n', '\r\n'), r1.replace('\n', '\r\n'))

    # 2. AI Market Summary
    t2 = '<div class="card" data-feature-id="overview_market_regime" style="padding:20px; margin-bottom:24px;">'
    r2 = '<div class="card admin-gated-section" data-feature-id="overview_market_regime" data-feature-name="Personalized AI Insights Summary" data-feature-page="overview" style="position:relative; padding:20px; margin-bottom:24px;">'
    c = c.replace(t2, r2)

    # 3. Watchlist & Opportunities
    t3 = '<!-- 3. Grid for Watchlist and Opportunities -->\n          <div class="g2" style="margin-bottom:24px;">'
    r3 = '<!-- 3. Grid for Watchlist and Opportunities -->\n          <div class="g2 admin-gated-section" data-feature-id="overview_watchlist_opps" data-feature-name="Watchlist & Tailored Opportunities" data-feature-page="overview" style="position:relative; margin-bottom:24px;">'
    c = c.replace(t3, r3).replace(t3.replace('\n', '\r\n'), r3.replace('\n', '\r\n'))

    # 4. Risk Alerts
    t4 = '<div class="card" style="padding:20px;">\n                <div class="card-title">🚨 RISK ALERTS & SAFEGUARDS</div>'
    r4 = '<div class="card admin-gated-section" data-feature-id="overview_risk_alerts" data-feature-name="Risk Alerts & Safeguards" data-feature-page="overview" style="position:relative; padding:20px;">\n                <div class="card-title">🚨 RISK ALERTS & SAFEGUARDS</div>'
    c = c.replace(t4, r4).replace(t4.replace('\n', '\r\n'), r4.replace('\n', '\r\n'))

    # 5. Market News
    t5 = '<div class="card" data-feature-id="overview_sentiment" style="padding:20px;">'
    r5 = '<div class="card admin-gated-section" data-feature-id="overview_sentiment" data-feature-name="Relevant Market News & Flow" data-feature-page="overview" style="position:relative; padding:20px;">'
    c = c.replace(t5, r5)

    # 6. Index Overview
    t6 = '<div class="card" data-feature-id="intraday_reversal_matrix" style="padding:0;overflow:hidden;margin-bottom:24px;">'
    r6 = '<div class="card admin-gated-section" data-feature-id="intraday_reversal_matrix" data-feature-name="Index Overview & Day Range" data-feature-page="overview" style="position:relative; padding:0;overflow:hidden;margin-bottom:24px;">'
    c = c.replace(t6, r6)

    # 7. Most Bought Stocks
    t7 = '<div id="ov-most-bought" class="ov-hscroll" style="margin-bottom:30px;"></div>'
    r7 = '<div id="ov-most-bought" class="ov-hscroll admin-gated-section" data-feature-id="overview_most_bought" data-feature-name="Most Bought Equities" data-feature-page="overview" style="position:relative; margin-bottom:30px;"></div>'
    c = c.replace(t7, r7)

    # 8. Top Movers
    t8 = '<div class="card" style="padding:16px;">\n          <div style="display:flex;justify-content:space-between;margin-bottom:16px;">\n             <div style="display:flex;gap:0;">\n                <button class="ov-pill-btn active" onclick="ovSwitchMoversTab(this,\'gainers\')"'
    r8 = '<div class="card admin-gated-section" data-feature-id="overview_top_movers" data-feature-name="Top Movers (Gainers & Losers)" data-feature-page="overview" style="position:relative; padding:16px;">\n          <div style="display:flex;justify-content:space-between;margin-bottom:16px;">\n             <div style="display:flex;gap:0;">\n                <button class="ov-pill-btn active" onclick="ovSwitchMoversTab(this,\'gainers\')"'
    c = c.replace(t8, r8).replace(t8.replace('\n', '\r\n'), r8.replace('\n', '\r\n'))

    # 9. Sectorwise Movements
    t9 = '<div class="card" style="padding:16px;">\n          <div style="display:flex;gap:8px;margin-bottom:16px;overflow-x:auto;" id="ov-sector-tabs">'
    r9 = '<div class="card admin-gated-section" data-feature-id="overview_sector_movements" data-feature-name="Sectorwise Movements Heatmap" data-feature-page="overview" style="position:relative; padding:16px;">\n          <div style="display:flex;gap:8px;margin-bottom:16px;overflow-x:auto;" id="ov-sector-tabs">'
    c = c.replace(t9, r9).replace(t9.replace('\n', '\r\n'), r9.replace('\n', '\r\n'))

    with open("pages/page_overview.py", "w", encoding="utf-8") as f:
        f.write(c)
    print("Successfully patched pages/page_overview.py with granular features!")
    return True

if __name__ == "__main__":
    patch_overview()
