"""
core/ohlc_rag/graph.py
======================
Unified Multi-Modal LangGraph Orchestrator (OHLC + News Sentiment + 10Y Financials).
Orchestrates:
  - Query Intent Decomposer across 3 Data Sources:
      1. OHLC Data (Price, Candles, Technical Stats, Screener, Calendar)
      2. News & FinBERT Sentiment (Headlines, Composite Score, Risk Catalysts, Why Move)
      3. Audited 10-Year Financials & Balance Sheets (Sales, PAT, Debt/Equity, Shareholding, NPAs)
  - Multi-Turn Conversational Memory & Pronoun Resolution ("it", "its", "that stock")
  - Crypto & Foreign Asset Guardrail ("Bitcoin", "Tesla", "Apple")
  - Domain Boundary Filter for Off-Topic Questions
  - Speed-Optimized Local LLM Synthesis with Qwen 2.5:7b (8-thread CPU acceleration + token limits)
"""

import os
import sys
import re
from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.ohlc_rag.retriever import OHLCHybridRetriever, extract_symbol_and_intent, KNOWN_SYMBOLS, DB_PATH
from core.ohlc_rag.tools import (
    ohlc_calendar_dates,
    ohlc_market_movers,
    ohlc_quote_lookup,
    ohlc_history_range,
    ohlc_technical_stats,
    ohlc_relative_performance
)
from core.news_rag.tools import (
    news_recent_headlines,
    news_sentiment_summary,
    news_explain_price_move
)
from core.financials_rag.tools import (
    financials_income_statement,
    financials_balance_sheet,
    financials_shareholding_trend,
    financials_banking_quality
)
from core.tools.derivatives_tools import derivatives_pcr_maxpain, derivatives_participant_oi
from core.tools.smart_money_tools import smart_money_deal_flow
from core.tools.quant_tools import quant_gann_sq9, quant_wyckoff_structure
from core.tools.astro_tools import astro_nakshatra_guidance, astro_planetary_aspects
from core.tools.ml_signal_tools import ml_trend_continuation, ml_deep_reversal_score

# Local LLM integration
try:
    from langchain_ollama import ChatOllama
    OLLAMA_AVAILABLE = True
except Exception:
    OLLAMA_AVAILABLE = False


class OHLCState(TypedDict):
    query: str
    symbol: Optional[str]
    second_symbol: Optional[str]
    intent: str
    sub_intents: List[str]
    timeframe: Optional[str]
    history: List[Dict[str, str]]
    retrieved_context: str
    tool_outputs: List[str]
    is_off_topic: bool
    is_foreign_crypto: bool
    skip_llm: bool
    final_response: str


# Singleton retriever
_RETRIEVER = None

def get_retriever():
    global _RETRIEVER
    if _RETRIEVER is None:
        _RETRIEVER = OHLCHybridRetriever()
    return _RETRIEVER


OFF_TOPIC_PATTERNS = [
    r"\b(RECIPE|COOK|PASTA|PIZZA|FOOD|CAKE|INGREDIENTS)\b",
    r"\b(WEATHER|TEMPERATURE|RAIN|FORECAST|CLIMATE)\b",
    r"\b(PYTHON|JAVA|JAVASCRIPT|FUNCTION|CODE|INVERT|BINARY TREE|ALGORITHM|DEBUG)\b",
    r"\b(WORLD CUP|FOOTBALL|SOCCER|CRICKET|MATCH|MOVIE|ACTOR|CELEBRITY|SONG|POEM)\b",
    r"\b(PRESIDENT|CAPITAL OF|WHO WON|HISTORY OF|ROME|DINOSAUR)\b"
]

FOREIGN_CRYPTO_PATTERNS = [
    r"\b(BITCOIN|BTC|ETHEREUM|ETH|DOGECOIN|DOGE|CRYPTO|SOLANA|BINANCE)\b",
    r"\b(TESLA|TSLA|APPLE|AAPL|GOOGLE|ALPHABET|GOOGL|AMAZON|AMZN|MICROSOFT|MSFT|META|NVIDIA|NVDA)\b",
    r"\b(XYZ\d+|FAKESTOCK|\b\d{2,4}\b)\b"
]


# ── NODE 1: Query Decomposer & Context Resolver ──────────────────────────────
def node_analyze_query(state: OHLCState) -> Dict[str, Any]:
    """
    Decomposes user query across OHLC, News Sentiment, and 10Y Financials.
    Resolves conversational pronouns ('it', 'its', 'that stock') from history.
    """
    query = state["query"]
    q_upper = query.upper()
    history = state.get("history") or []

    # 1. Off-Topic / Non-Relevant Check
    for pat in OFF_TOPIC_PATTERNS:
        if re.search(pat, q_upper):
            return {
                "symbol": None,
                "second_symbol": None,
                "intent": "off_topic",
                "sub_intents": [],
                "timeframe": None,
                "is_off_topic": True,
                "is_foreign_crypto": False
            }

    # 2. Crypto / Foreign Asset Check
    for pat in FOREIGN_CRYPTO_PATTERNS:
        if re.search(pat, q_upper) and not any(k in q_upper for k in ("NIFTY", "RELIANCE", "TCS", "INFY")):
            return {
                "symbol": None,
                "second_symbol": None,
                "intent": "foreign_crypto",
                "sub_intents": [],
                "timeframe": None,
                "is_off_topic": False,
                "is_foreign_crypto": True
            }

    # 3. Calendar Intent
    if re.search(r"\b(TRADING DATES|TRADING DAYS|LAST \d+ TRADING DATES|DATES DATA|DATES WE HAVE|CALENDAR DATES|RECENT TRADING SESSION DATE|LATEST SESSION DATE|MOST RECENT SESSION)\b", q_upper):
        return {
            "symbol": None,
            "second_symbol": None,
            "intent": "calendar",
            "sub_intents": ["calendar"],
            "timeframe": None,
            "is_off_topic": False,
            "is_foreign_crypto": False
        }

    # 4. Screener Intent (Expanded with all synonyms)
    if re.search(r"\b(FELL MOST|DROPPED MOST|FALLEN MOST|GAINED MOST|GAINED THE MOST|TOP LOSERS?|TOP GAINERS?|BIGGEST DROP|BIGGEST LOSERS?|BIGGEST GAINERS?|MARKET LOSERS?|TOP PERFORMERS?|BIGGEST FALL|BIGGEST MARKET DROP)\b", q_upper):
        sub_ints = ["screener"]
        if re.search(r"\b(WHY|SUMMARIZE WHY|REASON|NEWS)\b", q_upper):
            sub_ints.append("why_move")
        return {
            "symbol": None,
            "second_symbol": None,
            "intent": "screener",
            "sub_intents": sub_ints,
            "timeframe": "5D",
            "is_off_topic": False,
            "is_foreign_crypto": False
        }

    # 5. Multi-Symbol / Comparison Intent
    found_symbols: List[str] = []
    for alias in sorted(KNOWN_SYMBOLS.keys(), key=len, reverse=True):
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, q_upper):
            sym = KNOWN_SYMBOLS[alias]
            if sym not in found_symbols:
                found_symbols.append(sym)

    is_compare_query = bool(re.search(r"\b(COMPARE|VS|VERSUS|BETWEEN|OUTPERFORM|RELATIVE)\b", q_upper))

    if len(found_symbols) >= 2 or (len(found_symbols) == 1 and is_compare_query):
        sym1 = found_symbols[0]
        sym2 = found_symbols[1] if len(found_symbols) > 1 else None
        _, tf = extract_symbol_and_intent(query)
        sub_ints = ["comparison"]
        if re.search(r"\b(NEWS|HEADLINES)\b", q_upper):
            sub_ints.append("news")
        if re.search(r"\b(SENTIMENT|MOOD|FINBERT)\b", q_upper):
            sub_ints.append("sentiment")
        if re.search(r"\b(SALES|PROFIT|REVENUE|FINANCIALS|EARNINGS)\b", q_upper):
            sub_ints.append("financials_growth")
        if re.search(r"\b(FII|DII|PROMOTER|STAKE|SHAREHOLDING|OWNERSHIP|FOREIGN)\b", q_upper):
            sub_ints.append("financials_shareholding")
        if re.search(r"\b(DEBT|BORROWING|BALANCE SHEET|LEVERAGE)\b", q_upper):
            sub_ints.append("financials_balance_sheet")
        if re.search(r"\b(NPA|BAD LOANS?|ASSET QUALITY)\b", q_upper):
            sub_ints.append("financials_banking")
        if re.search(r"\b(WYCKOFF|ACCUMULATION|DISTRIBUTION PHASE)\b", q_upper):
            sub_ints.append("quant_wyckoff")
        if re.search(r"\b(GANN|SQUARE OF 9|SQ9)\b", q_upper):
            sub_ints.append("quant_gann")
        if re.search(r"\b(CONTINUATION|MLP|DEEP MODEL)\b", q_upper):
            sub_ints.append("ml_continuation")
        if re.search(r"\b(PCR|MAX PAIN|OPTION CHAIN)\b", q_upper):
            sub_ints.append("derivatives_pcr")
        return {
            "symbol": sym1,
            "second_symbol": sym2,
            "intent": "comparison",
            "sub_intents": sub_ints,
            "timeframe": tf or "5D",
            "is_off_topic": False,
            "is_foreign_crypto": False
        }

    # 6. Single Symbol or Follow-up Context Resolution
    sym1 = found_symbols[0] if found_symbols else None
    if not sym1:
        sym1, timeframe = extract_symbol_and_intent(query)
    else:
        _, timeframe = extract_symbol_and_intent(query)

    # Conversational Anaphora ('it', 'its', 'that stock', 'that company', 'the same')
    if not sym1 and history:
        for turn in reversed(history):
            prior_sym = turn.get("symbol")
            if prior_sym:
                if re.search(r"\b(IT|ITS|THAT STOCK|THIS STOCK|THE COMPANY|THAT COMPANY|SAME)\b", q_upper) or len(query.split()) <= 5:
                    sym1 = prior_sym
                    break

    # Discard pure numbers or short noise
    if sym1 and (sym1.isdigit() or (len(sym1) <= 2 and sym1 not in {"LT", "IT"})):
        sym1 = None

    # Check for Market-Wide Queries Without a Specific Stock Symbol
    if not sym1:
        market_sub_intents = []
        if re.search(r"\b(PARTICIPANT OI|FII FUTURES|FII LONG|PRO CALLS|CLIENT PUTS|SMART MONEY BIAS)\b", q_upper):
            market_sub_intents.append("participant_oi")
        if re.search(r"\b(PLANETARY ASPECTS?|RETROGRADE|PLANET STATIONS?|CONJUNCTION|OPPOSITION|TRINE)\b", q_upper):
            market_sub_intents.append("astro_aspects")
        if re.search(r"\b(NAKSHATRA|RAHU KAAL|ABHIJIT MUHURAT)\b", q_upper):
            market_sub_intents.append("astro_nakshatra")
        if re.search(r"\b(BULK DEALS?|BLOCK DEALS?|INSTITUTIONAL FLOW|BIG MONEY FLOW)\b", q_upper):
            market_sub_intents.append("smart_money_deals")
        if market_sub_intents:
            return {
                "symbol": None,
                "second_symbol": None,
                "intent": "market_wide",
                "sub_intents": market_sub_intents,
                "timeframe": None,
                "is_off_topic": False,
                "is_foreign_crypto": False
            }

    # Decompose into sub-intents across all 7 terminal data domains
    sub_intents = []
    if sym1:
        # Data Source 1: OHLC
        if re.search(r"\b(52W|52-WEEK|LOW|HIGH|SMA|ATR|STATS|INDICATOR|VOLATILITY)\b", q_upper):
            sub_intents.append("stats")
        if re.search(r"\b(QUOTE|PRICE|LTP|CLOSE|TODAY|YESTERDAY)\b", q_upper):
            sub_intents.append("quote")
        if re.search(r"\b(TABLE|HISTORY|CANDLES|LAST \d+ DAYS)\b", q_upper):
            sub_intents.append("history")

        # Data Source 2: News & FinBERT Sentiment
        if re.search(r"\b(SENTIMENT|SENTIMENTS|MOOD|FINBERT|BIAS|REGULATORY RISK|MANAGEMENT CHANGE|GUIDANCE)\b", q_upper):
            sub_intents.append("sentiment")
        if re.search(r"\b(NEWS|HEADLINES?|ANNOUNCEMENT|CATALYST|UPDATE)\b", q_upper):
            sub_intents.append("news")
        if re.search(r"\b(WHY|REASON|DRIVING|DROP|FALL|SURGE|EXPLAIN)\b", q_upper):
            sub_intents.append("why_move")

        # Data Source 3: Audited 10-Year Financials & Balance Sheets
        if re.search(r"\b(SALES|REVENUE|PROFIT|NET PROFIT|PAT|OPM|MARGIN|CAGR|GROWTH|INCOME STATEMENT|EARNINGS)\b", q_upper):
            sub_intents.append("financials_growth")
        if re.search(r"\b(DEBT|BORROWING|BALANCE SHEET|RESERVES|ASSETS|CASH|LEVERAGE|SOLVENCY|DEBT TO EQUITY)\b", q_upper):
            sub_intents.append("financials_balance_sheet")
        if re.search(r"\b(FII|DII|PROMOTER|STAKE|SHAREHOLDING|OWNERSHIP|PLEDGED)\b", q_upper):
            sub_intents.append("financials_shareholding")
        if re.search(r"\b(NPA|BAD LOANS?|ASSET QUALITY|GROSS NPA|NET NPA)\b", q_upper):
            sub_intents.append("financials_banking")

        # Data Source 4: Derivatives & Options Microstructure
        if re.search(r"\b(PCR|PUT CALL RATIO|MAX PAIN|OPTION CHAIN|CALL WALL|PUT WALL|IV SKEW)\b", q_upper):
            sub_intents.append("derivatives_pcr")
        if re.search(r"\b(PARTICIPANT OI|FII FUTURES|FII LONG|PRO CALLS|CLIENT PUTS|SMART MONEY BIAS)\b", q_upper):
            sub_intents.append("participant_oi")
        if re.search(r"\b(BULK DEALS?|BLOCK DEALS?|INSTITUTIONAL BUY|INSTITUTIONAL FLOW|BIG MONEY|DEALS? FLOW)\b", q_upper):
            sub_intents.append("smart_money_deals")

        # Data Source 5: Quant & Mathematical Engines (Gann / Wyckoff)
        if re.search(r"\b(GANN|SQUARE OF 9|SQ9|GANN ANGLES?|GANN LEVELS?)\b", q_upper):
            sub_intents.append("quant_gann")
        if re.search(r"\b(WYCKOFF|ACCUMULATION|DISTRIBUTION PHASE|SPRING|UPTHRUST|VOLATILITY SQUEEZE|HEDGE FUND LEVELS?)\b", q_upper):
            sub_intents.append("quant_wyckoff")

        # Data Source 6: Celestial & Vedic Astro Timing
        if re.search(r"\b(NAKSHATRA|RAHU KAAL|ABHIJIT MUHURAT|ASTRO|ASTROLOGY|VEDIC)\b", q_upper):
            sub_intents.append("astro_nakshatra")
        if re.search(r"\b(PLANETARY ASPECTS?|RETROGRADE|PLANET STATIONS?)\b", q_upper):
            sub_intents.append("astro_aspects")

        # Data Source 7: Deep Learning & ML Predictive Models
        if re.search(r"\b(DEEP CONTINUATION|MLP|CONTINUATION PROBABILITY|TREND CONTINUATION MODEL|WAVELET PHASE)\b", q_upper):
            sub_intents.append("ml_continuation")
        if re.search(r"\b(DEEP REVERSAL|REVERSAL MODEL|XGBOOST REVERSAL|REVERSAL SCORE|SWING EXHAUSTION)\b", q_upper):
            sub_intents.append("ml_reversal")

        # Comprehensive Dossier
        if re.search(r"\b(FULL DOSSIER|COMPLETE REPORT|COMPREHENSIVE ANALYSIS|QUANT DOSSIER|360 ANALYSIS)\b", q_upper):
            for extra in ("stats", "sentiment", "financials_growth", "derivatives_pcr", "quant_gann", "quant_wyckoff", "ml_continuation", "astro_nakshatra"):
                if extra not in sub_intents:
                    sub_intents.append(extra)

        if not sub_intents:
            sub_intents.append("trend_rag")

        intent = "multi_layered" if len(sub_intents) > 1 else sub_intents[0]
    else:
        intent = "general"

    return {
        "symbol": sym1,
        "second_symbol": None,
        "intent": intent,
        "sub_intents": sub_intents,
        "timeframe": timeframe,
        "is_off_topic": False,
        "is_foreign_crypto": False
    }


# ── NODE 2: Multi-Modal RAG Retriever ─────────────────────────────────────────
def node_retrieve_rag_context(state: OHLCState) -> Dict[str, Any]:
    """Fetches semantic vector documents from ChromaDB and exact SQL sessions."""
    if state.get("is_off_topic") or state.get("is_foreign_crypto"):
        return {"retrieved_context": ""}

    intent = state.get("intent")
    sub_intents = state.get("sub_intents", [])
    sym1 = state.get("symbol")
    sym2 = state.get("second_symbol")

    # Dynamic Tool Gating: skip heavy Chroma vector retrieval if query is already covered by deterministic tools
    needs_dense_rag = ("trend_rag" in sub_intents) or ("why_move" in sub_intents) or (intent == "trend_rag")
    if not needs_dense_rag:
        return {"retrieved_context": ""}

    if intent in ("calendar", "screener", "market_wide") or (not sym1 and intent == "general"):
        return {"retrieved_context": ""}

    retriever = get_retriever()

    if intent == "comparison" and sym1 and sym2:
        res1 = retriever.retrieve(f"OHLC price action for {sym1}", top_k=2)
        res2 = retriever.retrieve(f"OHLC price action for {sym2}", top_k=2)
        fused = (
            f"=== VERIFIED OHLC GROUND TRUTH FOR {sym1} ===\n"
            f"{res1.formatted_context}\n\n"
            f"=== VERIFIED OHLC GROUND TRUTH FOR {sym2} ===\n"
            f"{res2.formatted_context}"
        )
        return {"retrieved_context": fused}

    if sym1:
        res = retriever.retrieve(state["query"], top_k=2)
        return {"retrieved_context": res.formatted_context}

    return {"retrieved_context": ""}


# ── NODE 3: Deterministic Tools Execution ─────────────────────────────────────
def node_execute_tools(state: OHLCState) -> Dict[str, Any]:
    """Executes all relevant quantitative, news, and financial tools based on sub-intents."""
    if state.get("is_off_topic") or state.get("is_foreign_crypto"):
        return {"tool_outputs": []}

    intent = state.get("intent")
    sub_intents = state.get("sub_intents", [])
    sym = state.get("symbol")
    sym2 = state.get("second_symbol")
    query = state.get("query", "")
    tool_outputs: List[str] = []

    # 1. Calendar Tool
    if "calendar" in sub_intents or intent == "calendar":
        n_match = re.search(r"\b(\d+)\b", query)
        limit = int(n_match.group(1)) if n_match else 5
        tool_outputs.append(ohlc_calendar_dates.invoke({"limit": limit}))

    # 2. Screener Tool
    elif "screener" in sub_intents or intent == "screener":
        direction = "GAINERS" if re.search(r"\b(GAIN|GAINED|TOP GAINERS?|PERFORMERS?|RALLY)\b", query.upper()) else "LOSERS"
        n_days_match = re.search(r"\b(\d+)\s*(?:DAYS?|SESSIONS?)\b", query.upper())
        days = int(n_days_match.group(1)) if n_days_match else 5
        movers_res = ohlc_market_movers.invoke({"direction": direction, "days": days, "limit": 5})
        tool_outputs.append(movers_res)

        if "why_move" in sub_intents:
            top_sym_match = re.search(r"\|\s*1\s*\|\s*\*\*([A-Z0-9]+)\*\*", movers_res)
            if top_sym_match:
                top_sym = top_sym_match.group(1)
                why_res = news_explain_price_move.invoke({"symbol": top_sym, "days": days})
                tool_outputs.append(why_res)

    # 3. Comparison Tool
    elif "comparison" in sub_intents and sym and sym2:
        n_days_match = re.search(r"\b(\d+)\s*(?:DAYS?|SESSIONS?)\b", query.upper())
        days = int(n_days_match.group(1)) if n_days_match else 5
        tool_outputs.append(ohlc_relative_performance.invoke({"symbol_a": sym, "symbol_b": sym2, "days": days}))
        tool_outputs.append(ohlc_technical_stats.invoke({"symbol": sym, "lookback_days": 60}))
        tool_outputs.append(ohlc_technical_stats.invoke({"symbol": sym2, "lookback_days": 60}))
        if "news" in sub_intents:
            tool_outputs.append(news_recent_headlines.invoke({"symbol": sym, "limit": 3}))
            tool_outputs.append(news_recent_headlines.invoke({"symbol": sym2, "limit": 3}))
        if "sentiment" in sub_intents:
            tool_outputs.append(news_sentiment_summary.invoke({"symbol": sym}))
            tool_outputs.append(news_sentiment_summary.invoke({"symbol": sym2}))
        if "financials_growth" in sub_intents:
            tool_outputs.append(financials_income_statement.invoke({"symbol": sym, "years": 3}))
            tool_outputs.append(financials_income_statement.invoke({"symbol": sym2, "years": 3}))
        if "financials_shareholding" in sub_intents:
            tool_outputs.append(financials_shareholding_trend.invoke({"symbol": sym}))
            tool_outputs.append(financials_shareholding_trend.invoke({"symbol": sym2}))
        if "financials_balance_sheet" in sub_intents:
            tool_outputs.append(financials_balance_sheet.invoke({"symbol": sym}))
            tool_outputs.append(financials_balance_sheet.invoke({"symbol": sym2}))
        if "financials_banking" in sub_intents:
            tool_outputs.append(financials_banking_quality.invoke({"symbol": sym}))
            tool_outputs.append(financials_banking_quality.invoke({"symbol": sym2}))
        if "quant_wyckoff" in sub_intents:
            tool_outputs.append(quant_wyckoff_structure(sym).to_markdown())
            tool_outputs.append(quant_wyckoff_structure(sym2).to_markdown())
        if "quant_gann" in sub_intents:
            tool_outputs.append(quant_gann_sq9(sym).to_markdown())
            tool_outputs.append(quant_gann_sq9(sym2).to_markdown())
        if "ml_continuation" in sub_intents:
            tool_outputs.append(ml_trend_continuation(sym).to_markdown())
            tool_outputs.append(ml_trend_continuation(sym2).to_markdown())
        if "derivatives_pcr" in sub_intents:
            tool_outputs.append(derivatives_pcr_maxpain(sym).to_markdown())
            tool_outputs.append(derivatives_pcr_maxpain(sym2).to_markdown())

    # 4. Multi-Layered or Single-Stock Tools
    elif sym:
        # OHLC Tools
        if "quote" in sub_intents:
            tool_outputs.append(ohlc_quote_lookup.invoke({"symbol": sym}))
        if "history" in sub_intents:
            n_match = re.search(r"\b(\d+)\s*(?:DAYS?|SESSIONS?)\b", query.upper())
            days = int(n_match.group(1)) if n_match else 10
            tool_outputs.append(ohlc_history_range.invoke({"symbol": sym, "num_days": days}))
        if "stats" in sub_intents or "trend_rag" in sub_intents:
            tool_outputs.append(ohlc_technical_stats.invoke({"symbol": sym, "lookback_days": 60}))

        # News Tools
        if "sentiment" in sub_intents:
            tool_outputs.append(news_sentiment_summary.invoke({"symbol": sym}))
        if "news" in sub_intents:
            tool_outputs.append(news_recent_headlines.invoke({"symbol": sym, "limit": 3}))
        if "why_move" in sub_intents:
            n_match = re.search(r"\b(\d+)\s*(?:DAYS?|SESSIONS?)\b", query.upper())
            days = int(n_match.group(1)) if n_match else 5
            tool_outputs.append(news_explain_price_move.invoke({"symbol": sym, "days": days}))

        # Audited 10-Year Financials Tools
        if "financials_growth" in sub_intents:
            n_match = re.search(r"\b(\d+)\s*(?:YEARS?|YRS?)\b", query.upper())
            yrs = int(n_match.group(1)) if n_match else 3
            tool_outputs.append(financials_income_statement.invoke({"symbol": sym, "years": yrs}))
        if "financials_balance_sheet" in sub_intents:
            tool_outputs.append(financials_balance_sheet.invoke({"symbol": sym}))
        if "financials_shareholding" in sub_intents:
            tool_outputs.append(financials_shareholding_trend.invoke({"symbol": sym}))
        if "financials_banking" in sub_intents:
            tool_outputs.append(financials_banking_quality.invoke({"symbol": sym}))

        # Derivatives & Microstructure Tools
        if "derivatives_pcr" in sub_intents:
            tool_outputs.append(derivatives_pcr_maxpain(sym).to_markdown())
        if "participant_oi" in sub_intents:
            tool_outputs.append(derivatives_participant_oi().to_markdown())
        if "smart_money_deals" in sub_intents:
            tool_outputs.append(smart_money_deal_flow(sym, limit=5).to_markdown())

        # Quant & Mathematical Tools (Gann / Wyckoff)
        if "quant_gann" in sub_intents:
            tool_outputs.append(quant_gann_sq9(sym).to_markdown())
        if "quant_wyckoff" in sub_intents:
            tool_outputs.append(quant_wyckoff_structure(sym).to_markdown())

        # Astro & Celestial Tools
        if "astro_nakshatra" in sub_intents:
            tool_outputs.append(astro_nakshatra_guidance(sym).to_markdown())
        if "astro_aspects" in sub_intents:
            tool_outputs.append(astro_planetary_aspects().to_markdown())

        # Deep Machine Learning Predictive Models
        if "ml_continuation" in sub_intents:
            tool_outputs.append(ml_trend_continuation(sym).to_markdown())
        if "ml_reversal" in sub_intents:
            tool_outputs.append(ml_deep_reversal_score(sym).to_markdown())

    # 5. Market-Wide Non-Symbol Tools
    elif not sym:
        if "participant_oi" in sub_intents:
            tool_outputs.append(derivatives_participant_oi().to_markdown())
        if "astro_aspects" in sub_intents:
            tool_outputs.append(astro_planetary_aspects().to_markdown())
        if "astro_nakshatra" in sub_intents:
            tool_outputs.append(astro_nakshatra_guidance("NIFTY").to_markdown())
        if "smart_money_deals" in sub_intents:
            tool_outputs.append(smart_money_deal_flow(None, limit=5).to_markdown())

    return {"tool_outputs": tool_outputs}


# ── NODE 4: Local LLM Synthesis (Optimized Qwen 2.5:7b) ───────────────────────
def node_llm_synthesis(state: OHLCState) -> Dict[str, Any]:
    """Synthesizes the final grounded analyst response using local Qwen 2.5:7b LLM."""
    query = state["query"]
    symbol = state.get("symbol")
    intent = state.get("intent")
    context = state.get("retrieved_context", "")
    tool_outs = "\n\n".join(state.get("tool_outputs", []))

    # 1. Handle Off-Topic queries politely
    if state.get("is_off_topic"):
        return {
            "final_response": (
                "I am the **Vprofitables Quantitative AI Terminal Copilot**, specialized in "
                "Indian equity price action, technical analytics, moving averages, news sentiment, "
                "and 10-year audited financials for 500+ NSE stocks.\n\n"
                "I cannot assist with general cooking, coding, weather, or non-financial trivia. "
                "Please ask me about any Indian stock (e.g. *Reliance*, *TCS*, *HDFC Bank*), Nifty indices, screener setups, or audited financial growth!"
            )
        }

    # 2. Handle Foreign Assets & Cryptocurrencies
    if state.get("is_foreign_crypto"):
        return {
            "final_response": (
                f"The requested asset ('{query}') is a cryptocurrency, foreign US stock, or unlisted token not traded in the local NSE equity database.\n\n"
                "**Vprofitables Copilot tracks 500+ Indian Equities, Nifty 50, and Bank Nifty.**\n"
                "Available instruments include: **RELIANCE**, **TCS**, **INFY**, **HDFCBANK**, **KOTAKBANK**, **JIOFIN**, **BHARTIARTL**, **SBIN**, and other NSE listed companies."
            )
        }

    # 3. Anti-Hallucination Guardrail for Unknown Asset
    if not tool_outs and not context:
        if intent not in ("general", "calendar", "screener"):
            return {
                "final_response": (
                    f"I could not locate OHLC price, sentiment, or financial data for '{symbol or query}' in the local database.\n\n"
                    "Verified instruments currently indexed include:\n"
                    "- Indices: **NIFTY50**, **BANKNIFTY**\n"
                    "- Major Equities: **RELIANCE**, **TCS**, **INFY**, **HDFCBANK**, **KOTAKBANK**, **JIOFIN**, **BHARTIARTL**, **SBIN**, and other Nifty 500 stocks.\n\n"
                    "Please verify the ticker symbol or ask for recent market dates or screener top movers."
                )
            }

    system_prompt = (
        "You are an Elite Institutional Market Analyst & Quantitative Specialist for the National Stock Exchange of India (NSE).\n"
        "Your responses are grounded 100% STRICTLY in the provided verified data: OHLC price history, news headlines, audited financials, derivatives (PCR/Max Pain), Wyckoff market structure, Gann geometry, Deep ML continuation/reversal signals, and Vedic astrological timing.\n"
        "STRICT MANDATES:\n"
        "1. All currencies are in Indian Rupees (Rs. or INR) and monetary figures in Crores. NEVER cite US Dollar ($) or foreign exchanges (CME/ICE).\n"
        "2. Direct & Focused: Address ONLY the user's specific inquiry immediately. Cite exact figures and tables provided. Do NOT mention unrelated tools, and NEVER output 'Not applicable' for models or indicators the user did not ask about.\n"
        "3. Multi-Stock Comparison: When comparing two stocks, NEVER duplicate numbers across columns or rows. Use Symbol A's exact data for Symbol A, and Symbol B's exact data for Symbol B.\n"
        "4. Exact Dates & Figures: Cite only the dates, prices, and figures provided in the context."
    )

    combined_input = (
        f"USER QUESTION: {query}\n\n"
        f"{'=== DETERMINISTIC TOOL COMPUTATIONS (ALL TERMINAL DOMAINS) ===' if tool_outs else ''}\n"
        f"{tool_outs}\n\n"
        f"{'=== HYBRID RETRIEVED CONTEXT ===' if context else ''}\n"
        f"{context}\n\n"
        "Synthesize a compact, elegant, and strictly grounded institutional response addressing every part of the question."
    )

    response_text = ""
    # Speed-optimized ChatOllama call: qwen2.5:3b (high-speed CPU inference ~5-8s)
    if OLLAMA_AVAILABLE and not state.get("skip_llm"):
        try:
            llm = ChatOllama(
                model="qwen2.5:3b",
                temperature=0.1,
                num_predict=300,
                num_ctx=2048,
                num_thread=8
            )
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=combined_input)
            ]
            llm_result = llm.invoke(messages)
            response_text = llm_result.content.strip()
        except Exception:
            try:
                llm_7b = ChatOllama(model="qwen2.5:7b", temperature=0.1, num_predict=300, num_thread=8)
                llm_result = llm_7b.invoke([SystemMessage(content=system_prompt), HumanMessage(content=combined_input)])
                response_text = llm_result.content.strip()
            except Exception:
                response_text = ""

    if not response_text:
        fallback_lines = []
        if tool_outs:
            fallback_lines.append(tool_outs)
            fallback_lines.append("")
        if context:
            fallback_lines.append(context)
        response_text = "\n".join(fallback_lines)

    return {"final_response": response_text}


# ── BUILD STATE GRAPH ─────────────────────────────────────────────────────────
def build_ohlc_agent_graph():
    builder = StateGraph(OHLCState)

    builder.add_node("analyze_query", node_analyze_query)
    builder.add_node("retrieve_rag", node_retrieve_rag_context)
    builder.add_node("execute_tools", node_execute_tools)
    builder.add_node("llm_synthesis", node_llm_synthesis)

    builder.add_edge(START, "analyze_query")
    builder.add_edge("analyze_query", "retrieve_rag")
    builder.add_edge("retrieve_rag", "execute_tools")
    builder.add_edge("execute_tools", "llm_synthesis")
    builder.add_edge("llm_synthesis", END)

    return builder.compile()


ohlc_graph = build_ohlc_agent_graph()


def run_ohlc_graph(query: str, history: Optional[List[Dict[str, str]]] = None, skip_llm: bool = False) -> Dict[str, Any]:
    initial_state: OHLCState = {
        "query": query,
        "symbol": None,
        "second_symbol": None,
        "intent": "general",
        "sub_intents": [],
        "timeframe": None,
        "history": history or [],
        "retrieved_context": "",
        "tool_outputs": [],
        "is_off_topic": False,
        "is_foreign_crypto": False,
        "skip_llm": skip_llm,
        "final_response": ""
    }
    return ohlc_graph.invoke(initial_state)


if __name__ == "__main__":
    print("[*] Testing Unified Graph with Financials...")
    test_q = "What is TCS 3-year sales and profit growth, balance sheet debt-to-equity, and latest news sentiment?"
    print(f"Query: '{test_q}'")
    st = run_ohlc_graph(test_q)
    print("\nSymbol:", st.get("symbol"))
    print("Sub-intents:", st.get("sub_intents"))
    print("Tool outputs count:", len(st.get("tool_outputs", [])))
    print("\n--- SYNTHESIZED RESPONSE (QWEN 2.5:7b) ---")
    print(st.get("final_response"))
