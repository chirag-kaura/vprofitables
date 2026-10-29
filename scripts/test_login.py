import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.personalization_db import get_db_connection
from core.auth import verify_password, hash_password, create_access_token

conn = get_db_connection()
query = "SELECT id, email, display_name, password_hash, role FROM users WHERE role='ADMIN' ORDER BY (LOWER(email) LIKE '%admin%') DESC LIMIT 1"
user = conn.execute(query).fetchone()

print("Admin user found:", dict(user) if user else None)
if user:
    pwd_hash = user["password_hash"]
    print("Testing password 'admin123':", verify_password("admin123", pwd_hash))
    print("Testing password 'admin':", verify_password("admin", pwd_hash))
    token = create_access_token(user["id"], user["email"], user["role"])
    print("Generated token:", token[:40] + "...")
