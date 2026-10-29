import os
import sys
import json

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chatbot_engine import (
    handle_chat_query,
    get_chat_status,
    get_symbol_suggestions,
    get_all_symbols_catalog
)

def run_all_tests():
    print("=" * 70)
    print("COMPREHENSIVE AI ASSISTANT CHATBOT V2 INTEGRATION TEST SUITE")
    print("=" * 70)

    # Test 1: USER's EXACT QUERY: "Tell me about which stock has fallen max in last 5 days"
    print("\n--- [TEST 1] User's Query: 'Tell me about which stock has fallen max in last 5 days' ---")
    res1 = handle_chat_query({"message": "Tell me about which stock has fallen max in last 5 days"})
    print("Model used:", res1.get("model_used"))
    print("Sources:", res1.get("sources"))
    print("Symbol:", res1.get("symbol"))
    print("Reply:")
    print(res1.get("reply"))
    assert "Screener" in res1.get("reply") or "Decliners" in res1.get("reply")
    assert "JSWDULUX" in res1.get("reply") or "SWIGGY" in res1.get("reply")
    print(">> TEST 1 PASSED!")

    # Test 2: Screener Gainers: "Which stock has gained most today?"
    print("\n--- [TEST 2] 'Which stock has gained most today?' ---")
    res2 = handle_chat_query({"message": "Which stock has gained most today?"})
    print("Model used:", res2.get("model_used"))
    print("Reply preview:")
    for line in res2.get("reply", "").split("\n")[:8]:
        print(" ", line)
    assert "Gainers" in res2.get("reply")
    print(">> TEST 2 PASSED!")

    # Test 3: Comparison: "Compare TCS vs INFY"
    print("\n--- [TEST 3] 'Compare TCS vs INFY' ---")
    res3 = handle_chat_query({"message": "Compare TCS vs INFY"})
    print("Model used:", res3.get("model_used"))
    print("Reply preview:")
    for line in res3.get("reply", "").split("\n")[:10]:
        print(" ", line)
    assert "Head-to-Head" in res3.get("reply")
    print(">> TEST 3 PASSED!")

    # Test 4: Single Stock: "What was TCS revenue and operating margin in FY24?"
    print("\n--- [TEST 4] Single Stock Fundamental: 'What was TCS revenue in FY24?' ---")
    res4 = handle_chat_query({"message": "What was TCS revenue in FY24?"})
    print("Model used:", res4.get("model_used"))
    print("Symbol detected:", res4.get("symbol"))
    print("Reply preview:")
    for line in res4.get("reply", "").split("\n")[:10]:
        print(" ", line)
    assert res4.get("symbol") == "TCS"
    assert "TCS" in res4.get("reply")
    print(">> TEST 4 PASSED!")

    # Test 5: Ambiguous Query (No symbol): "What is the operating margin?"
    print("\n--- [TEST 5] Ambiguous Query: 'What is the operating margin?' (No symbol) ---")
    res5 = handle_chat_query({"message": "What is the operating margin?"})
    print("Model used:", res5.get("model_used"))
    print("Reply preview:")
    for line in res5.get("reply", "").split("\n")[:6]:
        print(" ", line)
    assert "Which company" in res5.get("reply")
    print(">> TEST 5 PASSED!")

    # Test 6: Concall Guidance for RELIANCE (Verify clean transcripts, NO office address!)
    print("\n--- [TEST 6] Concall Transcripts for RELIANCE (Boilerplate check) ---")
    res6 = handle_chat_query({"message": "What is management capex guidance for RELIANCE?"})
    reply6 = res6.get("reply", "")
    print("Checking for address/cover letter leaks:")
    print("  'Maker Chambers' in reply:", "Maker Chambers" in reply6)
    print("  'Nariman Point' in reply:", "Nariman Point" in reply6)
    print("  'Regulation 30' in reply:", "Regulation 30" in reply6)
    assert "Maker Chambers" not in reply6
    assert "Nariman Point" not in reply6
    assert "Regulation 30" not in reply6
    print(">> TEST 6 PASSED: Clean transcripts, zero boilerplate leaks!")

    # Test 7: Help Intent
    print("\n--- [TEST 7] Help / Capabilities: 'hello what can you do?' ---")
    res7 = handle_chat_query({"message": "hello what can you do?"})
    assert "Capabilities" in res7.get("reply")
    print(">> TEST 7 PASSED!")

    print("\n" + "=" * 70)
    print("ALL 7 CRITICAL CHATBOT TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    run_all_tests()
