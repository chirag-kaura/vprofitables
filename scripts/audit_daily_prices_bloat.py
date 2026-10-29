import sqlite3
import pandas as pd

conn = sqlite3.connect("market_data_v2.db")
c = conn.cursor()

# 1. Total daily_prices rows
total_prices = c.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
total_syms = c.execute("SELECT COUNT(DISTINCT symbol) FROM daily_prices").fetchone()[0]

# 2. Universe symbols (from nifty500.csv and instruments.py)
import csv
nifty_syms = set()
with open("data/nifty500.csv", "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        s = row.get("Symbol", "").strip().upper()
        if s: nifty_syms.add(s)

indices_commodities = {"NIFTY 50", "NIFTY BANK", "NIFTY IT", "BANKNIFTY", "NIFTY50", "GOLD", "SILVER", "COPPER", "CRUDEOIL", "NATURALGAS"}
core_universe = nifty_syms.union(indices_commodities)

# How many rows in daily_prices belong to core universe?
placeholders = ",".join("?" for _ in core_universe)
core_rows = c.execute(f"SELECT COUNT(*) FROM daily_prices WHERE symbol IN ({placeholders})", list(core_universe)).fetchone()[0]
non_core_rows = total_prices - core_rows

print(f"Total daily_prices rows: {total_prices} across {total_syms} symbols")
print(f"Core Universe rows (Nifty 500 + Indices/Cmd): {core_rows} rows")
print(f"Non-Core / Dead / Defunct symbols rows: {non_core_rows} rows ({non_core_rows/total_prices*100:.1f}%)")

# How many non-core symbols?
non_core_syms = total_syms - len(c.execute(f"SELECT DISTINCT symbol FROM daily_prices WHERE symbol IN ({placeholders})", list(core_universe)).fetchall())
print(f"Non-Core distinct symbols: {non_core_syms}")

# Check symbols with < 50 trading days
orphan_syms_cnt = c.execute("SELECT COUNT(*) FROM (SELECT symbol, COUNT(*) as cnt FROM daily_prices GROUP BY symbol HAVING cnt < 50)").fetchone()[0]
orphan_rows_cnt = c.execute("SELECT SUM(cnt) FROM (SELECT COUNT(*) as cnt FROM daily_prices GROUP BY symbol HAVING cnt < 50)").fetchone()[0]
print(f"Symbols with < 50 days: {orphan_syms_cnt} symbols totaling {orphan_rows_cnt} rows")

conn.close()
