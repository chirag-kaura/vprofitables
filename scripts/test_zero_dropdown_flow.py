import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from core.chatbot_engine import handle_chat_query

def test_zero_dropdown_suite():
    print("=" * 70)
    print("ZERO-DROPDOWN MULTI-TURN & ENTITY RESOLUTION TEST SUITE")
    print("=" * 70)

    session_id = "test_user_session_42"

    # Turn 1: "Give me quick bytes about Adani enterprise"
    print("\n--- [TURN 1] User: 'Give me quick bytes about Adani enterprise' ---")
    res1 = handle_chat_query({
        "message": "Give me quick bytes about Adani enterprise",
        "session_id": session_id
    })
    print("Model:", res1.get("model_used"))
    print("Symbol detected:", res1.get("symbol"))
    reply1 = res1.get("reply", "")
    for line in reply1.split("\n")[:6]:
        print(" ", line)
    assert res1.get("symbol") == "ADANIENT", f"Expected ADANIENT, got {res1.get('symbol')}"
    assert "ADANIENT" in reply1, "Expected ADANIENT in reply"
    assert "RELIANCE" not in reply1, "RELIANCE leaked into Adani query!"
    print(">> TURN 1 PASSED: Correctly mapped 'Adani enterprise' -> ADANIENT!")

    # Turn 2: Follow-up pronoun inheritance: "What is its debt?"
    print("\n--- [TURN 2] User: 'What is its debt?' (Follow-up) ---")
    res2 = handle_chat_query({
        "message": "What is its debt?",
        "session_id": session_id
    })
    print("Model:", res2.get("model_used"))
    print("Symbol detected:", res2.get("symbol"))
    reply2 = res2.get("reply", "")
    assert res2.get("symbol") == "ADANIENT", f"Expected inherited ADANIENT, got {res2.get('symbol')}"
    assert "ADANIENT" in reply2, "Expected ADANIENT in reply"
    assert "RELIANCE" not in reply2, "RELIANCE leaked into inherited query!"
    print(">> TURN 2 PASSED: Successfully inherited ADANIENT via session memory!")

    # Turn 3: "Im asking for Adani Enterprise"
    print("\n--- [TURN 3] User: 'Im asking for Adani Enterprise' ---")
    res3 = handle_chat_query({
        "message": "Im asking for Adani Enterprise",
        "session_id": "test_fresh_session_99"
    })
    print("Model:", res3.get("model_used"))
    print("Symbol detected:", res3.get("symbol"))
    reply3 = res3.get("reply", "")
    assert res3.get("symbol") == "ADANIENT", f"Expected ADANIENT, got {res3.get('symbol')}"
    assert "ADANIENT" in reply3
    assert "RELIANCE" not in reply3
    print(">> TURN 3 PASSED: 'Im asking for Adani Enterprise' mapped to ADANIENT!")

    # Turn 4: Conglomerate Group Query: "Tell me about Adani"
    print("\n--- [TURN 4] Conglomerate Ambiguity: 'Tell me about Adani' ---")
    res4 = handle_chat_query({
        "message": "Tell me about Adani",
        "session_id": "test_fresh_session_100"
    })
    print("Model:", res4.get("model_used"))
    print("Intent:", res4.get("metrics_summary", {}).get("intent"))
    reply4 = res4.get("reply", "")
    assert "Which **ADANI Group** company" in reply4 or "Which **Adani Group** company" in reply4 or "ADANIENT" in reply4
    assert "ADANIPORTS" in reply4
    print(">> TURN 4 PASSED: Successfully returned Group Disambiguation buttons!")

    # Turn 5: Screener: "Which stock has fallen max in last 5 days"
    print("\n--- [TURN 5] Market-Wide Screener: 'Which stock has fallen max in last 5 days' ---")
    res5 = handle_chat_query({
        "message": "Which stock has fallen max in last 5 days",
        "session_id": session_id
    })
    print("Model:", res5.get("model_used"))
    reply5 = res5.get("reply", "")
    assert "Top Decliners" in reply5 or "Screener" in reply5
    assert "SWIGGY" in reply5 or "JSWDULUX" in reply5
    print(">> TURN 5 PASSED: Screener decoupled from previous ADANIENT session!")

    # Turn 6: Swing Setups: "Im planning to invest my 10000 for 10-12 days can you suggest me any stock which i can look for"
    print("\n--- [TURN 6] Swing Setups: 'Im planning to invest my 10000 for 10-12 days...' ---")
    res6 = handle_chat_query({
        "message": "Im planning to invest my 10000 for 10-12 days can you suggest me any stock which i can look for",
        "session_id": session_id
    })
    print("Model:", res6.get("model_used"))
    reply6 = res6.get("reply", "")
    assert "Institutional Swing Trade Setups" in reply6 or "TARIL" in reply6
    print(">> TURN 6 PASSED: Generated swing trade setups!")

    print("\n" + "=" * 70)
    print("ALL ZERO-DROPDOWN & ENTITY RESOLUTION TESTS PASSED 100%!")
    print("=" * 70)

if __name__ == "__main__":
    test_zero_dropdown_suite()
