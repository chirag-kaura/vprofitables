import sqlite3
import json

conn = sqlite3.connect("market_data_v2.db")
c = conn.cursor()

row = c.execute("SELECT symbol, fiscal_period, sales, expenses, operating_profit, opm_pct, net_profit, eps, other_income, depreciation, interest, profit_before_tax, tax FROM company_financials_10y WHERE symbol='RELIANCE' AND period_type='ANNUAL' ORDER BY fiscal_period DESC LIMIT 2").fetchall()

for r in row:
    print("Period:", r[1])
    print("  Sales:", r[2])
    print("  Expenses:", r[3])
    print("  Operating Profit:", r[4])
    print("  OPM:", r[5])
    print("  Net Profit:", r[6])
    print("  EPS:", r[7])
    print("  PBT:", r[11])
    print("  Tax:", r[12])

conn.close()
