import sqlite3

conn = sqlite3.connect("market_data_v2.db")
c = conn.cursor()
r = c.execute("SELECT * FROM company_financials_10y WHERE symbol='RELIANCE' ORDER BY fiscal_period DESC LIMIT 1").fetchone()
cols = [col[0] for col in c.description]
for k, v in zip(cols, r):
    if v is not None:
        print(f"  {k}: {v}")
conn.close()
