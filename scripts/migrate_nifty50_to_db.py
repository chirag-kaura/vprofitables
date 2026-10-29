"""
scripts/migrate_nifty50_to_db.py
================================
Head of Database Engineering Migration Script.
Migrates Nifty50 10-year financials and concall transcripts into:
  1. market_data_v2.db -> company_financials_10y (structured tabular SQL)
  2. market_data_v2.db -> document_registry (content-addressable ledger)
  3. chroma_db/ -> concall_transcripts (vector database for AI chatbot)
Zero duplication, 100% idempotent.
"""

import os
import sys
import re
import glob
import hashlib
import sqlite3
import pandas as pd
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.paths import DB_PATH, BASE_DIR
from core.rag_engine import (
    _get_collection, _get_embedder, _extract_text_from_pdf_bytes,
    chunk_transcript, _sha
)

def init_tables(conn: sqlite3.Connection):
    """Create normalized schema in market_data_v2.db with strict primary keys and indexes."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS document_registry (
        doc_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol          TEXT NOT NULL,
        doc_type        TEXT NOT NULL,          -- 'transcript', 'financial_statement'
        fiscal_period   TEXT NOT NULL,          -- '2024-03-31', '2024-Q3'
        source_url      TEXT DEFAULT '',
        content_hash    TEXT UNIQUE NOT NULL,   -- SHA-256
        chunk_count     INTEGER DEFAULT 0,
        file_size_bytes INTEGER DEFAULT 0,
        ingested_at     TEXT DEFAULT (datetime('now', 'localtime')),
        UNIQUE(symbol, doc_type, fiscal_period)
    );
    CREATE INDEX IF NOT EXISTS idx_dr_symbol ON document_registry(symbol);
    CREATE INDEX IF NOT EXISTS idx_dr_hash ON document_registry(content_hash);

    CREATE TABLE IF NOT EXISTS company_financials_10y (
        symbol              TEXT NOT NULL,
        fiscal_period       TEXT NOT NULL,       -- 'YYYY-MM-DD'
        period_type         TEXT NOT NULL,       -- 'ANNUAL' or 'QUARTERLY'
        sales               REAL,
        expenses            REAL,
        operating_profit    REAL,
        opm_pct             REAL,
        other_income        REAL,
        depreciation        REAL,
        interest            REAL,
        profit_before_tax   REAL,
        tax                 REAL,
        net_profit          REAL,
        eps                 REAL,
        dividend_amount     REAL,
        equity_share_capital REAL,
        reserves            REAL,
        borrowings          REAL,
        other_liabilities   REAL,
        total_liabilities   REAL,
        net_block           REAL,
        cwip                REAL,
        investments         REAL,
        other_assets        REAL,
        total_assets        REAL,
        receivables         REAL,
        inventory           REAL,
        cash_bank           REAL,
        operating_cash_flow REAL,
        investing_cash_flow REAL,
        financing_cash_flow REAL,
        net_cash_flow       REAL,
        updated_at          TEXT DEFAULT (datetime('now', 'localtime')),
        PRIMARY KEY (symbol, fiscal_period, period_type)
    ) WITHOUT ROWID;
    CREATE INDEX IF NOT EXISTS idx_cf_sym ON company_financials_10y(symbol);
    CREATE INDEX IF NOT EXISTS idx_cf_sym_period ON company_financials_10y(symbol, fiscal_period);
    """)
    conn.commit()
    print("  [DB] document_registry and company_financials_10y verified in market_data_v2.db")

def parse_num(val) -> Optional[float]:
    if pd.isna(val) or val is None:
        return None
    s = str(val).replace(',', '').replace('%', '').strip()
    try:
        return float(s)
    except ValueError:
        return None

def parse_csv_financials(csv_path: str, symbol: str) -> List[Dict]:
    """Parse Screener 10-year CSV into normalized dict records for SQL insertion."""
    df = pd.read_csv(csv_path, header=None)
    sections = {}
    for i, val in enumerate(df[0]):
        sval = str(val).strip().upper()
        if sval in ['PROFIT & LOSS', 'QUARTERS', 'BALANCE SHEET', 'CASH FLOW:']:
            sections[sval] = i

    records = {}

    def get_section_dates(section_idx):
        date_row = df.iloc[section_idx + 1]
        dates = {}
        for col in range(1, len(date_row)):
            raw = str(date_row[col]).strip()
            # Normalize to YYYY-MM-DD
            m = re.search(r'(\d{4}-\d{2}-\d{2})', raw)
            if m:
                dates[col] = m.group(1)
        return dates

    # 1. Annual Profit & Loss
    if 'PROFIT & LOSS' in sections:
        s_idx = sections['PROFIT & LOSS']
        dates = get_section_dates(s_idx)
        end_idx = sections.get('QUARTERS', sections.get('BALANCE SHEET', len(df)))
        for col, dt in dates.items():
            key = (symbol, dt, 'ANNUAL')
            records.setdefault(key, {'symbol': symbol, 'fiscal_period': dt, 'period_type': 'ANNUAL'})
            for r in range(s_idx + 2, end_idx):
                label = str(df.iloc[r, 0]).strip().lower()
                val = parse_num(df.iloc[r, col])
                if 'sales' in label: records[key]['sales'] = val
                elif 'other income' in label: records[key]['other_income'] = val
                elif 'depreciation' in label: records[key]['depreciation'] = val
                elif 'interest' in label: records[key]['interest'] = val
                elif 'profit before tax' in label: records[key]['profit_before_tax'] = val
                elif label == 'tax': records[key]['tax'] = val
                elif 'net profit' in label: records[key]['net_profit'] = val
                elif 'dividend' in label: records[key]['dividend_amount'] = val

    # 2. Quarterly Profit & Loss
    if 'QUARTERS' in sections:
        s_idx = sections['QUARTERS']
        dates = get_section_dates(s_idx)
        end_idx = sections.get('BALANCE SHEET', len(df))
        for col, dt in dates.items():
            key = (symbol, dt, 'QUARTERLY')
            records.setdefault(key, {'symbol': symbol, 'fiscal_period': dt, 'period_type': 'QUARTERLY'})
            for r in range(s_idx + 2, end_idx):
                label = str(df.iloc[r, 0]).strip().lower()
                val = parse_num(df.iloc[r, col])
                if 'sales' in label: records[key]['sales'] = val
                elif 'expenses' in label: records[key]['expenses'] = val
                elif 'operating profit' in label: records[key]['operating_profit'] = val
                elif 'other income' in label: records[key]['other_income'] = val
                elif 'depreciation' in label: records[key]['depreciation'] = val
                elif 'interest' in label: records[key]['interest'] = val
                elif 'profit before tax' in label: records[key]['profit_before_tax'] = val
                elif label == 'tax': records[key]['tax'] = val
                elif 'net profit' in label: records[key]['net_profit'] = val

    # 3. Annual Balance Sheet
    if 'BALANCE SHEET' in sections:
        s_idx = sections['BALANCE SHEET']
        dates = get_section_dates(s_idx)
        end_idx = sections.get('CASH FLOW:', len(df))
        for col, dt in dates.items():
            key = (symbol, dt, 'ANNUAL')
            records.setdefault(key, {'symbol': symbol, 'fiscal_period': dt, 'period_type': 'ANNUAL'})
            for r in range(s_idx + 2, end_idx):
                label = str(df.iloc[r, 0]).strip().lower()
                val = parse_num(df.iloc[r, col])
                if 'equity share capital' in label: records[key]['equity_share_capital'] = val
                elif 'reserves' in label: records[key]['reserves'] = val
                elif 'borrowings' in label: records[key]['borrowings'] = val
                elif 'other liabilities' in label: records[key]['other_liabilities'] = val
                elif label == 'total' and 'total_liabilities' not in records[key]: records[key]['total_liabilities'] = val
                elif 'net block' in label: records[key]['net_block'] = val
                elif 'capital work in progress' in label or 'cwip' in label: records[key]['cwip'] = val
                elif 'investments' in label: records[key]['investments'] = val
                elif 'other assets' in label: records[key]['other_assets'] = val
                elif label == 'total' and 'total_assets' not in records[key]: records[key]['total_assets'] = val
                elif 'receivables' in label: records[key]['receivables'] = val
                elif 'inventory' in label: records[key]['inventory'] = val
                elif 'cash & bank' in label: records[key]['cash_bank'] = val

    # 4. Annual Cash Flow
    if 'CASH FLOW:' in sections:
        s_idx = sections['CASH FLOW:']
        dates = get_section_dates(s_idx)
        end_idx = len(df)
        for col, dt in dates.items():
            key = (symbol, dt, 'ANNUAL')
            records.setdefault(key, {'symbol': symbol, 'fiscal_period': dt, 'period_type': 'ANNUAL'})
            for r in range(s_idx + 2, end_idx):
                label = str(df.iloc[r, 0]).strip().lower()
                val = parse_num(df.iloc[r, col])
                if 'operating activity' in label: records[key]['operating_cash_flow'] = val
                elif 'investing activity' in label: records[key]['investing_cash_flow'] = val
                elif 'financing activity' in label: records[key]['financing_cash_flow'] = val
                elif 'net cash flow' in label: records[key]['net_cash_flow'] = val

    return list(records.values())

def migrate_all_financials(conn: sqlite3.Connection, base_dir: str):
    """Scan and migrate all 10-year CSVs into company_financials_10y and document_registry."""
    csv_files = glob.glob(os.path.join(base_dir, "*", "4_Financial_Statements", "*_10Yr_Financial_Statements.csv"))
    print(f"\n--- Migrating {len(csv_files)} Company Financial Statements ---")

    insert_sql = """
    INSERT INTO company_financials_10y (
        symbol, fiscal_period, period_type, sales, expenses, operating_profit, opm_pct,
        other_income, depreciation, interest, profit_before_tax, tax, net_profit,
        dividend_amount, equity_share_capital, reserves, borrowings, other_liabilities,
        total_liabilities, net_block, cwip, investments, other_assets, total_assets,
        receivables, inventory, cash_bank, operating_cash_flow, investing_cash_flow,
        financing_cash_flow, net_cash_flow
    ) VALUES (
        :symbol, :fiscal_period, :period_type, :sales, :expenses, :operating_profit, :opm_pct,
        :other_income, :depreciation, :interest, :profit_before_tax, :tax, :net_profit,
        :dividend_amount, :equity_share_capital, :reserves, :borrowings, :other_liabilities,
        :total_liabilities, :net_block, :cwip, :investments, :other_assets, :total_assets,
        :receivables, :inventory, :cash_bank, :operating_cash_flow, :investing_cash_flow,
        :financing_cash_flow, :net_cash_flow
    )
    ON CONFLICT(symbol, fiscal_period, period_type) DO UPDATE SET
        sales=excluded.sales, net_profit=excluded.net_profit, updated_at=datetime('now', 'localtime')
    """

    ledger_sql = """
    INSERT INTO document_registry (
        symbol, doc_type, fiscal_period, content_hash, file_size_bytes
    ) VALUES (?, 'financial_statement', ?, ?, ?)
    ON CONFLICT(symbol, doc_type, fiscal_period) DO NOTHING
    """

    total_records = 0
    for path in csv_files:
        symbol = os.path.basename(path).replace("_10Yr_Financial_Statements.csv", "")
        with open(path, "rb") as f:
            content = f.read()
        f_hash = hashlib.sha256(content).hexdigest()
        f_size = len(content)

        records = parse_csv_financials(path, symbol)
        for rec in records:
            # Set defaults for missing keys
            for col in ['sales', 'expenses', 'operating_profit', 'opm_pct', 'other_income',
                        'depreciation', 'interest', 'profit_before_tax', 'tax', 'net_profit',
                        'dividend_amount', 'equity_share_capital', 'reserves', 'borrowings',
                        'other_liabilities', 'total_liabilities', 'net_block', 'cwip',
                        'investments', 'other_assets', 'total_assets', 'receivables',
                        'inventory', 'cash_bank', 'operating_cash_flow', 'investing_cash_flow',
                        'financing_cash_flow', 'net_cash_flow']:
                rec.setdefault(col, None)
            conn.execute(insert_sql, rec)
            total_records += 1

        # Register in ledger
        latest_period = max([r['fiscal_period'] for r in records]) if records else '10Y'
        conn.execute(ledger_sql, (symbol, latest_period, f_hash, f_size))

    conn.commit()
    print(f"  [SUCCESS] Migrated {total_records} financial period rows into company_financials_10y")

def migrate_transcripts_to_chroma(conn: sqlite3.Connection, base_dir: str, max_per_company: int = 2):
    """Extract and embed transcripts into ChromaDB and document_registry."""
    print(f"\n--- Migrating Latest Concall Transcripts into ChromaDB & Document Registry ---")
    
    col = _get_collection()
    model = _get_embedder()

    comp_dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    total_docs = 0
    total_chunks = 0

    ledger_sql = """
    INSERT INTO document_registry (
        symbol, doc_type, fiscal_period, source_url, content_hash, chunk_count, file_size_bytes
    ) VALUES (?, 'transcript', ?, ?, ?, ?, ?)
    ON CONFLICT(symbol, doc_type, fiscal_period) DO NOTHING
    """

    for symbol in sorted(comp_dirs):
        ec_dir = os.path.join(base_dir, symbol, "3_Earning_Calls")
        if not os.path.isdir(ec_dir):
            continue

        pdfs = sorted(glob.glob(os.path.join(ec_dir, "*.pdf")), reverse=True)[:max_per_company]
        for pdf_path in pdfs:
            fname = os.path.basename(pdf_path)
            with open(pdf_path, "rb") as f:
                raw_bytes = f.read()

            f_hash = hashlib.sha256(raw_bytes).hexdigest()
            f_size = len(raw_bytes)

            # Check if hash already ingested
            existing = conn.execute("SELECT doc_id FROM document_registry WHERE content_hash=?", (f_hash,)).fetchone()
            if existing:
                continue

            # Extract fiscal period from filename (e.g. Sep_2024 or 2024)
            m = re.search(r'([A-Za-z]{3}_\d{4}|\d{4})', fname)
            period = m.group(1).replace('_', ' ') if m else 'Recent'

            text = _extract_text_from_pdf_bytes(raw_bytes)
            if not text or len(text) < 200:
                continue

            chunks = chunk_transcript(text, symbol)
            if not chunks:
                continue

            # Add fiscal period to chunk IDs and metadata
            for i, c in enumerate(chunks):
                c["chunk_id"] = f"{symbol}_transcript_{f_hash[:8]}_{i}"
                c["fiscal_period"] = period

            # Embed and upsert into ChromaDB
            texts = [c["text"] for c in chunks]
            ids = [c["chunk_id"] for c in chunks]
            metas = [{k: str(v) for k, v in c.items() if k != "text"} for c in chunks]
            embs = model.encode(texts, show_progress_bar=False, batch_size=32).tolist()

            col.upsert(
                ids=ids,
                documents=texts,
                embeddings=embs,
                metadatas=metas
            )

            conn.execute(ledger_sql, (symbol, period, fname, f_hash, len(chunks), f_size))
            total_docs += 1
            total_chunks += len(chunks)

        conn.commit()

    print(f"  [SUCCESS] Ingested {total_docs} transcripts ({total_chunks} chunks) into ChromaDB")

def main():
    base_dir = r"D:\VPROFITABLES\vprofitables\Nifty50_Complete_Data"
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    print("=" * 65)
    print("  GANN-ASTRO v3.9 — Phase 1: Database Migration & RAG Seeding")
    print("=" * 65)

    init_tables(conn)
    migrate_all_financials(conn, base_dir)
    migrate_transcripts_to_chroma(conn, base_dir, max_per_company=2)

    # Verification query
    fin_count = conn.execute("SELECT count(*) FROM company_financials_10y").fetchone()[0]
    sym_count = conn.execute("SELECT count(DISTINCT symbol) FROM company_financials_10y").fetchone()[0]
    doc_count = conn.execute("SELECT count(*) FROM document_registry").fetchone()[0]

    print("\n" + "=" * 65)
    print("  MIGRATION VERIFICATION STATS:")
    print(f"  - Total Financial Periods Stored : {fin_count:,} rows")
    print(f"  - Unique Companies with 10Y Data : {sym_count} companies")
    print(f"  - Total Documents in Registry    : {doc_count:,} documents")
    print("=" * 65 + "\n")

    conn.close()

if __name__ == "__main__":
    main()
