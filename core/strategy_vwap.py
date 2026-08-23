import numpy as np
import pandas as pd
from core.timeseries_db import get_1m_data

def get_intraday_vwap_and_profile(symbol: str, target_date: str = None) -> dict:
    \"\"\"
    Calculates Intraday VWAP, Market Profile (Point of Control), and 
    Cumulative Volume Delta (CVD) using the 1-minute DuckDB data.
    \"\"\"
    try:
        # Get latest 375 minutes (1 trading day in India roughly)
        df = get_1m_data(symbol, limit=375)
        if df.empty:
            return {"status": "error", "message": "No 1m data available"}
            
        if not target_date:
            target_date = df['datetime'].iloc[-1].strftime('%Y-%m-%d')
            
        df['date_str'] = df['datetime'].dt.strftime('%Y-%m-%d')
        day_df = df[df['date_str'] == target_date].copy()
        
        if day_df.empty:
            return {"status": "error", "message": f"No 1m data for {target_date}"}
            
        # VWAP Calculation
        day_df['cum_vol'] = day_df['volume'].cumsum()
        day_df['cum_vol_price'] = (day_df['close'] * day_df['volume']).cumsum()
        day_df['vwap'] = day_df['cum_vol_price'] / day_df['cum_vol']
        
        # Cumulative Volume Delta (CVD) Proxy (Phase 3 Upgrade)
        # Without level 2, we proxy order flow: 
        # Up candle = buyer initiated (+vol), Down candle = seller initiated (-vol)
        conditions = [
            day_df['close'] > day_df['open'],
            day_df['close'] < day_df['open']
        ]
        choices = [day_df['volume'], -day_df['volume']]
        day_df['vol_delta'] = np.select(conditions, choices, default=0)
        day_df['cvd'] = day_df['vol_delta'].cumsum()
        
        # Point of Control (POC) Calculation
        bins = np.linspace(day_df['low'].min(), day_df['high'].max(), 50)
        day_df['price_bin'] = pd.cut(day_df['close'], bins)
        volume_by_price = day_df.groupby('price_bin', observed=False)['volume'].sum()
        
        poc_idx = volume_by_price.argmax()
        poc_price = volume_by_price.index[poc_idx].mid
        
        current_vwap = float(day_df['vwap'].iloc[-1])
        current_cvd = float(day_df['cvd'].iloc[-1])
        
        return {
            "vwap": round(current_vwap, 2),
            "poc": round(poc_price, 2),
            "cvd": current_cvd,
            "target_date": target_date
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
