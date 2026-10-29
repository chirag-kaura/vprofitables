"""
core/tools/options_microstructure_tool.py
=========================================
Options Microstructure & Institutional Positioning Tool (Scenario 12).
Computes Call Wall vs Put Wall, Max Pain, PCR, and Participant OI (FII/DII/Pro/Client).
Renders interactive Call vs Put Wall ladder with strict Cash Equity risk rules.
"""

import os
import sqlite3
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "market_data_v2.db")

def _get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def get_options_microstructure(symbol: Optional[str] = "NIFTY") -> Dict[str, Any]:
    """
    Fetch options chain microstructure, PCR, Max Pain, and participant OI.
    Strictly Cash Equity risk management output.
    """
    sym = (symbol or "NIFTY").upper().strip()
    if sym in ("NIFTY 50", "NIFTY50"):
        sym = "NIFTY"
    elif sym in ("BANK NIFTY", "BANKNIFTY"):
        sym = "BANKNIFTY"

    conn = _get_conn()
    try:
        # 1. Fetch PCR Summary
        pcr_row = conn.execute("""
            SELECT symbol, trade_date, expiry_date, pcr, max_pain, atm_strike, spot_price, total_ce_oi, total_pe_oi
            FROM pcr_summary
            WHERE symbol = ?
            ORDER BY trade_date DESC LIMIT 1
        """, (sym,)).fetchone()

        if not pcr_row:
            # Fallback to NIFTY
            pcr_row = conn.execute("""
                SELECT symbol, trade_date, expiry_date, pcr, max_pain, atm_strike, spot_price, total_ce_oi, total_pe_oi
                FROM pcr_summary
                WHERE symbol = 'NIFTY'
                ORDER BY trade_date DESC LIMIT 1
            """).fetchone()

        # 2. Fetch Top Call Wall & Put Wall from option_chain_data
        ce_rows = conn.execute("""
            SELECT strike, oi, ltp, iv
            FROM option_chain_data
            WHERE symbol = ? AND option_type = 'CE' AND oi > 0
            ORDER BY oi DESC LIMIT 5
        """, (sym,)).fetchall()

        pe_rows = conn.execute("""
            SELECT strike, oi, ltp, iv
            FROM option_chain_data
            WHERE symbol = ? AND option_type = 'PE' AND oi > 0
            ORDER BY oi DESC LIMIT 5
        """, (sym,)).fetchall()

        # If empty for specific stock, try NIFTY
        if not ce_rows:
            ce_rows = conn.execute("""
                SELECT strike, oi, ltp, iv
                FROM option_chain_data
                WHERE symbol = 'NIFTY' AND option_type = 'CE' AND oi > 0
                ORDER BY oi DESC LIMIT 5
            """).fetchall()
            pe_rows = conn.execute("""
                SELECT strike, oi, ltp, iv
                FROM option_chain_data
                WHERE symbol = 'NIFTY' AND option_type = 'PE' AND oi > 0
                ORDER BY oi DESC LIMIT 5
            """).fetchall()

        # 3. Participant OI breakdown
        part_rows = conn.execute("""
            SELECT trade_date, client_type, future_index_long, future_index_short,
                   option_index_call_long, option_index_call_short, option_index_put_long, option_index_put_short
            FROM participant_oi
            ORDER BY trade_date DESC LIMIT 4
        """).fetchall()

        fii_stats = {}
        pro_stats = {}
        client_stats = {}

        for p in part_rows:
            ctype = (p["client_type"] or "").upper()
            net_fut = int(p["future_index_long"] or 0) - int(p["future_index_short"] or 0)
            net_call = int(p["option_index_call_long"] or 0) - int(p["option_index_call_short"] or 0)
            net_put = int(p["option_index_put_long"] or 0) - int(p["option_index_put_short"] or 0)
            info = {
                "net_futures": net_fut,
                "net_calls": net_call,
                "net_puts": net_put,
                "bias": "BULLISH" if net_fut > 0 else "BEARISH"
            }
            if "FII" in ctype:
                fii_stats = info
            elif "PRO" in ctype:
                pro_stats = info
            elif "CLIENT" in ctype:
                client_stats = info

        # Parse Call & Put Wall
        top_call_wall = float(ce_rows[0]["strike"]) if ce_rows else 0.0
        top_call_oi = int(ce_rows[0]["oi"]) if ce_rows else 0
        top_put_wall = float(pe_rows[0]["strike"]) if pe_rows else 0.0
        top_put_oi = int(pe_rows[0]["oi"]) if pe_rows else 0

        spot_px = float(pcr_row["spot_price"] or 0.0) if pcr_row else 0.0
        max_pain = float(pcr_row["max_pain"] or 0.0) if pcr_row else 0.0
        pcr_val = round(float(pcr_row["pcr"] or 0.0), 2) if pcr_row else 0.0

        # Construct strike ladder data for visual card (up to 5 strikes)
        strike_map = {}
        for r in ce_rows:
            stk = float(r["strike"])
            strike_map.setdefault(stk, {"strike": stk, "ce_oi": 0, "pe_oi": 0})
            strike_map[stk]["ce_oi"] = int(r["oi"])
        for r in pe_rows:
            stk = float(r["strike"])
            strike_map.setdefault(stk, {"strike": stk, "ce_oi": 0, "pe_oi": 0})
            strike_map[stk]["pe_oi"] = int(r["oi"])

        sorted_strikes = sorted(strike_map.values(), key=lambda x: x["strike"])
        max_oi = max([max(s["ce_oi"], s["pe_oi"]) for s in sorted_strikes] or [1])

        ladder_items = []
        for s in sorted_strikes:
            ce_pct = min(100, int((s["ce_oi"] / max_oi) * 100))
            pe_pct = min(100, int((s["pe_oi"] / max_oi) * 100))
            ladder_items.append({
                "strike": s["strike"],
                "ce_oi": s["ce_oi"],
                "pe_oi": s["pe_oi"],
                "ce_bar_pct": ce_pct,
                "pe_bar_pct": pe_pct,
                "is_call_wall": s["strike"] == top_call_wall,
                "is_put_wall": s["strike"] == top_put_wall,
                "is_atm": abs(s["strike"] - spot_px) <= (spot_px * 0.01) if spot_px > 0 else False
            })

        return {
            "symbol": sym,
            "spot_price": spot_px,
            "max_pain": max_pain,
            "pcr": pcr_val,
            "call_wall": top_call_wall,
            "call_wall_oi": top_call_oi,
            "put_wall": top_put_wall,
            "put_wall_oi": top_put_oi,
            "ladder": ladder_items,
            "fii": fii_stats,
            "pro": pro_stats,
            "client": client_stats
        }
    except Exception as e:
        return {"error": str(e), "symbol": sym}
    finally:
        conn.close()

def format_options_microstructure_markdown(data: Dict[str, Any]) -> str:
    """Format options microstructure and render Call Wall vs Put Wall Visual Ladder."""
    if data.get("error"):
        return f"⚠️ **Options Microstructure Notice:** {data['error']}"

    sym = data.get("symbol", "NIFTY")
    spot = data.get("spot_price", 0.0)
    call_wall = data.get("call_wall", 0.0)
    put_wall = data.get("put_wall", 0.0)
    max_pain = data.get("max_pain", 0.0)
    pcr = data.get("pcr", 0.0)

    pcr_regime = "Bullish Oversold (Put Heavy)" if pcr > 1.2 else "Bearish Overbought (Call Heavy)" if pcr < 0.75 else "Neutral Balance"

    lines = [
        f"### 🎯 Options Microstructure & Expiry Pinning: {sym}",
        f"• **Spot Price:** ₹{spot:,.2f} | **PCR:** **{pcr}** ({pcr_regime}) | **Max Pain:** ₹{max_pain:,.2f}",
        f"• **Major Call Wall (Ceiling Resistance):** **₹{call_wall:,.2f}** ({data.get('call_wall_oi', 0):,} contracts)",
        f"• **Major Put Wall (Floor Support):** **₹{put_wall:,.2f}** ({data.get('put_wall_oi', 0):,} contracts)",
        ""
    ]

    # Institutional Smart Money Positioning
    fii = data.get("fii", {})
    if fii:
        fii_fut = fii.get("net_futures", 0)
        fut_str = f"Net Long **+{fii_fut:,}**" if fii_fut > 0 else f"Net Short **{fii_fut:,}**"
        lines.append(f"#### 🏛️ Smart Money (FII / Pro) Positioning")
        lines.append(f"- **FII Index Futures:** {fut_str} contracts (`{fii.get('bias', 'NEUTRAL')}`)")
        if fii.get("net_calls") is not None:
            lines.append(f"- **FII Net Options:** Calls: {fii.get('net_calls', 0):+,} | Puts: {fii.get('net_puts', 0):+,}")
        lines.append("")

    # Visual HTML Call Wall vs Put Wall Ladder
    ladder = data.get("ladder", [])
    if ladder:
        lines.append("#### 📊 Call Wall vs. Put Wall Battleground")
        lines.append('<div class="vprof-options-ladder" style="background:#0f172a; border:1px solid #1e293b; border-radius:10px; padding:14px; margin:12px 0; font-family:monospace; font-size:12px;">')
        lines.append('<div style="display:flex; justify-content:space-between; margin-bottom:8px; font-weight:bold; color:#94a3b8; border-bottom:1px solid #334155; padding-bottom:6px;">')
        lines.append('  <span style="color:#ef4444; width:40%;">🔴 CALL OI (Resistance)</span>')
        lines.append('  <span style="text-align:center; width:20%; color:#f8fafc;">STRIKE</span>')
        lines.append('  <span style="text-align:right; color:#10b981; width:40%;">🟢 PUT OI (Support)</span>')
        lines.append('</div>')

        for item in ladder:
            stk = item["strike"]
            ce_w = item["ce_bar_pct"]
            pe_w = item["pe_bar_pct"]
            bg_stk = "#1e293b" if not item["is_atm"] else "#3b82f6"
            color_stk = "#f8fafc" if not item["is_atm"] else "#ffffff"
            tag = ""
            if item["is_call_wall"]:
                tag = ' <span style="font-size:9px; background:#ef4444; color:#fff; border-radius:3px; padding:1px 4px;">WALL</span>'
            elif item["is_put_wall"]:
                tag = ' <span style="font-size:9px; background:#10b981; color:#fff; border-radius:3px; padding:1px 4px;">FLOOR</span>'

            lines.append(f'''
<div style="display:flex; align-items:center; justify-content:space-between; margin:6px 0;">
  <div style="width:40%; display:flex; align-items:center; justify-content:flex-end;">
    <span style="font-size:10px; color:#fca5a5; margin-right:6px;">{item['ce_oi']:,}</span>
    <div style="background:#ef4444; height:10px; border-radius:2px 0 0 2px; width:{ce_w}%;"></div>
  </div>
  <div style="width:20%; text-align:center; background:{bg_stk}; color:{color_stk}; padding:2px 4px; border-radius:4px; font-weight:bold;">
    {stk:,.0f}{tag}
  </div>
  <div style="width:40%; display:flex; align-items:center;">
    <div style="background:#10b981; height:10px; border-radius:0 2px 2px 0; width:{pe_w}%;"></div>
    <span style="font-size:10px; color:#86efac; margin-left:6px;">{item['pe_oi']:,}</span>
  </div>
</div>
''')
        lines.append('</div>')
        lines.append("")

    # Strict Cash Equity Risk Rules (Scenario 12)
    lines.append("#### 🛡️ Cash Equity Hedging & Risk Rules (No Speculative Derivatives)")
    lines.append(f"1. **Tighten Trailing Stop-Loss:** Move trailing stop-losses up to the **20-EMA** on high-beta equity holdings.")
    lines.append(f"2. **Cap Near Call Wall:** Avoid chasing fresh breakouts directly into the **₹{call_wall:,.2f}** Call Wall without volume expansion.")
    lines.append(f"3. **Maintain Cash Buffer:** If FII index futures positioning remains net short, maintain a **20%–25% defensive cash buffer** to buy pullback continuation leaders at the **₹{put_wall:,.2f}** Put Wall.")

    return "\n".join(lines)
