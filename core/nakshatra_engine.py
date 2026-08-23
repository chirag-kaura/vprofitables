"""
core/nakshatra_engine.py
Nakshatra (lunar mansion) engine for GANN·ASTRO v3.9.
Implements The Stellar Setup methodology by Vaibhav Tillu.
"""
from datetime import date, timedelta
from typing import Tuple, List, Dict
from core.ephemeris import moon_longitude

NAK_SPAN = 360 / 27      # 13.3333° per Nakshatra

# 27 Nakshatras: name, ruler, guna, behavior, sectors, instruments, trade_style, caution
NAKSHATRAS = [
  ("Ashwini",          "Ketu",    "Rajas",  "VOLATILE",   ["Pharma","Auto"],            ["DRREDDY","MARUTI","BAJAJ-AUTO"],  "SWING",    "Impulsive energy — avoid overtrading"),
  ("Bharani",          "Venus",   "Rajas",  "EXIT_ONLY",  ["FMCG","Luxury","Speculative"],["HINDUNILVR","GOLD"],             "EXIT",     "Not for initiation; book profits or hedge"),
  ("Krittika",         "Sun",     "Rajas",  "DIRECTIONAL",["Energy","Steel","Defense"],  ["NTPC","TATASTEEL","HINDALCO"],    "BOLD",     "Decisive action; avoid analysis paralysis"),
  ("Rohini",           "Moon",    "Rajas",  "ACCUMULATE", ["FMCG","Agriculture","Dairy"],["HINDUNILVR","ITC"],              "BUY_HOLD", "Ideal for core portfolio additions"),
  ("Mrigashira",       "Mars",    "Tamas",  "SWING",      ["Media","Travel","Research"], [],                                "SWING",    "Stay nimble; news-driven moves"),
  ("Ardra",            "Rahu",    "Tamas",  "VOLATILE",   ["IT","Biotech","AI"],         ["TCS","INFY","DRREDDY"],          "EXPERT",   "Experienced traders only; creative destruction"),
  ("Punarvasu",        "Jupiter", "Sattva", "REBOUND",    ["Insurance","Education"],     ["HDFCLIFE","SBILIFE","BAJFINANCE"],"REENTRY",  "Re-enter quality stocks after pullback"),
  ("Pushya",           "Saturn",  "Sattva", "ACCUMULATE", ["Banking","FMCG","Healthcare"],["HDFCBANK","ICICIBANK","SBIN"],  "LONGTERM", "Most auspicious — SIP, blue-chip, long-term"),
  ("Ashlesha",         "Mercury", "Sattva", "CAUTION",    ["Pharma","AI","Derivatives"], ["DRREDDY","TCS"],                 "ANALYSTS", "Hidden volatility; thorough due diligence"),
  ("Magha",            "Ketu",    "Rajas",  "STABLE",     ["PSU","Infrastructure"],      ["NTPC","COALINDIA","POWERGRID"],  "LONGTERM", "Avoid modern-tech speculation"),
  ("Purva Phalguni",   "Venus",   "Rajas",  "BULLISH",    ["FMCG","Fashion","Travel"],   ["HINDUNILVR","GOLD","MARUTI"],    "MOMENTUM", "Festive/seasonal rally window"),
  ("Uttara Phalguni",  "Sun",     "Sattva", "STABLE",     ["Banking","Government","B2B"],["HDFCBANK","NTPC"],               "LONGTERM", "Foundation-building; partnerships"),
  ("Hasta",            "Moon",    "Sattva", "TACTICAL",   ["IT Services","E-commerce"],  ["TCS","WIPRO","INFY"],            "SWING",    "Precision timing; book partial profits"),
  ("Chitra",           "Mars",    "Tamas",  "BOLD",       ["Infrastructure","AI","Engineering"],["TATASTEEL","TCS","ULTRACEMCO"],"MOMENTUM","Watch for sudden reversals; Mars speed"),
  ("Swati",            "Rahu",    "Tamas",  "SPECULATIVE",["E-commerce","Fintech","Telecom"],["TECHM","HCLTECH"],           "OPTIONS",  "Stay alert; social media & algo-driven"),
  ("Vishakha",         "Jupiter", "Rajas",  "DIRECTIONAL",["Conglomerates","Banking","Energy"],["RELIANCE","HDFCBANK","BAJFINANCE"],"MIDLONG","Patient but powerful momentum"),
  ("Anuradha",         "Saturn",  "Tamas",  "STEADY",     ["Telecom","B2B","Networks"],  ["TECHM","HCLTECH"],              "BUY_HOLD", "Alliance-based growth; dividend stocks"),
  ("Jyeshtha",         "Mercury", "Rajas",  "VOLATILE",   ["Defense","Central Banks","Risk"],["SBIN","HDFCBANK"],          "NEWS",     "Decisive action; earnings season focus"),
  ("Mula",             "Ketu",    "Tamas",  "CAUTION",    ["Biotech","Distressed"],      ["DRREDDY","CIPLA","SUNPHARMA"],  "CONTRARIAN","Root-level disruption; exit unsustainable positions"),
  ("Purvashadha",      "Venus",   "Rajas",  "BULLISH",    ["Wellness","Export","EdTech"],["HINDUNILVR","GOLD"],            "MOMENTUM", "Ride consumer optimism; brand-driven"),
  ("Uttarashadha",     "Sun",     "Rajas",  "STABLE",     ["Infrastructure","Renewables"],["NTPC","POWERGRID","SUNPHARMA"],"LONGTERM", "Patient; ethical; long-term vision"),
  ("Shravan",          "Moon",    "Rajas",  "STEADY",     ["Banking","Media","Legal"],   ["HDFCBANK","SBIN","TECHM"],      "TREND",    "Follow fundamentals; trustworthy leadership"),
  ("Dhanishtha",       "Mars",    "Tamas",  "FAST",       ["Media","Machinery","Sports"],["TATASTEEL","M&M","HINDALCO"],   "INTRADAY", "Performance-driven; price action"),
  ("Shatabhisha",      "Rahu",    "Tamas",  "CONTRARIAN", ["Pharma","AI","Cybersecurity"],["DRREDDY","TCS","CIPLA"],       "RESEARCH", "Avoid hype; research-backed entries only"),
  ("Purva Bhadrapada", "Jupiter", "Rajas",  "VOLATILE",   ["Wellness","ESG","Alt-Invest"],["HDFCLIFE","SBILIFE"],         "SWING",    "Watch red flags; hidden intensity"),
  ("Uttara Bhadrapada","Saturn",  "Tamas",  "DEFENSIVE",  ["Green","Healthcare","Elder"], ["NTPC","SUNPHARMA","HDFCBANK"], "SIP",      "Patience rewarded; avoid quick-flips"),
  ("Revati",           "Mercury", "Sattva", "STEADY",     ["Logistics","Healthcare","Edu"],["TCS","DRREDDY","HDFCLIFE"],   "BALANCED", "Diversified; stable; risk-managed"),
]

RAHU_KAAL = {
    0: "07:30-09:00",
    1: "15:00-16:30",
    2: "12:00-13:30",
    3: "13:30-15:00",
    4: "10:30-12:00",
    5: "09:00-10:30",
    6: "none"
}

ABHIJIT_MUHURAT = "11:30-12:00"

def get_current_nakshatra(analysis_date: date) -> dict:
    moon_lon, moon_vel = moon_longitude(analysis_date)
    idx  = int(moon_lon / NAK_SPAN) % 27
    pada = int((moon_lon % NAK_SPAN) / (NAK_SPAN / 4)) + 1
    n    = NAKSHATRAS[idx]
    return {
        "number": idx + 1,
        "name": n[0],
        "ruler": n[1],
        "guna": n[2],
        "behavior": n[3],
        "fav_sectors": n[4],
        "fav_instruments": n[5],
        "trade_style": n[6],
        "caution": n[7],
        "pada": pada,
        "moon_longitude": round(moon_lon, 2),
        "rahu_kaal": RAHU_KAAL.get(analysis_date.weekday(), "none"),
        "abhijit_muhurat": ABHIJIT_MUHURAT,
    }

def compute_nakshatra_alignment(symbol: str, analysis_date: date, inv_type: str = "swing",
                                 ruling_planet: str = None, sector: str = None) -> dict:
    nak = get_current_nakshatra(analysis_date)
    
    # Resolve ruling planet and sector if not provided
    if not ruling_planet or not sector:
        try:
            from data.instruments import get_instrument
            inst = get_instrument(symbol)
            if inst:
                if not ruling_planet:
                    ruling_planet = inst.ruling_planet
                if not sector:
                    sector = inst.sector
        except Exception:
            pass

    score = 0
    fav_instruments = [i.upper() for i in nak["fav_instruments"]]
    
    # ── Condition 1: Instrument is in the Nakshatra's favored list (+5) ──
    if symbol.upper() in fav_instruments:
        score += 5

    # ── Condition 2: Instrument's ruling planet matches Nakshatra ruler (+3) ──
    if ruling_planet and ruling_planet.lower() == nak["ruler"].lower():
        score += 3

    # ── Condition 3: Nakshatra trade style matches investment type (+2) ──
    style_ok = {
        "swing": ["SWING", "MOMENTUM", "INTRADAY", "TACTICAL", "BOLD", "NEWS", "EXPERT"],
        "short": ["SWING", "TREND", "MOMENTUM", "MIDLONG", "REENTRY", "CONTRARIAN"],
        "long":  ["BUY_HOLD", "LONGTERM", "ACCUMULATE", "SIP", "BALANCED", "DEFENSIVE", "STEADY"]
    }
    if nak["trade_style"] in style_ok.get(inv_type, []):
        score += 2

    # ── Behavior gate: some behaviors reduce score ──
    if nak["behavior"] in ["EXIT_ONLY", "CAUTION"] and inv_type != "long":
        score -= 5      # Bharani / Ashlesha — not good for new entries
    if nak["behavior"] == "SPECULATIVE" and inv_type == "long":
        score -= 3      # Speculative Nakshatras penalise long-term entries

    score = max(0, min(10, score))

    # ── Guna bonus for long-type: Sattva Nakshatras are best for accumulation ──
    if inv_type == "long" and nak["guna"] == "Sattva":
        score = min(10, score + 2)    # Pushya/Punarvasu/Uttara Phalguni etc

    return {
        "nak_score": score,
        "nakshatra": nak["name"],
        "favored_today": symbol.upper() in fav_instruments,
        **nak
    }

def get_rahu_kaal_today(analysis_date: date) -> dict:
    weekday = analysis_date.weekday()
    window = RAHU_KAAL.get(weekday, "none")
    day_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][weekday]
    
    # Check if market hours overlap (IST market 09:15 to 15:30)
    overlap = False
    if window != "none":
        overlap = True  # Weekday rahu kaal always has some market hour overlap except Sunday
    return {
        "day": day_name,
        "window_ist": window,
        "market_overlap": overlap
    }

def _parse_time_range(t_str: str) -> Tuple[int, int]:
    t_clean = t_str.replace("IST", "").strip()
    if "-" in t_clean or "–" in t_clean:
        sep = "-" if "-" in t_clean else "–"
        parts = t_clean.split(sep)
        start_part = parts[0].strip()
        end_part = parts[1].strip()
    else:
        start_part = t_clean
        try:
            h, m = map(int, start_part.split(":"))
            start_m = h * 60 + m
            return start_m, start_m + 30
        except Exception:
            return 0, 0
            
    try:
        sh, sm = map(int, start_part.split(":"))
        eh, em = map(int, end_part.split(":"))
        return sh * 60 + sm, eh * 60 + em
    except Exception:
        return 0, 0

def _times_overlap(time_a_str: str, time_b_str: str) -> bool:
    if not time_a_str or not time_b_str or time_b_str.lower() == "none" or time_a_str.lower() == "none":
        return False
    start_a, end_a = _parse_time_range(time_a_str)
    start_b, end_b = _parse_time_range(time_b_str)
    if start_a == 0 and end_a == 0:
        return False
    if start_b == 0 and end_b == 0:
        return False
    return max(start_a, start_b) < min(end_a, end_b)

def get_trade_timing_guidance(buy_time_ist: str, analysis_date: date) -> dict:
    rk = get_rahu_kaal_today(analysis_date)
    rahu_warning = _times_overlap(buy_time_ist, rk["window_ist"])
    return {
        "rahu_kaal_today": rk["window_ist"],
        "rahu_warning":    rahu_warning,
        "abhijit_window":  ABHIJIT_MUHURAT,
        "timing_note":     "⚠️ Entry window overlaps Rahu Kaal — shift to Abhijit (11:30–12:00)" if rahu_warning else
                           "✓ Entry window is clear of Rahu Kaal"
    }

def get_upcoming_transitions(analysis_date: date, days: int = 14) -> list:
    """Return next N Nakshatra transitions with dates."""
    transitions = []
    # Get current index
    moon_lon, _ = moon_longitude(analysis_date)
    prev_idx = int(moon_lon / NAK_SPAN) % 27
    for d in range(1, days + 1):
        dt  = analysis_date + timedelta(days=d)
        m_lon, _ = moon_longitude(dt)
        idx = int(m_lon / NAK_SPAN) % 27
        if idx != prev_idx:
            n = NAKSHATRAS[idx]
            transitions.append({
                "date": dt.isoformat(),
                "nakshatra": n[0],
                "ruler": n[1],
                "behavior": n[3],
                "number": idx + 1
            })
            prev_idx = idx
    return transitions

# Alias for compatibility with the report text
get_upcoming_nakshatra_transitions = get_upcoming_transitions
