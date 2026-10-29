import re

with open("core/chatbot_engine.py", "r", encoding="utf-8") as f:
    content = f.read()

target = '''    # ── AGENTIC ORCHESTRATOR SWARM EXECUTION ──────────────────────────────
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
        print(f"  [ChatEngine] Agentic Swarm fallback error: {e}", flush=True)'''

replacement = '''    # ── AGENTIC ORCHESTRATOR SWARM EXECUTION ──────────────────────────────
    try:
        from core.agent_orchestrator import run_agentic_copilot
        session_id = params.get("session_id")
        res = run_agentic_copilot(query=user_msg, symbol=active_sym, session_id=session_id)
        reply = res.get("answer", "")
        resolved_sym = res.get("symbol") or active_sym or None
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
        print(f"  [ChatEngine] Agentic Swarm fallback error: {e}", flush=True)'''

if target in content:
    content = content.replace(target, replacement, 1)
    print("Replaced LF")
elif target.replace('\n', '\r\n') in content:
    content = content.replace(target.replace('\n', '\r\n'), replacement.replace('\n', '\r\n'), 1)
    print("Replaced CRLF")
else:
    print("Could not find exact block, using regex...")
    pattern = r'(\s+# ── AGENTIC ORCHESTRATOR SWARM EXECUTION.*?except Exception as e:.*?flush=True\))'
    m = re.search(pattern, content, re.DOTALL)
    if m:
        content = content[:m.start()] + replacement + content[m.end():]
        print("Replaced with regex")
    else:
        print("Regex failed to find block")

with open("core/chatbot_engine.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Finished patching core/chatbot_engine.py")
