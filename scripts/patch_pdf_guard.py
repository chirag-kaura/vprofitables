with open("core/financial_query.py", "r", encoding="utf-8") as f:
    c = f.read()

old_func = """def is_clean_transcript_chunk(text: str) -> bool:
    \"\"\"Check if a chunk contains substantive operational commentary rather than legal boilerplate.\"\"\"
    if not text or len(text.strip()) < 80:
        return False
    if _BOILERPLATE_REGEX.search(text):
        return False
    return True"""

new_func = """_PDF_BINARY_REGEX = re.compile(
    r"(%PDF-\d|\bendobj\b|\bFlateDecode\b|\bXRef\b|/Filter\b|/Length\b|/Index\b|>>stream\b)",
    re.IGNORECASE
)

def is_clean_transcript_chunk(text: str) -> bool:
    \"\"\"Check if a chunk contains substantive operational commentary rather than legal boilerplate or corrupt binary.\"\"\"
    if not text or len(text.strip()) < 80:
        return False
    # 1. Reject binary PDF stream dumps
    if _PDF_BINARY_REGEX.search(text):
        return False
    # 2. Reject non-printable binary bytes
    printable = sum(1 for ch in text if ch.isprintable() or ch in '\\n\\r\\t ')
    if (printable / len(text)) < 0.92:
        return False
    # 3. Reject regulatory boilerplate
    if _BOILERPLATE_REGEX.search(text):
        return False
    return True"""

old_crlf = old_func.replace("\n", "\r\n")
new_crlf = new_func.replace("\n", "\r\n")

if old_func in c:
    c = c.replace(old_func, new_func)
    print("Replaced LF")
elif old_crlf in c:
    c = c.replace(old_crlf, new_crlf)
    print("Replaced CRLF")
else:
    print("Not found")

with open("core/financial_query.py", "w", encoding="utf-8") as f:
    f.write(c)
