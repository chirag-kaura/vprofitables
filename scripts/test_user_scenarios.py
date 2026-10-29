import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from core.chatbot_engine import handle_chat_query

print("=" * 70)
print("TESTING USER SCENARIO 1: Short term trade 10-15 days")
print("=" * 70)
res1 = handle_chat_query({
    "message": "I am looking for short term trade for 10-15 days can you suggest me what all stocks can i look for and why?",
    "symbol": "RELIANCE"
})
print("Model:", res1.get("model_used"))
print("Symbol:", res1.get("symbol"))
print("Reply preview:")
for l in res1.get("reply", "").split("\n")[:18]:
    print(" ", l)

print("\n" + "=" * 70)
print("TESTING USER SCENARIO 2: Latest updates about Reliance")
print("=" * 70)
res2 = handle_chat_query({
    "message": "Give me latest updates about Reliance",
    "symbol": "RELIANCE"
})
print("Model:", res2.get("model_used"))
print("Symbol:", res2.get("symbol"))
print("Reply preview:")
for l in res2.get("reply", "").split("\n")[:25]:
    print(" ", l)
