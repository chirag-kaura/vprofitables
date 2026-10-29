import os
import re
import glob

# 1. Patch append_chat_html.py
with open("scripts/append_chat_html.py", "r", encoding="utf-8") as f:
    html_content = f.read()

pattern_html = r'<select id="vprof-chat-symbol-select".*?</select>\s*'
if re.search(pattern_html, html_content, re.DOTALL):
    html_content = re.sub(pattern_html, '', html_content)
    with open("scripts/append_chat_html.py", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("Removed dropdown from scripts/append_chat_html.py")

# 2. Patch append_chat_js.py
with open("scripts/append_chat_js.py", "r", encoding="utf-8") as f:
    js_content = f.read()

# Replace body payload to include session_id and omit sticky symbol
old_payload = r'body:\s*JSON\.stringify\(\{\s*message:\s*msg,\s*symbol:\s*window\.__vprof_chat_symbol\s*\|\|\s*""\s*\}\)'
new_payload = '''body: JSON.stringify({
          message: msg,
          session_id: getChatSessionId()
        })'''

js_content = re.sub(old_payload, new_payload, js_content)

# Add session ID helper
session_helper = '''
  function getChatSessionId() {
    let sid = sessionStorage.getItem("vprof_chat_session_id");
    if (!sid) {
      sid = "sess_" + Math.random().toString(36).substring(2, 12) + "_" + Date.now();
      sessionStorage.setItem("vprof_chat_session_id", sid);
    }
    return sid;
  }
'''

if "function getChatSessionId" not in js_content:
    js_content = js_content.replace('// Helpers', session_helper + '\n  // Helpers', 1)

# Remove select element updates
js_content = re.sub(r'const select = document\.getElementById\("vprof-chat-symbol-select"\);.*?if \(select\) select\.value = [^;]+;', '', js_content, flags=re.DOTALL)
js_content = re.sub(r'async function loadSymbolsCatalog\(\)\s*\{.*?\}\s*', 'async function loadSymbolsCatalog() { /* Deprecated - Zero Dropdown Architecture */ }\n', js_content, flags=re.DOTALL)
js_content = re.sub(r'window\.onChatSymbolChange\s*=\s*function\(sym\)\s*\{.*?\}\s*;', 'window.onChatSymbolChange = function(sym) {};\n', js_content, flags=re.DOTALL)

with open("scripts/append_chat_js.py", "w", encoding="utf-8") as f:
    f.write(js_content)
print("Updated scripts/append_chat_js.py for Zero-Dropdown and session_id")

# 3. Patch pages/_shared.js
if os.path.exists("pages/_shared.js"):
    with open("pages/_shared.js", "r", encoding="utf-8") as f:
        shared_js = f.read()
    shared_js = re.sub(pattern_html, '', shared_js)
    shared_js = re.sub(old_payload, new_payload, shared_js)
    if "function getChatSessionId" not in shared_js:
        shared_js = shared_js.replace('// Helpers', session_helper + '\n  // Helpers', 1)
    shared_js = re.sub(r'const select = document\.getElementById\("vprof-chat-symbol-select"\);.*?if \(select\) select\.value = [^;]+;', '', shared_js, flags=re.DOTALL)
    shared_js = re.sub(r'async function loadSymbolsCatalog\(\)\s*\{.*?\}\s*', 'async function loadSymbolsCatalog() { /* Deprecated */ }\n', shared_js, flags=re.DOTALL)
    shared_js = re.sub(r'window\.onChatSymbolChange\s*=\s*function\(sym\)\s*\{.*?\}\s*;', 'window.onChatSymbolChange = function(sym) {};\n', shared_js, flags=re.DOTALL)
    with open("pages/_shared.js", "w", encoding="utf-8") as f:
        f.write(shared_js)
    print("Updated pages/_shared.js")

# 4. Patch all generated HTML files in pages/
html_files = glob.glob("pages/*.html") + glob.glob("pages/*/*.html")
patched_html_count = 0
for hf in html_files:
    try:
        with open(hf, "r", encoding="utf-8") as f:
            c = f.read()
        if 'id="vprof-chat-symbol-select"' in c:
            c = re.sub(pattern_html, '', c)
            with open(hf, "w", encoding="utf-8") as f:
                f.write(c)
            patched_html_count += 1
    except Exception:
        pass

print(f"Purged dropdown from {patched_html_count} HTML pages in pages/.")
