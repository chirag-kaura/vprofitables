"""
tests/test_ohlc_rag_pipeline.py
================================
Unit and regression test suite for the LangChain + LangGraph OHLC RAG Pipeline.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ohlc_rag.chunker import load_candles_from_db, chunk_candles_into_documents
from core.ohlc_rag.retriever import extract_symbol_and_intent, OHLCHybridRetriever
from core.ohlc_rag.tools import (
    ohlc_quote_lookup,
    ohlc_history_range,
    ohlc_technical_stats,
    ohlc_relative_performance
)
from core.ohlc_rag.graph import ohlc_graph, run_ohlc_graph
from core.ohlc_rag.engine import run_ohlc_agent


def test_chunker_data_loading():
    """Verify that candles are loaded and converted into semantic documents."""
    df = load_candles_from_db("RELIANCE", limit_days=30)
    assert not df.empty, "RELIANCE daily candles should not be empty"
    assert "close" in df.columns
    assert "trade_date" in df.columns

    docs = chunk_candles_into_documents(df, window_sizes=[5, 20])
    assert len(docs) > 0, "Should generate multi-scale documents"
    assert "Stock: RELIANCE" in docs[0].page_content
    assert "return_pct" in docs[0].metadata
    assert docs[0].metadata["timeframe"] in ["5D", "20D"]


def test_retriever_query_extraction():
    """Verify symbol and timeframe extraction."""
    sym, tf = extract_symbol_and_intent("How has TCS traded over the last 20 days?")
    assert sym == "TCS"
    assert tf == "20D"

    sym2, tf2 = extract_symbol_and_intent("What is the recent quote for INFY?")
    assert sym2 == "INFY"
    assert tf2 == "5D"


def test_ohlc_tools():
    """Verify deterministic LangChain tools."""
    # 1. Quote
    quote = ohlc_quote_lookup.invoke({"symbol": "RELIANCE"})
    assert "Quote for RELIANCE" in quote
    assert "Close: Rs." in quote

    # 2. History Range
    history = ohlc_history_range.invoke({"symbol": "TCS", "num_days": 5})
    assert "OHLC History for TCS" in history
    assert "| Date | Open |" in history

    # 3. Technical Stats
    stats = ohlc_technical_stats.invoke({"symbol": "HDFCBANK", "lookback_days": 60})
    assert "Technical Quantitative Stats for HDFCBANK" in stats
    assert "SMA 20:" in stats
    assert "52-Week High:" in stats

    # 4. Relative Performance
    comp = ohlc_relative_performance.invoke({"symbol_a": "RELIANCE", "symbol_b": "TCS", "days": 20})
    assert "Relative Performance" in comp
    assert "RELIANCE:" in comp
    assert "TCS:" in comp


def test_langgraph_pipeline_execution():
    """Verify full LangGraph state machine run."""
    state = run_ohlc_graph("Show me the latest technical stats for INFY")
    assert state.get("symbol") == "INFY"
    assert state.get("intent") in ["stats", "trend_rag"]
    assert state.get("final_response") != ""


def test_engine_public_endpoint():
    """Verify engine output structure for UI integration."""
    res = run_ohlc_agent("What is the current quote and trend for RELIANCE?")
    assert "reply" in res
    assert res["symbol"] == "RELIANCE"
    assert "sources" in res
    assert len(res["sources"]) >= 3
    assert "latency_ms" in res


if __name__ == "__main__":
    print("[*] Running all OHLC RAG Pipeline tests...")
    test_chunker_data_loading()
    print("PASS: test_chunker_data_loading")
    test_retriever_query_extraction()
    print("PASS: test_retriever_query_extraction")
    test_ohlc_tools()
    print("PASS: test_ohlc_tools")
    test_langgraph_pipeline_execution()
    print("PASS: test_langgraph_pipeline_execution")
    test_engine_public_endpoint()
    print("PASS: test_engine_public_endpoint")
    print("\nALL 5 PIPELINE TESTS PASSED!")
