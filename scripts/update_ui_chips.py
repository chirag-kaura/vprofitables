import re

path = 'pages/_html_head.html'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

old_block = """      <div class="vprof-chat-chip" onclick="askQuickPrompt('Which stock has gained most today?')">🚀 Top Gainers</div>
      <div class="vprof-chat-chip" onclick="askQuickPrompt('Compare TCS vs INFY')">⚖️ TCS vs INFY</div>
      <div class="vprof-chat-chip" onclick="askQuickPrompt('What was revenue and net profit in latest FY?')">📊 FY Financials</div>
      <div class="vprof-chat-chip" onclick="askQuickPrompt('What is management forward guidance and capex?')">🎙️ Concall Guidance</div>"""

new_block = """      <div class="vprof-chat-chip" onclick="askQuickPrompt('What are the Gann SQ9 levels and Wyckoff phase for Reliance?')">📐 Gann & Wyckoff</div>
      <div class="vprof-chat-chip" onclick="askQuickPrompt('What does the deep continuation model say about TCS?')">🧠 Deep ML</div>
      <div class="vprof-chat-chip" onclick="askQuickPrompt('What is today Nakshatra and is Reliance aligned?')">🔮 Vedic Astro</div>
      <div class="vprof-chat-chip" onclick="askQuickPrompt('What is Nifty PCR and Max Pain?')">📊 Derivatives PCR</div>
      <div class="vprof-chat-chip" onclick="askQuickPrompt('Compare TCS vs INFY on 5-day gain and 3-year sales growth')">⚖️ TCS vs INFY</div>"""

# Replace CRLF or LF
if old_block.replace("\n", "\r\n") in text:
    text = text.replace(old_block.replace("\n", "\r\n"), new_block.replace("\n", "\r\n"))
    print("Replaced CRLF block successfully")
elif old_block in text:
    text = text.replace(old_block, new_block)
    print("Replaced LF block successfully")
else:
    print("Block not found!")

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
