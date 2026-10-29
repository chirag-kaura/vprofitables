import sqlite3

conn = sqlite3.connect("market_data_v2.db")
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM daily_prices WHERE deliverable_pct IS NOT NULL")
deliv_cnt = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM daily_prices")
total_cnt = c.fetchone()[0]
print(f"deliverable_pct populated: {deliv_cnt} / {total_cnt} ({deliv_cnt/total_cnt*100:.2f}%)")

# Check date range of deliverable_pct
if deliv_cnt > 0:
    min_d, max_d = c.execute("SELECT MIN(trade_date), MAX(trade_date) FROM daily_prices WHERE deliverable_pct IS NOT NULL").fetchone()
    print(f"deliverable_pct date range: {min_d} to {max_d}")

conn.close()
