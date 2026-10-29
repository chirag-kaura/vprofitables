"""
core/swarm/subgraphs/fundamental_subgraph.py
============================================
Fundamental & Sentiment Specialist Subgraph.
Responsible for:
  - 10-Year Audited Income Statements (Sales, PAT, OPM%, CAGR in ₹ Cr)
  - Balance Sheet Health (Borrowings, Net Worth, Cash, Debt/Equity)
  - Quarterly Institutional Shareholding (Promoter, FII, DII, Public, Pledged %)
  - Banking Asset Quality (Gross/Net NPA %, Financing Profit)
  - FinBERT News Sentiment, Composite Scores, Risk Catalysts, and Move Explanations
"""

import re
import time
from typing import List, Dict, Any
from langgraph.graph import StateGraph, START, END
from core.swarm.state import SwarmState, SpecialistOutput
from core.tools.contracts import ToolResult
from core.financials_rag.tools import (
    financials_income_statement,
    financials_balance_sheet,
    financials_shareholding_trend,
    financials_banking_quality
)
from core.news_rag.tools import (
    news_recent_headlines,
    news_sentiment_summary,
    news_explain_price_move
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

def node_execute_fundamental(state: SwarmState) -> Dict[str, Any]:
    """Executes audited financial statements and FinBERT news sentiment tools."""
    sym = state.get("symbol")
    sym2 = state.get("second_symbol")
    sub_intents = state.get("sub_intents", [])
    query = state.get("query", "")
    results: List[ToolResult] = []

    if not sym:
        return {"tool_results": []}

    # Comparison Mode
    if "comparison" in sub_intents and sym and sym2:
        if "financials_growth" in sub_intents or "fundamentals" in state.get("domains", []):
            results.append(_wrap_str_to_result(financials_income_statement.invoke({"symbol": sym, "years": 3}), "FINANCIALS", sym))
            results.append(_wrap_str_to_result(financials_income_statement.invoke({"symbol": sym2, "years": 3}), "FINANCIALS", sym2))
        if "financials_balance_sheet" in sub_intents:
            results.append(_wrap_str_to_result(financials_balance_sheet.invoke({"symbol": sym}), "FINANCIALS", sym))
            results.append(_wrap_str_to_result(financials_balance_sheet.invoke({"symbol": sym2}), "FINANCIALS", sym2))
        if "financials_shareholding" in sub_intents:
            results.append(_wrap_str_to_result(financials_shareholding_trend.invoke({"symbol": sym}), "FINANCIALS", sym))
            results.append(_wrap_str_to_result(financials_shareholding_trend.invoke({"symbol": sym2}), "FINANCIALS", sym2))
        if "financials_banking" in sub_intents:
            results.append(_wrap_str_to_result(financials_banking_quality.invoke({"symbol": sym}), "FINANCIALS", sym))
            results.append(_wrap_str_to_result(financials_banking_quality.invoke({"symbol": sym2}), "FINANCIALS", sym2))
        if "sentiment" in sub_intents:
            results.append(_wrap_str_to_result(news_sentiment_summary.invoke({"symbol": sym}), "NEWS", sym))
            results.append(_wrap_str_to_result(news_sentiment_summary.invoke({"symbol": sym2}), "NEWS", sym2))
        if "news" in sub_intents:
            results.append(_wrap_str_to_result(news_recent_headlines.invoke({"symbol": sym, "limit": 3}), "NEWS", sym))
            results.append(_wrap_str_to_result(news_recent_headlines.invoke({"symbol": sym2, "limit": 3}), "NEWS", sym2))
        return {"tool_results": results}

    # Single-Stock Mode
    run_all = ("dossier" in sub_intents)

    # 1. Audited Income Statement
    if run_all or "financials_growth" in sub_intents:
        n_match = re.search(r"\b(\d+)\s*(?:YEARS?|YRS?)\b", query.upper())
        yrs = int(n_match.group(1)) if n_match else 3
        results.append(_wrap_str_to_result(financials_income_statement.invoke({"symbol": sym, "years": yrs}), "FINANCIALS", sym))

    # 2. Balance Sheet Solvency
    if run_all or "financials_balance_sheet" in sub_intents:
        results.append(_wrap_str_to_result(financials_balance_sheet.invoke({"symbol": sym}), "FINANCIALS", sym))

    # 3. Shareholding Pattern
    if run_all or "financials_shareholding" in sub_intents:
        results.append(_wrap_str_to_result(financials_shareholding_trend.invoke({"symbol": sym}), "FINANCIALS", sym))

    # 4. Banking Quality
    if run_all or "financials_banking" in sub_intents:
        results.append(_wrap_str_to_result(financials_banking_quality.invoke({"symbol": sym}), "FINANCIALS", sym))

    # 5. FinBERT News Sentiment & Headlines
    if run_all or "sentiment" in sub_intents:
        results.append(_wrap_str_to_result(news_sentiment_summary.invoke({"symbol": sym}), "NEWS", sym))

    if run_all or "news" in sub_intents:
        results.append(_wrap_str_to_result(news_recent_headlines.invoke({"symbol": sym, "limit": 3}), "NEWS", sym))

    if "why_move" in sub_intents:
        n_match = re.search(r"\b(\d+)\s*(?:DAYS?|SESSIONS?)\b", query.upper())
        days = int(n_match.group(1)) if n_match else 5
        results.append(_wrap_str_to_result(news_explain_price_move.invoke({"symbol": sym, "days": days}), "NEWS", sym))

    return {"tool_results": results}

def build_fundamental_subgraph():
    builder = StateGraph(SwarmState, output_schema=SpecialistOutput)
    builder.add_node("exec_fundamental", node_execute_fundamental)
    builder.add_edge(START, "exec_fundamental")
    builder.add_edge("exec_fundamental", END)
    return builder.compile()

fundamental_subgraph = build_fundamental_subgraph()
