import sqlite3
import pandas as pd

conn = sqlite3.connect('market_data_v2.db')
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("TABLES:", tables)
for t in tables:
    df = pd.read_sql(f"SELECT * FROM {t} LIMIT 1", conn)
    print(f"\nTable: {t}\nColumns: {list(df.columns)}")
conn.close()
