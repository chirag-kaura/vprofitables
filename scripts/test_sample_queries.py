import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.financial_query import get_company_financials, assemble_chatbot_context
from core.shareholding_engine import get_shareholding_trend
from core.corporate_calendar import is_earnings_imminent

def test_samples():
    print("=" * 80)
    print("VERIFYING VERIFIED TABULAR FINANCIALS & ALPHA ACROSS EQUITIES")
    print("=" * 80)
    
    test_symbols = ["TCS", "POLYCAB", "TATAPOWER", "VOLTAS", "ADANIENT"]
    
    for sym in test_symbols:
        print(f"\n--- Symbol: {sym} ---")
        # 1. Financials
        fin = get_company_financials(sym, period_type="ANNUAL", limit=2)
        if fin:
            for r in fin:
                s_fmt = r['sales_fmt'].replace('\u20b9', 'INR ')
                op_fmt = r['operating_profit_fmt'].replace('\u20b9', 'INR ')
                np_fmt = r['net_profit_fmt'].replace('\u20b9', 'INR ')
                eps_fmt = r['eps_fmt'].replace('\u20b9', 'INR ')
                print(f"  [Annual {r['fiscal_period']}] Sales: {s_fmt} | OP: {op_fmt} ({r['opm_pct_fmt']}) | Net Profit: {np_fmt} | EPS: {eps_fmt}")
        else:
            q_fin = get_company_financials(sym, period_type="QUARTERLY", limit=2)
            for r in q_fin:
                s_fmt = r['sales_fmt'].replace('\u20b9', 'INR ')
                op_fmt = r['operating_profit_fmt'].replace('\u20b9', 'INR ')
                np_fmt = r['net_profit_fmt'].replace('\u20b9', 'INR ')
                eps_fmt = r['eps_fmt'].replace('\u20b9', 'INR ')
                print(f"  [Quarterly {r['fiscal_period']}] Sales: {s_fmt} | OP: {op_fmt} ({r['opm_pct_fmt']}) | Net Profit: {np_fmt} | EPS: {eps_fmt}")
                
        # 2. Shareholding Trend
        sh = get_shareholding_trend(sym)
        print(f"  [Shareholding] Period: {sh.get('latest_period')} | Promoter: {sh.get('promoter_pct')}% (Pledged: {sh.get('pledged_pct')}%) | FII: {sh.get('fii_pct')}% (QoQ: {sh.get('fii_qoq_delta'):+0.2f}%) | DII: {sh.get('dii_pct')}% (QoQ: {sh.get('dii_qoq_delta'):+0.2f}%) | Signal: {sh.get('institutional_signal')}")
        
        # 3. Earnings Risk Gate
        risk = is_earnings_imminent(sym, window_days=7)
        if risk.get("imminent"):
            print(f"  [Event Risk GATE] BLOCKED: {risk.get('risk_message')}")
        else:
            print(f"  [Event Risk GATE] CLEAR: No imminent earnings within 7 days.")

if __name__ == "__main__":
    test_samples()
