import os
import sys
import csv
import time
import random
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.paths import get_db_connection, BASE_DIR
from core.screener_sync import parse_html_financials
from core.shareholding_engine import parse_shareholding_html, ensure_shareholding_table

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

def fetch_worker(symbol: str) -> Dict[str, Any]:
    sess = get_session()
    candidates = [symbol]
    if "&" in symbol:
        candidates.append(symbol.replace("&", ""))
    if "-" in symbol:
        candidates.append(symbol.replace("-", ""))

    for sym_cand in candidates:
        for url in [
            f"https://www.screener.in/company/{sym_cand}/consolidated/",
            f"https://www.screener.in/company/{sym_cand}/"
        ]:
            try:
                r = sess.get(url, timeout=12)
                if r.status_code == 200 and len(r.text) > 3000:
                    soup = BeautifulSoup(r.text, "html.parser")
                    records = parse_html_financials(soup, symbol)
                    sh_rows = parse_shareholding_html(r.text, symbol)
                    if records or sh_rows:
                        return {
                            "symbol": symbol,
                            "success": True,
                            "records": records,
                            "sh_rows": sh_rows
                        }
            except Exception:
                time.sleep(0.5)

    return {"symbol": symbol, "success": False, "records": [], "sh_rows": []}

def run_sync_missing():
    print("=" * 75)
    print("RESILIENT ZERO-LOCK INGESTION FOR REMAINING NIFTY 500 EQUITIES")
    print("=" * 75)
    sys.stdout.flush()

    # Step 1: Query missing symbols and close DB handle immediately
    ensure_shareholding_table()
    conn_ro = get_db_connection(readonly=True, timeout=10.0)
    c_ro = conn_ro.cursor()
    c_ro.execute("SELECT DISTINCT symbol FROM company_financials_10y")
    existing_fin = set(row[0] for row in c_ro.fetchall())
    conn_ro.close()

    csv_path = os.path.join(BASE_DIR, "data", "nifty500.csv")
    targets = []
    with open(csv_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            s = (row.get("Symbol") or "").strip().upper()
            if s and s not in existing_fin:
                targets.append(s)

    print(f"Total target equities needing sync: {len(targets)}")
    sys.stdout.flush()

    if not targets:
        print("All equities already synced!")
        return

    # Step 2: Concurrently scrape into RAM (ZERO DB connections during scraping)
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

    all_financial_records = []
    all_shareholding_records = []
    success_count = 0
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=6) as executor:
        future_map = {executor.submit(fetch_worker, sym): sym for sym in targets}

        for i, future in enumerate(as_completed(future_map), 1):
            sym = future_map[future]
            try:
                res = future.result()
                if res["success"]:
                    success_count += 1
                    if res["records"]:
                        for rec in res["records"]:
                            if (rec.get('operating_profit') is None or rec.get('operating_profit') == 0) and rec.get('sales') and rec.get('expenses'):
                                rec['operating_profit'] = round(rec['sales'] - rec['expenses'], 2)
                                if not rec.get('opm_pct') and rec['sales'] > 0:
                                    rec['opm_pct'] = round((rec['operating_profit'] / rec['sales']) * 100, 1)
                            for col in all_cols:
                                rec.setdefault(col, None)
                        all_financial_records.extend(res["records"])

                    if res["sh_rows"]:
                        all_shareholding_records.extend(res["sh_rows"])

                    print(f"[{i}/{len(targets)}] Parsed {sym}: {len(res['records'])} fin periods, {len(res['sh_rows'])} sh periods")
                else:
                    print(f"[{i}/{len(targets)}] Not found on Screener: {sym}")
                sys.stdout.flush()
            except Exception as e:
                print(f"[{i}/{len(targets)}] Error on {sym}: {e}")
                sys.stdout.flush()

    fetch_time = time.time() - t0
    print(f"\nAll scraping completed in {fetch_time:.1f}s. Total financial records: {len(all_financial_records)}, shareholding records: {len(all_shareholding_records)}")
    print("Writing to SQLite database in single atomic transaction...")
    sys.stdout.flush()

    # Step 3: Atomic single-transaction insert into SQLite
    insert_fin_sql = """
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
        updated_at=datetime('now', 'localtime')
    """

    insert_sh_sql = """
    INSERT OR REPLACE INTO company_shareholding_quarterly
    (symbol, fiscal_period, promoter_pct, fii_pct, dii_pct, public_pct, pledged_pct)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    t_db = time.time()
    conn_w = get_db_connection(timeout=60.0)
    if all_financial_records:
        conn_w.executemany(insert_fin_sql, all_financial_records)
    if all_shareholding_records:
        conn_w.executemany(insert_sh_sql, all_shareholding_records)
    conn_w.commit()
    conn_w.close()
    db_time = time.time() - t_db

    total_time = time.time() - t0
    print("=" * 75)
    print(f"DATABASE WRITE COMPLETED IN {db_time:.3f}s!")
    print(f"SUCCESS: {success_count}/{len(targets)} equities successfully synced in {total_time:.1f}s total.")
    print("=" * 75)
    sys.stdout.flush()

if __name__ == "__main__":
    run_sync_missing()
