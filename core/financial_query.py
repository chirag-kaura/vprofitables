"""
core/financial_query.py
=======================
Enterprise Query Engine for AI Assistant Chatbot.
Provides:
  1. Exact SQL tabular fact retrieval with formatted INR Crores strings (Zero Hallucinations)
  2. Filtered Semantic Transcript Search with Executive / Analyst role attribution
  3. Hybrid Context Assembler for LLM prompts
"""

import os
import sys
import re
import sqlite3
import pandas as pd
from typing import Dict, List, Optional, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.paths import get_db_connection
from core.rag_engine import _get_collection, _get_embedder

# Currency formatting invariant contract
FINANCIAL_UNIT_CONTRACT = (
    "All financial statement metrics (Sales, Expenses, Profit, Cash Flow, Assets, Debt) "
    "are denominated in INR Crores (₹ Cr). Per-share metrics (EPS, Dividend per share) "
    "are in Indian Rupees (₹). Percentages (OPM, ROCE, Tax) are formatted with %."
)

def format_crores(val: Optional[float]) -> str:
    """Format float into readable Indian Crores notation (e.g. ₹1,05,578 Cr)."""
    if val is None or pd.isna(val):
        return "N/A"
    abs_val = abs(val)
    sign = "-" if val < 0 else ""
    return f"{sign}₹{abs_val:,.2f} Cr"

def format_inr(val: Optional[float]) -> str:
    """Format per-share values in INR (e.g. ₹42.50)."""
    if val is None or pd.isna(val):
        return "N/A"
    return f"₹{val:,.2f}"

def format_pct(val: Optional[float]) -> str:
    """Format percentages (e.g. 15.2%)."""
    if val is None or pd.isna(val):
        return "N/A"
    return f"{val:.1f}%"

def get_company_financials(
    symbol: str,
    period_type: str = "ANNUAL",
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Retrieve audited financial statements from SQLite.
    Returns list of dicts with exact float values and human-readable formatted strings.
    """
    symbol = symbol.strip().upper()
    period_type = period_type.strip().upper()

    conn = get_db_connection(readonly=True)
    cursor = conn.cursor()

    query = """
    SELECT
        symbol, fiscal_period, period_type, sales, expenses, operating_profit, opm_pct,
        other_income, depreciation, interest, profit_before_tax, tax, net_profit,
        eps, dividend_amount, equity_share_capital, reserves, borrowings, other_liabilities,
        total_liabilities, net_block, cwip, investments, other_assets, total_assets,
        receivables, inventory, cash_bank, operating_cash_flow, investing_cash_flow,
        financing_cash_flow, net_cash_flow, financing_profit, unit
    FROM company_financials_10y
    WHERE symbol = ? AND period_type = ?
    ORDER BY fiscal_period DESC
    LIMIT ?
    """
    rows = cursor.execute(query, (symbol, period_type, limit)).fetchall()
    cols = [col[0] for col in cursor.description]
    conn.close()

    results = []
    for r in rows:
        row_dict = dict(zip(cols, r))
        
        # 1. Dynamic derivation of Operating Profit & Margin if missing from primary table
        sales = row_dict.get("sales")
        expenses = row_dict.get("expenses")
        op_profit = row_dict.get("operating_profit")
        opm = row_dict.get("opm_pct")
        
        if (op_profit is None or pd.isna(op_profit)) and sales is not None and expenses is not None:
            op_profit = sales - expenses
            row_dict["operating_profit"] = op_profit

        if (opm is None or pd.isna(opm)) and op_profit is not None and sales and sales > 0:
            opm = round((op_profit / sales) * 100, 2)
            row_dict["opm_pct"] = opm

        # Add formatted strings for LLM injection
        row_dict["sales_fmt"] = format_crores(row_dict.get("sales"))
        row_dict["operating_profit_fmt"] = format_crores(row_dict.get("operating_profit"))
        row_dict["net_profit_fmt"] = format_crores(row_dict.get("net_profit"))
        row_dict["operating_cash_flow_fmt"] = format_crores(row_dict.get("operating_cash_flow"))
        row_dict["borrowings_fmt"] = format_crores(row_dict.get("borrowings"))
        row_dict["total_assets_fmt"] = format_crores(row_dict.get("total_assets"))
        row_dict["eps_fmt"] = format_inr(row_dict.get("eps"))
        row_dict["opm_pct_fmt"] = format_pct(row_dict.get("opm_pct"))
        row_dict["unit_contract"] = FINANCIAL_UNIT_CONTRACT
        results.append(row_dict)

    return results

# Regex patterns identifying non-informational boilerplate, legal headers, and corporate addresses
_BOILERPLATE_REGEX = re.compile(
    r"(trading\s+symbol\s*:\s*[A-Z]+|"
    r"regulation\s+30|"
    r"securities\s+and\s+exchange\s+board|"
    r"listing\s+obligations|"
    r"regd\.?\s*office\s*:|"
    r"maker\s+chambers|"
    r"nariman\s+point|"
    r"cin\s*[-:]|"
    r"phone\s*#|"
    r"telefax|"
    r"safe\s*harbor|"
    r"forward-looking\s*statement|"
    r"listen-only\s*mode|"
    r"moderator|"
    r"dear\s*sirs?|"
    r"bse\s*limited|"
    r"national\s*stock\s*exchange|"
    r"meeting\s+audio\s*:|"
    r"presentation\s+link\s*:|"
    r"does\s*not\s*constitute\s*an\s*offer)",
    re.IGNORECASE
)

_PDF_BINARY_REGEX = re.compile(
    r"(%PDF-\d|endobj|FlateDecode|XRef|/Filter|/Length|/Index|>>stream)",
    re.IGNORECASE
)

def is_clean_transcript_chunk(text: str) -> bool:
    """Check if a chunk contains substantive operational commentary rather than legal boilerplate or corrupt binary."""
    if not text or len(text.strip()) < 80:
        return False
    # 1. Reject binary PDF stream dumps
    if _PDF_BINARY_REGEX.search(text):
        return False
    # 2. Reject non-printable binary bytes
    printable = sum(1 for ch in text if ch.isprintable() or ch in '\n\r\t ')
    if (printable / len(text)) < 0.92:
        return False
    # 3. Reject regulatory boilerplate
    if _BOILERPLATE_REGEX.search(text):
        return False
    return True

def sanitize_speaker_label(role: str, name: str) -> Tuple[str, str]:
    """Clean verbose raw speaker labels into standard human-readable tags."""
    role_clean = (role or "EXECUTIVE").strip().upper()
    name_clean = (name or "Management").strip()
    
    if "TRADING SYMBOL" in name_clean.upper() or "SPEAKER" in name_clean.upper():
        name_clean = "Management"
    if role_clean not in {"EXECUTIVE", "ANALYST", "OPERATOR"}:
        role_clean = "EXECUTIVE"
    return role_clean, name_clean

def get_transcript_guidance(
    symbol: str,
    query: str,
    k: int = 3,
    executive_only: bool = True,
    fiscal_period: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve semantic chunks from ChromaDB with speaker attribution and strict boilerplate filtering.
    Optionally filter to EXECUTIVE statements only.
    """
    symbol = symbol.strip().upper()
    col = _get_collection()
    model = _get_embedder()

    q_emb = model.encode([query]).tolist()

    # Build metadata filter
    filters = [{"symbol": symbol}]
    if executive_only:
        filters.append({"speaker_role": "EXECUTIVE"})
    if fiscal_period:
        filters.append({"fiscal_period": fiscal_period})

    where_clause = {"$and": filters} if len(filters) > 1 else filters[0]

    # Query more results to allow filtering out boilerplate chunks
    fetch_k = max(k * 4, 12)
    try:
        res = col.query(
            query_embeddings=q_emb,
            n_results=fetch_k,
            where=where_clause
        )
    except Exception:
        # Fallback if specific where filter is too restrictive
        res = col.query(
            query_embeddings=q_emb,
            n_results=fetch_k,
            where={"symbol": symbol}
        )

    retrieved = []
    if res and res.get("documents"):
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            chunk_sym = (meta.get("symbol") or "").strip().upper()
            if chunk_sym and chunk_sym != symbol:
                continue  # STRICT ENTITY MATCH: Reject cross-entity chunks

            raw_role = (meta.get("speaker_role") or "").strip().upper()
            if raw_role in ("OPERATOR", "ANALYST"):
                continue  # NEVER quote external analysts or conference call operators as company guidance

            if not is_clean_transcript_chunk(doc):
                continue
            role, speaker = sanitize_speaker_label(meta.get("speaker_role", ""), meta.get("speaker_name", ""))
            
            # Clean leading bracket speaker prefixes if embedded in doc
            clean_text = re.sub(r"^\[SPEAKER:[^\]]+\]\s*", "", doc).strip()
            
            retrieved.append({
                "symbol": meta.get("symbol", symbol),
                "fiscal_period": meta.get("fiscal_period", "N/A"),
                "speaker_role": role,
                "speaker_name": speaker,
                "excerpt": clean_text,
                "relevance_score": round(1.0 - float(dist), 3) if dist is not None else 1.0
            })

    # Prioritize EXECUTIVE statements over OPERATOR/ANALYST
    role_priority = {"EXECUTIVE": 0, "ANALYST": 1, "OPERATOR": 2}
    retrieved.sort(key=lambda x: (role_priority.get(x["speaker_role"], 1), -x["relevance_score"]))
    return retrieved[:k]

def assemble_chatbot_context(symbol: str, user_question: str) -> Dict[str, Any]:
    """
    Unified router that prepares both verified SQL numbers and transcript quotes
    ready for direct LLM synthesis.
    """
    annual_fin = get_company_financials(symbol, period_type="ANNUAL", limit=3)
    quarterly_fin = get_company_financials(symbol, period_type="QUARTERLY", limit=4)
    transcript_quotes = get_transcript_guidance(symbol, user_question, k=3, executive_only=False)

    return {
        "symbol": symbol,
        "financial_unit_rule": FINANCIAL_UNIT_CONTRACT,
        "annual_financials": annual_fin,
        "quarterly_financials": quarterly_fin,
        "executive_transcripts": transcript_quotes
    }
