"""
core/tools/smart_money_deals_tool.py
====================================
Institutional Footprint & Smart Money Audit Tool.
Queries bulk_block_deals (216,000+ records) and volume_anomalies (300,000+ records)
to detect institutional block accumulation, absorption, or distribution exhaustion.
"""

import os
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "market_data_v2.db")

def _get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def get_smart_money_deals(symbol: Optional[str] = None, limit: int = 8) -> Dict[str, Any]:
    """
    Fetch recent bulk/block deals and volume anomalies for a symbol, or market-wide if symbol is None.
    Calculates total institutional buy vs sell turnover in ₹ Crores.
    """
    conn = _get_conn()
    deals = []
    anomalies = []
    sym_clean = symbol.upper().strip() if symbol else None

    try:
        # 1. Fetch bulk / block deals
        if sym_clean:
            d_rows = conn.execute("""
                SELECT deal_date, symbol, deal_type, quantity, price, deal_kind, client_name, client_category
                FROM bulk_block_deals
                WHERE symbol = ?
                ORDER BY deal_date DESC, id DESC
                LIMIT ?
            """, (sym_clean, limit)).fetchall()
        else:
            d_rows = conn.execute("""
                SELECT deal_date, symbol, deal_type, quantity, price, deal_kind, client_name, client_category
                FROM bulk_block_deals
                ORDER BY deal_date DESC, id DESC
                LIMIT ?
            """, (limit,)).fetchall()

        total_buy_val = 0.0
        total_sell_val = 0.0

        for r in d_rows:
            qty = float(r["quantity"] or 0)
            px = float(r["price"] or 0)
            deal_val = (qty * px) / 1e7  # Convert to ₹ Crores
            deal_type = (r["deal_type"] or "").upper()
            if deal_type == "BUY":
                total_buy_val += deal_val
            elif deal_type == "SELL":
                total_sell_val += deal_val

            deals.append({
                "deal_date": r["deal_date"],
                "symbol": r["symbol"],
                "deal_type": deal_type,
                "quantity": int(qty),
                "price": round(px, 2),
                "value_cr": round(deal_val, 2),
                "deal_kind": r["deal_kind"] or "BULK",
                "client_name": r["client_name"] or "Institutional Entity",
                "client_category": r["client_category"] or "FII/DII"
            })

        # 2. Fetch volume anomalies
        if sym_clean:
            a_rows = conn.execute("""
                SELECT trade_date, symbol, vol_ratio, signal, candle_type, price_change_pct
                FROM volume_anomalies
                WHERE symbol = ?
                ORDER BY trade_date DESC
                LIMIT 5
            """, (sym_clean,)).fetchall()
        else:
            a_rows = conn.execute("""
                SELECT trade_date, symbol, vol_ratio, signal, candle_type, price_change_pct
                FROM volume_anomalies
                ORDER BY trade_date DESC, vol_ratio DESC
                LIMIT ?
            """, (limit,)).fetchall()

        for a in a_rows:
            anomalies.append({
                "trade_date": a["trade_date"],
                "symbol": a["symbol"],
                "vol_ratio": round(float(a["vol_ratio"] or 1.0), 2),
                "signal": a["signal"] or "NORMAL",
                "candle_type": a["candle_type"] or "NORMAL",
                "price_change_pct": round(float(a["price_change_pct"] or 0.0), 2)
            })

        # 3. Overall smart money verdict
        net_flow_cr = round(total_buy_val - total_sell_val, 2)
        if total_buy_val > total_sell_val * 1.5:
            verdict = "INSTITUTIONAL_ACCUMULATION"
            verdict_label = "🏛️ Institutional Accumulation (Net Inflow)"
        elif total_sell_val > total_buy_val * 1.5:
            verdict = "INSTITUTIONAL_DISTRIBUTION"
            verdict_label = "⚠️ Institutional Distribution (Net Outflow)"
        else:
            verdict = "BALANCED_CHURN"
            verdict_label = "⚖️ Balanced Institutional Churn"

        return {
            "symbol": sym_clean,
            "deals": deals,
            "anomalies": anomalies,
            "total_buy_cr": round(total_buy_val, 2),
            "total_sell_cr": round(total_sell_val, 2),
            "net_flow_cr": net_flow_cr,
            "verdict": verdict,
            "verdict_label": verdict_label
        }
    except Exception as e:
        return {"error": str(e), "deals": [], "anomalies": []}
    finally:
        conn.close()

def format_smart_money_markdown(data: Dict[str, Any]) -> str:
    """Format institutional deal data and volume anomaly report in clean markdown."""
    if data.get("error"):
        return f"⚠️ **Institutional Audit Notice:** {data['error']}"

    sym = data.get("symbol")
    header = f"### 🏛️ Institutional Smart Money Audit: {sym}" if sym else "### 🏛️ Recent Institutional Block & Bulk Deals"
    lines = [
        header,
        f"**Verdict:** {data.get('verdict_label', 'Active')}",
        f"• **Total Institutional Bought:** ₹{data.get('total_buy_cr', 0):,.2f} Cr | **Sold:** ₹{data.get('total_sell_cr', 0):,.2f} Cr | **Net:** **{data.get('net_flow_cr', 0):+,.2f} Cr**",
        ""
    ]

    deals = data.get("deals", [])
    if deals:
        lines.append("#### 📋 Recent Bulk & Block Transactions")
        for d in deals:
            badge = "🟢 BUY " if d["deal_type"] == "BUY" else "🔴 SELL"
            lines.append(
                f"- **`{d['deal_date']}`** | `{badge}` **{d['symbol']}** | **{d['client_name']}** | "
                f"**{d['quantity']:,}** shares @ ₹{d['price']:,.2f} (**₹{d['value_cr']:,.2f} Cr** · {d['deal_kind']})"
            )
        lines.append("")
    else:
        lines.append("*(No major bulk or block deals recorded for this ticker in recent sessions).*")
        lines.append("")

    anomalies = data.get("anomalies", [])
    if anomalies:
        lines.append("#### ⚡ Institutional Volume Anomalies & Absorption Signals")
        for a in anomalies:
            sig = a["signal"]
            icon = "🔥" if "SPIKE" in sig or "ACCUMULATION" in sig else "💧" if "ABSORPTION" in sig else "⚠️"
            lines.append(
                f"- **`{a['trade_date']}`** {icon} **{a['symbol']}** — **{a['vol_ratio']}x** avg volume | "
                f"Signal: `{sig}` | Candle: `{a['candle_type']}` | Return: **{a['price_change_pct']:+.2f}%**"
            )
        lines.append("")

    lines.append("> 💡 **Quant Interpretation:** Institutional bulk deals represent high-conviction hands. When volume surges >2x with an `ABSORPTION` or `HAMMER` candle, smart money is absorbing retail panic selling at Gann support.")
    return "\n".join(lines)
