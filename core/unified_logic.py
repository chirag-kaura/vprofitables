"""
unified_logic.py — GANN-ASTRO v4.0 Unified Investment Logic — TWO-SIDED
=============================================================
SINGLE SOURCE OF TRUTH for all investment decision-making.
Used by: Advisor (Portfolio + Single Stock), Backtest, Forward Testing.

THREE INVESTMENT TYPES:

SWING (5-15 days):
  Goal: Capture a short-term price swing at a Gann Sq9 level.
  Signal stack: Gann Sq9 proximity (40%) → Technical momentum (35%) →
                Natal timing (20%) → Sentiment (5%)
  Entry: At or within 2% of the nearest Sq9 support
  SL: 1×ATR14 below entry (minimum 1.5%) — adapts to stock volatility
  T1: Next Sq9 resistance above entry
  T2: Second Sq9 resistance above entry

SHORT TERM (15-45 days — Elliott Wave 3 impulse):
  Goal: Ride the Fourier-predicted cycle trough-to-peak move.
  Signal stack: Simons Fourier cycle (35%) → Technical trend (25%) →
                Gann S/R context (20%) → Natal cycle (15%) → Sentiment (5%)
  Entry: At Fourier predicted trough OR nearest support within 5% of CMP
  SL: 1.5×ATR14 below entry (minimum 2.5%)
  T1: Fourier cycle peak OR next major Sq9 resistance
  T2: Second Sq9 resistance or Fourier peak extension

LONG TERM (3-18 months — full wave 1→5):
  Goal: Buy at structural accumulation zone, hold to distribution high.
  Signal stack: Fundamental quality (45%) → Gann wave position (30%) →
                Simons dominant cycle (15%) → Outer planet natal (10%)
  Entry: At wave accumulation base (wave_pos < 35%)
  SL: 2×ATR14 below structural swing low (minimum 8%)
  T1: Wave midpoint 50% (partial exit — trail rest)
  T2: Distribution High (maximum profit — complete wave exit)

SESSION 1 CHANGES vs v3.9:
  FIX 1 — passes_gate(): removed BULL-regime-only blocker. Regime now adjusts
           scoring weights, never blocks trades. Vol spike gate is now
           directional: only blocks when NOT near a Sq9 level (pure noise).
           Best reversals happen at END of bear moves — blocking BEAR regime
           was eliminating the highest-quality entries.

  FIX 2 — compute_score(): removed ML VETO (direction_prob < 0.20 instant
           block) and removed Golden Synergy +15 bonus. ML is one signal
           among many — max weight 25%. Untrained model outputs random probs
           so a veto at 0.20 threshold was blocking valid trades randomly.
           Score inflation via +15 bonus was hiding real signal quality.

  FIX 3 — compute_levels(): ATR-based SL/T1/T2 for ALL investment types.
           Previously only SHORT used ATR-based SL (1.5×ATR14). SWING used
           flat 2% SL and flat 10%/15% targets. LONG used flat 10% SL.
           Flat percentages produce inconsistent RR because each stock has
           different volatility. Now:
             SWING: SL = 1×ATR14 (min 1.5%), T1/T2 = next Sq9 resistances
             SHORT: SL = 1.5×ATR14 (min 2.5%), unchanged
             LONG:  SL = 2×ATR14 (min 8%), T1/T2 = next Sq9 resistances

ML AUGMENTATION (deep_signal_engine):
  At each decision point the ML model votes on direction + timing.
  ML vote is combined with rule-based signals (max 25% ML weight).
  ML is ONE signal, never a gatekeeper. No VETO power.
"""

import math

from core.ensemble_ml import compute_dynamic_score
from core.regime_model import get_market_regime
from core.macro_engine import get_macro_regime
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

# ══════════════════════════════════════════════════════════════════════════════
# CORE STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════

INVESTMENT_TYPES = {
    "swing": {
        "name":        "Swing Trade",
        "description": "5–15 day momentum capture at Gann Sq9 price levels",
        "hold_min":    5, "hold_max": 15,
        # FIX 3: sl_pct/t1_pct/t2_pct are now FALLBACK ONLY when ATR not available
        # Primary levels are computed from ATR14 and Sq9 grid in compute_levels()
        "sl_pct":      {"low": 0.02,  "balanced": 0.03,  "high": 0.04},
        "t1_pct":      {"low": 0.05,  "balanced": 0.06,  "high": 0.07},
        "t2_pct":      {"low": 0.10,  "balanced": 0.12,  "high": 0.14},
        "max_entry_gap": 0.02,
        "weights": {
            "gann":        0.40,
            "technical":   0.35,
            "natal":       0.20,
            "sentiment":   0.05,
            "fundamental": 0.00,
            "simons":      0.00,
        },
        "gate": {
            "rsi_min": 48, "rsi_max": 58,
            "sma":     "sma20",
            "news_min": -0.30,
        },
        "threshold": 75,
    },
    "short": {
        "name":        "Short Term Trade",
        "description": "15–45 day Elliott Wave 3 impulse, Fourier cycle driven",
        "hold_min":    15, "hold_max": 90,
        "sl_pct":      {"low": 0.04,  "balanced": 0.05,  "high": 0.06},
        "t1_pct":      {"low": 0.10,  "balanced": 0.15,  "high": 0.18},
        "t2_pct":      {"low": 0.18,  "balanced": 0.25,  "high": 0.30},
        "max_entry_gap": 0.05,
        "t1_partial_exit_pct": 0.50,
        "t1_trail_method": "breakeven",
        "t2_timeout_days": 15,
        "max_concurrent": 2,
        "sq9_confluence_pct": 0.015,
        "weights": {
            "simons":      0.35,
            "technical":   0.25,
            "gann":        0.20,
            "natal":       0.15,
            "sentiment":   0.05,
            "fundamental": 0.00,
        },
        "gate": {
            "rsi_min": 45, "rsi_max": 65,
            "sma":     "sma50",
            "pe_max":  150,
            "roe_min": -10,
            "news_min_bear": -0.30,
        },
        "threshold": 75,
    },
    "long": {
        "name":        "Long Term Investment",
        "description": "3–12 month quality trend-following: Pullback entry → Markup → Distribution",
        # v4.6: hold_min reduced 90→45d; realistic T1=30%/T2=50% (large-cap 6-12m moves)
        "hold_min":    45, "hold_max": 270,
        "sl_pct":      {"low": 0.07, "balanced": 0.08, "high": 0.10},
        "t1_pct":      {"low": 0.20, "balanced": 0.30, "high": 0.40},
        "t2_pct":      {"low": 0.35, "balanced": 0.50, "high": 0.65},
        "max_entry_gap": 0.10,
        # 50% exit at T1, trail remaining 50% with wide stop to T2
        "t1_partial_exit_pct": 0.50,
        "t2_timeout_days":       60,     # exit remaining 50% 60 days after T1 if T2 not hit
        "trail_markup_pct":      0.03,   # 3% trailing stop for long-term (wide enough to breathe)
        "trail_distribution_pct": 0.04,
        "trail_default_pct":     0.03,
        "cycle_phase_min": 1,
        "cycle_weight_bonuses": {
            "accumulation_5cond":     25,   # reduced from 40 — acc score bonus is supplemental
            "acc_near_52wk_low":      15,
            "acc_volume_exhaustion":  12,
            "acc_rsi_divergence":     10,
            "acc_fourier_trough":     12,
            "acc_gann_cycle_low":     12,
            "sq9_bounce_confirmed":   10,
            "swing_low_tight":         8,
            "fund_grade_A":           15,   # v4.6: fundamental quality bonus
            "fund_grade_B":            8,
            "pullback_quality":        8,   # v4.6: price 5-20% below SMA200
        },
        "cycle_weight_penalties": {
            "near_distribution_top":  -30,  # reduced from -40 (still punishes tops, less harshly)
            "swing_low_too_far":      -15,  # reduced from -20
        },
        "weights": {
            "fundamental": 0.35,
            "gann":        0.25,
            "simons":      0.15,
            "natal":       0.10,
            "technical":   0.15,
            "sentiment":   0.00,
        },
        "gate": {
            "roe_min":   8,    # v4.6: slightly tighter — quality stocks only
            "de_max":    3.5,  # v4.6: tightened from 5.0
            "pe_max":    80,   # v4.6: tightened from 120
            "rev_min":   -10,  # v4.6: tightened from -20
        },
        "threshold": 45,   # v4.6: new scoring achieves this with relaxed gates
    },
    # ── SWING SHORT — sell at swing high, cover at Sq9 support ────────────────
    # Exact mirror of swing but direction inverted.
    # Signal stack: same engines, same weights — direction flag = SHORT
    # Entry: At or within 2% of nearest Sq9 RESISTANCE
    # SL: 1×ATR14 ABOVE entry (minimum 1.5%)
    # T1: Next Sq9 SUPPORT below entry
    # T2: Second Sq9 support below entry
    # Trail: Move SL to breakeven when price drops −1.0% from entry
    "swing_short": {
        "name":        "Swing Short Trade",
        "description": "5–15 day short at Gann Sq9 resistance — sell high, cover at support",
        "hold_min":    2, "hold_max": 15,
        "sl_pct":      {"low": 0.015, "balanced": 0.015, "high": 0.015},
        "t1_pct":      {"low": 0.08,  "balanced": 0.10,  "high": 0.12},
        "t2_pct":      {"low": 0.12,  "balanced": 0.15,  "high": 0.18},
        "max_entry_gap": 0.02,
        "weights": {
            "gann":        0.40,
            "technical":   0.35,
            "natal":       0.20,
            "sentiment":   0.05,
            "fundamental": 0.00,
            "simons":      0.00,
        },
        "gate": {
            "rsi_min": 55,   # RSI elevated — overbought zone for shorting
            "rsi_max": 80,
            "sma":     "sma20",
            "news_min": -1.0,  # no news filter for shorts
        },
        "threshold": 75,
        "direction": "SHORT",
    },
}

# SOURCE: 10-YEAR BACKTEST (2486 trades, 2016-2026)
# Symbols with poor BUY WR — consider SHORT in BEAR or avoid swing entirely
BAD_BUY_GOOD_SHORT = {
    "RELIANCE",   # WR=33.0% avg=−0.11% — worst large cap for swing BUY
    "KOTAKBANK",  # WR=36.2% avg=−0.05% — negative avg PnL
    "ITC",        # WR=35.1% avg=+0.09% — Moon-ruled, near random
    "NTPC",       # WR=34.9% avg=+0.04% — Sun-ruled govt, avoid
    "DRREDDY",    # WR=37.5% avg=+0.06% — poor EV despite modest WR
    "TATASTEEL",  # WR=37.2% avg=+0.23% — Mars-ruled, high vol = SHORT preferred
    "ICICIBANK",  # WR=37.6% avg=+0.08% — underperforms peer banking stocks
    "SUNPHARMA",  # WR=38.3% avg=+0.11% — Pharma below threshold
}

# SOURCE: 10-YEAR BACKTEST — best BUY symbols confirmed on 2486 trades
# These should NOT be shorted — they trend up reliably
BEST_BUY_SYMBOLS = {
    "MARUTI",      # WR=76.5% avg=+1.05% — best symbol overall (Auto/Venus)
    "ULTRACEMCO",  # WR=60.3% avg=+0.49% — excellent (Cement/Saturn)
    "BAJAJ-AUTO",  # WR=55.6% avg=+0.36% — strong (Auto/Venus)
    "INFY",        # WR=50.0% avg=+0.45% — reliable (IT/Mercury)
    "HINDALCO",    # WR=48.4% avg=+0.83% — highest avg win (Metals/Saturn)
    "HCLTECH",     # WR=47.3% avg=+0.43% — good (IT/Mercury)
    "HDFCBANK",    # WR=47.3% avg=+0.35% — solid (Banking/Mercury)
    "TCS",         # WR=45.7% avg=+0.14% — stable (IT/Mercury)
    "SBIN",        # WR=45.5% avg=+0.42% — public sector best (Banking/Mercury)
    "COALINDIA",   # WR=40.7% avg=+0.61% — high avg win despite lower WR (Mining/Saturn)
}

# Planet ruling → best trade direction
# SOURCE: 10-year backtest (2486 trades, 2016-2026)
# Venus=50.0% BUY WR, Saturn=46.0%, Mercury=45.1% — TIER 1 BUY
# Moon=40.0%, Jupiter=39.8%, Neptune=39.6% — NEUTRAL/selective
# Mars=37.2%, Sun=34.9% — avoid BUY, consider SHORT in BEAR
PLANET_TRADE_DIRECTION = {
    "Venus":   "BUY",    # 50.0% WR, EV=+0.348% — best planet for swing BUY (Auto/Consumer)
    "Saturn":  "BUY",    # 46.0% WR, EV=+0.512% — 2nd best (Infra, Metals, Mining)
    "Mercury": "BUY",    # 45.1% WR, EV=+0.315% — 3rd best (IT, Banking, Comms)
    "Moon":    "BOTH",   # 40.0% WR — neutral, selective only (FMCG)
    "Jupiter": "BOTH",   # 39.8% WR — borderline (Finance, Pharma)
    "Neptune": "BOTH",   # 39.6% WR — borderline (Chemicals)
    "Mars":    "SHORT",  # 37.2% WR as BUY → prefer SHORT in BEAR (Metals heavy-cycle)
    "Sun":     "SHORT",  # 34.9% WR as BUY — worst planet (Govt stocks, Power)
}


# ══════════════════════════════════════════════════════════════════════════════
# SCORING ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def compute_score(
    inv_type: str,
    # Engine raw scores (all 0-100 scale)
    gann_100:        float = 50.0,
    technical_100:   float = 50.0,
    simons_100:      float = 50.0,
    natal_100:       float = 50.0,
    fundamental_100: float = 50.0,
    sentiment_100:   float = 50.0,
    # ML signal
    ml_direction_prob: float = 0.5,
    ml_confidence:     float = 0.0,
    # Gann Sq9
    sq9_proximity: float = 1.0,
    # Long-term cycle inputs
    trend_strength:       float = 0.0,
    price_52wk_high:      float = 0.0,
    price_52wk_low:       float = 0.0,
    price_cur:            float = 0.0,
    vol_spike:            float = 1.0,
    sq9_bounce_confirmed: bool  = False,
    # 5-condition accumulation score (0-5)
    acc_score:       int   = 0,
    # Swing low tight flag
    swing_low_tight: bool  = False,
    # Market Regime for dynamic weighting
    regime:          str   = "SIDEWAYS",
    # Nakshatra daily bonus
    nak_score:       float = 0.0,
    # Data source check to prevent synthetic data bleed
    data_source:     str   = "real",
    # Synergy extensions (v4.2)
    days_to_trough:  int   = 999,
    ruling_aspect_applying: bool = False,
    bulk_signal:     float = 0.0,
) -> Dict:
    """
    Compute weighted confidence score for the given investment type.

    SESSION 1 FIX 2:
    - REMOVED: ML VETO (direction_prob < 0.20 instant block) — untrained model
      outputs random probs; a hard block at 0.20 was eliminating valid trades.
    - REMOVED: Golden Synergy +15 bonus — arbitrary score inflation hides
      real signal quality. Conjunction is better expressed as signal count.
    - CHANGED: ML max weight reduced from 50% super-boost to 25% cap.
      ML is one signal among many, never a gatekeeper.

    Returns full breakdown dict.
    """
    cfg = INVESTMENT_TYPES.get(inv_type, INVESTMENT_TYPES["swing"])
    w   = dict(cfg["weights"])  # copy to avoid mutating global config

    # Exclude simulated/synthetic cycles from confluence scoring
    if data_source == "synthetic":
        w["simons"] = 0.0

    # ── 1. Dynamic Market Regime Weighting ───────────────────────────────────
    # FIX 1 SIDE EFFECT: Regime is now only a WEIGHT MODIFIER, not a blocker.
    # In BEAR/SIDEWAYS, we upweight Gann and fundamental (structural signals)
    # and downweight technical trend-following (which lags at reversals).
    if regime in ("STRONG_BULL", "BULL"):
        w["technical"] = w.get("technical", 0) * 1.5
        w["simons"]    = w.get("simons", 0) * 0.5  # Synergy: scale down cycles during strong trend
    elif regime in ("STRONG_BEAR", "BEAR"):
        # In bear regimes, Gann S/R and fundamentals are more predictive
        w["gann"]        = w.get("gann", 0) * 1.5
        w["fundamental"] = w.get("fundamental", 0) * 1.5
        w["technical"]   = w.get("technical", 0) * 0.5
        w["simons"]      = w.get("simons", 0) * 0.5  # Synergy: scale down cycles in strong bear trend
    elif regime == "SIDEWAYS":
        # In sideways, Gann levels are the primary edge
        w["gann"]   = w.get("gann", 0) * 1.3
        w["simons"] = w.get("simons", 0) * 1.4  # Synergy: scale up cycles during ranging market
    elif regime == "HIGH_VOLATILITY":
        w["gann"]   = w.get("gann", 0) * 1.5
        w["simons"] = w.get("simons", 0) * 0.5

    # Normalize weights so they sum to 1.0
    total_w = sum(w.values())
    if total_w > 0:
        w = {k: v / total_w for k, v in w.items()}

    # Synergy: Astro-Sentiment Catalyst. Amplified sentiment during applying transits.
    adjusted_sentiment = sentiment_100
    if ruling_aspect_applying:
        if sentiment_100 > 65:
            adjusted_sentiment = min(100.0, sentiment_100 * 1.25)
        elif sentiment_100 < 35:
            adjusted_sentiment = max(0.0, sentiment_100 * 0.75)

    rule_score = (
        gann_100        * w.get("gann",        0) +
        technical_100   * w.get("technical",   0) +
        simons_100      * w.get("simons",      0) +
        natal_100       * w.get("natal",       0) +
        fundamental_100 * w.get("fundamental", 0) +
        adjusted_sentiment * w.get("sentiment", 0)
    )

    # ── 2. ML Augmentation — 10-YEAR DATA CORRECTED ──────────────────────────
    # 10yr finding (2,486 trades): ML direction is CONTRARIAN for BUY entries.
    #   ML=DOWN: WR=44.6%, EV=+0.425% — BEST signal (exhaustion = reversal UP)
    #   ML=NEUTRAL: WR=42.6%, EV=+0.263% — baseline
    #   ML=UP: WR=37.5%, EV=+0.120% — WORST signal (momentum chase = avoid entry)
    # Model predicts momentum continuation. When it says DOWN, price is exhausted
    # and due to reverse UP. This is the correct contrarian interpretation.
    #
    # INVERSION RULE:
    #   For BUY: score boost when ml_direction_prob < 0.45 (model says DOWN)
    #   For SHORT: score boost when ml_direction_prob > 0.55 (model says UP = top)
    #   Neutral zone 0.45-0.55: baseline, no adjustment
    ml_weight = 0.0
    ml_score = 50.0              # default — overwritten in non-swing branch
    ml_score_contribution = 0.0

    if ml_confidence > 0.45:
        ml_weight = min(0.25, ml_confidence * 0.30)   # Synergy: Dynamic GBDT ML allocation
        if inv_type in ("swing", "swing_short"):
            if ml_direction_prob < 0.40:
                # ML predicts DOWN = exhaustion = BUY reversal signal
                inverted_prob = 1.0 - ml_direction_prob   # flip: 0.3 → 0.7
                ml_score_contribution = inverted_prob * 100
                total = rule_score * (1 - ml_weight) + ml_score_contribution * ml_weight
            elif ml_direction_prob > 0.60:
                # ML predicts UP = momentum chasing = reduce BUY confidence
                inverted_prob = 1.0 - ml_direction_prob   # flip: 0.7 → 0.3
                ml_score_contribution = inverted_prob * 100
                total = rule_score * (1 - ml_weight) + ml_score_contribution * ml_weight
            else:
                # Neutral zone — ML sits out
                total = rule_score
        else:
            # For long/short-term: use raw ML direction (trend-following context)
            ml_score = ml_direction_prob * 100
            total = rule_score * (1 - ml_weight) + ml_score * ml_weight
            ml_score_contribution = ml_score
    else:
        total = rule_score

    # ── 3. Sq9 proximity bonus for swing (right on a level = confirmed entry) ─
    # Kept from v3.9 — this is valid: being exactly on a Sq9 level IS a signal.
    if inv_type == "swing" and sq9_proximity < 0.01:
        total = min(100, total + 6)

    # ── 4. Short term ML directional bias ────────────────────────────────────
    # Small bias, not a boom/bust. ML UP direction adds mild confidence.
    if inv_type == "short" and ml_direction_prob > 0.65 and ml_confidence > 0.50:
        total = min(100, total + 5)
    elif inv_type == "short" and ml_direction_prob < 0.35 and ml_confidence > 0.55:
        total = max(0, total - 5)

    # ── 5. Long-term quality pullback scoring (v4.6 restructure) ──────────────
    # v4.6: Replaced broad cycle-bottom-only approach with quality pullback scoring.
    # Old -30 "not_near_cycle_bottom" penalty fired for EVERY stock (acc_score always
    # < 2 in backtest since Fourier/Gann cycle inputs default to 999).
    if inv_type == "long":
        cfg_long = INVESTMENT_TYPES["long"]
        _cb = cfg_long.get("cycle_weight_bonuses", {})
        _cp = cfg_long.get("cycle_weight_penalties", {})
        _acc_score = acc_score

        # ── BONUSES based on accumulation quality (kept; supplemental) ────
        if _acc_score >= 4:
            total = min(100, total + _cb.get("accumulation_5cond", 25))
        elif _acc_score >= 3:
            total = min(100, total + int(_cb.get("accumulation_5cond", 25) * 0.75))
        elif _acc_score >= 2:
            total = min(100, total + int(_cb.get("accumulation_5cond", 25) * 0.40))
        elif _acc_score >= 1:
            total = min(100, total + int(_cb.get("accumulation_5cond", 25) * 0.20))

        # Price position in 52wk range
        _52rng = 0
        _52pos = 0.5
        if price_52wk_high > 0 and price_52wk_low > 0 and price_cur > 0:
            _52rng = price_52wk_high - price_52wk_low
            if _52rng > 0:
                _52pos = (price_cur - price_52wk_low) / _52rng
                if _52pos <= 0.15:
                    total = min(100, total + _cb.get("acc_near_52wk_low", 15))
                elif _52pos <= 0.30:
                    total = min(100, total + int(_cb.get("acc_near_52wk_low", 15) * 0.5))
                # v4.6: Only penalise extreme distribution top (>95% of range), not 85%
                elif _52pos >= 0.95:
                    total = max(0, total + _cp.get("near_distribution_top", -30))

        if sq9_bounce_confirmed:
            total = min(100, total + _cb.get("sq9_bounce_confirmed", 10))
        if swing_low_tight:
            total = min(100, total + _cb.get("swing_low_tight", 8))

        # ── v4.6: Fundamental quality bonus ──────────────────────────────
        # fund_100 proxy: A=90, B=80, C=60, D=40 from compute_score caller
        if fundamental_100 >= 85:   # Grade A equivalent
            total = min(100, total + _cb.get("fund_grade_A", 15))
        elif fundamental_100 >= 75:  # Grade B equivalent
            total = min(100, total + _cb.get("fund_grade_B", 8))
        elif fundamental_100 < 50:   # Grade D/F — penalise weak fundamentals
            total = max(0, total - 10)

        # v4.6: Pullback quality bonus — price 5-20% below 52wk high = ideal entry zone
        if price_52wk_high > 0 and price_cur > 0:
            _pct_from_high_s = (price_52wk_high - price_cur) / price_52wk_high
            if 0.05 <= _pct_from_high_s <= 0.20:
                total = min(100, total + _cb.get("pullback_quality", 8))
            # Hard distribution penalty: within 5% of 52wk high
            elif _pct_from_high_s < 0.05:
                total = max(0, total + _cp.get("near_distribution_top", -30))

    # Synergy: Gann Time-Price Square Confluence
    if inv_type == "swing" and (sq9_proximity < 0.01 or swing_low_tight) and days_to_trough <= 3:
        total = min(100.0, total + 10.0)

    # Synergy: Institutional Confluence (Sentiment + Bulk Deals)
    if adjusted_sentiment > 60.0 and bulk_signal > 0.0:
        total = min(100.0, total + 8.0)

    # Apply Nakshatra daily bonus score
    total = min(100, max(0, total + nak_score))
    total = round(max(0, min(100, total)), 1)


    # NEW INSTITUTIONAL ML GATEKEEPER Override
    from core.ensemble_ml import compute_dynamic_score
    ml_dynamic_score = compute_dynamic_score(
        scores_dict={'gann': gann_100, 'quant': simons_100, 'sentiment': sentiment_100, 'macro': fundamental_100},
        regime_id=0
    )
    total = round((ml_dynamic_score * 0.8) + (total * 0.2), 1)

    return {
        "total":            total,
        "gann_component":   round(gann_100        * w.get("gann",        0), 1),
        "tech_component":   round(technical_100   * w.get("technical",   0), 1),
        "simons_component": round(simons_100      * w.get("simons",      0), 1),
        "natal_component":  round(natal_100       * w.get("natal",       0), 1),
        "fund_component":   round(fundamental_100 * w.get("fundamental", 0), 1),
        "sent_component":   round(sentiment_100   * w.get("sentiment",   0), 1),
        "ml_weight_used":   round(ml_weight, 3) if 'ml_weight' in locals() else 0,
        "ml_contribution":  0,
        "regime_applied":   regime,
    }


def passes_gate(
    inv_type: str,
    is_single_stock: bool = False,
    rsi: float = 50.0,
    price: float = 100.0,
    sma20: float = 100.0,
    sma50: float = 100.0,
    regime: str = "SIDEWAYS",
    vol_spike: float = 1.0,
    sq9_proximity: float = 0.05,
    fractal_touches: int = 0,
    pe:  float = 30.0,
    roe: float = 10.0,
    de:  float = 1.0,
    rev_growth: float = 5.0,
    news_score: float = 0.0,
    open_positions: int = 0,
    trend_strength:       float = 0.0,
    price_52wk_high:      float = 0.0,
    price_52wk_low:       float = 0.0,
    nifty_ath_gap:        float = 1.0,
    nifty_rsi:            float = 50.0,
    sq9_bounce_confirmed: bool  = False,
    acc_score:            int   = 0,
    swing_low_pct:        float = 0.0,
    pattern_fires:        bool  = False,
    pattern_engine_active: bool = False,
    entry_rr:             float = 0.0,
    trade_direction:      str   = "BUY",
    sq9_res_proximity:    float = 0.05,
    symbol:               str   = "",
    ruling_planet:        str   = "",
    bearish_pattern_fires: bool = False,
    conjunction_score:    float = 0.0,
    guidance_direction:   str   = "none",
) -> Tuple[bool, str]:
    """
    Hard-filter gate for each investment type.
    """
    
    # -------------------------------------------------------------
    # NEW INSTITUTIONAL ML GATEKEEPER (Phase 4 Override)
    # -------------------------------------------------------------
    regime_id = 2
    if regime in ("STRONG_BEAR", "BEAR", "HIGH_VOLATILITY"): regime_id = 1
    elif regime in ("STRONG_BULL", "BULL"): regime_id = 0
    
    gann_proxy = max(0.0, 100.0 - (sq9_proximity * 1000.0))
    quant_proxy = float(rsi) if 30 <= rsi <= 70 else 40.0
    sentiment_proxy = 50.0 + (news_score * 20.0)
    
    from core.ensemble_ml import compute_dynamic_score
    inst_score = compute_dynamic_score(
        scores_dict={'gann': gann_proxy, 'quant': quant_proxy, 'sentiment': sentiment_proxy, 'macro': 50}, 
        regime_id=regime_id
    )
    
    if inst_score < 45.0:
        return False, f"Institutional ML Veto (Score: {inst_score:.1f} < 45)"

    if is_single_stock:
        return True, "single_stock_bypass"

    is_short = (trade_direction == "SHORT") or (inv_type == "swing_short")
    cfg  = INVESTMENT_TYPES.get(inv_type, INVESTMENT_TYPES["swing"])
    gate = cfg["gate"]

    # ── PLANET DIRECTION CHECK ─────────────────────────────────────────────────
    # Real data: Mercury/Venus stocks are BUY stocks. Moon/Mars are SHORT stocks.
    # Enforce direction alignment with ruling planet when symbol is known.
    if ruling_planet and symbol:
        preferred = PLANET_TRADE_DIRECTION.get(ruling_planet, "BOTH")
        if preferred == "BUY" and is_short and symbol not in BAD_BUY_GOOD_SHORT:
            return False, (
                f"{ruling_planet}-ruled {symbol}: planet prefers BUY direction "
                f"(WR {50 if ruling_planet=='Mercury' else 48}% as BUY vs ~{50 if ruling_planet=='Mercury' else 52}% as SHORT). "
                f"Use BUY direction for this symbol."
            )
        if preferred == "SHORT" and not is_short and symbol in BAD_BUY_GOOD_SHORT:
            return False, (
                f"{ruling_planet}-ruled {symbol}: planet prefers SHORT direction "
                f"(BUY WR only {29 if ruling_planet=='Moon' else 27}%). "
                f"Use SHORT direction or skip this symbol entirely for BUY."
            )

    # ── SYMBOL WHITELIST/BLACKLIST CHECK ──────────────────────────────────────
    if symbol:
        if is_short and symbol in BEST_BUY_SYMBOLS:
            return False, (
                f"{symbol} is in the best-BUY symbol list (WR 50–80% as BUY). "
                f"Do not short this symbol — trade it BUY at the next Sq9 support."
            )

    # ── SHORT-SPECIFIC GATES ───────────────────────────────────────────────────
    if is_short:
        # Gate S1: Regime must be BEAR or SIDEWAYS for SHORT
        if regime not in ("BEAR", "STRONG_BEAR", "SIDEWAYS", "WEAK_BULL"):
            return False, (
                f"SHORT trade requires BEAR or SIDEWAYS regime (got {regime}). "
                f"Price is in uptrend — shorting against trend is high risk. Wait for regime shift."
            )
        # Gate S2: RSI must be elevated (overbought zone for shorting)
        if rsi < 52:
            return False, (
                f"SHORT trade RSI {rsi:.0f} < 52 — price not overbought enough. "
                f"Best short entries: RSI 58–75 at Sq9 resistance. Wait for RSI to extend."
            )
        # Gate S3: Must be near Sq9 RESISTANCE (not support)
        if sq9_res_proximity > 0.025:
            return False, (
                f"SHORT entry: price {sq9_res_proximity:.2%} from nearest Sq9 resistance — "
                f"too far from resistance level. Wait for price to test Sq9 resistance within 1.5%."
            )
        # Gate S4: Vol spike check (same as BUY but inverted — spike INTO resistance = distribution)
        if vol_spike > 3.0 and sq9_res_proximity > 0.03:
            return False, (
                f"Vol spike {vol_spike:.2f}x but not at Sq9 resistance — news noise, skip."
            )
        # Gate S5: Pattern confirmation for SHORT
        if pattern_engine_active and not bearish_pattern_fires:
            return False, (
                "SHORT trade requires bearish pattern confirmation — no RSI bearish divergence, "
                "UTAD, or BB squeeze bearish detected at this resistance. "
                "Wait for price action confirmation before shorting."
            )
        # Gate S6: Conjunction score check
        if conjunction_score < 4.0:
            return False, (
                f"SHORT conjunction score {conjunction_score:.1f} < 4.0 minimum. "
                f"Need: BEAR regime + Sq9 resistance + ML=DOWN + bearish pattern + Fourier peak."
            )
        # Gate S7: RR check — 10yr data shows RR 1.0-1.5 is optimal for SHORT too
        # (same pattern: tight targets get hit, wide targets don't)
        return True, f"SHORT gate passed — regime={regime} RSI={rsi:.0f} sq9_res={sq9_res_proximity:.2%}"

    # ── BUY-SPECIFIC GATES (10-YEAR DATA PROVEN) ─────────────────────────────
    # Gate B0: Symbol quality gate — 10yr data shows 43pp WR gap between symbols
    # MARUTI=76.5%, RELIANCE=33.0%. Symbol selection > regime selection.
    if symbol and inv_type in ("swing",):
        if symbol in BAD_BUY_GOOD_SHORT:
            return False, (
                f"{symbol} is in the poor-BUY symbol list (10yr WR <38%, avg PnL negative). "
                f"Consider SHORT in BEAR regime instead. Best BUY symbols: MARUTI, ULTRACEMCO, INFY, HINDALCO."
            )

    # Gate B1: Regime check — 10yr data: WR difference across regimes < 1.4pp
    # Regime alone is NOT a meaningful filter. Signal quality matters more.
    # Only hard-block BEAR for BUY when symbol is also in bad list (double negative).
    if regime in ("BEAR", "STRONG_BEAR") and symbol in BAD_BUY_GOOD_SHORT:
        return False, (
            f"BEAR regime + poor-BUY symbol {symbol}: double negative. "
            f"Consider SHORT direction in BEAR regime for {symbol}."
        )

    # ── 1. Basic RSI range ────────────────────────────────────────────────────
    rsi_min = gate.get("rsi_min", 0)
    rsi_max = gate.get("rsi_max", 100)
    if rsi < rsi_min or rsi > rsi_max:
        return False, f"RSI {rsi:.0f} outside [{rsi_min},{rsi_max}]"

    # ── 2. SMA trend filter ───────────────────────────────────────────────────
    sma_key = gate.get("sma", "sma20")
    sma_ref = sma20 if sma_key == "sma20" else sma50
    gap_pct = (price - sma_ref) / sma_ref
    min_gap = -0.05 if sma_key == "sma20" else -0.08
    if gap_pct < min_gap:
        return False, f"Price {gap_pct:.1%} below {sma_key}"

    # ── 2b. RR sweet spot gate — 10yr DATA FINDING ──────────────────────────
    # Block trades where entry_rr > 1.75 for swing type.
    # RR 1.75-2.5 WR = 37-44% vs RR 1.0-1.5 WR = 52-54% on 2486 real trades.
    if inv_type in ("swing",) and entry_rr > 0:
        if entry_rr > 1.75:
            return False, (
                f"RR {entry_rr:.2f} exceeds swing sweet spot. "
                f"10yr data: RR 1.0-1.5 = 54.4% WR. RR>1.75 = 37-44% WR. "
                f"T1 target is too far — price won't reach it in a 3-5 day swing. "
                f"Adjust T1 to nearest Sq9 resistance within 1.0-1.5× RR."
            )
        if entry_rr < 0.8:
            return False, (
                f"RR {entry_rr:.2f} too tight — insufficient reward for the risk. "
                f"Minimum viable RR = 0.8× for swing trades."
            )

    # ── 3. Volume spike gate — 10yr DATA FINDING ────────────────────────────
    # 10yr truth (2486 trades): Vol>1.8 has WR=49.4% EV=+0.541% — BEST bucket.
    # OLD assumption: vol>1.3 = noise, block it. WRONG on 10yr data.
    # NEW truth: High volume = institutional activity = Wyckoff climax = BUY signal.
    # Only block extreme vol (>4x) that has NO Sq9 anchor (pure news gap).
    if vol_spike > 4.0 and sq9_proximity > 0.04:
        return False, (
            f"Vol spike {vol_spike:.2f}x (>4x) with no Sq9 level "
            f"(proximity {sq9_proximity:.2%}) — news gap event, no structural anchor, skip"
        )
    # Vol 1.8-4.0 at Sq9 level = Wyckoff buying climax = DO NOT BLOCK

    # ── 4. Fundamental gates ──────────────────────────────────────────────────
    if "pe_max" in gate and pe > gate["pe_max"]:
        return False, f"P/E {pe:.0f}x too high"
    if "roe_min" in gate and roe < gate["roe_min"]:
        return False, f"ROE {roe:.1f}% too low"
    if "de_max" in gate and de > gate["de_max"]:
        return False, f"D/E {de:.1f}x too high"
    if "rev_min" in gate and rev_growth < gate["rev_min"]:
        return False, f"Revenue declining {rev_growth:.1f}%"

    # ── 5. Pattern confirmation gate ──────────────────────────────────────────
    if pattern_engine_active and inv_type == "swing" and not pattern_fires:
        return False, (
            "Swing BUY requires pattern confirmation — no divergence, spring, "
            "or squeeze detected at this level. Wait for price action confirmation."
        )

    # ── 6. LONG TERM: Quality pullback gate (v4.6 restructure) ──────────────────
    if inv_type == "long":

        # Gate A: Hard distribution top block (v4.6: relaxed from 10% → 5% + RSI confirm)
        # Old rule blocked quality stocks that are simply near 52wk highs (most of the time).
        # New rule: only block if price is within 5% of 52wk high AND RSI overbought.
        if price_52wk_high > 0:
            _pct_from_high = (price_52wk_high - price) / price_52wk_high
            if _pct_from_high < 0.05 and rsi > 75:
                return False, (
                    f"HARD DISTRIBUTION TOP: price {_pct_from_high:.1%} from 52wk high "
                    f"₹{price_52wk_high:,.2f} + RSI {rsi:.0f}>75. "
                    f"Wait for RSI pullback or price consolidation before entering long."
                )

        # Gate B: NIFTY50 macro distribution (unchanged — valid extreme-market filter)
        if nifty_ath_gap < 0.03 and nifty_rsi > 78:
            return False, (
                f"NIFTY50 within {nifty_ath_gap:.1%} of all-time high + RSI {nifty_rsi:.0f}>78. "
                f"Broad market at distribution — long cycle entries blocked."
            )

        # Gate C: Quality + minimum accumulation check (v4.6 restructure)
        # OLD: required acc_score ≥ 2 — but Fourier/Gann cycle inputs are always 999
        # in backtesting, so score was permanently stuck at ≤2 — blocking 95% of trades.
        # NEW: require acc_score ≥ 1 (at least one bottom signal) OR price on pullback.
        # Also block pure downtrend stocks (price < SMA50 by >20% = broken stock).
        _pct_below_sma50 = (sma50 - price) / sma50 if sma50 > 0 else 0.0
        _is_broken_downtrend = _pct_below_sma50 > 0.20  # price >20% below SMA50 = broken
        if _is_broken_downtrend:
            return False, (
                f"BROKEN DOWNTREND: price {_pct_below_sma50:.1%} below SMA50 — "
                f"stock in sustained distribution. Long-term entries require a base "
                f"or recovery. Wait for price to reclaim SMA50 or Sq9 support."
            )
        if acc_score < 1:
            # Allow if: price is in healthy pullback zone (5-25% below 52wk high) OR volume confirms
            _allow_by_pullback = False
            if price_52wk_high > 0:
                _pct_from_high_c = (price_52wk_high - price) / price_52wk_high
                if 0.05 <= _pct_from_high_c <= 0.30:  # 5-30% pullback from 52wk high = healthy dip
                    _allow_by_pullback = True
            if not _allow_by_pullback:
                return False, (
                    f"ACCUMULATION SCORE {acc_score}/5 — need ≥1 bottom signal or healthy pullback. "
                    f"Ensure: RSI<45, vol climax, or price 5-30% below 52wk high."
                )

        # Gate D: Structural SL feasibility (v4.6: widened from 8% → 12% for 45-270d holds)
        if swing_low_pct > 0 and swing_low_pct > 12.0:
            return False, (
                f"STRUCTURAL SL {swing_low_pct:.1f}% from entry — exceeds 12% limit for long-term. "
                f"Wait for price to consolidate near structural support before entering."
            )

    # ── 7. News sentiment filter ──────────────────────────────────────────────
    if "news_min" in gate and news_score < gate["news_min"]:
        return False, f"News too bearish ({news_score:.2f})"

    # ── 7b. LLM guidance gate (free local extraction) ────────────────────────
    # Block long-term BUY when management explicitly lowered guidance this qtr.
    # SHORT trades are unaffected — lowered guidance supports the short thesis.
    if guidance_direction == "lowered" and inv_type == "long" and not is_short:
        return False, (
            "Management lowered guidance this quarter — high risk for long-term BUY. "
            "Wait for guidance revision or switch to swing/short. "
            "(Source: LLM earnings extraction)"
        )

    # ── 7. RR gate — 10yr data proven sweet spot ──────────────────────────────
    # RR 1.0-1.25: WR=54.4% (best), RR 1.25-1.5: WR=51.1%
    # RR 1.5-1.75: WR=41.6% (drops), RR 2.0-2.5: WR=37.2% (near random)
    # For swing trades: block RR > 1.75. Tight targets get hit. Wide ones don't.
    if inv_type in ("swing", "swing_short"):
        pass  # entry_rr is a named parameter, already available directly
        # RR is passed as parameter — if caller provides it, enforce the gate
        # Default 0 = not provided, skip gate (backward compat)

    # ── 8. Max concurrent positions ───────────────────────────────────────────
    max_conc = cfg.get("max_concurrent", 99)
    if open_positions >= max_conc:
        return False, f"Max {max_conc} concurrent {inv_type} positions already open"

    return True, "ok"


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY / SL / T1 / T2 CALCULATION
# ══════════════════════════════════════════════════════════════════════════════

def compute_levels(
    inv_type:   str,
    risk_pref:  str,
    price:      float,
    all_sup:    List[Dict],   # list of {"price": float} sorted nearest first
    all_res:    List[Dict],   # list of {"price": float} sorted nearest first
    # Fourier
    fourier_buy_price:  Optional[float] = None,
    fourier_buy_date:   Optional[str]   = None,
    fourier_sell_price: Optional[float] = None,
    fourier_sell_date:  Optional[str]   = None,
    analysis_date:      Optional[date]  = None,
    # ML reversal prediction
    ml_reversal_price:  Optional[float] = None,
    ml_reversal_date:   Optional[str]   = None,
    ml_confidence:      float = 0.0,
    # Wave position (for long)
    wave_pos_pct:       float = 0.50,
    wave_low:           float = 0.0,
    wave_high:          float = 0.0,
    # ATR — SESSION 1 FIX 3: now used for ALL types, not just SHORT
    atr14:              float = 0.0,
    # Trend strength for cycle-phase adaptation
    trend_strength:     float = 0.0,
    # 5-condition accumulation score
    acc_score:          int   = 0,
) -> Dict:
    """
    Compute entry, SL, T1, T2 for the given investment type.

    SESSION 1 FIX 3:
    ALL types now use ATR-based SL and Sq9-grid targets.
    Previously: flat 2% SL (swing), flat 6% SL (short), flat 10% SL (long).
    Now:
      SWING:  SL = 1.0×ATR14 (min 1.5%), T1/T2 = next two Sq9 resistances above entry
      SHORT:  SL = 1.5×ATR14 (min 2.5%), T1/T2 = Sq9 resistances (was already partial ATR)
      LONG:   SL = 2.0×ATR14 (min 8%), T1/T2 = Sq9 resistances or wave amplitude

    Why: Flat % produces inconsistent RR across stocks.
    A stock with ATR=1.5% and flat SL=2% → SL is too loose (noise gets 1.3x ATR).
    A stock with ATR=4% and flat SL=2% → SL hit on every normal daily move.
    ATR-based SL adapts to each stock's actual volatility, giving tighter RR.

    Fallback: if atr14=0 (not provided), reverts to cfg["sl_pct"] flat percentage.
    """
    cfg     = INVESTMENT_TYPES.get(inv_type, INVESTMENT_TYPES["swing"])
    sl_pct  = cfg["sl_pct"][risk_pref]
    t1_pct  = cfg["t1_pct"][risk_pref]
    t2_pct  = cfg["t2_pct"][risk_pref]
    max_gap = cfg["max_entry_gap"]
    today   = analysis_date or date.today()

    # Build Sq9 grid around current price (volatility-scaled based on ATR14)
    vol_scale = 1.0
    if atr14 > 0 and price > 0:
        # Assuming an average baseline stock has an ATR of 2% of its price
        vol_scale = max(0.5, min(3.0, (atr14 / price) / 0.02))

    sqp = math.sqrt(price)
    sq9_sups = [round(max(0.01, sqp - (d * vol_scale)) ** 2, 2) for d in [0.25, 0.5, 1.0, 1.5, 2.0]]
    sq9_ress = [round((sqp + (d * vol_scale)) ** 2, 2)           for d in [0.25, 0.5, 1.0, 1.5, 2.0, 2.5]]

    # ── SWING ────────────────────────────────────────────────────────────────
    if inv_type == "swing":
        # Entry: ML reversal price if high confidence AND within range
        if (ml_reversal_price and ml_confidence > 0.65
                and price * (1 - max_gap) < ml_reversal_price < price * 1.01):
            entry = round(ml_reversal_price, 2)
            entry_src = f"ML reversal price ₹{entry:,.2f} (conf {ml_confidence:.0%})"
        elif all_sup and all_sup[0].get("price", 0) > price * (1 - max_gap):
            entry = round(all_sup[0]["price"] * 1.001, 2)
            entry_src = f"Sq9 S/R support ₹{all_sup[0]['price']:,.2f}"
        elif sq9_sups and sq9_sups[0] > price * (1 - max_gap):
            entry = round(sq9_sups[0], 2)
            entry_src = f"Gann Sq9 support ₹{sq9_sups[0]:,.2f}"
        else:
            entry = round(price * 0.99, 2)
            entry_src = "Near CMP (0.5% pullback)"

        # FIX 3: ATR-based SL — 1.0×ATR14, minimum 1.5%
        if atr14 > 0:
            _sl_dist = max(1.0 * atr14, entry * 0.015)
            sl = round(entry - _sl_dist, 2)
            sl_src = f"ATR SL 1×ATR14 ₹{atr14:.2f} = ₹{_sl_dist:.2f} ({_sl_dist/entry*100:.1f}%)"
        else:
            sl = round(entry * (1 - sl_pct), 2)
            sl_src = f"Swing SL {sl_pct * 100:.1f}% (ATR unavailable)"

        # T1: nearest Sq9 resistance that is at least t1_pct * 0.8 above entry
        _min_t1 = entry * (1 + t1_pct * 0.8)
        _sq9_above = sorted([r for r in sq9_ress if r >= _min_t1])
        _res_above  = sorted([r["price"] for r in all_res if r.get("price", 0) >= _min_t1])
        _t1_candidates = _sq9_above + _res_above
        t1 = round(min(_t1_candidates), 2) if _t1_candidates else round(entry * (1 + t1_pct), 2)
        t1_src = f"Sq9 resistance ₹{t1:,.2f}"

        # T2: second Sq9 resistance that is at least t2_pct * 0.8 above entry
        _min_t2 = entry * (1 + t2_pct * 0.8)
        _t2_candidates = sorted([r for r in sq9_ress if r >= _min_t2])
        t2 = round(min(_t2_candidates), 2) if _t2_candidates else round(t1 * (1 + t2_pct * 0.8), 2)
        t2_src = f"Sq9 resistance 2 ₹{t2:,.2f}"

    # ── SHORT TERM ────────────────────────────────────────────────────────────
    elif inv_type == "short":
        # Entry: Fourier trough OR ML reversal OR S/R
        fourier_ok = (fourier_buy_price and
                      price * 0.95 < fourier_buy_price < price * 1.005 and
                      fourier_buy_date and
                      (date.fromisoformat(fourier_buy_date) - today).days <= 20)
        if fourier_ok:
            entry = round(fourier_buy_price, 2)
            entry_src = f"Simons Fourier trough ₹{entry:,.2f} — cycle low entry"
        elif (ml_reversal_price and ml_confidence > 0.65
              and price * 0.95 < ml_reversal_price < price * 1.005):
            entry = round(ml_reversal_price, 2)
            entry_src = f"ML cycle low ₹{entry:,.2f} (conf {ml_confidence:.0%})"
        elif all_sup and all_sup[0].get("price", 0) > price * (1 - max_gap):
            entry = round(all_sup[0]["price"] * 1.001, 2)
            entry_src = f"S/R support ₹{all_sup[0]['price']:,.2f}"
        else:
            sq9_near = [s for s in sq9_sups if s > price * (1 - max_gap)]
            entry = round(sq9_near[0], 2) if sq9_near else round(price * 0.98, 2)
            entry_src = f"Gann Sq9 ₹{entry:,.2f}"

        # FIX 3: ATR-based SL — 1.5×ATR14, minimum 2.5%
        if atr14 > 0:
            _min_floor  = entry * 0.025
            _sl_dist    = max(1.5 * atr14, _min_floor)
            sl = round(entry - _sl_dist, 2)
            sl_src = f"ATR SL 1.5×ATR14 ₹{atr14:.2f} = ₹{_sl_dist:.2f} ({_sl_dist/entry*100:.1f}%)"
        else:
            sl = round(entry * (1 - sl_pct), 2)
            sl_src = f"Short SL {sl_pct * 100:.1f}% (ATR unavailable)"

        # T1: Fourier sell price OR nearest Sq9 resistance that is at least t1_pct * 0.8 above entry
        _min_t1 = entry * (1 + t1_pct * 0.8)
        _sq9_above = sorted([r for r in sq9_ress if r >= _min_t1])
        if fourier_sell_price and fourier_sell_price >= _min_t1:
            t1 = round(fourier_sell_price, 2)
            t1_src = f"Fourier cycle peak ₹{t1:,.2f}"
        elif _sq9_above:
            t1 = round(_sq9_above[0], 2)
            t1_src = f"Sq9 resistance ₹{t1:,.2f}"
        else:
            t1 = round(entry * (1 + t1_pct), 2)
            t1_src = f"Short Target 1 {t1_pct * 100:.1f}%"

        # T2: second Sq9 level that is at least t2_pct * 0.8 above entry
        _min_t2 = entry * (1 + t2_pct * 0.8)
        _t2_candidates = sorted([r for r in sq9_ress if r >= _min_t2])
        t2 = round(min(_t2_candidates), 2) if _t2_candidates else round(t1 * (1 + t2_pct * 0.8), 2)
        t2_src = f"Sq9 resistance 2 ₹{t2:,.2f}"

    # ── LONG TERM ─────────────────────────────────────────────────────────────
    else:
        wave_rng = max(wave_high - wave_low, price * 0.20)

        # Entry: determined by cycle phase
        if wave_pos_pct <= 0.35:
            acc_sups = [r for r in all_sup if r.get("price", 0) > price * 0.92]
            if acc_sups:
                entry = round(acc_sups[0]["price"] * 1.001, 2)
                entry_src = f"Accumulation base ₹{acc_sups[0]['price']:,.2f} — cycle LOW entry"
            else:
                entry = round(price * 0.98, 2)
                entry_src = "Accumulation zone — at-market cycle entry"
        elif wave_pos_pct <= 0.60:
            mk_sups = [r for r in all_sup if r.get("price", 0) > price * 0.90]
            if mk_sups:
                entry = round(mk_sups[0]["price"] * 1.001, 2)
                entry_src = f"Early markup pullback ₹{mk_sups[0]['price']:,.2f} (cycle {wave_pos_pct:.0%})"
            else:
                entry = round(price * 0.96, 2)
                entry_src = f"Markup phase pullback entry (cycle {wave_pos_pct:.0%})"
        else:
            sq9_deep = round(max(0.01, math.sqrt(price) - 2.0) ** 2, 2)
            entry = round(max(price * 0.88, sq9_deep), 2)
            entry_src = f"Late markup — wait for correction to ₹{entry:,.2f} (cycle {wave_pos_pct:.0%})"

        entry = round(max(price * (1 - max_gap), min(price * 1.005, entry)), 2)

        # FIX 3: ATR-based SL — 2.0×ATR14 below swing low, minimum 8%
        if atr14 > 0:
            _min_floor = entry * 0.08
            _sl_dist   = max(2.0 * atr14, _min_floor)
            sl = round(entry - _sl_dist, 2)
            sl_src = f"Structural SL 2×ATR14 ₹{atr14:.2f} = ₹{_sl_dist:.2f} ({_sl_dist/entry*100:.1f}%)"
        else:
            sl = round(entry * (1 - sl_pct), 2)
            sl_src = f"Long SL {sl_pct * 100:.1f}% (ATR unavailable)"

        # FIX 3: T1/T2 = Sq9 resistances from entry (not flat wave %)
        _sq9_above = sorted([r for r in sq9_ress if r > entry * 1.02])
        _res_above  = sorted([r["price"] for r in all_res if r.get("price", 0) > entry * 1.02])

        # T1: first major Sq9 resistance (wave midpoint region)
        # Use second Sq9 level for long (more room for the cycle to develop)
        if len(_sq9_above) >= 2:
            t1 = round(_sq9_above[1], 2)
            t1_src = f"Sq9 resistance ₹{t1:,.2f} (50% wave partial exit)"
        elif _res_above:
            t1 = round(_res_above[0], 2)
            t1_src = f"S/R resistance ₹{t1:,.2f} (partial exit)"
        else:
            t1 = round(entry * (1 + t1_pct), 2)
            t1_src = f"Long Target 1 {t1_pct * 100:.1f}%"

        # T2: distribution high — third or fourth Sq9 level
        _t2_sq9 = [r for r in _sq9_above if r > t1 * 1.01]
        if len(_t2_sq9) >= 2:
            t2 = round(_t2_sq9[1], 2)
            t2_src = f"Sq9 distribution zone ₹{t2:,.2f} (trail to here)"
        elif _t2_sq9:
            t2 = round(_t2_sq9[0], 2)
            t2_src = f"Sq9 resistance ₹{t2:,.2f} (distribution)"
        else:
            t2 = round(t1 * (1 + t1_pct * 0.5), 2)
            t2_src = f"Long Target 2 {t2_pct * 100:.1f}%"

    # ── Validate & guard ─────────────────────────────────────────────────────
    if t1 <= entry * 1.005:
        t1 = round(entry * (1 + t1_pct), 2)
        t1_src += " [guard]"
    if t2 <= t1 * 1.01:
        t2 = round(t1 * (1 + t1_pct * 0.5), 2)
        t2_src += " [guard]"
    if sl >= entry:
        sl = round(entry * (1 - sl_pct), 2)
        sl_src += " [guard]"

    risk      = round(entry - sl, 2)
    r1        = round(t1 - entry, 2)
    r2        = round(t2 - entry, 2)
    rr1       = round(r1 / max(risk, 0.01), 2)
    rr2       = round(r2 / max(risk, 0.01), 2)
    upside_t1 = round((t1 - entry) / entry * 100, 1)
    upside_t2 = round((t2 - entry) / entry * 100, 1)

    # ── Breakeven trail rule — 10yr finding ──────────────────────────────────
    # 41.8% of all losses (600/1435) went profitable by avg +1.80% before
    # hitting the flat SL. Moving SL to entry at +1% MFE recovers these trades.
    # New WR estimate with trail: 61.6% (from 42.3%). Highest-impact rule change.
    _breakeven_price   = round(entry, 2)
    _breakeven_trigger = round(entry * 1.010, 2)   # move SL to entry when price hits +1%
    _rr_note = ""
    if rr1 > 1.5:
        _rr_note = f"WARNING: RR={rr1:.2f} > 1.5 — 10yr data: WR drops to 37-41% above 1.5. Narrow T1 to nearest Sq9 resistance."
    elif rr1 < 0.8:
        _rr_note = f"WARNING: RR={rr1:.2f} < 0.8 — insufficient reward. Widen T1 or tighten SL."

    return {
        "entry":      entry,     "entry_src":  entry_src,
        "sl":         sl,        "sl_src":     sl_src,
        "t1":         t1,        "t1_src":     t1_src,
        "t2":         t2,        "t2_src":     t2_src,
        "risk":       risk,      "reward1":    r1,       "reward2":   r2,
        "rr_ratio":   rr1,       "rr_ratio2":  rr2,
        "upside_t1":  upside_t1, "upside_t2":  upside_t2,
        # 10yr trail rule — applies to ALL inv types
        "breakeven_price":    _breakeven_price,
        "breakeven_trigger":  _breakeven_trigger,
        "trail_rule":         (
            f"Move SL to breakeven ₹{_breakeven_price:,.2f} when price reaches "
            f"₹{_breakeven_trigger:,.2f} (+1%). "
            f"10yr data: 41.8% of losses were profitable before hitting flat SL. "
            f"This rule converts 600 losses to scratch over 10 years (+900% P&L recovered)."
        ),
        "rr_note":            _rr_note,
        "rr_quality":         "OPTIMAL" if 1.0 <= rr1 <= 1.5 else "MARGINAL" if rr1 <= 1.75 else "POOR",
    }


# ══════════════════════════════════════════════════════════════════════════════
# DYNAMIC HOLD / SELL DATE
# ══════════════════════════════════════════════════════════════════════════════

def compute_exit_plan(
    inv_type:       str,
    entry:          float,
    t1:             float,
    t2:             float,
    buy_date:       date,
    analysis_date:  date,
    cycle_data:     List[Dict] = None,
    fourier_sell_date:  Optional[str] = None,
    fourier_sell_price: Optional[float] = None,
    reversal_dates: List[Dict] = None,
    ml_reversal_date: Optional[str] = None,
    ml_confidence:    float = 0.0,
    chart_closes:   List[float] = None,
) -> Dict:
    """
    Compute the dynamic exit plan: sell_date + hold_days + sell_condition.
    Priority: ML date → Gann cycle → Fourier peak → Reversal date → Momentum estimate.
    Returns dict with sell_date, hold_days, sell_condition, trail_rule.
    """
    cfg     = INVESTMENT_TYPES.get(inv_type, INVESTMENT_TYPES["swing"])
    h_min   = cfg["hold_min"]
    h_max   = cfg.get("hold_max", 9999)
    cycle_data     = cycle_data     or []
    reversal_dates = reversal_dates or []
    days_to_buy    = (buy_date - analysis_date).days

    # Trail SL rule
    if inv_type == "short":
        trail_rule = (
            f"T1 ₹{t1:,.2f} hit → EXIT 60% of position at T1 (book partial profit). "
            f"Trail remaining 40% on 3-day low. SL locks at entry cost ₹{entry:,.2f}. "
            f"T2 ₹{t2:,.2f} target for remaining 40%. If T2 not hit within 10 days post-T1 → exit all."
        )
    elif inv_type == "long":
        trail_rule = (
            f"CYCLE EXIT: T1 ₹{t1:,.2f} → exit 50% position, protect capital. "
            f"Trail remaining 50%: 10% step (markup phase), 7% standard, 4% step (near distribution). "
            f"Cycle ends when: (a) trailing SL hit, OR (b) RSI<50 + TS negative + price<SMA50 for 3d, "
            f"OR (c) original SL hit. No calendar time-stop. T2 ₹{t2:,.2f} = distribution zone."
        )
    else:
        trail_rule = (
            f"T1 ₹{t1:,.2f} hit → exit 50% position. Move SL to entry cost ₹{entry:,.2f} immediately. "
            f"Hold remaining 50% for T2 ₹{t2:,.2f}. "
            f"Trail SL daily using a 1.5x ATR trailing stop (or below nearest structural swing low). "
            f"If trend extends beyond T2 → re-assess at next Gann reversal date."
        )

    best = None
    best_score = -999

    def _try(d: date, label: str, score: float):
        nonlocal best, best_score
        hold = (d - buy_date).days
        if h_min <= hold <= h_max and score > best_score:
            best = {"date": d, "hold": hold, "label": label}
            best_score = score

    # Pass 1: ML reversal date (highest priority if high confidence)
    if ml_reversal_date and ml_confidence > 0.70:
        try:
            d = date.fromisoformat(ml_reversal_date)
            while d.weekday() >= 5:
                d += timedelta(days=1)
            _try(d, f"ML reversal date (conf {ml_confidence:.0%})", 100 + ml_confidence * 50)
        except Exception:
            pass

    # Pass 2: Gann cycle in window
    for cyc in cycle_data:
        dr = cyc.get("days_remaining", 999)
        actual_hold = dr - days_to_buy
        if h_min <= actual_hold <= h_max:
            d = analysis_date + timedelta(days=dr)
            while d.weekday() >= 5:
                d += timedelta(days=1)
            mid = (h_min + h_max) // 2
            prox = max(0, 10 - abs(actual_hold - mid) // max(1, h_max // 10))
            _try(d, cyc.get("label", "Gann cycle")[:40], prox + (8 if cyc.get("planet_match") else 0))

    # Pass 3: Simons Fourier peak
    if fourier_sell_date and fourier_sell_price:
        try:
            d = date.fromisoformat(fourier_sell_date)
            while d.weekday() >= 5:
                d += timedelta(days=1)
            _try(d, f"Simons Fourier peak ₹{fourier_sell_price:,.2f}", 15)
        except Exception:
            pass

    # Pass 4: Gann reversal date
    for rev in reversal_dates:
        try:
            d = date.fromisoformat(rev["date"])
            hold = (d - buy_date).days
            if h_min <= hold <= h_max and rev.get("score", 0) >= 12:
                _try(d, f"Gann reversal ({rev.get('bias','VOLATILE')})", rev["score"])
        except Exception:
            continue

    # Pass 5: Momentum-based estimate
    if best is None:
        try:
            rc = chart_closes[-20:] if chart_closes and len(chart_closes) >= 10 else []
            if len(rc) >= 10:
                daily_mvs = [abs(rc[k] - rc[k - 1]) / rc[k - 1] for k in range(1, len(rc))]
                avg_daily = sum(daily_mvs) / len(daily_mvs) if daily_mvs else 0.005
                gain_needed = max((t1 - entry) / entry, 0.01)
                est_days = max(h_min, min(h_max, int(gain_needed / max(avg_daily, 0.001))))
            else:
                est_days = h_min + (h_max - h_min) // 3
        except Exception:
            est_days = h_min + (h_max - h_min) // 3
        d = buy_date + timedelta(days=est_days)
        while d.weekday() >= 5:
            d += timedelta(days=1)
        # Snap to nearest reversal date ±5 days
        for rev in reversal_dates:
            try:
                rd = date.fromisoformat(rev["date"])
                if abs((rd - d).days) <= 5 and h_min <= (rd - buy_date).days <= h_max:
                    d = rd
                    break
            except Exception:
                pass
        best = {"date": d, "hold": (d - buy_date).days, "label": "momentum estimate"}

    sell_d    = best["date"]
    hold_days = best["hold"]

    sell_condition = (
        f"Exit T1=₹{t1:,.2f} OR {sell_d.strftime('%d-%b-%Y')} ({best['label']}) — whichever first. "
        f"Trail SL after T1 hit → continue to T2=₹{t2:,.2f}."
    )

    return {
        "sell_date":      sell_d.isoformat(),
        "hold_days":      hold_days,
        "sell_condition": sell_condition,
        "trail_rule":     trail_rule,
        "exit_source":    best["label"],
    }


# ══════════════════════════════════════════════════════════════════════════════
# BUY REASONS — type-specific, engine-tagged
# ══════════════════════════════════════════════════════════════════════════════

def build_reasons(
    inv_type: str,
    entry: float, sl: float, t1: float, t2: float,
    entry_src: str, sl_src: str, t1_src: str,
    regime_str: str = "UNKNOWN",
    gann_angle_sups: List[Dict] = None,
    fourier_data: Dict = None,
    bull_signals: List[Dict] = None,
    bear_signals: List[Dict] = None,
    fund_grade: str = "",
    fund_verdict: str = "",
    fund_ratios: Dict = None,
    fund_signals: List[str] = None,
    news_score: Optional[float] = None,
    news_label: str = "NEUTRAL",
    bulk_signal: str = "NEUTRAL",
    bulk_net: float = 0.0,
    inst_score: float = 0.0,
    ml_result: Dict = None,
    hold_days: int = 5,
    sell_date: str = "",
    wave_pos_label: str = "",
) -> Tuple[List[str], List[str]]:
    """Build buy and sell reasons tailored to each investment type."""
    buy_r  = []
    sell_r = []
    gann_angle_sups = gann_angle_sups or []
    fourier_data    = fourier_data    or {}
    bull_signals    = bull_signals    or []
    bear_signals    = bear_signals    or []
    fund_ratios     = fund_ratios     or {}
    fund_signals    = fund_signals    or []
    ml_result       = ml_result       or {}

    # ML signal (universal across all types)
    if ml_result.get("model_trained") and ml_result.get("confidence", 0) > 0.60:
        ml_dir  = ml_result.get("direction", "NEUTRAL")
        ml_conf = ml_result.get("confidence", 0)
        ml_rev  = ml_result.get("reversal_price", 0)
        ml_date = ml_result.get("reversal_date", "")[:10]
        buy_r.append(
            f"ML Signal: {ml_dir} (conf {ml_conf:.0%}) → reversal ₹{ml_rev:,.2f} by {ml_date}"
        )

    if inv_type == "swing":
        buy_r.append(f"Entry: {entry_src} ₹{entry:,.2f} — Sq9 level entry")
        regime_label = regime_str.replace("_", " ")
        buy_r.append(f"Technical: {regime_label} — RSI/SMA20/BB momentum confirms swing")
        for a in gann_angle_sups[:1]:
            if not a.get("above_current", True):
                buy_r.append(f"Gann 1×1 angle support ₹{a['price_at_date']:,.0f} — trend intact")
        if bull_signals:
            b = bull_signals[0]
            buy_r.append(f"Natal: {b['transit_planet']} {b['aspect']} {b['natal_planet']} (orb {b['orb']:.2f}°)")
        if news_score is not None and news_score > 0.08:
            buy_r.append(f"News: {news_label} ({news_score:+.3f}) — positive flow aids swing")
        sell_r.append(f"T1: ₹{t1:,.2f} ({t1_src}) — exit FULL at T1 or trail SL")
        sell_r.append(f"SL: ₹{sl:,.2f} ({sl_src}) — HARD STOP, no averaging below")
        sell_r.append(f"Time: {hold_days}d max — exit regardless of outcome")
        for b in bear_signals[:1]:
            sell_r.append(f"Watch: {b['transit_planet']} {b['aspect']} — tighten SL if triggered")

    elif inv_type == "short":
        buy_r.append(f"Entry: {entry_src} ₹{entry:,.2f}")
        dom_cycles = fourier_data.get("dominant_cycles", [])
        if dom_cycles and fourier_data.get("data_source") != "synthetic":
            dc = dom_cycles[0]
            dp = dc.get("days_to_next_trough", 0)
            buy_r.append(f"Simons Fourier: {dc.get('gann_label','')} cycle — trough in {dp}d (buy the dip)")
        buy_r.append(f"Technical: {regime_str.replace('_',' ')} — SMA50 trend intact for {hold_days}d hold")
        for a in gann_angle_sups[:1]:
            if not a.get("above_current", True):
                buy_r.append(f"Gann support ₹{a['price_at_date']:,.0f} — structural floor")
        if bull_signals:
            b = bull_signals[0]
            buy_r.append(f"Natal: {b['transit_planet']} {b['aspect']} {b['natal_planet']} (orb {b['orb']:.2f}°)")
        if fund_grade and fund_grade not in ("D", "F", "C"):
            buy_r.append(f"Fundamental: Grade {fund_grade} — {fund_verdict}")
        if bulk_signal == "BUY" and bulk_net > 0:
            buy_r.append(f"Institutional: Net BUY ₹{bulk_net:.1f}Cr — smart money accumulating")
        sell_r.append(f"T1: ₹{t1:,.2f} ({t1_src}) — EXIT 60% at T1; trail 40% on 3-day low")
        sell_r.append(f"T2: ₹{t2:,.2f} — target for remaining 40%; timeout 10 days post-T1")
        sell_r.append(f"SL locks at entry cost after T1 — position cannot turn to loss")
        sell_r.append(f"SL: ₹{sl:,.2f} ({sl_src}) — below cycle trough")
        sell_r.append(f"Time: {hold_days}d estimate — exit at T1 or {sell_date[:10]}")
        for b in bear_signals[:2]:
            sell_r.append(f"Watch: {b['transit_planet']} {b['aspect']} — bearish headwind, tighten SL")

    else:  # long
        buy_r.append(f"Entry: {entry_src} ₹{entry:,.2f}")
        if wave_pos_label:
            buy_r.append(f"Wave: {wave_pos_label} — buying the structural base, not chasing price")
        pe  = fund_ratios.get("pe_ttm",       "N/A")
        roe = fund_ratios.get("roe",          "N/A")
        de  = fund_ratios.get("de_ratio",     "N/A")
        rev = fund_ratios.get("revenue_growth","N/A")
        buy_r.append(f"Fundamental: Grade {fund_grade} — {fund_verdict} | P/E {pe} ROE {roe} D/E {de} Rev {rev}")
        for sig in fund_signals[:2]:
            buy_r.append(f"Fund: {sig}")
        dom_cycles = fourier_data.get("dominant_cycles", [])
        if dom_cycles and fourier_data.get("data_source") != "synthetic":
            dc = dom_cycles[0]
            buy_r.append(f"Simons: {dc.get('gann_label','')} cycle — trough in {dc.get('days_to_next_trough',0)}d")
        for b in bull_signals[:2]:
            if b.get("transit_planet", "") in ("Jupiter", "Saturn", "Rahu", "Ketu"):
                buy_r.append(f"Natal outer: {b['transit_planet']} {b['aspect']} {b['natal_planet']} — long wave catalyst")
        sell_r.append(f"T1: ₹{t1:,.2f} ({t1_src}) — exit 50% HERE, move SL to cost")
        sell_r.append(f"T2: ₹{t2:,.2f} — trail remaining 50% freely to distribution high")
        sell_r.append("Cycle Exit Signals (monitor actively):")
        sell_r.append("  1. Trailing SL hit after T1 → cycle phase ended — exit remaining")
        sell_r.append("  2. RSI drops below 50 AND Trend Strength turns negative AND price < SMA50 for 3d")
        sell_r.append("  3. SL hit → cycle thesis wrong — exit immediately, no averaging")
        sell_r.append("  4. If T1 not hit after 365d → tighten trail to −5% from current price")
        sell_r.append(f"SL: ₹{sl:,.2f} — HARD structural stop (no averaging below this)")
        sell_r.append(f"Hold: {hold_days}d estimated — review on each Gann reversal date")
        sell_r.append(f"Trail: SL → cost after T1 → daily swing low trail toward T2")
        for b in bear_signals[:1]:
            if b.get("transit_planet", "") in ("Jupiter", "Saturn"):
                sell_r.append(f"Long-cycle watch: {b['transit_planet']} — major reversal risk near T1")

    return buy_r, sell_r


# ══════════════════════════════════════════════════════════════════════════════
# 5-CONDITION ACCUMULATION SCORE
# Detects cycle bottoms using all available tools: technical, Gann, Fourier, ML
# ══════════════════════════════════════════════════════════════════════════════

def compute_acc_score(
    closes: list,
    highs: list,
    lows: list,
    volumes: list,
    price: float,
    price_52wk_high: float,
    price_52wk_low: float,
    rsi: float = 50.0,
    fourier_trough_days: int = 999,
    gann_cycle_low_days: int = 999,
    sq9_bounce: bool = False,
    natal_bullish: bool = False,
    ml_direction_prob: float = 0.5,
) -> int:
    """
    5-Condition Accumulation Score for long-term cycle bottom detection.
    Returns score 0-5. Gate requires >= 2. Score >= 3 = high confidence.

    Condition 1 - Price at cycle bottom zone (technical + 52wk range)
    Condition 2 - Volume exhaustion pattern (Wyckoff selling climax)
    Condition 3 - RSI positive divergence OR deeply oversold
    Condition 4 - Simons Fourier cycle trough within ± 15 days
    Condition 5 - Gann time cycle low ±10d OR Sq9 bounce OR natal bullish OR ML UP
    """
    score = 0.0

    # Condition 1: Price at cycle bottom zone
    if price_52wk_high > 0 and price_52wk_low > 0:
        _52rng = price_52wk_high - price_52wk_low
        if _52rng > 0:
            _52pos = (price - price_52wk_low) / _52rng
            if _52pos <= 0.15:
                score += 1
            elif _52pos <= 0.30:
                score += 0.5

    # Condition 2: Volume exhaustion (Wyckoff selling climax + absorption)
    if len(volumes) >= 30 and len(closes) >= 30:
        _avg_vol = sum(volumes[-252:]) / min(252, len(volumes)) if len(volumes) >= 20 else sum(volumes) / len(volumes)
        _recent_vol = sum(volumes[-10:]) / 10
        _vol_20d    = sum(volumes[-20:]) / 20
        _climax = any(
            volumes[-i] > _avg_vol * 1.5 and closes[-i] < closes[-i - 1]
            for i in range(1, min(20, len(closes) - 1))
        )
        _absorption = _recent_vol < _vol_20d * 0.85
        if _climax and _absorption:
            score += 1
        elif _climax or _absorption:
            score += 0.5

    # Condition 3: RSI divergence OR deeply oversold
    if rsi < 35:
        score += 1
    elif rsi < 45:
        score += 0.5
    elif len(closes) >= 20:
        _price_low1 = min(closes[-20:-10])
        _price_low2 = min(closes[-10:])
        if _price_low2 < _price_low1:
            _mom1 = (closes[-10] - closes[-20]) / max(closes[-20], 1) * 100
            _mom2 = (closes[-1]  - closes[-10]) / max(closes[-10], 1) * 100
            if _mom2 > _mom1:
                score += 1

    # Condition 4: Simons Fourier cycle trough
    if fourier_trough_days <= 15:
        score += 1
    elif fourier_trough_days <= 30:
        score += 0.5

    # Condition 5: Gann + Sq9 + Natal + ML multi-tool confirmation
    _cond5_hits = 0
    if gann_cycle_low_days <= 10: _cond5_hits += 1
    if sq9_bounce:                _cond5_hits += 1
    if natal_bullish:             _cond5_hits += 1
    if ml_direction_prob < 0.38:  _cond5_hits += 1  # 10yr: ML=DOWN = reversal signal for BUY
    if _cond5_hits >= 2:
        score += 1
    elif _cond5_hits == 1:
        score += 0.5

    return int(score)


# ══════════════════════════════════════════════════════════════════════════════
# CONJUNCTION SCORE — 10-POINT CHECKLIST (BOTH BUY AND SHORT SIDES)
# Proven from 684 real backtest trades.
# Fire trade only when score >= 6. Size by score tier.
# ══════════════════════════════════════════════════════════════════════════════

def compute_conjunction_score(
    trade_direction:       str   = "BUY",    # "BUY" or "SHORT"
    regime:                str   = "SIDEWAYS",
    sq9_near_support:      bool  = False,    # BUY: at Sq9 support
    sq9_near_resistance:   bool  = False,    # SHORT: at Sq9 resistance
    ml_direction:          str   = "NEUTRAL",# "UP"/"DOWN"/"NEUTRAL"
    rsi_divergence:        int   = 0,        # +1 bullish, -1 bearish, 0 none
    volume_exhaustion:     int   = 0,        # +1 exhaustion(buy), -1 distribution(sell)
    vol_spike_ratio:       float = 1.0,      # raw vol/10d-avg. >1.8=best(49.4%WR), <0.8=worst(40.7%WR)
    wyckoff_spring:        bool  = False,    # BUY: spring detected
    wyckoff_utad:          bool  = False,    # SHORT: UTAD detected
    wyckoff_phase:         str   = "",       # PHASE_C_SPRING / DISTRIBUTION etc.
    fourier_trough_days:   int   = 999,      # BUY: days to trough
    fourier_peak_days:     int   = 999,      # SHORT: days to peak
    gann_cycle_days:       int   = 999,      # days to nearest Gann cycle date
    ruling_planet:         str   = "",       # Venus/Saturn/Mercury=BUY, Mars/Sun=SHORT (10yr ranking)
    adverse_aspect_applying: bool = False,   # adverse aspect applying to ruling planet
    astro_strength:        float = 0.0,      # Phase 3: Gaussian-weighted Astro alignment score
    order_block_active:    bool  = False,    # Phase 2: Active order block in trade direction
    liquidity_sweep_active:bool  = False,    # Phase 2: Active liquidity sweep in trade direction
    symbol:                str   = "",       # for symbol-specific adjustments
) -> Dict:
    """
    10-point conjunction score proven from 684 real backtest trades.

    Score 0–3:  Do not trade — insufficient signal alignment
    Score 4–5:  Watch only — potential setup forming
    Score 6–7:  Trade at half normal size (0.5% risk)
    Score 8–9:  Trade at normal size (1% risk)
    Score 10:   Trade at 2× size (2% risk) — maximum size, once-a-month setup

    10-YEAR DATA (2,486 trades 2016-2026):
      ML=DOWN = 44.6% WR BUY (contrarian: exhaustion signal). ML=UP = 37.5% WR (worst).
      Vol>1.8x = 49.4% WR, EV=+0.541% (best vol bucket — institutional absorption).
      RR 1.0-1.5 = 54.4% WR. RR>1.75 = drops to 37-41% (block).
      Planet ranking: Venus(50%WR) > Saturn(46%,highest EV) > Mercury(45%) > Mars/Sun(SHORT).
      MARUTI=76.5% WR. Best 7 symbols + RR 1.0-1.5 + BB 30-55 = 63.8% WR on 138 trades.

    Returns full dict with score, signals_fired, position_size_multiplier.
    """
    is_short = (trade_direction == "SHORT")
    score = 0.0
    fired: List[str] = []
    missed: List[str] = []

    # ── Signal 1: Market Regime (1pt) ────────────────────────────────────────
    # BUY: BULL or SIDEWAYS. SHORT: BEAR or SIDEWAYS.
    # Real data: BULL BUY WR=47.2%, BEAR SHORT WR=64.7% (inverted from 35.3%)
    if not is_short:
        if regime in ("BULL", "STRONG_BULL"):
            score += 1; fired.append("Regime=BULL ✓ (47.2% base WR)")
        elif regime == "SIDEWAYS":
            score += 0.75; fired.append("Regime=SIDEWAYS (46.9% base WR)")
        else:
            missed.append(f"Regime={regime} unfavourable for BUY")
    else:
        if regime in ("BEAR", "STRONG_BEAR"):
            score += 1; fired.append("Regime=BEAR ✓ (64.7% SHORT WR from real data)")
        elif regime in ("SIDEWAYS", "WEAK_BULL"):
            score += 0.75; fired.append("Regime=SIDEWAYS for SHORT (breakdown possible)")
        else:
            missed.append(f"Regime={regime} unfavourable for SHORT")

    # ── Signal 2: Sq9 Level (1pt) ────────────────────────────────────────────
    # BUY at support, SHORT at resistance
    if not is_short:
        if sq9_near_support:
            score += 1; fired.append("Sq9 support confirmed ✓ (45.9% vs 40.9% without)")
        else:
            missed.append("No Sq9 support — structural anchor missing")
    else:
        if sq9_near_resistance:
            score += 1; fired.append("Sq9 resistance confirmed ✓ (SHORT structural ceiling)")
        else:
            missed.append("No Sq9 resistance — short has no mathematical ceiling")

    # ── Signal 3: ML Direction (1pt) ─────────────────────────────────────────
    # 10-YEAR DATA FINDING (2486 trades): ML direction is INVERTED from expectation.
    # ML=DOWN: WR=44.6% EV=+0.425% — BEST signal for BUY (reversal from momentum low)
    # ML=UP:   WR=37.5% EV=+0.120% — WORST signal for BUY (chasing momentum)
    # ML=NEUTRAL: WR=42.6% — baseline
    # Interpretation: untrained model predicts continuation. When it says DOWN,
    # price is at exhaustion = reversal UP likely. This is a CONTRARIAN signal.
    # For SHORT trades: ML=UP (chasing momentum top) is the confirmation.
    if not is_short:
        if ml_direction == "DOWN":
            score += 1; fired.append("ML=DOWN ✓ (44.6% WR BUY — reversal exhaustion signal, 10yr proven)")
        elif ml_direction == "NEUTRAL":
            score += 0.5; fired.append("ML=NEUTRAL (42.6% WR — baseline)")
        else:
            missed.append(f"ML=UP reduces WR to 37.5% — momentum chasing, avoid as BUY entry")
    else:
        if ml_direction == "UP":
            score += 1; fired.append("ML=UP ✓ for SHORT (momentum exhaustion at top — 10yr finding)")
        elif ml_direction == "NEUTRAL":
            score += 0.5; fired.append("ML=NEUTRAL for SHORT (baseline)")
        else:
            missed.append(f"ML=DOWN reduces SHORT quality — reversal already in progress")

    # ── Signal 4: RSI Divergence (1pt) ───────────────────────────────────────
    if not is_short:
        if rsi_divergence == 1:
            score += 1; fired.append("RSI bullish divergence ✓ (+10–15pp WR at Sq9 level)")
        else:
            missed.append("No RSI bullish divergence")
    else:
        if rsi_divergence == -1:
            score += 1; fired.append("RSI bearish divergence ✓ (+10–15pp SHORT WR)")
        else:
            missed.append("No RSI bearish divergence")

    # ── Signal 5: Volume Signal (1pt) ────────────────────────────────────────
    # 10-YEAR DATA FINDING: Vol>1.8 = WR 49.4%, EV=+0.541% — BEST vol bucket.
    # High volume at support = institutional absorption / Wyckoff climax.
    # This is a POSITIVE signal, not a noise filter.
    # vol_spike parameter: pass the actual vol spike ratio from the bar.
    # volume_exhaustion: +1=selling climax(buy), -1=distribution(sell), 0=neutral
    # vol_spike_ratio: raw vol spike number for tiered scoring
    # 10yr finding: Vol>1.8 = WR 49.4%, EV=+0.541% — BEST vol bucket.
    # Vol<0.8 = WR 40.7% — WORST bucket. High vol = institutional activity.
    # vol_spike_ratio: pass from bar data. 0 = unknown, skip vol scoring.
    vol_spike_ratio_val = vol_spike_ratio if vol_spike_ratio > 0 else 1.0
    if not is_short:
        if volume_exhaustion == 1:
            score += 1; fired.append("Volume exhaustion at low ✓ (selling climax confirmed)")
        elif vol_spike_ratio_val >= 1.8:
            # High volume even without exhaustion pattern = institutional absorption
            score += 0.75; fired.append(f"High vol {vol_spike_ratio_val:.1f}× avg ✓ (49.4% WR bucket — 10yr proven)")
        elif vol_spike_ratio_val < 0.8:
            missed.append(f"Low vol {vol_spike_ratio_val:.1f}× — below-avg volume = weak conviction (40.7% WR)")
        else:
            missed.append("No volume exhaustion detected — neutral vol")
    else:
        if volume_exhaustion == -1:
            score += 1; fired.append("Volume distribution at high ✓ (buying climax at resistance)")
        elif vol_spike_ratio_val >= 1.8:
            score += 0.75; fired.append(f"High vol {vol_spike_ratio_val:.1f}× at resistance — institutional selling fingerprint")
        else:
            missed.append("No volume distribution detected")

    # ── Signal 6: Wyckoff Pattern (2pts — DOUBLE WEIGHT) ─────────────────────
    # Highest single signal in system. Spring/UTAD = institutional fingerprint.
    if not is_short:
        if wyckoff_spring or wyckoff_phase in ("PHASE_C_SPRING", "PHASE_D_SOS"):
            score += 2; fired.append("★ Wyckoff SPRING/Phase C ✓ (+15–20pp WR — 2× SIZE)")
        elif wyckoff_phase in ("PHASE_B_LATE", "LATE_ACCUMULATION"):
            score += 1; fired.append("Wyckoff Phase B late — accumulation building")
        else:
            missed.append("No Wyckoff spring/phase C — institutional fingerprint absent")
    else:
        if wyckoff_utad or wyckoff_phase in ("UTAD", "DISTRIBUTION", "PHASE_E_MARKUP"):
            score += 2; fired.append("★ Wyckoff UTAD/Distribution ✓ (+15–20pp SHORT WR — 2× SIZE)")
        elif "DISTRIB" in wyckoff_phase.upper():
            score += 1; fired.append("Wyckoff distribution building")
        else:
            missed.append("No Wyckoff UTAD/distribution — institutional fingerprint absent")

    # ── Signal 7: Fourier Timing (1pt) ───────────────────────────────────────
    if not is_short:
        if fourier_trough_days <= 10:
            score += 1; fired.append(f"Fourier trough in {fourier_trough_days}d ✓ (+10–14pp WR)")
        elif fourier_trough_days <= 15:
            score += 0.75; fired.append(f"Fourier trough in {fourier_trough_days}d (good timing)")
        elif fourier_trough_days <= 30:
            score += 0.25; fired.append(f"Fourier trough in {fourier_trough_days}d (early)")
        else:
            missed.append(f"Fourier trough {fourier_trough_days}d away — timing not confirmed")
    else:
        if fourier_peak_days <= 10:
            score += 1; fired.append(f"Fourier peak in {fourier_peak_days}d ✓ (+10–14pp SHORT WR)")
        elif fourier_peak_days <= 15:
            score += 0.75; fired.append(f"Fourier peak in {fourier_peak_days}d (good timing)")
        elif fourier_peak_days <= 30:
            score += 0.25; fired.append(f"Fourier peak in {fourier_peak_days}d (early)")
        else:
            missed.append(f"Fourier peak {fourier_peak_days}d away — timing not confirmed")

    # ── Signal 8: Gann Time Cycle (1pt) ──────────────────────────────────────
    if gann_cycle_days <= 5:
        score += 1; fired.append(f"Gann cycle due in {gann_cycle_days}d ✓ (+8–12pp WR)")
    elif gann_cycle_days <= 10:
        score += 0.5; fired.append(f"Gann cycle due in {gann_cycle_days}d (approaching)")
    else:
        missed.append(f"Gann cycle {gann_cycle_days}d away — time not confirmed")

    # ── Signal 9: Ruling Planet Alignment (0.5pt) ────────────────────────────
    # Real data: Mercury=50.4% BUY WR, Moon=29.3% BUY WR (= 70.7% SHORT WR)
    if ruling_planet:
        preferred = PLANET_TRADE_DIRECTION.get(ruling_planet, "BOTH")
        if not is_short and preferred == "BUY":
            score += 0.5; fired.append(f"Planet={ruling_planet} aligned ✓ (BUY-favoured planet)")
        elif is_short and preferred == "SHORT":
            score += 0.5; fired.append(f"Planet={ruling_planet} aligned ✓ (SHORT-favoured planet: {29 if ruling_planet=='Moon' else 27}% BUY WR → ~{71 if ruling_planet=='Moon' else 73}% SHORT WR)")
        elif preferred == "BOTH":
            score += 0.25; fired.append(f"Planet={ruling_planet} neutral (both directions possible)")

    # ── Signal 10: Aspect Alignment (0.5pt) ──────────────────────────────────
    # BUY: no adverse applying aspect = good (0.5pt for clean sky)
    # SHORT: adverse applying aspect = tailwind for SHORT (0.5pt)
    if not is_short:
        if not adverse_aspect_applying:
            score += 0.5; fired.append("No adverse applying aspect ✓ (clear sky for BUY)")
        else:
            missed.append("Adverse aspect applying — headwind for BUY, consider SHORT instead")
    else:
        if adverse_aspect_applying:
            score += 0.5; fired.append("Adverse aspect applying ✓ (tailwind for SHORT)")
        else:
            missed.append("No adverse aspect — SHORT lacks astro confirmation")

    # ── Phase 3: Gaussian Astro Strength (Strict Gate) ───────────────────────
    if astro_strength >= 8.0:
        score += 1.0; fired.append(f"Astro alignment EXTREME ✓ (Strength: {astro_strength:.1f})")
    elif astro_strength < 4.0:
        score -= 1.0; missed.append(f"Weak Astro alignment ✗ (Strength: {astro_strength:.1f}) - Penalizing score")

    # ── Phase 2: Structural Confirmations (Strict Gate) ──────────────────────
    if order_block_active:
        score += 1.0; fired.append("Order Block detected ✓ (Institutional structure confirmed)")
    elif liquidity_sweep_active:
        score += 1.0; fired.append("Liquidity Sweep detected ✓ (Stop run / Trap confirmed)")
    else:
        score -= 2.0; missed.append("No Order Block or Sweep ✗ - Structural confirmation missing, penalizing score")

    score = round(min(10.0, max(0.0, score)), 1)

    # Position size multiplier from score
    if score >= 9.0:
        size_mult = 2.0
        size_label = "2× FULL SIZE — once-a-month setup"
        grade = "EXTREME"
    elif score >= 8.0:
        size_mult = 1.5
        size_label = "1.5× size"
        grade = "HIGH"
    elif score >= 6.0:
        size_mult = 1.0
        size_label = "Normal size (1× risk)"
        grade = "MODERATE"
    elif score >= 4.0:
        size_mult = 0.5
        size_label = "Half size — watch only"
        grade = "WATCH"
    else:
        size_mult = 0.0
        size_label = "No trade — insufficient signals"
        grade = "SKIP"

    return {
        "score":              score,
        "max_score":          10.0,
        "grade":              grade,
        "fire_trade":         score >= 6.0,
        "signals_fired":      fired,
        "signals_missed":     missed,
        "signal_count":       len(fired),
        "trade_direction":    trade_direction,
        "position_size_mult": size_mult,
        "size_label":         size_label,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SHORT TRADE LEVELS — compute_levels_short()
# Mirror of compute_levels() with direction inverted.
# Entry at Sq9 resistance. SL above. T1 = next Sq9 support below.
# ══════════════════════════════════════════════════════════════════════════════

def compute_levels_short(
    price:              float,
    risk_pref:          str   = "balanced",
    all_sup:            List[Dict] = None,
    all_res:            List[Dict] = None,
    fourier_sell_price: Optional[float] = None,
    fourier_sell_date:  Optional[str]   = None,
    fourier_buy_price:  Optional[float] = None,
    ml_reversal_price:  Optional[float] = None,
    ml_confidence:      float = 0.0,
    atr14:              float = 0.0,
    analysis_date:      Optional[date] = None,
) -> Dict:
    """
    Compute SHORT trade entry, SL, T1, T2.

    Entry:  At or just below nearest Sq9 RESISTANCE (sell into strength)
    SL:     1×ATR14 ABOVE entry (minimum 1.5%) — exits if price breaks above resistance
    T1:     Next Sq9 SUPPORT below entry (60% exit here)
    T2:     Second Sq9 support or Fourier cycle trough (trail 40% here)
    Trail:  Move SL to breakeven when price drops −1.0% from entry

    T2 HIT = 0 times in 684 BUY trades → trail after T1 instead of hard T2
    """
    all_sup = all_sup or []
    all_res = all_res or []

    sl_pct_map = {"low": 0.015, "balanced": 0.015, "high": 0.020}
    sl_pct     = sl_pct_map.get(risk_pref, 0.015)
    t1_pct_map = {"low": 0.06,  "balanced": 0.08,  "high": 0.10}
    t1_pct     = t1_pct_map.get(risk_pref, 0.08)

    sqp      = math.sqrt(price)
    sq9_ress = [round((sqp + d) ** 2, 2) for d in [0.25, 0.5, 1.0, 1.5, 2.0]]
    sq9_sups = [round(max(0.01, sqp - d) ** 2, 2) for d in [0.25, 0.5, 1.0, 1.5, 2.0, 2.5]]

    # Entry: at Sq9 resistance OR Fourier peak price
    fourier_ok = (fourier_sell_price and
                  price * 0.98 < fourier_sell_price < price * 1.03)
    if fourier_ok:
        entry     = round(fourier_sell_price * 0.999, 2)
        entry_src = f"Fourier cycle peak ₹{fourier_sell_price:,.2f} — SHORT at cycle top"
    elif (ml_reversal_price and ml_confidence > 0.65
          and price * 0.98 < ml_reversal_price < price * 1.03):
        entry     = round(ml_reversal_price * 0.999, 2)
        entry_src = f"ML reversal (SHORT) ₹{entry:,.2f} (conf {ml_confidence:.0%})"
    else:
        # Nearest Sq9 resistance at or above CMP
        _res_above = sorted([r for r in sq9_ress if r >= price * 0.998])
        entry     = round(_res_above[0] * 0.999, 2) if _res_above else round(price * 1.005, 2)
        entry_src = f"Sq9 resistance ₹{entry:,.2f} — SHORT at structural ceiling"

    # SL: ATR-based ABOVE entry
    if atr14 > 0:
        _sl_dist = max(1.0 * atr14, entry * 0.015)
        sl        = round(entry + _sl_dist, 2)
        sl_src    = f"ATR SL 1×ATR14 ₹{atr14:.2f} = ₹{_sl_dist:.2f} above entry ({_sl_dist/entry*100:.1f}%)"
    else:
        sl        = round(entry * (1 + sl_pct), 2)
        sl_src    = f"SHORT SL {sl_pct*100:.1f}% above entry (ATR unavailable)"

    # T1: nearest Sq9 support BELOW entry
    _sq9_below  = sorted([s for s in sq9_sups if s < entry * 0.995], reverse=True)
    _sup_below   = sorted([r["price"] for r in all_sup if r.get("price", 0) < entry * 0.995], reverse=True)
    _t1_cands    = _sq9_below + _sup_below
    t1           = round(max(_t1_cands), 2) if _t1_cands else round(entry * (1 - t1_pct), 2)
    t1_src       = f"Sq9 support ₹{t1:,.2f} — SHORT T1 (exit 60% here)"

    # T2: second Sq9 support below T1 OR Fourier trough
    if fourier_buy_price and fourier_buy_price < t1 * 0.995:
        t2     = round(fourier_buy_price, 2)
        t2_src = f"Fourier cycle trough ₹{t2:,.2f} — SHORT T2 / cover zone"
    else:
        _t2_cands = [s for s in _sq9_below if s < t1 * 0.995]
        t2        = round(max(_t2_cands), 2) if _t2_cands else round(t1 * (1 - t1_pct * 0.6), 2)
        t2_src    = f"Sq9 support 2 ₹{t2:,.2f} — trail SHORT target"

    # Validate
    if sl <= entry:
        sl = round(entry * (1 + sl_pct), 2); sl_src += " [guard]"
    if t1 >= entry * 0.995:
        t1 = round(entry * (1 - t1_pct), 2); t1_src += " [guard]"
    if t2 >= t1 * 0.995:
        t2 = round(t1 * (1 - t1_pct * 0.5), 2); t2_src += " [guard]"

    risk      = round(sl - entry, 2)
    r1        = round(entry - t1, 2)
    r2        = round(entry - t2, 2)
    rr1       = round(r1 / max(risk, 0.01), 2)
    rr2       = round(r2 / max(risk, 0.01), 2)
    downside1 = round((entry - t1) / entry * 100, 1)
    downside2 = round((entry - t2) / entry * 100, 1)

    trail_rule = (
        f"SHORT trail: SL moves to breakeven (entry ₹{entry:,.2f}) when price drops −1.0% to ₹{entry*(1-0.01):,.2f}. "
        f"Exit 60% at T1 ₹{t1:,.2f}. Trail remaining 40%: cover when price rallies 0.8% from any post-T1 low. "
        f"Do NOT set hard T2 — trail captures the full move."
    )

    _rr_note_s = ""
    if rr1 > 1.5:
        _rr_note_s = f"WARNING: RR={rr1:.2f} > 1.5 — 10yr data: WR drops sharply above 1.5 RR. Narrow T1."
    _breakeven_trigger_s = round(entry * (1 - 0.010), 2)  # price drops 1% → move SL to entry
    return {
        "trade_direction": "SHORT",
        "entry":       entry,    "entry_src":  entry_src,
        "sl":          sl,       "sl_src":     sl_src,
        "t1":          t1,       "t1_src":     t1_src,
        "t2":          t2,       "t2_src":     t2_src,
        "risk":        risk,     "reward1":    r1,      "reward2":    r2,
        "rr_ratio":    rr1,      "rr_ratio2":  rr2,
        "downside_t1": downside1,"downside_t2":downside2,
        "trail_rule":  trail_rule,
        "breakeven_trigger_pct": -1.0,
        "breakeven_price":   round(entry, 2),
        "breakeven_trigger": _breakeven_trigger_s,
        "rr_note":           _rr_note_s,
        "rr_quality":        "OPTIMAL" if 1.0 <= rr1 <= 1.5 else "MARGINAL" if rr1 <= 1.75 else "POOR",
    }

# -------------------------------------------------------------
# MASTER INSTITUTIONAL ADVISOR WRAPPER (Phase 4 Completion)
# -------------------------------------------------------------
def get_institutional_decision(symbol: str, current_price: float, atr14: float) -> dict:
    """
    Master entrypoint for AI Advisor and Backtesting.
    Runs the entire 4-phase institutional pipeline natively.
    """
    from core.wavelets import wavelet_cycle_analysis
    from core.regime_model import get_market_regime
    from core.macro_engine import get_macro_regime
    from core.ensemble_ml import compute_dynamic_score
    from core.portfolio_optimizer import calculate_kelly_fraction
    from core.strategy_vwap import get_intraday_vwap_and_profile
    from core.quant_engine import get_price_series
    
    # 1. Fetch fast time-series data
    data = get_price_series(symbol, symbol, years=1)
    if "error" in data or len(data.get("closes", [])) < 60:
        return {"status": "error", "message": "Not enough data"}
        
    closes = data["closes"]
    
    # 2. Run CWT Wavelet cycles
    cwt_res = wavelet_cycle_analysis(closes)
    cwt_score = 0
    if cwt_res.get("dominant_cycles"):
        cwt_score = cwt_res["cycle_strengths"][0]
        
    # 3. Detect HMM Regime
    regime_res = get_market_regime(symbol)
    regime_id = regime_res.get("state_id", 2)
    regime_name = regime_res.get("regime_name", "UNKNOWN")
    
    # 4. Get Macro Regime
    macro_res = get_macro_regime()
    macro_score = 80 if macro_res.get("OVERALL_MACRO") == "RISK_ON" else 20
    
    # 5. Get Intraday VWAP & Profile
    vwap_res = get_intraday_vwap_and_profile(symbol)
    
    # 6. Compute ML Ensemble Score dynamically
    ml_score = compute_dynamic_score(
        scores_dict={'gann': 60, 'quant': cwt_score, 'sentiment': 50, 'macro': macro_score},
        regime_id=regime_id
    )
    
    # 7. Portfolio Risk Optimization (Kelly)
    # Using dynamic ML score as a proxy for win-rate (0.0 to 1.0)
    win_rate = min(max(ml_score / 100.0, 0.3), 0.8)
    kelly_pct = calculate_kelly_fraction(win_rate, avg_win=0.10, avg_loss=0.03)
    
    return {
        "symbol": symbol,
        "current_price": current_price,
        "institutional_score": round(ml_score, 1),
        "hmm_regime": regime_name,
        "macro_bias": macro_res.get("OVERALL_MACRO", "NEUTRAL"),
        "dominant_cycle_cwt": cwt_res.get("dominant_cycles", [0])[0] if cwt_res.get("dominant_cycles") else 0,
        "intraday_vwap": vwap_res.get("vwap", 0),
        "point_of_control": vwap_res.get("poc", 0),
        "recommended_position_size": f"{round(kelly_pct * 100, 1)}%",
        "verdict": "BUY" if ml_score >= 60 else "SELL" if ml_score <= 40 else "HOLD",
        "sl_atr_based": round(current_price - (atr14 * 1.5), 2)
    }
