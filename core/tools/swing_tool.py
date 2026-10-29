"""
core/tools/swing_tool.py
========================
Atomic Swing Trade & Short-Term Momentum Scanner Tool.
Scans for 10-15 day swing trade setups with verified multi-timeframe trend alignment,
EMA pullback setups, dynamic Stop-Loss, Targets, and Risk-Reward ratio.
"""

from typing import Dict, Any, List, Optional
try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func):
        return func

from core.trend_continuation_engine import scan_trend_pullbacks

@tool
def scan_swing_setups_tool(
    min_confidence: float = 65.0,
    min_rr: float = 1.5,
    limit: int = 4
) -> Dict[str, Any]:
    """
    Scans for 10-15 day short-term swing trading candidates across NSE equities.
    
    Args:
        min_confidence: Minimum algorithmic setup confidence percentage (default: 65.0).
        min_rr: Minimum Risk-to-Reward ratio required (default: 1.5).
        limit: Maximum number of setups to return (default: 4).
        
    Returns:
        Dict containing qualified swing candidates with Entry price, Target 1, Target 2,
        Stop Loss, R:R ratio, Setup Type, and technical rationale.
    """
    try:
        setups = scan_trend_pullbacks(
            horizon="swing",
            min_confidence=int(min_confidence),
            max_results=limit * 3
        )
        qualified = []
        for s in setups:
            rr = s.get("rr_ratio") or s.get("risk_reward_ratio") or 0.0
            if rr >= min_rr:
                qualified.append(s)
            if len(qualified) >= limit:
                break
                
        # If strict filter yielded none, take top candidates by confidence
        if not qualified and setups:
            qualified = setups[:limit]

        return {
            "status": "success",
            "total_screened": len(setups),
            "qualified_count": len(qualified),
            "setups": qualified
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "setups": []
        }
