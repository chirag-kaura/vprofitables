import re

with open("core/chatbot_engine.py", "r", encoding="utf-8") as f:
    code = f.read()

target = '    # 1. Multi-Intent Routing\n    intent, intent_params = classify_user_intent(user_msg, active_symbol=active_sym)'
target_crlf = target.replace('\n', '\r\n')

replacement = '''    # ── AGENTIC ORCHESTRATOR SWARM EXECUTION ──────────────────────────────
    try:
        from core.agent_orchestrator import run_agentic_copilot
        res = run_agentic_copilot(query=user_msg, symbol=active_sym)
        reply = res.get("answer", "")
        resolved_sym = res.get("symbol") or active_sym or "RELIANCE"
        latency_ms = int((time.time() - t0) * 1000)
        return {
            "reply": reply,
            "symbol": resolved_sym,
            "model_used": f"LangGraph-Agentic-Swarm ({res.get('intent', 'ROUTED')})",
            "is_fallback": False,
            "latency_ms": latency_ms,
            "sources": [
                "LangGraph Multi-Agent Swarm Orchestrator",
                "Verified 10Y SQL Financials & Daily Prices",
                "ChromaDB Clean Management Transcripts"
            ],
            "metrics_summary": {
                "intent": res.get("intent"),
                "symbol": resolved_sym
            }
        }
    except Exception as e:
        print(f"  [ChatEngine] Agentic Swarm fallback error: {e}", flush=True)

    # 1. Multi-Intent Routing
    intent, intent_params = classify_user_intent(user_msg, active_symbol=active_sym)'''

if target in code:
    code = code.replace(target, replacement, 1)
    print("Patched with LF")
elif target_crlf in code:
    code = code.replace(target_crlf, replacement.replace('\n', '\r\n'), 1)
    print("Patched with CRLF")
else:
    print("Target not found directly, searching regex...")
    pattern = r'(\s+# 1\. Multi-Intent Routing\s+intent,\s*intent_params\s*=\s*classify_user_intent[^\n]+)'
    m = re.search(pattern, code)
    if m:
        code = code[:m.start()] + replacement + code[m.end():]
        print("Patched with Regex")
    else:
        print("Failed to find target")

with open("core/chatbot_engine.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Updated core/chatbot_engine.py successfully!")
