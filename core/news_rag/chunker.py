"""
core/news_rag/chunker.py
========================
News & Sentiment Semantic Chunking & Vector Indexing Engine.
Extracts news articles, FinBERT sentiment scores, and risk tags from SQLite
(`news_sentiment`) and embeds them into ChromaDB (`news_sentiment_rag`).
"""

import os
import sys
import sqlite3
import pandas as pd
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
import chromadb

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.ohlc_rag.chunker import get_embeddings_model, get_chroma_client, DB_PATH

NEWS_COLLECTION_NAME = "news_sentiment_rag"


def get_news_collection():
    """Gets or creates the Chroma collection for news & sentiment documents."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=NEWS_COLLECTION_NAME,
        metadata={"description": "Enriched news headlines and FinBERT sentiment documents for RAG"}
    )


def load_news_from_db(symbol: Optional[str] = None, limit: int = 200) -> pd.DataFrame:
    """Loads news headlines and sentiment metrics from SQLite news_sentiment table."""
    conn = sqlite3.connect(DB_PATH)
    if symbol:
        query = """
            SELECT id, symbol, title, snippet, source, published_at, 
                   raw_score, label, finbert_prob_bullish, 
                   is_guidance_raised, is_regulatory_risk, is_management_change, url
            FROM news_sentiment
            WHERE symbol = ?
            ORDER BY published_at DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(symbol.upper(), limit))
    else:
        query = """
            SELECT id, symbol, title, snippet, source, published_at, 
                   raw_score, label, finbert_prob_bullish, 
                   is_guidance_raised, is_regulatory_risk, is_management_change, url
            FROM news_sentiment
            ORDER BY published_at DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(limit,))
    conn.close()
    return df


def chunk_news_into_documents(df: pd.DataFrame) -> List[Document]:
    """Transforms raw news rows into rich semantic Documents with FinBERT metadata."""
    if df.empty:
        return []

    docs: List[Document] = []
    for _, row in df.iterrows():
        nid = str(row["id"])
        sym = str(row.get("symbol") or "MARKET")
        title = (row.get("title") or "").strip()
        snippet = (row.get("snippet") or "").strip()
        source = str(row.get("source") or "Market Feed")
        pub_at = str(row.get("published_at") or "")
        label = str(row.get("label") or "Neutral")
        score = float(row.get("raw_score") or 0.0)
        bullish_prob = float(row.get("finbert_prob_bullish") or 0.5)

        # Risk tags
        risk_tags = []
        if row.get("is_regulatory_risk") == 1:
            risk_tags.append("Regulatory / Policy Risk")
        if row.get("is_management_change") == 1:
            risk_tags.append("Management Transition")
        if row.get("is_guidance_raised") == 1:
            risk_tags.append("Guidance Raised / Upgraded")
        tags_str = ", ".join(risk_tags) if risk_tags else "None"

        # Content for dense vector embedding
        content = (
            f"Symbol: {sym} | Published: {pub_at} | Source: {source}\n"
            f"Headline: {title}\n"
            f"Summary: {snippet}\n"
            f"Sentiment: {label} (FinBERT Score: {score:+.2f}, Bullish Prob: {bullish_prob:.1%})\n"
            f"Identified Catalysts/Risks: {tags_str}"
        )

        doc_id = f"news_{nid}_{sym}"
        metadata = {
            "doc_id": doc_id,
            "news_id": nid,
            "symbol": sym,
            "published_at": pub_at,
            "source": source,
            "label": label,
            "score": round(score, 3),
            "bullish_prob": round(bullish_prob, 3),
            "has_regulatory_risk": bool(row.get("is_regulatory_risk") == 1),
            "has_mgmt_change": bool(row.get("is_management_change") == 1),
            "guidance_raised": bool(row.get("is_guidance_raised") == 1)
        }
        docs.append(Document(page_content=content, metadata=metadata))

    return docs


def index_symbol_news(symbol: str, limit: int = 50) -> int:
    """Indexes recent news for a symbol into ChromaDB news collection."""
    df = load_news_from_db(symbol=symbol, limit=limit)
    if df.empty:
        return 0

    docs = chunk_news_into_documents(df)
    if not docs:
        return 0

    col = get_news_collection()
    embeddings = get_embeddings_model()

    doc_ids = [d.metadata["doc_id"] for d in docs]
    try:
        existing = col.get(ids=doc_ids)
        existing_ids = set(existing.get("ids", []))
    except Exception:
        existing_ids = set()

    new_docs = [d for d in docs if d.metadata["doc_id"] not in existing_ids]
    if not new_docs:
        return 0

    texts = [d.page_content for d in new_docs]
    metadatas = [d.metadata for d in new_docs]
    ids = [d.metadata["doc_id"] for d in new_docs]

    vectors = embeddings.embed_documents(texts)
    col.add(ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas)
    return len(new_docs)


def index_top_universe_news(symbols: Optional[List[str]] = None, limit_per_sym: int = 30) -> Dict[str, int]:
    """Indexes news for the core universe into ChromaDB."""
    if not symbols:
        symbols = [
            "RELIANCE", "TCS", "INFY", "HDFCBANK", "KOTAKBANK",
            "ICICIBANK", "SBIN", "BHARTIARTL", "ITC", "LT",
            "TATAMOTORS", "TATASTEEL", "WIPRO", "MARUTI", "JIOFIN"
        ]
    results = {}
    for s in symbols:
        try:
            cnt = index_symbol_news(s, limit=limit_per_sym)
            results[s] = cnt
        except Exception:
            results[s] = -1
    return results


if __name__ == "__main__":
    print("[*] Testing News & Sentiment Chunker...")
    res = index_top_universe_news(["RELIANCE", "TCS", "INFY", "BHARTIARTL", "HDFCBANK"])
    print("News indexing results:", res)
    col = get_news_collection()
    print("Total news documents in collection:", col.count())
