"""
core/feed_1m_poller.py

Fetches 1-minute candle data from Yahoo Finance and stores it in DuckDB.
Acts as a pseudo-real-time feed for intraday strategies.
"""
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
from core.timeseries_db import insert_1m_data
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_and_store_1m_data(symbols: list[str]):
    """
    Fetches the latest 1-minute data for a list of symbols and stores it in DuckDB.
    """
    for symbol in symbols:
        try:
            # yfinance requires .NS for NSE stocks
            yf_symbol = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
            
            # Fetch 1m data (yfinance max period for 1m is 7 days)
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period="1d", interval="1m")
            
            if df.empty:
                logging.warning(f"No 1m data found for {symbol}")
                continue
                
            # Prepare dataframe for DuckDB
            df = df.reset_index()
            df = df.rename(columns={
                "Datetime": "datetime",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume"
            })
            
            # Standardize symbol name back to internal representation (without .NS)
            clean_symbol = symbol.replace(".NS", "")
            df['symbol'] = clean_symbol
            
            # Keep only necessary columns
            df = df[['symbol', 'datetime', 'open', 'high', 'low', 'close', 'volume']]
            
            # Insert into DuckDB
            insert_1m_data(df)
            logging.info(f"Updated 1m data for {clean_symbol} ({len(df)} rows)")
            
            # Sleep slightly to avoid hitting yfinance rate limits
            time.sleep(0.5)
            
        except Exception as e:
            logging.error(f"Error fetching 1m data for {symbol}: {str(e)}")

def start_polling(symbols: list[str], interval_seconds: int = 60):
    """
    Continuously polls for new 1-minute data. 
    Intended to be run in a background thread.
    """
    logging.info(f"Starting 1m data poller for {len(symbols)} symbols...")
    while True:
        try:
            fetch_and_store_1m_data(symbols)
        except Exception as e:
            logging.error(f"Poller loop error: {str(e)}")
            
        # Wait for next minute boundary
        current_time = time.time()
        sleep_time = interval_seconds - (current_time % interval_seconds)
        time.sleep(sleep_time)

if __name__ == "__main__":
    # Test execution
    test_symbols = ["RELIANCE", "TCS", "HDFCBANK"]
    fetch_and_store_1m_data(test_symbols)
