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

NSE_STOCK_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "SBIN", "BHARTIARTL", "HINDUNILVR", "ITC", "LT",
    "AXISBANK", "KOTAKBANK", "BAJFINANCE", "WIPRO", "HCLTECH",
    "ADANIENT", "ADANIPORTS", "MARUTI", "TITAN", "SUNPHARMA",
    "TATASTEEL", "HINDALCO", "ULTRACEMCO", "ASIANPAINT", "BAJAJFINSV",
    "ONGC", "POWERGRID", "NTPC", "COALINDIA", "JSWSTEEL",
    "TATAMOTORS", "M&M", "CIPLA", "DRREDDY", "EICHERMOT",
    "BPCL", "APOLLOHOSP", "GRASIM", "TECHM", "DIVISLAB",
    "HEROMOTOCO", "TATACONSUM", "BRITANNIA", "NESTLEIND", "SHRIRAMFIN",
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
            fetched_at      TEXT    DEFAULT (datetime('now','localtime')),
            UNIQUE(symbol, trade_date, expiry_date, strike, option_type)
        );

        CREATE INDEX IF NOT EXISTS idx_oc_sym_date
            ON option_chain_data(symbol, trade_date);

        CREATE INDEX IF NOT EXISTS idx_oc_expiry
            ON option_chain_data(symbol, expiry_date, trade_date);

        CREATE TABLE IF NOT EXISTS pcr_summary (
            symbol          TEXT    NOT NULL,
            trade_date      TEXT    NOT NULL,
            expiry_date     TEXT    NOT NULL,
            total_ce_oi     INTEGER,
            total_pe_oi     INTEGER,
            pcr             REAL,
            max_pain        REAL,
            atm_strike      REAL,
            spot_price      REAL,
            fetched_at      TEXT    DEFAULT (datetime('now','localtime')),
            PRIMARY KEY (symbol, trade_date, expiry_date)
        );

        CREATE INDEX IF NOT EXISTS idx_pcr_sym
            ON pcr_summary(symbol, trade_date DESC);
    """)
    conn.commit()
    print("[DB] Tables ready: option_chain_data, pcr_summary")


# ═══════════════════════════════════════════════════════════════════════════════
# NSE SESSION + FETCH
# ═══════════════════════════════════════════════════════════════════════════════

def _new_session() -> requests.Session:
    """
    Create a warmed-up NSE session (sets cookies).
    NSE blocks direct API calls without first visiting the site pages.
    We hit 3 pages with short delays to establish a valid cookie jar.
    """
    sess = requests.Session()
    sess.headers.update(HEADERS)
    warmed = False
    for url in COOKIE_WARM_URLS:
        try:
            resp = sess.get(url, timeout=12)
            if resp.status_code < 400:
                warmed = True
                print(f"[NSE] Warm-up OK: {url}")
            else:
                print(f"[WARN] Warm-up {url} -> HTTP {resp.status_code}")
        except Exception as e:
            print(f"[WARN] Warm-up {url} failed: {e}")
        time.sleep(1.5)
    if not warmed:
        print("[WARN] All warm-up URLs failed — NSE may block headless requests. "
              "Try running during market hours (09:15-15:30 IST).")
    return sess


def fetch_option_chain(sess: requests.Session, symbol: str,
                       is_index: bool = True) -> Optional[dict]:
    """
    Fetch raw option chain JSON from NSE.
    Returns parsed dict or None on failure.
    """
    url = (OC_INDEX_URL if is_index else OC_EQUITY_URL).format(symbol=symbol)
    for attempt in range(3):
        try:
            resp = sess.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if "records" in data:
                return data
            print(f"[WARN] {symbol}: unexpected response format")
            return None
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 401:
                # Re-warm session and retry
                print(f"[NSE] 401 on {symbol} — re-warming session")
                sess.get(COOKIE_WARM_URL, timeout=10)
            else:
                print(f"[WARN] {symbol} HTTP {resp.status_code}: {e}")
        except Exception as e:
            print(f"[WARN] {symbol} fetch error (attempt {attempt+1}): {e}")
        time.sleep(1.5)
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
             oi, change_in_oi, volume, iv, ltp, bid, ask)
        VALUES
            (:symbol, :trade_date, :expiry_date, :strike, :option_type,
             :oi, :change_in_oi, :volume, :iv, :ltp, :bid, :ask)
        ON CONFLICT(symbol, trade_date, expiry_date, strike, option_type)
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
                     max_pain: float, atm: float, spot: float) -> None:
    """Upsert PCR summary row."""
    conn.execute("""
        INSERT INTO pcr_summary
            (symbol, trade_date, expiry_date, total_ce_oi, total_pe_oi,
             pcr, max_pain, atm_strike, spot_price)
        VALUES (?,?,?,?,?,?,?,?,?)
        ON CONFLICT(symbol, trade_date, expiry_date)
        DO UPDATE SET
            total_ce_oi = excluded.total_ce_oi,
            total_pe_oi = excluded.total_pe_oi,
            pcr         = excluded.pcr,
            max_pain    = excluded.max_pain,
            atm_strike  = excluded.atm_strike,
            spot_price  = excluded.spot_price,
            fetched_at  = datetime('now','localtime')
    """, (symbol, trade_date, expiry, ce_oi, pe_oi, pcr,
          max_pain, atm, spot))
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

    if dry_run:
        print(f"  [{symbol}] spot={spot:.2f}  expiry={near_expiry}"
              f"  PCR={pcr:.3f}  MaxPain={max_pain_s:.2f}  ATM={atm:.2f}"
              f"  rows={len(rows)}")
        return True

    saved = save_chain_rows(conn, rows)
    save_pcr_summary(conn, symbol, trade_date, near_expiry,
                     ce_oi, pe_oi, pcr, max_pain_s, atm, spot)
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

        # All stocks
        print("\n[STOCKS]")
        for sym in NSE_STOCK_SYMBOLS:
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
