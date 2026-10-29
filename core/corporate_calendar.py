"""
core/corporate_calendar.py
==========================
Corporate Announcements & Earnings Calendar Gatekeeper.
Prevents trading blindly into quarterly results, dividend dates, and board meetings.
"""

import os
import sys
import sqlite3
import json
import urllib.request
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.paths import get_db_connection

def ensure_calendar_table():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS earnings_calendar (
            symbol TEXT NOT NULL,
            company_name TEXT,
            event_date TEXT NOT NULL,
            purpose TEXT NOT NULL,
            announcement_date TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            PRIMARY KEY (symbol, event_date, purpose)
        )
    """)
    conn.commit()
    conn.close()

def is_earnings_imminent(symbol: str, window_days: int = 3) -> Dict[str, Any]:
    """
    Check if a symbol has an earnings release or board meeting within window_days.
    Returns:
      {
        "imminent": bool,
        "symbol": str,
        "event_date": str or None,
        "purpose": str or None,
        "days_until": int or None
      }
    """
    symbol = symbol.strip().upper()
    today = date.today().isoformat()
    max_date = (date.today() + timedelta(days=window_days)).isoformat()

    conn = get_db_connection(readonly=True)
    c = conn.cursor()
    row = c.execute("""
        SELECT event_date, purpose 
        FROM earnings_calendar 
        WHERE symbol = ? AND event_date >= ? AND event_date <= ?
        ORDER BY event_date ASC LIMIT 1
    """, (symbol, today, max_date)).fetchone()
    conn.close()

    if row:
        ev_date = row[0]
        purp = row[1]
        try:
            d_obj = datetime.strptime(ev_date, "%Y-%m-%d").date()
            days_until = (d_obj - date.today()).days
        except Exception:
            days_until = 0

        return {
            "imminent": True,
            "symbol": symbol,
            "event_date": ev_date,
            "purpose": purp,
            "days_until": days_until,
            "risk_message": f"High Event Volatility Risk: {purp} scheduled on {ev_date} ({days_until}d away)"
        }

    return {
        "imminent": False,
        "symbol": symbol,
        "event_date": None,
        "purpose": None,
        "days_until": None,
        "risk_message": None
    }

def fetch_nse_corporate_events() -> int:
    """
    Fetch upcoming corporate events from NSE India API.
    """
    ensure_calendar_table()
    import requests
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-event-calendar"
    })

    events = []
    try:
        s.get("https://www.nseindia.com", timeout=10)
        resp = s.get("https://www.nseindia.com/api/event-calendar", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                for item in data:
                    sym = (item.get("symbol") or "").strip().upper()
                    cname = (item.get("company") or "").strip()
                    raw_date = (item.get("date") or "").strip()
                    purpose = (item.get("purpose") or item.get("bm_desc") or item.get("desc") or "").strip()
                    if sym and raw_date and purpose:
                        try:
                            iso_date = datetime.strptime(raw_date, "%d-%b-%Y").strftime("%Y-%m-%d")
                        except Exception:
                            iso_date = raw_date
                        events.append((sym, cname, iso_date, purpose, date.today().isoformat()))
    except Exception as e:
        pass

    if events:
        conn = get_db_connection(timeout=30.0)
        conn.executemany("""
            INSERT OR REPLACE INTO earnings_calendar 
            (symbol, company_name, event_date, purpose, announcement_date)
            VALUES (?, ?, ?, ?, ?)
        """, events)
        conn.commit()
        conn.close()

    return len(events)
