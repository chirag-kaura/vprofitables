import os
import sys
import sqlite3
import time

DB_PATH = "market_data_v2.db"

def execute_step1():
    print("=" * 65)
    print("STEP 1: PURGING JUNK DATA & RECLAIMING DATABASE DISK SPACE")
    print("=" * 65)

    initial_size = os.path.getsize(DB_PATH)
    print(f"Initial DB Size: {initial_size / (1024*1024):.2f} MB")

    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    c = conn.cursor()

    # -------------------------------------------------------------
    # 1. Clean bulk_block_deals corrupted rows
    # -------------------------------------------------------------
    print("\n[1] Cleaning bulk_block_deals...")
    c.execute("SELECT COUNT(*) FROM bulk_block_deals WHERE price = 0 OR quantity = 0 OR symbol = ''")
    corrupt_deals = c.fetchone()[0]
    c.execute("DELETE FROM bulk_block_deals WHERE price = 0 OR quantity = 0 OR symbol = ''")
    conn.commit()
    print(f"    Purged {corrupt_deals} zero-quantity/price rows from bulk_block_deals.")

    # -------------------------------------------------------------
    # 2. Clean daily_prices: Purge 2,275 orphan/dead tickers
    # -------------------------------------------------------------
    print("\n[2] Cleaning daily_prices (Orphan & Dead Penny Tickers)...")
    # Load core universe
    import csv
    core_universe = set()
    nifty_path = os.path.join("data", "nifty500.csv")
    if os.path.exists(nifty_path):
        with open(nifty_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                s = row.get("Symbol", "").strip().upper()
                if s: core_universe.add(s)
    
    # Add indices and commodities
    core_universe.update([
        "NIFTY 50", "NIFTY BANK", "NIFTY IT", "BANKNIFTY", "NIFTY50", 
        "GOLD", "SILVER", "COPPER", "CRUDEOIL", "NATURALGAS",
        "NIFTYPHARMA", "NIFTYAUTO", "NIFTYMETAL", "NIFTYREALTY", "NIFTYFMCG"
    ])
    
    # Identify dead symbols: not in core universe AND fewer than 100 days of trading
    c.execute("SELECT symbol, COUNT(*) as cnt FROM daily_prices GROUP BY symbol")
    all_sym_counts = c.fetchall()
    
    dead_symbols = []
    for sym, cnt in all_sym_counts:
        if sym.upper() not in core_universe and cnt < 100:
            dead_symbols.append(sym)
            
    print(f"    Identified {len(dead_symbols)} dead/orphan symbols with <100 days trading not in Nifty 500.")
    if dead_symbols:
        # Delete dead symbols in batches of 500
        batch_size = 500
        total_deleted = 0
        for i in range(0, len(dead_symbols), batch_size):
            batch = dead_symbols[i:i+batch_size]
            q = f"DELETE FROM daily_prices WHERE symbol IN ({','.join('?' for _ in batch)})"
            c.execute(q, batch)
            total_deleted += c.rowcount
            conn.commit()
        print(f"    Purged {total_deleted} historical orphan rows from daily_prices.")

    # Also clean zero/negative price rows
    c.execute("DELETE FROM daily_prices WHERE close <= 0 OR high <= 0 OR low <= 0 OR open <= 0")
    zero_prices = c.rowcount
    conn.commit()
    print(f"    Purged {zero_prices} zero/negative price anomaly rows from daily_prices.")

    # -------------------------------------------------------------
    # 3. Clean news_sentiment noise
    # -------------------------------------------------------------
    print("\n[3] Cleaning news_sentiment (Empty Snippets & Promotional Aggregator Spam)...")
    c.execute("""
        DELETE FROM news_sentiment 
        WHERE (snippet IS NULL OR length(trim(snippet)) < 25) 
          AND (source IN ('Whalesbook', 'Univest') OR length(title) < 20)
    """)
    purged_news = c.rowcount
    conn.commit()
    print(f"    Purged {purged_news} low-quality / clickbait spam news rows.")

    # -------------------------------------------------------------
    # 4. Clean option_chain_data & pcr_summary
    # -------------------------------------------------------------
    print("\n[4] Cleaning option_chain_data & pcr_summary...")
    # Delete empty expiry dates
    c.execute("DELETE FROM option_chain_data WHERE expiry_date = '' OR expiry_date IS NULL")
    purged_opt = c.rowcount
    # Delete dead option strikes (zero LTP and zero OI)
    c.execute("DELETE FROM option_chain_data WHERE ltp = 0 AND oi = 0 AND volume = 0")
    purged_dead_strikes = c.rowcount
    conn.commit()
    print(f"    Purged {purged_opt} option chain rows with missing/empty expiry dates.")
    print(f"    Purged {purged_dead_strikes} dead strikes (LTP=0, OI=0, Vol=0).")

    # Clean pcr_summary dead rows where total OI is 0
    c.execute("DELETE FROM pcr_summary WHERE total_ce_oi = 0 AND total_pe_oi = 0")
    purged_pcr = c.rowcount
    conn.commit()
    print(f"    Purged {purged_pcr} dead rows from pcr_summary.")

    # -------------------------------------------------------------
    # 5. Database VACUUM & Re-index
    # -------------------------------------------------------------
    print("\n[5] Running SQLite VACUUM and ANALYZE to defragment B-Trees...")
    conn.close()
    
    # VACUUM must run in non-WAL or fresh exclusive connection
    t0 = time.time()
    conn2 = sqlite3.connect(DB_PATH, timeout=120)
    conn2.execute("VACUUM;")
    conn2.execute("ANALYZE;")
    conn2.close()
    vacuum_time = time.time() - t0
    print(f"    VACUUM complete in {vacuum_time:.1f}s.")

    final_size = os.path.getsize(DB_PATH)
    freed_mb = (initial_size - final_size) / (1024 * 1024)
    print(f"\nFinal DB Size: {final_size / (1024*1024):.2f} MB")
    print(f"Reclaimed Disk Space: {freed_mb:.2f} MB")
    print("=" * 65)
    print("STEP 1 COMPLETE: DATABASE IS CLEANED, DEFRAGMENTED, AND INDEXED!")
    print("=" * 65)

if __name__ == "__main__":
    execute_step1()
