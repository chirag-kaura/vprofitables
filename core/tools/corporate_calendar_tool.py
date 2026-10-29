"""
core/tools/corporate_calendar_tool.py
=====================================
LangChain tool for Corporate Actions, Earnings Calendar RAG, and Dividend Arbitrage.
Queries 'earnings_calendar' and 'corporate_actions' in market_data_v2.db.
"""

import os
import sys
import sqlite3
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "market_data_v2.db")

sys.path.insert(0, BASE_DIR)
from core.chatbot_engine import get_market_price_snapshot
from core.financial_query import format_crores, format_pct

def get_upcoming_corporate_events(symbol: Optional[str] = None, limit: int = 6, days_ahead: int = 14) -> Dict[str, Any]:
    """Fetch earnings board meetings and corporate actions (dividends, splits, bonuses)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    earnings_list = []
    actions_list = []

    if symbol:
        clean_sym = symbol.strip().upper()
        cur.execute("""
            SELECT symbol, company_name, event_date, purpose 
            FROM earnings_calendar 
            WHERE symbol = ? 
            ORDER BY event_date DESC 
            LIMIT ?
        """, (clean_sym, limit))
        for r in cur.fetchall():
            earnings_list.append({
                "symbol": r[0], "name": r[1], "event_date": r[2], "purpose": r[3]
            })

        cur.execute("""
            SELECT symbol, ex_date, action_type, value 
            FROM corporate_actions 
            WHERE symbol = ? 
            ORDER BY ex_date DESC 
            LIMIT ?
        """, (clean_sym, limit))
        for r in cur.fetchall():
            actions_list.append({
                "symbol": r[0], "ex_date": r[1], "action_type": r[2], "value": r[3]
            })
    else:
        cur.execute("""
            SELECT symbol, company_name, event_date, purpose 
            FROM earnings_calendar 
            ORDER BY event_date DESC 
            LIMIT ?
        """, (limit,))
        for r in cur.fetchall():
            earnings_list.append({
                "symbol": r[0], "name": r[1], "event_date": r[2], "purpose": r[3]
            })

        cur.execute("""
            SELECT symbol, ex_date, action_type, value 
            FROM corporate_actions 
            ORDER BY ex_date DESC 
            LIMIT ?
        """, (limit,))
        for r in cur.fetchall():
            actions_list.append({
                "symbol": r[0], "ex_date": r[1], "action_type": r[2], "value": r[3]
            })

    conn.close()
    return {
        "symbol": symbol,
        "earnings": earnings_list,
        "actions": actions_list
    }


def format_corporate_calendar_markdown(data: Dict[str, Any]) -> str:
    """Format corporate actions & earnings calendar report with dividend yield & event risk."""
    lines = []
    lines.append("### 📅 Corporate Calendar, Earnings & Dividend Radar")

    if data.get("earnings"):
        lines.append("\n#### 🎙️ Upcoming Financial Results & Board Meetings:")
        lines.append("| Symbol | Company | Result / Event Date | Purpose |")
        lines.append("| :--- | :--- | :---: | :--- |")
        for e in data["earnings"][:5]:
            lines.append(f"| **{e['symbol']}** | {e.get('name') or e['symbol']} | `{e['event_date']}` | {e['purpose']} |")

    if data.get("actions"):
        lines.append("\n#### 💰 Upcoming Dividends, Splits & Corporate Actions:")
        lines.append("| Symbol | Ex-Date | Corporate Action | Value / Ratio | Stock Price |")
        lines.append("| :--- | :---: | :---: | :---: | :---: |")
        for a in data["actions"][:5]:
            px = get_market_price_snapshot(a["symbol"])
            ltp = f"₹{px.get('ltp', 0):,.2f}" if px.get("ltp") else "N/A"
            val_str = f"₹{a['value']:.2f}" if a["action_type"] == "DIVIDEND" else str(a['value'])
            lines.append(f"| **{a['symbol']}** | `{a['ex_date']}` | **{a['action_type']}** | {val_str} | {ltp} |")

    lines.append("\n💡 *Before trading corporate actions, the Copilot verifies trend continuation to ensure you avoid post-dividend price collapse.*")
    return "\n".join(lines)


get_upcoming_earnings = get_upcoming_corporate_events
get_upcoming_dividends_splits = get_upcoming_corporate_events

@tool
def get_corporate_calendar_tool(symbol: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve upcoming board meetings, earnings announcements, and dividend corporate actions."""
    return get_upcoming_corporate_events(symbol=symbol)
