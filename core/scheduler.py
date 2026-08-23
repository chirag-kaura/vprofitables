"""
scheduler.py — Auto-update engine
Runs every day at 15:30 IST (market close) and 09:00 IST (pre-open)
Caches: price data, quant analysis, planetary signals → SQLite
So the UI is instant — no waiting for calculations on load
"""

import json
import sqlite3
import threading
import time
import os
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Optional

# Timezone: use zoneinfo (Python 3.9+) with fallback to fixed UTC+5:30 offset
try:
    from zoneinfo import ZoneInfo
    _IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    _IST = timezone(timedelta(hours=5, minutes=30))

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.paths import DB_PATH


def _get_db(path=None):
    """
    Open SQLite with performance PRAGMAs.
    WAL mode: app reads are never blocked by download_history.py writes.
    32MB cache + 256MB mmap: fast queries on 10M+ row daily_prices table.
    """
    conn = sqlite3.connect(path or DB_PATH, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-32000")    # 32 MB
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=268435456")  # 256 MB
    conn.execute("PRAGMA busy_timeout=30000")   # 30s retry
    return conn


# ── IST timezone ──────────────────────────────────────────────────────────────


def utc_now() -> datetime:
    """Return current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def ist_now() -> datetime:
    """Return current IST time as a timezone-aware datetime."""
    return datetime.now(_IST)


def ist_now_naive() -> datetime:
    """Return current IST time as a naive datetime (for DB storage / string ops)."""
    return datetime.now(_IST).replace(tzinfo=None)


_CACHED_HOLIDAYS = None

def _get_holidays() -> set:
    """Read holidays from data/holidays.csv. Returns a set of date objects."""
    global _CACHED_HOLIDAYS
    if _CACHED_HOLIDAYS is not None:
        return _CACHED_HOLIDAYS

    _CACHED_HOLIDAYS = set()
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "holidays.csv")
    if os.path.exists(csv_path):
        try:
            import csv
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date_str = row.get("Date", "").strip()
                    if date_str:
                        try:
                            # Support YYYY-MM-DD
                            _CACHED_HOLIDAYS.add(date.fromisoformat(date_str))
                        except ValueError:
                            # Support DD-MMM-YYYY (e.g. 01-May-2025)
                            try:
                                dt = datetime.strptime(date_str, "%d-%b-%Y")
                                _CACHED_HOLIDAYS.add(dt.date())
                            except ValueError:
                                pass
        except Exception as e:
            print(f"  [WARN] Failed to parse holidays.csv: {e}")
    return _CACHED_HOLIDAYS

def is_market_day(d: Optional[date] = None) -> bool:
    """
    Return True if d is a trading day on NSE/BSE.
    Checks Mon–Fri AND excludes known NSE holidays from data/holidays.csv.
    """
    d = d or date.today()
    if d.weekday() >= 5:          # Saturday=5, Sunday=6
        return False

    return d not in _get_holidays()


# ══════════════════════════════════════════════════════════════════════════
# DATABASE SETUP
# ══════════════════════════════════════════════════════════════════════════

def init_db():
    """
    Create tables if they don't exist.

    PHASE 1 CHANGES (S1, S2, S4, Fix 5):
      - Single DB: all tables (prices, positions, users, risk_settings) live
        in market_data_v2.db.  personalization_db.py was already pointed here;
        this function now calls init_personalization_db() to ensure the user/
        portfolio/risk_profile tables exist alongside price data.
      - `positions` table: the ONE table for all open/closed trades.
        Replaces the now-retired paper_portfolio for risk gate reads.
        Added: exit_reason, updated_at, source_signal_id, lifecycle_state.
      - `risk_settings` table: now keyed by user_id (not a single global row).
        Migration adds user_id column if the table already exists.
      - `paper_portfolio` migration: any existing rows are copied to `positions`
        and paper_portfolio is left intact but no longer written to.
    """
    conn = _get_db()
    c = conn.cursor()

    # ── ensure personalization tables (users, portfolios, risk_profiles, etc.) exist ──
    # These were already targeted at market_data_v2.db — this call is now the
    # authoritative place to ensure they are created on every startup.
    try:
        from core.personalization_db import init_personalization_db
        init_personalization_db()
    except Exception as _pdb_err:
        print(f"  [INIT] personalization_db init warn: {_pdb_err}", flush=True)

    # Daily price cache
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_prices (
            symbol      TEXT NOT NULL,
            trade_date  TEXT NOT NULL,
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

    # Quant analysis cache (heavy — Fourier + regime + S/R)
    c.execute("""
        CREATE TABLE IF NOT EXISTS quant_cache (
            symbol      TEXT NOT NULL,
            cache_date  TEXT NOT NULL,
            payload     TEXT NOT NULL,
            updated_at  TEXT,
            PRIMARY KEY (symbol, cache_date)
        )
    """)

    # ── Pivot levels — named swing pivots per instrument ──────────────────────
    # label: ATL | ATH | MAJOR_BOTTOM_LOW | MAJOR_TOP | RECENT_SWING_LOW | RECENT_SWING_HIGH | LAST_SWING_LOW | LAST_SWING_HIGH | CUSTOM
    # source: STATIC (from instruments.py) | AUTO (detected from daily_prices) | USER (manually set)
    # Rows are upserted every time daily_prices is refreshed with enough history
    c.execute("""
        CREATE TABLE IF NOT EXISTS pivot_levels (
            symbol      TEXT    NOT NULL,
            label       TEXT    NOT NULL,   -- ATL/ATH/MAJOR_BOTTOM_LOW/MAJOR_TOP/RECENT_SWING_LOW/RECENT_SWING_HIGH/LAST_SWING_LOW/LAST_SWING_HIGH
            pivot_price REAL    NOT NULL,
            pivot_date  TEXT    NOT NULL,
            source      TEXT    DEFAULT 'STATIC',  -- STATIC / AUTO / USER
            description TEXT    DEFAULT '',
            updated_at  TEXT,
            PRIMARY KEY (symbol, label)
        )
    """)

    # ── Migration: Add columns to signals table if not present ──
    for col_name, col_type in [
        ("signal_subtype", "TEXT"),
        ("fired_at", "TEXT"),
        ("price_at_signal", "REAL"),
        ("outcome_price_5d", "REAL"),
        ("outcome_price_10d", "REAL"),
        ("outcome_price_20d", "REAL"),
        ("planet_name", "TEXT"),
        ("aspect_type", "TEXT"),
        ("direction", "TEXT")
    ]:
        try:
            c.execute(f"ALTER TABLE signals ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass

    # ── Table: gann_calibrated_weights ──
    c.execute("""
        CREATE TABLE IF NOT EXISTS gann_calibrated_weights (
            weight_key TEXT PRIMARY KEY,
            weight_value REAL NOT NULL
        )
    """)

    # ── Table: gann_instrument_scales ──
    c.execute("""
        CREATE TABLE IF NOT EXISTS gann_instrument_scales (
            symbol TEXT PRIMARY KEY,
            scale REAL NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Planetary signals cache
    c.execute("""
        CREATE TABLE IF NOT EXISTS planet_cache (
            cache_date  TEXT PRIMARY KEY,
            payload     TEXT NOT NULL,
            updated_at  TEXT
        )
    """)

    # Scheduler run log
    c.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at      TEXT NOT NULL,
            run_type    TEXT NOT NULL,
            symbols_ok  INTEGER DEFAULT 0,
            symbols_err INTEGER DEFAULT 0,
            duration_s  REAL,
            notes       TEXT
        )
    """)

    # Forward signals table — persists live recommendations + their outcomes
    conn.execute("""
        CREATE TABLE IF NOT EXISTS forward_signals (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_date     TEXT NOT NULL,          -- date signal was generated
            symbol          TEXT NOT NULL,
            inv_type        TEXT NOT NULL,           -- swing/short/long/hedge_fund
            entry           REAL NOT NULL,
            stop_loss       REAL NOT NULL,
            target1         REAL NOT NULL,
            target2         REAL NOT NULL,
            rr_ratio        REAL,
            confidence      INTEGER,
            regime          TEXT,
            wyckoff_phase   TEXT,
            news_sentiment  TEXT,
            bulk_signal     TEXT,
            hold_days       INTEGER,
            buy_date        TEXT,
            sell_date       TEXT,
            reasons         TEXT,                   -- JSON list
            -- Live tracking (updated daily)
            status          TEXT DEFAULT 'OPEN',    -- OPEN/SL_HIT/T1_HIT/T2_HIT/TRAILING_SL/EXPIRED
            exit_date       TEXT DEFAULT NULL,
            exit_price      REAL DEFAULT NULL,
            exit_reason     TEXT DEFAULT NULL,
            max_high        REAL DEFAULT NULL,      -- highest price since entry (for trailing)
            trailing_sl     REAL DEFAULT NULL,      -- current trailing SL level
            pnl_pct         REAL DEFAULT NULL,
            notified        INTEGER DEFAULT 0,      -- 1 if notification was sent
            created_at      TEXT NOT NULL,
            updated_at      TEXT
        )
    """)

    # Paper portfolio table (Phases 1-2)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS paper_portfolio (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol          TEXT NOT NULL,
            inv_type        TEXT DEFAULT 'swing',
            side            TEXT DEFAULT 'BUY',
            entry_date      TEXT NOT NULL,
            entry_price     REAL NOT NULL,
            shares          INTEGER NOT NULL DEFAULT 1,
            stop_loss       REAL NOT NULL DEFAULT 0,
            target1         REAL NOT NULL DEFAULT 0,
            target2         REAL NOT NULL DEFAULT 0,
            gtt_trigger     REAL DEFAULT NULL,
            trailing_pct    REAL DEFAULT NULL,
            status          TEXT DEFAULT 'OPEN',
            exit_date       TEXT DEFAULT NULL,
            exit_price      REAL DEFAULT NULL,
            exit_reason     TEXT DEFAULT NULL,
            realized_pnl    REAL DEFAULT NULL,
            created_at      TEXT,
            updated_at      TEXT
        )
    """)

    # Watchlist items (Phase 3)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlist_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT NOT NULL UNIQUE,
            added_at    TEXT NOT NULL,
            notes       TEXT DEFAULT ''
        )
    """)

    # Price alerts (Phase 3)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_alerts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol          TEXT NOT NULL,
            condition       TEXT NOT NULL,  -- ABOVE / BELOW / PCT_UP / PCT_DOWN
            threshold       REAL NOT NULL,
            notify_browser  INTEGER DEFAULT 1,
            notify_whatsapp INTEGER DEFAULT 0,
            status          TEXT DEFAULT 'ACTIVE',  -- ACTIVE / TRIGGERED / DISABLED
            triggered_at    TEXT DEFAULT NULL,
            created_at      TEXT NOT NULL
        )
    """)

    # Risk settings (PHASE 1 FIX S2: per-user, not single global row)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS risk_settings (
            id                       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id                  TEXT UNIQUE,       -- NULL = legacy single-user mode
            capital                  REAL DEFAULT 1000000,
            max_risk_pct             REAL DEFAULT 2.0,
            max_positions            INTEGER DEFAULT 5,
            daily_loss_limit         REAL DEFAULT 50000,
            max_sector_pct           REAL DEFAULT 30.0,
            max_position_pct         REAL DEFAULT 10.0,
            max_correlation_exposure REAL DEFAULT 0.7,
            kill_switch              INTEGER DEFAULT 0,
            updated_at               TEXT
        )
    """)
    # ── Migrations for existing risk_settings rows ──────────────────────────
    for _col, _typ in [
        ("user_id",                  "TEXT"),
        ("max_position_pct",         "REAL DEFAULT 10.0"),
        ("max_correlation_exposure", "REAL DEFAULT 0.7"),
        ("daily_loss_limit",         "REAL DEFAULT 50000"),
    ]:
        try:
            conn.execute(f"ALTER TABLE risk_settings ADD COLUMN {_col} {_typ}")
        except Exception:
            pass  # column already exists
    try:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_risk_settings_user ON risk_settings(user_id)")
    except Exception:
        pass
    # Ensure a legacy single-user default row (id=1) still exists for backward compat
    conn.execute("INSERT OR IGNORE INTO risk_settings (id) VALUES (1)")

    # ── PHASE 3: position_audit_log table ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS position_audit_log (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            position_id      TEXT NOT NULL,
            field            TEXT NOT NULL,
            old_value        TEXT,
            new_value        TEXT,
            changed_at       TEXT NOT NULL,
            change_reason    TEXT,
            FOREIGN KEY (position_id) REFERENCES positions (id) ON DELETE CASCADE
        )
    """)

    # ── PHASE 1 FIX S1: positions table column migrations ──────────────────
    # Ensure all Phase-1-required columns exist on existing `positions` tables.
    # These ALTER TABLE calls are safe to run repeatedly (silently skipped if column exists).
    for _pcol, _ptyp in [
        ("exit_reason",      "TEXT DEFAULT NULL"),
        ("updated_at",       "TEXT DEFAULT NULL"),
        ("source_signal_id", "INTEGER DEFAULT NULL"),
        ("lifecycle_state",  "TEXT DEFAULT 'OPEN'"),
    ]:
        try:
            conn.execute(f"ALTER TABLE positions ADD COLUMN {_pcol} {_ptyp}")
        except Exception:
            pass  # column already exists

    # ── PHASE 1: Migrate any old paper_portfolio rows → positions ───────────
    # paper_portfolio is now read-retired; existing rows are moved to `positions`
    # so they appear in the Guardian and risk gates.  Runs once; safe to retry.
    try:
        _pp_rows = conn.execute(
            "SELECT symbol, inv_type, entry_date, entry_price, shares, "
            "stop_loss, target1, target2, status, exit_date, exit_price, "
            "exit_reason, realized_pnl, created_at "
            "FROM paper_portfolio"
        ).fetchall()
        if _pp_rows:
            import uuid as _uuid_pp
            # Find or create a 'legacy' portfolio for migrated rows
            _leg_pf = conn.execute(
                "SELECT id FROM portfolios WHERE name='legacy_paper'"
            ).fetchone()
            if not _leg_pf:
                _leg_pf_id = str(_uuid_pp.uuid4())
                conn.execute(
                    "INSERT OR IGNORE INTO portfolios (id, user_id, name, created_at) "
                    "VALUES (?, 'LEGACY', 'legacy_paper', ?)",
                    (_leg_pf_id, ist_now_naive().isoformat())
                )
            else:
                _leg_pf_id = _leg_pf[0]

            _migrated = 0
            for _row in _pp_rows:
                (sym, inv_type, edate, eprice, shares, sl, t1, t2,
                 st, exdate, exprice, exreason, pnl, creat) = _row
                _pos_id = str(_uuid_pp.uuid4())
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO positions "
                        "(id, portfolio_id, symbol, inv_type, entry_date, entry_price, "
                        " shares, stop_loss, target1, target2, status, exit_date, "
                        " exit_price, exit_reason, realized_pnl, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (_pos_id, _leg_pf_id, sym, inv_type or 'swing',
                         edate, eprice, shares or 1, sl or 0,
                         t1 or 0, t2 or 0, st or 'OPEN',
                         exdate, exprice, exreason, pnl, creat)
                    )
                    _migrated += 1
                except Exception:
                    pass
            if _migrated:
                print(f"  [INIT] Migrated {_migrated} paper_portfolio rows → positions", flush=True)
    except Exception as _pp_err:
        # paper_portfolio may not exist yet — that's fine
        pass

    # ── PHASE 2 FIX (Fix 9): correlation_cache table ─────────────────────────
    # Stores pre-computed Pearson correlations so risk_gates doesn't
    # re-query 120 days of price history on every portfolio_add call.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS correlation_cache (
            sym1       TEXT NOT NULL,
            sym2       TEXT NOT NULL,
            corr       REAL NOT NULL,
            computed_at TEXT NOT NULL,
            PRIMARY KEY (sym1, sym2)
        )
    """)

    conn.commit()
    conn.close()
    return DB_PATH


# ══════════════════════════════════════════════════════════════════════════
# PRICE FETCHER
# ══════════════════════════════════════════════════════════════════════════

def fetch_eod_prices(symbols_map: dict) -> dict:
    """
    Fetch end-of-day prices for all instruments.
    Always fetches the most recent ACTUAL trading day's data.
    Never creates rows for weekends or holidays.
    """
    results = {}
    try:
        import yfinance as yf
        yf_syms = [v for v in symbols_map.values() if v]
        if not yf_syms:
            return results

        # Use period="5d" to ensure we get the last actual trading day
        # even when running on weekends (avoids stale data)
        data = yf.download(
            tickers=" ".join(yf_syms[:100]),
            period="5d",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )

        # Drop any rows that are weekends (extra safety)
        if hasattr(data.index, 'dayofweek'):
            data = data[data.index.dayofweek < 5]

        if data.empty:
            return results

        # Map back to our symbols
        inv_map = {v: k for k, v in symbols_map.items() if v}
        for yf_sym, our_sym in inv_map.items():
            try:
                if len(yf_syms) == 1:
                    row = data.iloc[-1]
                    prev = data.iloc[-2] if len(data) > 1 else row
                    o, h, l, c = float(row['Open']), float(row['High']), float(row['Low']), float(row['Close'])
                    vol = int(row['Volume']) if 'Volume' in row else 0
                    prev_c = float(prev['Close'])
                else:
                    row = data['Close'][yf_sym].dropna()
                    if len(row) < 1:
                        continue
                    c = float(row.iloc[-1])
                    prev_c = float(row.iloc[-2]) if len(row) > 1 else c
                    h = float(data['High'][yf_sym].dropna().iloc[-1])
                    l = float(data['Low'][yf_sym].dropna().iloc[-1])
                    o = float(data['Open'][yf_sym].dropna().iloc[-1])
                    vol_col = data.get('Volume', None)
                    vol = int(vol_col[yf_sym].dropna().iloc[-1]) if vol_col is not None else 0

                chg = (c - prev_c) / prev_c * 100 if prev_c else 0
                results[our_sym] = {
                    "open": round(o, 2), "high": round(h, 2),
                    "low": round(l, 2), "close": round(c, 2),
                    "volume": vol, "change_pct": round(chg, 2),
                }
            except Exception:
                continue
    except ImportError:
        pass  # yfinance not installed
    except Exception as e:
        print(f"  [SCHED] Price fetch error: {e}")

    return results


# ══════════════════════════════════════════════════════════════════════════
# CACHE READ/WRITE
# ══════════════════════════════════════════════════════════════════════════

def cache_prices(prices: dict, trade_date: date):
    conn = _get_db()
    c = conn.cursor()
    now = ist_now_naive().isoformat()
    for sym, p in prices.items():
        c.execute("""
            INSERT OR REPLACE INTO daily_prices
            (symbol, trade_date, open, high, low, close, volume, change_pct, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (sym, trade_date.isoformat(),
              p.get('open'), p.get('high'), p.get('low'), p.get('close'),
              p.get('volume'), p.get('change_pct'), now))
    conn.commit()
    conn.close()
    invalidate_price_cache()   # flush stale in-process cache after DB write



# ══ PIVOT LEVEL HELPERS ══════════════════════════════════════════════════════

def seed_static_pivots():
    """Seed ATL pivot from instruments.py for all symbols. Safe to run every startup."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from data.instruments import ALL_INSTRUMENTS
    from datetime import datetime as dt_cls
    init_db()
    now = dt_cls.now().isoformat()
    rows = []
    for sym, inst in ALL_INSTRUMENTS.items():
        # ATL: use atl_date if known, else use inception_date as anchor
        # For pre-2000 symbols: atl_date is researched manually (or None → use inception)
        atl_date_str = str(inst.atl_date) if getattr(inst, 'atl_date', None) else str(inst.inception_date)
        rows.append((sym, "ATL", float(inst.all_time_low), atl_date_str,
                     "STATIC",
                     f"All-Time Low {inst.all_time_low:,.0f} — {atl_date_str} (manually researched)",
                     now))
        # ATH: use ath_date if known
        ath_date_str = str(inst.ath_date) if getattr(inst, 'ath_date', None) else "UNKNOWN"
        ath_source   = "STATIC" if ath_date_str != "UNKNOWN" else "STATIC_NODATE"
        ath_desc     = (f"All-Time High {inst.all_time_high:,.0f} — {ath_date_str} (manually researched)"
                        if ath_date_str != "UNKNOWN"
                        else f"All-Time High {inst.all_time_high:,.0f} — date unknown, will be refined from DB")
        rows.append((sym, "ATH", float(inst.all_time_high), ath_date_str,
                     ath_source, ath_desc, now))
    conn = _get_db()
    c = conn.cursor()
    c.executemany("""INSERT INTO pivot_levels
        (symbol,label,pivot_price,pivot_date,source,description,updated_at)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(symbol,label) DO UPDATE SET
            pivot_price = CASE
                -- ATL: update if our researched value is lower (more extreme) than what's stored
                WHEN excluded.label='ATL'  AND excluded.pivot_price < pivot_price THEN excluded.pivot_price
                -- ATH: update if our researched value is higher (more extreme) than what's stored
                WHEN excluded.label='ATH'  AND excluded.pivot_price > pivot_price THEN excluded.pivot_price
                -- For any other STATIC label: always update (e.g. re-seeding after corrections)
                WHEN excluded.source='STATIC' AND source NOT IN ('USER') THEN excluded.pivot_price
                ELSE pivot_price END,
            pivot_date = CASE
                WHEN excluded.label='ATL'  AND excluded.pivot_price < pivot_price THEN excluded.pivot_date
                WHEN excluded.label='ATH'  AND excluded.pivot_price > pivot_price THEN excluded.pivot_date
                WHEN excluded.source='STATIC' AND source NOT IN ('USER') THEN excluded.pivot_date
                ELSE pivot_date END,
            source = CASE
                WHEN source NOT IN ('USER') THEN excluded.source
                ELSE source END,
            description = CASE
                WHEN source NOT IN ('USER') THEN excluded.description
                ELSE description END,
            updated_at = excluded.updated_at""", rows)
    conn.commit(); conn.close()


def detect_auto_pivots(symbol: str):
    """
    Detect swing pivots using ZigZag algorithm on full daily_prices history.
    Delegates to download_history.compute_zigzag_pivots for real swing detection.
    Falls back to simple min/max if history is sparse (< 60 rows).
    Never overwrites USER pivots.
    """
    init_db()
    # Try ZigZag first (needs 60+ rows and full OHLC)
    try:
        import sys, os as _os
        root = _os.path.dirname(_os.path.dirname(__file__))
        if root not in sys.path: sys.path.insert(0, root)
        from download_history import compute_zigzag_pivots, write_zigzag_to_db, MIN_ROWS_FOR_PIVOTS
        conn = _get_db()
        cnt  = conn.execute("SELECT COUNT(*) FROM daily_prices WHERE symbol=?", (symbol,)).fetchone()[0]
        conn.close()
        if cnt >= MIN_ROWS_FOR_PIVOTS:
            pivots = compute_zigzag_pivots(symbol)
            if "_meta" in pivots:
                write_zigzag_to_db(symbol, pivots)
                return
    except Exception:
        pass  # fall through to simple detection below

    # ── Fallback: simple min/max for sparse data ──────────────────────────
    from datetime import datetime as dt_cls, date as date_cls, timedelta
    conn = _get_db()
    c    = conn.cursor()
    c.execute("SELECT trade_date, close, high, low FROM daily_prices WHERE symbol=? AND close IS NOT NULL ORDER BY trade_date", (symbol,))
    rows = c.fetchall()
    if len(rows) < 10:
        conn.close(); return

    now  = dt_cls.now().isoformat()
    def co(days): return (date_cls.today() - timedelta(days=days)).isoformat()
    def flo(data): m=min(data,key=lambda x:x[1]); return float(m[1]),m[0]
    def fhi(data): m=max(data,key=lambda x:x[1]); return float(m[1]),m[0]

    cl_rows = [(d, cl) for d,cl,hi,lo in rows if cl]
    hi_rows = [(d, hi) for d,cl,hi,lo in rows if hi]
    lo_rows = [(d, lo) for d,cl,hi,lo in rows if lo]

    defs = [
        ("ATL",               lo_rows,                               "Lowest low in DB history"),
        ("ATH",               hi_rows,                               "Highest high in DB history"),
        ("MAJOR_BOTTOM_LOW",  cl_rows,                               "Lowest close in DB history"),
        ("MAJOR_TOP",         hi_rows,                               "Highest high in DB history"),
        ("RECENT_SWING_LOW",  [(d,p) for d,p in cl_rows if d>=co(365)], "Lowest close last 12m"),
        ("RECENT_SWING_HIGH", [(d,p) for d,p in hi_rows if d>=co(365)], "Highest high last 12m"),
        ("LAST_SWING_LOW",    [(d,p) for d,p in cl_rows if d>=co(180)], "Lowest close last 6m"),
        ("LAST_SWING_HIGH",   [(d,p) for d,p in hi_rows if d>=co(180)], "Highest high last 6m"),
    ]
    ups = []
    for label, data, desc in defs:
        if not data: continue
        fn = flo if "LOW" in label or "BOTTOM" in label else fhi
        price, dt = fn(data)
        if price: ups.append((symbol, label, price, dt, "AUTO", desc, now))

    if ups:
        c.executemany("""INSERT INTO pivot_levels(symbol,label,pivot_price,pivot_date,source,description,updated_at)
            VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(symbol,label) DO UPDATE SET
                pivot_price=CASE WHEN source NOT IN ('USER','STATIC') THEN excluded.pivot_price ELSE pivot_price END,
                pivot_date =CASE WHEN source NOT IN ('USER','STATIC') THEN excluded.pivot_date  ELSE pivot_date  END,
                source     =CASE WHEN source NOT IN ('USER','STATIC') THEN excluded.source      ELSE source      END,
                description=CASE WHEN source NOT IN ('USER','STATIC') THEN excluded.description ELSE description END,
                updated_at =excluded.updated_at""", ups)
    conn.commit(); conn.close()


def get_pivots_for_symbol(symbol: str) -> list:
    """Return all pivot levels for a symbol ordered by pivot_price ASC."""
    init_db()
    conn = _get_db()
    c    = conn.cursor()
    c.execute("SELECT label,pivot_price,pivot_date,source,description FROM pivot_levels WHERE symbol=? ORDER BY pivot_price ASC", (symbol,))
    rows = c.fetchall()
    conn.close()
    return [{"label":r[0],"price":r[1],"date":r[2],"source":r[3],"description":r[4]} for r in rows]


def save_user_pivot(symbol: str, label: str, price: float, dt: str, description: str = ""):
    """Persist a USER-defined custom pivot. Never auto-overwritten."""
    from datetime import datetime as dt_cls
    init_db()
    now  = dt_cls.now().isoformat()
    conn = _get_db()
    c    = conn.cursor()
    c.execute("""INSERT INTO pivot_levels(symbol,label,pivot_price,pivot_date,source,description,updated_at)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(symbol,label) DO UPDATE SET
            pivot_price=excluded.pivot_price, pivot_date=excluded.pivot_date,
            source='USER', description=excluded.description, updated_at=excluded.updated_at""",
        (symbol, label, float(price), dt, "USER", description, now))
    conn.commit(); conn.close()


# ── In-process price cache — avoids SQLite round-trip on every API request ──
# The "latest prices" query is called by 6+ endpoints per page load.
# We cache the result for 60 seconds; backtest (date-specific) calls bypass it.
_price_cache_store: dict = {"data": {}, "ts": 0.0, "date": None}
_price_cache_lock  = threading.Lock()
_PRICE_CACHE_TTL   = 60   # seconds


def get_cached_prices(trade_date: Optional[date] = None) -> dict:
    """
    Get latest cached prices from SQLite.
    If trade_date is given (backtest mode), always hits the DB — no caching.
    Otherwise, results are cached in-process for _PRICE_CACHE_TTL seconds so
    multiple endpoints served in the same second share a single DB read.
    """
    global _price_cache_store

    # Backtest / date-specific: always read from DB, never cache
    if trade_date:
        conn = _get_db()
        rows = conn.execute("""
            SELECT symbol, open, high, low, close, volume, change_pct, trade_date
            FROM daily_prices WHERE trade_date = ?
        """, (trade_date.isoformat(),)).fetchall()

        # If exact date has no data (holiday / weekend), fall back to most recent
        # prior trading day (up to 7 calendar days back) to get real prices.
        if not rows:
            fallback_rows = conn.execute("""
                SELECT d.symbol, d.open, d.high, d.low, d.close, d.volume, d.change_pct, d.trade_date
                FROM daily_prices d
                INNER JOIN (
                    SELECT symbol, MAX(trade_date) AS max_date
                    FROM daily_prices
                    WHERE trade_date < ? AND trade_date >= date(?, '-7 days')
                    GROUP BY symbol
                ) m ON d.symbol = m.symbol AND d.trade_date = m.max_date
                ORDER BY d.trade_date DESC
            """, (trade_date.isoformat(), trade_date.isoformat())).fetchall()
            rows = fallback_rows

        conn.close()
        result = {}
        for row in rows:
            sym, o, h, l, cl, vol, chg, dt = row
            result[sym] = {"open": o, "high": h, "low": l, "close": cl,
                           "volume": vol, "change_pct": chg, "date": dt}
        return result

    # Live prices: serve from in-process cache if fresh
    now_ts = time.time()
    with _price_cache_lock:
        if (now_ts - _price_cache_store["ts"]) < _PRICE_CACHE_TTL and _price_cache_store["data"]:
            return _price_cache_store["data"]

    # Cache miss — query DB (optimized with loose index scan for 40x speedup)
    conn = _get_db()
    rows = conn.execute("""
        WITH RECURSIVE
          syms(x) AS (
             SELECT MIN(symbol) FROM daily_prices
             UNION ALL
             SELECT (SELECT MIN(symbol) FROM daily_prices WHERE symbol > x)
             FROM syms WHERE x IS NOT NULL
          )
        SELECT d.symbol, d.open, d.high, d.low, d.close, d.volume, d.change_pct, d.trade_date
        FROM daily_prices d
        INNER JOIN (
            SELECT x AS symbol, (SELECT MAX(trade_date) FROM daily_prices WHERE symbol = x) AS max_date
            FROM syms
            WHERE x IS NOT NULL
        ) m ON d.symbol = m.symbol AND d.trade_date = m.max_date
    """).fetchall()
    conn.close()

    result = {}
    for row in rows:
        sym, o, h, l, cl, vol, chg, dt = row
        result[sym] = {"open": o, "high": h, "low": l, "close": cl,
                       "volume": vol, "change_pct": chg, "date": dt}

    with _price_cache_lock:
        _price_cache_store["data"] = result
        _price_cache_store["ts"]   = now_ts
    return result


def invalidate_price_cache() -> None:
    """Call after writing new prices to DB so the next request re-fetches."""
    with _price_cache_lock:
        _price_cache_store["ts"] = 0.0


def cache_quant(symbol: str, payload: dict, cache_date: date):
    def ser(o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        try:
            import numpy as np
            if isinstance(o, np.integer):  return int(o)
            if isinstance(o, np.floating): return None if np.isnan(o) else float(o)
            if isinstance(o, np.bool_):    return bool(o)
            if isinstance(o, np.ndarray):  return o.tolist()
        except ImportError:
            pass
        if hasattr(o, 'item'):   return o.item()
        if hasattr(o, 'tolist'): return o.tolist()
        raise TypeError(type(o))

    conn = _get_db()
    c = conn.cursor()
    serialized = json.dumps(payload, default=ser)
    c.execute("""
        INSERT OR REPLACE INTO quant_cache (symbol, cache_date, payload, updated_at)
        VALUES (?,?,?,?)
    """, (symbol, cache_date.isoformat(), serialized, ist_now_naive().isoformat()))
    conn.commit()
    conn.close()


def get_cached_quant(symbol: str, max_age_days: int = 1) -> Optional[dict]:
    conn = _get_db()
    c = conn.cursor()
    cutoff = (date.today() - timedelta(days=max_age_days)).isoformat()
    row = c.execute("""
        SELECT payload, cache_date FROM quant_cache
        WHERE symbol = ? AND cache_date >= ?
        ORDER BY cache_date DESC LIMIT 1
    """, (symbol, cutoff)).fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row[0])
        except Exception:
            return None
    return None


def cache_planets(payload: dict, cache_date: date):
    conn = _get_db()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO planet_cache (cache_date, payload, updated_at)
        VALUES (?,?,?)
    """, (cache_date.isoformat(), json.dumps(payload), ist_now_naive().isoformat()))
    conn.commit()
    conn.close()


def get_cached_planets(cache_date: Optional[date] = None) -> Optional[dict]:
    conn = _get_db()
    c = conn.cursor()
    dt = (cache_date or date.today()).isoformat()
    row = c.execute("""
        SELECT payload FROM planet_cache WHERE cache_date = ?
    """, (dt,)).fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row[0])
        except Exception:
            return None
    return None


def get_scheduler_log(n: int = 10) -> list:
    conn = _get_db()
    c = conn.cursor()
    rows = c.execute("""
        SELECT run_at, run_type, symbols_ok, symbols_err, duration_s, notes
        FROM scheduler_log ORDER BY id DESC LIMIT ?
    """, (n,)).fetchall()
    conn.close()
    return [{"run_at": r[0], "type": r[1], "ok": r[2], "err": r[3],
             "duration_s": r[4], "notes": r[5]} for r in rows]


def log_run(run_type: str, ok: int, err: int, duration_s: float, notes: str = ""):
    conn = _get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO scheduler_log (run_at, run_type, symbols_ok, symbols_err, duration_s, notes)
        VALUES (?,?,?,?,?,?)
    """, (ist_now().isoformat(), run_type, ok, err, round(duration_s, 2), notes))
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════════════════════
# MAIN UPDATE JOB
# ══════════════════════════════════════════════════════════════════════════

def run_eod_update(verbose: bool = True):
    """Full end-of-day update: prices + quant analysis + planetary cache"""
    from data.instruments import ALL_INSTRUMENTS
    from core.quant_engine import full_quant_analysis
    from core.signal_engine import get_planet_dashboard

    start = time.time()
    today = date.today()

    # Bug fix: use the LAST ACTUAL TRADING DAY as trade_date
    # yfinance always returns the most recent trading day's data
    # but if today is weekend/holiday, we must NOT store it as today's date
    trade_date = today
    if not is_market_day(today):
        # Walk back to find the last trading day
        d = today - timedelta(days=1)
        while not is_market_day(d):
            d -= timedelta(days=1)
        trade_date = d
        if verbose:
            print(f"  [SCHED] Today ({today}) is non-trading — using last trading day: {trade_date}")

    ok, err = 0, 0

    if verbose:
        print(f"\n  [SCHED] Starting EOD update — {ist_now().strftime('%Y-%m-%d %H:%M IST')}")

    # 1. Fetch prices
    sym_map = {sym: inst.yfinance_symbol
               for sym, inst in ALL_INSTRUMENTS.items()
               if inst.yfinance_symbol}
    prices = fetch_eod_prices(sym_map)
    if prices:
        cache_prices(prices, trade_date)   # trade_date = last actual trading day
        if verbose:
            print(f"  [SCHED] Prices cached: {len(prices)} instruments for {trade_date}")

    # 2. Planetary dashboard
    try:
        planet_data = get_planet_dashboard(today)
        cache_planets(planet_data, today)
        if verbose:
            print("  [SCHED] Planetary data cached")
    except Exception as e:
        if verbose:
            print(f"  [SCHED] Planetary cache failed: {e}")

    # 3. Quant analysis for priority instruments
    PRIORITY = [
        "NIFTY50", "BANKNIFTY", "SENSEX", "NIFTYIT", "NIFTYPHARMA",
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "GOLD", "SILVER", "CRUDEOIL", "TATAMOTORS", "MARUTI",
    ]
    for sym in PRIORITY:
        inst = ALL_INSTRUMENTS.get(sym)
        if not inst:
            continue
        try:
            # Use cached close price if available
            price_row = prices.get(sym)
            current_price = price_row["close"] if price_row else (inst.all_time_high * 0.85)
            result = full_quant_analysis(
                symbol=sym,
                yf_symbol=inst.yfinance_symbol,
                current_price=current_price,
                atl=inst.all_time_low,
                ath=inst.all_time_high,
                trend_up=True,
            )
            # Trim chart data to save space
            result["chart"]["closes"] = result["chart"]["closes"][-120:]
            result["chart"]["dates"]  = result["chart"]["dates"][-120:]
            result["chart"]["highs"]  = result["chart"]["highs"][-120:]
            result["chart"]["lows"]   = result["chart"]["lows"][-120:]
            result["chart"]["volumes"] = result["chart"]["volumes"][-120:]
            result["chart"]["sma20"]  = result["chart"]["sma20"][-120:]
            result["chart"]["sma50"]  = result["chart"]["sma50"][-120:]
            result["chart"]["sma200"] = result["chart"]["sma200"][-120:]
            cache_quant(sym, result, today)
            ok += 1
        except Exception as e:
            err += 1
            if verbose:
                print(f"  [SCHED] Quant failed for {sym}: {e}")

    # 4. Incremental history top-up + ZigZag pivot refresh for updated symbols
    try:
        from download_history import incremental_update_symbol
        updated_syms = list(prices.keys())[:30]  # cap at 30 to keep update fast
        for sym in updated_syms:
            inst = ALL_INSTRUMENTS.get(sym)
            if inst and inst.yfinance_symbol:
                try:
                    incremental_update_symbol(sym, inst.yfinance_symbol, inst.inception_date)
                except Exception:
                    pass
        if verbose:
            print(f"  [SCHED] Incremental history + pivots refreshed for {len(updated_syms)} symbols")
    except ImportError:
        pass  # download_history not available

    # ── 5. Auto-fetch today's bulk/block deals (v3.9 — 3-source auto-fetcher) ──
    deals_saved = 0
    try:
        from fetch_institutional import auto_fetch_today as _auto_fetch, compute_volume_anomalies as _cva
        # auto_fetch_today() handles: already-fetched check, backfill gaps, all 3 sources
        deals_saved = _auto_fetch()
        if verbose:
            print(f"  [SCHED] Bulk/Block deals: {deals_saved} new records (incl. backfill)")
        # Always recompute volume anomalies for updated symbols
        for sym in list(prices.keys())[:20]:
            try: _cva(sym)
            except Exception: pass
    except Exception as _bd_err:
        if verbose:
            print(f"  [SCHED] Bulk deal fetch error (non-fatal): {_bd_err}")

    # ── 6. Gann Angle Scales Caching ──
    try:
        from core.gann_math import calibrate_gann_scale
        for sym in prices.keys():
            calibrate_gann_scale(sym)
        if verbose:
            print(f"  [SCHED] Gann scales calibrated and cached for {len(prices)} symbols")
    except Exception as _gs_err:
        if verbose:
            print(f"  [SCHED] Gann scale calibration warn: {_gs_err}")

    # ── 7. Gann Signals Backfill & Weight Recalibration ──
    try:
        def _backfill_gann_signals():
            conn = _get_db()
            cursor = conn.cursor()
            rows = cursor.execute("""
                SELECT id, symbol, fired_at, price_at_signal FROM signals 
                WHERE (outcome_price_5d IS NULL OR outcome_price_10d IS NULL OR outcome_price_20d IS NULL)
                  AND signal_subtype IS NOT NULL
            """).fetchall()
            for sig_id, symbol, fired_at, price_at_signal in rows:
                fwd_prices = cursor.execute("""
                    SELECT close FROM daily_prices 
                    WHERE symbol=? AND trade_date > ? 
                    ORDER BY trade_date ASC LIMIT 25
                """, (symbol, fired_at)).fetchall()
                updates = {}
                if len(fwd_prices) >= 5:
                    updates["outcome_price_5d"] = fwd_prices[4][0]
                if len(fwd_prices) >= 10:
                    updates["outcome_price_10d"] = fwd_prices[9][0]
                if len(fwd_prices) >= 20:
                    updates["outcome_price_20d"] = fwd_prices[19][0]
                if updates:
                    set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
                    params = list(updates.values()) + [sig_id]
                    cursor.execute(f"UPDATE signals SET {set_clause} WHERE id=?", params)
            conn.commit()
            conn.close()
            
        _backfill_gann_signals()
        from core.gann_math import recalibrate_gann_weights
        recalibrate_gann_weights()
        if verbose:
            print("  [SCHED] Gann sub-signal outcomes backfilled and weights recalibrated successfully")
    except Exception as _rc_err:
        if verbose:
            print(f"  [SCHED] Gann weights recalibration warn: {_rc_err}")

    # ── 8. Guardian Risk Engine — runs ONCE at EOD after prices are cached ───
    # PHASE 1 FIX (C1, C2, D1):
    #   Moved from portfolio_get (fired on every page load) to here.
    #   Uses correct exit prices: t_sl for SL-hit, t_t2 for T2-hit.
    #   Staleness guard: skips any position whose latest price is > 3 days old.
    try:
        guardian_result = run_guardian_eod(verbose=verbose)
        if verbose:
            print(f"  [SCHED] Guardian: {guardian_result['summary']}")
    except Exception as _g_err:
        if verbose:
            print(f"  [SCHED] Guardian error (non-fatal): {_g_err}")

    # -- 9. Daily P&L Monitor -- auto kill-switch if daily loss limit breached
    # PHASE 2 FIX (Fix 7): Runs AFTER Guardian so auto-closes are included.
    try:
        pnl_result = run_daily_pnl_monitor(verbose=verbose)
        if verbose:
            print(f"  [SCHED] PnL Monitor: {pnl_result['summary']}")
    except Exception as _pnl_err:
        if verbose:
            print(f"  [SCHED] PnL monitor error (non-fatal): {_pnl_err}")

    duration = time.time() - start
    log_run("EOD_UPDATE", ok, err, duration,
            f"prices={len(prices)}, quant={ok}/{len(PRIORITY)}, deals={deals_saved}")

    if verbose:
        print(f"  [SCHED] Done in {duration:.1f}s — {ok} quant ok, {err} failed, {deals_saved} deals saved")

    return {"ok": ok, "err": err, "prices": len(prices), "duration_s": round(duration, 2), "deals_saved": deals_saved}


# ══════════════════════════════════════════════════════════════════════════
# GUARDIAN RISK ENGINE — EOD POSITION MONITOR
# ══════════════════════════════════════════════════════════════════════════

# Slippage assumption for auto-exits (0.1% of price)
_SLIPPAGE_PCT = 0.001
# Max age of price data before guardian skips a position (trading days)
_MAX_PRICE_STALE_DAYS = 3


def run_guardian_eod(verbose: bool = True) -> dict:
    """
    Guardian Risk Engine — runs ONCE per EOD after prices are cached.

    PHASE 1 FIXES applied:
      C1: Removed from portfolio_get (no longer fires on page load).
          Now runs at 15:35 IST exactly once after prices are written.
      C2: Exit prices are correct:
            SL-hit  → exit at t_sl  (the agreed stop level), not stale close.
            T2-hit  → exit at t_t2  (the agreed target level), not stale close.
            T1-trail → trail SL to breakeven (entry price), not arbitrary close.
          A configurable slippage (0.1%) is applied to all auto-exits.
      D1: Staleness guard — if the latest price for a symbol is older than
          _MAX_PRICE_STALE_DAYS trading days, that position is skipped and
          logged. This prevents wrong auto-closes on weekends or data gaps.

    Actions:
      1. Trail SL to entry (breakeven) when T1 is hit.
      2. Auto-close at T2 price when T2 is hit (+ slippage).
      3. Auto-close at SL price when SL is breached (+ slippage).

    Returns a summary dict for logging.
    """
    conn = _get_db()
    try:
        open_trades = conn.execute(
            "SELECT id, symbol, entry_price, target1, target2, stop_loss, "
            "       portfolio_id, inv_type "
            "FROM positions WHERE status='OPEN'"
        ).fetchall()
    finally:
        conn.close()

    if not open_trades:
        return {"summary": "No open positions to evaluate", "trailed": 0, "closed": 0, "skipped": 0}

    trailed = 0
    closed  = 0
    skipped = 0
    today_str = date.today().isoformat()
    # cutoff: most recent allowed price date (3 trading days back)
    cutoff_date = (date.today() - timedelta(days=_MAX_PRICE_STALE_DAYS * 2)).isoformat()

    conn = _get_db()
    try:
        for trade in open_trades:
            t_id, t_sym, t_ent, t_t1, t_t2, t_sl, t_pf_id, t_inv_type = trade

            # ── D1: Staleness guard ─────────────────────────────────────────
            # Fetch the MOST RECENT price AND its date together
            px_row = conn.execute(
                "SELECT close, high, low, trade_date FROM daily_prices "
                "WHERE symbol=? AND close IS NOT NULL AND trade_date >= ? "
                "ORDER BY trade_date DESC LIMIT 1",
                (t_sym, cutoff_date)
            ).fetchone()

            if not px_row:
                # No fresh price found — skip this position
                if verbose:
                    print(
                        f"  [GUARD] SKIP {t_sym}: no price data within last "
                        f"{_MAX_PRICE_STALE_DAYS} trading days"
                    )
                skipped += 1
                continue

            cmp_close, cmp_high, cmp_low, price_date = px_row
            cmp_close = float(cmp_close)
            # Use high/low for T1/T2/SL breach detection (more realistic)
            day_high  = float(cmp_high) if cmp_high else cmp_close
            day_low   = float(cmp_low)  if cmp_low  else cmp_close

            t_ent = float(t_ent)
            t_t1  = float(t_t1)  if t_t1 else None
            t_t2  = float(t_t2)  if t_t2 else None
            t_sl  = float(t_sl)  if t_sl else None

            now_iso = ist_now_naive().isoformat()

            # ── C2: Priority order — check T2 first, then SL, then trail ───
            # T2 check: if today's high >= target2 → close at t_t2 (not cmp)
            if t_t2 and day_high >= t_t2:
                exit_px = round(t_t2 * (1 - _SLIPPAGE_PCT), 2)   # small slippage on sell
                shares  = _get_shares(conn, t_id)
                from core.indicators import calculate_transaction_costs
                tx_costs = calculate_transaction_costs(t_ent, exit_px, shares)
                real_pnl = round((exit_px - t_ent) * shares - tx_costs, 2)
                conn.execute(
                    "UPDATE positions SET status='CLOSED', exit_date=?, exit_price=?, "
                    "realized_pnl=?, exit_reason=?, updated_at=? WHERE id=?",
                    (today_str, exit_px, real_pnl, "T2 Hit (EOD Guardian)", now_iso, t_id)
                )
                closed += 1
                if verbose:
                    print(f"  [GUARD] CLOSED {t_sym} @ ₹{exit_px:,.2f} — T2 Hit  PnL: ₹{real_pnl:,.2f} (costs: ₹{tx_costs:.2f})")
                continue  # skip trailing check since position is now closed

            # SL check: if today's low <= stop_loss → close at t_sl (not cmp)
            if t_sl and day_low <= t_sl:
                exit_px  = round(t_sl * (1 + _SLIPPAGE_PCT), 2)  # slippage on SL (worse fill)
                shares  = _get_shares(conn, t_id)
                from core.indicators import calculate_transaction_costs
                tx_costs = calculate_transaction_costs(t_ent, exit_px, shares)
                real_pnl = round((exit_px - t_ent) * shares - tx_costs, 2)
                conn.execute(
                    "UPDATE positions SET status='CLOSED', exit_date=?, exit_price=?, "
                    "realized_pnl=?, exit_reason=?, updated_at=? WHERE id=?",
                    (today_str, exit_px, real_pnl, "SL Hit (EOD Guardian)", now_iso, t_id)
                )
                closed += 1
                if verbose:
                    print(f"  [GUARD] CLOSED {t_sym} @ ₹{exit_px:,.2f} — SL Hit  PnL: ₹{real_pnl:,.2f} (costs: ₹{tx_costs:.2f})")
                continue

            # T1 trail: if day's high >= target1 AND current SL is still below entry
            # → move SL up to entry price (breakeven protection)
            if t_t1 and day_high >= t_t1 and t_sl is not None and t_sl < t_ent:
                conn.execute(
                    "UPDATE positions SET stop_loss=?, updated_at=?, "
                    "exit_reason='T1 Hit — SL Trailed to Breakeven' WHERE id=?",
                    (t_ent, now_iso, t_id)
                )
                trailed += 1
                if verbose:
                    print(f"  [GUARD] TRAIL   {t_sym} — SL moved to entry ₹{t_ent:,.2f} (T1 reached)")

        conn.commit()
    finally:
        conn.close()

    summary = (
        f"{len(open_trades)} evaluated — "
        f"{closed} closed, {trailed} trailed, {skipped} skipped (stale price)"
    )
    return {"summary": summary, "trailed": trailed, "closed": closed, "skipped": skipped}


def _get_shares(conn, position_id: str) -> int:
    """Helper: fetch share count for a position within an open connection."""
    row = conn.execute("SELECT shares FROM positions WHERE id=?", (position_id,)).fetchone()
    return int(row[0]) if row and row[0] else 1


# ══════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════
# PHASE 2 FIX (Fix 9): CORRELATION MATRIX PRE-COMPUTATION
# ══════════════════════════════════════════════════════════════════════════

_CORR_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR",
    "BAJFINANCE", "KOTAKBANK", "SBIN", "AXISBANK", "LT", "WIPRO",
    "MARUTI", "TATAMOTORS", "SUNPHARMA", "DRREDDY", "ULTRACEMCO",
    "TATASTEEL", "JSWSTEEL", "ADANIENT", "NIFTY50", "BANKNIFTY",
    "GOLD", "SILVER", "CRUDEOIL",
]


def run_correlation_cache(verbose: bool = True) -> dict:
    """
    PHASE 2 FIX (Fix 9): Pre-compute pairwise Pearson correlation of returns
    for _CORR_SYMBOLS and store in the correlation_cache table.
    Runs nightly at 22:05 IST. risk_gates reads from this cache first.
    """
    import math
    from collections import defaultdict

    conn = _get_db()
    try:
        placeholders = ",".join("?" * len(_CORR_SYMBOLS))
        rows = conn.execute(
            f"SELECT symbol, trade_date, close FROM daily_prices "
            f"WHERE symbol IN ({placeholders}) AND close IS NOT NULL "
            f"ORDER BY symbol, trade_date DESC",
            _CORR_SYMBOLS
        ).fetchall()
    finally:
        conn.close()

    price_by_sym = defaultdict(list)
    for sym, tdate, close in rows:
        if len(price_by_sym[sym]) < 120:
            price_by_sym[sym].append(float(close))

    def _pearson(s1, s2):
        min_len = min(len(s1), len(s2))
        if min_len < 10:
            return 0.0
        r1 = [(s1[i] - s1[i+1]) / s1[i+1] for i in range(min_len - 1)]
        r2 = [(s2[i] - s2[i+1]) / s2[i+1] for i in range(min_len - 1)]
        n  = len(r1)
        if n == 0:
            return 0.0
        m1 = sum(r1) / n
        m2 = sum(r2) / n
        num  = sum((r1[i] - m1) * (r2[i] - m2) for i in range(n))
        den1 = sum((x - m1) ** 2 for x in r1)
        den2 = sum((x - m2) ** 2 for x in r2)
        if den1 == 0 or den2 == 0:
            return 0.0
        return round(num / math.sqrt(den1 * den2), 4)

    now_iso = ist_now_naive().isoformat()
    syms    = [s for s in _CORR_SYMBOLS if len(price_by_sym[s]) >= 10]
    pairs   = 0

    conn = _get_db()
    try:
        for i, s1 in enumerate(syms):
            for s2 in syms[i+1:]:
                corr = _pearson(price_by_sym[s1], price_by_sym[s2])
                conn.execute("""
                    INSERT INTO correlation_cache (sym1, sym2, corr, computed_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(sym1, sym2) DO UPDATE SET
                        corr=excluded.corr, computed_at=excluded.computed_at
                """, (s1, s2, corr, now_iso))
                conn.execute("""
                    INSERT INTO correlation_cache (sym1, sym2, corr, computed_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(sym1, sym2) DO UPDATE SET
                        corr=excluded.corr, computed_at=excluded.computed_at
                """, (s2, s1, corr, now_iso))
                pairs += 1
        conn.commit()
    finally:
        conn.close()

    if verbose:
        print(f"  [CORR] Computed {pairs} pairs for {len(syms)} symbols", flush=True)
    return {"ok": True, "pairs": pairs, "symbols": len(syms)}


# ══════════════════════════════════════════════════════════════════════════
# PHASE 2 FIX (Fix 7): DAILY P&L MONITOR + AUTO KILL-SWITCH
# ══════════════════════════════════════════════════════════════════════════


def run_daily_pnl_monitor(verbose: bool = True) -> dict:
    """
    PHASE 2 FIX (Fix 7): For every user whose kill_switch is OFF, sum today's
    realized PnL. If it breaches their daily_loss_limit, auto-set kill_switch=1.
    Called at EOD after run_guardian_eod().
    """
    today_s  = date.today().isoformat()
    now_iso  = ist_now_naive().isoformat()
    breaches = []
    skipped  = 0

    conn = _get_db()
    try:
        users = conn.execute(
            "SELECT rs.user_id, rs.daily_loss_limit, p.id "
            "FROM risk_settings rs "
            "JOIN portfolios p ON p.user_id = rs.user_id "
            "WHERE rs.user_id IS NOT NULL AND rs.kill_switch = 0"
        ).fetchall()

        for user_id, daily_limit, pf_id in users:
            daily_limit = float(daily_limit) if daily_limit else 50000.0
            pnl_row = conn.execute(
                "SELECT SUM(realized_pnl) FROM positions "
                "WHERE portfolio_id=? AND status='CLOSED' AND exit_date=?",
                (pf_id, today_s)
            ).fetchone()
            today_pnl = float(pnl_row[0]) if pnl_row and pnl_row[0] is not None else 0.0

            if today_pnl <= -daily_limit:
                conn.execute(
                    "UPDATE risk_settings SET kill_switch=1, updated_at=? WHERE user_id=?",
                    (now_iso, user_id)
                )
                breaches.append({"user_id": user_id, "today_pnl": round(today_pnl, 2), "limit": -daily_limit})
                if verbose:
                    print(
                        f"  [PNLMON] BREACH {user_id}: pnl=₹{today_pnl:,.2f} "
                        f"limit=-₹{daily_limit:,.2f} → kill_switch AUTO-ACTIVATED",
                        flush=True
                    )
            else:
                skipped += 1

        conn.commit()
    finally:
        conn.close()

    summary = f"{len(breaches)} breach(es), {skipped} within limit"
    return {"summary": summary, "breaches": breaches, "ok_count": skipped}

# BACKGROUND THREAD SCHEDULER
# ══════════════════════════════════════════════════════════════════════════

class MarketScheduler:
    """
    Background thread that:
    - Runs EOD update at 15:35 IST every market day
    - Runs pre-open cache warm-up at 09:00 IST
    - Also runs immediately on first startup if today not cached yet
    """

    def __init__(self):
        self._thread = None
        self._stop   = threading.Event()
        self._status = {
            "running": False,
            "last_run": None,
            "next_run": None,
            "last_result": None,
        }
        init_db()

    @property
    def status(self):
        return dict(self._status)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="MarketScheduler")
        self._thread.start()
        print("  [SCHED] Scheduler started — auto-update at 15:35 IST")
        # Warm up if today not cached yet
        threading.Thread(target=self._warmup, daemon=True).start()
        # Trigger news fetch on startup if not already done today
        threading.Thread(target=self._startup_news_check,
                         daemon=True, name="StartupNewsCheck").start()

    def stop(self):
        self._stop.set()

    def trigger_now(self):
        """Manually trigger an update"""
        threading.Thread(target=self._run_update, daemon=True, name="ManualUpdate").start()
        return {"message": "Update triggered"}

    def _warmup(self):
        """Run a quick update if today's data not in cache"""
        time.sleep(3)  # let server start first
        today = date.today()
        prices = get_cached_prices(today)
        if not prices:
            print("  [SCHED] No cache for today — running warmup update...")
            self._run_update(run_type="WARMUP")

    def _startup_news_check(self):
        """
        On startup: fetch news if not fetched in the last 60 minutes.
        Uses full datetime so a 2nd run within the same day still fetches
        any news published since the 1st run.
        """
        import time as _t, sqlite3 as _sq_nc, os as _os_nc
        _t.sleep(15)  # wait for DB init to complete
        try:
            _db = _os_nc.path.join(_os_nc.path.dirname(__file__), "..", "market_data_v2.db")
            _db = _os_nc.normpath(_db)
            _c  = _sq_nc.connect(_db, timeout=5)
            # Check if ANY fetch happened in the last 60 minutes (not just today)
            _cutoff = (ist_now() - timedelta(minutes=60)).strftime("%Y-%m-%d %H:%M:%S")
            _cnt = _c.execute(
                "SELECT COUNT(*) FROM news_sentiment WHERE fetched_at >= ?",
                (_cutoff,)).fetchone()[0]
            _c.close()
            if _cnt == 0:
                print(f"  [SCHED] No news in last 60min — running startup fetch", flush=True)
                self._run_news_fetch()
            else:
                print(f"  [SCHED] News recently fetched ({_cnt} items since {_cutoff}) — skipping", flush=True)
        except Exception as _e:
            print(f"  [SCHED] Startup news check error: {_e}", flush=True)

    def _run_news_fetch(self):
        """Fetch today's news for all symbols — runs every day including weekends."""
        if self._status.get("news_running"):
            print("  [SCHED] News fetch already running, skipping", flush=True)
            return
        self._status["news_running"] = True
        try:
            print(f"  [SCHED] Daily news fetch starting — {ist_now().strftime('%Y-%m-%d %H:%M IST')}", flush=True)
            import importlib.util as _ilu_n, os as _os_n
            _bn_path = _os_n.path.join(_os_n.path.dirname(__file__), "bulk_news_fetch.py")
            if _os_n.path.exists(_bn_path):
                _bn_spec = _ilu_n.spec_from_file_location("bulk_news_fetch", _bn_path)
                _bn_mod  = _ilu_n.module_from_spec(_bn_spec)
                _bn_spec.loader.exec_module(_bn_mod)
                result = _bn_mod.bulk_fetch_all(delay_secs=1.5, max_per_symbol=20, verbose=True)
                print(f"  [SCHED] News fetch done: {result}", flush=True)
            else:
                print(f"  [SCHED] bulk_news_fetch.py not found at {_bn_path}", flush=True)
        except Exception as e:
            print(f"  [SCHED] News fetch error: {e}", flush=True)
        finally:
            self._status["news_running"] = False

    def _run_update(self, run_type: str = "EOD_UPDATE"):
        if self._status["running"]:
            print("  [SCHED] Update already running, skipping")
            return
        self._status["running"] = True
        try:
            result = run_eod_update(verbose=True)
            self._status["last_run"] = ist_now().isoformat()
            self._status["last_result"] = result
        except Exception as e:
            print(f"  [SCHED] Update error: {e}")
            self._status["last_result"] = {"error": str(e)}
        finally:
            self._status["running"] = False

    def _loop(self):
        """Main scheduler loop — checks every minute"""
        while not self._stop.is_set():
            now = ist_now()

            # ── Daily news fetch: 08:00 IST every day (incl. weekends/holidays) ──
            # News runs regardless of market status — financial news never stops
            if (now.hour == 8 and now.minute == 0 and now.second < 60):
                threading.Thread(target=self._run_news_fetch,
                                 daemon=True, name="DailyNewsFetch").start()

            # EOD run: 15:35 IST on market days only (prices + bulk deals + quant)
            if (is_market_day() and
                now.hour == 15 and now.minute == 35 and now.second < 60):
                self._status["next_run"] = None
                self._run_update("EOD_UPDATE")

            # RAG nightly ingest: 22:00 IST every day (free local LLM pipeline)
            # Fetches earnings transcripts, analyst reports, EPS data and embeds
            # them locally using sentence-transformers + ChromaDB. No API key.
            if (now.hour == 22 and now.minute == 0 and now.second < 60):
                threading.Thread(target=run_rag_nightly_ingest,
                                 daemon=True, name="RAGNightlyIngest").start()

            # PHASE 2 FIX (Fix 9): Nightly correlation matrix pre-computation 22:05 IST
            if (now.hour == 22 and now.minute == 5 and now.second < 60):
                threading.Thread(target=run_correlation_cache,
                                 daemon=True, name="CorrCache").start()

            # Pre-open cache warm: 09:00 IST on market days
            if (is_market_day() and
                now.hour == 9 and now.minute == 0 and now.second < 60):
                self._run_update("PRE_OPEN")

            # Calculate next run time
            tomorrow = now.date() + timedelta(days=1)
            while not is_market_day(tomorrow):
                tomorrow += timedelta(days=1)
            # next_dt is a naive IST datetime (15:35 on next trading day)
            # Attach IST tzinfo so it converts correctly to UTC for storage
            next_dt_ist = datetime.combine(tomorrow, datetime.min.time().replace(hour=15, minute=35)).replace(tzinfo=_IST)
            self._status["next_run"] = next_dt_ist.astimezone(timezone.utc).isoformat()

            self._stop.wait(60)  # check every minute


# Singleton instance
_scheduler: Optional[MarketScheduler] = None


def get_scheduler() -> MarketScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = MarketScheduler()
    return _scheduler

# ══════════════════════════════════════════════════════════════════════════════
# v4.0: DAILY REVERSAL ZONE REBUILD
# Run at 6:00 AM IST every market day — BEFORE the market opens.
# Builds forward-looking reversal zones for all 40 symbols.
# Result stored in reversal_map.ZONE_CACHE (in-memory dict).
# ══════════════════════════════════════════════════════════════════════════════

_ZONE_REBUILD_RUNNING = False


def rebuild_reversal_zones(verbose=True):
    """
    Rebuild reversal zones for all instruments.
    Called by the daily scheduler at 6 AM IST.

    Requires: price history in market_data_v2.db (daily_prices table).
    Returns summary dict: {symbol: zone_count, ...}
    """
    global _ZONE_REBUILD_RUNNING
    if _ZONE_REBUILD_RUNNING:
        return {}
    _ZONE_REBUILD_RUNNING = True
    summary = {}

    try:
        from core.reversal_map import build_zones_for_symbol
        from data.instruments import ALL_INSTRUMENTS
    except ImportError as e:
        if verbose:
            print(f"  [ZoneRebuild] Import error: {e}")
        _ZONE_REBUILD_RUNNING = False
        return {}

    today = date.today()
    conn  = _get_db()

    for inst in ALL_INSTRUMENTS:
        sym = inst.symbol
        try:
            cutoff = (today - timedelta(days=730)).isoformat()
            rows   = conn.execute("""
                SELECT trade_date, high, low, close, volume
                FROM daily_prices
                WHERE symbol=? AND close IS NOT NULL AND trade_date >= ?
                ORDER BY trade_date ASC
            """, (sym, cutoff)).fetchall()

            if len(rows) < 60:
                if verbose:
                    print(f"  [ZoneRebuild] {sym}: skip (only {len(rows)} rows)")
                summary[sym] = 0
                continue

            closes  = [float(r[3]) for r in rows]
            highs   = [float(r[1] or r[3]) for r in rows]
            lows    = [float(r[2] or r[3]) for r in rows]
            volumes = [float(r[4] or 0) for r in rows]

            piv_row = conn.execute("""
                SELECT pivot_price, pivot_date FROM pivot_levels
                WHERE symbol=? AND label IN ('ATL','MAJOR_BOTTOM_LOW','LAST_SWING_LOW')
                ORDER BY CASE label WHEN 'ATL' THEN 0 WHEN 'MAJOR_BOTTOM_LOW' THEN 1 ELSE 2 END
                LIMIT 1
            """, (sym,)).fetchone()

            pivot_price = float(piv_row[0]) if piv_row else closes[0]
            pivot_date_str = piv_row[1] if piv_row else rows[0][0]
            try:
                pivot_dt = date.fromisoformat(pivot_date_str[:10])
            except Exception:
                pivot_dt = today - timedelta(days=365)

            atl_row = conn.execute("""
                SELECT pivot_price FROM pivot_levels
                WHERE symbol=? AND label='ATL' LIMIT 1
            """, (sym,)).fetchone()
            atl_price = float(atl_row[0]) if atl_row else min(lows)

            zones = build_zones_for_symbol(
                symbol=sym,
                closes=closes, highs=highs, lows=lows, volumes=volumes,
                pivot_price=pivot_price, pivot_date=pivot_dt,
                atl_price=atl_price,
                analysis_date=today,
            )

            summary[sym] = len(zones)
            if verbose:
                grades = {"EXTREME": 0, "HIGH": 0, "MODERATE": 0}
                for z in zones:
                    grades[z.grade] = grades.get(z.grade, 0) + 1
                g = grades
                print(f"  [ZoneRebuild] {sym}: {len(zones)} zones "
                      f"(EXT={g['EXTREME']} HIGH={g['HIGH']} MOD={g['MODERATE']})")

        except Exception as ex:
            if verbose:
                print(f"  [ZoneRebuild] {sym}: error — {ex}")
            summary[sym] = 0

    conn.close()
    _ZONE_REBUILD_RUNNING = False
    total = sum(summary.values())
    if verbose:
        print(f"  [ZoneRebuild] Done — {len(summary)} symbols, {total} total zones built")
    return summary

# ══════════════════════════════════════════════════════════════════════════════
# RAG NIGHTLY INGEST JOB
# Run at 22:00 IST every night — after market close.
# Fetches and embeds new earnings transcripts, analyst reports, EPS data.
# Incremental: skips docs already seen (SHA-256 hash deduplicated).
# No API keys required — all free sources.
# ══════════════════════════════════════════════════════════════════════════════

_RAG_INGEST_RUNNING = False


def run_rag_nightly_ingest(verbose: bool = True) -> dict:
    """
    Trigger the RAG nightly ingest for all equity instruments.
    Called by the scheduler at 22:00 IST.
    Safe to call manually from the UI via the rag_ingest endpoint.
    """
    global _RAG_INGEST_RUNNING
    if _RAG_INGEST_RUNNING:
        if verbose:
            print("  [RAG] Nightly ingest already running — skipped.", flush=True)
        return {"ok": False, "reason": "already_running"}

    _RAG_INGEST_RUNNING = True
    try:
        from core.rag_engine import nightly_ingest, init_rag_tables, RAG_AVAILABLE
        if not RAG_AVAILABLE:
            if verbose:
                print("  [RAG] Nightly ingest skipped — sentence-transformers or "
                      "chromadb not installed. Run: pip install sentence-transformers "
                      "chromadb --break-system-packages", flush=True)
            return {"ok": False, "reason": "dependencies_missing"}
        init_rag_tables()
        result = nightly_ingest(verbose=verbose)
        return result
    except Exception as e:
        if verbose:
            print(f"  [RAG] Nightly ingest error: {e}", flush=True)
        return {"ok": False, "error": str(e)}
    finally:
        _RAG_INGEST_RUNNING = False