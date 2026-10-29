"""
core/financials_rag/tools.py
============================
Phase 3 Data Source: Dedicated LangChain Tools for 10-Year Audited Financials,
Balance Sheet Health, Cash Flows, and Quarterly Institutional Shareholding.
All monetary metrics are strictly verified in Indian Rupees (₹ Crores).
"""

import os
import sys
import sqlite3
import pandas as pd
from typing import Optional
from langchain_core.tools import tool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.ohlc_rag.chunker import DB_PATH


@tool
def financials_income_statement(symbol: str, years: int = 5) -> str:
    """
    Retrieves the audited annual Income Statement (Sales, Operating Profit, OPM%, Net Profit, EPS)
    for a given stock symbol over the last N years from `company_financials_10y`.
    Calculates multi-year revenue and profit growth. All monetary amounts are in ₹ Crores.
    """
    sym = symbol.strip().upper()
    n_years = max(1, min(int(years), 10))
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT fiscal_period, sales, operating_profit, opm_pct, net_profit, eps, unit
        FROM company_financials_10y
        WHERE symbol = ? AND period_type = 'ANNUAL'
        ORDER BY fiscal_period DESC
        LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=(sym, n_years))
    conn.close()

    if df.empty:
        return f"No audited annual financials found for symbol '{sym}' in company_financials_10y."

    df = df.sort_values("fiscal_period").reset_index(drop=True)
    unit_str = df["unit"].iloc[0] if "unit" in df and pd.notna(df["unit"].iloc[0]) else "Cr"

    lines = [
        f"Audited Annual Income Statement for {sym} (Last {len(df)} Fiscal Years, in Rs. {unit_str}):",
        "| Fiscal Period | Sales (Revenue) | Operating Profit | OPM % | Net Profit (PAT) | EPS (Rs.) |",
        "|---|---|---|---|---|---|"
    ]
    for _, r in df.iterrows():
        s_val = f"Rs. {r['sales']:,.1f}" if pd.notna(r['sales']) else "-"
        op_val = f"Rs. {r['operating_profit']:,.1f}" if pd.notna(r['operating_profit']) else "-"
        opm_val = f"{r['opm_pct']:.1f}%" if pd.notna(r['opm_pct']) else "-"
        np_val = f"Rs. {r['net_profit']:,.1f}" if pd.notna(r['net_profit']) else "-"
        eps_val = f"Rs. {r['eps']:.2f}" if pd.notna(r['eps']) else "-"
        lines.append(f"| {r['fiscal_period']} | {s_val} | {op_val} | {opm_val} | {np_val} | {eps_val} |")

    # Calculate growth if at least 2 periods
    if len(df) >= 2:
        s_start = df["sales"].iloc[0]
        s_end = df["sales"].iloc[-1]
        np_start = df["net_profit"].iloc[0]
        np_end = df["net_profit"].iloc[-1]
        n_periods = len(df) - 1

        growth_lines = ["\nGrowth Analysis:"]
        if s_start and s_end and s_start > 0 and s_end > 0:
            cagr_sales = ((s_end / s_start) ** (1.0 / n_periods) - 1.0) * 100.0
            growth_lines.append(f"- Sales Growth: {cagr_sales:+.2f}% CAGR over {n_periods} years (from Rs. {s_start:,.1f} Cr to Rs. {s_end:,.1f} Cr).")
        if np_start and np_end and np_start > 0 and np_end > 0:
            cagr_np = ((np_end / np_start) ** (1.0 / n_periods) - 1.0) * 100.0
            growth_lines.append(f"- Net Profit Growth: {cagr_np:+.2f}% CAGR over {n_periods} years (from Rs. {np_start:,.1f} Cr to Rs. {np_end:,.1f} Cr).")
        lines.extend(growth_lines)

    return "\n".join(lines)


@tool
def financials_balance_sheet(symbol: str) -> str:
    """
    Retrieves the latest audited Balance Sheet metrics (Borrowings, Reserves, Total Assets, Cash, Net Block)
    and computes Debt-to-Equity and financial solvency for a given stock symbol.
    """
    sym = symbol.strip().upper()
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT fiscal_period, borrowings, reserves, equity_share_capital, 
               total_liabilities, total_assets, net_block, cash_bank, operating_cash_flow
        FROM company_financials_10y
        WHERE symbol = ? AND period_type = 'ANNUAL'
        ORDER BY fiscal_period DESC
        LIMIT 1
    """
    df = pd.read_sql_query(query, conn, params=(sym,))
    conn.close()

    if df.empty:
        return f"No audited balance sheet record found for symbol '{sym}'."

    row = df.iloc[0]
    period = row["fiscal_period"]
    borrowings = row.get("borrowings") or 0.0
    reserves = row.get("reserves") or 0.0
    eq_cap = row.get("equity_share_capital") or 0.0
    tot_assets = row.get("total_assets") or 0.0
    cash = row.get("cash_bank") or 0.0
    cfo = row.get("operating_cash_flow") or 0.0

    total_networth = reserves + eq_cap
    de_ratio = (borrowings / total_networth) if total_networth > 0 else None
    de_str = f"{de_ratio:.2f}" if de_ratio is not None else "N/A"
    
    solvency_desc = "Virtually Debt-Free / Strong Net Worth" if de_ratio is not None and de_ratio < 0.1 else \
                    "Conservative Leverage" if de_ratio is not None and de_ratio < 0.5 else \
                    "Moderate Leverage" if de_ratio is not None and de_ratio < 1.0 else \
                    "High Leverage / Debt-Heavy"

    return (
        f"Audited Balance Sheet Health for {sym} (As of {period}, in Rs. Crores):\n"
        f"- Total Borrowings (Debt): Rs. {borrowings:,.1f} Cr\n"
        f"- Net Worth (Reserves + Share Capital): Rs. {total_networth:,.1f} Cr (Reserves: Rs. {reserves:,.1f} Cr)\n"
        f"- Debt-to-Equity Ratio: **{de_str}** ({solvency_desc})\n"
        f"- Cash & Bank Balances: Rs. {cash:,.1f} Cr\n"
        f"- Operating Cash Flow (CFO): Rs. {cfo:,.1f} Cr\n"
        f"- Total Assets / Balance Sheet Size: Rs. {tot_assets:,.1f} Cr"
    )


@tool
def financials_shareholding_trend(symbol: str) -> str:
    """
    Retrieves the quarterly institutional shareholding breakdown (Promoter %, FII %, DII %, Public %, Pledged %)
    for a stock symbol across recent quarters from `company_shareholding_quarterly`.
    """
    sym = symbol.strip().upper()
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT fiscal_period, promoter_pct, fii_pct, dii_pct, public_pct, pledged_pct
        FROM company_shareholding_quarterly
        WHERE symbol = ?
        ORDER BY fiscal_period DESC
        LIMIT 4
    """
    df = pd.read_sql_query(query, conn, params=(sym,))
    conn.close()

    if df.empty:
        return f"No quarterly shareholding data found for symbol '{sym}'."

    lines = [
        f"Quarterly Institutional Shareholding Pattern for {sym}:",
        "| Quarter | Promoter % | FII (Foreign) % | DII (Domestic) % | Public % | Pledged % |",
        "|---|---|---|---|---|---|"
    ]
    for _, r in df.iterrows():
        p_val = f"{r['promoter_pct']:.2f}%" if pd.notna(r['promoter_pct']) else "-"
        fii_val = f"{r['fii_pct']:.2f}%" if pd.notna(r['fii_pct']) else "-"
        dii_val = f"{r['dii_pct']:.2f}%" if pd.notna(r['dii_pct']) else "-"
        pub_val = f"{r['public_pct']:.2f}%" if pd.notna(r['public_pct']) else "-"
        pl_val = f"{r['pledged_pct']:.2f}%" if pd.notna(r['pledged_pct']) else "0.00%"
        lines.append(f"| {r['fiscal_period']} | {p_val} | {fii_val} | {dii_val} | {pub_val} | {pl_val} |")

    return "\n".join(lines)


@tool
def financials_banking_quality(symbol: str) -> str:
    """
    Retrieves banking asset quality metrics (Gross NPA %, Net NPA %, Financing Profit) for banks and NBFCs.
    Clarifies if the requested stock is a non-banking entity where NPA does not apply.
    """
    sym = symbol.strip().upper()
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT fiscal_period, gross_npa_pct, net_npa_pct, financing_profit, net_profit
        FROM company_financials_10y
        WHERE symbol = ? AND period_type = 'ANNUAL' AND (gross_npa_pct IS NOT NULL OR financing_profit IS NOT NULL)
        ORDER BY fiscal_period DESC
        LIMIT 4
    """
    df = pd.read_sql_query(query, conn, params=(sym,))
    conn.close()

    if df.empty:
        return f"Asset quality / NPA metrics are not applicable to '{sym}' as it is not categorized as a Banking/NBFC institution in the database."

    lines = [
        f"Banking Asset Quality & NPA Trajectory for {sym}:",
        "| Fiscal Period | Gross NPA % | Net NPA % | Financing Profit (Rs. Cr) | Net Profit (Rs. Cr) |",
        "|---|---|---|---|---|"
    ]
    for _, r in df.iterrows():
        gnpa = f"{r['gross_npa_pct']:.2f}%" if pd.notna(r['gross_npa_pct']) else "-"
        nnpa = f"{r['net_npa_pct']:.2f}%" if pd.notna(r['net_npa_pct']) else "-"
        fp = f"Rs. {r['financing_profit']:,.1f}" if pd.notna(r['financing_profit']) else "-"
        np_val = f"Rs. {r['net_profit']:,.1f}" if pd.notna(r['net_profit']) else "-"
        lines.append(f"| {r['fiscal_period']} | {gnpa} | {nnpa} | {fp} | {np_val} |")

    return "\n".join(lines)


ALL_FINANCIALS_TOOLS = [
    financials_income_statement,
    financials_balance_sheet,
    financials_shareholding_trend,
    financials_banking_quality
]


if __name__ == "__main__":
    print("[*] Testing Financials Tools...")
    print("\n--- Income Statement: RELIANCE ---")
    print(financials_income_statement.invoke({"symbol": "RELIANCE", "years": 3}))

    print("\n--- Balance Sheet: TCS ---")
    print(financials_balance_sheet.invoke({"symbol": "TCS"}))

    print("\n--- Shareholding: HDFCBANK ---")
    print(financials_shareholding_trend.invoke({"symbol": "HDFCBANK"}))

    print("\n--- Asset Quality: SBIN ---")
    print(financials_banking_quality.invoke({"symbol": "SBIN"}))
