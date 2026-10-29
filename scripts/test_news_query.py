import sqlite3

conn = sqlite3.connect("market_data_v2.db")
c = conn.cursor()
rows = c.execute("SELECT title, label, calibrated_score, published_at, source FROM news_sentiment WHERE symbol='RELIANCE' ORDER BY published_at DESC LIMIT 3").fetchall()
print(f"Loaded {len(rows)} news items for RELIANCE:")
for r in rows:
    print(f"  • [{r[1] or 'NEUTRAL'}] {r[0]} ({r[3]}, Source: {r[4]})")
conn.close()
