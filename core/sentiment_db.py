"""
sentiment_db.py — SQLite layer for news sentiment
Part of GANN·ASTRO v3.7

Schema design:
  Store ONLY what cannot be recomputed:
    - The headline itself (title, snippet, source, url, published_at)
    - The VADER raw_score (point-in-time NLP score)
    - Market feedback columns (populated days later from daily_prices)

  Never store:
    - age_days, time_weight, weighted_score  → computed on-the-fly in SQL
    - human_label, model_label, model_score  → obsolete: market IS the label now

  The market-supervised learning loop (market_feedback.py) fills:
    - market_return_1d / 5d / 20d  → actual price reaction
    - market_label                  → ground truth from price (not human)
    - calibrated_score              → model-corrected score post-training
    - prediction_error              → |raw_score - calibrated_score|
    - model_was_correct             → 1/0 direction accuracy

Time-decay (half-life=7d, never stored):
    age_days       = julianday('now') - julianday(published_at)
    time_weight    = exp(-0.09902 * age_days)
    weighted_score = raw_score * time_weight
"""

import sqlite3, hashlib, os, math
from datetime import datetime, timedelta

from core.paths import DB_PATH

# On-the-fly time decay expressions (reused in all queries)
_AGE    = "CAST((julianday('now') - julianday(NULLIF(published_at,''))) AS REAL)"
_WEIGHT = f"exp(-0.09902 * {_AGE})"
_WSCORE = f"(COALESCE(calibrated_score, raw_score) * exp(-0.09902 * {_AGE}))"


def _conn(timeout=10):
    c = sqlite3.connect(DB_PATH, timeout=timeout)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    c.create_function("exp", 1, math.exp)
    c.row_factory = sqlite3.Row
    return c

def _hash(title: str) -> str:
    return hashlib.sha1(title.lower().strip().encode()).hexdigest()[:16]

def _skeleton_hash(title: str) -> str:
    import re as _r
    t = title.lower().strip()
    t = _r.sub(r'\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{4}\b','',t)
    t = _r.sub(r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2},?\s*\d{4}\b','',t)
    t = _r.sub(r'\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\b','',t)
    t = _r.sub(r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}\b','',t)
    t = _r.sub(r'\b\d{1,2}:\d{2}\s*(?:am|pm|ist)?\b','',t,flags=_r.IGNORECASE)
    t = _r.sub(r'\b\w[\w\s]{2,30}?\s+(?:ltd\.?|limited|inc\.?|corp\.?|co\.?|plc)\b','',t,flags=_r.IGNORECASE)
    t = _r.sub(r'\b[A-Z][A-Z0-9\-&]{1,15}\b','',t)
    t = _r.sub(r'\b\d+(?:[.,]\d+)?\s*(?:percent|%|cr|crore|lakh|bn|mn|rs|inr)?\b','',t,flags=_r.IGNORECASE)
    t = _r.sub(r'[;:,\-\|]+',' ',t)
    t = _r.sub(r'\s+',' ',t).strip()
    return hashlib.sha1(t[:70].encode()).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

def init_sentiment_tables():
    """
    Create or migrate to the clean schema.
    Migration removes: age_days, time_weight, weighted_score (derived)
                       human_label, model_label, model_score, model_version (obsolete)
                       market_label_window hardcoded default
    Adds: market feedback columns (all NULL until market_feedback.py runs)
    """
    conn = _conn()
    c    = conn.cursor()

    existing = {row[1] for row in c.execute("PRAGMA table_info(news_sentiment)").fetchall()}
    has_old  = bool(existing) and (
        "weighted_score" in existing or
        "age_days"       in existing or
        "human_label"    in existing
    )

    if has_old:
        print("  [DB   ] news_sentiment: migrating to clean schema...", flush=True)
        _migrate(conn, c, existing)

    # Create table (new install or post-migration)
    c.execute("""
        CREATE TABLE IF NOT EXISTS news_sentiment (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol          TEXT NOT NULL,
            headline_hash   TEXT NOT NULL,
            skeleton_hash   TEXT,
            title           TEXT NOT NULL,
            snippet         TEXT DEFAULT '',
            source          TEXT DEFAULT '',
            url             TEXT DEFAULT '',
            published_at    TEXT DEFAULT '',
            fetched_at      TEXT NOT NULL,
            raw_score       REAL NOT NULL,
            label           TEXT NOT NULL DEFAULT 'NEUTRAL',
            instrument_type TEXT DEFAULT 'EQUITY',
            -- Market feedback (all NULL until market_feedback.py runs)
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

    # Add any missing columns to existing table
    new_cols = [
        ("skeleton_hash",     "TEXT DEFAULT NULL"),
        ("snippet",           "TEXT DEFAULT ''"),
        ("source",            "TEXT DEFAULT ''"),
        ("url",               "TEXT DEFAULT ''"),
        ("market_return_1d",  "REAL DEFAULT NULL"),
        ("market_return_5d",  "REAL DEFAULT NULL"),
        ("market_return_20d", "REAL DEFAULT NULL"),
        ("market_label",      "TEXT DEFAULT NULL"),
        ("market_labelled_at","TEXT DEFAULT NULL"),
        ("calibrated_score",  "REAL DEFAULT NULL"),
        ("prediction_error",  "REAL DEFAULT NULL"),
        ("model_was_correct", "INTEGER DEFAULT NULL"),
    ]
    for col, defn in new_cols:
        if col not in existing:
            try:
                c.execute(f"ALTER TABLE news_sentiment ADD COLUMN {col} {defn}")
                print(f"  [DB   ] news_sentiment: +{col}", flush=True)
            except Exception:
                pass

    # Drop old sentiment_labels if it exists
    if _table_exists(c, "sentiment_labels"):
        c.execute("DROP TABLE sentiment_labels")
        print("  [DB   ] Dropped sentiment_labels (no longer needed)", flush=True)

    # Indexes
    for sql in [
        "CREATE INDEX IF NOT EXISTS idx_ns_symbol    ON news_sentiment(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_ns_published ON news_sentiment(published_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_ns_fetched   ON news_sentiment(fetched_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_ns_score     ON news_sentiment(raw_score)",
        "CREATE INDEX IF NOT EXISTS idx_ns_mkt_label ON news_sentiment(symbol, market_label)",
        "CREATE INDEX IF NOT EXISTS idx_ns_sym_pub   ON news_sentiment(symbol, published_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_ns_skeleton  ON news_sentiment(symbol, skeleton_hash)",
        "CREATE INDEX IF NOT EXISTS idx_ns_sym_fetched ON news_sentiment(symbol, fetched_at DESC)",
    ]:
        c.execute(sql)

    conn.commit()
    conn.close()


def _table_exists(c, name):
    return bool(c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone())


def _migrate(conn, c, existing):
    """Recreate news_sentiment with clean schema, copying only real columns."""
    c.execute("""
        CREATE TABLE IF NOT EXISTS news_sentiment_clean (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol          TEXT NOT NULL,
            headline_hash   TEXT NOT NULL,
            skeleton_hash   TEXT,
            title           TEXT NOT NULL,
            snippet         TEXT DEFAULT '',
            source          TEXT DEFAULT '',
            url             TEXT DEFAULT '',
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

    # Copy only the columns that are in both old and new schema
    keep = ["id","symbol","headline_hash","title","snippet","source","url",
            "published_at","fetched_at","raw_score","label","instrument_type"]
    if "skeleton_hash" in existing:
        keep.append("skeleton_hash")
    # Carry over any market feedback that was already computed
    for col in ["market_return_1d","market_return_5d","market_return_20d",
                "market_label","market_labelled_at","calibrated_score",
                "prediction_error","model_was_correct"]:
        if col in existing:
            keep.append(col)

    cols = ", ".join(keep)
    c.execute(f"""
        INSERT OR IGNORE INTO news_sentiment_clean ({cols})
        SELECT {cols} FROM news_sentiment
    """)
    n = c.execute("SELECT COUNT(*) FROM news_sentiment_clean").fetchone()[0]
    c.execute("DROP TABLE news_sentiment")
    c.execute("ALTER TABLE news_sentiment_clean RENAME TO news_sentiment")
    conn.commit()
    print(f"  [DB   ] Migration complete: {n} rows, clean schema ✓", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# WRITE
# ─────────────────────────────────────────────────────────────────────────────

def save_headlines(symbol: str, headlines: list, instrument_type: str = "EQUITY") -> int:
    """
    Upsert headlines. Stores only immutable facts + VADER label.
    Market feedback columns start NULL — market_feedback.py fills them later.
    """
    if not headlines:
        return 0

    now  = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = _conn()
    c    = conn.cursor()

    try:
        existing_skeletons = {
            r[0] for r in conn.execute(
                "SELECT skeleton_hash FROM news_sentiment "
                "WHERE symbol=? AND skeleton_hash IS NOT NULL", (symbol,)
            ).fetchall()
        }
    except Exception:
        existing_skeletons = set()

    inserted = 0
    for h in headlines:
        title = (h.get("title") or "").strip()
        if not title:
            continue
        hh = _hash(title)
        sh = _skeleton_hash(title)
        if sh in existing_skeletons:
            continue
        existing_skeletons.add(sh)

        try:
            c.execute("""
                INSERT INTO news_sentiment
                    (symbol, headline_hash, skeleton_hash, title, snippet,
                     source, url, published_at, fetched_at,
                     raw_score, label, instrument_type)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(symbol, headline_hash) DO UPDATE SET
                    fetched_at    = excluded.fetched_at,
                    skeleton_hash = excluded.skeleton_hash,
                    snippet = COALESCE(NULLIF(excluded.snippet,''), news_sentiment.snippet),
                    url     = COALESCE(NULLIF(excluded.url,''),     news_sentiment.url)
            """, (
                symbol, hh, sh, title,
                h.get("snippet","")[:300], h.get("source","")[:80],
                h.get("url","")[:500],     h.get("published",""),
                now,
                round(float(h.get("score", 0)), 4),
                h.get("label", "NEUTRAL"),
                instrument_type,
            ))
            inserted += 1
        except Exception as e:
            print(f"  [SENT ] save error [{symbol}]: {e}", flush=True)

    conn.commit()
    conn.close()
    if inserted:
        print(f"  [SENT ] {symbol}: {inserted} new headlines saved", flush=True)
    return inserted


def save_headlines_batch(batch_data: list) -> int:
    """
    Bulk insert or upsert a list of headlines across multiple symbols in a single transaction.
    batch_data: list of dicts, each containing:
      - symbol
      - instrument_type
      - title
      - snippet
      - source
      - url
      - published
      - score
      - label
    """
    if not batch_data:
        return 0

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = _conn()
    c = conn.cursor()

    # Pre-load existing skeleton hashes for all symbols in the batch to avoid duplicates
    symbols = list({x["symbol"] for x in batch_data})
    existing_skeletons = {}
    try:
        # Load existing skeleton hashes for these symbols
        placeholders = ",".join("?" for _ in symbols)
        rows = conn.execute(f"""
            SELECT symbol, skeleton_hash FROM news_sentiment
            WHERE symbol IN ({placeholders}) AND skeleton_hash IS NOT NULL
        """, symbols).fetchall()
        for r in rows:
            sym = r["symbol"]
            sk = r["skeleton_hash"]
            if sym not in existing_skeletons:
                existing_skeletons[sym] = set()
            existing_skeletons[sym].add(sk)
    except Exception:
        pass

    inserted = 0
    tuples_to_insert = []
    
    for h in batch_data:
        sym = h.get("symbol")
        title = (h.get("title") or "").strip()
        if not title or not sym:
            continue
        hh = _hash(title)
        sh = _skeleton_hash(title)
        
        # Check for near-duplicates using skeleton hash
        if sym not in existing_skeletons:
            existing_skeletons[sym] = set()
        if sh in existing_skeletons[sym]:
            continue
        existing_skeletons[sym].add(sh)
        
        tuples_to_insert.append((
            sym, hh, sh, title,
            h.get("snippet", "")[:300], h.get("source", "")[:80],
            h.get("url", "")[:500], h.get("published", ""),
            now,
            round(float(h.get("score", 0)), 4),
            h.get("label", "NEUTRAL"),
            h.get("instrument_type", "EQUITY")
        ))

    if tuples_to_insert:
        try:
            c.executemany("""
                INSERT INTO news_sentiment
                    (symbol, headline_hash, skeleton_hash, title, snippet,
                     source, url, published_at, fetched_at,
                     raw_score, label, instrument_type)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(symbol, headline_hash) DO UPDATE SET
                    fetched_at    = excluded.fetched_at,
                    skeleton_hash = excluded.skeleton_hash,
                    snippet = COALESCE(NULLIF(excluded.snippet,''), news_sentiment.snippet),
                    url     = COALESCE(NULLIF(excluded.url,''),     news_sentiment.url)
            """, tuples_to_insert)
            inserted = c.rowcount if c.rowcount > 0 else len(tuples_to_insert)
        except Exception as e:
            print(f"  [SENT ] Batch save error: {e}", flush=True)

    conn.commit()
    conn.close()
    
    if inserted:
        print(f"  [SENT ] Batch saved: {inserted} headlines saved in one transaction", flush=True)
    return inserted


# ─────────────────────────────────────────────────────────────────────────────
# READ
# ─────────────────────────────────────────────────────────────────────────────

def get_recent_headlines(symbol: str, days: int = 7, limit: int = 30) -> list:
    """
    Recent headlines. Scores: calibrated_score if available, else raw_score.
    weighted_score = effective_score * time_weight — always fresh.
    """
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    conn   = _conn()
    rows   = conn.execute(f"""
        SELECT *,
            {_AGE}    AS age_days,
            {_WEIGHT} AS time_weight,
            {_WSCORE} AS weighted_score,
            COALESCE(calibrated_score, raw_score) AS effective_score
        FROM   news_sentiment
        WHERE  symbol = ?
        AND   (published_at >= ? OR fetched_at >= ?)
        ORDER  BY ABS({_WSCORE}) DESC
        LIMIT  ?
    """, (symbol, cutoff, cutoff, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_training_data(use_market_labels: bool = True) -> list:
    """
    Training data for ML model.
    use_market_labels=True: only returns rows where market_label is known
                            (the ground truth from actual price reaction).
    use_market_labels=False: returns all rows using VADER label as fallback.
    """
    LABEL_INT = {
        "STRONGLY BULLISH": 2, "BULLISH": 1, "NEUTRAL": 0,
        "BEARISH": -1, "STRONGLY BEARISH": -2,
    }
    conn  = _conn()
    where = "WHERE market_label IS NOT NULL" if use_market_labels else ""
    rows  = conn.execute(f"""
        SELECT title, snippet, symbol, raw_score, published_at,
               label AS vader_label, market_label,
               market_return_5d, calibrated_score, prediction_error,
               {_AGE}    AS age_days,
               {_WEIGHT} AS time_weight
        FROM   news_sentiment
        {where}
        ORDER  BY published_at DESC
    """).fetchall()
    conn.close()

    samples = []
    for r in rows:
        r         = dict(r)
        # Ground truth: market_label > vader_label
        final     = r.get("market_label") or r.get("vader_label") or "NEUTRAL"
        label_int = LABEL_INT.get(final.upper(), 0)
        text      = (r["title"] + " " + (r.get("snippet") or "")).strip()

        # Sample weight: bigger price move = stronger signal = higher weight
        ret    = abs(r.get("market_return_5d") or 0)
        weight = round(1.0 + min(ret / 2.0, 3.0), 2)  # 1.0–4.0

        samples.append({
            "text":         text,
            "title":        r["title"],
            "snippet":      r.get("snippet",""),
            "label_int":    label_int,
            "label_str":    final,
            "label_source": "MARKET" if r.get("market_label") else "VADER",
            "raw_score":    r["raw_score"],
            "time_weight":  round(float(r["time_weight"] or 1.0), 4),
            "sample_weight":weight,
            "symbol":       r["symbol"],
            "published_at": r["published_at"],
            "age_days":     round(float(r["age_days"] or 0), 2),
            "market_return_5d": r.get("market_return_5d"),
        })
    return samples


def get_stats() -> dict:
    """Summary stats — single query, no JOINs."""
    conn = _conn()
    try:
        row = conn.execute("""
            SELECT
                COUNT(*)                                            AS total,
                COUNT(DISTINCT symbol)                             AS symbols,
                SUM(CASE WHEN market_label IS NOT NULL THEN 1 END) AS market_labelled,
                SUM(CASE WHEN calibrated_score IS NOT NULL THEN 1 END) AS calibrated,
                SUM(CASE WHEN model_was_correct = 1 THEN 1 END)   AS correct_predictions,
                SUM(CASE WHEN model_was_correct IS NOT NULL THEN 1 END) AS scored_predictions,
                MAX(fetched_at)                                    AS latest_fetch,
                MAX(market_labelled_at)                            AS latest_market_label
            FROM news_sentiment
        """).fetchone()
        row = dict(row)

        label_dist = conn.execute("""
            SELECT label, COUNT(*) AS cnt FROM news_sentiment
            GROUP BY label ORDER BY cnt DESC
        """).fetchall()
        market_dist = conn.execute("""
            SELECT market_label, COUNT(*) AS cnt FROM news_sentiment
            WHERE  market_label IS NOT NULL
            GROUP  BY market_label ORDER BY cnt DESC
        """).fetchall()
        top_syms = conn.execute("""
            SELECT symbol,
                   COUNT(*) AS total,
                   SUM(CASE WHEN market_label IS NOT NULL THEN 1 END) AS labelled
            FROM   news_sentiment
            GROUP  BY symbol ORDER BY total DESC LIMIT 10
        """).fetchall()

        pred_acc = None
        if row["scored_predictions"]:
            pred_acc = round(row["correct_predictions"] / row["scored_predictions"], 3)

        return {
            "total_headlines":   row["total"] or 0,
            "unique_symbols":    row["symbols"] or 0,
            "market_labelled":   row["market_labelled"] or 0,
            "calibrated":        row["calibrated"] or 0,
            "prediction_accuracy": pred_acc,
            "latest_fetch":      row["latest_fetch"] or "—",
            "latest_market_label": row["latest_market_label"] or "—",
            "label_distribution":  [dict(r) for r in label_dist],
            "market_distribution": [dict(r) for r in market_dist],
            "top_symbols":         [dict(r) for r in top_syms],
            "ready_to_train":      (row["market_labelled"] or 0) >= 50,
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()


def get_last_fetch_date(symbol: str = None) -> dict:
    """
    Return the last DATETIME each symbol's news was fetched (not just date).
    Uses MAX(fetched_at) so a 2nd run on the same day fetches news published
    between the 1st and 2nd run, not the whole day again.
    """
    conn = _conn()
    try:
        if symbol:
            row = conn.execute(
                "SELECT MAX(fetched_at) FROM news_sentiment WHERE symbol=?", (symbol,)
            ).fetchone()
            return {symbol: row[0] if row else None}
        else:
            # Optimized with loose index scan using recursive CTE and composite index
            rows = conn.execute("""
                WITH RECURSIVE
                  syms(x) AS (
                     SELECT MIN(symbol) FROM news_sentiment
                     UNION ALL
                     SELECT (SELECT MIN(symbol) FROM news_sentiment WHERE symbol > x)
                     FROM syms WHERE x IS NOT NULL
                  )
                SELECT x AS symbol, (SELECT MAX(fetched_at) FROM news_sentiment WHERE symbol = x) AS last_dt
                FROM syms WHERE x IS NOT NULL
            """).fetchall()
            return {r[0]: r[1] for r in rows}
    except Exception:
        return {}
    finally:
        conn.close()


def get_fetch_gaps(instruments: list) -> list:
    """
    Compute fetch gaps per symbol using full datetime precision.
    gap_days=0  means fetched within the last hour  → skip
    gap_days=0  with last_dt > 1h ago               → needs_fetch=True (intra-day update)
    """
    now   = datetime.now()
    today = now.date()
    last  = get_last_fetch_date()   # returns datetime strings e.g. "2026-04-10 14:32:05"
    gaps  = []
    for inst in instruments:
        sym    = inst[0]
        last_s = last.get(sym)          # full datetime string or None
        gap_days   = 999
        needs_fetch = True
        last_label  = "NEVER"
        if last_s:
            try:
                # Parse as datetime — supports both "YYYY-MM-DD HH:MM:SS" and "YYYY-MM-DD"
                if len(last_s) > 10:
                    last_dt = datetime.strptime(last_s[:19], "%Y-%m-%d %H:%M:%S")
                else:
                    last_dt = datetime.strptime(last_s, "%Y-%m-%d")
                gap_days   = (today - last_dt.date()).days
                hours_ago  = (now - last_dt).total_seconds() / 3600
                # Skip only if fetched within the last 60 minutes
                needs_fetch = hours_ago >= 1.0
                last_label  = last_dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                gap_days    = 999
                needs_fetch = True
        gaps.append({
            "symbol":       sym,
            "last_date":    last_label,
            "gap_days":     gap_days,
            "needs_fetch":  needs_fetch,
        })
    return sorted(gaps, key=lambda x: (x["needs_fetch"], x["gap_days"]), reverse=True)


def get_google_date_param(gap_days: int) -> str:
    return f"when:{max(1, min(30, gap_days + 1))}d"


def get_symbol_sentiment_trend(symbol: str, days: int = 30) -> list:
    """Daily sentiment trend — uses calibrated_score when available."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    conn   = _conn()
    rows   = conn.execute(f"""
        SELECT
            DATE(published_at) AS pub_date,
            AVG({_WSCORE})     AS avg_weighted,
            AVG(COALESCE(calibrated_score, raw_score)) AS avg_effective,
            COUNT(*)           AS article_count,
            SUM(CASE WHEN COALESCE(calibrated_score,raw_score) >=  0.10 THEN 1 ELSE 0 END) AS bull_count,
            SUM(CASE WHEN COALESCE(calibrated_score,raw_score) <= -0.10 THEN 1 ELSE 0 END) AS bear_count,
            SUM(CASE WHEN market_label IS NOT NULL THEN 1 END) AS market_validated
        FROM   news_sentiment
        WHERE  symbol=? AND published_at>=? AND published_at!=''
        GROUP  BY DATE(published_at)
        ORDER  BY pub_date ASC
    """, (symbol, cutoff)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
