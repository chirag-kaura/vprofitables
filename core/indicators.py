# core/indicators.py
"""
Centralized indicators and calculators module for GANN-ASTRO.
PHASE 4 FIX (Fix 15, Fix 17): Unifies RSI, EMA, and Transaction cost calculations.
"""
import math

def calculate_rsi(closes: list, period: int = 14) -> float:
    """
    Standard Wilder's smoothed RSI (used consistently across app.py, scanners, quant engines).
    """
    if len(closes) < period + 1:
        return 50.0
    
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        if diff > 0:
            gains.append(diff)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(diff))
            
    # Wilder's smoothing
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
    if avg_loss == 0:
        return 100.0
        
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)

def calculate_ema(closes: list, period: int) -> float:
    """
    Exponential Moving Average.
    """
    if not closes:
        return 0.0
    if len(closes) < period:
        return sum(closes) / len(closes)
        
    k = 2.0 / (period + 1.0)
    ema_val = closes[0]
    for val in closes[1:]:
        ema_val = val * k + ema_val * (1.0 - k)
    return round(ema_val, 2)

def calculate_transaction_costs(entry_price: float, exit_price: float, shares: int) -> float:
    """
    PHASE 4 FIX (Fix 15):
    Calculates realistic round-trip transaction costs for Indian equities on NSE.
    Includes STT, Brokerage (flat rate), Stamp Duty, SEBI & exchange charges, and GST.
    """
    shares = int(shares)
    if shares <= 0 or entry_price <= 0 or exit_price <= 0:
        return 0.0

    # 1. Buy costs
    buy_val = entry_price * shares
    brokerage_buy = 20.0
    gst_buy = brokerage_buy * 0.18  # 18% GST on brokerage
    stamp_duty = buy_val * 0.00015  # 0.015%
    exchange_charge_buy = buy_val * 0.0000325  # 0.00325%
    sebi_charge_buy = buy_val * 0.000001  # 0.0001%
    total_buy_costs = brokerage_buy + gst_buy + stamp_duty + exchange_charge_buy + sebi_charge_buy

    # 2. Sell costs
    sell_val = exit_price * shares
    brokerage_sell = 20.0
    gst_sell = brokerage_sell * 0.18
    stt_sell = sell_val * 0.001  # 0.1% STT on sell side
    exchange_charge_sell = sell_val * 0.0000325
    sebi_charge_sell = sell_val * 0.000001
    total_sell_costs = brokerage_sell + gst_sell + stt_sell + exchange_charge_sell + sebi_charge_sell

    return round(total_buy_costs + total_sell_costs, 2)
