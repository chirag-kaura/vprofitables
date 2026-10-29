import sqlite3
import numpy as np

conn = sqlite3.connect('market_data_v2.db')
c = conn.cursor()

# Get Nifty returns
c.execute("SELECT trade_date, close FROM daily_prices WHERE symbol='NIFTY50' ORDER BY trade_date DESC LIMIT 60")
nifty_data = dict(c.fetchall())

# Get INFY returns
c.execute("SELECT trade_date, close FROM daily_prices WHERE symbol='INFY' ORDER BY trade_date DESC LIMIT 60")
infy_data = dict(c.fetchall())

common_dates = sorted(set(nifty_data.keys()).intersection(set(infy_data.keys())))
print("Common dates:", len(common_dates))
if len(common_dates) > 10:
    n_closes = [nifty_data[d] for d in common_dates]
    s_closes = [infy_data[d] for d in common_dates]
    n_ret = np.diff(n_closes) / n_closes[:-1]
    s_ret = np.diff(s_closes) / s_closes[:-1]
    cov = np.cov(s_ret, n_ret)[0, 1]
    var_n = np.var(n_ret)
    beta = cov / var_n if var_n > 0 else 1.0
    print(f"INFY Beta vs NIFTY50: {beta:.2f}")
