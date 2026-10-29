"""
download_participant_oi.py — NSE Participant-Wise Open Interest Pipeline
=========================================================================
Downloads daily participant-wise derivative open interest (Client, DII, FII, Pro)
from official NSE archives to identify Smart Money vs. Retail positioning.

USAGE:
  python download_participant_oi.py                # fetches missing days in last 60 days
  python download_participant_oi.py --days 180     # backfill last 180 days
  python download_participant_oi.py --date 2026-10-08
"""

import os
import sys
import time
import io
import argparse
import sqlite3
import requests
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "market_data_v2.db")

def init_participant_tables(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS participant_oi (
            trade_date              TEXT NOT NULL,
            client_type             TEXT NOT NULL,
            future_index_long       INTEGER DEFAULT 0,
            future_index_short      INTEGER DEFAULT 0,
            future_stock_long       INTEGER DEFAULT 0,
            future_stock_short      INTEGER DEFAULT 0,
            option_index_call_long  INTEGER DEFAULT 0,
            option_index_put_long   INTEGER DEFAULT 0,
            option_index_call_short INTEGER DEFAULT 0,
            option_index_put_short  INTEGER DEFAULT 0,
            option_stock_call_long  INTEGER DEFAULT 0,
            option_stock_put_long   INTEGER DEFAULT 0,
            option_stock_call_short INTEGER DEFAULT 0,
            option_stock_put_short  INTEGER DEFAULT 0,
            total_long              INTEGER DEFAULT 0,
            total_short             INTEGER DEFAULT 0,
            fetched_at              TEXT DEFAULT (datetime('now','localtime')),
            PRIMARY KEY (trade_date, client_type)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS participant_sentiment_summary (
            trade_date              TEXT PRIMARY KEY,
            fii_net_index_futures   INTEGER DEFAULT 0,
            fii_index_long_pct      REAL DEFAULT 50.0,
            client_net_index_calls  INTEGER DEFAULT 0,
            client_net_index_puts   INTEGER DEFAULT 0,
            pro_net_index_calls     INTEGER DEFAULT 0,
            smart_money_bias        TEXT DEFAULT 'NEUTRAL',
            reversal_setup          TEXT DEFAULT 'NONE',
            computed_at             TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS participant_oi_checked_dates (
            trade_date              TEXT PRIMARY KEY,
            status                  TEXT DEFAULT 'CHECKED',
            checked_at              TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()

def fetch_participant_csv(dt: date) -> Optional[pd.DataFrame]:
    d_str = dt.strftime("%d%m%Y")
    urls = [
        f"https://archives.nseindia.com/content/nsccl/fao_participant_oi_{d_str}.csv",
        f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_{d_str}.csv"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code == 200 and len(r.content) > 100:
                lines = r.text.splitlines()
                # Line 0 is often a title header, line 1 is the CSV header
                csv_lines = [l for l in lines if l.strip() and not l.startswith('""')]
                if not csv_lines:
                    continue
                df = pd.read_csv(io.StringIO("\n".join(csv_lines)))
                df.columns = [c.strip() for c in df.columns]
                return df
        except Exception:
            continue
    return None

def parse_and_save_participant_data(conn: sqlite3.Connection, dt: date, df: pd.DataFrame) -> bool:
    if df is None or df.empty:
        return False

    dt_str = dt.strftime("%Y-%m-%d")
    records = []
    summary_data = {}

    def clean_int(val):
        try:
            s = str(val).replace(",", "").strip()
            return int(float(s)) if s and s != "-" else 0
        except Exception:
            return 0

    for _, row in df.iterrows():
        c_type = str(row.get("Client Type", "")).strip()
        if not c_type or c_type.lower() == "nan":
            continue

        fi_long = clean_int(row.get("Future Index Long", 0))
        fi_short = clean_int(row.get("Future Index Short", 0))
        fs_long = clean_int(row.get("Future Stock Long", 0))
        fs_short = clean_int(row.get("Future Stock Short", 0))

        oic_long = clean_int(row.get("Option Index Call Long", 0))
        oip_long = clean_int(row.get("Option Index Put Long", 0))
        oic_short = clean_int(row.get("Option Index Call Short", 0))
        oip_short = clean_int(row.get("Option Index Put Short", 0))

        osc_long = clean_int(row.get("Option Stock Call Long", 0))
        osp_long = clean_int(row.get("Option Stock Put Long", 0))
        osc_short = clean_int(row.get("Option Stock Call Short", 0))
        osp_short = clean_int(row.get("Option Stock Put Short", 0))

        tot_long = clean_int(row.get("Total Long Contracts", 0))
        tot_short = clean_int(row.get("Total Short Contracts", 0))

        records.append((
            dt_str, c_type,
            fi_long, fi_short, fs_long, fs_short,
            oic_long, oip_long, oic_short, oip_short,
            osc_long, osp_long, osc_short, osp_short,
            tot_long, tot_short
        ))

        summary_data[c_type] = {
            "fi_long": fi_long, "fi_short": fi_short,
            "oic_long": oic_long, "oic_short": oic_short,
            "oip_long": oip_long, "oip_short": oip_short
        }

    if not records:
        return False

    conn.executemany("""
        INSERT OR REPLACE INTO participant_oi
            (trade_date, client_type,
             future_index_long, future_index_short, future_stock_long, future_stock_short,
             option_index_call_long, option_index_put_long, option_index_call_short, option_index_put_short,
             option_stock_call_long, option_stock_put_long, option_stock_call_short, option_stock_put_short,
             total_long, total_short)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, records)

    # Compute Smart Money vs Retail Indicators
    fii = summary_data.get("FII", {})
    client = summary_data.get("Client", {})
    pro = summary_data.get("Pro", {})

    fii_long = fii.get("fi_long", 0)
    fii_short = fii.get("fi_short", 0)
    fii_net_fut = fii_long - fii_short
    fii_long_pct = round((fii_long / (fii_long + fii_short) * 100), 2) if (fii_long + fii_short) > 0 else 50.0

    client_net_calls = client.get("oic_long", 0) - client.get("oic_short", 0)
    client_net_puts  = client.get("oip_long", 0) - client.get("oip_short", 0)
    pro_net_calls    = pro.get("oic_long", 0) - pro.get("oic_short", 0)

    # Classify Reversal Setups
    smart_bias = "NEUTRAL"
    reversal_setup = "NONE"

    if fii_long_pct <= 20.0 and client_net_puts > 150000:
        smart_bias = "EXTREME_BULLISH_CONTRARIAN"
        reversal_setup = "CAPITULATION_BOTTOM_REVERSAL"
    elif fii_long_pct <= 25.0:
        smart_bias = "BULLISH_ACCUMULATION"
        reversal_setup = "SHORT_COVERING_POTENTIAL"
    elif fii_long_pct >= 75.0 and client_net_calls > 150000:
        smart_bias = "EXTREME_BEARISH_CONTRARIAN"
        reversal_setup = "EXHAUSTION_TOP_REVERSAL"
    elif fii_long_pct >= 70.0:
        smart_bias = "BEARISH_DISTRIBUTION"
        reversal_setup = "LONG_UNWINDING_POTENTIAL"

    conn.execute("""
        INSERT OR REPLACE INTO participant_sentiment_summary
            (trade_date, fii_net_index_futures, fii_index_long_pct,
             client_net_index_calls, client_net_index_puts, pro_net_index_calls,
             smart_money_bias, reversal_setup)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (dt_str, fii_net_fut, fii_long_pct, client_net_calls, client_net_puts, pro_net_calls, smart_bias, reversal_setup))

    conn.commit()
    try:
        from core.tracker import handle_participant_oi_drip
        handle_participant_oi_drip(dt_str, fii_long_pct, conn=conn)
    except Exception as _e:
        pass
    return True

def backfill_participant_oi(conn: sqlite3.Connection, lookback_days: int = 60) -> int:
    # Find active NSE Equity trading days in daily_prices using NIFTY50 anchor
    rows = conn.execute("""
        SELECT DISTINCT trade_date FROM daily_prices
        WHERE symbol = 'NIFTY50'
          AND trade_date >= date('now', ?)
        ORDER BY trade_date ASC
    """, (f"-{lookback_days} days",)).fetchall()

    existing = {r[0] for r in conn.execute(
        "SELECT DISTINCT trade_date FROM participant_oi UNION SELECT trade_date FROM participant_oi_checked_dates"
    ).fetchall()}

    today = date.today()
    now_hour_min = datetime.now().hour * 60 + datetime.now().minute
    # NSE releases participant OI ~19:15 IST; before that, today's file will 404
    can_fetch_today = now_hour_min >= (19 * 60 + 15)

    target_dates = []
    for r in rows:
        d = datetime.strptime(r[0], "%Y-%m-%d").date()
        if r[0] in existing:
            continue
        if d.weekday() >= 5:  # Skip weekends
            continue
        if d == today and not can_fetch_today:
            continue
        target_dates.append(d)

    if not target_dates:
        print("  [INFO] Participant OI is already up-to-date!", flush=True)
        return 0

    print(f"  [INFO] Found {len(target_dates)} missing trading days for Participant OI. Fetching from NSE...", flush=True)
    saved = 0
    for idx, d in enumerate(target_dates):
        df = fetch_participant_csv(d)
        d_str = d.strftime("%Y-%m-%d")
        if df is not None:
            ok = parse_and_save_participant_data(conn, d, df)
            if ok:
                saved += 1
                conn.execute("INSERT OR REPLACE INTO participant_oi_checked_dates (trade_date, status) VALUES (?, 'FOUND')", (d_str,))
                conn.commit()
                print(f"    [{idx+1}/{len(target_dates)}] {d_str}: Saved FII/DII/Client OI", flush=True)
        else:
            # If past date has no archive on NSE, mark as NO_ARCHIVE so we don't query 404 every day
            if d < today:
                conn.execute("INSERT OR REPLACE INTO participant_oi_checked_dates (trade_date, status) VALUES (?, 'NO_ARCHIVE')", (d_str,))
                conn.commit()
        time.sleep(0.4)
    return saved

def main():
    parser = argparse.ArgumentParser(description="Download NSE Participant-Wise Open Interest")
    parser.add_argument("--days", type=int, default=60, help="Days to check for missing participant OI")
    parser.add_argument("--date", type=str, help="Specific trade date (YYYY-MM-DD)")
    args = parser.parse_args()

    print("=" * 60)
    print("  NSE Participant-Wise Open Interest Downloader")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    init_participant_tables(conn)

    if args.date:
        d = datetime.strptime(args.date, "%Y-%m-%d").date()
        df = fetch_participant_csv(d)
        if df is not None:
            ok = parse_and_save_participant_data(conn, d, df)
            print(f"  Single Date {args.date}: {'SUCCESS' if ok else 'FAILED'}")
        else:
            print(f"  Single Date {args.date}: No data from NSE archives.")
    else:
        saved = backfill_participant_oi(conn, lookback_days=args.days)
        print(f"\n  Done: Backfilled {saved} trading days of Participant OI.")

    conn.close()
    print("=" * 60)

if __name__ == "__main__":
    main()
