"""
core/tools/personalization_tool.py
==================================
LangChain tool for Dynamic Conversational Learning and User Preference Persistence.
Extracts user exclusions (e.g., "Exclude PSU Banks & Adani") and preferences (e.g., "High Dividend"),
persisting them in real time to 'risk_profiles' in market_data_v2.db.
"""

import os
import sys
import json
import re
import sqlite3
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "market_data_v2.db")

DEFAULT_ADMIN_USER_ID = "08d25bf2-10a3-43c3-8aa5-b09f9a20736a"

SECTOR_KEYWORDS = {
    "PSU BANK": "PSU Banks",
    "PSU BANKS": "PSU Banks",
    "BANK": "Banking",
    "BANKS": "Banking",
    "IT": "IT",
    "TECH": "IT",
    "PHARMA": "Pharma",
    "HEALTHCARE": "Pharma",
    "AUTO": "Automobile",
    "AUTOMOBILE": "Automobile",
    "METAL": "Metals",
    "METALS": "Metals",
    "FMCG": "FMCG",
    "REALTY": "Realty",
    "ENERGY": "Energy",
    "OIL & GAS": "Oil & Gas"
}

CONGLOMERATE_KEYWORDS = {
    "ADANI": "Adani Group",
    "TATA": "Tata Group",
    "BAJAJ": "Bajaj Group",
    "BIRLA": "Birla Group"
}

THEME_KEYWORDS = {
    "DIVIDEND": "High Dividend Yield",
    "DIVIDENDS": "High Dividend Yield",
    "HIGH DIVIDEND": "High Dividend Yield",
    "SWING": "Swing Trading",
    "GROWTH": "High Growth",
    "VALUE": "Value Compounding",
    "LOW RISK": "Conservative / Low Risk",
    "HIGH RISK": "Aggressive Alpha"
}

def get_user_risk_profile(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve user risk profile from risk_profiles table."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    uid = user_id or DEFAULT_ADMIN_USER_ID
    
    cur.execute("""
        SELECT user_id, starting_capital, excluded_sectors, preferred_sectors, trading_styles, max_position_pct, max_sector_pct
        FROM risk_profiles
        WHERE user_id = ?
    """, (uid,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return {
            "user_id": uid,
            "starting_capital": 100000.0,
            "excluded_sectors": [],
            "preferred_sectors": [],
            "trading_styles": [],
            "max_position_pct": 20.0,
            "max_sector_pct": 30.0
        }

    def _parse_list(val):
        if not val:
            return []
        if isinstance(val, list):
            return val
        try:
            return json.loads(val)
        except Exception:
            return [str(val)]

    return {
        "user_id": row[0],
        "starting_capital": float(row[1] or 100000.0),
        "excluded_sectors": _parse_list(row[2]),
        "preferred_sectors": _parse_list(row[3]),
        "trading_styles": _parse_list(row[4]),
        "max_position_pct": float(row[5] or 20.0),
        "max_sector_pct": float(row[6] or 30.0)
    }


def parse_and_update_preferences(text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Parse natural language exclusions/preferences and update risk_profiles in real time."""
    upper = text.upper()
    uid = user_id or DEFAULT_ADMIN_USER_ID
    profile = get_user_risk_profile(uid)

    excluded = set(profile["excluded_sectors"])
    preferred = set(profile["preferred_sectors"])
    styles = set(profile["trading_styles"])

    # 1. Detect Exclusions
    # e.g., "don't like PSU banks or Adani", "avoid IT", "exclude Pharma"
    has_exclude = any(w in upper for w in ("DON'T LIKE", "DONT LIKE", "DO NOT LIKE", "AVOID", "EXCLUDE", "NO PSU", "NO ADANI", "HATE"))
    if has_exclude:
        for kw, label in SECTOR_KEYWORDS.items():
            if re.search(r'\b' + re.escape(kw) + r'\b', upper):
                excluded.add(label)
        for kw, label in CONGLOMERATE_KEYWORDS.items():
            if re.search(r'\b' + re.escape(kw) + r'\b', upper):
                excluded.add(label)

    # 2. Detect Preferences
    has_prefer = any(w in upper for w in ("PREFER", "LIKE", "WANT", "FAVOR", "LOOKING FOR", "LOVE", "REGULAR DIVIDEND", "DIVIDEND"))
    if has_prefer:
        for kw, label in THEME_KEYWORDS.items():
            if re.search(r'\b' + re.escape(kw) + r'\b', upper):
                styles.add(label)
        for kw, label in SECTOR_KEYWORDS.items():
            if re.search(r'\b' + re.escape(kw) + r'\b', upper) and not has_exclude:
                preferred.add(label)

    # Persist to database
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        UPDATE risk_profiles
        SET excluded_sectors = ?, preferred_sectors = ?, trading_styles = ?, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, (
        json.dumps(sorted(list(excluded))),
        json.dumps(sorted(list(preferred))),
        json.dumps(sorted(list(styles))),
        uid
    ))
    conn.commit()
    conn.close()

    # Build confirmation badge
    ex_str = ", ".join(sorted(list(excluded))) if excluded else "None"
    pr_str = ", ".join(sorted(list(styles | preferred))) if (styles | preferred) else "Balanced"

    badge_html = (
        f"<div class=\"vprof-preference-badge\">\n"
        f"  <span class=\"badge-title\">✅ Dynamic Preferences Updated</span>\n"
        f"  <div class=\"badge-details\">\n"
        f"    <div>🚫 <strong>Excluded:</strong> {ex_str}</div>\n"
        f"    <div>🎯 <strong>Preferred Themes:</strong> {pr_str}</div>\n"
        f"  </div>\n"
        f"</div>"
    )

    return {
        "ok": True,
        "user_id": uid,
        "excluded_sectors": sorted(list(excluded)),
        "preferred_sectors": sorted(list(preferred)),
        "trading_styles": sorted(list(styles)),
        "badge_html": badge_html,
        "summary_text": f"✅ Preferences Updated: Excluded [{ex_str}] | Preference: [{pr_str}]"
    }


@tool
def update_user_preferences_tool(query: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Parse user preference and exclusion requests and persist them to risk_profiles."""
    return parse_and_update_preferences(query, user_id=user_id)
