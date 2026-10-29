with open("core/screener_sync.py", "r", encoding="utf-8") as f:
    code = f.read()

target = "            html_hash = hashlib.sha256(res.text.encode('utf-8')).hexdigest()"

replacement = """            # Sync Shareholding Pattern (FII, DII, Promoter Pledging)
            try:
                from core.shareholding_engine import parse_and_store_shareholding
                sh_count = parse_and_store_shareholding(res.text, symbol)
                if sh_count:
                    stats['shareholding_periods'] = sh_count
            except Exception as _she:
                pass

            html_hash = hashlib.sha256(res.text.encode('utf-8')).hexdigest()"""

if target in code:
    code = code.replace(target, replacement, 1)
    with open("core/screener_sync.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("Patched core/screener_sync.py with shareholding pattern ingestion")
else:
    print("Target not found in core/screener_sync.py")
