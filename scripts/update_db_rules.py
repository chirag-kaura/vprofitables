import sqlite3
from datetime import datetime

def populate_all_features():
    conn = sqlite3.connect("market_data_v2.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS feature_access_rules (
            feature_id TEXT PRIMARY KEY,
            feature_name TEXT NOT NULL,
            page TEXT NOT NULL,
            category TEXT DEFAULT 'ANALYTICS',
            min_role TEXT DEFAULT 'PREMIUM',
            is_locked_for_free INTEGER DEFAULT 1,
            description TEXT,
            updated_at TEXT NOT NULL
        )
    """)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    features = [
        # ── Investment Advisor Granular Features ──
        ("adv_portfolio_summary", "📊 Portfolio Summary & Allocation", "advisor", "ADVISORY", "PREMIUM", 1, "Overall portfolio stats, allocation breakdown and verdict"),
        ("adv_planetary_env", "🌌 Current Planetary Environment", "advisor", "ASTRO", "PREMIUM", 1, "Cosmic weather, planetary aspects and transit alignments"),
        ("adv_nakshatra_timing", "🌙 Moon Nakshatra & Timing Widget", "advisor", "ASTRO", "PREMIUM", 1, "Lunar mansion, Abhijit Muhurat and Rahu Kaal execution windows"),
        ("adv_rec_header", "🎯 Recommendation Header & Conviction", "advisor", "ADVISORY", "FREE", 0, "Symbol identity, archetype tag and overall confidence percentage"),
        ("adv_score_bars", "📊 5-Engine Score Bars", "advisor", "ANALYTICS", "PREMIUM", 1, "Detailed score breakdown across Fund (25), Gann (20), Quant (20), Natal (20), Planet (15)"),
        ("adv_trade_levels", "💰 Actionable Trade Corridor & P&L", "advisor", "ADVISORY", "PREMIUM", 1, "Exact Entry, Stop Loss, Target 1, Target 2, R:R, Max Profit and Max Loss levels"),
        ("adv_combined_signal", "🌌 Combined Signal Matrix", "advisor", "QUANT", "PREMIUM", 1, "All 5 engines combined score matrix and total conviction bar"),
        ("adv_sector_index", "🏢 Sector Index & Divergence", "advisor", "MARKET", "FREE", 0, "Sector index trend, 20d performance and divergence warnings"),
        ("adv_reasons_regime", "📋 Buy/Sell Signals & Planetary Regime", "advisor", "ADVISORY", "PREMIUM", 1, "Reasons to buy, exit signals, planetary influence and holding horizon"),
        ("adv_ml_deep_signal", "🤖 ML Deep Signal & Continuation Engine", "advisor", "MACHINE_LEARNING", "PREMIUM", 1, "v4.0 ML reversal sparkline timeline and 20-EMA Dip & Rip continuation edge"),
        ("adv_tech_momentum", "📈 Tech Momentum & Wyckoff Accumulation", "advisor", "ANALYTICS", "PREMIUM", 1, "Wyckoff accumulation phase classification (Phase C Spring / SOS) and score"),
        ("adv_news_institutional", "🗞 FinBERT News & Bulk/Block Deals", "advisor", "SENTIMENT", "PREMIUM", 1, "30-day FinBERT NLP sentiment score and institutional bulk deal flow"),
        ("adv_gann_simons_trigger", "⚡ Gann + Simons Trigger & Session Reversals", "advisor", "GANN", "PREMIUM", 1, "Price & date buy/sell triggers with high-confluence session reversal times"),
        ("adv_charts_projections", "📈 Projections & S/R Charts", "advisor", "QUANT", "PREMIUM", 1, "Price projection, Support/Resistance and Natal aspect strength charts"),
        ("adv_single_deep_analysis", "🔬 Single Stock Deep Analysis Synthesis", "advisor", "RESEARCH", "PREMIUM", 1, "Comprehensive qualitative and quantitative deep research narratives"),

        # ── Market Overview Granular Features ──
        ("overview_market_regime", "🤖 Personalized AI Insights Summary", "overview", "REGIME", "FREE", 0, "Daily algorithmic market overview and regime verdict"),
        ("overview_sentiment", "📰 Relevant Market News & Flow", "overview", "SENTIMENT", "FREE", 0, "Real-time market sentiment and institutional news wire"),
        ("intraday_reversal_matrix", "📈 Index Overview & Day Range", "overview", "INTRADAY", "PREMIUM", 1, "Index OHLC day range slider and intraday index chart"),
        ("overview_watchlist_opps", "👁️ Watchlist & Tailored Opportunities", "overview", "ADVISORY", "PREMIUM", 1, "Personalized watchlist cards and high-confluence opportunities"),
        ("overview_risk_alerts", "🚨 Risk Alerts & Safeguards", "overview", "RISK", "FREE", 0, "Market volatility safeguards and portfolio protection warnings"),
        ("overview_most_bought", "🔥 Most Bought Equities", "overview", "DISCOVERY", "PREMIUM", 1, "Top traded and accumulated equities across NSE"),
        ("overview_top_movers", "🚀 Top Movers (Gainers & Losers)", "overview", "MARKET", "FREE", 0, "Top daily percentage gainers and losers across indices"),
        ("overview_sector_movements", "🌐 Sectorwise Movements Heatmap", "overview", "MARKET", "PREMIUM", 1, "Sectoral rotation and performance leaderboards"),

        # ── Specialized Analytical Engines ──
        ("scanner_full_pool", "📡 518-Instrument Multi-Confluence Scanner", "scanner", "SCANNER", "PREMIUM", 1, "Full universe market scanner with Gann, Astro & Quant confluence"),
        ("simons_fourier_lab", "🧠 Simons Cycle Lab & Harmonics", "simons", "QUANT", "PREMIUM", 1, "Fourier spectral energy decomposition and cycle projections"),
        ("trading_desk_execution", "⚡ Order Book & Demat Execution", "trading", "EXECUTION", "PREMIUM", 1, "Paper and broker live trade execution desk"),
        ("gann_sq9_spiral", "⬛ Gann Square of 9 Spiral Matrix", "sq9", "GANN", "PREMIUM", 1, "Cardinal and diagonal price vibration angles"),
        ("gann_time_cycles", "⏰ Gann Time Cycles Calculator", "sq9", "GANN", "PREMIUM", 1, "Pivot-based time cycle vibrations and projection dates"),
        ("confluence_scorer", "🎯 Confluence Scorer Engine", "sq9", "QUANT", "PREMIUM", 1, "Manual multi-parameter confluence scoring engine"),
        ("ephemeris_aspects", "🪐 Planetary Ephemeris & Geocentric Aspects", "dashboard", "ASTRO", "PREMIUM", 1, "Planetary longitude calculations and aspect windows"),
        ("options_smart_money", "📊 Participant Open Interest & Smart Money", "sentiment", "DERIVATIVES", "PREMIUM", 1, "FII vs DII vs Retail derivatives positioning and PCR")
    ]

    for f in features:
        c.execute("""
            INSERT OR REPLACE INTO feature_access_rules
            (feature_id, feature_name, page, category, min_role, is_locked_for_free, description, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (f[0], f[1], f[2], f[3], f[4], f[5], f[6], now_str))

    conn.commit()
    conn.close()
    print(f"Successfully populated {len(features)} granular feature access rules!")

if __name__ == "__main__":
    populate_all_features()
