"""
wyckoff_engine.py — Wyckoff Market Cycle + Institutional Accumulation Detection
Place in: core/wyckoff_engine.py

Implements:
  1. Wyckoff Phase Detection (Accumulation → Markup transition)
  2. Accumulation Score (weighted composite)
  3. Breakout Probability Score
  4. Volatility Compression (Bollinger Band Width percentile)
  5. Institutional Volume Confirmation
  6. Market Regime Filter (avoids sideways/bear)
  7. MFE / MAE calculator for trade analysis

Hedge Fund mode:
  - Enter 1-2 days BEFORE institutions start markup
  - Signal: Volatility compression + liquidity absorption detected
  - Exit: Dynamic trailing from T1 toward T2
"""

import math
from typing import List, Tuple, Optional, Dict


# ─────────────────────────────────────────────────────────────────────────────
# v4.0: WYCKOFF PHASE ENUM CONSTANTS
# Use these in pattern_engine and swing_classifier instead of string parsing.
# wyckoff_phase() now always returns one of these in the 'phase_enum' key.
# ─────────────────────────────────────────────────────────────────────────────

class WyckoffPhase:
    ACCUMULATION       = "ACCUMULATION"         # Sq9 + vol dryup + higher lows
    LATE_ACCUMULATION  = "LATE_ACCUMULATION"     # markup imminent — enter now
    MARKUP             = "MARKUP"               # price trending up
    DISTRIBUTION       = "DISTRIBUTION"         # smart money selling
    MARKDOWN           = "MARKDOWN"             # price trending down
    SPRING             = "SPRING"               # shakeout below support — BUY
    UTAD               = "UTAD"                 # push above resistance — SELL
    PHASE_A            = "PHASE_A"              # selling climax — too early
    PHASE_B_EARLY      = "PHASE_B_EARLY"        # cause building
    PHASE_B_LATE       = "PHASE_B_LATE"         # late cause, watch
    PHASE_C_SPRING     = "PHASE_C_SPRING"       # spring shakeout — HEDGE FUND ENTRY
    PHASE_D_SOS        = "PHASE_D_SOS"          # sign of strength — confirmed entry
    PHASE_E_MARKUP     = "PHASE_E_MARKUP"       # markup in progress
    UNKNOWN            = "UNKNOWN"


def phase_to_inv_type(phase: str) -> str:
    """Map Wyckoff phase to investment type for swing_classifier."""
    buy_phases  = {WyckoffPhase.SPRING, WyckoffPhase.PHASE_C_SPRING,
                   WyckoffPhase.LATE_ACCUMULATION, WyckoffPhase.ACCUMULATION,
                   WyckoffPhase.PHASE_D_SOS, WyckoffPhase.PHASE_B_LATE}
    sell_phases = {WyckoffPhase.UTAD, WyckoffPhase.DISTRIBUTION}
    if phase in buy_phases:  return "long"
    if phase in sell_phases: return "swing"
    return "short"



# ─────────────────────────────────────────────────────────────────────────────
# 1. CORE INDICATOR HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _sma(series: List[float], n: int) -> Optional[float]:
    if len(series) < n: return None
    return sum(series[-n:]) / n

def _atr(highs: List[float], lows: List[float], closes: List[float],
         n: int = 14) -> float:
    """Average True Range."""
    if len(closes) < 2: return (highs[-1] - lows[-1]) if highs else 0.0
    trs = []
    for i in range(max(1, len(closes)-n), len(closes)):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i-1]),
                 abs(lows[i]  - closes[i-1]))
        trs.append(tr)
    return sum(trs) / len(trs) if trs else 0.0

def _bollinger(closes: List[float], n: int = 20, k: float = 2.0) -> Dict:
    """Bollinger Bands + BB Width."""
    if len(closes) < n:
        return {"upper": closes[-1], "lower": closes[-1], "mid": closes[-1],
                "width": 0.0, "pct_b": 0.5}
    tail  = closes[-n:]
    mid   = sum(tail) / n
    var   = sum((x - mid)**2 for x in tail) / n
    std   = math.sqrt(var)
    upper = mid + k * std
    lower = mid - k * std
    width = (upper - lower) / mid if mid > 0 else 0.0
    pct_b = (closes[-1] - lower) / (upper - lower) if (upper - lower) > 0 else 0.5
    return {"upper": round(upper, 2), "lower": round(lower, 2),
            "mid": round(mid, 2), "width": round(width, 4),
            "pct_b": round(pct_b, 3)}

def _bb_width_percentile(closes: List[float], lookback: int = 120,
                          bb_period: int = 20) -> float:
    """
    BB Width percentile over last `lookback` bars.
    Low percentile = compression = potential breakout.
    """
    if len(closes) < lookback + bb_period:
        return 50.0
    widths = []
    for i in range(lookback):
        idx = len(closes) - lookback + i
        if idx < bb_period: continue
        bb = _bollinger(closes[:idx], bb_period)
        widths.append(bb["width"])
    if not widths: return 50.0
    cur_width = _bollinger(closes, bb_period)["width"]
    below = sum(1 for w in widths if w > cur_width)
    return round(below / len(widths) * 100, 1)  # low = compressed


# ─────────────────────────────────────────────────────────────────────────────
# 2. ACCUMULATION SCORE
# Wyckoff: true accumulation = vol dry-up + range compression + higher lows + delivery
# Score = 0.30×VolDryUp + 0.25×RangeCompression + 0.25×HigherLows + 0.20×DeliveryProxy
# ─────────────────────────────────────────────────────────────────────────────

def accumulation_score(closes: List[float], highs: List[float],
                       lows: List[float], volumes: List[float],
                       lookback: int = 15) -> Dict:
    """
    Compute Wyckoff accumulation score 0–100.
    Returns score + component breakdown + detected signals.
    """
    n = len(closes)
    if n < lookback + 2:
        return {"score": 0, "components": {}, "signals": [], "phase": "INSUFFICIENT_DATA"}

    c  = closes[-lookback:]
    h  = highs[-lookback:]
    lo = lows[-lookback:]
    v  = volumes[-lookback:]

    signals = []
    comp = {}

    # ── Component 1: Volume Dry-Up (weight 0.30) ─────────────────────────────
    # True accumulation: volume falls while price holds → absorption
    half = max(1, len(v) // 2)
    v_early = sum(v[:half]) / half
    v_late  = sum(v[half:]) / max(len(v) - half, 1)
    price_range_pct = (max(c) - min(c)) / max(c) * 100 if c else 100

    if v_late < v_early * 0.60 and price_range_pct < 5:
        vdu = 100; signals.append(f"Strong vol dry-up: {v_late/v_early*100:.0f}% of prior vol with price held in {price_range_pct:.1f}% range")
    elif v_late < v_early * 0.75 and price_range_pct < 7:
        vdu = 70;  signals.append(f"Vol dry-up: {v_late/v_early*100:.0f}% of prior vol (absorption forming)")
    elif v_late < v_early * 0.85:
        vdu = 40;  signals.append(f"Mild vol decline: {v_late/v_early*100:.0f}% of prior (watch for compression)")
    else:
        vdu = 0
    comp["vol_dry_up"] = round(vdu, 1)

    # ── Component 2: Range Compression (weight 0.25) ─────────────────────────
    # Bollinger Band Width below 20th percentile of last 120 bars
    bb_pct = _bb_width_percentile(closes, lookback=min(120, n-5))
    cur_bb  = _bollinger(closes, 20)

    # Also check narrowing of recent bars vs earlier bars
    early_ranges = [h[k]-lo[k] for k in range(half)]
    late_ranges  = [h[k]-lo[k] for k in range(half, len(h))]
    avg_er = sum(early_ranges)/len(early_ranges) if early_ranges else 1
    avg_lr = sum(late_ranges)/len(late_ranges) if late_ranges else avg_er
    range_ratio = avg_lr / max(avg_er, 0.001)

    if bb_pct <= 20 and range_ratio < 0.70:
        rc = 100; signals.append(f"BB Width at {bb_pct:.0f}th percentile + range {range_ratio*100:.0f}% of prior (tight coil)")
    elif bb_pct <= 30 or range_ratio < 0.75:
        rc = 70;  signals.append(f"Volatility compression: BB pct {bb_pct:.0f}, range ratio {range_ratio:.2f}")
    elif bb_pct <= 40:
        rc = 40;  signals.append(f"Mild compression: BB pct {bb_pct:.0f}")
    else:
        rc = 0
    comp["range_compression"] = round(rc, 1)
    comp["bb_width_percentile"] = bb_pct
    comp["bb_width"] = cur_bb["width"]

    # ── Component 3: Higher Lows (weight 0.25) ───────────────────────────────
    # Institutions protect their positions → lows keep rising
    lo_list = list(lo)
    hl_count = sum(1 for k in range(1, len(lo_list)) if lo_list[k] > lo_list[k-1])
    hl_ratio = hl_count / max(len(lo_list) - 1, 1)

    if hl_ratio >= 0.70:
        hl = 100; signals.append(f"Strong higher lows: {hl_count}/{len(lo_list)-1} sessions (institutional support)")
    elif hl_ratio >= 0.55:
        hl = 65;  signals.append(f"Higher lows pattern: {hl_count}/{len(lo_list)-1} sessions")
    elif hl_ratio >= 0.45:
        hl = 35;  signals.append(f"Partial higher lows: {hl_count}/{len(lo_list)-1}")
    else:
        hl = 0
    comp["higher_lows"] = round(hl, 1)
    comp["hl_ratio"] = round(hl_ratio, 2)

    # ── Component 4: Delivery % Proxy (weight 0.20) ──────────────────────────
    # Up-sessions avg volume vs down-sessions avg volume (delivery rising = institutions)
    c_list = list(c); v_list = list(v)
    up_vols = [v_list[k] for k in range(1, len(c_list)) if c_list[k] > c_list[k-1]]
    dn_vols = [v_list[k] for k in range(1, len(c_list)) if c_list[k] < c_list[k-1]]
    avg_up  = sum(up_vols)/len(up_vols) if up_vols else 0
    avg_dn  = sum(dn_vols)/len(dn_vols) if dn_vols else max(avg_up * 0.5, 1)
    del_ratio = avg_up / max(avg_dn, 1)

    # Also check if recent up-vol is trending higher
    if len(up_vols) >= 3:
        up_trend = sum(1 for k in range(1, len(up_vols)) if up_vols[k] > up_vols[k-1])
        del_rising = up_trend / (len(up_vols) - 1) >= 0.5
    else:
        del_rising = False

    if del_ratio >= 1.8 and del_rising:
        dp = 100; signals.append(f"Rising delivery: up-vol/dn-vol {del_ratio:.2f}x with uptrend in delivery (institutions accumulating)")
    elif del_ratio >= 1.4:
        dp = 65;  signals.append(f"Delivery improvement: ratio {del_ratio:.2f}x")
    elif del_ratio >= 1.1:
        dp = 35;  signals.append(f"Mild delivery uptick: ratio {del_ratio:.2f}x")
    else:
        dp = 0
    comp["delivery_proxy"] = round(dp, 1)
    comp["delivery_ratio"] = round(del_ratio, 2)

    # ── Composite Score ──────────────────────────────────────────────────────
    score = round(0.30*vdu + 0.25*rc + 0.25*hl + 0.20*dp, 1)
    score = min(score, 100)

    # Phase classification
    if score >= 75:
        phase = "LATE_ACCUMULATION"  # enter now — markup imminent
        phase_label = "Late Accumulation → Markup imminent (enter now)"
    elif score >= 50:
        phase = "MID_ACCUMULATION"
        phase_label = "Mid Accumulation → Wait for breakout confirmation"
    elif score >= 30:
        phase = "EARLY_ACCUMULATION"
        phase_label = "Early Accumulation / Distribution — too early"
    else:
        phase = "NO_ACCUMULATION"
        phase_label = "No accumulation pattern detected"

    return {
        "score":       score,
        "phase":       phase,
        "phase_label": phase_label,
        "components":  comp,
        "signals":     signals,
        "bb_width":    cur_bb["width"],
        "bb_pct_b":    cur_bb["pct_b"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. BREAKOUT SCORE
# Breakout = Accumulation → Markup transition
# Score = 0.4×VolSpike + 0.3×RangeExpansion + 0.3×CloseStrength
# ─────────────────────────────────────────────────────────────────────────────

def breakout_score(closes: List[float], highs: List[float],
                   lows: List[float], volumes: List[float]) -> Dict:
    """
    Detect imminent or occurring breakout from accumulation.
    Uses last bar vs 20-day averages.
    """
    if len(closes) < 22:
        return {"score": 0, "signals": [], "vol_spike": 0,
                "range_expansion": 0, "close_strength": 0}

    # ── Volume Spike = Volume / AvgVolume20 ──────────────────────────────────
    avg_vol20 = sum(volumes[-21:-1]) / 20
    last_vol  = volumes[-1]
    vol_spike = round(last_vol / max(avg_vol20, 1), 2)

    # ── Range Expansion = TrueRange / ATR14 ─────────────────────────────────
    atr14 = _atr(highs, lows, closes, 14)
    last_tr = max(highs[-1] - lows[-1],
                  abs(highs[-1] - closes[-2]),
                  abs(lows[-1]  - closes[-2]))
    range_expansion = round(last_tr / max(atr14, 0.001), 2)

    # ── Close Strength = (Close - Low) / (High - Low) ───────────────────────
    bar_range = highs[-1] - lows[-1]
    close_strength = round((closes[-1] - lows[-1]) / max(bar_range, 0.001), 3)

    # ── Composite Score ──────────────────────────────────────────────────────
    # Normalise vol_spike to 0-100 (1.8× = threshold, 3× = max)
    vs_norm  = min(100, max(0, (vol_spike - 1.0) / 2.0 * 100))
    # Normalise range expansion (1.0 = normal, 2.0 = expansion)
    re_norm  = min(100, max(0, (range_expansion - 0.8) / 1.2 * 100))
    # Close strength already 0-1
    cs_norm  = close_strength * 100

    score = round(0.4*vs_norm + 0.3*re_norm + 0.3*cs_norm, 1)

    signals = []
    if vol_spike >= 1.8:
        signals.append(f"Institutional volume: {vol_spike:.2f}× avg (markup confirmation)")
    elif vol_spike >= 1.3:
        signals.append(f"Above-avg volume: {vol_spike:.2f}× (increasing interest)")

    if range_expansion >= 1.5:
        signals.append(f"Range expansion: {range_expansion:.2f}× ATR (breakout bar)")
    if close_strength >= 0.70:
        signals.append(f"Close strength {close_strength:.2f} (closed near high — buyers in control)")
    elif close_strength <= 0.30:
        signals.append(f"Weak close {close_strength:.2f} (closed near low — bearish)")

    return {
        "score":           round(score, 1),
        "vol_spike":       vol_spike,
        "range_expansion": range_expansion,
        "close_strength":  close_strength,
        "signals":         signals,
        "is_breakout":     score >= 60 and vol_spike >= 1.8,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. VOLATILITY COMPRESSION TRIGGER
# BB Width < 20th percentile of last 120 days = compression
# ─────────────────────────────────────────────────────────────────────────────

def volatility_compression(closes: List[float], lookback: int = 120) -> Dict:
    """
    Measure volatility compression using Bollinger Band Width.
    Returns percentile rank, current width, and trigger signal.
    """
    bb     = _bollinger(closes, 20)
    bb_pct = _bb_width_percentile(closes, lookback)

    if bb_pct <= 10:
        signal  = "EXTREME_COMPRESSION"
        label   = "Extreme squeeze — breakout highly imminent"
        trigger = True
    elif bb_pct <= 20:
        signal  = "COMPRESSED"
        label   = "Volatility compressed — watch for breakout"
        trigger = True
    elif bb_pct <= 35:
        signal  = "MILD_COMPRESSION"
        label   = "Mild compression — accumulation possible"
        trigger = False
    else:
        signal  = "NORMAL"
        label   = "Normal volatility — no compression"
        trigger = False

    return {
        "bb_width":       bb["width"],
        "bb_upper":       bb["upper"],
        "bb_lower":       bb["lower"],
        "bb_mid":         bb["mid"],
        "pct_b":          bb["pct_b"],
        "percentile":     bb_pct,
        "signal":         signal,
        "label":          label,
        "trigger":        trigger,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. INSTITUTIONAL VOLUME CONFIRMATION
# Institutions enter markup with Volume >= 1.8× AvgVolume20
# But only AFTER accumulation phase (acc_score >= 50)
# ─────────────────────────────────────────────────────────────────────────────

def institutional_volume_confirm(volumes: List[float],
                                  acc_score: float) -> Dict:
    """
    Confirm institutional entry in markup phase.
    Returns True only if BOTH conditions are met:
      - Volume >= 1.8× AvgVol20
      - Accumulation score >= 50 (they were accumulating before)
    """
    if len(volumes) < 22:
        return {"confirmed": False, "vol_ratio": 0, "reason": "Insufficient data"}

    avg20     = sum(volumes[-21:-1]) / 20
    last_vol  = volumes[-1]
    vol_ratio = round(last_vol / max(avg20, 1), 2)

    if vol_ratio >= 1.8 and acc_score >= 50:
        confirmed = True
        reason = f"Institutional markup confirmed: {vol_ratio:.2f}× vol after accumulation (score {acc_score})"
    elif vol_ratio >= 1.8 and acc_score < 50:
        confirmed = False
        reason = f"Volume spike {vol_ratio:.2f}× BUT no prior accumulation (score {acc_score}) — likely distribution"
    elif vol_ratio >= 1.3:
        confirmed = False
        reason = f"Above-avg vol {vol_ratio:.2f}× — not yet institutional threshold (need 1.8×)"
    else:
        confirmed = False
        reason = f"Normal volume {vol_ratio:.2f}× — no institutional activity"

    return {
        "confirmed": confirmed,
        "vol_ratio": vol_ratio,
        "avg_vol20": round(avg20, 0),
        "reason":    reason,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. MARKET REGIME FILTER
# Hedge Fund mode avoids: sideways, bear, high-vol markets
# Only enters: trending up with moderate-low volatility
# ─────────────────────────────────────────────────────────────────────────────

def market_regime_filter(closes: List[float], highs: List[float],
                          lows: List[float]) -> Dict:
    """
    Determine if market is in a tradeable regime for Hedge Fund mode.
    Sideways = skip. Bear = skip. Bull or Late-Accumulation-before-bull = trade.
    """
    if len(closes) < 50:
        return {"tradeable": False, "regime": "INSUFFICIENT_DATA", "reason": "Need 50+ bars"}

    sma20  = sum(closes[-20:]) / 20
    sma50  = sum(closes[-50:]) / 50
    sma200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else sma50
    cur    = closes[-1]

    # Returns
    ret20 = (cur - closes[-21]) / closes[-21] * 100 if len(closes) >= 21 else 0
    ret60 = (cur - closes[-61]) / closes[-61] * 100 if len(closes) >= 61 else ret20

    # ATR-based volatility
    atr14 = _atr(highs, lows, closes, 14)
    atr_pct = atr14 / cur * 100

    # Trend consistency (ADX proxy)
    slopes = [closes[i] - closes[i-1] for i in range(len(closes)-20, len(closes))]
    up_days = sum(1 for s in slopes if s > 0)
    trend_strength = abs(up_days - 10) / 10 * 100  # 0 = choppy, 100 = strong trend

    # Regime decision
    if atr_pct > 4.5:
        regime = "HIGH_VOLATILITY"; tradeable = False
        reason = f"ATR {atr_pct:.1f}% — too volatile for precise entry"
    elif cur < sma200 and ret60 < -10:
        regime = "STRONG_BEAR"; tradeable = False
        reason = f"Price below SMA200, ret60d={ret60:.1f}% — avoid longs"
    elif cur < sma50 and ret20 < -5:
        regime = "WEAK_BEAR"; tradeable = False
        reason = f"Price below SMA50, short-term downtrend"
    elif cur < sma20 and cur < sma50:
        regime = "SIDEWAYS_BEAR"; tradeable = False
        reason = "Choppy/sideways with downward bias — wait"
    elif trend_strength < 20 and abs(ret20) < 2:
        regime = "SIDEWAYS"; tradeable = False
        reason = f"Trend strength {trend_strength:.0f}% — true sideways market, skip"
    elif cur > sma20 and cur > sma50 and ret20 > 0:
        if ret20 > 5 and trend_strength > 60:
            regime = "STRONG_BULL"; tradeable = True
            reason = f"Strong trend: ret20d={ret20:.1f}%, consistency={trend_strength:.0f}%"
        else:
            regime = "WEAK_BULL"; tradeable = True
            reason = f"Uptrend: above SMA20/50, ret20d={ret20:.1f}%"
    elif cur > sma50:
        # Late accumulation before trend — Hedge Fund entry zone
        regime = "PRE_MARKUP"; tradeable = True
        reason = f"Pre-markup: above SMA50, tight range (ATR {atr_pct:.1f}%)"
    else:
        regime = "TRANSITION"; tradeable = False
        reason = "Transitional — wait for direction clarity"

    return {
        "regime":         regime,
        "tradeable":      tradeable,
        "reason":         reason,
        "sma20":          round(sma20, 2),
        "sma50":          round(sma50, 2),
        "sma200":         round(sma200, 2),
        "atr_pct":        round(atr_pct, 2),
        "ret20d":         round(ret20, 2),
        "ret60d":         round(ret60, 2),
        "trend_strength": round(trend_strength, 1),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7. WYCKOFF PHASE DETECTOR
# Combines accumulation + breakout + volatility + regime into a single signal
# ─────────────────────────────────────────────────────────────────────────────

def wyckoff_phase(closes: List[float], highs: List[float],
                   lows: List[float], volumes: List[float]) -> Dict:
    """
    Full Wyckoff phase detection.
    Returns the dominant phase + composite signal + entry recommendation.
    
    Phases:
      PHASE_A: Selling climax (end of downtrend) — too early
      PHASE_B: Building cause (accumulation range) — watch
      PHASE_C: Spring (last shakeout) — entry on spring reversal  ← HEDGE FUND ENTRY
      PHASE_D: SOS (sign of strength) — entry confirmed
      PHASE_E: Markup (trending up) — momentum entry (late)
    """
    if len(closes) < 30:
        # Return full structure with safe defaults so callers can always access sub-keys
        _empty_acc = {"score":0,"phase":"INSUFFICIENT_DATA","phase_label":"","components":{},"signals":[],
                      "bb_width":0,"bb_pct_b":0.5}
        _empty_brk = {"score":0,"vol_spike":0,"range_expansion":0,"close_strength":0,
                      "signals":[],"is_breakout":False}
        _empty_vc  = {"bb_width":0,"bb_upper":0,"bb_lower":0,"bb_mid":0,"pct_b":0.5,
                      "percentile":50,"signal":"NORMAL","label":"Insufficient data","trigger":False}
        _empty_reg = {"regime":"INSUFFICIENT_DATA","tradeable":False,
                      "reason":"Need 30+ bars","sma20":0,"sma50":0,"sma200":0,
                      "atr_pct":0,"ret20d":0,"ret60d":0,"trend_strength":0}
        _empty_inst= {"confirmed":False,"vol_ratio":0,"avg_vol20":0,"reason":"Insufficient data"}
        return {"phase":"UNKNOWN","entry_signal":False,"confidence":0,"score":0,
                "reason":"Insufficient price data (need 30+ bars)",
                "accumulation":_empty_acc,"breakout":_empty_brk,"volatility":_empty_vc,
                "regime":_empty_reg,"inst_confirm":_empty_inst}

    acc  = accumulation_score(closes, highs, lows, volumes, lookback=15)
    brkout = breakout_score(closes, highs, lows, volumes)
    vc   = volatility_compression(closes)
    reg  = market_regime_filter(closes, highs, lows)
    inst = institutional_volume_confirm(volumes, acc["score"])

    # ── Phase mapping ────────────────────────────────────────────────────────
    # Score matrix: accumulation high + breakout low = Phase C (spring)
    #               accumulation high + breakout rising = Phase D (SOS)
    #               breakout high + inst confirmed = Phase E (markup)

    if not reg["tradeable"]:
        phase = "UNFAVORABLE_REGIME"
        entry = False
        confidence = 0
        reason = reg["reason"]
    elif brkout["is_breakout"] and inst["confirmed"]:
        phase = "PHASE_D_SOS"
        entry = True
        confidence = round(0.4*acc["score"] + 0.4*brkout["score"] + 0.2*50, 1)
        reason = "Sign of Strength: volume breakout confirmed by institutional activity"
    elif acc["score"] >= 65 and vc["trigger"] and not brkout["is_breakout"]:
        phase = "PHASE_C_SPRING"
        entry = True
        confidence = round(0.5*acc["score"] + 0.3*(100-vc["percentile"]) + 0.2*brkout["score"], 1)
        reason = "Phase C — Accumulation complete, volatility compressed: enter 1-2 days before markup"
    elif acc["score"] >= 40 and vc["trigger"]:
        phase = "PHASE_B_LATE"
        entry = False
        confidence = round(acc["score"] * 0.6, 1)
        reason = "Late Phase B — Accumulation building, wait for spring or SOS"
    elif acc["score"] >= 25:
        phase = "PHASE_B_EARLY"
        entry = False
        confidence = round(acc["score"] * 0.4, 1)
        reason = "Early Phase B — Accumulation starting, not yet tradeable"
    else:
        phase = "PHASE_A_OR_MARKUP"
        entry = False
        confidence = 0
        reason = "No accumulation pattern — either Phase A (too early) or extended markup (too late)"

    # v4.0: Map internal phase string to WyckoffPhase enum constant
    _phase_enum_map = {
        "PHASE_D_SOS":        WyckoffPhase.PHASE_D_SOS,
        "PHASE_C_SPRING":     WyckoffPhase.PHASE_C_SPRING,
        "PHASE_B_LATE":       WyckoffPhase.PHASE_B_LATE,
        "PHASE_B_EARLY":      WyckoffPhase.PHASE_B_EARLY,
        "PHASE_A_OR_MARKUP":  WyckoffPhase.PHASE_A,
        "UNFAVORABLE_REGIME": WyckoffPhase.UNKNOWN,
    }
    phase_enum = _phase_enum_map.get(phase, WyckoffPhase.UNKNOWN)

    return {
        "phase":            phase,
        "phase_enum":       phase_enum,      # v4.0: clean enum for swing_classifier + pattern_engine
        "entry_signal":     entry,
        "confidence":       min(confidence, 100),
        "reason":           reason,
        "accumulation":     acc,
        "breakout":         brkout,
        "volatility":       vc,
        "regime":           reg,
        "inst_confirm":     inst,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8. HEDGE FUND ENTRY OPTIMIZER
# Entry: 1-2 bars before markup, using last Sq9 support inside accumulation range
# SL: below the spring low (NOT a percentage — Wyckoff spring defines the risk)
# T1: top of accumulation range (last resistance)
# T2: ATR-based projection from T1
# ─────────────────────────────────────────────────────────────────────────────

def hedge_fund_levels(closes: List[float], highs: List[float],
                      lows: List[float], volumes: List[float],
                      current_price: float) -> Dict:
    """
    Compute precise entry / SL / T1 / T2 for Hedge Fund mode.
    
    Entry: highest accumulation low (HHL) — last higher low
    SL:    below the spring low (lowest point in accumulation range)
    T1:    top of accumulation range (highest high of last 20 bars)
    T2:    T1 + (T1 - SL) × 1.5 (projected markup target)
    """
    lb = min(20, len(closes)-1)
    recent_closes = closes[-lb:]
    recent_highs  = highs[-lb:]
    recent_lows   = lows[-lb:]

    # Spring low = lowest point in accumulation range
    spring_low = min(recent_lows)
    # Accumulation high = highest high in range (T1)
    range_high = max(recent_highs)
    # Range size
    range_size = range_high - spring_low

    # Entry: last higher low in the series
    entry = current_price
    for k in range(len(recent_lows)-2, 0, -1):
        if recent_lows[k] > recent_lows[k-1]:
            entry = round(recent_closes[k] * 1.001, 2)  # just above the higher low close
            break

    # Clamp entry to reasonable range
    entry = round(max(current_price * 0.990, min(current_price * 1.005, entry)), 2)

    # SL: 0.5% below spring low (gives slight buffer below the shakeout)
    sl = round(spring_low * 0.995, 2)

    # T1: top of accumulation range
    t1 = round(range_high, 2)
    if t1 <= entry:
        t1 = round(entry * 1.04, 2)  # at least 4% if range is unclear

    # T2: projected markup = T1 + (range_size × 1.0) Wyckoff measured move
    wyckoff_target = round(t1 + range_size * 1.0, 2)
    t2 = wyckoff_target

    # ATR-based T2 alternative
    atr = _atr(highs, lows, closes, 14)
    atr_t2 = round(t1 + atr * 3, 2)

    # Use the more conservative
    t2 = round(min(wyckoff_target, atr_t2) if wyckoff_target > t1 else atr_t2, 2)
    if t2 <= t1: t2 = round(t1 * 1.06, 2)

    risk    = round(entry - sl, 2)
    reward1 = round(t1 - entry, 2)
    reward2 = round(t2 - entry, 2)
    rr1     = round(reward1 / max(risk, 0.01), 2)
    rr2     = round(reward2 / max(risk, 0.01), 2)

    return {
        "entry":       entry,
        "entry_src":   "Wyckoff higher low (accumulation support)",
        "sl":          sl,
        "sl_src":      f"Below spring low ₹{spring_low:.2f} (Wyckoff stop)",
        "t1":          t1,
        "t1_src":      f"Accumulation range high ₹{range_high:.2f}",
        "t2":          t2,
        "t2_src":      f"Wyckoff measured move ₹{t2:.2f}",
        "spring_low":  round(spring_low, 2),
        "range_high":  round(range_high, 2),
        "range_size":  round(range_size, 2),
        "risk":        risk,
        "reward1":     reward1,
        "reward2":     reward2,
        "rr1":         rr1,
        "rr2":         rr2,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 9. MFE / MAE CALCULATOR
# MFE = Maximum Favorable Excursion (best the trade could have been)
# MAE = Maximum Adverse Excursion (worst drawdown before exit)
# ─────────────────────────────────────────────────────────────────────────────

def mfe_mae(entry_price: float, exit_price: float,
            highs_in_trade: List[float], lows_in_trade: List[float],
            direction: str = "LONG") -> Dict:
    """
    Calculate MFE and MAE for a completed trade.
    Essential for assessing stop placement quality and target realism.
    """
    if not highs_in_trade or not lows_in_trade:
        pnl = exit_price - entry_price
        return {"mfe_pct": 0, "mae_pct": 0, "mfe_abs": 0, "mae_abs": 0,
                "captured_pct": 100 if pnl >= 0 else 0}

    if direction == "LONG":
        best_price  = max(highs_in_trade)
        worst_price = min(lows_in_trade)
        mfe_abs = round(best_price  - entry_price, 2)
        mae_abs = round(entry_price - worst_price, 2)
    else:
        best_price  = min(lows_in_trade)
        worst_price = max(highs_in_trade)
        mfe_abs = round(entry_price - best_price,  2)
        mae_abs = round(worst_price - entry_price, 2)

    mfe_pct = round(mfe_abs / entry_price * 100, 2)
    mae_pct = round(mae_abs / entry_price * 100, 2)

    # Captured efficiency: how much of MFE did we actually capture?
    actual_pnl  = abs(exit_price - entry_price)
    captured_pct = round(actual_pnl / max(mfe_abs, 0.001) * 100, 1) if mfe_abs > 0 else 0

    # SL quality: if MAE > planned risk it means SL was too tight
    return {
        "mfe_abs":       mfe_abs,
        "mfe_pct":       mfe_pct,
        "mae_abs":       mae_abs,
        "mae_pct":       mae_pct,
        "best_price":    round(best_price, 2),
        "worst_price":   round(worst_price, 2),
        "captured_pct":  captured_pct,
    }