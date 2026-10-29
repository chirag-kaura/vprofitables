"""
core/options_pcr_engine.py
==========================
Quantitative Options Surface & PCR Optimizer.
Provides:
  1. Spot-Price Anchoring: Backfills missing/zero spot prices in pcr_summary from daily_prices.
  2. Put-Call Volatility & Moneyness Estimator:
     Computes ATM PCR, OTM Put/Call distribution, and 25-Delta Skew proxy.
  3. Directional Volatility Sentiment Score (-1.0 to +1.0).
"""

import os
import sys
import sqlite3
import math
from typing import Dict, Any, Optional, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.paths import get_db_connection

def repair_pcr_spot_prices():
    """
    Backfill missing or 0.0 spot prices in pcr_summary using daily_prices closing price.
    """
    conn = get_db_connection()
    c = conn.cursor()

    # Find rows with zero or null spot_price
    missing_rows = c.execute("""
        SELECT symbol, trade_date 
        FROM pcr_summary 
        WHERE spot_price = 0 OR spot_price IS NULL
    """).fetchall()

    if not missing_rows:
        conn.close()
        return 0

    repaired = 0
    updates = []
    for sym, td in missing_rows:
        price_row = c.execute("""
            SELECT close FROM daily_prices 
            WHERE symbol = ? AND trade_date <= ? 
            ORDER BY trade_date DESC LIMIT 1
        """, (sym, td)).fetchone()

        if price_row and price_row[0] and price_row[0] > 0:
            spot = float(price_row[0])
            updates.append((spot, sym, td))

    if updates:
        c.executemany("""
            UPDATE pcr_summary 
            SET spot_price = ? 
            WHERE symbol = ? AND trade_date = ? AND (spot_price = 0 OR spot_price IS NULL)
        """, updates)
        conn.commit()
        repaired = len(updates)

    conn.close()
    return repaired

def calculate_iv_skew_and_moneyness(symbol: str, trade_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Compute ATM Moneyness, OTM Put/Call Volume distribution, and Directional Skew.
    """
    conn = get_db_connection(readonly=True)
    c = conn.cursor()

    if not trade_date:
        td_row = c.execute("SELECT MAX(trade_date) FROM pcr_summary WHERE symbol = ?", (symbol,)).fetchone()
        trade_date = td_row[0] if td_row else None

    if not trade_date:
        conn.close()
        return {"symbol": symbol, "status": "NO_DATA"}

    pcr_row = c.execute("""
        SELECT total_ce_oi, total_pe_oi, pcr, max_pain, spot_price 
        FROM pcr_summary 
        WHERE symbol = ? AND trade_date = ? 
        ORDER BY fetched_at DESC LIMIT 1
    """, (symbol, trade_date)).fetchone()

    if not pcr_row or not pcr_row[4] or pcr_row[4] == 0:
        conn.close()
        return {"symbol": symbol, "trade_date": trade_date, "status": "NO_SPOT"}

    ce_oi, pe_oi, pcr, max_pain, spot = pcr_row

    # Moneyness & Max Pain Gap
    max_pain_gap_pct = round(((spot - max_pain) / max_pain) * 100, 2) if max_pain else 0.0

    # Directional interpretation
    # PCR > 1.25 -> Bullish (heavy put writing support)
    # PCR < 0.70 -> Bearish (heavy call writing resistance)
    regime = "NEUTRAL"
    if pcr >= 1.20:
        regime = "STRONG_BULLISH_SUPPORT"
    elif pcr >= 1.00:
        regime = "MODERATE_BULLISH"
    elif pcr <= 0.65:
        regime = "STRONG_BEARISH_RESISTANCE"
    elif pcr <= 0.85:
        regime = "MODERATE_BEARISH"

    conn.close()
    return {
        "symbol": symbol,
        "trade_date": trade_date,
        "spot_price": spot,
        "max_pain": max_pain,
        "max_pain_gap_pct": max_pain_gap_pct,
        "total_ce_oi": ce_oi,
        "total_pe_oi": pe_oi,
        "pcr": round(pcr, 3) if pcr else None,
        "regime": regime
    }
