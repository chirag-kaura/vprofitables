"""
instruments.py — Gann-Astro v3.6
40 instruments: 5 indices + 30 equities + 5 MCX commodities
ATL/ATH: historically researched, split-adjusted, NSE/BSE/MCX-verified
Pre-2000 ATL dates manually researched — seeded as STATIC pivot rows in DB.
Yahoo Finance symbols verified for yfinance compatibility.

TO EXPAND: Add instruments following the same _idx/_eq/_mcx pattern.
The download_history.py --test flag uses TEST_SYMBOLS list in download_history.py.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Dict
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.ephemeris import get_all_planets, PlanetState


# ── NatalChart ───────────────────────────────────────────────────────────────
@dataclass
class NatalChart:
    inception_date:     date
    inception_time_ist: str  = "09:15"
    location:           str  = "Mumbai, India"
    primary_ruler:      str  = "Jupiter"
    secondary_ruler:    str  = "Saturn"
    tertiary_ruler:     str  = "Mars"
    _planets: dict = field(default_factory=dict, repr=False)

    def all_positions(self):
        if not self._planets:
            self._planets = get_all_planets(self.inception_date)
        return self._planets


# ── Instrument ───────────────────────────────────────────────────────────────
@dataclass
class Instrument:
    symbol:           str
    name:             str
    exchange:         str           # NSE / MCX
    instrument_type:  str           # INDEX / EQUITY / COMMODITY
    sector:           str
    ruling_planet:    str
    secondary_planet: str
    all_time_low:     float
    all_time_high:    float
    atl_date:         Optional[date]  # Researched ATL date (manually verified)
    ath_date:         Optional[date]  # Researched ATH date
    inception_date:   date
    yfinance_symbol:  str
    description:      str = ""
    lot_size:         int = 1
    natal: Optional[NatalChart] = field(default=None, repr=False)


# ── Constructor helpers ───────────────────────────────────────────────────────
def _mk(symbol, name, exchange, itype, sector, rp, sp,
        atl, ath, atl_date, ath_date, inception, yf, lot=1):
    nc = NatalChart(
        inception_date=inception,
        primary_ruler=rp, secondary_ruler=sp, tertiary_ruler="Mars",
        location="Mumbai, India",
    )
    return Instrument(
        symbol=symbol, name=name, exchange=exchange, instrument_type=itype,
        sector=sector, ruling_planet=rp, secondary_planet=sp,
        all_time_low=atl, all_time_high=ath,
        atl_date=atl_date, ath_date=ath_date,
        inception_date=inception, yfinance_symbol=yf,
        lot_size=lot, natal=nc,
    )

def _idx(symbol, name, sector, rp, sp, atl, ath, atl_date, ath_date, inception, yf):
    return _mk(symbol, name, "NSE", "INDEX", sector, rp, sp,
               atl, ath, atl_date, ath_date, inception, yf, 1)

def _eq(symbol, name, sector, rp, sp, atl, ath, atl_date, ath_date, inception, yf, lot=1):
    return _mk(symbol, name, "NSE", "EQUITY", sector, rp, sp,
               atl, ath, atl_date, ath_date, inception, yf, lot)

def _mcx(symbol, name, sector, rp, sp, atl, ath, atl_date, ath_date, inception, yf, lot=1):
    return _mk(symbol, name, "MCX", "COMMODITY", sector, rp, sp,
               atl, ath, atl_date, ath_date, inception, yf, lot)


# ════════════════════════════════════════════════════════════════════════════
# 5 KEY NSE INDICES
# ════════════════════════════════════════════════════════════════════════════
# Pre-2000 symbols: Yahoo data starts 2000-01-01.
# ATL/date below is the true historical low (manually verified).
# These are seeded as STATIC pivot rows in pivot_levels DB table.
# ────────────────────────────────────────────────────────────────────────────
NSE_INDICES = {i.symbol: i for i in [
    _idx("NIFTY50",
         "Nifty 50", "Broad Market", "Jupiter", "Saturn",
         atl=854,    atl_date=date(1996, 4, 22),   # True ATL — manually verified
         ath=26277,  ath_date=date(2024, 9, 27),
         inception=date(1996, 4, 22), yf="^NSEI"),

    _idx("BANKNIFTY",
         "Nifty Bank", "Banking", "Jupiter", "Mars",
         atl=805,    atl_date=date(2001, 9, 21),   # post-9/11 low
         ath=54467,  ath_date=date(2024, 9, 26),
         inception=date(2000, 9, 15), yf="^NSEBANK"),

    _idx("NIFTYIT",
         "Nifty IT", "Technology", "Mercury", "Uranus",
         atl=891,    atl_date=date(2001, 9, 21),   # dot-com bust low
         ath=44000,  ath_date=date(2024, 7, 16),
         inception=date(1999, 1, 1), yf="^CNXIT"),

    _idx("NIFTYPHARMA",
         "Nifty Pharma", "Pharma", "Neptune", "Jupiter",
         atl=1197,   atl_date=date(2001, 10, 5),
         ath=22500,  ath_date=date(2024, 9, 27),
         inception=date(2001, 1, 1), yf="^CNXPHARMA"),

    _idx("NIFTYAUTO",
         "Nifty Auto", "Auto", "Venus", "Mars",
         atl=1412,   atl_date=date(2004, 5, 17),
         ath=25980,  ath_date=date(2024, 7, 16),
         inception=date(2004, 1, 1), yf="^CNXAUTO"),
]}


# ════════════════════════════════════════════════════════════════════════════
# 30 KEY NSE EQUITIES
# ════════════════════════════════════════════════════════════════════════════
# Pre-2000 inceptions: ATL is the true historical low (split-adjusted).
# Yahoo Finance .NS data downloaded from max(inception, 2000-01-01).
# ────────────────────────────────────────────────────────────────────────────
NSE_EQUITIES = {i.symbol: i for i in [

    # ── BANKING (5) ──────────────────────────────────────────────────────────
    _eq("HDFCBANK",
        "HDFC Bank", "Banking", "Jupiter", "Moon",
        atl=5,      atl_date=date(1999, 7, 28),    # verified split-adjusted
        ath=1794,   ath_date=date(2023, 7, 3),
        inception=date(1995, 11, 14), yf="HDFCBANK.NS", lot=550),

    _eq("ICICIBANK",
        "ICICI Bank", "Banking", "Jupiter", "Mercury",
        atl=2,      atl_date=date(2002, 5, 28),
        ath=1330,   ath_date=date(2024, 7, 19),
        inception=date(1997, 9, 17), yf="ICICIBANK.NS", lot=700),

    _eq("SBIN",
        "State Bank of India", "Banking", "Saturn", "Jupiter",
        atl=2,      atl_date=date(2003, 5, 12),    # split-adjusted
        ath=912,    ath_date=date(2024, 6, 3),
        inception=date(1993, 3, 1), yf="SBIN.NS", lot=1500),

    _eq("AXISBANK",
        "Axis Bank", "Banking", "Jupiter", "Venus",
        atl=6,      atl_date=date(2001, 9, 21),
        ath=1340,   ath_date=date(2024, 7, 12),
        inception=date(1998, 11, 2), yf="AXISBANK.NS", lot=625),

    _eq("KOTAKBANK",
        "Kotak Mahindra Bank", "Banking", "Jupiter", "Venus",
        atl=10,     atl_date=date(2004, 5, 17),
        ath=2063,   ath_date=date(2023, 12, 1),
        inception=date(2003, 12, 20), yf="KOTAKBANK.NS", lot=400),

    # ── IT (5) ───────────────────────────────────────────────────────────────
    _eq("TCS",
        "Tata Consultancy Services", "IT", "Mercury", "Jupiter",
        atl=430,    atl_date=date(2004, 8, 25),    # IPO low
        ath=4592,   ath_date=date(2024, 9, 5),
        inception=date(2004, 8, 25), yf="TCS.NS", lot=175),

    _eq("INFY",
        "Infosys", "IT", "Mercury", "Uranus",
        atl=18,     atl_date=date(2002, 12, 5),    # split-adjusted post dot-com
        ath=1874,   ath_date=date(2021, 10, 13),
        inception=date(1993, 2, 8), yf="INFY.NS", lot=400),

    _eq("WIPRO",
        "Wipro", "IT", "Mercury", "Saturn",
        atl=7,      atl_date=date(2002, 9, 30),    # split-adjusted
        ath=740,    ath_date=date(2021, 10, 19),
        inception=date(1995, 11, 1), yf="WIPRO.NS", lot=1500),

    _eq("HCLTECH",
        "HCL Technologies", "IT", "Mercury", "Uranus",
        atl=28,     atl_date=date(2001, 9, 21),
        ath=1974,   ath_date=date(2024, 9, 19),
        inception=date(1999, 11, 12), yf="HCLTECH.NS", lot=700),

    _eq("TECHM",
        "Tech Mahindra", "IT", "Mercury", "Mars",
        atl=30,     atl_date=date(2008, 12, 15),
        ath=1762,   ath_date=date(2024, 9, 27),
        inception=date(2006, 8, 28), yf="TECHM.NS", lot=600),

    # ── ENERGY / POWER (5) ───────────────────────────────────────────────────
    _eq("RELIANCE",
        "Reliance Industries", "Oil & Gas", "Jupiter", "Sun",
        atl=35,     atl_date=date(2002, 6, 3),     # split-adjusted
        ath=3218,   ath_date=date(2024, 7, 8),
        inception=date(1995, 11, 29), yf="RELIANCE.NS", lot=250),

    _eq("ONGC",
        "Oil & Natural Gas Corp", "Oil & Gas", "Neptune", "Mars",
        atl=15,     atl_date=date(2002, 10, 14),
        ath=347,    ath_date=date(2024, 9, 13),
        inception=date(1994, 8, 19), yf="ONGC.NS", lot=1975),

    _eq("NTPC",
        "NTPC", "Power", "Sun", "Saturn",
        atl=15,     atl_date=date(2004, 11, 5),    # IPO low
        ath=448,    ath_date=date(2024, 9, 24),
        inception=date(2004, 11, 5), yf="NTPC.NS", lot=2250),

    _eq("POWERGRID",
        "Power Grid Corporation", "Power", "Saturn", "Sun",
        atl=25,     atl_date=date(2007, 10, 5),    # IPO low
        ath=364,    ath_date=date(2024, 9, 24),
        inception=date(2007, 10, 5), yf="POWERGRID.NS", lot=2700),

    _eq("COALINDIA",
        "Coal India", "Mining", "Saturn", "Mars",
        atl=60,     atl_date=date(2013, 9, 27),
        ath=540,    ath_date=date(2024, 9, 11),
        inception=date(2010, 11, 4), yf="COALINDIA.NS", lot=1350),

    # ── FMCG / PHARMA (5) ────────────────────────────────────────────────────
    _eq("HINDUNILVR",
        "Hindustan Unilever", "FMCG", "Moon", "Venus",
        atl=95,     atl_date=date(2001, 10, 2),    # split-adjusted
        ath=3035,   ath_date=date(2023, 9, 29),
        inception=date(1995, 1, 1), yf="HINDUNILVR.NS", lot=300),

    _eq("ITC",
        "ITC", "FMCG", "Moon", "Saturn",
        atl=4,      atl_date=date(2002, 10, 28),   # split-adjusted
        ath=505,    ath_date=date(2024, 9, 26),
        inception=date(1995, 1, 1), yf="ITC.NS", lot=3200),

    _eq("SUNPHARMA",
        "Sun Pharmaceutical", "Pharma", "Neptune", "Jupiter",
        atl=5,      atl_date=date(2000, 4, 7),     # split-adjusted
        ath=1960,   ath_date=date(2024, 9, 26),
        inception=date(1994, 11, 7), yf="SUNPHARMA.NS", lot=700),

    _eq("DRREDDY",
        "Dr Reddys Laboratories", "Pharma", "Neptune", "Mercury",
        atl=55,     atl_date=date(2000, 3, 31),
        ath=7500,   ath_date=date(2024, 9, 24),
        inception=date(1994, 6, 1), yf="DRREDDY.NS", lot=125),

    _eq("CIPLA",
        "Cipla", "Pharma", "Neptune", "Mercury",
        atl=8,      atl_date=date(2000, 6, 12),    # split-adjusted
        ath=1694,   ath_date=date(2024, 9, 11),
        inception=date(1995, 2, 8), yf="CIPLA.NS", lot=650),

    # ── AUTO (4) ─────────────────────────────────────────────────────────────
    _eq("MARUTI",
        "Maruti Suzuki", "Auto", "Venus", "Mercury",
        atl=200,    atl_date=date(2003, 7, 9),     # IPO low
        ath=13680,  ath_date=date(2024, 9, 16),
        inception=date(2003, 7, 9), yf="MARUTI.NS", lot=100),

    _eq("BAJAJ-AUTO",
        "Bajaj Auto", "Auto", "Venus", "Mars",
        atl=100,    atl_date=date(2008, 11, 21),
        ath=12775,  ath_date=date(2024, 9, 26),
        inception=date(2008, 5, 26), yf="BAJAJ-AUTO.NS", lot=75),

    _eq("M&M",
        "Mahindra & Mahindra", "Auto", "Venus", "Mars",
        atl=18,     atl_date=date(2001, 9, 21),    # split-adjusted
        ath=3264,   ath_date=date(2024, 9, 19),
        inception=date(1996, 3, 27), yf="M&M.NS", lot=350),

    _eq("TATAMOTORS",
        "Tata Motors", "Auto", "Saturn", "Mars",
        atl=15,     atl_date=date(2001, 9, 21),    # split-adjusted
        ath=1179,   ath_date=date(2024, 7, 30),
        inception=date(1995, 11, 29), yf="TATAMOTORS.NS", lot=550),

    # ── METALS / CEMENT (3) ──────────────────────────────────────────────────
    _eq("TATASTEEL",
        "Tata Steel", "Metals", "Mars", "Saturn",
        atl=5,      atl_date=date(2001, 9, 21),    # split-adjusted
        ath=175,    ath_date=date(2024, 9, 18),
        inception=date(1995, 11, 29), yf="TATASTEEL.NS", lot=5500),

    _eq("HINDALCO",
        "Hindalco Industries", "Metals", "Saturn", "Mars",
        atl=12,     atl_date=date(2002, 10, 28),   # split-adjusted
        ath=772,    ath_date=date(2024, 9, 26),
        inception=date(1997, 4, 15), yf="HINDALCO.NS", lot=1375),

    _eq("ULTRACEMCO",
        "UltraTech Cement", "Cement", "Saturn", "Mars",
        atl=200,    atl_date=date(2004, 8, 26),    # IPO low
        ath=12400,  ath_date=date(2024, 9, 26),
        inception=date(2004, 8, 26), yf="ULTRACEMCO.NS", lot=100),

    # ── FINANCE / INSURANCE (3) ──────────────────────────────────────────────
    _eq("BAJFINANCE",
        "Bajaj Finance", "Finance", "Jupiter", "Mercury",
        atl=50,     atl_date=date(2011, 12, 20),
        ath=8192,   ath_date=date(2023, 9, 14),
        inception=date(2010, 9, 1), yf="BAJFINANCE.NS", lot=125),

    _eq("HDFCLIFE",
        "HDFC Life Insurance", "Insurance", "Jupiter", "Moon",
        atl=230,    atl_date=date(2020, 3, 24),
        ath=800,    ath_date=date(2021, 10, 18),
        inception=date(2017, 11, 17), yf="HDFCLIFE.NS", lot=1100),

    _eq("SBILIFE",
        "SBI Life Insurance", "Insurance", "Jupiter", "Saturn",
        atl=460,    atl_date=date(2020, 3, 24),
        ath=1950,   ath_date=date(2024, 9, 23),
        inception=date(2017, 10, 3), yf="SBILIFE.NS", lot=750),
]}


# ════════════════════════════════════════════════════════════════════════════
# 5 KEY MCX COMMODITIES
# ════════════════════════════════════════════════════════════════════════════
# MCX futures — Yahoo Finance continuous contract symbols (=F)
# ATL is MCX-traded low (not international spot low)
# ────────────────────────────────────────────────────────────────────────────
MCX_COMMODITIES = {i.symbol: i for i in [
    _mcx("GOLD",
         "Gold (MCX)", "Precious Metal", "Venus", "Sun",
         atl=5600,   atl_date=date(2003, 11, 10),  # MCX listing low
         ath=79685,  ath_date=date(2024, 10, 30),
         inception=date(2003, 11, 10), yf="GC=F", lot=1),

    _mcx("SILVER",
         "Silver (MCX)", "Precious Metal", "Moon", "Venus",
         atl=7200,   atl_date=date(2003, 11, 10),
         ath=99359,  ath_date=date(2024, 10, 22),
         inception=date(2003, 11, 10), yf="SI=F", lot=1),

    _mcx("CRUDEOIL",
         "Crude Oil (MCX)", "Energy", "Sun", "Mars",
         atl=900,    atl_date=date(2016, 1, 20),
         ath=8850,   ath_date=date(2022, 3, 7),
         inception=date(2005, 2, 9), yf="CL=F", lot=1),

    _mcx("NATURALGAS",
         "Natural Gas (MCX)", "Energy", "Mercury", "Neptune",
         atl=80,     atl_date=date(2020, 6, 26),
         ath=900,    ath_date=date(2022, 8, 24),
         inception=date(2006, 1, 17), yf="NG=F", lot=1),

    _mcx("COPPER",
         "Copper (MCX)", "Base Metal", "Venus", "Saturn",
         atl=155,    atl_date=date(2016, 1, 15),
         ath=920,    ath_date=date(2024, 5, 20),
         inception=date(2004, 3, 5), yf="HG=F", lot=1),
]}


# ════════════════════════════════════════════════════════════════════════════
# COMBINED — ALL 40 INSTRUMENTS + NIFTY 500 DYNAMIC REGISTRY
# ════════════════════════════════════════════════════════════════════════════
ALL_INSTRUMENTS: Dict[str, Instrument] = {}
ALL_INSTRUMENTS.update(NSE_INDICES)
ALL_INSTRUMENTS.update(NSE_EQUITIES)
ALL_INSTRUMENTS.update(MCX_COMMODITIES)

def _load_nifty500_registry():
    import csv
    csv_path = os.path.join(os.path.dirname(__file__), "nifty500.csv")
    if not os.path.exists(csv_path):
        return

    # Industry to Planetary Rulers mapping (Gann Astrological Rules)
    INDUSTRY_PLANETS = {
        "Automobile and Auto Components": ("Venus", "Mars"),
        "Capital Goods":                  ("Mars", "Sun"),
        "Chemicals":                      ("Mercury", "Saturn"),
        "Construction":                   ("Saturn", "Moon"),
        "Construction Materials":         ("Saturn", "Mars"),
        "Consumer Durables":              ("Moon", "Venus"),
        "Consumer Services":              ("Venus", "Mercury"),
        "Diversified":                    ("Jupiter", "Saturn"),
        "Fast Moving Consumer Goods":     ("Moon", "Venus"),
        "Financial Services":             ("Jupiter", "Moon"),
        "Healthcare":                     ("Neptune", "Jupiter"),
        "Information Technology":          ("Mercury", "Uranus"),
        "Media Entertainment & Publication": ("Venus", "Mercury"),
        "Metals & Mining":                ("Saturn", "Mars"),
        "Oil Gas & Consumable Fuels":     ("Sun", "Mars"),
        "Power":                          ("Sun", "Saturn"),
        "Realty":                         ("Saturn", "Moon"),
        "Services":                       ("Mercury", "Jupiter"),
        "Telecommunication":              ("Mercury", "Saturn"),
        "Textiles":                       ("Venus", "Moon"),
    }

    try:
        with open(csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = row.get("Symbol", "").strip()
                name = row.get("Company Name", "").strip()
                industry = row.get("Industry", "").strip()
                
                if not symbol or symbol in ALL_INSTRUMENTS:
                    continue
                
                rp, sp = INDUSTRY_PLANETS.get(industry, ("Jupiter", "Saturn"))
                yf_symbol = f"{symbol}.NS"
                inception_d = date(2000, 1, 1)
                
                # New symbols start with placeholder ATL/ATH which are refined
                # dynamically from the daily prices DB table at startup/download
                ALL_INSTRUMENTS[symbol] = _eq(
                    symbol=symbol, name=name, sector=industry,
                    rp=rp, sp=sp,
                    atl=1.0, ath=10000.0,
                    atl_date=None, ath_date=None,
                    inception=inception_d, yf=yf_symbol, lot=1
                )
    except Exception as e:
        print(f"  [WARN] Failed to load nifty500.csv: {e}")

_load_nifty500_registry()


def get_instrument(symbol: str) -> Optional[Instrument]:
    return ALL_INSTRUMENTS.get(symbol.upper())


def get_natal(symbol: str) -> Optional[NatalChart]:
    inst = get_instrument(symbol)
    return inst.natal if inst else None


def list_all_symbols():
    return sorted(ALL_INSTRUMENTS.keys())


def get_transit_to_natal_aspects(natal: NatalChart, transit_date: date):
    # ── Planet classification (Gann) ─────────────────────────────────────────
    BENEFICS  = {"Jupiter", "Venus", "Sun", "Mercury"}   # Mercury = neutral-benefic
    MALEFICS  = {"Saturn", "Mars", "Rahu", "Ketu"}
    # Planet weight by orbital speed (how major an event it signals)
    WEIGHT = {
        "Saturn": "MAJOR", "Rahu": "MAJOR", "Ketu": "MAJOR",
        "Jupiter": "MAJOR", "Uranus": "MEDIUM", "Neptune": "MEDIUM", "Mars": "MEDIUM",
        "Sun": "MINOR", "Venus": "MINOR", "Mercury": "MINOR", "Moon": "MINOR",
    }
    # Orbs: Gann used tight orbs — applying 1°, separating 2°
    # We use slightly wider to be practical: conj/opp 6°, trine/sq 5°, sextile 4°, quincunx 3°
    ORB_LIMITS = {0: 6, 60: 4, 90: 5, 120: 5, 150: 3, 180: 6}

    natal_planets   = natal.all_positions()
    transit_planets = get_all_planets(transit_date)
    # Also get next day positions to determine applying vs separating
    try:
        next_day_planets = get_all_planets(transit_date + __import__('datetime').timedelta(days=1))
    except Exception:
        next_day_planets = {}

    aspects = []
    rulers  = [natal.primary_ruler, natal.secondary_ruler, natal.tertiary_ruler]

    for t_name, t_planet in transit_planets.items():
        for n_name, n_planet in natal_planets.items():
            if t_name == n_name:
                continue  # skip same planet (return to natal self is handled separately)

            raw_diff = (t_planet.longitude - n_planet.longitude) % 360
            diff = min(raw_diff, 360 - raw_diff)

            # Find which aspect angle is closest and check orb
            best_angle, best_orb = None, 999
            for angle, max_orb in ORB_LIMITS.items():
                d = abs(diff - angle)
                if d <= max_orb and d < best_orb:
                    best_angle, best_orb = angle, d

            if best_angle is None:
                continue

            # Aspect name
            ASPECT_NAMES = {
                0:   ("Conjunction \u260c"),
                60:  ("Sextile \u26b9"),
                90:  ("Square \u25a1"),
                120: ("Trine \u25b3"),
                150: ("Quincunx \u26bb"),
                180: ("Opposition \u260d"),
            }
            aspect_name = ASPECT_NAMES[best_angle]

            # ── Nature determination (Gann-correct) ──────────────────────────
            if best_angle == 0:
                # CONJUNCTION: nature depends on planet pair
                if t_name in BENEFICS and n_name in BENEFICS:
                    nature = "BULLISH"
                elif t_name in MALEFICS and n_name in MALEFICS:
                    nature = "BEARISH"
                elif t_name in {"Rahu", "Ketu"} or n_name in {"Rahu", "Ketu"}:
                    nature = "VOLATILE"   # Nodal conjunction = chaotic
                elif t_name in MALEFICS:
                    nature = "BEARISH"    # Malefic transiting benefic natal = bearish
                else:
                    nature = "BULLISH"    # Benefic transiting malefic natal = softening
            elif best_angle in (60, 120):
                nature = "BULLISH"
            elif best_angle in (90, 150, 180):
                nature = "BEARISH"
            else:
                nature = "NEUTRAL"

            # ── Retrograde flip (Gann) ────────────────────────────────────────
            # Retrograde malefic in a normally bullish aspect → BEARISH
            # Retrograde benefic in a normally bearish aspect → softened (NEUTRAL)
            retro = t_planet.retrograde
            if retro:
                if t_name in MALEFICS and nature == "BULLISH":
                    nature = "BEARISH"
                elif t_name in BENEFICS and nature == "BEARISH":
                    nature = "NEUTRAL"

            # ── Applying vs Separating ────────────────────────────────────────
            applying = None
            if t_name in next_day_planets:
                next_t = next_day_planets[t_name]
                diff_today    = abs(t_planet.longitude  - n_planet.longitude) % 360
                diff_today    = min(diff_today, 360 - diff_today)
                diff_tomorrow = abs(next_t.longitude    - n_planet.longitude) % 360
                diff_tomorrow = min(diff_tomorrow, 360 - diff_tomorrow)
                orb_today    = abs(diff_today    - best_angle)
                orb_tomorrow = abs(diff_tomorrow - best_angle)
                applying = orb_tomorrow < orb_today  # getting closer = applying

            aspects.append({
                "transit_planet":     t_name,
                "natal_planet":       n_name,
                "aspect":             aspect_name,
                "orb":                round(best_orb, 2),
                "nature":             nature,
                "transit_retrograde": retro,
                "applying":           applying,          # True=applying, False=separating, None=unknown
                "weight":             WEIGHT.get(t_name, "MINOR"),
                "is_ruler_activated": t_name in rulers or n_name in rulers,
                "label":              f"{t_name} {aspect_name} natal {n_name}",
            })

    # Sort: ruler first, then by weight (MAJOR>MEDIUM>MINOR), then by orb
    W_ORDER = {"MAJOR": 0, "MEDIUM": 1, "MINOR": 2}
    aspects.sort(key=lambda x: (
        0 if x["is_ruler_activated"] else 1,
        W_ORDER.get(x["weight"], 2),
        x["orb"]
    ))
    return aspects


# ── Startup: pre-compute natal charts ────────────────────────────────────────
print(f"  [INIT] Loading {len(ALL_INSTRUMENTS)} instruments (v3.6)...")
_n_idx = sum(1 for i in ALL_INSTRUMENTS.values() if i.instrument_type == "INDEX")
_n_eq  = sum(1 for i in ALL_INSTRUMENTS.values() if i.instrument_type == "EQUITY")
_n_cm  = sum(1 for i in ALL_INSTRUMENTS.values() if i.instrument_type == "COMMODITY")
for inst in ALL_INSTRUMENTS.values():
    if inst.natal:
        try:
            inst.natal.all_positions()
        except Exception:
            pass
print(f"  [INIT] {len(ALL_INSTRUMENTS)} instruments: "
      f"{_n_idx} indices | {_n_eq} equities | {_n_cm} commodities")
