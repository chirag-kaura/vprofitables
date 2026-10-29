import sys
import os
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from core.paths import DB_PATH
from core.auth import hash_password

def setup_admin():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Target admin accounts to normalize & harmonize
    admin_accounts = [
        {"email": "admin@vprofitables.com", "name": "Administrator", "aliases": ["admin"]},
        {"email": "chiragkaura@gmail.com", "name": "Chirag Kaura", "aliases": ["chiragkaura"]},
        {"email": "chiragkaura2003@gmail.com", "name": "Chirag Kaura", "aliases": ["chiragkaura2003"]},
        {"email": "vprofitables@gmail.com", "name": "Vprofitables Admin", "aliases": ["vprofitables"]}
    ]
    
    # We will use "admin123" and also support "admin"
    default_pass = "admin123"
    pwd_hash = hash_password(default_pass)
    now_str = datetime.utcnow().isoformat()
    
    print("Normalizing Admin accounts and setting master credentials...")
    for acc in admin_accounts:
        em = acc["email"]
        name = acc["name"]
        
        row = c.execute("SELECT id, email, role FROM users WHERE LOWER(email)=?", (em.lower(),)).fetchone()
        if not row:
            uid = str(uuid.uuid4())
            print(f"  + Creating admin account: {em} ({name})")
            c.execute("""
                INSERT INTO users (id, email, password_hash, display_name, auth_method, role, created_at)
                VALUES (?, ?, ?, ?, 'password', 'ADMIN', ?)
            """, (uid, em, pwd_hash, name, now_str))
            user_id = uid
        else:
            user_id = row["id"]
            print(f"  * Updating password & role for admin account: {em} (ID: {user_id})")
            c.execute("""
                UPDATE users 
                SET password_hash=?, role='ADMIN', auth_method='password', display_name=?
                WHERE id=?
            """, (pwd_hash, name, user_id))
            
        # Ensure completed risk profile for this admin so they bypass onboarding
        rp = c.execute("SELECT id FROM risk_profiles WHERE user_id=?", (user_id,)).fetchone()
        if not rp:
            rp_id = str(uuid.uuid4())
            print(f"  + Creating completed risk_profile for: {em}")
            c.execute("""
                INSERT INTO risk_profiles (
                    id, user_id, primary_goal, horizon_weights, drawdown_reaction,
                    experience_level, starting_capital, excluded_sectors,
                    max_position_pct, max_sector_pct, onboarding_version,
                    created_at, updated_at
                ) VALUES (
                    ?, ?, 'growth', '{"swing": 40, "short": 30, "long": 30}', 'buy_more',
                    'experienced', 1000000.0, '[]',
                    25.0, 40.0, 1,
                    ?, ?
                )
            """, (rp_id, user_id, now_str, now_str))

    conn.commit()
    conn.close()
    print("Admin credentials and profiles successfully provisioned!")

if __name__ == "__main__":
    setup_admin()
