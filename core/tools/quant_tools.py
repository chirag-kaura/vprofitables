"""
core/tools/quant_tools.py
========================
Quantitative & Mathematical Engine Tool Adapter.
Integrates:
  1. W.D. Gann Square of 9 Geometry, Angles, and Cardinal/Ordinal Rotations.
  2. Richard Wyckoff Accumulation/Distribution Phases, Volatility Compression, and Institutional Hedge Fund Levels.
"""

import os
import sqlite3
import time
from typing import Optional, Dict, Any, List
from core.tools.contracts import ToolResult
from core.gann_math import nearest_sq9, sq9_levels
from core.wyckoff_engine import wyckoff_phase, accumulation_score, volatility_compression, hedge_fund_levels
from core.swarm.cache import ttl_cached, TTL_DAILY_MATH

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "market_data_v2.db")

def _get_price_history(symbol: str, limit: int = 100):
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT trade_date, open, high, low, close, volume, vwap
            FROM daily_prices
            WHERE symbol = ? AND close IS NOT NULL
            ORDER BY trade_date DESC LIMIT ?
        """, (symbol, limit)).fetchall()
        return list(reversed(rows))
    finally:
        conn.close()

@ttl_cached(ttl=TTL_DAILY_MATH, namespace="quant_gann")
def quant_gann_sq9(symbol: str) -> ToolResult:
    """
    Compute Gann Square of 9 cardinal and ordinal price levels from current closing price.
    Calculates immediate Square of 9 Support, Resistance, and 45°, 90°, 180°, 270°, 360° rotation levels.
    """
    t0 = time.perf_counter()
    sym = symbol.upper().strip()
    history = _get_price_history(sym, limit=5)
    if not history:
        return ToolResult(
            domain="QUANT_GANN",
            symbol=sym,
            headline_metric=f"No price history found for {sym}",
            tabular_summary=f"*Could not compute Gann Square of 9: no price data for {sym}.*",
            execution_ms=int((time.perf_counter() - t0) * 1000),
            error=f"No price history for {sym}"
        )

    latest = history[-1]
    curr_px = float(latest["close"])
    trade_date = latest["trade_date"]

    # 1. Nearest Support & Resistance from Sq9
    sup, res, s_deg, r_deg = nearest_sq9(curr_px)
    sup_dist = ((sup - curr_px) / curr_px) * 100
    res_dist = ((res - curr_px) / curr_px) * 100

    # 2. Key Multi-Rotation Levels
    levels = sq9_levels(curr_px, n=4)

    table_lines = [
        f"| Rotation Angle | Support Level (Rs.) | Distance % | Resistance Level (Rs.) | Distance % |",
        f"| :--- | :--- | :--- | :--- | :--- |"
    ]

    raw_levels = []
    for lvl in levels:
        table_lines.append(f"| **{lvl.rotation} ({lvl.degrees} deg)** | Rs. {lvl.below:,.2f} | {lvl.below_pct:+.2f}% | Rs. {lvl.above:,.2f} | {lvl.above_pct:+.2f}% |")
        raw_levels.append({
            "rotation": lvl.rotation,
            "degrees": lvl.degrees,
            "support": round(lvl.below, 2),
            "resistance": round(lvl.above, 2),
            "support_pct": round(lvl.below_pct, 2),
            "resistance_pct": round(lvl.above_pct, 2)
        })

    headline = f"Gann Sq9 Anchor: Rs. {curr_px:,.2f} (Date: {trade_date}) | Nearest Support: Rs. {sup:,.2f} ({sup_dist:+.2f}%) | Resistance: Rs. {res:,.2f} ({res_dist:+.2f}%)"

    raw = {
        "symbol": sym,
        "current_price": curr_px,
        "trade_date": trade_date,
        "nearest_support": round(sup, 2),
        "nearest_resistance": round(res, 2),
        "support_degrees": s_deg,
        "resistance_degrees": r_deg,
        "levels": raw_levels
    }

    return ToolResult(
        domain="QUANT_GANN",
        symbol=sym,
        headline_metric=headline,
        tabular_summary="\n".join(table_lines),
        raw_data=raw,
        execution_ms=int((time.perf_counter() - t0) * 1000)
    )

@ttl_cached(ttl=TTL_DAILY_MATH, namespace="quant_wyckoff")
def quant_wyckoff_structure(symbol: str) -> ToolResult:
    """
    Evaluate Wyckoff market structure, accumulation/distribution phase (Phase A to E),
    spring/upthrust detection, and institutional volatility compression.
    """
    t0 = time.perf_counter()
    sym = symbol.upper().strip()
    history = _get_price_history(sym, limit=80)
    if len(history) < 30:
        return ToolResult(
            domain="WYCKOFF",
            symbol=sym,
            headline_metric=f"Insufficient candle history for Wyckoff analysis ({len(history)} candles)",
            tabular_summary=f"*Wyckoff market structure analysis requires at least 30 candles.*",
            execution_ms=int((time.perf_counter() - t0) * 1000),
            error=f"Insufficient history ({len(history)})"
        )

    closes = [float(r["close"]) for r in history]
    highs = [float(r["high"] or r["close"]) for r in history]
    lows = [float(r["low"] or r["close"]) for r in history]
    volumes = [float(r["volume"] or 0) for r in history]
    curr_px = closes[-1]

    # 1. Wyckoff Phase
    phase_res = wyckoff_phase(closes, highs, lows, volumes)
    phase_name = phase_res.get("phase", "UNCERTAIN")
    phase_detail = phase_res.get("detail", "")
    bias = phase_res.get("bias", "NEUTRAL")

    # 2. Accumulation Score
    acc_res = accumulation_score(closes, highs, lows, volumes)
    acc_score = acc_res.get("total_score", 0)

    # 3. Volatility Compression (Bollinger Bandwidth Percentile)
    sqz_res = volatility_compression(closes)
    is_compressed = sqz_res.get("compressed", False)
    bbw_pct = sqz_res.get("percentile", 50.0)

    # 4. Hedge Fund Liquidity Levels
    hf_res = hedge_fund_levels(closes, highs, lows, volumes, curr_px)
    entry_lvl = hf_res.get("entry", curr_px)
    sl_lvl = hf_res.get("sl", curr_px * 0.95)
    t1_lvl = hf_res.get("t1", curr_px * 1.05)
    t2_lvl = hf_res.get("t2", curr_px * 1.10)

    headline = f"Wyckoff Phase: {phase_name} ({bias}) | Accumulation Score: {acc_score}/100 | Squeeze: {'ACTIVE' if is_compressed else 'NORMAL'}"

    table_lines = [
        "| Wyckoff Indicator | Status / Level | Institutional Interpretation |",
        "| :--- | :--- | :--- |",
        f"| **Market Phase** | **{phase_name}** | {phase_detail} |",
        f"| **Structural Bias** | {bias} | Smart money directional accumulation vs distribution |",
        f"| **Accumulation Quality** | {acc_score} / 100 | Volume spread analysis absorption score |",
        f"| **Volatility Squeeze** | {bbw_pct:.1f}th Percentile | {'High breakout probability compression' if is_compressed else 'Normal price dispersion'} |",
        f"| **Hedge Fund Entry** | Rs. {entry_lvl:,.2f} | Last accumulation higher low |",
        f"| **Structural Stop Loss** | Rs. {sl_lvl:,.2f} | Protected beneath spring shakeout low |",
        f"| **Wyckoff Target 1 (T1)**| Rs. {t1_lvl:,.2f} | Range high resistance target |",
        f"| **Wyckoff Target 2 (T2)**| Rs. {t2_lvl:,.2f} | Measured markup extension target |"
    ]

    raw = {
        "symbol": sym,
        "phase": phase_name,
        "detail": phase_detail,
        "bias": bias,
        "accumulation_score": acc_score,
        "compressed": is_compressed,
        "bbw_percentile": bbw_pct,
        "entry": entry_lvl,
        "sl": sl_lvl,
        "t1": t1_lvl,
        "t2": t2_lvl
    }

    return ToolResult(
        domain="WYCKOFF",
        symbol=sym,
        headline_metric=headline,
        tabular_summary="\n".join(table_lines),
        raw_data=raw,
        execution_ms=int((time.perf_counter() - t0) * 1000)
    )
