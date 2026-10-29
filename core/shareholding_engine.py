"""
core/shareholding_engine.py
===========================
Quarterly Shareholding & Promoter Pledging Pattern Engine.
Tracks smart money ownership:
  - FII & DII QoQ accumulation vs distribution
  - Promoter Pledging % increases (leading crash / default warning)
"""

import os
import sys
import re
import sqlite3
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.paths import get_db_connection

def ensure_shareholding_table():
    conn = get_db_connection(timeout=30.0)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS company_shareholding_quarterly (
            symbol TEXT NOT NULL,
            fiscal_period TEXT NOT NULL,
            promoter_pct REAL,
            fii_pct REAL,
            dii_pct REAL,
            public_pct REAL,
            pledged_pct REAL,
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            PRIMARY KEY (symbol, fiscal_period)
        )
    """)
    conn.commit()
    conn.close()

def parse_shareholding_html(html: str, symbol: str) -> List[Tuple]:
    """
    Pure HTML parser: Extracts quarterly shareholding rows into tuples.
    Zero database dependencies or locks.
    """
    soup = BeautifulSoup(html, "html.parser")
    section = soup.find("section", id="shareholding")
    if not section:
        return []

    table = section.find("table")
    if not table:
        return []

    headers = [th.get_text(strip=True) for th in table.find("thead").find_all("th")] if table.find("thead") else []
    periods = [h for h in headers if h and h.lower() != "name" and not h.isdigit()]
    if not periods:
        return []

    data_map = {}
    for p in periods:
        data_map[p] = {"promoter_pct": None, "fii_pct": None, "dii_pct": None, "public_pct": None, "pledged_pct": None}

    tbody = table.find("tbody")
    if tbody:
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if not tds:
                continue
            line_name = tds[0].get_text(strip=True).lower()
            vals = [td.get_text(strip=True).replace("%", "").replace(",", "") for td in tds[1:]]

            target_key = None
            if "promoter" in line_name and "pledge" not in line_name:
                target_key = "promoter_pct"
            elif "fii" in line_name or "foreign" in line_name:
                target_key = "fii_pct"
            elif "dii" in line_name or "domestic" in line_name:
                target_key = "dii_pct"
            elif "public" in line_name:
                target_key = "public_pct"
            elif "pledge" in line_name:
                target_key = "pledged_pct"

            if target_key:
                for idx, v in enumerate(vals):
                    if idx < len(periods):
                        p = periods[idx]
                        try:
                            data_map[p][target_key] = float(v)
                        except Exception:
                            pass

    rows_to_insert = []
    for p, metrics in data_map.items():
        if any(v is not None for v in metrics.values()):
            rows_to_insert.append((
                symbol,
                p,
                metrics.get("promoter_pct"),
                metrics.get("fii_pct"),
                metrics.get("dii_pct"),
                metrics.get("public_pct"),
                metrics.get("pledged_pct")
            ))

    return rows_to_insert

def parse_and_store_shareholding(html: str, symbol: str) -> int:
    """
    Extract quarterly shareholding rows and store them directly in the database.
    """
    ensure_shareholding_table()
    rows = parse_shareholding_html(html, symbol)
    if rows:
        conn = get_db_connection(timeout=30.0)
        conn.executemany("""
            INSERT OR REPLACE INTO company_shareholding_quarterly
            (symbol, fiscal_period, promoter_pct, fii_pct, dii_pct, public_pct, pledged_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
        conn.close()
    return len(rows)

def get_shareholding_trend(symbol: str) -> Dict[str, Any]:
    """
    Retrieve latest shareholding structure and QoQ institutional flow delta.
    """
    conn = get_db_connection(readonly=True, timeout=15.0)
    c = conn.cursor()
    rows = c.execute("""
        SELECT fiscal_period, promoter_pct, fii_pct, dii_pct, public_pct, pledged_pct
        FROM company_shareholding_quarterly
        WHERE symbol = ?
        ORDER BY rowid DESC LIMIT 2
    """, (symbol.upper(),)).fetchall()
    conn.close()

    if not rows:
        return {"symbol": symbol, "status": "NO_SHAREHOLDING_DATA"}

    latest = rows[0]
    prev = rows[1] if len(rows) > 1 else None

    fii_delta = round(latest[2] - prev[2], 2) if (prev and latest[2] is not None and prev[2] is not None) else 0.0
    dii_delta = round(latest[3] - prev[3], 2) if (prev and latest[3] is not None and prev[3] is not None) else 0.0
    pledge_delta = round(latest[5] - prev[5], 2) if (prev and latest[5] is not None and prev[5] is not None) else 0.0

    return {
        "symbol": symbol,
        "latest_period": latest[0],
        "promoter_pct": latest[1],
        "fii_pct": latest[2],
        "dii_pct": latest[3],
        "public_pct": latest[4],
        "pledged_pct": latest[5] or 0.0,
        "fii_qoq_delta": fii_delta,
        "dii_qoq_delta": dii_delta,
        "pledge_qoq_delta": pledge_delta,
        "institutional_signal": "ACCUMULATION" if (fii_delta + dii_delta) > 0.5 else ("DISTRIBUTION" if (fii_delta + dii_delta) < -0.5 else "STABLE")
    }
