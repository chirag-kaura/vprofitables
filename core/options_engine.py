"""
core/options_engine.py — Options Gamma Exposure (GEX) Calculations Engine (v4.3)
Calculates institutional hedging walls (Max Gamma Wall, Zero Gamma Level)
using 100% free options chain data from Yahoo Finance (yfinance).
"""

import math
import yfinance as yf
import pandas as pd

def calculate_black_scholes_gamma(S, K, T, sigma, r=0.07):
    """
    Calculate option Gamma using native math to avoid scipy dependency.
    S: Spot Price
    K: Strike Price
    T: Time to Expiration in years (days / 365.0)
    sigma: Implied Volatility
    r: Risk-free interest rate (default 7% for INR markets)
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    try:
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        n_prime = math.exp(-0.5 * d1 ** 2) / math.sqrt(2 * math.pi)
        gamma = n_prime / (S * sigma * math.sqrt(T))
        return gamma
    except Exception:
        return 0.0

def fetch_gex_profile(yf_symbol: str, spot_price: float) -> dict:
    """
    Fetch nearest options chain from yfinance and compute GEX walls.
    Returns:
        {
            "max_gamma_wall": float (strike with highest call GEX),
            "zero_gamma_level": float (strike where GEX crosses 0),
            "total_gex": float (aggregate net GEX),
            "skew_ratio": float (average Put IV / Call IV),
            "status": str ("OK" or error message)
        }
    """
    if not yf_symbol or spot_price <= 0:
        return {"max_gamma_wall": None, "zero_gamma_level": None, "total_gex": 0.0, "skew_ratio": 1.0, "status": "Invalid inputs"}

    try:
        ticker = yf.Ticker(yf_symbol)
        expirations = ticker.options
        if not expirations:
            return {"max_gamma_wall": None, "zero_gamma_level": None, "total_gex": 0.0, "skew_ratio": 1.0, "status": "No options chain found"}
        
        # Use the nearest monthly expiration (usually expirations[0] or [1])
        nearest_exp = expirations[0]
        opt_chain = ticker.option_chain(nearest_exp)
        
        calls = opt_chain.calls
        puts = opt_chain.puts
        
        if calls.empty and puts.empty:
            return {"max_gamma_wall": None, "zero_gamma_level": None, "total_gex": 0.0, "skew_ratio": 1.0, "status": "Empty option chain"}
            
        # Parse expiration date to get T (time to maturity)
        from datetime import datetime
        exp_date = datetime.strptime(nearest_exp, "%Y-%m-%d")
        days_to_expiry = max(1, (exp_date - datetime.today()).days)
        T = days_to_expiry / 365.0
        
        gex_list = []
        
        # 1. Process Calls
        for _, row in calls.iterrows():
            strike = float(row['strike'])
            oi = float(row.get('openInterest', 0) or 0)
            iv = float(row.get('impliedVolatility', 0) or 0.20)
            if oi <= 0 or iv <= 0:
                continue
            gamma = calculate_black_scholes_gamma(spot_price, strike, T, iv)
            # Call GEX is positive (dealer is long calls = buys lower, sells higher)
            call_gex = oi * (spot_price ** 2) * gamma * 0.15
            gex_list.append({"strike": strike, "type": "call", "gex": call_gex, "iv": iv})
            
        # 2. Process Puts
        for _, row in puts.iterrows():
            strike = float(row['strike'])
            oi = float(row.get('openInterest', 0) or 0)
            iv = float(row.get('impliedVolatility', 0) or 0.20)
            if oi <= 0 or iv <= 0:
                continue
            gamma = calculate_black_scholes_gamma(spot_price, strike, T, iv)
            # Put GEX is negative (dealer is short puts = buys higher, sells lower)
            put_gex = -oi * (spot_price ** 2) * gamma * 0.15
            gex_list.append({"strike": strike, "type": "put", "gex": put_gex, "iv": iv})
            
        if not gex_list:
            return {"max_gamma_wall": None, "zero_gamma_level": None, "total_gex": 0.0, "skew_ratio": 1.0, "status": "No open interest GEX"}
            
        df = pd.DataFrame(gex_list)
        
        # Compute Max Gamma Wall (strike price with the highest call GEX)
        call_df = df[df["type"] == "call"]
        max_gamma_wall = float(call_df.loc[call_df["gex"].idxmax()]["strike"]) if not call_df.empty else spot_price * 1.05
        
        # Compute Zero Gamma Level (strike where Net GEX crosses from negative to positive)
        # We group by strike and find the strike where net GEX goes from negative to positive
        strike_gex = df.groupby("strike")["gex"].sum().reset_index()
        strike_gex = strike_gex.sort_values("strike")
        
        # Locate the strike where sign flips
        zero_gamma_level = spot_price
        for i in range(len(strike_gex) - 1):
            g1 = strike_gex.iloc[i]["gex"]
            g2 = strike_gex.iloc[i+1]["gex"]
            if g1 < 0 and g2 >= 0:
                # Interpolate strike
                s1 = strike_gex.iloc[i]["strike"]
                s2 = strike_gex.iloc[i+1]["strike"]
                zero_gamma_level = s1 + (0.0 - g1) * (s2 - s1) / (g2 - g1)
                break
                
        # Compute Skew Ratio (average Put IV / average Call IV near spot)
        near_calls = call_df[abs(call_df["strike"] - spot_price)/spot_price <= 0.10]
        near_puts = df[(df["type"] == "put") & (abs(df["strike"] - spot_price)/spot_price <= 0.10)]
        avg_call_iv = near_calls["iv"].mean() if not near_calls.empty else 0.20
        avg_put_iv = near_puts["iv"].mean() if not near_puts.empty else 0.20
        skew_ratio = avg_put_iv / avg_call_iv if avg_call_iv > 0 else 1.0
        
        return {
            "max_gamma_wall": round(max_gamma_wall, 2),
            "zero_gamma_level": round(zero_gamma_level, 2),
            "total_gex": round(df["gex"].sum(), 2),
            "skew_ratio": round(skew_ratio, 2),
            "status": "OK"
        }
        
    except Exception as e:
        return {"max_gamma_wall": None, "zero_gamma_level": None, "total_gex": 0.0, "skew_ratio": 1.0, "status": f"Error: {e}"}
