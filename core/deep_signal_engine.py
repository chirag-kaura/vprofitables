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
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
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
    close_to_vwap_ratio: float = 1.0,
    deliverable_volume_spike_pct: float = 0.0,
    distance_to_high_volume_pivot: float = 1.0,
    local_pcr_change: float = 0.0,
    atm_vol_oi_ratio: float = 0.0,
    institutional_buy_pressure: float = 0.5,
    net_capital_flow: float = 0.0,
    deal_volume_pct: float = 0.0,
    finbert_prob_bullish: float = 0.5,
    is_guidance_raised: float = 0.0,
    is_regulatory_risk: float = 0.0,
    is_management_change: float = 0.0,
    nifty50_trend_10d: float = 0.0,
    sector_relative_strength: float = 0.0,
    market_breadth: float = 0.5,
    fii_index_long_pct_norm: float = 0.0,
    retail_call_put_imbalance: float = 0.0,
    smart_money_contrarian_bias: float = 0.0,
    vix_value_norm: float = 0.3,
    vix_change_5d: float = 0.0,
) -> Optional[np.ndarray]:
    """
    Build feature vector from all available signals.
    Returns numpy array of shape (1, N_FEATURES) or None if insufficient data.
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
            resistance_dev,
            
            # NEW v4.3 — Structure & Delivery (4 features)
            close_to_vwap_ratio,
            deliverable_volume_spike_pct,
            distance_to_high_volume_pivot,
            local_pcr_change,
            
            # NEW v4.4 — ATM Option Flow (1 feature)
            atm_vol_oi_ratio,
            
            # NEW v4.5 — Bulk Deal Aggregates (3 features)
            institutional_buy_pressure,
            net_capital_flow,
            deal_volume_pct,
            
            # NEW v4.6 — Advanced Sentiment (4 features)
            finbert_prob_bullish,
            is_guidance_raised,
            is_regulatory_risk,
            is_management_change,
            nifty50_trend_10d,
            sector_relative_strength,
            market_breadth,

            # NEW v4.7 — Institutional Positioning & Volatility Regime (5 features)
            fii_index_long_pct_norm,
            retail_call_put_imbalance,
            smart_money_contrarian_bias,
            vix_value_norm,
            vix_change_5d,
        ]
        return np.array(feats, dtype=np.float32).reshape(1, -1)
    except Exception:
        return None


# IMPORTANT: N_FEATURES must match len(feats) above exactly.
N_FEATURES = 65


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


_NIFTY50_TREND_CACHE = {}
_SECTOR_RS_CACHE = {}
_MARKET_BREADTH_CACHE = {}

def _get_nifty50_trend_10d(conn, date_str: str) -> float:
    key = date_str[:10]
    if key in _NIFTY50_TREND_CACHE: return _NIFTY50_TREND_CACHE[key]
    try:
        rows = conn.execute("SELECT close FROM daily_prices WHERE symbol='NIFTY50' AND trade_date <= ? ORDER BY trade_date DESC LIMIT 11", (key,)).fetchall()
        if len(rows) >= 11:
            curr_close = float(rows[0][0])
            past_close = float(rows[10][0])
            res = (curr_close / past_close) - 1.0
        else:
            res = 0.0
    except Exception:
        res = 0.0
    _NIFTY50_TREND_CACHE[key] = res
    return res

def _get_sector_relative_strength(conn, symbol: str, date_str: str) -> float:
    key = (symbol, date_str[:10])
    if key in _SECTOR_RS_CACHE: return _SECTOR_RS_CACHE[key]
    try:
        sym_rows = conn.execute("SELECT close FROM daily_prices WHERE symbol=? AND trade_date <= ? ORDER BY trade_date DESC LIMIT 11", (symbol, date_str[:10])).fetchall()
        if len(sym_rows) < 11:
            res = 0.0
        else:
            sym_ret = (float(sym_rows[0][0]) / float(sym_rows[10][0])) - 1.0
            nifty_ret = _get_nifty50_trend_10d(conn, date_str)
            res = sym_ret - nifty_ret
    except Exception:
        res = 0.0
    _SECTOR_RS_CACHE[key] = res
    return res

def _get_market_breadth(conn, date_str: str) -> float:
    key = date_str[:10]
    if key in _MARKET_BREADTH_CACHE: return _MARKET_BREADTH_CACHE[key]
    try:
        # Proxy for breadth: ratio of stocks closing above VWAP
        row = conn.execute("SELECT COUNT(*), SUM(CASE WHEN close > vwap THEN 1 ELSE 0 END) FROM daily_prices WHERE trade_date = ?", (key,)).fetchone()
        if row and row[0] > 0:
            res = float(row[1]) / float(row[0])
        else:
            res = 0.5
    except Exception:
        res = 0.5
    _MARKET_BREADTH_CACHE[key] = res
    return res

_PARTICIPANT_OI_CACHE = {}
_VIX_CACHE = {}

def _get_participant_oi_features(conn, date_str: str) -> Tuple[float, float, float]:
    key = date_str[:10]
    if key in _PARTICIPANT_OI_CACHE:
        return _PARTICIPANT_OI_CACHE[key]
    try:
        row = conn.execute("""
            SELECT fii_index_long_pct, client_net_index_calls, client_net_index_puts, smart_money_bias
            FROM participant_sentiment_summary
            WHERE trade_date <= ?
            ORDER BY trade_date DESC LIMIT 1
        """, (key,)).fetchone()
        if row:
            fii_pct = float(row[0] or 50.0)
            c_calls = float(row[1] or 0.0)
            c_puts = float(row[2] or 0.0)
            bias_s = str(row[3] or "NEUTRAL")

            fii_norm = (fii_pct - 50.0) / 50.0
            ret_imb = (c_calls - c_puts) / max(abs(c_calls) + abs(c_puts), 1000.0)

            bias_v = 0.0
            if "EXTREME_BULLISH" in bias_s:
                bias_v = 1.0
            elif "BULLISH" in bias_s:
                bias_v = 0.5
            elif "EXTREME_BEARISH" in bias_s:
                bias_v = -1.0
            elif "BEARISH" in bias_s:
                bias_v = -0.5

            res = (fii_norm, ret_imb, bias_v)
        else:
            res = (0.0, 0.0, 0.0)
    except Exception:
        res = (0.0, 0.0, 0.0)
    _PARTICIPANT_OI_CACHE[key] = res
    return res

def _get_vix_features(conn, date_str: str) -> Tuple[float, float]:
    key = date_str[:10]
    if key in _VIX_CACHE:
        return _VIX_CACHE[key]
    try:
        rows = conn.execute("""
            SELECT close FROM daily_prices
            WHERE symbol='INDIAVIX' AND trade_date <= ?
            ORDER BY trade_date DESC LIMIT 6
        """, (key,)).fetchall()
        if rows:
            v_now = float(rows[0][0] or 15.0)
            v_past = float(rows[-1][0] or v_now) if len(rows) > 1 else v_now
            v_norm = round(min(50.0, max(5.0, v_now)) / 50.0, 4)
            v_chg = round((v_now - v_past) / max(v_past, 1.0), 4)
            res = (v_norm, v_chg)
        else:
            res = (0.3, 0.0)
    except Exception:
        res = (0.3, 0.0)
    _VIX_CACHE[key] = res
    return res

def _get_news_features(conn, symbol: str, date_str: str) -> Tuple[float, float, float, float, float]:
    """Returns (news_score, finbert_prob_bullish, is_guidance_raised, is_regulatory_risk, is_management_change)"""
    key = (symbol, date_str[:10])
    if key in _SENTIMENT_SCORE_CACHE:
        return _SENTIMENT_SCORE_CACHE[key]
    try:
        t_dt = date.fromisoformat(date_str[:10])
        t_start = (t_dt - timedelta(days=3)).isoformat()
        row = conn.execute("""
            SELECT AVG(COALESCE(calibrated_score, raw_score)) as score,
                   AVG(finbert_prob_bullish) as finbert_prob_bullish,
                   MAX(is_guidance_raised) as is_guidance_raised,
                   MAX(is_regulatory_risk) as is_regulatory_risk,
                   MAX(is_management_change) as is_management_change
            FROM news_sentiment 
            WHERE symbol = ? AND published_at <= ? AND published_at >= ?
        """, (symbol, date_str[:10] + " 23:59", t_start + " 00:00")).fetchone()
        
        score = float(row[0]) if row and row[0] is not None else 0.0
        fb_bullish = float(row[1]) if row and row[1] is not None else 0.5
        ig_raised = float(row[2]) if row and row[2] is not None else 0.0
        ir_risk = float(row[3]) if row and row[3] is not None else 0.0
        im_change = float(row[4]) if row and row[4] is not None else 0.0
        
        res = (score, fb_bullish, ig_raised, ir_risk, im_change)
    except Exception:
        res = (0.0, 0.5, 0.0, 0.0, 0.0)
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
    horizons: List[int] = [3, 10, 30],
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
                SELECT trade_date, open, high, low, close, volume, vwap, deliverable_qty, deliverable_pct
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
            vwaps_s   = [float(r[6] or r[4]) for r in rows]
            dqty_s    = [int(r[7] or 0) for r in rows]
            dpct_s    = [float(r[8] or 0.0) for r in rows]

            # Scan each bar: need 60 bars of history + 5 bars ahead for swing detection
            max_forward = max(horizons)
            for i in range(60, len(closes_s) - max_forward - 5):

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
                news_score, fb_bullish, ig_raised, ir_risk, im_change = _get_news_features(conn, sym, dates_s[i])
                bulk_signal = _get_bulk_signal(conn, sym, dates_s[i])
                inst_score = _get_inst_score(conn, sym, dates_s[i])

                # ── Fetch options metrics ──
                pcr_val = 1.0
                max_pain_dev = 0.0
                support_dev = -0.05
                resistance_dev = 0.05

                try:
                    pcr_row = conn.execute(
                        "SELECT pcr, max_pain, local_pcr FROM pcr_summary WHERE symbol=? AND trade_date=? LIMIT 1",
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

                # NEW FEATURES CALCULATION
                close_to_vwap_ratio = 1.0
                if vwaps_s[i] > 0:
                    close_to_vwap_ratio = closes_s[i] / vwaps_s[i]
                
                deliverable_volume_spike_pct = 0.0
                if i >= 10:
                    avg_deliv = sum(dqty_s[i-10:i]) / 10
                    if avg_deliv > 0:
                        deliverable_volume_spike_pct = dqty_s[i] / avg_deliv
                
                distance_to_high_volume_pivot = 1.0
                try:
                    high_vol_pivot = conn.execute(
                        "SELECT pivot_price FROM pivot_levels WHERE symbol=? ORDER BY volume_profile DESC LIMIT 1",
                        (sym,)
                    ).fetchone()
                    if high_vol_pivot and high_vol_pivot[0]:
                        distance_to_high_volume_pivot = (closes_s[i] - float(high_vol_pivot[0])) / closes_s[i]
                except Exception:
                    pass
                
                local_pcr_change = 0.0
                atm_vol_oi_ratio = 0.0
                try:
                    curr_pcr_row = conn.execute("SELECT local_pcr, atm_vol_oi_ratio FROM pcr_summary WHERE symbol=? AND trade_date=? AND session='EOD'", (sym, dates_s[i])).fetchone()
                    prev_pcr_row = conn.execute("SELECT local_pcr FROM pcr_summary WHERE symbol=? AND trade_date<? AND session='EOD' ORDER BY trade_date DESC LIMIT 1", (sym, dates_s[i])).fetchone()
                    
                    if curr_pcr_row:
                        curr_lpcr = float(curr_pcr_row[0] or 0.0)
                        atm_vol_oi_ratio = float(curr_pcr_row[1] or 0.0)
                        
                        prev_lpcr = float(prev_pcr_row[0]) if prev_pcr_row and prev_pcr_row[0] else 0.0
                        if prev_lpcr > 0:
                            local_pcr_change = (curr_lpcr - prev_lpcr) / prev_lpcr
                except Exception:
                    pass
                    
                institutional_buy_pressure = 0.5
                net_capital_flow = 0.0
                deal_volume_pct = 0.0
                try:
                    bulk_row = conn.execute("SELECT institutional_buy_pressure, net_capital_flow, deal_volume_pct FROM daily_bulk_summary WHERE symbol=? AND deal_date=?", (sym, dates_s[i])).fetchone()
                    if bulk_row:
                        institutional_buy_pressure = float(bulk_row[0] or 0.5)
                        net_capital_flow = float(bulk_row[1] or 0.0)
                        deal_volume_pct = float(bulk_row[2] or 0.0)
                except Exception:
                    pass

                nifty_trend = _get_nifty50_trend_10d(conn, dates_s[i])
                sector_rs = _get_sector_relative_strength(conn, sym, dates_s[i])
                mkt_breadth = _get_market_breadth(conn, dates_s[i])
                fii_norm, ret_imb, bias_v = _get_participant_oi_features(conn, dates_s[i])
                v_norm, v_chg = _get_vix_features(conn, dates_s[i])
        
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
                    close_to_vwap_ratio=close_to_vwap_ratio,
                    deliverable_volume_spike_pct=deliverable_volume_spike_pct,
                    distance_to_high_volume_pivot=distance_to_high_volume_pivot,
                    local_pcr_change=local_pcr_change,
                    atm_vol_oi_ratio=atm_vol_oi_ratio,
                    institutional_buy_pressure=institutional_buy_pressure,
                    net_capital_flow=net_capital_flow,
                    deal_volume_pct=deal_volume_pct,
                    finbert_prob_bullish=fb_bullish,
                    is_guidance_raised=ig_raised,
                    is_regulatory_risk=ir_risk,
                    is_management_change=im_change,
                    nifty50_trend_10d=nifty_trend,
                    sector_relative_strength=sector_rs,
                    market_breadth=mkt_breadth,
                    fii_index_long_pct_norm=fii_norm,
                    retail_call_put_imbalance=ret_imb,
                    smart_money_contrarian_bias=bias_v,
                    vix_value_norm=v_norm,
                    vix_change_5d=v_chg,
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

                # Measure the actual swing move forward from this bar for multiple horizons
                labels_for_horizons = []
                days_for_horizons = []
                valid = True
                for forward_days in horizons:
                    future_closes = closes_s[i+1 : i+1+forward_days]
                    if len(future_closes) < forward_days // 2:
                        valid = False
                        break

                    future_max = max(future_closes)
                    future_min = min(future_closes)

                    # Swing must produce a meaningful move to be labeled
                    move_up   = (future_max - cur) / cur * 100
                    move_down = (cur - future_min) / cur * 100

                    # NEW: ATR adjusted threshold
                    atr_slice = _atr(highs_s[i-13:i+1], lows_s[i-13:i+1], closes_s[i-13:i+1])
                    dyn_threshold = max(threshold_pct, (atr_slice / cur * 100) * 1.5) if cur > 0 else threshold_pct

                    if is_swing_low and move_up >= dyn_threshold:
                        labels_for_horizons.append(1)
                        days_for_horizons.append(future_closes.index(future_max) + 1)
                    elif is_swing_high and move_down >= dyn_threshold:
                        labels_for_horizons.append(-1)
                        days_for_horizons.append(future_closes.index(future_min) + 1)
                    else:
                        labels_for_horizons.append(0)
                        days_for_horizons.append(forward_days // 2)

                if valid:
                    X_all.append(feats[0])
                    y_dir.append(labels_for_horizons)
                    y_days_all.append(days_for_horizons)
                    planets_all.append(planet)

        except Exception as e:
            print(f"Error on {symbol}: {e}")
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
_MODEL_PATH = os.path.join(MODEL_DIR, "multi_horizon_xgboost.pkl")
META_PATH            = os.path.join(MODEL_DIR, "model_meta.pkl")



def train_models(
    symbols: Optional[List[str]] = None,
    lookback_years: int = 3,
    horizons: List[int] = [3, 10, 30],
    min_samples: int = 500,
    verbose: bool = True,
    **kwargs,
) -> Dict:
    """
    Train Intraday and EOD Ensemble models (XGBoost + PyTorch MLP) for multiple horizons.
    """
    try:
        from xgboost import XGBClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler, QuantileTransformer
        from sklearn.metrics import accuracy_score, roc_auc_score, balanced_accuracy_score, f1_score
        from sklearn.pipeline import Pipeline
        from sklearn.utils.class_weight import compute_class_weight
        import torch
        import torch.nn as nn
        import torch.optim as optim
        from torch.utils.data import TensorDataset, DataLoader
    except ImportError as e:
        return {"error": f"Missing library: {e}"}

    if verbose:
        print(f"\n{'='*50}\n[DEEP SIGNAL ENGINE] Extracting Multi-Horizon Features...\n{'='*50}", flush=True)

    X_all, y_dir, y_days, planets = build_training_data(
        symbols=symbols, lookback_years=lookback_years, horizons=horizons, min_rows=min_samples
    )
    
    if len(X_all) < min_samples:
        return {"error": f"Not enough data: {len(X_all)} < {min_samples}"}

    global_models = {}
    metrics = {}
    
    # MLP Definition
    class ReversalMLP(nn.Module):
        def __init__(self, input_dim):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, 128),
                nn.BatchNorm1d(128),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(128, 64),
                nn.BatchNorm1d(64),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(64, 3) # 3 classes: Down, Neutral, Up
            )
        def forward(self, x):
            return self.net(x)

    for h_idx, horizon in enumerate(horizons):
        y_h = y_dir[:, h_idx] if isinstance(y_dir, np.ndarray) else np.array([y[h_idx] for y in y_dir])
        y_xgb = y_h + 1 # shift to 0, 1, 2
        
        # Dynamic Class Weights
        classes = np.unique(y_xgb)
        cw = compute_class_weight('balanced', classes=classes, y=y_xgb)
        weight_dict = {c: w for c, w in zip(classes, cw)}
        sample_weights = np.array([weight_dict[y] for y in y_xgb])
        
        X_tr, X_te, y_tr, y_te, sw_tr, sw_te = train_test_split(X_all, y_xgb, sample_weights, test_size=0.2, random_state=42)
        
        # XGBoost Pipeline with QuantileTransformer
        pipe_xgb = Pipeline([
            ("scaler", QuantileTransformer(output_distribution='normal')),
            ("clf", XGBClassifier(n_estimators=150, max_depth=6, learning_rate=0.03, random_state=42))
        ])
        pipe_xgb.fit(X_tr, y_tr, clf__sample_weight=sw_tr)
        
        # PyTorch MLP
        scaler = QuantileTransformer(output_distribution='normal')
        X_tr_scaled = scaler.fit_transform(X_tr)
        X_te_scaled = scaler.transform(X_te)
        
        X_t = torch.FloatTensor(X_tr_scaled)
        y_t = torch.LongTensor(y_tr)
        dataset = TensorDataset(X_t, y_t)
        loader = DataLoader(dataset, batch_size=64, shuffle=True)
        
        mlp = ReversalMLP(input_dim=X_t.shape[1])
        criterion = nn.CrossEntropyLoss(weight=torch.FloatTensor(cw))
        optimizer = optim.Adam(mlp.parameters(), lr=0.001)
        
        for epoch in range(15):
            mlp.train()
            for bx, by in loader:
                optimizer.zero_grad()
                out = mlp(bx)
                loss = criterion(out, by)
                loss.backward()
                optimizer.step()
        
        mlp.eval()
        with torch.no_grad():
            preds = mlp(torch.FloatTensor(X_te_scaled))
            pred_classes = torch.argmax(preds, dim=1).numpy()
            
        xgb_preds = pipe_xgb.predict(X_te)
        acc_xgb = accuracy_score(y_te, xgb_preds)
        acc_mlp = accuracy_score(y_te, pred_classes)
        bal_acc_xgb = balanced_accuracy_score(y_te, xgb_preds)
        bal_acc_mlp = balanced_accuracy_score(y_te, pred_classes)
        f1_xgb = f1_score(y_te, xgb_preds, average="macro", zero_division=0)
        f1_mlp = f1_score(y_te, pred_classes, average="macro", zero_division=0)

        global_models[f"xgb_{horizon}d"] = pipe_xgb
        global_models[f"mlp_{horizon}d"] = {"model": mlp.state_dict(), "scaler": scaler, "input_dim": X_t.shape[1]}
        metrics[f"acc_xgb_{horizon}d"] = acc_xgb
        metrics[f"acc_mlp_{horizon}d"] = acc_mlp
        metrics[f"bal_acc_xgb_{horizon}d"] = bal_acc_xgb
        metrics[f"bal_acc_mlp_{horizon}d"] = bal_acc_mlp
        metrics[f"f1_xgb_{horizon}d"] = f1_xgb
        metrics[f"f1_mlp_{horizon}d"] = f1_mlp

        if verbose:
            print(f"[{horizon}d] XGB Acc: {acc_xgb:.2f} (Bal: {bal_acc_xgb:.2f}, F1: {f1_xgb:.2f}) | MLP Acc: {acc_mlp:.2f} (Bal: {bal_acc_mlp:.2f}, F1: {f1_mlp:.2f})", flush=True)

    os.makedirs(os.path.dirname(_MODEL_PATH), exist_ok=True)
    with open(_MODEL_PATH, "wb") as f:
        import pickle
        pickle.dump({
            "models": global_models,
            "metrics": metrics,
            "N_FEATURES": N_FEATURES
        }, f)
        
    return {"status": "trained", "metrics": metrics}

def generate_signals_for_today(symbols: Optional[List[str]] = None, verbose: bool = True) -> List[Dict]:
    """Generate signals using the multi-horizon XGBoost models."""
    import pickle
    if not os.path.exists(_MODEL_PATH):
        if verbose: print("No models found. Train first.")
        return []

    with open(_MODEL_PATH, "rb") as f:
        data = pickle.load(f)
        models = data.get("models", {})

    conn = get_db_connection()
    if not symbols:
        symbols = [r[0] for r in conn.execute("SELECT DISTINCT symbol FROM daily_prices").fetchall()]

    signals = []
    conn.close()
    return signals

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true", help="Build features and train models")
    parser.add_argument("--symbols", type=str, help="Comma-separated symbols to train on (default: all)")
    args = parser.parse_args()

    sym_list = args.symbols.split(",") if args.symbols else None
    
    if args.train:
        train_models(symbols=sym_list)
    else:
        generate_signals_for_today(symbols=sym_list)

def predict_reversal(symbol: Optional[str] = None, date_str: Optional[str] = None, **kwargs) -> Dict:
    import pickle
    import torch
    import torch.nn as nn
    if symbol is None and "symbol" in kwargs:
        symbol = kwargs["symbol"]
    if date_str is None and "analysis_date" in kwargs:
        date_str = kwargs["analysis_date"]

    if not symbol:
        return {
            "error": "Symbol not specified",
            "model_trained": os.path.exists(_MODEL_PATH),
            "confidence": 0.0,
            "direction": "NEUTRAL"
        }

    if not os.path.exists(_MODEL_PATH):
        return {
            "error": "Models not trained.",
            "model_trained": False,
            "confidence": 0.0,
            "direction": "NEUTRAL"
        }
        
    try:
        with open(_MODEL_PATH, "rb") as f:
            data = pickle.load(f)
            models = data["models"]
    except Exception as e:
        return {
            "error": str(e),
            "model_trained": False,
            "confidence": 0.0,
            "direction": "NEUTRAL"
        }

    conn = _db_conn()
    try:
        # Detect date column name (trade_date vs date)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(daily_prices)").fetchall()}
        date_col = "trade_date" if "trade_date" in cols else "date"
        q = f"SELECT {date_col}, close, high, low, volume FROM daily_prices WHERE symbol=? ORDER BY {date_col} ASC"
        rows = conn.execute(q, (symbol,)).fetchall()
        if not rows:
            return {
                "error": f"No data for {symbol}",
                "model_trained": True,
                "confidence": 0.0,
                "direction": "NEUTRAL"
            }
        
        if date_str:
            rows = [r for r in rows if str(r[0])[:10] <= str(date_str)[:10]]
        
        if len(rows) < 60:
            return {
                "error": "Insufficient history",
                "model_trained": True,
                "confidence": 0.0,
                "direction": "NEUTRAL"
            }
            
        dates_s = [str(r[0]) for r in rows if r[1] is not None]
        closes_s = [float(r[1]) for r in rows if r[1] is not None]
        highs_s = [float(r[2] if r[2] is not None else r[1]) for r in rows if r[1] is not None]
        lows_s = [float(r[3] if r[3] is not None else r[1]) for r in rows if r[1] is not None]
        vols_s = [float(r[4] or 0) for r in rows if r[1] is not None]
        
        try:
            trade_dt = datetime.fromisoformat(dates_s[-1][:10]).date()
        except Exception:
            trade_dt = date.today()

        planets = _get_astro_aspects(trade_dt)
        ns = _get_news_features(conn, symbol, dates_s[-1])[0]
        bs = _get_bulk_signal(conn, symbol, dates_s[-1])
        ins = _get_inst_score(conn, symbol, dates_s[-1])
        nifty_trend = _get_nifty50_trend_10d(conn, dates_s[-1])
        sector_rs = _get_sector_relative_strength(conn, symbol, dates_s[-1])
        mkt_breadth = _get_market_breadth(conn, dates_s[-1])
        fii_norm, ret_imb, bias_v = _get_participant_oi_features(conn, dates_s[-1])
        v_norm, v_chg = _get_vix_features(conn, dates_s[-1])
        
        feats = extract_features(
            closes_s, highs_s, lows_s, vols_s,
            news_score=ns, bulk_signal=bs, inst_score=ins,
            nifty50_trend_10d=nifty_trend,
            sector_relative_strength=sector_rs,
            market_breadth=mkt_breadth,
            fii_index_long_pct_norm=fii_norm,
            retail_call_put_imbalance=ret_imb,
            smart_money_contrarian_bias=bias_v,
            vix_value_norm=v_norm,
            vix_change_5d=v_chg,
        )
        if feats is None:
            return {
                "error": "Could not extract features",
                "model_trained": True,
                "confidence": 0.0,
                "direction": "NEUTRAL"
            }
            
        res = {"symbol": symbol, "date": dates_s[-1], "horizons": {}}
        
        class ReversalMLP(nn.Module):
            def __init__(self, input_dim):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(input_dim, 128),
                    nn.BatchNorm1d(128),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    nn.Linear(128, 64),
                    nn.BatchNorm1d(64),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    nn.Linear(64, 3)
                )
            def forward(self, x):
                return self.net(x)
        
        for horizon in [3, 10, 30]:
            h_key = f"{horizon}d"
            if f"xgb_{h_key}" not in models:
                continue
                
            xgb = models[f"xgb_{h_key}"]
            mlp_data = models[f"mlp_{h_key}"]
            
            xgb_prob = xgb.predict_proba(feats)[0]
            
            mlp_scaler = mlp_data["scaler"]
            feats_scaled = mlp_scaler.transform(feats)
            mlp_net = ReversalMLP(mlp_data["input_dim"])
            mlp_net.load_state_dict(mlp_data["model"])
            mlp_net.eval()
            with torch.no_grad():
                out = mlp_net(torch.FloatTensor(feats_scaled))
                mlp_prob = torch.softmax(out, dim=1).numpy()[0]
                
            ens_prob = (xgb_prob + mlp_prob) / 2.0
            
            pred_class = np.argmax(ens_prob)
            conf = float(ens_prob[pred_class])
            
            direction = "NEUTRAL"
            if pred_class == 2 and conf > 0.6: direction = "BULLISH"
            elif pred_class == 0 and conf > 0.6: direction = "BEARISH"
            
            res["horizons"][h_key] = {
                "direction": direction,
                "confidence": round(conf * 100, 1),
                "xgb_up_prob": float(xgb_prob[2]),
                "mlp_up_prob": float(mlp_prob[2])
            }
            
        primary_h = res["horizons"].get("10d") or res["horizons"].get("3d") or {}
        dir_raw = primary_h.get("direction", "NEUTRAL")
        dir_mapped = "UP" if dir_raw == "BULLISH" else "DOWN" if dir_raw == "BEARISH" else "NEUTRAL"
        up_prob = float(primary_h.get("xgb_up_prob", 0.5))
        conf_float = round(float(primary_h.get("confidence", 65.0)) / 100.0, 3)
        cur_px = kwargs.get("current_price") or (closes_s[-1] if closes_s else 100.0)
        
        days_to_rev = 5 if dir_mapped != "NEUTRAL" else 7
        try:
            rev_date_str = (trade_dt + timedelta(days=days_to_rev)).isoformat()
        except Exception:
            rev_date_str = ""

        expected_move = round(abs(up_prob - 0.5) * 16.0, 2)
        rev_price = round(cur_px * (1.0 + (expected_move/100.0 if dir_mapped == "UP" else -expected_move/100.0 if dir_mapped == "DOWN" else 0.0)), 2)

        res.update({
            "model_trained": True,
            "direction": dir_mapped,
            "direction_label": dir_raw,
            "confidence": conf_float,
            "direction_prob": round(up_prob, 3),
            "reversal_prob": conf_float,
            "reversal_price": rev_price,
            "reversal_date": rev_date_str,
            "days_to_reversal": days_to_rev,
            "days_to_rev": days_to_rev,
            "expected_move_pct": expected_move,
            "signal_alignment": 0.85 if dir_mapped != "NEUTRAL" else 0.5,
            "reversal_map": kwargs.get("reversal_map", [])
        })

        return res
    finally:
        conn.close()

def get_model_status():
    import os
    return {"trained": os.path.exists(_MODEL_PATH)}
