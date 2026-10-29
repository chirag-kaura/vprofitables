import sqlite3
import pandas as pd

conn = sqlite3.connect("market_data_v2.db")
c = conn.cursor()

print("="*60)
print("DEEP DIVE: EXACT FLAW MEASUREMENTS")
print("="*60)

# 1. bulk_block_deals zero / corrupt check
c.execute("SELECT COUNT(*) FROM bulk_block_deals WHERE price = 0 OR quantity = 0 OR client_name LIKE '%?%' OR client_name LIKE '%%'")
corrupt_deals = c.fetchone()[0]
total_deals = c.execute("SELECT COUNT(*) FROM bulk_block_deals").fetchone()[0]
print(f"\n1. BULK/BLOCK DEALS FLAW:")
print(f"   Total rows: {total_deals}")
print(f"   Corrupt/Zero/Garbage rows: {corrupt_deals} ({corrupt_deals/total_deals*100:.1f}%)")

# 2. option_chain_data empty expiry & zero price check
c.execute("SELECT COUNT(*) FROM option_chain_data WHERE expiry_date = '' OR expiry_date IS NULL")
empty_expiry = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM option_chain_data WHERE ltp = 0 AND oi = 0")
dead_strikes = c.fetchone()[0]
total_options = c.execute("SELECT COUNT(*) FROM option_chain_data").fetchone()[0]
print(f"\n2. OPTION CHAIN DATA FLAW:")
print(f"   Total rows: {total_options}")
print(f"   Empty Expiry Date rows: {empty_expiry} ({empty_expiry/total_options*100:.1f}%)")
print(f"   Dead Strikes (LTP=0 & OI=0): {dead_strikes} ({dead_strikes/total_options*100:.1f}%)")

# 3. pcr_summary missing spot / atm check
c.execute("SELECT COUNT(*) FROM pcr_summary WHERE spot_price = 0 OR spot_price IS NULL")
zero_spot = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM pcr_summary WHERE iv_skew IS NULL")
null_skew = c.fetchone()[0]
total_pcr = c.execute("SELECT COUNT(*) FROM pcr_summary").fetchone()[0]
print(f"\n3. PCR SUMMARY FLAW:")
print(f"   Total rows: {total_pcr}")
print(f"   Zero/Null Spot Price: {zero_spot} ({zero_spot/total_pcr*100:.1f}%)")
print(f"   Null IV Skew: {null_skew} ({null_skew/total_pcr*100:.1f}%)")

# 4. news_sentiment quality check
print(f"\n4. NEWS SENTIMENT QUALITY CHECK:")
c.execute("SELECT source, COUNT(*) FROM news_sentiment GROUP BY source ORDER BY COUNT(*) DESC LIMIT 5")
print(f"   Top Sources: {c.fetchall()}")
c.execute("SELECT COUNT(*) FROM news_sentiment WHERE length(title) < 15 OR snippet IS NULL OR length(snippet) < 20")
low_quality_news = c.fetchone()[0]
total_news = c.execute("SELECT COUNT(*) FROM news_sentiment").fetchone()[0]
print(f"   Low quality/empty snippet news: {low_quality_news} ({low_quality_news/total_news*100:.1f}%)")
# Check how many news items are older than 90 days vs actively used
c.execute("SELECT COUNT(*) FROM news_sentiment WHERE published_at < '2025-01-01'")
old_news = c.fetchone()[0]
print(f"   Old / Historical news (>1 yr): {old_news} ({old_news/total_news*100:.1f}%)")

# 5. daily_prices symbol bloating
c.execute("SELECT COUNT(DISTINCT symbol) FROM daily_prices")
price_syms = c.fetchone()[0]
print(f"\n5. DAILY PRICES UNIVERSE BLOAT:")
print(f"   Distinct symbols in daily_prices: {price_syms}")
# Symbols with less than 50 rows
c.execute("SELECT COUNT(*) FROM (SELECT symbol, COUNT(*) as cnt FROM daily_prices GROUP BY symbol HAVING cnt < 50)")
dead_syms = c.fetchone()[0]
print(f"   Orphan/dead symbols with < 50 days of trading: {dead_syms}")

conn.close()

conn = sqlite3.connect("market_data_v2.db")
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM daily_prices WHERE delivery_pct IS NOT NULL")
deliv_filled = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM daily_prices")
total_prices = c.fetchone()[0]
print(f"\n6. DELIVERY DATA POPULATION:")
print(f"   Delivery % populated: {deliv_filled} / {total_prices} ({deliv_filled/total_prices*100:.2f}%)")

# Check update_all.py or active scheduler
conn.close()
