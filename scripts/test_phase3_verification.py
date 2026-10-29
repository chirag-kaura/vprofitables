# scripts/test_phase3_verification.py
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chatbot_engine import handle_chat_query

test_cases = [
    {
        "name": "Single Stock Ticker Detail + Action Chips",
        "params": {"message": "How is TCS performing?", "session_id": "test_phase3_session"},
        "expected_intent": "TICKER_DETAIL",
        "check_strings": ["TCS", "vprof-chat-chip", "openSymbolChart('TCS')"]
    },
    {
        "name": "Options Microstructure Query Routing",
        "params": {"message": "What is the options microstructure for NIFTY?", "session_id": "test_phase3_session"},
        "expected_intent": "OPTIONS_MICROSTRUCTURE",
        "check_strings": ["Call Wall", "Put Wall", "vprof-chat-chip"]
    },
    {
        "name": "Head-to-Head Comparison + Action Chips",
        "params": {"message": "Compare TCS and Infosys", "session_id": "test_phase3_session"},
        "expected_intent": "COMPARISON",
        "check_strings": ["TCS", "INFY", "vprof-chat-chip"]
    },
    {
        "name": "Comparison Recommendation + Action Chips",
        "params": {"message": "Which of the two is better to buy?", "session_id": "test_phase3_session"},
        "expected_intent": "COMPARISON_RECOMMENDATION",
        "check_strings": ["Primary Allocation Preference", "vprof-chat-chip"]
    },
    {
        "name": "Market Screener + Action Chips",
        "params": {"message": "Which stock has fallen max in last 5 days?", "session_id": "test_phase3_session"},
        "expected_intent": "SCREENER_LOSERS",
        "check_strings": ["Nifty 500 Screener", "vprof-chat-chip"]
    },
    {
        "name": "Swing Trade Setups + 1-Click Buy Chips",
        "params": {"message": "I am looking for short term trade for 10-15 days can you suggest me what all stocks can i look for and why?", "session_id": "test_phase3_session"},
        "expected_intent": "SWING_SETUPS",
        "check_strings": ["1-Click Paper Buy", "vprof-chat-chip"]
    },
    {
        "name": "Portfolio Audit with User ID",
        "params": {"message": "How is my portfolio doing today?", "session_id": "test_phase3_session", "user_id": "08d25bf2-10a3-43c3-8aa5-b09f9a20736a"},
        "expected_intent": "PORTFOLIO_AUDIT",
        "check_strings": ["Portfolio", "vprof-chat-chip"]
    },
    {
        "name": "Macro Stress Test Simulation",
        "params": {"message": "Simulate a -3% macro shock on my portfolio", "session_id": "test_phase3_session", "user_id": "08d25bf2-10a3-43c3-8aa5-b09f9a20736a"},
        "expected_intent": "MACRO_STRESS_TEST",
        "check_strings": ["Macro Stress", "vprof-chat-chip"]
    }
]

print("=== Running Phase 3 End-to-End Chatbot Test Suite ===")
all_passed = True

for tc in test_cases:
    print(f"\n--- Testing: {tc['name']} ---")
    res = handle_chat_query(tc["params"])
    reply = res.get("reply", "")
    intent = res.get("metrics_summary", {}).get("intent") or res.get("model_used")
    
    # Check expected intent
    print(f"Intent routed: {intent}")
    if tc["expected_intent"] not in str(intent):
        print(f"  [FAIL] Intent mismatch: expected {tc['expected_intent']} in {intent}")
        all_passed = False
    else:
        print(f"  [PASS] Intent matched: {tc['expected_intent']}")

    # Check required strings
    missing = [s for s in tc["check_strings"] if s not in reply]
    if missing:
        print(f"  [FAIL] Missing expected strings in reply: {missing}")
        all_passed = False
    else:
        print(f"  [PASS] All expected strings & action chips verified ({len(tc['check_strings'])} strings)")

print("\n" + "=" * 50)
if all_passed:
    print("SUCCESS: ALL PHASE 3 VERIFICATION TESTS PASSED SUCCESSFULLY!")
else:
    print("FAILURE: SOME TESTS FAILED. PLEASE REVIEW.")
    sys.exit(1)
