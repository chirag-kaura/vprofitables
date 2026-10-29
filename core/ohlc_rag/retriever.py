"""
core/ohlc_rag/retriever.py
==========================
Phase 2: Hybrid Query Retriever Engine for OHLC Data.
Combines:
  1. Dense Semantic Vector Retrieval from ChromaDB (`ohlc_rag_documents`)
  2. Entity & Temporal Query Parsing (Symbol, timeframe, regime filter)
  3. Relational SQL Ground Truth Lookup from `daily_prices`
  4. Context Fusion (Semantic trend narratives + exact numerical session tables)
"""

import os
import sys
import re
import sqlite3
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_core.documents import Document

from core.ohlc_rag.chunker import (
    get_ohlc_collection,
    get_embeddings_model,
    index_symbol_chunks,
    DB_PATH
)

# Known major ticker aliases for fast regex resolution (sorted by match priority)
KNOWN_SYMBOLS = {
    "NIFTY 50": "NIFTY50",
    "NIFTY-50": "NIFTY50",
    "NIFTY50": "NIFTY50",
    "NIFTY": "NIFTY50",
    "BANK NIFTY": "BANKNIFTY",
    "BANKNIFTY": "BANKNIFTY",
    "BANK-NIFTY": "BANKNIFTY",
    "JIO FINANCIAL": "JIOFIN",
    "JIO FINANCE": "JIOFIN",
    "JIOFINANCE": "JIOFIN",
    "JIOFIN": "JIOFIN",
    "KOTAK BANK": "KOTAKBANK",
    "KOTAK": "KOTAKBANK",
    "KOTAKBANK": "KOTAKBANK",
    "HDFC BANK": "HDFCBANK",
    "HDFCBANK": "HDFCBANK",
    "HDFC": "HDFCBANK",
    "RELIANCE": "RELIANCE",
    "TCS": "TCS",
    "INFOSYS": "INFY",
    "INFY": "INFY",
    "ICICI BANK": "ICICIBANK",
    "ICICIBANK": "ICICIBANK",
    "STATE BANK OF INDIA": "SBIN",
    "STATE BANK": "SBIN",
    "SBIN": "SBIN",
    "SBI": "SBIN",
    "BHARTI AIRTEL": "BHARTIARTL",
    "BHARTI": "BHARTIARTL",
    "AIRTEL": "BHARTIARTL",
    "BHARTIARTL": "BHARTIARTL",
    "ITC": "ITC",
    "LARSEN & TOUBRO": "LT",
    "LARSEN": "LT",
    "L&T": "LT",
    "LT": "LT",
    "TATA MOTORS": "TATAMOTORS",
    "TATAMOTORS": "TATAMOTORS",
    "TATA STEEL": "TATASTEEL",
    "TATASTEEL": "TATASTEEL",
    "WIPRO": "WIPRO",
    "MARUTI SUZUKI": "MARUTI",
    "MARUTI": "MARUTI",
    "SUN PHARMA": "SUNPHARMA",
    "SUNPHARMA": "SUNPHARMA",
    "AXIS BANK": "AXISBANK",
    "AXISBANK": "AXISBANK",
    "BAJAJ FINANCE": "BAJFINANCE",
    "BAJFINANCE": "BAJFINANCE",
    "BAJAJ FINSERV": "BAJAJFINSV",
    "BAJAJFINSV": "BAJAJFINSV",
    "HCL TECH": "HCLTECH",
    "HCLTECH": "HCLTECH"
}

COMMON_ENGLISH_WORDS = {
    "WHAT", "ABOUT", "WHICH", "GIVE", "TELL", "SHOW", "LAST", "DAYS", "DATE", "DATES",
    "DATA", "HAVE", "FELL", "MOST", "GAIN", "DROP", "LOSE", "LOSS", "PRICE", "TODAY",
    "YESTERDAY", "WEEK", "MONTH", "YEAR", "HIGH", "CLOSE", "OPEN", "COMPARE", "VERSUS",
    "SUMMARY", "SUMMARIZE", "WHY", "BASED", "GIVES", "MAXIMUM", "MINIMUM", "BEST", "WORST"
}


@dataclass
class HybridRetrievalResult:
    symbol: Optional[str]
    timeframe: Optional[str]
    semantic_docs: List[Document]
    latest_candles: List[Dict[str, Any]]
    stats_summary: Dict[str, Any]
    formatted_context: str


def extract_symbol_and_intent(query: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extracts stock symbol and timeframe preference from user query.
    """
    q_upper = query.upper()
    extracted_sym = None
    
    # Check known aliases (prioritize longer keys first)
    sorted_aliases = sorted(KNOWN_SYMBOLS.keys(), key=len, reverse=True)
    for alias in sorted_aliases:
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, q_upper):
            extracted_sym = KNOWN_SYMBOLS[alias]
            break

    # If not found in known dict, check database symbols (ignoring common English words and pure numbers)
    if not extracted_sym:
        potential_words = [w for w in re.findall(r"\b[A-Z]{3,12}\b", q_upper) if w not in COMMON_ENGLISH_WORDS]
        if potential_words:
            conn = sqlite3.connect(DB_PATH)
            placeholders = ",".join(["?"] * len(potential_words))
            cur = conn.cursor()
            cur.execute(f"SELECT symbol FROM daily_prices WHERE symbol IN ({placeholders}) LIMIT 1", potential_words)
            row = cur.fetchone()
            conn.close()
            if row:
                extracted_sym = row[0]

    # Timeframe extraction
    timeframe = None
    if re.search(r"\b(20[\s-]?DAYS?|MONTHS?|MONTHLY|SWING|4[\s-]?WEEKS?)\b", q_upper):
        timeframe = "20D"
    elif re.search(r"\b(5[\s-]?DAYS?|WEEKS?|WEEKLY|RECENT|SHORT[\s-]?TERM)\b", q_upper):
        timeframe = "5D"

    return extracted_sym, timeframe


def get_latest_candles_sql(symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetches exact latest OHLC candles from SQLite."""
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT trade_date, open, high, low, close, volume, 
               change_pct, vwap, deliverable_pct
        FROM daily_prices
        WHERE symbol = ?
        ORDER BY trade_date DESC
        LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=(symbol.upper(), limit))
    conn.close()
    if df.empty:
        return []
    df = df.sort_values("trade_date").reset_index(drop=True)
    return df.to_dict(orient="records")


def compute_ohlc_stats(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes instant statistical summary over recent candles."""
    if not candles:
        return {}
    
    closes = [c["close"] for c in candles if c.get("close") is not None and not pd.isna(c.get("close"))]
    highs = [c["high"] for c in candles if c.get("high") is not None and not pd.isna(c.get("high"))]
    lows = [c["low"] for c in candles if c.get("low") is not None and not pd.isna(c.get("low"))]
    volumes = [c["volume"] for c in candles if c.get("volume") is not None and not pd.isna(c.get("volume"))]
    deliveries = [c["deliverable_pct"] for c in candles if c.get("deliverable_pct") is not None and not pd.isna(c.get("deliverable_pct"))]

    if not closes:
        return {}

    first_close = closes[0]
    last_close = closes[-1]
    pct_return = ((last_close - first_close) / first_close) * 100.0 if first_close > 0 else 0.0

    last_vwap = candles[-1].get("vwap")
    latest_vwap_val = round(float(last_vwap), 2) if last_vwap is not None and not pd.isna(last_vwap) else None

    return {
        "sessions_count": len(candles),
        "start_date": candles[0]["trade_date"],
        "end_date": candles[-1]["trade_date"],
        "latest_close": round(last_close, 2),
        "period_high": round(max(highs), 2) if highs else last_close,
        "period_low": round(min(lows), 2) if lows else last_close,
        "period_return_pct": round(pct_return, 2),
        "avg_volume": int(sum(volumes) / len(volumes)) if volumes else 0,
        "avg_delivery_pct": round(sum(deliveries) / len(deliveries), 2) if deliveries else None,
        "latest_vwap": latest_vwap_val
    }


class OHLCHybridRetriever:
    """
    Hybrid Retriever that queries ChromaDB vector documents and combines
    them with exact SQL time-series data.
    """
    def __init__(self):
        self.collection = get_ohlc_collection()
        self.embeddings = get_embeddings_model()

    def retrieve(self, query: str, top_k: int = 4) -> HybridRetrievalResult:
        symbol, timeframe = extract_symbol_and_intent(query)
        
        # If symbol is found, ensure it is indexed in Chroma
        if symbol:
            count = self.collection.count()
            # Check if this symbol has documents in collection
            res = self.collection.get(where={"symbol": symbol}, limit=1)
            if not res or not res.get("ids"):
                index_symbol_chunks(symbol, limit_days=180)

        # Build ChromaDB metadata filter
        where_filter = {}
        if symbol and timeframe:
            where_filter = {"$and": [{"symbol": symbol}, {"timeframe": timeframe}]}
        elif symbol:
            where_filter = {"symbol": symbol}
        elif timeframe:
            where_filter = {"timeframe": timeframe}

        # Embed query and search Chroma
        query_vec = self.embeddings.embed_query(query)
        query_kwargs = {
            "query_embeddings": [query_vec],
            "n_results": top_k
        }
        if where_filter:
            query_kwargs["where"] = where_filter

        try:
            results = self.collection.query(**query_kwargs)
        except Exception:
            # Fallback without where filter if filter was too restrictive
            query_kwargs.pop("where", None)
            results = self.collection.query(**query_kwargs)

        semantic_docs: List[Document] = []
        if results and results.get("documents") and results["documents"][0]:
            for text, meta in zip(results["documents"][0], results["metadatas"][0]):
                semantic_docs.append(Document(page_content=text, metadata=meta))

        # Relational SQL exact data
        latest_candles = []
        stats = {}
        if symbol:
            latest_candles = get_latest_candles_sql(symbol, limit=10)
            stats = compute_ohlc_stats(latest_candles)

        # Build fused context string
        context_parts = []
        if symbol and stats:
            context_parts.append(f"### EXACT OHLC GROUND TRUTH FOR {symbol}:")
            vwap_str = f"Rs. {stats.get('latest_vwap')}" if stats.get('latest_vwap') is not None else "N/A"
            deliv_str = f"{stats.get('avg_delivery_pct')}%" if stats.get('avg_delivery_pct') is not None else "N/A"
            context_parts.append(
                f"- Period: {stats.get('start_date')} to {stats.get('end_date')} ({stats.get('sessions_count')} trading sessions)\n"
                f"- Current / Latest Close: Rs. {stats.get('latest_close')}\n"
                f"- Period Range: High Rs. {stats.get('period_high')}, Low Rs. {stats.get('period_low')}\n"
                f"- Net Period Return: {stats.get('period_return_pct'):+.2f}%\n"
                f"- Latest VWAP: {vwap_str}\n"
                f"- Avg Daily Volume: {stats.get('avg_volume'):,}\n"
                f"- Avg Deliverable %: {deliv_str}\n"
            )
            
            # Format candle table
            context_parts.append("#### Recent Trading Sessions Table:")
            context_parts.append("| Date | Open | High | Low | Close | Chg% | VWAP | Volume | Delivery% |")
            context_parts.append("|---|---|---|---|---|---|---|---|---|")
            for c in latest_candles[-5:]:
                vwap_val = round(c['vwap'], 2) if c.get('vwap') else '-'
                deliv_val = f"{c['deliverable_pct']:.1f}%" if c.get('deliverable_pct') is not None else '-'
                chg_val = f"{c['change_pct']:+.2f}%" if c.get('change_pct') is not None else '-'
                vol_val = f"{int(c['volume']):,}" if c.get('volume') else '-'
                context_parts.append(
                    f"| {c['trade_date']} | Rs. {c['open']:.2f} | Rs. {c['high']:.2f} | Rs. {c['low']:.2f} | "
                    f"Rs. {c['close']:.2f} | {chg_val} | Rs. {vwap_val} | {vol_val} | {deliv_val} |"
                )

        if semantic_docs:
            context_parts.append("\n### SEMANTIC TIME-SERIES RAG CHUNKS (MULTI-DAY REGIMES):")
            for idx, doc in enumerate(semantic_docs, 1):
                context_parts.append(f"[{idx}] {doc.page_content.strip()}")

        formatted_context = "\n".join(context_parts)

        return HybridRetrievalResult(
            symbol=symbol,
            timeframe=timeframe,
            semantic_docs=semantic_docs,
            latest_candles=latest_candles,
            stats_summary=stats,
            formatted_context=formatted_context
        )


if __name__ == "__main__":
    print("[*] Testing Phase 2 Hybrid Query Retriever...")
    retriever = OHLCHybridRetriever()
    test_queries = [
        "How has RELIANCE traded recently over the last 2 weeks?",
        "What is the price action and VWAP level of TCS?"
    ]
    for q in test_queries:
        print(f"\n==================== QUERY: {q} ====================")
        res = retriever.retrieve(q, top_k=2)
        print(f"Extracted Symbol: {res.symbol} | Timeframe: {res.timeframe}")
        print(f"Retrieved {len(res.semantic_docs)} semantic docs.")
        print("Fused Context Preview:")
        print(res.formatted_context[:500] + "...")
