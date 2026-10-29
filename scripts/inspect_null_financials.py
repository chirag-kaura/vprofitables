import sqlite3

conn = sqlite3.connect("market_data_v2.db")
c = conn.cursor()

# 1. Total rows and symbol count
total_rows = c.execute("SELECT COUNT(*) FROM company_financials_10y").fetchone()[0]
total_syms = c.execute("SELECT COUNT(DISTINCT symbol) FROM company_financials_10y").fetchone()[0]
print(f"Total rows: {total_rows} across {total_syms} symbols")

# 2. Check null rates by period_type (ANNUAL vs QUARTERLY)
print("\nNull counts by period_type:")
for ptype in ['ANNUAL', 'QUARTERLY']:
    cnt = c.execute("SELECT COUNT(*) FROM company_financials_10y WHERE period_type=?", (ptype,)).fetchone()[0]
    null_eps = c.execute("SELECT COUNT(*) FROM company_financials_10y WHERE period_type=? AND (eps IS NULL OR eps=0)", (ptype,)).fetchone()[0]
    null_op = c.execute("SELECT COUNT(*) FROM company_financials_10y WHERE period_type=? AND (operating_profit IS NULL OR operating_profit=0)", (ptype,)).fetchone()[0]
    null_sales = c.execute("SELECT COUNT(*) FROM company_financials_10y WHERE period_type=? AND (sales IS NULL OR sales=0)", (ptype,)).fetchone()[0]
    print(f"  {ptype:<10} | Total: {cnt:<5} | Null EPS: {null_eps} ({null_eps/cnt*100:.1f}%) | Null OpProfit: {null_op} ({null_op/cnt*100:.1f}%) | Null Sales: {null_sales} ({null_sales/cnt*100:.1f}%)")

# 3. Check sample rows where EPS is null
print("\nSample rows where EPS is NULL:")
sample_null_eps = c.execute("SELECT symbol, fiscal_period, period_type, sales, operating_profit, net_profit, eps, unit FROM company_financials_10y WHERE eps IS NULL LIMIT 5").fetchall()
for r in sample_null_eps:
    print(" ", r)

# 4. Check sample rows where Operating Profit is null
print("\nSample rows where Operating Profit is NULL:")
sample_null_op = c.execute("SELECT symbol, fiscal_period, period_type, sales, operating_profit, net_profit, eps, financing_profit, unit FROM company_financials_10y WHERE operating_profit IS NULL LIMIT 5").fetchall()
for r in sample_null_op:
    print(" ", r)

conn.close()
