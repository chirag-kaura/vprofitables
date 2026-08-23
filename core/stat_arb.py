"""
core/stat_arb.py

Statistical Arbitrage (Pairs Trading) Engine
Designed to find highly cointegrated pairs (e.g., HDFCBANK / ICICIBANK) and 
trade the spread mean-reversion, capturing alpha completely market-neutral.
"""

import numpy as np

def calculate_spread_zscore(price_a: list, price_b: list, window: int = 20) -> float:
    """
    Calculates the current Z-Score of the spread between two assets.
    Spread = log(Price_A) - log(Price_B)
    """
    if len(price_a) < window or len(price_b) < window:
        return 0.0
        
    # Use the most recent 'window' days
    p_a = np.array(price_a[-window:])
    p_b = np.array(price_b[-window:])
    
    # Calculate log spread
    spread = np.log(p_a) - np.log(p_b)
    
    mean_spread = np.mean(spread)
    std_spread = np.std(spread)
    
    if std_spread == 0:
        return 0.0
        
    current_spread = spread[-1]
    z_score = (current_spread - mean_spread) / std_spread
    
    return float(z_score)

def stat_arb_signal(z_score: float, entry_threshold: float = 2.0, exit_threshold: float = 0.0) -> dict:
    """
    Generates trading signals based on the spread Z-Score.
    """
    signal = {"action": "HOLD", "confidence": 0.0, "direction": "NEUTRAL"}
    
    # If Z-score is heavily positive, Asset A is overvalued relative to B
    if z_score > entry_threshold:
        signal["action"] = "ENTER"
        signal["direction"] = "SHORT_A_LONG_B"
        signal["confidence"] = min(100.0, (z_score - entry_threshold) * 20 + 60)
        
    # If Z-score is heavily negative, Asset A is undervalued relative to B
    elif z_score < -entry_threshold:
        signal["action"] = "ENTER"
        signal["direction"] = "LONG_A_SHORT_B"
        signal["confidence"] = min(100.0, (abs(z_score) - entry_threshold) * 20 + 60)
        
    # Exit when mean reverts
    elif abs(z_score) <= exit_threshold:
        signal["action"] = "EXIT"
        
    return signal
