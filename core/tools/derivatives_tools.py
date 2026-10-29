"""
core/tools/derivatives_tools.py
==============================
Derivatives & Options Microstructure Tool Adapter.
Queries pcr_summary, option_chain_data, and participant_sentiment_summary.
Returns verified ToolResult with Call/Put walls, Max Pain, PCR, and FII positioning.
"""

import os
import sqlite3
import time
from typing import Optional, Dict, Any
from core.tools.contracts import ToolResult
from core.swarm.cache import ttl_cached, TTL_INTRADAY, TTL_DAILY_MATH

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "market_data_v2.db")

def _get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

@ttl_cached(ttl=TTL_INTRADAY, namespace="deriv_pcr")
def derivatives_pcr_maxpain(symbol: Optional[str] = "NIFTY") -> ToolResult:
    """
    Fetch Put-Call Ratio (PCR), Max Pain, ATM Strike, and top Call/Put resistance/support walls.
    """
    t0 = time.perf_counter()
    sym = (symbol or "NIFTY").upper().strip()
    if sym in ("NIFTY 50", "NIFTY50"):
        sym = "NIFTY"
    elif sym in ("BANK NIFTY", "BANKNIFTY"):
        sym = "BANKNIFTY"

    conn = _get_conn()
    try:
        # 1. Fetch PCR Summary
        pcr_row = conn.execute("""
            SELECT symbol, trade_date, expiry_date, pcr, max_pain, atm_strike, spot_price, total_ce_oi, total_pe_oi, iv_skew
            FROM pcr_summary
            WHERE symbol = ?
            ORDER BY trade_date DESC LIMIT 1
        """, (sym,)).fetchone()

        if not pcr_row:
            # Fallback to NIFTY
            pcr_row = conn.execute("""
                SELECT symbol, trade_date, expiry_date, pcr, max_pain, atm_strike, spot_price, total_ce_oi, total_pe_oi, iv_skew
                FROM pcr_summary
                ORDER BY trade_date DESC LIMIT 1
            """).fetchone()

        if not pcr_row:
            return ToolResult(
                domain="DERIVATIVES",
                symbol=sym,
                headline_metric="No derivatives data available",
                tabular_summary="*No options data found in pcr_summary table.*",
                execution_ms=int((time.perf_counter() - t0) * 1000),
                error=f"No options chain record for {sym}"
            )

        trade_date = pcr_row["trade_date"]
        pcr = float(pcr_row["pcr"] or 0.0)
        max_pain = float(pcr_row["max_pain"] or 0.0)
        atm_strike = float(pcr_row["atm_strike"] or 0.0)
        spot_price = float(pcr_row["spot_price"] or 0.0)
        total_ce = int(pcr_row["total_ce_oi"] or 0)
        total_pe = int(pcr_row["total_pe_oi"] or 0)
        iv_skew = float(pcr_row["iv_skew"] or 0.0)

        # 2. Top Call Wall (Resistance) & Put Wall (Support)
        ce_wall = conn.execute("""
            SELECT strike, oi, ltp FROM option_chain_data
            WHERE symbol = ? AND option_type = 'CE' AND oi > 0
            ORDER BY oi DESC LIMIT 1
        """, (sym,)).fetchone()

        pe_wall = conn.execute("""
            SELECT strike, oi, ltp FROM option_chain_data
            WHERE symbol = ? AND option_type = 'PE' AND oi > 0
            ORDER BY oi DESC LIMIT 1
        """, (sym,)).fetchone()

        call_wall_strike = float(ce_wall["strike"]) if ce_wall else 0.0
        call_wall_oi = int(ce_wall["oi"]) if ce_wall else 0
        put_wall_strike = float(pe_wall["strike"]) if pe_wall else 0.0
        put_wall_oi = int(pe_wall["oi"]) if pe_wall else 0

        # Qualitative interpretation
        if pcr > 1.3:
            bias = "Overbought / Bullish Momentum (Put writing aggressive)"
        elif pcr < 0.7:
            bias = "Oversold / Bearish Overhang (Call writing heavy)"
        else:
            bias = "Neutral / Balanced Expiry Range"

        headline = f"PCR: {pcr:.2f} ({bias}) | Max Pain: Rs. {max_pain:,.2f} | Spot: Rs. {spot_price:,.2f}"

        table_lines = [
            "| Metric | Level / Value | Institutional Context |",
            "| :--- | :--- | :--- |",
            f"| **Underlying Spot** | Rs. {spot_price:,.2f} | Current underlying benchmark |",
            f"| **PCR (OI)** | {pcr:.2f} | Total PE OI: {total_pe:,} vs CE OI: {total_ce:,} |",
            f"| **Max Pain Strike** | Rs. {max_pain:,.2f} | Expiry gravitating strike |",
            f"| **ATM Strike** | Rs. {atm_strike:,.2f} | At-the-money straddle anchor |",
            f"| **Call Wall (Resistance)** | Rs. {call_wall_strike:,.2f} | Open Interest: {call_wall_oi:,} contracts |",
            f"| **Put Wall (Support)** | Rs. {put_wall_strike:,.2f} | Open Interest: {put_wall_oi:,} contracts |",
            f"| **IV Skew** | {iv_skew:+.2f}% | OTM Put vs OTM Call volatility premium |"
        ]

        raw = {
            "symbol": sym,
            "trade_date": trade_date,
            "pcr": pcr,
            "max_pain": max_pain,
            "spot_price": spot_price,
            "atm_strike": atm_strike,
            "call_wall_strike": call_wall_strike,
            "call_wall_oi": call_wall_oi,
            "put_wall_strike": put_wall_strike,
            "put_wall_oi": put_wall_oi,
            "bias": bias
        }

        return ToolResult(
            domain="DERIVATIVES",
            symbol=sym,
            headline_metric=headline,
            tabular_summary="\n".join(table_lines),
            raw_data=raw,
            execution_ms=int((time.perf_counter() - t0) * 1000)
        )
    except Exception as e:
        return ToolResult(
            domain="DERIVATIVES",
            symbol=sym,
            headline_metric=f"Error querying derivatives for {sym}",
            tabular_summary=f"> Execution error: {e}",
            execution_ms=int((time.perf_counter() - t0) * 1000),
            error=str(e)
        )
    finally:
        conn.close()

@ttl_cached(ttl=TTL_DAILY_MATH, namespace="deriv_participant_oi")
def derivatives_participant_oi() -> ToolResult:
    """
    Fetch FII, Pro, Client, and DII net derivative positions and smart money sentiment bias.
    """
    t0 = time.perf_counter()
    conn = _get_conn()
    try:
        row = conn.execute("""
            SELECT trade_date, fii_net_index_futures, fii_index_long_pct, client_net_index_calls, client_net_index_puts,
                   pro_net_index_calls, smart_money_bias, reversal_setup
            FROM participant_sentiment_summary
            ORDER BY trade_date DESC LIMIT 1
        """).fetchone()

        if not row:
            return ToolResult(
                domain="DERIVATIVES",
                headline_metric="Participant OI data unavailable",
                tabular_summary="*No participant OI records found in participant_sentiment_summary.*",
                execution_ms=int((time.perf_counter() - t0) * 1000),
                error="No participant OI records"
            )

        trade_date = row["trade_date"]
        fii_long_pct = float(row["fii_index_long_pct"] or 0.0)
        fii_net_fut = int(row["fii_net_index_futures"] or 0)
        smart_money_bias = row["smart_money_bias"] or "NEUTRAL"
        reversal_setup = row["reversal_setup"] or "NONE"

        headline = f"FII Index Futures Long: {fii_long_pct:.1f}% | Smart Money Bias: {smart_money_bias} (Date: {trade_date})"

        table_lines = [
            "| Participant Category | Net Position / Bias | Regime Interpretation |",
            "| :--- | :--- | :--- |",
            f"| **FII Index Long Ratio** | {fii_long_pct:.1f}% | Historical Mean: 50%. Above 65% is overleveraged long |",
            f"| **FII Net Index Futures** | {fii_net_fut:+,} contracts | Institutional directional commitment |",
            f"| **Pro Desks Net Calls** | {int(row['pro_net_index_calls'] or 0):+,} contracts | Proprietary option writing flow |",
            f"| **Retail / Client Net Puts** | {int(row['client_net_index_puts'] or 0):+,} contracts | Retail hedge / speculative exposure |",
            f"| **Smart Money Bias** | **{smart_money_bias}** | Institutional positioning composite |",
            f"| **Reversal Setup** | {reversal_setup} | Extreme skew trap warning |"
        ]

        raw = {
            "trade_date": trade_date,
            "fii_long_pct": fii_long_pct,
            "fii_net_futures": fii_net_fut,
            "smart_money_bias": smart_money_bias,
            "reversal_setup": reversal_setup
        }

        return ToolResult(
            domain="DERIVATIVES",
            symbol="MARKET_WIDE",
            headline_metric=headline,
            tabular_summary="\n".join(table_lines),
            raw_data=raw,
            execution_ms=int((time.perf_counter() - t0) * 1000)
        )
    except Exception as e:
        return ToolResult(
            domain="DERIVATIVES",
            headline_metric="Error fetching participant OI",
            tabular_summary=f"> Execution error: {e}",
            execution_ms=int((time.perf_counter() - t0) * 1000),
            error=str(e)
        )
    finally:
        conn.close()
