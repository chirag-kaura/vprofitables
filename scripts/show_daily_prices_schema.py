import sqlite3

conn = sqlite3.connect("market_data_v2.db")
c = conn.cursor()
info = c.execute('PRAGMA table_info("daily_prices")').fetchall()
print("daily_prices columns:")
for col in info:
    print(f"  {col[1]}: {col[2]}")
conn.close()
