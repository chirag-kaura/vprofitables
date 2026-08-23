"""
core/timeseries_db.py

DuckDB-based time-series database interface for storing 1-minute candle data.
Provides ultra-fast analytical queries required for VWAP, Volume Profile, and intraday CWT.
"""
import duckdb
import pandas as pd
from pathlib import Path
import os
import threading

# Use project data directory
DATA_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(DATA_DIR / "market_data_1m.duckdb")

_thread_local = threading.local()

def get_duckdb_conn():
    """
    Returns a thread-local DuckDB connection. 
    DuckDB supports concurrent reads easily, and handles single-writer locks internally.
    """
    if not hasattr(_thread_local, "conn"):
        _thread_local.conn = duckdb.connect(DB_PATH)
    return _thread_local.conn

def init_db():
    """Initializes the 1-minute time-series schema if it doesn't exist."""
    conn = get_duckdb_conn()
    
    # 1-minute historical prices
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices_1m (
            symbol VARCHAR,
            datetime TIMESTAMP,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume DOUBLE,
            PRIMARY KEY (symbol, datetime)
        )
    """)
    
    # Create an index for faster symbol-based time-range queries
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_prices_1m_symbol_time 
        ON prices_1m(symbol, datetime DESC)
    """)
    
def insert_1m_data(df: pd.DataFrame):
    """
    Inserts a pandas DataFrame containing 1-minute data into DuckDB.
    Expected columns: symbol, datetime, open, high, low, close, volume
    """
    if df.empty:
        return
        
    conn = get_duckdb_conn()
    
    # DuckDB can insert directly from a pandas DataFrame via an INSERT INTO ... SELECT
    # We use ON CONFLICT to avoid duplicate entries for the same minute
    conn.execute("""
        INSERT INTO prices_1m 
        SELECT symbol, datetime, open, high, low, close, volume 
        FROM df
        ON CONFLICT (symbol, datetime) DO UPDATE SET 
            open=EXCLUDED.open,
            high=EXCLUDED.high,
            low=EXCLUDED.low,
            close=EXCLUDED.close,
            volume=EXCLUDED.volume
    """)

def get_1m_data(symbol: str, start_time=None, end_time=None, limit=None) -> pd.DataFrame:
    """
    Retrieves 1-minute historical data for a given symbol.
    Returns a pandas DataFrame ordered chronologically.
    """
    conn = get_duckdb_conn()
    query = "SELECT * FROM prices_1m WHERE symbol = ?"
    params = [symbol]
    
    if start_time:
        query += " AND datetime >= ?"
        params.append(start_time)
    if end_time:
        query += " AND datetime <= ?"
        params.append(end_time)
        
    query += " ORDER BY datetime ASC"
    
    if limit:
        # Since we want the *latest* N candles but chronologically, we wrap it
        query = f"""
            SELECT * FROM (
                SELECT * FROM prices_1m 
                WHERE symbol = ?
                ORDER BY datetime DESC 
                LIMIT {int(limit)}
            ) sub 
            ORDER BY datetime ASC
        """
        params = [symbol] # resetting params since start/end aren't used in limit wrapper
        
    df = conn.execute(query, params).fetchdf()
    return df

# Initialize the database on import
init_db()
