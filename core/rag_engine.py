"""
rag_engine.py — RAG (Retrieval-Augmented Generation) Engine for GANN·ASTRO v3.9
================================================================================
100% free, 100% local — no API keys, no cloud calls, no cost ever.

What it does
------------
1. Scrapes earnings transcripts/presentations from NSE, BSE, MoneyControl (free)
2. Fetches EPS / earnings calendar from yfinance (already in requirements.txt)
3. Chunks documents by natural boundaries (Q&A turns, section headings)
4. Embeds chunks with sentence-transformers (all-MiniLM-L6-v2, runs on CPU, 83 MB)
5. Stores vectors in ChromaDB (local directory — no server, no Docker)
6. Exposes retrieve(symbol, query, k) for downstream LLM / rule extractor use
7. Exposes nightly_ingest() — called by scheduler every night at 22:00 IST

Install (once):
    pip install sentence-transformers chromadb requests --break-system-packages

The chroma_db/ directory is created next to market_data_v2.db automatically.
"""

import os
import re
import sqlite3
import hashlib
import json
import time
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from urllib.request import urlopen, Request
from urllib.parse import quote_plus, urljoin
from urllib.error import URLError

from core.paths import DB_PATH, BASE_DIR
_DB     = DB_PATH
_CHROMA = os.path.normpath(os.path.join(BASE_DIR, "chroma_db"))

# ── Lazy globals ──────────────────────────────────────────────────────────────
_embedder  = None   # sentence-transformers model (loaded once)
_chroma    = None   # ChromaDB client
_collection = None  # ChromaDB collection

# ── ChromaDB / sentence-transformers availability ─────────────────────────────
def _has_chromadb():
    try:
        import chromadb  # noqa
        return True
    except ImportError:
        return False

def _has_st():
    try:
        from sentence_transformers import SentenceTransformer  # noqa
        return True
    except ImportError:
        return False

RAG_AVAILABLE = _has_chromadb() and _has_st()

# ── SQLite helpers ────────────────────────────────────────────────────────────
def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB, timeout=10)
    c.row_factory = sqlite3.Row
    return c

def init_rag_tables():
    """Create rag_docs table to track ingested document hashes."""
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS rag_docs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT    NOT NULL,
            doc_type    TEXT    NOT NULL,  -- 'transcript','analyst','eps'
            source_url  TEXT,
            doc_hash    TEXT    UNIQUE,    -- SHA-256 prevents re-processing
            chunk_count INTEGER DEFAULT 0,
            ingested_at TEXT    DEFAULT (datetime('now')),
            fiscal_period TEXT             -- 'Q1FY25', 'FY24', etc.
        );
        CREATE TABLE IF NOT EXISTS rag_extractions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol              TEXT NOT NULL,
            fiscal_period       TEXT,
            eps_beat_pct        REAL,      -- actual vs estimate %
            revenue_growth_yoy  REAL,      -- YoY %
            mgmt_tone           REAL,      -- -1.0 to +1.0
            guidance_direction  TEXT,      -- 'raised','lowered','maintained','none'
            key_risks           TEXT,      -- JSON list of strings
            extracted_at        TEXT DEFAULT (datetime('now')),
            extractor_method    TEXT,      -- 'ollama','llama_cpp','rules'
            UNIQUE(symbol, fiscal_period)
        );
        """)
    print("  [RAG] Tables ready.", flush=True)

# ── SHA-256 hash ──────────────────────────────────────────────────────────────
def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()

# ── Lazy embedder loader ──────────────────────────────────────────────────────
def _get_embedder():
    global _embedder
    if _embedder is None:
        if not _has_st():
            raise ImportError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers --break-system-packages"
            )
        from sentence_transformers import SentenceTransformer
        print("  [RAG] Loading embedding model (first run downloads ~83 MB)…", flush=True)
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
        print("  [RAG] Embedding model ready.", flush=True)
    return _embedder

# ── Lazy ChromaDB loader ──────────────────────────────────────────────────────
def _get_collection():
    global _chroma, _collection
    if _collection is None:
        if not _has_chromadb():
            raise ImportError(
                "chromadb not installed. "
                "Run: pip install chromadb --break-system-packages"
            )
        import chromadb
        os.makedirs(_CHROMA, exist_ok=True)
        _chroma = chromadb.PersistentClient(path=_CHROMA)
        _collection = _chroma.get_or_create_collection(
            name="gann_astro_docs",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection

# ── Text cleaning ─────────────────────────────────────────────────────────────
def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)           # strip HTML
    text = re.sub(r"&[a-z]+;", " ", text)           # HTML entities
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def _extract_text_from_pdf_bytes(raw: bytes) -> str:
    """Try pdfplumber then PyMuPDF then naive text fallback."""
    try:
        import pdfplumber, io
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception:
        pass
    try:
        import fitz, io  # PyMuPDF
        doc = fitz.open(stream=raw, filetype="pdf")
        return "\n".join(page.get_text() for page in doc)
    except Exception:
        pass
    # Last resort: naive decode (works for text-layer PDFs)
    return raw.decode("utf-8", errors="replace")

# ══════════════════════════════════════════════════════════════════════════════
# CHUNKING
# ══════════════════════════════════════════════════════════════════════════════

def chunk_transcript(text: str, symbol: str) -> List[Dict]:
    """
    Split an earnings call transcript by Q&A turns.
    Pattern: lines starting with "Q:", "A:", "Operator:", speaker names.
    Falls back to 800-word sliding window with 200-word overlap.
    """
    chunks = []
    # Split on Q&A speaker markers
    turns = re.split(
        r'\n(?=(?:Q\s*:|A\s*:|Operator\s*:|Moderator\s*:|'
        r'Analyst\s*:|Management\s*:|[A-Z][a-z]+\s+[A-Z][a-z]+\s*:))',
        text
    )
    for i, turn in enumerate(turns):
        turn = _clean(turn).strip()
        if len(turn) < 60:
            continue
        chunks.append({
            "text":     turn[:2000],
            "symbol":   symbol,
            "doc_type": "transcript",
            "chunk_id": f"{symbol}_transcript_{i}",
        })
    if not chunks:
        # Sliding window fallback
        words = text.split()
        step, size = 600, 800
        for i in range(0, len(words), step):
            block = " ".join(words[i:i+size])
            if len(block) < 60:
                continue
            chunks.append({
                "text":     block,
                "symbol":   symbol,
                "doc_type": "transcript",
                "chunk_id": f"{symbol}_transcript_sw_{i}",
            })
    return chunks

def chunk_report(text: str, symbol: str, doc_type: str = "analyst") -> List[Dict]:
    """
    Split analyst report / investor presentation by section headings.
    Headings: ALL CAPS lines, numbered sections, underlined lines.
    """
    chunks = []
    # Split on heading patterns
    sections = re.split(
        r'\n(?=[A-Z][A-Z\s]{4,50}\n|'      # ALL CAPS headings
        r'\d+\.\s+[A-Z]|'                   # "1. Financial Highlights"
        r'#{1,3}\s)',                        # Markdown headings
        text
    )
    for i, sec in enumerate(sections):
        sec = _clean(sec).strip()
        if len(sec) < 60:
            continue
        # Sub-chunk long sections (>1200 chars)
        if len(sec) > 1200:
            words = sec.split()
            for j in range(0, len(words), 180):
                block = " ".join(words[j:j+200])
                if len(block) < 40:
                    continue
                chunks.append({
                    "text":     block,
                    "symbol":   symbol,
                    "doc_type": doc_type,
                    "chunk_id": f"{symbol}_{doc_type}_{i}_{j}",
                })
        else:
            chunks.append({
                "text":     sec,
                "symbol":   symbol,
                "doc_type": doc_type,
                "chunk_id": f"{symbol}_{doc_type}_{i}",
            })
    return chunks

# ══════════════════════════════════════════════════════════════════════════════
# DATA FETCHERS  (all free, no API keys)
# ══════════════════════════════════════════════════════════════════════════════

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def _get(url: str, timeout: int = 10) -> Optional[bytes]:
    try:
        req = Request(url, headers={"User-Agent": _UA})
        with urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None

def fetch_nse_filings(symbol: str) -> List[Dict]:
    """
    Fetch investor presentations and quarterly results PDFs from NSE.
    NSE's public XBRL/PDF endpoint — free, no login.
    Returns list of {url, text, fiscal_period, doc_type}.
    """
    docs = []
    # NSE quarterly results PDF index
    nse_sym = symbol.replace("&", "%26")
    url = (f"https://www.nseindia.com/api/corp-info?symbol={nse_sym}"
           f"&market=capital&corpType=announcement&fromDate=&toDate=&search=")
    raw = _get(url)
    if raw:
        try:
            data = json.loads(raw)
            for item in (data.get("data") or [])[:5]:
                att = item.get("attchmnt", "")
                if att and att.endswith(".pdf"):
                    pdf_url = f"https://nsearchives.nseindia.com/{att.lstrip('/')}"
                    pdf_raw = _get(pdf_url, timeout=15)
                    if pdf_raw and len(pdf_raw) > 1000:
                        text = _extract_text_from_pdf_bytes(pdf_raw)
                        if len(text) > 200:
                            docs.append({
                                "url":           pdf_url,
                                "text":          text,
                                "fiscal_period": item.get("period", ""),
                                "doc_type":      "analyst",
                            })
        except Exception:
            pass
    return docs

def fetch_moneycontrol_news(symbol: str, company_name: str) -> List[Dict]:
    """
    Scrape MoneyControl news headlines for analyst commentary.
    Uses Google News RSS (free, no login) scoped to MoneyControl results.
    """
    docs = []
    q    = quote_plus(f'"{company_name}" earnings results site:moneycontrol.com')
    url  = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
    raw  = _get(url)
    if not raw:
        return docs
    text_blob = raw.decode("utf-8", errors="replace")
    items     = re.findall(r"<item>(.*?)</item>", text_blob, re.DOTALL)
    for item in items[:8]:
        tm = re.search(r"<title>(.*?)</title>", item, re.DOTALL)
        xm = re.search(r"<description>(.*?)</description>", item, re.DOTALL)
        lm = re.search(r"<link>(.*?)</link>", item, re.DOTALL)
        title   = _clean(tm.group(1)) if tm else ""
        snippet = _clean(xm.group(1)) if xm else ""
        if title and len(title) > 20:
            docs.append({
                "url":           lm.group(1).strip() if lm else "",
                "text":          f"{title}. {snippet}",
                "fiscal_period": "",
                "doc_type":      "analyst",
            })
    return docs

def fetch_yfinance_earnings(symbol: str, yf_symbol: str) -> List[Dict]:
    """
    Fetch earnings history from yfinance — EPS actual vs estimate.
    Already in requirements.txt — zero extra cost.
    """
    docs = []
    if not yf_symbol:
        return docs
    try:
        import yfinance as yf
        t    = yf.Ticker(yf_symbol)
        hist = t.earnings_history if hasattr(t, "earnings_history") else None
        if hist is None or (hasattr(hist, "empty") and hist.empty):
            # Try quarterly earnings
            q = t.quarterly_earnings if hasattr(t, "quarterly_earnings") else None
            if q is not None and not (hasattr(q, "empty") and q.empty):
                for idx, row in q.iterrows():
                    rev = float(row.get("Revenue", 0) or 0)
                    ear = float(row.get("Earnings", 0) or 0)
                    text = (f"{symbol} quarterly earnings for {str(idx)[:10]}: "
                            f"Revenue={rev:,.0f} Earnings={ear:,.0f}.")
                    docs.append({"url": "", "text": text,
                                 "fiscal_period": str(idx)[:7],
                                 "doc_type": "eps"})
            return docs
        for idx, row in hist.iterrows():
            eps_act = float(row.get("epsActual",  0) or 0)
            eps_est = float(row.get("epsEstimate", 0) or 0)
            surp    = float(row.get("epsDifference", 0) or 0)
            surp_pct = (surp / eps_est * 100) if eps_est else 0
            beat_miss = "beat" if surp > 0 else ("missed" if surp < 0 else "met")
            text = (f"{symbol} earnings {str(idx)[:10]}: "
                    f"EPS actual={eps_act:.2f}, estimate={eps_est:.2f}, "
                    f"{beat_miss} by {abs(surp_pct):.1f}%.")
            docs.append({
                "url":           "",
                "text":          text,
                "fiscal_period": str(idx)[:7],
                "doc_type":      "eps",
            })
    except Exception as e:
        print(f"  [RAG] yfinance earnings fetch error [{symbol}]: {e}", flush=True)
    return docs

# ══════════════════════════════════════════════════════════════════════════════
# INGEST PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def _embed_and_store(chunks: List[Dict]):
    """Embed a list of chunks and upsert into ChromaDB."""
    if not chunks:
        return
    col   = _get_collection()
    model = _get_embedder()
    texts = [c["text"] for c in chunks]
    ids   = [c["chunk_id"] for c in chunks]
    metas = [{k: v for k, v in c.items() if k not in ("text",)} for c in chunks]
    embs  = model.encode(texts, show_progress_bar=False).tolist()
    # Upsert in batches of 50
    batch = 50
    for i in range(0, len(chunks), batch):
        col.upsert(
            ids=ids[i:i+batch],
            embeddings=embs[i:i+batch],
            documents=texts[i:i+batch],
            metadatas=metas[i:i+batch],
        )

def ingest_symbol(symbol: str, yf_symbol: str = "", company_name: str = "") -> Dict:
    """
    Full ingest for one symbol: fetch → chunk → embed → store.
    Skips documents already seen (hash deduplicated).
    Returns summary dict.
    """
    if not RAG_AVAILABLE:
        return {"ok": False, "error": "sentence-transformers or chromadb not installed"}

    init_rag_tables()
    name    = company_name or symbol
    results = {"symbol": symbol, "new_chunks": 0, "skipped_docs": 0, "errors": []}

    # Gather all docs
    all_docs: List[Dict] = []
    all_docs.extend(fetch_yfinance_earnings(symbol, yf_symbol))
    all_docs.extend(fetch_moneycontrol_news(symbol, name))
    all_docs.extend(fetch_nse_filings(symbol))

    for doc in all_docs:
        text = (doc.get("text") or "").strip()
        if len(text) < 50:
            continue
        h = _sha(text)

        # Check if already ingested
        with _conn() as c:
            row = c.execute(
                "SELECT id FROM rag_docs WHERE doc_hash=?", (h,)
            ).fetchone()
        if row:
            results["skipped_docs"] += 1
            continue

        # Chunk
        doc_type = doc.get("doc_type", "analyst")
        if doc_type == "transcript":
            chunks = chunk_transcript(text, symbol)
        else:
            chunks = chunk_report(text, symbol, doc_type)

        if not chunks:
            continue

        # Add fiscal_period to chunk metadata
        fp = doc.get("fiscal_period", "")
        for ch in chunks:
            ch["fiscal_period"] = fp

        try:
            _embed_and_store(chunks)
            with _conn() as c:
                c.execute(
                    """INSERT OR IGNORE INTO rag_docs
                       (symbol, doc_type, source_url, doc_hash, chunk_count, fiscal_period)
                       VALUES (?,?,?,?,?,?)""",
                    (symbol, doc_type, doc.get("url",""), h, len(chunks), fp)
                )
            results["new_chunks"] += len(chunks)
        except Exception as e:
            results["errors"].append(str(e))

    print(f"  [RAG] {symbol}: +{results['new_chunks']} chunks "
          f"(skipped {results['skipped_docs']} docs)", flush=True)
    return results

def nightly_ingest(verbose: bool = True) -> Dict:
    """
    Ingest all EQUITY instruments. Called by scheduler at 22:00 IST.
    Skips INDICES and COMMODITIES (no meaningful transcripts).
    """
    if not RAG_AVAILABLE:
        print("  [RAG] Skipping nightly ingest — dependencies not installed.", flush=True)
        return {"ok": False, "reason": "dependencies_missing"}

    try:
        from data.instruments import ALL_INSTRUMENTS
    except ImportError:
        return {"ok": False, "reason": "instruments_not_found"}

    total_chunks = 0
    errors       = []
    for sym, inst in ALL_INSTRUMENTS.items():
        itype = getattr(inst, "instrument_type", "EQUITY")
        if itype != "EQUITY":
            continue
        yf_sym = getattr(inst, "yfinance_symbol", "") or ""
        name   = getattr(inst, "name", sym)
        try:
            res = ingest_symbol(sym, yf_sym, name)
            total_chunks += res.get("new_chunks", 0)
        except Exception as e:
            errors.append(f"{sym}: {e}")
        time.sleep(1.0)   # polite delay

    summary = {"ok": True, "total_new_chunks": total_chunks, "errors": errors}
    if verbose:
        print(f"  [RAG] Nightly ingest done: {total_chunks} new chunks, "
              f"{len(errors)} errors.", flush=True)
    return summary

# ══════════════════════════════════════════════════════════════════════════════
# RETRIEVAL
# ══════════════════════════════════════════════════════════════════════════════

def retrieve(symbol: str, query: str, k: int = 5) -> List[Dict]:
    """
    Retrieve top-k most relevant chunks for a symbol + natural-language query.
    Returns list of {text, doc_type, fiscal_period, distance}.
    Falls back to [] if ChromaDB / embedder not available.
    """
    if not RAG_AVAILABLE:
        return []
    try:
        col   = _get_collection()
        model = _get_embedder()
        q_emb = model.encode([query], show_progress_bar=False).tolist()
        res   = col.query(
            query_embeddings=q_emb,
            n_results=k,
            where={"symbol": symbol},
        )
        out = []
        docs  = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        for text, meta, dist in zip(docs, metas, dists):
            out.append({
                "text":          text,
                "doc_type":      meta.get("doc_type", ""),
                "fiscal_period": meta.get("fiscal_period", ""),
                "distance":      round(dist, 4),
            })
        return out
    except Exception as e:
        print(f"  [RAG] retrieve error [{symbol}]: {e}", flush=True)
        return []

def retrieve_any(query: str, k: int = 5) -> List[Dict]:
    """
    Retrieve top-k chunks across ALL symbols (for market-wide Q&A).
    """
    if not RAG_AVAILABLE:
        return []
    try:
        col   = _get_collection()
        model = _get_embedder()
        q_emb = model.encode([query], show_progress_bar=False).tolist()
        res   = col.query(query_embeddings=q_emb, n_results=k)
        out   = []
        docs  = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        for text, meta, dist in zip(docs, metas, dists):
            out.append({
                "text":          text,
                "symbol":        meta.get("symbol", ""),
                "doc_type":      meta.get("doc_type", ""),
                "fiscal_period": meta.get("fiscal_period", ""),
                "distance":      round(dist, 4),
            })
        return out
    except Exception as e:
        print(f"  [RAG] retrieve_any error: {e}", flush=True)
        return []

def get_rag_status() -> Dict:
    """Return RAG system status for the UI."""
    status = {
        "rag_available":         RAG_AVAILABLE,
        "chromadb":              _has_chromadb(),
        "sentence_transformers": _has_st(),
        "chroma_path":           _CHROMA,
        "collection_count":      0,
        "doc_count":             0,
        "embedder_ready":        _embedder is not None,   # True after pre-warm completes
        "collection_ready":      _collection is not None,
    }
    if RAG_AVAILABLE:
        try:
            col = _get_collection()
            status["collection_count"] = col.count()
            status["collection_ready"] = True
        except Exception:
            pass
    try:
        with _conn() as c:
            row = c.execute("SELECT COUNT(*) AS n FROM rag_docs").fetchone()
            status["doc_count"] = row["n"] if row else 0
    except Exception:
        pass
    return status