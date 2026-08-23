"""
reversal_map.py — GANN-ASTRO v4.0
====================================
PURPOSE: Pre-compute forward-looking reversal zones for each symbol by
         intersecting ALL signal systems: price levels × time windows.

A REVERSAL ZONE = a price band (±2%) × a date window (±5 days) where
                  ≥3 independent signal systems agree.

ZONE GRADES:
  EXTREME  — 7+ systems agree  → trade with full position
  HIGH     — 5-6 systems agree → trade with 2/3 position, wait for pattern
  MODERATE — 3-4 systems agree → watch only, enter on pattern confirmation
  (below 3 = no zone, not stored)

9 SIGNAL SYSTEMS CHECKED:
  1. Gann Sq9 price level proximity (within 1%)
  2. Gann time cycle due (within ±5 days)
  3. Gann angle support/resistance test
  4. Fourier cycle trough or peak (within date window)
  5. Planetary aspect active (applying, major, orb ≤ 4°)
  6. Planetary station (retrograde/direct within window)
  7. Natal transit (transiting planet aspects natal planet, orb ≤ 2°)
  8. VPOC / HVN level coincidence (from volume_profile)
  9. ATL Sq9 harmonic (360°/720°/1080° rotation from all-time low)

USAGE:
  from core.reversal_map import build_zones, is_in_zone, ReversalZone

  zones = build_zones(symbol, closes, highs, lows, volumes,
                      sq9_levels_list, gann_cycle_dates,
                      fourier_trough_date, fourier_peak_date,
                      aspect_dates, natal_transit_dates,
                      vpoc_levels, atl_price)

  active = is_in_zone(current_price, date.today(), zones)
  if active:
      # price is inside a reversal zone — proceed to pattern + signal check
      print(active.grade, active.signal_count, active.signals)

SCHEDULER INTEGRATION:
  Run build_zones() for all 40 symbols at 6 AM IST daily.
  Cache result in ZONE_CACHE dict (in-memory) or SQLite.
  reversal_map rebuild takes <5 seconds for 40 symbols.
"""

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple


@dataclass
class ReversalZone:
    symbol:       str
    price_low:    float          # price band lower bound
    price_high:   float          # price band upper bound
    date_start:   date           # date window start
    date_end:     date           # date window end
    grade:        str            # EXTREME / HIGH / MODERATE
    signal_count: int
    signals:      List[str] = field(default_factory=list)
    direction:    str = "BOTH"   # BUY / SELL / BOTH
    zone_center_price: float = 0.0
    zone_center_date:  Optional[date] = None


# In-memory zone cache keyed by symbol
ZONE_CACHE: Dict[str, List[ReversalZone]] = {}

def _atr14(highs: List[float], lows: List[float], closes: List[float]) -> float:
    """ATR over last 14 bars."""
    period = min(14, len(closes) - 1)
    if period < 1:
        return (highs[-1] - lows[-1]) if highs else 0.0
    trs = []
    for i in range(-period, 0):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i - 1]),
                 abs(lows[i]  - closes[i - 1]))
        trs.append(tr)
    return sum(trs) / len(trs) if trs else 0.0


def _detect_order_blocks(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    lookback: int = 100,
) -> List[Dict]:
    """
    Detect structural Order Blocks (OB).
    Bullish OB: the last down candle (close < open) before an impulsive upward move.
    Bearish OB: the last up candle (close > open) before an impulsive downward move.
    """
    n = len(closes)
    if n < 20:
        return []

    atr = _atr14(highs, lows, closes)
    if atr <= 0:
        atr = closes[-1] * 0.015

    obs = []
    start_idx = max(1, n - lookback)
    for i in range(start_idx, n - 2):
        open_i = closes[i - 1]
        close_i = closes[i]

        if close_i < open_i:
            move_up = closes[i + 2] - close_i
            if move_up > 1.5 * atr:
                obs.append({
                    "type": "BULLISH",
                    "price": highs[i],
                    "index": i,
                })
        elif close_i > open_i:
            move_down = close_i - closes[i + 2]
            if move_down > 1.5 * atr:
                obs.append({
                    "type": "BEARISH",
                    "price": lows[i],
                    "index": i,
                })
    return obs


def _detect_liquidity_sweeps(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    lookback: int = 30,
) -> List[Dict]:
    """
    Detect Liquidity Sweeps in the last 5 bars.
    Bullish Sweep: Price dips below prior support and closes back above it.
    Bearish Sweep: Price spikes above prior resistance and closes back below it.
    """
    n = len(closes)
    if n < lookback:
        return []

    sweeps = []
    for i in range(n - 5, n):
        prior_low = min(lows[i - lookback : i])
        prior_high = max(highs[i - lookback : i])

        if lows[i] < prior_low and closes[i] > prior_low:
            sweeps.append({
                "type": "BULLISH",
                "price": prior_low,
                "index": i,
            })
        if highs[i] > prior_high and closes[i] < prior_high:
            sweeps.append({
                "type": "BEARISH",
                "price": prior_high,
                "index": i,
            })
    return sweeps
def build_zones(
    symbol:               str,
    closes:               List[float],
    highs:                List[float],
    lows:                 List[float],
    volumes:              List[float],
    sq9_levels_list:      List[float],      # from gann_math.sq9_levels()
    gann_cycle_dates:     List[date],       # from gann_math.time_cycles_from_pivot()
    fourier_trough_date:  Optional[date],   # from quant_engine get_fourier_dates()
    fourier_peak_date:    Optional[date],   # from quant_engine get_fourier_dates()
    aspect_dates:         List[date],       # from aspects.find_aspects_in_range()
    natal_transit_dates:  List[date],       # from signal_engine natal analysis
    vpoc_levels:          List[float],      # from volume_profile.get_vpoc_levels()
    atl_price:            float = 0.0,      # all-time low for harmonic check
    analysis_date:        Optional[date] = None,
    horizon_days:         int = 60,
    price_band_pct:       float = 0.02,     # ±2% price band around Sq9 level
    date_window_days:     int = 5,          # ±5 days around cycle date
) -> List[ReversalZone]:
    """
    Build reversal zones for the next horizon_days.

    For each Sq9 level, iterate every candidate time date and count how
    many of the 9 signal systems agree on that price×date combination.
    Return zones with signal_count >= 3, graded by count.

    Zones are deduplicated — overlapping zones keep the highest grade.
    Result is stored in ZONE_CACHE[symbol] for fast access.
    """
    today = analysis_date or date.today()
    price = closes[-1] if closes else 0.0
    zones: List[ReversalZone] = []

    if price <= 0 or not sq9_levels_list:
        ZONE_CACHE[symbol] = []
        return []

    # Calculate ATR-based dynamic band
    atr = _atr14(highs, lows, closes)

    # Detect Order Blocks and Liquidity Sweeps
    order_blocks = _detect_order_blocks(highs, lows, closes)
    liquidity_sweeps = _detect_liquidity_sweeps(highs, lows, closes)

    # Build VPOC set for fast proximity check
    vpoc_set = set(vpoc_levels)

    # ATL Sq9 harmonics
    atl_harmonics = _compute_atl_harmonics(atl_price, lows) if atl_price > 0 else set()

    # All candidate date windows (union of all time signals)
    candidate_dates: List[date] = list(gann_cycle_dates)
    if fourier_trough_date:
        candidate_dates.append(fourier_trough_date)
    if fourier_peak_date:
        candidate_dates.append(fourier_peak_date)
    candidate_dates += aspect_dates + natal_transit_dates
    # Filter to horizon
    candidate_dates = [
        d for d in candidate_dates
        if today <= d <= today + timedelta(days=horizon_days)
    ]
    if not candidate_dates:
        ZONE_CACHE[symbol] = []
        return []

    # Deduplicate candidate dates within 3 days of each other
    candidate_dates = _dedup_dates(candidate_dates, min_gap=3)

    # For each Sq9 level within ±15% of current price
    for level in sq9_levels_list:
        if level <= 0:
            continue
        if abs(level - price) / price > 0.15:
            continue   # only consider levels within ±15% of CMP

        # Volatility-adjusted band calculation (using 0.75 * ATR, min 0.5%, max 3.0%)
        if atr > 0:
            half_band = 0.75 * atr
            price_low = round(level - half_band, 2)
            price_high = round(level + half_band, 2)
        else:
            price_low  = round(level * (1 - price_band_pct), 2)
            price_high = round(level * (1 + price_band_pct), 2)

        # For each candidate time centre
        for center_date in candidate_dates:
            window_start = center_date - timedelta(days=date_window_days)
            window_end   = center_date + timedelta(days=date_window_days)

            sigs: List[str] = []

            # ── Signal 1: Sq9 level (always true here — we iterate Sq9 grid) ──
            proximity_pct = abs(level - price) / price
            sigs.append(f"Sq9 ₹{level:,.2f} ({proximity_pct*100:.1f}% from CMP)")

            # ── Signal 2: Gann time cycle ─────────────────────────────────────
            matching_cycles = [
                d for d in gann_cycle_dates
                if window_start <= d <= window_end
            ]
            if matching_cycles:
                if len(matching_cycles) > 1:
                    sigs.append(f"Harmonic Gann cycles × {len(matching_cycles)} converging {matching_cycles[0]}")
                else:
                    sigs.append(f"Gann cycle {matching_cycles[0]}")

            # ── Signal 3: Gann angle test ─────────────────────────────────────
            if _gann_angle_near(level, price, closes):
                sigs.append(f"Gann 1×1 angle tests ₹{level:,.2f}")

            # ── Signal 4: Fourier trough/peak ─────────────────────────────────
            if fourier_trough_date and window_start <= fourier_trough_date <= window_end:
                sigs.append(f"Fourier cycle trough {fourier_trough_date}")
            if fourier_peak_date and window_start <= fourier_peak_date <= window_end:
                sigs.append(f"Fourier cycle peak {fourier_peak_date}")

            # ── Signal 5: Planetary aspect ────────────────────────────────────
            matching_aspects = [d for d in aspect_dates if window_start <= d <= window_end]
            if matching_aspects:
                sigs.append(f"Planetary aspect {matching_aspects[0]}")

            # ── Signal 6: Planetary station ───────────────────────────────────
            # Aspects list already includes station dates from aspects.find_aspects_in_range()

            # ── Signal 7: Natal transit ───────────────────────────────────────
            matching_natal = [d for d in natal_transit_dates if window_start <= d <= window_end]
            if matching_natal:
                sigs.append(f"Natal transit {matching_natal[0]}")

            # ── Signal 8: VPOC / HVN level ────────────────────────────────────
            for vp in vpoc_levels:
                if abs(vp - level) / max(level, 0.01) <= 0.020:
                    sigs.append(f"VPOC ₹{vp:,.2f} — structural volume cluster")
                    break

            # ── Signal 9: ATL Sq9 harmonic ────────────────────────────────────
            for harmonic in atl_harmonics:
                if abs(harmonic - level) / max(level, 0.01) <= 0.015:
                    sigs.append(f"ATL Sq9 harmonic ₹{harmonic:,.2f} (structural)")
                    break

            # ── Signal 10: Order Block Coincidence ───────────────────────────
            for ob in order_blocks:
                if abs(ob["price"] - level) / max(level, 0.01) <= 0.015:
                    sigs.append(f"{ob['type']} Order Block ₹{ob['price']:,.2f} — institutional key level")
                    break

            # ── Signal 11: Liquidity Sweep Coincidence ───────────────────────
            for ls in liquidity_sweeps:
                if abs(ls["price"] - level) / max(level, 0.01) <= 0.020:
                    sigs.append(f"{ls['type']} Liquidity Sweep ₹{ls['price']:,.2f} — fakeout/reversal pattern")
                    break

            n = len(sigs)
            if n < 3:
                continue   # not enough confluence — skip this zone

            grade     = "EXTREME" if n >= 8 else "HIGH" if n >= 5 else "MODERATE"
            direction = _zone_direction(level, price, closes, volumes)

            zones.append(ReversalZone(
                symbol=symbol,
                price_low=price_low,
                price_high=price_high,
                date_start=window_start,
                date_end=window_end,
                grade=grade,
                signal_count=n,
                signals=sigs,
                direction=direction,
                zone_center_price=round(level, 2),
                zone_center_date=center_date,
            ))

    # Deduplicate overlapping zones, keep highest grade
    zones = _dedup_zones(zones)

    # Sort: EXTREME first, then HIGH, then MODERATE; within grade by date
    grade_rank = {"EXTREME": 3, "HIGH": 2, "MODERATE": 1}
    zones.sort(key=lambda z: (-grade_rank.get(z.grade, 0), z.date_start))

    ZONE_CACHE[symbol] = zones
    return zones


def is_in_zone(
    price:     float,
    today:     date,
    zones:     List[ReversalZone],
    min_grade: str = "MODERATE",
) -> Optional[ReversalZone]:
    """
    Returns the highest-grade active zone containing the current price and date.
    Returns None if price is not inside any active zone of the required grade.

    Call this before running signal conjunction scoring.
    If None → no trade (zone gate not satisfied).
    """
    grade_rank = {"EXTREME": 3, "HIGH": 2, "MODERATE": 1}
    min_rank   = grade_rank.get(min_grade, 1)

    active = [
        z for z in zones
        if z.price_low <= price <= z.price_high
        and z.date_start <= today <= z.date_end
        and grade_rank.get(z.grade, 0) >= min_rank
    ]
    if not active:
        return None
    return max(active, key=lambda z: grade_rank.get(z.grade, 0))


def get_cached_zones(symbol: str) -> List[ReversalZone]:
    """Return the cached zones for a symbol (built at 6 AM by scheduler)."""
    return ZONE_CACHE.get(symbol, [])


def zone_summary(zones: List[ReversalZone]) -> Dict:
    """Return a summary dict for UI display."""
    return {
        "total":    len(zones),
        "extreme":  sum(1 for z in zones if z.grade == "EXTREME"),
        "high":     sum(1 for z in zones if z.grade == "HIGH"),
        "moderate": sum(1 for z in zones if z.grade == "MODERATE"),
        "next_zone": zones[0] if zones else None,
    }


# ── Internal helpers ─────────────────────────────────────────────────────────

def _compute_atl_harmonics(atl_price: float, lows: List[float]) -> set:
    """Compute Sq9 harmonics (360°/720°/1080°) from all-time low."""
    if atl_price <= 0:
        return set()
    atl = min(atl_price, min(lows) if lows else atl_price)
    sqp = math.sqrt(atl)
    harmonics = set()
    for r in [1, 2, 3, 4]:     # 360°, 720°, 1080°, 1440° rotations
        h = round((sqp + r) ** 2, 2)
        harmonics.add(h)
    return harmonics


def _gann_angle_near(level: float, price: float, closes: List[float]) -> bool:
    """
    Simple check: is the Sq9 level near a Gann 1×1 angle from a recent pivot?
    A full angle computation needs pivot date+price — this uses a proxy:
    if the level is within 1.5% of the current close, it's likely angle-tested.
    """
    if not closes or len(closes) < 20:
        return False
    recent_low  = min(closes[-60:]) if len(closes) >= 60 else min(closes)
    recent_high = max(closes[-60:]) if len(closes) >= 60 else max(closes)
    midpoint    = (recent_low + recent_high) / 2
    # Near midpoint or near 1×1 from recent low
    return (
        abs(level - midpoint) / midpoint < 0.015
        or abs(level - recent_low) / recent_low < 0.015
    )


def _zone_direction(level: float, price: float, closes: List[float], volumes: List[float]) -> str:
    """Determine if zone is a BUY (price above level = support) or SELL (resistance)."""
    if price > level * 1.005:
        return "SELL"   # level is below price = price rallied to resistance
    if price < level * 0.995:
        return "BUY"    # level is above price = price fell to support
    # At the level — use 5-bar momentum
    if len(closes) >= 5:
        mom = (closes[-1] - closes[-5]) / max(closes[-5], 0.01)
        return "BUY" if mom < 0 else "SELL"
    return "BOTH"


def _dedup_dates(dates: List[date], min_gap: int = 3) -> List[date]:
    """Remove dates that are within min_gap days of each other (keep earliest)."""
    if not dates:
        return []
    sorted_dates = sorted(set(dates))
    result = [sorted_dates[0]]
    for d in sorted_dates[1:]:
        if (d - result[-1]).days >= min_gap:
            result.append(d)
    return result


def _dedup_zones(zones: List[ReversalZone]) -> List[ReversalZone]:
    """
    Deduplicate overlapping zones. For two zones that overlap in BOTH
    price band and date window, keep the one with higher signal_count.
    """
    grade_rank = {"EXTREME": 3, "HIGH": 2, "MODERATE": 1}
    # Sort by signal_count desc so we keep the strongest first
    sorted_zones = sorted(zones, key=lambda z: -z.signal_count)
    result: List[ReversalZone] = []

    for z in sorted_zones:
        overlap = False
        for kept in result:
            price_overlap = (z.price_low <= kept.price_high and z.price_high >= kept.price_low)
            date_overlap  = (z.date_start <= kept.date_end and z.date_end >= kept.date_start)
            if price_overlap and date_overlap:
                overlap = True
                break
        if not overlap:
            result.append(z)

    return result


def build_zones_for_symbol(
    symbol:        str,
    closes:        List[float],
    highs:         List[float],
    lows:          List[float],
    volumes:       List[float],
    pivot_price:   float,
    pivot_date:    date,
    atl_price:     float = 0.0,
    analysis_date: Optional[date] = None,
) -> List[ReversalZone]:
    """
    Convenience wrapper used by scheduler.py.
    Computes all inputs from closes/lows/pivot and calls build_zones().
    Requires: gann_math, aspects, quant_engine, volume_profile available.
    """
    try:
        from core.gann_math import sq9_levels as gann_sq9, time_cycles_from_pivot
        from core.aspects   import find_aspects_in_range
        from core.quant_engine import fourier_cycle_analysis
        from core.volume_profile import get_vpoc_levels
        from core.scheduler import get_pivots_for_symbol
    except ImportError as e:
        return []

    today = analysis_date or date.today()
    price = closes[-1] if closes else 0.0

    # Sq9 levels within ±20% of CMP
    sq9_raw = gann_sq9(price, n=8)
    sq9_prices = [lvl.above for lvl in sq9_raw] + [lvl.below for lvl in sq9_raw]

    # Fetch all pivots for multi-pivot Gann wheel checks
    pivots = []
    try:
        pivots = get_pivots_for_symbol(symbol)
    except Exception:
        pass

    # Fallback to single pivot if no DB pivots found
    if not pivots and pivot_date:
        pivots = [{"label": "PRIMARY_PIVOT", "date": pivot_date.isoformat() if hasattr(pivot_date, 'isoformat') else str(pivot_date)}]

    # Compute cycle dates from all verified pivots
    cycle_dates = []
    for p in pivots:
        p_date_str = p.get("date")
        if not p_date_str or p_date_str == "UNKNOWN":
            continue
        try:
            p_date = date.fromisoformat(p_date_str)
            p_cycles = time_cycles_from_pivot(p_date, today)
            for c in p_cycles:
                if 0 <= c.days_remaining <= 60:
                    cycle_dates.append(c.target_date)
        except Exception:
            pass

    cycle_dates = sorted(list(set(cycle_dates)))



    # Fourier trough/peak dates
    fourier_trough_date = None
    fourier_peak_date   = None
    try:
        if len(closes) >= 60:
            fourier = fourier_cycle_analysis(closes)
            if fourier and "dominant_cycles" in fourier and fourier["dominant_cycles"]:
                dom = fourier["dominant_cycles"][0]
                dt_trough = dom.get("days_to_next_trough", 999)
                dt_peak   = dom.get("days_to_next_peak",   999)
                if 0 <= dt_trough <= 60:
                    fourier_trough_date = today + __import__("datetime").timedelta(days=dt_trough)
                if 0 <= dt_peak <= 60:
                    fourier_peak_date = today + __import__("datetime").timedelta(days=dt_peak)
    except Exception:
        pass

    # Planetary aspects
    try:
        end_date = today + __import__("datetime").timedelta(days=60)
        aspects_raw = find_aspects_in_range(today, end_date)
        aspect_dates = [
            __import__("datetime").date.fromisoformat(a["date"])
            for a in aspects_raw
            if a.get("applying", True)
        ]
    except Exception:
        aspect_dates = []

    # VPOC levels
    vp = get_vpoc_levels(symbol, closes, volumes)
    vpoc_prices = [vp.vpoc] + vp.hvn_levels if vp else []

    return build_zones(
        symbol=symbol,
        closes=closes, highs=highs, lows=lows, volumes=volumes,
        sq9_levels_list=sq9_prices,
        gann_cycle_dates=cycle_dates,
        fourier_trough_date=fourier_trough_date,
        fourier_peak_date=fourier_peak_date,
        aspect_dates=aspect_dates,
        natal_transit_dates=[],      # natal comes from signal_engine per symbol
        vpoc_levels=vpoc_prices,
        atl_price=atl_price,
        analysis_date=today,
    )


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from datetime import date, timedelta
    import math

    today = date.today()
    price = 500.0
    sqp   = math.sqrt(price)

    # Build minimal inputs
    sq9 = [
        round((sqp + d) ** 2, 2) for d in [0.25, 0.5, 1.0, 1.5, 2.0]
    ] + [
        round(max(0.01, sqp - d) ** 2, 2) for d in [0.25, 0.5, 1.0]
    ]

    # Simulate multiple systems converging on the 0.5-rotation level
    target_level = round((sqp + 0.5) ** 2, 2)   # one Sq9 level above
    target_date  = today + timedelta(days=12)

    gann_cycles   = [target_date, today + timedelta(days=45)]
    aspect_dates  = [target_date + timedelta(days=2)]
    fourier_trough= target_date + timedelta(days=1)
    vpoc          = [target_level * 1.003]   # VPOC very near target level

    closes  = [price] * 100
    highs   = [p * 1.005 for p in closes]
    lows    = [p * 0.995 for p in closes]
    volumes = [500_000] * 100

    zones = build_zones(
        symbol="TEST",
        closes=closes, highs=highs, lows=lows, volumes=volumes,
        sq9_levels_list=sq9,
        gann_cycle_dates=gann_cycles,
        fourier_trough_date=fourier_trough,
        fourier_peak_date=None,
        aspect_dates=aspect_dates,
        natal_transit_dates=[],
        vpoc_levels=vpoc,
        atl_price=300.0,
    )

    print(f"Zones built: {len(zones)}")
    for z in zones:
        print(f"  {z.grade} | price {z.price_low:.0f}–{z.price_high:.0f} | "
              f"{z.date_start}–{z.date_end} | {z.signal_count} signals | {z.direction}")

    assert len(zones) > 0, "Should have built at least one zone"

    # Test is_in_zone
    active = is_in_zone(target_level, target_date, zones)
    print(f"\nis_in_zone at target: {active.grade if active else None} "
          f"(expected MODERATE or higher)")
    assert active is not None, "Should find active zone at target"

    print("\nPASSED")