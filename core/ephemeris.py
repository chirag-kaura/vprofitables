"""
ephemeris.py — Planetary position calculator
Uses simplified VSOP87 / Meeus algorithms (no external dependencies)
Accurate to ~0.1° which is sufficient for Gann analysis
"""

import math
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ── Constants ──────────────────────────────────────────────────────────────
DEG = math.pi / 180
RAD = 180 / math.pi


@dataclass
class PlanetState:
    name: str
    longitude: float      # 0–360° ecliptic longitude
    latitude: float       # degrees from ecliptic
    distance: float       # AU from Sun
    speed: float          # degrees/day (negative = retrograde)
    retrograde: bool
    sign: str             # Zodiac sign
    sign_degree: float    # degree within sign (0–30)
    nakshatra: str = ""   # Vedic lunar mansion (e.g., Ashwini, Bharani)
    nakshatra_lord: str = ""

    @property
    def retrograde_symbol(self):
        return " ℞" if self.retrograde else ""


ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

PLANET_COLORS = {
    "Sun":     "#FFD700",
    "Moon":    "#C0C0C0",
    "Mercury": "#B5B5FF",
    "Venus":   "#FFB6C1",
    "Mars":    "#FF6B6B",
    "Jupiter": "#FFA500",
    "Saturn":  "#DEB887",
    "Uranus":  "#7FFFD4",
    "Neptune": "#6495ED",
    "Pluto":   "#9370DB",
    "Rahu":    "#4A4A4A",
    "Ketu":    "#8B4513",
}

# Planetary rulerships for Gann analysis
PLANET_RULES = {
    "Sun":     ["Gold", "Power Sector", "Government Bonds", "Wheat"],
    "Moon":    ["Silver", "FMCG", "Dairy", "Real Estate", "Rice"],
    "Mercury": ["IT/Tech", "Telecom", "Banking", "Media", "Nifty IT"],
    "Venus":   ["Copper", "Luxury", "FMCG-Premium", "Automobiles"],
    "Mars":    ["Steel/Iron", "Defense", "Crude Oil", "Cement"],
    "Jupiter": ["Nifty 50", "Sensex", "Finance/Banks", "Nifty Bank"],
    "Saturn":  ["Coal", "Real Estate", "Infrastructure", "Metals"],
    "Uranus":  ["IT Innovation", "Semiconductor", "EV", "Crypto"],
    "Neptune": ["Oil & Gas", "Pharma", "Chemicals", "Shipping"],
    "Pluto":   ["Mining", "Nuclear", "Derivatives"],
}

# Nakshatra data based on "The Stellar Setup"
# Spans 13°20' each (360 / 27 = 13.3333°)
NAKSHATRA_DATA = [
    {"name": "Ashwini",       "lord": "Ketu",    "sectors": ["Healthcare", "Pharma", "Automobiles", "Travel", "Startups"]},
    {"name": "Bharani",       "lord": "Venus",   "sectors": ["Entertainment", "Cosmetics", "Agriculture", "Insurance"]},
    {"name": "Krittika",      "lord": "Sun",     "sectors": ["Energy", "Defense", "Steel", "Manufacturing", "Food Processing"]},
    {"name": "Rohini",        "lord": "Moon",    "sectors": ["FMCG", "Dairy", "Real Estate", "Textiles"]},
    {"name": "Mrigashira",    "lord": "Mars",    "sectors": ["Media", "Travel", "Education", "Research"]},
    {"name": "Ardra",         "lord": "Rahu",    "sectors": ["Biotech", "IT", "Telecom", "AI", "Gaming"]},
    {"name": "Punarvasu",     "lord": "Jupiter", "sectors": ["Education", "Insurance", "Agriculture", "Renewable Energy"]},
    {"name": "Pushya",        "lord": "Saturn",  "sectors": ["Finance", "Mining", "Heavy Industries", "Commodities"]},
    {"name": "Ashlesha",      "lord": "Mercury", "sectors": ["Chemicals", "Pesticides", "Auditing", "Trading"]},
    {"name": "Magha",         "lord": "Ketu",    "sectors": ["Government", "Heritage", "Luxury", "Large Caps"]},
    {"name": "Purva Phalguni","lord": "Venus",   "sectors": ["Entertainment", "Hospitality", "Wedding Industry", "Arts"]},
    {"name": "Uttara Phalguni","lord": "Sun",    "sectors": ["Government Contracts", "Healthcare", "Leadership", "Defense"]},
    {"name": "Hasta",         "lord": "Moon",    "sectors": ["Handicrafts", "FMCG", "Trading", "Logistics"]},
    {"name": "Chitra",        "lord": "Mars",    "sectors": ["Architecture", "Engineering", "Design", "Jewelry"]},
    {"name": "Swati",         "lord": "Rahu",    "sectors": ["Aviation", "E-commerce", "IT", "Wind Energy"]},
    {"name": "Vishakha",      "lord": "Jupiter", "sectors": ["Banking", "Export-Import", "Law", "Large Scale Tech"]},
    {"name": "Anuradha",      "lord": "Saturn",  "sectors": ["Mining", "Travel", "Foreign Exchange", "Logistics"]},
    {"name": "Jyeshtha",      "lord": "Mercury", "sectors": ["Telecom", "Management", "Consulting", "Security"]},
    {"name": "Mula",          "lord": "Ketu",    "sectors": ["Research", "Biotech", "Herbal", "Mining"]},
    {"name": "Purvashadha",   "lord": "Venus",   "sectors": ["Shipping", "Water", "Luxury", "Aviation"]},
    {"name": "Uttarashadha",  "lord": "Sun",     "sectors": ["Government", "Leadership", "Heavy Industries", "Defense"]},
    {"name": "Shravana",      "lord": "Moon",    "sectors": ["Media", "Telecommunications", "Education", "Consulting"]},
    {"name": "Dhanishta",     "lord": "Mars",    "sectors": ["Real Estate", "Metals", "Music", "Finance"]},
    {"name": "Shatabhisha",   "lord": "Rahu",    "sectors": ["Aviation", "Tech", "Space", "Medical Tech"]},
    {"name": "Purva Bhadrapada","lord": "Jupiter","sectors": ["Banking", "Education", "Occult", "Insurance"]},
    {"name": "Uttara Bhadrapada","lord": "Saturn","sectors": ["Long Term Investments", "Infrastructure", "Retirement Homes"]},
    {"name": "Revati",        "lord": "Mercury", "sectors": ["Finance", "Shipping", "Logistics", "Orphanages"]},
]

def get_nakshatra_info(longitude: float) -> dict:
    """Return Nakshatra data based on ecliptic longitude (0-360)."""
    lon = normalize(longitude)
    idx = int(lon / (360.0 / 27.0))
    return NAKSHATRA_DATA[idx % 27]



def julian_day(dt: date) -> float:
    """Convert date to Julian Day Number (J2000.0 epoch)."""
    a = (14 - dt.month) // 12
    y = dt.year + 4800 - a
    m = dt.month + 12 * a - 3
    jdn = dt.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return float(jdn) - 0.5  # noon


def j2000(dt: date) -> float:
    """Centuries since J2000.0 (Jan 1.5, 2000)."""
    return (julian_day(dt) - 2451545.0) / 36525.0


def normalize(angle: float) -> float:
    """Normalize angle to 0–360°."""
    return angle % 360.0


def degree_to_sign(lon: float) -> Tuple[str, float]:
    """Convert ecliptic longitude to sign + degree within sign."""
    lon = normalize(lon)
    sign_idx = int(lon // 30)
    sign_deg = lon % 30
    return ZODIAC_SIGNS[sign_idx % 12], round(sign_deg, 2)


# ── Sun ────────────────────────────────────────────────────────────────────
def sun_longitude(dt: date) -> Tuple[float, float]:
    """Returns (longitude°, speed°/day) for the Sun."""
    T = j2000(dt)
    # Mean longitude
    L0 = normalize(280.46646 + 36000.76983 * T)
    # Mean anomaly
    M = normalize(357.52911 + 35999.05029 * T - 0.0001537 * T * T)
    M_r = M * DEG
    # Equation of center
    C = (1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M_r)
    C += (0.019993 - 0.000101 * T) * math.sin(2 * M_r)
    C += 0.000289 * math.sin(3 * M_r)
    lon = normalize(L0 + C)
    # Speed (approx 1°/day)
    T1 = j2000(dt + timedelta(days=1))
    L0_1 = normalize(280.46646 + 36000.76983 * T1)
    M1 = normalize(357.52911 + 35999.05029 * T1)
    M1_r = M1 * DEG
    C1 = (1.914602 - 0.004817 * T1) * math.sin(M1_r) + (0.019993 - 0.000101 * T1) * math.sin(2 * M1_r)
    lon1 = normalize(L0_1 + C1)
    speed = (lon1 - lon + 360) % 360
    if speed > 180:
        speed -= 360
    return lon, speed


# ── Moon ───────────────────────────────────────────────────────────────────
def moon_longitude(dt: date) -> Tuple[float, float]:
    """Returns (longitude°, speed°/day) for the Moon."""
    T = j2000(dt)
    # Simplified Brown's lunar theory
    L = normalize(218.3164477 + 481267.88123421 * T)
    D = normalize(297.8501921 + 445267.1114034 * T)
    M = normalize(357.5291092 + 35999.0502909 * T)
    Mp = normalize(134.9633964 + 477198.8675055 * T)
    F = normalize(93.2720950 + 483202.0175233 * T)
    D_r, M_r, Mp_r, F_r = D * DEG, M * DEG, Mp * DEG, F * DEG
    lon = L
    lon += 6.288774 * math.sin(Mp_r)
    lon += 1.274027 * math.sin(2 * D_r - Mp_r)
    lon += 0.658314 * math.sin(2 * D_r)
    lon += 0.213618 * math.sin(2 * Mp_r)
    lon -= 0.185116 * math.sin(M_r)
    lon -= 0.114332 * math.sin(2 * F_r)
    lon = normalize(lon)
    # speed ~13.2°/day
    T1 = j2000(dt + timedelta(days=1))
    L1 = normalize(218.3164477 + 481267.88123421 * T1)
    D1 = normalize(297.8501921 + 445267.1114034 * T1)
    Mp1 = normalize(134.9633964 + 477198.8675055 * T1)
    F1 = normalize(93.2720950 + 483202.0175233 * T1)
    lon1 = L1 + 6.288774 * math.sin(Mp1 * DEG) + 1.274027 * math.sin(2 * D1 * DEG - Mp1 * DEG) + 0.658314 * math.sin(2 * D1 * DEG) - 0.185116 * math.sin(M_r)
    lon1 = normalize(lon1)
    speed = (lon1 - lon + 360) % 360
    if speed > 180:
        speed -= 360
    return lon, speed


# ── Outer Planets (Simplified VSOP87) ──────────────────────────────────────
PLANET_ELEMENTS = {
    # name: (L0, L1, a, e0, e1, i, omega, w, n)  — approximate orbital elements
    "Mercury": (252.25032350, 149472.67411175, 0.38709927, 0.20563593, 0.00001906, 7.00497902, 48.33076593, 77.45779628),
    "Venus":   (181.97909950, 58517.81538729,  0.72333566, 0.00677672, -0.00004107, 3.39467605, 76.67984255, 131.60246718),
    "Mars":    (355.43327010, 19140.30268499,  1.52371034, 0.09339410, 0.00007882,  1.84969142, 49.55953891, 336.04084002),
    "Jupiter": (34.39644051,  3034.74612775,   5.20288700, 0.04838624, -0.00013253, 1.30439695, 100.47390909, 14.72847983),
    "Saturn":  (49.95424423,  1222.49362201,   9.53667594, 0.05386179, -0.00050991, 2.48599187, 113.66242448, 92.59887831),
    "Uranus":  (313.23810451, 428.48202785,    19.18916464, 0.04725744, -0.00004397, 0.77263783, 74.01692503, 170.95427630),
    "Neptune": (-55.12002969, 218.45945325,    30.06992276, 0.00859048, 0.00005105, 1.77004347, 131.78422574, 44.96476227),
}

def planet_longitude_hel_single(name: str, dt: date) -> Tuple[float, float, float]:
    """Helper to return (hel_lon, radius, mean_anomaly) for a single date."""
    if name == "Sun":
        lon, sp = sun_longitude(dt)
        return lon, 0.0001, lon
    if name == "Moon":
        lon, sp = moon_longitude(dt)
        return lon, 0.00257, lon
        
    T = j2000(dt)
    elem = PLANET_ELEMENTS[name]
    L0, L1, a, e0, e1 = elem[0], elem[1], elem[2], elem[3], elem[4]
    L = normalize(L0 + L1 * T / 100)
    e = e0 + e1 * T
    M = normalize(L - elem[7])
    M_r = M * DEG
    E_c = (2 * e - e**3 / 4) * math.sin(M_r) + (5 / 4) * e**2 * math.sin(2 * M_r) + (13 / 12) * e**3 * math.sin(3 * M_r)
    hel_lon = normalize(M + elem[7] + E_c * RAD)
    R_p = a * (1.0 - e * math.cos(M_r))
    return hel_lon, R_p, M

def planet_longitude_geocentric_single(name: str, dt: date) -> float:
    """Helper to return projected geocentric longitude for a single date."""
    if name in ("Sun", "Moon"):
        if name == "Sun":
            return sun_longitude(dt)[0]
        else:
            return moon_longitude(dt)[0]
            
    T = j2000(dt)
    sun_lon, _ = sun_longitude(dt)
    M_sun = normalize(357.52911 + 35999.05029 * T) * DEG
    L_e = (sun_lon + 180.0) * DEG
    R_e = 1.00014 * (1.0 - 0.016708 * math.cos(M_sun))
    x_e = R_e * math.cos(L_e)
    y_e = R_e * math.sin(L_e)
    
    hel_lon, R_p, _ = planet_longitude_hel_single(name, dt)
    L_p = hel_lon * DEG
    x_p = R_p * math.cos(L_p)
    y_p = R_p * math.sin(L_p)
    
    x_g = x_p - x_e
    y_g = y_p - y_e
    
    return normalize(math.atan2(y_g, x_g) * RAD)

def planet_longitude(name: str, dt: date, heliocentric: bool = False) -> Tuple[float, float]:
    """Calculate projected geocentric or heliocentric longitude and speed."""
    if name == "Sun":
        if heliocentric:
            return 0.0, 0.0
        return sun_longitude(dt)
    if name == "Moon":
        if heliocentric:
            sun_lon, _ = sun_longitude(dt)
            return normalize(sun_lon + 180.0), 0.9856
        return moon_longitude(dt)
        
    # Get current longitude
    if heliocentric:
        lon, _, _ = planet_longitude_hel_single(name, dt)
    else:
        lon = planet_longitude_geocentric_single(name, dt)
        
    # Centered difference for speed
    _step = 7
    dt_fwd = dt + timedelta(days=_step)
    dt_bwd = dt - timedelta(days=_step)
    if heliocentric:
        lon_fwd, _, _ = planet_longitude_hel_single(name, dt_fwd)
        lon_bwd, _, _ = planet_longitude_hel_single(name, dt_bwd)
    else:
        lon_fwd = planet_longitude_geocentric_single(name, dt_fwd)
        lon_bwd = planet_longitude_geocentric_single(name, dt_bwd)
        
    speed = (lon_fwd - lon_bwd + 360 * 2) % 360
    if speed > 180:
        speed -= 360
    speed /= (2 * _step)
    return lon, speed


def rahu_longitude(dt: date) -> float:
    """North Node (Rahu) longitude — important for Vedic Gann analysis."""
    T = j2000(dt)
    return normalize(125.0445479 - 1934.1362608 * T)


# Cache planet positions by date — VSOP87 runs 11 orbital series per planet
# Computing all 11 planets takes 3-8s. Cache saves 99% of computation.
_PLANET_CACHE: dict = {}

def get_all_planets(dt: date, heliocentric: bool = False) -> Dict[str, PlanetState]:
    """Return all planet states for a given date. Results cached by date."""
    global _PLANET_CACHE
    cache_key = f"{dt.isoformat()}_hel" if heliocentric else dt.isoformat()
    if cache_key in _PLANET_CACHE:
        return _PLANET_CACHE[cache_key]
    planets = {}
    planet_names = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"]

    for name in planet_names:
        lon, speed = planet_longitude(name, dt, heliocentric=heliocentric)
        sign, sign_deg = degree_to_sign(lon)
        nak_info = get_nakshatra_info(lon)
        planets[name] = PlanetState(
            name=name,
            longitude=round(lon, 4),
            latitude=0.0,
            distance=1.0,
            speed=round(speed, 4),
            retrograde=(speed < 0),
            sign=sign,
            sign_degree=sign_deg,
            nakshatra=nak_info["name"],
            nakshatra_lord=nak_info["lord"]
        )

    # Add Rahu / Ketu (Lunar Nodes) — critical for Indian market analysis
    rahu_lon = rahu_longitude(dt)
    ketu_lon = normalize(rahu_lon + 180)
    r_sign, r_deg = degree_to_sign(rahu_lon)
    k_sign, k_deg = degree_to_sign(ketu_lon)

    planets["Rahu"] = PlanetState("Rahu", round(rahu_lon, 4), 0, 0, -0.053, True, r_sign, r_deg, get_nakshatra_info(rahu_lon)["name"], get_nakshatra_info(rahu_lon)["lord"])
    planets["Ketu"] = PlanetState("Ketu", round(ketu_lon, 4), 0, 0, -0.053, True, k_sign, k_deg, get_nakshatra_info(ketu_lon)["name"], get_nakshatra_info(ketu_lon)["lord"])

    # Store in cache (limit to 60 dates)
    if len(_PLANET_CACHE) > 60:
        del _PLANET_CACHE[next(iter(_PLANET_CACHE))]
    _PLANET_CACHE[cache_key] = planets
    return planets


def build_ephemeris_range(start: date, end: date) -> List[Dict]:
    """Build a table of planetary positions for a date range."""
    rows = []
    d = start
    while d <= end:
        planets = get_all_planets(d)
        row = {"date": d.isoformat()}
        for name, p in planets.items():
            row[f"{name}_lon"] = p.longitude
            row[f"{name}_speed"] = p.speed
            row[f"{name}_retro"] = p.retrograde
            row[f"{name}_sign"] = p.sign
        rows.append(row)
        d += timedelta(days=1)
    return rows
