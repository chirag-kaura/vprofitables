"""
swing_classifier.py — GANN-ASTRO v4.0
=======================================
PURPOSE: Detect and classify every price swing as primary, secondary, or tertiary.
         This determines investment type automatically — the user picks risk
         preference (tight/balanced/wide), not the trade duration bucket.

SWING TYPES:
  Primary   — weeks to months, moves 15–60%+
              Maps to LONG investment type
              Requires: acc_score >= 3, Fourier dominant cycle >= 60 days

  Secondary — days to weeks, moves 6–20%
              Maps to SHORT investment type
              Requires: Fourier cycle 20–59 days, clear fractal structure

  Tertiary  — 1–7 days, moves 2–8%
              Maps to SWING investment type
              Requires: Sq9 proximity <= 1.5%, pattern confirmation

CLASSIFICATION ALGORITHM:
  1. Detect all swing highs/lows using a fractal window (5-bar default)
  2. Measure each swing's magnitude, duration, ATR multiple
  3. Classify using Fourier dominant cycle + ATR ratio + Wyckoff phase
  4. Score confidence using cycle alignment and signal count

OUTPUT: SwingClassification dataclass with all fields needed by unified_logic
        and reversal_map to set trade parameters.
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from datetime import date, timedelta


@dataclass
class SwingPoint:
    index:     int          # bar index in the series
    price:     float        # high or low price at the swing
    bar_date:  Optional[date] = None
    kind:      str  = ""    # "HIGH" or "LOW"
    magnitude: float = 0.0  # % move from the preceding opposite swing point


@dataclass
class SwingClassification:
    swing_type:      str    # "primary" / "secondary" / "tertiary"
    inv_type:        str    # "long" / "short" / "swing"  ← fed to unified_logic
    direction:       str    # "BUY" (at swing low) / "SELL" (at swing high)
    confidence:      float  # 0.0–1.0
    magnitude_pct:   float  # size of the detected swing in %
    atr_multiple:    float  # swing magnitude / ATR14
    fourier_period:  float  # dominant Fourier cycle that classifies this swing
    wyckoff_phase:   str    # from wyckoff_engine (ACCUMULATION / MARKUP / etc.)
    signals:         List[str] = field(default_factory=list)
    # Entry/SL hints (refined by compute_levels in unified_logic)
    swing_low:       float  = 0.0   # most recent swing low (structural SL anchor)
    swing_high:      float  = 0.0   # most recent swing high (structural target anchor)
    bars_in_swing:   int    = 0


def detect_swing_points(
    highs:  List[float],
    lows:   List[float],
    closes: List[float],
    window: int = 2,
) -> Tuple[List[SwingPoint], List[SwingPoint]]:
    """
    Detect fractal swing highs and lows using a symmetric window.

    A swing HIGH at bar i: highs[i] is the maximum within [i-window, i+window].
    A swing LOW  at bar i: lows[i]  is the minimum within [i-window, i+window].

    Args:
        window: bars on each side to check (default 2 = 5-bar fractal)

    Returns:
        (swing_highs, swing_lows) — lists of SwingPoint sorted oldest first.
    """
    n = len(closes)
    if n < window * 2 + 3:
        return [], []

    swing_highs: List[SwingPoint] = []
    swing_lows:  List[SwingPoint] = []

    for i in range(window, n - window):
        # Swing HIGH: local max of highs
        lo_i = i - window
        hi_i = i + window + 1
        local_highs = highs[lo_i:hi_i]
        local_lows  = lows[lo_i:hi_i]

        if highs[i] == max(local_highs):
            swing_highs.append(SwingPoint(index=i, price=highs[i], kind="HIGH"))

        if lows[i] == min(local_lows):
            swing_lows.append(SwingPoint(index=i, price=lows[i], kind="LOW"))

    # Annotate magnitude (% move from preceding opposite swing)
    all_swings = sorted(swing_highs + swing_lows, key=lambda s: s.index)
    for k in range(1, len(all_swings)):
        prev = all_swings[k - 1]
        curr = all_swings[k]
        if prev.price > 0:
            curr.magnitude = abs(curr.price - prev.price) / prev.price * 100

    return swing_highs, swing_lows


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


def classify_swing(
    closes:        List[float],
    highs:         List[float],
    lows:          List[float],
    volumes:       List[float],
    # Fourier data from quant_engine.fourier_cycle_analysis()
    fourier_dominant_period: float = 0.0,
    fourier_days_to_trough:  int   = 999,
    fourier_days_to_peak:    int   = 999,
    # Wyckoff phase from wyckoff_engine.wyckoff_phase()
    wyckoff_phase_str: str = "UNKNOWN",
    # Accumulation score from unified_logic.compute_acc_score()
    acc_score:     int   = 0,
    # 52-week range position (0 = at low, 1 = at high)
    price_52wk_pos: float = 0.5,
    # Gann cycle alignment (True if a cycle is due ±5 days)
    gann_cycle_due: bool = False,
    # Analysis date
    analysis_date: Optional[date] = None,
) -> SwingClassification:
    """
    Classify the current swing at the end of the price series.

    Returns SwingClassification with swing_type, inv_type, direction,
    and confidence. All fields needed by unified_logic.passes_gate() and
    reversal_map.build_zones().
    """
    today = analysis_date or date.today()
    price = closes[-1]
    signals: List[str] = []

    # ── Detect swing structure ────────────────────────────────────────────────
    swing_highs, swing_lows = detect_swing_points(highs, lows, closes, window=2)

    recent_low  = min(lows[-20:])  if len(lows)  >= 20 else min(lows)
    recent_high = max(highs[-20:]) if len(highs) >= 20 else max(highs)
    recent_range = recent_high - recent_low

    # Last confirmed swing low and high
    last_swing_low  = swing_lows[-1].price  if swing_lows  else recent_low
    last_swing_high = swing_highs[-1].price if swing_highs else recent_high

    # Current swing magnitude (distance from last swing extreme)
    if price < last_swing_high:
        # Declining — at or near a swing low
        current_magnitude = (last_swing_high - price) / max(last_swing_high, 0.01) * 100
        at_low = True
    else:
        # Rising — at or near a swing high
        current_magnitude = (price - last_swing_low) / max(last_swing_low, 0.01) * 100
        at_low = False

    direction = "BUY" if at_low else "SELL"

    # ATR ratio — how many ATRs did this swing cover?
    atr = _atr14(highs, lows, closes)
    atr_multiple = (recent_range / atr) if atr > 0 else 5.0

    # Bars since last opposite swing point
    bars_in_swing = 0
    if at_low and swing_highs:
        bars_in_swing = len(closes) - 1 - swing_highs[-1].index
    elif not at_low and swing_lows:
        bars_in_swing = len(closes) - 1 - swing_lows[-1].index

    # ── PRIMARY swing classification ──────────────────────────────────────────
    # Characteristics: large magnitude, long duration, acc_score >= 2,
    #                  Fourier period >= 60 days, at/near 52wk low
    primary_score = 0

    if fourier_dominant_period >= 60:
        primary_score += 2
        signals.append(f"Fourier dominant cycle {fourier_dominant_period:.0f}d >= 60d — primary cycle")

    if current_magnitude >= 15:
        primary_score += 2
        signals.append(f"Swing magnitude {current_magnitude:.1f}% >= 15% — primary scale")
    elif current_magnitude >= 8:
        primary_score += 1

    if acc_score >= 3:
        primary_score += 2
        signals.append(f"Accumulation score {acc_score}/5 — cycle bottom confirmed")
    elif acc_score >= 2:
        primary_score += 1

    if price_52wk_pos <= 0.20 and at_low:
        primary_score += 2
        signals.append(f"Price at {price_52wk_pos:.0%} of 52wk range — structural low")
    elif price_52wk_pos >= 0.80 and not at_low:
        primary_score += 1

    if atr_multiple >= 10:
        primary_score += 1
        signals.append(f"ATR multiple {atr_multiple:.1f}x — large structural swing")

    if wyckoff_phase_str in ("PHASE_C_SPRING", "LATE_ACCUMULATION", "PHASE_D_SOS"):
        primary_score += 2
        signals.append(f"Wyckoff: {wyckoff_phase_str} — primary entry zone")

    if fourier_days_to_trough <= 10 and at_low:
        primary_score += 1
        signals.append(f"Fourier trough due in {fourier_days_to_trough}d")

    # ── SECONDARY swing classification ────────────────────────────────────────
    secondary_score = 0

    if 20 <= fourier_dominant_period < 60:
        secondary_score += 2
        signals.append(f"Fourier dominant cycle {fourier_dominant_period:.0f}d — secondary cycle")

    if 6 <= current_magnitude < 15:
        secondary_score += 2
        signals.append(f"Swing magnitude {current_magnitude:.1f}% — secondary scale")

    if 5 <= atr_multiple < 10:
        secondary_score += 1

    if 10 <= bars_in_swing <= 45:
        secondary_score += 1
        signals.append(f"Swing duration {bars_in_swing} bars — secondary timeframe")

    if wyckoff_phase_str in ("MID_ACCUMULATION", "PHASE_B_LATE", "PRE_MARKUP"):
        secondary_score += 1

    if fourier_days_to_trough <= 15 and at_low:
        secondary_score += 1
    elif fourier_days_to_peak <= 15 and not at_low:
        secondary_score += 1

    # ── TERTIARY swing classification ─────────────────────────────────────────
    tertiary_score = 0

    if fourier_dominant_period < 20:
        tertiary_score += 2
    elif fourier_dominant_period > 0:
        tertiary_score += 1

    if current_magnitude < 8:
        tertiary_score += 2
        signals.append(f"Swing magnitude {current_magnitude:.1f}% — tertiary scale")

    if bars_in_swing <= 10:
        tertiary_score += 1

    if atr_multiple < 5:
        tertiary_score += 1

    if gann_cycle_due:
        tertiary_score += 1
        signals.append("Gann time cycle due ±5 days — short-cycle timing")

    # ── Assign type by highest score ──────────────────────────────────────────
    scores = {
        "primary":   primary_score,
        "secondary": secondary_score,
        "tertiary":  tertiary_score,
    }
    inv_map = {"primary": "long", "secondary": "short", "tertiary": "swing"}
    swing_type = max(scores, key=scores.get)
    inv_type   = inv_map[swing_type]

    # Confidence: ratio of winning score to max possible per type
    max_possible = {"primary": 12, "secondary": 8, "tertiary": 7}
    raw_conf = scores[swing_type] / max(max_possible[swing_type], 1)
    confidence = round(min(0.95, max(0.30, raw_conf)), 3)

    return SwingClassification(
        swing_type=swing_type,
        inv_type=inv_type,
        direction=direction,
        confidence=confidence,
        magnitude_pct=round(current_magnitude, 2),
        atr_multiple=round(atr_multiple, 2),
        fourier_period=fourier_dominant_period,
        wyckoff_phase=wyckoff_phase_str,
        signals=signals,
        swing_low=round(last_swing_low, 2),
        swing_high=round(last_swing_high, 2),
        bars_in_swing=bars_in_swing,
    )


def get_inv_type(classification: SwingClassification) -> str:
    """Convenience: return the investment type string for unified_logic."""
    return classification.inv_type


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Simulate a downtrend followed by a potential reversal (primary bottom)
    import random
    random.seed(99)

    n = 120
    closes = [1000.0]
    for i in range(n - 1):
        closes.append(round(closes[-1] * (1 + random.uniform(-0.012, 0.008)), 2))
    # Force a significant drop
    for i in range(40):
        closes.append(round(closes[-1] * 0.992, 2))

    highs  = [c * 1.005 for c in closes]
    lows   = [c * 0.995 for c in closes]
    vols   = [500_000 + random.randint(-50_000, 50_000) for _ in closes]

    sc = classify_swing(
        closes, highs, lows, vols,
        fourier_dominant_period=90.0,
        fourier_days_to_trough=8,
        wyckoff_phase_str="PHASE_C_SPRING",
        acc_score=3,
        price_52wk_pos=0.12,
    )
    print(f"Type       : {sc.swing_type} ({sc.inv_type})")
    print(f"Direction  : {sc.direction}")
    print(f"Confidence : {sc.confidence:.2f}")
    print(f"Magnitude  : {sc.magnitude_pct:.1f}%")
    print(f"Signals    : {sc.signals}")
    assert sc.swing_type == "primary", f"Expected primary, got {sc.swing_type}"
    assert sc.direction == "BUY"
    print("PASSED")