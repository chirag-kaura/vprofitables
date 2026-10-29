import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "d:/VPROFITABLES/vprofitables/data/vprofitables.db")

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def get_live_stop_loss(position_id: str) -> float:
    """
    Calculates the live exact stop-loss price dynamically based on atr_multiplier and current ATR.
    """
    conn = get_db_connection()
    try:
        # Fetch position
        pos = conn.execute("SELECT symbol, inv_type, entry_price, stop_loss, atr_multiplier FROM positions WHERE id=?", (position_id,)).fetchone()
        if not pos:
            return 0.0
            
        sym, inv_type, entry, static_sl, atr_mult = pos
        
        # If no ATR multiplier is set, fallback to static stop-loss
        if atr_mult is None or atr_mult <= 0:
            return static_sl if static_sl else 0.0
            
        # Fetch current ATR (we approximate ATR as high-low of last day or from a pivot_levels table if available)
        # For simplicity, let's just get the last 14 days and calculate a rough ATR
        prices = conn.execute("SELECT high, low, close FROM daily_prices WHERE symbol=? ORDER BY trade_date DESC LIMIT 14", (sym,)).fetchall()
        
        if not prices:
            return static_sl if static_sl else 0.0
            
        true_ranges = []
        for i in range(len(prices)):
            high, low, close = prices[i]
            prev_close = prices[i+1][2] if i+1 < len(prices) else close
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)
            
        current_atr = sum(true_ranges) / len(true_ranges)
        
        latest_close = prices[0][2]
        
        if inv_type in ['long', 'swing']:
            live_sl = latest_close - (current_atr * atr_mult)
        else:
            live_sl = latest_close + (current_atr * atr_mult)
            
        return round(live_sl, 2)
        
    finally:
        conn.close()
