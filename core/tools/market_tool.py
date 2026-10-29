"""
core/tools/market_tool.py
=========================
Atomic Market Momentum & Multi-Day Return Screener Tool.
Scans 500+ NSE equities over 1, 5, 10, or 20 trading sessions.
Calculates exact return percentages, flags splits/bonuses, and identifies organic movers.
"""

from typing import Dict, Any, List, Optional
try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func):
        return func

from core.market_screener import screen_price_performance, format_screener_markdown

@tool
def scan_market_momentum_tool(
    direction: str = "LOSERS",
    sessions: int = 5,
    limit: int = 5
) -> Dict[str, Any]:
    """
    Scans the entire NSE market (500+ equities) for top gainers or losers over N trading sessions.
    
    Args:
        direction: 'LOSERS' (or 'FALLEN', 'DOWN') to find biggest decliners, 
                   or 'GAINERS' (or 'GAINED', 'UP') to find top performers.
        sessions: Number of historical trading days (default: 5, supports 1, 5, 10, 20).
        limit: Number of stocks to return (default: 5).
        
    Returns:
        Dict containing top screened stocks, verified % change, baseline and latest dates,
        and corporate action split/bonus warnings.
    """
    is_gainers = direction.upper() in ("GAINED", "GAINERS", "UP", "RISING", "MAX_GAIN")
    dir_str = "GAINERS" if is_gainers else "LOSERS"
    
    result = screen_price_performance(days=sessions, direction=dir_str, limit=limit)
    return result
