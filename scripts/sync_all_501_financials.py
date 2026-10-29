import os
import sys
import csv
import time
import sqlite3
import random
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.paths import get_db_connection, BASE_DIR
from core.screener_sync import parse_html_financials, HEADERS
from core.shareholding_engine import parse_and_store_shareholding

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/124.0.0.0 Safari/537.36",
]

def get_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return s

def fetch_and_parse_company(symbol: str) -> Dict[str, Any]:
    sess = get_session()
    # Try consolidated first, fallback to standalone
    for url in [
        f"https://www.screener.in/company/{symbol}/consolidated/",
        f"https://www.screener.in/company/{symbol}/"
    ]:
        try:
            r = sess.get(url, timeout=12)
            if r.status_code == 200 and len(r.text) > 3000:
                soup = BeautifulSoup(r.text, "html.parser")
                records = parse_html_financials(soup, symbol)
                if records:
                    # Parse shareholding
                    sh_count = parse_and_store_shareholding(r.text, symbol)
                    return {
                        "symbol": symbol,
                        "success": True,
                        "records": records,
                        "shareholding_count": sh_count
                    }
        except Exception as e:
            time.sleep(0.5)

    return {"symbol": symbol, "success": False, "records": [], "shareholding_count": 0}

def sync_all_501_equities():
    print("=" * 70)
    print("EXECUTING FULL INGESTION & REPAIR FOR ALL 501 NIFTY 500 EQUITIES")
    print("=" * 70)

    # 1. Load Nifty 500 Symbols
    csv_path = os.path.join(BASE_DIR, "data", "nifty500.csv")
    symbols = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            s = (row.get("Symbol") or "").strip().upper()
            if s:
                symbols.append(s)

    print(f"Loaded {len(symbols)} target equities from {csv_path}")

    # Check already complete symbols
    conn = get_db_connection()
    c = conn.cursor()

    insert_sql = """
    INSERT INTO company_financials_10y (
        symbol, fiscal_period, period_type, sales, expenses, operating_profit, opm_pct,
        other_income, depreciation, interest, profit_before_tax, tax, net_profit,
        eps, dividend_amount, equity_share_capital, reserves, borrowings, other_liabilities,
        total_liabilities, net_block, cwip, investments, other_assets, total_assets,
        receivables, inventory, cash_bank, operating_cash_flow, investing_cash_flow,
        financing_cash_flow, net_cash_flow, unit, financing_profit, gross_npa_pct, net_npa_pct
    ) VALUES (
        :symbol, :fiscal_period, :period_type, :sales, :expenses, :operating_profit, :opm_pct,
        :other_income, :depreciation, :interest, :profit_before_tax, :tax, :net_profit,
        :eps, :dividend_amount, :equity_share_capital, :reserves, :borrowings, :other_liabilities,
        :total_liabilities, :net_block, :cwip, :investments, :other_assets, :total_assets,
        :receivables, :inventory, :cash_bank, :operating_cash_flow, :investing_cash_flow,
        :financing_cash_flow, :net_cash_flow, :unit, :financing_profit, :gross_npa_pct, :net_npa_pct
    )
    ON CONFLICT(symbol, fiscal_period, period_type) DO UPDATE SET
        sales=excluded.sales,
        expenses=excluded.expenses,
        operating_profit=excluded.operating_profit,
        opm_pct=excluded.opm_pct,
        net_profit=excluded.net_profit,
        eps=excluded.eps,
        other_income=excluded.other_income,
        depreciation=excluded.depreciation,
        interest=excluded.interest,
        profit_before_tax=excluded.profit_before_tax,
        tax=excluded.tax,
        borrowings=excluded.borrowings,
        operating_cash_flow=excluded.operating_cash_flow,
        updated_at=datetime('now', 'localtime')
    """

    all_cols = [
        'sales', 'expenses', 'operating_profit', 'opm_pct', 'other_income',
        'depreciation', 'interest', 'profit_before_tax', 'tax', 'net_profit',
        'eps', 'dividend_amount', 'equity_share_capital', 'reserves', 'borrowings',
        'other_liabilities', 'total_liabilities', 'net_block', 'cwip',
        'investments', 'other_assets', 'total_assets', 'receivables',
        'inventory', 'cash_bank', 'operating_cash_flow', 'investing_cash_flow',
        'financing_cash_flow', 'net_cash_flow', 'unit', 'financing_profit',
        'gross_npa_pct', 'net_npa_pct'
    ]

    total_synced = 0
    total_records = 0
    t0 = time.time()

    print(f"Starting parallel ingestion with 6 workers...\n")

    with ThreadPoolExecutor(max_workers=6) as executor:
        future_map = {executor.submit(fetch_and_parse_company, sym): sym for sym in symbols}
        
        batch_records = []
        completed_count = 0
        
        for future in as_completed(future_map):
            sym = future_map[future]
            completed_count += 1
            try:
                res = future.result()
                if res["success"] and res["records"]:
                    total_synced += 1
                    for rec in res["records"]:
                        # Integrity fallback: if operating_profit is null, compute from sales - expenses
                        if (rec.get('operating_profit') is None or rec.get('operating_profit') == 0) and rec.get('sales') and rec.get('expenses'):
                            rec['operating_profit'] = round(rec['sales'] - rec['expenses'], 2)
                            if not rec.get('opm_pct') and rec['sales'] > 0:
                                rec['opm_pct'] = round((rec['operating_profit'] / rec['sales']) * 100, 1)

                        for col in all_cols:
                            rec.setdefault(col, None)
                        batch_records.append(rec)
                        total_records += 1

                if completed_count % 25 == 0 or completed_count == len(symbols):
                    # Commit batch to database
                    if batch_records:
                        conn.executemany(insert_sql, batch_records)
                        conn.commit()
                        batch_records = []
                    elapsed = time.time() - t0
                    print(f"  Progress: {completed_count}/{len(symbols)} symbols ({total_synced} successful, {total_records} financial periods saved in {elapsed:.1f}s)")

            except Exception as e:
                print(f"  Error on {sym}: {e}")

        if batch_records:
            conn.executemany(insert_sql, batch_records)
            conn.commit()

    conn.close()

    total_time = time.time() - t0
    print("\n" + "=" * 70)
    print(f"INGESTION COMPLETE: {total_synced}/{len(symbols)} equities successfully synced!")
    print(f"Total financial statement periods saved: {total_records} in {total_time:.1f}s")
    print("=" * 70)

if __name__ == "__main__":
    sync_all_501_equities()
