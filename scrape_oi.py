"""
scrape_oi.py — NSE Open Interest Pipeline
==========================================
Scrapes the NSE option chain API for F&O symbols (indices + stocks),
computes PCR (Put-Call Ratio) and Max Pain, then saves to market_data_v2.db.

Usage:
  python scrape_oi.py                    # scrape all F&O symbols
  python scrape_oi.py --symbol NIFTY50   # single symbol
  python scrape_oi.py --dry-run          # print data without saving

Schedule:
  09:30 IST daily → pre-open snapshot
  15:45 IST daily → post-close snapshot (main)
"""

import os
import sys
import time
import sqlite3
import argparse
import requests
import json
from datetime import date, datetime
from typing import List, Dict, Tuple, Optional

# ─── DB path ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "market_data_v2.db")

# ─── NSE F&O symbols to track ─────────────────────────────────────────────────
NSE_INDEX_SYMBOLS = [
    "NIFTY",
    "BANKNIFTY",
    "FINNIFTY",
    "MIDCPNIFTY",
]



# ─── NSE session headers (required to avoid 403) ──────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer":         "https://www.nseindia.com/option-chain",
    "Connection":      "keep-alive",
}

NSE_BASE_URL      = "https://www.nseindia.com"
OC_INDEX_URL      = "https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
OC_EQUITY_URL     = "https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
# NSE requires hitting several pages to establish valid session cookies
COOKIE_WARM_URLS  = [
    "https://www.nseindia.com/",
    "https://www.nseindia.com/option-chain",
    "https://www.nseindia.com/market-data/live-equity-market",
]


# ═══════════════════════════════════════════════════════════════════════════════
# DB SETUP
# ═══════════════════════════════════════════════════════════════════════════════

def ensure_db_tables(conn: sqlite3.Connection) -> None:
    """Create OI tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS option_chain_data (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol          TEXT    NOT NULL,
            trade_date      TEXT    NOT NULL,
            expiry_date     TEXT    NOT NULL,
            strike          REAL    NOT NULL,
            option_type     TEXT    NOT NULL,
            oi              INTEGER,
            change_in_oi    INTEGER,
            volume          INTEGER,
            iv              REAL,
            ltp             REAL,
            bid             REAL,
            ask             REAL,
            delta           REAL,
            session         TEXT    DEFAULT 'EOD',
            fetched_at      TEXT    DEFAULT (datetime('now','localtime')),
            UNIQUE(symbol, trade_date, expiry_date, strike, option_type, session)
        );

        CREATE INDEX IF NOT EXISTS idx_oc_sym_date
            ON option_chain_data(symbol, trade_date);

        CREATE INDEX IF NOT EXISTS idx_oc_expiry
            ON option_chain_data(symbol, expiry_date, trade_date);

        CREATE TABLE IF NOT EXISTS pcr_summary (
            symbol          TEXT    NOT NULL,
            trade_date      TEXT    NOT NULL,
            expiry_date     TEXT    NOT NULL,
            session         TEXT    DEFAULT 'EOD',
            total_ce_oi     INTEGER,
            total_pe_oi     INTEGER,
            pcr             REAL,
            max_pain        REAL,
            atm_strike      REAL,
            spot_price      REAL,
            local_pcr       REAL,
            iv_skew         REAL,
            atm_vol_oi_ratio REAL,
            fetched_at      TEXT    DEFAULT (datetime('now','localtime')),
            PRIMARY KEY (symbol, trade_date, expiry_date, session)
        );

        CREATE INDEX IF NOT EXISTS idx_pcr_sym
            ON pcr_summary(symbol, trade_date DESC);
    """)

    # Schema Migrations
    for table, col, col_type in [
        ('pcr_summary', 'local_pcr', 'REAL'),
        ('pcr_summary', 'session', "TEXT DEFAULT 'EOD'"),
        ('pcr_summary', 'iv_skew', 'REAL'),
        ('pcr_summary', 'atm_vol_oi_ratio', 'REAL'),
        ('option_chain_data', 'session', "TEXT DEFAULT 'EOD'"),
    ]:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass

    migrated = False
    try:
        info = conn.execute("PRAGMA table_info(pcr_summary)").fetchall()
        pk_cols = [r[1] for r in info if r[5] > 0]
        if 'session' not in pk_cols:
            conn.execute("ALTER TABLE pcr_summary RENAME TO pcr_summary_old")
            conn.execute("""
                CREATE TABLE pcr_summary (
                    symbol          TEXT    NOT NULL,
                    trade_date      TEXT    NOT NULL,
                    expiry_date     TEXT    NOT NULL,
                    session         TEXT    DEFAULT 'EOD',
                    total_ce_oi     INTEGER,
                    total_pe_oi     INTEGER,
                    pcr             REAL,
                    max_pain        REAL,
                    atm_strike      REAL,
                    spot_price      REAL,
                    local_pcr       REAL,
                    iv_skew         REAL,
                    atm_vol_oi_ratio REAL,
                    fetched_at      TEXT    DEFAULT (datetime('now','localtime')),
                    PRIMARY KEY (symbol, trade_date, expiry_date, session)
                )
            """)
            conn.execute("""
                INSERT INTO pcr_summary (symbol, trade_date, expiry_date, total_ce_oi, total_pe_oi, pcr, max_pain, atm_strike, spot_price, local_pcr, session, fetched_at)
                SELECT symbol, trade_date, expiry_date, total_ce_oi, total_pe_oi, pcr, max_pain, atm_strike, spot_price, local_pcr, session, fetched_at
                FROM pcr_summary_old
            """)
            conn.execute("DROP TABLE pcr_summary_old")
            
            conn.execute("ALTER TABLE option_chain_data RENAME TO option_chain_data_old")
            conn.execute("""
                CREATE TABLE option_chain_data (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol          TEXT    NOT NULL,
                    trade_date      TEXT    NOT NULL,
                    expiry_date     TEXT    NOT NULL,
                    strike          REAL    NOT NULL,
                    option_type     TEXT    NOT NULL,
                    oi              INTEGER,
                    change_in_oi    INTEGER,
                    volume          INTEGER,
                    iv              REAL,
                    ltp             REAL,
                    bid             REAL,
                    ask             REAL,
                    delta           REAL,
                    session         TEXT    DEFAULT 'EOD',
                    fetched_at      TEXT    DEFAULT (datetime('now','localtime')),
                    UNIQUE(symbol, trade_date, expiry_date, strike, option_type, session)
                )
            """)
            conn.execute("""
                INSERT INTO option_chain_data (id, symbol, trade_date, expiry_date, strike, option_type, oi, change_in_oi, volume, iv, ltp, bid, ask, delta, session, fetched_at)
                SELECT id, symbol, trade_date, expiry_date, strike, option_type, oi, change_in_oi, volume, iv, ltp, bid, ask, delta, session, fetched_at
                FROM option_chain_data_old
            """)
            conn.execute("DROP TABLE option_chain_data_old")
            migrated = True
    except Exception as e:
        pass
    conn.commit()
    print("[DB] Tables ready: option_chain_data, pcr_summary")


# ═══════════════════════════════════════════════════════════════════════════════
# NSE SESSION + FETCH
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from jugaad_data.nse import NSELive
    HAVE_JUGAAD = True
except ImportError:
    HAVE_JUGAAD = False
    NSELive = None

_http_sess_global = None

def _new_http_session():
    import requests
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    })
    try:
        s.get("https://www.nseindia.com", timeout=8)
        time.sleep(0.5)
        s.get("https://www.nseindia.com/option-chain", timeout=8)
        time.sleep(0.5)
    except Exception:
        pass
    s.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nseindia.com/option-chain",
        "X-Requested-With": "XMLHttpRequest"
    })
    return s

def _new_session():
    if HAVE_JUGAAD:
        try:
            return NSELive()
        except Exception:
            pass
    return _new_http_session()

def fetch_option_chain(n, symbol: str, is_index: bool = True) -> Optional[dict]:
    """
    Fetch raw option chain JSON from NSE using jugaad-data or direct requests fallback.
    Returns parsed dict or None on failure.
    """
    global _http_sess_global

    # 1. Try jugaad-data if n is NSELive
    if HAVE_JUGAAD and n is not None and hasattr(n, 'index_option_chain'):
        for attempt in range(2):
            try:
                if is_index:
                    data = n.index_option_chain(symbol)
                else:
                    data = n.equities_option_chain(symbol)
                if data and isinstance(data, dict) and "records" in data and data.get("records"):
                    return data
            except Exception:
                pass
            time.sleep(0.8)

    # 2. Fallback to HTTP requests with warmed session
    if _http_sess_global is None:
        if isinstance(n, requests.Session):
            _http_sess_global = n
        else:
            _http_sess_global = _new_http_session()

    url = OC_INDEX_URL.format(symbol=symbol) if is_index else OC_EQUITY_URL.format(symbol=symbol)
    
    for attempt in range(3):
        try:
            r = _http_sess_global.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict) and "records" in data and data.get("records"):
                    return data
            elif r.status_code in (401, 403):
                _http_sess_global = _new_http_session()
        except Exception:
            pass
        time.sleep(1.0)
    return None



# ═══════════════════════════════════════════════════════════════════════════════
# PARSE + COMPUTE
# ═══════════════════════════════════════════════════════════════════════════════

def parse_chain(raw: dict, symbol: str,
                trade_date: str) -> Tuple[List[dict], List[str], float]:
    """
    Parse NSE option chain JSON into flat row list.

    Returns:
        rows        : list of dicts (one per strike × option_type)
        expiries    : sorted list of expiry date strings
        spot_price  : underlying spot price
    """
    records   = raw.get("records", {})
    expiries  = sorted(records.get("expiryDates", []))
    spot_price = float(records.get("underlyingValue", 0))
    raw_data  = records.get("data", [])

    rows = []
    for entry in raw_data:
        expiry = entry.get("expiryDate", "")
        strike = float(entry.get("strikePrice", 0))

        for opt_type in ("CE", "PE"):
            d = entry.get(opt_type, {})
            if not d:
                continue
            rows.append({
                "symbol":       symbol,
                "trade_date":   trade_date,
                "expiry_date":  expiry,
                "strike":       strike,
                "option_type":  opt_type,
                "oi":           int(d.get("openInterest", 0) or 0),
                "change_in_oi": int(d.get("changeinOpenInterest", 0) or 0),
                "volume":       int(d.get("totalTradedVolume", 0) or 0),
                "iv":           float(d.get("impliedVolatility", 0) or 0),
                "ltp":          float(d.get("lastPrice", 0) or 0),
                "bid":          float(d.get("bidprice", 0) or 0),
                "ask":          float(d.get("askPrice", 0) or 0),
            })
    return rows, expiries, spot_price


def compute_pcr(rows: List[dict], expiry: str) -> Tuple[int, int, float]:
    """
    Compute Put-Call Ratio for a given expiry.
    Returns (total_ce_oi, total_pe_oi, pcr).
    """
    ce_oi = sum(r["oi"] for r in rows
                if r["option_type"] == "CE" and r["expiry_date"] == expiry)
    pe_oi = sum(r["oi"] for r in rows
                if r["option_type"] == "PE" and r["expiry_date"] == expiry)
    pcr = round(pe_oi / ce_oi, 4) if ce_oi > 0 else 0.0
    return ce_oi, pe_oi, pcr


def compute_max_pain(rows: List[dict], expiry: str) -> float:
    """
    Compute max pain strike for a given expiry.

    Max pain = strike where option writers (sellers) lose the least,
    i.e., total payout to option buyers is minimized.

    Method: for each strike S, compute total payout = Σ(CE payout) + Σ(PE payout)
      CE payout at S = Σ [ max(0, S - strike_k) × CE_OI_k ]  for all k < S
      PE payout at S = Σ [ max(0, strike_k - S) × PE_OI_k ]  for all k > S
    Returns the strike with minimum total payout.
    """
    expiry_rows = [r for r in rows if r["expiry_date"] == expiry]
    if not expiry_rows:
        return 0.0

    strikes = sorted(set(r["strike"] for r in expiry_rows))
    ce_oi   = {r["strike"]: r["oi"] for r in expiry_rows if r["option_type"] == "CE"}
    pe_oi   = {r["strike"]: r["oi"] for r in expiry_rows if r["option_type"] == "PE"}

    min_pain   = float("inf")
    max_pain_s = strikes[0]

    for s in strikes:
        ce_pain = sum(max(0.0, s - k) * ce_oi.get(k, 0) for k in strikes)
        pe_pain = sum(max(0.0, k - s) * pe_oi.get(k, 0) for k in strikes)
        total   = ce_pain + pe_pain
        if total < min_pain:
            min_pain   = total
            max_pain_s = s

    return max_pain_s


def find_atm_strike(rows: List[dict], expiry: str, spot: float) -> float:
    """Find the ATM (at-the-money) strike closest to spot price."""
    strikes = sorted(set(r["strike"] for r in rows if r["expiry_date"] == expiry))
    if not strikes:
        return 0.0
    return min(strikes, key=lambda k: abs(k - spot))


# ═══════════════════════════════════════════════════════════════════════════════
# SAVE TO DB
# ═══════════════════════════════════════════════════════════════════════════════

def save_chain_rows(conn: sqlite3.Connection, rows: List[dict]) -> int:
    """Upsert option chain rows. Returns count inserted/updated."""
    if not rows:
        return 0
    conn.executemany("""
        INSERT INTO option_chain_data
            (symbol, trade_date, expiry_date, strike, option_type,
             oi, change_in_oi, volume, iv, ltp, bid, ask, session)
        VALUES
            (:symbol, :trade_date, :expiry_date, :strike, :option_type,
             :oi, :change_in_oi, :volume, :iv, :ltp, :bid, :ask, :session)
        ON CONFLICT(symbol, trade_date, expiry_date, strike, option_type, session)
        DO UPDATE SET
            oi           = excluded.oi,
            change_in_oi = excluded.change_in_oi,
            volume       = excluded.volume,
            iv           = excluded.iv,
            ltp          = excluded.ltp,
            bid          = excluded.bid,
            ask          = excluded.ask,
            fetched_at   = datetime('now','localtime')
    """, rows)
    conn.commit()
    return len(rows)


def save_pcr_summary(conn: sqlite3.Connection, symbol: str, trade_date: str,
                     expiry: str, ce_oi: int, pe_oi: int, pcr: float,
                     max_pain: float, atm: float, spot: float,
                     local_pcr: float = 0.0, iv_skew: float = 0.0,
                     atm_vol_oi_ratio: float = 0.0, session: str = 'EOD') -> None:
    """Upsert PCR summary row."""
    conn.execute("""
        INSERT INTO pcr_summary
            (symbol, trade_date, expiry_date, session, total_ce_oi, total_pe_oi,
             pcr, max_pain, atm_strike, spot_price, local_pcr, iv_skew, atm_vol_oi_ratio)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(symbol, trade_date, expiry_date, session)
        DO UPDATE SET
            total_ce_oi = excluded.total_ce_oi,
            total_pe_oi = excluded.total_pe_oi,
            pcr         = excluded.pcr,
            max_pain    = excluded.max_pain,
            atm_strike  = excluded.atm_strike,
            spot_price  = excluded.spot_price,
            local_pcr   = excluded.local_pcr,
            iv_skew     = excluded.iv_skew,
            atm_vol_oi_ratio = excluded.atm_vol_oi_ratio,
            fetched_at  = datetime('now','localtime')
    """, (symbol, trade_date, expiry, session, ce_oi, pe_oi, pcr,
          max_pain, atm, spot, local_pcr, iv_skew, atm_vol_oi_ratio))
    conn.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def scrape_symbol(sess: requests.Session, conn: sqlite3.Connection,
                  symbol: str, is_index: bool, trade_date: str,
                  dry_run: bool = False) -> bool:
    """
    Full pipeline for one symbol:
    fetch → parse → PCR → max pain → save.
    Returns True on success.
    """
    raw = fetch_option_chain(sess, symbol, is_index=is_index)
    if not raw:
        print(f"  [{symbol}] SKIP — no data")
        return False

    rows, expiries, spot = parse_chain(raw, symbol, trade_date)
    if not rows:
        print(f"  [{symbol}] SKIP — empty chain")
        return False

    # Use the nearest expiry as primary
    near_expiry = expiries[0] if expiries else ""

    ce_oi, pe_oi, pcr = compute_pcr(rows, near_expiry)
    max_pain_s        = compute_max_pain(rows, near_expiry)
    atm               = find_atm_strike(rows, near_expiry, spot)

    # Advanced metrics
    local_pcr = 0.0
    iv_skew = 0.0
    atm_vol_oi_ratio = 0.0
    
    expiry_rows = [r for r in rows if r["expiry_date"] == near_expiry]
    if spot > 0 and expiry_rows:
        # local PCR (+/- 5%)
        local_ce = sum(r["oi"] for r in expiry_rows if r["option_type"] == "CE" and (spot*0.95) <= r["strike"] <= (spot*1.05))
        local_pe = sum(r["oi"] for r in expiry_rows if r["option_type"] == "PE" and (spot*0.95) <= r["strike"] <= (spot*1.05))
        local_pcr = round(local_pe / local_ce, 4) if local_ce > 0 else 0.0
        
        # ATM Vol/OI
        atm_ce_rows = [r for r in expiry_rows if r["strike"] == atm and r["option_type"] == "CE"]
        atm_pe_rows = [r for r in expiry_rows if r["strike"] == atm and r["option_type"] == "PE"]
        atm_vol = sum(r["volume"] for r in atm_ce_rows + atm_pe_rows)
        atm_oi = sum(r["oi"] for r in atm_ce_rows + atm_pe_rows)
        atm_vol_oi_ratio = float(atm_vol) / float(atm_oi) if atm_oi > 0 else 0.0
        
        # IV Skew
        strikes = sorted(set(r["strike"] for r in expiry_rows))
        if strikes:
            put_target = spot * 0.95
            call_target = spot * 1.05
            put_s = min(strikes, key=lambda k: abs(k - put_target))
            call_s = min(strikes, key=lambda k: abs(k - call_target))
            
            p_iv_list = [r["iv"] for r in expiry_rows if r["strike"] == put_s and r["option_type"] == "PE"]
            c_iv_list = [r["iv"] for r in expiry_rows if r["strike"] == call_s and r["option_type"] == "CE"]
            p_iv = p_iv_list[0] if p_iv_list else 0.0
            c_iv = c_iv_list[0] if c_iv_list else 0.0
            iv_skew = p_iv - c_iv

    if dry_run:
        print(f"  [{symbol}] spot={spot:.2f}  expiry={near_expiry}"
              f"  PCR={pcr:.3f}  MaxPain={max_pain_s:.2f}  ATM={atm:.2f}"
              f"  rows={len(rows)}")
        return True

    # determine session from datetime
    hour = datetime.now().hour
    session = 'morning' if hour < 12 else 'EOD'

    # Add session to rows
    for r in rows:
        r['session'] = session

    saved = save_chain_rows(conn, rows)
    save_pcr_summary(conn, symbol, trade_date, near_expiry,
                     ce_oi, pe_oi, pcr, max_pain_s, atm, spot, local_pcr, iv_skew, atm_vol_oi_ratio, session)
    print(f"  [{symbol}] OK  spot={spot:.2f}  expiry={near_expiry}"
          f"  PCR={pcr:.3f}  MaxPain={max_pain_s:.2f}"
          f"  {saved} rows saved")
    return True


def main():
    parser = argparse.ArgumentParser(description="NSE Option Chain OI Scraper")
    parser.add_argument("--symbol", help="Single symbol to scrape (e.g. NIFTY50)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and compute but do not save to DB")
    parser.add_argument("--date", help="Override trade date (YYYY-MM-DD), default=today")
    args = parser.parse_args()

    trade_date = args.date or date.today().strftime("%Y-%m-%d")
    print(f"\n{'='*60}")
    print(f"  NSE OI Scraper  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Trade Date      : {trade_date}")
    print(f"  Dry Run         : {args.dry_run}")
    print(f"{'='*60}\n")

    # DB setup
    conn = sqlite3.connect(DB_PATH)
    ensure_db_tables(conn)

    # Warm NSE session
    sess = _new_session()
    time.sleep(1)

    success = 0
    failed  = 0

    if args.symbol:
        # Single symbol
        sym_upper = args.symbol.upper()
        # Normalise NSE index names (NSE uses e.g. "NIFTY" not "NIFTY50")
        index_lookup = {
            "NIFTY50":     "NIFTY",
            "BANKNIFTY":   "BANKNIFTY",
            "FINNIFTY":    "FINNIFTY",
            "MIDCPNIFTY":  "MIDCPNIFTY",
        }
        nse_sym  = index_lookup.get(sym_upper, sym_upper)
        is_index = nse_sym in NSE_INDEX_SYMBOLS
        print(f"[SINGLE] {sym_upper} -> NSE sym={nse_sym}  is_index={is_index}")
        ok = scrape_symbol(sess, conn, nse_sym, is_index, trade_date, args.dry_run)
        if ok:
            success += 1
        else:
            failed += 1
    else:
        # All indices
        print("[INDICES]")
        for sym in NSE_INDEX_SYMBOLS:
            ok = scrape_symbol(sess, conn, sym, is_index=True,
                               trade_date=trade_date, dry_run=args.dry_run)
            if ok:
                success += 1
            else:
                failed += 1
            time.sleep(1.0)   # polite delay between NSE requests

        # Dynamic Fetching: Query for all FUTSTK / F&O stocks
        print("\n[STOCKS]")
        stock_symbols = []
        try:
            from data.instruments import ALL_INSTRUMENTS
            for sym, inst in ALL_INSTRUMENTS.items():
                if getattr(inst, "instrument_type", "EQUITY") == "EQUITY" and sym not in NSE_INDEX_SYMBOLS:
                    clean_sym = sym.replace(".NS", "")
                    if clean_sym not in stock_symbols:
                        stock_symbols.append(clean_sym)
        except Exception:
            pass

        if not stock_symbols:
            query = "SELECT DISTINCT symbol FROM option_chain_data WHERE symbol NOT IN (?, ?, ?, ?)"
            stock_rows = conn.execute(query, tuple(NSE_INDEX_SYMBOLS)).fetchall()
            stock_symbols = [r[0] for r in stock_rows]

        for sym in stock_symbols:
            ok = scrape_symbol(sess, conn, sym, is_index=False,
                               trade_date=trade_date, dry_run=args.dry_run)
            if ok:
                success += 1
            else:
                failed += 1
            time.sleep(1.2)

    conn.close()
    print(f"\n{'='*60}")
    print(f"  Done: {success} OK  |  {failed} failed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
