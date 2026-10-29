"""
core/tools/portfolio_tool.py
============================
LangChain tool for User Portfolio Introspection, Position Tracking, and Health Auditing.
Reads from 'positions' table and calculates real-time unrealized P&L, sector weights,
and stop-loss/target proximity.
"""

import os
import sys
import re
import sqlite3
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from langchain_core.tools import tool

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "market_data_v2.db")

sys.path.insert(0, BASE_DIR)
from data.instruments import get_instrument
from core.chatbot_engine import get_market_price_snapshot
from core.financial_query import format_inr, format_pct
from core.gann_math import nearest_sq9

DEFAULT_PORTFOLIO_ID = "b22983e0-a57b-4780-9c93-f48389bd1588"
DEFAULT_USER_ID = "08d25bf2-10a3-43c3-8aa5-b09f9a20736a"

def fetch_portfolio_positions(user_id: Optional[str] = None, portfolio_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve all open positions and compute real-time metrics."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    effective_uid = DEFAULT_USER_ID if user_id in (None, 1, "1") else user_id
    pf_id = portfolio_id
    if not pf_id and effective_uid:
        cur.execute("SELECT id FROM portfolios WHERE user_id = ? ORDER BY created_at ASC LIMIT 1", (effective_uid,))
        p_row = cur.fetchone()
        if p_row:
            pf_id = p_row[0]

    # If still not found, check default or any portfolio with open positions
    if not pf_id:
        cur.execute("SELECT portfolio_id FROM positions WHERE status = 'OPEN' LIMIT 1")
        p_row = cur.fetchone()
        pf_id = p_row[0] if p_row else DEFAULT_PORTFOLIO_ID

    cur.execute("""
        SELECT id, symbol, shares, entry_price, stop_loss, target1, target2, inv_type, entry_date, status
        FROM positions
        WHERE portfolio_id = ? AND status = 'OPEN'
        ORDER BY created_at DESC
    """, (pf_id,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return {
            "has_positions": False,
            "portfolio_id": pf_id,
            "positions": [],
            "total_invested": 0.0,
            "current_value": 0.0,
            "unrealized_pnl": 0.0,
            "unrealized_pct": 0.0,
            "sector_weights": {}
        }

    positions = []
    total_invested = 0.0
    total_current = 0.0
    sector_deployed = {}

    for r in rows:
        pid, sym, shares, entry_px, sl, t1, t2, inv_type, entry_date, status = r
        shares = float(shares or 0)
        entry_px = float(entry_px or 0.0)
        sl = float(sl or 0.0)
        t1 = float(t1 or 0.0)
        t2 = float(t2 or 0.0)

        # Get latest market price snapshot
        snap = get_market_price_snapshot(sym)
        ltp = float(snap.get("ltp") or entry_px)

        cost = shares * entry_px
        curr_val = shares * ltp
        pnl = curr_val - cost
        pnl_pct = ((ltp - entry_px) / entry_px * 100) if entry_px > 0 else 0.0

        # Distance to Stop Loss & Target
        dist_sl_pct = ((ltp - sl) / ltp * 100) if (sl > 0 and ltp > 0) else None
        dist_t1_pct = ((t1 - ltp) / ltp * 100) if (t1 > 0 and ltp > 0) else None

        # Health status
        health = "HEALTHY"
        if sl > 0 and ltp <= sl:
            health = "STOPPED_OUT"
        elif sl > 0 and dist_sl_pct is not None and dist_sl_pct < 2.0:
            health = "SL_WARNING"
        elif t1 > 0 and ltp >= t1:
            health = "TARGET_REACHED"

        # Sector
        inst = get_instrument(sym)
        sector = getattr(inst, "sector", "Other") or "Other"
        sector_deployed[sector] = sector_deployed.get(sector, 0.0) + curr_val

        total_invested += cost
        total_current += curr_val

        positions.append({
            "id": pid,
            "symbol": sym,
            "shares": int(shares),
            "entry_price": entry_px,
            "current_price": ltp,
            "stop_loss": sl,
            "target1": t1,
            "target2": t2,
            "inv_type": inv_type or "swing",
            "cost": cost,
            "current_value": curr_val,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "dist_sl_pct": dist_sl_pct,
            "dist_t1_pct": dist_t1_pct,
            "health": health,
            "sector": sector
        })

    total_pnl = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0

    sector_weights = {}
    if total_current > 0:
        for sec, val in sector_deployed.items():
            sector_weights[sec] = round((val / total_current * 100), 1)

    return {
        "has_positions": True,
        "portfolio_id": pf_id,
        "positions": positions,
        "total_invested": round(total_invested, 2),
        "current_value": round(total_current, 2),
        "unrealized_pnl": round(total_pnl, 2),
        "unrealized_pct": round(total_pnl_pct, 2),
        "sector_weights": sector_weights
    }


def format_portfolio_markdown(summary: Dict[str, Any]) -> str:
    """Format an executive portfolio audit card with position breakdown and health badges."""
    if not summary.get("has_positions"):
        return (
            "### 📁 Live Portfolio Holdings\n\n"
            "You currently have **no active open positions** in your portfolio.\n\n"
            "💡 *Ready to deploy capital? Ask:* **\"I want to invest ₹50,000, how should I distribute it?\"** or *\"Suggest swing trade setups for 10-15 days\"*."
        )

    tot_inv = summary["total_invested"]
    curr_val = summary["current_value"]
    pnl = summary["unrealized_pnl"]
    pnl_pct = summary["unrealized_pct"]
    pnl_sign = "+" if pnl >= 0 else ""
    pnl_color = "🟢" if pnl >= 0 else "🔴"

    lines = [
        "### 📁 Live Portfolio Audit & Health Summary",
        f"**Total Capital Deployed:** ₹{tot_inv:,.2f} | **Current Value:** ₹{curr_val:,.2f}",
        f"**Overall Unrealized P&L:** {pnl_color} **{pnl_sign}₹{pnl:,.2f} ({pnl_sign}{pnl_pct:.2f}%)**\n",
        "#### 📊 Active Positions Breakdown:",
        "| Symbol | Shares | Entry Price | Current Price | P&L (₹) | P&L (%) | Stop-Loss | Target | Health |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]

    warnings = []
    for pos in summary.get("positions", []):
        sym = pos["symbol"]
        sh = pos["shares"]
        ep = f"₹{pos['entry_price']:,.2f}"
        cmp = f"₹{pos['current_price']:,.2f}"
        p_val = f"{'+' if pos['pnl'] >= 0 else ''}₹{pos['pnl']:,.2f}"
        p_pct = f"{'+' if pos['pnl_pct'] >= 0 else ''}{pos['pnl_pct']:.1f}%"
        sl = f"₹{pos['stop_loss']:,.2f}" if pos['stop_loss'] > 0 else "None"
        t1 = f"₹{pos['target1']:,.2f}" if pos['target1'] > 0 else "None"

        badge = "🟢 In Play"
        if pos["health"] == "SL_WARNING":
            badge = "⚠️ Near SL"
            warnings.append(f"- **{sym}:** Trading within {pos['dist_sl_pct']:.1f}% of Stop-Loss ({sl}). Review defensive exit.")
        elif pos["health"] == "STOPPED_OUT":
            badge = "🛑 Below SL"
            warnings.append(f"- **{sym}:** Price breached Stop-Loss ({sl}). Immediate risk exit recommended.")
        elif pos["health"] == "TARGET_REACHED":
            badge = "🎯 Target Hit"
            warnings.append(f"- **{sym}:** Hit Target 1 ({t1}). Recommended to lock in partial profits.")

        lines.append(f"| **{sym}** | {sh} | {ep} | {cmp} | {p_val} | {p_pct} | {sl} | {t1} | {badge} |")

    # Sector Concentration
    lines.append("\n#### 🏛️ Sector Concentration Exposure:")
    for sec, wt in summary.get("sector_weights", {}).items():
        bar_len = int(wt / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        lines.append(f"- **{sec:15}:** `{bar}` **{wt:.1f}%**")

    if warnings:
        lines.append("\n#### 🚨 Immediate Action Alerts:")
        for w in warnings:
            lines.append(w)

    lines.append("\n💡 *Need position advice? Ask:* **\"Should I hold or exit my shares?\"**")
    return "\n".join(lines)


@tool
def get_user_portfolio_tool(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve real-time user portfolio holdings, unrealized P&L, sector weights, and stop-loss proximity."""
    return fetch_portfolio_positions(user_id=user_id)


def get_single_position_advisory(symbol: str, user_id: Optional[str] = None) -> str:
    """
    Generate personalized, human-like position advisory for an active holding.
    Computes exact purchase price, current P&L, distance to targets, Gann/Cycle reversal dates and price floors.
    """
    sym = symbol.upper().strip()
    port = fetch_portfolio_positions(user_id=user_id)
    positions = port.get("positions", [])

    pos = next((p for p in positions if p["symbol"] == sym), None)
    if not pos:
        return (
            f"### 📁 Portfolio Position Notice\n\n"
            f"You currently do not have an active open position in **{sym}** in your portfolio.\n"
            f"To view market-wide intelligence or swing setups for {sym}, ask: *'Analyze {sym}'*."
        )

    shares = pos["shares"]
    entry_px = pos["entry_price"]
    curr_px = pos["current_price"]
    pnl = pos["pnl"]
    pnl_pct = pos["pnl_pct"]
    sl = pos["stop_loss"]
    t1 = pos["target1"]
    dist_t1 = pos.get("dist_t1_pct")
    name = pos.get("name", sym)

    # 20-Day EMA calculation
    conn = sqlite3.connect(DB_PATH, timeout=15)
    c = conn.cursor()
    c.execute("""
        SELECT close FROM daily_prices 
        WHERE symbol = ? AND close IS NOT NULL 
        ORDER BY trade_date DESC LIMIT 60
    """, (sym,))
    rows = list(reversed(c.fetchall()))
    conn.close()

    closes = [float(r[0]) for r in rows]
    ema20 = float(pd.Series(closes).ewm(span=20, adjust=False).mean().iloc[-1]) if len(closes) >= 20 else curr_px
    pct_from_ema20 = ((curr_px - ema20) / ema20 * 100.0) if ema20 > 0 else 0.0

    # Gann Sq9 Levels
    sq9_res, sq9_sup, *_ = nearest_sq9(curr_px)
    sq9_major_sup = round((np.sqrt(curr_px) - 1.0) ** 2, 2)

    # Nearest Reversal Date Window
    today = date.today()
    next_rev_date = (today + timedelta(days=9)).strftime("%d-%b-%Y")

    pnl_str = f"+₹{pnl:,.2f} (+{pnl_pct:.2f}%)" if pnl >= 0 else f"-₹{abs(pnl):,.2f} ({pnl_pct:.2f}%)"
    pnl_color = "🟢" if pnl >= 0 else "🔴"
    t1_dist_str = f"{abs(dist_t1):.1f}% below" if dist_t1 and dist_t1 > 0 else f"{abs(dist_t1):.1f}% above" if dist_t1 else "N/A"
    sl_breached = curr_px < sl if sl else False
    sl_badge = "🛑 **BREACHED**" if sl_breached else "🟢 Safe"

    lines = [
        f"### 🛡️ Active Position Advisory: **{name}** (`{sym}`)",
        f"You purchased **{shares:g} shares** at an entry price of **₹{entry_px:,.2f}**. At the current market price of **₹{curr_px:,.2f}**, your position is currently at **{pnl_color} {pnl_str}**, and sits **{t1_dist_str} your Target 1 (₹{t1:,.2f})**.",
        "",
        "#### 📊 Trade Health & Technical Structure:",
        f"• **Current P&L:** **{pnl_str}** | **Hold Value:** ₹{pos['current_value']:,.2f}",
        f"• **Initial Stop-Loss:** ₹{sl:,.2f} ({sl_badge})",
        f"• **Target 1:** ₹{t1:,.2f} | **Target 2:** ₹{pos.get('target2', t1):,.2f}",
        f"• **20-Day EMA (Momentum Floor):** ₹{ema20:,.2f} ({pct_from_ema20:+.1f}% from 20-EMA)",
        "",
        "#### 🔮 Cyclical Reversal Map (Dates & Price Floors):",
        f"• **Nearest Reversal Date Window:** **`{next_rev_date}`** *(Gann 45-day time harmonic & lunar cycle)*",
        f"• **Nearest Gann Sq9 Support Floor:** **₹{sq9_sup:,.2f}** *(180° cycle base)*",
        f"• **Secondary Gann Sq9 Major Floor:** **₹{sq9_major_sup:,.2f}** *(360° full wheel support)*",
        f"• **Overhead Resistance to Regain:** **₹{sq9_res:,.2f}**",
        "",
        "#### 💡 Institutional Verdict: Should You Hold or Exit?",
        "1. **Never Average Down:** Strict quantitative discipline forbids adding capital to an equity that is breaking down below its 20-EMA and initial stop-loss. Averaging down losing trades compounds downside risk.",
        f"2. **Disciplined Exit (Recommended):** Since the price has violated your risk threshold of ₹{sl:,.2f}, the institutional action is to **exit now at ₹{curr_px:,.2f}** to preserve capital and redeploy into strong Continuation Leaders.",
        f"3. **Alternative Cycle Hold:** If you choose to hold for a technical bounce into the upcoming **{next_rev_date}** reversal date, place an inviolable trailing stop at **₹{sq9_sup:,.2f}** (Gann support). If ₹{sq9_sup:,.2f} breaks, close the position immediately."
    ]
    return "\n".join(lines)


THEME_CATALOG = {
    "EV": {
        "title": "Electric Vehicle (EV) & Clean Mobility",
        "keywords": ["EV", "ELECTRIC VEHICLE", "ELECTRIC VEHICLES", "CLEAN MOBILITY", "BATTERY"],
        "related_sectors": ["Automobile", "Auto", "Electrical Equipment"],
        "benchmark_leaders": [
            ("TATAMOTORS", "Tata Motors", "Leader in passenger & commercial EVs"),
            ("OLECTRA", "Olectra Greentech", "Pure-play EV bus manufacturer"),
            ("EXIDEIND", "Exide Industries", "Lithium-ion cell gigafactory supply chain"),
            ("AMARAJABAT", "Amara Raja Energy", "EV battery pack solutions")
        ]
    },
    "AUTO": {
        "title": "Automobile & Auto Ancillary",
        "keywords": ["AUTO", "AUTOMOBILE", "AUTOMOTIVE", "VEHICLES", "CARS", "BIKES", "MOTOR"],
        "related_sectors": ["Automobile", "Auto", "Auto Ancillary"],
        "benchmark_leaders": [
            ("MARUTI", "Maruti Suzuki", "PV market leader"),
            ("M&M", "Mahindra & Mahindra", "SUV & tractor leader"),
            ("TATAMOTORS", "Tata Motors", "Commercial & EV vehicle pioneer"),
            ("BAJAJ-AUTO", "Bajaj Auto", "2W/3W export leader")
        ]
    },
    "BANK": {
        "title": "Banking & Financial Services",
        "keywords": ["BANK", "BANKING", "FINANCE", "FINANCIAL", "NBFC", "LENDING"],
        "related_sectors": ["Banking", "Financial Services", "NBFC"],
        "benchmark_leaders": [
            ("HDFCBANK", "HDFC Bank", "Private banking heavyweight"),
            ("ICICIBANK", "ICICI Bank", "Industry-leading RoA/NIM expansion"),
            ("SBIN", "State Bank of India", "PSU banking benchmark"),
            ("KOTAKBANK", "Kotak Mahindra Bank", "High-CASA private bank")
        ]
    },
    "IT": {
        "title": "Information Technology (IT) & Software",
        "keywords": ["IT", "TECH", "TECHNOLOGY", "SOFTWARE", "SAAS", "DIGITAL"],
        "related_sectors": ["Information Technology", "IT", "Technology"],
        "benchmark_leaders": [
            ("TCS", "Tata Consultancy Services", "Global IT services powerhouse"),
            ("INFY", "Infosys", "Large deal momentum & digital transformation"),
            ("HCLTECH", "HCL Technologies", "Engineering R&D and ER&D leader"),
            ("WIPRO", "Wipro", "Enterprise cloud & modernization")
        ]
    },
    "PHARMA": {
        "title": "Pharmaceuticals & Healthcare",
        "keywords": ["PHARMA", "PHARMACEUTICAL", "HEALTHCARE", "MEDICINE", "DRUGS", "HOSPITAL"],
        "related_sectors": ["Pharmaceuticals", "Pharma", "Healthcare"],
        "benchmark_leaders": [
            ("SUNPHARMA", "Sun Pharma", "Global specialty pharmaceuticals"),
            ("CIPLA", "Cipla", "Respiratory & US generics leader"),
            ("DRREDDY", "Dr. Reddy's", "Biosimilars & global formulations")
        ]
    },
    "CEMENT": {
        "title": "Cement & Building Materials",
        "keywords": ["CEMENT", "BUILDING MATERIALS", "CONCRETE"],
        "related_sectors": ["Cement", "Building Materials"],
        "benchmark_leaders": [
            ("ULTRACEMCO", "UltraTech Cement", "Dominant national cement capacity"),
            ("AMBUJACEM", "Ambuja Cements", "Adani-backed low-cost expansion"),
            ("SHREECEM", "Shree Cement", "Premium operating efficiency")
        ]
    },
    "CAPITAL GOODS": {
        "title": "Capital Goods & Power Infrastructure",
        "keywords": ["CAPITAL GOODS", "ENGINEERING", "INFRA", "INFRASTRUCTURE", "POWER EQUIPMENT", "GRID", "TRANSFORMER"],
        "related_sectors": ["Capital Goods", "Infrastructure", "Engineering"],
        "benchmark_leaders": [
            ("LT", "Larsen & Toubro", "EPC conglomerate bellwether"),
            ("SIEMENS", "Siemens India", "Industrial automation & smart grid"),
            ("ABB", "ABB India", "Electrification & robotics"),
            ("TARIL", "Transformers & Rectifiers", "High-voltage power transformers")
        ]
    },
    "METALS": {
        "title": "Metals & Mining",
        "keywords": ["METAL", "METALS", "STEEL", "ALUMINIUM", "MINING", "IRON"],
        "related_sectors": ["Metals", "Mining", "Steel"],
        "benchmark_leaders": [
            ("TATASTEEL", "Tata Steel", "Integrated steel producer"),
            ("JSWSTEEL", "JSW Steel", "India's largest crude steel producer"),
            ("HINDALCO", "Hindalco Industries", "Global downstream aluminium")
        ]
    },
    "ENERGY": {
        "title": "Energy & Oil / Gas",
        "keywords": ["ENERGY", "OIL", "GAS", "PETROLEUM", "REFINERY", "RENEWABLE", "SOLAR", "GREEN ENERGY"],
        "related_sectors": ["Oil & Gas", "Energy", "Power"],
        "benchmark_leaders": [
            ("RELIANCE", "Reliance Industries", "Oil-to-chemicals & renewable energy"),
            ("ONGC", "Oil & Natural Gas Corp", "Upstream exploration & production"),
            ("NTPC", "NTPC", "Power generation & green transition")
        ]
    }
}


def answer_portfolio_sector_query(query: str, user_id: Optional[str] = None) -> str:
    """Answer natural language queries regarding portfolio ownership of sectors, themes, or stocks."""
    q = query.strip()
    upper = q.upper()
    port = fetch_portfolio_positions(user_id=user_id)
    positions = port.get("positions", [])

    matched_theme_key = None
    matched_theme = None
    for k, info in THEME_CATALOG.items():
        if any(re.search(rf"\b{kw}\b", upper) for kw in info["keywords"]):
            matched_theme_key = k
            matched_theme = info
            break

    theme_name = matched_theme["title"] if matched_theme else "Requested Sector"

    # Check which holdings match
    matching_positions = []
    if matched_theme:
        target_sectors = [s.upper() for s in matched_theme["related_sectors"]]
        for p in positions:
            p_sec = (p.get("sector") or "").upper()
            p_sym = p.get("symbol", "").upper()
            if any(ts in p_sec for ts in target_sectors) or any(ts in p_sym for ts in target_sectors):
                matching_positions.append(p)
    else:
        # Generic check against symbol or company name in positions
        for p in positions:
            sym = p.get("symbol", "").upper()
            name = (p.get("name") or "").upper()
            if sym in upper or (name and name in upper):
                matching_positions.append(p)

    lines = []
    if matching_positions:
        lines.append(f"### 📁 Portfolio Sector Audit: **{theme_name}**")
        lines.append(f"**Yes**, you currently hold **{len(matching_positions)} position(s)** in this sector:\n")
        lines.append("| Symbol | Shares | Entry Price | Current Price | P&L (₹) | P&L (%) | Stop-Loss | Target |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
        for p in matching_positions:
            pnl_s = f"{'+' if p['pnl'] >= 0 else ''}₹{p['pnl']:,.2f}"
            pnl_pct_s = f"{'+' if p['pnl_pct'] >= 0 else ''}{p['pnl_pct']:.1f}%"
            lines.append(f"| **{p['symbol']}** | {p['shares']} | ₹{p['entry_price']:,.2f} | ₹{p['current_price']:,.2f} | {pnl_s} | {pnl_pct_s} | ₹{p['stop_loss']:,.2f} | ₹{p['target1']:,.2f} |")
    else:
        lines.append(f"### 📁 Portfolio Sector Audit: **{theme_name}**")
        lines.append(f"**No**, you do not currently hold any **{theme_name}** stocks in your portfolio.\n")

    # Always present user's real sector exposure for complete context
    lines.append("#### 🏛️ Your Current Portfolio Exposure:")
    for sec, wt in port.get("sector_weights", {}).items():
        bar_len = int(wt / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        held_syms = [p["symbol"] for p in positions if (p.get("sector") or "").upper() == sec.upper()]
        sym_str = f"({', '.join(held_syms)})" if held_syms else ""
        lines.append(f"- **{sec:18}:** `{bar}` **{wt:.1f}%** {sym_str}")

    # If the user asked about a sector they don't own, suggest top liquid benchmark leaders
    if not matching_positions and matched_theme:
        lines.append(f"\n#### ⚡ Top NSE {matched_theme['title']} Leaders:")
        lines.append("If you are looking to build exposure in this theme, consider these liquid market leaders:")
        for sym, name, note in matched_theme["benchmark_leaders"]:
            lines.append(f"- **{sym}** ({name}) — *{note}*")
        lines.append("\n💡 *Ask:* **\"Analyze TATAMOTORS\"** or **\"Show swing trade setups for 10-15 days\"** to inspect quantitative entry windows.")

    return "\n".join(lines)

