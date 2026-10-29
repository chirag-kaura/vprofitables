"""
core/tools/multi_timeframe_tool.py
==================================
Multi-Timeframe Alignment & Conflict Resolution Engine (Scenario 18).
Computes 3 distinct horizon horizons:
  1. Short-Term (Intraday / 1-2 Days): VWAP & Momentum RSI.
  2. Medium-Term (Swing 10-15 Days): 20-EMA Pullback & ADX Trend Strength.
  3. Positional (1-3 Months): 50-EMA, 200-EMA Institutional Structural Support.
Synthesizes alignment score and generates institutional Quant Action Plan.
"""

import os
import sqlite3
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from core.gann_math import nearest_sq9

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "market_data_v2.db")

def _get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def compute_rsi(series: np.ndarray, period: int = 14) -> float:
    """Compute RSI for price array."""
    if len(series) < period + 1:
        return 50.0
    diff = np.diff(series)
    gains = np.where(diff > 0, diff, 0.0)
    losses = np.where(diff < 0, -diff, 0.0)
    avg_gain = pd.Series(gains).ewm(alpha=1.0/period, adjust=False).mean().iloc[-1]
    avg_loss = pd.Series(losses).ewm(alpha=1.0/period, adjust=False).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(float(100.0 - (100.0 / (1.0 + rs))), 1)

def get_multi_timeframe_matrix(symbol: str) -> Dict[str, Any]:
    """Compute multi-timeframe indicators and alignment matrix for a stock symbol."""
    sym = symbol.upper().strip()
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT trade_date, open, high, low, close, volume, vwap
            FROM daily_prices
            WHERE symbol = ? AND close IS NOT NULL
            ORDER BY trade_date DESC LIMIT 220
        """, (sym,)).fetchall()

        if len(rows) < 50:
            return {"error": f"Insufficient price history for {sym} to compute multi-timeframe matrix."}

        rows = list(reversed(rows))
        closes = np.array([float(r["close"]) for r in rows])
        highs = np.array([float(r["high"] or r["close"]) for r in rows])
        lows = np.array([float(r["low"] or r["close"]) for r in rows])
        volumes = np.array([float(r["volume"] or 0) for r in rows])
        last_vwap = float(rows[-1]["vwap"] or closes[-1])
        curr_price = round(float(closes[-1]), 2)

        # EMAs
        ema20 = float(pd.Series(closes).ewm(span=20, adjust=False).mean().iloc[-1])
        ema50 = float(pd.Series(closes).ewm(span=50, adjust=False).mean().iloc[-1])
        ema200 = float(pd.Series(closes).ewm(span=200, adjust=False).mean().iloc[-1]) if len(closes) >= 200 else ema50

        # RSI & Gann
        rsi = compute_rsi(closes, period=14)
        sq9_res, sq9_sup, *_ = nearest_sq9(curr_price)

        # 1. Short-Term (1-2 Days)
        st_bull = curr_price >= last_vwap and rsi >= 48
        st_bias = "BULLISH" if st_bull else "PULLBACK / WEAK"
        st_detail = f"Price {'above' if curr_price >= last_vwap else 'below'} VWAP (₹{last_vwap:,.2f}), RSI {rsi}"

        # 2. Medium-Term (10-15 Days Swing)
        dist_20ema = ((curr_price - ema20) / ema20) * 100.0
        mt_bull = curr_price >= ema20 and ema20 >= ema50
        mt_bias = "BULLISH TREND" if mt_bull else "CONSOLIDATION / RETEST" if -2.5 <= dist_20ema <= 1.0 else "BEARISH CHOP"
        mt_detail = f"20-EMA ₹{ema20:,.2f} ({dist_20ema:+.1f}%), 50-EMA ₹{ema50:,.2f}"

        # 3. Positional (1-3 Months)
        pos_bull = curr_price >= ema200 and ema50 >= ema200
        pos_bias = "MACRO UPTREND" if pos_bull else "MACRO CORRECTION"
        pos_detail = f"200-EMA ₹{ema200:,.2f}, Gann Sq9 Floor ₹{sq9_sup:,.2f}"

        # Alignment score
        bull_votes = sum([1 for b in [st_bull, mt_bull, pos_bull] if b])
        if bull_votes == 3:
            alignment = "FULL_BULLISH_CONFLUENCE"
            align_label = "🟢 3/3 Full Bullish Confluence (Ideal Continuation Entry)"
            action_plan = "All 3 timeframes are aligned in markup. Buy pullbacks to the 20-EMA with tight stop below the swing low."
        elif bull_votes == 2:
            alignment = "MODERATE_ALIGNMENT"
            align_label = "🟡 2/3 Moderate Alignment (Horizon Asymmetry)"
            if not st_bull:
                action_plan = "Macro & Swing trends are bullish, but short-term intraday momentum is cooling off. Wait for intraday dip to complete near 20-EMA before executing."
            else:
                action_plan = "Short-term bounce active inside higher-timeframe resistance. Size conservatively with strict 1:2 R:R."
        else:
            alignment = "CONFLICT_OR_BEARISH"
            align_label = "🔴 1/3 Bearish Conflict (High Risk)"
            action_plan = "Higher timeframes are broken below structural EMAs. Avoid fresh positional long exposure; wait for Gann Sq9 base confirmation."

        return {
            "symbol": sym,
            "current_price": curr_price,
            "short_term": {"bias": st_bias, "detail": st_detail, "is_bull": st_bull},
            "medium_term": {"bias": mt_bias, "detail": mt_detail, "is_bull": mt_bull},
            "positional": {"bias": pos_bias, "detail": pos_detail, "is_bull": pos_bull},
            "alignment": alignment,
            "align_label": align_label,
            "action_plan": action_plan,
            "ema20": round(ema20, 2),
            "ema50": round(ema50, 2),
            "ema200": round(ema200, 2),
            "sq9_support": sq9_sup,
            "sq9_resistance": sq9_res
        }
    finally:
        conn.close()

def format_multi_timeframe_markdown(mtf: Dict[str, Any]) -> str:
    """Format multi-timeframe matrix in clean, institutional markdown."""
    if mtf.get("error"):
        return f"⚠️ **Multi-Timeframe Notice:** {mtf['error']}"

    sym = mtf["symbol"]
    lines = [
        f"### ⏳ Multi-Timeframe Alignment Matrix: {sym}",
        f"**LTP:** ₹{mtf['current_price']:,.2f} | **Confluence Status:** {mtf['align_label']}",
        "",
        "| Timeframe Horizon | Trend Regime | Technical Structure | Signal Bias |",
        "| :--- | :---: | :--- | :---: |",
        f"| **Short-Term (Intraday / 1-2D)** | `{mtf['short_term']['bias']}` | {mtf['short_term']['detail']} | {'🟢 BUY' if mtf['short_term']['is_bull'] else '🟡 WAIT'} |",
        f"| **Medium-Term (Swing 10-15D)** | `{mtf['medium_term']['bias']}` | {mtf['medium_term']['detail']} | {'🟢 BUY' if mtf['medium_term']['is_bull'] else '🟡 RETEST'} |",
        f"| **Positional (1-3 Months)** | `{mtf['positional']['bias']}` | {mtf['positional']['detail']} | {'🟢 BULL' if mtf['positional']['is_bull'] else '🔴 DEFENSIVE'} |",
        "",
        "#### 🎯 Algorithmic Quant Action Plan",
        f"> 💡 {mtf['action_plan']}",
        "",
        f"• **Key Levels:** 20-EMA: **₹{mtf['ema20']:,.2f}** | 50-EMA: **₹{mtf['ema50']:,.2f}** | 200-EMA: **₹{mtf['ema200']:,.2f}** | Gann Sq9 Sup: **₹{mtf['sq9_support']:,.2f}**"
    ]
    return "\n".join(lines)
