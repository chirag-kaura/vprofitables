"""
core/tools/concall_tool.py
==========================
Atomic Earnings Concall & Management Guidance Tool.
Retrieves semantic excerpts from earnings call transcripts.
Enforces strict PDF binary stream filters, SEBI boilerplate rejection,
and executive attribution.
"""

from typing import Dict, Any, List, Optional
try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func):
        return func

from core.financial_query import get_transcript_guidance, is_clean_transcript_chunk

@tool
def search_clean_concalls_tool(
    symbol: str,
    query: str = "guidance growth capex margins demand outlook",
    k: int = 4
) -> Dict[str, Any]:
    """
    Retrieves verified management commentary from quarterly earnings conference calls.
    Filters out raw PDF streams, legal disclaimers, and boilerplate.
    
    Args:
        symbol: NSE ticker symbol (e.g., 'RELIANCE', 'TCS').
        query: Semantic topic query (e.g., 'capex and margin guidance').
        k: Maximum number of clean excerpts to return (default: 4).
        
    Returns:
        Dict containing filtered excerpts, speaker attribution (EXECUTIVE / ANALYST),
        and fiscal quarter period.
    """
    clean_sym = symbol.strip().upper()
    excerpts = get_transcript_guidance(clean_sym, query=query, k=k)
    return {
        "symbol": clean_sym,
        "count": len(excerpts),
        "query": query,
        "excerpts": excerpts
    }
