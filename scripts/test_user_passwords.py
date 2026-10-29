import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sqlite3
from core.auth import verify_password

conn = sqlite3.connect('market_data_v2.db')
c = conn.cursor()
c.execute("SELECT email, password_hash, role FROM users WHERE email LIKE '%chirag%' OR email LIKE '%admin%'")
rows = c.fetchall()
for email, h, role in rows:
    matches = []
    for test in ['admin', 'admin123', 'Admin@123', 'chirag', 'chirag123', 'vprofitables', '123456', 'password']:
        if h and verify_password(test, h):
            matches.append(test)
    print(f"{email} ({role}) -> matched passwords: {matches}")
