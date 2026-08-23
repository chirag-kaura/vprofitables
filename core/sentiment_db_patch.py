"""
sentiment_db_patch.py — One-time DB optimization for v3.8
Run once: python sentiment_db_patch.py

What it does:
  1. Drops the `url` column from news_sentiment (saves ~40% storage)
     URL is never used in training, scoring, or the UI display.
  2. Trims snippet to 120 chars for existing rows
  3. Runs VACUUM to reclaim freed space
  4. Rebuilds indexes

Run time: ~5-30 seconds depending on DB size.
Safe to re-run: all operations are idempotent.
"""

import sqlite3, os, sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for p in (BASE_DIR, os.path.join(BASE_DIR, "core")):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from core.scheduler import DB_PATH
except ImportError:
    DB_PATH = os.path.join(BASE_DIR, "market_data_v2.db")

if not os.path.exists(DB_PATH):
    print(f"  DB not found: {DB_PATH}")
    sys.exit(1)

before_mb = os.path.getsize(DB_PATH) / 1024 / 1024
print(f"  DB size before: {before_mb:.1f} MB")

conn = sqlite3.connect(DB_PATH, timeout=30)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")

cols = {r[1] for r in conn.execute("PRAGMA table_info(news_sentiment)").fetchall()}
print(f"  Existing columns: {sorted(cols)}")

# ── Step 1: Trim snippets in place ────────────────────────────────────────────
print("  Trimming snippet to 120 chars...")
conn.execute("UPDATE news_sentiment SET snippet = SUBSTR(snippet, 1, 120) WHERE LENGTH(snippet) > 120")
conn.commit()
print("  Done.")

# ── Step 2: Remove url column if present (SQLite needs table rebuild) ─────────
if "url" in cols:
    print("  Removing url column (not used in training)...")
    keep = [c for c in ["id","symbol","headline_hash","skeleton_hash","title",
                         "snippet","source","published_at","fetched_at",
                         "raw_score","label","instrument_type",
                         "market_return_1d","market_return_5d","market_return_20d",
                         "market_label","market_labelled_at","calibrated_score",
                         "prediction_error","model_was_correct"] if c in cols]
    cols_sql = ", ".join(keep)
    conn.execute(f"""
        CREATE TABLE news_sentiment_new AS
        SELECT {cols_sql} FROM news_sentiment
    """)
    # Recreate proper table with constraints
    conn.execute("DROP TABLE news_sentiment")
    conn.execute(f"""
        CREATE TABLE news_sentiment (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol          TEXT NOT NULL,
            headline_hash   TEXT NOT NULL,
            skeleton_hash   TEXT,
            title           TEXT NOT NULL,
            snippet         TEXT DEFAULT '',
            source          TEXT DEFAULT '',
            published_at    TEXT DEFAULT '',
            fetched_at      TEXT NOT NULL,
            raw_score       REAL NOT NULL,
            label           TEXT NOT NULL DEFAULT 'NEUTRAL',
            instrument_type TEXT DEFAULT 'EQUITY',
            market_return_1d  REAL DEFAULT NULL,
            market_return_5d  REAL DEFAULT NULL,
            market_return_20d REAL DEFAULT NULL,
            market_label      TEXT DEFAULT NULL,
            market_labelled_at TEXT DEFAULT NULL,
            calibrated_score  REAL DEFAULT NULL,
            prediction_error  REAL DEFAULT NULL,
            model_was_correct INTEGER DEFAULT NULL,
            UNIQUE(symbol, headline_hash)
        )
    """)
    conn.execute(f"INSERT OR IGNORE INTO news_sentiment ({cols_sql}) SELECT {cols_sql} FROM news_sentiment_new")
    conn.execute("DROP TABLE news_sentiment_new")
    conn.commit()
    print("  url column removed.")
else:
    print("  url column already absent — skipping.")

# ── Step 3: Rebuild indexes ───────────────────────────────────────────────────
print("  Rebuilding indexes...")
for sql in [
    "CREATE INDEX IF NOT EXISTS idx_ns_symbol    ON news_sentiment(symbol)",
    "CREATE INDEX IF NOT EXISTS idx_ns_published ON news_sentiment(published_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_ns_fetched   ON news_sentiment(fetched_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_ns_score     ON news_sentiment(raw_score)",
    "CREATE INDEX IF NOT EXISTS idx_ns_mkt_label ON news_sentiment(symbol, market_label)",
    "CREATE INDEX IF NOT EXISTS idx_ns_sym_pub   ON news_sentiment(symbol, published_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_ns_skeleton  ON news_sentiment(symbol, skeleton_hash)",
]:
    conn.execute(sql)
conn.commit()

# ── Step 4: VACUUM ────────────────────────────────────────────────────────────
print("  Running VACUUM (reclaims free pages)...")
conn.execute("VACUUM")
conn.close()

after_mb = os.path.getsize(DB_PATH) / 1024 / 1024
print(f"\n  DB size after : {after_mb:.1f} MB")
print(f"  Space saved   : {before_mb - after_mb:.1f} MB  ({(1 - after_mb/before_mb)*100:.0f}%)")
print(f"  Done.")
