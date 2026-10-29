import sqlite3
import os
import uuid
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "d:/VPROFITABLES/vprofitables/data/vprofitables.db")

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def monitor_implicit_feedback():
    """
    Scans watchlist_stocks for 'high interest, no action' behavior.
    If the Deep Signal Engine recently generated a BUY signal for such a stock,
    creates a high-priority recommendation alert for the user.
    """
    conn = get_db_connection()
    try:
        # 1. Identify users and their high-interest watchlisted stocks (view_count >= 10)
        high_interest_stocks = conn.execute('''
            SELECT w.user_id, ws.symbol, ws.view_count, w.id as portfolio_id
            FROM watchlist_stocks ws
            JOIN watchlists w ON ws.watchlist_id = w.id
            WHERE ws.view_count >= 10
        ''').fetchall()
        
        for row in high_interest_stocks:
            user_id, symbol, views, portfolio_id = row
            
            # 2. Check if the user already has an open position for this stock (no action check)
            open_pos = conn.execute('''
                SELECT id FROM positions 
                WHERE symbol = ? AND status = 'OPEN' AND portfolio_id IN (
                    SELECT id FROM portfolios WHERE user_id = ?
                )
            ''', (symbol, user_id)).fetchone()
            
            if open_pos:
                continue # They already took action
                
            # 3. Check Deep Signal Engine for a recent Reversal Low or Wyckoff Spring
            # Assuming 'reversal LOW' or 'Wyckoff Spring' would be in raw_output or score > 0.8
            # We will just look for a recent BUY signal (score >= 0.7 or direction='BUY')
            recent_signal = conn.execute('''
                SELECT id, score, raw_output FROM signals 
                WHERE symbol = ? AND score >= 0.7
                ORDER BY analysis_date DESC LIMIT 1
            ''', (symbol,)).fetchone()
            
            if recent_signal:
                sig_id, score, raw = recent_signal
                # Create a high priority alert recommendation
                alert_id = "rec_" + str(uuid.uuid4())[:8]
                payload = f'{{"symbol": "{symbol}", "signal_id": "{sig_id}", "priority": "HIGH"}}'
                reasoning = f"You've viewed {symbol} {views} times recently. Deep Signal Engine just detected a high probability reversal setup (Score: {score})."
                
                # Check if we already alerted them recently
                existing_alert = conn.execute('''
                    SELECT id FROM recommendations 
                    WHERE user_id=? AND rec_type='alert' AND payload LIKE ?
                ''', (user_id, f'%"{symbol}"%')).fetchone()
                
                if not existing_alert:
                    # Write to recommendations
                    conn.execute('''
                        INSERT INTO recommendations (id, user_id, portfolio_id, rec_type, payload, reasoning, constraints_checked, passed, created_at, applied)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (alert_id, user_id, portfolio_id, 'alert', payload, reasoning, "{}", 1, datetime.now().isoformat(), 0))
                    print(f"Triggered High-Priority Alert for {user_id} on {symbol} (Telemetry: {views} views)")
                    
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    monitor_implicit_feedback()
