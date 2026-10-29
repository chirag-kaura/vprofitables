import re

def parseMarkdown(md):
    html = md
    # Protect valid HTML tags
    # Replace standard characters
    html = html.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # Unescape safe allowed tags
    html = re.sub(r'&lt;(\/?(?:div|button|span|b|strong|em|p|blockquote|table|tr|th|td|ul|li|br|hr)[^&]*)&gt;', r'<\1>', html, flags=re.IGNORECASE)
    # Unescape quotes inside tags
    html = re.sub(r'(<[^>]+?)&quot;', r'\1"', html)
    return html

sample = '<div class="vprof-order-card"><button onclick="window.executePaperTrade(\'TARIL\', 10, 303.9, 290, 340, this)" class="vprof-btn-execute">⚡ Execute</button></div>'
res = parseMarkdown(sample)
print("Parsed HTML:", res)
assert res == sample
print("SUCCESS: HTML tags preserved perfectly!")
