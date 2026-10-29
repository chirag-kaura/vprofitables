"""
core/swarm/subgraphs/ohlc_subgraph.py
=====================================
OHLC Technical Price Action Specialist Subgraph.
Responsible for:
  - Exact candle quotes, rolling VWAP, delivery volume %
  - Multi-session OHLC candle tables
  - Technical statistics (SMA20, SMA50, ATR 14, 52-Week High / Low)
  - Relative performance comparators
  - Screener top gainers and losers
  - NSE trading calendar sessions
"""

import re
from typing import List, Dict, Any
from langgraph.graph import StateGraph, START, END
from core.swarm.state import SwarmState, SpecialistOutput
from core.tools.contracts import ToolResult
from core.ohlc_rag.tools import (
    ohlc_calendar_dates,
    ohlc_market_movers,
    ohlc_quote_lookup,
    ohlc_history_range,
    ohlc_technical_stats,
    ohlc_relative_performance
)

def _wrap_str_to_result(raw_str: str, domain: str, symbol: str) -> ToolResult:
    lines = raw_str.strip().split("\n")
    headline = lines[0] if lines else f"{domain} result for {symbol}"
    return ToolResult(
        domain=domain,
        symbol=symbol,
        headline_metric=headline[:120],
        tabular_summary=raw_str,
        raw_data={"summary_text": raw_str[:300]}
    )

def node_execute_ohlc(state: SwarmState) -> Dict[str, Any]:
    """Executes OHLC technical candle, stat, screener, and calendar tools."""
    sym = state.get("symbol")
    sym2 = state.get("second_symbol")
    sub_intents = state.get("sub_intents", [])
    intent = state.get("intent", "")
    query = state.get("query", "")
    results: List[ToolResult] = []

    # 1. Calendar Tool
    if "calendar" in sub_intents or intent == "calendar":
        n_match = re.search(r"\b(\d+)\b", query)
        limit = int(n_match.group(1)) if n_match else 5
        results.append(_wrap_str_to_result(ohlc_calendar_dates.invoke({"limit": limit}), "CALENDAR", "NSE"))
        return {"tool_results": results}

    # 2. Screener Tool
    if "screener" in sub_intents or intent == "screener":
        direction = "GAINERS" if re.search(r"\b(GAIN|GAINED|TOP GAINERS?|PERFORMERS?|RALLY)\b", query.upper()) else "LOSERS"
        n_days_match = re.search(r"\b(\d+)\s*(?:DAYS?|SESSIONS?)\b", query.upper())
        days = int(n_days_match.group(1)) if n_days_match else 5
        results.append(_wrap_str_to_result(ohlc_market_movers.invoke({"direction": direction, "days": days, "limit": 5}), "SCREENER", "MARKET"))
        return {"tool_results": results}

    # 3. Comparison Tool
    if "comparison" in sub_intents and sym and sym2:
        n_days_match = re.search(r"\b(\d+)\s*(?:DAYS?|SESSIONS?)\b", query.upper())
        days = int(n_days_match.group(1)) if n_days_match else 5
        results.append(_wrap_str_to_result(ohlc_relative_performance.invoke({"symbol_a": sym, "symbol_b": sym2, "days": days}), "OHLC", f"{sym}_vs_{sym2}"))
        results.append(_wrap_str_to_result(ohlc_technical_stats.invoke({"symbol": sym, "lookback_days": 60}), "OHLC", sym))
        results.append(_wrap_str_to_result(ohlc_technical_stats.invoke({"symbol": sym2, "lookback_days": 60}), "OHLC", sym2))
        return {"tool_results": results}

    # 4. Single-Stock Mode
    if sym:
        run_all = ("dossier" in sub_intents)
        if run_all or "quote" in sub_intents:
            results.append(_wrap_str_to_result(ohlc_quote_lookup.invoke({"symbol": sym}), "OHLC", sym))
        if run_all or "history" in sub_intents:
            n_match = re.search(r"\b(\d+)\s*(?:DAYS?|SESSIONS?)\b", query.upper())
            days = int(n_match.group(1)) if n_match else 10
            results.append(_wrap_str_to_result(ohlc_history_range.invoke({"symbol": sym, "num_days": days}), "OHLC", sym))
        if run_all or "stats" in sub_intents or "trend_rag" in sub_intents or not sub_intents:
            results.append(_wrap_str_to_result(ohlc_technical_stats.invoke({"symbol": sym, "lookback_days": 60}), "OHLC", sym))

    return {"tool_results": results}

def build_ohlc_subgraph():
    builder = StateGraph(SwarmState, output_schema=SpecialistOutput)
    builder.add_node("exec_ohlc", node_execute_ohlc)
    builder.add_edge(START, "exec_ohlc")
    builder.add_edge("exec_ohlc", END)
    return builder.compile()

ohlc_subgraph = build_ohlc_subgraph()
