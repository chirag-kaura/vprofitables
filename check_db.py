"""
check_db.py — Database diagnostic tool for GANN·ASTRO v3.9
Run: python check_db.py

Shows exactly what's in market_data_v2.db:
  - Row counts per symbol
  - Date ranges
  - Latest prices
  - Pivot levels
  - DB health stats
"""
import sqlite3, os, sys
from datetime import date

BASE = os.path.dirname(os.path.abspath(__file__))
DB   = os.path.join(BASE, "market_data_v2.db")

if sys.platform == "win32":
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


SEP = "=" * 65

print(SEP)
print("  GANN·ASTRO v3.9 — DATABASE DIAGNOSTIC")
print(SEP)
print(f"  DB path   : {DB}")
print(f"  DB exists : {os.path.exists(DB)}")

if not os.path.exists(DB):
    print("\n  market_data_v2.db not found.")
    print("  Run:  python app.py  to create it and fetch today's prices.")
    print("  Run:  python download_history.py  to download full history.")
    sys.exit(0)

db_mb = os.path.getsize(DB) / 1024 / 1024
print(f"  DB size   : {db_mb:.1f} MB")

conn = sqlite3.connect(DB)
conn.execute("PRAGMA journal_mode=WAL")

# ── daily_prices summary ──────────────────────────────────────────────────
total = conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
syms  = conn.execute("SELECT COUNT(DISTINCT symbol) FROM daily_prices").fetchone()[0]
print(f"\n  daily_prices : {total:,} rows  |  {syms} symbols")

if total == 0:
    print("\n  ⚠  TABLE IS EMPTY")
    print("  Run:  python download_history.py")
else:
    latest = conn.execute("SELECT MAX(trade_date) FROM daily_prices").fetchone()[0]
    oldest = conn.execute("SELECT MIN(trade_date) FROM daily_prices").fetchone()[0]
    print(f"  Date range   : {oldest} → {latest}")

    # Top 20 by row count
    rows = conn.execute("""
        SELECT symbol, COUNT(*) c, MIN(trade_date), MAX(trade_date)
        FROM daily_prices GROUP BY symbol ORDER BY c DESC LIMIT 20
    """).fetchall()

    print(f"\n  TOP 20 SYMBOLS BY HISTORY DEPTH:")
    print(f"  {'SYMBOL':<22} {'ROWS':>7}  {'FROM':<12}  {'TO'}")
    print("  " + "-" * 58)
    for sym, cnt, frm, to in rows:
        print(f"  {sym:<22} {cnt:>7,}  {frm:<12}  {to}")

    # Symbols with only startup data (≤5 rows)
    sparse = conn.execute("""
        SELECT COUNT(DISTINCT symbol) FROM daily_prices
        GROUP BY symbol HAVING COUNT(*) <= 5
    """).fetchall()
    n_sparse = len(sparse)
    n_full   = syms - n_sparse
    print(f"\n  Symbols with full history (>5 rows) : {n_full}")
    print(f"  Symbols with startup data only (≤5)  : {n_sparse}")

    if n_sparse > 0:
        print(f"\n  ⚠  {n_sparse} symbols need download_history.py")
        print(f"  Run:  python download_history.py")
    else:
        print(f"\n  ✓  All symbols have full history loaded")

# ── pivot_levels summary ──────────────────────────────────────────────────
piv_count = conn.execute("SELECT COUNT(*) FROM pivot_levels").fetchone()[0]
piv_syms  = conn.execute("SELECT COUNT(DISTINCT symbol) FROM pivot_levels").fetchone()[0]
print(f"\n  pivot_levels : {piv_count:,} pivots  |  {piv_syms} symbols")

if piv_count > 0:
    source_breakdown = conn.execute("""
        SELECT source, COUNT(*) FROM pivot_levels GROUP BY source
    """).fetchall()
    for src, cnt in source_breakdown:
        print(f"    {src:<15} : {cnt:,}")

# ── Latest prices ────────────────────────────────────────────────────────
print(f"\n  LATEST PRICES (most recent trade date per symbol, first 20):")
latest_rows = conn.execute("""
    SELECT d.symbol, d.trade_date, d.close, d.change_pct
    FROM daily_prices d
    INNER JOIN (
        SELECT symbol, MAX(trade_date) AS max_date
        FROM daily_prices GROUP BY symbol
    ) m ON d.symbol = m.symbol AND d.trade_date = m.max_date
    ORDER BY d.symbol LIMIT 20
""").fetchall()

print(f"  {'SYMBOL':<22} {'DATE':<12}  {'CLOSE':>12}  {'CHG%':>7}")
print("  " + "-" * 58)
for sym, dt, cl, chg in latest_rows:
    arrow = "▲" if (chg or 0) >= 0 else "▼"
    print(f"  {sym:<22} {dt:<12}  {cl:>12,.2f}  {arrow}{abs(chg or 0):>6.2f}%")

# ── WAL mode check ────────────────────────────────────────────────────────
wal = conn.execute("PRAGMA journal_mode").fetchone()[0]
print(f"\n  SQLite journal mode : {wal.upper()}")
if wal.lower() != "wal":
    print("  ⚠  WAL mode not enabled — run download_history.py to enable it")

conn.close()
print(f"\n{SEP}")
