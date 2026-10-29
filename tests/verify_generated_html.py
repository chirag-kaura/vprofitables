import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
import re
import subprocess
import tempfile

html = app.HTML
print(f"HTML generated successfully! Length: {len(html):,} characters")

script_pattern = re.compile(r'<script(?:\s+id=["\']([^"\']+)["\'])?>(.*?)</script>', re.DOTALL)
scripts = script_pattern.findall(html)
print(f"Total script blocks in HTML: {len(scripts)}")

all_ok = True
for sid, scode in scripts:
    if not scode.strip():
        continue
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
        tf.write(scode)
        tf_name = tf.name
    try:
        res = subprocess.run(["node", "--check", tf_name], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"  [FAIL] Script block '{sid}':\n{res.stderr.strip()}")
            all_ok = False
        else:
            print(f"  [PASS] Script block '{sid or 'anonymous'}': OK ({len(scode):,} chars)")
    finally:
        if os.path.exists(tf_name):
            os.remove(tf_name)

print("=" * 65)
print("FINAL HTML VERIFICATION:", "ALL SCRIPT BLOCKS 100% CLEAN!" if all_ok else "ERRORS FOUND!")
print("=" * 65)
if not all_ok:
    sys.exit(1)
