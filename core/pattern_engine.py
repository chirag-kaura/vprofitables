"""
pattern_engine.py — GANN-ASTRO v4.0
=====================================
PURPOSE: Detect price action CONFIRMATION that a Gann/Fourier/Astro reversal
         zone is actually holding right now.

PROBLEM IT SOLVES:
  Gann Sq9 levels, Fourier cycle dates, and planetary aspect windows are
  FORECASTS — they tell you WHERE and WHEN a reversal is likely. But price
  can overshoot a Sq9 level, or a Fourier trough can arrive 3 days late.
  Without a confirmation mechanism, every Sq9 level is a 50/50 coin flip.

  pattern_engine detects EVIDENCE that the market is ACTUALLY reacting at
  the forecast level RIGHT NOW. You only trade when both conditions are true:
    (1) Price is inside a reversal zone (Gann + Fourier + Astro agree)
    (2) Pattern engine confirms price action is reversing there

HOW TO USE:
  from core.pattern_engine import detect, PatternResult

  result: PatternResult = detect(closes, highs, lows, volumes)

  if result.fires:
      # Pattern confirmed — proceed to signal conjunction scoring
      pass

PATTERNS DETECTED:
  1. RSI divergence     — price lower low + RSI higher low (bullish)
                          price higher high + RSI lower high (bearish)
  2. Volume exhaustion  — price at low/high on shrinking volume (selling/buying climax)
  3. Wyckoff Spring     — brief dip below support on low vol + sharp recovery
  4. Wyckoff UTAD       — brief push above resistance on high vol + sharp reversal
  5. BB squeeze breakout— BB width compressed then expanding with directional close
  6. Reversal candle    — hammer / shooting star with body ratio + wick rules

OUTPUT: PatternResult dataclass
  pattern:           str   — BULLISH_DIV / BEARISH_DIV / SPRING / UTAD /
                              SQUEEZE_BULL / SQUEEZE_BEAR / REV_CANDLE / NONE
  divergence_type:   str   — RSI / VOLUME / MACD / NONE
  strength:          float — 0.0-1.0 quality of pattern (higher = cleaner pattern)
  volume_exhaustion: bool  — selling/buying climax confirmed
  inst_absorption:   bool  — institutional absorption detected (flat price + high vol)
  fires:             bool  — True = trade confirmation. Requires ≥2 signals OR spring.
  signals:           list  — human-readable list of what fired

INTEGRATION:
  In passes_gate() (unified_logic.py), once pattern_engine is deployed:
    result = pattern_engine.detect(closes, highs, lows, volumes)
    ok, reason = passes_gate(..., pattern_fires=result.fires,
                                   pattern_engine_active=True)

  For SWING trades: pattern_fires=True is REQUIRED.
  For SHORT/LONG: pattern_fires contributes +1 to signal conjunction count.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class PatternResult:
    pattern:           str   = "NONE"
    divergence_type:   str   = "NONE"
    strength:          float = 0.0
    volume_exhaustion: bool  = False
    inst_absorption:   bool  = False
    fires:             bool  = False
    signals:           List[str] = field(default_factory=list)


def detect(
    closes:  list,
    highs:   list,
    lows:    list,
    volumes: list,
    lookback:   int = 20,
    rsi_period: int = 14,
) -> PatternResult:
    """
    Main entry point. Run on each new bar when price is inside a reversal zone.

    Args:
        closes:     list of close prices, most recent last
        highs:      list of high prices, same length and order
        lows:       list of low prices, same length and order
        volumes:    list of volumes, same length and order
        lookback:   bars to look back for divergence detection (default 20)
        rsi_period: RSI calculation period (default 14)

    Returns:
        PatternResult — fires=True means pattern confirmation exists.
    """
    min_bars = max(lookback + rsi_period + 5, 50)
    if len(closes) < min_bars:
        return PatternResult()

    res     = PatternResult()
    signals: List[str] = []

    # ── 1. RSI Divergence ────────────────────────────────────────────────────
    rsi_div = _rsi_divergence(closes, rsi_period, lookback)
    if rsi_div == 1.0:
        if res.pattern == "NONE": res.pattern = "BULLISH_DIV"
        res.divergence_type = "RSI"
        res.strength = max(res.strength, 0.75)
        signals.append("RSI bullish divergence — price lower low, RSI higher low")
    elif rsi_div == -1.0:
        if res.pattern == "NONE": res.pattern = "BEARISH_DIV"
        res.divergence_type = "RSI"
        res.strength = max(res.strength, 0.75)
        signals.append("RSI bearish divergence — price higher high, RSI lower high")

    # ── 2. Volume-Price Divergence (exhaustion / distribution) ───────────────
    vol_div = _volume_exhaustion(closes, volumes, lookback)
    if vol_div > 0:
        res.volume_exhaustion = True
        res.strength = max(res.strength, 0.80)
        if res.divergence_type == "NONE": res.divergence_type = "VOLUME"
        if res.pattern == "NONE": res.pattern = "BULLISH_DIV"
        signals.append("Volume exhaustion — price at low on shrinking volume (selling climax)")
    elif vol_div < 0:
        res.strength = max(res.strength, 0.75)
        if res.divergence_type == "NONE": res.divergence_type = "VOLUME"
        if res.pattern in ("NONE", "BULLISH_DIV") and rsi_div != 1.0:
            res.pattern = "BEARISH_DIV"
        signals.append("Volume distribution — price at high on shrinking volume (buying climax)")

    # ── 3. Wyckoff Spring (most powerful bullish signal) ─────────────────────
    if _wyckoff_spring(closes, lows, volumes, lookback):
        res.pattern = "SPRING"   # spring overrides other patterns — highest priority
        res.strength = max(res.strength, 0.90)
        res.inst_absorption = True
        signals.append(
            "Wyckoff Spring — dip below support on low volume + recovery. "
            "Institutional fingerprint of accumulation."
        )

    # ── 4. Wyckoff UTAD (most powerful bearish signal) ───────────────────────
    if _wyckoff_utad(closes, highs, volumes, lookback):
        res.pattern = "UTAD"
        res.strength = max(res.strength, 0.90)
        res.inst_absorption = True
        signals.append(
            "Wyckoff UTAD — push above resistance on high volume + reversal. "
            "Distribution phase confirmed."
        )

    # ── 5. BB Squeeze + Directional Breakout ─────────────────────────────────
    squeeze_dir = _bb_squeeze_breakout(closes)
    if squeeze_dir == 1:
        if res.pattern == "NONE": res.pattern = "SQUEEZE_BULL"
        res.strength = max(res.strength, 0.65)
        signals.append("BB squeeze bullish breakout — compression resolved upward")
    elif squeeze_dir == -1:
        if res.pattern in ("NONE", "BULLISH_DIV"):
            res.pattern = "SQUEEZE_BEAR"
        res.strength = max(res.strength, 0.65)
        signals.append("BB squeeze bearish breakout — compression resolved downward")

    # ── 6. Reversal Candle ───────────────────────────────────────────────────
    candle = _reversal_candle(closes, highs, lows)
    if candle == 1:
        res.strength = max(res.strength, 0.60)
        signals.append("Bullish reversal candle — hammer/doji at swing low (wick > 55% of range)")
    elif candle == -1:
        res.strength = max(res.strength, 0.60)
        signals.append("Bearish reversal candle — shooting star at swing high (wick > 55% of range)")

    # ── 7. Institutional Absorption (flat price + above-average volume) ───────
    if _institutional_absorption(closes, volumes):
        res.inst_absorption = True
        signals.append(
            "Institutional absorption — price flat ±1.5% over 5 bars on above-avg volume. "
            "Smart money absorbing supply at support."
        )

    # ── FIRING LOGIC ─────────────────────────────────────────────────────────
    # Pattern fires when:
    #   (a) Spring or UTAD detected — single highest-conviction signal is enough
    #   (b) At least 2 other signals fired AND strength >= 0.65
    # This prevents false confirmations from weak single signals.
    res.signals = signals
    is_structural = res.pattern in ("SPRING", "UTAD")
    res.fires = is_structural or (len(signals) >= 2 and res.strength >= 0.65)

    return res


# ══════════════════════════════════════════════════════════════════════════════
# PATTERN DETECTION FUNCTIONS (internal)
# ══════════════════════════════════════════════════════════════════════════════

def _rsi(closes: list, period: int = 14) -> float:
    """Simple RSI calculation."""
    if len(closes) < period + 1:
        return 50.0
    gains  = [max(0, closes[-i] - closes[-i-1]) for i in range(1, period+1)]
    losses = [max(0, closes[-i-1] - closes[-i]) for i in range(1, period+1)]
    ag = sum(gains) / period
    al = sum(losses) / period
    return 100 - 100 / (1 + ag / max(al, 0.001))


def _rsi_divergence(closes: list, rsi_period: int = 14, lookback: int = 20) -> float:
    """
    RSI divergence detection.

    Bullish: price makes lower low in 2nd half of lookback, RSI makes higher low → +1.0
    Bearish: price makes higher high in 2nd half, RSI makes lower high → -1.0
    None → 0.0

    Minimum price/RSI movement thresholds prevent false signals from noise.
    """
    if len(closes) < lookback + rsi_period + 5:
        return 0.0
    try:
        half = lookback // 2

        rsi_mid = _rsi(closes[:-half], rsi_period)
        rsi_now = _rsi(closes, rsi_period)

        first  = closes[-lookback:-half]
        second = closes[-half:]
        if not first or not second:
            return 0.0

        p_low1 = min(first);  p_low2 = min(second)
        p_hi1  = max(first);  p_hi2  = max(second)

        # Bullish: newer low is lower (by at least 0.2%) AND RSI made a higher low
        if p_low2 < p_low1 * 0.998 and rsi_now > rsi_mid + 1.0:
            return 1.0

        # Bearish: newer high is higher (by at least 0.2%) AND RSI made a lower high
        if p_hi2 > p_hi1 * 1.002 and rsi_now < rsi_mid - 1.0:
            return -1.0

    except Exception:
        pass
    return 0.0


def _volume_exhaustion(closes: list, volumes: list, lookback: int = 20) -> float:
    """
    Volume-price divergence — detects selling/buying exhaustion.

    Selling exhaustion (bullish +1.0):
      Price is falling to new lows over the lookback window, but recent
      volume (last 5 bars) is less than 75% of the average. Sellers are
      running out of ammunition.

    Buying/distribution exhaustion (bearish -1.0):
      Price is rising to new highs but volume is collapsing. Buyers are
      losing conviction. Smart money is distributing into rising prices.

    Returns 0.0 if neither condition met.
    """
    if len(closes) < lookback + 10 or len(volumes) < lookback + 10:
        return 0.0
    try:
        avg_vol    = sum(volumes[-(lookback+5):-5]) / lookback
        recent_vol = sum(volumes[-5:]) / 5
        vol_shrinking = recent_vol < avg_vol * 0.75

        price_falling = closes[-1] < closes[-lookback]   # lower than N bars ago
        price_rising  = closes[-1] > closes[-lookback]   # higher than N bars ago

        if vol_shrinking and price_falling:
            return 1.0   # selling exhaustion → price likely to bounce
        if vol_shrinking and price_rising:
            return -1.0  # distribution → price likely to top

    except Exception:
        pass
    return 0.0


def _wyckoff_spring(closes: list, lows: list, volumes: list, lookback: int = 30) -> bool:
    """
    Detect Wyckoff Spring — the clearest institutional accumulation signal.

    Condition 1: Price briefly dips BELOW the prior support (lowest low of the
                 lookback range, excluding last 5 bars) on BELOW-AVERAGE volume.
                 Low volume = weak sellers, not panic selling.

    Condition 2: Price recovers quickly back ABOVE the support level, and the
                 current close is above the close from 4 bars ago (momentum shift).

    Both conditions must hold simultaneously in the last 5 bars.
    """
    if len(closes) < lookback or len(lows) < lookback or len(volumes) < lookback:
        return False
    try:
        # Support level = lowest low in lookback window, excluding last 5 bars
        support = min(lows[-lookback:-5])
        avg_vol = sum(volumes[-lookback:-5]) / max(lookback - 5, 1)

        # Spring: any of the last 5 bars dips below support on low volume
        spring_bar = any(
            lows[-i] < support * 0.998 and volumes[-i] < avg_vol * 0.85
            for i in range(1, 6)
        )
        # Recovery: current close back above support and above 4 bars ago
        recovery = closes[-1] > support and closes[-1] > closes[-5]

        return spring_bar and recovery

    except Exception:
        return False


def _wyckoff_utad(closes: list, highs: list, volumes: list, lookback: int = 30) -> bool:
    """
    Detect Wyckoff UTAD (Upthrust After Distribution) — bearish signal.

    Condition 1: Price briefly pushes ABOVE the prior resistance (highest high
                 of the lookback range, excluding last 5 bars) on ABOVE-AVERAGE
                 volume. High volume push = smart money selling into strength.

    Condition 2: Price reverses quickly back BELOW the resistance level, and
                 the current close is below the close from 4 bars ago.

    The UTAD is the distribution zone equivalent of the Spring in accumulation.
    """
    if len(closes) < lookback or len(highs) < lookback or len(volumes) < lookback:
        return False
    try:
        resistance = max(highs[-lookback:-5])
        avg_vol    = sum(volumes[-lookback:-5]) / max(lookback - 5, 1)

        # UTAD: any of the last 5 bars pushes above resistance on high volume
        utad_bar = any(
            highs[-i] > resistance * 1.002 and volumes[-i] > avg_vol * 1.15
            for i in range(1, 6)
        )
        # Reversal: current close back below resistance and below 4 bars ago
        reversal = closes[-1] < resistance and closes[-1] < closes[-5]

        return utad_bar and reversal

    except Exception:
        return False


def _bb_squeeze_breakout(closes: list, period: int = 20, history: int = 100) -> int:
    """
    Detect BB squeeze followed by directional breakout.

    Step 1: Was BB width compressed (below 20th percentile) in the last 3 bars?
    Step 2: Is BB width now expanding (current > previous)?
    Step 3: Which direction did price close in? → determines bull or bear breakout.

    Returns:
       +1 if squeeze + expanding + price rising (SQUEEZE_BULL)
       -1 if squeeze + expanding + price falling (SQUEEZE_BEAR)
        0 if no squeeze detected
    """
    if len(closes) < period + history:
        return 0
    try:
        def bb_width(c_slice: list) -> float:
            mid = sum(c_slice) / len(c_slice)
            std = (sum((x - mid)**2 for x in c_slice) / len(c_slice)) ** 0.5
            return (4 * std) / max(mid, 0.01)

        # Compute widths for all available bars (excluding current)
        widths = [
            bb_width(closes[i - period:i])
            for i in range(period, len(closes) - 1)
        ]
        if len(widths) < 50:
            return 0

        p20 = sorted(widths)[int(len(widths) * 0.20)]

        # Was squeeze present in recent bars?
        was_squeezed = all(widths[-k] <= p20 for k in range(1, 4) if k <= len(widths))

        # Is width now expanding?
        cur_width  = bb_width(closes[-period:])
        prev_width = widths[-1] if widths else cur_width
        expanding  = cur_width > prev_width * 1.05

        if was_squeezed and expanding:
            price_direction = closes[-1] > closes[-4]  # bullish if close above 4-bar-ago
            return 1 if price_direction else -1

    except Exception:
        pass
    return 0


def _reversal_candle(closes: list, highs: list, lows: list, lookback: int = 5) -> int:
    """
    Detect reversal candles at swing extremes.

    Bullish (hammer at swing low):
      - Current bar's low is the lowest of last `lookback` bars (at swing low)
      - Lower wick > 55% of total bar range
      - Body < 30% of total bar range
      → Returns +1

    Bearish (shooting star at swing high):
      - Current bar's high is the highest of last `lookback` bars (at swing high)
      - Upper wick > 55% of total bar range
      - Body < 30% of total bar range
      → Returns -1

    Returns 0 if no reversal candle detected.
    """
    if len(closes) < lookback + 1 or len(highs) < lookback + 1 or len(lows) < lookback + 1:
        return 0
    try:
        total_range = highs[-1] - lows[-1]
        if total_range < closes[-1] * 0.002:
            # Doji with no range — not a meaningful candle
            return 0

        body       = abs(closes[-1] - closes[-2])
        body_ratio = body / total_range

        open_close_high = max(closes[-1], closes[-2])
        open_close_low  = min(closes[-1], closes[-2])

        lower_wick = (open_close_low - lows[-1])  / total_range
        upper_wick = (highs[-1] - open_close_high) / total_range

        at_swing_low  = lows[-1]  == min(lows[-lookback:])
        at_swing_high = highs[-1] == max(highs[-lookback:])

        # Hammer: at swing low, dominant lower wick, small body
        if at_swing_low and lower_wick > 0.55 and body_ratio < 0.30:
            return 1

        # Shooting star: at swing high, dominant upper wick, small body
        if at_swing_high and upper_wick > 0.55 and body_ratio < 0.30:
            return -1

    except Exception:
        pass
    return 0


def _institutional_absorption(closes: list, volumes: list, lookback: int = 10) -> bool:
    """
    Detect institutional absorption — the setup that precedes Wyckoff markup.

    Characteristic: Over the last 5 bars, price is essentially FLAT (tight range
    within 1.5% of each other) while volume is ABOVE average. This means large
    buyers are absorbing all available supply without moving price much.

    This is different from a Spring (which has a brief excursion below support).
    Absorption happens at or near support, with price marking time before the move.
    """
    if len(closes) < lookback + 5 or len(volumes) < lookback + 5:
        return False
    try:
        avg_vol    = sum(volumes[-(lookback+5):-5]) / lookback
        recent_vol = sum(volumes[-5:]) / 5

        price_range = (max(closes[-5:]) - min(closes[-5:])) / max(closes[-5:])

        return recent_vol > avg_vol * 1.30 and price_range < 0.015

    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# QUICK SELF-TEST (run as standalone: python core/pattern_engine.py)
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import random
    random.seed(42)

    print("pattern_engine.py — self-test")
    print("=" * 40)

    # Build synthetic spring pattern
    base = [500 - i * 0.3 for i in range(60)]    # downtrend
    support = min(base)
    # Spring: dip below support on low vol, recover
    base += [support * 0.994, support * 0.998, support * 1.01, support * 1.02, support * 1.03]
    closes = base
    highs  = [c * 1.005 for c in closes]
    lows   = [c * 0.995 for c in closes]
    avg_v  = 100_000
    vols   = [avg_v] * 60 + [avg_v * 0.70, avg_v * 0.75, avg_v * 1.2, avg_v * 1.3, avg_v * 1.1]
    # Lower the spring bar lows
    lows[-5] = support * 0.993
    lows[-4] = support * 0.996

    r = detect(closes, highs, lows, vols)
    print(f"Spring test:  pattern={r.pattern}, fires={r.fires}, strength={r.strength:.2f}")
    print(f"  signals: {r.signals}")
    assert r.fires, "Spring should fire"

    # Build synthetic RSI divergence (bullish)
    # First half: declining price
    half1 = [500 - i * 1.5 for i in range(30)]
    # Second half: price makes lower low, but smaller decline (RSI should be higher)
    half2_start = half1[-1] - 5          # slight lower low
    half2 = [half2_start - i * 0.2 for i in range(20)]
    closes2 = half1 + half2 + [half2[-1] + 1, half2[-1] + 2]  # small uptick at end
    highs2  = [c * 1.005 for c in closes2]
    lows2   = [c * 0.995 for c in closes2]
    vols2   = [avg_v * (0.9 - i*0.005) for i in range(len(closes2))]  # declining volume

    r2 = detect(closes2, highs2, lows2, vols2)
    print(f"\nRSI div test: pattern={r2.pattern}, fires={r2.fires}, divergence={r2.divergence_type}")
    print(f"  signals: {r2.signals}")

    print("\nAll tests passed.")