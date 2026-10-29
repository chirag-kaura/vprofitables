import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add chat endpoints to public_endpoints
old_pub = '"features/locks"'
new_pub = '"features/locks",\n            "chat", "chat/status", "chat/suggestions", "chat/symbols"'

if old_pub in content and '"chat"' not in content:
    content = content.replace(old_pub, new_pub, 1)
    print("Added chat endpoints to public_endpoints")

# 2. Add handlers before config
old_config = '        # ── config ───────────────────────────────────────────────────\n        if ep == "config":'
new_config = '''        # ── AI Assistant Chatbot Endpoints ───────────────────────────
        if ep == "chat":
            from core.chatbot_engine import handle_chat_query
            return handle_chat_query(p)

        if ep == "chat/status":
            from core.chatbot_engine import get_chat_status
            return get_chat_status()

        if ep == "chat/suggestions":
            from core.chatbot_engine import get_symbol_suggestions
            sym = p.get("symbol", "RELIANCE")
            return {"suggestions": get_symbol_suggestions(sym)}

        if ep == "chat/symbols":
            from core.chatbot_engine import get_all_symbols_catalog
            return {"symbols": get_all_symbols_catalog()}

        # ── config ───────────────────────────────────────────────────
        if ep == "config":'''

if old_config in content:
    content = content.replace(old_config, new_config, 1)
    print("Added chat handlers before config")
else:
    # Try with CRLF
    old_config_crlf = old_config.replace('\n', '\r\n')
    new_config_crlf = new_config.replace('\n', '\r\n')
    if old_config_crlf in content:
        content = content.replace(old_config_crlf, new_config_crlf, 1)
        print("Added chat handlers before config (CRLF)")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Finished patching app.py")
