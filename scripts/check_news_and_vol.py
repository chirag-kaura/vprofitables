import sqlite3

conn = sqlite3.connect("market_data_v2.db")
c = conn.cursor()

# Check daily_prices columns
cols = [col[1] for col in c.execute("PRAGMA table_info(daily_prices)").fetchall()]
print("daily_prices columns:", cols)

# Query recent news for RELIANCE
news = c.execute("SELECT title, sentiment_label, sentiment_score, published_at, source FROM news_sentiment WHERE symbol='RELIANCE' ORDER BY published_at DESC LIMIT 3").fetchall()
print(f"Reliance news count: {len(news)}")
for n in news:
    print(" -", n)

conn.close()
