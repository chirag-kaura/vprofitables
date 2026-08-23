"""
deep_signal_engine.py — GANN-ASTRO v4.0 Deep Signal Engine
==============================================================
PURPOSE: Use machine-learning to predict reversal PRICE and reversal DATE
         with higher precision than pure rule-based systems.

APPROACH (no GPU required — runs on CPU in <2 seconds per symbol):

STEP 1 — FEATURE EXTRACTION
  Every day for a symbol we compute 38 features:
  ├─ Technical: RSI(14), MACD, BB%B, ATR, SMA ratios, volume ratio
  ├─ Gann: distance to nearest Sq9 level (above/below), angle proximity
  ├─ Simons/Fourier: cycle phase (0-1), days_to_trough, r_squared
  ├─ Natal: bull_aspects, bear_aspects, ruler_activated
  ├─ Sentiment: news_score, bulk_deal_signal, institutional_score
  └─ NEW v4.0 — Divergence & Pattern (4 features):
       rsi_divergence    (+1 bullish, -1 bearish, 0 none)
       volume_divergence (+1 exhaustion, -1 distribution, 0 none)
       bb_squeeze        (1.0 = BB width at <20th percentile)
       wyckoff_spring    (1.0 = spring pattern detected)

STEP 2 — MODEL ENSEMBLE
  Model A — Random Forest: predicts DIRECTION (UP/DOWN/NEUTRAL) probability
  Model B — Gradient Boost: predicts MAGNITUDE (% move in next N days)
  Model C — Reversal Detector: predicts whether TODAY is within ±2 bars of reversal
  Model D — Cycle Timing: regression model for days-to-next-reversal

STEP 3 — OUTPUT
  {
    "direction_prob":    0.72,         # 0-1, probability of upward move
    "expected_move_pct": 8.3,          # expected % move if direction correct
    "reversal_prob":     0.85,         # probability current price IS a reversal point
    "reversal_price":    984.48,       # predicted reversal price (entry level)
    "reversal_date":     "2026-04-20", # predicted date of next reversal
    "days_to_reversal":  5,            # days until next reversal
    "confidence":        0.71,         # combined model confidence
    "model_version":     "v4.0-rf",
    "features_used":     38,
  }

TRAINING (auto-learns from your own market_data_v2.db):
  - Reads historical OHLCV from DB
  - Computes features at each bar
  - v4.0 LABEL CHANGE: labels whether bar is within ±2 bars of a swing high/low
    (not just "did price move 3% in next 10 days" — that was labelling trending bars)
  - Trains RandomForest + GradientBoost on NSE price history
  - Model improves automatically as more data is collected
  - No manual labelling needed — price data is the ground truth

SESSION 1+2 CHANGES vs v3.9:
  FIX — extract_features(): added 4 divergence/pattern features.
        rsi_divergence, volume_price_divergence, bb_squeeze, wyckoff_spring.
        These are the reversal fingerprints the model was missing.
        N_FEATURES updated from 34 → 38.

  FIX — build_training_data(): labels now detect actual swing high/low bars
        (price is local min/max within ±5 bars) rather than any bar where
        price later moved 3%+. The old label was tagging every trending bar
        as UP. The new label targets the actual reversal point.

  NOTE — After deploying this file, retrain the model:
        python core/deep_signal_engine.py
        This rebuilds direction_model.pkl and timing_model.pkl with the new
        features and correct labels. Old .pkl files will not be compatible.

MODEL PERSISTENCE:
  - Saved to core/models/ directory
  - Auto-retrained weekly via scheduler
  - Version-tagged with accuracy metrics
"""

import os, sys, math, pickle, sqlite3
import numpy as np
from datetime import date, timedelta, datetime
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.ephemeris import get_all_planets, NAKSHATRA_DATA
from core.aspects import detect_aspects
from core.quant_engine import fourier_cycle_analysis
from core.indicators import calculate_rsi
from data.instruments import get_instrument
from core.paths import DB_PATH, BASE_DIR
MODEL_DIR  = os.path.join(BASE_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1: FEATURE ENGINEERING
# Every feature is normalized and interpretable
# ══════════════════════════════════════════════════════════════════════════════

def _rsi(closes: list, period: int = 14) -> float:
    return calculate_rsi(closes, period)

def _macd(closes: list) -> Tuple[float, float]:
    """Returns (MACD line, signal) normalized by price."""
    if len(closes) < 26: return 0.0, 0.0
    def ema(data, n):
        k = 2/(n+1); e = data[0]
        for v in data[1:]: e = v*k + e*(1-k)
        return e
    ema12 = ema(closes[-26:], 12); ema26 = ema(closes[-26:], 26)
    macd_line = (ema12 - ema26) / max(closes[-1], 0.01)
    signal = ema([macd_line], 9)
    return round(macd_line * 100, 4), round(signal * 100, 4)

def _bb_pct(closes: list, period: int = 20) -> float:
    if len(closes) < period: return 0.5
    c = closes[-period:]
    mid = sum(c)/len(c)
    std = (sum((x-mid)**2 for x in c)/len(c))**0.5
    bb_lo = mid - 2*std; bb_hi = mid + 2*std
    return round((closes[-1] - bb_lo) / max(bb_hi - bb_lo, 0.001), 4)

def _atr(highs: list, lows: list, closes: list, period: int = 14) -> float:
    if len(closes) < 2: return 0.02
    trs = [max(highs[-i]-lows[-i], abs(highs[-i]-closes[-i-1]), abs(lows[-i]-closes[-i-1]))
           for i in range(1, min(period+1, len(closes)))]
    return sum(trs)/len(trs)/max(closes[-1], 0.01)

def _volume_ratio(volumes: list, period: int = 20) -> float:
    if len(volumes) < period+1: return 1.0
    avg = sum(volumes[-period-1:-1])/period
    return round(volumes[-1]/max(avg, 1), 3)

def _sq9_features(price: float) -> Dict:
    """How close is price to Gann Sq9 levels? Returns proximity 0-1."""
    sqp = math.sqrt(price)
    levels = [(round(max(0.01, sqp-d)**2, 2), "sup") for d in [0.25, 0.5, 1.0, 1.5, 2.0]] + \
             [(round((sqp+d)**2, 2), "res") for d in [0.25, 0.5, 1.0, 1.5, 2.0]]
    nearest_sup = min([abs(price-l)/price for l,t in levels if t=="sup"], default=0.5)
    nearest_res = min([abs(price-l)/price for l,t in levels if t=="res"], default=0.5)
    on_sq9 = 1.0 if nearest_sup < 0.01 or nearest_res < 0.01 else 0.0
    return {
        "sq9_dist_sup": round(nearest_sup, 4),
        "sq9_dist_res": round(nearest_res, 4),
        "sq9_on_level": on_sq9,
    }

def _trend_features(closes: list) -> Dict:
    if len(closes) < 50: return {"trend_5":0,"trend_20":0,"trend_50":0,"above_sma20":0,"above_sma50":0}
    sma5  = sum(closes[-5:])/5
    sma20 = sum(closes[-20:])/20
    sma50 = sum(closes[-50:])/min(50,len(closes))
    cur   = closes[-1]
    return {
        "trend_5":    round((cur/sma5  - 1)*100, 3),
        "trend_20":   round((cur/sma20 - 1)*100, 3),
        "trend_50":   round((cur/sma50 - 1)*100, 3),
        "above_sma20": int(cur > sma20),
        "above_sma50": int(cur > sma50),
    }

def _swing_features(highs: list, lows: list, closes: list, period: int = 20) -> Dict:
    """Wave-based features: where are we in the current swing?"""
    if len(closes) < period:
        return {"wave_pos": 0.5, "from_swing_low": 0.0, "from_swing_high": 0.0}
    h_max = max(highs[-period:]); l_min = min(lows[-period:])
    rng   = max(h_max - l_min, closes[-1]*0.001)
    wave_pos = (closes[-1] - l_min) / rng
    return {
        "wave_pos":        round(wave_pos, 4),
        "from_swing_low":  round((closes[-1]-l_min)/l_min*100, 2),
        "from_swing_high": round((h_max-closes[-1])/h_max*100, 2),
    }


# ══════════════════════════════════════════════════════════════════════════════
# NEW v4.0 — DIVERGENCE & PATTERN FEATURES
# These are the actual reversal fingerprints the model was missing.
# Each returns a normalized value the model can learn from directly.
# ══════════════════════════════════════════════════════════════════════════════

def _rsi_divergence(closes: list, rsi_period: int = 14, lookback: int = 20) -> float:
    """
    Detect RSI divergence against price over the last `lookback` bars.

    Bullish divergence: price makes a lower low in the second half of the
    lookback window while RSI makes a higher low → price is oversold and
    momentum is strengthening → return +1.0

    Bearish divergence: price makes a higher high while RSI makes a lower
    high → price is overbought but momentum is weakening → return -1.0

    No divergence → 0.0

    This is one of the highest-conviction reversal signals when it occurs
    at a Gann Sq9 level or inside a Fourier cycle trough window.
    """
    if len(closes) < lookback + rsi_period + 5:
        return 0.0
    try:
        half = lookback // 2

        def rsi_at(c):
            return calculate_rsi(c, rsi_period)

        rsi_mid = rsi_at(closes[:-half])
        rsi_now = rsi_at(closes)

        price_first_half = closes[-lookback:-half]
        price_second_half = closes[-half:]

        p_low1 = min(price_first_half) if price_first_half else closes[-lookback]
        p_low2 = min(price_second_half) if price_second_half else closes[-1]
        p_hi1  = max(price_first_half) if price_first_half else closes[-lookback]
        p_hi2  = max(price_second_half) if price_second_half else closes[-1]

        # Bullish: lower price low + higher RSI low
        if p_low2 < p_low1 * 0.998 and rsi_now > rsi_mid + 1.0:
            return 1.0

        # Bearish: higher price high + lower RSI high
        if p_hi2 > p_hi1 * 1.002 and rsi_now < rsi_mid - 1.0:
            return -1.0

    except Exception:
        pass
    return 0.0


def _volume_price_divergence(closes: list, volumes: list, lookback: int = 10) -> float:
    """
    Detect volume-price divergence — the most reliable standalone reversal signal.

    Selling exhaustion (bullish): price is falling to new lows but volume is
    DECLINING. Sellers are running out of ammunition. When selling climaxes on
    high volume and then subsequent lows are made on LOW volume → return +1.0

    Distribution (bearish): price is rising to new highs but volume is DECLINING.
    Buyers are losing conviction. Smart money is distributing into strength.
    → return -1.0

    No divergence → 0.0
    """
    if len(closes) < lookback + 10 or len(volumes) < lookback + 10:
        return 0.0
    try:
        # Compare average volume over lookback vs recent 5 bars
        avg_vol    = sum(volumes[-(lookback+5):-5]) / lookback
        recent_vol = sum(volumes[-5:]) / 5
        vol_shrinking = recent_vol < avg_vol * 0.75

        price_falling = closes[-1] < closes[-lookback]
        price_rising  = closes[-1] > closes[-lookback]

        if vol_shrinking and price_falling:
            return 1.0   # selling exhaustion → bullish reversal signal
        if vol_shrinking and price_rising:
            return -1.0  # distribution → bearish reversal signal

    except Exception:
        pass
    return 0.0


def _bb_squeeze(closes: list, period: int = 20, history: int = 252) -> float:
    """
    Detect Bollinger Band squeeze — a compression that precedes explosive moves.

    BB squeeze = current BB width is at or below the 20th percentile of the
    last `history` bars. When the squeeze resolves (BB width expands after
    compression), the first directional move tends to sustain.

    Returns 1.0 if currently in a squeeze, 0.0 otherwise.
    The squeeze itself is neutral — direction is determined by the breakout candle.
    Pattern engine uses this + price direction to give SQUEEZE_BULL or SQUEEZE_BEAR.
    """
    if len(closes) < max(period, history):
        return 0.0
    try:
        def bb_width(c_slice):
            mid = sum(c_slice) / len(c_slice)
            std = (sum((x - mid)**2 for x in c_slice) / len(c_slice)) ** 0.5
            return (4 * std) / max(mid, 0.01)

        # Compute width for last `history` bars
        widths = [
            bb_width(closes[i - period:i])
            for i in range(period, len(closes))
        ]
        if len(widths) < 50:
            return 0.0

        cur_width = widths[-1]
        p20_width = sorted(widths)[int(len(widths) * 0.20)]
        return 1.0 if cur_width <= p20_width else 0.0

    except Exception:
        return 0.0


def _wyckoff_spring(closes: list, lows: list, volumes: list, lookback: int = 30) -> float:
    """
    Detect Wyckoff Spring pattern — the institutional fingerprint of accumulation.

    A Spring occurs when:
    1. Price briefly dips BELOW a well-established support level (the prior lows
       of the trading range) on BELOW-AVERAGE volume (weak sellers)
    2. Price then quickly recovers ABOVE the support level (smart money absorption)

    This is the highest-conviction bullish reversal pattern because it shows
    institutional traders absorbing all remaining supply at the bottom.

    Returns 1.0 if spring detected in the last 5 bars, 0.0 otherwise.
    """
    if len(closes) < lookback or len(lows) < lookback or len(volumes) < lookback:
        return 0.0
    try:
        # Support = lowest low in the lookback window, excluding last 5 bars
        support  = min(lows[-lookback:-5])
        avg_vol  = sum(volumes[-lookback:-5]) / (lookback - 5)

        # Spring bar: dips below support on below-average volume (weak hands)
        spring_detected = any(
            lows[-i] < support * 0.998 and volumes[-i] < avg_vol * 0.85
            for i in range(1, 6)
        )
        # Recovery: current close is back above support and above 3-bar-ago close
        recovery = closes[-1] > support and closes[-1] > closes[-4]

        return 1.0 if spring_detected and recovery else 0.0

    except Exception:
        return 0.0


def _adx(highs: list, lows: list, closes: list, period: int = 14) -> float:
    """Average Directional Index (ADX) normalized to 0.0 - 1.0."""
    if len(closes) < period * 2 + 2:
        return 0.5
    try:
        tr_l, pdm_l, ndm_l = [], [], []
        for i in range(1, len(closes)):
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
            dp = highs[i] - highs[i-1]
            dn = lows[i-1] - lows[i]
            pdm = dp if (dp > 0 and dp > dn) else 0.0
            ndm = dn if (dn > 0 and dn > dp) else 0.0
            tr_l.append(tr)
            pdm_l.append(pdm)
            ndm_l.append(ndm)

        def wilder_smooth(data, n):
            smooth = [sum(data[:n])]
            for val in data[n:]:
                smooth.append(smooth[-1] - (smooth[-1] / n) + val)
            return smooth

        atr_s = wilder_smooth(tr_l, period)
        pdm_s = wilder_smooth(pdm_l, period)
        ndm_s = wilder_smooth(ndm_l, period)

        dx_l = []
        for k in range(len(atr_s)):
            atr_val = max(atr_s[k], 0.001)
            di_plus = (pdm_s[k] / atr_val) * 100
            di_minus = (ndm_s[k] / atr_val) * 100
            sum_di = di_plus + di_minus
            diff_di = abs(di_plus - di_minus)
            dx = (diff_di / max(sum_di, 0.001)) * 100
            dx_l.append(dx)

        adx_val = sum(dx_l[-period:]) / period
        return round(adx_val / 100.0, 4)
    except Exception:
        return 0.5


def _zscore(closes: list, period: int = 20) -> float:
    """Rolling 20-day Z-Score mapped to -1.0 to 1.0 (clamped)."""
    if len(closes) < period:
        return 0.0
    try:
        slice_c = closes[-period:]
        mean = sum(slice_c) / period
        std = (sum((x - mean)**2 for x in slice_c) / period) ** 0.5
        if std == 0:
            return 0.0
        z = (closes[-1] - mean) / std
        return round(max(-3.0, min(3.0, z)) / 3.0, 4)
    except Exception:
        return 0.0


def _cmo(closes: list, period: int = 14) -> float:
    """Chande Momentum Oscillator (CMO) normalized to -1.0 to 1.0."""
    if len(closes) < period + 1:
        return 0.0
    try:
        gains, losses = 0.0, 0.0
        for i in range(1, period + 1):
            diff = closes[-i] - closes[-i-1]
            if diff > 0:
                gains += diff
            else:
                losses += abs(diff)
        denom = gains + losses
        if denom == 0:
            return 0.0
        return round((gains - losses) / denom, 4)
    except Exception:
        return 0.0


def extract_features(
    closes: list, highs: list, lows: list, volumes: list,
    fourier_phase: float = 0.5,          # 0=trough, 0.5=mid, 1=peak
    days_to_trough: int = 999,
    fourier_r2: float = 0.0,
    natal_bull: int = 0, natal_bear: int = 0,
    ruler_activated: int = 0,
    news_score: float = 0.0,
    bulk_signal: float = 0.0,            # +1=BUY, -1=SELL, 0=NEUTRAL
    inst_score: float = 0.0,             # institutional accumulation 0-100
    gann_angle_support: int = 0,         # 1 if price near Gann angle
    nakshatra_alignment: float = 0.0,    # 1.0 if sector favored
    nakshatra_volatility: float = 0.5,   # 0.0-1.0 volatility index
    pcr_val: float = 1.0,
    max_pain_dev: float = 0.0,
    support_dev: float = -0.05,
    resistance_dev: float = 0.05,
) -> Optional[np.ndarray]:
    """
    Build feature vector from all available signals.
    Returns numpy array of shape (1, N_FEATURES) or None if insufficient data.

    v4.1: N_FEATURES = 41 (was 38). 3 new indicators added: ADX, Z-Score, CMO.
    IMPORTANT: retrain models after deploying this version.
    """
    if len(closes) < 50: return None
    try:
        rsi   = _rsi(closes)
        macd, macd_sig = _macd(closes)
        bb    = _bb_pct(closes)
        atr   = _atr(highs, lows, closes)
        volr  = _volume_ratio(volumes)
        sq9   = _sq9_features(closes[-1])
        trend = _trend_features(closes)
        swing = _swing_features(highs, lows, closes)

        # Momentum: return over last N days
        ret5  = (closes[-1]/closes[-6]  - 1)*100 if len(closes) > 6  else 0.0
        ret10 = (closes[-1]/closes[-11] - 1)*100 if len(closes) > 11 else 0.0
        ret20 = (closes[-1]/closes[-21] - 1)*100 if len(closes) > 21 else 0.0

        # Volume momentum
        vol5  = sum(volumes[-5:])/5 / max(sum(volumes[-25:-5])/20, 1)

        # Natal net signal (-1 to +1)
        natal_net = (natal_bull - natal_bear) / max(natal_bull + natal_bear, 1)

        # Fourier: phase normalized, proximity to trough
        days_trough_norm = min(days_to_trough, 365) / 365.0

        # ── NEW v4.0: Divergence & Pattern features ───────────────────────
        rsi_div   = _rsi_divergence(closes)           # +1 bull / -1 bear / 0
        vol_div   = _volume_price_divergence(closes, volumes)  # +1 exhaustion / -1 dist
        bb_sq     = _bb_squeeze(closes)               # 1.0 = squeeze active
        wyckoff_s = _wyckoff_spring(closes, lows, volumes)     # 1.0 = spring detected

        # NEW v4.1: Indicators
        adx_val = _adx(highs, lows, closes)
        z_score = _zscore(closes)
        cmo_val = _cmo(closes)

        feats = [
            # Technical (14 features)
            rsi / 100.0,
            bb,
            atr,
            macd / 10.0,
            macd_sig / 10.0,
            trend["trend_5"]  / 10.0,
            trend["trend_20"] / 10.0,
            trend["trend_50"] / 10.0,
            float(trend["above_sma20"]),
            float(trend["above_sma50"]),
            ret5  / 10.0,
            ret10 / 10.0,
            ret20 / 10.0,
            min(volr, 5.0) / 5.0,

            # Gann Sq9 (3 features)
            min(sq9["sq9_dist_sup"], 0.1) / 0.1,
            min(sq9["sq9_dist_res"], 0.1) / 0.1,
            sq9["sq9_on_level"],

            # Wave position (3 features)
            swing["wave_pos"],
            min(swing["from_swing_low"],  50) / 50.0,
            min(swing["from_swing_high"], 50) / 50.0,

            # Simons/Fourier (3 features)
            fourier_phase,
            1.0 - days_trough_norm,   # higher = trough is closer (buy signal)
            fourier_r2,

            # Natal (3 features)
            min(natal_bull, 10) / 10.0,
            min(natal_bear, 10) / 10.0,
            natal_net,

            # Planetary (1 feature)
            float(ruler_activated),

            # Sentiment (3 features)
            max(-1.0, min(1.0, news_score)),
            max(-1.0, min(1.0, bulk_signal)),
            min(inst_score, 100) / 100.0,

            # Gann angle (1 feature)
            float(gann_angle_support),

            # Volume surge (1 feature)
            min(vol5, 5.0) / 5.0,

            # Nakshatra Context (2 features)
            nakshatra_alignment,
            nakshatra_volatility,

            # NEW v4.0 — Divergence & Pattern (4 features)
            rsi_div,        # RSI divergence: +1 bullish, -1 bearish, 0 none
            vol_div,        # Volume divergence: +1 exhaustion, -1 distribution
            bb_sq,          # BB squeeze: 1.0 = compressed, imminent breakout
            wyckoff_s,      # Wyckoff spring: 1.0 = institutional accumulation

            # NEW v4.1 — Advanced Indicators (3 features)
            adx_val,
            z_score,
            cmo_val,

            # NEW v4.2 — Option Chain Open Interest (4 features)
            pcr_val,
            max_pain_dev,
            support_dev,
            resistance_dev
        ]
        return np.array(feats, dtype=np.float32).reshape(1, -1)
    except Exception:
        return None


# IMPORTANT: N_FEATURES must match len(feats) above exactly.
# v3.9 = 34. v4.0 = 38. v4.1 = 41. v4.2 = 45. Old .pkl models are incompatible — retrain.
N_FEATURES = 45


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2: TRAINING DATA BUILDER
# Reads historical data from DB, computes features+labels for every bar
# ══════════════════════════════════════════════════════════════════════════════

def _db_conn():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"DB not found: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


_ASTRO_ASPECTS_CACHE = {}


def _get_astro_aspects(dt: date) -> Tuple[int, int, int]:
    """Helper to detect aspects and cache them for historical dates."""
    if dt in _ASTRO_ASPECTS_CACHE:
        return _ASTRO_ASPECTS_CACHE[dt]
    try:
        aspects = detect_aspects(dt)
        bull = sum(1 for a in aspects if a.bullish_bearish == "BULLISH")
        bear = sum(1 for a in aspects if a.bullish_bearish == "BEARISH")
        planets = get_all_planets(dt)
        ruler = int(any(planets[p].retrograde for p in ["Mercury", "Jupiter", "Venus"]))
        res = (bull, bear, ruler)
    except Exception:
        res = (0, 0, 0)
    _ASTRO_ASPECTS_CACHE[dt] = res
    return res


_SENTIMENT_SCORE_CACHE = {}
_BULK_SIGNAL_CACHE = {}
_INST_SCORE_CACHE = {}


def _get_sentiment_score(conn, symbol: str, date_str: str) -> float:
    """Query average news sentiment score for symbol over the last 3 days before date_str."""
    key = (symbol, date_str[:10])
    if key in _SENTIMENT_SCORE_CACHE:
        return _SENTIMENT_SCORE_CACHE[key]
    try:
        t_dt = date.fromisoformat(date_str[:10])
        t_start = (t_dt - timedelta(days=3)).isoformat()
        row = conn.execute("""
            SELECT AVG(COALESCE(calibrated_score, raw_score)) 
            FROM news_sentiment 
            WHERE symbol = ? AND published_at <= ? AND published_at >= ?
        """, (symbol, date_str[:10] + " 23:59", t_start + " 00:00")).fetchone()
        res = float(row[0]) if row[0] is not None else 0.0
    except Exception:
        res = 0.0
    _SENTIMENT_SCORE_CACHE[key] = res
    return res


def _get_bulk_signal(conn, symbol: str, date_str: str) -> float:
    """Query net bulk deal signal over the last 7 days (1.0 = Buy, -1.0 = Sell, 0.0 = Neutral)."""
    key = (symbol, date_str[:10])
    if key in _BULK_SIGNAL_CACHE:
        return _BULK_SIGNAL_CACHE[key]
    try:
        t_dt = date.fromisoformat(date_str[:10])
        t_start = (t_dt - timedelta(days=7)).isoformat()
        row = conn.execute("""
            SELECT SUM(CASE WHEN deal_type = 'BUY' THEN quantity * price ELSE -quantity * price END)
            FROM bulk_block_deals
            WHERE symbol = ? AND deal_date <= ? AND deal_date >= ?
        """, (symbol, date_str[:10], t_start)).fetchone()
        val = float(row[0]) if row[0] is not None else 0.0
        res = 1.0 if val > 0 else -1.0 if val < 0 else 0.0
    except Exception:
        res = 0.0
    _BULK_SIGNAL_CACHE[key] = res
    return res


def _get_inst_score(conn, symbol: str, date_str: str) -> float:
    """Query FII + DII percentage from shareholding for the most recent quarter."""
    key = (symbol, date_str[:10])
    if key in _INST_SCORE_CACHE:
        return _INST_SCORE_CACHE[key]
    try:
        t_dt = date.fromisoformat(date_str[:10])
        q = (t_dt.month - 1) // 3 + 1
        q_str = f"{t_dt.year}-Q{q}"
        row = conn.execute("""
            SELECT fii_pct, dii_pct 
            FROM shareholding 
            WHERE symbol = ? AND quarter <= ? 
            ORDER BY quarter DESC LIMIT 1
        """, (symbol, q_str)).fetchone()
        if row:
            res = float(row["fii_pct"] or 0.0) + float(row["dii_pct"] or 0.0)
        else:
            res = 0.0
    except Exception:
        res = 0.0
    _INST_SCORE_CACHE[key] = res
    return res


def build_training_data(
    symbols: Optional[List[str]] = None,
    lookback_years: int = 3,
    forward_days: int = 10,
    threshold_pct: float = 3.0,
    min_rows: int = 200,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build X (features), y_direction (UP=1/NEUTRAL=0/DOWN=-1), y_days (days to reversal).

    v4.0 LABEL CHANGE — Session 2 Fix:
    OLD label (v3.9): "did price move threshold_pct% in the next forward_days?"
      → Problem: this labels EVERY bar in an uptrend as UP, even mid-trend bars.
        The model learned "if price is trending up, it will keep going up" —
        a momentum model, not a reversal model.

    NEW label (v4.0): "is THIS bar within ±2 bars of a swing high or swing low?"
      A swing low  = local minimum within a ±5-bar window (looking left and right).
      A swing high = local maximum within a ±5-bar window.
      Only labeled UP/DOWN if the swing move is >= threshold_pct%.
      → The model now learns "what does price/volume look like JUST BEFORE a reversal?"
        This is the correct task for a reversal detection model.

    Returns:
      X        — feature matrix (n_samples, N_FEATURES)
      y_dir    — labels: 1=reversal LOW (buy), -1=reversal HIGH (sell), 0=neutral
      y_days   — days from this bar to the next significant price peak/trough
    """
    try:
        conn = _db_conn()
    except FileNotFoundError:
        return np.array([]), np.array([]), np.array([])

    if symbols is None:
        # Default to top 14 highly liquid sector leaders + indices for training efficiency
        symbols = [
            'NIFTY50', 'BANKNIFTY', 'RELIANCE', 'TCS', 'INFY', 
            'HDFCBANK', 'ICICIBANK', 'SBIN', 'BHARTIARTL', 'ITC', 
            'AXISBANK', 'KOTAKBANK', 'LT', 'TATASTEEL'
        ]

    cutoff = (date.today() - timedelta(days=int(lookback_years * 365))).isoformat()
    X_all, y_dir, y_days_all, planets_all = [], [], [], []

    for sym in symbols:
        try:
            inst = get_instrument(sym)
            planet = inst.ruling_planet if inst else "Unknown"
            rows = conn.execute("""
                SELECT trade_date, open, high, low, close, volume
                FROM daily_prices
                WHERE symbol=? AND close IS NOT NULL AND trade_date >= ?
                ORDER BY trade_date ASC
            """, (sym, cutoff)).fetchall()

            if len(rows) < min_rows: continue

            dates_s   = [r[0] for r in rows]
            closes_s  = [float(r[4]) for r in rows]
            highs_s   = [float(r[2] or r[4]) for r in rows]
            lows_s    = [float(r[3] or r[4]) for r in rows]
            volumes_s = [int(r[5] or 0) for r in rows]

            # Scan each bar: need 60 bars of history + 5 bars ahead for swing detection
            for i in range(60, len(closes_s) - forward_days - 5):

                # Nakshatra alignment for this historical date
                trade_dt = datetime.fromisoformat(dates_s[i]).date()
                try:
                    planets = get_all_planets(trade_dt)
                    moon_nak_name = planets["Moon"].nakshatra
                    alignment = 0.0
                    volatility = 0.5
                    inst = get_instrument(sym)
                    if inst:
                        for nak in NAKSHATRA_DATA:
                            if nak["name"] == moon_nak_name:
                                for s in nak["sectors"]:
                                    if s.lower() in inst.sector.lower() or inst.sector.lower() in s.lower():
                                        alignment = 1.0
                                if nak["lord"] in ["Rahu", "Ketu", "Mars"]:   volatility = 0.9
                                elif nak["lord"] in ["Saturn", "Sun"]:         volatility = 0.7
                                elif nak["lord"] in ["Moon", "Venus", "Jupiter"]: volatility = 0.3
                                break
                except Exception:
                    alignment, volatility = 0.0, 0.5

                # ── Run historical Fourier cycle analysis ──
                f_phase, f_days_trough, f_r2 = 0.5, 999, 0.0
                try:
                    fres = fourier_cycle_analysis(closes_s[:i+1])
                    if "error" not in fres:
                        f_r2 = fres.get("r_squared", 0.0)
                        fc60 = fres.get("forecast_60d", [])
                        if fc60:
                            prices_only = [p for _, p in fc60]
                            min_val = min(prices_only)
                            min_idx = prices_only.index(min_val)
                            f_phase = min_idx / len(prices_only)
                            f_days_trough = min_idx + 1
                except Exception:
                    pass

                # ── Fetch historical Aspects, News, and Deals ──
                natal_bull, natal_bear, ruler_activated = _get_astro_aspects(trade_dt)
                news_score = _get_sentiment_score(conn, sym, dates_s[i])
                bulk_signal = _get_bulk_signal(conn, sym, dates_s[i])
                inst_score = _get_inst_score(conn, sym, dates_s[i])

                # ── Fetch options metrics ──
                pcr_val = 1.0
                max_pain_dev = 0.0
                support_dev = -0.05
                resistance_dev = 0.05

                try:
                    pcr_row = conn.execute(
                        "SELECT pcr, max_pain FROM pcr_summary WHERE symbol=? AND trade_date=? LIMIT 1",
                        (sym, dates_s[i])
                    ).fetchone()
                    if pcr_row:
                        pcr_val = float(pcr_row[0] or 1.0)
                        m_pain = float(pcr_row[1] or closes_s[i])
                        max_pain_dev = (closes_s[i] - m_pain) / closes_s[i]
                        
                        # Find nearest expiry option chain boundaries
                        exp_row = conn.execute(
                            "SELECT MIN(expiry_date) FROM option_chain_data WHERE symbol=? AND trade_date=? AND expiry_date >= ?",
                            (sym, dates_s[i], dates_s[i])
                        ).fetchone()
                        if exp_row and exp_row[0]:
                            nearest_exp = exp_row[0]
                            max_pe = conn.execute(
                                "SELECT strike FROM option_chain_data WHERE symbol=? AND trade_date=? AND expiry_date=? AND option_type='PE' ORDER BY oi DESC LIMIT 1",
                                (sym, dates_s[i], nearest_exp)
                            ).fetchone()
                            max_ce = conn.execute(
                                "SELECT strike FROM option_chain_data WHERE symbol=? AND trade_date=? AND expiry_date=? AND option_type='CE' ORDER BY oi DESC LIMIT 1",
                                (sym, dates_s[i], nearest_exp)
                            ).fetchone()
                            if max_pe:
                                support_dev = (closes_s[i] - float(max_pe[0])) / closes_s[i]
                            if max_ce:
                                resistance_dev = (float(max_ce[0]) - closes_s[i]) / closes_s[i]
                except Exception:
                    pass

                feats = extract_features(
                    closes_s[:i+1], highs_s[:i+1], lows_s[:i+1], volumes_s[:i+1],
                    fourier_phase=f_phase,
                    days_to_trough=f_days_trough,
                    fourier_r2=f_r2,
                    natal_bull=natal_bull,
                    natal_bear=natal_bear,
                    ruler_activated=ruler_activated,
                    news_score=news_score,
                    bulk_signal=bulk_signal,
                    inst_score=inst_score,
                    nakshatra_alignment=alignment,
                    nakshatra_volatility=volatility,
                    pcr_val=pcr_val,
                    max_pain_dev=max_pain_dev,
                    support_dev=support_dev,
                    resistance_dev=resistance_dev,
                )
                if feats is None: continue

                # ── v4.0 LABEL: Is bar [i] within ±2 bars of a swing high/low? ──
                # Use a symmetric 5-bar window: 2 bars left + current + 2 bars right
                win_size = 5
                half_win = win_size // 2

                # Slice: [i-2, i-1, i, i+1, i+2]
                w_closes = closes_s[i - half_win : i + half_win + 1]
                w_lows   = lows_s[  i - half_win : i + half_win + 1]
                w_highs  = highs_s[ i - half_win : i + half_win + 1]

                cur        = closes_s[i]
                cur_low    = lows_s[i]
                cur_high   = highs_s[i]

                is_swing_low  = cur_low  == min(w_lows)   and len(w_lows)  == win_size
                is_swing_high = cur_high == max(w_highs)  and len(w_highs) == win_size

                # Measure the actual swing move forward from this bar
                future_closes = closes_s[i+1 : i+1+forward_days]
                if not future_closes: continue

                future_max = max(future_closes)
                future_min = min(future_closes)

                # Swing must produce a meaningful move to be labeled
                move_up   = (future_max - cur) / cur * 100
                move_down = (cur - future_min)  / cur * 100

                if is_swing_low and move_up >= threshold_pct:
                    label    = 1   # reversal LOW — buy signal
                    peak_i   = future_closes.index(future_max)
                    days_rev = peak_i + 1

                elif is_swing_high and move_down >= threshold_pct:
                    label     = -1  # reversal HIGH — sell/exit signal
                    trough_i  = future_closes.index(future_min)
                    days_rev  = trough_i + 1

                else:
                    label    = 0   # neutral — not a significant reversal bar
                    days_rev = forward_days // 2

                X_all.append(feats[0])
                y_dir.append(label)
                y_days_all.append(days_rev)
                planets_all.append(planet)

        except Exception:
            continue

    conn.close()

    if not X_all:
        return np.array([]), np.array([]), np.array([]), np.array([])

    return (
        np.array(X_all, dtype=np.float32),
        np.array(y_dir,  dtype=np.int32),
        np.array(y_days_all, dtype=np.float32),
        np.array(planets_all),
    )


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3: MODEL TRAINING
# Uses sklearn RandomForest + GradientBoosting (CPU-friendly)
# ══════════════════════════════════════════════════════════════════════════════

DIRECTION_MODEL_PATH = os.path.join(MODEL_DIR, "direction_model.pkl")
TIMING_MODEL_PATH    = os.path.join(MODEL_DIR, "timing_model.pkl")
META_PATH            = os.path.join(MODEL_DIR, "model_meta.pkl")


def train_models(
    symbols: Optional[List[str]] = None,
    lookback_years: int = 3,
    forward_days: int = 10,
    min_samples: int = 500,
    verbose: bool = True,
) -> Dict:
    """
    Train direction + timing models, building both per-ruling-planet models and a global fallback.
    Returns global accuracy metrics dict.
    """
    try:
        from sklearn.ensemble import HistGradientBoostingClassifier, GradientBoostingRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import classification_report, mean_absolute_error
        from sklearn.pipeline import Pipeline
    except ImportError:
        return {"error": "scikit-learn not installed. Run: pip install scikit-learn"}

    if verbose:
        print(f"  [ML v4.1] Building training data...")
        print(f"  [ML v4.1] N_FEATURES={N_FEATURES} | lookback={lookback_years}y | forward={forward_days}d")
        print(f"  [ML v4.1] Labels: swing high/low bars (±2 bar window), not trend bars")

    X, y_dir, y_days, planets = build_training_data(
        symbols=symbols, lookback_years=lookback_years, forward_days=forward_days
    )

    if len(X) < min_samples:
        return {
            "error": (
                f"Insufficient training data: {len(X)} samples (need {min_samples}). "
                f"Run the app for a few weeks to collect more price history."
            )
        }

    # Helper function to train and save direction + timing models for a subset
    def _train_single_subset(sub_X, sub_y_dir, sub_y_days, label_suffix, min_sz=80):
        if len(sub_X) < min_sz:
            if verbose:
                print(f"    Skipping planet subset {label_suffix}: too few samples ({len(sub_X)} < {min_sz})")
            return None, None, None

        # Train Direction Model
        try:
            X_tr, X_te, y_tr, y_te = train_test_split(sub_X, sub_y_dir, test_size=0.2, random_state=42)
            from core.ml_ensemble_engine import train_single_ensemble
            dir_pipe, ens_metrics = train_single_ensemble(X_tr, y_tr, X_te, y_te, verbose=verbose)
            dir_acc = ens_metrics["ensemble_accuracy"]
        except Exception as e:
            print(f"    Error training ensemble direction classifier for {label_suffix}: {e}")
            import traceback
            traceback.print_exc()
            return None, None, None

        # Train Timing Model
        timing_pipe = None
        tim_mae = float("nan")
        try:
            non_neutral = np.where(sub_y_dir != 0)[0]
            if len(non_neutral) > 30:
                X_nd, y_nd = sub_X[non_neutral], sub_y_days[non_neutral]
                X_tr2, X_te2, y_tr2, y_te2 = train_test_split(X_nd, y_nd, test_size=0.2, random_state=42)
                timing_pipe = Pipeline([
                    ("scaler", StandardScaler()),
                    ("reg", GradientBoostingRegressor(
                        n_estimators=100,
                        max_depth=3,
                        learning_rate=0.08,
                        subsample=0.8,
                        random_state=42,
                    ))
                ])
                timing_pipe.fit(X_tr2, y_tr2)
                y_pred_tim = timing_pipe.predict(X_te2)
                tim_mae = mean_absolute_error(y_te2, y_pred_tim)
        except Exception as e:
            print(f"    Error training timing regressor for {label_suffix}: {e}")

        # Meta
        meta_d = {
            "version":        f"v4.1-{date.today().isoformat()}",
            "trained_at":     datetime.now().isoformat(),
            "n_samples":      len(sub_X),
            "n_features":     sub_X.shape[1],
            "dir_accuracy":   dir_acc,
            "timing_mae":     tim_mae,
            "forward_days":   forward_days,
            "lookback_years": lookback_years,
            "label_method":   "swing_highlow_pm2bars",
        }

        # Paths
        dp = os.path.join(MODEL_DIR, f"direction_model_{label_suffix.lower()}.pkl")
        tp = os.path.join(MODEL_DIR, f"timing_model_{label_suffix.lower()}.pkl")
        mp = os.path.join(MODEL_DIR, f"model_meta_{label_suffix.lower()}.pkl")

        with open(dp, "wb") as f: pickle.dump(dir_pipe, f)
        if timing_pipe:
            with open(tp, "wb") as f: pickle.dump(timing_pipe, f)
        with open(mp, "wb") as f: pickle.dump(meta_d, f)

        if verbose:
            print(f"    [ML v4.1] Planet {label_suffix}: samples={len(sub_X)} | dir_acc={dir_acc:.1%} | tim_mae={tim_mae:.1f}d")
        return dir_pipe, timing_pipe, meta_d

    # 1. Train global fallback model
    if verbose:
        print("  [ML v4.1] Training global model...")
    global_dir_pipe, global_timing_pipe, global_meta = _train_single_subset(X, y_dir, y_days, "global", min_sz=min_samples)

    # 2. Train per-ruling-planet models
    unique_planets = np.unique(planets)
    for planet in unique_planets:
        if not planet or planet == "Unknown":
            continue
        is_planet = planets == planet
        sub_X = X[is_planet]
        sub_y_dir = y_dir[is_planet]
        sub_y_days = y_days[is_planet]
        _train_single_subset(sub_X, sub_y_dir, sub_y_days, planet, min_sz=80)

    # Keep compatibility with existing paths (link direction_model.pkl to direction_model_global.pkl)
    if global_dir_pipe:
        with open(DIRECTION_MODEL_PATH, "wb") as f: pickle.dump(global_dir_pipe, f)
    if global_timing_pipe:
        with open(TIMING_MODEL_PATH, "wb") as f: pickle.dump(global_timing_pipe, f)
    if global_meta:
        with open(META_PATH, "wb") as f: pickle.dump(global_meta, f)

    return global_meta or {"status": "trained"}


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4: INFERENCE — predict for a single symbol right now
# ══════════════════════════════════════════════════════════════════════════════

_DIR_MODELS_CACHE = {}     # planet_name -> model pipeline
_TIM_MODELS_CACHE = {}     # planet_name -> model pipeline
_PLANETS_META_CACHE = {}   # planet_name -> meta dict
_CACHE_LOADED_AT = None

def _load_model_for_planet(planet: str):
    global _DIR_MODELS_CACHE, _TIM_MODELS_CACHE, _PLANETS_META_CACHE, _CACHE_LOADED_AT
    planet = (planet or "global").lower()
    now = datetime.now()
    
    # Reload all cached models if older than 1 hour
    if _CACHE_LOADED_AT and (now - _CACHE_LOADED_AT).seconds > 3600:
        _DIR_MODELS_CACHE.clear()
        _TIM_MODELS_CACHE.clear()
        _PLANETS_META_CACHE.clear()
        _CACHE_LOADED_AT = now
    elif not _CACHE_LOADED_AT:
        _CACHE_LOADED_AT = now

    if planet in _DIR_MODELS_CACHE:
        return

    # Paths for this specific planet model
    dir_path = os.path.join(MODEL_DIR, f"direction_model_{planet}.pkl")
    tim_path = os.path.join(MODEL_DIR, f"timing_model_{planet}.pkl")
    meta_path = os.path.join(MODEL_DIR, f"model_meta_{planet}.pkl")

    if os.path.exists(dir_path):
        try:
            with open(dir_path, "rb") as f:
                dm = pickle.load(f)
            
            # Check features size compatibility
            mm = None
            if os.path.exists(meta_path):
                with open(meta_path, "rb") as f:
                    mm = pickle.load(f)
            
            if mm and mm.get("n_features", N_FEATURES) == N_FEATURES:
                _DIR_MODELS_CACHE[planet] = dm
                _PLANETS_META_CACHE[planet] = mm
                if os.path.exists(tim_path):
                    with open(tim_path, "rb") as f:
                        _TIM_MODELS_CACHE[planet] = pickle.load(f)
                return
        except Exception:
            pass

    # Fallback: Load global model
    global_dir_path = os.path.join(MODEL_DIR, "direction_model_global.pkl")
    global_tim_path = os.path.join(MODEL_DIR, "timing_model_global.pkl")
    global_meta_path = os.path.join(MODEL_DIR, "model_meta_global.pkl")

    if "global" not in _DIR_MODELS_CACHE:
        # If legacy files exist, use them
        g_dir = global_dir_path if os.path.exists(global_dir_path) else DIRECTION_MODEL_PATH
        g_tim = global_tim_path if os.path.exists(global_tim_path) else TIMING_MODEL_PATH
        g_meta = global_meta_path if os.path.exists(global_meta_path) else META_PATH
        
        if os.path.exists(g_dir):
            try:
                with open(g_dir, "rb") as f:
                    _DIR_MODELS_CACHE["global"] = pickle.load(f)
                if os.path.exists(g_tim):
                    with open(g_tim, "rb") as f:
                        _TIM_MODELS_CACHE["global"] = pickle.load(f)
                if os.path.exists(g_meta):
                    with open(g_meta, "rb") as f:
                        _PLANETS_META_CACHE["global"] = pickle.load(f)
            except Exception:
                pass

    if "global" in _DIR_MODELS_CACHE:
        _DIR_MODELS_CACHE[planet] = _DIR_MODELS_CACHE["global"]
        if "global" in _TIM_MODELS_CACHE:
            _TIM_MODELS_CACHE[planet] = _TIM_MODELS_CACHE["global"]
        if "global" in _PLANETS_META_CACHE:
            _PLANETS_META_CACHE[planet] = _PLANETS_META_CACHE["global"]


def predict_reversal(
    closes: list, highs: list, lows: list, volumes: list,
    current_price: float,
    analysis_date: Optional[date] = None,
    # Augmented signals from other engines
    fourier_phase: float = 0.5,
    days_to_trough: int = 999,
    fourier_r2: float = 0.0,
    natal_bull: int = 0, natal_bear: int = 0,
    ruler_activated: int = 0,
    news_score: float = 0.0,
    bulk_signal: float = 0.0,
    inst_score: float = 0.0,
    gann_angle_support: int = 0,
    symbol: str = "",
) -> Dict:
    """
    Main inference function. Returns reversal prediction dict.
    Falls back to rule-based heuristics if models not trained yet.

    v4.0: no ML VETO. ML direction_prob is one input, not a gatekeeper.
    ML confidence < 0.55 → ML weight = 0 (sits out, rule-based takes over).
    """
    # Phase 4 Planet-specific ML model loading
    inst_obj = get_instrument(symbol) if symbol else None
    planet_lbl = inst_obj.ruling_planet if inst_obj else "global"
    _load_model_for_planet(planet_lbl)
    
    dir_model = _DIR_MODELS_CACHE.get(planet_lbl.lower())
    tim_model = _TIM_MODELS_CACHE.get(planet_lbl.lower())
    meta_data = _PLANETS_META_CACHE.get(planet_lbl.lower())

    today = analysis_date or date.today()

    # Nakshatra alignment
    alignment = 0.0
    volatility = 0.5
    if symbol:
        try:
            planets = get_all_planets(today)
            moon_nak_name = planets["Moon"].nakshatra
            inst = get_instrument(symbol)
            if inst:
                for nak in NAKSHATRA_DATA:
                    if nak["name"] == moon_nak_name:
                        for s in nak["sectors"]:
                            if s.lower() in inst.sector.lower() or inst.sector.lower() in s.lower():
                                alignment = 1.0
                        if nak["lord"] in ["Rahu", "Ketu", "Mars"]:    volatility = 0.9
                        elif nak["lord"] in ["Saturn", "Sun"]:          volatility = 0.7
                        elif nak["lord"] in ["Moon", "Venus", "Jupiter"]: volatility = 0.3
                        break
        except Exception:
            pass

    # ── Auto-compute missing/default features for inference alignment ──
    if fourier_phase == 0.5 and days_to_trough == 999:
        try:
            fres = fourier_cycle_analysis(closes)
            if "error" not in fres:
                fourier_r2 = fres.get("r_squared", 0.0)
                fc60 = fres.get("forecast_60d", [])
                if fc60:
                    prices_only = [p for _, p in fc60]
                    min_val = min(prices_only)
                    min_idx = prices_only.index(min_val)
                    fourier_phase = min_idx / len(prices_only)
                    days_to_trough = min_idx + 1
        except Exception:
            pass

    if natal_bull == 0 and natal_bear == 0:
        try:
            natal_bull, natal_bear, ruler_activated = _get_astro_aspects(today)
        except Exception:
            pass

    pcr_val = 1.0
    max_pain_dev = 0.0
    support_dev = -0.05
    resistance_dev = 0.05

    if symbol:
        today_str = today.isoformat()
        key = (symbol, today_str[:10])
        if key in _SENTIMENT_SCORE_CACHE and key in _BULK_SIGNAL_CACHE and key in _INST_SCORE_CACHE:
            if news_score == 0.0:
                news_score = _SENTIMENT_SCORE_CACHE[key]
            if bulk_signal == 0.0:
                bulk_signal = _BULK_SIGNAL_CACHE[key]
            if inst_score == 0.0:
                inst_score = _INST_SCORE_CACHE[key]
        else:
            try:
                conn = sqlite3.connect(DB_PATH, timeout=5)
                conn.row_factory = sqlite3.Row
                if news_score == 0.0:
                    news_score = _get_sentiment_score(conn, symbol, today_str)
                if bulk_signal == 0.0:
                    bulk_signal = _get_bulk_signal(conn, symbol, today_str)
                if inst_score == 0.0:
                    inst_score = _get_inst_score(conn, symbol, today_str)
                conn.close()
            except Exception:
                pass

        try:
            conn = sqlite3.connect(DB_PATH, timeout=5)
            pcr_row = conn.execute(
                "SELECT pcr, max_pain FROM pcr_summary WHERE symbol=? AND trade_date<=? ORDER BY trade_date DESC LIMIT 1",
                (symbol, today_str)
            ).fetchone()
            if pcr_row:
                pcr_val = float(pcr_row[0] or 1.0)
                m_pain = float(pcr_row[1] or closes[-1])
                max_pain_dev = (closes[-1] - m_pain) / closes[-1]
                
                # Fetch option chain support/resistance
                tc_row = conn.execute(
                    "SELECT MAX(trade_date) FROM option_chain_data WHERE symbol=? AND trade_date<=?",
                    (symbol, today_str)
                ).fetchone()
                if tc_row and tc_row[0]:
                    last_tc = tc_row[0]
                    exp_row = conn.execute(
                        "SELECT MIN(expiry_date) FROM option_chain_data WHERE symbol=? AND trade_date=? AND expiry_date >= ?",
                        (symbol, last_tc, last_tc)
                    ).fetchone()
                    if exp_row and exp_row[0]:
                        nearest_exp = exp_row[0]
                        max_pe = conn.execute(
                            "SELECT strike FROM option_chain_data WHERE symbol=? AND trade_date=? AND expiry_date=? AND option_type='PE' ORDER BY oi DESC LIMIT 1",
                            (symbol, last_tc, nearest_exp)
                        ).fetchone()
                        max_ce = conn.execute(
                            "SELECT strike FROM option_chain_data WHERE symbol=? AND trade_date=? AND expiry_date=? AND option_type='CE' ORDER BY oi DESC LIMIT 1",
                            (symbol, last_tc, nearest_exp)
                        ).fetchone()
                        if max_pe:
                            support_dev = (closes[-1] - float(max_pe[0])) / closes[-1]
                        if max_ce:
                            resistance_dev = (float(max_ce[0]) - closes[-1]) / closes[-1]
            conn.close()
        except Exception:
            pass

    feats = extract_features(
        closes, highs, lows, volumes,
        fourier_phase=fourier_phase, days_to_trough=days_to_trough,
        fourier_r2=fourier_r2, natal_bull=natal_bull, natal_bear=natal_bear,
        ruler_activated=ruler_activated, news_score=news_score,
        bulk_signal=bulk_signal, inst_score=inst_score,
        gann_angle_support=gann_angle_support,
        nakshatra_alignment=alignment,
        nakshatra_volatility=volatility,
        pcr_val=pcr_val,
        max_pain_dev=max_pain_dev,
        support_dev=support_dev,
        resistance_dev=resistance_dev,
    )

    if feats is None:
        return _rule_based_fallback(closes, highs, lows, current_price, today)

    # ── Direction prediction ──────────────────────────────────────────────────
    direction_prob = 0.5
    direction      = "NEUTRAL"
    model_version  = "rule-based"

    if dir_model is not None:
        try:
            proba   = dir_model.predict_proba(feats)[0]
            classes = dir_model.classes_
            class_to_prob = dict(zip(classes, proba))
            up_prob   = class_to_prob.get(1,  0.0)
            down_prob = class_to_prob.get(-1, 0.0)
            direction = "UP" if up_prob > 0.52 else "DOWN" if down_prob > 0.52 else "NEUTRAL"
            direction_prob = up_prob if direction == "UP" else down_prob if direction == "DOWN" else 0.5
            model_version  = meta_data.get("version", "v4.1") if meta_data else "v4.1"
        except Exception:
            pass

    # ── Timing prediction ─────────────────────────────────────────────────────
    days_to_rev = _fallback_timing(closes, fourier_phase, days_to_trough, direction)
    if tim_model is not None:
        try:
            days_pred   = float(tim_model.predict(feats)[0])
            days_to_rev = max(1, min(365, int(round(days_pred))))
        except Exception:
            pass

    # ── Reversal price prediction ─────────────────────────────────────────────
    reversal_price = _predict_reversal_price(closes, highs, lows, current_price, direction, days_to_rev)

    # ── Reversal date ─────────────────────────────────────────────────────────
    rev_date = today + timedelta(days=days_to_rev)
    while rev_date.weekday() >= 5: rev_date += timedelta(days=1)

    # ── Confidence ────────────────────────────────────────────────────────────
    signal_alignment = _score_signal_alignment(
        direction, fourier_phase, days_to_trough, natal_bull, natal_bear,
        ruler_activated, news_score, bulk_signal,
    )
    if dir_model is not None:
        raw_conf = 0.6 * direction_prob + 0.4 * signal_alignment
    else:
        raw_conf = signal_alignment

    if direction == "NEUTRAL":
        _fourier_prox = 1.0 - min(days_to_trough, 30) / 30.0
        raw_conf = max(raw_conf, 0.35 + _fourier_prox * 0.15)

    confidence = round(min(0.95, max(0.35, raw_conf)), 3)

    # ── Expected move % ───────────────────────────────────────────────────────
    sqp = math.sqrt(current_price)
    if direction == "UP":
        target_sq9   = round((sqp + 0.5)**2, 2)
        expected_move = round((target_sq9 - current_price)/current_price*100, 2)
    elif direction == "DOWN":
        target_sq9   = round(max(0.01, sqp - 0.5)**2, 2)
        expected_move = round((current_price - target_sq9)/current_price*100, 2)
    else:
        expected_move = 0.0

    return {
        "direction":         direction,
        "direction_prob":    round(direction_prob, 3),
        "expected_move_pct": expected_move,
        "reversal_prob":     round(signal_alignment, 3),
        "reversal_price":    reversal_price,
        "reversal_date":     rev_date.isoformat(),
        "days_to_reversal":  days_to_rev,
        "confidence":        confidence,
        "model_version":     model_version,
        "model_trained":     dir_model is not None,
        "features_used":     N_FEATURES,
        "signal_alignment":  round(signal_alignment, 3),
    }


def _fallback_timing(closes, fourier_phase, days_to_trough, direction):
    """Rule-based timing estimate when ML timing model is unavailable."""
    rsi = _rsi(closes)
    if days_to_trough < 999:
        return max(1, min(days_to_trough, 90))
    if direction == "UP":
        return 3 if rsi < 30 else 5 if rsi < 40 else 8
    elif direction == "DOWN":
        return 3 if rsi > 70 else 5 if rsi > 60 else 8
    else:
        bb = _bb_pct(closes)
        if bb < 0.20 or bb > 0.80: return 4
        if rsi < 38 or rsi > 62:   return 5
        return 10


def _predict_reversal_price(closes, highs, lows, current_price, direction, days):
    """Predict WHERE the reversal will occur — Sq9 grid + fractal S/R."""
    sqp = math.sqrt(current_price)
    sq9_res = [round((sqp + d)**2, 2)           for d in [0.25, 0.5, 1.0, 1.5, 2.0]]
    sq9_sup = [round(max(0.01, sqp - d)**2, 2)  for d in [0.25, 0.5, 1.0, 1.5, 2.0]]

    swing_highs, swing_lows = [], []
    lb = min(len(highs), 30)
    for k in range(2, lb - 2):
        i = -(lb - k)
        win_h = highs[i-2:i+3] if i+3 <= 0 else highs[i-2:]
        win_l = lows[i-2:i+3]  if i+3 <= 0 else lows[i-2:]
        if win_h and highs[i] == max(win_h): swing_highs.append(highs[i])
        if win_l and lows[i]  == min(win_l): swing_lows.append(lows[i])

    if direction == "UP":
        candidates = sq9_res[:]
        if swing_highs: candidates.append(max(swing_highs))
        above = sorted([c for c in candidates if c > current_price * 1.003])
        return above[0] if above else round(current_price * 1.04, 2)

    elif direction == "DOWN":
        candidates = sq9_sup[:]
        if swing_lows: candidates.append(min(swing_lows))
        below = sorted([c for c in candidates if c < current_price * 0.997], reverse=True)
        return below[0] if below else round(current_price * 0.96, 2)

    else:
        mom5 = (closes[-1]/closes[-6] - 1) if len(closes) > 6 else 0.0
        if mom5 >= 0:
            above = sorted([c for c in sq9_res if c > current_price * 1.003])
            return above[0] if above else round(current_price * 1.03, 2)
        else:
            below = sorted([c for c in sq9_sup if c < current_price * 0.997], reverse=True)
            return below[0] if below else round(current_price * 0.97, 2)


def _score_signal_alignment(
    direction, fourier_phase, days_to_trough, natal_bull, natal_bear,
    ruler_activated, news_score, bulk_signal,
):
    """Score how well all non-ML signals agree with predicted direction (0–1)."""
    score = 0.0; total = 0.0

    fourier_available = (days_to_trough < 999) or (abs(fourier_phase - 0.5) > 0.05)
    if fourier_available:
        if direction == "UP":
            score += (1.0 - fourier_phase) * 0.25
        elif direction == "DOWN":
            score += fourier_phase * 0.25
        else:
            score += abs(fourier_phase - 0.5) * 2 * 0.25
        total += 0.25

    if days_to_trough < 999:
        if direction == "UP" and days_to_trough <= 20:
            score += (1.0 - days_to_trough / 20) * 0.20
        elif direction == "DOWN" and days_to_trough > 40:
            score += min((days_to_trough - 40) / 60, 1.0) * 0.20
        elif direction == "NEUTRAL":
            score += max(0.0, 1.0 - days_to_trough / 30) * 0.20
        total += 0.20

    if natal_bull > 0 or natal_bear > 0:
        if direction == "UP":
            score += min(natal_bull, 5) / 5 * 0.20
        elif direction == "DOWN":
            score += min(natal_bear, 5) / 5 * 0.20
        else:
            score += min(abs(natal_bull - natal_bear), 3) / 3 * 0.20
        total += 0.20

    if ruler_activated:
        score += 0.10; total += 0.10

    if abs(news_score) > 0.05:
        if direction == "UP":   score += max(0, news_score)  * 0.15
        elif direction == "DOWN": score += max(0, -news_score) * 0.15
        else:                   score += abs(news_score) * 0.10
        total += 0.15

    if abs(bulk_signal) > 0:
        if direction == "UP" and bulk_signal > 0:
            score += min(bulk_signal, 1.0) * 0.10
        elif direction == "DOWN" and bulk_signal < 0:
            score += min(-bulk_signal, 1.0) * 0.10
        elif direction == "NEUTRAL":
            score += min(abs(bulk_signal), 1.0) * 0.05
        total += 0.10

    if total == 0:
        return 0.30
    return round(score / total, 3)


def _rule_based_fallback(closes, highs, lows, current_price, today):
    """Minimal fallback when not enough data for ML features."""
    rsi = _rsi(closes)
    direction = "UP" if rsi < 40 else "DOWN" if rsi > 65 else "NEUTRAL"
    sqp = math.sqrt(current_price)
    if direction == "UP":
        rev_price = round((sqp + 0.5)**2, 2); days = 5
    elif direction == "DOWN":
        rev_price = round(max(0.01, sqp - 0.5)**2, 2); days = 5
    else:
        rev_price = current_price; days = 7
    rev_date = today + timedelta(days=days)
    while rev_date.weekday() >= 5: rev_date += timedelta(days=1)
    return {
        "direction": direction,
        "direction_prob": 0.55 if direction != "NEUTRAL" else 0.5,
        "expected_move_pct": 3.0, "reversal_prob": 0.50,
        "reversal_price": rev_price, "reversal_date": rev_date.isoformat(),
        "days_to_reversal": days, "confidence": 0.45,
        "model_version": "rule-based-fallback", "model_trained": False,
        "features_used": N_FEATURES, "signal_alignment": 0.50,
    }


def get_model_status() -> Dict:
    """Return current model status for display in UI."""
    _load_model_for_planet("global")
    meta_g = _PLANETS_META_CACHE.get("global")
    if meta_g:
        return {
            "trained":      True,
            "version":      meta_g.get("version", "?"),
            "trained_at":   meta_g.get("trained_at", "?")[:10],
            "n_samples":    meta_g.get("n_samples", 0),
            "n_features":   meta_g.get("n_features", N_FEATURES),
            "dir_accuracy": round(meta_g.get("dir_accuracy", 0)*100, 1),
            "timing_mae":   round(meta_g.get("timing_mae", 0), 1),
            "label_method": meta_g.get("label_method", "unknown"),
        }
    return {
        "trained":  False,
        "version":  "untrained",
        "message":  (
            "No model trained yet. Run: python core/deep_signal_engine.py "
            "after collecting sufficient price history (≥500 bars per symbol)."
        ),
    }


if __name__ == "__main__":
    print("GANN-ASTRO v4.1 — Deep Signal Engine Training")
    print("=" * 52)
    print(f"Features: {N_FEATURES} (41 aligned features, including 3 new indicators)")
    print(f"Labels:   swing high/low bars (±2 bar window)")
    print()
    meta = train_models(lookback_years=3, verbose=True)
    if "error" in meta:
        print(f"\nERROR: {meta['error']}")
    else:
        print(f"\nDone! Version:          {meta.get('version')}")
        print(f"Direction accuracy:     {meta.get('dir_accuracy',0):.1%}")
        print(f"Timing MAE:             {meta.get('timing_mae',0):.1f} days")
        print(f"Label method:           {meta.get('label_method','?')}")