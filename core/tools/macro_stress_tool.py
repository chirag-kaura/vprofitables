"""
core/tools/macro_stress_tool.py
===============================
Macro Stress-Testing & Shock Simulation Tool (Scenario 17).
Computes historical Beta vs NIFTY 50 for all open portfolio positions and
simulates index shocks (-3%, -5%, or -500 points) to quantify portfolio drawdown.
"""

import os
import sqlite3
import numpy as np
from typing import Dict, Any, List, Optional
from core.tools.portfolio_tool import fetch_portfolio_positions

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "market_data_v2.db")

def _get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def compute_stock_beta(symbol: str, conn: sqlite3.Connection, lookback_days: int = 60) -> float:
    """Compute historical Beta of an equity symbol against NIFTY50."""
    try:
        n_rows = conn.execute("""
            SELECT trade_date, close FROM daily_prices 
            WHERE symbol = 'NIFTY50' ORDER BY trade_date DESC LIMIT ?
        """, (lookback_days,)).fetchall()
        
        s_rows = conn.execute("""
            SELECT trade_date, close FROM daily_prices 
            WHERE symbol = ? ORDER BY trade_date DESC LIMIT ?
        """, (symbol, lookback_days)).fetchall()

        n_dict = {r["trade_date"]: float(r["close"]) for r in n_rows if r["close"]}
        s_dict = {r["trade_date"]: float(r["close"]) for r in s_rows if r["close"]}

        common_dates = sorted(set(n_dict.keys()).intersection(set(s_dict.keys())))
        if len(common_dates) < 15:
            return 1.0  # Default market beta

        n_closes = [n_dict[d] for d in common_dates]
        s_closes = [s_dict[d] for d in common_dates]

        n_ret = np.diff(n_closes) / n_closes[:-1]
        s_ret = np.diff(s_closes) / s_closes[:-1]

        cov = np.cov(s_ret, n_ret)[0, 1]
        var_n = np.var(n_ret)
        if var_n > 0:
            beta = float(cov / var_n)
            return round(max(0.2, min(3.0, beta)), 2)
        return 1.0
    except Exception:
        return 1.0

def simulate_macro_stress(user_id: int = 1, shock_pct: float = -3.0, shock_points: Optional[float] = None) -> Dict[str, Any]:
    """
    Simulates a macro drawdown on current user portfolio.
    If shock_points is provided (e.g. 500 points), converts to percentage based on latest Nifty close.
    """
    port = fetch_portfolio_positions(user_id=user_id)
    positions = port.get("positions", [])
    if not positions:
        return {
            "error": "No open positions found in portfolio to stress-test.",
            "total_value": 0,
            "simulated_loss": 0,
            "simulated_loss_pct": 0
        }

    conn = _get_conn()
    try:
        # Determine actual shock_pct if shock_points given
        nifty_row = conn.execute("SELECT close FROM daily_prices WHERE symbol='NIFTY50' ORDER BY trade_date DESC LIMIT 1").fetchone()
        nifty_curr = float(nifty_row[0]) if nifty_row else 22600.0

        if shock_points:
            shock_pct = -abs(float(shock_points) / nifty_curr * 100.0)

        total_curr_val = 0.0
        total_stressed_val = 0.0
        position_shocks = []

        for p in positions:
            sym = p["symbol"]
            curr_px = p["current_price"]
            shares = p["shares"]
            pos_val = p["current_value"]
            total_curr_val += pos_val

            beta = compute_stock_beta(sym, conn)
            stock_shock_pct = round(beta * shock_pct, 2)
            stressed_px = round(curr_px * (1.0 + (stock_shock_pct / 100.0)), 2)
            stressed_pos_val = round(stressed_px * shares, 2)
            loss_inr = round(pos_val - stressed_pos_val, 2)
            total_stressed_val += stressed_pos_val

            # SL breach check under stress
            sl = p["stop_loss"]
            sl_breached = stressed_px <= sl if sl else False

            position_shocks.append({
                "symbol": sym,
                "shares": shares,
                "beta": beta,
                "current_price": curr_px,
                "current_value": pos_val,
                "shock_pct": stock_shock_pct,
                "stressed_price": stressed_px,
                "stressed_value": stressed_pos_val,
                "loss_inr": loss_inr,
                "sl": sl,
                "sl_breached": sl_breached
            })

        # Sort positions by highest drawdown / vulnerability
        position_shocks.sort(key=lambda x: x["loss_inr"], reverse=True)

        total_loss_inr = round(total_curr_val - total_stressed_val, 2)
        portfolio_drawdown_pct = round((total_loss_inr / total_curr_val) * 100.0, 2) if total_curr_val > 0 else 0.0

        # Weighted portfolio beta
        w_beta = sum(p["beta"] * (p["current_value"] / total_curr_val) for p in position_shocks) if total_curr_val > 0 else 1.0

        return {
            "nifty_close": nifty_curr,
            "shock_pct": round(shock_pct, 2),
            "shock_points": round(abs(shock_pct / 100.0 * nifty_curr), 1),
            "total_portfolio_value": round(total_curr_val, 2),
            "stressed_portfolio_value": round(total_stressed_val, 2),
            "total_loss_inr": total_loss_inr,
            "portfolio_drawdown_pct": portfolio_drawdown_pct,
            "portfolio_beta": round(w_beta, 2),
            "position_shocks": position_shocks
        }
    finally:
        conn.close()

def format_macro_stress_markdown(sim: Dict[str, Any]) -> str:
    """Format macro stress test simulation into an institutional risk dossier."""
    if sim.get("error"):
        return f"⚠️ **Macro Stress-Testing Notice:** {sim['error']}"

    n_close = sim.get("nifty_close", 22600.0)
    shock_pct = sim.get("shock_pct", -3.0)
    shock_pts = sim.get("shock_points", 678.0)
    tot_val = sim.get("total_portfolio_value", 0.0)
    tot_loss = sim.get("total_loss_inr", 0.0)
    drawdown_pct = sim.get("portfolio_drawdown_pct", 0.0)
    p_beta = sim.get("portfolio_beta", 1.0)

    lines = [
        f"### ⚡ Macro Stress-Testing & Shock Simulation (NIFTY 50 {shock_pct:+.1f}%)",
        f"*Simulating a **{shock_pts:,.0f}-point drop** in NIFTY 50 (from ₹{n_close:,.1f}) across current holdings*",
        "",
        f"• **Current Portfolio Value:** ₹{tot_val:,.2f}",
        f"• **Simulated Value After Shock:** ₹{sim.get('stressed_portfolio_value', 0):,.2f}",
        f"• **Projected Portfolio Loss:** **-₹{tot_loss:,.2f}** (**-{drawdown_pct:.2f}%**)",
        f"• **Weighted Portfolio Beta:** **{p_beta:.2f}** {'(High Volatility)' if p_beta > 1.15 else '(Defensive / Resilient)' if p_beta < 0.9 else '(Market Parity)'}",
        ""
    ]

    shocks = sim.get("position_shocks", [])
    if shocks:
        lines.append("#### 📊 Position-by-Position Impact Matrix")
        lines.append("| Ticker | Beta | Current Val | Shock % | Stressed Val | Projected Loss | Stop-Loss Status |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

        vulnerable = []
        sl_hits = []

        for p in shocks:
            sl_note = "🔴 **TRIGGERED**" if p["sl_breached"] else "🟢 Safe"
            if p["sl_breached"]:
                sl_hits.append(p["symbol"])
            if p["beta"] >= 1.2:
                vulnerable.append(f"**{p['symbol']}** (Beta {p['beta']})")

            lines.append(
                f"| **{p['symbol']}** | {p['beta']:.2f} | ₹{p['current_value']:,.0f} | "
                f"{p['shock_pct']:+.1f}% | ₹{p['stressed_value']:,.0f} | **-₹{p['loss_inr']:,.0f}** | {sl_note} |"
            )
        lines.append("")

        lines.append("#### 🛡️ Institutional Risk Management Recommendations")
        if sl_hits:
            lines.append(f"1. ⚠️ **Immediate Stop-Loss Exposure:** {', '.join(sl_hits)} will breach stop-loss levels during this magnitude of index correction. Consider tightening trailing SL to 20-EMA.")
        else:
            lines.append("1. ✅ **Stop-Loss Buffers Intact:** Current stop-losses sit below the projected drawdown levels for all holdings.")

        if vulnerable:
            lines.append(f"2. 📉 **High-Beta Concentration:** {', '.join(vulnerable)} represent outsized downside risk. Trim exposure by 25% or hedge with defensive cash.")
        else:
            lines.append("2. 🛡️ **Balanced Beta:** Portfolio exhibits defensive resilience vs broad benchmark pullbacks.")

        lines.append("3. 💵 **Cash Reallocation Rule:** Maintain at least 15–20% cash ready to deploy into continuation leaders once NIFTY hits Gann Sq9 support.")

    return "\n".join(lines)
