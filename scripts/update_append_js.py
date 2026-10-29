with open('scripts/append_chat_js.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = 'html = html.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");'
replacement = '''html = html.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    html = html.replace(/&lt;(\/?(?:div|button|span|b|strong|em|p|blockquote|table|tr|th|td|ul|li|br|hr)[^&]*)&gt;/gi, '<$1>');
    html = html.replace(/(<[^>]+?)&quot;/g, '$1"');'''

if target in content:
    content = content.replace(target, replacement, 1)
    with open('scripts/append_chat_js.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated scripts/append_chat_js.py successfully.")
else:
    print("Target already updated or not found.")
