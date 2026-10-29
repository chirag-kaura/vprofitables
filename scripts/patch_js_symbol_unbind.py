import os

for path in ["pages/_shared.js", "scripts/append_chat_js.py"]:
    if not os.path.exists(path):
        continue
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    # Replace hardcoded window.__vprof_chat_symbol = "RELIANCE"
    c = c.replace('window.__vprof_chat_symbol = "RELIANCE";', 'window.__vprof_chat_symbol = "";')
    c = c.replace('symbol: window.__vprof_chat_symbol || "RELIANCE"', 'symbol: window.__vprof_chat_symbol || ""')

    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print(f"Updated {path}")
