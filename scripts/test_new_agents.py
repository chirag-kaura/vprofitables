import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.agent_orchestrator import run_agentic_copilot

test_queries = [
    # Scenario 1: Portfolio
    ("Help me with what all investments i already have in my portfolio", "PORTFOLIO_AUDIT"),
    # Scenario 3: Capital Allocation ₹50,000
    ("I am looking to make a new investment of 50000 Help me understand How Should I Distribute it to make better profits", "CAPITAL_ALLOCATION"),
    # Scenario 6: Hold vs Exit
    ("Should I hold or exit my positions?", "PORTFOLIO_AUDIT"),
    # Scenario 7 & 19: Earnings & Dividends
    ("Upcoming earnings calendar for Reliance", "CORPORATE_CALENDAR"),
    ("High dividend yield stocks with upcoming ex-date", "CORPORATE_CALENDAR"),
    # Scenario 8: Bulk Deals
    ("Show me recent bulk and block deals in the market", "SMART_MONEY_AUDIT"),
    # Scenario 12: Options Expiry Call Wall / Put Wall
    ("What is the Call Wall and Put Wall for Nifty?", "OPTIONS_MICROSTRUCTURE"),
    # Scenario 16: Dynamic Preferences
    ("Exclude PSU banks and Adani, prefer high dividend yield", "PERSONALIZATION_UPDATE"),
    # Scenario 17: Macro Stress Test
    ("What happens to my portfolio if Nifty drops 500 points?", "MACRO_STRESS_TEST"),
    # Scenario 18: Multi-Timeframe Alignment
    ("Multi timeframe analysis for Reliance", "MULTI_TIMEFRAME")
]

print("=== RUNNING MULTI-AGENT SWARM INTENT VERIFICATION ===")
passed = 0
for q, expected_intent in test_queries:
    res = run_agentic_copilot(query=q)
    actual_intent = res.get("intent")
    ans_len = len(res.get("answer", ""))
    ok = (actual_intent == expected_intent)
    if ok:
        passed += 1
        print(f"[PASS] {actual_intent:25} | Len: {ans_len:5} | Q: '{q[:45]}...'")
    else:
        print(f"[FAIL] Expected {expected_intent:20} Got {actual_intent:20} | Q: '{q}'")

print(f"\nVerification Result: {passed}/{len(test_queries)} passed.")
