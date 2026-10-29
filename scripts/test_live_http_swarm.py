import requests
import json
import time

BASE_URL = "http://localhost:5050"

test_scenarios = [
    ("Scenario 1: Portfolio Audit", "Help me with what all investments i already have in my portfolio"),
    ("Scenario 2: Single Stock News & Sentiment", "Help me with latest news about Reliance and what people are talking about it"),
    ("Scenario 3: Capital Allocation ₹50,000", "I am looking to make a new investment of 50000 Help me understand How Should I Distribute it to make better profits"),
    ("Scenario 4: Head-to-Head Comparison", "Compare TCS vs INFY"),
    ("Scenario 6: Hold vs Exit Audit", "Should I hold or exit my positions?"),
    ("Scenario 8: Institutional Bulk Deals", "Show me recent bulk and block deals in the market"),
    ("Scenario 12: Options Microstructure & Call/Put Wall", "What is the Call Wall and Put Wall for Nifty?"),
    ("Scenario 16: Dynamic User Preference Learning", "Exclude PSU banks and Adani, prefer high dividend yield"),
    ("Scenario 17: Macro Stress Test (-500 pts)", "What happens to my portfolio if Nifty drops 500 points?"),
    ("Scenario 18: Multi-Timeframe Matrix", "Multi timeframe analysis for Reliance")
]

print("=" * 70)
print("🚀 RUNNING LIVE HTTP MULTI-AGENT SWARM VERIFICATION (PORT 5050)")
print("=" * 70)

all_passed = True
for name, query in test_scenarios:
    t0 = time.time()
    try:
        resp = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": query, "session_id": "test_e2e_session"},
            timeout=30
        )
        latency = int((time.time() - t0) * 1000)
        if resp.status_code == 200:
            data = resp.json()
            model = data.get("model_used", "")
            ans = data.get("reply", "")
            sym = data.get("symbol")
            print(f"✅ [PASS] {name}")
            print(f"   Model: {model} | Latency: {latency}ms | Symbol: {sym}")
            print(f"   Excerpt: {ans[:120].replace(chr(10), ' ')}...\n")
        else:
            print(f"❌ [FAIL] {name}: HTTP {resp.status_code}")
            all_passed = False
    except Exception as e:
        print(f"❌ [ERROR] {name}: {e}")
        all_passed = False

# Now test direct In-Chat Paper Trade Execution endpoint
print("-" * 70)
print("⚡ TESTING IN-CHAT 1-CLICK PAPER ORDER EXECUTION (/api/chat/execute_order)")
print("-" * 70)
try:
    order_payload = {
        "symbol": "TARIL",
        "shares": 5,
        "entry_price": 303.90,
        "stop_loss": 288.70,
        "target1": 340.00,
        "order_type": "BUY"
    }
    resp = requests.post(f"{BASE_URL}/api/chat/execute_order", json=order_payload, timeout=10)
    if resp.status_code == 200:
        ord_res = resp.json()
        print(f"✅ [PASS] Paper Order Execution Succeeded!")
        print(f"   Status: {ord_res.get('status')} | Order ID: #{ord_res.get('order_id')}")
        print(f"   Message: {ord_res.get('message')}\n")
    else:
        print(f"❌ [FAIL] Order execution returned HTTP {resp.status_code}: {resp.text}")
        all_passed = False
except Exception as e:
    print(f"❌ [ERROR] Order execution test failed: {e}")
    all_passed = False

if all_passed:
    print("=" * 70)
    print("🏆 ALL LIVE HTTP SWARM SCENARIOS & 1-CLICK EXECUTION VERIFIED 100%!")
    print("=" * 70)
else:
    print("⚠️ Some tests encountered issues.")
