"""
signal_engine.py — Master signal generator
Combines ephemeris + Gann math + aspects → ranked signals
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.ephemeris import get_all_planets, build_ephemeris_range
from core.aspects import detect_aspects, detect_stations, detect_retrogrades
from core.gann_math import (
    sq9_levels, gann_angles, time_cycles_from_pivot,
    confluence_score, planetary_price_map, sq9_from_atl
)
from data.instruments import ALL_INSTRUMENTS, Instrument, get_instrument, get_transit_to_natal_aspects


def analyze_instrument(
    symbol: str,
    current_price: float,
    pivot_price: float,
    pivot_date: date,
    analysis_date: Optional[date] = None,
    volume_spike: bool = False,
    reversal_candle: bool = False,
    gap_opening: bool = False,
) -> Dict:
    """Full Gann + Astro analysis for a single instrument."""

    today = analysis_date or date.today()
    instrument = get_instrument(symbol)
    if instrument is None:
        return {"error": f"Unknown instrument: {symbol}"}

    # ── Planetary Data ──
    heliocentric = (instrument.instrument_type == "COMMODITY")
    planets = get_all_planets(today, heliocentric=heliocentric)
    aspects = detect_aspects(today, heliocentric=heliocentric)
    stations = detect_stations(today, days_window=5)
    retrogrades = detect_retrogrades(today)

    # Filter aspects involving ruling planet
    ruling_aspects = [
        a for a in aspects
        if a.planet_a == instrument.ruling_planet or a.planet_b == instrument.ruling_planet
    ]
    major_aspects = [a for a in aspects if a.is_major and a.orb <= 3.0]

    # Transit-to-natal aspects (the core Gann natal method)
    natal_aspects = []
    if instrument.natal:
        natal_aspects = get_transit_to_natal_aspects(instrument.natal, today)
    ruler_natal_aspects = [a for a in natal_aspects if a.get("is_ruler_activated")]

    # ── Gann Math ──
    from core.gann_math import calibrate_gann_scale
    scale = calibrate_gann_scale(symbol)

    sq9 = sq9_levels(current_price, n=4)
    sq9_atl = sq9_from_atl(instrument.all_time_low, current_price)
    angles = gann_angles(pivot_price, pivot_date, today, scale=scale, current_price=current_price)
    cycles = time_cycles_from_pivot(pivot_date, today)

    # Due cycles
    due_cycles = [c for c in cycles if abs(c.days_remaining) <= 7]
    approaching_cycles = [c for c in cycles if 7 < abs(c.days_remaining) <= 21]

    # ── Planetary Price Map ──
    ruling_planet_state = planets.get(instrument.ruling_planet)
    planet_price_map = None
    if ruling_planet_state:
        planet_price_map = planetary_price_map(
            instrument.all_time_low,
            instrument.all_time_high,
            ruling_planet_state.longitude
        )

    # ── Confluence Score ──
    planet_signal_count = int(sum([a.get_weighted_strength("swing") for a in ruling_aspects if a.orb <= 5]) / 10)
    # Natal ruler activations count as strong planetary signals
    natal_ruler_count = len([a for a in natal_aspects if a.get("is_ruler_activated") and a.get("orb",99) <= 3])
    planet_signal_count = min(planet_signal_count + natal_ruler_count, 5)
    station_count = len(stations)

    # Compile aspects and stations metadata
    active_aspects_list = []
    for a in ruling_aspects:
        if a.orb <= 5:
            active_aspects_list.append({"planet": a.planet_a, "aspect": a.aspect_name})
    for a in natal_aspects:
        if a.get("is_ruler_activated") and a.get("orb", 99) <= 3:
            active_aspects_list.append({"planet": a.get("transit_planet"), "aspect": a.get("aspect")})

    active_stations_list = []
    for s in stations:
        active_stations_list.append({"planet": s["planet"], "direction": s["direction"]})

    conf = confluence_score(
        current_price=current_price,
        pivot_price=pivot_price,
        pivot_date=pivot_date,
        today=today,
        planet_signals=min(planet_signal_count, 3),
        retrograde_stations=station_count,
        volume_spike=volume_spike,
        reversal_candle=reversal_candle,
        gap_opening=gap_opening,
        scale=scale,
        symbol=symbol,
        active_aspects=active_aspects_list,
        active_stations=active_stations_list,
    )

    # ── Next 30 Days Forward Scan ──
    upcoming_signals = _forward_scan(instrument, current_price, today, days=30)

    return {
        "instrument": {
            "symbol": symbol,
            "name": instrument.name,
            "exchange": instrument.exchange,
            "sector": instrument.sector,
            "ruling_planet": instrument.ruling_planet,
            "secondary_planet": instrument.secondary_planet,
            "atl": instrument.all_time_low,
            "ath": instrument.all_time_high,
            "inception_date": instrument.inception_date.isoformat(),
        },
        "analysis_date": today.isoformat(),
        "current_price": current_price,
        "pivot": {
            "price": pivot_price,
            "date": pivot_date.isoformat(),
            "days_ago": (today - pivot_date).days,
        },
        "confluence": conf,
        "gann_math": {
            "sq9_levels": [
                {"rotation": l.rotation, "above": l.above, "below": l.below,
                 "above_pct": l.above_pct, "below_pct": l.below_pct}
                for l in sq9
            ],
            "sq9_from_atl": sq9_atl,
            "angles": [
                {"name": a.name, "angle_deg": a.angle_deg,
                 "price": a.price_at_date, "above": a.above_current}
                for a in angles
            ],
            "time_cycles_due": [
                {"label": c.label, "target_date": c.target_date.isoformat(),
                 "days_remaining": c.days_remaining, "planet": c.planet_cycle}
                for c in due_cycles
            ],
            "time_cycles_approaching": [
                {"label": c.label, "target_date": c.target_date.isoformat(),
                 "days_remaining": c.days_remaining}
                for c in approaching_cycles
            ],
        },
        "planetary": {
            "ruling_planet_position": {
                "name": instrument.ruling_planet,
                "longitude": ruling_planet_state.longitude if ruling_planet_state else None,
                "sign": ruling_planet_state.sign if ruling_planet_state else None,
                "sign_degree": ruling_planet_state.sign_degree if ruling_planet_state else None,
                "retrograde": ruling_planet_state.retrograde if ruling_planet_state else None,
                "speed": ruling_planet_state.speed if ruling_planet_state else None,
            },
            "planet_price_map": planet_price_map,
            "ruling_aspects": [
                {"planets": f"{a.planet_a}–{a.planet_b}",
                 "aspect": a.aspect_name, "orb": a.orb,
                 "strength": a.strength, "symbol": a.symbol,
                 "direction": a.bullish_bearish,
                 "meaning": a.market_meaning}
                for a in ruling_aspects[:5]
            ],
            "major_aspects_today": [
                {"planets": f"{a.planet_a}–{a.planet_b}",
                 "aspect": a.aspect_name, "orb": a.orb,
                 "direction": a.bullish_bearish,
                 "meaning": a.market_meaning}
                for a in major_aspects[:8]
            ],
            "retrograde_planets": [p for p, r in retrogrades.items() if r],
            "stations_nearby": stations,
        },
        "upcoming_signals": upcoming_signals,
        "natal_chart": {
            "inception_date": instrument.natal.inception_date.isoformat() if instrument.natal else None,
            "primary_ruler": instrument.natal.primary_ruler if instrument.natal else None,
            "secondary_ruler": instrument.natal.secondary_ruler if instrument.natal else None,
            "tertiary_ruler": instrument.natal.tertiary_ruler if instrument.natal else None,
            "planets": {
                name: {
                    "longitude": p.longitude,
                    "sign": p.sign,
                    "sign_degree": p.sign_degree,
                    "retrograde": p.retrograde,
                }
                for name, p in instrument.natal.all_positions().items()
            } if instrument.natal else {},
            "transit_to_natal": natal_aspects[:15],
            "ruler_activations": ruler_natal_aspects[:8],
        },
    }


def _auto_scale(p_price, c_price, p_date, today):
    """Auto-calculate angle scale from pivot data."""
    days = max(1, (today - p_date).days)
    return max(0.5, abs(c_price - p_price) / days / 1.5)


def _forward_scan(instrument: Instrument, current_price: float, today: date, days: int = 30) -> List[Dict]:
    """Scan next N days for high-confluence dates."""
    signals = []
    pivot_date = today - timedelta(days=90)  # assume 90d pivot
    from core.gann_math import calibrate_gann_scale
    scale = calibrate_gann_scale(instrument.symbol)

    for i in range(1, days + 1):
        check_date = today + timedelta(days=i)
        aspects = detect_aspects(check_date)
        stations = detect_stations(check_date, days_window=1)

        ruling_aspects = [
            a for a in aspects
            if (a.planet_a == instrument.ruling_planet or
                a.planet_b == instrument.ruling_planet) and a.orb <= 4
        ]
        major = [a for a in aspects if a.is_major and a.orb <= 2]

        if ruling_aspects or stations or major:
            score = len(ruling_aspects) * 2 + len(stations) * 3 + len(major)
            if score >= 3:
                signals.append({
                    "date": check_date.isoformat(),
                    "days_ahead": i,
                    "score": score,
                    "ruling_aspects": [f"{a.planet_a}–{a.planet_b} {a.aspect_name}" for a in ruling_aspects[:3]],
                    "stations": [s["planet"] + " " + s["direction"] for s in stations],
                    "major_aspects": [f"{a.planet_a}–{a.planet_b} {a.aspect_name}" for a in major[:3]],
                    "watch_for": "REVERSAL" if score >= 6 else "MOMENTUM CHANGE",
                })

    signals.sort(key=lambda x: x["score"], reverse=True)
    return signals[:10]


def daily_astro_prefilter(analysis_date: Optional[date] = None) -> List[Dict]:
    """Run quick scan of all instruments for today's high-confluence signals."""
    today = analysis_date or date.today()

    # Pre-compute aspects once
    aspects = detect_aspects(today)
    stations = detect_stations(today)
    planets = get_all_planets(today)

    results = []
    for symbol, inst in ALL_INSTRUMENTS.items():
        ruling_aspects = [
            a for a in aspects
            if a.planet_a == inst.ruling_planet or a.planet_b == inst.ruling_planet
        ]
        score = sum(a.get_weighted_strength("swing") for a in ruling_aspects if a.orb <= 5) + len(stations) * 5

        results.append({
            "symbol": symbol,
            "name": inst.name,
            "exchange": inst.exchange,
            "sector": inst.sector,
            "ruling_planet": inst.ruling_planet,
            "signal_score": score,
            "active_aspects": len(ruling_aspects),
            "stations": len(stations),
            "retrograde": planets.get(inst.ruling_planet, None) and planets[inst.ruling_planet].retrograde,
            "alert": score >= 6,
        })

    results.sort(key=lambda x: x["signal_score"], reverse=True)
    return results


def get_planet_dashboard(analysis_date: Optional[date] = None) -> Dict:
    """Full planetary dashboard for today."""
    today = analysis_date or date.today()
    planets = get_all_planets(today)
    aspects = detect_aspects(today)
    stations = detect_stations(today, days_window=5)
    retrogrades = {name: p.retrograde for name, p in planets.items()}

    return {
        "date": today.isoformat(),
        "planets": {
            name: {
                "longitude": p.longitude,
                "sign": p.sign,
                "sign_degree": p.sign_degree,
                "retrograde": p.retrograde,
                "speed": p.speed,
            }
            for name, p in planets.items()
        },
        "aspects": [
            {
                "symbol": a.symbol,
                "planets": f"{a.planet_a} {a.symbol} {a.planet_b}",
                "orb": a.orb,
                "strength": a.strength,
                "direction": a.bullish_bearish,
                "applying": a.applying,
                "meaning": a.market_meaning,
            }
            for a in aspects[:15]
        ],
        "stations": stations,
        "retrograde_count": sum(retrogrades.values()),
        "retrograde_planets": [p for p, r in retrogrades.items() if r],
    }


# ══════════════════════════════════════════════════════════════════════════════
# v4.0 TWO-SIDED SWING SCANNER
# Evaluates BOTH BUY (at Sq9 support) and SHORT (at Sq9 resistance) for every
# symbol every day. Returns conjunction scores for both directions.
# ══════════════════════════════════════════════════════════════════════════════

def scan_two_sided(
    symbol:         str,
    current_price:  float,
    pivot_price:    float,
    pivot_date:     date,
    closes:         list   = None,
    highs:          list   = None,
    lows:           list   = None,
    volumes:        list   = None,
    regime:         str    = "SIDEWAYS",
    rsi:            float  = 50.0,
    atr14:          float  = 0.0,
    ml_direction:   str    = "NEUTRAL",
    ml_confidence:  float  = 0.0,
    fourier_trough_days: int = 999,
    fourier_peak_days:   int = 999,
    analysis_date:  date   = None,
    inv_type:       str    = "swing",
) -> Dict:
    """
    Run both BUY and SHORT conjunction scoring for a symbol.
    Returns which direction has the better setup today.

    Integrates:
      - gann_math (Sq9 levels, time cycles)
      - pattern_engine (divergence, spring, UTAD)
      - aspects (ruling planet aspects, applying/adverse)
      - unified_logic (conjunction scoring, gates)

    Used by the daily scanner (page_scanner.py) and advisor (page_advisor.py).
    Returns dict with buy_score, short_score, recommended_direction, and
    full level details for the better-scoring side.
    """
    import math
    today = analysis_date or date.today()
    instrument = get_instrument(symbol)

    # ── Sq9 level proximity ──────────────────────────────────────────────────
    sqp = math.sqrt(current_price)
    sq9_sups = [round(max(0.01, sqp - d)**2, 2) for d in [0.25, 0.5, 1.0, 1.5, 2.0]]
    sq9_ress = [round((sqp + d)**2, 2)           for d in [0.25, 0.5, 1.0, 1.5, 2.0]]

    nearest_sup = min(sq9_sups, key=lambda x: abs(x - current_price))
    nearest_res = min(sq9_ress, key=lambda x: abs(x - current_price))
    sq9_sup_prox = abs(current_price - nearest_sup) / current_price
    sq9_res_prox = abs(current_price - nearest_res) / current_price
    
    # Phase 1: Volatility-Adjusted Bands
    band_pct = (0.5 * atr14 / current_price) if atr14 > 0 else 0.015
    sq9_near_sup = sq9_sup_prox <= band_pct
    sq9_near_res = sq9_res_prox <= band_pct

    # ── Gann time cycles ─────────────────────────────────────────────────────
    cycles = time_cycles_from_pivot(pivot_date, today)
    gann_days = min((abs(c.days_remaining) for c in cycles), default=999)

    # ── Ruling planet aspects ────────────────────────────────────────────────
    ruling_planet = instrument.ruling_planet if instrument else "Jupiter"
    aspects_today = detect_aspects(today)
    ruling_aspects = [a for a in aspects_today
                      if (a.planet_a == ruling_planet or a.planet_b == ruling_planet)
                      and a.orb <= 5]
    
    # Phase 3: Astro Gaussian Weighting
    astro_strength = sum(a.get_weighted_strength(inv_type) for a in ruling_aspects)

    adverse_applying = any(
        a for a in ruling_aspects
        if a.bullish_bearish == "BEARISH" and getattr(a, "applying", False)
    )

    # Phase 2: Order Blocks & Liquidity Sweeps
    order_block_active = False
    liquidity_sweep_active = False
    if highs and lows and closes:
        try:
            from core.reversal_map import _detect_order_blocks, _detect_liquidity_sweeps
            obs = _detect_order_blocks(highs, lows, closes)
            sweeps = _detect_liquidity_sweeps(highs, lows, closes)
            # A recent order block or sweep sets the flag to True
            order_block_active = len(obs) > 0
            liquidity_sweep_active = len(sweeps) > 0
        except Exception:
            pass

    # ── Pattern detection (if OHLCV provided) ───────────────────────────────
    rsi_div = 0; vol_exhaust = 0
    wyckoff_spring = False; wyckoff_utad = False; wyckoff_phase_str = ""
    if closes and len(closes) >= 50:
        try:
            from core.pattern_engine import detect as pattern_detect
            pat_r = pattern_detect(closes, highs or [], lows or [], volumes or [])
            rsi_div    = 1 if "RSI bullish" in " ".join(pat_r.signals) else (-1 if "RSI bearish" in " ".join(pat_r.signals) else 0)
            vol_exhaust = 1 if pat_r.volume_exhaustion else (-1 if "distribution" in " ".join(pat_r.signals).lower() else 0)
            wyckoff_spring = pat_r.pattern == "SPRING"
            wyckoff_utad   = pat_r.pattern == "UTAD"
        except Exception:
            pass
        try:
            from core.wyckoff_engine import wyckoff_phase
            wp = wyckoff_phase(closes, highs or [], lows or [], volumes or [])
            wyckoff_phase_str = wp.get("phase_enum", wp.get("phase", ""))
        except Exception:
            pass

    # ── Import conjunction scorer ────────────────────────────────────────────
    from core.unified_logic import (compute_conjunction_score, compute_levels,
                                     compute_levels_short, passes_gate,
                                     PLANET_TRADE_DIRECTION, BAD_BUY_GOOD_SHORT,
                                     BEST_BUY_SYMBOLS)

    # ── Compute vol spike ratio for 10yr-aware conjunction scoring ─────────────
    vol_spike_ratio_val = 1.0
    if volumes and len(volumes) >= 12:
        avg_vol = sum(volumes[-11:-1]) / 10
        vol_spike_ratio_val = round(volumes[-1] / max(avg_vol, 1), 2)

    # ── 10yr ML INVERSION: ML=DOWN = BUY signal, ML=UP = caution ─────────────
    # Remap ml_direction for conjunction scorer:
    # raw model UP(prob>0.55) → contrarian DOWN signal for BUY scoring
    # raw model DOWN(prob<0.45) → contrarian UP signal for BUY scoring
    ml_for_buy   = "DOWN"   if ml_direction == "UP" else ("UP" if ml_direction == "DOWN" else "NEUTRAL")
    ml_for_short = ml_direction   # SHORT uses raw direction (momentum confirmation)

    # ── BUY conjunction score ────────────────────────────────────────────────
    buy_cs = compute_conjunction_score(
        trade_direction="BUY",
        regime=regime,
        sq9_near_support=sq9_near_sup,
        ml_direction=ml_for_buy,     # 10yr: inverted ML for BUY
        rsi_divergence=rsi_div,
        volume_exhaustion=vol_exhaust,
        vol_spike_ratio=vol_spike_ratio_val,   # 10yr: Vol>1.8 = +0.75pt
        wyckoff_spring=wyckoff_spring,
        wyckoff_phase=wyckoff_phase_str,
        fourier_trough_days=fourier_trough_days,
        gann_cycle_days=gann_days,
        ruling_planet=ruling_planet,
        adverse_aspect_applying=adverse_applying,
        astro_strength=astro_strength,
        order_block_active=order_block_active,
        liquidity_sweep_active=liquidity_sweep_active,
        symbol=symbol,
    )

    # ── SHORT conjunction score ──────────────────────────────────────────────
    short_cs = compute_conjunction_score(
        trade_direction="SHORT",
        regime=regime,
        sq9_near_resistance=sq9_near_res,
        ml_direction=ml_for_short,
        rsi_divergence=rsi_div,
        volume_exhaustion=vol_exhaust,
        vol_spike_ratio=vol_spike_ratio_val,
        wyckoff_utad=wyckoff_utad,
        wyckoff_phase=wyckoff_phase_str,
        fourier_peak_days=fourier_peak_days,
        gann_cycle_days=gann_days,
        ruling_planet=ruling_planet,
        adverse_aspect_applying=adverse_applying,
        astro_strength=astro_strength,
        order_block_active=order_block_active,
        liquidity_sweep_active=liquidity_sweep_active,
        symbol=symbol,
    )

    # ── Recommended direction ────────────────────────────────────────────────
    # Prefer BUY if scores are within 1pt of each other and symbol is BUY-preferred
    buy_score  = buy_cs["score"]
    short_score = short_cs["score"]
    planet_pref = PLANET_TRADE_DIRECTION.get(ruling_planet, "BOTH")

    if buy_score >= 6.0 and (buy_score >= short_score or planet_pref == "BUY"):
        rec_direction = "BUY"
        rec_score     = buy_score
        rec_grade     = buy_cs["grade"]
        fire          = buy_cs["fire_trade"]
    elif short_score >= 6.0 and (short_score > buy_score or planet_pref == "SHORT"):
        rec_direction = "SHORT"
        rec_score     = short_score
        rec_grade     = short_cs["grade"]
        fire          = short_cs["fire_trade"]
    else:
        rec_direction = "WAIT"
        rec_score     = max(buy_score, short_score)
        rec_grade     = "WATCH" if rec_score >= 4 else "SKIP"
        fire          = False

    # ── Compute levels for recommended direction ─────────────────────────────
    levels = {}
    if rec_direction == "BUY" and fire:
        levels = compute_levels(
            inv_type="swing", risk_pref="balanced",
            price=current_price,
            all_sup=[{"price": nearest_sup}],
            all_res=[{"price": nearest_res}],
            atr14=atr14,
            ml_confidence=ml_confidence,
        )
        levels["trade_direction"] = "BUY"
    elif rec_direction == "SHORT" and fire:
        levels = compute_levels_short(
            price=current_price,
            risk_pref="balanced",
            all_sup=[{"price": nearest_sup}],
            all_res=[{"price": nearest_res}],
            atr14=atr14,
            ml_confidence=ml_confidence,
        )

    # ── 10yr quality flags ──────────────────────────────────────────────────
    from core.unified_logic import BAD_BUY_GOOD_SHORT, BEST_BUY_SYMBOLS
    _is_tier1_symbol = symbol in BEST_BUY_SYMBOLS
    _is_blacklisted  = symbol in BAD_BUY_GOOD_SHORT
    _vol_label = (
        "HIGH_VOL_CLIMAX ★" if vol_spike_ratio_val >= 1.8
        else "ELEVATED" if vol_spike_ratio_val >= 1.3
        else "NORMAL" if vol_spike_ratio_val >= 0.8
        else "LOW_CONVICTION"
    )

    return {
        "symbol":             symbol,
        "current_price":      current_price,
        "analysis_date":      today.isoformat(),
        "regime":             regime,
        "recommended":        rec_direction,
        "fire_trade":         fire,
        "conjunction_score":  rec_score,
        "grade":              rec_grade,
        "buy_score":          buy_score,
        "buy_grade":          buy_cs["grade"],
        "buy_signals_fired":  buy_cs["signals_fired"],
        "short_score":        short_score,
        "short_grade":        short_cs["grade"],
        "short_signals_fired":short_cs["signals_fired"],
        "signals_missed":     (buy_cs if rec_direction == "BUY" else short_cs)["signals_missed"],
        "ruling_planet":      ruling_planet,
        "planet_preference":  planet_pref,
        "sq9_near_support":   sq9_near_sup,
        "sq9_near_resistance":sq9_near_res,
        "sq9_support":        nearest_sup,
        "sq9_resistance":     nearest_res,
        "wyckoff_phase":      wyckoff_phase_str,
        "levels":             levels,
        "position_size_mult": (buy_cs if rec_direction in ("BUY","WAIT") else short_cs)["position_size_mult"],
        "size_label":         (buy_cs if rec_direction in ("BUY","WAIT") else short_cs)["size_label"],
        # ── 10yr quality metadata ──────────────────────────────────────────
        "is_tier1_symbol":    _is_tier1_symbol,   # True = MARUTI/ULTRACEMCO/INFY/etc.
        "is_blacklisted_buy": _is_blacklisted,    # True = RELIANCE/ITC/etc. (poor BUY WR)
        "vol_spike_ratio":    vol_spike_ratio_val,
        "vol_label":          _vol_label,         # HIGH_VOL_CLIMAX ★ = best bucket (49.4% WR)
        "ml_direction_raw":   ml_direction,       # raw model output
        "ml_direction_buy":   ml_for_buy,         # inverted for BUY (10yr finding)
        "breakeven_trail": {
            "trigger_pct":    1.0,
            "description":    "Move SL to entry when price reaches +1%. 10yr: 41.8% of losses were profitable before hitting flat SL.",
        },
    }