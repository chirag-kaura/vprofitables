import urllib.request
import json
import time
import sys

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def log(msg):
    print(msg, flush=True)

def query_chat(msg, session_id="test_session_1", model="qwen2.5:7b", symbol=None):
    payload = {
        "message": msg,
        "session_id": session_id,
        "model": model
    }
    if symbol:
        payload["symbol"] = symbol

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:5050/api/chat",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        res["duration_s"] = round(time.time() - t0, 2)
        return res

log("====================================================================")
log(" TEST 1: Broad Market Trends ('what is the recent trends in the market')")
log("====================================================================")
r1 = query_chat("what is the recent trends in the market")
log(f"Symbol: {r1.get('symbol')}")
log(f"Model Used: {r1.get('model_used')}")
log(f"Duration: {r1.get('duration_s')} s")
log(f"Reply:\n{r1.get('reply', '')[:300]}...\n")
assert "could not locate quantitative" not in r1.get("reply", ""), "Should NOT fail with missing data error"

log("====================================================================")
log(" TEST 2: Meta Instruction ('use 7b parameter model')")
log("====================================================================")
r2 = query_chat("use 7b parameter model")
log(f"Reply:\n{r2.get('reply')}")
assert "Switched Active Model Engine" in r2.get("reply", ""), "Should acknowledge model switch"

log("====================================================================")
log(" TEST 3: Earnings & Future Planning ('Recent earnings and their future planning of Reliance')")
log("====================================================================")
r3 = query_chat("Recent earnings and their future planning of Reliance")
log(f"Symbol: {r3.get('symbol')}")
log(f"Duration: {r3.get('duration_s')} s")
log(f"Reply:\n{r3.get('reply')}")
assert not r3.get("reply", "").endswith("operating"), "Response should not cut off at 'operating'"

log("\n====================================================================")
log(" TEST 4: Multi-Turn Memory ('current cycle of DALBHARAT' -> 'what is the next reversal day for this symbol')")
log("====================================================================")
sess_id = f"dalbharat_test_{int(time.time())}"
t1 = query_chat("current cycle of DALBHARAT", session_id=sess_id)
log(f"Turn 1 (DALBHARAT) Symbol: {t1.get('symbol')}")

t2 = query_chat("what is the next reversal day for this symbol", session_id=sess_id)
log(f"Turn 2 ('this symbol') Resolved Symbol: {t2.get('symbol')}")
log(f"Turn 2 Reply:\n{t2.get('reply')}")
assert t2.get("symbol") == "DALBHARAT", f"Expected DALBHARAT, got {t2.get('symbol')}"
assert "could not locate quantitative" not in t2.get("reply", ""), "Should resolve DALBHARAT successfully"

log("\n====================================================================")
log(" TEST 5: Model Switch Parameter ('qwen2.5:7b' vs 'finance-13b')")
log("====================================================================")
m1 = query_chat("What is the LTP of TCS?", model="qwen2.5:7b")
log(f"Requested qwen2.5:7b -> Model Used: {m1.get('model_used')}")

m2 = query_chat("What is the LTP of TCS?", model="finance-13b")
log(f"Requested finance-13b -> Model Used: {m2.get('model_used')}")

log("\n>>> ALL TEST VERIFICATIONS COMPLETED SUCCESSFULLY! <<<")
