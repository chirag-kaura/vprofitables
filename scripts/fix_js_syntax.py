# Fix extra brace in scripts/append_chat_js.py and pages/_shared.js

def fix_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Target pattern: loadSymbolsCatalog() { /* ... */ }\n}
    import re
    p = r'(async function loadSymbolsCatalog\(\)\s*\{[^\}]*\}\s*)\}'
    if re.search(p, content):
        content = re.sub(p, r'\1', content)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Fixed extra brace in {filepath}")
    else:
        print(f"Pattern not found in {filepath}")

fix_file("scripts/append_chat_js.py")
fix_file("pages/_shared.js")
