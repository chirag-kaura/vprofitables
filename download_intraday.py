"""
download_intraday.py — Historical Intraday (5m & 15m) Downloader
=================================================================
Downloads historical 5m and 15m intraday OHLCV candles from Yahoo Finance
and stores them in market_data_v2.db for exact reversal time and price detection.

USAGE:
  python download_intraday.py --symbols NIFTY50 BANKNIFTY RELIANCE TCS HDFCBANK
  python download_intraday.py --test            # downloads key 20 liquid leaders (5m & 15m)
  python download_intraday.py --interval 5m     # 5m only
  python download_intraday.py --interval 15m    # 15m only
"""

import os
import sys
import time
import random
import argparse
import sqlite3
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "market_data_v2.db")

sys.path.insert(0, BASE_DIR)
from data.instruments import ALL_INSTRUMENTS

KEY_SYMBOLS = [
    "NIFTY50", "BANKNIFTY", "RELIANCE", "TCS", "HDFCBANK",
    "ICICIBANK", "SBIN", "INFY", "BHARTIARTL", "ITC",
    "AXISBANK", "KOTAKBANK", "LT", "TATASTEEL", "MARUTI",
    "BAJFINANCE", "TATAMOTORS", "SUNPHARMA", "NTPC", "ONGC"
]

def init_intraday_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS intraday_prices (
            symbol        TEXT NOT NULL,
            interval      TEXT NOT NULL,
            candle_time   TEXT NOT NULL,
            open          REAL NOT NULL,
            high          REAL NOT NULL,
            low           REAL NOT NULL,
            close         REAL NOT NULL,
            volume        INTEGER DEFAULT 0,
            vwap          REAL,
            fetched_at    TEXT DEFAULT (datetime('now','localtime')),
            PRIMARY KEY (symbol, interval, candle_time)
        )
    """)
    conn.commit()

TICKER_FALLBACKS = {
    "TATAMOTORS.NS": ["TMPV.NS", "TMCV.NS"],
    "TMPV.NS": ["TATAMOTORS.NS", "TMCV.NS"],
}

def download_symbol_intraday(
    conn: sqlite3.Connection,
    symbol: str,
    interval: str = "5m",
    period: str = "60d",
    max_time: str = None,
    force: bool = False
) -> int:
    inst = ALL_INSTRUMENTS.get(symbol)
    if not inst:
        print(f"  [WARN] Unknown symbol: {symbol}", flush=True)
        return 0

    # ── Incremental Lookback Optimization ───────────────────────────────────
    # If symbol already has recent bars, avoid requesting 60 full days.
    effective_period = period
    if not force:
        if max_time is None:
            r = conn.execute(
                "SELECT MAX(candle_time) FROM intraday_prices WHERE symbol=? AND interval=?",
                (symbol, interval)
            ).fetchone()
            max_time = r[0] if r and r[0] else None

        if max_time:
            try:
                last_dt = datetime.strptime(max_time[:10], "%Y-%m-%d").date()
                today_dt = datetime.now().date()
                days_behind = (today_dt - last_dt).days

                # If current session is already captured, skip download entirely
                now_str = datetime.now().strftime("%H:%M:%S")
                market_closed = now_str >= "15:30:00"
                if days_behind == 0 and (max_time[11:16] >= "15:25" or not market_closed):
                    return 0

                if days_behind <= 4:
                    effective_period = "5d"
                elif days_behind <= 25:
                    effective_period = "1mo"
                else:
                    effective_period = "60d"
            except Exception:
                effective_period = period

    yf_sym = inst.yfinance_symbol
    candidates = [yf_sym] + [alt for alt in TICKER_FALLBACKS.get(yf_sym, []) if alt != yf_sym]

    df = None
    for cand in candidates:
        try:
            df = yf.download(cand, period=effective_period, interval=interval, progress=False)
            if df is not None and not df.empty:
                break
        except Exception:
            continue

    if df is None or df.empty:
        return 0

    try:
        # Handle yfinance MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.reset_index()
        time_col = "Datetime" if "Datetime" in df.columns else "Date"
        if time_col not in df.columns:
            return 0

        # Convert timestamp to clean IST string 'YYYY-MM-DD HH:MM:SS'
        records = []
        for _, row in df.iterrows():
            ts = row[time_col]
            if hasattr(ts, "strftime"):
                t_str = ts.strftime("%Y-%m-%d %H:%M:%S")
            else:
                t_str = str(ts)[:19]

            o = float(row.get("Open", 0.0) or 0.0)
            h = float(row.get("High", 0.0) or 0.0)
            l = float(row.get("Low", 0.0) or 0.0)
            c = float(row.get("Close", 0.0) or 0.0)
            v = int(row.get("Volume", 0) or 0)
            if c <= 0:
                continue

            # Typical price for bar VWAP
            typ = (h + l + c) / 3.0
            records.append((symbol, interval, t_str, o, h, l, c, v, typ))

        if not records:
            return 0

        # Compute intraday VWAP partitioned by date (VWAP strictly resets each day)
        df_rec = pd.DataFrame(records, columns=["symbol", "interval", "candle_time", "open", "high", "low", "close", "volume", "typ"])
        df_rec["date"] = df_rec["candle_time"].str[:10]

        df_rec["pv"] = df_rec["typ"] * df_rec["volume"]
        df_rec["cum_pv"] = df_rec.groupby("date")["pv"].cumsum()
        df_rec["cum_v"] = df_rec.groupby("date")["volume"].cumsum()
        df_rec["vwap"] = np.where(df_rec["cum_v"] > 0, df_rec["cum_pv"] / df_rec["cum_v"], df_rec["close"])
        df_rec["vwap"] = df_rec["vwap"].round(2)

        # In incremental mode, filter out candles that are already present in DB
        if max_time and not force:
            df_rec = df_rec[df_rec["candle_time"] > max_time]
            if df_rec.empty:
                return 0

        insert_rows = []
        for _, r in df_rec.iterrows():
            insert_rows.append((
                r["symbol"], r["interval"], r["candle_time"],
                r["open"], r["high"], r["low"], r["close"],
                r["volume"], r["vwap"]
            ))

        initial_changes = conn.total_changes
        for attempt in range(5):
            try:
                conn.executemany("""
                    INSERT OR REPLACE INTO intraday_prices
                        (symbol, interval, candle_time, open, high, low, close, volume, vwap)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, insert_rows)
                conn.commit()
                break
            except sqlite3.OperationalError as oe:
                if "locked" in str(oe).lower() and attempt < 4:
                    time.sleep(0.5 * (attempt + 1) + random.uniform(0.1, 0.4))
                else:
                    raise oe

        return conn.total_changes - initial_changes

    except Exception as e:
        print(f"  [ERROR] {symbol} ({interval}): {e}", flush=True)
        return 0

from concurrent.futures import ThreadPoolExecutor, as_completed

def worker_download(sym: str, intervals: list, period: str, max_times: dict = None, force: bool = False) -> tuple:
    # Each thread opens its own SQLite connection to prevent cross-thread lock
    c = sqlite3.connect(DB_PATH, timeout=60)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    c.execute("PRAGMA busy_timeout=60000")
    bars_saved = 0
    for iv in intervals:
        m_time = max_times.get((sym, iv)) if max_times else None
        n = download_symbol_intraday(c, sym, interval=iv, period=period, max_time=m_time, force=force)
        bars_saved += n
    c.close()
    return sym, bars_saved

def main():
    parser = argparse.ArgumentParser(description="Download historical intraday 5m & 15m data for GANN-ASTRO")
    parser.add_argument("--symbols", nargs="+", help="Specific symbols to download (e.g. NIFTY50 BANKNIFTY RELIANCE)")
    parser.add_argument("--all", action="store_true", help="Download for ALL 511 instruments")
    parser.add_argument("--test", action="store_true", help="Download top 20 core F&O liquid leaders")
    parser.add_argument("--interval", type=str, default="both", choices=["5m", "15m", "both"], help="Candle interval")
    parser.add_argument("--period", type=str, default="60d", help="Lookback period (e.g. 60d)")
    parser.add_argument("--incremental", action="store_true", default=True, help="Incremental mode: only fetch new bars since latest stored candle (default: True)")
    parser.add_argument("--force", action="store_true", help="Force full 60d re-download from scratch, ignoring existing bars")
    parser.add_argument("--workers", type=int, default=6, help="Concurrent download threads")
    args = parser.parse_args()

    if args.all:
        symbols = list(ALL_INSTRUMENTS.keys())
    elif args.symbols:
        symbols = args.symbols
    else:
        symbols = KEY_SYMBOLS

    intervals = ["5m", "15m"] if args.interval == "both" else [args.interval]

    mode_str = "FORCE FULL RE-DOWNLOAD" if args.force else "INCREMENTAL TOP-UP (Smart Lookback)"
    print("=" * 60)
    print(f"  GANN-ASTRO Intraday Downloader [{mode_str}]")
    print(f"  Total Instruments: {len(symbols)} | Intervals: {', '.join(intervals)} | Threads: {args.workers}")
    print("=" * 60)

    # Initialize table with primary connection
    init_conn = sqlite3.connect(DB_PATH, timeout=30)
    init_conn.execute("PRAGMA journal_mode=WAL")
    init_intraday_table(init_conn)

    # Pre-cache latest stored candle times across all symbols in ~5ms
    latest_timestamps = {}
    if not args.force:
        try:
            cur = init_conn.cursor()
            cur.execute("SELECT symbol, interval, MAX(candle_time) FROM intraday_prices GROUP BY symbol, interval")
            for r in cur.fetchall():
                latest_timestamps[(r[0], r[1])] = r[2]
            print(f"  [INFO] Pre-cached {len(latest_timestamps)} existing series timestamps for smart top-up.")
        except Exception as _e:
            print(f"  [WARN] Failed to pre-cache timestamps: {_e}")
    init_conn.close()

    total_bars = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(worker_download, sym, intervals, args.period, latest_timestamps, args.force): sym
            for sym in symbols
        }
        completed = 0
        for future in as_completed(futures):
            completed += 1
            sym, count = future.result()
            total_bars += count
            if count > 0 or completed % 25 == 0 or completed == len(symbols):
                print(f"  [{completed:3d}/{len(symbols):3d}] {sym:14s} -> {count:,} bars saved (Total: {total_bars:,})", flush=True)

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"  Intraday Download Completed in {elapsed:.1f}s ({elapsed/60:.1f} min)!")
    print(f"  Total New Intraday Bars Saved across {len(symbols)} symbols: {total_bars:,}")
    print("=" * 60)

if __name__ == "__main__":
    main()
