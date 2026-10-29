"""
core/screener_sync.py
=====================
Enterprise Continuous Ingestion Engine for Screener.in Fundamentals & Concall Transcripts.
Features:
  1. 100% Public HTML Parsing: Zero session/cookie dependency for financial tables.
  2. Sector-Adaptive Schema: Automatically normalizes Corporate and Banking/NBFC rows.
  3. Deterministic Fiscal Dates: Standardized quarters (e.g. '2025-Q2'), never 'Recent'.
  4. Speaker Attribution: Explicit [SPEAKER: EXECUTIVE / ANALYST] tagging in ChromaDB.
  5. Currency Magnitude: Stores unit multiplier ('INR_CRORES') for LLM accuracy.
  6. Idempotent Ingestion Ledger: Tracks SHA-256 hashes in document_registry.
  7. In-Memory Streaming: Zero loose PDF/Excel files written to disk.
"""

import os
import sys
import io
import re
import time
import random
import hashlib
import argparse
import sqlite3
import requests
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.paths import DB_PATH, BASE_DIR, get_db_connection
from core.rag_engine import (
    _get_collection, _get_embedder, _extract_text_from_pdf_bytes,
    chunk_transcript, extract_fiscal_period, init_rag_tables
)
from data.instruments import ALL_INSTRUMENTS

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

# ── Date Normalizer ────────────────────────────────────────────────────────────
def normalize_table_date(date_str: str) -> Optional[str]:
    """Convert 'Mar 2024' or 'Sep 2023' into standard ISO 'YYYY-MM-DD'."""
    date_str = date_str.strip()
    month_map = {
        'jan': '01-31', 'feb': '02-28', 'mar': '03-31', 'apr': '04-30',
        'may': '05-31', 'jun': '06-30', 'jul': '07-31', 'aug': '08-31',
        'sep': '09-30', 'oct': '10-31', 'nov': '11-30', 'dec': '12-31'
    }
    m = re.search(r'([A-Za-z]{3})\s+(\d{4})', date_str)
    if m:
        mon = m.group(1).lower()
        yr = m.group(2)
        day_part = month_map.get(mon, '03-31')
        return f"{yr}-{day_part}"
    if 'ttm' in date_str.lower():
        return 'TTM'
    return None

def parse_num(val) -> Optional[float]:
    if pd.isna(val) or val is None:
        return None
    s = str(val).replace(',', '').replace('%', '').strip()
    try:
        return float(s)
    except ValueError:
        return None

# ── Public HTML Financial Tables Parser ────────────────────────────────────────
def parse_html_financials(soup: BeautifulSoup, symbol: str) -> List[Dict[str, Any]]:
    """
    Extract 10-year financials directly from 100% public HTML tables.
    Works for BOTH regular corporates and banks/NBFCs without requiring any login/cookie.
    """
    records: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    def process_section(sec_id: str, p_type: str):
        sec = soup.find('section', id=sec_id)
        if not sec:
            return
        table = sec.find('table')
        if not table:
            return

        headers = [th.text.strip() for th in table.find_all('th')]
        col_dates: Dict[int, str] = {}
        for col_idx, h in enumerate(headers):
            nd = normalize_table_date(h)
            if nd:
                col_dates[col_idx] = nd

        tbody = table.find('tbody')
        if not tbody:
            return

        for tr in tbody.find_all('tr'):
            tds = [td.text.strip().replace('\xa0', ' ') for td in tr.find_all('td')]
            if not tds:
                continue
            raw_label = tds[0].replace('+', '').strip().lower()

            for col_idx, dt in col_dates.items():
                if col_idx >= len(tds):
                    continue
                val = parse_num(tds[col_idx])
                key = (symbol, dt, p_type)
                if key not in records:
                    records[key] = {
                        'symbol': symbol,
                        'fiscal_period': dt,
                        'period_type': p_type,
                        'unit': 'INR_CRORES'
                    }

                # Corporate & Bank mapping
                if raw_label in ['sales', 'revenue', 'interest earned']:
                    records[key]['sales'] = val
                elif raw_label in ['expenses', 'financing expenses']:
                    records[key]['expenses'] = val
                elif raw_label in ['operating profit']:
                    records[key]['operating_profit'] = val
                elif raw_label in ['financing profit']:
                    records[key]['operating_profit'] = val
                    records[key]['financing_profit'] = val
                elif raw_label in ['opm %', 'financing margin %']:
                    records[key]['opm_pct'] = val
                elif raw_label in ['other income']:
                    records[key]['other_income'] = val
                elif raw_label in ['interest']:
                    records[key]['interest'] = val
                elif raw_label in ['depreciation']:
                    records[key]['depreciation'] = val
                elif raw_label in ['profit before tax']:
                    records[key]['profit_before_tax'] = val
                elif raw_label in ['tax %']:
                    records[key]['tax'] = val
                elif raw_label in ['net profit']:
                    records[key]['net_profit'] = val
                elif raw_label in ['eps in rs', 'eps']:
                    records[key]['eps'] = val
                elif raw_label in ['dividend payout %']:
                    records[key]['dividend_amount'] = val
                elif raw_label in ['equity capital', 'equity share capital']:
                    records[key]['equity_share_capital'] = val
                elif raw_label in ['reserves']:
                    records[key]['reserves'] = val
                elif raw_label in ['borrowings']:
                    records[key]['borrowings'] = val
                elif raw_label in ['other liabilities']:
                    records[key]['other_liabilities'] = val
                elif raw_label in ['total liabilities', 'total']:
                    if 'total_liabilities' not in records[key] or records[key]['total_liabilities'] is None:
                        records[key]['total_liabilities'] = val
                elif raw_label in ['fixed assets', 'net block']:
                    records[key]['net_block'] = val
                elif raw_label in ['cwip', 'capital work in progress']:
                    records[key]['cwip'] = val
                elif raw_label in ['investments']:
                    records[key]['investments'] = val
                elif raw_label in ['other assets']:
                    records[key]['other_assets'] = val
                elif raw_label in ['total assets']:
                    records[key]['total_assets'] = val
                elif raw_label in ['cash from operating activity']:
                    records[key]['operating_cash_flow'] = val
                elif raw_label in ['cash from investing activity']:
                    records[key]['investing_cash_flow'] = val
                elif raw_label in ['cash from financing activity']:
                    records[key]['financing_cash_flow'] = val
                elif raw_label in ['net cash flow']:
                    records[key]['net_cash_flow'] = val
                elif raw_label in ['gross npa %']:
                    records[key]['gross_npa_pct'] = val
                elif raw_label in ['net npa %']:
                    records[key]['net_npa_pct'] = val

    # Parse all 4 core financial tables
    process_section('profit-loss', 'ANNUAL')
    process_section('quarters', 'QUARTERLY')
    process_section('balance-sheet', 'ANNUAL')
    process_section('cash-flow', 'ANNUAL')

    return list(records.values())

# ── Core Single Symbol Sync ───────────────────────────────────────────────────
def sync_single_symbol(
    symbol: str,
    conn: sqlite3.Connection,
    col,
    model,
    session: requests.Session,
    incremental: bool = True,
    max_transcripts: int = 2
) -> Dict[str, int]:
    """
    Syncs financial statements and transcripts for one symbol.
    Uses 100% public HTML scraping with zero cookie dependencies.
    """
    stats = {'financial_periods': 0, 'transcripts': 0, 'chunks': 0}

    need_financials = True
    if incremental:
        recent_fin = conn.execute("""
            SELECT ingested_at FROM document_registry
            WHERE symbol=? AND doc_type='financial_statement'
            ORDER BY ingested_at DESC LIMIT 1
        """, (symbol,)).fetchone()
        if recent_fin:
            ingested_date = recent_fin[0][:10]
            if (pd.Timestamp.now() - pd.Timestamp(ingested_date)).days < 30:
                need_financials = False

    # 1. Fetch Company Page
    url = f"https://www.screener.in/company/{symbol}/consolidated/"
    res = session.get(url, headers=HEADERS, timeout=15)
    if res.status_code != 200:
        url = f"https://www.screener.in/company/{symbol}/"
        res = session.get(url, headers=HEADERS, timeout=15)
        if res.status_code != 200:
            return stats

    soup = BeautifulSoup(res.text, "html.parser")

    # 2. Sync Financial Statements (Direct HTML Parsing — Zero Cookie Dependency)
    if need_financials:
        records = parse_html_financials(soup, symbol)
        if records:
            insert_sql = """
            INSERT INTO company_financials_10y (
                symbol, fiscal_period, period_type, sales, expenses, operating_profit, opm_pct,
                other_income, depreciation, interest, profit_before_tax, tax, net_profit,
                eps, dividend_amount, equity_share_capital, reserves, borrowings, other_liabilities,
                total_liabilities, net_block, cwip, investments, other_assets, total_assets,
                receivables, inventory, cash_bank, operating_cash_flow, investing_cash_flow,
                financing_cash_flow, net_cash_flow, unit, financing_profit, gross_npa_pct, net_npa_pct
            ) VALUES (
                :symbol, :fiscal_period, :period_type, :sales, :expenses, :operating_profit, :opm_pct,
                :other_income, :depreciation, :interest, :profit_before_tax, :tax, :net_profit,
                :eps, :dividend_amount, :equity_share_capital, :reserves, :borrowings, :other_liabilities,
                :total_liabilities, :net_block, :cwip, :investments, :other_assets, :total_assets,
                :receivables, :inventory, :cash_bank, :operating_cash_flow, :investing_cash_flow,
                :financing_cash_flow, :net_cash_flow, :unit, :financing_profit, :gross_npa_pct, :net_npa_pct
            )
            ON CONFLICT(symbol, fiscal_period, period_type) DO UPDATE SET
                sales=excluded.sales, expenses=excluded.expenses, operating_profit=excluded.operating_profit,
                opm_pct=excluded.opm_pct, net_profit=excluded.net_profit, eps=excluded.eps,
                updated_at=datetime('now', 'localtime')
            """
            for rec in records:
                for c in ['sales', 'expenses', 'operating_profit', 'opm_pct', 'other_income',
                          'depreciation', 'interest', 'profit_before_tax', 'tax', 'net_profit',
                          'eps', 'dividend_amount', 'equity_share_capital', 'reserves', 'borrowings',
                          'other_liabilities', 'total_liabilities', 'net_block', 'cwip',
                          'investments', 'other_assets', 'total_assets', 'receivables',
                          'inventory', 'cash_bank', 'operating_cash_flow', 'investing_cash_flow',
                          'financing_cash_flow', 'net_cash_flow', 'unit', 'financing_profit',
                          'gross_npa_pct', 'net_npa_pct']:
                    rec.setdefault(c, None)
                conn.execute(insert_sql, rec)
                stats['financial_periods'] += 1

            latest_p = max([r['fiscal_period'] for r in records if r['fiscal_period'] != 'TTM']) if records else '10Y'
            # Sync Shareholding Pattern (FII, DII, Promoter Pledging)
            try:
                from core.shareholding_engine import parse_and_store_shareholding
                sh_count = parse_and_store_shareholding(res.text, symbol)
                if sh_count:
                    stats['shareholding_periods'] = sh_count
            except Exception as _she:
                pass

            html_hash = hashlib.sha256(res.text.encode('utf-8')).hexdigest()
            conn.execute("""
                INSERT INTO document_registry (
                    symbol, doc_type, fiscal_period, content_hash, file_size_bytes
                ) VALUES (?, 'financial_statement', ?, ?, ?)
                ON CONFLICT(symbol, doc_type, fiscal_period) DO NOTHING
            """, (symbol, latest_p, html_hash, len(res.text)))

    # 3. Sync Concall Transcripts (In-Memory Stream to ChromaDB with Speaker Attribution)
    docs_div = soup.find(id="documents")
    if docs_div:
        links = docs_div.find_all("a", href=True)
        transcript_count = 0

        for a in links:
            text = a.text.strip()
            if "Transcript" not in text:
                continue

            doc_url = a['href']
            if doc_url.startswith('/'):
                doc_url = "https://www.screener.in" + doc_url

            # Extract date tag from row
            row_date = ""
            parent_row = a.find_parent("div", class_="flex-row")
            if parent_row:
                date_div = parent_row.find("div", class_="ink-600")
                if date_div:
                    row_date = date_div.text.strip()

            period = extract_fiscal_period(text, row_date)

            # Check registry first by (symbol, period)
            already_indexed = conn.execute("""
                SELECT doc_id FROM document_registry
                WHERE symbol=? AND doc_type='transcript' AND fiscal_period=?
            """, (symbol, period)).fetchone()

            if already_indexed:
                continue

            # Stream PDF directly into RAM
            try:
                pdf_res = session.get(doc_url, headers=HEADERS, timeout=20)
                if pdf_res.status_code == 200 and len(pdf_res.content) > 1000:
                    raw_bytes = pdf_res.content
                    f_hash = hashlib.sha256(raw_bytes).hexdigest()

                    # Deduplication check by hash
                    if conn.execute("SELECT doc_id FROM document_registry WHERE content_hash=?", (f_hash,)).fetchone():
                        continue

                    pdf_text = _extract_text_from_pdf_bytes(raw_bytes)
                    if pdf_text and len(pdf_text) > 200:
                        # Refine fiscal period from actual PDF text header
                        period = extract_fiscal_period(pdf_text[:800], period)
                        chunks = chunk_transcript(pdf_text, symbol)
                        if chunks:
                            for idx, c in enumerate(chunks):
                                c["chunk_id"] = f"{symbol}_transcript_{f_hash[:8]}_{idx}"
                                c["fiscal_period"] = period

                            texts = [c["text"] for c in chunks]
                            ids = [c["chunk_id"] for c in chunks]
                            metas = [{k: str(v) for k, v in c.items() if k != "text"} for c in chunks]
                            embs = model.encode(texts, show_progress_bar=False, batch_size=32).tolist()

                            col.upsert(ids=ids, documents=texts, embeddings=embs, metadatas=metas)

                            conn.execute("""
                                INSERT INTO document_registry (
                                    symbol, doc_type, fiscal_period, source_url, content_hash, chunk_count, file_size_bytes
                                ) VALUES (?, 'transcript', ?, ?, ?, ?, ?)
                                ON CONFLICT(symbol, doc_type, fiscal_period) DO NOTHING
                            """, (symbol, period, doc_url, f_hash, len(chunks), len(raw_bytes)))

                            stats['transcripts'] += 1
                            stats['chunks'] += len(chunks)
                            transcript_count += 1
                            if transcript_count >= max_transcripts:
                                break
            except Exception:
                pass

    conn.commit()
    return stats

# ── Main Orchestrator ─────────────────────────────────────────────────────────
def run_sync(
    symbols: Optional[List[str]] = None,
    limit: Optional[int] = None,
    incremental: bool = True
):
    conn = get_db_connection(readonly=False)
    col = _get_collection()
    model = _get_embedder()
    session = requests.Session()

    if not symbols:
        all_equities = [k for k, v in ALL_INSTRUMENTS.items() if getattr(v, 'instrument_type', '') == 'EQUITY']
        target_symbols = all_equities
    else:
        target_symbols = symbols

    if limit:
        target_symbols = target_symbols[:limit]

    print("=" * 65)
    print(f"  GANN-ASTRO v3.9 — Screener Public HTML Sync & RAG Engine")
    print(f"  Target Scope : {len(target_symbols)} Equities")
    print(f"  Mode         : {'INCREMENTAL (30-day delta)' if incremental else 'FULL REFRESH'}")
    print("=" * 65)

    total_periods = 0
    total_transcripts = 0
    total_chunks = 0

    for i, symbol in enumerate(target_symbols):
        try:
            print(f"  [{i+1}/{len(target_symbols)}] Syncing {symbol:<12} ...", end=" ", flush=True)
            stats = sync_single_symbol(
                symbol=symbol,
                conn=conn,
                col=col,
                model=model,
                session=session,
                incremental=incremental
            )
            total_periods += stats['financial_periods']
            total_transcripts += stats['transcripts']
            total_chunks += stats['chunks']

            summary = []
            if stats['financial_periods'] > 0: summary.append(f"+{stats['financial_periods']} periods")
            if stats['transcripts'] > 0: summary.append(f"+{stats['transcripts']} transcripts ({stats['chunks']} chunks)")
            status_text = ", ".join(summary) if summary else "Up to date"
            print(f"[{status_text}]")

            time.sleep(random.uniform(1.2, 2.0))

        except Exception as e:
            print(f"[ERROR: {e}]")

    print("\n" + "=" * 65)
    print("  SYNC COMPLETED:")
    print(f"  - Financial Periods Synced : {total_periods:,}")
    print(f"  - Transcripts Ingested     : {total_transcripts:,}")
    print(f"  - Vector Chunks Added      : {total_chunks:,}")
    print("=" * 65 + "\n")

    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Continuous Screener Fundamentals & Transcript Ingestion")
    parser.add_argument("--symbols", type=str, help="Comma-separated symbols (e.g. TCS,RELIANCE)")
    parser.add_argument("--limit", type=int, help="Limit number of symbols")
    parser.add_argument("--force", action="store_true", help="Force full sync ignoring TTL")
    args = parser.parse_args()

    syms = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else None
    run_sync(symbols=syms, limit=args.limit, incremental=not args.force)
