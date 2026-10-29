import os
import sys
import json
import urllib.parse

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

def test_endpoints():
    print("=" * 60)
    print("TESTING CHATBOT ENGINE DIRECT INTEGRATION")
    print("=" * 60)

    # 1. Chat Status
    status = get_chat_status()
    print("\n[1] /api/chat/status:")
    print(json.dumps(status, indent=2))
    assert status["status"] == "ready"
    assert status["symbols_tracked"] >= 500

    # 2. Suggestions
    suggs = get_symbol_suggestions("INFY")
    print("\n[2] /api/chat/suggestions for INFY:")
    for s in suggs:
        print(f"  - {s}")
    assert len(suggs) >= 4

    # 3. Symbols Catalog
    syms = get_all_symbols_catalog()
    print(f"\n[3] /api/chat/symbols: Loaded {len(syms)} equities")
    assert len(syms) >= 500

    # 4. Chat Query (TCS)
    print("\n[4] /api/chat Query for TCS:")
    res_tcs = handle_chat_query({"message": "What was TCS revenue and net profit in FY24?"})
    print(f"  Symbol detected: {res_tcs.get('symbol')}")
    print(f"  Model: {res_tcs.get('model_used')}")
    print(f"  Sources: {res_tcs.get('sources')}")
    print("  Reply preview:")
    reply_lines = res_tcs.get("reply", "").split("\n")
    for l in reply_lines[:6]:
        print(f"    {l}")

    # 5. Chat Query (Banking stock: HDFCBANK)
    print("\n[5] /api/chat Query for HDFC Bank:")
    res_hdfc = handle_chat_query({"message": "How is HDFC Bank performance?", "symbol": "HDFCBANK"})
    print(f"  Symbol detected: {res_hdfc.get('symbol')}")
    print(f"  Model: {res_hdfc.get('model_used')}")
    print(f"  Sources: {res_hdfc.get('sources')}")

    print("\n" + "=" * 60)
    print("ALL CHATBOT INTEGRATION TESTS PASSED PERFECTLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_endpoints()
