import os
import re

print("Updating Chat UI Copy in frontend files...")

# Replacement patterns
old_welcome_html = '''        <div class="vprof-msg-bubble">
          <h3>Vprofitables Quant Copilot</h3>
          <p>I analyze <strong>501 Nifty 500 companies</strong> with verified 10-year financials & 54,000+ transcript chunks.</p>
          <p style="color:#00d4ff; font-size:0.72rem; margin-top:4px;">
            🔒 <em>Zero hallucinations: exact figures verified in ₹ Crores. Click any suggestion above or ask anything.</em>
          </p>
        </div>'''

new_welcome_html = '''        <div class="vprof-msg-bubble">
          <h3>Vprofitables Quant Copilot</h3>
          <p>Quantitative terminal copilot for <strong>500+ NSE Equities</strong>. Instant technical screeners & verified audited financials.</p>
          <p style="color:#00d4ff; font-size:0.72rem; margin-top:4px;">
            🔒 <em>Zero hallucinations: exact figures verified in ₹ Crores. Ask for screeners, fundamentals, or concall guidance.</em>
          </p>
        </div>'''

old_suggestions_html = '''    <div id="vprof-chat-suggestions" class="vprof-chat-suggestions">
      <div class="vprof-chat-chip" onclick="askQuickPrompt('What was revenue and net profit in latest FY?')">📊 FY Financials</div>
      <div class="vprof-chat-chip" onclick="askQuickPrompt('What is management forward guidance and capex?')">🎙️ Guidance & Capex</div>
      <div class="vprof-chat-chip" onclick="askQuickPrompt('Summarize debt, cash flow and NPA health')">💰 Debt & Cash Flow</div>
      <div class="vprof-chat-chip" onclick="askQuickPrompt('What are key risks and headwinds?')">⚠️ Key Risks</div>
    </div>'''

new_suggestions_html = '''    <div id="vprof-chat-suggestions" class="vprof-chat-suggestions">
      <div class="vprof-chat-chip" onclick="askQuickPrompt('Which stock has fallen max in last 5 days?')">📉 5D Losers</div>
      <div class="vprof-chat-chip" onclick="askQuickPrompt('Which stock has gained most today?')">🚀 Top Gainers</div>
      <div class="vprof-chat-chip" onclick="askQuickPrompt('Compare TCS vs INFY')">⚖️ TCS vs INFY</div>
      <div class="vprof-chat-chip" onclick="askQuickPrompt('What was revenue and net profit in latest FY?')">📊 FY Financials</div>
      <div class="vprof-chat-chip" onclick="askQuickPrompt('What is management forward guidance and capex?')">🎙️ Concall Guidance</div>
    </div>'''

# 1. Update pages/_html_head.html
head_path = os.path.join("pages", "_html_head.html")
if os.path.exists(head_path):
    with open(head_path, "r", encoding="utf-8") as f:
        content = f.read()
    if old_welcome_html in content:
        content = content.replace(old_welcome_html, new_welcome_html)
        print("Updated welcome bubble in pages/_html_head.html")
    if old_suggestions_html in content:
        content = content.replace(old_suggestions_html, new_suggestions_html)
        print("Updated suggestions chips in pages/_html_head.html")
    with open(head_path, "w", encoding="utf-8") as f:
        f.write(content)

# 2. Update pages/_shared.js
shared_path = os.path.join("pages", "_shared.js")
if os.path.exists(shared_path):
    with open(shared_path, "r", encoding="utf-8") as f:
        content = f.read()
    if old_welcome_html in content:
        content = content.replace(old_welcome_html, new_welcome_html)
        print("Updated welcome bubble in pages/_shared.js")
    if old_suggestions_html in content:
        content = content.replace(old_suggestions_html, new_suggestions_html)
        print("Updated suggestions chips in pages/_shared.js")
    with open(shared_path, "w", encoding="utf-8") as f:
        f.write(content)

# 3. Update scripts/append_chat_html.py
s_html = os.path.join("scripts", "append_chat_html.py")
if os.path.exists(s_html):
    with open(s_html, "r", encoding="utf-8") as f:
        content = f.read()
    if old_welcome_html in content:
        content = content.replace(old_welcome_html, new_welcome_html)
    if old_suggestions_html in content:
        content = content.replace(old_suggestions_html, new_suggestions_html)
    with open(s_html, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated scripts/append_chat_html.py")

# 4. Update scripts/append_chat_js.py
s_js = os.path.join("scripts", "append_chat_js.py")
if os.path.exists(s_js):
    with open(s_js, "r", encoding="utf-8") as f:
        content = f.read()
    if old_welcome_html in content:
        content = content.replace(old_welcome_html, new_welcome_html)
    if old_suggestions_html in content:
        content = content.replace(old_suggestions_html, new_suggestions_html)
    with open(s_js, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated scripts/append_chat_js.py")

print("All frontend files successfully updated!")
