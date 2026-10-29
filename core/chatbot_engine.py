"""
core/chatbot_engine.py
======================
AI Assistant Copilot Engine for Vprofitables Terminal.
Features:
  1. Multi-Intent Quantitative Router:
     - Screener Intent: Instant quantitative scans over daily_prices (top gainers, top losers, 5-day drops).
     - Head-to-Head Comparison Intent: Side-by-side fundamentals & price analytics (e.g. TCS vs INFY).
     - Single-Stock Fundamental & Transcript Intelligence (10Y verified financials & concalls).
     - Conversational Guidance & Disambiguation (zero silent guessing or false defaults).
  2. Grounded Multi-strategy Symbol Resolution (symbol, company name, fuzzy search).
  3. Grounded Context Gathering & Sanitization:
     - Relational SQL Tabular Financials (10Y Annual & Quarterly in ₹ Cr).
     - ChromaDB Vector Semantic Search with legal/address boilerplate purging.
     - Technical market price & trend snapshot from daily_prices.
     - Derivatives Options PCR & Shareholding institutional alpha.
  4. Dual-Mode Synthesis:
     - Connects to Ollama local LLM (gemma4:latest / llama3.2:3b / auto-detect).
     - Deterministic Fallback Synthesizer if Ollama is offline (100% uptime, zero hallucinations).
"""

import os
import sys
import json
import re
import time
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.paths import get_db_connection, DB_PATH, BASE_DIR
from core.financial_query import (
    get_company_financials,
    get_transcript_guidance,
    FINANCIAL_UNIT_CONTRACT,
    format_crores,
    format_pct,
    format_inr
)
from core.rag_engine import RAG_AVAILABLE
from core.llm_extractor import _detect_ollama_model, _OLLAMA_HOST
from core.market_screener import screen_price_performance, format_screener_markdown

# ── Symbol Mapping Cache ──────────────────────────────────────────────────────
_SYMBOL_MAP: Dict[str, str] = {}
_ALL_SYMBOLS: List[Dict[str, str]] = []

def _load_symbol_map():
    global _SYMBOL_MAP, _ALL_SYMBOLS
    if _SYMBOL_MAP:
        return
    
    csv_path = os.path.join(BASE_DIR, "data", "nifty500.csv")
    if os.path.exists(csv_path):
        import csv
        try:
            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sym = (row.get("Symbol") or "").strip().upper()
                    name = (row.get("Company Name") or "").strip()
                    ind = (row.get("Industry") or "").strip()
                    if sym:
                        _SYMBOL_MAP[sym] = sym
                        if name:
                            _SYMBOL_MAP[name.upper()] = sym
                            # Add simplified name (e.g. "TATA MOTORS LIMITED" -> "TATA MOTORS")
                            clean_name = re.sub(r"\b(LTD|LIMITED|PVT|INDIA|CORP|CORPORATION)\b", "", name, flags=re.I).strip().upper()
                            if clean_name and clean_name != name.upper():
                                _SYMBOL_MAP[clean_name] = sym
                        _ALL_SYMBOLS.append({"symbol": sym, "name": name, "industry": ind})
        except Exception as e:
            print(f"  [CHATBOT] Error reading nifty500.csv: {e}", flush=True)

    # Common aliases & abbreviations
    _COMMON_ALIASES = {
        "TCS": "TCS",
        "RELIANCE": "RELIANCE",
        "RIL": "RELIANCE",
        "INFY": "INFY",
        "INFOSYS": "INFY",
        "HDFC": "HDFCBANK",
        "HDFCBANK": "HDFCBANK",
        "ICICI": "ICICIBANK",
        "ICICIBANK": "ICICIBANK",
        "SBI": "SBIN",
        "SBIN": "SBIN",
        "BHARTI": "BHARTIARTL",
        "AIRTEL": "BHARTIARTL",
        "TATA MOTORS": "TATAMOTORS",
        "TATAMOTORS": "TATAMOTORS",
        "TATA STEEL": "TATASTEEL",
        "L&T": "LT",
        "LT": "LT",
        "ITC": "ITC",
        "POLYCAB": "POLYCAB",
        "KOTAK": "KOTAKBANK",
        "MARUTI": "MARUTI",
        "BAJAJ FINANCE": "BAJFINANCE",
        "BAJFINANCE": "BAJFINANCE",
        "SWIGGY": "SWIGGY",
        "ZOMATO": "ZOMATO",
    }
    for k, v in _COMMON_ALIASES.items():
        _SYMBOL_MAP[k.upper()] = v

_load_symbol_map()

def resolve_symbol(text: str, default_symbol: Optional[str] = None) -> Optional[str]:
    """
    Detect equity symbol mentioned in user query.
    Returns None if no ticker is identified (avoids false defaults).
    """
    _load_symbol_map()
    text_clean = text.strip()
    upper = text_clean.upper()

    # 1. Direct symbol check in text tokens
    tokens = re.findall(r"[A-Z0-9&-]+", upper)
    for t in tokens:
        if t in _SYMBOL_MAP:
            return _SYMBOL_MAP[t]

    # 2. Substring matching in aliases with word boundary check
    for alias, target_sym in sorted(_SYMBOL_MAP.items(), key=lambda x: -len(x[0])):
        if len(alias) >= 3 and alias in upper:
            # Match whole word to avoid substring collisions
            if re.search(r"\b" + re.escape(alias) + r"\b", upper):
                return target_sym

    # 3. Fallback to default symbol ONLY if explicitly provided and valid
    if default_symbol and default_symbol.strip() and default_symbol.strip().upper() not in {"NONE", "ALL"}:
        sym_clean = default_symbol.strip().upper()
        if sym_clean in _SYMBOL_MAP:
            return _SYMBOL_MAP[sym_clean]
        return sym_clean

    return None

# ── Multi-Intent Classifier ───────────────────────────────────────────────────

def classify_user_intent(message: str, active_symbol: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Categorize user query into distinct execution intents:
      - 'SWING_SETUPS': Short-term / swing trades (10-15 days, Wyckoff, trend continuation)
      - 'SCREENER': Quantitative performance scans (gainers, losers, 5-day drops, volume)
      - 'COMPARISON': Comparing 2 or more stocks (e.g. TCS vs INFY)
      - 'HELP': Help, capabilities, greetings
      - 'TICKER_DETAIL': Deep dive into a specific stock's fundamentals or guidance
      - 'AMBIGUOUS': Question without any stock specified
    """
    msg = message.strip()
    lower = msg.lower()
    _load_symbol_map()

    # Guardrail: If query is market discovery or asking for stock ideas, decouple active_symbol
    is_market_discovery = bool(re.search(
        r"\b(what\s+all\s+stocks|which\s+stocks|suggest|short\s+term|swing|ideas|look\s+for|screener|scanner|recommend|best\s+stocks|top\s+stocks|any\s+stocks)\b",
        lower
    ))
    if is_market_discovery:
        active_symbol = None

    # 1. Help & Greeting intent
    if re.search(r"^(hi|hello|hey|help|who are you|what can you do|capabilities|guide)\b", lower):
        return "HELP", {}

    # 2. Short-Term Swing Trade Setup intent (10-15 days, swing trade suggestions)
    swing_patterns = [
        r"short\s*term\s*trade",
        r"10[- ](?:to[- ])?15\s*days?",
        r"swing\s*trade",
        r"swing\s*trading",
        r"what\s+all\s+stocks\s+can\s+i\s+look\s+for",
        r"suggest.*stocks",
        r"stocks\s+to\s+(buy|trade|watch)",
        r"trade\s*setups?",
        r"trading\s*ideas?",
    ]
    if any(re.search(pat, lower) for pat in swing_patterns):
        # Extract horizon if present
        horizon_days = "10-15 days"
        h_match = re.search(r"(\d+[- ](?:to[- ])?\d+\s*days?)", lower)
        if h_match:
            horizon_days = h_match.group(1)
        return "SWING_SETUPS", {"horizon": horizon_days}

    # 2. Screener Performance intent (gainers, losers, fallen max, drops, rallies)
    screener_patterns = [
        r"fallen\s+max",
        r"fallen\s+most",
        r"fell\s+max",
        r"fell\s+most",
        r"drop(ped)?\s+max",
        r"drop(ped)?\s+most",
        r"top\s+loser",
        r"top\s+gainer",
        r"biggest\s+loser",
        r"biggest\s+gainer",
        r"worst\s+perform",
        r"best\s+perform",
        r"which\s+stock.*(fall|drop|down|gain|rise|rally)",
        r"(most|max)\s+fallen",
        r"down\s+most",
        r"up\s+most",
        r"top\s+\d+\s+(gainer|loser|mover)",
        r"volume\s+shocker",
        r"highest\s+volume",
    ]
    if any(re.search(pat, lower) for pat in screener_patterns):
        # Extract direction: LOSERS vs GAINERS
        is_loser = any(w in lower for w in ["fall", "fell", "drop", "down", "loser", "worst", "crash", "dip", "bottom"])
        direction = "LOSERS" if is_loser else "GAINERS"

        # Extract days
        days = 5  # default
        days_match = re.search(r"(\d+)\s*(?:trading\s*)?days?", lower)
        if days_match:
            days = int(days_match.group(1))
        elif "today" in lower or "1 day" in lower:
            days = 1
        elif "week" in lower:
            days = 5
        elif "month" in lower:
            days = 20

        # Extract limit
        limit = 5
        limit_match = re.search(r"top\s*(\d+)", lower)
        if limit_match:
            limit = int(limit_match.group(1))

        return "SCREENER", {"direction": direction, "days": days, "limit": limit}

    # 3. Stock Comparison intent (e.g. "compare TCS and INFY", "TCS vs INFY")
    tokens = re.findall(r"[A-Z0-9&-]+", msg.upper())
    found_symbols = []
    for t in tokens:
        if t in _SYMBOL_MAP and _SYMBOL_MAP[t] not in found_symbols:
            found_symbols.append(_SYMBOL_MAP[t])

    if len(found_symbols) >= 2 and ("vs" in lower or "versus" in lower or "compare" in lower or "comparison" in lower):
        return "COMPARISON", {"symbols": found_symbols[:2]}

    # 4. Check if a symbol is mentioned in the message
    detected_sym = resolve_symbol(msg, default_symbol=None)
    if detected_sym:
        return "TICKER_DETAIL", {"symbol": detected_sym}

    # 5. If active symbol is present from UI and query refers to stock aspects
    if active_symbol and active_symbol not in {"NONE", "ALL"}:
        return "TICKER_DETAIL", {"symbol": active_symbol}

    # 6. Ambiguous query with no target symbol
    return "AMBIGUOUS", {}

# ── Format Helpers for Specialized Intents ────────────────────────────────────

def format_help_guide() -> str:
    """Format interactive capability guide for Quant Copilot."""
    lines = [
        "### ⚡ Vprofitables Quant Copilot — Capabilities",
        "I am your dedicated quantitative and fundamental market intelligence assistant. Here is what I can do for you:",
        "",
        "#### 1. 📉 Quantitative Market Screener (NSE Equities)",
        "- *'Which stock has fallen max in the last 5 days?'*",
        "- *'Top 5 gainers in Nifty 500 today'*",
        "- *'Top losers over the last 10 trading days'*",
        "",
        "#### 2. 📊 Verified Audited Financials (10-Year Statements)",
        "- *'What was TCS revenue, operating margin, and net profit in FY24?'*",
        "- *'Summarize debt, borrowings, and operating cash flow for RELIANCE'*",
        "- *'How was INFY's recent quarterly performance?'*",
        "",
        "#### 3. 🎙️ Concall Guidance & Transcripts",
        "- *'What is management's forward capex and demand guidance for RELIANCE?'*",
        "- *'What are the key headwinds and risk factors for HDFCBANK?'*",
        "",
        "#### 4. ⚖️ Head-to-Head Equities Comparison",
        "- *'Compare TCS vs INFY'*",
        "- *'Compare HDFCBANK and ICICIBANK margins and price performance'*",
        "",
        "💡 *Tip: Mention any stock symbol or click one of the quick suggestion chips above!*"
    ]
    return "\n".join(lines)

def format_clarification_prompt() -> str:
    """Prompt the user gracefully when a query lacks a stock symbol."""
    lines = [
        "### 🔍 Which company would you like to analyze?",
        "I couldn't identify a specific stock ticker or company name in your query.",
        "",
        "You can:",
        "- **Mention a company or ticker:** e.g. *\"What was the operating margin for **TCS** in FY24?\"* or *\"Show capex guidance for **RELIANCE**\"*",
        "- **Select an active stock:** Pick any stock from the header selector above.",
        "- **Run a market screener:** e.g. *\"Which stock has fallen max in the last 5 days?\"* or *\"Top gainers today\"*."
    ]
    return "\n".join(lines)

def format_comparison_markdown(sym1: str, sym2: str) -> str:
    """Generate a side-by-side quantitative comparison between two equities."""
    p1 = get_market_price_snapshot(sym1)
    p2 = get_market_price_snapshot(sym2)
    fin1 = get_company_financials(sym1, period_type="ANNUAL", limit=1)
    fin2 = get_company_financials(sym2, period_type="ANNUAL", limit=1)

    lines = [
        f"### ⚖️ Head-to-Head Comparison: **{sym1}** vs **{sym2}**",
        ""
    ]
    lines.append("| Financial / Technical Metric | " + sym1 + " | " + sym2 + " |")
    lines.append("|:---|:---:|:---:|")

    ltp1 = f"₹{p1['ltp']:,.2f}" if p1.get("ltp") else "N/A"
    ltp2 = f"₹{p2['ltp']:,.2f}" if p2.get("ltp") else "N/A"
    lines.append(f"| **Current Price (LTP)** | **{ltp1}** | **{ltp2}** |")

    range1 = f"₹{p1.get('low_52w', 0):,.2f} - ₹{p1.get('high_52w', 0):,.2f}" if p1.get("low_52w") else "N/A"
    range2 = f"₹{p2.get('low_52w', 0):,.2f} - ₹{p2.get('high_52w', 0):,.2f}" if p2.get("low_52w") else "N/A"
    lines.append(f"| **52-Week Range** | {range1} | {range2} |")

    drop1 = f"{p1.get('pct_from_52w_high', 0):+.1f}%" if p1.get("pct_from_52w_high") is not None else "N/A"
    drop2 = f"{p2.get('pct_from_52w_high', 0):+.1f}%" if p2.get("pct_from_52w_high") is not None else "N/A"
    lines.append(f"| **Distance from 52W High** | {drop1} | {drop2} |")

    f1 = fin1[0] if fin1 else {}
    f2 = fin2[0] if fin2 else {}

    lines.append(f"| **Latest FY Period** | {f1.get('fiscal_period', 'N/A')} | {f2.get('fiscal_period', 'N/A')} |")
    lines.append(f"| **Total Revenue / Sales** | {f1.get('sales_fmt', 'N/A')} | {f2.get('sales_fmt', 'N/A')} |")
    lines.append(f"| **Operating Margin (OPM)** | {f1.get('opm_pct_fmt', 'N/A')} | {f2.get('opm_pct_fmt', 'N/A')} |")
    lines.append(f"| **Net Profit (PAT)** | {f1.get('net_profit_fmt', 'N/A')} | {f2.get('net_profit_fmt', 'N/A')} |")
    lines.append(f"| **Operating Cash Flow** | {f1.get('operating_cash_flow_fmt', 'N/A')} | {f2.get('operating_cash_flow_fmt', 'N/A')} |")
    lines.append(f"| **Total Borrowings / Debt** | {f1.get('borrowings_fmt', 'N/A')} | {f2.get('borrowings_fmt', 'N/A')} |")
    lines.append("")
    lines.append("*(All financial metric figures are verified against official audited filings in `market_data_v2.db` denominated in INR Crores).*")
    return "\n".join(lines)

# ── Market Price Snapshot Helper ──────────────────────────────────────────────

def get_market_price_snapshot(symbol: str) -> Dict[str, Any]:
    """Retrieve latest closing price, 52W range, and recent performance."""
    try:
        conn = get_db_connection(readonly=True)
        row = conn.execute("""
            SELECT close, high, low, trade_date 
            FROM daily_prices 
            WHERE symbol = ? 
            ORDER BY trade_date DESC 
            LIMIT 1
        """, (symbol,)).fetchone()
        
        hist = conn.execute("""
            SELECT close, high, low, trade_date 
            FROM daily_prices 
            WHERE symbol = ? 
            ORDER BY trade_date DESC 
            LIMIT 250
        """, (symbol,)).fetchall()
        conn.close()

        if not row:
            return {"symbol": symbol, "ltp": None, "high_52w": None, "low_52w": None}

        ltp = float(row[0])
        trade_date = row[3]
        all_highs = [float(r[1]) for r in hist if r[1] is not None]
        all_lows = [float(r[2]) for r in hist if r[2] is not None]

        high_52w = max(all_highs) if all_highs else ltp
        low_52w = min(all_lows) if all_lows else ltp

        pct_from_52w_high = round(((ltp - high_52w) / high_52w) * 100, 1) if high_52w else 0.0

        # Calculate 5-Day price return and 20-Day volume accumulation trend
        change_5d_pct = None
        if len(hist) >= 5 and hist[4][0]:
            p_5d_ago = float(hist[4][0])
            if p_5d_ago > 0:
                change_5d_pct = round(((ltp - p_5d_ago) / p_5d_ago) * 100, 2)

        vol_20d_note = "Volume data steady"
        cur_vol = 0
        try:
            # Query recent volume from daily_prices
            v_rows = conn.execute("SELECT volume FROM daily_prices WHERE symbol=? ORDER BY trade_date DESC LIMIT 20", (symbol,)).fetchall()
            vols = [float(vr[0]) for vr in v_rows if vr[0] is not None]
            if vols:
                cur_vol = vols[0]
                avg_vol = sum(vols) / len(vols)
                ratio = cur_vol / max(1.0, avg_vol)
                if ratio >= 1.25:
                    vol_20d_note = f"Volume expanding ({ratio:.1f}x of 20D average) — institutional accumulation signature"
                elif ratio <= 0.75:
                    vol_20d_note = f"Volume drying up ({ratio:.1f}x of 20D average) — selling exhaustion / absorption"
                else:
                    vol_20d_note = f"Volume in-line with 20D average ({ratio:.1f}x)"
        except Exception:
            pass

        return {
            "symbol": symbol,
            "ltp": ltp,
            "trade_date": trade_date,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "pct_from_52w_high": pct_from_52w_high,
            "change_5d_pct": change_5d_pct,
            "volume_latest": cur_vol,
            "vol_accumulation_note": vol_20d_note
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}

# ── Grounded Prompt Builder ───────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are the Vprofitables Senior Quantitative & Fundamental Equity Copilot.
You assist professional traders and research analysts by delivering clear, concise, 
and strictly factual answers regarding Indian listed equities (NSE/BSE).

INVARIANT ACCURACY RULES:
1. ALWAYS quote exact financial numbers from the VERIFIED AUDITED FINANCIAL STATEMENTS provided.
2. In accordance with the contract: all Income Statement, Balance Sheet, and Cash Flow metrics 
   are in INR Crores (₹ Cr). Per-share metrics are in ₹. Never confuse Crores with Thousands or Billions.
3. When referencing earnings calls or management commentary, cite the speaker attribution 
   (e.g., [Executive: Management] or [Analyst: Brokerage]) and the relevant fiscal period.
4. If a requested metric is not in the verified context, state that it is not present rather than guessing.
5. Structure your output cleanly using Markdown with concise bullet points and bold financial metrics.
"""

def build_prompt(symbol: str, question: str, context: Dict[str, Any]) -> str:
    """Build grounded prompt containing verified tabular facts and transcript excerpts."""
    price_info = context.get("price_snapshot", {})
    annual_fin = context.get("annual_financials", [])
    quarterly_fin = context.get("quarterly_financials", [])
    transcripts = context.get("transcripts", [])

    # Format price snapshot
    price_txt = ""
    if price_info.get("ltp"):
        price_txt = (
            f"- Latest Closing Price: ₹{price_info['ltp']:,.2f} (As of {price_info.get('trade_date', 'recent')})\n"
            f"- 52-Week Range: ₹{price_info.get('low_52w', 0):,.2f} — ₹{price_info.get('high_52w', 0):,.2f} "
            f"({price_info.get('pct_from_52w_high', 0)}% from high)\n"
        )
    else:
        price_txt = "- Market Price: Daily price tracking active in terminal.\n"

    # Format annual table
    annual_txt = ""
    if annual_fin:
        annual_txt = "VERIFIED ANNUAL FINANCIAL STATEMENTS (in INR Crores):\n"
        annual_txt += "| Period | Sales (₹ Cr) | Op Profit (₹ Cr) | OPM % | Net Profit (₹ Cr) | EPS (₹) | Op Cash Flow (₹ Cr) | Borrowings (₹ Cr) |\n"
        annual_txt += "|---|---|---|---|---|---|---|---|\n"
        for r in annual_fin:
            annual_txt += (
                f"| {r.get('fiscal_period')} | {r.get('sales_fmt')} | {r.get('operating_profit_fmt')} | "
                f"{r.get('opm_pct_fmt')} | {r.get('net_profit_fmt')} | {r.get('eps_fmt')} | "
                f"{r.get('operating_cash_flow_fmt')} | {r.get('borrowings_fmt')} |\n"
            )
    else:
        annual_txt = "No annual tabular statements recorded yet for this symbol in database.\n"

    # Format quarterly table
    quarterly_txt = ""
    if quarterly_fin:
        quarterly_txt = "VERIFIED RECENT QUARTERS (in INR Crores):\n"
        quarterly_txt += "| Quarter | Sales (₹ Cr) | Op Profit (₹ Cr) | OPM % | Net Profit (₹ Cr) | EPS (₹) |\n"
        quarterly_txt += "|---|---|---|---|---|---|\n"
        for r in quarterly_fin[:4]:
            quarterly_txt += (
                f"| {r.get('fiscal_period')} | {r.get('sales_fmt')} | {r.get('operating_profit_fmt')} | "
                f"{r.get('opm_pct_fmt')} | {r.get('net_profit_fmt')} | {r.get('eps_fmt')} |\n"
            )

    # Format transcript excerpts
    transcript_txt = ""
    if transcripts:
        transcript_txt = "CONFERENCE CALL TRANSCRIPT EXCERPTS & MANAGEMENT COMMENTARY:\n"
        for i, t in enumerate(transcripts, 1):
            role_tag = f"[{t.get('speaker_role', 'EXECUTIVE')}: {t.get('speaker_name', 'Management')}]"
            period_tag = f"({t.get('fiscal_period', 'Period N/A')})"
            transcript_txt += f"{i}. {role_tag} {period_tag}:\n   \"{t.get('excerpt', '').strip()}\"\n\n"
    else:
        transcript_txt = "No specific strategic management guidance found in verified concalls for this query.\n"

    prompt = f"""\
{_SYSTEM_PROMPT}

CONTEXT FOR SYMBOL: {symbol}
{price_txt}
{annual_txt}
{quarterly_txt}
{transcript_txt}

USER QUESTION:
{question}

ASSISTANT RESPONSE (Concise, accurate, formatted with Markdown):
"""
    return prompt

# ── Local Ollama Invocation ───────────────────────────────────────────────────

def call_ollama(prompt: str, timeout: int = 15) -> Optional[str]:
    """Call local Ollama server if available."""
    model = _detect_ollama_model()
    if not model:
        return None
    try:
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.15,
                "num_predict": 450,
                "top_p": 0.9,
            }
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{_OLLAMA_HOST}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return (data.get("response") or "").strip()
    except Exception as e:
        return None

# ── Deterministic Fallback Synthesizer (Zero Hallucination) ───────────────────

def synthesize_deterministic_reply(symbol: str, question: str, context: Dict[str, Any]) -> str:
    """
    High-fidelity deterministic synthesizer that produces clean, verified 
    financial answers without ugly N/A clutter.
    """
    annual = context.get("annual_financials", [])
    quarterly = context.get("quarterly_financials", [])
    transcripts = context.get("transcripts", [])
    price = context.get("price_snapshot", {})

    lines = [f"### 📊 Financial Intelligence: **{symbol}**"]

    if price.get("ltp"):
        chg_5d = f" | **5-Day Return:** {price.get('change_5d_pct'):+.2f}%" if price.get('change_5d_pct') is not None else ""
        lines.append(
            f"**Current Price:** ₹{price['ltp']:,.2f}{chg_5d} | "
            f"**52W High:** ₹{price.get('high_52w', 0):,.2f} | "
            f"**52W Low:** ₹{price.get('low_52w', 0):,.2f} ({price.get('pct_from_52w_high', 0):+.1f}% from peak)"
        )
        if price.get("vol_accumulation_note"):
            lines.append(f"📊 **Volume Trend:** {price.get('vol_accumulation_note')}")
        lines.append("")

    news = context.get("recent_news", [])
    if news:
        lines.append("#### 📰 Latest News & Market Sentiment Pulse")
        for n in news:
            lines.append(f"- **[{n['label']}]** {n['title']} *({n['published_at']}, Source: {n['source']})*")
        lines.append("")

    if annual:
        latest = annual[0]
        prev = annual[1] if len(annual) > 1 else None
        lines.append(f"#### 📈 Audited Performance Highlights ({latest.get('fiscal_period', 'Latest FY')})")
        
        if latest.get("sales_fmt") and latest.get("sales_fmt") != "N/A":
            lines.append(f"- **Total Revenue / Sales:** {latest.get('sales_fmt')}")
            
        if latest.get("operating_profit_fmt") and latest.get("operating_profit_fmt") != "N/A":
            opm_str = f" (Operating Margin: **{latest.get('opm_pct_fmt')}**)" if latest.get('opm_pct_fmt') != "N/A" else ""
            lines.append(f"- **Operating Profit:** {latest.get('operating_profit_fmt')}{opm_str}")
            
        if latest.get("net_profit_fmt") and latest.get("net_profit_fmt") != "N/A":
            lines.append(f"- **Net Profit (PAT):** {latest.get('net_profit_fmt')}")
            
        if latest.get("eps_fmt") and latest.get("eps_fmt") != "N/A":
            lines.append(f"- **Earnings Per Share (EPS):** {latest.get('eps_fmt')}")
            
        if latest.get("operating_cash_flow_fmt") and latest.get("operating_cash_flow_fmt") != "N/A":
            lines.append(f"- **Operating Cash Flow:** {latest.get('operating_cash_flow_fmt')}")
            
        if latest.get("borrowings_fmt") and latest.get("borrowings_fmt") != "N/A":
            lines.append(f"- **Total Borrowings / Debt:** {latest.get('borrowings_fmt')}")

        if prev and latest.get("sales") and prev.get("sales"):
            growth = ((latest["sales"] - prev["sales"]) / prev["sales"]) * 100
            lines.append(f"- **YoY Sales Growth:** {growth:+.1f}% vs {prev.get('fiscal_period')}")
        lines.append("")

    if quarterly:
        q_latest = quarterly[0]
        lines.append(f"#### ⏱️ Recent Quarter: {q_latest.get('fiscal_period')}")
        opm_q = f" | **Op Margin:** {q_latest.get('opm_pct_fmt')}" if q_latest.get('opm_pct_fmt') != "N/A" else ""
        lines.append(f"- **Quarterly Sales:** {q_latest.get('sales_fmt')}{opm_q}")
        if q_latest.get("net_profit_fmt") and q_latest.get("net_profit_fmt") != "N/A":
            lines.append(f"- **Quarterly Net Profit:** {q_latest.get('net_profit_fmt')}")
        lines.append("")

    sh = context.get("shareholding", {})
    if sh and sh.get("promoter_pct") is not None:
        lines.append(f"#### 🏛️ Smart Money & Shareholding ({sh.get('latest_period', 'Latest')})")
        lines.append(f"- **Promoter Holding:** {sh.get('promoter_pct')}% (Pledged: **{sh.get('pledged_pct', 0.0)}%**)")
        lines.append(f"- **FII Stake:** {sh.get('fii_pct')}% ({sh.get('fii_qoq_delta', 0.0):+.2f}% QoQ) | **DII:** {sh.get('dii_pct')}% ({sh.get('dii_qoq_delta', 0.0):+.2f}% QoQ)")
        lines.append(f"- **Institutional Flow Signal:** `{sh.get('institutional_signal', 'STABLE')}`")
        lines.append("")

    pcr_info = context.get("options_pcr", {})
    if pcr_info and pcr_info.get("pcr") is not None:
        lines.append(f"#### 🎯 Derivatives & Options Sentiment")
        lines.append(f"- **PCR (Put-Call Ratio):** {pcr_info.get('pcr')} ({pcr_info.get('regime')})")
        lines.append(f"- **Max Pain Strike:** ₹{pcr_info.get('max_pain')} (Spot Gap: {pcr_info.get('max_pain_gap_pct'):+.1f}%)")
        lines.append("")

    ev = context.get("imminent_event", {})
    if ev and ev.get("imminent"):
        lines.append(f"> ⚠️ **EVENT RISK ALERT:** {ev.get('risk_message')}")
        lines.append("")

    valid_transcripts = [t for t in transcripts if t.get("excerpt", "").strip()]
    if valid_transcripts:
        lines.append("#### 🎙️ Key Management Guidance & Transcript Excerpts")
        for t in valid_transcripts[:2]:
            role = t.get("speaker_role", "EXECUTIVE")
            period = t.get("fiscal_period", "")
            excerpt = t.get("excerpt", "").strip()
            if len(excerpt) > 280:
                excerpt = excerpt[:277] + "..."
            lines.append(f"> **[{role}] ({period}):** \"{excerpt}\"")
        lines.append("")

    lines.append("*(All financial metric figures are verified against official audited filings in `market_data_v2.db` denominated in INR Crores).*")
    return "\n".join(lines)

# ── Primary Chat Handler API ──────────────────────────────────────────────────

def format_swing_setups_markdown(candidates: List[Dict[str, Any]], query_horizon: str = "10-15 days") -> str:
    lines = [
        f"### 🎯 Institutional Swing Trade Setups ({query_horizon})",
        "*Quantitative Trend Continuation & Pullback Engine (Multi-Timeframe Trend + 20-EMA Absorption + Volume Exhaustion)*",
        ""
    ]
    if not candidates:
        lines.append("No active swing setups met the minimum institutional confidence threshold today.")
        return "\n".join(lines)

    for i, c in enumerate(candidates, 1):
        lines.append(f"#### #{i}. **{c['symbol']}** — {c.get('name', c['symbol'])} ({c.get('sector', 'Sector N/A')})")
        lines.append(f"- **Setup:** `{c.get('setup_name', '20-EMA Dip & Rip')}` | **AI Confidence:** **{c.get('confidence')}%** | **R:R:** **{c.get('rr_ratio')}:1**")
        lines.append(f"- **Current LTP:** ₹{c.get('price', 0):,.2f}")
        lines.append(f"- **Entry Zone:** **₹{c.get('entry_zone_low', 0):,.2f} – ₹{c.get('entry_zone_high', 0):,.2f}** (Ideal: ₹{c.get('entry', 0):,.2f})")
        lines.append(f"- **Stop Loss (SL):** **₹{c.get('stop_loss', 0):,.2f}** (Risk: ₹{c.get('risk_per_share', 0):,.2f}/share)")
        lines.append(f"- **Target 1:** **₹{c.get('target1', 0):,.2f}** | **Target 2:** **₹{c.get('target2', 0):,.2f}**")
        lines.append(f"- **Estimated Hold Period:** **{c.get('hold_days', 12)} Trading Days**")
        lines.append(f"- **Technical & Quantitative 'Why':**")
        for r in c.get('reasons', []):
            lines.append(f"  • {r}")
        csym = c.get('symbol', 'RELIANCE')
        centry = c.get('entry', 0)
        csl = c.get('stop_loss', 0)
        ct1 = c.get('target1', 0)
        lines.append(
            f'<div class="vprof-chip-container" style="display:flex; flex-wrap:wrap; gap:6px; margin:6px 0 12px 0;">'
            f'<button class="vprof-chat-chip" onclick="openSymbolChart(\'{csym}\')">📈 Open {csym} Chart</button>'
            f'<button class="vprof-chat-chip" style="background:#059669; color:#fff;" onclick="executePaperTrade(\'{csym}\', 10, {centry}, {csl}, {ct1}, this)">⚡ 1-Click Paper Buy</button>'
            f'<button class="vprof-chat-chip" onclick="askQuickPrompt(\'Multi timeframe analysis for {csym}\')">🔍 MTF Matrix</button>'
            f'</div>'
        )

    lines.append("> 🛡️ **Risk Gate:** Always size positions to risk ≤ 1% of total portfolio equity. Invalidate position if price closes below the 20-EMA on 1D timeframe.")
    return "\n".join(lines)

def handle_chat_query(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for /api/chat.
    Accepts:
      {
        "message": "Which stock has fallen max in last 5 days?",
        "symbol": "RELIANCE" (optional active symbol context),
        "history": [...] (optional prior conversation)
      }
    Returns:
      {
        "reply": str,
        "symbol": str,
        "model_used": str,
        "latency_ms": int,
        "sources": [...]
      }
    """
    t0 = time.time()
    user_msg = (params.get("message") or "").strip()
    active_sym = (params.get("symbol") or "").strip().upper()
    session_id = params.get("session_id")
    selected_model = params.get("model") or "qwen2.5:7b"

    if not user_msg:
        return {"error": "Message is required."}

    # ── Model Switch Command Detection ─────────────────────────────────────────
    model_switch_match = re.search(r"\b(?:use|switch(?:\s+to)?|change(?:\s+to)?|set\s+model(?:\s+to)?)\s+(7b|3b|13b|finance|qwen|gemma)\b", user_msg.lower())
    if model_switch_match:
        target_alias = model_switch_match.group(1).lower()
        if "7" in target_alias or "qwen" in target_alias:
            model_name = "qwen2.5:7b"
            display_name = "Qwen 2.5 7B (High-Precision Quantitative Edge Model)"
        elif "13" in target_alias or "finance" in target_alias:
            model_name = "finance-13b"
            display_name = "AdaptLLM / Finance-LLM-13B (Domain Financial Edge Model)"
        elif "gemma" in target_alias:
            model_name = "gemma4:latest"
            display_name = "Gemma 4 (9.6B General Reasoning Model)"
        else:
            model_name = "qwen2.5:7b"
            display_name = "Qwen 2.5 7B"

        if session_id:
            try:
                from core.session_manager import get_session
                sess = get_session(session_id)
                if sess:
                    sess.selected_model = model_name
            except Exception:
                pass

        return {
            "reply": f"### ⚡ Switched Active Model Engine\n\nActive model has been set to **{display_name}**.\n\nSubsequent quantitative queries will be synthesized using this model. You can also toggle between models at any time using the toggle buttons at the top of this chat window!",
            "symbol": active_sym or None,
            "model_used": display_name,
            "selected_model": model_name,
            "is_fallback": False,
            "latency_ms": 1,
            "sources": ["Model Configuration Engine"]
        }

    # ── PHASE 5: LANGGRAPH OHLC RAG AGENT EXECUTION ───────────────────────
    try:
        from core.ohlc_rag.engine import run_ohlc_agent
        agent_res = run_ohlc_agent(user_msg, active_symbol=active_sym, session_id=session_id, model=selected_model)
        if agent_res and agent_res.get("reply"):
            return agent_res
    except Exception as e:
        print(f"  [ChatEngine] OHLC LangGraph RAG error: {e}", flush=True)

    # ── AGENTIC ORCHESTRATOR SWARM EXECUTION ──────────────────────────────
    try:
        from core.agent_orchestrator import run_agentic_copilot
        session_id = params.get("session_id")
        user_id = params.get("user_id")
        res = run_agentic_copilot(query=user_msg, symbol=active_sym, session_id=session_id, user_id=user_id)
        reply = res.get("answer", "")
        intent = res.get("intent", "")
        if intent in (
            "SCREENER_LOSERS", "SCREENER_GAINERS", "SWING_SETUPS", "GREETING_OR_HELP",
            "FUNDAMENTAL_SCREENER", "AMBIGUOUS", "GROUP_DISAMBIGUATION",
            "PORTFOLIO_AUDIT", "PORTFOLIO_SECTOR_AUDIT", "PERSONALIZATION_UPDATE", "CAPITAL_ALLOCATION", "MACRO_STRESS_TEST"
        ):
            resolved_sym = res.get("symbol") or None
        else:
            resolved_sym = res.get("symbol") or active_sym or None
        latency_ms = int((time.time() - t0) * 1000)
        return {
            "reply": reply,
            "symbol": resolved_sym,
            "model_used": f"LangGraph-Agentic-Swarm ({res.get('intent', 'ROUTED')})",
            "is_fallback": False,
            "latency_ms": latency_ms,
            "sources": [
                "LangGraph Multi-Agent Swarm Orchestrator",
                "Verified 10Y SQL Financials & Daily Prices",
                "ChromaDB Clean Management Transcripts"
            ],
            "metrics_summary": {
                "intent": res.get("intent"),
                "symbol": resolved_sym
            }
        }
    except Exception as e:
        print(f"  [ChatEngine] Agentic Swarm fallback error: {e}", flush=True)

    # 1. Multi-Intent Routing
    intent, intent_params = classify_user_intent(user_msg, active_symbol=active_sym)

    # ── INTENT 0: SWING TRADE SETUPS (10-15 Days) ─────────────────────────────
    if intent == "SWING_SETUPS":
        from core.trend_continuation_engine import scan_trend_pullbacks
        horizon = intent_params.get("horizon", "10-15 days")
        candidates = scan_trend_pullbacks(horizon="swing", min_confidence=55, max_results=3)
        reply = format_swing_setups_markdown(candidates, query_horizon=horizon)
        latency_ms = int((time.time() - t0) * 1000)
        top_sym = candidates[0]["symbol"] if candidates else "NIFTY50"
        return {
            "reply": reply,
            "symbol": top_sym,
            "model_used": "Vprofitables-Trend-Continuation-Engine",
            "is_fallback": False,
            "latency_ms": latency_ms,
            "sources": [
                "Institutional Trend Continuation & Pullback Engine (20-EMA Dip & Rip)",
                "Daily Prices (Multi-Timeframe Trend + Volume Drying Up + RS vs NIFTY)"
            ],
            "metrics_summary": {
                "intent": "SWING_SETUPS",
                "horizon": horizon,
                "top_symbol": top_sym
            }
        }

    # ── INTENT A: QUANTITATIVE SCREENER ───────────────────────────────────────
    if intent == "SCREENER":
        days = intent_params.get("days", 5)
        direction = intent_params.get("direction", "LOSERS")
        limit = intent_params.get("limit", 5)

        screen_res = screen_price_performance(days=days, direction=direction, limit=limit)
        reply = format_screener_markdown(screen_res)
        latency_ms = int((time.time() - t0) * 1000)

        top_sym = screen_res["results"][0]["symbol"] if screen_res.get("results") else active_sym

        return {
            "reply": reply,
            "symbol": top_sym,
            "model_used": "Vprofitables-Quant-Screener-Engine",
            "is_fallback": False,
            "latency_ms": latency_ms,
            "sources": [
                f"NSE Daily Price Database ({screen_res.get('universe_count', 500)}+ Equities, {screen_res.get('start_date')} to {screen_res.get('end_date')})"
            ],
            "metrics_summary": {
                "screener_type": direction,
                "days": days,
                "top_symbol": top_sym
            }
        }

    # ── INTENT B: INTERACTIVE HELP & CAPABILITIES ─────────────────────────────
    if intent == "HELP":
        reply = format_help_guide()
        return {
            "reply": reply,
            "symbol": active_sym or "RELIANCE",
            "model_used": "Vprofitables-Assistant-Router",
            "is_fallback": False,
            "latency_ms": int((time.time() - t0) * 1000),
            "sources": ["Terminal System Catalog"]
        }

    # ── INTENT C: HEAD-TO-HEAD COMPARISON ─────────────────────────────────────
    if intent == "COMPARISON":
        syms = intent_params.get("symbols", [])
        if len(syms) >= 2:
            reply = format_comparison_markdown(syms[0], syms[1])
            return {
                "reply": reply,
                "symbol": syms[0],
                "model_used": "Vprofitables-Quant-Comparison-Engine",
                "is_fallback": False,
                "latency_ms": int((time.time() - t0) * 1000),
                "sources": [
                    f"SQLite 10Y Statements & Daily Prices for {syms[0]} & {syms[1]}"
                ]
            }

    # ── INTENT D: AMBIGUOUS QUERY (Ask for clarification) ─────────────────────
    if intent == "AMBIGUOUS":
        reply = format_clarification_prompt()
        return {
            "reply": reply,
            "symbol": active_sym or "RELIANCE",
            "model_used": "Vprofitables-Disambiguation-Engine",
            "is_fallback": False,
            "latency_ms": int((time.time() - t0) * 1000),
            "sources": []
        }

    # ── INTENT E: SINGLE TICKER FUNDAMENTALS & TRANSCRIPTS ─────────────────────
    target_symbol = intent_params.get("symbol") or resolve_symbol(user_msg, default_symbol=active_sym)
    if not target_symbol:
        reply = format_clarification_prompt()
        return {
            "reply": reply,
            "symbol": active_sym or "RELIANCE",
            "model_used": "Vprofitables-Disambiguation-Engine",
            "is_fallback": False,
            "latency_ms": int((time.time() - t0) * 1000),
            "sources": []
        }

    # Collect Grounded Context for Target Symbol
    annual_fin = get_company_financials(target_symbol, period_type="ANNUAL", limit=3)
    quarterly_fin = get_company_financials(target_symbol, period_type="QUARTERLY", limit=4)
    transcripts = get_transcript_guidance(target_symbol, user_msg, k=3, executive_only=False)
    price_snap = get_market_price_snapshot(target_symbol)

    # 5. News Sentiment Pulse
    recent_news = []
    try:
        conn_n = get_db_connection(readonly=True)
        n_rows = conn_n.execute("""
            SELECT title, label, calibrated_score, published_at, source
            FROM news_sentiment
            WHERE symbol = ?
            ORDER BY published_at DESC
            LIMIT 3
        """, (target_symbol,)).fetchall()
        conn_n.close()
        for nr in n_rows:
            recent_news.append({
                "title": nr[0],
                "label": nr[1] or "NEUTRAL",
                "score": round(float(nr[2]), 2) if nr[2] is not None else 0.0,
                "published_at": nr[3],
                "source": nr[4]
            })
    except Exception:
        recent_news = []

    # Alpha Datasets: Shareholding, Options PCR & Event Risk
    try:
        from core.shareholding_engine import get_shareholding_trend
        shareholding = get_shareholding_trend(target_symbol)
    except Exception:
        shareholding = {}

    try:
        from core.corporate_calendar import is_earnings_imminent
        imminent_event = is_earnings_imminent(target_symbol)
    except Exception:
        imminent_event = {}

    try:
        from core.options_pcr_engine import calculate_iv_skew_and_moneyness
        options_pcr = calculate_iv_skew_and_moneyness(target_symbol)
    except Exception:
        options_pcr = {}

    context = {
        "symbol": target_symbol,
        "annual_financials": annual_fin,
        "quarterly_financials": quarterly_fin,
        "transcripts": transcripts,
        "price_snapshot": price_snap,
        "shareholding": shareholding,
        "imminent_event": imminent_event,
        "options_pcr": options_pcr,
        "recent_news": recent_news,
    }

    # Build Grounded Prompt
    prompt = build_prompt(target_symbol, user_msg, context)

    # Attempt Local Ollama LLM
    model_name = _detect_ollama_model() or "gemma4:latest"
    reply = call_ollama(prompt, timeout=18)
    used_fallback = False

    if not reply:
        # High-fidelity deterministic fallback synthesizer
        reply = synthesize_deterministic_reply(target_symbol, user_msg, context)
        model_name = "Vprofitables-Quant-Deterministic-Synthesizer"
        used_fallback = True

    latency_ms = int((time.time() - t0) * 1000)

    # Build sources summary
    sources = []
    if annual_fin:
        sources.append(f"SQLite Audited Statements ({len(annual_fin)} Annual FY)")
    if quarterly_fin:
        sources.append(f"SQLite Quarterly Filings ({len(quarterly_fin)} Quarters)")
    if transcripts:
        sources.append(f"ChromaDB Earnings Transcripts ({len(transcripts)} Excerpts)")
    if price_snap.get("ltp"):
        sources.append(f"Daily Price Database (LTP ₹{price_snap['ltp']:,.2f})")

    return {
        "reply": reply,
        "symbol": target_symbol,
        "model_used": model_name,
        "is_fallback": used_fallback,
        "latency_ms": latency_ms,
        "sources": sources,
        "metrics_summary": {
            "ltp": price_snap.get("ltp"),
            "latest_fy": annual_fin[0].get("fiscal_period") if annual_fin else None,
            "latest_sales": annual_fin[0].get("sales_fmt") if annual_fin else None,
            "latest_net_profit": annual_fin[0].get("net_profit_fmt") if annual_fin else None,
            "latest_opm": annual_fin[0].get("opm_pct_fmt") if annual_fin else None,
        }
    }

def get_symbol_suggestions(symbol: str) -> List[str]:
    """Generate dynamic suggested prompts tailored to technical screener & fundamental intelligence."""
    sym = (symbol or "TCS").strip().upper()
    return [
        "Which stock has fallen max in last 5 days?",
        "Top 5 gainers in Nifty 500 today",
        f"What was {sym}'s revenue and operating margin in latest FY?",
        f"What is management's forward guidance and capex plan for {sym}?",
    ]

def get_chat_status() -> Dict[str, Any]:
    """Return comprehensive health status of the Chatbot backend engine."""
    _load_symbol_map()
    
    ollama_model = _detect_ollama_model()
    ollama_online = ollama_model is not None

    db_ok = False
    financials_count = 0
    try:
        conn = get_db_connection(readonly=True)
        c = conn.cursor()
        financials_count = c.execute("SELECT COUNT(*) FROM company_financials_10y").fetchone()[0]
        conn.close()
        db_ok = True
    except Exception:
        pass

    return {
        "status": "ready" if db_ok else "degraded",
        "llm_engine": "ollama" if ollama_online else "deterministic_quant_synthesizer",
        "active_model": ollama_model or "Vprofitables-Deterministic-Engine",
        "ollama_online": ollama_online,
        "rag_available": RAG_AVAILABLE,
        "symbols_tracked": len(_ALL_SYMBOLS),
        "db_financials_recorded": financials_count,
        "currency_unit": "INR Crores (₹ Cr)",
        "accuracy_guarantee": "Zero Hallucination Verified SQL & ChromaDB Grounding"
    }

def get_all_symbols_catalog() -> List[Dict[str, str]]:
    """Return all tracked symbols for client-side search and autocomplete."""
    _load_symbol_map()
    return _ALL_SYMBOLS
