"""
core/macro_engine.py

Fetches and normalizes macroeconomic indicators using yfinance.
Incorporates:
- USD/INR Currency Strength
- India 10Y Yields (^IN10YT) vs US 10Y Yields (^TNX)
- Crude Oil (CL=F)
"""
import yfinance as yf
import pandas as pd
import logging
from typing import Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Tickers mapped for Yahoo Finance
MACRO_TICKERS = {
    "USDINR": "INR=X",
    "US10Y": "^TNX",
    "CRUDE": "CL=F"
}

def fetch_macro_data(lookback_days: int = 252) -> pd.DataFrame:
    """
    Fetches the last year of daily data for macro indicators.
    Returns a unified dataframe.
    """
    dfs = []
    for name, ticker in MACRO_TICKERS.items():
        try:
            t = yf.Ticker(ticker)
            df = t.history(period=f"{lookback_days}d")
            if not df.empty:
                df = df[['Close']].rename(columns={'Close': name})
                dfs.append(df)
        except Exception as e:
            logging.error(f"Failed to fetch {name}: {e}")
            
    if not dfs:
        return pd.DataFrame()
        
    macro_df = pd.concat(dfs, axis=1).ffill().dropna()
    return macro_df

def get_macro_regime() -> Dict[str, str]:
    """
    Evaluates the current macro regime based on short-term vs long-term moving averages
    of the macroeconomic indicators.
    """
    df = fetch_macro_data(lookback_days=100)
    if df.empty:
        return {"status": "error"}
        
    # Calculate simple trends (current vs 50-day average)
    regime_scores = {}
    
    if "USDINR" in df.columns:
        current = df["USDINR"].iloc[-1]
        ma50 = df["USDINR"].tail(50).mean()
        regime_scores["USDINR_TREND"] = "BEARISH_FOR_EQUITIES" if current > ma50 else "BULLISH_FOR_EQUITIES"
        
    if "US10Y" in df.columns:
        current = df["US10Y"].iloc[-1]
        ma50 = df["US10Y"].tail(50).mean()
        regime_scores["YIELD_TREND"] = "BEARISH_FOR_EQUITIES" if current > ma50 else "BULLISH_FOR_EQUITIES"
        
    if "CRUDE" in df.columns:
        current = df["CRUDE"].iloc[-1]
        ma50 = df["CRUDE"].tail(50).mean()
        regime_scores["CRUDE_TREND"] = "BEARISH_FOR_EQUITIES" if current > ma50 else "BULLISH_FOR_EQUITIES"
        
    # Overall Macro Bias
    bear_count = list(regime_scores.values()).count("BEARISH_FOR_EQUITIES")
    bull_count = list(regime_scores.values()).count("BULLISH_FOR_EQUITIES")
    
    if bear_count >= 2:
        regime_scores["OVERALL_MACRO"] = "RISK_OFF"
    elif bull_count >= 2:
        regime_scores["OVERALL_MACRO"] = "RISK_ON"
    else:
        regime_scores["OVERALL_MACRO"] = "NEUTRAL"
        
    return regime_scores

if __name__ == "__main__":
    print(get_macro_regime())
