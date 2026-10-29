def patch_app():
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()

    target = """            try:
                curr = conn.execute("SELECT is_locked_for_free, min_role FROM feature_access_rules WHERE feature_id=?", (feature_id,)).fetchone()
                if not curr:
                    raise Exception(f"Feature '{feature_id}' not found.")
                
                # If lock state is explicitly sent, use it; otherwise toggle
                if "is_locked_for_free" in p:
                    new_locked = 1 if p["is_locked_for_free"] in [1, True, "1", "true"] else 0
                else:
                    new_locked = 0 if curr["is_locked_for_free"] == 1 else 1"""

    target_crlf = target.replace("\n", "\r\n")

    replacement = """            try:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                curr = conn.execute("SELECT is_locked_for_free, min_role FROM feature_access_rules WHERE feature_id=?", (feature_id,)).fetchone()
                if not curr:
                    # Auto-provision dynamic feature rule on the fly
                    feat_name = p.get("feature_name") or feature_id.replace("_", " ").title()
                    feat_page = p.get("page") or (feature_id.split("_")[0] if "_" in feature_id else "general")
                    feat_cat = p.get("category") or "ADVANCED"
                    conn.execute(\"\"\"
                        INSERT INTO feature_access_rules
                        (feature_id, feature_name, page, category, min_role, is_locked_for_free, description, updated_at)
                        VALUES (?, ?, ?, ?, 'PREMIUM', 0, ?, ?)
                    \"\"\", (feature_id, feat_name, feat_page, feat_cat, f"Dynamic element lock for {feat_name}", now_str))
                    conn.commit()
                    curr = {"is_locked_for_free": 0, "min_role": "PREMIUM"}
                
                # If lock state is explicitly sent, use it; otherwise toggle
                if "is_locked_for_free" in p:
                    new_locked = 1 if p["is_locked_for_free"] in [1, True, "1", "true"] else 0
                else:
                    new_locked = 0 if curr["is_locked_for_free"] == 1 else 1"""

    replacement_crlf = replacement.replace("\n", "\r\n")

    if target in content:
        content = content.replace(target, replacement, 1)
    elif target_crlf in content:
        content = content.replace(target_crlf, replacement_crlf, 1)
    else:
        print("Target not found in app.py!")
        return False

    with open("app.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully patched app.py toggle_feature_lock!")
    return True

if __name__ == "__main__":
    patch_app()
