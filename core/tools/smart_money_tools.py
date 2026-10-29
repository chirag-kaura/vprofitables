"""
core/tools/smart_money_tools.py
==============================
Institutional Smart Money & Bulk/Block Deals Tool Adapter.
Tracks verified large block transactions, institutional buy/sell pressure, and net capital flow in ₹ Crores.
"""

import os
import sqlite3
import time
from typing import Optional, Dict, Any, List
from core.tools.contracts import ToolResult
from core.swarm.cache import ttl_cached, TTL_INTRADAY

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "market_data_v2.db")

def _get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

@ttl_cached(ttl=TTL_INTRADAY, namespace="smart_money_deals")
def smart_money_deal_flow(symbol: Optional[str] = None, limit: int = 5) -> ToolResult:
    """
    Fetch recent institutional bulk/block deals for a specific symbol or market-wide.
    Aggregates buy turnover, sell turnover, and net institutional capital flow in ₹ Crores.
    """
    t0 = time.perf_counter()
    sym = symbol.upper().strip() if symbol else None
    conn = _get_conn()
    try:
        if sym:
            rows = conn.execute("""
                SELECT deal_date, symbol, deal_type, quantity, price, deal_kind, client_name, client_category
                FROM bulk_block_deals
                WHERE symbol = ?
                ORDER BY deal_date DESC, id DESC
                LIMIT ?
            """, (sym, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT deal_date, symbol, deal_type, quantity, price, deal_kind, client_name, client_category
                FROM bulk_block_deals
                ORDER BY deal_date DESC, id DESC
                LIMIT ?
            """, (limit,)).fetchall()

        if not rows:
            return ToolResult(
                domain="SMART_MONEY",
                symbol=sym or "MARKET_WIDE",
                headline_metric=f"No recent bulk/block deals recorded for {sym or 'the market'}",
                tabular_summary="*No institutional bulk/block deals found in the audit trail.*",
                execution_ms=int((time.perf_counter() - t0) * 1000)
            )

        total_buy_cr = 0.0
        total_sell_cr = 0.0
        table_rows = [
            "| Date | Symbol | Type | Client Name | Qty | Price | Value (Rs. Cr) |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        ]

        deals_data = []
        for r in rows:
            d_date = r["deal_date"]
            s = r["symbol"]
            d_type = (r["deal_type"] or "").upper()
            qty = int(r["quantity"] or 0)
            px = float(r["price"] or 0.0)
            val_cr = (qty * px) / 1e7

            if d_type == "BUY":
                total_buy_cr += val_cr
            elif d_type == "SELL":
                total_sell_cr += val_cr

            client = (r["client_name"] or "Unknown")[:25]
            table_rows.append(f"| {d_date} | {s} | **{d_type}** | {client} | {qty:,} | Rs. {px:,.2f} | Rs. {val_cr:,.2f} Cr |")
            deals_data.append({
                "date": d_date,
                "symbol": s,
                "type": d_type,
                "client": client,
                "qty": qty,
                "price": px,
                "value_cr": round(val_cr, 2)
            })

        net_flow_cr = total_buy_cr - total_sell_cr
        pressure = "ACCUMULATION (Net Inflow)" if net_flow_cr > 0 else ("DISTRIBUTION (Net Outflow)" if net_flow_cr < 0 else "BALANCED")
        headline = f"Net Institutional Flow: Rs. {net_flow_cr:+,.2f} Cr ({pressure}) | Total Buy: Rs. {total_buy_cr:,.2f} Cr, Total Sell: Rs. {total_sell_cr:,.2f} Cr"

        raw = {
            "symbol": sym,
            "total_buy_cr": round(total_buy_cr, 2),
            "total_sell_cr": round(total_sell_cr, 2),
            "net_flow_cr": round(net_flow_cr, 2),
            "pressure": pressure,
            "deals_count": len(deals_data),
            "deals": deals_data
        }

        return ToolResult(
            domain="SMART_MONEY",
            symbol=sym or "MARKET_WIDE",
            headline_metric=headline,
            tabular_summary="\n".join(table_rows),
            raw_data=raw,
            execution_ms=int((time.perf_counter() - t0) * 1000)
        )
    except Exception as e:
        return ToolResult(
            domain="SMART_MONEY",
            symbol=sym,
            headline_metric=f"Error reading bulk deals for {sym}",
            tabular_summary=f"> Execution error: {e}",
            execution_ms=int((time.perf_counter() - t0) * 1000),
            error=str(e)
        )
    finally:
        conn.close()
