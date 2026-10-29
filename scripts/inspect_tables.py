import sqlite3

conn = sqlite3.connect('market_data_v2.db')
c = conn.cursor()
c.execute("""
    SELECT strike, option_type, oi, volume, ltp 
    FROM option_chain_data 
    WHERE symbol='ADANIENT' 
    ORDER BY oi DESC LIMIT 8
""")
print("ADANIENT top strikes by OI:", c.fetchall())
