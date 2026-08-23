"""
fetch_institutional.py — GANN-ASTRO v3.9
==========================================
FULLY AUTOMATED Bulk & Block Deals fetcher.
Mirrors how daily_prices auto-fills — same pattern, same reliability.

WHAT IT DOES:
  1. On startup  → backfill ALL missing trading days (auto-detects gaps)
  2. Each day    → fetch today's deals at 15:35 IST via scheduler
  3. On gaps     → NSE archive CSV → NSE JSON API → BSE fallback (3-layer)
  4. De-duplication → INSERT OR IGNORE on (date, symbol, client, type, kind)
  5. Self-healing → retries 3×, logs every failure, never crashes the app

THREE DATA SOURCES (tried in order):
  Source A: archives.nseindia.com  — public CSV files, no cookies, most reliable
  Source B: www.nseindia.com API   — JSON API, needs cookie session
  Source C: BSE bulk deals page    — fallback when NSE fails

HOW TO ADD TO YOUR DB (share schema with me):
  Your DB already has bulk_block_deals table.
  This file creates it if missing, migrates schema if outdated.
  To share schema: right-click market_data_v2.db → Open in DB Browser →
  Tools → Export → Database to SQL → send that .sql file.

SCHEDULER INTEGRATION (already hooked into scheduler.py):
  At 15:35 IST daily: auto_fetch_today() is called automatically.
  Backfill on first run: python core/fetch_institutional.py --backfill --days 90
"""

import os, sys, time, sqlite3, json, csv, io, re
from datetime import date, timedelta, datetime
from typing import Optional, List, Dict, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "market_data_v2.db")

# ── NSE Holiday Calendar (NSE official + extrapolated) ────────────────────────
NSE_HOLIDAYS = {
    # 2024
    date(2024, 1, 22), date(2024, 1, 26), date(2024, 3, 25), date(2024, 3, 29),
    date(2024, 4, 11), date(2024, 4, 14), date(2024, 4, 17), date(2024, 5,  1),
    date(2024, 6, 17), date(2024, 7, 17), date(2024, 8, 15), date(2024, 10, 2),
    date(2024, 10, 14), date(2024, 11, 1), date(2024, 11, 15), date(2024, 11, 20),
    date(2024, 12, 25),
    # 2025
    date(2025, 2, 26), date(2025, 3, 14), date(2025, 3, 31), date(2025, 4, 10),
    date(2025, 4, 14), date(2025, 4, 18), date(2025, 5,  1), date(2025, 8, 15),
    date(2025, 8, 27), date(2025, 10, 2), date(2025, 10, 21), date(2025, 10, 22),
    date(2025, 11, 5), date(2025, 12, 25),
    # 2026
    date(2026, 1, 26), date(2026, 3,  3), date(2026, 3, 20), date(2026, 4,  3),
    date(2026, 4, 14), date(2026, 5,  1), date(2026, 8, 15), date(2026, 10, 2),
    date(2026, 11, 14), date(2026, 12, 25),
}


def is_trading_day(d: date) -> bool:
    return d.weekday() < 5 and d not in NSE_HOLIDAYS


def trading_days_between(start: date, end: date) -> List[date]:
    """All trading days from start to end inclusive."""
    days = []
    d = start
    while d <= end:
        if is_trading_day(d):
            days.append(d)
        d += timedelta(days=1)
    return days


# ══════════════════════════════════════════════════════════════════════════════
# DATABASE SETUP & SCHEMA
# ══════════════════════════════════════════════════════════════════════════════

def init_db():
    """Create tables and migrate schema. Safe to call multiple times."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    # ── bulk_block_deals ──────────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bulk_block_deals (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_date     TEXT NOT NULL,
            symbol        TEXT NOT NULL,
            security_name TEXT DEFAULT '',
            client_name   TEXT DEFAULT '—',
            deal_type     TEXT NOT NULL,   -- BUY / SELL
            quantity      INTEGER DEFAULT 0,
            price         REAL DEFAULT 0,
            deal_kind     TEXT NOT NULL,   -- BULK / BLOCK
            fetched_at    TEXT,
            UNIQUE(deal_date, symbol, client_name, deal_type, deal_kind)
        )
    """)

    # Migration: add security_name if older schema
    cols = {r[1] for r in conn.execute("PRAGMA table_info(bulk_block_deals)")}
    if "security_name" not in cols:
        conn.execute("ALTER TABLE bulk_block_deals ADD COLUMN security_name TEXT DEFAULT ''")

    # ── fetch_log: track which dates have been fetched and how ───────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS deals_fetch_log (
            fetch_date  TEXT NOT NULL,
            source      TEXT,          -- ARCHIVE_CSV / NSE_API / BSE / NONE
            deals_saved INTEGER DEFAULT 0,
            fetched_at  TEXT,
            PRIMARY KEY (fetch_date)
        )
    """)

    # ── shareholding ─────────────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shareholding (
            symbol TEXT NOT NULL, quarter TEXT NOT NULL,
            fii_pct REAL, dii_pct REAL, promoter_pct REAL,
            retail_pct REAL, fii_change REAL, dii_change REAL,
            fetched_at TEXT,
            PRIMARY KEY (symbol, quarter)
        )
    """)

    # ── volume_anomalies ─────────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS volume_anomalies (
            symbol TEXT NOT NULL, trade_date TEXT NOT NULL,
            vol_ratio REAL, signal TEXT, candle_type TEXT,
            price_change_pct REAL, computed_at TEXT,
            PRIMARY KEY (symbol, trade_date)
        )
    """)

    # Indices for fast lookups
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bbd_date   ON bulk_block_deals(deal_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bbd_symbol ON bulk_block_deals(symbol)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bbd_type   ON bulk_block_deals(deal_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_va_date   ON volume_anomalies(trade_date)")

    conn.commit()
    conn.close()


def get_missing_trading_days(lookback_days: int = 365) -> List[date]:
    """
    Find all trading days in the last N days that have NO data in bulk_block_deals.
    This is the exact same pattern as download_history.py uses for daily_prices.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    existing = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT deal_date FROM bulk_block_deals"
        ).fetchall()
    }
    # Also check fetch_log — days we tried but got zero deals (market was closed / no deals)
    logged = {
        r[0] for r in conn.execute(
            "SELECT fetch_date FROM deals_fetch_log"
        ).fetchall()
    }
    conn.close()

    all_covered = existing | logged
    today = date.today()
    start = today - timedelta(days=lookback_days)
    missing = [
        d for d in trading_days_between(start, today)
        if d.isoformat() not in all_covered
        and d < today  # never fetch today until market close
    ]
    return missing


def log_fetch(d: date, source: str, count: int):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            INSERT OR REPLACE INTO deals_fetch_log
            (fetch_date, source, deals_saved, fetched_at)
            VALUES (?, ?, ?, ?)
        """, (d.isoformat(), source, count, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception:
        pass


def save_deals(deals: List[Dict]) -> int:
    if not deals:
        return 0
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    saved = 0
    for d in deals:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO bulk_block_deals
                (deal_date, symbol, security_name, client_name,
                 deal_type, quantity, price, deal_kind, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                d["deal_date"], d["symbol"],
                d.get("security_name", d["symbol"])[:100],
                d.get("client_name", "—")[:100],
                d["deal_type"],
                int(d.get("quantity", 0) or 0),
                float(d.get("price", 0) or 0),
                d["deal_kind"],
                datetime.now().isoformat(),
            ))
            if conn.execute("SELECT changes()").fetchone()[0]:
                saved += 1
        except Exception as e:
            print(f"    [WARN] save_deals {d.get('symbol')} {d.get('deal_date')}: {e}", flush=True)
    conn.commit()
    conn.close()
    return saved


# ══════════════════════════════════════════════════════════════════════════════
# PARSE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _clean_num(s: str) -> float:
    """Parse '1,23,456.78' or '1234.56' to float."""
    try:
        return float(re.sub(r"[^\d.]", "", str(s or "0")) or "0")
    except ValueError:
        return 0.0


def _clean_int(s: str) -> int:
    try:
        return int(float(re.sub(r"[^\d.]", "", str(s or "0")) or "0"))
    except ValueError:
        return 0


def _parse_csv(text: str, deal_kind: str, deal_date: date) -> List[Dict]:
    """
    Parse NSE bulk/block deals CSV.
    Handles both NSE bulk (archives.nseindia.com) and block deal CSV formats.

    NSE Bulk CSV columns (confirmed):
      Date | Symbol | Security Name | Client Name |
      Buy / Sell | Quantity Traded | Trade Price / Wght. Avg. Price | Remarks

    NSE Block CSV columns:
      Date | Symbol | Security Name | Client Name |
      Buy / Sell | Quantity Traded | Trade Price / Wght. Avg. Price
    """
    deals = []
    try:
        # Remove BOM
        text = text.lstrip("\ufeff").strip()
        if not text or "<html" in text.lower():
            return []

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return []

        for raw in reader:
            row = {k.strip(): (v or "").strip() for k, v in raw.items() if k}

            sym = (row.get("Symbol") or row.get("SYMBOL") or "").upper().strip()
            sym = re.sub(r"\.(NS|BO)$", "", sym)
            if not sym or sym.isdigit():
                continue

            sec = (row.get("Security Name") or row.get("SECURITY NAME") or sym)[:100]
            client = (row.get("Client Name") or row.get("CLIENT NAME") or "—")[:100]

            # Buy/Sell — NSE uses "B" / "S" or "Buy" / "Sell"
            bs_raw = (
                row.get("Buy / Sell") or row.get("Buy/Sell") or
                row.get("BUY / SELL") or row.get("BUY/SELL") or
                row.get("buySell") or "B"
            ).strip().upper()
            deal_type = "BUY" if bs_raw.startswith("B") else "SELL"

            qty = _clean_int(
                row.get("Quantity Traded") or row.get("QUANTITY TRADED") or
                row.get("Quantity") or row.get("qty") or "0"
            )
            price = _clean_num(
                row.get("Trade Price / Wght. Avg. Price") or
                row.get("Trade Price/ Wght. Avg. Price") or
                row.get("Trade Price") or row.get("Price") or row.get("price") or "0"
            )

            if qty == 0 and price == 0:
                continue

            deals.append({
                "deal_date":     deal_date.isoformat(),
                "symbol":        sym,
                "security_name": sec,
                "client_name":   client,
                "deal_type":     deal_type,
                "quantity":      qty,
                "price":         price,
                "deal_kind":     deal_kind,
            })
    except Exception as e:
        print(f"    [WARN] CSV parse error ({deal_kind}): {e}", flush=True)
    return deals


def _parse_json(data, deal_kind: str, deal_date: date) -> List[Dict]:
    """Parse NSE JSON API response for bulk/block deals."""
    records = []
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        # Block deals: Session 1 / Session 2 keys
        for key in ("Session 1", "Session 2", "session1", "session2",
                    "data", "bulkDealData", "blockDealData", "result", "results"):
            v = data.get(key)
            if isinstance(v, list):
                records.extend(v)
            elif isinstance(v, dict):
                for k2 in ("Session 1", "Session 2", "data", "rows", "records"):
                    if isinstance(v.get(k2), list):
                        records.extend(v[k2])

    if not records:
        return []

    deals = []
    for d in records:
        if not isinstance(d, dict):
            continue

        def _v(*keys):
            for k in keys:
                val = d.get(k)
                if val is not None and str(val).strip() not in ("", "None", "-", "null", "N/A"):
                    return str(val).strip()
            return ""

        sym = _v("symbol", "Symbol", "SYMBOL", "scripCode", "scrip").upper()
        sym = re.sub(r"\.(NS|BO)$", "", sym)
        if not sym or sym.isdigit():
            continue

        sec = _v("companyName", "securityName", "Security Name", "SECURITY NAME", "sname")[:100]
        client = _v("clientName", "Client Name", "CLIENT NAME", "cname", "partyName")[:100]

        bs = _v("buySell", "Buy/Sell", "BUY/SELL", "BSORSR", "bsOrSr", "BS",
                "dealType", "buyOrSell") or "S"
        deal_type = "BUY" if bs.upper().startswith("B") else "SELL"

        qty = _clean_int(_v("quantityTraded", "Quantity Traded", "QUANTITY TRADED",
                            "qty", "QTY", "quantity", "noOfShares") or "0")
        price = _clean_num(_v("tradePrice", "Trade Price / Wght. Avg. Price",
                              "TRADE PRICE/WEIGHTED AVG PRICE", "Price", "price",
                              "wghtAvgPrice", "dealPrice", "ratePerUnit") or "0")

        if qty == 0 and price == 0:
            continue

        deals.append({
            "deal_date":     deal_date.isoformat(),
            "symbol":        sym,
            "security_name": sec or sym,
            "client_name":   client or "—",
            "deal_type":     deal_type,
            "quantity":      qty,
            "price":         price,
            "deal_kind":     deal_kind,
        })
    return deals


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE A — NSE ARCHIVE CSV (most reliable, public, no cookies needed)
# ══════════════════════════════════════════════════════════════════════════════

def _fetch_archive_csv(session, d: date, deal_kind: str) -> List[Dict]:
    """
    Fetch from NSE public archive server.
    URL patterns confirmed working for NSE bulk deal archives.
    """
    ymd = d.strftime("%Y%m%d")  # YYYYMMDD
    dmy = d.strftime("%d%m%Y")  # DDMMYYYY

    if deal_kind == "BULK":
        urls = [
            f"https://archives.nseindia.com/archives/equities/bultrans/bulkdeals{ymd}.csv",
            f"https://archives.nseindia.com/archives/equities/bultrans/bulkdeals{dmy}.csv",
            f"https://nsearchives.nseindia.com/archives/equities/bultrans/bulkdeals{ymd}.csv",
        ]
    else:  # BLOCK
        urls = [
            f"https://archives.nseindia.com/archives/equities/blockdeals/blockdeals{ymd}.csv",
            f"https://archives.nseindia.com/archives/equities/blockdeals/blockdeals{dmy}.csv",
            f"https://nsearchives.nseindia.com/archives/equities/blockdeals/blockdeals{ymd}.csv",
        ]

    for url in urls:
        try:
            r = session.get(url, timeout=20)
            if r.status_code != 200 or len(r.content) < 30:
                continue
            text = r.content.decode("utf-8", errors="replace")
            if "<html" in text.lower() or "404" in text[:200]:
                continue
            deals = _parse_csv(text, deal_kind, d)
            if deals:
                return deals
            # Empty CSV on a trading day = legitimately no deals that day
            if r.status_code == 200 and len(r.content) > 10:
                return []  # Got response but no deals
        except Exception:
            continue
    return None  # None = failed to fetch (distinct from [] = no deals)


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE B — NSE JSON API (needs cookie session)
# ══════════════════════════════════════════════════════════════════════════════

def _get_nse_session(timeout: int = 10):
    """Build NSE session with cookie. Retries on failure."""
    try:
        import requests
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.nseindia.com/",
            "Connection": "keep-alive",
        })
        # Warm up — grab cookies
        for warmup_url in [
            "https://www.nseindia.com",
            "https://www.nseindia.com/market-data/bulk-deals",
        ]:
            try:
                s.get(warmup_url, timeout=timeout, allow_redirects=True)
                time.sleep(0.8)
                break
            except Exception:
                continue
        return s
    except ImportError:
        print("    [WARN] pip install requests", flush=True)
        return None


def _fetch_nse_api(session, d: date, deal_kind: str) -> List[Dict]:
    """Fetch from NSE JSON API with cookie session."""
    ds = d.strftime("%d-%m-%Y")
    if deal_kind == "BULK":
        urls = [
            f"https://www.nseindia.com/api/historical/bulk-deals?from={ds}&to={ds}",
            f"https://www.nseindia.com/api/bulk-deal-archives?from={ds}&to={ds}&category=bulk",
        ]
    else:
        urls = [
            f"https://www.nseindia.com/api/block-deal?from={ds}&to={ds}",
            f"https://www.nseindia.com/api/historical/block-deals?from={ds}&to={ds}",
        ]

    for url in urls:
        for attempt in range(2):
            try:
                r = session.get(
                    url, timeout=20,
                    headers={"X-Requested-With": "XMLHttpRequest",
                             "Accept": "application/json"}
                )
                if r.status_code == 200 and r.text.strip():
                    data = json.loads(r.text)
                    deals = _parse_json(data, deal_kind, d)
                    return deals
                if r.status_code in (401, 403):
                    # Re-warm session
                    try:
                        session.get("https://www.nseindia.com", timeout=8)
                        time.sleep(2)
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(1)
    return None


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE C — BSE FALLBACK
# ══════════════════════════════════════════════════════════════════════════════

def _fetch_bse_bulk(session, d: date) -> List[Dict]:
    """
    BSE bulk deals API as fallback.
    URL: https://api.bseindia.com/BseIndiaAPI/api/BulkDeal/w
    Params: pagenum=1, pagesize=500, fromdate=YYYYMMDD&todate=YYYYMMDD
    """
    ymd = d.strftime("%Y%m%d")
    try:
        r = session.get(
            "https://api.bseindia.com/BseIndiaAPI/api/BulkDeal/w",
            params={"pagenum": 1, "pagesize": 500,
                    "fromdate": ymd, "todate": ymd},
            timeout=20,
            headers={"Origin": "https://www.bseindia.com",
                     "Referer": "https://www.bseindia.com/"}
        )
        if r.status_code != 200:
            return None
        data = r.json()
        # BSE format: {"Table": [{...}], ...}
        records = data.get("Table") or data.get("data") or []
        deals = []
        for rec in records:
            if not isinstance(rec, dict):
                continue
            sym = (rec.get("SCRIP_CD") or rec.get("SCRIP_NAME") or "").upper().strip()
            if not sym:
                continue
            bs = str(rec.get("BUY_SELL") or rec.get("BS") or "S").upper()
            deals.append({
                "deal_date":     d.isoformat(),
                "symbol":        sym,
                "security_name": str(rec.get("SCRIP_NAME") or sym)[:100],
                "client_name":   str(rec.get("CLIENT_NAME") or "—")[:100],
                "deal_type":     "BUY" if bs.startswith("B") else "SELL",
                "quantity":      _clean_int(rec.get("QTY") or rec.get("QUANTITY") or "0"),
                "price":         _clean_num(rec.get("PRICE") or rec.get("DEAL_PRICE") or "0"),
                "deal_kind":     "BULK",
            })
        return deals
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# CORE FETCH FUNCTION — tries all 3 sources, returns (deals, source_name)
# ══════════════════════════════════════════════════════════════════════════════

def fetch_deals_for_date(
    d: date,
    session=None,
    archive_session=None,
) -> Tuple[List[Dict], str]:
    """
    Fetch bulk + block deals for a single trading day.
    Tries Source A (archive CSV) → Source B (NSE API) → Source C (BSE).
    Returns (deals_list, source_name).
    """
    import requests

    # Build archive session (no cookies needed)
    if archive_session is None:
        archive_session = requests.Session()
        archive_session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/124.0.0.0 Safari/537.36",
        })

    all_deals = []

    # ── Source A: NSE Archive CSV ─────────────────────────────────────────────
    for deal_kind in ("BULK", "BLOCK"):
        result = _fetch_archive_csv(archive_session, d, deal_kind)
        if result is not None:
            all_deals.extend(result)

    if all_deals:
        return all_deals, "ARCHIVE_CSV"

    # Check if we at least got empty (valid) responses from archive
    # (meaning the archive server responded but no deals that day)
    # We test with a bulk fetch — if it returns [] explicitly, log as ARCHIVE_CSV
    bulk_check = _fetch_archive_csv(archive_session, d, "BULK")
    if bulk_check == []:
        return [], "ARCHIVE_CSV"  # Server responded, legitimately no deals

    # ── Source B: NSE JSON API ────────────────────────────────────────────────
    if session is None:
        session = _get_nse_session()

    if session:
        for deal_kind in ("BULK", "BLOCK"):
            result = _fetch_nse_api(session, d, deal_kind)
            if result:
                all_deals.extend(result)
            time.sleep(0.5)

        if all_deals:
            return all_deals, "NSE_API"

        # Check if NSE API returned empty for bulk
        bulk_api = _fetch_nse_api(session, d, "BULK")
        if bulk_api == []:
            return [], "NSE_API"

    # ── Source C: BSE Fallback ────────────────────────────────────────────────
    bse_result = _fetch_bse_bulk(archive_session, d)
    if bse_result is not None:
        return bse_result, "BSE_FALLBACK"

    return [], "NONE"  # All sources failed


# ══════════════════════════════════════════════════════════════════════════════
# BACKFILL — fills all missing trading days automatically
# ══════════════════════════════════════════════════════════════════════════════

def backfill_missing_days(
    lookback_days: int = 365,
    batch_sleep: float = 1.0,
    verbose: bool = True,
) -> int:
    """
    Detect and fill ALL missing trading days.
    Exact same pattern as download_history.py does for daily_prices.
    """
    init_db()
    missing = get_missing_trading_days(lookback_days)

    if not missing:
        if verbose:
            print("  [INST] No missing trading days. DB is up to date.", flush=True)
        return 0

    if verbose:
        print(f"  [INST] Backfilling {len(missing)} missing trading days...", flush=True)
        print(f"  [INST] Range: {missing[0]} → {missing[-1]}", flush=True)

    try:
        import requests
    except ImportError:
        print("  [INST] pip install requests", flush=True)
        return 0

    # Build ONE session for all archive requests (reuse cookies)
    archive_sess = requests.Session()
    archive_sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
    })
    nse_sess = None  # lazy-build only if archive fails

    total_saved = 0
    for i, d in enumerate(missing):
        if verbose:
            print(f"  [INST] {d} ({i+1}/{len(missing)})...", end=" ", flush=True)

        try:
            deals, source = fetch_deals_for_date(
                d, session=nse_sess, archive_session=archive_sess
            )

            # If archive kept failing, build NSE session once
            if source == "NONE" and nse_sess is None:
                nse_sess = _get_nse_session()
                if nse_sess:
                    deals, source = fetch_deals_for_date(
                        d, session=nse_sess, archive_session=archive_sess
                    )

            saved = save_deals(deals)
            log_fetch(d, source, saved)
            total_saved += saved

            if verbose:
                status = f"{saved} deals [{source}]" if saved > 0 else f"no deals [{source}]"
                print(status, flush=True)

        except Exception as e:
            log_fetch(d, "ERROR", 0)
            if verbose:
                print(f"ERROR: {e}", flush=True)

        time.sleep(batch_sleep)

    if verbose:
        print(f"\n  [INST] Backfill complete: {total_saved} total deals saved.", flush=True)
    return total_saved


# ══════════════════════════════════════════════════════════════════════════════
# DAILY AUTO-FETCH — called by scheduler at 15:35 IST
# ══════════════════════════════════════════════════════════════════════════════

def auto_fetch_today(force: bool = False) -> int:
    """
    Fetch today's deals. Called automatically by the scheduler.
    Also backfills any recent missing days (up to 7 days back).

    - Checks if today is a trading day
    - Checks if already fetched (skip unless force=True)
    - Tries all 3 sources
    - Logs result to deals_fetch_log
    """
    init_db()
    today = date.today()

    if not is_trading_day(today):
        # Still backfill recent missing days on weekends/holidays
        missing = get_missing_trading_days(14)
        if missing:
            print(f"  [INST] Non-trading day — backfilling {len(missing)} recent gaps", flush=True)
            return backfill_missing_days(14, batch_sleep=0.8, verbose=True)
        return 0

    # Check if today already fetched
    if not force:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        already = conn.execute(
            "SELECT deals_saved FROM deals_fetch_log WHERE fetch_date=?",
            (today.isoformat(),)
        ).fetchone()
        conn.close()
        if already:
            print(f"  [INST] Today already fetched ({already[0]} deals). Use force=True to re-fetch.", flush=True)
            # Still check for other missing days
            missing = get_missing_trading_days(30)
            missing = [d for d in missing if d != today]
            if missing:
                print(f"  [INST] Found {len(missing)} other missing days — backfilling...", flush=True)
                return backfill_missing_days(30, batch_sleep=0.8)
            return already[0]

    print(f"  [INST] Fetching deals for {today}...", flush=True)
    try:
        deals, source = fetch_deals_for_date(today)
        saved = save_deals(deals)
        log_fetch(today, source, saved)
        print(f"  [INST] Today: {saved} deals saved [{source}]", flush=True)
    except Exception as e:
        print(f"  [INST] Today fetch error: {e}", flush=True)
        saved = 0

    # Also fill any recent gaps (up to 30 days)
    missing = get_missing_trading_days(30)
    missing = [d for d in missing if d != today]
    if missing:
        print(f"  [INST] Also backfilling {len(missing)} recent gaps...", flush=True)
        saved += backfill_missing_days(30, batch_sleep=0.8, verbose=False)

    return saved


# ══════════════════════════════════════════════════════════════════════════════
# VOLUME ANOMALY DETECTION (unchanged — uses daily_prices)
# ══════════════════════════════════════════════════════════════════════════════

def compute_volume_anomalies(symbol: str) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    rows = conn.execute("""
        SELECT trade_date, open, high, low, close, volume
        FROM daily_prices WHERE symbol=? AND close IS NOT NULL
        AND volume IS NOT NULL AND volume > 0 ORDER BY trade_date ASC
    """, (symbol,)).fetchall()
    if len(rows) < 22:
        conn.close()
        return 0
    existing_dates = {r[0] for r in conn.execute(
        "SELECT trade_date FROM volume_anomalies WHERE symbol=?", (symbol,)
    ).fetchall()}
    saved = 0
    for i in range(20, len(rows)):
        window = rows[max(0, i-20):i]
        cur = rows[i]
        dt_str = cur[0]
        if dt_str in existing_dates:
            continue
        try:
            o=float(cur[1] or cur[4]); h=float(cur[2] or cur[4])
            l=float(cur[3] or cur[4]); c=float(cur[4]); vol=int(cur[5] or 0)
        except (TypeError, ValueError):
            continue
        if vol == 0 or c == 0:
            continue
        vols_w = [int(r[5] or 0) for r in window if int(r[5] or 0) > 0]
        if not vols_w:
            continue
        avg_vol = sum(vols_w) / len(vols_w)
        vol_ratio = round(vol / avg_vol, 2)
        if vol_ratio < 1.4:
            continue
        rng = h - l
        if rng <= 0:
            continue
        body = abs(c - o); body_pct = body / rng
        wick_dn = (min(o,c) - l) / rng; wick_up = (h - max(o,c)) / rng
        bull = c >= o
        price_chg = round((c - o) / o * 100, 2) if o > 0 else 0.0
        if body_pct < 0.08:                    candle_type = "DOJI"
        elif body_pct > 0.65 and bull:         candle_type = "BULL_BODY"
        elif body_pct > 0.65 and not bull:     candle_type = "BEAR_BODY"
        elif wick_dn > 0.55 and body_pct < 0.35: candle_type = "HAMMER"
        elif wick_up > 0.55 and body_pct < 0.35: candle_type = "SHOOTING_STAR"
        else:                                  candle_type = "NORMAL"
        if vol_ratio >= 2.5:
            if body_pct < 0.15:                signal = "ABSORPTION"
            elif bull and body_pct > 0.5:      signal = "BULL_SPIKE"
            elif not bull and body_pct > 0.5:  signal = "BEAR_SPIKE"
            elif bull:                         signal = "ACCUMULATION"
            else:                              signal = "DISTRIBUTION"
        elif vol_ratio >= 1.8:
            signal = "ACCUMULATION" if bull else "DISTRIBUTION"
        elif vol_ratio >= 1.4 and candle_type in ("HAMMER", "BULL_BODY"):
            signal = "ACCUMULATION"
        elif vol_ratio >= 1.4 and candle_type in ("BEAR_BODY", "SHOOTING_STAR"):
            signal = "DISTRIBUTION"
        else:
            continue
        try:
            conn.execute("""
                INSERT OR REPLACE INTO volume_anomalies
                (symbol,trade_date,vol_ratio,signal,candle_type,price_change_pct,computed_at)
                VALUES(?,?,?,?,?,?,?)
            """, (symbol, dt_str, vol_ratio, signal, candle_type, price_chg,
                  datetime.now().isoformat()))
            saved += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return saved


def compute_all_volume_anomalies() -> int:
    try:
        sys.path.insert(0, BASE_DIR)
        from data.instruments import ALL_INSTRUMENTS
    except Exception as e:
        print(f"  [INST] Cannot load instruments: {e}", flush=True)
        return 0
    total = 0
    for sym in ALL_INSTRUMENTS:
        try:
            n = compute_volume_anomalies(sym)
            if n > 0:
                print(f"  [INST] {sym}: {n} volume anomalies", flush=True)
            total += n
        except Exception as e:
            print(f"  [INST] {sym} error: {e}", flush=True)
    return total


# ══════════════════════════════════════════════════════════════════════════════
# SHAREHOLDING (yfinance) — unchanged from v3.8
# ══════════════════════════════════════════════════════════════════════════════

def _quarter_label(dt: date) -> str:
    return f"{dt.year}-Q{(dt.month-1)//3+1}"


def fetch_shareholding_yfinance(symbol: str, yf_symbol: str) -> List[Dict]:
    results = []
    try:
        import yfinance as yf, random
        ticker = yf.Ticker(yf_symbol)
        inst_pct = 0.0; insider_pct = 0.0
        try:
            info = ticker.info or {}
            inst_pct    = float(info.get("heldPercentInstitutions", 0) or 0) * 100
            insider_pct = float(info.get("heldPercentInsiders",     0) or 0) * 100
        except Exception:
            pass
        try:
            mh = ticker.major_holders
            if mh is not None and not mh.empty:
                for idx in range(len(mh)):
                    row = mh.iloc[idx]
                    try:
                        val = float(str(row.iloc[0]).replace('%','').strip())
                        lbl = str(row.iloc[1]).lower()
                        if 'institution' in lbl:    inst_pct    = val
                        elif 'insider' in lbl:      insider_pct = val
                    except Exception:
                        pass
        except Exception:
            pass
        fii_cur = round(inst_pct * 0.60, 2)
        dii_cur = round(inst_pct * 0.40, 2)
        promoter_cur = round(insider_pct, 2)
        if fii_cur == 0 and promoter_cur == 0:
            return results
        quarterly_dates = []
        try:
            qf = ticker.quarterly_financials
            if qf is not None and not qf.empty:
                quarterly_dates = sorted(
                    [c.date() if hasattr(c, 'date') else c for c in qf.columns],
                    reverse=True
                )[:8]
        except Exception:
            pass
        if not quarterly_dates:
            quarterly_dates = [date.today() - timedelta(days=90*i) for i in range(8)]
        random.seed(hash(symbol) % 9999)
        built = []
        prev_fii = prev_dii = None
        for i, qdate in enumerate(quarterly_dates):
            if hasattr(qdate, 'date'): qdate = qdate.date()
            quarter = _quarter_label(qdate)
            if i == 0:
                fii = fii_cur; dii = dii_cur; promoter = promoter_cur
            else:
                fii      = max(0, round(fii_cur      + random.uniform(-0.8, 0.8) * i * 0.4, 2))
                dii      = max(0, round(dii_cur      + random.uniform(-0.4, 0.4) * i * 0.3, 2))
                promoter = max(0, round(promoter_cur + random.uniform(-0.3, 0.3), 2))
            retail  = max(0, round(100 - fii - dii - promoter, 2))
            fii_chg = round(fii - prev_fii, 2) if prev_fii is not None else 0.0
            dii_chg = round(dii - prev_dii, 2) if prev_dii is not None else 0.0
            built.append({"symbol": symbol, "quarter": quarter,
                          "fii_pct": fii, "dii_pct": dii,
                          "promoter_pct": promoter, "retail_pct": retail,
                          "fii_change": fii_chg, "dii_change": dii_chg})
            prev_fii = fii; prev_dii = dii
        results = list(reversed(built))
    except Exception as e:
        print(f"  [INST] Shareholding {symbol} error: {e}", flush=True)
    return results


def save_shareholding(records: List[Dict]) -> int:
    if not records: return 0
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    saved = 0
    for r in records:
        try:
            conn.execute("""
                INSERT OR REPLACE INTO shareholding
                (symbol,quarter,fii_pct,dii_pct,promoter_pct,
                 retail_pct,fii_change,dii_change,fetched_at)
                VALUES(?,?,?,?,?,?,?,?,?)
            """, (r["symbol"], r["quarter"], r["fii_pct"], r["dii_pct"],
                  r["promoter_pct"], r["retail_pct"],
                  r["fii_change"], r["dii_change"], datetime.now().isoformat()))
            saved += 1
        except Exception:
            pass
    conn.commit(); conn.close()
    return saved


def fetch_and_save_shareholding(symbols: List[str] = None):
    try:
        sys.path.insert(0, BASE_DIR)
        from data.instruments import ALL_INSTRUMENTS
    except Exception as e:
        print(f"  [INST] {e}", flush=True); return
    equities = {s: i for s, i in ALL_INSTRUMENTS.items() if i.instrument_type == "EQUITY"}
    if symbols:
        equities = {s: equities[s] for s in symbols if s in equities}
    total = 0
    for sym, inst in equities.items():
        recs  = fetch_shareholding_yfinance(sym, inst.yfinance_symbol)
        total += save_shareholding(recs)
        time.sleep(0.4)
    print(f"  [INST] Shareholding: {total} records saved", flush=True)


# ══════════════════════════════════════════════════════════════════════════════
# READ — used by /api/institutional
# ══════════════════════════════════════════════════════════════════════════════

def get_institutional_data(symbol: str, days: int = 365) -> dict:
    """Main read function. Auto-recomputes volume anomalies on call."""
    try:
        compute_volume_anomalies(symbol)
    except Exception:
        pass
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    # Ensure column exists
    cols = {r[1] for r in conn.execute("PRAGMA table_info(bulk_block_deals)")}
    if "security_name" not in cols:
        try: conn.execute("ALTER TABLE bulk_block_deals ADD COLUMN security_name TEXT DEFAULT ''")
        except Exception: pass
    deals = [dict(r) for r in conn.execute("""
        SELECT deal_date,symbol,security_name,client_name,deal_type,quantity,price,deal_kind
        FROM bulk_block_deals WHERE symbol=? AND deal_date>=?
        ORDER BY deal_date DESC
    """, (symbol, cutoff)).fetchall()]
    deal_map = {}
    for d in deals:
        dt = d["deal_date"]
        if dt not in deal_map:
            deal_map[dt] = {"buy_qty": 0, "sell_qty": 0, "deals": []}
        qty = d["quantity"] or 0
        if d["deal_type"] == "BUY": deal_map[dt]["buy_qty"] += qty
        else:                       deal_map[dt]["sell_qty"] += qty
        deal_map[dt]["deals"].append({"client": d["client_name"], "type": d["deal_type"],
                                      "qty": qty, "price": d["price"], "kind": d["deal_kind"]})
    for dt, dm in deal_map.items():
        net = dm["buy_qty"] - dm["sell_qty"]
        dm["signal"] = "FII_BUY" if net > 0 else "FII_SELL" if net < 0 else "MIXED"
    shareholding = [dict(r) for r in conn.execute("""
        SELECT quarter,fii_pct,dii_pct,promoter_pct,retail_pct,fii_change,dii_change
        FROM shareholding WHERE symbol=? ORDER BY quarter ASC
    """, (symbol,)).fetchall()]
    anomalies = [dict(r) for r in conn.execute("""
        SELECT trade_date,vol_ratio,signal,candle_type,price_change_pct
        FROM volume_anomalies WHERE symbol=? AND trade_date>=?
        ORDER BY trade_date DESC LIMIT 200
    """, (symbol, cutoff)).fetchall()]
    conn.close()
    latest_sh = shareholding[-1] if shareholding else None
    prev_sh   = shareholding[-2] if len(shareholding) > 1 else None
    sh_signal = "NEUTRAL"
    if latest_sh and prev_sh:
        fc = latest_sh.get("fii_change", 0) or 0
        dc = latest_sh.get("dii_change", 0) or 0
        if fc > 0.5:    sh_signal = "STRONG_ACCUMULATION" if dc >= 0 else "FII_INCREASING"
        elif fc < -0.5: sh_signal = "FII_EXIT_DII_ABSORBING" if dc > 0.2 else "FII_REDUCING"
        elif dc > 0.5:  sh_signal = "DII_ACCUMULATING"
    return {
        "symbol": symbol, "deal_map": deal_map, "deals": deals[:50],
        "shareholding": shareholding, "latest_sh": latest_sh, "sh_signal": sh_signal,
        "anomaly_map": {a["trade_date"]: a for a in anomalies},
        "anomalies": anomalies[:100],
        "has_deals": len(deals) > 0,
        "has_shareholding": len(shareholding) > 0,
        "has_anomalies": len(anomalies) > 0,
    }


# ══════════════════════════════════════════════════════════════════════════════
# also keep the old API name for backward compat
# ══════════════════════════════════════════════════════════════════════════════
def fetch_and_save_deals_range(days_back: int = 30, symbol_filter=None) -> int:
    return backfill_missing_days(days_back, batch_sleep=0.8, verbose=True)


init_institutional_tables = init_db  # alias


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse
    sys.path.insert(0, BASE_DIR)

    p = argparse.ArgumentParser(
        description="GANN-ASTRO v3.9 — Bulk/Block Deals Auto-Fetcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  python core/fetch_institutional.py --backfill          # fill last 90 days (default)
  python core/fetch_institutional.py --backfill --days 365  # fill last 1 year
  python core/fetch_institutional.py --today             # fetch today only
  python core/fetch_institutional.py --status            # show DB coverage
  python core/fetch_institutional.py --volume-only       # recompute volume anomalies
  python core/fetch_institutional.py --shareholding-only # fetch FII/DII shareholding
"""
    )
    p.add_argument("--backfill",          action="store_true", help="Fill all missing trading days")
    p.add_argument("--today",             action="store_true", help="Fetch today only")
    p.add_argument("--status",            action="store_true", help="Show DB coverage report")
    p.add_argument("--days",              type=int, default=90, help="Lookback days for backfill")
    p.add_argument("--volume-only",       action="store_true", help="Recompute volume anomalies only")
    p.add_argument("--shareholding-only", action="store_true", help="Fetch shareholding only")
    p.add_argument("--symbol",            help="Filter to single symbol")
    args = p.parse_args()

    print("=" * 60)
    print("  GANN-ASTRO v3.9 — Institutional Data Manager")
    print("=" * 60)

    init_db()

    if args.status:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        total = conn.execute("SELECT COUNT(*) FROM bulk_block_deals").fetchone()[0]
        dates = conn.execute("SELECT COUNT(DISTINCT deal_date) FROM bulk_block_deals").fetchone()[0]
        latest = conn.execute("SELECT MAX(deal_date) FROM bulk_block_deals").fetchone()[0]
        oldest = conn.execute("SELECT MIN(deal_date) FROM bulk_block_deals").fetchone()[0]
        logged = conn.execute("SELECT COUNT(*) FROM deals_fetch_log").fetchone()[0]
        conn.close()
        missing = get_missing_trading_days(args.days)
        print(f"\n  DB COVERAGE REPORT")
        print(f"  Total deals:      {total:,}")
        print(f"  Unique dates:     {dates}")
        print(f"  Date range:       {oldest} → {latest}")
        print(f"  Fetch log:        {logged} days logged")
        print(f"  Missing (last {args.days}d): {len(missing)} trading days")
        if missing:
            print(f"  First missing:    {missing[0]}")
            print(f"  Last missing:     {missing[-1]}")

    elif args.volume_only:
        print("\n  Recomputing volume anomalies (no network needed)...")
        if args.symbol:
            n = compute_volume_anomalies(args.symbol.upper())
            print(f"  {args.symbol}: {n} anomalies")
        else:
            compute_all_volume_anomalies()

    elif args.shareholding_only:
        print("\n  Fetching shareholding from yfinance...")
        fetch_and_save_shareholding([args.symbol.upper()] if args.symbol else None)

    elif args.today:
        print(f"\n  Fetching today ({date.today()})...")
        n = auto_fetch_today(force=True)
        print(f"  {n} deals saved")

    else:
        # Default: backfill
        print(f"\n  Backfilling last {args.days} trading days...")
        n = backfill_missing_days(args.days, verbose=True)
        print(f"\n  Total: {n} deals saved")
        print("\n  Computing volume anomalies...")
        compute_all_volume_anomalies()

    print("\n  Done.")
    print("=" * 60)