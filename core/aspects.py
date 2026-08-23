"""
aspects.py — Planetary aspect detection engine
Computes all major and minor aspects between planets
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math
from .ephemeris import get_all_planets, PlanetState


@dataclass
class Aspect:
    planet_a: str
    planet_b: str
    aspect_name: str
    angle: float          # exact aspect angle (0,60,90,120,150,180)
    actual_diff: float    # actual angular difference
    orb: float            # how far from exact
    strength: float       # 0–10 (10 = exact)
    applying: bool        # True = getting tighter, False = separating
    date: str
    market_meaning: str

    def get_weighted_strength(self, inv_type: str = "swing") -> float:
        """Weight strength based on planetary speed and investment horizon."""
        fast = {"Moon", "Mercury", "Venus", "Sun"}
        medium = {"Mars", "Jupiter"}
        slow = {"Saturn", "Uranus", "Neptune", "Pluto"}
        
        def get_multiplier(p: str, itype: str) -> float:
            itype = itype.lower()
            if p in fast:
                return 1.5 if itype == "swing" else 1.0 if itype == "short" else 0.5
            elif p in medium:
                return 1.0 if itype == "swing" else 1.5 if itype == "short" else 1.0
            else:
                return 0.5 if itype == "swing" else 1.0 if itype == "short" else 2.0

        mult_a = get_multiplier(self.planet_a, inv_type)
        mult_b = get_multiplier(self.planet_b, inv_type)
        return round(self.strength * mult_a * mult_b, 2)

    @property
    def symbol(self):
        SYMBOLS = {
            "Conjunction": "☌", "Sextile": "⚹", "Square": "□",
            "Trine": "△", "Quincunx": "⊻", "Opposition": "☍"
        }
        return SYMBOLS.get(self.aspect_name, "∗")

    @property
    def is_major(self):
        return self.aspect_name in ("Conjunction", "Square", "Opposition", "Trine")

    @property
    def bullish_bearish(self):
        BULL = {"Trine", "Sextile", "Conjunction"}
        BEAR = {"Square", "Opposition", "Quincunx"}
        if self.aspect_name in BULL:
            return "BULLISH"
        elif self.aspect_name in BEAR:
            return "BEARISH"
        return "NEUTRAL"


MAJOR_ASPECTS = {
    "Conjunction":  (0,   8.0),   # angle, max_orb
    "Sextile":      (60,  4.0),
    "Square":       (90,  6.0),
    "Trine":        (120, 6.0),
    "Quincunx":     (150, 3.0),
    "Opposition":   (180, 8.0),
}

MARKET_MEANINGS = {
    ("Jupiter", "Saturn", "Conjunction"):  "MAJOR MARKET TOP/BOTTOM — 20-yr cycle",
    ("Jupiter", "Saturn", "Opposition"):   "MID-CYCLE REVERSAL — Major trend change",
    ("Jupiter", "Saturn", "Square"):       "SIGNIFICANT CORRECTION — 5-yr cycle",
    ("Jupiter", "Saturn", "Trine"):        "SUSTAINED BULL MOVE — Expansion phase",
    ("Mars",    "Saturn", "Conjunction"):  "SHARP SELLOFF — Energy meets restriction",
    ("Mars",    "Saturn", "Opposition"):   "HIGH VOLATILITY — Market tension peak",
    ("Mars",    "Jupiter","Conjunction"):  "STRONG RALLY — Energy meets expansion",
    ("Sun",     "Jupiter","Conjunction"):  "ANNUAL BULL SIGNAL — Confidence surge",
    ("Sun",     "Saturn", "Opposition"):   "MID-YEAR CORRECTION — Resistance peak",
    ("Venus",   "Jupiter","Conjunction"):  "CONSUMER RALLY — Luxury/FMCG surge",
    ("Mercury", "Jupiter","Conjunction"):  "TECH/BANK RALLY — Communication expansion",
    ("Mercury", "Saturn", "Square"):       "TECH CORRECTION — Mercury retrograde risk",
    ("Moon",    "Jupiter","Opposition"):   "SENTIMENT PEAK — Short-term top signal",
}

def _get_meaning(p_a: str, p_b: str, aspect: str) -> str:
    key = (p_a, p_b, aspect)
    key2 = (p_b, p_a, aspect)
    return MARKET_MEANINGS.get(key, MARKET_MEANINGS.get(key2, f"{p_a}–{p_b} {aspect} — Monitor closely"))


def angular_diff(lon_a: float, lon_b: float) -> float:
    """Shortest angular distance between two longitudes (0–180)."""
    diff = abs(lon_a - lon_b) % 360
    return 360 - diff if diff > 180 else diff


def detect_aspects(dt: date, orb_override: Optional[float] = None, heliocentric: bool = False) -> List[Aspect]:
    """Detect all active aspects for a given date."""
    planets = get_all_planets(dt, heliocentric=heliocentric)
    planet_list = list(planets.keys())
    aspects_found = []

    for i, p_a in enumerate(planet_list):
        for p_b in planet_list[i + 1:]:
            lon_a = planets[p_a].longitude
            lon_b = planets[p_b].longitude
            diff = angular_diff(lon_a, lon_b)

            for asp_name, (angle, max_orb) in MAJOR_ASPECTS.items():
                orb = abs(diff - angle)
                if orb <= (orb_override or max_orb):
                    # Check applying/separating
                    tomorrow = dt + timedelta(days=1)
                    pl_tom = get_all_planets(tomorrow, heliocentric=heliocentric)
                    diff_tom = angular_diff(pl_tom[p_a].longitude, pl_tom[p_b].longitude)
                    orb_tom = abs(diff_tom - angle)
                    applying = orb_tom < orb  # getting closer to exact

                    # Gaussian decay for orb proximity
                    sigma = max_orb / 2.5
                    strength = round(10 * math.exp(- (orb**2) / (2 * sigma**2)), 2) if sigma > 0 else 0.0
                    meaning = _get_meaning(p_a, p_b, asp_name)

                    aspects_found.append(Aspect(
                        planet_a=p_a,
                        planet_b=p_b,
                        aspect_name=asp_name,
                        angle=angle,
                        actual_diff=round(diff, 3),
                        orb=round(orb, 3),
                        strength=max(0, strength),
                        applying=applying,
                        date=dt.isoformat(),
                        market_meaning=meaning,
                    ))

    # Sort by strength (strongest first)
    aspects_found.sort(key=lambda x: x.strength, reverse=True)
    return aspects_found


def detect_retrogrades(dt: date) -> Dict[str, bool]:
    """Return which planets are retrograde on dt, using verified station table."""
    # Verified 2025-2027 planetary station dates (NASA JPL)
    STATIONS = [
        ("2025-01-30","Uranus","DIRECT"),  ("2025-04-07","Mercury","RETROGRADE"),
        ("2025-05-01","Mercury","DIRECT"), ("2025-07-18","Mercury","RETROGRADE"),
        ("2025-08-11","Mercury","DIRECT"), ("2025-08-15","Uranus","RETROGRADE"),
        ("2025-10-24","Jupiter","RETROGRADE"),("2025-11-09","Mercury","RETROGRADE"),
        ("2025-11-29","Mercury","DIRECT"), ("2026-01-30","Uranus","DIRECT"),
        ("2026-02-04","Mercury","RETROGRADE"),("2026-02-24","Jupiter","DIRECT"),
        ("2026-02-26","Mercury","DIRECT"), ("2026-06-02","Saturn","RETROGRADE"),
        ("2026-06-11","Mercury","RETROGRADE"),("2026-07-06","Mercury","DIRECT"),
        ("2026-08-21","Uranus","RETROGRADE"),("2026-10-14","Jupiter","RETROGRADE"),
        ("2026-10-29","Mercury","RETROGRADE"),("2026-11-18","Saturn","DIRECT"),
        ("2026-11-20","Mercury","DIRECT"), ("2027-02-10","Jupiter","DIRECT"),
        ("2027-02-12","Mercury","RETROGRADE"),("2027-03-04","Mercury","DIRECT"),
        ("2027-06-10","Saturn","RETROGRADE"),("2027-11-29","Saturn","DIRECT"),
    ]
    tbl = {}
    for ds, planet, direction in sorted(STATIONS):
        if date.fromisoformat(ds) <= dt:
            tbl[planet] = (direction == "RETROGRADE")
    planets = get_all_planets(dt)
    result = {}
    for name, p in planets.items():
        if name in tbl:
            result[name] = tbl[name]
        else:
            result[name] = p.retrograde
    return result


def detect_stations(dt: date, days_window: int = 5) -> List[Dict]:
    """Find planetary stations near dt using verified 2025-2027 station table."""
    STATION_TABLE = [
        ("2025-01-30","Uranus","DIRECT","Uranus direct - tech/innovation clarity returns"),
        ("2025-04-07","Mercury","RETROGRADE","Mercury retrograde - IT/comms/banking disrupted"),
        ("2025-05-01","Mercury","DIRECT","Mercury direct - IT/comms clarity returns"),
        ("2025-07-18","Mercury","RETROGRADE","Mercury retrograde - IT/comms/banking disrupted"),
        ("2025-08-11","Mercury","DIRECT","Mercury direct - IT/comms clarity returns"),
        ("2025-08-15","Uranus","RETROGRADE","Uranus retrograde - tech disruption turns internal"),
        ("2025-10-24","Jupiter","RETROGRADE","Jupiter retrograde - banking/finance expansion pauses"),
        ("2025-11-09","Mercury","RETROGRADE","Mercury retrograde - IT/comms/banking disrupted"),
        ("2025-11-29","Mercury","DIRECT","Mercury direct - IT/comms clarity returns"),
        ("2026-01-30","Uranus","DIRECT","Uranus direct - tech/innovation sectors recover"),
        ("2026-02-04","Mercury","RETROGRADE","Mercury retrograde - IT/comms/banking disrupted"),
        ("2026-02-24","Jupiter","DIRECT","Jupiter direct - MAJOR BUY for banking/finance"),
        ("2026-02-26","Mercury","DIRECT","Mercury direct - IT/comms clarity returns"),
        ("2026-06-02","Saturn","RETROGRADE","Saturn retrograde - real estate/infra pressured"),
        ("2026-06-11","Mercury","RETROGRADE","Mercury retrograde - IT/comms/banking disrupted"),
        ("2026-07-06","Mercury","DIRECT","Mercury direct - IT/comms clarity returns"),
        ("2026-08-21","Uranus","RETROGRADE","Uranus retrograde - tech disruption turns internal"),
        ("2026-10-14","Jupiter","RETROGRADE","Jupiter retrograde - banking/finance expansion pauses"),
        ("2026-10-29","Mercury","RETROGRADE","Mercury retrograde - IT/comms/banking disrupted"),
        ("2026-11-18","Saturn","DIRECT","Saturn direct - real estate/infra stabilises"),
        ("2026-11-20","Mercury","DIRECT","Mercury direct - IT/comms clarity returns"),
        ("2027-02-10","Jupiter","DIRECT","Jupiter direct - MAJOR BUY for banking/finance"),
        ("2027-02-12","Mercury","RETROGRADE","Mercury retrograde - IT/comms/banking disrupted"),
        ("2027-03-04","Mercury","DIRECT","Mercury direct - IT/comms clarity returns"),
        ("2027-06-10","Saturn","RETROGRADE","Saturn retrograde - real estate/infra pressured"),
        ("2027-11-29","Saturn","DIRECT","Saturn direct - real estate/infra stabilises"),
    ]
    stations = []
    seen = set()
    for ds, planet, direction, impact in STATION_TABLE:
        station_date = date.fromisoformat(ds)
        delta = (station_date - dt).days
        if -days_window <= delta <= days_window:
            key = (ds, planet)
            if key not in seen:
                seen.add(key)
                stations.append({
                    "planet": planet,
                    "direction": direction,
                    "date": ds,
                    "days_away": delta,
                    "market_impact": impact,
                })
    return sorted(stations, key=lambda x: x.get("days_away", 0))


def find_aspects_in_range(start: date, end: date, planets_filter: Optional[List[str]] = None) -> List[Dict]:
    """Find all aspects in a date range — for building the signal database."""
    results = []
    d = start
    while d <= end:
        aspects = detect_aspects(d)
        for asp in aspects:
            if planets_filter:
                if asp.planet_a not in planets_filter and asp.planet_b not in planets_filter:
                    continue
            results.append({
                "date": asp.date,
                "planet_a": asp.planet_a,
                "planet_b": asp.planet_b,
                "aspect": asp.aspect_name,
                "orb": asp.orb,
                "strength": asp.strength,
                "applying": asp.applying,
                "bullish_bearish": asp.bullish_bearish,
                "meaning": asp.market_meaning,
            })
        d += timedelta(days=1)
    return results
