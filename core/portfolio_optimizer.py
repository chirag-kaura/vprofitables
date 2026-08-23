"""
core/portfolio_optimizer.py

Institutional-grade portfolio risk management for Vprofitables.
Calculates mathematically optimal bet sizing (Kelly Criterion) and 
mitigates correlation risk via Covariance matrices.
"""
import numpy as np
import pandas as pd
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)

def calculate_kelly_fraction(win_rate: float, avg_win: float, avg_loss: float, fraction_multiplier: float = 0.5) -> float:
    """
    Calculates the Kelly Criterion percentage for position sizing.
    Uses 'Half-Kelly' by default to mitigate volatility drag.
    
    win_rate: 0.0 to 1.0 (e.g., 0.55 for 55%)
    avg_win: average profit percentage (e.g., 0.10 for 10%)
    avg_loss: average loss percentage (positive float, e.g., 0.05 for 5%)
    """
    if avg_loss <= 0 or win_rate <= 0:
        return 0.0
        
    win_loss_ratio = avg_win / avg_loss
    kelly_pct = win_rate - ((1 - win_rate) / win_loss_ratio)
    
    # Cap maximum risk per trade at 20% even if Kelly suggests higher, apply Half-Kelly
    safe_kelly = min(kelly_pct * fraction_multiplier, 0.20)
    
    return max(0.0, safe_kelly) # Never return negative size

def calculate_covariance_matrix(returns_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the covariance matrix of daily returns for a basket of symbols.
    Used to ensure the portfolio isn't overly correlated.
    """
    return returns_df.cov()

def optimize_portfolio(signals: List[Dict], historical_returns: pd.DataFrame, max_capital: float) -> List[Dict]:
    """
    Takes raw signals and outputs sized orders adjusting for correlation and Kelly risk.
    """
    if historical_returns.empty or not signals:
        return signals
        
    cov_matrix = calculate_covariance_matrix(historical_returns)
    optimized_orders = []
    
    # Simplified Risk Parity: 
    # Reduce size if the symbol is highly correlated with already-sized symbols.
    allocated_symbols = []
    
    for sig in sorted(signals, key=lambda x: x.get('score', 0), reverse=True):
        symbol = sig['symbol']
        
        # Calculate Kelly based on historical backtest stats for this specific strategy/symbol
        win_rate = sig.get('hist_win_rate', 0.50)
        avg_win = sig.get('hist_avg_win', 0.05)
        avg_loss = sig.get('hist_avg_loss', 0.02)
        
        base_weight = calculate_kelly_fraction(win_rate, avg_win, avg_loss)
        
        # Correlation penalty
        penalty = 1.0
        if symbol in cov_matrix.columns:
            for alloc_sym in allocated_symbols:
                if alloc_sym in cov_matrix.columns:
                    correlation = historical_returns[symbol].corr(historical_returns[alloc_sym])
                    if correlation > 0.6: # Highly correlated
                        penalty *= 0.5 # Reduce size by half for each highly correlated existing position
                        
        final_weight = base_weight * penalty
        alloc_amount = max_capital * final_weight
        
        if final_weight > 0.01: # Minimum 1% allocation
            sig['recommended_size_pct'] = round(final_weight * 100, 2)
            sig['recommended_capital'] = round(alloc_amount, 2)
            optimized_orders.append(sig)
            allocated_symbols.append(symbol)
            
    return optimized_orders
