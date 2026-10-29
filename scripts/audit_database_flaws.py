import os
import sys
import sqlite3
import json
from datetime import datetime

DB_PATH = "market_data_v2.db"

def run_audit():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    print(f"=== DATABASE AUDIT: {DB_PATH} ({len(tables)} tables) ===\n")

    table_stats = []
    for t in tables:
        try:
            cnt = c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            cols = [col[1] for col in c.execute(f'PRAGMA table_info("{t}")').fetchall()]
            
            # Check for date columns to find date range
            date_col = None
            for candidate in ['trade_date', 'date', 'timestamp', 'created_at', 'published_at', 'fiscal_period', 'news_date']:
                if candidate in cols:
                    date_col = candidate
                    break
            
            date_range = "N/A"
            if date_col and cnt > 0:
                try:
                    min_d, max_d = c.execute(f'SELECT MIN({date_col}), MAX({date_col}) FROM "{t}" WHERE {date_col} IS NOT NULL').fetchone()
                    date_range = f"{min_d} to {max_d}"
                except Exception:
                    pass

            table_stats.append({
                "table": t,
                "count": cnt,
                "columns": cols,
                "date_col": date_col,
                "date_range": date_range
            })
            print(f"Table: {t:<30} | Rows: {cnt:<8} | DateRange: {date_range}")
        except Exception as e:
            print(f"Table: {t:<30} | ERROR: {e}")

    print("\n" + "="*70)
    print("DETAILED FLAW AUDIT BY DATA CATEGORY")
    print("="*70)

    # 1. NEWS & SENTIMENT AUDIT
    print("\n--- [1] NEWS & SENTIMENT DATA AUDIT ---")
    news_tables = [t for t in tables if 'news' in t.lower() or 'sentiment' in t.lower()]
    for nt in news_tables:
        print(f"\nAudit for table '{nt}':")
        cnt = c.execute(f'SELECT COUNT(*) FROM "{nt}"').fetchone()[0]
        if cnt == 0:
            print(f"  Empty table: 0 rows.")
            continue
        cols = [col[1] for col in c.execute(f'PRAGMA table_info("{nt}")').fetchall()]
        print(f"  Columns: {cols}")
        sample = c.execute(f'SELECT * FROM "{nt}" LIMIT 2').fetchall()
        for s in sample:
            print(f"  Sample: {s[:6]}")
        # Check duplicate titles or empty content
        if 'title' in cols:
            dups = c.execute(f'SELECT title, COUNT(*) FROM "{nt}" GROUP BY title HAVING COUNT(*) > 1 LIMIT 5').fetchall()
            print(f"  Duplicate titles found: {len(dups)}")
            if dups:
                print(f"    Sample dup: {dups[0]}")

    # 2. OHLC / PRICE AUDIT
    print("\n--- [2] OHLC & PRICE DATA AUDIT ---")
    price_tables = [t for t in tables if 'price' in t.lower() or 'bhav' in t.lower() or 'daily' in t.lower()]
    for pt in price_tables:
        print(f"\nAudit for table '{pt}':")
        cnt = c.execute(f'SELECT COUNT(*) FROM "{pt}"').fetchone()[0]
        print(f"  Total rows: {cnt}")
        if cnt == 0:
            continue
        cols = [col[1] for col in c.execute(f'PRAGMA table_info("{pt}")').fetchall()]
        # Check symbols count
        if 'symbol' in cols:
            sym_cnt = c.execute(f'SELECT COUNT(DISTINCT symbol) FROM "{pt}"').fetchone()[0]
            print(f"  Distinct symbols: {sym_cnt}")
        # Check for 0 volume or 0 open/high/low/close anomalies
        check_cols = [col for col in ['open', 'high', 'low', 'close', 'volume'] if col in cols]
        if check_cols:
            where_zero = " OR ".join([f"{col} <= 0 OR {col} IS NULL" for col in check_cols if col != 'volume'])
            if where_zero:
                zero_cnt = c.execute(f'SELECT COUNT(*) FROM "{pt}" WHERE {where_zero}').fetchone()[0]
                print(f"  Zero/Negative/NULL price anomalies: {zero_cnt}")
            if 'volume' in cols:
                zero_vol = c.execute(f'SELECT COUNT(*) FROM "{pt}" WHERE volume = 0 OR volume IS NULL').fetchone()[0]
                print(f"  Zero volume rows: {zero_vol}")

    # 3. OI & PCR AUDIT
    print("\n--- [3] OI, PARTICIPANT & PCR AUDIT ---")
    oi_tables = [t for t in tables if 'oi' in t.lower() or 'pcr' in t.lower() or 'option' in t.lower()]
    for ot in oi_tables:
        print(f"\nAudit for table '{ot}':")
        cnt = c.execute(f'SELECT COUNT(*) FROM "{ot}"').fetchone()[0]
        print(f"  Total rows: {cnt}")
        if cnt > 0:
            cols = [col[1] for col in c.execute(f'PRAGMA table_info("{ot}")').fetchall()]
            print(f"  Columns: {cols}")
            sample = c.execute(f'SELECT * FROM "{ot}" LIMIT 2').fetchall()
            for s in sample:
                print(f"  Sample: {s}")

    # 4. DEALS & INSIDER AUDIT
    print("\n--- [4] BULK / BLOCK DEALS & CORPORATE ACTIONS ---")
    deal_tables = [t for t in tables if 'deal' in t.lower() or 'action' in t.lower() or 'insider' in t.lower()]
    for dt in deal_tables:
        print(f"\nAudit for table '{dt}':")
        cnt = c.execute(f'SELECT COUNT(*) FROM "{dt}"').fetchone()[0]
        print(f"  Total rows: {cnt}")
        if cnt > 0:
            cols = [col[1] for col in c.execute(f'PRAGMA table_info("{dt}")').fetchall()]
            print(f"  Columns: {cols}")
            sample = c.execute(f'SELECT * FROM "{dt}" LIMIT 2').fetchall()
            for s in sample:
                print(f"  Sample: {s}")

    # 5. FINANCIALS & BOILERPLATE AUDIT
    print("\n--- [5] FINANCIAL STATEMENTS & VECTOR TRANSCRIPTS AUDIT ---")
    fin_cnt = c.execute('SELECT COUNT(*) FROM company_financials_10y').fetchone()[0]
    sym_fin = c.execute('SELECT COUNT(DISTINCT symbol) FROM company_financials_10y').fetchone()[0]
    print(f"company_financials_10y: {fin_cnt} rows across {sym_fin} symbols")
    # Check null rates in financial tables
    null_sales = c.execute('SELECT COUNT(*) FROM company_financials_10y WHERE sales IS NULL').fetchone()[0]
    null_op = c.execute('SELECT COUNT(*) FROM company_financials_10y WHERE operating_profit IS NULL').fetchone()[0]
    null_pat = c.execute('SELECT COUNT(*) FROM company_financials_10y WHERE net_profit IS NULL').fetchone()[0]
    null_cf = c.execute('SELECT COUNT(*) FROM company_financials_10y WHERE operating_cash_flow IS NULL').fetchone()[0]
    print(f"  NULL sales: {null_sales}/{fin_cnt} ({null_sales/fin_cnt*100:.1f}%)" if fin_cnt else "  0 rows")
    print(f"  NULL op profit: {null_op}/{fin_cnt} ({null_op/fin_cnt*100:.1f}%)" if fin_cnt else "  0 rows")
    print(f"  NULL net profit: {null_pat}/{fin_cnt} ({null_pat/fin_cnt*100:.1f}%)" if fin_cnt else "  0 rows")
    print(f"  NULL cash flow: {null_cf}/{fin_cnt} ({null_cf/fin_cnt*100:.1f}%)" if fin_cnt else "  0 rows")

    # Document Registry
    reg_cnt = c.execute('SELECT COUNT(*) FROM document_registry').fetchone()[0]
    reg_syms = c.execute('SELECT COUNT(DISTINCT symbol) FROM document_registry').fetchone()[0]
    print(f"\ndocument_registry: {reg_cnt} files registered across {reg_syms} symbols")
    # Check document types
    doc_types = c.execute('SELECT doc_type, COUNT(*) FROM document_registry GROUP BY doc_type').fetchall()
    print(f"  Document types: {doc_types}")

    conn.close()

if __name__ == "__main__":
    run_audit()
