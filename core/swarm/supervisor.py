"""
core/swarm/supervisor.py
========================
Master Supervisor Router for the Hierarchical Multi-Agent Swarm.
Decomposes queries across 6 specialized quantitative domains:
  1. 'derivatives_agent'   - Options Microstructure, PCR, Max Pain, Bulk Deals
  2. 'quant_agent'         - Gann Square of 9, Wyckoff Phases & Compression
  3. 'deep_ml_agent'       - PyTorch Continuation MLP & XGBoost Reversal
  4. 'astro_agent'         - Vedic Nakshatras & Planetary Aspects
  5. 'fundamental_agent'   - 10Y Audited Financials, Balance Sheets & FinBERT News
  6. 'ohlc_agent'          - Daily Candles, SMA/ATR Stats, Screener & Calendar
"""

import re
from typing import Dict, Any, List, Optional
from core.swarm.state import SwarmState
from core.ohlc_rag.retriever import extract_symbol_and_intent, KNOWN_SYMBOLS

OFF_TOPIC_PATTERNS = [
    r"\b(RECIPE|COOK\w*|PASTA|PIZZA|FOOD|CAKE|COOKIES?|INGREDIENTS)\b",
    r"\b(WEATHER|TEMPERATURE|RAIN|FORECAST|CLIMATE)\b",
    r"\b(PYTHON|JAVA|JAVASCRIPT|FUNCTION|CODE|INVERT|BINARY TREE|ALGORITHM|DEBUG)\b",
    r"\b(WORLD CUP|FOOTBALL|SOCCER|CRICKET|MATCH|MOVIE|ACTOR|CELEBRITY|SONG|POEM)\b",
    r"\b(PRESIDENT|CAPITAL OF|WHO WON|HISTORY OF|ROME|DINOSAUR)\b"
]

FOREIGN_CRYPTO_PATTERNS = [
    r"\b(BITCOIN|BTC|ETHEREUM|ETH|DOGECOIN|DOGE|CRYPTO|SOLANA|BINANCE)\b",
    r"\b(TESLA|TSLA|APPLE|AAPL|GOOGLE|ALPHABET|GOOGL|AMAZON|AMZN|MICROSOFT|MSFT|META|NVIDIA|NVDA)\b"
]

def node_supervisor(state: SwarmState) -> Dict[str, Any]:
    """
    Master supervisory intent classifier & entity resolver.
    Extracts entities and selects the exact domain specialist agents needed.
    """
    query = state["query"]
    q_upper = query.upper()
    history = state.get("history") or []

    # Fast Indian equity presence check
    has_indian_stock = any(re.search(r"\b" + re.escape(alias) + r"\b", q_upper) for alias in KNOWN_SYMBOLS)

    # 1. Off-Topic Check
    if not has_indian_stock:
        for pat in OFF_TOPIC_PATTERNS:
            if re.search(pat, q_upper):
                return {
                    "symbol": None,
                    "second_symbol": None,
                    "intent": "off_topic",
                    "domains": [],
                    "sub_intents": [],
                    "is_off_topic": True,
                    "is_foreign_crypto": False
                }

    # 2. Crypto / Foreign Asset Check
    if not has_indian_stock:
        for pat in FOREIGN_CRYPTO_PATTERNS:
            if re.search(pat, q_upper):
                return {
                    "symbol": None,
                    "second_symbol": None,
                    "intent": "foreign_crypto",
                    "domains": [],
                    "sub_intents": [],
                    "is_off_topic": False,
                    "is_foreign_crypto": True
                }

    # 3. Calendar Check
    if re.search(r"\b(TRADING DATES|TRADING DAYS|LAST \d+ TRADING DATES|DATES DATA|DATES WE HAVE|CALENDAR DATES|RECENT TRADING SESSION DATE|LATEST SESSION DATE|MOST RECENT SESSION)\b", q_upper):
        return {
            "symbol": None,
            "second_symbol": None,
            "intent": "calendar",
            "domains": ["ohlc_agent"],
            "sub_intents": ["calendar"],
            "is_off_topic": False,
            "is_foreign_crypto": False
        }

    # 4. Screener Check
    if re.search(r"\b(FELL MOST|DROPPED MOST|FALLEN MOST|GAINED MOST|GAINED THE MOST|TOP LOSERS?|TOP GAINERS?|BIGGEST DROP|BIGGEST LOSERS?|BIGGEST GAINERS?|MARKET LOSERS?|TOP PERFORMERS?|BIGGEST FALL|BIGGEST MARKET DROP)\b", q_upper):
        sub_ints = ["screener"]
        domains = ["ohlc_agent"]
        if re.search(r"\b(WHY|SUMMARIZE WHY|REASON|NEWS)\b", q_upper):
            sub_ints.append("why_move")
            domains.append("fundamental_agent")
        return {
            "symbol": None,
            "second_symbol": None,
            "intent": "screener",
            "domains": domains,
            "sub_intents": sub_ints,
            "timeframe": "5D",
            "is_off_topic": False,
            "is_foreign_crypto": False
        }

    # 5. Multi-Symbol / Comparison Check
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
        domains = ["ohlc_agent"]

        if re.search(r"\b(NEWS|HEADLINES|SENTIMENT|FINBERT)\b", q_upper):
            domains.append("fundamental_agent")
            sub_ints.extend(["news", "sentiment"])
        if re.search(r"\b(SALES|PROFIT|REVENUE|FINANCIALS|EARNINGS|DEBT|BALANCE SHEET|SHAREHOLDING|NPA)\b", q_upper):
            domains.append("fundamental_agent")
            sub_ints.extend(["financials_growth", "financials_balance_sheet"])
        if re.search(r"\b(WYCKOFF|ACCUMULATION|DISTRIBUTION PHASE|GANN|SQ9)\b", q_upper):
            domains.append("quant_agent")
            sub_ints.extend(["quant_wyckoff", "quant_gann"])
        if re.search(r"\b(CONTINUATION|MLP|DEEP MODEL|REVERSAL)\b", q_upper):
            domains.append("deep_ml_agent")
            sub_ints.extend(["ml_continuation", "ml_reversal"])
        if re.search(r"\b(PCR|MAX PAIN|OPTION CHAIN|CALL WALL)\b", q_upper):
            domains.append("derivatives_agent")
            sub_ints.append("derivatives_pcr")

        # Deduplicate domains
        domains = list(dict.fromkeys(domains))
        return {
            "symbol": sym1,
            "second_symbol": sym2,
            "intent": "comparison",
            "domains": domains,
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

    # Conversational Anaphora ('it', 'its', 'that stock', 'this symbol', 'the same')
    if not sym1 and history:
        for turn in reversed(history):
            prior_sym = turn.get("symbol")
            if prior_sym:
                if re.search(r"\b(IT|ITS|THAT STOCK|THIS STOCK|THIS SYMBOL|THAT SYMBOL|THE SYMBOL|THE COMPANY|THAT COMPANY|THIS COMPANY|SAME|THIS ONE)\b", q_upper) or len(query.split()) <= 7:
                    sym1 = prior_sym
                    break

    # If state already carried an active UI symbol
    if not sym1 and state.get("symbol"):
        sym1 = state.get("symbol")

    # Discard numbers or short noise
    if sym1 and (sym1.isdigit() or (len(sym1) <= 2 and sym1 not in {"LT", "IT"})):
        sym1 = None

    # Check for Market-Wide Queries or Overall Market Trend
    if not sym1:
        # Check if user is asking for general market trends / market overview
        if re.search(r"\b(RECENT TRENDS?\s+(IN\s+)?(THE\s+)?MARKET|MARKET TRENDS?|TREND IN (THE )?MARKET|HOW IS THE MARKET|MARKET OVERVIEW|MARKET STATUS|WHAT IS THE MARKET DOING|OVERALL MARKET|STATE OF THE MARKET|MARKET DIRECTION)\b", q_upper):
            return {
                "symbol": "NIFTY50",
                "second_symbol": "BANKNIFTY",
                "intent": "market_trend",
                "domains": ["ohlc_agent", "quant_agent"],
                "sub_intents": ["quote", "stats", "quant_wyckoff", "screener"],
                "timeframe": "5D",
                "is_off_topic": False,
                "is_foreign_crypto": False
            }

        market_domains = []
        market_sub_intents = []
        if re.search(r"\b(PARTICIPANT OI|FII\b.*?\bFUTURES|FII LONG|PRO CALLS|CLIENT PUTS|SMART MONEY BIAS|DII LONG|FII NET|INDEX FUTURES)\b", q_upper) or ("FII" in q_upper and any(w in q_upper for w in ["FUTURES", "CONTRACT", "POSITION", "LONG"])):
            market_domains.append("derivatives_agent")
            market_sub_intents.append("participant_oi")
        if re.search(r"\b(PLANETARY ASPECTS?|RETROGRADE|PLANET STATIONS?|CONJUNCTION|OPPOSITION|TRINE)\b", q_upper) or ("PLANETARY" in q_upper and "ASPECT" in q_upper):
            market_domains.append("astro_agent")
            market_sub_intents.append("astro_aspects")
        if re.search(r"\b(NAKSHATRA|RAHU KAAL|ABHIJIT MUHURAT)\b", q_upper):
            market_domains.append("astro_agent")
            market_sub_intents.append("astro_nakshatra")
        if re.search(r"\b(BULK DEALS?|BLOCK DEALS?|INSTITUTIONAL\b.*?\bFLOW|DEAL FLOWS?|BIG MONEY FLOW)\b", q_upper) or ("DEAL" in q_upper and any(w in q_upper for w in ["BULK", "BLOCK", "FLOW", "INSTITUTIONAL"])):
            market_domains.append("derivatives_agent")
            market_sub_intents.append("smart_money_deals")

        if market_domains:
            return {
                "symbol": None,
                "second_symbol": None,
                "intent": "market_wide",
                "domains": list(dict.fromkeys(market_domains)),
                "sub_intents": market_sub_intents,
                "timeframe": None,
                "is_off_topic": False,
                "is_foreign_crypto": False
            }

    # 7. Single Stock Intent & Domain Routing
    domains = []
    sub_intents = []

    if sym1:
        # Check Comprehensive Dossier
        if re.search(r"\b(FULL DOSSIER|COMPLETE REPORT|COMPREHENSIVE ANALYSIS|QUANT DOSSIER|360 ANALYSIS)\b", q_upper):
            return {
                "symbol": sym1,
                "second_symbol": None,
                "intent": "full_dossier",
                "domains": ["ohlc_agent", "derivatives_agent", "quant_agent", "deep_ml_agent", "astro_agent", "fundamental_agent"],
                "sub_intents": ["dossier", "quote", "stats", "derivatives_pcr", "quant_gann", "quant_wyckoff", "ml_continuation", "astro_nakshatra", "financials_growth"],
                "timeframe": timeframe,
                "is_off_topic": False,
                "is_foreign_crypto": False
            }

        # Domain 1: Derivatives
        if re.search(r"\b(PCR|PUT CALL RATIO|MAX PAIN|OPTION CHAIN|CALL WALL|PUT WALL|IV SKEW|FII LONG|PARTICIPANT OI)\b", q_upper):
            domains.append("derivatives_agent")
            sub_intents.append("derivatives_pcr")
        if re.search(r"\b(BULK DEALS?|BLOCK DEALS?|INSTITUTIONAL BUY|INSTITUTIONAL FLOW|BIG MONEY|DEALS? FLOW)\b", q_upper):
            domains.append("derivatives_agent")
            sub_intents.append("smart_money_deals")

        # Domain 2: Quant Math (Gann / Wyckoff)
        if re.search(r"\b(GANN|SQUARE OF 9|SQ9|GANN ANGLES?|GANN LEVELS?|CARDINAL|ORDINAL|ROTATION LEVELS?|ANGLES?|360 DEGREE)\b", q_upper):
            domains.append("quant_agent")
            sub_intents.append("quant_gann")
        if re.search(r"\b(WYCKOFF|ACCUMULATION|DISTRIBUTION PHASE|SPRING|UPTHRUST|VOLATILITY COMPRESSION|VOLATILITY SQUEEZE|HEDGE FUND\w*|CORRIDOR)\b", q_upper):
            domains.append("quant_agent")
            sub_intents.append("quant_wyckoff")

        # Domain 3: Deep ML Models
        if re.search(r"\b(DEEP CONTINUATION|MLP|CONTINUATION\w*|TREND CONTINUATION|WAVELET\w*|CWT|NEURAL NETWORK|DEEP LEARNING|ML MODEL|DEEP MODEL|ABSORPTION)\b", q_upper):
            domains.append("deep_ml_agent")
            sub_intents.append("ml_continuation")
        if re.search(r"\b(DEEP REVERSAL|REVERSAL\w*|XGBOOST|SWING EXHAUSTION|CONVICTION SCORE|DIRECTIONAL REVERSAL|TURNING POINT|PIVOT DATE)\b", q_upper):
            domains.append("deep_ml_agent")
            sub_intents.append("ml_reversal")
            # If asking about timing, day, or date, also invoke Gann & Astro timing
            if any(w in q_upper for w in ["DAY", "DATE", "WHEN", "NEXT", "TIME", "CYCLE"]):
                domains.extend(["quant_agent", "astro_agent"])
                sub_intents.extend(["quant_gann", "astro_aspects"])

        # Domain 4: Astro & Celestial
        if re.search(r"\b(NAKSHATRA|RAHU KAAL|ABHIJIT MUHURAT|ASTRO\w*|VEDIC|CELESTIAL|HOROSCOPE|ZODIAC)\b", q_upper):
            domains.append("astro_agent")
            sub_intents.append("astro_nakshatra")
        if re.search(r"\b(PLANETARY\w*|RETROGRADE|PLANET STATIONS?|HARMONIC\w*)\b", q_upper):
            domains.append("astro_agent")
            sub_intents.append("astro_aspects")

        # Domain 5: Audited Financials & News Sentiment
        if re.search(r"\b(SALES|REVENUE|PROFIT|NET PROFIT|PAT|OPM|MARGIN|CAGR|GROWTH|INCOME STATEMENT|EARNINGS)\b", q_upper):
            domains.append("fundamental_agent")
            sub_intents.append("financials_growth")
        if re.search(r"\b(DEBT|BORROWING|BALANCE SHEET|RESERVES|ASSETS|CASH|LEVERAGE|SOLVENCY|DEBT TO EQUITY)\b", q_upper):
            domains.append("fundamental_agent")
            sub_intents.append("financials_balance_sheet")
        if re.search(r"\b(FII|DII|PROMOTER|STAKE|SHAREHOLDING|OWNERSHIP|PLEDGED)\b", q_upper):
            domains.append("fundamental_agent")
            sub_intents.append("financials_shareholding")
        if re.search(r"\b(NPA|BAD LOANS?|ASSET QUALITY|GROSS NPA|NET NPA)\b", q_upper):
            domains.append("fundamental_agent")
            sub_intents.append("financials_banking")
        if re.search(r"\b(SENTIMENT|SENTIMENTS|MOOD|FINBERT|BIAS|REGULATORY RISK|MANAGEMENT CHANGE|GUIDANCE)\b", q_upper):
            domains.append("fundamental_agent")
            sub_intents.append("sentiment")
        if re.search(r"\b(NEWS|HEADLINES?|ANNOUNCEMENT|CATALYST|UPDATE)\b", q_upper):
            domains.append("fundamental_agent")
            sub_intents.append("news")
        if re.search(r"\b(WHY|REASON|DRIVING|DROP|FALL|SURGE|EXPLAIN)\b", q_upper):
            domains.append("fundamental_agent")
            sub_intents.append("why_move")

        # Domain 6: OHLC Technicals (Quotes, Candles, Stats)
        if re.search(r"\b(QUOTE|PRICE|LTP|CLOSE|TODAY|YESTERDAY)\b", q_upper):
            domains.append("ohlc_agent")
            sub_intents.append("quote")
        if re.search(r"\b(TABLE|HISTORY|CANDLES|LAST \d+ DAYS)\b", q_upper):
            domains.append("ohlc_agent")
            sub_intents.append("history")
        if re.search(r"\b(52W|52-WEEK|LOW|HIGH|SMA|ATR|STATS|INDICATOR|VOLATILITY)\b", q_upper):
            domains.append("ohlc_agent")
            sub_intents.append("stats")

        # Default fallback to OHLC stats if no domain matched
        if not domains:
            domains.append("ohlc_agent")
            sub_intents.append("stats")

        intent = "multi_domain" if len(domains) > 1 else domains[0]
    else:
        intent = "general"
        domains = ["ohlc_agent"]

    return {
        "symbol": sym1,
        "second_symbol": None,
        "intent": intent,
        "domains": list(dict.fromkeys(domains)),
        "sub_intents": sub_intents,
        "timeframe": timeframe,
        "is_off_topic": False,
        "is_foreign_crypto": False
    }

def route_to_specialists(state: SwarmState) -> List[str]:
    """Conditional routing function: directs state to the selected domain agents."""
    if state.get("is_off_topic") or state.get("is_foreign_crypto"):
        return ["aggregator"]
    
    domains = state.get("domains") or []
    if not domains:
        return ["ohlc_agent"]
    
    return domains
