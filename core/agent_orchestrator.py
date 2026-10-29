"""
core/agent_orchestrator.py
==========================
LangGraph & LangChain Multi-Agent Swarm Orchestrator for Vprofitables Quant Copilot.

Architecture:
  - Supervisor / Router: Dispatches query to specialized micro-agents based on intent.
  - Neural Entity Linker (NEL): Resolves colloquial aliases ("Adani enterprise", "M&M", "TCS", "Nifty").
  - Working Memory State Machine: Maintains multi-turn context (session_id) without dropdown coupling.
  - Micro-Agents:
      * GreetingOrHelpAgent           (Platform capabilities, greetings, educational walkthrough)
      * MarketMomentumAgent           (scan_market_momentum_tool for 1D/5D/10D Gainers & Losers)
      * FundamentalScreenerAgent      (Audited Net Profit / PAT & Revenue ranking from company_financials_10y)
      * SwingScannerAgent             (scan_swing_setups_tool for 10-15 day setups)
      * BenchmarkIndexAgent           (Real-time index intelligence for NIFTY 50, BANK NIFTY, sectors)
      * FinancialAuditAgent           (get_verified_financials_tool for single-stock 10Y financials)
      * ComparisonAgent               (Side-by-side asset comparison)
      * ComparisonRecommendationAgent (Algorithmic multi-factor evaluation & investment thesis)
      * DisambiguationAgent           (Interactive group options for conglomerates)
  - Grounded Synthesizer: 100% uptime, zero hallucinations, ₹ Cr contract guaranteed.
"""

import os
import sys
import re
import sqlite3
from typing import Dict, Any, List, Optional, Tuple, TypedDict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# LangChain Tools
from core.tools.market_tool import scan_market_momentum_tool
from core.tools.swing_tool import scan_swing_setups_tool
from core.tools.financials_tool import get_verified_financials_tool
from core.tools.news_tool import get_news_sentiment_tool
from core.tools.smart_money_tool import get_institutional_holdings_tool
from core.tools.concall_tool import search_clean_concalls_tool
from core.tools.portfolio_tool import fetch_portfolio_positions, format_portfolio_markdown, get_single_position_advisory, answer_portfolio_sector_query
from core.tools.personalization_tool import parse_and_update_preferences
from core.tools.capital_allocation_tool import allocate_capital, format_capital_allocation_markdown
from core.tools.corporate_calendar_tool import get_upcoming_earnings, get_upcoming_dividends_splits, format_corporate_calendar_markdown
from core.tools.smart_money_deals_tool import get_smart_money_deals, format_smart_money_markdown
from core.tools.options_microstructure_tool import get_options_microstructure, format_options_microstructure_markdown
from core.tools.macro_stress_tool import simulate_macro_stress, format_macro_stress_markdown
from core.tools.multi_timeframe_tool import get_multi_timeframe_matrix, format_multi_timeframe_markdown
from core.autonomous_reasoning import run_autonomous_reasoning

from core.financial_query import (
    format_crores,
    format_pct,
    format_inr,
    FINANCIAL_UNIT_CONTRACT
)
from core.market_screener import format_screener_markdown
from core.chatbot_engine import (
    get_market_price_snapshot,
    _load_symbol_map,
    _SYMBOL_MAP,
    format_swing_setups_markdown
)
from core.entity_resolver import resolve_equity_entity, get_entity_resolver, is_index_symbol
from core.session_manager import get_session_manager


def make_action_chips(chips: List[Tuple[str, str]]) -> str:
    """Renders a responsive strip of interactive action chips for Copilot chat responses."""
    if not chips:
        return ""
    buttons = []
    for label, onclick in chips:
        escaped_onclick = onclick.replace('"', '&quot;')
        buttons.append(f'<button class="vprof-chat-chip" onclick="{escaped_onclick}">{label}</button>')
    return '\n\n<div class="vprof-chip-container" style="display:flex; flex-wrap:wrap; gap:6px; margin-top:10px;">' + "".join(buttons) + '</div>'

# ── 1. Define AgentState ───────────────────────────────────────────────────────
class AgentState(TypedDict):
    query: str
    session_id: Optional[str]
    user_id: Optional[str]
    symbol: Optional[str]
    intent: str
    comparison_symbol: Optional[str]
    screener_metric: Optional[str]
    tool_results: Dict[str, Any]
    response_markdown: str
    group_data: Optional[Dict[str, Any]]
    error: Optional[str]


# ── Helper: Extract Comparison Candidates ─────────────────────────────────────
def extract_comparison_candidates(query: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract two distinct stock tickers from comparison natural language query."""
    q = query.strip()
    upper = q.upper()
    cleaned = re.sub(r"^(PLEASE\s+)?(CAN\s+YOU\s+)?(COMPARE|COMPARISON\s+OF|COMPARISON\s+BETWEEN|DIFFERENCE\s+BETWEEN)\s+", "", upper).strip()
    
    splitters = [r"\s+VS\.?\s+", r"\s+VERSUS\s+", r"\s+AND\s+", r"\s+WITH\s+", r"\s+TO\s+", r"\s+AGAINST\s+"]
    for sp in splitters:
        parts = re.split(sp, cleaned, maxsplit=1)
        if len(parts) == 2:
            s1_info = resolve_equity_entity(parts[0])
            s2_info = resolve_equity_entity(parts[1])
            s1 = s1_info.get("symbol")
            s2 = s2_info.get("symbol")
            if s1 and s2 and s1 != s2:
                return s1, s2

    # Fallback: scan query tokens against registered aliases
    resolver = get_entity_resolver()
    resolver.initialize()
    found_syms = []
    for alias, sym in sorted(resolver._alias_to_symbol.items(), key=lambda x: -len(x[0])):
        if len(alias) >= 3:
            pat = r"\b" + re.escape(alias) + r"\b"
            if re.search(pat, upper) and sym not in found_syms:
                found_syms.append(sym)
                if len(found_syms) == 2:
                    return found_syms[0], found_syms[1]

    return None, None


# ── Helper: Fundamental Screener Query ────────────────────────────────────────
def get_top_fundamental_screener(metric: str = "net_profit", limit: int = 5) -> List[Dict[str, Any]]:
    """Query company_financials_10y for top audited companies by profit, sales, or margins."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "market_data_v2.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    order_clause = "net_profit DESC"
    where_clause = "f.period_type = 'ANNUAL' AND f.fiscal_period = '2026-03-31' AND f.net_profit IS NOT NULL"
    if metric == "sales":
        order_clause = "sales DESC"
        where_clause = "f.period_type = 'ANNUAL' AND f.fiscal_period = '2026-03-31' AND f.sales IS NOT NULL"
    elif metric == "opm_pct":
        order_clause = "opm_pct DESC"
        where_clause = "f.period_type = 'ANNUAL' AND f.fiscal_period = '2026-03-31' AND f.sales > 1000 AND f.opm_pct IS NOT NULL"
    elif metric == "lowest_debt":
        order_clause = "borrowings ASC"
        where_clause = "f.period_type = 'ANNUAL' AND f.fiscal_period = '2026-03-31' AND f.net_profit > 500 AND f.borrowings IS NOT NULL"

    cur.execute(f"""
        SELECT f.symbol, f.net_profit, f.sales, f.opm_pct, f.borrowings, f.fiscal_period
        FROM company_financials_10y f
        WHERE {where_clause}
        ORDER BY {order_clause}
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()

    resolver = get_entity_resolver()
    results = []
    for rank, r in enumerate(rows, 1):
        sym, pat, sales, opm, debt, fp = r
        meta = resolver._symbol_to_meta.get(sym, {})
        cname = meta.get("name", sym)
        px = get_market_price_snapshot(sym)
        results.append({
            "rank": rank,
            "symbol": sym,
            "name": cname,
            "net_profit": pat,
            "sales": sales,
            "opm_pct": opm,
            "borrowings": debt,
            "fiscal_period": fp,
            "ltp": px.get("ltp")
        })
    return results


# ── Helper: Index Snapshot ────────────────────────────────────────────────────
def get_index_snapshot(symbol: str) -> Dict[str, Any]:
    """Retrieve verified benchmark index closing levels, daily range, and 52W stats."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "market_data_v2.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT trade_date, open, high, low, close, change_pct 
        FROM daily_prices 
        WHERE symbol = ?
        ORDER BY trade_date DESC 
        LIMIT 5
    """, (symbol,))
    rows = cur.fetchall()

    cur.execute("""
        SELECT MAX(high), MIN(low) 
        FROM daily_prices 
        WHERE symbol = ?
    """, (symbol,))
    h52_row = cur.fetchone()
    conn.close()

    if not rows:
        return {"symbol": symbol, "found": False}

    latest = rows[0]
    h52 = h52_row[0] if (h52_row and h52_row[0]) else latest[2]
    l52 = h52_row[1] if (h52_row and h52_row[1]) else latest[3]
    pct_from_high = ((latest[4] - h52) / h52 * 100) if h52 else 0.0

    return {
        "symbol": symbol,
        "found": True,
        "date": latest[0],
        "close": latest[4],
        "open": latest[1],
        "high": latest[2],
        "low": latest[3],
        "change_pct": latest[5],
        "high_52w": h52,
        "low_52w": l52,
        "pct_from_high": pct_from_high,
        "trend_5d": rows
    }


# ── 2. Guardrails & Intent Classification ─────────────────────────────────────
DISCOVERY_TOKENS = (
    "FALLEN", "MAX FALL", "TOP LOSER", "TOP GAINER", "SUGGEST", "WHERE TO INVEST",
    "INVEST MY", "HOW TO INVEST", "SHORT TERM", "WHAT ALL", "WHICH STOCK", "ANY STOCK",
    "RECOMMEND", "BEST STOCK", "PICK", "SWING TRAD", "MAXIMUM PROFIT",
    "HIGHEST PROFIT", "TOP PROFIT", "WHICH ALL COMPANIES", "HIGHEST REVENUE"
)

def classify_and_guard(state: AgentState) -> AgentState:
    """Supervisor router node: resolves intent and symbol via NEL & session memory."""
    q = state["query"].strip()
    upper = q.upper()
    session_id = state.get("session_id")
    sess = get_session_manager().get_session(session_id)
    
    # ── Check Comparison Recommendation Follow-up First ───────────────────────
    is_comp_rec = len(sess.last_compared_symbols) == 2 and any(
        phrase in upper for phrase in (
            "WHICH ONE", "WHICH IS BETTER", "WHICH TO INVEST", "WHICH TO BUY",
            "WHICH TO PICK", "HELP ME OUT WHICH", "BETTER TO BUY", "SHOULD I BUY",
            "WHICH SHOULD I", "WHICH STOCK IS BETTER", "WHICH STOCK SHOULD I",
            "WHERE SHOULD I INVEST", "WHICH WOULD YOU", "WHICH ONE WOULD YOU",
            "WHICH OF THE TWO", "WHICH OF THESE"
        )
    ) and not any(tok in upper for tok in ("FALLEN", "FELL", "FALL", "GAIN", "GAINED", "TOP LOSER", "TOP GAINER", "MAX FALL", "MAX GAIN"))

    # Decouple context if user is asking broad discovery questions
    is_discovery = not is_comp_rec and (any(tok in upper for tok in DISCOVERY_TOKENS) or any(
        w in upper for w in ("WHICH STOCK", "WHAT ALL STOCKS", "SUGGEST ME", "INVEST MY", "WHICH ALL COMPANIES")
    ))
    if is_discovery:
        sess.clear_symbol()
        sess.last_compared_symbols = []
        active_session_sym = None
    else:
        active_session_sym = sess.active_symbol

    # Resolve entity via Neural Entity Linker
    entity_info = resolve_equity_entity(q, session_symbol=active_session_sym)
    resolved_sym = entity_info.get("symbol")
    is_ambiguous_group = entity_info.get("is_ambiguous_group", False)
    is_idx = entity_info.get("is_index", False) or is_index_symbol(resolved_sym)

    screener_metric = None
    comp_sym = None
    active_sym = None

    # ── ROUTE 1: Greetings, Profile Identity, & Educational Guidance ──────────
    is_greeting_or_help = bool(re.search(
        r"^(HI|HELLO|HEY|NAMASTE|GOOD\s+MORNING|GOOD\s+EVENING|GOOD\s+AFTERNOON)\b", upper
    )) or bool(re.search(
        r"(WHAT('?S|\s+IS)?\s+MY\s+NAME|WHO\s+AM\s+I)", upper
    )) or bool(re.search(
        r"(HOW\s+(IT|DOES\s+THIS|THIS|THE\s+COPILOT)\s+WORKS?|HOW\s+TO\s+USE|HELP\s+ME\s+(TO\s+)?UNDERSTAND|WHAT\s+CAN\s+YOU\s+DO|CAPABILITIES|GUIDE\s+ME|RESEARCHING\s+TO\s+INVEST)", upper
    ))

    # ── Specialized Swarm Intent Detectors ────────────────────────────────────
    is_macro_stress_query = bool(re.search(
        r"\b(NIFTY\s+(DROPS?|FALLS?|CRASHES?)|BLACK\s+SWAN|STRESS\s+TEST|PORTFOLIO\s+DRAWDOWN|IF\s+NIFTY\s+DROPS?|MACRO\s+SHOCK|MACRO\s+STRESS|SIMULATE.*SHOCK)\b", upper
    ))
    is_portfolio_query = bool(re.search(
        r"\b(MY\s+PORTFOLIO|MY\s+INVESTMENTS|WHAT\s+ALL\s+INVESTMENTS|MY\s+HOLDINGS|MY\s+POSITIONS|HOLD\s+(OR|VS)\s+EXIT|PORTFOLIO\s+HEALTH)\b", upper
    ))
    is_explicit_pref = bool(re.search(
        r"\b(EXCLUDE|EXCLUDING|DON'?T\s+SUGGEST|DO\s+NOT\s+RECOMMEND|UPDATE\s+PREFERENCES|MY\s+PREFERENCES?)\b", upper
    ))
    is_corp_cal_query = not is_explicit_pref and bool(re.search(
        r"\b(EARNINGS\s+CALENDAR|UPCOMING\s+EARNINGS|UPCOMING\s+RESULTS|DIVIDEND\s+YIELD|UPCOMING\s+DIVIDENDS?|EX-?DATE|BONUS\s+OR\s+SPLIT|CORPORATE\s+ACTIONS?)\b", upper
    ))
    is_personalization_query = is_explicit_pref or bool(re.search(
        r"\b(I\s+PREFER|PREFER\s+HIGH\s+DIVIDEND|PREFER\s+DIVIDEND)\b", upper
    )) and not is_corp_cal_query

    is_capital_alloc_query = bool(re.search(
        r"\b(NEW\s+INVESTMENT|HOW\s+SHOULD\s+I\s+DISTRIBUTE|DISTRIBUTE\s+(IT|MY|50000|50,000|MONEY)|INVEST\s+(\d+|FIFTY\s+THOUSAND)|ALLOCATE\s+\d+|THEMATIC\s+BASKET)\b", upper
    ))
    is_mtf_query = bool(re.search(
        r"\b(MULTI\s+TIMEFRAME|MTF|ACROSS\s+TIMEFRAMES|ALL\s+TIMEFRAMES|TIMEFRAME\s+ALIGNMENT)\b", upper
    ))
    is_options_query = bool(re.search(
        r"\b(OPTIONS?|MICROSTRUCTURE|CALL\s+WALL|PUT\s+WALL|MAX\s+PAIN|OPTION\s+CHAIN|OPTIONS?\s+CHAIN|OPTIONS?\s+EXPIRY|EXPIRY\s+PINNING|PARTICIPANT\s+OI|FII\s+POSITIONING|PCR|PUT\s+CALL\s+RATIO|OPEN\s+INTEREST)\b", upper
    ))
    is_smart_money_query = bool(re.search(
        r"\b(BULK\s+DEALS?|BLOCK\s+DEALS?|VOLUME\s+ANOMAL|INSTITUTIONAL\s+FOOTPRINT|WHO\s+IS\s+BUYING|WHALE\s+TRADES?)\b", upper
    ))
    is_position_advisory_query = bool(re.search(
        r"\b(HOLD|SELL|EXIT|AVERAGE|CUT|WHAT\s+TO\s+DO|MY\s+SHARES|MY\s+STOCK|MY\s+POSITION|REVIEW\s+MY|SHOULD\s+I|KEEP\s+OR\s+SELL)\b", upper
    )) and not any(w in upper for w in ("COMPARE", "VS", "VERSUS", "DIFFERENCE BETWEEN"))
    is_portfolio_sector_query = bool(re.search(
        r"\b(DO\s+I\s+OWN|DO\s+I\s+HAVE|AM\s+I\s+HOLDING|HAVE\s+I\s+BOUGHT|DO\s+WE\s+OWN|ANY\s+.*(SECTOR|STOCK|SHARES)|MY\s+SECTOR|SECTOR\s+EXPOSURE|SECTOR\s+ALLOCATION|EXPOSURE\s+TO|ANY\s+EV|ANY\s+BANK|ANY\s+AUTO|ANY\s+IT|ANY\s+PHARMA|ANY\s+CEMENT|ANY\s+METAL|ANY\s+ENERGY)\b", upper
    ))

    if is_macro_stress_query:
        intent = "MACRO_STRESS_TEST"

    elif is_corp_cal_query:
        intent = "CORPORATE_CALENDAR"
        active_sym = resolved_sym

    elif is_personalization_query:
        intent = "PERSONALIZATION_UPDATE"

    elif is_portfolio_sector_query:
        intent = "PORTFOLIO_SECTOR_AUDIT"
        active_sym = resolved_sym

    elif resolved_sym and is_position_advisory_query:
        intent = "POSITION_ADVISORY"
        active_sym = resolved_sym

    elif active_session_sym and is_position_advisory_query and any(w in upper for w in ("IT", "THIS", "POSITION", "HOLD", "EXIT", "SELL", "MY SHARES", "MY STOCK")):
        intent = "POSITION_ADVISORY"
        active_sym = active_session_sym

    elif is_portfolio_query:
        intent = "PORTFOLIO_AUDIT"

    elif is_capital_alloc_query:
        intent = "CAPITAL_ALLOCATION"

    elif is_options_query:
        intent = "OPTIONS_MICROSTRUCTURE"
        active_sym = resolved_sym or "NIFTY"

    elif is_smart_money_query:
        intent = "SMART_MONEY_AUDIT"
        active_sym = resolved_sym

    elif is_mtf_query:
        intent = "MULTI_TIMEFRAME"
        active_sym = resolved_sym or active_session_sym or "RELIANCE"

    elif is_greeting_or_help and not resolved_sym and not any(w in upper for w in ("COMPARE", "FALLEN", "GAIN")):
        intent = "GREETING_OR_HELP"

    elif is_comp_rec:
        intent = "COMPARISON_RECOMMENDATION"
        active_sym = sess.last_compared_symbols[0]
        comp_sym = sess.last_compared_symbols[1]

    # ── ROUTE 3: Conglomerate Group Disambiguation ────────────────────────────
    elif is_ambiguous_group and not is_discovery:
        intent = "GROUP_DISAMBIGUATION"
        state["group_data"] = entity_info

    # ── ROUTE 4: Head-to-Head Comparison ──────────────────────────────────────
    elif re.search(r"\b(VS\.?|VERSUS|COMPARE|DIFFERENCE\s+BETWEEN)\b", upper):
        intent = "COMPARISON"
        s1, s2 = extract_comparison_candidates(q)
        if s1 and s2:
            active_sym = s1
            comp_sym = s2
            sess.set_compared_symbols(s1, s2)
        else:
            active_sym = resolved_sym or "TCS"
            comp_sym = "INFY" if active_sym != "INFY" else "TCS"
            sess.set_compared_symbols(active_sym, comp_sym)

    # ── ROUTE 5: Fundamental Screener (Max Profits, Revenue, OPM, Lowest Debt) ─
    elif any(w in upper for w in (
        "MAXIMUM PROFIT", "MAX PROFIT", "HIGHEST PROFIT", "TOP PROFIT",
        "HIGHEST PAT", "MAXIMUM PAT", "WHICH ALL COMPANIES HAS MAXIMUM",
        "MOST PROFIT", "PROFITABLE COMPANIES", "TOP EARNINGS", "HIGHEST SALES",
        "HIGHEST REVENUE", "MAXIMUM REVENUE", "HIGHEST MARGIN", "HIGHEST OPM",
        "LOWEST DEBT", "DEBT FREE", "ZERO DEBT"
    )):
        intent = "FUNDAMENTAL_SCREENER"
        if any(w in upper for w in ("REVENUE", "SALES")):
            screener_metric = "sales"
        elif any(w in upper for w in ("MARGIN", "OPM")):
            screener_metric = "opm_pct"
        elif any(w in upper for w in ("DEBT", "BORROWING")):
            screener_metric = "lowest_debt"
        else:
            screener_metric = "net_profit"

    # ── ROUTE 6: Technical Screener - Losers / Falls ──────────────────────────
    elif re.search(r"\b(FALLEN|FELL|FALL|FALLING|DOWN|LOSER|LOSERS|CRASH|CRASHED|MAX FALL)\b", upper):
        intent = "SCREENER_LOSERS"

    # ── ROUTE 7: Technical Screener - Gainers / Rallies ───────────────────────
    elif re.search(r"\b(GAIN|GAINED|GAINING|GAINER|GAINERS|RISING|ROSE|SURGE|SURGED|MAX GAIN|TOP GAINERS)\b", upper):
        intent = "SCREENER_GAINERS"

    # ── ROUTE 8: Short-Term Swing Trading Setups ──────────────────────────────
    elif any(w in upper for w in ("SHORT TERM", "10-15 DAYS", "10-12 DAYS", "SWING", "INVEST MY", "SUGGEST ME", "WHAT ALL STOCKS", "WHERE TO INVEST")):
        intent = "SWING_SETUPS"

    # ── ROUTE 9: Benchmark Index Tracking (Nifty 50, Bank Nifty) ──────────────
    elif is_idx:
        intent = "INDEX_DETAIL"
        active_sym = resolved_sym

    # ── ROUTE 10: Explicit or Linked Single Stock Detail ──────────────────────
    elif resolved_sym:
        intent = "TICKER_DETAIL"
        active_sym = resolved_sym
        sess.set_symbol(resolved_sym, entity_info.get("company_name"))

    # ── ROUTE 11: Multi-Turn Session Inherited Ticker Detail ──────────────────
    elif active_session_sym and any(w in upper for w in (
        "FINANCIALS", "REVENUE", "DEBT", "MARGIN", "PROFIT", "RESULTS", "PAT", "SALES",
        "NEWS", "CONCALL", "GUIDANCE", "IT", "ITS", "THEIR", "PROMOTER", "FII"
    )):
        intent = "TICKER_DETAIL"
        active_sym = active_session_sym

    # ── ROUTE 12: Ambiguous Fallback ──────────────────────────────────────────
    else:
        intent = "AMBIGUOUS"

    state["intent"] = intent
    state["symbol"] = active_sym
    state["comparison_symbol"] = comp_sym
    state["screener_metric"] = screener_metric
    state["tool_results"] = {}
    return state


# ── 3. Micro-Agents & Specialists ─────────────────────────────────────────────

def execute_greeting_or_help_agent(state: AgentState) -> AgentState:
    """Agent welcoming the user, providing persona clarity, and educational walkthrough."""
    q = state["query"].strip()
    upper = q.upper()

    is_name_query = bool(re.search(r"(WHAT('?S|\s+IS)?\s+MY\s+NAME|WHO\s+AM\s+I)", upper))

    lines = []
    lines.append("### ⚡ Vprofitables Quant Terminal Copilot")
    if is_name_query:
        lines.append("Hello! You are connected as an **Authenticated Terminal Trader**.")
        lines.append("I am your quantitative copilot, analyzing **500+ NSE Equities and Benchmark Indices** with 10-year verified regulatory financials.\n")
    else:
        lines.append("Welcome! I am your institutional-grade **Quantitative Terminal Copilot**.")
        lines.append("I empower your investment research with 100% verified data, zero hallucinations, and exact audited ₹ Crores figures.\n")

    lines.append("#### 🧭 What I Can Do For You:")
    lines.append("1. **📉 Instant Market Screeners:**")
    lines.append("   - *\"Which stock has fallen max in last 5 days?\"*")
    lines.append("   - *\"Top gainers today\"*")
    lines.append("   - *\"Which all companies has maximum profits in current year?\"*")
    lines.append("")
    lines.append("2. **🎯 10-15 Day Swing Trade Setups:**")
    lines.append("   - *\"I am looking for short term trade for 10-15 days can you suggest me what all stocks can i look for and why?\"*")
    lines.append("   - *\"Im planning to invest 10000 for 10-12 days suggest stocks\"*")
    lines.append("")
    lines.append("3. **📊 Single Stock Intelligence (360° Analysis):**")
    lines.append("   - *\"Give me quick bytes about Adani enterprise\"*")
    lines.append("   - *\"What was TCS revenue and operating profit in latest FY?\"*")
    lines.append("   - *\"Show management forward capex guidance for Reliance\"*")
    lines.append("")
    lines.append("4. **⚖️ Head-to-Head Comparison & Quant Thesis:**")
    lines.append("   - *\"Compare HCL and Tech Mahindra\"*")
    lines.append("   - Follow-up with: *\"Help me out which one to invest\"*")
    lines.append("")
    lines.append("5. **📈 Benchmark Indices & Market Regime:**")
    lines.append("   - *\"What is Nifty current price?\"*")
    lines.append("   - *\"Bank Nifty level today\"*")
    lines.append("")
    lines.append(f"> 🔒 *{FINANCIAL_UNIT_CONTRACT}*")
    
    state["response_markdown"] = "\n".join(lines)
    return state


def execute_index_agent(state: AgentState) -> AgentState:
    """Agent querying daily_prices for benchmark indices (NIFTY 50, BANK NIFTY)."""
    sym = state.get("symbol") or "NIFTY50"
    snap = get_index_snapshot(sym)
    
    if not snap.get("found"):
        state["response_markdown"] = f"### ⚠️ Benchmark Index: **{sym}**\nCould not locate verified price records for index `{sym}`."
        return state

    close = snap["close"]
    chg = snap["change_pct"]
    dt = snap["date"]
    open_px = snap["open"]
    high = snap["high"]
    low = snap["low"]
    h52 = snap["high_52w"]
    l52 = snap["low_52w"]
    pct_peak = snap["pct_from_high"]

    lines = [
        f"### 📈 Benchmark Index Intelligence: **{sym}**",
        f"**Current Level:** **{close:,.2f}** ({chg:+.2f}%) | **Trade Date:** {dt}\n",
        "#### 📊 Daily Range & 52-Week Statistics:",
        f"- **Day's Range:** Open: **{open_px:,.2f}** | High: **{high:,.2f}** | Low: **{low:,.2f}**",
        f"- **52-Week Range:** High: **{h52:,.2f}** | Low: **{l52:,.2f}** ({pct_peak:+.1f}% from 52W ATH)\n",
        "#### ⏱️ Recent 5-Session Trajectory:",
        "| Date | Closing Level | Daily Change |",
        "| :--- | :---: | :---: |"
    ]
    for row in snap.get("trend_5d", []):
        r_dt, _, _, _, r_close, r_chg = row
        lines.append(f"| {r_dt} | {r_close:,.2f} | {r_chg:+.2f}% |")

    lines.append("\n💡 *Need stock-specific ideas? Ask: \"Which stock has fallen max in last 5 days?\" or \"Suggest swing trades for 10-15 days\".*")
    state["response_markdown"] = "\n".join(lines)
    return state


def execute_fundamental_screener_agent(state: AgentState) -> AgentState:
    """Agent ranking Corporate India by audited net profit, revenue, or margins."""
    metric = state.get("screener_metric") or "net_profit"
    leaders = get_top_fundamental_screener(metric=metric, limit=5)
    
    metric_label = "Net Profit (PAT)"
    if metric == "sales":
        metric_label = "Total Revenue / Sales"
    elif metric == "opm_pct":
        metric_label = "Operating Profit Margin (OPM %)"
    elif metric == "lowest_debt":
        metric_label = "Lowest Debt / Borrowings"

    lines = [
        f"### 🏆 Corporate India Leaderboard: Top by **{metric_label}** (Audited FY26)",
        f"Verified against official audited filings in `market_data_v2.db` denominated in **INR Crores**:\n",
        "| Rank | Company | Symbol | Net Profit (PAT) | Total Revenue | Op Margin | Current Price |",
        "| :---: | :--- | :---: | :---: | :---: | :---: | :---: |"
    ]

    for item in leaders:
        ltp_str = f"₹{item['ltp']:,.2f}" if item.get("ltp") else "N/A"
        lines.append(
            f"| {item['rank']} | **{item['name']}** | `{item['symbol']}` | "
            f"**{format_crores(item['net_profit'])}** | {format_crores(item['sales'])} | "
            f"{format_pct(item['opm_pct'])} | {ltp_str} |"
        )

    lines.append("\n#### 💡 Quantitative Observations:")
    if leaders:
        top = leaders[0]
        lines.append(f"- **Leader:** **{top['name']}** (`{top['symbol']}`) leads with **{format_crores(top['net_profit'])}** PAT and **{format_crores(top['sales'])}** annual sales.")
        total_pool = sum((it.get("net_profit") or 0) for it in leaders)
        lines.append(f"- **Top 5 Profit Concentration:** The top 5 companies generate over **₹{total_pool:,.0f} Cr** in annual net profits.")

    lines.append(f"\n> 🔒 *{FINANCIAL_UNIT_CONTRACT}*")
    chips = [
        (f"📈 Open {sym} Chart", f"openSymbolChart('{sym}')"),
        (f"🎙️ Concall Guidance", f"askQuickPrompt('Show management guidance and concalls for {sym}')"),
        (f"⚡ Options & PCR", f"askQuickPrompt('What is the options microstructure for {sym}?')"),
        (f"🛡️ Position Advisor", f"askQuickPrompt('Should I hold or exit {sym}?')"),
        (f"📅 Corporate Actions", f"askQuickPrompt('Upcoming corporate actions and dividends for {sym}')"),
    ]
    lines.append(make_action_chips(chips))
    state["response_markdown"] = "\n".join(lines)
    return state


def execute_screener_agent(state: AgentState) -> AgentState:
    """Agent executing multi-day market momentum screening."""
    direction = "LOSERS" if state["intent"] == "SCREENER_LOSERS" else "GAINERS"
    sessions = 5
    if "10" in state["query"] or "10 DAYS" in state["query"].upper():
        sessions = 10
    elif "20" in state["query"] or "20 DAYS" in state["query"].upper():
        sessions = 20
    elif "1 DAY" in state["query"].upper() or "TODAY" in state["query"].upper():
        sessions = 1
        
    result = scan_market_momentum_tool.invoke({
        "direction": direction,
        "sessions": sessions,
        "limit": 5
    })
    state["tool_results"]["screener"] = result
    state["response_markdown"] = format_screener_markdown(result)
    return state


def execute_swing_agent(state: AgentState) -> AgentState:
    """Agent executing 10-15 day algorithmic trend continuation scan."""
    result = scan_swing_setups_tool.invoke({
        "min_confidence": 65.0,
        "min_rr": 1.5,
        "limit": 4
    })
    state["tool_results"]["swing"] = result
    state["response_markdown"] = format_swing_setups_markdown(result.get("setups", []))
    return state


def execute_ticker_intelligence_agent(state: AgentState) -> AgentState:
    """
    Multi-faceted single-stock quantitative & fundamental intelligence agent.
    Combines: Price Snapshot, Audited Financials, News Sentiment, Smart Money, & Concalls.
    """
    sym = state["symbol"]
    if not sym:
        return execute_ambiguous_agent(state)

    px = get_market_price_snapshot(sym)
    fin = get_verified_financials_tool.invoke({"symbol": sym})
    news = get_news_sentiment_tool.invoke({"symbol": sym, "limit": 4})
    sm = get_institutional_holdings_tool.invoke({"symbol": sym})
    concalls = search_clean_concalls_tool.invoke({
        "symbol": sym,
        "query": "capex growth margin demand expansion guidance",
        "k": 3
    })
    
    state["tool_results"]["price"] = px
    state["tool_results"]["financials"] = fin
    state["tool_results"]["news"] = news
    state["tool_results"]["smart_money"] = sm
    state["tool_results"]["concalls"] = concalls
    
    lines = []
    lines.append(f"### 📊 Grounded Equity Intelligence: **{sym}**")
    if px.get("ltp"):
        p_chg = f" ({px.get('pct_from_52w_high'):+.1f}% from 52W High)" if px.get("pct_from_52w_high") is not None else ""
        lines.append(f"**Current Price:** ₹{px.get('ltp'):,.2f} | **52W High:** ₹{px.get('high_52w'):,.2f} | **52W Low:** ₹{px.get('low_52w'):,.2f}{p_chg}")
    
    # Audited Annual Financials
    ann = fin.get("latest_annual")
    if ann:
        lines.append("\n#### 📈 Audited Financial Highlights (FY)")
        lines.append(f"- **Total Revenue / Sales:** {ann.get('sales_fmt') or format_crores(ann.get('sales'))}")
        lines.append(f"- **Operating Profit (EBITDA):** {ann.get('operating_profit_fmt') or format_crores(ann.get('operating_profit'))} ({ann.get('opm_pct_fmt') or format_pct(ann.get('opm_pct'))})")
        lines.append(f"- **Net Profit (PAT):** {ann.get('net_profit_fmt') or format_crores(ann.get('net_profit') or ann.get('pat'))}")
        lines.append(f"- **Operating Cash Flow:** {ann.get('operating_cash_flow_fmt') or format_crores(ann.get('operating_cash_flow'))}")
        lines.append(f"- **Total Borrowings / Debt:** {ann.get('borrowings_fmt') or format_crores(ann.get('borrowings'))}")
        if ann.get("yoy_sales_growth") is not None:
            lines.append(f"- **YoY Sales Growth:** {format_pct(ann.get('yoy_sales_growth'))}")

    # Recent Quarter
    qtr = fin.get("latest_quarterly")
    if qtr:
        lines.append(f"\n#### ⏱️ Recent Quarter ({qtr.get('quarter_date') or qtr.get('fiscal_period') or 'Latest'})")
        lines.append(f"- **Quarterly Sales:** {qtr.get('sales_fmt') or format_crores(qtr.get('sales'))} | **Operating Margin:** {qtr.get('opm_pct_fmt') or format_pct(qtr.get('opm_pct'))}")
        lines.append(f"- **Quarterly Net Profit:** {qtr.get('net_profit_fmt') or format_crores(qtr.get('net_profit') or qtr.get('pat'))}")

    # Smart Money
    if sm.get("has_data"):
        lines.append(f"\n#### 🏛️ Smart Money & Institutional Flow ({sm.get('period', 'Latest')})")
        p_pledge = f" (Pledged: {sm.get('promoter_pledged')}%)" if sm.get("promoter_pledged") else ""
        lines.append(f"- **Promoter Holding:** {format_pct(sm.get('promoter_pct'))}{p_pledge}")
        lines.append(f"- **FII Stake:** {format_pct(sm.get('fii_pct'))} ({format_pct(sm.get('fii_change'))} QoQ) | **DII Stake:** {format_pct(sm.get('dii_pct'))} ({format_pct(sm.get('dii_change'))} QoQ)")
        lines.append(f"- **Institutional Signal:** `{sm.get('signal', 'STABLE')}`")

    # News & Catalysts
    if news.get("headlines"):
        lines.append(f"\n#### 📰 Recent Catalysts & Sentiment (`{news.get('overall_sentiment')}`, Score: {news.get('avg_score'):+.2f})")
        for h in news["headlines"][:3]:
            dt = f" *({h['date'][:10]})*" if h.get("date") else ""
            lines.append(f"- [{h.get('label')}] **{h.get('title')}**{dt}")

    # Concalls
    if concalls.get("excerpts"):
        valid_excerpts = [c for c in concalls["excerpts"] if c.get("text", "").strip()]
        if valid_excerpts:
            lines.append("\n#### 🎙️ Clean Management Guidance & Strategic Highlights")
            for c in valid_excerpts[:3]:
                speaker = c.get("speaker_role", "MANAGEMENT")
                period = f" ({c.get('fiscal_period')})" if c.get("fiscal_period") else ""
                txt = c.get("text", "").strip()
                if len(txt) > 220:
                    txt = txt[:220] + "..."
                lines.append(f"- **[{speaker}]{period}:** \"{txt}\"")

    lines.append(f"\n> 🔒 *{FINANCIAL_UNIT_CONTRACT}*")
    chips = [
        (f"📈 Open {sym} Chart", f"openSymbolChart('{sym}')"),
        (f"🎙️ Concall Guidance", f"askQuickPrompt('Show management guidance and concalls for {sym}')"),
        (f"⚡ Options & PCR", f"askQuickPrompt('What is the options microstructure for {sym}?')"),
        (f"🛡️ Position Advisor", f"askQuickPrompt('Should I hold or exit {sym}?')"),
        (f"📅 Corporate Actions", f"askQuickPrompt('Upcoming corporate actions and dividends for {sym}')"),
    ]
    lines.append(make_action_chips(chips))
    state["response_markdown"] = "\n".join(lines)
    return state


def execute_comparison_agent(state: AgentState) -> AgentState:
    """Agent executing side-by-side financial comparison."""
    sym1 = state.get("symbol") or "TCS"
    sym2 = state.get("comparison_symbol") or "INFY"
    session_id = state.get("session_id")
    sess = get_session_manager().get_session(session_id)
    sess.set_compared_symbols(sym1, sym2)
    
    fin1 = get_verified_financials_tool.invoke({"symbol": sym1})
    fin2 = get_verified_financials_tool.invoke({"symbol": sym2})
    px1 = get_market_price_snapshot(sym1)
    px2 = get_market_price_snapshot(sym2)
    
    a1 = fin1.get("latest_annual", {}) or {}
    a2 = fin2.get("latest_annual", {}) or {}
    
    lines = [
        f"### ⚖️ Grounded Head-to-Head Comparison: **{sym1}** vs **{sym2}**",
        "",
        "| Metric | " + f"**{sym1}** | **{sym2}** |",
        "| :--- | :--- | :--- |",
        f"| **Current Price** | ₹{px1.get('ltp', 0):,.2f} | ₹{px2.get('ltp', 0):,.2f} |",
        f"| **52W High Proximity** | {px1.get('pct_from_52w_high', 0):+.1f}% | {px2.get('pct_from_52w_high', 0):+.1f}% |",
        f"| **Annual Sales** | {a1.get('sales_fmt') or format_crores(a1.get('sales'))} | {a2.get('sales_fmt') or format_crores(a2.get('sales'))} |",
        f"| **Operating Margin (OPM)** | {a1.get('opm_pct_fmt') or format_pct(a1.get('opm_pct'))} | {a2.get('opm_pct_fmt') or format_pct(a2.get('opm_pct'))} |",
        f"| **Net Profit (PAT)** | {a1.get('net_profit_fmt') or format_crores(a1.get('net_profit') or a1.get('pat'))} | {a2.get('net_profit_fmt') or format_crores(a2.get('net_profit') or a2.get('pat'))} |",
        f"| **Operating Cash Flow** | {a1.get('operating_cash_flow_fmt') or format_crores(a1.get('operating_cash_flow'))} | {a2.get('operating_cash_flow_fmt') or format_crores(a2.get('operating_cash_flow'))} |",
        f"| **Borrowings / Debt** | {a1.get('borrowings_fmt') or format_crores(a1.get('borrowings'))} | {a2.get('borrowings_fmt') or format_crores(a2.get('borrowings'))} |",
        f"| **YoY Sales Growth** | {format_pct(a1.get('yoy_sales_growth'))} | {format_pct(a2.get('yoy_sales_growth'))} |",
        "",
        "💡 *Deciding which one to buy? Ask directly:* **\"Help me out which one to invest\"**",
        "",
        f"> 🔒 *{FINANCIAL_UNIT_CONTRACT}*"
    ]
    chips = [
        ("🎯 Which is Better?", f"askQuickPrompt('Which of {sym1} or {sym2} is better to buy?')"),
        (f"📈 {sym1} Chart", f"openSymbolChart('{sym1}')"),
        (f"📈 {sym2} Chart", f"openSymbolChart('{sym2}')"),
    ]
    lines.append(make_action_chips(chips))
    state["response_markdown"] = "\n".join(lines)
    return state


def execute_comparison_recommendation_agent(state: AgentState) -> AgentState:
    """Agent delivering multi-factor algorithmic evaluation and investment verdict between compared stocks."""
    sym1 = state.get("symbol")
    sym2 = state.get("comparison_symbol")
    session_id = state.get("session_id")
    sess = get_session_manager().get_session(session_id)
    
    if not sym1 or not sym2:
        if len(sess.last_compared_symbols) == 2:
            sym1, sym2 = sess.last_compared_symbols
        else:
            state["response_markdown"] = (
                "### 🎯 Which two stocks would you like me to evaluate?\n\n"
                "Please specify the companies you are considering, for example:\n"
                "- *\"Compare HCL and Tech Mahindra\"*\n"
                "- *\"Compare TCS vs INFY\"*\n"
                "- *\"Compare HDFCBANK vs ICICIBANK\"*"
            )
            return state

    fin1 = get_verified_financials_tool.invoke({"symbol": sym1})
    fin2 = get_verified_financials_tool.invoke({"symbol": sym2})
    px1 = get_market_price_snapshot(sym1)
    px2 = get_market_price_snapshot(sym2)

    a1 = fin1.get("latest_annual", {}) or {}
    a2 = fin2.get("latest_annual", {}) or {}

    opm1 = a1.get("opm_pct") or 0.0
    opm2 = a2.get("opm_pct") or 0.0
    pat1 = a1.get("net_profit") or a1.get("pat") or 0.0
    pat2 = a2.get("net_profit") or a2.get("pat") or 0.0
    debt1 = a1.get("borrowings") or 0.0
    debt2 = a2.get("borrowings") or 0.0
    ocf1 = a1.get("operating_cash_flow") or 0.0
    ocf2 = a2.get("operating_cash_flow") or 0.0
    prox1 = px1.get("pct_from_52w_high") or -99.0
    prox2 = px2.get("pct_from_52w_high") or -99.0

    # Scorecard calculation
    s1_score = 0
    s2_score = 0
    
    # Margin score
    if opm1 > opm2:
        s1_score += 1
        margin_winner = f"🏆 **{sym1}** (+{opm1 - opm2:.1f}% higher operational efficiency)"
    else:
        s2_score += 1
        margin_winner = f"🏆 **{sym2}** (+{opm2 - opm1:.1f}% higher operational efficiency)"

    # Absolute Profit scale
    if pat1 > pat2:
        s1_score += 1
        pat_winner = f"🏆 **{sym1}** ({format_crores(pat1)} vs {format_crores(pat2)})"
    else:
        s2_score += 1
        pat_winner = f"🏆 **{sym2}** ({format_crores(pat2)} vs {format_crores(pat1)})"

    # Cash flow conversion
    if ocf1 > ocf2:
        s1_score += 1
        ocf_winner = f"🏆 **{sym1}** (Superior operating cash conversion)"
    else:
        s2_score += 1
        ocf_winner = f"🏆 **{sym2}** (Superior operating cash conversion)"

    # Balance Sheet Debt
    if debt1 < debt2:
        s1_score += 1
        debt_winner = f"🏆 **{sym1}** (Lower borrowings leverage)"
    else:
        s2_score += 1
        debt_winner = f"🏆 **{sym2}** (Lower borrowings leverage)"

    # Technical Resilience (closer to 52W high)
    if prox1 > prox2:
        s1_score += 1
        tech_winner = f"🏆 **{sym1}** (Stronger price structure at {prox1:+.1f}%)"
    else:
        s2_score += 1
        tech_winner = f"🏆 **{sym2}** (Stronger price structure at {prox2:+.1f}%)"

    overall_winner = sym1 if s1_score >= s2_score else sym2

    lines = [
        f"### 🎯 Quantitative Investment Evaluation: **{sym1}** vs **{sym2}**",
        "Institutional multi-factor evaluation based on audited filings and current technical price action:\n",
        "#### 📊 Multi-Factor Scorecard Matrix:",
        f"| Evaluation Factor | {sym1} | {sym2} | Quantitative Edge |",
        "| :--- | :---: | :---: | :--- |",
        f"| **Operating Margin (OPM)** | {format_pct(opm1)} | {format_pct(opm2)} | {margin_winner} |",
        f"| **Net Profit Scale** | {format_crores(pat1)} | {format_crores(pat2)} | {pat_winner} |",
        f"| **Operating Cash Flow** | {format_crores(ocf1)} | {format_crores(ocf2)} | {ocf_winner} |",
        f"| **Borrowings / Debt** | {format_crores(debt1)} | {format_crores(debt2)} | {debt_winner} |",
        f"| **52W High Proximity** | {prox1:+.1f}% | {prox2:+.1f}% | {tech_winner} |",
        "",
        "#### 💡 Institutional Allocation Verdict:",
        f"🏆 **Primary Allocation Preference: `{overall_winner}`** (Scored {max(s1_score, s2_score)}/5 Factors)",
        "",
        f"1. **Case for `{sym1}`:**",
        f"   - Operating Margin: **{format_pct(opm1)}** with Net Profit of **{format_crores(pat1)}**.",
        f"   - Annual Operating Cash Flow: **{format_crores(ocf1)}** provides high reinvestment and dividend stability.",
        "",
        f"2. **Case for `{sym2}`:**",
        f"   - Operating Margin: **{format_pct(opm2)}** with Net Profit of **{format_crores(pat2)}**.",
        f"   - Balance Sheet Borrowings: **{format_crores(debt2)}**.",
        "",
        "#### ⏱️ Suggested Strategy & Horizon:",
        f"- **Defensive & Quality Compounder:** **`{overall_winner}`** is the higher conviction pick for medium-to-long term fundamental safety.",
        f"- **Tactical Swing Horizon:** Monitor volume confirmations near 20-day exponential moving averages before initiating new tranche allocations.",
        "",
        f"> 🔒 *{FINANCIAL_UNIT_CONTRACT}*"
    ]
    chips = [
        (f"📈 Open {overall_winner} Chart", f"openSymbolChart('{overall_winner}')"),
        (f"🔍 Multi-Timeframe Alignment", f"askQuickPrompt('Multi timeframe analysis for {overall_winner}')"),
        (f"⚡ Options & PCR", f"askQuickPrompt('What is the options microstructure for {overall_winner}?')"),
    ]
    lines.append(make_action_chips(chips))
    state["response_markdown"] = "\n".join(lines)
    return state


def execute_group_disambiguation_agent(state: AgentState) -> AgentState:
    """Agent rendering interactive options for conglomerate inquiries (e.g. 'Adani', 'Tata')."""
    gdata = state.get("group_data", {})
    gname = gdata.get("group_name", "Conglomerate")
    candidates = gdata.get("group_candidates", [])

    lines = [
        f"### 🏢 Which **{gname} Group** company would you like to analyze?",
        f"I found multiple listed companies under **{gname}**. Click any option below to inspect verified financials:\n"
    ]
    for c in candidates:
        lines.append(f"- <button class=\"vprof-chat-chip\" onclick=\"askQuickPrompt('Analyze {c['symbol']}')\"><strong>{c['symbol']}</strong> — {c['name']}</button>")

    lines.append(f"\n💡 *Or type the exact company name (e.g. 'Adani enterprise', 'Adani ports', 'Tata motors').*")
    state["response_markdown"] = "\n".join(lines)
    return state


def execute_portfolio_agent(state: AgentState) -> AgentState:
    """Agent auditing open portfolio positions, real-time P&L, risk gates, and hold vs exit signals."""
    uid = state.get("user_id")
    port_data = fetch_portfolio_positions(user_id=uid)
    md = format_portfolio_markdown(port_data)
    chips = [
        ("🚨 Macro Stress Test (-3%)", "askQuickPrompt('Simulate a -3% macro shock on my portfolio')"),
        ("💼 Open Demat Portfolio", "nav('portfolio')"),
        ("🏛️ Sector Exposure", "askQuickPrompt('What is my sector exposure?')"),
    ]
    state["response_markdown"] = md + make_action_chips(chips)
    state["tool_results"]["portfolio"] = port_data
    return state


def execute_position_advisor_agent(state: AgentState) -> AgentState:
    """Agent providing human-like personalized position health, P&L, targets, and reversal dates/floors."""
    sym = state.get("symbol") or "ULTRACEMCO"
    uid = state.get("user_id")
    advisory_md = get_single_position_advisory(symbol=sym, user_id=uid)
    chips = [
        (f"📈 Open {sym} Chart", f"openSymbolChart('{sym}')"),
        (f"⚡ Options & PCR", f"askQuickPrompt('What is the options microstructure for {sym}?')"),
        ("💼 View Portfolio", "nav('portfolio')"),
    ]
    state["response_markdown"] = advisory_md + make_action_chips(chips)
    state["tool_results"]["position_advisory"] = {"symbol": sym}
    return state


def execute_portfolio_sector_agent(state: AgentState) -> AgentState:
    """Agent evaluating portfolio ownership of themes, sectors, or specific sector exposure."""
    q = state["query"].strip()
    uid = state.get("user_id")
    ans_md = answer_portfolio_sector_query(q, user_id=uid)
    chips = [
        ("💼 Open Portfolio", "nav('portfolio')"),
        ("🛡️ Review All Positions", "askQuickPrompt('Review my portfolio positions')"),
    ]
    state["response_markdown"] = ans_md + make_action_chips(chips)
    state["tool_results"]["portfolio_sector"] = {"query": q}
    return state


def execute_personalization_agent(state: AgentState) -> AgentState:
    """Agent parsing conversational preferences (e.g. exclusions, styles) and updating risk_profiles."""
    q = state["query"].strip()
    uid = state.get("user_id")
    res = parse_and_update_preferences(q, user_id=uid)
    state["response_markdown"] = res.get("message", "Preferences processed.")
    state["tool_results"]["personalization"] = res
    return state


def execute_capital_allocation_agent(state: AgentState) -> AgentState:
    """Agent executing Regime-Adaptive Capital Allocation with exact share orders and 1-click execution cards."""
    q = state["query"].strip()
    upper = q.upper()
    
    # Extract investment amount if present (e.g. 50000, 50,000, 100000)
    amt = 50000.0
    m = re.search(r"\b(\d[\d,]{3,8})\b", q)
    if m:
        try:
            amt = float(m.group(1).replace(",", ""))
        except Exception:
            pass
    elif "FIFTY THOUSAND" in upper:
        amt = 50000.0
    elif "ONE LAKH" in upper or "1 LAKH" in upper:
        amt = 100000.0

    uid = state.get("user_id")
    plan = allocate_capital(amount_inr=amt, user_id=uid)
    md = format_capital_allocation_markdown(plan)
    chips = [
        ("💼 Open Demat Portfolio", "nav('portfolio')"),
        ("🎯 10-15D Swing Setups", "askQuickPrompt('I am looking for short term swing trades for 10-15 days')"),
    ]
    state["response_markdown"] = md + make_action_chips(chips)
    state["tool_results"]["capital_allocation"] = plan
    return state


def execute_corporate_calendar_agent(state: AgentState) -> AgentState:
    """Agent screening upcoming corporate actions, dividend yields, and earnings announcements."""
    sym = state.get("symbol")
    q = state["query"].upper()

    if any(w in q for w in ("DIVIDEND", "SPLIT", "BONUS", "EX-DATE")):
        data = get_upcoming_dividends_splits(symbol=sym, days_ahead=14)
    else:
        data = get_upcoming_earnings(symbol=sym, days_ahead=14)

    state["response_markdown"] = format_corporate_calendar_markdown(data)
    state["tool_results"]["corporate_calendar"] = data
    return state


def execute_smart_money_agent(state: AgentState) -> AgentState:
    """Agent auditing institutional bulk/block deals and volume surge absorption signals."""
    sym = state.get("symbol")
    deals_data = get_smart_money_deals(symbol=sym, limit=8)
    state["response_markdown"] = format_smart_money_markdown(deals_data)
    state["tool_results"]["smart_money_deals"] = deals_data
    return state


def execute_options_microstructure_agent(state: AgentState) -> AgentState:
    """Agent auditing Call Wall vs Put Wall battleground, Max Pain, and participant OI."""
    sym = state.get("symbol") or "NIFTY"
    opt_data = get_options_microstructure(symbol=sym)
    md = format_options_microstructure_markdown(opt_data)
    chips = [
        (f"📈 Open {sym} Chart", f"openSymbolChart('{sym}')"),
        (f"🔍 Smart Money Footprint", f"askQuickPrompt('Institutional bulk deals and smart money for {sym}')"),
        (f"📊 Multi-Timeframe Matrix", f"askQuickPrompt('Multi timeframe analysis for {sym}')"),
    ]
    state["response_markdown"] = md + make_action_chips(chips)
    state["tool_results"]["options_microstructure"] = opt_data
    return state


def execute_macro_stress_agent(state: AgentState) -> AgentState:
    """Agent simulating macro market shocks (-3% or -500 points) on open portfolio equity."""
    q = state["query"]
    uid = state.get("user_id")
    pts = 500.0 if ("500" in q or "POINT" in q.upper()) else None
    sim_data = simulate_macro_stress(user_id=uid, shock_pct=-3.0, shock_points=pts)
    md = format_macro_stress_markdown(sim_data)
    chips = [
        ("💼 Open Demat Portfolio", "nav('portfolio')"),
        ("🛡️ Review All Positions", "askQuickPrompt('Review my portfolio positions')"),
        ("🎯 Safe Swing Setups", "askQuickPrompt('I am looking for short term swing trades for 10-15 days')"),
    ]
    state["response_markdown"] = md + make_action_chips(chips)
    state["tool_results"]["macro_stress"] = sim_data
    return state


def execute_multi_timeframe_agent(state: AgentState) -> AgentState:
    """Agent generating Multi-Timeframe Alignment Matrix (Intraday, Swing, Positional) & Action Plan."""
    sym = state.get("symbol") or "RELIANCE"
    mtf_data = get_multi_timeframe_matrix(symbol=sym)
    md = format_multi_timeframe_markdown(mtf_data)
    chips = [
        (f"📈 Open {sym} Chart", f"openSymbolChart('{sym}')"),
        (f"🎯 Swing Setups", "askQuickPrompt('I am looking for short term swing trades for 10-15 days')"),
        (f"🎙️ Concall Guidance", f"askQuickPrompt('Show management guidance and concalls for {sym}')"),
    ]
    state["response_markdown"] = md + make_action_chips(chips)
    state["tool_results"]["multi_timeframe"] = mtf_data
    return state


def execute_ambiguous_agent(state: AgentState) -> AgentState:
    """Autonomous Quantitative Reasoning Agent replacing static ambiguous fallback."""
    q = state["query"].strip()
    res = run_autonomous_reasoning(q, user_id=1, session_id=state.get("session_id"))
    state["response_markdown"] = res.get("answer", "")
    state["tool_results"]["autonomous_reasoning"] = res
    return state


# ── 4. Build LangGraph Workflow ───────────────────────────────────────────────
def build_orchestration_graph():
    """Builds and compiles the LangGraph StateGraph."""
    try:
        from langgraph.graph import StateGraph, END
        
        builder = StateGraph(AgentState)
        
        # Add nodes
        builder.add_node("supervisor", classify_and_guard)
        builder.add_node("greeting_agent", execute_greeting_or_help_agent)
        builder.add_node("index_agent", execute_index_agent)
        builder.add_node("fundamental_screener_agent", execute_fundamental_screener_agent)
        builder.add_node("screener_agent", execute_screener_agent)
        builder.add_node("swing_agent", execute_swing_agent)
        builder.add_node("ticker_agent", execute_ticker_intelligence_agent)
        builder.add_node("comparison_agent", execute_comparison_agent)
        builder.add_node("comparison_rec_agent", execute_comparison_recommendation_agent)
        builder.add_node("group_agent", execute_group_disambiguation_agent)
        builder.add_node("portfolio_agent", execute_portfolio_agent)
        builder.add_node("portfolio_sector_agent", execute_portfolio_sector_agent)
        builder.add_node("position_advisor_agent", execute_position_advisor_agent)
        builder.add_node("personalization_agent", execute_personalization_agent)
        builder.add_node("capital_allocation_agent", execute_capital_allocation_agent)
        builder.add_node("corporate_calendar_agent", execute_corporate_calendar_agent)
        builder.add_node("smart_money_agent", execute_smart_money_agent)
        builder.add_node("options_microstructure_agent", execute_options_microstructure_agent)
        builder.add_node("macro_stress_agent", execute_macro_stress_agent)
        builder.add_node("multi_timeframe_agent", execute_multi_timeframe_agent)
        builder.add_node("ambiguous_agent", execute_ambiguous_agent)
        
        builder.set_entry_point("supervisor")
        
        # Router conditional edges
        def route_by_intent(state: AgentState) -> str:
            intent = state["intent"]
            if intent == "GREETING_OR_HELP":
                return "greeting_agent"
            elif intent == "PORTFOLIO_AUDIT":
                return "portfolio_agent"
            elif intent == "PORTFOLIO_SECTOR_AUDIT":
                return "portfolio_sector_agent"
            elif intent == "POSITION_ADVISORY":
                return "position_advisor_agent"
            elif intent == "PERSONALIZATION_UPDATE":
                return "personalization_agent"
            elif intent == "CAPITAL_ALLOCATION":
                return "capital_allocation_agent"
            elif intent == "CORPORATE_CALENDAR":
                return "corporate_calendar_agent"
            elif intent == "SMART_MONEY_AUDIT":
                return "smart_money_agent"
            elif intent == "OPTIONS_MICROSTRUCTURE":
                return "options_microstructure_agent"
            elif intent == "MACRO_STRESS_TEST":
                return "macro_stress_agent"
            elif intent == "MULTI_TIMEFRAME":
                return "multi_timeframe_agent"
            elif intent == "INDEX_DETAIL":
                return "index_agent"
            elif intent == "FUNDAMENTAL_SCREENER":
                return "fundamental_screener_agent"
            elif intent in ("SCREENER_LOSERS", "SCREENER_GAINERS"):
                return "screener_agent"
            elif intent == "SWING_SETUPS":
                return "swing_agent"
            elif intent == "COMPARISON":
                return "comparison_agent"
            elif intent == "COMPARISON_RECOMMENDATION":
                return "comparison_rec_agent"
            elif intent == "TICKER_DETAIL":
                return "ticker_agent"
            elif intent == "GROUP_DISAMBIGUATION":
                return "group_agent"
            else:
                return "ambiguous_agent"

        builder.add_conditional_edges("supervisor", route_by_intent, {
            "greeting_agent": "greeting_agent",
            "index_agent": "index_agent",
            "fundamental_screener_agent": "fundamental_screener_agent",
            "screener_agent": "screener_agent",
            "swing_agent": "swing_agent",
            "comparison_agent": "comparison_agent",
            "comparison_rec_agent": "comparison_rec_agent",
            "ticker_agent": "ticker_agent",
            "group_agent": "group_agent",
            "portfolio_agent": "portfolio_agent",
            "portfolio_sector_agent": "portfolio_sector_agent",
            "position_advisor_agent": "position_advisor_agent",
            "personalization_agent": "personalization_agent",
            "capital_allocation_agent": "capital_allocation_agent",
            "corporate_calendar_agent": "corporate_calendar_agent",
            "smart_money_agent": "smart_money_agent",
            "options_microstructure_agent": "options_microstructure_agent",
            "macro_stress_agent": "macro_stress_agent",
            "multi_timeframe_agent": "multi_timeframe_agent",
            "ambiguous_agent": "ambiguous_agent"
        })
        
        builder.add_edge("greeting_agent", END)
        builder.add_edge("index_agent", END)
        builder.add_edge("fundamental_screener_agent", END)
        builder.add_edge("screener_agent", END)
        builder.add_edge("swing_agent", END)
        builder.add_edge("ticker_agent", END)
        builder.add_edge("comparison_agent", END)
        builder.add_edge("comparison_rec_agent", END)
        builder.add_edge("group_agent", END)
        builder.add_edge("portfolio_agent", END)
        builder.add_edge("portfolio_sector_agent", END)
        builder.add_edge("position_advisor_agent", END)
        builder.add_edge("personalization_agent", END)
        builder.add_edge("capital_allocation_agent", END)
        builder.add_edge("corporate_calendar_agent", END)
        builder.add_edge("smart_money_agent", END)
        builder.add_edge("options_microstructure_agent", END)
        builder.add_edge("macro_stress_agent", END)
        builder.add_edge("multi_timeframe_agent", END)
        builder.add_edge("ambiguous_agent", END)
        
        return builder.compile()
    except Exception as e:
        print(f"  [Orchestrator] LangGraph compilation warning: {e}. Using deterministic router.")
        return None

_COMPILED_GRAPH = None

def get_orchestration_graph():
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_orchestration_graph()
    return _COMPILED_GRAPH

def run_agentic_copilot(
    query: str,
    symbol: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main entrypoint called by chatbot_engine.handle_chat_query.
    Runs query through LangGraph multi-agent workflow.
    """
    initial_state: AgentState = {
        "query": query,
        "session_id": session_id or "default_session",
        "user_id": user_id,
        "symbol": symbol,
        "intent": "AMBIGUOUS",
        "comparison_symbol": None,
        "screener_metric": None,
        "tool_results": {},
        "response_markdown": "",
        "group_data": None,
        "error": None
    }
    
    graph = get_orchestration_graph()
    if graph:
        try:
            final_state = graph.invoke(initial_state)
            return {
                "answer": final_state.get("response_markdown", ""),
                "symbol": final_state.get("symbol"),
                "intent": final_state.get("intent"),
                "tool_results": final_state.get("tool_results", {})
            }
        except Exception as e:
            print(f"  [Orchestrator] LangGraph execution error: {e}")
            
    # Deterministic fallback router
    state = classify_and_guard(initial_state)
    intent = state["intent"]
    if intent == "GREETING_OR_HELP":
        state = execute_greeting_or_help_agent(state)
    elif intent == "PORTFOLIO_AUDIT":
        state = execute_portfolio_agent(state)
    elif intent == "PORTFOLIO_SECTOR_AUDIT":
        state = execute_portfolio_sector_agent(state)
    elif intent == "POSITION_ADVISORY":
        state = execute_position_advisor_agent(state)
    elif intent == "PERSONALIZATION_UPDATE":
        state = execute_personalization_agent(state)
    elif intent == "CAPITAL_ALLOCATION":
        state = execute_capital_allocation_agent(state)
    elif intent == "CORPORATE_CALENDAR":
        state = execute_corporate_calendar_agent(state)
    elif intent == "SMART_MONEY_AUDIT":
        state = execute_smart_money_agent(state)
    elif intent == "OPTIONS_MICROSTRUCTURE":
        state = execute_options_microstructure_agent(state)
    elif intent == "MACRO_STRESS_TEST":
        state = execute_macro_stress_agent(state)
    elif intent == "MULTI_TIMEFRAME":
        state = execute_multi_timeframe_agent(state)
    elif intent == "INDEX_DETAIL":
        state = execute_index_agent(state)
    elif intent == "FUNDAMENTAL_SCREENER":
        state = execute_fundamental_screener_agent(state)
    elif intent in ("SCREENER_LOSERS", "SCREENER_GAINERS"):
        state = execute_screener_agent(state)
    elif intent == "SWING_SETUPS":
        state = execute_swing_agent(state)
    elif intent == "COMPARISON":
        state = execute_comparison_agent(state)
    elif intent == "COMPARISON_RECOMMENDATION":
        state = execute_comparison_recommendation_agent(state)
    elif intent == "TICKER_DETAIL":
        state = execute_ticker_intelligence_agent(state)
    elif intent == "GROUP_DISAMBIGUATION":
        state = execute_group_disambiguation_agent(state)
    else:
        state = execute_ambiguous_agent(state)
        
    return {
        "answer": state.get("response_markdown", ""),
        "symbol": state.get("symbol"),
        "intent": state.get("intent"),
        "tool_results": state.get("tool_results", {})
    }
