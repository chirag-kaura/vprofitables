"""
download_corporate_actions.py — Historical Stock Splits & Dividends Downloader
=============================================================================
Fetches official historical stock splits and dividend distributions from Yahoo Finance
for all instruments. Essential for Gann Square of 9 scaling, historical price
reconstructions, and unadjusted level alignment.

USAGE:
  python download_corporate_actions.py
  python download_corporate_actions.py --symbols INFY TCS RELIANCE
"""

import os
import sys
import sqlite3
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "market_data_v2.db")

from data.instruments import ALL_INSTRUMENTS

def init_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS corporate_actions (
            symbol       TEXT NOT NULL,
            ex_date      TEXT NOT NULL,
            action_type  TEXT NOT NULL,
            value        REAL NOT NULL,
            fetched_at   TEXT DEFAULT (datetime('now', 'localtime')),
            PRIMARY KEY (symbol, ex_date, action_type)
        )
    """)
    conn.commit()

def fetch_symbol_actions(symbol: str, yf_sym: str) -> list:
    records = []
    try:
        t = yf.Ticker(yf_sym)
        splits = t.splits
        if splits is not None and not splits.empty:
            for dt, val in splits.items():
                if val and float(val) > 0:
                    d_str = dt.strftime("%Y-%m-%d")
                    records.append((symbol, d_str, "SPLIT", float(val)))

        divs = t.dividends
        if divs is not None and not divs.empty:
            for dt, val in divs.items():
                if val and float(val) > 0:
                    d_str = dt.strftime("%Y-%m-%d")
                    records.append((symbol, d_str, "DIVIDEND", float(val)))
    except Exception:
        pass
    return records

def main():
    parser = argparse.ArgumentParser(description="Download Corporate Actions (Splits & Dividends)")
    parser.add_argument("--symbols", nargs="+", help="Specific symbols to download")
    parser.add_argument("--workers", type=int, default=8, help="Parallel worker threads")
    args = parser.parse_args()

    print("=" * 60)
    print("  Corporate Actions Downloader (Splits & Dividends)")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    init_table(conn)

    if args.symbols:
        targets = {s: ALL_INSTRUMENTS[s] for s in args.symbols if s in ALL_INSTRUMENTS}
    else:
        # Equities only
        targets = {s: inst for s, inst in ALL_INSTRUMENTS.items() if inst.instrument_type == "EQUITY"}

    print(f"  Target instruments: {len(targets)} equities")
    total_actions = 0
    saved_symbols = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(fetch_symbol_actions, sym, inst.yfinance_symbol): sym for sym, inst in targets.items()}
        for i, future in enumerate(as_completed(futures)):
            sym = futures[future]
            try:
                actions = future.result()
                if actions:
                    conn.executemany("""
                        INSERT OR REPLACE INTO corporate_actions (symbol, ex_date, action_type, value)
                        VALUES (?, ?, ?, ?)
                    """, actions)
                    conn.commit()
                    total_actions += len(actions)
                    saved_symbols += 1
                if (i + 1) % 25 == 0 or (i + 1) == len(targets):
                    print(f"    [{i+1}/{len(targets)}] Processed... Total corporate actions saved: {total_actions}", flush=True)
            except Exception as e:
                print(f"    [ERR] {sym}: {e}")

    conn.close()
    print("=" * 60)
    print(f"  Corporate Actions Complete: {total_actions} records saved across {saved_symbols} equities.")
    print("=" * 60)

if __name__ == "__main__":
    main()
