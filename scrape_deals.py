"""
scrape_deals.py — NSE Bulk and Block Deals Pipeline
===================================================
Scrapes the NSE API for bulk and block deals using nselib and saves to market_data_v2.db.
Handles fetching missing days automatically.

Usage:
  python scrape_deals.py                    # fetch missing days up to today
  python scrape_deals.py --days 30          # check the last 30 days for missing data
"""

import os
import sqlite3
import argparse
import pandas as pd
from datetime import date, datetime, timedelta
from nselib import capital_market

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "market_data_v2.db")

def ensure_db_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS bulk_block_deals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_date   TEXT NOT NULL,
            symbol      TEXT NOT NULL,
            deal_type   TEXT NOT NULL,
            quantity    INTEGER DEFAULT 0,
            price       REAL    DEFAULT 0,
            deal_kind   TEXT NOT NULL,
            client_name TEXT    DEFAULT '',
            fetched_at  TEXT, 
            security_name TEXT DEFAULT '',
            UNIQUE(deal_date, symbol, deal_type, deal_kind, quantity)
        );
        CREATE TABLE IF NOT EXISTS deals_checked_dates (
            deal_date   TEXT PRIMARY KEY,
            deals_found INTEGER DEFAULT 0,
            checked_at  TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_bb_deals_date ON bulk_block_deals(deal_date, deal_kind);
        CREATE INDEX IF NOT EXISTS idx_bb_deals_sym ON bulk_block_deals(symbol, deal_date);
    """)
    conn.commit()

def get_missing_dates(conn: sqlite3.Connection, check_days: int) -> list:
    missing = []
    end_date = date.today()
    start_date = end_date - timedelta(days=check_days)
    curr = start_date
    while curr <= end_date:
        if curr.weekday() < 5:  # Mon-Fri
            date_str = curr.strftime("%Y-%m-%d")
            cur = conn.cursor()
            cur.execute("""
                SELECT 1 FROM bulk_block_deals WHERE deal_date = ?
                UNION
                SELECT 1 FROM deals_checked_dates WHERE deal_date = ?
            """, (date_str, date_str))
            if not cur.fetchone():
                missing.append(curr)
        curr += timedelta(days=1)
    return missing

def parse_and_save(conn: sqlite3.Connection, df: pd.DataFrame, deal_kind: str):
    if df is None or df.empty:
        return 0
    rows = []
    for _, row in df.iterrows():
        # Date format from nselib is usually DD-MMM-YYYY
        try:
            raw_date = str(row.get('Date', '')).strip()
            if not raw_date:
                continue
            dt_obj = datetime.strptime(raw_date, "%d-%b-%Y")
            db_date = dt_obj.strftime("%Y-%m-%d")
        except ValueError:
            continue
            
        symbol = str(row.get('Symbol', '')).strip()
        sec_name = str(row.get('SecurityName', '')).strip()
        client = str(row.get('ClientName', '')).strip()
        buy_sell = str(row.get('Buy/Sell', '')).strip()
        
        try:
            qty_str = str(row.get('QuantityTraded', '0')).replace(',', '')
            qty = int(qty_str) if qty_str != '-' else 0
        except:
            qty = 0
            
        try:
            price_str = str(row.get('TradePrice/Wght.Avg.Price', '0.0')).replace(',', '')
            price = float(price_str) if price_str != '-' else 0.0
        except:
            price = 0.0
            
        rows.append({
            "deal_date": db_date,
            "symbol": symbol,
            "deal_type": buy_sell,
            "quantity": qty,
            "price": price,
            "deal_kind": deal_kind,
            "client_name": client,
            "security_name": sec_name
        })
        
    if not rows:
        return 0
        
    initial_changes = conn.total_changes
    conn.executemany("""
        INSERT OR IGNORE INTO bulk_block_deals
            (deal_date, symbol, deal_type, quantity, price, deal_kind, client_name, security_name, fetched_at)
        VALUES
            (:deal_date, :symbol, :deal_type, :quantity, :price, :deal_kind, :client_name, :security_name, datetime('now','localtime'))
    """, rows)
    conn.commit()
    try:
        from core.tracker import handle_bulk_deals_drip
        handle_bulk_deals_drip(rows, conn=conn)
    except Exception as _e:
        pass
    return conn.total_changes - initial_changes

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=15)
    args = parser.parse_args()

    print(f"\\n{'='*60}")
    print(f"  NSE Bulk/Block Deals Scraper  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\\n")

    conn = sqlite3.connect(DB_PATH)
    ensure_db_tables(conn)

    missing_dates = get_missing_dates(conn, args.days)
    if not missing_dates:
        print("[INFO] No missing market days found. All caught up!")
        conn.close()
        return

    print(f"[INFO] Found {len(missing_dates)} missing days. Fetching with nselib...")
    total_inserted = 0

    start_dt = missing_dates[0]
    end_dt = min(missing_dates[-1], date.today())
    if start_dt >= end_dt:
        start_dt = end_dt - timedelta(days=1)
    start_date_str = start_dt.strftime("%d-%m-%Y")
    end_date_str = end_dt.strftime("%d-%m-%Y")
    
    print(f"[INFO] Fetching BULK deals from {start_date_str} to {end_date_str}...")
    bulk_df = None
    try:
        bulk_df = capital_market.bulk_deal_data(start_date_str, end_date_str)
    except Exception as e:
        print(f"  -> BULK deals range error: {e}, trying period='1M' fallback...")
    if bulk_df is None or bulk_df.empty:
        try:
            bulk_df = capital_market.bulk_deal_data(period="1M")
        except Exception as e:
            print(f"  -> BULK deals period='1M' fallback error: {e}")
    if bulk_df is not None and not bulk_df.empty:
        inserted = parse_and_save(conn, bulk_df, "BULK")
        print(f"  -> BULK deals inserted: {inserted}")
        total_inserted += inserted
        
    print(f"[INFO] Fetching BLOCK deals from {start_date_str} to {end_date_str}...")
    block_df = None
    try:
        block_df = capital_market.block_deals_data(start_date_str, end_date_str)
    except Exception as e:
        print(f"  -> BLOCK deals range error: {e}, trying period='1M' fallback...")
    if block_df is None or block_df.empty:
        try:
            block_df = capital_market.block_deals_data(period="1M")
        except Exception as e:
            print(f"  -> BLOCK deals period='1M' fallback error: {e}")
    if block_df is not None and not block_df.empty:
        inserted = parse_and_save(conn, block_df, "BLOCK")
        print(f"  -> BLOCK deals inserted: {inserted}")
        total_inserted += inserted

    # Mark checked dates so holidays / 0-deal days are not queried indefinitely
    cur = conn.cursor()
    for d in missing_dates:
        if d < date.today() or (d == date.today() and datetime.now().hour >= 17):
            d_str = d.strftime("%Y-%m-%d")
            deals_cnt = cur.execute("SELECT COUNT(*) FROM bulk_block_deals WHERE deal_date = ?", (d_str,)).fetchone()[0]
            cur.execute("INSERT OR REPLACE INTO deals_checked_dates (deal_date, deals_found) VALUES (?, ?)", (d_str, deals_cnt))
    conn.commit()

    conn.close()
    print(f"\\n{'='*60}")
    print(f"  Done: Scraped missing dates. Total new rows inserted: {total_inserted}")
    print(f"{'='*60}\\n")

if __name__ == "__main__":
    main()
