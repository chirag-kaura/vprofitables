"""
fundamental_engine.py — Jim Simons meets Warren Buffett
Fundamental analysis for NSE/BSE equities via yfinance.info
Scores each instrument on 5 dimensions vs sector peers.
Two-table cache strategy:
  fundamental_cache   — one live row per symbol, adaptive TTL (1-day in earnings months Jan/Apr/Jul/Oct, else 7-day)
  fundamental_history — quarterly snapshots auto-saved for backtesting
                        (~120 rows/year for 30 equities, grows controlled)
"""

import json, math, sqlite3, os, sys
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.paths import DB_PATH

# ── Ensure fundamental cache table exists ─────────────────────────────────────
def _init_fundamental_table():
    """
    fundamental_cache  — one live row per symbol (current ratios, 7-day TTL)
    fundamental_history — quarterly snapshots for backtesting (one row per symbol per quarter)
    """
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")

        # ── Live cache: ONE row per symbol, replaced on every refresh ──────
        # PRIMARY KEY is symbol alone → INSERT OR REPLACE keeps exactly 30 rows
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fundamental_cache (
                symbol      TEXT PRIMARY KEY NOT NULL,
                cache_date  TEXT NOT NULL,
                payload     TEXT NOT NULL,
                updated_at  TEXT
            )
        """)

        # ── Historical snapshots: one row per (symbol, quarter) ──────────────
        # Stored automatically every quarter (when cache_date crosses a new quarter).
        # Used for backtesting: "what were TCS fundamentals in Q3 2024?"
        # Never deleted — grows ~30 rows per quarter (~120 rows/year for 30 equities)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fundamental_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol      TEXT    NOT NULL,
                quarter     TEXT    NOT NULL,   -- e.g. "2024-Q3"
                snapshot_date TEXT  NOT NULL,   -- exact date this snapshot was taken
                payload     TEXT    NOT NULL,   -- full JSON (same structure as cache)
                pe_ratio    REAL,               -- key ratios denormalised for fast SQL queries
                pb_ratio    REAL,
                roe         REAL,
                revenue_growth REAL,
                profit_margin  REAL,
                debt_equity    REAL,
                market_cap     REAL,
                total_score    REAL,            -- fundamental_score() result
                grade          TEXT,
                created_at  TEXT,
                UNIQUE(symbol, quarter)
            )
        """)

        # Indexes for backtesting queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fh_symbol  ON fundamental_history(symbol)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fh_quarter ON fundamental_history(quarter)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fh_sym_q   ON fundamental_history(symbol, quarter)")

        # ── Migrate: detect composite PK and collapse to single row per symbol ──
        # Check actual PRIMARY KEY definition — composite = old schema, single = new
        pk_info = conn.execute(
            "SELECT COUNT(*) FROM pragma_table_info('fundamental_cache') WHERE pk > 0"
        ).fetchone()
        pk_count = pk_info[0] if pk_info else 0

        if pk_count > 1:
            # Old composite PK (symbol, cache_date) detected — migrate now
            try:
                # Step 1: keep only the most recent row per symbol
                conn.execute("""
                    DELETE FROM fundamental_cache
                    WHERE rowid NOT IN (
                        SELECT MAX(rowid) FROM fundamental_cache GROUP BY symbol
                    )
                """)
                # Step 2: rebuild table with symbol-only PRIMARY KEY
                conn.execute("""
                    CREATE TABLE _fc_new (
                        symbol     TEXT PRIMARY KEY NOT NULL,
                        cache_date TEXT NOT NULL,
                        payload    TEXT NOT NULL,
                        updated_at TEXT
                    )
                """)
                conn.execute("""
                    INSERT INTO _fc_new (symbol, cache_date, payload, updated_at)
                    SELECT symbol, cache_date, payload, updated_at
                    FROM   fundamental_cache
                """)
                conn.execute("DROP TABLE fundamental_cache")
                conn.execute("ALTER TABLE _fc_new RENAME TO fundamental_cache")
                print("  [DB   ] fundamental_cache migrated: "
                      "composite PK -> symbol-only PK (1 row per symbol)")
            except Exception as _me:
                print(f"  [WARN ] fundamental_cache migration error: {_me}")

        conn.commit()
        conn.close()
    except Exception:
        pass

_init_fundamental_table()


# ── Raw ratio fields we pull from yfinance.info ───────────────────────────────
YF_FIELDS = [
    "trailingPE", "forwardPE", "priceToBook", "trailingEps", "forwardEps",
    "revenueGrowth", "earningsGrowth", "returnOnEquity", "returnOnAssets",
    "debtToEquity", "currentRatio", "quickRatio", "freeCashflow",
    "operatingCashflow", "totalRevenue", "grossMargins", "operatingMargins",
    "profitMargins", "marketCap", "enterpriseValue", "enterpriseToEbitda",
    "enterpriseToRevenue", "dividendYield", "payoutRatio",
    "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "fiftyDayAverage",
    "twoHundredDayAverage", "sharesOutstanding", "floatShares",
    "heldPercentInsiders",   # promoter/insider holding proxy
    "heldPercentInstitutions",
    "shortRatio", "beta",
    "bookValue", "priceToSalesTrailing12Months",
    "pegRatio",
]

DISPLAY_LABELS = {
    "trailingPE":               "P/E (TTM)",
    "forwardPE":                "P/E (Forward)",
    "priceToBook":              "P/B Ratio",
    "trailingEps":              "EPS (TTM)",
    "forwardEps":               "EPS (Forward)",
    "revenueGrowth":            "Revenue Growth YoY",
    "earningsGrowth":           "Earnings Growth YoY",
    "returnOnEquity":           "ROE",
    "returnOnAssets":           "ROA",
    "debtToEquity":             "Debt / Equity",
    "currentRatio":             "Current Ratio",
    "freeCashflow":             "Free Cash Flow",
    "grossMargins":             "Gross Margin",
    "operatingMargins":         "Operating Margin",
    "profitMargins":            "Net Margin",
    "marketCap":                "Market Cap",
    "enterpriseToEbitda":       "EV / EBITDA",
    "dividendYield":            "Dividend Yield",
    "fiftyTwoWeekHigh":         "52W High",
    "fiftyTwoWeekLow":          "52W Low",
    "fiftyDayAverage":          "50D SMA",
    "twoHundredDayAverage":     "200D SMA",
    "heldPercentInsiders":      "Promoter / Insider %",
    "heldPercentInstitutions":  "Institutional %",
    "beta":                     "Beta",
    "pegRatio":                 "PEG Ratio",
    "priceToSalesTrailing12Months": "P/S Ratio",
}

FORMAT_RULES = {
    # field: (format_type, multiplier)
    # format_type: "pct", "cr" (crores), "x" (multiple), "raw"
    "trailingPE":   ("x", 1),
    "forwardPE":    ("x", 1),
    "priceToBook":  ("x", 1),
    "trailingEps":  ("inr", 1),
    "forwardEps":   ("inr", 1),
    "revenueGrowth": ("pct", 100),
    "earningsGrowth": ("pct", 100),
    "returnOnEquity": ("pct", 100),
    "returnOnAssets": ("pct", 100),
    "debtToEquity": ("x", 0.01),       # yfinance returns as %, divide by 100 → ratio
    "currentRatio": ("x", 1),
    "freeCashflow": ("cr", 1e-7),       # rupees → crores
    "grossMargins": ("pct", 100),
    "operatingMargins": ("pct", 100),
    "profitMargins": ("pct", 100),
    "marketCap":    ("cr", 1e-7),
    "enterpriseToEbitda": ("x", 1),
    "dividendYield": ("pct", 1),        # yfinance already returns as % (e.g. 2.27 not 0.0227)
    "fiftyTwoWeekHigh": ("inr", 1),
    "fiftyTwoWeekLow":  ("inr", 1),
    "fiftyDayAverage":  ("inr", 1),
    "twoHundredDayAverage": ("inr", 1),
    "heldPercentInsiders": ("pct", 100),
    "heldPercentInstitutions": ("pct", 100),
    "beta": ("raw", 1),
    "pegRatio": ("x", 1),
    "priceToSalesTrailing12Months": ("x", 1),
}


def _fmt(field: str, val) -> str:
    """Format a raw yfinance value for display."""
    if val is None or val != val:   # None or NaN
        return "—"
    try:
        val = float(val)
        ft, mult = FORMAT_RULES.get(field, ("raw", 1))
        v = val * mult
        if ft == "pct":   return f"{v:.1f}%"
        if ft == "inr":   return f"₹{v:,.2f}"
        if ft == "cr":    return f"₹{v:,.0f} Cr"
        if ft == "x":     return f"{v:.2f}x"
        return f"{v:.2f}"
    except Exception:
        return str(val)


# ══════════════════════════════════════════════════════════════════════════════
# 1. FETCH — yfinance with SQLite cache (24h TTL)
# ══════════════════════════════════════════════════════════════════════════════

def fetch_fundamentals(symbol: str, yf_symbol: str, force_refresh: bool = False) -> Dict:
    """
    Fetch fundamental ratios for a symbol.
    Returns cached data if < 24h old, else fetches from yfinance.
    """
    today = date.today().isoformat()

    # ── Cache check: adaptive TTL ────────────────────────────────────────────
    # Fundamentals (PE, ROE, D/E) change quarterly at most.
    # During earnings season (Jan/Apr/Jul/Oct) use a tighter 1-day TTL so
    # freshly-released quarterly results are picked up quickly.
    # Outside earnings season, 7 days avoids unnecessary yfinance calls.
    _earnings_months = {1, 4, 7, 10}
    CACHE_TTL_DAYS = 1 if date.today().month in _earnings_months else 7
    if not force_refresh:
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5)
            row = conn.execute(
                "SELECT payload, cache_date FROM fundamental_cache WHERE symbol=?",
                (symbol,)
            ).fetchone()
            conn.close()
            if row:
                cached_date = date.fromisoformat(row[1][:10])
                age_days    = (date.today() - cached_date).days
                if age_days < CACHE_TTL_DAYS:
                    cached = json.loads(row[0])
                    cached["source"]    = f"CACHE ({age_days}d old)"
                    cached["cache_age"] = age_days
                    return cached
        except Exception:
            pass

    # Fetch from yfinance
    data = {"symbol": symbol, "yf_symbol": yf_symbol, "fetch_date": today,
            "source": "yfinance", "error": None, "ratios": {}, "formatted": {}}
    try:
        import yfinance as yf
        ticker = yf.Ticker(yf_symbol)
        info   = ticker.info or {}

        for field in YF_FIELDS:
            raw = info.get(field)
            if raw is not None and raw == raw:   # skip NaN
                data["ratios"][field] = raw
                data["formatted"][field] = _fmt(field, raw)

        # Derived: ROE from income/equity if yfinance didn't return it
        if "returnOnEquity" not in data["ratios"]:
            ni  = info.get("netIncomeToCommon")
            eq  = info.get("totalStockholderEquity") or info.get("bookValue", 0) * info.get("sharesOutstanding", 0)
            if ni and eq and float(eq) > 0:
                roe = float(ni) / float(eq)
                data["ratios"]["returnOnEquity"] = roe
                data["formatted"]["returnOnEquity"] = _fmt("returnOnEquity", roe)

        # Derived: Current Ratio from balance sheet if missing
        if "currentRatio" not in data["ratios"]:
            ca = info.get("totalCurrentAssets")
            cl = info.get("totalCurrentLiabilities")
            if ca and cl and float(cl) > 0:
                cr = float(ca) / float(cl)
                data["ratios"]["currentRatio"] = cr
                data["formatted"]["currentRatio"] = _fmt("currentRatio", cr)

        # Derived: 52W position (where is price in its annual range)
        hi = data["ratios"].get("fiftyTwoWeekHigh", 0)
        lo = data["ratios"].get("fiftyTwoWeekLow", 0)
        price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
        if hi > lo > 0 and price > 0:
            data["ratios"]["week52_position_pct"] = round((price - lo) / (hi - lo) * 100, 1)
            data["formatted"]["week52_position_pct"] = f"{data['ratios']['week52_position_pct']:.1f}%"

        # Derived: price vs 200 SMA
        sma200 = data["ratios"].get("twoHundredDayAverage", 0)
        if sma200 > 0 and price > 0:
            vs200 = round((price / sma200 - 1) * 100, 2)
            data["ratios"]["vs_sma200_pct"] = vs200
            data["formatted"]["vs_sma200_pct"] = f"{vs200:+.1f}%"

        data["current_price"] = round(price, 2)
        data["company_name"]  = info.get("longName") or info.get("shortName") or symbol
        data["sector_yf"]     = info.get("sector", "")
        data["industry_yf"]   = info.get("industry", "")

    except Exception as e:
        data["error"] = str(e)
        data["source"] = "error"

    # ── Write to live cache (INSERT OR REPLACE → always exactly 1 row per symbol) ─
    payload_json = json.dumps(data)
    now_iso      = datetime.now().isoformat()
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        conn.execute(
            """INSERT OR REPLACE INTO fundamental_cache
               (symbol, cache_date, payload, updated_at)
               VALUES (?,?,?,?)""",
            (symbol, today, payload_json, now_iso)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

    # ── Write quarterly snapshot for backtesting ─────────────────────────────
    # Quarter format: "2024-Q3". Only stores a new row when quarter changes.
    # This builds a historical record without growing the live cache.
    try:
        d_obj   = date.fromisoformat(today)
        quarter = f"{d_obj.year}-Q{(d_obj.month - 1) // 3 + 1}"
        scores  = fundamental_score(data)
        ratios  = data.get("ratios", {})
        conn2   = sqlite3.connect(DB_PATH, timeout=5)
        conn2.execute("""
            INSERT OR IGNORE INTO fundamental_history
                (symbol, quarter, snapshot_date, payload,
                 pe_ratio, pb_ratio, roe, revenue_growth, profit_margin,
                 debt_equity, market_cap, total_score, grade, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            symbol, quarter, today, payload_json,
            ratios.get("trailingPE"),
            ratios.get("priceToBook"),
            ratios.get("returnOnEquity"),
            ratios.get("revenueGrowth"),
            ratios.get("profitMargins"),
            ratios.get("debtToEquity"),
            ratios.get("marketCap"),
            scores["total_score"],
            scores["grade"],
            now_iso,
        ))
        conn2.commit()
        conn2.close()
    except Exception:
        pass

    return data


# ══════════════════════════════════════════════════════════════════════════════
# 2. SCORE — 5 dimensions, 0-100 per dimension, weighted total 0-25
# ══════════════════════════════════════════════════════════════════════════════

def _safe(d: dict, key: str, default=None):
    v = d.get("ratios", {}).get(key)
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return default
    return v


def score_value(data: dict) -> float:
    """Value score 0-100. Lower P/E, P/B, EV/EBITDA = better."""
    pts = 0; n = 0
    pe = _safe(data, "trailingPE")
    if pe and pe > 0:
        # Excellent <15, Good <25, Fair <40, Poor >40
        pts += max(0, min(100, 100 - (pe - 10) * 2.5))
        n += 1
    pb = _safe(data, "priceToBook")
    if pb and pb > 0:
        pts += max(0, min(100, 100 - (pb - 1) * 15))
        n += 1
    ev_ebitda = _safe(data, "enterpriseToEbitda")
    if ev_ebitda and ev_ebitda > 0:
        pts += max(0, min(100, 100 - (ev_ebitda - 8) * 4))
        n += 1
    peg = _safe(data, "pegRatio")
    if peg and peg > 0:
        pts += max(0, min(100, 100 - (peg - 1) * 30))
        n += 1
    return round(pts / n, 1) if n > 0 else 50.0


def score_growth(data: dict) -> float:
    """Growth score 0-100. Higher YoY revenue + earnings growth = better."""
    pts = 0; n = 0
    rev = _safe(data, "revenueGrowth")
    if rev is not None:
        pts += max(0, min(100, 50 + rev * 300))   # 0% → 50pts, 20% → 110→clipped 100
        n += 1
    earn = _safe(data, "earningsGrowth")
    if earn is not None:
        pts += max(0, min(100, 50 + earn * 250))
        n += 1
    fwd_pe = _safe(data, "forwardPE")
    tr_pe  = _safe(data, "trailingPE")
    if fwd_pe and tr_pe and fwd_pe > 0 and tr_pe > 0:
        # Earnings expected to grow if forward P/E < trailing P/E
        growth_implied = (tr_pe / fwd_pe - 1) * 100
        pts += max(0, min(100, 50 + growth_implied * 3))
        n += 1
    return round(pts / n, 1) if n > 0 else 50.0


def score_quality(data: dict) -> float:
    """Quality score 0-100. ROE, margins, low debt, positive FCF."""
    pts = 0; n = 0
    roe = _safe(data, "returnOnEquity")
    if roe is not None:
        pts += max(0, min(100, roe * 500))   # 20% ROE → 100pts (yfinance: decimal)
        n += 1
    margin = _safe(data, "profitMargins")
    if margin is not None:
        pts += max(0, min(100, margin * 500))
        n += 1
    de_raw = _safe(data, "debtToEquity")
    if de_raw is not None:
        de = de_raw * 0.01  # yfinance returns as %, convert to ratio
        pts += max(0, min(100, 100 - de * 20))  # 0 debt → 100, 5x → 0
        n += 1
    fcf = _safe(data, "freeCashflow")
    if fcf is not None:
        pts += 80 if fcf > 0 else 20
        n += 1
    cur = _safe(data, "currentRatio")
    if cur is not None:
        pts += max(0, min(100, cur * 40))   # 2.5 current ratio → 100pts
        n += 1
    return round(pts / n, 1) if n > 0 else 50.0


def score_momentum(data: dict) -> float:
    """Momentum score 0-100. 52W position, vs 200 SMA, beta."""
    pts = 0; n = 0
    pos52 = _safe(data, "week52_position_pct")
    if pos52 is not None:
        # Near 52W high with uptrend = bullish (but not at all-time high = overbought)
        if pos52 >= 80:
            pts += 85     # strong — near highs but not extreme
        elif pos52 >= 60:
            pts += 70
        elif pos52 >= 40:
            pts += 55
        elif pos52 >= 20:
            pts += 35
        else:
            pts += 20     # near 52W low — potential mean reversion or downtrend
        n += 1
    vs200 = _safe(data, "vs_sma200_pct")
    if vs200 is not None:
        pts += max(0, min(100, 50 + vs200 * 2))  # +10% above 200SMA → 70pts
        n += 1
    beta = _safe(data, "beta")
    if beta is not None and beta > 0:
        # Beta 1.0–1.3 = ideal for swing trades; >2 = too risky; <0.5 = too slow
        pts += max(0, min(100, 100 - abs(beta - 1.1) * 40))
        n += 1
    return round(pts / n, 1) if n > 0 else 50.0


def score_promoter(data: dict) -> float:
    """Governance score. High insider holding + institutional interest = trust."""
    pts = 0; n = 0
    insider = _safe(data, "heldPercentInsiders")
    if insider is not None:
        # 50-75% promoter holding ideal for Indian markets
        if insider >= 0.5:
            pts += 90
        elif insider >= 0.35:
            pts += 70
        elif insider >= 0.20:
            pts += 50
        else:
            pts += 25
        n += 1
    inst = _safe(data, "heldPercentInstitutions")
    if inst is not None:
        pts += max(0, min(100, inst * 200))  # 50% institutional = 100pts
        n += 1
    return round(pts / n, 1) if n > 0 else 50.0


def fundamental_score(data: dict) -> Dict:
    """
    Compute all 5 dimension scores and a weighted total (0-100).
    Returns dict with per-dimension scores + final score.
    """
    v  = score_value(data)
    g  = score_growth(data)
    q  = score_quality(data)
    m  = score_momentum(data)
    pr = score_promoter(data)

    # Weighted total: quality+growth matter most for stock selection
    total = round(v * 0.20 + g * 0.25 + q * 0.30 + m * 0.15 + pr * 0.10, 1)

    if total >= 75:   verdict, grade = "STRONG BUY",  "A+"
    elif total >= 60: verdict, grade = "BUY",          "A"
    elif total >= 50: verdict, grade = "HOLD",         "B"
    elif total >= 35: verdict, grade = "WEAK",         "C"
    else:             verdict, grade = "AVOID",        "D"

    return {
        "value_score":    v,
        "growth_score":   g,
        "quality_score":  q,
        "momentum_score": m,
        "promoter_score": pr,
        "total_score":    total,
        "verdict":        verdict,
        "grade":          grade,
        "weights":        {"value": 20, "growth": 25, "quality": 30, "momentum": 15, "promoter": 10},
    }


# ══════════════════════════════════════════════════════════════════════════════
# 3. PEER COMPARISON — rank within sector
# ══════════════════════════════════════════════════════════════════════════════

def get_sector_peers(symbol: str) -> List[Dict]:
    """Return all EQUITY instruments in the same sector as symbol."""
    try:
        from data.instruments import ALL_INSTRUMENTS
        target = ALL_INSTRUMENTS.get(symbol)
        if not target:
            return []
        sector = target.sector
        return [
            {"symbol": s, "name": i.name, "yf_symbol": i.yfinance_symbol}
            for s, i in ALL_INSTRUMENTS.items()
            if i.instrument_type == "EQUITY" and i.sector == sector and s != symbol
        ]
    except Exception:
        return []


def get_sector_index(sector: str) -> Optional[Dict]:
    """Return the most relevant index instrument for a given sector."""
    SECTOR_INDEX_MAP = {
        "Banking":   "BANKNIFTY",
        "IT":        "NIFTYIT",
        "Pharma":    "NIFTYPHARMA",
        "Auto":      "NIFTY50",
        "FMCG":      "NIFTY50",
        "Finance":   "BANKNIFTY",
        "Insurance": "BANKNIFTY",
        "Metals":    "NIFTY50",
        "Cement":    "NIFTY50",
        "Oil & Gas": "NIFTY50",
        "Power":     "NIFTY50",
        "Mining":    "NIFTY50",
    }
    try:
        from data.instruments import ALL_INSTRUMENTS
        idx_sym = SECTOR_INDEX_MAP.get(sector, "NIFTY50")
        inst    = ALL_INSTRUMENTS.get(idx_sym)
        if inst:
            return {"symbol": idx_sym, "name": inst.name, "yf_symbol": inst.yfinance_symbol}
    except Exception:
        pass
    return None


def compare_vs_peers(symbol: str, yf_symbol: str) -> Dict:
    """
    Fetch fundamentals for symbol + all peers, score all, rank symbol.
    Returns full comparison table with per-metric percentile ranks.
    """
    # Get all peers in sector
    peers = get_sector_peers(symbol)

    # Fetch target
    target_data = fetch_fundamentals(symbol, yf_symbol)
    target_scores = fundamental_score(target_data)

    # Fetch peers (use cache — fast if already fetched today)
    peer_results = []
    for p in peers[:8]:   # cap at 8 peers for performance
        try:
            pdata   = fetch_fundamentals(p["symbol"], p["yf_symbol"])
            pscores = fundamental_score(pdata)
            peer_results.append({
                "symbol":  p["symbol"],
                "name":    p["name"],
                "ratios":  pdata.get("ratios", {}),
                "scores":  pscores,
                "price":   pdata.get("current_price", 0),
            })
        except Exception:
            pass

    # Build comparison metrics table
    COMPARE_FIELDS = [
        ("trailingPE",       "P/E (TTM)",        "lower"),
        ("priceToBook",      "P/B",              "lower"),
        ("returnOnEquity",   "ROE",              "higher"),
        ("profitMargins",    "Net Margin",       "higher"),
        ("debtToEquity",     "Debt/Equity",      "lower"),
        ("revenueGrowth",    "Rev Growth",       "higher"),
        ("earningsGrowth",   "EPS Growth",       "higher"),
        ("dividendYield",    "Div Yield",        "higher"),
        ("week52_position_pct", "52W Position",  "higher"),
    ]

    # Compute percentile rank for target on each metric vs peers
    target_ratios = target_data.get("ratios", {})
    comparison = []
    for field, label, direction in COMPARE_FIELDS:
        tv = target_ratios.get(field)
        if tv is None:
            continue
        peer_vals = [p["ratios"].get(field) for p in peer_results if p["ratios"].get(field) is not None]
        all_vals  = peer_vals + [tv]
        if not all_vals:
            continue

        if direction == "higher":
            rank = sum(1 for v in peer_vals if v <= tv)
        else:
            rank = sum(1 for v in peer_vals if v >= tv)

        total_peers = len(peer_vals)
        percentile  = round(rank / max(total_peers, 1) * 100, 0) if total_peers > 0 else 50

        comparison.append({
            "field":      field,
            "label":      label,
            "direction":  direction,
            "target_val": tv,
            "target_fmt": _fmt(field, tv),
            "peer_avg":   round(sum(peer_vals) / len(peer_vals), 4) if peer_vals else None,
            "peer_avg_fmt": _fmt(field, sum(peer_vals)/len(peer_vals)) if peer_vals else "—",
            "peer_min":   min(peer_vals) if peer_vals else None,
            "peer_max":   max(peer_vals) if peer_vals else None,
            "percentile": percentile,
            "rank":       rank + 1,
            "out_of":     total_peers + 1,
            "is_best":    (rank == total_peers and total_peers > 0),
            "is_worst":   (rank == 0 and total_peers > 0),
        })

    # Overall peer rank by total score
    all_scores = [(symbol, target_scores["total_score"])] + \
                 [(p["symbol"], p["scores"]["total_score"]) for p in peer_results]
    all_scores.sort(key=lambda x: x[1], reverse=True)
    peer_rank = next((i+1 for i, (s, _) in enumerate(all_scores) if s == symbol), 1)

    return {
        "symbol":       symbol,
        "sector":       _get_sector(symbol),
        "target":       {
            "ratios":   target_ratios,
            "formatted": target_data.get("formatted", {}),
            "scores":   target_scores,
            "price":    target_data.get("current_price", 0),
            "name":     target_data.get("company_name", symbol),
        },
        "peers":        peer_results,
        "comparison":   comparison,
        "peer_rank":    peer_rank,
        "peer_total":   len(all_scores),
        "all_scores":   [{"symbol": s, "score": sc} for s, sc in all_scores],
        "sector_index": get_sector_index(_get_sector(symbol)),
    }


def _get_sector(symbol: str) -> str:
    try:
        from data.instruments import ALL_INSTRUMENTS
        inst = ALL_INSTRUMENTS.get(symbol)
        return inst.sector if inst else ""
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════════════════════
# 4. ADVISOR INTEGRATION — returns 0-25 score for Investment Advisor
# ══════════════════════════════════════════════════════════════════════════════

def fundamental_advisor_score(symbol: str, yf_symbol: str) -> Dict:
    """
    Returns a 0-25 fundamental score suitable for plugging into
    the Investment Advisor's confidence scoring system.
    Also returns key ratios for display in the recommendation card.
    """
    try:
        data   = fetch_fundamentals(symbol, yf_symbol)
        scores = fundamental_score(data)
        ratios = data.get("ratios", {})
        fmt    = data.get("formatted", {})

        # Scale 0-100 total → 0-25 for advisor
        adv_score = round(scores["total_score"] / 4, 1)

        # Key signals for buy reasons
        signals = []
        roe = ratios.get("returnOnEquity", 0) or 0
        if roe > 0.15:
            signals.append(f"ROE {roe*100:.1f}% — above 15% threshold")
        pe = ratios.get("trailingPE")
        if pe and pe < 20:
            signals.append(f"P/E {pe:.1f}x — attractively valued")
        elif pe and pe > 50:
            signals.append(f"P/E {pe:.1f}x — expensive vs earnings")
        rev_g = ratios.get("revenueGrowth", 0) or 0
        if rev_g > 0.10:
            signals.append(f"Revenue growing {rev_g*100:.1f}% YoY")
        de = ratios.get("debtToEquity")
        if de is not None and de < 0.5:
            signals.append(f"Low debt (D/E {de:.2f}x) — balance sheet strength")
        elif de is not None and de > 2.0:
            signals.append(f"High debt (D/E {de:.2f}x) — leverage risk")
        fcf = ratios.get("freeCashflow", 0) or 0
        if fcf > 0:
            signals.append(f"Positive free cash flow")

        return {
            "fundamental_score": adv_score,
            "grade":             scores["grade"],
            "verdict":           scores["verdict"],
            "breakdown": {
                "value":    scores["value_score"],
                "growth":   scores["growth_score"],
                "quality":  scores["quality_score"],
                "momentum": scores["momentum_score"],
                "promoter": scores["promoter_score"],
            },
            "key_ratios": {
                "pe":      fmt.get("trailingPE", "—"),
                "pb":      fmt.get("priceToBook", "—"),
                "roe":     fmt.get("returnOnEquity", "—"),
                "de":      fmt.get("debtToEquity", "—"),
                "rev_g":   fmt.get("revenueGrowth", "—"),
                "margin":  fmt.get("profitMargins", "—"),
                "div":     fmt.get("dividendYield", "—"),
                "mktcap":  fmt.get("marketCap", "—"),
            },
            "signals": signals[:5],
            "error":   data.get("error"),
        }
    except Exception as e:
        return {"fundamental_score": 12, "grade": "B", "verdict": "HOLD",
                "breakdown": {}, "key_ratios": {}, "signals": [], "error": str(e)}
