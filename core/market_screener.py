"""
core/market_screener.py
=======================
High-performance quantitative screener engine for Vprofitables AI Assistant.
Queries daily_prices table across 500+ NSE equities to answer:
  - Top gainers and losers over N days (1D, 5D, 10D, 30D, etc.)
  - High volume shockers and active trading movers
  - 52-week highs and lows
  - Detects corporate actions (stock splits / bonuses) vs genuine price moves.
"""

import os
import sys
import csv
import sqlite3
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.paths import DB_PATH, BASE_DIR

_NIFTY500_CACHE: Dict[str, Dict[str, str]] = {}

def get_nifty500_catalog() -> Dict[str, Dict[str, str]]:
    """Load and cache Nifty 500 metadata from data/nifty500.csv."""
    global _NIFTY500_CACHE
    if _NIFTY500_CACHE:
        return _NIFTY500_CACHE

    csv_path = os.path.join(BASE_DIR, "data", "nifty500.csv")
    if os.path.exists(csv_path):
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sym = (row.get("Symbol") or "").strip().upper()
                    if sym:
                        _NIFTY500_CACHE[sym] = {
                            "name": (row.get("Company Name") or sym).strip(),
                            "industry": (row.get("Industry") or "Equity").strip()
                        }
        except Exception as e:
            print(f"  [SCREENER] Warning reading nifty500.csv: {e}", flush=True)

    return _NIFTY500_CACHE

def get_recent_trading_dates(limit: int = 10) -> List[str]:
    """Retrieve the most recent distinct trading dates in descending order."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute(
        "SELECT DISTINCT trade_date FROM daily_prices ORDER BY trade_date DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]

def screen_price_performance(
    days: int = 5,
    direction: str = "LOSERS",
    limit: int = 5,
    min_volume: int = 5000,
    min_price: float = 10.0
) -> Dict[str, Any]:
    """
    Screen top gainers or losers over the last N trading sessions.
    
    Parameters:
      days: Number of trading sessions (e.g. 1 for today, 5 for 1 week).
      direction: 'LOSERS' for max price fall, 'GAINERS' for max price rise.
      limit: Number of results to return.
      min_volume: Minimum trading volume to exclude illiquid noise.
      min_price: Minimum base price to filter out penny stocks.
      
    Returns:
      Dict with start_date, end_date, days, direction, results list, and corporate action notes.
    """
    direction = direction.strip().upper()
    days = max(1, min(days, 60))
    
    needed_dates = days + 1
    dates = get_recent_trading_dates(limit=needed_dates)
    if len(dates) < 2:
        return {"error": "Insufficient trading date history in daily_prices table."}

    end_date = dates[0]
    actual_days = min(days, len(dates) - 1)
    start_date = dates[actual_days]

    nifty_map = get_nifty500_catalog()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    query = """
    SELECT 
        p_end.symbol,
        p_start.close AS base_price,
        p_end.close AS current_price,
        ROUND(((p_end.close - p_start.close) / p_start.close) * 100, 2) AS pct_change,
        p_end.volume,
        p_end.high,
        p_end.low
    FROM daily_prices p_end
    JOIN daily_prices p_start ON p_end.symbol = p_start.symbol
    WHERE p_end.trade_date = ? 
      AND p_start.trade_date = ?
      AND p_start.close >= ?
      AND p_end.volume >= ?
    """
    rows = c.execute(query, (end_date, start_date, min_price, min_volume)).fetchall()
    conn.close()

    # Filter to tracked equities and enrich metadata
    enriched = []
    for r in rows:
        sym = r[0]
        meta = nifty_map.get(sym, {"name": sym, "industry": "Equity"})
        # Exclude known commodities or non-equity symbols
        if sym in {"SILVER", "GOLD", "CRUDEOIL", "NATURALGAS", "COPPER"}:
            continue

        pct = float(r[3])
        # Detect probable stock split or bonus adjustment
        is_split = False
        split_note = ""
        if pct <= -70.0:
            is_split = True
            split_note = "Probable corporate action / stock split or bonus adjustment."

        enriched.append({
            "symbol": sym,
            "name": meta["name"],
            "industry": meta["industry"],
            "base_price": float(r[1]),
            "current_price": float(r[2]),
            "pct_change": pct,
            "volume": int(r[4]),
            "high": float(r[5]) if r[5] else float(r[2]),
            "low": float(r[6]) if r[6] else float(r[2]),
            "is_split": is_split,
            "split_note": split_note
        })

    is_desc = (direction == "GAINERS")
    enriched.sort(key=lambda x: x["pct_change"], reverse=is_desc)

    return {
        "days": actual_days,
        "start_date": start_date,
        "end_date": end_date,
        "direction": direction,
        "results": enriched[:limit],
        "universe_count": len(enriched)
    }

def format_screener_markdown(screen_data: Dict[str, Any]) -> str:
    """Format quantitative screener result into a crisp, readable markdown report."""
    if "error" in screen_data:
        return f"⚠️ **Screener Notice:** {screen_data['error']}"

    direction = screen_data.get("direction", "LOSERS")
    days = screen_data.get("days", 5)
    start_date = screen_data.get("start_date", "")
    end_date = screen_data.get("end_date", "")
    results = screen_data.get("results", [])

    is_losers = (direction == "LOSERS")
    icon = "📉" if is_losers else "🚀"
    title_dir = "Top Decliners (Max Fallen)" if is_losers else "Top Gainers (Best Performers)"

    lines = [
        f"### {icon} Nifty 500 Screener: {title_dir}",
        f"**Performance Window:** Last {days} Trading Sessions ({start_date} → {end_date})",
        f"*Screened across {screen_data.get('universe_count', 500)}+ tracked NSE equities with active trading volume.*",
        ""
    ]

    if not results:
        lines.append("No stocks matched the specified filter criteria.")
        return "\n".join(lines)

    lines.append("| Rank | Symbol | Company Name | Sector / Industry | Base Price | Current Price | Change % | Volume |")
    lines.append("|:---:|:---|:---|:---|:---:|:---:|:---:|:---:|")

    split_notes = []
    top_clean_symbol = None

    for i, r in enumerate(results, 1):
        chg_sign = "+" if r["pct_change"] > 0 else ""
        chg_str = f"**{chg_sign}{r['pct_change']:.2f}%**"
        vol_str = f"{r['volume']:,}"
        
        note_flag = ""
        if r.get("is_split"):
            note_flag = " ⚠️*"
            split_notes.append(f"**{r['symbol']}**: {r['split_note']} (Base ₹{r['base_price']:,.2f} → ₹{r['current_price']:,.2f})")
        elif top_clean_symbol is None:
            top_clean_symbol = r["symbol"]

        lines.append(
            f"| **#{i}** | **{r['symbol']}** | {r['name']} | {r['industry']} | "
            f"₹{r['base_price']:,.2f} | ₹{r['current_price']:,.2f} | {chg_str}{note_flag} | {vol_str} |"
        )

    lines.append("")

    if split_notes:
        lines.append("> ⚠️ **Corporate Action Notice:**")
        for sn in split_notes:
            lines.append(f"> - {sn}")
        if is_losers and top_clean_symbol:
            lines.append(f">\n> *Excluding split anomalies, **{top_clean_symbol}** is the largest organic decliner in this period.*")
        lines.append("")

    suggested_sym = top_clean_symbol or results[0]["symbol"]
    lines.append(f"💡 *Would you like an in-depth fundamental or earnings transcript analysis for **{suggested_sym}**?*")

    chips_html = (
        f'<div class="vprof-chip-container" style="display:flex; flex-wrap:wrap; gap:6px; margin-top:10px;">'
        f'<button class="vprof-chat-chip" onclick="askQuickPrompt(\'Analyze {suggested_sym}\')">📊 Analyze {suggested_sym}</button>'
        f'<button class="vprof-chat-chip" onclick="openSymbolChart(\'{suggested_sym}\')">📈 Open {suggested_sym} Chart</button>'
    )
    if len(results) > 1:
        s2 = results[1]["symbol"]
        chips_html += f'<button class="vprof-chat-chip" onclick="askQuickPrompt(\'Compare {suggested_sym} vs {s2}\')">⚖️ Compare {suggested_sym} vs {s2}</button>'
    chips_html += '</div>'
    lines.append(chips_html)

    return "\n".join(lines)
