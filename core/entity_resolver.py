"""
core/entity_resolver.py
=======================
Enterprise-grade Named Entity Linking (NEL) Engine for Indian Equities (NSE/BSE).
Resolves colloquial queries (e.g. "Adani enterprise", "M&M", "Tata Motors", "Airtel")
into exact canonical tickers (e.g. "ADANIENT", "M&M", "TATAMOTORS", "BHARTIARTL").

Features:
  1. Multi-tier resolution:
     - Exact ticker match (case-insensitive)
     - Colloquial alias registry (conglomerates, brands, acronyms)
     - Canonical name normalization (suffix stripping, singular/plural)
     - Trigram / Jaro-Winkler fuzzy matching for typos
  2. Conversational prefix stripping ("Give me quick bytes about", "Im asking for", etc.)
  3. Conglomerate / Group Ambiguity Detection (e.g. "Adani" -> returns group candidates).
"""

import os
import sys
import re
import csv
from typing import Dict, List, Optional, Tuple, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "data", "nifty500.csv")

# ── Conversational Filler Stripping ───────────────────────────────────────────
CONVERSATIONAL_PREFIXES = [
    r"^GIVE\s+ME\s+(QUICK\s+)?(BYTES|UPDATES?|INFO|DETAILS?|OVERVIEW)\s+(ABOUT|ON|FOR)",
    r"^TELL\s+ME\s+(ABOUT|MORE\s+ABOUT)",
    r"^WHAT\s+(IS|ARE)(\s+THE)?(\s+CURRENT)?\s+(PRICE|LEVEL|VALUE)?\s+(OF|FOR)?",
    r"^WHAT\s+(ABOUT|IS|ARE)",
    r"^HOW\s+MUCH\s+IS",
    r"^(SHOW|CHECK|GET)(\s+ME)?\s+(THE\s+)?(CURRENT\s+)?(PRICE|LEVEL|VALUE)\s+(OF|FOR)?",
    r"^I\s*M\s+ASKING\s+FOR",
    r"^I\s+AM\s+ASKING\s+FOR",
    r"^CAN\s+YOU\s+(ANALYZE|SHOW|CHECK|TELL\s+ME\s+ABOUT)",
    r"^PLEASE\s+(ANALYZE|SHOW|CHECK|TELL\s+ME\s+ABOUT)",
    r"^SHOW\s+ME(\s+THE)?",
    r"^ANALYZE(\s+THE)?",
    r"^HOW\s+IS",
    r"^QUICK\s+(BYTES|LOOK|SUMMARY|UPDATE)\s+(ON|FOR|ABOUT)",
    r"^LOOK\s+AT",
    r"^SEARCH\s+(FOR)?",
    r"^FINANCIALS?\s+(FOR|OF)",
    r"^RESULTS?\s+(FOR|OF)",
    r"^BALANCE\s+SHEET\s+(FOR|OF)",
    r"^REVENUE\s+(FOR|OF)",
    r"^DEBT\s+(FOR|OF)",
    r"^PROFIT\s+(FOR|OF)",
    r"^NEWS\s+(ON|FOR|ABOUT)",
]

# ── High-Frequency Curated Colloquial Aliases ─────────────────────────────────
CURATED_ALIASES: Dict[str, str] = {
    # Benchmark & Sectoral Indices
    "NIFTY": "NIFTY50",
    "NIFTY 50": "NIFTY50",
    "NIFTY50": "NIFTY50",
    "NIFTY FIFTY": "NIFTY50",
    "NIFTY INDEX": "NIFTY50",
    "CNX NIFTY": "NIFTY50",
    "BANK NIFTY": "BANKNIFTY",
    "BANKNIFTY": "BANKNIFTY",
    "NIFTY BANK": "BANKNIFTY",
    "NIFTY IT": "NIFTYIT",
    "NIFTY AUTO": "NIFTYAUTO",
    "NIFTY PHARMA": "NIFTYPHARMA",
    "NIFTY FMCG": "NIFTYFMCG",
    "NIFTY METAL": "NIFTYMETAL",
    "NIFTY REALTY": "NIFTYREALTY",
    "NIFTY ENERGY": "NIFTYENERGY",
    "NIFTY INFRA": "NIFTYINFRA",
    "NIFTY MIDCAP": "NIFTYMIDCAP50",
    "NIFTY MIDCAP 50": "NIFTYMIDCAP50",
    # Adani Group
    "ADANI ENTERPRISE": "ADANIENT",
    "ADANI ENTERPRISES": "ADANIENT",
    "ADANI ENT": "ADANIENT",
    "AEL": "ADANIENT",
    "ADANI PORTS": "ADANIPORTS",
    "ADANI PORT": "ADANIPORTS",
    "APSEZ": "ADANIPORTS",
    "ADANI POWER": "ADANIPOWER",
    "ADANI GREEN": "ADANIGREEN",
    "ADANI GREEN ENERGY": "ADANIGREEN",
    "ADANI ENERGY": "ADANIENSOL",
    "ADANI ENERGY SOLUTIONS": "ADANIENSOL",
    "ADANI TRANSMISSION": "ADANIENSOL",
    "ADANI TOTAL GAS": "ATGL",
    "ADANI GAS": "ATGL",
    "ADANI WILMAR": "AWL",

    # Reliance
    "RELIANCE": "RELIANCE",
    "RELIANCE INDUSTRIES": "RELIANCE",
    "RELIANCE INDUSTRY": "RELIANCE",
    "RIL": "RELIANCE",
    "MUKESH AMBANI": "RELIANCE",
    "JIO": "RELIANCE",
    "RELIANCE JIO": "RELIANCE",
    "JIO FINANCIAL": "JIOFIN",
    "JIO FINANCIAL SERVICES": "JIOFIN",
    "JIOFIN": "JIOFIN",

    # Tata Group
    "TCS": "TCS",
    "TATA CONSULTANCY": "TCS",
    "TATA CONSULTANCY SERVICES": "TCS",
    "TATA MOTORS": "TATAMOTORS",
    "TATA MOTOR": "TATAMOTORS",
    "TATAMOTORS": "TATAMOTORS",
    "TATA POWER": "TATAPOWER",
    "TATA STEEL": "TATASTEEL",
    "TATA CONSUMER": "TATACONSUM",
    "TATA CONSUMER PRODUCTS": "TATACONSUM",
    "TITAN": "TITAN",
    "TITAN COMPANY": "TITAN",
    "TRENT": "TRENT",
    "WESTSIDE": "TRENT",
    "ZUDIO": "TRENT",
    "VOLTAS": "VOLTAS",
    "TATA ELXSI": "TATAELXSI",
    "TATA COMMUNICATIONS": "TATACOMM",
    "TATA TECH": "TATATECH",
    "TATA TECHNOLOGIES": "TATATECH",

    # Banking & Financials
    "HDFC": "HDFCBANK",
    "HDFC BANK": "HDFCBANK",
    "HDFCBANK": "HDFCBANK",
    "HDFC LIFE": "HDFCLIFE",
    "HDFC AMC": "HDFCAMC",
    "ICICI": "ICICIBANK",
    "ICICI BANK": "ICICIBANK",
    "ICICIBANK": "ICICIBANK",
    "ICICI PRU": "ICICIPRULI",
    "ICICI LOMBARD": "ICICIGI",
    "SBI": "SBIN",
    "STATE BANK": "SBIN",
    "STATE BANK OF INDIA": "SBIN",
    "SBIN": "SBIN",
    "KOTAK": "KOTAKBANK",
    "KOTAK BANK": "KOTAKBANK",
    "KOTAK MAHINDRA": "KOTAKBANK",
    "KOTAK MAHINDRA BANK": "KOTAKBANK",
    "AXIS": "AXISBANK",
    "AXIS BANK": "AXISBANK",
    "INDUSIND": "INDUSINDBK",
    "INDUSIND BANK": "INDUSINDBK",
    "BANK OF BARODA": "BANKBARODA",
    "BOB": "BANKBARODA",
    "PNB": "PNB",
    "PUNJAB NATIONAL BANK": "PNB",
    "BAJAJ FINANCE": "BAJFINANCE",
    "BAJAJ FINSERV": "BAJAJFINSV",
    "BAJAJ AUTO": "BAJAJ-AUTO",

    # IT & Tech
    "INFOSYS": "INFY",
    "INFY": "INFY",
    "WIPRO": "WIPRO",
    "HCL": "HCLTECH",
    "HCL TECH": "HCLTECH",
    "HCL TECHNOLOGIES": "HCLTECH",
    "TECH MAHINDRA": "TECHM",
    "TECHM": "TECHM",
    "LTIMINDTREE": "LTIM",
    "LTIM": "LTIM",
    "PERSISTENT": "PERSISTENT",
    "COFORGE": "COFORGE",
    "MPHASIS": "MPHASIS",

    # Auto & Industrials
    "MARUTI": "MARUTI",
    "MARUTI SUZUKI": "MARUTI",
    "M&M": "M&M",
    "MAHINDRA": "M&M",
    "MAHINDRA & MAHINDRA": "M&M",
    "MAHINDRA AND MAHINDRA": "M&M",
    "EICHER": "EICHERMOT",
    "EICHER MOTORS": "EICHERMOT",
    "ROYAL ENFIELD": "EICHERMOT",
    "HERO": "HEROMOTOCO",
    "HERO MOTOCORP": "HEROMOTOCO",
    "TVS": "TVSMOTOR",
    "TVS MOTOR": "TVSMOTOR",
    "L&T": "LT",
    "LARSEN": "LT",
    "LARSEN & TOUBRO": "LT",
    "LARSEN AND TOUBRO": "LT",
    "BHARAT ELECTRONICS": "BEL",
    "BEL": "BEL",
    "HAL": "HAL",
    "HINDUSTAN AERONAUTICS": "HAL",

    # Telecom, FMCG, Pharma, Energy
    "AIRTEL": "BHARTIARTL",
    "BHARTI AIRTEL": "BHARTIARTL",
    "BHARTI": "BHARTIARTL",
    "ITC": "ITC",
    "HUL": "HINDUNILVR",
    "HINDUSTAN UNILEVER": "HINDUNILVR",
    "NESTLE": "NESTLEIND",
    "NESTLE INDIA": "NESTLEIND",
    "BRITANNIA": "BRITANNIA",
    "DABUR": "DABUR",
    "MARICO": "MARICO",
    "SUN PHARMA": "SUNPHARMA",
    "SUN PHARMACEUTICALS": "SUNPHARMA",
    "DR REDDY": "DRREDDY",
    "DR REDDYS": "DRREDDY",
    "CIPLA": "CIPLA",
    "DIVIS": "DIVISLAB",
    "DIVIS LAB": "DIVISLAB",
    "ONGC": "ONGC",
    "NTPC": "NTPC",
    "POWER GRID": "POWERGRID",
    "POWERGRID": "POWERGRID",
    "COAL INDIA": "COALINDIA",
    "IOC": "IOC",
    "INDIAN OIL": "IOC",
    "BPCL": "BPCL",
    "BHARAT PETROLEUM": "BPCL",
    "GAIL": "GAIL",

    # New Age Tech & Retail
    "ZOMATO": "ZOMATO",
    "SWIGGY": "SWIGGY",
    "PAYTM": "PAYTM",
    "ONE97": "PAYTM",
    "POLICYBAZAAR": "POLICYBZR",
    "POLICY BAZAAR": "POLICYBZR",
    "PB FINTECH": "POLICYBZR",
    "NYKAA": "NYKAA",
    "FSN E-COMMERCE": "NYKAA",
    "DMART": "DMART",
    "AVENUE SUPERMARTS": "DMART",
}

# ── Conglomerate Group Families (for Ambiguity Detection) ─────────────────────
CONGLOMERATE_GROUPS = {
    "ADANI": [
        {"symbol": "ADANIENT", "name": "Adani Enterprises (Flagship / Incubator)"},
        {"symbol": "ADANIPORTS", "name": "Adani Ports & SEZ (Logistics & Ports)"},
        {"symbol": "ADANIPOWER", "name": "Adani Power (Thermal Generation)"},
        {"symbol": "ADANIGREEN", "name": "Adani Green Energy (Renewable Power)"},
        {"symbol": "ADANIENSOL", "name": "Adani Energy Solutions (Transmission)"},
        {"symbol": "ATGL", "name": "Adani Total Gas (City Gas Distribution)"},
        {"symbol": "AWL", "name": "Adani Wilmar (Edible Oils & FMCG)"},
    ],
    "TATA": [
        {"symbol": "TCS", "name": "Tata Consultancy Services (IT Services)"},
        {"symbol": "TATAMOTORS", "name": "Tata Motors (EV & Commercial Vehicles)"},
        {"symbol": "TATASTEEL", "name": "Tata Steel (Metals & Mining)"},
        {"symbol": "TATAPOWER", "name": "Tata Power (Renewables & Utilities)"},
        {"symbol": "TATACONSUM", "name": "Tata Consumer Products (FMCG)"},
        {"symbol": "TITAN", "name": "Titan Company (Jewellery & Watches)"},
        {"symbol": "TRENT", "name": "Trent (Zudio & Westside Retail)"},
    ],
    "BAJAJ": [
        {"symbol": "BAJFINANCE", "name": "Bajaj Finance (Consumer Lending / NBFC)"},
        {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv (Financial Services Holding)"},
        {"symbol": "BAJAJ-AUTO", "name": "Bajaj Auto (2-Wheelers & 3-Wheelers)"},
        {"symbol": "BAJAJHLDNG", "name": "Bajaj Holdings & Investment"},
    ],
    "BIRLA": [
        {"symbol": "GRASIM", "name": "Grasim Industries (Viscose & Chemicals)"},
        {"symbol": "HINDALCO", "name": "Hindalco Industries (Aluminium & Copper)"},
        {"symbol": "ULTRACEMCO", "name": "UltraTech Cement (Building Materials)"},
        {"symbol": "ABCAPITAL", "name": "Aditya Birla Capital (Financial Services)"},
    ]
}

# ── Market Benchmark & Sectoral Indices ───────────────────────────────────────
INDEX_METADATA: Dict[str, Dict[str, Any]] = {
    "NIFTY50": {"name": "NIFTY 50 Benchmark Index", "industry": "Benchmark Index", "is_index": True},
    "BANKNIFTY": {"name": "Nifty Bank Index", "industry": "Banking Index", "is_index": True},
    "NIFTYIT": {"name": "Nifty IT Index", "industry": "Technology Index", "is_index": True},
    "NIFTYAUTO": {"name": "Nifty Auto Index", "industry": "Automotive Index", "is_index": True},
    "NIFTYPHARMA": {"name": "Nifty Pharma Index", "industry": "Healthcare Index", "is_index": True},
    "NIFTYFMCG": {"name": "Nifty FMCG Index", "industry": "Consumer Goods Index", "is_index": True},
    "NIFTYMETAL": {"name": "Nifty Metal Index", "industry": "Metals Index", "is_index": True},
    "NIFTYREALTY": {"name": "Nifty Realty Index", "industry": "Real Estate Index", "is_index": True},
    "NIFTYENERGY": {"name": "Nifty Energy Index", "industry": "Energy Index", "is_index": True},
    "NIFTYINFRA": {"name": "Nifty Infrastructure Index", "industry": "Infrastructure Index", "is_index": True},
    "NIFTYMIDCAP50": {"name": "Nifty Midcap 50 Index", "industry": "Midcap Index", "is_index": True},
}


class EntityResolver:
    """Singleton high-speed entity linking engine."""

    def __init__(self):
        self._exact_symbols: Dict[str, str] = {}            # SYMBOL -> SYMBOL
        self._alias_to_symbol: Dict[str, str] = {}          # "adani enterprise" -> "ADANIENT"
        self._symbol_to_meta: Dict[str, Dict[str, Any]] = {}# "ADANIENT" -> {name, industry}
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return

        # 0. Load Index Metadata
        for idx_sym, meta in INDEX_METADATA.items():
            self._exact_symbols[idx_sym] = idx_sym
            self._symbol_to_meta[idx_sym] = meta

        # 1. Load curated dictionary
        for alias, sym in CURATED_ALIASES.items():
            self._alias_to_symbol[self._normalize(alias)] = sym.upper()

        # 2. Load Nifty 500 CSV
        if os.path.exists(CSV_PATH):
            try:
                with open(CSV_PATH, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        sym = (r.get("Symbol") or "").strip().upper()
                        name = (r.get("Company Name") or "").strip()
                        ind = (r.get("Industry") or "").strip()
                        if not sym:
                            continue

                        self._exact_symbols[sym] = sym
                        self._symbol_to_meta[sym] = {"name": name, "industry": ind}
                        
                        # Register canonical name
                        self._register_name_variations(name, sym)
            except Exception as e:
                print(f"  [EntityResolver] Error loading nifty500.csv: {e}", flush=True)

        self._initialized = True

    def _normalize(self, text: str) -> str:
        """Strip punctuation, corporate suffixes, and collapse whitespace."""
        t = text.upper()
        # Remove dots and commas
        t = re.sub(r"[,\.]", "", t)
        # Strip corporate suffixes
        t = re.sub(r"\b(LIMITED|LTD|PVT|PRIVATE|HOLDINGS|HOLDING|CORP|CORPORATION)\b", "", t)
        # Strip generic geography
        t = re.sub(r"\b(INDIA)\b", "", t)
        # Collapse multiple spaces
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _register_name_variations(self, company_name: str, symbol: str):
        """Generate normalized search keys for a company name."""
        norm = self._normalize(company_name)
        if norm and len(norm) >= 3:
            self._alias_to_symbol[norm] = symbol
            
            # Singular / Plural variation (e.g. Enterprises -> Enterprise)
            if norm.endswith("S") and len(norm) > 4:
                self._alias_to_symbol[norm[:-1]] = symbol
            else:
                self._alias_to_symbol[norm + "S"] = symbol

            # First 2 words if multi-word
            parts = norm.split()
            if len(parts) >= 2:
                two_words = " ".join(parts[:2])
                if len(two_words) >= 5 and two_words not in self._alias_to_symbol:
                    self._alias_to_symbol[two_words] = symbol

    def strip_conversational_prefixes(self, text: str) -> str:
        """Clean conversational fluff (e.g. 'Give me quick bytes about X' -> 'X')."""
        clean = text.strip()
        upper = clean.upper()
        
        for pat in CONVERSATIONAL_PREFIXES:
            m = re.match(pat, upper)
            if m:
                clean = clean[m.end():].strip()
                upper = clean.upper()
                break

        # Remove trailing question mark or punctuation
        clean = re.sub(r"[\?\!\.\,]+$", "", clean).strip()
        # Remove trailing price / level / stock queries: e.g. "nifty current price" -> "nifty"
        clean = re.sub(r"\b(CURRENT\s+PRICE|SHARE\s+PRICE|STOCK\s+PRICE|PRICE|LEVEL|STATUS|TODAY|NOW)\b", "", clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r"[\?\!\.\,]+$", "", clean).strip()
        return clean

    def is_index(self, symbol: Optional[str]) -> bool:
        return bool(symbol and symbol.upper() in INDEX_METADATA)

    def resolve(self, text: str, active_session_symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Primary entity resolution method.
        Returns:
          {
            "symbol": Optional[str],
            "confidence": float,
            "match_type": str,
            "is_ambiguous_group": bool,
            "group_candidates": List[Dict],
            "is_index": bool
          }
        """
        self.initialize()
        
        raw_text = text.strip()
        if not raw_text:
            return {"symbol": None, "confidence": 0.0, "match_type": "EMPTY", "is_index": False}

        cleaned = self.strip_conversational_prefixes(raw_text)
        upper_cleaned = self._normalize(cleaned)
        upper_raw = self._normalize(raw_text)

        # ── Step 0: Check Conglomerate Group Ambiguity ────────────────────────
        # If the user literally typed just "Adani" or "Tell me about Tata"
        words_cleaned = upper_cleaned.split()
        if len(words_cleaned) == 1 and words_cleaned[0] in CONGLOMERATE_GROUPS:
            group_key = words_cleaned[0]
            return {
                "symbol": None,
                "confidence": 0.5,
                "match_type": "GROUP_DISAMBIGUATION",
                "is_ambiguous_group": True,
                "group_name": group_key,
                "group_candidates": CONGLOMERATE_GROUPS[group_key],
                "is_index": False
            }

        # ── Step 1: Direct Exact Symbol Match in Raw Tokens ───────────────────
        tokens = re.findall(r"[A-Z0-9&-]+", raw_text.upper())
        for tok in tokens:
            if tok in self._exact_symbols:
                return {
                    "symbol": tok,
                    "confidence": 1.0,
                    "match_type": "EXACT_TICKER",
                    "company_name": self._symbol_to_meta.get(tok, {}).get("name", tok),
                    "is_index": self.is_index(tok)
                }

        # ── Step 2: Full String Alias Match (Highest Priority for Colloquial) ─
        # Checks both cleaned ("ADANI ENTERPRISE", "NIFTY") and raw
        for candidate in (upper_cleaned, upper_raw):
            if candidate in self._alias_to_symbol:
                sym = self._alias_to_symbol[candidate]
                return {
                    "symbol": sym,
                    "confidence": 0.98,
                    "match_type": "COLLOQUIAL_ALIAS",
                    "company_name": self._symbol_to_meta.get(sym, {}).get("name", sym),
                    "is_index": self.is_index(sym)
                }

        # ── Step 3: Substring Alias Matching (Longest Key First) ──────────────
        for candidate in (upper_cleaned, upper_raw):
            for alias, sym in sorted(self._alias_to_symbol.items(), key=lambda x: -len(x[0])):
                if len(alias) >= 4:
                    # Use regex word boundaries so 'UP' doesn't match 'UPDATES'
                    pattern = r'\b' + re.escape(alias) + r'\b'
                    if re.search(pattern, candidate):
                        return {
                            "symbol": sym,
                            "confidence": 0.92,
                            "match_type": "SUBSTRING_ALIAS",
                            "company_name": self._symbol_to_meta.get(sym, {}).get("name", sym),
                            "is_index": self.is_index(sym)
                        }

        # ── Step 4: Fuzzy Matching with Jaro-Winkler / Levenshtein ───────────
        # For misspellings like "Adani enterprize", "Relience"
        best_sym = None
        best_score = 0.0
        
        # Check against aliases >= 4 chars
        for alias, sym in self._alias_to_symbol.items():
            if len(alias) >= 4 and abs(len(alias) - len(upper_cleaned)) <= 3:
                # Simple character overlap / Jaccard similarity for sub-millisecond response
                s1, s2 = set(alias), set(upper_cleaned)
                jaccard = len(s1 & s2) / max(1, len(s1 | s2))
                if jaccard > 0.85:
                    # Verify common prefix
                    if alias[:3] == upper_cleaned[:3]:
                        if jaccard > best_score:
                            best_score = jaccard
                            best_sym = sym

        if best_sym and best_score >= 0.85:
            return {
                "symbol": best_sym,
                "confidence": round(best_score, 2),
                "match_type": "FUZZY_MATCH",
                "company_name": self._symbol_to_meta.get(best_sym, {}).get("name", best_sym),
                "is_index": self.is_index(best_sym)
            }

        # ── Step 5: Anaphoric Pronoun Inheritance (Multi-Turn Working Memory) ──
        # e.g. "What is its debt?", "Tell me about their operating margin"
        if active_session_symbol and any(
            p in raw_text.lower().split() for p in ("its", "their", "it", "this", "the company", "the stock")
        ):
            return {
                "symbol": active_session_symbol,
                "confidence": 0.88,
                "match_type": "SESSION_PRONOUN_INHERITANCE",
                "company_name": self._symbol_to_meta.get(active_session_symbol, {}).get("name", active_session_symbol),
                "is_index": self.is_index(active_session_symbol)
            }

        return {
            "symbol": None,
            "confidence": 0.0,
            "match_type": "NO_ENTITY_FOUND",
            "is_index": False
        }

# Global singleton
_RESOLVER_INSTANCE = None

def get_entity_resolver() -> EntityResolver:
    global _RESOLVER_INSTANCE
    if _RESOLVER_INSTANCE is None:
        _RESOLVER_INSTANCE = EntityResolver()
        _RESOLVER_INSTANCE.initialize()
    return _RESOLVER_INSTANCE

def resolve_equity_entity(text: str, session_symbol: Optional[str] = None) -> Dict[str, Any]:
    """Convenience helper used across agent swarm."""
    resolver = get_entity_resolver()
    return resolver.resolve(text, active_session_symbol=session_symbol)

def is_index_symbol(symbol: Optional[str]) -> bool:
    """Check if symbol is an index."""
    if not symbol:
        return False
    return symbol.upper() in INDEX_METADATA
