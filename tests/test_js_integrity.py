# tests/test_js_integrity.py
"""
Pre-flight integrity test for all frontend JavaScript modules.
Ensures zero-syntax-error guarantees before server launch.
"""
import sys
import os

# Ensure workspace root is in python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.js_guard import validate_all_pages

def main():
    print("=" * 65)
    print("  Vprofitables Frontend JavaScript Integrity Suite")
    print("=" * 65)
    
    results = validate_all_pages()
    failures = []
    
    for r in results:
        mod = r["module"]
        valid = r["valid"]
        msg = r["message"]
        if valid:
            print(f"  [PASS] {mod:<25} OK")
        else:
            print(f"  [FAIL] {mod:<25} {msg}")
            failures.append((mod, msg))
            
    print("=" * 65)
    if failures:
        print(f"  [RESULT] FAILED: {len(failures)} module(s) contained errors.")
        for mod, msg in failures:
            print(f"   - {mod}: {msg}")
        print("=" * 65)
        sys.exit(1)
    else:
        print("  [RESULT] ALL MODULES PASSED (0 Syntax Errors)")
        print("=" * 65)
        sys.exit(0)

if __name__ == "__main__":
    main()
