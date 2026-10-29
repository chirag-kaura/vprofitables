import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.paths import DB_PATH

def optimize_indexes():
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    cursor = conn.cursor()

    print("Checking current indexes on intraday_prices...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='intraday_prices'")
    print("intraday_prices indexes:", cursor.fetchall())

    print("Dropping duplicate idx_intra_sym_time if exists...")
    cursor.execute("DROP INDEX IF EXISTS idx_intra_sym_time;")

    print("Creating covering composite indexes...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fs_status_sym ON forward_signals(status, symbol, projected_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tb_status_proj ON tracker_bucket(status, projected_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tel_sym_disp ON tracker_events_log(symbol, dispatched_at DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_sym_fired ON signals(symbol, fired_at DESC);")

    conn.commit()
    print("Indexes successfully updated.")

    cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE name IN ('idx_fs_status_sym', 'idx_tb_status_proj', 'idx_tel_sym_disp', 'idx_signals_sym_fired')")
    print("Created indexes:", cursor.fetchall())

    conn.close()

if __name__ == "__main__":
    optimize_indexes()
