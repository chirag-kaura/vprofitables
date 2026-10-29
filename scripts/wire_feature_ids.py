import os

def wire_features():
    # 1. page_overview.py
    if os.path.exists("pages/page_overview.py"):
        with open("pages/page_overview.py", "r", encoding="utf-8") as f:
            ov = f.read()
        
        # overview_market_regime
        t1 = '<div class="card" style="padding:20px; margin-bottom:24px;">\n             <div class="card-title">🤖 PERSONALIZED AI INSIGHTS SUMMARY</div>'
        r1 = '<div class="card" data-feature-id="overview_market_regime" style="padding:20px; margin-bottom:24px;">\n             <div class="card-title">🤖 PERSONALIZED AI INSIGHTS SUMMARY</div>'
        
        # overview_sentiment
        t2 = '<div class="card" style="padding:20px;">\n                <div class="card-title">📰 RELEVANT MARKET NEWS</div>'
        r2 = '<div class="card" data-feature-id="overview_sentiment" style="padding:20px;">\n                <div class="card-title">📰 RELEVANT MARKET NEWS</div>'
        
        # intraday_reversal_matrix
        t3 = '<div class="card" style="padding:0;overflow:hidden;margin-bottom:24px;">'
        r3 = '<div class="card" data-feature-id="intraday_reversal_matrix" style="padding:0;overflow:hidden;margin-bottom:24px;">'

        ov_mod = ov
        for t, r in [(t1, r1), (t2, r2), (t3, r3)]:
            if t in ov_mod:
                ov_mod = ov_mod.replace(t, r, 1)
            else:
                # try CRLF
                t_crlf = t.replace("\n", "\r\n")
                r_crlf = r.replace("\n", "\r\n")
                if t_crlf in ov_mod:
                    ov_mod = ov_mod.replace(t_crlf, r_crlf, 1)

        with open("pages/page_overview.py", "w", encoding="utf-8") as f:
            f.write(ov_mod)
        print("Updated pages/page_overview.py with data-feature-id attributes!")

    # 2. page_advisor.py
    if os.path.exists("pages/page_advisor.py"):
        with open("pages/page_advisor.py", "r", encoding="utf-8") as f:
            adv = f.read()

        # advisor_trade_corridor on the results or single params
        t_adv1 = '<div id="adv-single-params"'
        r_adv1 = '<div id="adv-single-params" data-feature-id="advisor_trade_corridor"'
        
        t_adv2 = '<div id="adv-portfolio-results"'
        r_adv2 = '<div id="adv-portfolio-results" data-feature-id="advisor_track_dossier"'

        adv_mod = adv
        for t, r in [(t_adv1, r_adv1), (t_adv2, r_adv2)]:
            if t in adv_mod and r not in adv_mod:
                adv_mod = adv_mod.replace(t, r, 1)

        with open("pages/page_advisor.py", "w", encoding="utf-8") as f:
            f.write(adv_mod)
        print("Updated pages/page_advisor.py with data-feature-id attributes!")

    # 3. page_scanner.py
    if os.path.exists("pages/page_scanner.py"):
        with open("pages/page_scanner.py", "r", encoding="utf-8") as f:
            scn = f.read()
        if 'data-feature-id="scanner_full_pool"' not in scn:
            scn = scn.replace('<div class="card"', '<div class="card" data-feature-id="scanner_full_pool"', 1)
            with open("pages/page_scanner.py", "w", encoding="utf-8") as f:
                f.write(scn)
            print("Updated pages/page_scanner.py with data-feature-id attributes!")

    # 4. page_simons.py
    if os.path.exists("pages/page_simons.py"):
        with open("pages/page_simons.py", "r", encoding="utf-8") as f:
            sim = f.read()
        if 'data-feature-id="simons_fourier_lab"' not in sim:
            sim = sim.replace('<div class="card"', '<div class="card" data-feature-id="simons_fourier_lab"', 1)
            with open("pages/page_simons.py", "w", encoding="utf-8") as f:
                f.write(sim)
            print("Updated pages/page_simons.py with data-feature-id attributes!")

    # 5. page_trading.py
    if os.path.exists("pages/page_trading.py"):
        with open("pages/page_trading.py", "r", encoding="utf-8") as f:
            trd = f.read()
        if 'data-feature-id="trading_desk_execution"' not in trd:
            trd = trd.replace('<div class="card"', '<div class="card" data-feature-id="trading_desk_execution"', 1)
            with open("pages/page_trading.py", "w", encoding="utf-8") as f:
                f.write(trd)
            print("Updated pages/page_trading.py with data-feature-id attributes!")

    # 6. page_sq9.py
    if os.path.exists("pages/page_sq9.py"):
        with open("pages/page_sq9.py", "r", encoding="utf-8") as f:
            sq9 = f.read()
        if 'data-feature-id="gann_sq9_spiral"' not in sq9:
            sq9 = sq9.replace('<div class="card"', '<div class="card" data-feature-id="gann_sq9_spiral"', 1)
            with open("pages/page_sq9.py", "w", encoding="utf-8") as f:
                f.write(sq9)
            print("Updated pages/page_sq9.py with data-feature-id attributes!")

    # 7. page_dashboard.py
    if os.path.exists("pages/page_dashboard.py"):
        with open("pages/page_dashboard.py", "r", encoding="utf-8") as f:
            dsh = f.read()
        if 'data-feature-id="ephemeris_aspects"' not in dsh:
            dsh = dsh.replace('<div class="card"', '<div class="card" data-feature-id="ephemeris_aspects"', 1)
            with open("pages/page_dashboard.py", "w", encoding="utf-8") as f:
                f.write(dsh)
            print("Updated pages/page_dashboard.py with data-feature-id attributes!")

    # 8. page_sentiment.py
    if os.path.exists("pages/page_sentiment.py"):
        with open("pages/page_sentiment.py", "r", encoding="utf-8") as f:
            snt = f.read()
        if 'data-feature-id="options_smart_money"' not in snt:
            snt = snt.replace('<div class="card"', '<div class="card" data-feature-id="options_smart_money"', 1)
            with open("pages/page_sentiment.py", "w", encoding="utf-8") as f:
                f.write(snt)
            print("Updated pages/page_sentiment.py with data-feature-id attributes!")

if __name__ == "__main__":
    wire_features()
