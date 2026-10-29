import os

def patch_app():
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()

    target_start = '        # ── admin/users ──────────────────────────────────────────────'
    target_end = '        # ── all_symbols ──────────────────────────────────────────────'

    idx_start = content.find(target_start)
    idx_end = content.find(target_end)

    if idx_start == -1 or idx_end == -1:
        print("Error: Target blocks not found!")
        return False

    new_block = '''        # ── features/locks ──────────────────────────────────────────────
        if ep == "features/locks":
            from core.personalization_db import get_db_connection
            conn = get_db_connection()
            try:
                rows = conn.execute("SELECT feature_id, feature_name, page, category, min_role, is_locked_for_free, description FROM feature_access_rules").fetchall()
                locks_map = {}
                rules_list = []
                for r in rows:
                    d = dict(r)
                    locks_map[d["feature_id"]] = {
                        "locked": bool(d["is_locked_for_free"]),
                        "min_role": d["min_role"],
                        "name": d["feature_name"],
                        "page": d["page"]
                    }
                    rules_list.append(d)
                return {"ok": True, "locks": locks_map, "rules": rules_list}
            finally:
                conn.close()

        # ── admin/users ──────────────────────────────────────────────
        if ep == "admin/users":
            if not self.current_user or self.current_user.get("role") != "ADMIN":
                raise Exception("Access denied: Administrator privileges required.")
            
            from core.personalization_db import get_db_connection
            conn = get_db_connection()
            try:
                users = conn.execute("SELECT id, email, display_name, auth_method, role, created_at FROM users ORDER BY created_at DESC").fetchall()
                user_list = []
                role_counts = {"FREE": 0, "PREMIUM": 0, "ELITE": 0, "ADMIN": 0}
                for u in users:
                    ud = dict(u)
                    r = ud.get("role")
                    if r in ("USER", None, ""):
                        r = "FREE"
                    ud["role"] = r
                    role_counts[r] = role_counts.get(r, 0) + 1
                    user_list.append(ud)
                
                # Fetch system stats too
                inst_cnt = conn.execute("SELECT COUNT(*) FROM instruments").fetchone()[0]
                prices_cnt = conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
                try:
                    intraday_cnt = conn.execute("SELECT COUNT(*) FROM intraday_15m").fetchone()[0]
                except Exception:
                    intraday_cnt = 0
                try:
                    signals_cnt = conn.execute("SELECT COUNT(*) FROM forward_signals").fetchone()[0]
                except Exception:
                    signals_cnt = 0
                try:
                    tracker_cnt = conn.execute("SELECT COUNT(*) FROM tracker_bucket").fetchone()[0]
                except Exception:
                    tracker_cnt = 0
                try:
                    recs_cnt = conn.execute("SELECT COUNT(*) FROM recommendations").fetchone()[0]
                except Exception:
                    recs_cnt = 0

                # Fetch all feature access rules for admin control panel
                features = [dict(f) for f in conn.execute("SELECT feature_id, feature_name, page, category, min_role, is_locked_for_free, description, updated_at FROM feature_access_rules ORDER BY page, feature_name").fetchall()]
                
                # DB size calculation
                db_size_mb = 0
                try:
                    if os.path.exists("market_data_v2.db"):
                        db_size_mb = round(os.path.getsize("market_data_v2.db") / (1024 * 1024), 2)
                except Exception:
                    pass

                return {
                    "users": user_list,
                    "features": features,
                    "stats": {
                        "total_users": len(user_list),
                        "role_counts": role_counts,
                        "instruments": inst_cnt,
                        "daily_prices": prices_cnt,
                        "intraday_bars": intraday_cnt,
                        "signals": signals_cnt,
                        "tracked_trades": tracker_cnt,
                        "recommendations": recs_cnt,
                        "db_size_mb": db_size_mb,
                        "engine_status": "ONLINE",
                        "wal_mode": "ACTIVE"
                    }
                }
            finally:
                conn.close()

        # ── admin/update_role ────────────────────────────────────────
        if ep == "admin/update_role":
            if not self.current_user or self.current_user.get("role") != "ADMIN":
                raise Exception("Access denied: Administrator privileges required.")
            
            target_user_id = p.get("user_id")
            new_role = (p.get("role") or "").upper()
            if new_role == "USER":
                new_role = "FREE"
            if not target_user_id or new_role not in ["FREE", "PREMIUM", "ELITE", "ADMIN"]:
                raise Exception("Invalid request parameters.")
                
            from core.personalization_db import get_db_connection
            conn = get_db_connection()
            try:
                # Prevent self-demotion or demoting master admin
                target_user = conn.execute("SELECT id, email, role FROM users WHERE id=?", (target_user_id,)).fetchone()
                if not target_user:
                    raise Exception("Target user not found.")
                
                admin_email = os.environ.get("ADMIN_EMAIL", "chiragkaura@gmail.com").strip().lower()
                if target_user["email"].lower() == admin_email and new_role != "ADMIN":
                    raise Exception("Master administrator account cannot be demoted.")
                if target_user_id == self.current_user["user_id"] and new_role != "ADMIN":
                    raise Exception("You cannot demote yourself.")
                    
                conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, target_user_id))
                conn.commit()
                return {"ok": True, "user_id": target_user_id, "role": new_role}
            finally:
                conn.close()

        # ── admin/toggle_feature_lock ─────────────────────────────────
        if ep == "admin/toggle_feature_lock":
            if not self.current_user or self.current_user.get("role") != "ADMIN":
                raise Exception("Access denied: Administrator privileges required.")
            
            feature_id = p.get("feature_id")
            if not feature_id:
                raise Exception("Missing feature_id parameter.")
            
            from datetime import datetime
            from core.personalization_db import get_db_connection
            conn = get_db_connection()
            try:
                curr = conn.execute("SELECT is_locked_for_free, min_role FROM feature_access_rules WHERE feature_id=?", (feature_id,)).fetchone()
                if not curr:
                    raise Exception(f"Feature '{feature_id}' not found.")
                
                # If lock state is explicitly sent, use it; otherwise toggle
                if "is_locked_for_free" in p:
                    new_locked = 1 if p["is_locked_for_free"] in [1, True, "1", "true"] else 0
                else:
                    new_locked = 0 if curr["is_locked_for_free"] == 1 else 1
                
                new_min_role = p.get("min_role", curr["min_role"])
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                conn.execute("""
                    UPDATE feature_access_rules
                    SET is_locked_for_free = ?, min_role = ?, updated_at = ?
                    WHERE feature_id = ?
                """, (new_locked, new_min_role, now_str, feature_id))
                conn.commit()
                
                return {
                    "ok": True,
                    "feature_id": feature_id,
                    "is_locked_for_free": new_locked,
                    "min_role": new_min_role,
                    "message": f"Feature '{feature_id}' is now {'LOCKED for Free tier' if new_locked else 'UNLOCKED for Free tier'}."
                }
            finally:
                conn.close()

'''
    updated = content[:idx_start] + new_block + content[idx_end:]
    with open("app.py", "w", encoding="utf-8", newline="\r\n") as f:
        f.write(updated)
    print("Successfully patched app.py!")
    return True

if __name__ == "__main__":
    patch_app()
