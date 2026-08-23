"""
download_bulk_deals.py — GANN-ASTRO v4.0
==========================================
Run this ON YOUR WINDOWS MACHINE (where NSE is accessible).

WHAT IT DOES:
  1. Checks your DB for missing trading days
  2. Downloads NSE bulk + block deal CSVs for each missing day
  3. Imports directly into market_data_v2.db
  4. Runs forever (daily auto mode) or once (backfill mode)

USAGE:
  python download_bulk_deals.py                    # backfill missing + run daily
  python download_bulk_deals.py --backfill         # fill all missing days (90 days)
  python download_bulk_deals.py --backfill --days 365  # fill last 1 year
  python download_bulk_deals.py --date 2026-04-07  # fetch one specific date
  python download_bulk_deals.py --status           # show what's in DB

REQUIREMENTS:
  pip install requests
  (Python 3.8+ only, no other dependencies)
"""

import os, sys, csv, io, re, sqlite3, time, json, argparse
from datetime import date, datetime, timedelta
from pathlib import Path

# ── Find the DB ───────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
DB_PATH = SCRIPT_DIR / "market_data_v2.db"
if not DB_PATH.exists():
    # Try parent dir
    DB_PATH = SCRIPT_DIR.parent / "market_data_v2.db"
if not DB_PATH.exists():
    print(f"ERROR: market_data_v2.db not found in {SCRIPT_DIR}")
    print("Place this script in your GANN-ASTRO-v4.0 folder.")
    sys.exit(1)

print(f"  DB: {DB_PATH}")

# ── NSE Holiday Calendar ──────────────────────────────────────────────────────
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


# ── DB Setup ──────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bulk_block_deals (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_date     TEXT NOT NULL,
            symbol        TEXT NOT NULL,
            security_name TEXT DEFAULT '',
            client_name   TEXT DEFAULT '—',
            deal_type     TEXT NOT NULL,
            quantity      INTEGER DEFAULT 0,
            price         REAL DEFAULT 0,
            deal_kind     TEXT NOT NULL,
            fetched_at    TEXT,
            UNIQUE(deal_date, symbol, client_name, deal_type, deal_kind)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS deals_fetch_log (
            fetch_date  TEXT NOT NULL,
            source      TEXT,
            deals_saved INTEGER DEFAULT 0,
            fetched_at  TEXT,
            PRIMARY KEY (fetch_date)
        )
    """)
    # Add missing columns if older schema
    cols = {r[1] for r in conn.execute("PRAGMA table_info(bulk_block_deals)")}
    if "security_name" not in cols:
        conn.execute("ALTER TABLE bulk_block_deals ADD COLUMN security_name TEXT DEFAULT ''")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bbd_date   ON bulk_block_deals(deal_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bbd_symbol ON bulk_block_deals(symbol)")
    conn.commit()
    conn.close()


def get_missing_days(lookback: int = 90):
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    existing = {r[0] for r in conn.execute("SELECT DISTINCT deal_date FROM bulk_block_deals")}
    logged   = {r[0] for r in conn.execute("SELECT fetch_date FROM deals_fetch_log")}
    conn.close()
    covered = existing | logged
    today   = date.today()
    start   = today - timedelta(days=lookback)
    missing = []
    d = start
    while d < today:   # never fetch today — market still open
        if is_trading_day(d) and d.isoformat() not in covered:
            missing.append(d)
        d += timedelta(days=1)
    return missing


def log_fetch(d: date, source: str, count: int):
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            INSERT OR REPLACE INTO deals_fetch_log(fetch_date, source, deals_saved, fetched_at)
            VALUES(?,?,?,?)
        """, (d.isoformat(), source, count, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception:
        pass


def save_deals(deals: list) -> int:
    if not deals:
        return 0
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    saved = 0
    for deal in deals:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO bulk_block_deals
                (deal_date, symbol, security_name, client_name,
                 deal_type, quantity, price, deal_kind, fetched_at)
                VALUES(?,?,?,?,?,?,?,?,?)
            """, (
                deal["deal_date"],
                deal["symbol"][:20],
                deal.get("security_name", deal["symbol"])[:100],
                deal.get("client_name", "—")[:100],
                deal["deal_type"],
                int(deal.get("quantity", 0) or 0),
                float(deal.get("price", 0) or 0),
                deal["deal_kind"],
                datetime.now().isoformat(),
            ))
            if conn.execute("SELECT changes()").fetchone()[0]:
                saved += 1
        except Exception as e:
            print(f"    [WARN] save error: {e}", flush=True)
    conn.commit()
    conn.close()
    return saved


# ── CSV Parsing ───────────────────────────────────────────────────────────────
def _clean_num(s):
    try: return float(re.sub(r"[^\d.]", "", str(s or "0")) or "0")
    except: return 0.0

def _clean_int(s):
    try: return int(float(re.sub(r"[^\d.]", "", str(s or "0")) or "0"))
    except: return 0

def parse_csv(text: str, deal_kind: str, deal_date: date) -> list:
    """
    Parse NSE bulk/block deal CSV exactly as downloaded from NSE website.
    Handles both date formats in the CSV (01-APR-2026 and 01/04/2026).
    """
    deals = []
    try:
        text = text.lstrip("\ufeff").strip()
        if not text or len(text) < 20 or "<html" in text.lower():
            return []

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return []

        # Normalise field names (strip spaces)
        fields = [f.strip() for f in (reader.fieldnames or [])]

        for raw in reader:
            row = {k.strip(): (v or "").strip() for k, v in raw.items() if k}

            # DATE override from row if present (e.g. multi-day export from website)
            row_date_str = row.get("Date") or row.get("DATE") or row.get("deal_date")
            row_date = deal_date.isoformat()
            if row_date_str:
                try:
                    # Format is usually "20-APR-2026"
                    from datetime import datetime
                    parsed = datetime.strptime(row_date_str.strip(), "%d-%b-%Y").date()
                    row_date = parsed.isoformat()
                except Exception:
                    pass

            # SYMBOL
            sym = (row.get("Symbol") or row.get("SYMBOL") or
                   row.get("symbol") or "").upper().strip()
            sym = re.sub(r"\.(NS|BO)$", "", sym)
            if not sym or sym.isdigit() or sym == "SYMBOL":
                continue

            # SECURITY NAME
            sec = (row.get("Security Name") or row.get("SECURITY NAME") or
                   row.get("security_name") or sym)[:100]

            # CLIENT NAME
            client = (row.get("Client Name") or row.get("CLIENT NAME") or
                      row.get("client_name") or "—")[:100]

            # BUY / SELL — NSE uses "B" or "S" sometimes, "Buy" or "Sell" other times
            bs_raw = (
                row.get("Buy / Sell") or row.get("Buy/Sell") or
                row.get("BUY / SELL") or row.get("BUY/SELL") or
                row.get("buySell") or row.get("BS") or "B"
            ).strip().upper()
            deal_type = "BUY" if bs_raw.startswith("B") else "SELL"

            # QUANTITY
            qty = _clean_int(
                row.get("Quantity Traded") or row.get("QUANTITY TRADED") or
                row.get("Quantity") or row.get("qty") or "0"
            )

            # PRICE
            price = _clean_num(
                row.get("Trade Price / Wght. Avg. Price") or
                row.get("Trade Price/ Wght. Avg. Price") or
                row.get("Trade Price/Weighted Avg Price") or
                row.get("Trade Price") or row.get("Price") or
                row.get("price") or "0"
            )

            if qty == 0 and price == 0:
                continue

            deals.append({
                "deal_date":     row_date,
                "symbol":        sym,
                "security_name": sec,
                "client_name":   client,
                "deal_type":     deal_type,
                "quantity":      qty,
                "price":         price,
                "deal_kind":     deal_kind,
            })

    except Exception as e:
        print(f"    [WARN] CSV parse error: {e}", flush=True)
    return deals


def parse_json(data, deal_kind: str, deal_date: date) -> list:
    """Parse NSE JSON API response."""
    records = []
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        for key in ("data", "bulkDealData", "blockDealData",
                    "Session 1", "Session 2", "result"):
            v = data.get(key)
            if isinstance(v, list):
                records.extend(v)

    deals = []
    for d in records:
        if not isinstance(d, dict):
            continue
        def _v(*keys):
            for k in keys:
                val = d.get(k)
                if val is not None and str(val).strip() not in ("", "None", "-", "null"):
                    return str(val).strip()
            return ""
        sym = _v("symbol", "Symbol", "SYMBOL").upper()
        sym = re.sub(r"\.(NS|BO)$", "", sym)
        if not sym or sym.isdigit():
            continue
        bs = _v("buySell", "Buy/Sell", "BUY/SELL", "BS") or "S"
        deals.append({
            "deal_date":     deal_date.isoformat(),
            "symbol":        sym,
            "security_name": _v("companyName", "securityName", "Security Name")[:100] or sym,
            "client_name":   _v("clientName", "Client Name", "CLIENT NAME")[:100] or "—",
            "deal_type":     "BUY" if bs.upper().startswith("B") else "SELL",
            "quantity":      _clean_int(_v("quantityTraded", "Quantity Traded", "qty") or "0"),
            "price":         _clean_num(_v("tradePrice", "Trade Price / Wght. Avg. Price", "Price") or "0"),
            "deal_kind":     deal_kind,
        })
    return deals


# ══════════════════════════════════════════════════════════════════════════════
# NSE DOWNLOADER — runs directly on your Windows machine
# ══════════════════════════════════════════════════════════════════════════════

class NSEDownloader:
    """
    Downloads NSE bulk + block deal CSVs.
    Runs on your local Windows machine where NSE is accessible.
    Three strategies tried in order:
      1. NSE archive CSV (public static files, most reliable)
      2. NSE website API (needs session cookie)
      3. NSE website HTML scrape (last resort)
    """

    def __init__(self):
        import requests
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-IN,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        })
        self._cookie_fresh = False
        self._warm_up()

    def _warm_up(self):
        """Get NSE session cookies — required for API calls."""
        try:
            r = self.session.get(
                "https://www.nseindia.com",
                timeout=15,
                headers={"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"},
                allow_redirects=True
            )
            if r.status_code == 200:
                time.sleep(1.2)
                # Also hit the bulk deals page to get correct referer cookies
                self.session.get(
                    "https://www.nseindia.com/market-data/bulk-deals",
                    timeout=15
                )
                time.sleep(0.8)
                self._cookie_fresh = True
                print(f"  [NSE] Session ready. Cookies: {list(self.session.cookies.keys())}")
            else:
                print(f"  [NSE] Homepage returned {r.status_code}. Will try archive directly.")
        except Exception as e:
            print(f"  [NSE] Warmup warning: {e}")

    def _re_warm(self):
        """Re-acquire cookies if session expired (401/403)."""
        try:
            self.session.get("https://www.nseindia.com", timeout=10)
            time.sleep(2.0)
            self._cookie_fresh = True
        except Exception:
            pass

    def _fetch_url(self, url: str, is_api: bool = False, retry: int = 3) -> bytes | None:
        """Fetch a URL with retry logic."""
        headers = {}
        if is_api:
            headers = {
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": "https://www.nseindia.com/market-data/bulk-deals",
            }
        else:
            headers = {
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                "Referer": "https://www.nseindia.com/",
            }

        for attempt in range(retry):
            try:
                r = self.session.get(url, headers=headers, timeout=25)
                if r.status_code == 200 and len(r.content) > 30:
                    return r.content
                if r.status_code in (401, 403) and attempt < retry - 1:
                    print(f"    [{r.status_code}] Re-acquiring session...", flush=True)
                    self._re_warm()
                    time.sleep(2)
            except Exception as e:
                if attempt < retry - 1:
                    time.sleep(1.5)
        return None

    def fetch_date(self, d: date) -> tuple[list, str]:
        """
        Fetch bulk + block deals for a single date.
        Returns (deals_list, source_name).
        """
        ymd  = d.strftime("%Y%m%d")
        dmy  = d.strftime("%d%m%Y")
        dapi = d.strftime("%d-%m-%Y")

        all_deals = []
        source = "NONE"

        # ── Strategy 1: NSE Archive CSV (static public files) ─────────────────
        # These URLs work from Indian IPs without any cookies
        for deal_kind, urls in [
            ("BULK", [
                f"https://archives.nseindia.com/archives/equities/bultrans/bulkdeals{ymd}.csv",
                f"https://archives.nseindia.com/archives/equities/bultrans/bulkdeals{dmy}.csv",
                f"https://nsearchives.nseindia.com/archives/equities/bultrans/bulkdeals{ymd}.csv",
            ]),
            ("BLOCK", [
                f"https://archives.nseindia.com/archives/equities/blockdeals/blockdeals{ymd}.csv",
                f"https://archives.nseindia.com/archives/equities/blockdeals/blockdeals{dmy}.csv",
                f"https://nsearchives.nseindia.com/archives/equities/blockdeals/blockdeals{ymd}.csv",
            ]),
        ]:
            for url in urls:
                content = self._fetch_url(url)
                if content is None:
                    continue
                text = content.decode("utf-8", errors="replace")
                if "<html" in text.lower():
                    continue
                deals = parse_csv(text, deal_kind, d)
                if deals:
                    all_deals.extend(deals)
                    source = "ARCHIVE_CSV"
                    break
                elif len(content) > 10:
                    # Got response but no data = legitimately no deals
                    source = "ARCHIVE_CSV"
                    break

        if all_deals:
            return all_deals, source

        # ── Strategy 2: NSE JSON API (with session cookie) ────────────────────
        for deal_kind, api_urls in [
            ("BULK", [
                f"https://www.nseindia.com/api/historical/bulk-deals?from={dapi}&to={dapi}",
                f"https://www.nseindia.com/api/bulk-deal-archives?from={dapi}&to={dapi}&category=bulk",
            ]),
            ("BLOCK", [
                f"https://www.nseindia.com/api/block-deal?from={dapi}&to={dapi}",
                f"https://www.nseindia.com/api/historical/block-deals?from={dapi}&to={dapi}",
            ]),
        ]:
            for url in api_urls:
                content = self._fetch_url(url, is_api=True)
                if content is None:
                    continue
                try:
                    data  = json.loads(content)
                    deals = parse_json(data, deal_kind, d)
                    if deals:
                        all_deals.extend(deals)
                        source = "NSE_API"
                        break
                    else:
                        source = "NSE_API"  # Got response, no data
                        break
                except Exception:
                    continue

        if all_deals:
            return all_deals, source

        # ── Strategy 3: NSE website HTML download links ───────────────────────
        # The NSE bulk deal page has download links that look like:
        # https://www.nseindia.com/api/bulk-deals-download?from=DD-MM-YYYY&to=DD-MM-YYYY
        for deal_kind, dl_url in [
            ("BULK",  f"https://www.nseindia.com/api/bulk-deals-download?from={dapi}&to={dapi}"),
            ("BLOCK", f"https://www.nseindia.com/api/block-deals-download?from={dapi}&to={dapi}"),
        ]:
            content = self._fetch_url(dl_url, is_api=True)
            if content:
                text = content.decode("utf-8", errors="replace")
                if not "<html" in text.lower() and len(content) > 30:
                    deals = parse_csv(text, deal_kind, d)
                    if deals:
                        all_deals.extend(deals)
                        source = "NSE_DOWNLOAD"

        return all_deals, source if all_deals else "NONE"


# ══════════════════════════════════════════════════════════════════════════════
# IMPORT FROM CSV FOLDER — if you already have CSVs downloaded manually
# ══════════════════════════════════════════════════════════════════════════════

def import_csv_folder(folder_path: str) -> int:
    """
    Import all CSV files from a folder into the DB.
    Filename format: bulkdeals_YYYY-MM-DD.csv or blockdeals_YYYY-MM-DD.csv
    Or: BulkDeal_01042026.csv etc. — auto-detects date from filename.
    """
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Folder not found: {folder}")
        return 0

    total = 0
    csv_files = list(set(list(folder.glob("*.csv")) + list(folder.glob("*.CSV"))))
    print(f"  Found {len(csv_files)} CSV files in {folder}")

    for csv_file in sorted(csv_files):
        name = csv_file.stem.lower()

        # Detect deal_kind from filename
        if "block" in name:
            deal_kind = "BLOCK"
        else:
            deal_kind = "BULK"  # default

        # Extract date from filename — try multiple formats
        d = None
        date_patterns = [
            r"(\d{4})-(\d{2})-(\d{2})",  # YYYY-MM-DD
            r"(\d{4})(\d{2})(\d{2})",      # YYYYMMDD
            r"(\d{2})(\d{2})(\d{4})",      # DDMMYYYY
            r"(\d{2})-(\d{2})-(\d{4})",   # DD-MM-YYYY
        ]
        for pat in date_patterns:
            m = re.search(pat, name)
            if m:
                g = m.groups()
                try:
                    if len(g[0]) == 4:  # YYYY first
                        d = date(int(g[0]), int(g[1]), int(g[2]))
                    elif len(g[2]) == 4:  # YYYY last
                        d = date(int(g[2]), int(g[1]), int(g[0]))
                    if d and date(2020, 1, 1) <= d <= date.today():
                        break
                    d = None
                except Exception:
                    d = None

        if d is None:
            print(f"  [SKIP] Cannot determine date from: {csv_file.name}")
            continue

        try:
            text = csv_file.read_text(encoding="utf-8", errors="replace")
            deals = parse_csv(text, deal_kind, d)
            if deals:
                saved = save_deals(deals)
                log_fetch(d, f"IMPORT_CSV:{csv_file.name}", saved)
                print(f"  [IMPORT] {csv_file.name}: {saved}/{len(deals)} {deal_kind} deals saved for {d}")
                total += saved
                # Permanently delete the file after successful import
                try:
                    csv_file.unlink()
                except Exception as e:
                    print(f"  [WARN] Could not delete {csv_file.name}: {e}")
            else:
                # Print headers to help debug why 0 deals
                try:
                    import csv, io
                    reader = csv.reader(io.StringIO(text.lstrip("\ufeff").strip()))
                    headers = next(reader, [])
                    print(f"  [SKIP] {csv_file.name}: no valid deals found. Headers seen: {headers}")
                except Exception:
                    print(f"  [SKIP] {csv_file.name}: no valid deals found (could not parse headers)")
        except Exception as e:
            print(f"  [ERROR] {csv_file.name}: {e}")

    return total


# ══════════════════════════════════════════════════════════════════════════════
# DAILY RUNNER — runs at 15:35 IST automatically
# ══════════════════════════════════════════════════════════════════════════════

def run_daily_auto(downloader: "NSEDownloader"):
    """
    Run automatically every day at 15:35 IST.
    Fetches today's deals + fills any recent gaps.
    """
    import threading

    def _ist_now():
        """Current IST time (UTC+5:30)."""
        return datetime.utcnow() + timedelta(hours=5, minutes=30)

    def _next_fetch_time():
        """Next 15:35 IST in UTC+5:30."""
        now_ist = _ist_now()
        target  = now_ist.replace(hour=15, minute=35, second=0, microsecond=0)
        if now_ist >= target:
            target += timedelta(days=1)
        # Skip to next trading day if target is weekend/holiday
        while not is_trading_day(target.date()):
            target += timedelta(days=1)
            target  = target.replace(hour=15, minute=35, second=0, microsecond=0)
        return target

    print("\n  DAILY AUTO MODE — will fetch at 15:35 IST every trading day")
    print("  Press Ctrl+C to stop.\n")

    while True:
        next_run = _next_fetch_time()
        now_ist  = _ist_now()
        wait_sec = (next_run - now_ist).total_seconds()

        print(f"  Next fetch: {next_run.strftime('%Y-%m-%d %H:%M IST')} "
              f"(in {wait_sec/3600:.1f} hours)")

        time.sleep(max(0, wait_sec))

        run_date = date.today()
        if not is_trading_day(run_date):
            print(f"  [SKIP] {run_date} is not a trading day")
            continue

        print(f"\n  [{datetime.now().strftime('%H:%M:%S')}] Fetching {run_date}...")

        # Also backfill any gaps from the last 30 days
        missing = get_missing_days(lookback=30)
        if missing:
            print(f"  Found {len(missing)} missing days — backfilling...")
            for d in missing:
                print(f"    {d}...", end=" ", flush=True)
                deals, src = downloader.fetch_date(d)
                saved = save_deals(deals)
                log_fetch(d, src, saved)
                print(f"{saved} deals [{src}]")
                time.sleep(1.5)

        # Fetch today
        deals, src = downloader.fetch_date(run_date)
        saved = save_deals(deals)
        log_fetch(run_date, src, saved)
        print(f"  Today {run_date}: {saved} deals saved [{src}]")
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] Done.")


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(
        description="GANN-ASTRO v4.0 — NSE Bulk/Block Deal Downloader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  python download_bulk_deals.py --backfill              Fill last 90 days
  python download_bulk_deals.py --backfill --days 365   Fill last 1 year
  python download_bulk_deals.py --date 2026-04-07       Fetch one date
  python download_bulk_deals.py --import-csv ./deals/   Import all CSVs from folder
  python download_bulk_deals.py --status                Show DB coverage
  python download_bulk_deals.py --daily                 Run daily at 15:35 IST (keep running)

FOLDER IMPORT (if you already downloaded CSVs manually):
  1. Put all your CSV files in a folder (e.g. C:/deals/)
  2. python download_bulk_deals.py --import-csv C:/deals/
  Filename format: bulkdeals20260402.csv or blockdeals_2026-04-02.csv
"""
    )
    p.add_argument("--backfill",    action="store_true",  help="Fill all missing trading days")
    p.add_argument("--daily",       action="store_true",  help="Run daily mode (keeps running)")
    p.add_argument("--date",        type=str,             help="Fetch specific date YYYY-MM-DD")
    p.add_argument("--import-csv",  type=str, metavar="FOLDER", help="Import CSV files from folder")
    p.add_argument("--status",      action="store_true",  help="Show DB coverage report")
    p.add_argument("--days",        type=int, default=90, help="Lookback days for backfill")
    args = p.parse_args()

    print("=" * 60)
    print("  GANN-ASTRO v4.0 — NSE Bulk/Block Deal Downloader")
    print("=" * 60)

    init_db()

    # ── Status ────────────────────────────────────────────────────────────────
    if args.status:
        conn = sqlite3.connect(str(DB_PATH), timeout=10)
        total   = conn.execute("SELECT COUNT(*) FROM bulk_block_deals").fetchone()[0]
        dates   = conn.execute("SELECT COUNT(DISTINCT deal_date) FROM bulk_block_deals").fetchone()[0]
        latest  = conn.execute("SELECT MAX(deal_date) FROM bulk_block_deals").fetchone()[0]
        oldest  = conn.execute("SELECT MIN(deal_date) FROM bulk_block_deals").fetchone()[0]
        by_src  = conn.execute("""
            SELECT source, COUNT(*), SUM(deals_saved)
            FROM deals_fetch_log GROUP BY source ORDER BY COUNT(*) DESC
        """).fetchall()
        conn.close()
        missing = get_missing_days(args.days)
        print(f"\n  ── DATABASE COVERAGE REPORT ──")
        print(f"  Total deal rows:    {total:,}")
        print(f"  Unique dates:       {dates}")
        print(f"  Date range:         {oldest} → {latest}")
        print(f"  Missing (last {args.days}d): {len(missing)} trading days")
        if missing:
            print(f"  Missing dates:      {[str(m) for m in missing[:5]]}" +
                  (" ..." if len(missing) > 5 else ""))
        if by_src:
            print(f"\n  ── FETCH LOG BY SOURCE ──")
            for src, cnt, total_deals in by_src:
                print(f"  {(src or 'NONE'):20s} {cnt:3d} days  {(total_deals or 0):6,} deals")
        return

    # ── Import CSV folder ─────────────────────────────────────────────────────
    if args.import_csv:
        print(f"\n  Importing CSVs from: {args.import_csv}")
        n = import_csv_folder(args.import_csv)
        print(f"\n  Total imported: {n} deals")
        return

    # ── Single date ───────────────────────────────────────────────────────────
    if args.date:
        try:
            d = date.fromisoformat(args.date)
        except ValueError:
            print(f"Invalid date format. Use YYYY-MM-DD")
            return
        print(f"\n  Fetching {d}...")
        downloader = NSEDownloader()
        deals, src = downloader.fetch_date(d)
        saved = save_deals(deals)
        log_fetch(d, src, saved)
        print(f"  {saved} deals saved [{src}]")
        if deals:
            syms = list({d["symbol"] for d in deals})[:10]
            print(f"  Symbols: {', '.join(syms)}")
        return

    # ── Backfill ──────────────────────────────────────────────────────────────
    if args.backfill or not any([args.daily, args.date, args.import_csv, args.status]):
        missing = get_missing_days(args.days)
        if not missing:
            print(f"\n  ✓ No missing trading days in last {args.days} days. DB is complete.")
        else:
            print(f"\n  Backfilling {len(missing)} missing trading days...")
            print(f"  Range: {missing[0]} → {missing[-1]}\n")
            downloader = NSEDownloader()
            total = 0
            for i, d in enumerate(missing):
                print(f"  [{i+1:3d}/{len(missing)}] {d}...", end=" ", flush=True)
                deals, src = downloader.fetch_date(d)
                saved = save_deals(deals)
                log_fetch(d, src, saved)
                total += saved
                status = f"{saved} deals" if saved > 0 else "no deals"
                print(f"{status} [{src}]", flush=True)
                time.sleep(1.5)  # Be respectful to NSE servers
            print(f"\n  ✓ Backfill complete: {total} total deals saved")

        if args.daily:
            downloader = NSEDownloader()
            run_daily_auto(downloader)
        return

    # ── Daily mode only ───────────────────────────────────────────────────────
    if args.daily:
        downloader = NSEDownloader()
        run_daily_auto(downloader)


if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        print("ERROR: requests not installed. Run: pip install requests")
        sys.exit(1)
    main()