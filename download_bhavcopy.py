"""
download_bhavcopy.py — NSE F&O Bhavcopy Bulk Downloader + Daily Updater
=======================================================================
Downloads 20 years of NSE F&O bhavcopy data (2004 → today) via the
official NSE Reports API and nsearchives CDN.

Modes:
  python download_bhavcopy.py                # bulk: all missing dates
  python download_bhavcopy.py --year 2022    # single year backfill
  python download_bhavcopy.py --incremental  # yesterday only (daily cron)
  python download_bhavcopy.py --dry-run      # no DB writes, print only
  python download_bhavcopy.py --reset        # wipe OI tables and restart

NSE Bypass Strategy (confirmed working via testing):
  1. Warm session on market-data page (sets cookies)
  2. Use NSE Reports API (JSON-triggered ZIP download) — works 2004→2024
  3. Fall back to nsearchives CDN for recent dates (2023-12+)
  4. Polite delays (1-2s) + 3-attempt retry with re-warm on 401/403
  5. Progress saved to bhavcopy_progress.json — safe to interrupt/resume

Data stored in:
  option_chain_data  — per strike, per expiry OI rows
  pcr_summary        — daily PCR + max pain per symbol + expiry
"""

import os
import sys
import io
import json
import time
import random
import zipfile
import argparse
import sqlite3
import logging
from datetime import date, datetime, timedelta
from typing import Optional, Tuple, List

import requests
import pandas as pd

# ─── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DB_PATH       = os.path.join(BASE_DIR, "market_data_v2.db")
PROGRESS_FILE = os.path.join(BASE_DIR, "bhavcopy_progress.json")
LOG_FILE      = os.path.join(BASE_DIR, "bhavcopy_download.log")

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("bhavcopy")

# ─── NSE Session Config ────────────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

WARM_UP_PAGES = [
    "https://www.nseindia.com/market-data/equity-derivatives-watch",
    "https://www.nseindia.com/",
]

# Reports API — works for ALL years 2004→2024 (confirmed via testing)
REPORTS_API = (
    "https://www.nseindia.com/api/reports"
    "?archives=%5B%7B%22name%22%3A%22F%26O%20-%20Bhavcopy(csv)%22"
    "%2C%22type%22%3A%22archives%22%2C%22category%22%3A%22derivatives%22"
    "%2C%22section%22%3A%22equity%22%7D%5D"
    "&date={date}&type=equity&mode=single"
)

# NSE Archives CDN — works for recent dates (2023-12 onwards)
CDN_URL = (
    "https://nsearchives.nseindia.com/content/fo/"
    "BhavCopy_NSE_FO_0_0_0_{yyyymmdd}_F_0000.csv"
)

# ─── Instrument filter: which F&O instruments to keep ─────────────────────────
# FUTIDX = index futures, FUTSTK = stock futures
# OPTIDX = index options (CE/PE), OPTSTK = stock options (CE/PE)
KEEP_INSTRUMENTS = {"FUTIDX", "FUTSTK", "OPTIDX", "OPTSTK"}

# Only store these symbols (indices + top 50 stocks) to keep DB lean
# Leave empty set to store ALL symbols (uses more disk space)
SYMBOL_FILTER: set = set()   # set() = store all; populate to restrict


# ═══════════════════════════════════════════════════════════════════════════════
# DB SETUP
# ═══════════════════════════════════════════════════════════════════════════════

def ensure_tables(conn: sqlite3.Connection) -> None:
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

        CREATE TABLE IF NOT EXISTS bhavcopy_log (
            trade_date  TEXT PRIMARY KEY,
            status      TEXT,      -- 'ok' | 'skip' | 'fail'
            rows_saved  INTEGER    DEFAULT 0,
            source      TEXT,      -- 'reports_api' | 'cdn' | 'cache'
            fetched_at  TEXT       DEFAULT (datetime('now','localtime'))
        );
    """)
    conn.commit()


def get_already_fetched(conn: sqlite3.Connection) -> set:
    """Return set of trade_date strings already successfully fetched."""
    rows = conn.execute(
        "SELECT trade_date FROM bhavcopy_log WHERE status='ok'"
    ).fetchall()
    return {r[0] for r in rows}


# ═══════════════════════════════════════════════════════════════════════════════
# NSE SESSION
# ═══════════════════════════════════════════════════════════════════════════════

def new_session() -> requests.Session:
    """Create a properly warmed NSE session."""
    sess = requests.Session()
    ua = random.choice(USER_AGENTS)
    sess.headers.update({
        "User-Agent":         ua,
        "Accept":             "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language":    "en-US,en;q=0.9",
        "Accept-Encoding":    "gzip, deflate, br",
        "Referer":            "https://www.nseindia.com/",
        "Connection":         "keep-alive",
        "DNT":                "1",
    })
    warmed = False
    for page in WARM_UP_PAGES:
        try:
            r = sess.get(page, timeout=12)
            if r.status_code < 400:
                log.info(f"  Warm-up OK [{r.status_code}]: {page}")
                warmed = True
                break
        except Exception as e:
            log.warning(f"  Warm-up failed: {page} — {e}")
        time.sleep(1)
    if not warmed:
        log.warning("  All warm-up URLs failed — proceeding anyway")
    time.sleep(1.5)
    return sess


def rewarm(sess: requests.Session) -> None:
    """Re-warm an existing session (called after 401/403/503)."""
    for page in WARM_UP_PAGES:
        try:
            r = sess.get(page, timeout=10)
            if r.status_code < 400:
                log.info(f"  Re-warm OK: {page}")
                time.sleep(1)
                return
        except Exception:
            pass
    time.sleep(2)


# ═══════════════════════════════════════════════════════════════════════════════
# FETCH BHAVCOPY
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_reports_api(sess: requests.Session, date_str: str) -> Optional[bytes]:
    """
    Fetch bhavcopy ZIP via NSE Reports API.
    date_str: DD-MM-YYYY format
    Returns raw ZIP bytes or None.
    """
    url = REPORTS_API.format(date=date_str)
    for attempt in range(3):
        try:
            r = sess.get(url, timeout=25)
            if r.status_code == 200 and b"PK" in r.content[:4]:
                return r.content
            if r.status_code in (401, 403, 503):
                log.warning(f"    [{date_str}] {r.status_code} — re-warming")
                rewarm(sess)
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code == 404:
                return None
            log.warning(f"    [{date_str}] Reports API HTTP {r.status_code}")
            return None
        except requests.exceptions.Timeout:
            log.warning(f"    [{date_str}] timeout (attempt {attempt+1})")
            time.sleep(3)
        except Exception as e:
            log.warning(f"    [{date_str}] error: {e}")
            time.sleep(2)
    return None


def _fetch_cdn(sess: requests.Session, trade_date: date) -> Optional[Tuple[bytes, bool]]:
    """
    Fetch bhavcopy from nsearchives CDN.
    Checks both .csv.zip and .csv formats.
    Returns (bytes, is_zip) or None.
    """
    yyyymmdd = trade_date.strftime("%Y%m%d")
    
    # Try .csv.zip first (used for newer dates)
    url_zip = f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{yyyymmdd}_F_0000.csv.zip"
    try:
        r = sess.get(url_zip, timeout=15)
        if r.status_code == 200 and b"PK" in r.content[:4]:
            return r.content, True
    except Exception:
        pass

    # Try raw .csv fallback
    url_raw = f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{yyyymmdd}_F_0000.csv"
    try:
        r = sess.get(url_raw, timeout=15)
        if r.status_code == 200 and b"DOCTYPE" not in r.content[:20]:
            return r.content, False
    except Exception:
        pass

    return None


def fetch_bhavcopy(sess: requests.Session,
                   trade_date: date) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Fetch and parse bhavcopy for a single date.
    Returns (DataFrame, source_label) or (None, "fail/skip").
    """
    date_str_iso = trade_date.strftime("%Y-%m-%d")

    # ── Strategy 1: nsearchives CDN (For dates Dec 2023 to today) ──────────────────
    if trade_date >= date(2023, 12, 1):
        res = _fetch_cdn(sess, trade_date)
        if res:
            raw_bytes, is_zip = res
            try:
                if is_zip:
                    z = zipfile.ZipFile(io.BytesIO(raw_bytes))
                    csv_name = next((n for n in z.namelist() if n.endswith(".csv")), None)
                    if csv_name:
                        df = pd.read_csv(io.BytesIO(z.read(csv_name)), low_memory=False)
                        return df, "cdn"
                else:
                    df = pd.read_csv(io.BytesIO(raw_bytes), low_memory=False)
                    return df, "cdn"
            except Exception as e:
                log.warning(f"    [{date_str_iso}] CDN parse error: {e}")

    # ── Strategy 2: Reports API (For older dates, using correct DD-MMM-YYYY) ──────
    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    month_str = months[trade_date.month - 1]
    date_str_api = f"{trade_date.day:02d}-{month_str}-{trade_date.year}"

    raw_zip = _fetch_reports_api(sess, date_str_api)
    if raw_zip:
        try:
            z = zipfile.ZipFile(io.BytesIO(raw_zip))
            csv_name = next((n for n in z.namelist() if n.endswith(".csv")), None)
            if csv_name:
                df = pd.read_csv(io.BytesIO(z.read(csv_name)), low_memory=False)
                return df, "reports_api"
        except Exception as e:
            log.warning(f"    [{date_str_iso}] Reports API parse error: {e}")

    # CDN Fallback as last resort for older dates if Reports API failed
    if trade_date < date(2023, 12, 1):
        res = _fetch_cdn(sess, trade_date)
        if res:
            raw_bytes, is_zip = res
            try:
                if is_zip:
                    z = zipfile.ZipFile(io.BytesIO(raw_bytes))
                    csv_name = next((n for n in z.namelist() if n.endswith(".csv")), None)
                    if csv_name:
                        df = pd.read_csv(io.BytesIO(z.read(csv_name)), low_memory=False)
                        return df, "cdn"
                else:
                    df = pd.read_csv(io.BytesIO(raw_bytes), low_memory=False)
                    return df, "cdn"
            except Exception:
                pass

    return None, "fail"


# ═══════════════════════════════════════════════════════════════════════════════
# NORMALISE + FILTER DATAFRAME
# ═══════════════════════════════════════════════════════════════════════════════

def normalise(df: pd.DataFrame, trade_date: date) -> pd.DataFrame:
    """
    Normalise all 3 NSE bhavcopy column format variants into a common schema:
      - Old format  (2004-2008): OPTIONTYPE, OPEN_INT, SYMBOL, EXPIRY_DT, STRIKE_PR
      - Std format  (2009-2024): OPTION_TYP, OPEN_INT, same rest
      - CDN format  (2023+):     OpnIntrst,  TckrSym,  XpryDt, StrkPric, OptTp, FinInstrmTp
    """
    df = df.copy()
    df.columns = [c.strip().upper() for c in df.columns]

    # ── Detect and unify CDN new format ──────────────────────────────────────
    is_cdn = "TCKRSYM" in df.columns or "OPNINTRST" in df.columns or "TCKRSYMB" in df.columns
    if is_cdn:
        cdn_map = {
            "TCKRSYM":     "SYMBOL",
            "TCKRSYMB":    "SYMBOL",
            "XPRYDT":      "EXPIRY_DT",
            "STRKPRIC":    "STRIKE_PR",
            "OPTTP":       "OPTIONTYPE",
            "OPTNTP":      "OPTIONTYPE",
            "OPNINTRST":   "OPEN_INT",
            "CHNGINNOPNPS":"CHG_IN_OI",
            "CHNGINOPNINTRST": "CHG_IN_OI",
            "TTLTRADGVOL": "CONTRACTS",
            "CLSPRIC":     "ltp",
            "LASTPRIC":    "last_price",
            "STTLMPRIC":   "settle_price",
            "FININSTRMNTP":"INSTRUMENT",
            "FININSTRMTP": "INSTRUMENT",
        }
        df = df.rename(columns={k: v for k, v in cdn_map.items() if k in df.columns})
        # CDN format instrument filter
        if "INSTRUMENT" in df.columns:
            df = df[df["INSTRUMENT"].str.upper().isin({"STO", "STF", "IDO", "IDF",
                                                        "OI", "IO", "OPTIDX", "OPTSTK",
                                                        "FUTIDX", "FUTSTK"})].copy()
        # CDN option type values: CE/PE already present
    else:
        # Unify OPTION_TYP → OPTIONTYPE for standard format
        if "OPTION_TYP" in df.columns:
            df = df.rename(columns={"OPTION_TYP": "OPTIONTYPE"})
        # Keep only F&O instruments (old/std format)
        if "INSTRUMENT" in df.columns:
            df = df[df["INSTRUMENT"].isin(KEEP_INSTRUMENTS)].copy()

    # Symbol filter (optional)
    if SYMBOL_FILTER and "SYMBOL" in df.columns:
        df = df[df["SYMBOL"].isin(SYMBOL_FILTER)].copy()

    # ── Standardise column names ──────────────────────────────────────────────
    col_map = {
        "SYMBOL":    "symbol",
        "EXPIRY_DT": "expiry_date",
        "STRIKE_PR": "strike",
        "OPTIONTYPE":"option_type",
        "OPEN_INT":  "oi",
        "CHG_IN_OI": "change_in_oi",
        "CONTRACTS": "volume",
        "CLOSE":     "ltp",
        "INSTRUMENT":"instrument",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # Check if this is a valid F&O bhavcopy or an error page
    if "symbol" not in df.columns:
        raise ValueError("Invalid bhavcopy file: 'symbol' column not found. The download might be a corrupt file or HTML error page.")

    # Ensure critical columns exist with defaults
    for col, default in [("oi", 0), ("change_in_oi", 0), ("volume", 0),
                          ("ltp", 0.0), ("strike", 0.0)]:
        if col not in df.columns:
            df[col] = default

    # Add trade_date
    td_str = trade_date.strftime("%Y-%m-%d")
    df["trade_date"] = td_str

    # Convert expiry_date to YYYY-MM-DD
    if "expiry_date" in df.columns:
        df["expiry_date"] = pd.to_datetime(
            df["expiry_date"], dayfirst=True, errors="coerce"
        ).dt.strftime("%Y-%m-%d")

    # Coerce numeric
    for col in ("strike", "oi", "change_in_oi", "volume", "ltp"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Normalise option_type — ensure CE/PE/XX strings
    if "option_type" not in df.columns:
        df["option_type"] = "XX"
    df["option_type"] = df["option_type"].astype(str).str.strip().str.upper()

    return df


# ═══════════════════════════════════════════════════════════════════════════════
# COMPUTE PCR + MAX PAIN
# ═══════════════════════════════════════════════════════════════════════════════

def compute_pcr_maxpain(df: pd.DataFrame, symbol: str,
                        trade_date: str, expiry: str):
    """Compute PCR and max-pain for a symbol+expiry from option rows."""
    sub = df[
        (df["symbol"] == symbol) &
        (df["expiry_date"] == expiry) &
        (df["option_type"].isin(["CE", "PE"]))
    ].copy()
    if sub.empty:
        return None

    ce = sub[sub["option_type"] == "CE"]
    pe = sub[sub["option_type"] == "PE"]
    ce_oi = int(ce["oi"].sum())
    pe_oi = int(pe["oi"].sum())
    pcr   = round(pe_oi / ce_oi, 4) if ce_oi > 0 else 0.0

    # Max pain
    strikes = sorted(sub["strike"].unique())
    ce_map  = dict(zip(ce["strike"], ce["oi"].fillna(0)))
    pe_map  = dict(zip(pe["strike"], pe["oi"].fillna(0)))

    min_pain = float("inf")
    max_pain = strikes[0] if strikes else 0
    for s in strikes:
        pain = sum(max(0, s - k) * ce_map.get(k, 0) for k in strikes) + \
               sum(max(0, k - s) * pe_map.get(k, 0) for k in strikes)
        if pain < min_pain:
            min_pain = pain
            max_pain = s

    return {
        "symbol":      symbol,
        "trade_date":  trade_date,
        "expiry_date": expiry,
        "total_ce_oi": ce_oi,
        "total_pe_oi": pe_oi,
        "pcr":         pcr,
        "max_pain":    max_pain,
        "atm_strike":  0.0,   # no spot price in bhavcopy
        "spot_price":  0.0,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SAVE TO DB
# ═══════════════════════════════════════════════════════════════════════════════

def save_to_db(conn: sqlite3.Connection, df: pd.DataFrame,
               trade_date: str, source: str, dry_run: bool = False) -> int:
    """
    Save normalised bhavcopy DataFrame to option_chain_data + pcr_summary.
    Returns count of option chain rows saved.
    """
    # ── Option/Futures chain rows (all F&O open interest) ───────────────────
    opt_df = df[df["option_type"].isin(["CE", "PE", "XX"])].copy()
    required = ["symbol", "trade_date", "expiry_date", "strike", "option_type", "oi"]
    opt_df = opt_df.dropna(subset=required)

    if dry_run:
        log.info(f"    DRY RUN: would save {len(opt_df)} option rows")
        return len(opt_df)

    rows_saved = 0
    if not opt_df.empty:
        records = []
        for _, r in opt_df.iterrows():
            records.append((
                str(r["symbol"]), str(r["trade_date"]), str(r["expiry_date"]),
                float(r.get("strike", 0)), str(r["option_type"]),
                int(r.get("oi", 0)), int(r.get("change_in_oi", 0)),
                int(r.get("volume", 0)), None, float(r.get("ltp", 0)),
                None, None,
            ))

        conn.executemany("""
            INSERT INTO option_chain_data
                (symbol, trade_date, expiry_date, strike, option_type,
                 oi, change_in_oi, volume, iv, ltp, bid, ask)
            VALUES (?,?,?,?,?, ?,?,?,?,?, ?,?)
            ON CONFLICT(symbol, trade_date, expiry_date, strike, option_type)
            DO UPDATE SET
                oi           = excluded.oi,
                change_in_oi = excluded.change_in_oi,
                volume       = excluded.volume,
                ltp          = excluded.ltp,
                fetched_at   = datetime('now','localtime')
        """, records)
        rows_saved = len(records)

    # ── PCR + max pain per symbol × nearest expiry ───────────────────────────
    for symbol in opt_df["symbol"].unique():
        expiries = sorted(opt_df[opt_df["symbol"] == symbol]["expiry_date"].unique())
        near_exp = expiries[0] if expiries else None
        if not near_exp:
            continue
        pcr_row = compute_pcr_maxpain(opt_df, symbol, trade_date, near_exp)
        if pcr_row:
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
                    fetched_at  = datetime('now','localtime')
            """, (
                pcr_row["symbol"], pcr_row["trade_date"], pcr_row["expiry_date"],
                pcr_row["total_ce_oi"], pcr_row["total_pe_oi"], pcr_row["pcr"],
                pcr_row["max_pain"], pcr_row["atm_strike"], pcr_row["spot_price"],
            ))

    conn.commit()
    return rows_saved


def log_result(conn: sqlite3.Connection, trade_date: str,
               status: str, rows: int, source: str, dry_run: bool) -> None:
    if dry_run:
        return
    conn.execute("""
        INSERT INTO bhavcopy_log (trade_date, status, rows_saved, source)
        VALUES (?,?,?,?)
        ON CONFLICT(trade_date) DO UPDATE SET
            status=excluded.status, rows_saved=excluded.rows_saved,
            source=excluded.source, fetched_at=datetime('now','localtime')
    """, (trade_date, status, rows, source))
    conn.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# DATE RANGE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def trading_days_in_range(start: date, end: date) -> List[date]:
    """Return all weekdays between start and end (inclusive)."""
    days = []
    cur = start
    while cur <= end:
        if cur.weekday() < 5:   # Mon-Fri
            days.append(cur)
        cur += timedelta(days=1)
    return days


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="NSE F&O Bhavcopy Bulk Downloader (2004 → today)"
    )
    parser.add_argument("--year",        type=int, help="Download a specific year only")
    parser.add_argument("--from-date",   help="Start date YYYY-MM-DD (default: 2004-01-01)")
    parser.add_argument("--to-date",     help="End date   YYYY-MM-DD (default: yesterday)")
    parser.add_argument("--incremental", action="store_true",
                        help="Download yesterday only (for daily cron)")
    parser.add_argument("--dry-run",     action="store_true",
                        help="Fetch data but do not write to DB")
    parser.add_argument("--reset",       action="store_true",
                        help="Drop and recreate OI tables before starting")
    parser.add_argument("--workers",     type=int, default=1,
                        help="Parallel download workers (default 1, NSE is strict)")
    args = parser.parse_args()

    # ── Date range ────────────────────────────────────────────────────────────
    yesterday = date.today() - timedelta(days=1)

    if args.incremental:
        # Smart lookback: find the latest successfully downloaded date in bhavcopy_log
        # and start from the day after it to fill in any missed days when offline.
        conn_temp = sqlite3.connect(DB_PATH)
        try:
            row = conn_temp.execute(
                "SELECT MAX(trade_date) FROM bhavcopy_log WHERE status='ok'"
            ).fetchone()
            if row and row[0]:
                last_success = date.fromisoformat(row[0])
                start_date = last_success + timedelta(days=1)
            else:
                # Fallback to 15 days ago if table is empty
                start_date = yesterday - timedelta(days=15)
        except Exception:
            start_date = yesterday
        finally:
            conn_temp.close()
            
        end_date = yesterday
        if start_date > yesterday:
            start_date = yesterday
    elif args.year:
        start_date = date(args.year, 1, 1)
        end_date   = date(args.year, 12, 31)
        if end_date > yesterday:
            end_date = yesterday
    else:
        start_date = date(2004, 1, 1) if not args.from_date else date.fromisoformat(args.from_date)
        end_date   = yesterday        if not args.to_date   else date.fromisoformat(args.to_date)

    log.info("=" * 65)
    log.info(f"  NSE Bhavcopy Downloader  |  {datetime.now():%Y-%m-%d %H:%M:%S}")
    log.info(f"  Range : {start_date} -> {end_date}")
    log.info(f"  Dry   : {args.dry_run}")
    log.info("=" * 65)

    # ── DB setup ─────────────────────────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)

    if args.reset and not args.dry_run:
        log.info("  RESET: dropping option_chain_data + pcr_summary + bhavcopy_log")
        conn.executescript("""
            DROP TABLE IF EXISTS option_chain_data;
            DROP TABLE IF EXISTS pcr_summary;
            DROP TABLE IF EXISTS bhavcopy_log;
        """)

    ensure_tables(conn)

    already_done = get_already_fetched(conn)
    log.info(f"  Already fetched: {len(already_done)} dates")

    # ── Build work list ───────────────────────────────────────────────────────
    all_days  = trading_days_in_range(start_date, end_date)
    work_days = [d for d in all_days if d.strftime("%Y-%m-%d") not in already_done]
    log.info(f"  To fetch : {len(work_days)} dates  |  Skipping {len(all_days)-len(work_days)} already done")
    log.info("")

    # ── Session ───────────────────────────────────────────────────────────────
    sess = new_session()

    # ── Download loop ─────────────────────────────────────────────────────────
    ok_count   = 0
    skip_count = 0
    fail_count = 0
    rewarm_every = 50   # re-warm NSE session every N requests

    for idx, trade_date in enumerate(work_days, 1):
        td_str = trade_date.strftime("%Y-%m-%d")

        # Periodic re-warm to keep session alive
        if idx > 1 and (idx - 1) % rewarm_every == 0:
            log.info(f"  [{idx}/{len(work_days)}] Refreshing NSE session...")
            rewarm(sess)

        # Progress log every 10 dates
        if idx % 10 == 0 or idx == 1:
            pct = idx / len(work_days) * 100
            log.info(f"  [{idx}/{len(work_days)}  {pct:.0f}%]  OK={ok_count}  SKIP={skip_count}  FAIL={fail_count}")

        df, source = fetch_bhavcopy(sess, trade_date)

        if df is None:
            # Weekend/holiday or persistent failure — log as skip
            log_result(conn, td_str, "skip", 0, "none", args.dry_run)
            skip_count += 1
            time.sleep(0.5)
            continue

        try:
            norm_df = normalise(df, trade_date)
            rows    = save_to_db(conn, norm_df, td_str, source, args.dry_run)
            log_result(conn, td_str, "ok", rows, source, args.dry_run)
            ok_count += 1
            if idx % 5 == 0:  # show every 5th success
                log.info(f"    {td_str}  [{source}]  {rows} rows  OK")
        except Exception as e:
            import traceback
            log.error(f"    {td_str} SAVE ERROR: {e}\n{traceback.format_exc()}")
            log_result(conn, td_str, "fail", 0, source, args.dry_run)
            fail_count += 1

        # Polite delay — vary slightly to look less bot-like
        time.sleep(random.uniform(1.0, 2.0))

    conn.close()

    log.info("")
    log.info("=" * 65)
    log.info(f"  DONE   OK={ok_count}  SKIP={skip_count}  FAIL={fail_count}")
    log.info(f"  Log: {LOG_FILE}")
    log.info("=" * 65)

    # Print summary stats from DB
    if not args.dry_run and ok_count > 0:
        conn2 = sqlite3.connect(DB_PATH)
        total_rows = conn2.execute("SELECT COUNT(*) FROM option_chain_data").fetchone()[0]
        total_dates = conn2.execute("SELECT COUNT(DISTINCT trade_date) FROM option_chain_data").fetchone()[0]
        oldest = conn2.execute("SELECT MIN(trade_date) FROM option_chain_data").fetchone()[0]
        newest = conn2.execute("SELECT MAX(trade_date) FROM option_chain_data").fetchone()[0]
        conn2.close()
        log.info(f"  DB: {total_rows:,} option rows  |  {total_dates:,} trading days  |  {oldest} -> {newest}")


if __name__ == "__main__":
    main()
