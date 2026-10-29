import sqlite3

conn = sqlite3.connect('market_data_v2.db')
c = conn.cursor()
c.execute("SELECT id, portfolio_id, symbol, shares, entry_price, status FROM positions WHERE status='OPEN'")
print("All OPEN positions:")
for r in c.fetchall():
    print(r)

c.execute("SELECT id, user_id, name FROM portfolios")
print("All Portfolios:")
for r in c.fetchall():
    print(r)
