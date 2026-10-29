import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from core.agent_orchestrator import run_agentic_copilot

def test_orchestration():
    queries = [
        ("Tell me about which stock has fallen max in last 5 days", "RELIANCE"),
        ("Im planning to invest my 10000 for 10-12 days can you suggest me any stock which i can look for", "RELIANCE"),
        ("Give me latest updates about Reliance", "RELIANCE"),
        ("Compare TCS vs INFY", "TCS"),
    ]
    
    print("Testing LangGraph Agent Orchestrator...\n" + "="*50)
    for q, sym in queries:
        print(f"\nUser Query: {q}")
        print(f"Sticky UI Symbol: {sym}")
        res = run_agentic_copilot(query=q, symbol=sym)
        print(f"Detected Intent: {res.get('intent')}")
        print(f"Resolved Symbol: {res.get('symbol')}")
        ans_preview = res.get("answer", "").split("\n")[:4]
        print("Answer Preview:\n" + "\n".join(ans_preview))
        
        # Verify guardrails
        if "fallen max" in q:
            assert res.get("intent") == "SCREENER_LOSERS"
            assert "SWIGGY" in res.get("answer") or "Screened" in res.get("answer")
        elif "invest my 10000" in q:
            assert res.get("intent") == "SWING_SETUPS"
            assert "Swing Trading Setups" in res.get("answer") or "TARIL" in res.get("answer")
        elif "latest updates about Reliance" in q:
            assert res.get("intent") == "TICKER_DETAIL"
            assert "%PDF" not in res.get("answer")
        elif "Compare" in q:
            assert res.get("intent") == "COMPARISON"
            
        print("--> PASS!")

    print("\nALL ORCHESTRATION TESTS PASSED!")

if __name__ == "__main__":
    test_orchestration()
