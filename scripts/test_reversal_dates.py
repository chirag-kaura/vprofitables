import sys, os
from datetime import date, timedelta
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.gann_math import nearest_sq9, sq9_levels, time_cycles_from_pivot
from core.reversal_map import build_zones_for_symbol

conn = sqlite3.connect('market_data_v2.db')
c = conn.cursor()
c.execute("""
    SELECT trade_date, open, high, low, close, volume 
    FROM daily_prices 
    WHERE symbol='ULTRACEMCO' AND close IS NOT NULL
    ORDER BY trade_date DESC LIMIT 120
""")
rows = list(reversed(c.fetchall()))
closes = [float(r[4]) for r in rows]
highs = [float(r[2] or r[4]) for r in rows]
lows = [float(r[3] or r[4]) for r in rows]
volumes = [float(r[5] or 0) for r in rows]
curr_price = closes[-1]

res_sq9, sup_sq9, *_ = nearest_sq9(curr_price)
print(f"ULTRACEMCO Current Price: ₹{curr_price:,.2f}")
print(f"Gann Sq9 Support: ₹{sup_sq9:,.2f} | Resistance: ₹{res_sq9:,.2f}")

# Reversal Zones
zones = build_zones_for_symbol(
    symbol="ULTRACEMCO",
    closes=closes, highs=highs, lows=lows, volumes=volumes,
    pivot_price=closes[0], pivot_date=date.today() - timedelta(days=90),
    analysis_date=date.today()
)
print(f"Reversal zones count: {len(zones)}")
for z in zones[:3]:
    print(f"  Zone: {z.grade} | {z.date_start} to {z.date_end} | Price: ₹{z.price_low:,.0f} - ₹{z.price_high:,.0f} | Signals: {z.signals}")
