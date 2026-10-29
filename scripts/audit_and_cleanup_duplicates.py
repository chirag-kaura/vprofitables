import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.paths import DB_PATH

def audit_duplicates():
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    c = conn.cursor()

    print("=" * 60)
    print("  DATABASE DUPLICATE & INTEGRITY AUDIT")
    print("=" * 60)

    # 1. Check intraday date range & bar count
    c.execute("SELECT MIN(candle_time), MAX(candle_time), COUNT(*) FROM intraday_prices")
    min_t, max_t, cnt = c.fetchone()
    print(f"\n1. intraday_prices: {cnt:,} bars, from {min_t} to {max_t}")
    c.execute("""
        SELECT COUNT(*) FROM (
            SELECT symbol, interval, candle_time, COUNT(*) as c
            FROM intraday_prices
            GROUP BY symbol, interval, candle_time
            HAVING c > 1
        )
    """)
    dup_intra = c.fetchone()[0]
    print(f"   Duplicate (symbol, interval, candle_time) keys: {dup_intra}")

    # 2. Check forward_signals duplicates
    c.execute("""
        SELECT symbol, projected_date, scout_source, COUNT(*) as c
        FROM forward_signals
        GROUP BY symbol, projected_date, scout_source
        HAVING c > 1
    """)
    dup_fs = c.fetchall()
    total_dup_fs_rows = sum(r[3] - 1 for r in dup_fs)
    print(f"\n2. forward_signals: {len(dup_fs)} duplicate groups, {total_dup_fs_rows} redundant rows")
    for r in dup_fs[:5]:
        print(f"   * {r[0]} on {r[1]} via {r[2]} -> {r[3]} occurrences")

    # 3. Check news_sentiment duplicates by headline_hash and title
    c.execute("""
        SELECT headline_hash, COUNT(*) as c
        FROM news_sentiment
        WHERE headline_hash IS NOT NULL AND headline_hash != ''
        GROUP BY headline_hash
        HAVING c > 1
    """)
    dup_news = c.fetchall()
    total_dup_news = sum(r[1] - 1 for r in dup_news)
    print(f"\n3. news_sentiment: {len(dup_news)} duplicate headline_hash groups, {total_dup_news} redundant rows")

    # 4. Check option_chain_data duplicates
    c.execute("""
        SELECT symbol, trade_date, expiry_date, strike, option_type, COUNT(*) as c
        FROM option_chain_data
        GROUP BY symbol, trade_date, expiry_date, strike, option_type
        HAVING c > 1
    """)
    dup_opt = c.fetchall()
    total_dup_opt = sum(r[5] - 1 for r in dup_opt)
    print(f"\n4. option_chain_data: {len(dup_opt)} duplicate strike/expiry groups, {total_dup_opt} redundant rows")

    # 5. Check tracker_bucket duplicates
    c.execute("""
        SELECT symbol, projected_date, COUNT(*) as c
        FROM tracker_bucket
        GROUP BY symbol, projected_date
        HAVING c > 1
    """)
    dup_tb = c.fetchall()
    total_dup_tb = sum(r[2] - 1 for r in dup_tb)
    print(f"\n5. tracker_bucket: {len(dup_tb)} duplicate groups, {total_dup_tb} redundant rows")

    # 6. Check database freelist space
    c.execute("PRAGMA page_count")
    page_count = c.fetchone()[0]
    c.execute("PRAGMA page_size")
    page_size = c.fetchone()[0]
    c.execute("PRAGMA freelist_count")
    freelist_count = c.fetchone()[0]
    total_mb = (page_count * page_size) / (1024 * 1024)
    free_mb = (freelist_count * page_size) / (1024 * 1024)
    print(f"\n6. Storage & Freelist Fragmentation:")
    print(f"   Total DB file size: {total_mb:.2f} MB")
    print(f"   Freelist dead space: {freelist_count} pages ({free_mb:.2f} MB)")

    conn.close()

def clean_duplicates():
    conn = sqlite3.connect(DB_PATH, timeout=120.0)
    c = conn.cursor()
    print("\n" + "=" * 60)
    print("  EXECUTING DETERMINISTIC DEDUPLICATION")
    print("=" * 60)

    # 1. forward_signals
    c.execute("""
        DELETE FROM forward_signals
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM forward_signals
            GROUP BY symbol, COALESCE(projected_date, ''), COALESCE(scout_source, '')
        )
    """)
    del_fs = c.rowcount
    print(f"  * Purged {del_fs:,} duplicate forward_signals.")

    # 2. tracker_bucket
    c.execute("""
        DELETE FROM tracker_bucket
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM tracker_bucket
            GROUP BY symbol, COALESCE(projected_date, '')
        )
    """)
    del_tb = c.rowcount
    print(f"  * Purged {del_tb:,} duplicate tracker_bucket rows.")

    # 3. news_sentiment
    c.execute("""
        DELETE FROM news_sentiment
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM news_sentiment
            GROUP BY headline_hash
        ) AND headline_hash IS NOT NULL AND headline_hash != ''
    """)
    del_news = c.rowcount
    print(f"  * Purged {del_news:,} duplicate news_sentiment rows.")

    # 4. option_chain_data
    c.execute("""
        DELETE FROM option_chain_data
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM option_chain_data
            GROUP BY symbol, trade_date, expiry_date, strike, option_type
        )
    """)
    del_opt = c.rowcount
    print(f"  * Purged {del_opt:,} duplicate option_chain_data rows.")

    conn.commit()
    print("  [OK] Deduplication committed successfully.")

    # Create covering unique indexes to permanently prevent recurrence
    print("\n--- Enforcing Unique Constraints ---")
    try:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_uniq_oc ON option_chain_data(symbol, trade_date, expiry_date, strike, option_type)")
        print("  * Unique index enforced: idx_uniq_oc on option_chain_data")
    except Exception as e:
        print(f"  [WARN] idx_uniq_oc: {e}")

    try:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_uniq_news_hash ON news_sentiment(headline_hash)")
        print("  * Unique index enforced: idx_uniq_news_hash on news_sentiment")
    except Exception as e:
        print(f"  [WARN] idx_uniq_news_hash: {e}")

    conn.commit()

    print("\n--- Running SQLite VACUUM to reclaim disk space & defragment B-trees ---")
    c.execute("VACUUM")
    conn.commit()
    print("  [OK] VACUUM completed.")

    # Post-cleanup metrics
    c.execute("PRAGMA page_count")
    p_cnt = c.fetchone()[0]
    c.execute("PRAGMA page_size")
    p_sz = c.fetchone()[0]
    c.execute("PRAGMA freelist_count")
    f_cnt = c.fetchone()[0]
    total_mb = (p_cnt * p_sz) / (1024 * 1024)
    free_mb = (f_cnt * p_sz) / (1024 * 1024)
    print(f"\nPost-Cleanup Metrics:")
    print(f"  * Database Size: {total_mb:.2f} MB")
    print(f"  * Freelist Dead Space: {free_mb:.2f} MB ({f_cnt} pages)")

    conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="Execute deduplication and VACUUM")
    args = parser.parse_args()

    audit_duplicates()
    if args.clean:
        clean_duplicates()
