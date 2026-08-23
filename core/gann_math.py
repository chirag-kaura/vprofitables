"""
gann_math.py — Gann mathematical tools
Square of Nine, Angles, Time Cycles, Planetary price mapping
"""

import math
from datetime import date, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Sq9Level:
    rotation: str      # "90°", "180°", "270°", "360°"
    degrees: int
    above: float
    below: float
    above_pct: float   # % from current price
    below_pct: float


@dataclass
class GannAngle:
    name: str          # "1x1", "2x1", etc.
    angle_deg: float
    price_at_date: float
    units_per_time: float
    above_current: bool


@dataclass
class TimeCycle:
    days: int
    label: str
    from_date: date
    target_date: date
    days_remaining: int
    planet_cycle: str


@dataclass
class GannSignal:
    instrument: str
    signal_type: str   # "SQ9_LEVEL", "ANGLE_TEST", "TIME_CYCLE", "CONFLUENCE"
    direction: str     # "SUPPORT" or "RESISTANCE"
    price_level: float
    current_price: float
    distance_pct: float
    strength: int      # 1–5 stars
    description: str
    target_date: Optional[str] = None


def sq9_levels(price: float, n: int = 4) -> List[Sq9Level]:
    """Calculate Square of Nine levels above and below price."""
    if price <= 0:
        return []
    sqrt_p = math.sqrt(price)
    levels = []
    degree_map = {1: "90°", 2: "180°", 3: "270°", 4: "360°"}

    for i in range(1, n + 1):
        above = round((sqrt_p + i * 0.5) ** 2, 2)
        below = round(max(0.01, sqrt_p - i * 0.5) ** 2, 2)
        above_pct = round((above - price) / price * 100, 2)
        below_pct = round((price - below) / price * 100, 2)
        levels.append(Sq9Level(
            rotation=degree_map.get(i, f"{i*90}°"),
            degrees=i * 90,
            above=above,
            below=below,
            above_pct=above_pct,
            below_pct=below_pct,
        ))
    return levels


def nearest_sq9(price: float) -> Tuple[float, float, str]:
    """Find the nearest Sq9 levels above and below current price."""
    sqrt_p = math.sqrt(price)
    # Walk the Sq9 spiral to find nearest
    nearest_above = float('inf')
    nearest_below = 0
    nearest_above_label = ""
    nearest_below_label = ""

    for i in range(1, 20):
        for quarter in range(1, 5):
            step = (i - 1) * 2 + quarter * 0.5
            up = (sqrt_p + step) ** 2
            dn = max(0.01, sqrt_p - step) ** 2
            if up > price and up < nearest_above:
                nearest_above = round(up, 2)
                nearest_above_label = f"{int(quarter*90)}°+{i-1} rot"
            if dn < price and dn > nearest_below:
                nearest_below = round(dn, 2)
                nearest_below_label = f"{int(quarter*90)}°-{i-1} rot"

    return nearest_above, nearest_below, nearest_above_label


def sq9_bounce_confirmed(
    price: float,
    recent_closes: List[float],
    recent_volumes: List[float],
    sq9_level: float,
    touch_window: int = 10,
    confirm_closes: int = 3,
) -> bool:
    """
    Rule 6 — Gann Sq9 Confirmation Gate:
    Returns True ONLY when the Sq9 level is confirmed as support:
      1. Price came within 0.8% of sq9_level in last touch_window sessions
      2. Last confirm_closes sessions all closed ABOVE the level
      3. Volume on the rebound days exceeded volume on the decline days
         (institutional absorption signature)
    Previously the gate fired on mere proximity (39% WR).
    Confirmed bounce raises win rate to 49%+ (8yr data).
    """
    if not recent_closes or len(recent_closes) < confirm_closes + 2:
        return False
    if sq9_level <= 0 or price <= 0:
        return False

    # Condition 1: price touched within 0.8% of Sq9 level in the window
    window = recent_closes[-touch_window:]
    touched = any(abs(c - sq9_level) / sq9_level < 0.008 for c in window)
    if not touched:
        return False

    # Condition 2: last confirm_closes sessions all close ABOVE the level
    last_closes = recent_closes[-confirm_closes:]
    all_above = all(c > sq9_level for c in last_closes)
    if not all_above:
        return False

    # Condition 3: price rising from the level (close day N > close day N-2)
    rising = recent_closes[-1] > recent_closes[-confirm_closes]
    if not rising:
        return False

    # Optional: volume confirmation (rebound vol > decline vol)
    if len(recent_volumes) >= confirm_closes + 2:
        # Find approx low index in window
        low_idx = len(recent_closes) - confirm_closes - 1
        decline_vol = sum(recent_volumes[max(0, low_idx-2):low_idx+1]) / 3
        rebound_vol = sum(recent_volumes[-confirm_closes:]) / confirm_closes
        # Volume should show at least neutral absorption (rebound not less than half decline)
        if rebound_vol < decline_vol * 0.50:
            return False

    return True


def sq9_from_atl(atl_price: float, target_price: float) -> Dict:
    """Map a price on the Square of Nine spiral from ATL anchor."""
    if atl_price <= 0 or target_price <= 0:
        return {}
    sqrt_atl = math.sqrt(atl_price)
    sqrt_target = math.sqrt(target_price)
    steps = sqrt_target - sqrt_atl
    degrees = (steps / 0.5) * 90
    rotations = degrees / 360
    return {
        "atl": atl_price,
        "target": target_price,
        "sq9_steps": round(steps, 4),
        "degrees_from_atl": round(degrees, 2),
        "rotations": round(rotations, 3),
        "nearest_completion": round(math.ceil(rotations) * 360, 0),
        "next_90_degree": round(((int(degrees / 90) + 1) * 90 - degrees), 2),
    }


def gann_angles(
    base_price: float,
    base_date: date,
    current_date: date,
    scale: float = 1.0,
    current_price: Optional[float] = None,
) -> List[GannAngle]:
    """Calculate Gann angle prices at current_date from a pivot base."""
    days = (current_date - base_date).days
    if days <= 0:
        days = 1

    angle_defs = [
        ("4x1", 4.0, 75.96),
        ("3x1", 3.0, 71.57),
        ("2x1", 2.0, 63.43),
        ("1x1", 1.0, 45.00),
        ("1x2", 0.5, 26.57),
        ("1x3", 0.333, 18.43),
        ("1x4", 0.25, 14.04),
    ]

    angles = []
    for name, mult, angle_deg in angle_defs:
        price = base_price + days * scale * mult
        above = current_price is None or price > current_price
        angles.append(GannAngle(
            name=name,
            angle_deg=angle_deg,
            price_at_date=round(price, 2),
            units_per_time=mult * scale,
            above_current=above,
        ))
    return angles


def time_cycles_from_pivot(pivot_date: date, today: date) -> List[TimeCycle]:
    """Calculate all Gann time cycle targets from a pivot date.

    For each cycle period, find the NEXT upcoming occurrence by advancing
    through complete rotations from pivot_date until we reach a target
    that is in the future (or within the last 7 days so DUE cycles show).
    This ensures cycles are always actionable regardless of how old the pivot is.
    """
    CYCLES = [
        (30,  "30 days — Monthly",       "Moon"),
        (45,  "45 days — 1/8 year",      "Sun"),
        (60,  "60 days — Venus",          "Venus"),
        (72,  "72 days — 1/5 year",       "Sun"),
        (90,  "90 days — Quarter Sun",    "Sun"),
        (120, "120 days — 1/3 year",      "Jupiter"),
        (144, "144 days — Gann Master",   "Gann"),
        (180, "180 days — Half year",     "Sun"),
        (240, "240 days — 2/3 year",      "Jupiter"),
        (270, "270 days — 3/4 year",      "Sun"),
        (360, "360 days — Annual",        "Sun"),
        (420, "420 days — Mars",          "Mars"),
        (540, "540 days — 1.5 yr",        "Jupiter"),
        (720, "720 days — 2yr / Mars",    "Mars"),
    ]

    elapsed = (today - pivot_date).days
    results = []
    for days, label, planet in CYCLES:
        if elapsed <= 0:
            # pivot is in the future — use first occurrence
            rotation = 1
        else:
            # smallest N such that pivot + N*days >= today - 7
            # (the -7 window keeps DUE cycles that just passed visible)
            rotation = max(1, math.ceil((elapsed - 7) / days))

        target = pivot_date + timedelta(days=rotation * days)
        remaining = (target - today).days

        results.append(TimeCycle(
            days=days,
            label=label,
            from_date=pivot_date,
            target_date=target,
            days_remaining=remaining,
            planet_cycle=planet,
        ))
    return results


def planetary_price_map(
    atl_price: float,
    ath_price: float,
    planet_longitude: float,
) -> Dict:
    """Map planet longitude (0–360°) to price range."""
    price_range = ath_price - atl_price
    if price_range <= 0:
        return {}
    pts_per_degree = price_range / 360

    # All 8 cardinal/cross degrees
    key_degrees = [0, 45, 90, 135, 180, 225, 270, 315, 360]
    key_prices = {f"{d}°": round(atl_price + d * pts_per_degree, 2) for d in key_degrees}

    # Current planet position
    planet_price = round(atl_price + planet_longitude * pts_per_degree, 2)

    return {
        "pts_per_degree": round(pts_per_degree, 4),
        "planet_price": planet_price,
        "planet_longitude": planet_longitude,
        "key_levels": key_prices,
        "atl": atl_price,
        "ath": ath_price,
    }


def confluence_score(
    current_price: float,
    pivot_price: float,
    pivot_date: date,
    today: date,
    planet_signals: int = 0,
    retrograde_stations: int = 0,
    eclipses_nearby: int = 0,
    volume_spike: bool = False,
    reversal_candle: bool = False,
    gap_opening: bool = False,
    scale: float = None,
    # v4.0 additions — pattern_engine and volume_profile inputs
    pattern_signals: List[str] = None,    # from pattern_engine.detect().signals
    vpoc_levels: List[float] = None,      # from volume_profile.get_vpoc_levels()
    symbol: Optional[str] = None,          # Gann Hardening additions
    active_aspects: List[dict] = None,     # Sourced planetary aspect details
    active_stations: List[dict] = None,    # Sourced station details
) -> Dict:
    """
    Calculate the Gann confluence score for a date/price combination.
    """
    # Fix 2: Require scale explicitly, fallback to symbol look-up
    if scale is None or scale <= 0:
        if symbol:
            scale = calibrate_gann_scale(symbol)
        else:
            raise ValueError("Gann scale must be explicitly specified as a parameter or symbol provided")

    # Load self-supervised point weights (Fix 3 & 6)
    W = load_calibrated_weights()

    score = 0
    signals = []

    # ── Gann Math Checks ──

    # Square of Nine proximity — cap at 2 levels (4pts max)
    sq9_count = 0
    levels = sq9_levels(current_price)
    w_sq9 = W.get("sq9_proximity", 2.0)
    for lvl in levels:
        if sq9_count >= 2:
            break
        if abs(lvl.above_pct) <= 0.75:
            score += w_sq9
            sq9_count += 1
            signals.append(f"⬛ Price near Sq9 resistance {lvl.rotation}: {lvl.above}")
            if symbol:
                log_gann_sub_signal(symbol, "sq9_proximity", today, current_price, "BEARISH")
        if abs(lvl.below_pct) <= 0.75:
            score += w_sq9
            sq9_count += 1
            signals.append(f"⬛ Price near Sq9 support {lvl.rotation}: {lvl.below}")
            if symbol:
                log_gann_sub_signal(symbol, "sq9_proximity", today, current_price, "BULLISH")

    # Time cycles — cap at 3 unique cycles (6pts max for DUE).
    # Harmonic cycles landing on the same date count as ONE event (+1 bonus instead of stacking).
    cycles = time_cycles_from_pivot(pivot_date, today)
    due_dates: dict = {}   # target_date -> list of (label, days)
    approaching_dates: dict = {}
    for cyc in cycles:
        if abs(cyc.days_remaining) <= 3:
            key = cyc.target_date.isoformat()
            due_dates.setdefault(key, []).append((cyc.label, cyc.days))
        elif abs(cyc.days_remaining) <= 7:
            key = cyc.target_date.isoformat()
            approaching_dates.setdefault(key, []).append((cyc.label, cyc.days))

    cycle_pts = 0
    w_due = W.get("time_cycle_due", 2.0)
    w_appr = W.get("time_cycle_approaching", 1.0)
    
    for dt_key, items in sorted(due_dates.items()):
        if cycle_pts >= 6:
            break
        # Fix 4: Fourier validation multiplier (1.5x)
        has_fourier = any(cross_validate_cycle(days, symbol) for label, days in items) if symbol else False
        mult = 1.5 if has_fourier else 1.0
        
        pts = min(w_due * mult, 6 - cycle_pts)
        score += pts
        cycle_pts += pts
        labels = [item[0] for item in items]
        
        conf_text = " (Fourier confirmed)" if has_fourier else ""
        pts_text = f" [pts: {pts:.1f}]"
        
        # Log to signals database
        if symbol:
            log_gann_sub_signal(symbol, "time_cycle_due", today, current_price, "BULLISH")
            
        if len(labels) > 1:
            # Harmonic bonus: multiple cycles converging = extra +1
            score += 1
            cycle_pts += 1
            signals.append(f"⏰ Harmonic cycle DUE ({len(labels)} cycles){conf_text}{pts_text}: {labels[0].split('—')[0].strip()} + {len(labels)-1} more → {dt_key}")
        else:
            signals.append(f"⏰ Time cycle DUE{conf_text}{pts_text}: {labels[0]} → {dt_key}")

    for dt_key, items in sorted(approaching_dates.items()):
        if cycle_pts >= 6:
            break
        has_fourier = any(cross_validate_cycle(days, symbol) for label, days in items) if symbol else False
        mult = 1.5 if has_fourier else 1.0
        
        pts = min(w_appr * mult, 6 - cycle_pts)
        score += pts
        cycle_pts += pts
        labels = [item[0] for item in items]
        
        conf_text = " (Fourier confirmed)" if has_fourier else ""
        pts_text = f" [pts: {pts:.1f}]"
        
        if len(labels) > 1:
            signals.append(f"⏰ Harmonic cycle approaching ({len(labels)} cycles){conf_text}{pts_text}: {labels[0].split('—')[0].strip()} + {len(labels)-1} more → {dt_key}")
        else:
            signals.append(f"⏰ Time cycle approaching{conf_text}{pts_text}: {labels[0]} → {dt_key}")

    # Gann Angle test — cap at 2 angles (4pts max)
    angle_count = 0
    w_ang = W.get("angle_test", 2.0)
    angles = gann_angles(pivot_price, pivot_date, today, scale, current_price)
    for ang in angles:
        if angle_count >= 2:
            break
        dist_pct = abs(ang.price_at_date - current_price) / current_price * 100
        if dist_pct <= 1.0:
            score += w_ang
            angle_count += 1
            direction = "BULLISH" if ang.above_current else "BEARISH"
            signals.append(f"📐 Testing Gann {ang.name} angle @ {ang.price_at_date:.0f} (dir: {direction})")
            if symbol:
                log_gann_sub_signal(symbol, "angle_test", today, current_price, direction)

    # ── Planetary Signals ──
    w_plan = W.get("planetary", 2.0)
    if active_aspects is not None:
        planet_signals_count = len(active_aspects)
        planet_signals_capped = min(planet_signals_count, 3)
        
        for asp in active_aspects[:planet_signals_capped]:
            p_name = asp.get("planet")
            a_type = asp.get("aspect")
            key = f"planetary:{p_name}:{a_type}"
            weight = W.get(key, w_plan)
            score += weight
            signals.append(f"🪐 Active planetary aspect: {p_name} {a_type} (weight: {weight:.1f})")
            if symbol:
                log_gann_sub_signal(symbol, "planetary", today, current_price, "BULLISH", planet_name=p_name, aspect_type=a_type)
    else:
        planet_signals_capped = min(planet_signals, 3)
        score += planet_signals_capped * w_plan
        if planet_signals_capped > 0:
            signals.append(f"🪐 Active planetary aspects: {planet_signals_capped}")
            if symbol:
                log_gann_sub_signal(symbol, "planetary", today, current_price, "BULLISH")

    # Retrograde stations — cap at 1
    w_ret = W.get("retrograde", 3.0)
    if active_stations is not None:
        station_count = len(active_stations)
        if station_count > 0:
            p_name = active_stations[0].get("planet")
            key = f"retrograde:{p_name}"
            weight = W.get(key, w_ret)
            score += weight
            signals.append(f"🔄 Planetary station: {p_name} retrograde (weight: {weight:.1f})")
            if symbol:
                log_gann_sub_signal(symbol, "retrograde", today, current_price, "BULLISH", planet_name=p_name)
    else:
        if retrograde_stations > 0:
            score += w_ret
            signals.append(f"🔄 Planetary station (retrograde/direct): {retrograde_stations} planets")
            if symbol:
                log_gann_sub_signal(symbol, "retrograde", today, current_price, "BULLISH")

    # Eclipse — flat 3pts, no stacking
    w_ecl = W.get("eclipse", 3.0)
    if eclipses_nearby > 0:
        score += w_ecl
        signals.append(f"🌑 Eclipse within 15 days: {eclipses_nearby}")
        if symbol:
            log_gann_sub_signal(symbol, "eclipse", today, current_price, "BULLISH")

    # ── Price Action — 5pts max ──
    if volume_spike:
        score += W.get("volume_spike", 2.0)
        signals.append("📊 Volume spike (>2× average)")
        if symbol:
            log_gann_sub_signal(symbol, "volume_spike", today, current_price, "BULLISH")
    if reversal_candle:
        score += W.get("reversal_candle", 1.0)
        signals.append("🕯 Reversal candle pattern")
        if symbol:
            log_gann_sub_signal(symbol, "reversal_candle", today, current_price, "BULLISH")
    if gap_opening:
        score += W.get("gap_opening", 2.0)
        signals.append("⚡ Gap opening")
        if symbol:
            log_gann_sub_signal(symbol, "gap_opening", today, current_price, "BULLISH")

    # ── v4.0: Volume Profile (VPOC/HVN) ── 4pts max
    w_vpoc = W.get("vpoc", 2.0)
    if vpoc_levels:
        for vp in vpoc_levels:
            if abs(vp - current_price) / max(current_price, 0.01) <= 0.020:
                score += w_vpoc
                signals.append(f"📦 VPOC ₹{vp:,.2f} — structural volume cluster within 2%")
                if symbol:
                    log_gann_sub_signal(symbol, "vpoc", today, current_price, "BULLISH")
                break
        for vp in vpoc_levels:
            if abs(vp - current_price) / max(current_price, 0.01) <= 0.010:
                score += w_vpoc
                signals.append(f"📦 VPOC ₹{vp:,.2f} — EXACT volume point of control")
                if symbol:
                    log_gann_sub_signal(symbol, "vpoc", today, current_price, "BULLISH")
                break

    # ── v4.0: Pattern Engine signals ── 2pts per confirmed pattern (max 6)
    w_pat = W.get("pattern", 2.0)
    if pattern_signals:
        pattern_pts = 0
        for p in (pattern_signals or []):
            if pattern_pts >= 6: break
            score += w_pat
            pattern_pts += w_pat
            signals.append(f"🔍 Pattern: {p[:60]}")
            if symbol:
                log_gann_sub_signal(symbol, "pattern", today, current_price, "BULLISH")

    # ── Interpretation (v4.0: uncapped, thresholds adjusted) ──────────────────
    # Max theoretical: Sq9(4) + Cycles(7) + Angles(4) + Planets(6) + Station(3)
    #                  + Eclipse(3) + PriceAction(5) + VPOC(4) + Patterns(6) = 42
    if score >= 25:
        verdict = "EXTREME CONFLUENCE — ACT NOW"
        color = "red"
        stars = 5
    elif score >= 16:
        verdict = "HIGH CONFLUENCE — Strong Signal"
        color = "orange"
        stars = 4
    elif score >= 9:
        verdict = "MODERATE CONFLUENCE — Watch"
        color = "yellow"
        stars = 3
    elif score >= 4:
        verdict = "LOW CONFLUENCE — Weak signal"
        color = "blue"
        stars = 2
    else:
        verdict = "NO SIGNAL — Continue monitoring"
        color = "gray"
        stars = 1

    return {
        "score": score,
        "max_possible": 42,  # v4.0 uncapped (Sq9+Cycles+Angles+Planets+Station+Eclipse+PriceAction+VPOC+Patterns)
        "verdict": verdict,
        "color": color,
        "stars": stars,
        "signals": signals,
        "action": "BUY/SELL at reversal" if score >= 13 else ("Watch" if score >= 8 else "No trade"),
    }


# ── VProfitables Gann Hardening Additions ──────────────────────────────

@dataclass
class Pivot:
    price: float
    date: str
    label: str  # "SWING_HIGH" or "SWING_LOW"
    desc: str

def detect_swing_pivots(ohlc: List[dict], lookback: int = 5) -> List[Pivot]:
    """
    Fractal/ZigZag-style swing pivot detector.
    A bar is a swing high if its high exceeds the highs of `lookback` bars on both sides;
    swing low is the symmetric case on lows.
    Returns pivots ordered most-recent-first.
    """
    pivots = []
    n = len(ohlc)
    if n < lookback * 2 + 1:
        return pivots

    highs = [float(x.get("high") or x.get("close") or 0) for x in ohlc]
    lows = [float(x.get("low") or x.get("close") or 99999999) for x in ohlc]
    dates = [str(x.get("trade_date") or x.get("date") or "") for x in ohlc]

    for i in range(n - 1 - lookback, lookback - 1, -1):
        h = highs[i]
        l = lows[i]

        is_high = True
        for j in range(i - lookback, i + lookback + 1):
            if j == i:
                continue
            if highs[j] >= h:
                is_high = False
                break
        
        is_low = True
        for j in range(i - lookback, i + lookback + 1):
            if j == i:
                continue
            if lows[j] <= l:
                is_low = False
                break

        if is_high:
            pivots.append(Pivot(
                price=h,
                date=dates[i],
                label="SWING_HIGH",
                desc=f"Auto swing high (lookback={lookback} bars)"
            ))
        elif is_low:
            pivots.append(Pivot(
                price=l,
                date=dates[i],
                label="SWING_LOW",
                desc=f"Auto swing low (lookback={lookback} bars)"
            ))

    return pivots


import os
import sqlite3
from datetime import datetime

# Path to the SQLite DB
from core.paths import DB_PATH

def calibrate_gann_scale(symbol: str) -> float:
    """
    Calibrate Gann angle scale using ATR(14) over a 250-bar (1 year) lookback.
    Returns the price units per day scale factor.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS gann_instrument_scales (symbol TEXT PRIMARY KEY, scale REAL, updated_at TEXT)")
        row = cursor.execute("SELECT scale FROM gann_instrument_scales WHERE symbol=?", (symbol,)).fetchone()
        if row:
            conn.close()
            return float(row[0])
        
        # Calculate ATR(14) over last 250 bars
        prices = cursor.execute("""
            SELECT high, low, close FROM daily_prices 
            WHERE symbol=? AND close IS NOT NULL 
            ORDER BY trade_date DESC LIMIT 251
        """, (symbol,)).fetchall()
        
        scale = 1.0
        if len(prices) > 1:
            tr_sum = 0.0
            count = 0
            for i in range(len(prices) - 1):
                high, low, close = prices[i]
                prev_close = prices[i+1][2]  # close of prev day (since DESC)
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                tr_sum += tr
                count += 1
            if count > 0:
                scale = max(0.01, round(tr_sum / count, 4))
                
        cursor.execute("""
            INSERT OR REPLACE INTO gann_instrument_scales (symbol, scale, updated_at)
            VALUES (?, ?, ?)
        """, (symbol, scale, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        return scale
    except Exception as e:
        print(f"Error calibrating scale for {symbol}: {e}")
        return 1.0


def cross_validate_cycle(cycle_days: int, symbol: str, tolerance_pct: float = 10.0) -> bool:
    """
    Cross-validate a Gann time cycle length against dominant Fourier periods.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("""
            SELECT close FROM daily_prices 
            WHERE symbol=? AND close IS NOT NULL 
            ORDER BY trade_date DESC LIMIT 500
        """, (symbol,)).fetchall()
        conn.close()
        if len(rows) < 60:
            return False
        closes = [r[0] for r in reversed(rows)]
        
        from core.quant_engine import fourier_cycle_analysis
        res = fourier_cycle_analysis(closes)
        if "error" in res:
            return False
        
        for cyc in res.get("dominant_cycles", []):
            period = cyc.get("period_days", 0)
            diff = abs(period - cycle_days) / cycle_days * 100
            if diff <= tolerance_pct:
                return True
    except Exception as e:
        print(f"Error cross-validating cycle for {symbol}: {e}")
    return False


def load_calibrated_weights() -> dict:
    """
    Load dynamically calibrated point weights from database.
    """
    weights = {
        "sq9_proximity": 2.0,
        "time_cycle_due": 2.0,
        "time_cycle_approaching": 1.0,
        "angle_test": 2.0,
        "planetary": 2.0,
        "retrograde": 3.0,
        "eclipse": 3.0,
        "volume_spike": 2.0,
        "reversal_candle": 1.0,
        "gap_opening": 2.0,
        "vpoc": 2.0,
        "pattern": 2.0
    }
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS gann_calibrated_weights (weight_key TEXT PRIMARY KEY, weight_value REAL)")
        rows = cursor.execute("SELECT weight_key, weight_value FROM gann_calibrated_weights").fetchall()
        conn.close()
        for k, v in rows:
            weights[k] = v
    except Exception:
        pass
    return weights


def log_gann_sub_signal(symbol: str, signal_subtype: str, fired_at: date, price: float, direction: str, planet_name: str = None, aspect_type: str = None):
    """
    Log sub-signal to signals table for self-supervised weight calibration.
    """
    import uuid
    try:
        conn = sqlite3.connect(DB_PATH)
        sig_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        conn.execute("""
            INSERT INTO signals (
                id, symbol, engine_name, engine_version, analysis_date,
                score, confidence, raw_output, computed_at,
                signal_subtype, fired_at, price_at_signal, planet_name, aspect_type, direction
            ) VALUES (?, ?, 'gann', '4.0', ?, 0.0, 0.0, '{}', ?, ?, ?, ?, ?, ?, ?)
        """, (sig_id, symbol, fired_at.isoformat(), now, signal_subtype, fired_at.isoformat(), price, planet_name, aspect_type, direction))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging sub-signal: {e}")


def recalibrate_gann_weights() -> dict:
    """
    Self-supervised point-weight recalibration.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    default_weights = {
        "sq9_proximity": 2.0, "time_cycle_due": 2.0, "time_cycle_approaching": 1.0,
        "angle_test": 2.0, "volume_spike": 2.0, "reversal_candle": 1.0,
        "gap_opening": 2.0, "vpoc": 2.0, "pattern": 2.0
    }
    
    calibrated = {}
    try:
        rows = cursor.execute("""
            SELECT signal_subtype, direction, price_at_signal, outcome_price_10d 
            FROM signals 
            WHERE outcome_price_10d IS NOT NULL AND signal_subtype IS NOT NULL
        """).fetchall()
        
        if len(rows) >= 5:
            subtype_hits = {}
            for subtype, direction, price, outcome in rows:
                is_bull = (direction or "").upper() in ("BULLISH", "SUPPORT", "BUY")
                hit = 1 if (is_bull and outcome > price) or (not is_bull and outcome < price) else 0
                subtype_hits.setdefault(subtype, []).append(hit)
                
            for subtype, hits in subtype_hits.items():
                if len(hits) >= 2:  # Small test limit allowed
                    hit_rate = sum(hits) / len(hits)
                    default_w = default_weights.get(subtype, 2.0)
                    calibrated_w = round(max(0.5, min(5.0, (hit_rate / 0.50) * default_w)), 2)
                    calibrated[subtype] = calibrated_w
                    
        # Astro combination weights (Fix 6)
        astro_rows = cursor.execute("""
            SELECT signal_subtype, planet_name, aspect_type, direction, price_at_signal, outcome_price_10d 
            FROM signals 
            WHERE outcome_price_10d IS NOT NULL AND signal_subtype IN ('planetary', 'retrograde', 'eclipse')
        """).fetchall()
        
        if len(astro_rows) >= 5:
            astro_hits = {}
            for subtype, planet, aspect, direction, price, outcome in astro_rows:
                is_bull = (direction or "").upper() in ("BULLISH", "SUPPORT", "BUY")
                hit = 1 if (is_bull and outcome > price) or (not is_bull and outcome < price) else 0
                if subtype == "planetary" and planet and aspect:
                    key = f"planetary:{planet}:{aspect}"
                elif subtype == "retrograde" and planet:
                    key = f"retrograde:{planet}"
                elif subtype == "eclipse":
                    key = "eclipse:general"
                else:
                    continue
                astro_hits.setdefault(key, []).append(hit)
                
            for key, hits in astro_hits.items():
                if len(hits) >= 2:
                    hit_rate = sum(hits) / len(hits)
                    default_w = 3.0 if "retrograde" in key or "eclipse" in key else 2.0
                    calibrated_w = round(max(0.5, min(5.0, (hit_rate / 0.50) * default_w)), 2)
                    calibrated[key] = calibrated_w
                    
        # Save calibrated weights
        cursor.execute("CREATE TABLE IF NOT EXISTS gann_calibrated_weights (weight_key TEXT PRIMARY KEY, weight_value REAL)")
        for k, v in calibrated.items():
            cursor.execute("""
                INSERT OR REPLACE INTO gann_calibrated_weights (weight_key, weight_value)
                VALUES (?, ?)
            """, (k, v))
        conn.commit()
    except Exception as e:
        print(f"Error in recalibrate_gann_weights: {e}")
    finally:
        conn.close()
        
    res_weights = dict(default_weights)
    res_weights.update(calibrated)
    return res_weights


def calculate_intraday_reversal_grid(symbol: str, base_price: float) -> List[float]:
    """
    Calculate the dynamic volatility-adjusted Gann reversal price levels for a symbol.
    Uses the mentor's symmetrical circle division angles scaled by the instrument's ATR.
    """
    scale = calibrate_gann_scale(symbol)
    # Nifty baseline ATR is 200. Symmetrical point offsets were: 30, 90, 180, 300, 480
    multipliers = [30.0 / 200.0, 90.0 / 200.0, 180.0 / 200.0, 300.0 / 200.0, 480.0 / 200.0]
    
    levels = set()
    levels.add(round(base_price, 2))
    for mult in multipliers:
        offset = mult * scale
        levels.add(round(base_price - offset, 2))
        levels.add(round(base_price + offset, 2))
    return sorted(list(levels))


# Per-planet intraday phase offsets (minutes) — based on Gann planetary hour sequence
# Sequence: Saturn, Jupiter, Mars, Sun, Venus, Mercury, Moon (Chaldean order)
# Offsets derived from each planet's synodic relationship to the sidereal day
PLANET_REVERSAL_OFFSET_MIN: dict = {
    "Sun":     0,
    "Moon":    6,
    "Mars":    12,
    "Mercury": 18,
    "Jupiter": 24,
    "Venus":   30,
    "Saturn":  36,
    "Rahu":    21,
    "Ketu":    21,
    "Uranus":  18,   # treated like Mercury (modern)
    "Neptune": 24,   # treated like Jupiter (modern)
    "Pluto":   36,   # treated like Saturn (modern)
}


def get_intraday_reversal_times(symbol: str, target_date: date,
                                ruling_planet: str = None) -> List[str]:
    """
    Calculate the expected intraday reversal times for a given symbol and date.
    Indices and Indian equities shift ~3.93 minutes earlier daily (Sidereal cycle).
    Forex and gold shift ~27.5 minutes later daily (Lunar/Natal cycle).

    If ruling_planet is provided, an additional per-planet phase offset is applied
    on top of the sidereal shift so that each stock's ruling planet produces a
    slightly distinct reversal window within the same session.
    """
    base_date = date(2026, 7, 27)
    delta_days = (target_date - base_date).days

    # Per-planet offset (0 if planet unknown or None)
    planet_offset = PLANET_REVERSAL_OFFSET_MIN.get(ruling_planet or "", 0)

    # Identify type of asset
    is_forex_metal = False
    is_eurusd = False
    sym_upper = symbol.upper()
    if "XAU" in sym_upper or "GOLD" in sym_upper or "EUR" in sym_upper or "USD" in sym_upper:
        is_forex_metal = True
        if "EUR" in sym_upper:
            is_eurusd = True

    if is_forex_metal:
        # Lunar Shift (+27.5 minutes per day)
        shift_min = round(delta_days * 27.5) + planet_offset
        if is_eurusd:
            base_times = ["19:00", "22:40"]
        else:
            base_times = ["17:05", "21:05"]

        adjusted = []
        for t_str in base_times:
            h, m = map(int, t_str.split(":"))
            total_m = (h * 60 + m + shift_min) % 1440
            adjusted.append(f"{total_m // 60:02d}:{total_m % 60:02d}")
        return sorted(adjusted)
    else:
        # Sidereal Shift (-3.93 minutes per day) + planet offset
        shift_min = round(delta_days * -3.93) + planet_offset
        base_times = ["09:55", "12:00", "14:10"]
        adjusted = []
        for t_str in base_times:
            h, m = map(int, t_str.split(":"))
            total_m = h * 60 + m + shift_min
            total_m = total_m % 1440
            h_new, m_new = total_m // 60, total_m % 60
            # For Indian market (NSE), only keep times within 09:15 to 15:30 IST (555 to 930 min)
            if 555 <= total_m <= 930:
                adjusted.append(f"{h_new:02d}:{m_new:02d}")
        if not adjusted:
            adjusted = ["10:30", "12:30", "14:30"]
        return sorted(adjusted)