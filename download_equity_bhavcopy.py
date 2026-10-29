import os
import sys
import io
import time
import random
import sqlite3
import logging
import argparse
from datetime import date, datetime, timedelta
import pandas as pd
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
DB_PATH = os.path.join(BASE_DIR, "market_data_v2.db")
LOG_FILE = os.path.join(BASE_DIR, "equity_bhavcopy.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("equity_bhavcopy")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

def new_session():
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.nseindia.com/",
    })
    # Warmup
    try:
        sess.get("https://www.nseindia.com/", timeout=10)
    except:
        pass
    return sess

def get_already_fetched(conn):
    try:
        rows = conn.execute("SELECT DISTINCT trade_date FROM daily_prices WHERE deliverable_qty IS NOT NULL").fetchall()
        return {r[0] for r in rows}
    except Exception:
        return set()

def fetch_equity_bhavcopy(sess, trade_date):
    # Try new URL format
    ddmmyyyy = trade_date.strftime("%d%m%Y")
    url = f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{ddmmyyyy}.csv"
    
    for attempt in range(3):
        try:
            r = sess.get(url, timeout=15)
            if r.status_code == 200 and len(r.content) > 1000:
                df = pd.read_csv(io.BytesIO(r.content), skipinitialspace=True)
                return df
            if r.status_code in (401, 403):
                sess = new_session()
                time.sleep(2)
                continue
            if r.status_code == 404:
                # Try alternative old URL if needed
                pass
        except Exception as e:
            log.warning(f"Error fetching {trade_date}: {e}")
            time.sleep(2)
    return None

def process_and_save(conn, df, trade_date):
    # Filter for EQ (Equities) series
    if "SERIES" not in df.columns:
        return 0
    df = df[df["SERIES"] == "EQ"].copy()
    
    df.columns = [c.strip().upper() for c in df.columns]
    
    td_str = trade_date.strftime("%Y-%m-%d")
    
    records = []
    # Columns expected: SYMBOL, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, CLOSE_PRICE, PREV_CLOSE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER
    for _, row in df.iterrows():
        sym = row.get("SYMBOL")
        if not sym:
            continue
        
        op = float(row.get("OPEN_PRICE", 0))
        hi = float(row.get("HIGH_PRICE", 0))
        lo = float(row.get("LOW_PRICE", 0))
        cl = float(row.get("CLOSE_PRICE", 0))
        prev_cl = float(row.get("PREV_CLOSE", 0))
        
        vol = int(row.get("TTL_TRD_QNTY", 0))
        deliv_qty = row.get("DELIV_QTY")
        deliv_qty = int(deliv_qty) if pd.notnull(deliv_qty) and str(deliv_qty).strip() != '-' else None
        deliv_pct = row.get("DELIV_PER")
        deliv_pct = float(deliv_pct) if pd.notnull(deliv_pct) and str(deliv_pct).strip() != '-' else None
        
        turnover = float(row.get("TURNOVER_LACS", 0)) * 100000 # in Rs
        vwap = turnover / vol if vol > 0 else cl
        
        change_pct = round((cl - prev_cl) / prev_cl * 100, 4) if prev_cl else None
        
        records.append((
            sym, td_str, op, hi, lo, cl, vol, change_pct, vwap, deliv_qty, deliv_pct
        ))
        
    if records:
        conn.executemany("""
            INSERT INTO daily_prices
                (symbol, trade_date, open, high, low, close, volume, change_pct, vwap, deliverable_qty, deliverable_pct, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,datetime('now','localtime'))
            ON CONFLICT(symbol, trade_date) DO UPDATE SET
                open=excluded.open,
                high=excluded.high,
                low=excluded.low,
                close=excluded.close,
                volume=excluded.volume,
                vwap=excluded.vwap,
                deliverable_qty=excluded.deliverable_qty,
                deliverable_pct=excluded.deliverable_pct,
                updated_at=excluded.updated_at
        """, records)
        conn.commit()
        try:
            from core.tracker import handle_delivery_spike_drip, get_active_trackers
            active_trackers = {r["symbol"].upper().strip() for r in get_active_trackers(conn=conn)}
            if active_trackers:
                for rec in records:
                    sym_rec = rec[0].upper().strip()
                    if sym_rec in active_trackers:
                        td_rec, vol_rec, deliv_qty_rec, deliv_pct_rec = rec[1], rec[6], rec[9], rec[10]
                        handle_delivery_spike_drip(sym_rec, td_rec, deliv_pct_rec, deliv_qty_rec, conn=conn)
        except Exception as _e:
            pass
    return len(records)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--incremental", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    
    # Try to add schema columns if they don't exist
    for col, ctype in [("vwap", "REAL"), ("deliverable_qty", "INTEGER"), ("deliverable_pct", "REAL")]:
        try:
            conn.execute(f"ALTER TABLE daily_prices ADD COLUMN {col} {ctype}")
        except sqlite3.OperationalError:
            pass
    conn.commit()

    already_done = get_already_fetched(conn)
    yesterday = date.today() - timedelta(days=1)
    
    if args.incremental:
        start_date = yesterday - timedelta(days=10)
    else:
        start_date = date(2023, 1, 1) # Full backfill start date
        
    all_days = []
    cur = start_date
    while cur <= yesterday:
        if cur.weekday() < 5:
            all_days.append(cur)
        cur += timedelta(days=1)
        
    work_days = [d for d in all_days if d.strftime("%Y-%m-%d") not in already_done]
    
    log.info(f"Equity Bhavcopy: {len(work_days)} days to fetch.")
    
    sess = new_session()
    
    for idx, d in enumerate(work_days):
        df = fetch_equity_bhavcopy(sess, d)
        if df is not None:
            saved = process_and_save(conn, df, d)
            log.info(f"[{idx+1}/{len(work_days)}] {d.strftime('%Y-%m-%d')}: Saved {saved} records.")
        else:
            log.warning(f"[{idx+1}/{len(work_days)}] {d.strftime('%Y-%m-%d')}: Failed or missing.")
        time.sleep(random.uniform(1.0, 2.0))
        
    conn.close()

if __name__ == "__main__":
    main()
