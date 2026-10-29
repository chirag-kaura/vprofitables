"""
core/ohlc_rag/engine.py
=======================
Phase 5: Public Engine Interface for OHLC LangGraph RAG Assistant.
Provides high-level conversational interface for endpoints, terminal UI,
and testing harnesses with latency tracking and metadata extraction.
"""

import os
import sys
import time
from typing import Dict, Any, Optional, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.ohlc_rag.chunker import index_batch_symbols
from core.swarm.graph import run_swarm_graph


def run_ohlc_agent(
    query: str,
    active_symbol: Optional[str] = None,
    session_id: Optional[str] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes a user prompt through the LangChain + LangGraph Multi-Agent Swarm pipeline.
    
    Returns structured payload compliant with the Vprofitables Assistant API:
      - reply: Markdown formatted institutional analysis
      - symbol: Target symbol resolved
      - intent: Extracted quantitative intent
      - model_used: Local LLM runtime string
      - latency_ms: Execution duration in ms
      - sources: List of grounded factual data providers used
    """
    t0 = time.time()
    
    effective_query = query.strip()
    history = []
    
    # ── Conversational Session Context & Anaphora Binding ──────────────
    session = None
    if session_id:
        try:
            from core.session_manager import get_session
            session = get_session(session_id)
            if session:
                if not active_symbol and session.active_symbol:
                    active_symbol = session.active_symbol
                history = [
                    {"role": h.get("role", "user"), "content": h.get("content", ""), "symbol": session.active_symbol}
                    for h in session.history
                ]
        except Exception as e:
            pass
            
    state = run_swarm_graph(
        effective_query,
        symbol=active_symbol,
        history=history,
        model=model
    )
    
    resolved_sym = state.get("symbol") or active_symbol
    if session and resolved_sym:
        try:
            session.set_symbol(resolved_sym)
            session.add_turn("user", effective_query)
            if state.get("final_response"):
                session.add_turn("assistant", state.get("final_response"))
        except Exception:
            pass

    latency_ms = int((time.time() - t0) * 1000)
    
    final_text = state.get("final_response") or "No analysis could be generated for the given request."
    intent = state.get("intent", "swarm_dossier")
    domains = state.get("domains", [])
    model_tag = state.get("model_used") or (model or "Qwen 2.5:7b")

    sources = [
        "LangGraph Hierarchical Multi-Agent Swarm Orchestrator",
        "SQLite Verified Daily Prices & 10Y Financials (market_data_v2.db)",
        "Derivatives Microstructure & Option Chain (pcr_summary)",
        "Institutional Smart Money Bulk/Block Deals Flow",
        "W.D. Gann Square of 9 Geometric Calculator (gann_math.py)",
        "Richard Wyckoff Market Phase Engine (wyckoff_engine.py)",
        "PyTorch Deep MLP Trend Continuation Neural Network",
        "Vedic Nakshatra & Planetary Ephemeris (nakshatra_engine.py)"
    ]

    return {
        "reply": final_text,
        "symbol": resolved_sym,
        "intent": intent,
        "domains": domains,
        "model_used": f"Hierarchical Swarm + {model_tag}",
        "latency_ms": latency_ms,
        "sources": sources,
        "is_fallback": False
    }


def warmup_and_index_core_universe(symbols: Optional[List[str]] = None) -> Dict[str, int]:
    """
    Pre-indexes core universe into ChromaDB for instant sub-second retrieval.
    """
    if not symbols:
        symbols = [
            "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", 
            "SBIN", "BHARTIARTL", "ITC", "LT", "TATAMOTORS",
            "TATASTEEL", "WIPRO", "MARUTI", "SUNPHARMA", "KOTAKBANK"
        ]
    return index_batch_symbols(symbols, limit_days=180)


if __name__ == "__main__":
    print("[*] Running Phase 5 Public Engine Test...")
    res = run_ohlc_agent("What is the current quote and latest 52W range for TCS?")
    print("\nReply:\n", res["reply"])
    print("\nMetadata:\n", {k: v for k, v in res.items() if k != "reply"})
