import sqlite3

conn = sqlite3.connect('market_data_v2.db')
c = conn.cursor()
c.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='positions'")
print("Indexes on positions:")
for row in c.fetchall():
    print(row)
