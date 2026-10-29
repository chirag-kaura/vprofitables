# core/js_guard.py
"""
Vprofitables JavaScript Guard & Architectural Fault-Isolation Engine.

Guarantees zero-paralysis frontend stability:
1. Validates JavaScript syntax of all page modules at server startup.
2. Isolates page modules into independent browser <script> contexts so a failure
   in any single feature module NEVER halts the execution of authentication or
   other pages.
3. Provides automated pre-flight integrity testing.
"""

import os
import sys
import shutil
import subprocess
import tempfile
import json
from typing import Tuple, List, Dict

_NODE_PATH = shutil.which("node")


def _check_braces_python(code: str) -> Tuple[bool, str]:
    """
    Pure-Python token-aware balanced brace, bracket, and parenthesis checker.
    Ignores characters inside single-line comments, block comments, single quotes,
    double quotes, and backtick template literals.
    """
    stack = []
    in_single = False
    in_double = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False
    escaped = False

    i = 0
    line_num = 1
    col_num = 1
    n = len(code)

    while i < n:
        c = code[i]
        if c == '\n':
            line_num += 1
            col_num = 0
            in_line_comment = False
            escaped = False
            i += 1
            col_num += 1
            continue

        if escaped:
            escaped = False
            i += 1
            col_num += 1
            continue

        if c == '\\':
            escaped = True
            i += 1
            col_num += 1
            continue

        if in_line_comment:
            i += 1
            col_num += 1
            continue

        if in_block_comment:
            if c == '*' and i + 1 < n and code[i + 1] == '/':
                in_block_comment = False
                i += 2
                col_num += 2
                continue
            i += 1
            col_num += 1
            continue

        if in_single:
            if c == "'":
                in_single = False
            i += 1
            col_num += 1
            continue

        if in_double:
            if c == '"':
                in_double = False
            i += 1
            col_num += 1
            continue

        if in_backtick:
            if c == '`':
                in_backtick = False
            i += 1
            col_num += 1
            continue

        # Look for comment starts
        if c == '/' and i + 1 < n and code[i + 1] == '/':
            in_line_comment = True
            i += 2
            col_num += 2
            continue
        if c == '/' and i + 1 < n and code[i + 1] == '*':
            in_block_comment = True
            i += 2
            col_num += 2
            continue

        # Look for string starts
        if c == "'":
            in_single = True
            i += 1
            col_num += 1
            continue
        if c == '"':
            in_double = True
            i += 1
            col_num += 1
            continue
        if c == '`':
            in_backtick = True
            i += 1
            col_num += 1
            continue

        # Enclosing tokens
        if c in '{[(':
            stack.append((c, line_num, col_num))
        elif c in '}])':
            if not stack:
                return False, f"Unmatched closing '{c}' at line {line_num}:{col_num}"
            top, tl, tc = stack.pop()
            matches = {'}': '{', ']': '[', ')': '('}
            if matches[c] != top:
                return False, f"Mismatched closing '{c}' at line {line_num}:{col_num} (matches '{top}' from line {tl}:{tc})"

        i += 1
        col_num += 1

    if stack:
        top, tl, tc = stack[-1]
        return False, f"Unclosed '{top}' opened at line {tl}:{tc}"

    return True, "OK"


def validate_js(code: str, module_name: str = "") -> Tuple[bool, str]:
    """
    Validates JavaScript syntax using Node.js if present, or fallback Python token parser.
    """
    if not code or not code.strip():
        return True, "OK"

    if _NODE_PATH:
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
                tf.write(code)
                tf_name = tf.name
            try:
                res = subprocess.run([_NODE_PATH, "--check", tf_name], capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    return True, "OK"
                else:
                    err = res.stderr.strip()
                    # Strip temp file path for cleaner logging
                    if tf_name in err:
                        err = err.replace(tf_name, module_name or "inline_script")
                    return False, err
            finally:
                if os.path.exists(tf_name):
                    try:
                        os.remove(tf_name)
                    except Exception:
                        pass
        except Exception as e:
            # Fall back to python brace check if node fails to invoke
            pass

    return _check_braces_python(code)


def wrap_module_script(module_name: str, code: str) -> str:
    """
    Wraps module JS in its own dedicated, isolated <script> block.
    If the module has a syntax error, it isolates the failure and prints a loud console alert,
    preventing the syntax error from crashing other modules or the auth flow.
    """
    if not code or not code.strip():
        return ""

    is_valid, msg = validate_js(code, module_name)
    safe_id = module_name.replace(".", "_").replace("/", "_").replace("\\", "_")

    if is_valid:
        return f'\n<script id="mod-{safe_id}">\n/* Module: {module_name} */\n{code}\n</script>\n'
    else:
        print(f"\n  [JS GUARD ALERT] Syntax error detected in module '{module_name}':", flush=True)
        print(f"  --> {msg}\n  [JS GUARD] Module '{module_name}' safely isolated to keep system stable.\n", flush=True)
        escaped_err = json.dumps(f"Module '{module_name}' syntax error: {msg}")
        return (
            f'\n<script id="mod-{safe_id}-error">\n'
            f'console.error("Vprofitables JS Guard: Module \'{module_name}\' contains syntax errors and was isolated:", {escaped_err});\n'
            f'</script>\n'
        )


def validate_all_pages(pages_dir: str = "pages") -> List[Dict]:
    """
    Scans all page files and returns a list of results.
    """
    import glob
    results = []

    # Check _shared.js
    shared_path = os.path.join(pages_dir, "_shared.js")
    if os.path.exists(shared_path):
        with open(shared_path, encoding="utf-8") as f:
            code = f.read()
        valid, msg = validate_js(code, "_shared.js")
        results.append({"module": "_shared.js", "valid": valid, "message": msg})

    # Check each page_<name>.py
    for fpath in sorted(glob.glob(os.path.join(pages_dir, "page_*.py"))):
        mname = os.path.basename(fpath)
        try:
            mod = {}
            with open(fpath, encoding="utf-8") as f:
                exec(f.read(), mod)
            js = mod.get("JS", "")
            if js:
                valid, msg = validate_js(js, mname)
                results.append({"module": mname, "valid": valid, "message": msg})
            else:
                results.append({"module": mname, "valid": True, "message": "No JS attribute"})
        except Exception as e:
            results.append({"module": mname, "valid": False, "message": f"Python load error: {e}"})

    return results
