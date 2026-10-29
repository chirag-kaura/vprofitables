with open("pages/page_tools.py", "r", encoding="utf-8") as f:
    c = f.read()

target = '<!-- ═══════════ PAGE: SQ9 ═══════════ -->\n<div class="page" id="page-sq9">\n  <div class="topbar"><h2>SQUARE OF NINE</h2><span class="page-tag">GANN SQ9</span></div>\n  <div class="card">'
target_crlf = '<!-- ═══════════ PAGE: SQ9 ═══════════ -->\r\n<div class="page" id="page-sq9">\r\n  <div class="topbar"><h2>SQUARE OF NINE</h2><span class="page-tag">GANN SQ9</span></div>\r\n  <div class="card">'
replacement = '<!-- ═══════════ PAGE: SQ9 ═══════════ -->\n<div class="page" id="page-sq9">\n  <div class="topbar"><h2>SQUARE OF NINE</h2><span class="page-tag">GANN SQ9</span></div>\n  <div class="card" data-feature-id="gann_sq9_spiral">'
replacement_crlf = '<!-- ═══════════ PAGE: SQ9 ═══════════ -->\r\n<div class="page" id="page-sq9">\r\n  <div class="topbar"><h2>SQUARE OF NINE</h2><span class="page-tag">GANN SQ9</span></div>\r\n  <div class="card" data-feature-id="gann_sq9_spiral">'

if target in c:
    c = c.replace(target, replacement, 1)
elif target_crlf in c:
    c = c.replace(target_crlf, replacement_crlf, 1)

with open("pages/page_tools.py", "w", encoding="utf-8") as f:
    f.write(c)
print("Updated page_tools.py!")
