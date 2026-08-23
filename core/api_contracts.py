# core/api_contracts.py

"""
API response contract specifications.
Defines required keys for endpoints to prevent frontend-backend drift.
"""

CONTRACTS = {
    "all_symbols": ["indices", "equities", "commodities"],
    "ticker": ["prices", "date"],
    "overview_data": ["indices", "most_bought", "gainers", "losers", "sectors", "performers", "screeners", "signals", "research", "pocket"],
    "portfolio_get": ["positions", "total_invested", "total_exposure", "realized_pnl", "unrealized_pnl", "trades"],
    "risk_dashboard": ["ok", "open_positions", "total_invested", "total_exposure", "unrealized_pnl", "realized_pnl", "max_drawdown_pct", "var_95", "var_95_pct", "win_pct", "health_score", "positions", "sector_exposure", "total_trades"],
    "risk_settings_get": ["ok", "settings"],
    "watchlist_get": ["symbols", "items"],
    "market_depth": ["ok", "symbol", "ltp", "bid", "ask", "total_bid", "total_ask", "imbalance"],
    "alert_get": ["ok", "alerts"],
    "correlation_matrix": ["ok", "matrix", "symbols"],
    "advisor_plan": ["ok", "plan"],
}

ANALYTICS_CONTRACTS = {
    "calendar": ["ok", "type", "daily_pnl", "total_pnl", "best_day", "worst_day", "profitable_days", "total_days"],
    "equity_curve": ["ok", "type", "curve", "start_capital", "end_capital", "total_return", "nifty_return", "sharpe", "max_drawdown"],
    "statistics": ["ok", "type", "total_trades", "win_pct", "loss_pct", "avg_win", "avg_loss", "profit_factor", "expectancy", "avg_rr", "best_rr", "worst_rr", "avg_hold_days", "max_consec_wins", "max_consec_losses", "recent_streak", "monthly_pnl", "weekday"],
    "best_worst": ["ok", "type", "trades"],
    "sector_pnl": ["ok", "type", "sectors"]
}

def validate_response(endpoint: str, result: dict):
    """
    Validates that a response dictionary contains all the expected keys defined in the contract.
    Raises AssertionError if keys are missing in dev mode.
    """
    if not isinstance(result, dict):
        return

    # Skip if result indicates failure (has error) unless we want to validate error keys
    if "error" in result and not result.get("ok", True):
        return

    # Check main contracts
    if endpoint in CONTRACTS:
        expected = CONTRACTS[endpoint]
        missing = [key for key in expected if key not in result]
        if missing:
            raise AssertionError(f"Endpoint '{endpoint}' response is missing keys: {missing}. Keys returned: {list(result.keys())}")

    # Check analytics endpoint sub-types
    elif endpoint == "analytics_data":
        dtype = result.get("type")
        if dtype in ANALYTICS_CONTRACTS:
            expected = ANALYTICS_CONTRACTS[dtype]
            missing = [key for key in expected if key not in result]
            if missing:
                raise AssertionError(f"Analytics type '{dtype}' response is missing keys: {missing}. Keys returned: {list(result.keys())}")
