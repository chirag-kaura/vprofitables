"""
llm_extractor.py — Local LLM Structured Extraction for GANN·ASTRO v3.9
========================================================================
100% free, 100% local — no API keys, no cloud, no cost ever.

Extraction priority chain (auto-detected at startup):
    ① Ollama + llama3.2:3b    — ACTIVE (you have this installed)
    ② llama-cpp-python         — pure pip install, loads GGUF in-process
    ③ spaCy + regex rules      — zero GPU, zero download, instant fallback

All three produce the same JSON output:
    {
      "eps_beat_pct":         float | null,
      "revenue_growth_yoy":   float | null,
      "mgmt_tone":            float,         # -1.0 to +1.0
      "guidance_direction":   str,           # "raised"|"lowered"|"maintained"|"none"
      "key_risks":            [str, ...],
      "extractor_method":     str,
    }

Results cached in SQLite (rag_extractions table, 90-day TTL).
"""

import os
import re
import json
import sqlite3
import importlib
import importlib.util
from datetime import datetime
from typing import List, Dict, Optional

# ── Paths ─────────────────────────────────────────────────────────────────────
from core.paths import DB_PATH
_DB = DB_PATH

# ── Ollama config ─────────────────────────────────────────────────────────────
_OLLAMA_HOST        = "http://localhost:11434"
_OLLAMA_MODEL       = "llama3.2:3b"   # default; overridden at runtime by auto-detect
_ollama_model_verified = False
_ollama_detected_model = None         # stores the actual model found on the server

def _detect_ollama_model() -> Optional[str]:
    """
    Auto-detect whichever Ollama model is actually installed.
    Priority: any llama3 > any gemma > any mistral > any qwen > first available.
    Returns the model name string or None if Ollama is not running.
    """
    try:
        import urllib.request
        with urllib.request.urlopen(f"{_OLLAMA_HOST}/api/tags", timeout=3) as r:
            if r.status != 200:
                return None
            data   = json.loads(r.read())
            models = [m.get("name", "") for m in (data.get("models") or []) if m.get("name")]
            if not models:
                return None
            # Preferred model families in order
            for prefix in ["llama3", "llama-3", "gemma", "mistral", "qwen", "phi"]:
                for m in models:
                    if m.lower().startswith(prefix):
                        return m
            return models[0]   # whatever is there
    except Exception:
        return None

# ── SQLite helper ─────────────────────────────────────────────────────────────
def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB, timeout=10)
    c.row_factory = sqlite3.Row
    return c

def _ensure_tables():
    """Create rag_extractions + rag_docs tables if they don't exist. Safe to call multiple times."""
    try:
        with _conn() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS rag_extractions (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol              TEXT NOT NULL,
                fiscal_period       TEXT DEFAULT '',
                eps_beat_pct        REAL,
                revenue_growth_yoy  REAL,
                mgmt_tone           REAL DEFAULT 0.0,
                guidance_direction  TEXT DEFAULT 'none',
                key_risks           TEXT DEFAULT '[]',
                extracted_at        TEXT DEFAULT (datetime('now')),
                extractor_method    TEXT DEFAULT 'rules',
                UNIQUE(symbol, fiscal_period)
            );
            CREATE TABLE IF NOT EXISTS rag_docs (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol        TEXT    NOT NULL,
                doc_type      TEXT    NOT NULL,
                source_url    TEXT    DEFAULT '',
                doc_hash      TEXT    UNIQUE,
                chunk_count   INTEGER DEFAULT 0,
                ingested_at   TEXT    DEFAULT (datetime('now')),
                fiscal_period TEXT    DEFAULT ''
            );
            """)
    except Exception:
        pass  # Never crash on table init

# Auto-init on import — ensures tables exist before any extract() call
_ensure_tables()

# ══════════════════════════════════════════════════════════════════════════════
# PROMPT TEMPLATES
# ══════════════════════════════════════════════════════════════════════════════

_EXTRACT_PROMPT = """\
You are a financial analyst extracting structured data from earnings documents.

Analyze the excerpts below for {symbol} and return ONLY a valid JSON object.
Do not add any text before or after the JSON.

Required JSON fields:
- "eps_beat_pct": number or null (EPS actual vs estimate %, positive=beat, negative=miss)
- "revenue_growth_yoy": number or null (revenue YoY growth %, positive=growth)
- "mgmt_tone": number between -1.0 and 1.0 (-1=very negative, 0=neutral, +1=very positive)
- "guidance_direction": one of "raised", "lowered", "maintained", "none"
- "key_risks": array of up to 5 short strings (max 15 words each)

EXCERPTS FOR {symbol}:
{context}

JSON:"""

_QA_PROMPT = """\
You are a financial research analyst. Answer the question below using ONLY the provided excerpts.
Keep your answer to 3-5 sentences. Be specific and factual.

Question: {query}

Excerpts:
{context}

Answer:"""

# ══════════════════════════════════════════════════════════════════════════════
# METHOD ①: OLLAMA  (llama3.2:3b — you have this installed)
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# METHOD ①: OLLAMA  (auto-detects whatever model you have installed)
# ══════════════════════════════════════════════════════════════════════════════

def _ollama_available() -> bool:
    """Check if Ollama is running and auto-detect the installed model."""
    global _ollama_model_verified, _ollama_detected_model, _OLLAMA_MODEL
    if _ollama_model_verified and _ollama_detected_model:
        return True
    model = _detect_ollama_model()
    if model:
        _ollama_detected_model = model
        _OLLAMA_MODEL          = model   # update global so prompts use it
        _ollama_model_verified = True
        print(f"  [LLM] Ollama ready — using model: {model}", flush=True)
        return True
    return False

def _ollama_extract(prompt: str) -> Optional[str]:
    """POST to Ollama /api/generate using the auto-detected model."""
    if not _ollama_detected_model:
        return None
    try:
        import urllib.request
        payload = json.dumps({
            "model":  _ollama_detected_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature":    0.1,
                "num_predict":    600,
                "top_p":          0.9,
                "repeat_penalty": 1.1,
            },
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{_OLLAMA_HOST}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
            return (data.get("response") or "").strip()
    except Exception as e:
        print(f"  [LLM] Ollama extract error: {e}", flush=True)
        return None

def _ollama_qa(query: str, context: str) -> Optional[str]:
    """Run a free-text Q&A via Ollama."""
    prompt = _QA_PROMPT.format(query=query, context=context[:4000])
    return _ollama_extract(prompt)

# ══════════════════════════════════════════════════════════════════════════════
# METHOD ②: llama-cpp-python
# ══════════════════════════════════════════════════════════════════════════════

_llama_cpp_model = None

def _llama_cpp_available() -> bool:
    try:
        if importlib.util.find_spec("llama_cpp") is None:
            return False
        for f in os.listdir(_BASE):
            if f.endswith(".gguf"):
                return True
        return False
    except Exception:
        return False

def _llama_cpp_extract(prompt: str) -> Optional[str]:
    global _llama_cpp_model
    try:
        _mod  = importlib.import_module("llama_cpp")
        Llama = _mod.Llama  # type: ignore[attr-defined]
        if _llama_cpp_model is None:
            gguf = next(
                (os.path.join(_BASE, f)
                 for f in sorted(os.listdir(_BASE)) if f.endswith(".gguf")),
                None,
            )
            if not gguf:
                return None
            print(f"  [LLM] Loading llama-cpp: {os.path.basename(gguf)}", flush=True)
            _llama_cpp_model = Llama(model_path=gguf, n_ctx=2048,
                                     n_threads=4, verbose=False)
        out = _llama_cpp_model(prompt, max_tokens=512,
                               temperature=0.05, echo=False)
        return out["choices"][0]["text"].strip()
    except Exception as e:
        print(f"  [LLM] llama-cpp error: {e}", flush=True)
        return None

# ══════════════════════════════════════════════════════════════════════════════
# METHOD ③: Rules (spaCy + regex — always available, zero deps)
# ══════════════════════════════════════════════════════════════════════════════

_POS_TONE = [
    "strong", "robust", "record", "beat", "exceeded", "outperformed",
    "growth", "margin expansion", "confident", "optimistic", "positive",
    "improvement", "recovery", "momentum", "beat estimates", "raised guidance",
    "strong demand", "order book", "revenue growth", "profit growth",
    "market share gain", "cost reduction", "efficiency", "healthy",
]
_NEG_TONE = [
    "headwind", "challenging", "pressure", "decline", "miss", "missed",
    "below estimate", "weak", "slowdown", "concern", "uncertainty", "risk",
    "margin compression", "cost inflation", "demand weakness", "lowered guidance",
    "restructuring", "impairment", "write-off", "default", "npa",
    "inventory build", "pricing pressure", "competitive intensity",
]

def _rules_extract(text: str, eps_hint: Optional[float] = None) -> Dict:
    """Regex + keyword scoring fallback. No external deps."""
    text_lower = text.lower()

    # mgmt_tone
    pos = sum(1 for w in _POS_TONE if w in text_lower)
    neg = sum(1 for w in _NEG_TONE if w in text_lower)
    tot = pos + neg
    mgmt_tone = round((pos - neg) / (tot + 5), 3) if tot else 0.0
    mgmt_tone = max(-1.0, min(1.0, mgmt_tone))

    # guidance_direction
    guidance = "none"
    if any(p in text_lower for p in [
        "raised guidance", "raising guidance", "upgraded guidance",
        "increase our outlook", "raised outlook", "upward revision",
    ]):
        guidance = "raised"
    elif any(p in text_lower for p in [
        "lowered guidance", "lowering guidance", "cut guidance",
        "reduced guidance", "downgraded guidance", "cautious outlook",
        "reduced outlook", "downward revision", "guidance cut",
    ]):
        guidance = "lowered"
    elif any(p in text_lower for p in [
        "maintain guidance", "maintained guidance", "reiterate guidance",
        "reaffirm guidance", "in line with guidance",
    ]):
        guidance = "maintained"

    # revenue_growth_yoy
    rev_growth = None
    for pat in [
        r"revenue[s]?\s+(?:grew?|increased?|rose?|up)\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*%",
        r"revenue[s]?\s+(?:declined?|fell?|down|decreased?)\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*%",
    ]:
        m = re.search(pat, text_lower)
        if m:
            val = float(m.group(1))
            if any(x in pat for x in ["declin", "fell", "down", "decreas"]):
                val = -val
            rev_growth = round(val, 2)
            break

    # eps_beat_pct
    eps_beat = eps_hint
    if eps_beat is None:
        for pat in [
            r"eps\s+(?:beat|exceeded)\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*%",
            r"(?:beat|exceeded)\s+estimate[s]?\s+by\s+(\d+(?:\.\d+)?)\s*%",
            r"(?:missed?|below)\s+estimate[s]?\s+by\s+(\d+(?:\.\d+)?)\s*%",
        ]:
            m = re.search(pat, text_lower)
            if m:
                val = float(m.group(1))
                if "miss" in pat or "below" in pat:
                    val = -val
                eps_beat = round(val, 2)
                break

    # key_risks — extract sentences with negative signals
    risks, seen = [], set()
    sentences = re.split(r"[.!?]\s+", text)
    for sent in sentences:
        sl = sent.lower()
        if any(w in sl for w in _NEG_TONE[:12]):
            risk = re.sub(r"\s+", " ", sent).strip()[:100]
            key  = risk[:40].lower()
            if key not in seen and len(risk) > 20:
                risks.append(risk[0].upper() + risk[1:])
                seen.add(key)
        if len(risks) >= 5:
            break

    return {
        "eps_beat_pct":       eps_beat,
        "revenue_growth_yoy": rev_growth,
        "mgmt_tone":          mgmt_tone,
        "guidance_direction": guidance,
        "key_risks":          risks[:5],
        "extractor_method":   "rules",
    }

# ══════════════════════════════════════════════════════════════════════════════
# JSON PARSER
# ══════════════════════════════════════════════════════════════════════════════

def _parse_llm_json(raw: str, method: str) -> Optional[Dict]:
    """Extract and validate JSON from LLM response. Robust to markdown fences."""
    if not raw:
        return None
    # Strip markdown code fences
    raw = re.sub(r"```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
    # Find first JSON object
    m = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
    if not m:
        # Try full raw if it looks like JSON
        raw = raw.strip()
        if not raw.startswith("{"):
            return None
        m_str = raw
    else:
        m_str = m.group(0)

    try:
        data = json.loads(m_str)
    except json.JSONDecodeError:
        # Attempt to fix common LLM JSON mistakes (trailing commas, single quotes)
        fixed = re.sub(r",\s*([}\]])", r"\1", m_str)     # trailing commas
        fixed = fixed.replace("'", '"')                    # single → double quotes
        try:
            data = json.loads(fixed)
        except Exception:
            return None

    def _f(v):
        try: return round(float(v), 2) if v is not None else None
        except: return None

    def _g(v):
        v = str(v or "none").lower().strip()
        return v if v in ("raised", "lowered", "maintained", "none") else "none"

    return {
        "eps_beat_pct":       _f(data.get("eps_beat_pct")),
        "revenue_growth_yoy": _f(data.get("revenue_growth_yoy")),
        "mgmt_tone":          max(-1.0, min(1.0, float(data.get("mgmt_tone", 0) or 0))),
        "guidance_direction": _g(data.get("guidance_direction")),
        "key_risks":          [str(r)[:100] for r in (data.get("key_risks") or [])[:5]],
        "extractor_method":   method,
    }

# ══════════════════════════════════════════════════════════════════════════════
# CACHE LAYER
# ══════════════════════════════════════════════════════════════════════════════

_CACHE_TTL_DAYS = 90

def _get_cached(symbol: str, fiscal_period: str = "") -> Optional[Dict]:
    """Return a fresh cached extraction or None."""
    try:
        with _conn() as c:
            row = c.execute(
                """SELECT * FROM rag_extractions
                   WHERE symbol=? AND (fiscal_period=? OR fiscal_period='')
                   ORDER BY extracted_at DESC LIMIT 1""",
                (symbol, fiscal_period),
            ).fetchone()
        if not row:
            return None
        age = (datetime.now() - datetime.fromisoformat(row["extracted_at"])).days
        if age > _CACHE_TTL_DAYS:
            return None
        return {
            "eps_beat_pct":       row["eps_beat_pct"],
            "revenue_growth_yoy": row["revenue_growth_yoy"],
            "mgmt_tone":          float(row["mgmt_tone"] or 0.0),
            "guidance_direction": row["guidance_direction"] or "none",
            "key_risks":          json.loads(row["key_risks"] or "[]"),
            "extractor_method":   row["extractor_method"] or "cached",
            "cached":             True,
            "fiscal_period":      row["fiscal_period"] or "",
        }
    except Exception:
        return None

def _save_extraction(symbol: str, fp: str, result: Dict):
    """Persist extraction result to SQLite."""
    try:
        with _conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO rag_extractions
                   (symbol, fiscal_period, eps_beat_pct, revenue_growth_yoy,
                    mgmt_tone, guidance_direction, key_risks, extractor_method)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    symbol, fp or "",
                    result.get("eps_beat_pct"),
                    result.get("revenue_growth_yoy"),
                    result.get("mgmt_tone", 0.0),
                    result.get("guidance_direction", "none"),
                    json.dumps(result.get("key_risks", [])),
                    result.get("extractor_method", "rules"),
                ),
            )
    except Exception as e:
        print(f"  [LLM] Cache save error [{symbol}]: {e}", flush=True)

# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def extract(symbol: str, fiscal_period: str = "",
            context_chunks: Optional[List[Dict]] = None) -> Dict:
    """
    Main extraction entry point.
    Priority: cache → Ollama (llama3.2:3b) → llama-cpp → rules.
    Always returns a valid result dict.
    """
    # 1. Cache check
    cached = _get_cached(symbol, fiscal_period)
    if cached:
        return cached

    # 2. Build context from RAG chunks
    context = ""
    if context_chunks:
        context = "\n\n---\n\n".join(c["text"] for c in context_chunks[:6])

    result = None

    # 3. Ollama (llama3.2:3b)
    if _ollama_available():
        ctx_text = context[:4000] if context else f"{symbol} — no earnings documents indexed yet."
        prompt   = _EXTRACT_PROMPT.format(symbol=symbol, context=ctx_text)
        raw      = _ollama_extract(prompt)
        if raw:
            result = _parse_llm_json(raw, "ollama")
            if result:
                print(f"  [LLM] {symbol}: extracted via Ollama ({_OLLAMA_MODEL})", flush=True)
            else:
                print(f"  [LLM] {symbol}: Ollama response not valid JSON, falling back", flush=True)

    # 4. llama-cpp-python
    if result is None and _llama_cpp_available() and context:
        prompt = _EXTRACT_PROMPT.format(symbol=symbol, context=context[:2000])
        raw    = _llama_cpp_extract(prompt)
        if raw:
            result = _parse_llm_json(raw, "llama_cpp")
            if result:
                print(f"  [LLM] {symbol}: extracted via llama-cpp", flush=True)

    # 5. Rules fallback (always succeeds)
    if result is None:
        result = _rules_extract(context or f"{symbol} earnings")
        print(f"  [LLM] {symbol}: extracted via rules fallback", flush=True)

    # 6. Cache and return
    _save_extraction(symbol, fiscal_period, result)
    return result


def _build_symbol_context(symbol: str) -> str:
    """
    Build a rich context string from existing DB tables (sentiment, prices, news)
    so Ollama can answer questions even before RAG ingest has run.
    """
    parts = []
    try:
        with _conn() as c:
            # Sentiment scores
            row = c.execute(
                """SELECT external_score, external_label, yahoo_score, google_score,
                          analyst_score, total_items, fetched_at
                   FROM sentiment_cache WHERE symbol=?
                   ORDER BY fetched_at DESC LIMIT 1""", (symbol,)
            ).fetchone()
            if row:
                parts.append(
                    f"{symbol} sentiment data (as of {(row['fetched_at'] or '')[:10]}): "
                    f"Overall score {row['external_score']:.3f} ({row['external_label']}). "
                    f"Yahoo Finance score: {row['yahoo_score'] or 'N/A'}. "
                    f"Google News score: {row['google_score'] or 'N/A'}. "
                    f"Analyst consensus: {row['analyst_score'] or 'N/A'}. "
                    f"Based on {row['total_items'] or 0} news items."
                )
    except Exception:
        pass
    try:
        with _conn() as c:
            # Recent headlines
            rows = c.execute(
                """SELECT headline, source, score, published_at FROM sentiment_headlines
                   WHERE symbol=? ORDER BY published_at DESC LIMIT 8""", (symbol,)
            ).fetchall()
            if rows:
                headlines = [
                    f"- [{r['source']}] {r['headline']} (score: {r['score']:.2f})"
                    for r in rows
                ]
                parts.append(
                    f"Recent {symbol} news headlines:\n" + "\n".join(headlines)
                )
    except Exception:
        pass
    try:
        with _conn() as c:
            # Latest price data
            row = c.execute(
                """SELECT date, close, volume, rsi_14, macd_hist, atr_14
                   FROM daily_prices WHERE symbol=?
                   ORDER BY date DESC LIMIT 1""", (symbol,)
            ).fetchone()
            if row:
                parts.append(
                    f"{symbol} latest market data ({row['date']}): "
                    f"Close ₹{row['close']:.2f}. "
                    f"RSI(14): {row['rsi_14']:.1f}. "
                    f"MACD hist: {row['macd_hist']:.3f}. "
                    f"ATR(14): {row['atr_14']:.2f}."
                )
    except Exception:
        pass
    try:
        with _conn() as c:
            # LLM extraction cache
            row = c.execute(
                """SELECT mgmt_tone, guidance_direction, eps_beat_pct,
                          revenue_growth_yoy, key_risks, extractor_method
                   FROM rag_extractions WHERE symbol=?
                   ORDER BY extracted_at DESC LIMIT 1""", (symbol,)
            ).fetchone()
            if row:
                risks = json.loads(row['key_risks'] or '[]')
                parts.append(
                    f"{symbol} AI earnings extraction: "
                    f"Management tone {row['mgmt_tone']:.2f} (range -1 to +1). "
                    f"Guidance direction: {row['guidance_direction']}. "
                    f"EPS beat: {row['eps_beat_pct']}%. "
                    f"Revenue growth YoY: {row['revenue_growth_yoy']}%. "
                    + (f"Key risks: {'; '.join(risks)}." if risks else "")
                )
    except Exception:
        pass
    return "\n\n".join(parts)


def answer_question(query: str, context_chunks: List[Dict],
                    symbol: str = "") -> Dict:
    """
    Answer a free-text question using RAG chunks + live DB data.
    Falls back to DB sentiment/news/price data when no docs are indexed yet.
    """
    # Build context from RAG chunks
    rag_context = "\n\n---\n\n".join(c["text"] for c in context_chunks[:5])

    # Always supplement with live DB data (sentiment, news, price, extraction)
    db_context = _build_symbol_context(symbol) if symbol else ""

    # Combine: RAG first, then DB data
    context = "\n\n".join(filter(None, [rag_context, db_context]))

    if not context:
        return {
            "answer":      (
                f"No data available for {symbol or 'this query'} yet. "
                f"Try running a Sentiment analysis on the Sentiment tab first, "
                f"or click RE-INGEST on the Research page to index earnings documents."
            ),
            "method":      "none",
            "chunks_used": 0,
            "sources":     [],
        }

    answer = None
    method = "rules"

    # Try Ollama (auto-detected model — gemma4, llama3, or whatever is installed)
    if _ollama_available():
        raw = _ollama_qa(query, context)
        if raw and len(raw.strip()) > 20:
            answer = raw.strip()
            method = f"ollama:{_ollama_detected_model or _OLLAMA_MODEL}"

    # llama-cpp fallback
    if answer is None and _llama_cpp_available():
        prompt = _QA_PROMPT.format(query=query, context=context[:3000])
        raw    = _llama_cpp_extract(prompt)
        if raw and len(raw.strip()) > 20:
            answer = raw.strip()
            method = "llama_cpp"

    # Smart rule-based synthesis when no LLM available
    if answer is None:
        answer = _rules_qa(query, context, symbol)
        method = "rules"

    return {
        "answer":      answer,
        "method":      method,
        "chunks_used": len(context_chunks),
        "db_context":  bool(db_context),
        "sources":     [
            {"doc_type":      c.get("doc_type", ""),
             "fiscal_period": c.get("fiscal_period", "")}
            for c in context_chunks
        ],
    }


def _rules_qa(query: str, context: str, symbol: str = "") -> str:
    """
    Smart keyword-based Q&A fallback. Actually reads the context and
    returns relevant sentences rather than a generic message.
    """
    q = query.lower()
    sentences = [s.strip() for s in re.split(r'[.!?\n]+', context) if len(s.strip()) > 25]

    # Score each sentence by keyword overlap with the query
    q_words = set(re.findall(r'\b\w{4,}\b', q))
    scored = []
    for sent in sentences:
        s_words = set(re.findall(r'\b\w{4,}\b', sent.lower()))
        # Topic keywords
        topic_score = 0
        if any(w in q for w in ['sentiment', 'news', 'feeling', 'mood', 'outlook']):
            if any(w in sent.lower() for w in ['sentiment', 'score', 'bullish', 'bearish', 'news', 'headline']):
                topic_score += 3
        if any(w in q for w in ['invest', 'buy', 'should', 'recommend']):
            if any(w in sent.lower() for w in ['rsi', 'guidance', 'score', 'signal', 'buy', 'entry', 'target']):
                topic_score += 3
        if any(w in q for w in ['risk', 'danger', 'concern', 'worry']):
            if any(w in sent.lower() for w in ['risk', 'concern', 'headwind', 'challenge', 'pressure']):
                topic_score += 3
        if any(w in q for w in ['earnings', 'eps', 'revenue', 'profit', 'results']):
            if any(w in sent.lower() for w in ['earnings', 'eps', 'revenue', 'growth', 'beat', 'miss']):
                topic_score += 3
        if any(w in q for w in ['guidance', 'outlook', 'forecast']):
            if any(w in sent.lower() for w in ['guidance', 'raised', 'lowered', 'maintained', 'outlook']):
                topic_score += 3
        overlap = len(q_words & s_words)
        scored.append((topic_score + overlap, sent))

    scored.sort(key=lambda x: -x[0])
    best = [s for _, s in scored[:5] if s]

    if not best:
        return (f"Based on available data for {symbol or 'this symbol'}: "
                f"No specific information found matching your query. "
                f"Try running the Sentiment analysis or clicking RE-INGEST to fetch earnings documents.")

    intro = f"Based on available data for {symbol}:" if symbol else "Based on available data:"
    return intro + " " + ". ".join(best[:3]) + "."


def get_extraction_status() -> Dict:
    """Return extractor capability status for the settings/status UI."""
    ollama_up    = _ollama_available()
    active_model = _ollama_detected_model or _OLLAMA_MODEL
    return {
        "ollama_available":    ollama_up,
        "ollama_model":        active_model if ollama_up else None,
        "ollama_host":         _OLLAMA_HOST,
        "llama_cpp_available": _llama_cpp_available(),
        "rules_available":     True,
        "active_method": (
            f"ollama ({active_model})" if ollama_up else
            "llama_cpp"               if _llama_cpp_available() else
            "rules"
        ),
    }


def get_cached_extractions(symbol: str) -> List[Dict]:
    """Return all cached extractions for a symbol (history table in UI)."""
    try:
        with _conn() as c:
            rows = c.execute(
                """SELECT * FROM rag_extractions
                   WHERE symbol=? ORDER BY extracted_at DESC LIMIT 8""",
                (symbol,),
            ).fetchall()
        return [
            {
                "fiscal_period":       r["fiscal_period"],
                "eps_beat_pct":        r["eps_beat_pct"],
                "revenue_growth_yoy":  r["revenue_growth_yoy"],
                "mgmt_tone":           r["mgmt_tone"],
                "guidance_direction":  r["guidance_direction"],
                "key_risks":           json.loads(r["key_risks"] or "[]"),
                "extractor_method":    r["extractor_method"],
                "extracted_at":        r["extracted_at"],
            }
            for r in rows
        ]
    except Exception:
        return []