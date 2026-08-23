# VERSION: 5.0-OPTIMISED
"""
download_history.py  —  Full Historical Data Download + ZigZag Pivot Detection
================================================================================
Downloads complete OHLCV history for instruments from Yahoo Finance.
Start date: max(inception_date, 2000-01-01) — Yahoo .NS unreliable before 2000.
For pre-2000 inceptions: ATL/ATH seeded from instruments.py as STATIC pivots.

USAGE
─────
  Test mode — 40 key symbols (5 indices + 30 stocks + 5 MCX):
      python download_history.py --test

  Full download (all ~257 symbols):
      python download_history.py

  Top-up stale data only:
      python download_history.py --topup
      python download_history.py --test --topup

  Force full re-download:
      python download_history.py --force

  Pivot detection only (no download):
      python download_history.py --pivots-only

  Specific symbols:
      python download_history.py --symbols NIFTY50 GOLD HDFCBANK

PERFORMANCE
───────────
  • Batch yf.download()  — 8 symbols per HTTP request, far fewer rate-limit failures
  • Grouped by type      — indices/equities/futures batched separately (better YF compat)
  • WAL journal mode     — app.py reads never blocked by writes
  • 32 MB cache + mmap   — fast queries on million+ row table
  • executemany chunks   — 2000 rows per DB transaction
  • INSERT OR IGNORE     — safe to re-run anytime, no duplicates
  • Parallel pivots      — 4-thread ThreadPoolExecutor for ZigZag detection

PRE-2000 SYMBOLS
────────────────
  Yahoo Finance .NS data starts ~2000. For symbols with earlier inception:
    1. Download from 2000-01-01 onwards (reliable Yahoo data)
    2. Manually-researched ATL/ATH/date already in instruments.py is seeded
       as STATIC pivot_levels rows — never overwritten by AUTO detection
  Result: ZigZag AUTO pivots cover 2000-present; STATIC rows cover full history.
"""

from __future__ import annotations
import os, sys, time, sqlite3, math, argparse, io, threading, random
from datetime import date, datetime, timedelta
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.platform == "win32":
    import io
    if sys.stdout is not None:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        elif hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.stderr is not None:
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        elif hasattr(sys.stderr, "buffer"):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Path setup ───────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

try:
    from core.scheduler import DB_PATH, init_db, seed_static_pivots, is_market_day
except ImportError as e:
    print(f"\n  [ERROR] Cannot import core.scheduler: {e}")
    print(f"  Run from project root: cd <gann_folder> && python download_history.py\n")
    sys.exit(1)

try:
    from data.instruments import ALL_INSTRUMENTS
except ImportError as e:
    print(f"\n  [ERROR] Cannot import data.instruments: {e}\n")
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════════════════
# TEST SYMBOL SET — 5 indices + 30 equities + 5 MCX = 40 total
# ══════════════════════════════════════════════════════════════════════════════
TEST_SYMBOLS = [
    # ── 5 KEY INDICES ────────────────────────────────────────────────────────
    "NIFTY50",      # Broad market anchor — ATL 854 (1996), manually seeded
    "BANKNIFTY",    # Banking sector — data from 2000-09-15
    "NIFTYIT",      # Tech sector — ATL 891 (1999), manually seeded
    "NIFTYPHARMA",  # Pharma sector
    "NIFTYAUTO",    # Auto sector

    # ── 30 KEY EQUITIES ──────────────────────────────────────────────────────
    # Banking (5)
    "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK",
    # IT (5)
    "TCS", "INFY", "WIPRO", "HCLTECH", "TECHM",
    # Energy / Power (5)
    "RELIANCE", "ONGC", "NTPC", "POWERGRID", "COALINDIA",
    # FMCG / Pharma (5)
    "HINDUNILVR", "ITC", "SUNPHARMA", "DRREDDY", "CIPLA",
    # Auto (4)
    "MARUTI", "BAJAJ-AUTO", "M&M", "TATAMOTORS",
    # Metals / Cement (3)
    "TATASTEEL", "HINDALCO", "ULTRACEMCO",
    # Finance / Insurance (3)
    "BAJFINANCE", "HDFCLIFE", "SBILIFE",

    # ── 5 KEY MCX COMMODITIES ────────────────────────────────────────────────
    "GOLD", "SILVER", "CRUDEOIL", "NATURALGAS", "COPPER",
]

# ── Config ────────────────────────────────────────────────────────────────────
YF_MIN_DATE      = date(2000, 1, 1)   # Yahoo .NS data unreliable before 2000
BATCH_SIZE       = 40                 # symbols per yf.download() call
BATCH_SLEEP      = 6.0                # seconds between batches (rate-limit safety)
FALLBACK_SLEEP   = 1.2                # seconds between individual fallback calls
WRITE_CHUNK      = 2000               # rows per DB transaction (fast bulk insert)
MIN_ROWS_PIVOTS  = 60                 # minimum rows for ZigZag pivot detection
ZIGZAG_MINOR_PCT = 3.0                # minor swing threshold %
ZIGZAG_MAJOR_PCT = 8.0                # major swing threshold %
PIVOT_WORKERS    = 4                  # parallel threads for pivot detection
FULL_THRESHOLD   = 30                 # fewer rows = treat as full download needed

_print_lock = threading.Lock()

def _log(msg: str, end: str = "\n"):
    with _print_lock:
        print(msg, end=end, flush=True)


# ══════════════════════════════════════════════════════════════════════════════
# DATABASE — WAL mode + covering indexes
# ══════════════════════════════════════════════════════════════════════════════

def open_db(path=None):
    """Open SQLite with performance PRAGMAs. WAL = app reads never blocked."""
    conn = sqlite3.connect(path or DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-32000")    # 32 MB page cache
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=268435456")  # 256 MB memory-mapped I/O
    conn.execute("PRAGMA busy_timeout=30000")   # 30 s retry on WAL lock
    return conn


def ensure_schema_and_indexes():
    """Create tables + covering indexes. Idempotent — safe to call every run."""
    conn = open_db()
    c = conn.cursor()

    # daily_prices — OHLCV history
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_prices (
            symbol      TEXT    NOT NULL,
            trade_date  TEXT    NOT NULL,
            open        REAL,
            high        REAL,
            low         REAL,
            close       REAL,
            volume      INTEGER,
            change_pct  REAL,
            updated_at  TEXT,
            PRIMARY KEY (symbol, trade_date)
        )
    """)

    # pivot_levels — named swing anchors per instrument
    c.execute("""
        CREATE TABLE IF NOT EXISTS pivot_levels (
            symbol      TEXT    NOT NULL,
            label       TEXT    NOT NULL,
            pivot_price REAL    NOT NULL,
            pivot_date  TEXT    NOT NULL,
            source      TEXT    DEFAULT 'STATIC',
            description TEXT    DEFAULT '',
            updated_at  TEXT,
            PRIMARY KEY (symbol, label)
        )
    """)

    # ── Covering indexes ──────────────────────────────────────────────────────
    # (symbol, trade_date DESC) → ORDER BY trade_date DESC LIMIT N  in O(log n)
    # Without this index, every "latest price" query is a full table scan.
    c.execute("CREATE INDEX IF NOT EXISTS idx_dp_sym_date  ON daily_prices(symbol, trade_date DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_dp_sym       ON daily_prices(symbol)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_dp_date      ON daily_prices(trade_date)")
    # Partial index skips NULL close rows (sparse commodity data)
    c.execute("CREATE INDEX IF NOT EXISTS idx_dp_sym_close ON daily_prices(symbol, trade_date) WHERE close IS NOT NULL")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pl_sym       ON pivot_levels(symbol)")

    conn.commit()
    conn.close()
    _log("  [DB   ] Schema + indexes verified")


def get_symbol_row_counts() -> dict:
    """Return {symbol: {count, first, last}} for every symbol in DB."""
    conn = open_db()
    rows = conn.execute(
        "SELECT symbol, COUNT(*), MIN(trade_date), MAX(trade_date) "
        "FROM daily_prices GROUP BY symbol"
    ).fetchall()
    conn.close()
    return {r[0]: {"count": r[1], "first": r[2], "last": r[3]} for r in rows}


def get_db_summary() -> dict:
    """Return stats for the status banner."""
    conn = open_db()
    total = conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
    syms  = conn.execute("SELECT COUNT(DISTINCT symbol) FROM daily_prices").fetchone()[0]
    pivs  = conn.execute("SELECT COUNT(*) FROM pivot_levels").fetchone()[0]
    conn.close()
    return {"total_rows": total, "symbols": syms, "pivots": pivs}


# ══════════════════════════════════════════════════════════════════════════════
# YAHOO FINANCE DOWNLOAD
# ══════════════════════════════════════════════════════════════════════════════

class _Silence:
    """Suppress yfinance stderr noise during downloads."""
    def __enter__(self):
        self._old = sys.stderr
        sys.stderr = io.StringIO()
    def __exit__(self, *_):
        sys.stderr = self._old


def _df_to_rows(df, yf_sym=None) -> list:
    """
    Convert yfinance DataFrame → list of
    (date_str, open, high, low, close, volume, change_pct).

    Handles all yfinance column structures:
    - Flat columns  (single Ticker.history())
    - MultiIndex (ticker, price_field)  — yf.download group_by='ticker'
    - MultiIndex (price_field, ticker)  — yf.download default
    """
    try:
        import pandas as pd
    except ImportError:
        return []

    if df is None or df.empty:
        return []

    PRICE_FIELDS = {"open","high","low","close","volume","Open","High","Low","Close","Volume"}

    if isinstance(df.columns, pd.MultiIndex):
        lvl0 = df.columns.get_level_values(0).tolist()
        lvl1 = df.columns.get_level_values(1).tolist()
        lvl0_set = set(lvl0)

        # Case A: multi-ticker — (ticker, price_field)
        if yf_sym and yf_sym in lvl0_set:
            try:
                sub = df[yf_sym]
                if isinstance(sub.columns, pd.MultiIndex):
                    sub.columns = sub.columns.get_level_values(-1)
                sub.columns = [c.lower() for c in sub.columns]
                df = sub
            except Exception:
                return []
        # Case B: single-ticker — (price_field, ticker)
        elif lvl0_set & PRICE_FIELDS:
            df = df.droplevel(1, axis=1)
            df.columns = [c.lower() for c in df.columns]
        else:
            try:
                df = df.droplevel(1, axis=1)
                df.columns = [c.lower() for c in df.columns]
            except Exception:
                return []
    else:
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]

    rows = []
    prev_close = None
    for dt_idx, row in df.iterrows():
        try:
            dt_str = dt_idx.strftime("%Y-%m-%d") if hasattr(dt_idx, "strftime") else str(dt_idx)[:10]
            
            try:
                dt_obj = date.fromisoformat(dt_str)
                if not is_market_day(dt_obj):
                    continue
            except Exception:
                pass

            o   = float(row.get("open")  or 0) or None
            h   = float(row.get("high")  or 0) or None
            lo  = float(row.get("low")   or 0) or None
            cl  = float(row.get("close") or 0) or None
            vol = int(row.get("volume")  or 0) or None

            if not cl:
                prev_close = None
                continue

            chg = round((cl - prev_close) / prev_close * 100, 4) if prev_close else None
            prev_close = cl
            rows.append((dt_str, o, h, lo, cl, vol, chg))
        except Exception:
            continue

    return rows


def download_batch(sym_to_yf: dict, start: date) -> dict:
    """
    Download a batch of symbols in ONE yf.download() HTTP request.
    sym_to_yf: {our_symbol: yfinance_ticker}
    Returns: {our_symbol: [rows]}
    """
    try:
        import yfinance as yf
    except ImportError:
        _log("  [ERROR] yfinance not installed. Run: pip install yfinance")
        return {}

    yf_to_sym  = {v: k for k, v in sym_to_yf.items()}
    yf_tickers = list(sym_to_yf.values())
    eff_start  = max(start, YF_MIN_DATE).isoformat()

    df = None
    with _Silence():
        try:
            kwargs = dict(
                tickers     = " ".join(yf_tickers),
                period      = "max",          # bypass Yahoo date-range rate limiting
                auto_adjust = True,
                actions     = False,
                progress    = False,
                threads     = True,
                group_by    = "ticker",
            )
            try:
                df = yf.download(**kwargs, multi_level_index=True)
            except TypeError:
                df = yf.download(**kwargs)
        except Exception:
            pass

    if df is None or (hasattr(df, "empty") and df.empty):
        return {}

    results = {}
    for yf_sym in yf_tickers:
        our_sym = yf_to_sym.get(yf_sym)
        if not our_sym:
            continue
        try:
            rows = _df_to_rows(df, yf_sym)
            rows = [r for r in rows if r[0] >= eff_start]
            if rows:
                results[our_sym] = rows
        except Exception:
            pass

    return results


def download_individual(our_sym: str, yf_sym: str, start: date) -> list:
    """
    Download one symbol with Ticker.history() — retry + exponential backoff.
    Tries period='max' first (bypasses date-range rate limit),
    falls back to explicit start= date query.
    """
    try:
        import yfinance as yf
    except ImportError:
        return []

    eff_start = max(start, YF_MIN_DATE).isoformat()
    end_str   = (date.today() + timedelta(days=1)).isoformat()

    for attempt in range(3):
        if attempt > 0:
            wait = 5 * (2 ** attempt) + random.uniform(0, 3)   # 10s, 20s + jitter
            _log(f"    Retry {attempt}/3 for {our_sym} (wait {wait:.1f}s)...")
            time.sleep(wait)

        # Attempt 1: period=max (best — no date-range throttle)
        with _Silence():
            try:
                df = yf.Ticker(yf_sym).history(period="max", auto_adjust=True, actions=False)
                if df is not None and not df.empty:
                    rows = _df_to_rows(df)
                    rows = [r for r in rows if r[0] >= eff_start]
                    if rows:
                        return rows
            except Exception:
                pass

        # Attempt 2: explicit start date
        with _Silence():
            try:
                df = yf.Ticker(yf_sym).history(start=eff_start, end=end_str,
                                                auto_adjust=True, actions=False)
                if df is not None and not df.empty:
                    rows = _df_to_rows(df)
                    if rows:
                        return rows
            except Exception:
                pass

    return []


# ══════════════════════════════════════════════════════════════════════════════
# DATABASE WRITE
# ══════════════════════════════════════════════════════════════════════════════

def write_to_db(sym_rows: dict) -> int:
    """
    Bulk-write {symbol: [(date, o, h, l, c, vol, chg), ...]} to daily_prices.
    Uses executemany in WRITE_CHUNK batches — fast even for 500k+ rows.
    INSERT OR IGNORE: never overwrites existing rows, safe to re-run.
    Returns total rows written.
    """
    if not sym_rows:
        return 0

    now_str  = datetime.now().isoformat()
    all_rows = []
    for sym, rows in sym_rows.items():
        for r in rows:
            dt, o, h, lo, cl, vol, chg = r
            all_rows.append((sym, dt, o, h, lo, cl, vol, chg, now_str))

    conn = open_db()
    sql  = """
        INSERT OR IGNORE INTO daily_prices
            (symbol, trade_date, open, high, low, close, volume, change_pct, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?)
    """
    total = 0
    for i in range(0, len(all_rows), WRITE_CHUNK):
        conn.executemany(sql, all_rows[i:i+WRITE_CHUNK])
        conn.commit()
        total += len(all_rows[i:i+WRITE_CHUNK])

    conn.close()
    return total


# ══════════════════════════════════════════════════════════════════════════════
# ZIGZAG SWING PIVOT DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def compute_zigzag_pivots(symbol: str) -> dict:
    """
    Run ZigZag algorithm on full OHLC history for symbol.
    Returns {label: {price, date, desc}} + {_meta: {rows, first, last}}.

    Labels produced:
      ATL, ATH                        — true all-time from DB history
      MAJOR_BOTTOM_LOW, MAJOR_TOP     — ZigZag >= 8% swings
      RECENT_SWING_LOW/HIGH           — last 12 months
      LAST_SWING_LOW/HIGH             — last 6 months
    """
    conn = open_db()
    rows = conn.execute("""
        SELECT trade_date, high, low, close
        FROM daily_prices
        WHERE symbol=? AND close IS NOT NULL
          AND high IS NOT NULL AND low IS NOT NULL
        ORDER BY trade_date ASC
    """, (symbol,)).fetchall()
    conn.close()

    if len(rows) < MIN_ROWS_PIVOTS:
        return {}

    dates = [r[0] for r in rows]
    highs = [float(r[1]) if r[1] else float(r[3]) for r in rows]
    lows  = [float(r[2]) if r[2] else float(r[3]) for r in rows]
    n     = len(rows)

    def _zigzag(pct):
        """Core ZigZag algorithm — returns (swing_highs, swing_lows)."""
        t = pct / 100.0
        direction, li, lp = 1, 0, highs[0]
        sh, sl = [], []
        for i in range(1, n):
            if direction == 1:
                if highs[i] >= lp:
                    lp, li = highs[i], i
                elif lows[i] <= lp * (1 - t):
                    sh.append((dates[li], lp, li))
                    direction, lp, li = -1, lows[i], i
            else:
                if lows[i] <= lp:
                    lp, li = lows[i], i
                elif highs[i] >= lp * (1 + t):
                    sl.append((dates[li], lp, li))
                    direction, lp, li = 1, highs[i], i
        (sh if direction == 1 else sl).append((dates[li], lp, li))
        return sh, sl

    minor_highs, minor_lows = _zigzag(ZIGZAG_MINOR_PCT)
    major_highs, major_lows = _zigzag(ZIGZAG_MAJOR_PCT)

    # True ATL/ATH from actual low/high arrays (not close)
    atl_i = lows.index(min(lows))
    ath_i = highs.index(max(highs))

    # Date cutoffs for recent/last periods
    cutoff_12m = (date.today() - timedelta(days=365)).isoformat()
    cutoff_6m  = (date.today() - timedelta(days=180)).isoformat()

    def _best_low(swings):
        b = min(swings, key=lambda x: x[1])
        return b[1], b[0]

    def _best_high(swings):
        b = max(swings, key=lambda x: x[1])
        return b[1], b[0]

    def _cut(swings, cutoff):
        return [x for x in swings if x[0] >= cutoff]

    result = {
        "ATL": {
            "price": lows[atl_i],
            "date":  dates[atl_i],
            "desc":  f"True all-time low from {n:,} OHLC rows (from {dates[0]})",
        },
        "ATH": {
            "price": highs[ath_i],
            "date":  dates[ath_i],
            "desc":  f"True all-time high from {n:,} OHLC rows (from {dates[0]})",
        },
    }

    for lbl, swings, fn, desc in [
        ("MAJOR_BOTTOM_LOW",  major_lows  or minor_lows,  _best_low,
         f"Major swing bottom — ZigZag >={ZIGZAG_MAJOR_PCT}% decline from peak"),
        ("MAJOR_TOP",         major_highs or minor_highs, _best_high,
         f"Major swing top — ZigZag >={ZIGZAG_MAJOR_PCT}% advance from trough"),
        ("RECENT_SWING_LOW",  _cut(minor_lows,  cutoff_12m), _best_low,
         "Lowest ZigZag swing low in last 12 months"),
        ("RECENT_SWING_HIGH", _cut(minor_highs, cutoff_12m), _best_high,
         "Highest ZigZag swing high in last 12 months"),
        ("LAST_SWING_LOW",    _cut(minor_lows,  cutoff_6m),  _best_low,
         "Most recent ZigZag swing low in last 6 months"),
        ("LAST_SWING_HIGH",   _cut(minor_highs, cutoff_6m),  _best_high,
         "Most recent ZigZag swing high in last 6 months"),
    ]:
        if not swings:
            continue
        try:
            price, dt = fn(swings)
            if price:
                result[lbl] = {"price": price, "date": dt, "desc": desc}
        except Exception:
            pass

    result["_meta"] = {"rows": n, "first": dates[0], "last": dates[-1]}
    return result


def write_zigzag_to_db(symbol: str, pivots: dict):
    """
    Upsert ZigZag AUTO pivots into pivot_levels.
    NEVER overwrites USER source rows (user-entered custom pivots).
    STATIC rows (from instruments.py ATL/ATH) are also preserved for pre-2000 data.
    Only AUTO rows are updated.
    """
    if not pivots:
        return

    now_str = datetime.now().isoformat()
    conn    = open_db()
    c       = conn.cursor()

    ups = []
    for label, pv in pivots.items():
        if label.startswith("_"):
            continue
        price = pv.get("price")
        dt    = pv.get("date")
        desc  = pv.get("desc", "")
        if not price or not dt:
            continue
        ups.append((symbol, label, float(price), str(dt), "AUTO", desc, now_str))

    if ups:
        c.executemany("""
            INSERT INTO pivot_levels
                (symbol, label, pivot_price, pivot_date, source, description, updated_at)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(symbol, label) DO UPDATE SET
                pivot_price = CASE WHEN source != 'USER' THEN excluded.pivot_price ELSE pivot_price END,
                pivot_date  = CASE WHEN source != 'USER' THEN excluded.pivot_date  ELSE pivot_date  END,
                source      = CASE WHEN source != 'USER' THEN excluded.source      ELSE source      END,
                description = CASE WHEN source != 'USER' THEN excluded.description ELSE description END,
                updated_at  = excluded.updated_at
        """, ups)

    conn.commit()
    conn.close()


def run_zigzag_for_symbol(symbol: str) -> str:
    """Worker for ThreadPoolExecutor — detect + write pivots for one symbol."""
    try:
        pivots = compute_zigzag_pivots(symbol)
        if "_meta" in pivots:
            write_zigzag_to_db(symbol, pivots)
            meta   = pivots["_meta"]
            labels = [k for k in pivots if not k.startswith("_")]
            return f"  ✓ {symbol:<18} {meta['rows']:>6,} rows  {meta['first']} → {meta['last']}  [{', '.join(labels)}]"
        else:
            conn = open_db()
            cnt  = conn.execute("SELECT COUNT(*) FROM daily_prices WHERE symbol=?", (symbol,)).fetchone()[0]
            conn.close()
            return f"  · {symbol:<18} {cnt:>6,} rows  (need {MIN_ROWS_PIVOTS}+ for ZigZag)"
    except Exception as e:
        return f"  ✗ {symbol:<18} ERROR: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# DOWNLOAD ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

def _run_batched_download(tasks: list, phase: str) -> tuple:
    """
    Execute batch downloads for tasks = [(sym, yf_sym, start_date), ...].
    Groups by ticker type (INDEX/EQUITY/FUTURE) for better Yahoo compatibility.
    Falls back to individual Ticker.history() for any failed symbols.
    Returns (success_count, total_rows_written).
    """
    total_success = 0
    total_rows    = 0

    # Group by ticker type — Yahoo handles each type with different internal providers
    def _ticker_type(yf_sym: str) -> str:
        if yf_sym.startswith("^"):  return "INDEX"
        if yf_sym.endswith(".NS"):   return "EQUITY"
        if "=F" in yf_sym:          return "FUTURE"
        return "OTHER"

    grouped: dict = defaultdict(list)
    for sym, yf_sym, start in tasks:
        grouped[_ticker_type(yf_sym)].append((sym, yf_sym, start))

    for grp_name, grp_tasks in grouped.items():
        _log(f"\n  [{phase}] {grp_name} group — {len(grp_tasks)} symbols")
        batches = [grp_tasks[i:i+BATCH_SIZE] for i in range(0, len(grp_tasks), BATCH_SIZE)]
        failed  = []

        for b_idx, batch in enumerate(batches):
            batch_start = min(t[2] for t in batch)
            sym_to_yf   = {t[0]: t[1] for t in batch}
            sym_starts  = {t[0]: t[2] for t in batch}

            _log(f"    Batch {b_idx+1}/{len(batches)} [{', '.join(sym_to_yf)}]...", end=" ")
            t0 = time.time()

            results = download_batch(sym_to_yf, batch_start)

            # Per-symbol trim to inception start
            trimmed = {}
            for sym, yf_sym, start in batch:
                if sym in results:
                    rows = [r for r in results[sym] if r[0] >= max(start, YF_MIN_DATE).isoformat()]
                    if rows:
                        trimmed[sym] = rows
                    else:
                        failed.append((sym, yf_sym, start))
                else:
                    failed.append((sym, yf_sym, start))

            if trimmed:
                n = write_to_db(trimmed)
                total_rows    += sum(len(v) for v in trimmed.values())
                total_success += len(trimmed)
                _log(f"OK  {len(trimmed)}/{len(batch)} syms  "
                     f"{sum(len(v) for v in trimmed.values()):,} rows  "
                     f"{time.time()-t0:.1f}s")
            else:
                _log(f"EMPTY — all {len(batch)} queued for individual retry")

            if b_idx < len(batches) - 1:
                time.sleep(BATCH_SLEEP)

        # Individual fallback
        if failed:
            _log(f"\n  [{phase}] Individual fallback: {len(failed)} symbols")
            for i, (sym, yf_sym, start) in enumerate(failed):
                _log(f"    [{i+1}/{len(failed)}] {sym:<18} ({yf_sym})...", end=" ")
                rows = download_individual(sym, yf_sym, start)
                if rows:
                    write_to_db({sym: rows})
                    total_rows    += len(rows)
                    total_success += 1
                    _log(f"{len(rows):,} rows")
                else:
                    _log("FAILED (no data from Yahoo Finance)")
                if i < len(failed) - 1:
                    time.sleep(FALLBACK_SLEEP)

    return total_success, total_rows


def run_download(force=False, topup=False, pivots_only=False,
                 symbols_filter=None, test_mode=False):
    """Main entry point. Orchestrates all 3 phases: download, top-up, pivots."""
    SEP = "=" * 72
    _log(f"\n{SEP}")
    _log("  GANN-ASTRO  |  HISTORICAL DATA DOWNLOADER v5.0")
    _log(SEP)
    _log(f"  DB           : {DB_PATH}")
    _log(f"  Total instr  : {len(ALL_INSTRUMENTS)}")

    # Determine active symbol set
    if test_mode and not symbols_filter:
        symbols_filter = TEST_SYMBOLS
        _log(f"  Mode         : TEST — {len(TEST_SYMBOLS)} symbols "
             f"(5 indices + 30 equities + 5 MCX)")
    elif symbols_filter:
        _log(f"  Mode         : SPECIFIC — {len(symbols_filter)} symbols")
    else:
        _log(f"  Mode         : FULL — all {len(ALL_INSTRUMENTS)} instruments")

    # Initialise DB
    init_db()
    ensure_schema_and_indexes()
    seed_static_pivots()    # seeds ATL/ATH from instruments.py as STATIC rows

    existing = get_symbol_row_counts()

    # Build task lists
    tasks_full   = []   # (sym, yf_sym, start_date)
    tasks_topup  = []   # (sym, yf_sym, start_date)
    tasks_pivots = []   # sym
    no_yf        = []

    for sym, inst in sorted(ALL_INSTRUMENTS.items()):
        if symbols_filter and sym not in symbols_filter:
            continue
        yf_sym = getattr(inst, "yfinance_symbol", None)
        if not yf_sym:
            no_yf.append(sym)
            continue

        ex        = existing.get(sym)
        inception = getattr(inst, "inception_date", YF_MIN_DATE)
        # For pre-2000 inception: download from 2000 onwards only
        # (pre-2000 ATL/ATH already seeded as STATIC from instruments.py)
        start_full = max(inception, YF_MIN_DATE)

        if pivots_only:
            if ex and ex["count"] >= MIN_ROWS_PIVOTS:
                tasks_pivots.append(sym)
            continue

        if force or not ex or ex["count"] < FULL_THRESHOLD:
            tasks_full.append((sym, yf_sym, start_full))
        else:
            days_stale = (date.today() - date.fromisoformat(ex["last"])).days
            if days_stale <= 1:
                # Already current — only run pivots if enough data
                if ex["count"] >= MIN_ROWS_PIVOTS:
                    tasks_pivots.append(sym)
            else:
                # Stale — top-up from 10 days before last known date
                topup_start = max(
                    date.fromisoformat(ex["last"]) - timedelta(days=10),
                    YF_MIN_DATE
                )
                tasks_topup.append((sym, yf_sym, topup_start))
                if ex["count"] >= MIN_ROWS_PIVOTS:
                    tasks_pivots.append(sym)

    _log(f"\n  Full downloads : {len(tasks_full)}")
    _log(f"  Top-ups        : {len(tasks_topup)}")
    _log(f"  Pivot-only     : {len(tasks_pivots)}")
    _log(f"  No YF symbol   : {len(no_yf)}")
    if no_yf:
        _log(f"  Skipped        : {', '.join(no_yf)}")

    if not tasks_full and not tasks_topup and not tasks_pivots:
        before = get_db_summary()
        _log(f"\n  All data current. DB: {before['symbols']} symbols, "
             f"{before['total_rows']:,} rows, {before['pivots']} pivot rows.\n")
        return

    t_start = time.time()

    # ── Phase 1: Full downloads ───────────────────────────────────────────────
    if tasks_full:
        _log(f"\n{'─'*72}")
        _log(f"  PHASE 1 — Full download ({len(tasks_full)} symbols)")
        _log(f"  Batch size: {BATCH_SIZE} | Sleep between batches: {BATCH_SLEEP}s")
        _log(f"{'─'*72}")
        ok, rows = _run_batched_download(tasks_full, "FULL")
        _log(f"\n  Phase 1 complete: {ok}/{len(tasks_full)} symbols, {rows:,} rows")

    # ── Phase 2: Top-ups ──────────────────────────────────────────────────────
    if tasks_topup:
        _log(f"\n{'─'*72}")
        _log(f"  PHASE 2 — Top-up stale data ({len(tasks_topup)} symbols)")
        _log(f"{'─'*72}")
        ok, rows = _run_batched_download(tasks_topup, "TOPUP")
        _log(f"\n  Phase 2 complete: {ok}/{len(tasks_topup)} symbols, {rows:,} rows")

    # ── Phase 3: ZigZag pivot detection (parallel) ────────────────────────────
    # Add newly downloaded symbols that now have enough data
    if not pivots_only:
        existing2  = get_symbol_row_counts()
        pivot_syms = set(tasks_pivots)
        for sym, _, _ in (tasks_full + tasks_topup):
            ex2 = existing2.get(sym)
            if ex2 and ex2["count"] >= MIN_ROWS_PIVOTS:
                pivot_syms.add(sym)
        tasks_pivots = sorted(pivot_syms)

    if tasks_pivots:
        _log(f"\n{'─'*72}")
        _log(f"  PHASE 3 — ZigZag pivot detection ({len(tasks_pivots)} symbols, "
             f"{PIVOT_WORKERS} threads)")
        _log(f"{'─'*72}")
        with ThreadPoolExecutor(max_workers=PIVOT_WORKERS) as executor:
            futs = {executor.submit(run_zigzag_for_symbol, sym): sym
                    for sym in tasks_pivots}
            for fut in as_completed(futs):
                _log(fut.result())

    # ── Phase 4: Refine dynamic ATL/ATH from price database ──────────────────
    try:
        refine_dynamic_atl_ath_in_db()
    except Exception as e:
        _log(f"  [WARN] Failed to refine dynamic ATL/ATH: {e}")

    # ── Final summary ─────────────────────────────────────────────────────────
    final  = get_db_summary()
    elapsed = time.time() - t_start
    _log(f"\n{'='*72}")
    _log(f"  COMPLETE  |  {elapsed:.0f}s elapsed")
    _log(f"  DB now   :  {final['symbols']} symbols  |  "
         f"{final['total_rows']:,} OHLCV rows  |  {final['pivots']} pivot rows")
    _log(f"{'='*72}\n")


def refine_dynamic_atl_ath_in_db():
    """
    For all dynamic symbols, query the daily_prices table for the MIN(low) and MAX(high),
    and upsert those values as 'ATL' and 'ATH' into pivot_levels.
    """
    _log("\n  Refining dynamic ATL/ATH values from price database...")
    conn = open_db()
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    # Get all active instruments
    from data.instruments import ALL_INSTRUMENTS
    
    refined_count = 0
    for sym, inst in ALL_INSTRUMENTS.items():
        # Only refine if it doesn't have manually researched static values
        is_dynamic = getattr(inst, 'atl_date', None) is None
        if not is_dynamic:
            continue
            
        # Find min low and max high from daily_prices
        row = c.execute("""
            SELECT MIN(low), MAX(high) FROM daily_prices WHERE symbol=? AND low IS NOT NULL AND high IS NOT NULL
        """, (sym,)).fetchone()
        
        if not row or row[0] is None or row[1] is None:
            continue
            
        db_min_low, db_max_high = row
        
        # Retrieve the date of the min low
        min_date_row = c.execute("""
            SELECT trade_date FROM daily_prices WHERE symbol=? AND low=? ORDER BY trade_date ASC LIMIT 1
        """, (sym, db_min_low)).fetchone()
        min_date = min_date_row[0] if min_date_row else "UNKNOWN"
        
        # Retrieve the date of the max high
        max_date_row = c.execute("""
            SELECT trade_date FROM daily_prices WHERE symbol=? AND high=? ORDER BY trade_date ASC LIMIT 1
        """, (sym, db_max_high)).fetchone()
        max_date = max_date_row[0] if max_date_row else "UNKNOWN"
        
        # Seed or update pivot_levels for ATL
        c.execute("""
            INSERT INTO pivot_levels (symbol, label, pivot_price, pivot_date, source, description, updated_at)
            VALUES (?, 'ATL', ?, ?, 'DB_AUTO', ?, ?)
            ON CONFLICT(symbol, label) DO UPDATE SET
                pivot_price = excluded.pivot_price,
                pivot_date = excluded.pivot_date,
                source = 'DB_AUTO',
                description = excluded.description,
                updated_at = excluded.updated_at
            WHERE source != 'USER'
        """, (sym, db_min_low, min_date, f"Auto-detected All-Time Low {db_min_low:,.2f} on {min_date}", now))
        
        # Seed or update pivot_levels for ATH
        c.execute("""
            INSERT INTO pivot_levels (symbol, label, pivot_price, pivot_date, source, description, updated_at)
            VALUES (?, 'ATH', ?, ?, 'DB_AUTO', ?, ?)
            ON CONFLICT(symbol, label) DO UPDATE SET
                pivot_price = excluded.pivot_price,
                pivot_date = excluded.pivot_date,
                source = 'DB_AUTO',
                description = excluded.description,
                updated_at = excluded.updated_at
            WHERE source != 'USER'
        """, (sym, db_max_high, max_date, f"Auto-detected All-Time High {db_max_high:,.2f} on {max_date}", now))
        
        # Update properties on the live instrument object as well
        inst.all_time_low = float(db_min_low)
        inst.all_time_high = float(db_max_high)
        refined_count += 1
        
    conn.commit()
    conn.close()
    _log(f"  ✓ Refined and seeded {refined_count} dynamic instruments with true extremes from DB.")


# ══════════════════════════════════════════════════════════════════════════════
# COMPATIBILITY SHIM (used by core/scheduler.py detect_auto_pivots)
# ══════════════════════════════════════════════════════════════════════════════

def download_symbol_history(symbol, yf_symbol, start_date, end_date=None):
    return download_individual(symbol, yf_symbol, start_date)

MIN_ROWS_FOR_PIVOTS = MIN_ROWS_PIVOTS   # alias used by scheduler.py


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        prog="download_history.py",
        description="Gann-Astro — Historical Data Downloader v5.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python download_history.py --test              # 40 key symbols — fast test
  python download_history.py                     # all 257 instruments
  python download_history.py --test --topup      # top-up 40 symbols only
  python download_history.py --test --force      # force re-download 40 symbols
  python download_history.py --pivots-only       # re-detect pivots, no download
  python download_history.py --symbols NIFTY50 GOLD HDFCBANK TCS RELIANCE
        """,
    )
    ap.add_argument("--test",        action="store_true",
                    help="Process only the 40 test symbols (5 idx + 30 eq + 5 MCX)")
    ap.add_argument("--force",       action="store_true",
                    help="Re-download every symbol from scratch (ignore existing data)")
    ap.add_argument("--topup",       action="store_true",
                    help="Only fetch symbols with missing or stale data")
    ap.add_argument("--pivots-only", action="store_true", dest="pivots_only",
                    help="Skip all downloads; only re-detect ZigZag pivots")
    ap.add_argument("--symbols",     nargs="+", metavar="SYM",
                    help="Process only these symbols (space-separated)")
    ap.add_argument("--backfill-1m", action="store_true", dest="backfill_1m",
                    help="Backfill 1-minute data into DuckDB using yfinance")
    args = ap.parse_args()

    if args.backfill_1m:
        print("Backfilling 1-minute data into DuckDB...")
        from core.feed_1m_poller import fetch_and_store_1m_data
        
        symbols_to_process = []
        if args.test:
            symbols_to_process = TEST_SYMBOLS
        elif args.symbols:
            symbols_to_process = args.symbols
        else:
            symbols_to_process = [i["symbol"] for i in ALL_INSTRUMENTS]
            
        fetch_and_store_1m_data(symbols_to_process)
        print("1-minute backfill complete.")
        import sys
        sys.exit(0)

    run_download(
        force          = args.force,
        topup          = args.topup,
        pivots_only    = args.pivots_only,
        symbols_filter = args.symbols,
        test_mode      = args.test,
    )
