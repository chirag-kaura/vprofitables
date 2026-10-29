# scripts/test_live_chat_endpoint.py
import urllib.request
import json
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def send_chat(msg, session_id="live_test_session"):
    data = json.dumps({"message": msg, "session_id": session_id}).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:5050/api/chat",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=35) as resp:
        return json.loads(resp.read().decode("utf-8"))

print("Testing live /api/chat endpoint on http://localhost:5050/api/chat ...")

res1 = send_chat("Analyze TCS")
print("\n[Query: 'Analyze TCS']")
print("Model:", res1.get("model_used"))
print("Symbol:", res1.get("symbol"))
has_chips = "vprof-chat-chip" in res1.get("reply", "")
print("Has Action Chips:", has_chips)
assert has_chips, "Expected action chips in reply"

res2 = send_chat("What is the options microstructure for NIFTY?")
print("\n[Query: 'What is the options microstructure for NIFTY?']")
print("Model:", res2.get("model_used"))
print("Symbol:", res2.get("symbol"))
has_call_wall = "Call Wall" in res2.get("reply", "")
print("Has Call Wall:", has_call_wall)
assert has_call_wall, "Expected options microstructure analysis"

res3 = send_chat("Which stock has fallen max in last 5 days?")
print("\n[Query: 'Which stock has fallen max in last 5 days?']")
print("Model:", res3.get("model_used"))
has_screener_chips = "vprof-chat-chip" in res3.get("reply", "")
print("Has Screener Chips:", has_screener_chips)
assert has_screener_chips, "Expected action chips in screener"

print("\nLive HTTP API Endpoint Verification: 100% SUCCESS!")
