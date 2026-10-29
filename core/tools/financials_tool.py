"""
core/tools/financials_tool.py
=============================
Atomic Audited Financial Intelligence Tool.
Retrieves 10-year audited annual financial statements and recent quarterly filings
strictly denominated in INR Crores (₹ Cr). Zero hallucination contract.
"""

from typing import Dict, Any, List, Optional
try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func):
        return func

from core.financial_query import get_company_financials, format_crores, format_pct

@tool
def get_verified_financials_tool(symbol: str) -> Dict[str, Any]:
    """
    Retrieves verified audited balance sheet and income statement metrics for an NSE equity.
    
    Args:
        symbol: NSE ticker symbol (e.g., 'RELIANCE', 'TCS', 'INFY').
        
    Returns:
        Dict containing annual audited metrics (Sales, Operating Profit, PAT, OCF, Debt, YoY Growth)
        and recent quarterly results, strictly in INR Crores (₹ Cr).
    """
    clean_sym = symbol.strip().upper()
    annual_list = get_company_financials(clean_sym, period_type="ANNUAL", limit=5)
    quarterly_list = get_company_financials(clean_sym, period_type="QUARTERLY", limit=4)
    
    latest_ann = annual_list[0] if annual_list else None
    latest_qtr = quarterly_list[0] if quarterly_list else None
    
    return {
        "symbol": clean_sym,
        "unit": "INR Crores (₹ Cr)",
        "annual_data": annual_list,
        "quarterly_data": quarterly_list,
        "latest_annual": latest_ann,
        "latest_quarterly": latest_qtr,
    }
