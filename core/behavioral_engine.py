import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional

DB_PATH = os.environ.get("DB_PATH", "d:/VPROFITABLES/vprofitables/data/vprofitables.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    return conn

def calculate_user_behavior_metrics(user_id: str) -> Dict[str, Any]:
    """
    Analyzes historical positions to determine true psychological risk profile.
    Returns calculated features like Average_Realized_Holding_Period and Panic_Sell_Rate.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute('''
            SELECT p.entry_date, p.exit_date, p.exit_reason, p.stop_loss, p.exit_price, p.target1, p.inv_type 
            FROM positions p
            JOIN portfolios pf ON p.portfolio_id = pf.id
            WHERE pf.user_id = ? AND p.status = 'closed'
        ''', (user_id,)).fetchall()
        
        if not rows:
            return {
                "average_realized_holding_period_days": 0.0,
                "panic_sell_rate": 0.0,
                "total_closed_trades": 0
            }
            
        total_days = 0
        panic_sells = 0
        valid_holding_records = 0
        
        for row in rows:
            entry_str, exit_str, exit_reason, stop_loss, exit_price, target1, inv_type = row
            
            # 1. Holding Period
            if entry_str and exit_str:
                try:
                    entry_dt = datetime.fromisoformat(entry_str)
                    exit_dt = datetime.fromisoformat(exit_str)
                    days = (exit_dt - entry_dt).days
                    total_days += max(0, days)
                    valid_holding_records += 1
                except ValueError:
                    pass
            
            # 2. Panic Sell Logic
            # Assuming 'manual' exit before stop_loss or target hit
            # A panic sell for a long position might be exiting manually at a loss before hitting stop_loss
            # But the requirement says "percentage of trades closed manually before hitting the stop-loss"
            # So if exit_reason == 'manual' or it just didn't hit stop loss/target, it's a panic sell.
            if exit_reason and 'manual' in exit_reason.lower():
                # For long positions:
                if inv_type in ['long', 'swing']:
                    if exit_price and stop_loss and target1:
                        # Exited before target and above stop loss
                        if exit_price < target1 and exit_price > stop_loss:
                            panic_sells += 1
                elif inv_type == 'short':
                    if exit_price and stop_loss and target1:
                        if exit_price > target1 and exit_price < stop_loss:
                            panic_sells += 1
        
        avg_holding = (total_days / valid_holding_records) if valid_holding_records > 0 else 0.0
        panic_rate = panic_sells / len(rows)
        
        # Store these revealed preferences back into the user's risk profile
        c = conn.cursor()
        c.execute('''
            UPDATE risk_profiles 
            SET revealed_panic_sell_rate = ?, revealed_avg_holding_days = ?
            WHERE user_id = ?
        ''', (panic_rate, avg_holding, user_id))
        
        # Update schema if these columns didn't exist
        
        conn.commit()
        
        return {
            "average_realized_holding_period_days": avg_holding,
            "panic_sell_rate": panic_rate,
            "total_closed_trades": len(rows)
        }
        
    except sqlite3.OperationalError as e:
        # Schema migration for revealed preferences on the fly
        if "no such column" in str(e).lower():
            conn.execute("ALTER TABLE risk_profiles ADD COLUMN revealed_panic_sell_rate REAL DEFAULT 0.0")
            conn.execute("ALTER TABLE risk_profiles ADD COLUMN revealed_avg_holding_days REAL DEFAULT 0.0")
            conn.commit()
            return calculate_user_behavior_metrics(user_id)
        else:
            raise e
    finally:
        conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", type=str, help="User ID to profile", default="admin_1")
    args = parser.parse_args()
    
    metrics = calculate_user_behavior_metrics(args.user)
    print(f"Behavioral Metrics for {args.user}: {json.dumps(metrics, indent=2)}")
