"""
core/ohlc_rag/chunker.py
========================
Phase 1: OHLC Semantic Document Chunking & Vector Indexing Engine.
Transforms time-series OHLC data from `daily_prices` into enriched semantic
analytical chunks with rolling metrics (returns, range, VWAP, delivery %, regimes)
and indexes them into ChromaDB using HuggingFace sentence embeddings.
"""

import os
import sqlite3
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
import chromadb

# Path configurations
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sys
sys.path.insert(0, BASE_DIR)
from core.paths import get_db_connection as _open_sqlite_connection
DB_PATH = os.path.join(BASE_DIR, "market_data_v2.db")
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")
COLLECTION_NAME = "ohlc_rag_documents"

_EMBEDDINGS = None


def get_embeddings_model():
    """Singleton getter for HuggingFace embeddings."""
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        _EMBEDDINGS = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
    return _EMBEDDINGS


def get_chroma_client():
    """Returns persistent ChromaDB client."""
    return chromadb.PersistentClient(path=CHROMA_PATH)


def get_ohlc_collection():
    """Gets or creates the Chroma collection for OHLC documents."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Enriched semantic OHLC time-series chunks for RAG"}
    )


def load_candles_from_db(symbol: str, limit_days: int = 180) -> pd.DataFrame:
    """Loads daily OHLC candles from SQLite daily_prices table."""
    conn = _open_sqlite_connection(readonly=True, path=DB_PATH)
    query = """
        SELECT symbol, trade_date, open, high, low, close, volume, 
               change_pct, vwap, deliverable_qty, deliverable_pct
        FROM daily_prices
        WHERE symbol = ?
        ORDER BY trade_date DESC
        LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=(symbol.upper(), limit_days))
    conn.close()

    if df.empty:
        return pd.DataFrame()

    df = df.sort_values("trade_date").reset_index(drop=True)
    # Ensure numeric types
    num_cols = ["open", "high", "low", "close", "volume", "change_pct", "vwap", "deliverable_pct"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def classify_regime(pct_change: float, range_pct: float, last_close: float, high: float, low: float) -> str:
    """Classifies the price regime of a trading window."""
    if pct_change >= 4.0:
        if last_close >= high * 0.98:
            return "Bullish Breakout / Strong Momentum"
        return "Bullish Trend"
    elif pct_change <= -4.0:
        if last_close <= low * 1.02:
            return "Bearish Breakdown"
        return "Bearish Trend"
    elif range_pct < 3.5:
        return "Tight Consolidation / Base Building"
    elif pct_change > 0:
        return "Mild Upward Drift"
    else:
        return "Mild Downward Drift"


def chunk_candles_into_documents(df: pd.DataFrame, window_sizes: List[int] = [5, 20]) -> List[Document]:
    """
    Transforms time-series DataFrame into enriched multi-scale semantic Documents.
    Creates 5-day (micro-momentum) and 20-day (swing regime) chunks.
    """
    if df.empty or len(df) < 5:
        return []

    symbol = df["symbol"].iloc[0]
    docs: List[Document] = []
    n = len(df)

    for w in window_sizes:
        if n < w:
            continue
        step = max(1, w // 2)  # 50% overlap for rolling continuity
        for i in range(0, n - w + 1, step):
            window_df = df.iloc[i:i + w]
            start_date = str(window_df["trade_date"].iloc[0])
            end_date = str(window_df["trade_date"].iloc[-1])
            first_open = float(window_df["open"].iloc[0])
            last_close = float(window_df["close"].iloc[-1])
            high_price = float(window_df["high"].max())
            low_price = float(window_df["low"].min())
            
            # Cumulative return over window
            window_return = ((last_close - first_open) / first_open) * 100.0 if first_open > 0 else 0.0
            range_pct = ((high_price - low_price) / low_price) * 100.0 if low_price > 0 else 0.0

            # VWAP & Delivery metrics
            mean_vwap = float(window_df["vwap"].dropna().mean()) if "vwap" in window_df and not window_df["vwap"].dropna().empty else last_close
            vwap_diff_pct = ((last_close - mean_vwap) / mean_vwap) * 100.0 if mean_vwap > 0 else 0.0

            avg_vol = float(window_df["volume"].mean()) if "volume" in window_df else 0.0
            avg_deliv = float(window_df["deliverable_pct"].dropna().mean()) if "deliverable_pct" in window_df and not window_df["deliverable_pct"].dropna().empty else 0.0

            regime = classify_regime(window_return, range_pct, last_close, high_price, low_price)
            timeframe = f"{w}D"

            # Formulate enriched narrative content
            content = (
                f"Stock: {symbol} | Window: {start_date} to {end_date} ({timeframe} Trading Period)\n"
                f"- Price Action: Opened at Rs. {first_open:.2f}, Closed at Rs. {last_close:.2f} ({window_return:+.2f}% change).\n"
                f"- Trading Range: High of Rs. {high_price:.2f}, Low of Rs. {low_price:.2f} (Spread: {range_pct:.2f}%).\n"
                f"- Benchmark VWAP: Average VWAP is Rs. {mean_vwap:.2f}. Close is currently {vwap_diff_pct:+.2f}% relative to VWAP.\n"
                f"- Volume & Institutional Delivery: Average daily volume was {int(avg_vol):,}. "
                f"Average deliverable volume ratio was {avg_deliv:.1f}%.\n"
                f"- Market Structure / Regime: {regime}.\n"
            )

            doc_id = f"{symbol}_{timeframe}_{start_date}_{end_date}"
            metadata = {
                "doc_id": doc_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "start_date": start_date,
                "end_date": end_date,
                "open": round(first_open, 2),
                "close": round(last_close, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "return_pct": round(window_return, 2),
                "range_pct": round(range_pct, 2),
                "vwap": round(mean_vwap, 2),
                "avg_delivery_pct": round(avg_deliv, 2),
                "regime": regime
            }

            docs.append(Document(page_content=content, metadata=metadata))

    return docs


def index_symbol_chunks(symbol: str, limit_days: int = 180) -> int:
    """
    Ingests and embeds OHLC documents for a symbol into ChromaDB.
    Returns number of newly indexed documents.
    """
    df = load_candles_from_db(symbol, limit_days=limit_days)
    if df.empty:
        return 0

    docs = chunk_candles_into_documents(df)
    if not docs:
        return 0

    collection = get_ohlc_collection()
    embeddings = get_embeddings_model()

    # Query existing IDs to avoid redundant re-embedding
    doc_ids = [d.metadata["doc_id"] for d in docs]
    try:
        existing = collection.get(ids=doc_ids)
        existing_ids = set(existing.get("ids", []))
    except Exception:
        existing_ids = set()

    new_docs = [d for d in docs if d.metadata["doc_id"] not in existing_ids]
    if not new_docs:
        return 0

    texts = [d.page_content for d in new_docs]
    metadatas = [d.metadata for d in new_docs]
    ids = [d.metadata["doc_id"] for d in new_docs]

    # Batch embed
    vectors = embeddings.embed_documents(texts)
    collection.add(
        ids=ids,
        embeddings=vectors,
        documents=texts,
        metadatas=metadatas
    )

    return len(new_docs)


def index_batch_symbols(symbols: List[str], limit_days: int = 180) -> Dict[str, int]:
    """Indexes multiple symbols into ChromaDB."""
    results = {}
    for sym in symbols:
        try:
            cnt = index_symbol_chunks(sym, limit_days=limit_days)
            results[sym] = cnt
        except Exception as e:
            results[sym] = -1
    return results


if __name__ == "__main__":
    print("[*] Testing OHLC Semantic Chunker on RELIANCE and TCS...")
    res = index_batch_symbols(["RELIANCE", "TCS", "INFY", "HDFCBANK"], limit_days=120)
    print("Ingestion results:", res)
    col = get_ohlc_collection()
    print("Total documents in collection:", col.count())
