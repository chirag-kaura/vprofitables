"""
core/ohlc_rag/tools.py
======================
Phase 3: Dedicated LangChain Tools for OHLC Quantitative Analytics.
Contains modular tools decorated with `@tool` for:
  - Exact quote lookup
  - Time-series candle history table
  - Technical stats (SMA20/50, 52-week High/Low, ATR, Volume spikes)
  - Head-to-head relative performance comparison
"""

import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from typing import Optional
from langchain_core.tools import tool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.ohlc_rag.chunker import DB_PATH
from core.market_screener import screen_price_performance, get_recent_trading_dates


@tool
def ohlc_calendar_dates(limit: int = 5) -> str:
    """
    Retrieves the most recent verified trading dates available in the local database.
    Use this when the user asks what dates data we have, yesterday's date, or recent trading calendar.
    """
    dates = get_recent_trading_dates(limit=max(1, min(limit, 30)))
    if not dates:
        return "No trading dates found in the local database."
    lines = [
        f"Verified Trading Dates in Database (Most recent {len(dates)} sessions):",
        f"- Latest Trading Date: **{dates[0]}**"
    ]
    for d in dates[1:]:
        lines.append(f"- Previous Session: {d}")
    return "\n".join(lines)


@tool
def ohlc_market_movers(direction: str = "losers", days: int = 5, limit: int = 5) -> str:
    """
    Screens the top market gainers or losers across all NSE equities in the database over the last N trading sessions.
    Use this when the user asks which stock fell most, gained most, biggest losers, or biggest gainers.
    """
    dir_clean = "LOSERS" if "LOSE" in direction.upper() or "FALL" in direction.upper() or "DROP" in direction.upper() else "GAINERS"
    res = screen_price_performance(days=days, direction=dir_clean, limit=limit)
    if res.get("error"):
        return f"Screener Error: {res.get('error')}"

    movers = res.get("results", [])
    if not movers:
        return f"No symbols found meeting the screener criteria over the last {days} trading days."

    start_d = res.get("start_date")
    end_d = res.get("end_date")
    verb = "Fell Most (Top Losers)" if dir_clean == "LOSERS" else "Gained Most (Top Gainers)"
    lines = [
        f"### Market Screener: Stocks that {verb} over last {days} trading sessions ({start_d} to {end_d}):",
        "| Rank | Symbol | Company Name | Start Price | Current Price | % Change | Volume |",
        "|---|---|---|---|---|---|---|"
    ]
    for idx, m in enumerate(movers, 1):
        lines.append(
            f"| {idx} | **{m['symbol']}** | {m.get('name', m['symbol'])} | Rs. {m['base_price']:.2f} | "
            f"Rs. {m['current_price']:.2f} | **{m['pct_change']:+.2f}%** | {m['volume']:,} |"
        )
    return "\n".join(lines)


@tool
def ohlc_quote_lookup(symbol: str) -> str:
    """
    Fetches the most recent trading session quote for a given stock symbol.
    Provides latest Open, High, Low, Close, Volume, and Change %.
    """
    sym = symbol.strip().upper()
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT symbol, trade_date, open, high, low, close, volume, change_pct, vwap
        FROM daily_prices
        WHERE symbol = ?
        ORDER BY trade_date DESC
        LIMIT 1
    """
    df = pd.read_sql_query(query, conn, params=(sym,))
    conn.close()

    if df.empty:
        return f"No daily OHLC price record found for symbol '{sym}'."

    row = df.iloc[0]
    trade_date = row["trade_date"]
    open_p = row["open"]
    high_p = row["high"]
    low_p = row["low"]
    close_p = row["close"]
    vol = row["volume"]
    chg = row["change_pct"]
    vwap = row.get("vwap")

    chg_str = f"{chg:+.2f}%" if pd.notna(chg) else "N/A"
    vwap_str = f"Rs. {vwap:.2f}" if pd.notna(vwap) else "N/A"
    vol_str = f"{int(vol):,}" if pd.notna(vol) else "N/A"

    return (
        f"Quote for {sym} as of {trade_date}:\n"
        f"- Close: Rs. {close_p:.2f} ({chg_str})\n"
        f"- Open: Rs. {open_p:.2f} | High: Rs. {high_p:.2f} | Low: Rs. {low_p:.2f}\n"
        f"- VWAP: {vwap_str} | Volume: {vol_str}"
    )


@tool
def ohlc_history_range(symbol: str, num_days: int = 10) -> str:
    """
    Retrieves the last N daily OHLC candles for a stock symbol as a structured table.
    Use this when the user requests historical prices, recent days' performance, or candle sequence.
    """
    sym = symbol.strip().upper()
    days = min(max(int(num_days), 1), 60)
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT trade_date, open, high, low, close, volume, change_pct
        FROM daily_prices
        WHERE symbol = ?
        ORDER BY trade_date DESC
        LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=(sym, days))
    conn.close()

    if df.empty:
        return f"No price history found for symbol '{sym}'."

    df = df.sort_values("trade_date").reset_index(drop=True)
    lines = [
        f"OHLC History for {sym} (Last {len(df)} sessions):",
        "| Date | Open | High | Low | Close | Chg% | Volume |",
        "|---|---|---|---|---|---|---|"
    ]
    for _, r in df.iterrows():
        c_pct = f"{r['change_pct']:+.2f}%" if pd.notna(r['change_pct']) else "-"
        vol_str = f"{int(r['volume']):,}" if pd.notna(r['volume']) else "-"
        lines.append(
            f"| {r['trade_date']} | Rs. {r['open']:.2f} | Rs. {r['high']:.2f} | "
            f"Rs. {r['low']:.2f} | Rs. {r['close']:.2f} | {c_pct} | {vol_str} |"
        )
    return "\n".join(lines)


@tool
def ohlc_technical_stats(symbol: str, lookback_days: int = 60) -> str:
    """
    Computes key quantitative moving averages (SMA 20, SMA 50), 52-Week High & Low,
    and 14-day Average True Range (ATR) for a given stock symbol.
    """
    sym = symbol.strip().upper()
    conn = sqlite3.connect(DB_PATH)
    
    # 52-week high & low query (approx 252 trading days)
    yr_query = """
        SELECT MAX(high) as yr_high, MIN(low) as yr_low
        FROM daily_prices
        WHERE symbol = ?
        ORDER BY trade_date DESC
        LIMIT 252
    """
    yr_df = pd.read_sql_query(yr_query, conn, params=(sym,))
    
    # History for moving averages
    hist_query = """
        SELECT trade_date, open, high, low, close, volume
        FROM daily_prices
        WHERE symbol = ?
        ORDER BY trade_date DESC
        LIMIT ?
    """
    df = pd.read_sql_query(hist_query, conn, params=(sym, max(lookback_days, 60)))
    conn.close()

    if df.empty:
        return f"Insufficient data to compute technical stats for '{sym}'."

    df = df.sort_values("trade_date").reset_index(drop=True)
    latest_close = float(df["close"].iloc[-1])
    
    # Moving Averages
    sma20 = float(df["close"].rolling(20).mean().iloc[-1]) if len(df) >= 20 else None
    sma50 = float(df["close"].rolling(50).mean().iloc[-1]) if len(df) >= 50 else None

    # ATR 14
    df["h_l"] = df["high"] - df["low"]
    df["h_pc"] = (df["high"] - df["close"].shift(1)).abs()
    df["l_pc"] = (df["low"] - df["close"].shift(1)).abs()
    df["tr"] = df[["h_l", "h_pc", "l_pc"]].max(axis=1)
    atr14 = float(df["tr"].rolling(14).mean().iloc[-1]) if len(df) >= 14 else None

    # 52W High / Low
    yr_high = yr_df["yr_high"].iloc[0] if not yr_df.empty and pd.notna(yr_df["yr_high"].iloc[0]) else None
    yr_low = yr_df["yr_low"].iloc[0] if not yr_df.empty and pd.notna(yr_df["yr_low"].iloc[0]) else None

    high_dist = f"{((latest_close - yr_high) / yr_high) * 100.0:+.2f}%" if yr_high else "N/A"
    low_dist = f"{((latest_close - yr_low) / yr_low) * 100.0:+.2f}%" if yr_low else "N/A"

    sma20_str = f"Rs. {sma20:.2f}" if sma20 else "N/A"
    sma50_str = f"Rs. {sma50:.2f}" if sma50 else "N/A"
    atr_str = f"Rs. {atr14:.2f} ({(atr14 / latest_close * 100.0):.2f}% of price)" if atr14 and latest_close > 0 else "N/A"

    # Moving average trend position
    trend_desc = "Above both SMA20 and SMA50 (Bullish alignment)" if (sma20 and sma50 and latest_close > sma20 > sma50) else \
                 "Below both SMA20 and SMA50 (Bearish alignment)" if (sma20 and sma50 and latest_close < sma20 < sma50) else \
                 "Mixed moving average alignment"

    return (
        f"Technical Quantitative Stats for {sym} (Latest Close: Rs. {latest_close:.2f}):\n"
        f"- SMA 20: {sma20_str} | SMA 50: {sma50_str}\n"
        f"- Moving Average Stance: {trend_desc}\n"
        f"- 14-Day ATR (Volatility): {atr_str}\n"
        f"- 52-Week High: Rs. {yr_high:.2f} ({high_dist} from current close)\n"
        f"- 52-Week Low: Rs. {yr_low:.2f} ({low_dist} from current close)"
    )


@tool
def ohlc_relative_performance(symbol_a: str, symbol_b: str, days: int = 30) -> str:
    """
    Compares the price return and performance of two stocks over the last N trading sessions.
    Example: Compare RELIANCE vs TCS over 30 days.
    """
    sym_a = symbol_a.strip().upper()
    sym_b = symbol_b.strip().upper()
    n_days = min(max(int(days), 5), 180)

    conn = sqlite3.connect(DB_PATH)
    q = """
        SELECT trade_date, close
        FROM daily_prices
        WHERE symbol = ?
        ORDER BY trade_date DESC
        LIMIT ?
    """
    df_a = pd.read_sql_query(q, conn, params=(sym_a, n_days))
    df_b = pd.read_sql_query(q, conn, params=(sym_b, n_days))
    conn.close()

    if df_a.empty or df_b.empty:
        return f"Unable to compare {sym_a} and {sym_b}: missing price data for one or both symbols."

    df_a = df_a.sort_values("trade_date").reset_index(drop=True)
    df_b = df_b.sort_values("trade_date").reset_index(drop=True)

    ret_a = ((df_a["close"].iloc[-1] - df_a["close"].iloc[0]) / df_a["close"].iloc[0]) * 100.0
    ret_b = ((df_b["close"].iloc[-1] - df_b["close"].iloc[0]) / df_b["close"].iloc[0]) * 100.0
    alpha = ret_a - ret_b

    winner = sym_a if ret_a > ret_b else sym_b

    return (
        f"Relative Performance ({n_days} sessions):\n"
        f"- {sym_a}: {ret_a:+.2f}% (from Rs. {df_a['close'].iloc[0]:.2f} to Rs. {df_a['close'].iloc[-1]:.2f})\n"
        f"- {sym_b}: {ret_b:+.2f}% (from Rs. {df_b['close'].iloc[0]:.2f} to Rs. {df_b['close'].iloc[-1]:.2f})\n"
        f"- Spread / Outperformance: {winner} outperformed by {abs(alpha):.2f}%."
    )


ALL_OHLC_TOOLS = [
    ohlc_calendar_dates,
    ohlc_market_movers,
    ohlc_quote_lookup,
    ohlc_history_range,
    ohlc_technical_stats,
    ohlc_relative_performance
]


if __name__ == "__main__":
    print("[*] Testing Phase 3 OHLC LangChain Tools...")
    print("\n--- Tool 1: Quote Lookup ---")
    print(ohlc_quote_lookup.invoke({"symbol": "RELIANCE"}))
    
    print("\n--- Tool 2: Technical Stats ---")
    print(ohlc_technical_stats.invoke({"symbol": "TCS", "lookback_days": 60}))
    
    print("\n--- Tool 3: Relative Performance ---")
    print(ohlc_relative_performance.invoke({"symbol_a": "RELIANCE", "symbol_b": "TCS", "days": 20}))
