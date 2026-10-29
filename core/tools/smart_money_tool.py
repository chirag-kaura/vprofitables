"""
core/tools/smart_money_tool.py
==============================
Atomic Institutional Shareholding & Smart Money Flow Tool.
Retrieves quarterly Promoter, FII, and DII ownership percentages, QoQ accumulation/distribution,
and institutional positioning.
"""

from typing import Dict, Any, Optional
try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func):
        return func

from core.shareholding_engine import get_shareholding_trend

@tool
def get_institutional_holdings_tool(symbol: str) -> Dict[str, Any]:
    """
    Retrieves institutional shareholding data (Promoter, FII, DII) and QoQ changes for an NSE equity.
    
    Args:
        symbol: NSE ticker symbol (e.g., 'RELIANCE', 'TCS').
        
    Returns:
        Dict containing latest quarter holdings (Promoter %, FII %, DII %), QoQ delta,
        pledge percentage, and flow signal (ACCUMULATION / DISTRIBUTION / STABLE).
    """
    clean_sym = symbol.strip().upper()
    sh = get_shareholding_trend(clean_sym)
    if not sh or sh.get("status") == "NO_SHAREHOLDING_DATA":
        return {
            "symbol": clean_sym,
            "has_data": False,
            "signal": "UNKNOWN"
        }
    return {
        "symbol": clean_sym,
        "has_data": True,
        "period": sh.get("latest_period"),
        "promoter_pct": sh.get("promoter_pct"),
        "promoter_pledged": sh.get("pledged_pct", 0.0),
        "fii_pct": sh.get("fii_pct"),
        "fii_change": sh.get("fii_qoq_delta"),
        "dii_pct": sh.get("dii_pct"),
        "dii_change": sh.get("dii_qoq_delta"),
        "signal": sh.get("institutional_signal", "STABLE")
    }
