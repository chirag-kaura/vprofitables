import os
import sys
import sqlite3
import csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.paths import BASE_DIR, DB_PATH

def run_audit():
    print("=" * 80)
    print("DATABASE HEALTH & MISSING ALPHA POST-INGESTION AUDIT")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Total symbols in nifty500.csv
    nifty_csv = os.path.join(BASE_DIR, "data", "nifty500.csv")
    csv_syms = set()
    if os.path.exists(nifty_csv):
        with open(nifty_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                s = (row.get("Symbol") or "").strip().upper()
                if s:
                    csv_syms.add(s)
    print(f"1. Target Nifty 500 Equities in list: {len(csv_syms)}")
    
    # 2. Financials Table Coverage
    c.execute("SELECT COUNT(DISTINCT symbol), COUNT(*) FROM company_financials_10y")
    fin_syms_cnt, fin_rows = c.fetchone()
    print(f"2. company_financials_10y:")
    print(f"   - Distinct Symbols: {fin_syms_cnt} / {len(csv_syms)} ({(fin_syms_cnt/len(csv_syms))*100:.1f}%)")
    print(f"   - Total Statement Rows: {fin_rows}")
    
    # Check null rates in company_financials_10y
    c.execute("SELECT COUNT(*) FROM company_financials_10y WHERE eps IS NULL")
    eps_nulls = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM company_financials_10y WHERE operating_profit IS NULL")
    op_nulls = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM company_financials_10y WHERE sales IS NULL")
    sales_nulls = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM company_financials_10y WHERE net_profit IS NULL")
    np_nulls = c.fetchone()[0]
    
    print(f"   - Null EPS: {eps_nulls} / {fin_rows} ({(eps_nulls/fin_rows)*100:.2f}%)")
    print(f"   - Null Operating Profit: {op_nulls} / {fin_rows} ({(op_nulls/fin_rows)*100:.2f}%)")
    print(f"   - Null Sales: {sales_nulls} / {fin_rows} ({(sales_nulls/fin_rows)*100:.2f}%)")
    print(f"   - Null Net Profit: {np_nulls} / {fin_rows} ({(np_nulls/fin_rows)*100:.2f}%)")
    
    # 3. Shareholding Table Coverage
    c.execute("SELECT COUNT(DISTINCT symbol), COUNT(*) FROM company_shareholding_quarterly")
    sh_syms_cnt, sh_rows = c.fetchone()
    print(f"3. company_shareholding_quarterly:")
    print(f"   - Distinct Symbols: {sh_syms_cnt} / {len(csv_syms)} ({(sh_syms_cnt/len(csv_syms))*100:.1f}%)")
    print(f"   - Total Shareholding Quarters: {sh_rows}")
    
    # 4. PCR Summary & Options Spot Price Backfill
    c.execute("SELECT COUNT(*), COUNT(CASE WHEN spot_price IS NULL OR spot_price = 0 THEN 1 END) FROM pcr_summary")
    pcr_total, pcr_zero_spot = c.fetchone()
    print(f"4. pcr_summary:")
    print(f"   - Total Rows: {pcr_total}")
    print(f"   - Zero/Null Spot Prices: {pcr_zero_spot} (was previously 5,042)")
    
    # 5. Earnings Calendar Coverage
    c.execute("SELECT COUNT(*), COUNT(DISTINCT symbol) FROM earnings_calendar")
    ec_rows, ec_syms = c.fetchone()
    print(f"5. earnings_calendar:")
    print(f"   - Upcoming Events Recorded: {ec_rows} across {ec_syms} symbols")
    
    # 6. Bulk Block Deals Cleanliness
    c.execute("SELECT COUNT(*) FROM bulk_block_deals WHERE quantity <= 0 OR price <= 0")
    bad_deals = c.fetchone()[0]
    print(f"6. bulk_block_deals:")
    print(f"   - Zero/Negative Price/Qty Deals: {bad_deals} (was previously 88)")
    
    # 7. Daily Prices Cleanliness
    c.execute("SELECT COUNT(*) FROM daily_prices WHERE close <= 0")
    bad_prices = c.fetchone()[0]
    print(f"7. daily_prices:")
    print(f"   - Corrupt Zero/Negative Closes: {bad_prices} (was previously 91)")
    
    # 8. Check any missing symbols
    c.execute("SELECT DISTINCT symbol FROM company_financials_10y")
    synced_syms = set(row[0] for row in c.fetchall())
    missing_syms = csv_syms - synced_syms
    if missing_syms:
        print(f"8. Equities not found on Screener (first 10): {sorted(list(missing_syms))[:10]}")
    else:
        print("8. 100% of Nifty 500 Equities Synced!")
        
    conn.close()

if __name__ == "__main__":
    run_audit()
