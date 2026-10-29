import urllib.request
import re
import subprocess

html = urllib.request.urlopen("http://localhost:5050/").read().decode("utf-8")
scripts = re.findall(r'<script(?:\s+[^>]*)?>(.*?)</script>', html, re.DOTALL)

print(f"Extracted {len(scripts)} inline script blocks from served HTML.")

for i, script_code in enumerate(scripts):
    if not script_code.strip():
        continue
    temp_path = f"temp_script_{i}.js"
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(script_code)
    try:
        res = subprocess.run(["node", "-c", temp_path], capture_output=True, text=True, check=True)
        print(f"Script #{i+1} ({len(script_code):,} chars): SYNTAX OK (0 errors)")
    except subprocess.CalledProcessError as e:
        print(f"Script #{i+1} FAILED with syntax error:\n{e.stderr}")
    finally:
        import os
        if os.path.exists(temp_path):
            os.remove(temp_path)

print("HTML JAVASCRIPT INTEGRITY CHECK COMPLETE!")
