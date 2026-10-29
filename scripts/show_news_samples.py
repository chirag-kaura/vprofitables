import sqlite3

conn = sqlite3.connect("market_data_v2.db")
c = conn.cursor()

sample_junk = c.execute("SELECT id, symbol, title, snippet, source, published_at FROM news_sentiment WHERE snippet IS NULL OR length(snippet) < 20 LIMIT 5").fetchall()
print("Sample Junk News:")
for row in sample_junk:
    print(row)

sample_good = c.execute("SELECT id, symbol, title, snippet, source, published_at FROM news_sentiment WHERE snippet IS NOT NULL AND length(snippet) >= 80 LIMIT 3").fetchall()
print("\nSample Good News:")
for row in sample_good:
    print(row)

conn.close()
