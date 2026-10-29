import sqlite3
import pandas as pd
import csv
import os

DB_PATH = "market_data_v2.db"
NIFTY_CSV = "data/nifty500.csv"

# Load Nifty 500 symbols
nifty_symbols = {}
if os.path.exists(NIFTY_CSV):
    with open(NIFTY_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sym = row.get("Symbol", "").strip().upper()
            if sym:
                nifty_symbols[sym] = {
                    "name": row.get("Company Name", "").strip(),
                    "industry": row.get("Industry", "").strip()
                }

print(f"Loaded {len(nifty_symbols)} Nifty 500 equities from CSV.")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Get last 6 dates (for 5-day delta)
dates = [r[0] for r in c.execute("SELECT DISTINCT trade_date FROM daily_prices ORDER BY trade_date DESC LIMIT 6").fetchall()]
end_date = dates[0]
start_date = dates[-1]
print(f"Screening from {start_date} to {end_date} (5 trading sessions)")

q = """
SELECT 
    p1.symbol,
    p2.close as start_close,
    p1.close as end_close,
    ROUND(((p1.close - p2.close) / p2.close) * 100, 2) as pct_change,
    p1.volume
FROM daily_prices p1
JOIN daily_prices p2 ON p1.symbol = p2.symbol
WHERE p1.trade_date = ? 
  AND p2.trade_date = ?
  AND p1.volume > 5000
"""
rows = c.execute(q, (end_date, start_date)).fetchall()
conn.close()

# Filter only Nifty 500 equities
nifty_rows = []
for r in rows:
    sym = r[0]
    if sym in nifty_symbols:
        nifty_rows.append({
            "symbol": sym,
            "name": nifty_symbols[sym]["name"],
            "industry": nifty_symbols[sym]["industry"],
            "start_close": r[1],
            "end_close": r[2],
            "pct_change": r[3],
            "volume": r[4]
        })

df = pd.DataFrame(nifty_rows)
losers = df.sort_values(by="pct_change", ascending=True).head(5)
gainers = df.sort_values(by="pct_change", ascending=False).head(5)

print("\n--- TOP 5 LOSERS (LAST 5 DAYS) IN NIFTY 500 ---")
print(losers[["symbol", "name", "industry", "start_close", "end_close", "pct_change", "volume"]].to_string(index=False))

print("\n--- TOP 5 GAINERS (LAST 5 DAYS) IN NIFTY 500 ---")
print(gainers[["symbol", "name", "industry", "start_close", "end_close", "pct_change", "volume"]].to_string(index=False))
