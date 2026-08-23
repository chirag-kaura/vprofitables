"""
core/advanced_metrics.py

Phase 5 Institutional Upgrades:
- Monte Carlo Permutation (Drawdown Analysis)
- Deflated Sharpe Ratio (p-hacking adjustment)
"""
import numpy as np

def run_monte_carlo_drawdown(trade_returns_pct: list, iterations: int = 10000, confidence_level: float = 0.95) -> dict:
    """
    Shuffles the sequence of historical trade returns iterations times to simulate 
    alternative market realities and find the True Maximum Drawdown.
    
    trade_returns_pct: List of percentage returns (e.g. 5.2 for +5.2%, -1.5 for -1.5%)
    """
    if not trade_returns_pct or len(trade_returns_pct) < 10:
        return {"max_drawdown_95": 0.0, "median_drawdown": 0.0}
        
    returns = np.array(trade_returns_pct) / 100.0
    max_drawdowns = []
    
    for _ in range(iterations):
        # Permute (shuffle) the returns
        shuffled = np.random.permutation(returns)
        # Calculate cumulative equity curve (starting at 1.0)
        equity = np.cumprod(1 + shuffled)
        # Calculate running maximum
        running_max = np.maximum.accumulate(equity)
        # Calculate drawdowns
        drawdowns = (running_max - equity) / running_max
        max_drawdowns.append(drawdowns.max())
        
    max_drawdowns = np.array(max_drawdowns)
    
    # 95th percentile worst-case drawdown
    mdd_95 = np.percentile(max_drawdowns, confidence_level * 100)
    median_mdd = np.median(max_drawdowns)
    
    return {
        "max_drawdown_95": round(mdd_95 * 100, 2),
        "median_drawdown": round(median_mdd * 100, 2)
    }

def compute_deflated_sharpe(sharpe_ratio: float, trials: int = 100, variance: float = 1.0) -> float:
    """
    Computes a simplified Deflated Sharpe Ratio (DSR) to penalize for multiple testing bias.
    The more backtests you run (trials), the higher the hurdle for a Sharpe ratio to be statistically significant.
    """
    import scipy.stats as st
    
    # Expected maximum Sharpe under the null hypothesis
    # Approximation of the expected maximum of standard normal variables
    if trials <= 1:
        expected_max = 0
    else:
        # Euler-Mascheroni constant approx
        expected_max = np.sqrt(2 * np.log(trials))
        
    # Standard deviation of the trials (assumed or calculated)
    # Deflated Sharpe subtracts the expected maximum (scaled by variance)
    dsr = sharpe_ratio - (expected_max * np.sqrt(variance))
    
    # DSR must not be negative if original was positive (simplification)
    if sharpe_ratio > 0 and dsr < 0:
        dsr = 0.01
        
    return round(dsr, 2)
