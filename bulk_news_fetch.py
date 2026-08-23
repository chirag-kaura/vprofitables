"""
bulk_news_fetch.py — Bulk news fetcher for all instruments → market_data_v2.db
Place in:  (project root, same level as app.py)
Run:       python bulk_news_fetch.py
Schedule:  Run daily via Windows Task Scheduler or add to START.bat

What it does:
  1. Fetches Yahoo Finance news + Google News RSS for every symbol
  2. Validates headline RELEVANCE — rejects off-topic articles
  3. Deduplicates — same headline can appear for multiple symbols;
     only stored once per (symbol, headline_hash)
  4. Saves everything to news_sentiment table in market_data_v2.db
  5. Prints a detailed report showing counts, scores, and any issues

After running:
  - You'll have 500-1000 headlines in the DB ready for model training
  - Run again daily to keep data fresh
  - Run: python core/train_sentiment_model.py  to train the model
"""

import sys
import os
import time
import re
from datetime import datetime, timedelta

# ── Path setup ────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
CORE_DIR  = os.path.join(BASE_DIR, "core")
DATA_DIR  = os.path.join(BASE_DIR, "data")
# Add both project root and core/ so imports work from any working directory
for _p in (BASE_DIR, CORE_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Direct imports now that sys.path is set — no try/except needed
# These will always resolve because CORE_DIR is in sys.path above
import importlib as _il
_se  = _il.import_module("sentiment_external")
_sdb = _il.import_module("sentiment_db")
_fetch_yahoo_fn         = _se._fetch_yahoo
_fetch_google_fn        = _se._fetch_google
_fetch_yahoo_async_fn   = _se._fetch_yahoo_async
_fetch_google_async_fn  = _se._fetch_google_async
_make_hl_fn             = _se._make_hl
_save_headlines_fn      = _sdb.save_headlines
_save_headlines_batch_fn = _sdb.save_headlines_batch
_init_tables_fn         = _sdb.init_sentiment_tables
_get_stats_fn           = _sdb.get_stats
_get_training_fn        = _sdb.get_training_data
_get_gaps_fn            = _sdb.get_fetch_gaps
_hash_fn                = _sdb._hash
_sdb_ref                = _sdb

# ── Dynamic instruments loading ───────────────────────────────────────────────
from data.instruments import ALL_INSTRUMENTS

# Default keywords for core instruments to maintain exact original logic:
CORE_KEYWORDS = {
    "NIFTY50": ["nifty","sensex","nse","bse","market","index","equity","stock market"],
    "BANKNIFTY": ["bank nifty","banknifty","banking sector","nse bank","bank index"],
    "NIFTYIT": ["nifty it","it index","tech sector","information technology","it stocks"],
    "NIFTYPHARMA": ["nifty pharma","pharma index","pharma sector","pharmaceutical stocks"],
    "NIFTYAUTO": ["nifty auto","auto index","automobile sector","auto stocks"],
    "HDFCBANK": ["hdfc bank","hdfcbank","hdfc","housing development finance"],
    "ICICIBANK": ["icici bank","icicibank","icici"],
    "SBIN": ["sbi","state bank","sbin","state bank of india"],
    "AXISBANK": ["axis bank","axisbank"],
    "KOTAKBANK": ["kotak","kotak bank","kotak mahindra"],
    "TCS": ["tcs","tata consultancy","tata consulting"],
    "INFY": ["infosys","infy","infosy"],
    "WIPRO": ["wipro"],
    "HCLTECH": ["hcl tech","hcltech","hcl technologies"],
    "TECHM": ["tech mahindra","techm"],
    "RELIANCE": ["reliance","ril","mukesh ambani","jio","reliance industries"],
    "ONGC": ["ongc","oil natural gas","oil and natural gas"],
    "NTPC": ["ntpc","national thermal power"],
    "POWERGRID": ["power grid","powergrid"],
    "COALINDIA": ["coal india","coalindia"],
    "HINDUNILVR": ["hindustan unilever","hul","hindunilvr","unilever india"],
    "ITC": ["itc","itc ltd","itc limited"],
    "SUNPHARMA": ["sun pharma","sunpharma","sun pharmaceutical"],
    "DRREDDY": ["dr reddy","drreddy","dr. reddy"],
    "CIPLA": ["cipla"],
    "MARUTI": ["maruti","maruti suzuki","msil"],
    "BAJAJ-AUTO": ["bajaj auto","bajaj-auto"],
    "M&M": ["mahindra","m&m","m and m"],
    "TATAMOTORS": ["tata motors","tatamotors"],
    "TATASTEEL": ["tata steel","tatasteel"],
    "HINDALCO": ["hindalco","hindalco industries"],
    "ULTRACEMCO": ["ultratech","ultracemco","ultratech cement"],
    "BAJFINANCE": ["bajaj finance","bajfinance"],
    "HDFCLIFE": ["hdfc life","hdfclife"],
    "SBILIFE": ["sbi life","sbilife"],
    "GOLD": ["gold","mcx gold","gold price","bullion"],
    "SILVER": ["silver","mcx silver","silver price"],
    "CRUDEOIL": ["crude oil","crude","oil price","brent","wti"],
    "NATURALGAS": ["natural gas","gas price","mcx gas"],
    "COPPER": ["copper","mcx copper","copper price"],
}

INSTRUMENTS = []
for sym, inst in ALL_INSTRUMENTS.items():
    if sym in CORE_KEYWORDS:
        keywords = CORE_KEYWORDS[sym]
    else:
        keywords = [sym.lower(), inst.name.lower()]
        words = re.split(r'\W+', inst.name.lower())
        for w in words:
            if len(w) >= 3 and w not in {"ltd", "limited", "india", "corp", "corporation", "industries", "holdings", "bank", "co", "company"}:
                keywords.append(w)
        keywords = list(dict.fromkeys(keywords))
        
    INSTRUMENTS.append((
        sym,
        inst.yfinance_symbol,
        inst.name,
        inst.instrument_type,
        inst.sector,
        keywords
    ))# ── Relevance checker with NER Rescue (Fix 6) ─────────────────────────────────
_nlp = None
def _get_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        except Exception:
            _nlp = None
    return _nlp


def _ner_matches_instrument(ent_text, symbol, company_name):
    ent_lower = ent_text.lower().strip()
    sym_lower = symbol.lower().strip()
    co_lower = company_name.lower().strip()
    
    if len(ent_lower) < 2:
        return False
        
    if ent_lower == sym_lower or ent_lower == co_lower:
        return True
    if ent_lower in co_lower or co_lower in ent_lower:
        generic_words = {"bank", "india", "limited", "ltd", "corp", "corporation", "power", "industries", "steel", "motors", "auto", "finance"}
        if ent_lower in generic_words:
            return False
        return True
        
    # Token-level overlap check for non-generic words
    generic_words = {"bank", "india", "limited", "ltd", "corp", "corporation", "power", "industries", "steel", "motors", "auto", "finance", "board", "share", "stock", "ltd."}
    
    co_tokens = [w for w in re.split(r'\W+', co_lower) if w and w not in generic_words]
    ent_tokens = [w for w in re.split(r'\W+', ent_lower) if w and w not in generic_words]
    
    if sym_lower not in generic_words and re.search(r'\b' + re.escape(sym_lower) + r'\b', ent_lower):
        return True
        
    for ct in co_tokens:
        if len(ct) >= 3 and ct in ent_tokens:
            return True
            
    return False


def check_relevance_with_ner(title, snippet, keywords, symbol, company_name):
    """
    Check if title or snippet is relevant to the instrument.
    First pass: Fast keyword matching.
    Second pass: NER organization extraction (rescues synonyms/abbreviations).
    """
    text = (title + " " + (snippet or "")).lower()
    is_kw_match = any(kw.lower() in text for kw in keywords)
    if is_kw_match:
        return True, False
        
    nlp = _get_nlp()
    if nlp:
        try:
            full_text = title + " " + (snippet or "")
            doc = nlp(full_text)
            orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
            for org in orgs:
                if _ner_matches_instrument(org, symbol, company_name):
                    return True, True  # Rescued!
        except Exception:
            pass
            
    return False, False


def _is_relevant(title, snippet, keywords):
    """Deprecated simple keyword relevance. Kept for legacy compatibility."""
    return check_relevance_with_ner(title, snippet, keywords, "", "")[0]


def _is_duplicate_across_symbols(title, seen_titles):
    """
    Check if this exact title was already saved for a different symbol.
    Used to detect cross-symbol duplicates (same news tagged to 5 symbols).
    """
    key = title.lower().strip()[:80]
    return key in seen_titles


# ── Near-duplicate TF-IDF Cosine Similarity checks (Fix 2) ───────────────────
def parse_date(pub_str):
    if not pub_str:
        return datetime.now().date()
    pub_str = pub_str.strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(pub_str[:19], fmt).date()
        except ValueError:
            continue
    return datetime.now().date()


def _check_near_duplicate(new_title, existing_titles, threshold=0.60):
    if not existing_titles:
        return False
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        
        t_new = new_title.lower().strip()
        t_ex = [t.lower().strip() for t in existing_titles]
        
        vectorizer = TfidfVectorizer(use_idf=False).fit_transform([t_new] + t_ex)
        vectors = vectorizer.toarray()
        new_vector = vectors[0:1]
        existing_vectors = vectors[1:]
        
        similarities = cosine_similarity(new_vector, existing_vectors)[0]
        max_similarity = float(similarities.max())
        if max_similarity >= threshold:
            return True
    except Exception:
        # Fallback to Jaccard overlap
        new_tokens = set(new_title.lower().split())
        for ex in existing_titles:
            ex_tokens = set(ex.lower().split())
            if not new_tokens or not ex_tokens:
                continue
            jaccard = len(new_tokens & ex_tokens) / len(new_tokens | ex_tokens)
            if jaccard >= threshold:
                return True
    return False


def _is_near_duplicate(title, symbol, published_at, conn, current_run_titles, threshold=0.60):
    pub_date = parse_date(published_at)
    start_date = (pub_date - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (pub_date + timedelta(days=1)).strftime("%Y-%m-%d")
    
    existing_titles = []
    if conn:
        try:
            rows = conn.execute("""
                SELECT title FROM news_sentiment
                WHERE symbol = ?
                AND published_at >= ?
                AND published_at <= ?
            """, (symbol, start_date + " 00:00", end_date + " 23:59")).fetchall()
            existing_titles.extend([r["title"] for r in rows])
        except Exception:
            pass
            
    for other_title, other_pub in current_run_titles:
        other_date = parse_date(other_pub)
        if abs((pub_date - other_date).days) <= 1:
            existing_titles.append(other_title)
            
    return _check_near_duplicate(title, existing_titles, threshold=threshold)


# ── Module references (resolved at import time via sys.path above) ────────────
def _import_modules():
    """Return pre-loaded module function references."""
    return (_fetch_yahoo_fn, _fetch_google_fn, _make_hl_fn,
            _save_headlines_fn, _init_tables_fn,
            _fetch_yahoo_async_fn, _fetch_google_async_fn, _save_headlines_batch_fn)


# ── Main bulk fetch ───────────────────────────────────────────────────────────
def bulk_fetch_all(delay_secs=2.0, max_per_symbol=20, verbose=True, force_all=False):
    """
    Incremental fetch -- only fetches news for the missing date range per symbol.
    Smart gap detection:
      - Symbol never fetched  -> searches last 30 days
      - Gap of N days         -> searches last N+2 days (overlap buffer)
      - Already fetched today -> skipped entirely
    """
    _log = print if verbose else lambda *a: None
    _log("=" * 65)
    _log("  GANN-ASTRO -- Incremental News Fetch")
    _log(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    _log("=" * 65)

    try:
        _fetch_yahoo, _fetch_google, _make_hl, save_headlines, init_sentiment_tables, _fetch_yahoo_async, _fetch_google_async, save_headlines_batch = _import_modules()
    except Exception as e:
        _log(f"  ERROR: Could not import modules: {e}")
        return {}

    init_sentiment_tables()

    # ── Gap detection: what does each symbol need? ────────────────────────
    gaps         = _get_gaps_fn(INSTRUMENTS)
    needs_fetch  = [g for g in gaps if g["needs_fetch"] or force_all]
    already_done = [g for g in gaps if not g["needs_fetch"] and not force_all]

    _log(f"  Symbols needing fetch : {len(needs_fetch)}")
    _log(f"  Already up to date    : {len(already_done)}")
    if already_done:
        done_syms = ", ".join(g["symbol"] for g in already_done[:8])
        _log(f"  Skipping              : {done_syms}" + ("..." if len(already_done) > 8 else ""))
    _log()

    results         = {}
    total_new       = 0
    total_fetched   = 0
    total_skipped   = 0
    ner_rescued_count = 0
    seen_titles     = set()

    # Open SQLite connection for near-duplicate check queries
    db_conn = None
    try:
        db_conn = _sdb_ref._conn()
    except Exception as e:
        _log(f"  [WARN ] Failed to open DB connection for dedup check: {e}")

    # Pre-load existing hashes AND skeleton hashes to catch near-duplicates
    try:
        conn = _sdb_ref._conn()
        existing_hashes    = {r[0] for r in conn.execute(
            "SELECT headline_hash FROM news_sentiment").fetchall()}
        existing_skeletons = {r[0] for r in conn.execute(
            "SELECT skeleton_hash FROM news_sentiment WHERE skeleton_hash IS NOT NULL"
        ).fetchall()}
        conn.close()
    except Exception:
        existing_hashes    = set()
        existing_skeletons = set()

    import asyncio
    import httpx
    import time
    import threading

    def run_async(coro):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        
        res = []
        err = []
        def worker():
            try:
                res.append(asyncio.run(coro))
            except Exception as e:
                err.append(e)
        t = threading.Thread(target=worker)
        t.start()
        t.join()
        if err: raise err[0]
        return res[0]

    async def _async_bulk_fetch_all():
        nonlocal ner_rescued_count, total_fetched, total_skipped, total_new
        
        _fetch_yahoo_async, _fetch_google_async, save_headlines_batch = (
            _fetch_yahoo_async_fn, _fetch_google_async_fn, _save_headlines_batch_fn
        )
        
        # Load existing hashes & skeletons
        try:
            conn = _sdb_ref._conn()
            existing_hashes = {r[0] for r in conn.execute(
                "SELECT headline_hash FROM news_sentiment").fetchall()}
            existing_skeletons = {r[0] for r in conn.execute(
                "SELECT skeleton_hash FROM news_sentiment WHERE skeleton_hash IS NOT NULL"
            ).fetchall()}
            conn.close()
        except Exception:
            existing_hashes = set()
            existing_skeletons = set()
            
        sem = asyncio.Semaphore(30)
        batch_to_save = []
        
        async def process_symbol(gap, client):
            nonlocal ner_rescued_count, total_fetched, total_skipped
            sym      = gap["symbol"]
            gap_days = gap["gap_days"]
            last_dt  = gap["last_date"]

            inst = next((r for r in INSTRUMENTS if r[0] == sym), None)
            if not inst:
                return
            _, yf_sym, name, itype, sector, keywords = inst

            # How far back to search
            if gap_days >= 999:
                search_days = 30
                status_str  = "FIRST FETCH (30d)"
            elif gap_days == 0:
                status_str  = "UP TO DATE -- skip"
                return
            else:
                search_days = min(30, gap_days + 2)
                status_str  = f"GAP {gap_days}d"
                
            async with sem:
                t0_sym = time.time()
                yahoo_task = _fetch_yahoo_async(client, yf_sym, n=max_per_symbol)
                google_task = _fetch_google_async(client, name, sym, itype, n=max_per_symbol, days=search_days)
                yh_list, gh_list = await asyncio.gather(yahoo_task, google_task)
                
            dur_fetch = time.time() - t0_sym
            
            raw_headlines = []
            if yh_list:
                for h in yh_list: raw_headlines.append((h, "Yahoo"))
            if gh_list:
                for h in gh_list: raw_headlines.append((h, "Google"))
                
            sym_fetched = len(raw_headlines)
            sym_rejected = 0
            sym_headlines = []
            sym_kept_titles = []
            cutoff_date = (datetime.now() - timedelta(days=search_days)).date()
            
            for h, source_tag in raw_headlines:
                is_relevant, is_rescued = check_relevance_with_ner(
                    h["title"], h.get("snippet", ""), keywords, sym, name
                )
                if not is_relevant:
                    sym_rejected += 1
                    continue
                if is_rescued:
                    ner_rescued_count += 1
                    if verbose:
                        print(f"    [RESCUE] Rescued by NER: '{h['title']}' for {sym}", flush=True)
                        
                # Date filter
                if not force_all and gap_days < 999 and h.get("published"):
                    try:
                        pub = datetime.strptime(h["published"][:10], "%Y-%m-%d").date()
                        if pub < cutoff_date:
                            sym_rejected += 1
                            continue
                    except Exception:
                        pass
                        
                hh = _hash_fn(h["title"])
                sh = _sdb_ref._skeleton_hash(h["title"])
                if hh in existing_hashes:
                    sym_rejected += 1
                    continue
                if sh in existing_skeletons:
                    sym_rejected += 1
                    continue
                title_key = h["title"].lower().strip()[:80]
                if title_key in seen_titles:
                    sym_rejected += 1
                    continue
                    
                # Near-duplicate check within ±1 day window
                if _is_near_duplicate(h["title"], sym, h.get("published"), db_conn, sym_kept_titles, threshold=0.60):
                    sym_rejected += 1
                    if verbose:
                        print(f"    [DEDUP] Skipped near-duplicate headline: '{h['title']}' (vs similar in ±1d window)", flush=True)
                    continue
                    
                seen_titles.add(title_key)
                existing_hashes.add(hh)
                existing_skeletons.add(sh)
                sym_kept_titles.append((h["title"], h.get("published")))
                
                h_to_save = h.copy()
                h_to_save["symbol"] = sym
                h_to_save["instrument_type"] = itype
                sym_headlines.append(h_to_save)
                
            total_fetched += sym_fetched
            total_skipped += sym_rejected
            
            pos = sum(1 for h in sym_headlines if h["score"] >= 0.10)
            neg = sum(1 for h in sym_headlines if h["score"] <= -0.10)
            neut = len(sym_headlines) - pos - neg
            
            if sym_headlines:
                _log(f"  {sym:<14} | {status_str} | fetched:{sym_fetched:<2} | kept:{len(sym_headlines):<2} | [up:{pos} flat:{neut} dn:{neg}] ({dur_fetch:5.2f}s)")
                batch_to_save.extend(sym_headlines)
            else:
                _log(f"  {sym:<14} | {status_str} | No new headlines (fetched:{sym_fetched} skip:{sym_rejected}) ({dur_fetch:5.2f}s)")
                
            results[sym] = {
                "fetched": sym_fetched, "kept": len(sym_headlines),
                "new_rows": 0, "rejected": sym_rejected,
                "gap_days": gap_days, "search_days": search_days
            }

        limits = httpx.Limits(max_keepalive_connections=30, max_connections=60)
        async with httpx.AsyncClient(limits=limits, timeout=10.0) as client:
            await asyncio.gather(*(process_symbol(gap, client) for gap in needs_fetch), return_exceptions=True)
            
        # Run batch database saving
        t0_db = time.time()
        total_new = save_headlines_batch(batch_to_save)
        dur_db = time.time() - t0_db
        _log(f"  [DB   ] Bulk database insert completed in {dur_db*1000:.1f}ms")
        
        # Update new_rows count in results dictionary
        for h in batch_to_save:
            sym = h["symbol"]
            if sym in results:
                results[sym]["new_rows"] += 1

    t_start_pipeline = time.time()
    run_async(_async_bulk_fetch_all())
    
    if db_conn:
        try:
            db_conn.close()
        except Exception:
            pass
            
    _log(f"  Pipeline execution time: {time.time() - t_start_pipeline:.2f}s")

    # ── Summary ───────────────────────────────────────────────────────────
    _log()
    _log("=" * 65)
    _log(f"  INCREMENTAL FETCH COMPLETE")
    _log(f"  Symbols processed     : {len(needs_fetch)}")
    _log(f"  New DB rows           : {total_new}")
    _log(f"  NER rescued headlines : {ner_rescued_count}")
    _log()
    stats    = _get_stats_fn()
    total_db = stats.get("total_headlines", 0)
    _log(f"  DB total headlines : {total_db:,}")
    _log(f"  DB unique symbols  : {stats.get('unique_symbols', 0)}")
    _log(f"  Market labelled    : {stats.get('market_labelled', 0)}")
    _log()

    # ── Step 2: Apply market labels to newly matured headlines ────────────
    # Headlines > 7 days old get their actual price reaction measured
    # This is the ground truth that trains the model
    if total_db >= 50:
        _log("  Applying market labels to matured headlines (>7 days old)...")
        try:
            import importlib.util as _ilu, os as _os
            _mf_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                     "core", "market_feedback.py")
            if _os.path.exists(_mf_path):
                _mf_spec = _ilu.spec_from_file_location("market_feedback", _mf_path)
                _mf_mod  = _ilu.module_from_spec(_mf_spec)
                _mf_spec.loader.exec_module(_mf_mod)
                n_labelled = _mf_mod.apply_market_labels(min_age_days=7, batch_size=300)
                if n_labelled:
                    _log(f"  Market labels applied: {n_labelled} headlines")
                else:
                    _log(f"  Market labels: no new headlines ready yet (<7 days old)")
        except Exception as _mfe:
            _log(f"  Market labelling skipped: {_mfe}")

    # ── Step 3: Update calibrated scores if model exists ──────────────────
    # If market model has been trained, score new headlines with it immediately
    try:
        import importlib.util as _ilu2, os as _os2
        _mf_path2 = _os2.path.join(_os2.path.dirname(_os2.path.abspath(__file__)),
                                   "core", "market_feedback.py")
        _model_all = _os2.path.join(_os2.path.dirname(_os2.path.abspath(__file__)),
                                    "core", "market_model_all.pkl")
        if _os2.path.exists(_mf_path2) and _os2.path.exists(_model_all):
            _mf_spec2 = _ilu2.spec_from_file_location("market_feedback", _mf_path2)
            _mf_mod2  = _ilu2.module_from_spec(_mf_spec2)
            _mf_spec2.loader.exec_module(_mf_mod2)
            # Score any headlines that don't have calibrated_score yet
            import sqlite3 as _sq
            _db = _os2.path.join(_os2.path.dirname(_os2.path.abspath(__file__)), "market_data_v2.db")
            _conn2 = _sq.connect(_db, timeout=5); _conn2.row_factory = _sq.Row
            _unscored = _conn2.execute("""
                SELECT id, symbol, title, snippet FROM news_sentiment
                WHERE calibrated_score IS NULL
                ORDER BY fetched_at DESC LIMIT 200
            """).fetchall()
            _conn2.close()
            if _unscored:
                _log(f"  Scoring {len(_unscored)} headlines with market model...")
                scored = 0
                for row in _unscored:
                    result = _mf_mod2.score_headline(
                        row["title"], row["snippet"] or "", row["symbol"])
                    if result:
                        _sq.connect(_db, timeout=5).execute(
                            "UPDATE news_sentiment SET calibrated_score=?, model_label=? WHERE id=?",
                            (result["calibrated_score"], result["market_label"], row["id"])
                        ).connection.commit()
                        scored += 1
                _log(f"  Calibrated scores updated: {scored} headlines")
    except Exception as _cse:
        pass  # Model not trained yet — normal on first run

    _print_training_readiness(total_db, stats, _log)
    _log("=" * 65)
    return results


def _print_training_readiness(total_db, stats, _log):
    """Print training readiness guidance with accuracy expectations over time."""
    human = stats.get("human_labelled", 0)
    days_of_data = 0
    try:
        conn = _sdb_ref._conn()
        row  = conn.execute("""
            SELECT CAST(julianday('now') - julianday(MIN(DATE(fetched_at))) AS INTEGER)
            FROM   news_sentiment
        """).fetchone()
        conn.close()
        if row and row[0]: days_of_data = int(row[0])
    except Exception:
        pass

    months = days_of_data // 30
    _log(f"  Data age           : {days_of_data} days ({months} month(s))")
    _log()

    if total_db < 200:
        _log(f"  [WEEK 1]  {total_db}/200 rows -- keep running daily fetches")
    elif total_db < 500:
        _log(f"  [MONTH 1] {total_db} rows -- basic model (~70-75% accuracy)")
        _log(f"  Run: python core/train_sentiment_model.py")
    elif total_db < 1500:
        _log(f"  [MONTH 2] {total_db} rows -- good model (~75-82% accuracy)")
        if human >= 20:
            _log(f"  With {human} human labels: ~82-87% accuracy")
        _log(f"  Run: python core/train_sentiment_model.py")
    else:
        _log(f"  [MONTH 3+] {total_db} rows -- strong model (~85-92% accuracy)")
        _log(f"  Run: python core/train_sentiment_model.py")

    if human < 20:
        _log()
        _log(f"  TIP: Add {20-human} human labels for +5-8% accuracy:")
        _log(f"  Run: python bulk_news_fetch.py --labels")


def suggest_labels(min_confidence=0.5, limit=20):
    """
    Print high-confidence headlines that are easy to label manually.
    These are the best candidates to review and confirm/reject.
    """
    samples = _get_training_fn()
    # Find headlines where |score| is high = VADER is confident
    strong = sorted(
        [s for s in samples if abs(s["raw_score"]) >= min_confidence and not s.get("human_label")],
        key=lambda x: abs(x["raw_score"]),
        reverse=True
    )[:limit]

    if not strong:
        print("  No high-confidence unlabelled headlines found.")
        return

    print(f"\n  ── TOP {len(strong)} HIGH-CONFIDENCE HEADLINES TO LABEL ──")
    print(f"  (VADER score ≥ {min_confidence} — easiest to confirm/reject)")
    print()
    for i, s in enumerate(strong):
        sc   = s["raw_score"]
        lbl  = s["label_str"]
        col  = "▲▲" if sc >= 0.35 else "▲" if sc >= 0.10 else "▼▼" if sc <= -0.35 else "▼"
        print(f"  {i+1:>2}. {col} {sc:+.3f} [{s['symbol']:<12}] {s['title'][:70]}")
        print(f"      VADER says: {lbl}  |  Age: {s['age_days']:.0f}d  |  Source: {s.get('published_at','')[:10]}")

    print()
    print("  To label these via SQL (open market_data_v2.db in any SQLite browser):")
    print()
    print("  -- Label 'beats estimates' as BULLISH:")
    print("  UPDATE sentiment_labels")
    print("  SET human_label='BULLISH', labelled_at=datetime('now')")
    print("  WHERE label_source='VADER' AND title LIKE '%beats estimates%';")
    print()
    print("  -- Label crash/panic headlines as STRONGLY BEARISH:")
    print("  UPDATE sentiment_labels")
    print("  SET human_label='STRONGLY BEARISH', labelled_at=datetime('now')")
    print("  WHERE label_source='VADER' AND")
    print("  (title LIKE '%crash%' OR title LIKE '%plunge%' OR title LIKE '%wiped out%');")


# ── Duplicate checker ──────────────────────────────────────────────────────────
def check_duplicates():
    """
    Report any duplicate headlines in the DB.
    Proper dedup should mean zero duplicates, but let's verify.
    """
    DB_PATH = _sdb.DB_PATH

    import sqlite3
    conn = sqlite3.connect(DB_PATH)

    # Check duplicates within same symbol (should be 0 due to UNIQUE constraint)
    intra = conn.execute("""
        SELECT symbol, title, COUNT(*) as cnt
        FROM   news_sentiment
        GROUP  BY symbol, headline_hash
        HAVING COUNT(*) > 1
    """).fetchall()

    # Check same headline across different symbols (expected for broad market news)
    cross = conn.execute("""
        SELECT title, COUNT(DISTINCT symbol) as sym_count, GROUP_CONCAT(symbol) as symbols
        FROM   news_sentiment
        GROUP  BY headline_hash
        HAVING COUNT(DISTINCT symbol) > 1
        ORDER  BY sym_count DESC
        LIMIT  10
    """).fetchall()

    conn.close()

    print(f"\n  ── DUPLICATE CHECK ──")
    print(f"  Intra-symbol duplicates (same headline twice for same symbol): {len(intra)}")
    if intra:
        for row in intra[:5]:
            print(f"    {row[0]}: {row[1][:60]} (×{row[2]})")

    print(f"\n  Cross-symbol appearances (same headline for multiple symbols): {len(cross)}")
    print("  (These are NORMAL for broad market news like 'Sensex falls')")
    if cross:
        for row in cross[:5]:
            print(f"    ×{row[1]} symbols [{row[2]}]: {row[0][:60]}")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Bulk news fetch for GANN-ASTRO")
    parser.add_argument("--delay",   type=float, default=2.0,
                        help="Seconds between symbols (default 2.0)")
    parser.add_argument("--max",     type=int,   default=20,
                        help="Max headlines per symbol (default 20)")
    parser.add_argument("--labels",  action="store_true",
                        help="Show high-confidence headlines to label")
    parser.add_argument("--dupes",   action="store_true",
                        help="Check for duplicate headlines in DB")
    parser.add_argument("--force",   action="store_true",
                        help="Re-fetch even symbols already up to date today")
    parser.add_argument("--trim",    type=int, default=0,
                        help="Delete headlines older than TRIM days (0=keep all)")
    parser.add_argument("--quiet",   action="store_true",
                        help="Suppress non-essential output")
    parser.add_argument("--symbols", nargs="*",
                        help="Only fetch for specific symbols (e.g. --symbols TCS INFY)")
    args = parser.parse_args()

    if args.dupes:
        check_duplicates()
        sys.exit(0)

    if args.labels:
        suggest_labels()
        sys.exit(0)

    # Trim old headlines if requested
    if args.trim > 0:
        try:
            import sqlite3 as _sq, os as _os
            _db = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "market_data_v2.db")
            _c  = _sq.connect(_db, timeout=5)
            # Keep market-labelled rows always — they're training data
            n = _c.execute("""
                DELETE FROM news_sentiment
                WHERE market_label IS NULL
                AND julianday('now') - julianday(fetched_at) > ?
            """, (args.trim,)).rowcount
            _c.commit(); _c.close()
            print(f"  Trimmed {n} old unlabelled headlines (>{args.trim} days)")
        except Exception as e:
            print(f"  Trim failed: {e}")

    # Filter symbols if requested
    if args.symbols:
        wanted = {s.upper() for s in args.symbols}
        filtered = [row for row in INSTRUMENTS if row[0] in wanted]
        print(f"  Fetching only: {[r[0] for r in filtered]}")
        INSTRUMENTS = filtered

    bulk_fetch_all(delay_secs=args.delay, max_per_symbol=args.max,
                   verbose=not args.quiet, force_all=args.force)
