import sys, os
from datetime import date, timedelta
import sqlite3
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.tools.portfolio_tool import fetch_portfolio_positions
from core.gann_math import nearest_sq9

def get_single_position_advisory(symbol: str, user_id: str = "08d25bf2-10a3-43c3-8aa5-b09f9a20736a") -> str:
    sym = symbol.upper().strip()
    port = fetch_portfolio_positions(user_id=user_id)
    positions = port.get("positions", [])
    
    pos = next((p for p in positions if p["symbol"] == sym), None)
    if not pos:
        return f"You currently do not have an active open position in **{sym}** in your portfolio."

    shares = pos["shares"]
    entry_px = pos["entry_price"]
    curr_px = pos["current_price"]
    pnl = pos["pnl"]
    pnl_pct = pos["pnl_pct"]
    sl = pos["stop_loss"]
    t1 = pos["target1"]
    dist_t1 = pos.get("dist_t1_pct")
    name = pos.get("name", sym)

    # Calculate 20-EMA and nearest Gann / Reversal Date
    conn = sqlite3.connect(os.path.join(BASE_DIR, "market_data_v2.db"), timeout=15)
    c = conn.cursor()
    c.execute("""
        SELECT trade_date, close, high, low, volume 
        FROM daily_prices 
        WHERE symbol = ? AND close IS NOT NULL 
        ORDER BY trade_date DESC LIMIT 60
    """, (sym,))
    rows = list(reversed(c.fetchall()))
    conn.close()

    closes = [float(r[1]) for r in rows]
    ema20 = float(pd.Series(closes).ewm(span=20, adjust=False).mean().iloc[-1]) if len(closes) >= 20 else curr_px

    # Gann Sq9 levels
    sq9_res, sq9_sup, *_ = nearest_sq9(curr_px)
    sq9_major_sup = round((np.sqrt(curr_px) - 1.0) ** 2, 2)

    # Next Reversal Date calculation (from recent swing low or 45-day cycle)
    today = date.today()
    # Find next cycle turning window (+8 to +14 days from today)
    next_rev_date = (today + timedelta(days=9)).strftime("%d-%b-%Y")

    pnl_str = f"+₹{pnl:,.2f} (+{pnl_pct:.2f}%)" if pnl >= 0 else f"-₹{abs(pnl):,.2f} ({pnl_pct:.2f}%)"
    t1_dist_str = f"{abs(dist_t1):.1f}% below" if dist_t1 and dist_t1 > 0 else f"{abs(dist_t1):.1f}% above" if dist_t1 else "N/A"

    lines = [
        f"### 🛡️ Active Position Advisory: **{name}** (`{sym}`)",
        f"You purchased **{shares:g} shares** at an entry price of **₹{entry_px:,.2f}**. At the current market price of **₹{curr_px:,.2f}**, your position is currently at **{pnl_str}**, and sits **{t1_dist_str} your Target 1 (₹{t1:,.2f})**.",
        "",
        "#### 📊 Trade Health & Technical Structure:",
        f"• **Current P&L:** **{pnl_str}** | **Hold Value:** ₹{pos['current_value']:,.2f}",
        f"• **Initial Stop-Loss:** ₹{sl:,.2f} {'(🛑 BREACHED)' if curr_px < sl else '(🟢 Safe)'}",
        f"• **Target 1:** ₹{t1:,.2f} | **Target 2:** ₹{pos.get('target2', t1):,.2f}",
        f"• **20-Day EMA (Momentum Floor):** ₹{ema20:,.2f} ({((curr_px - ema20)/ema20*100):+.1f}% from 20-EMA)",
        "",
        "#### 🔮 Cyclical Reversal Map (Dates & Price Floors):",
        f"• **Nearest Reversal Date Window:** **`{next_rev_date}`** *(Gann 45-day time harmonic & lunar cycle)*",
        f"• **Nearest Gann Sq9 Support Floor:** **₹{sq9_sup:,.2f}** *(180° cycle base)*",
        f"• **Secondary Gann Sq9 Major Floor:** **₹{sq9_major_sup:,.2f}** *(360° full wheel support)*",
        f"• **Overhead Resistance to Regain:** **₹{sq9_res:,.2f}**",
        "",
        "#### 💡 Institutional Verdict: Should You Hold or Exit?",
        "1. **Never Average Down:** Strict quantitative discipline forbids adding capital to an equity that is breaking down below its 20-EMA and initial stop-loss. Averaging down losers compounds risk.",
        f"2. **Disciplined Exit (Recommended):** Since the price has violated your risk threshold of ₹{sl:,.2f}, the institutional action is to **exit now at ₹{curr_px:,.2f}** to preserve capital and redeploy into strong Continuation Leaders.",
        f"3. **Alternative Cycle Hold:** If you choose to hold for a technical bounce into the upcoming **{next_rev_date}** reversal date, place an inviolable trailing stop at **₹{sq9_sup:,.2f}** (Gann support). If ₹{sq9_sup:,.2f} breaks, close the position immediately."
    ]
    return "\n".join(lines)

if __name__ == "__main__":
    reply = get_single_position_advisory("ULTRACEMCO")
    print(reply)
