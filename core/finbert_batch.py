"""
finbert_batch.py — Nightly FinBERT scorer for news headlines
Runs AFTER ingestion, not during. Batches headlines for CPU efficiency.
"""
import sys, os, sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.paths import DB_PATH

_pipe = None

def _get_pipe():
    global _pipe
    if _pipe is None:
        try:
            from transformers import pipeline
            _pipe = pipeline(
                "text-classification",
                model="ProsusAI/finbert",
                device=-1,        # CPU
                batch_size=16,    # process in batches
                truncation=True,
                max_length=128
            )
        except Exception as e:
            print(f"  [FINB ] Could not load FinBERT pipeline: {e}", flush=True)
            _pipe = None
    return _pipe

def score_unprocessed_headlines(limit: int = 500) -> int:
    """Score headlines where finbert_prob_bullish IS NULL."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id, title, snippet FROM news_sentiment
        WHERE finbert_prob_bullish IS NULL
        ORDER BY fetched_at DESC LIMIT ?
    """, (limit,)).fetchall()

    if not rows:
        print("  [FINB ] No unscored headlines pending.", flush=True)
        conn.close()
        return 0

    pipe = _get_pipe()
    if pipe is None:
        conn.close()
        return 0

    texts = [(r["title"] + " " + (r["snippet"] or ""))[:200] for r in rows]
    ids   = [r["id"] for r in rows]

    print(f"  [FINB ] Scoring {len(texts)} headlines with FinBERT (batch_size=16)...", flush=True)

    try:
        results = pipe(texts)
    except Exception as e:
        print(f"  [FINB ] Error during batch inference: {e}", flush=True)
        conn.close()
        return 0

    updates = []
    for row_id, res in zip(ids, results):
        lbl   = res.get("label", "")
        score = float(res.get("score", 0.5))
        if   lbl == "positive": fb_prob = score
        elif lbl == "negative": fb_prob = 1.0 - score
        else:                   fb_prob = 0.5
        updates.append((round(fb_prob, 4), row_id))

    conn.executemany(
        "UPDATE news_sentiment SET finbert_prob_bullish=? WHERE id=?", updates
    )
    conn.commit()
    conn.close()
    print(f"  [FINB ] Successfully updated {len(updates)} headlines with FinBERT probabilities.", flush=True)
    return len(updates)

if __name__ == "__main__":
    score_unprocessed_headlines()
