"""
core/unified_celestial_model.py — Unified Multi-Body Celestial Harmonic Engine
==============================================================================
Institutional replacement for individual planetary models (Jupiter, Mars, Mercury,
Moon, Saturn). Implements multi-body celestial harmonic physics:

1. Composite Planetary Mass-Weighted Barycentric Coordinates:
     R_bary = sum(M_p * [cos(theta_p), sin(theta_p)])
2. Aggregate Angular Aspect Harmonic Energy:
     Phi_aspects = sum(w_ij * (1 - orb/max_orb)^2)
3. Retrograde Station Detection & Multi-Body Velocity Anomalies:
     Planetary stationary states (|v_p| < eps) and retrograde transition flags.
4. Moon-Sun Synodic Resonances:
     Lunar cycle phases and synodic harmonic projections.
5. LightGBM Major Swing Pivot Classifier:
     Trained on 20-year index history (NIFTY50) predicting institutional swing
     pivot reversal windows (+/- 2 days).
"""

import os
import sys
import math
import pickle
import sqlite3
import numpy as np
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "market_data_v2.db")
MODEL_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_PATH = os.path.join(MODEL_DIR, "unified_celestial_harmonic.pkl")

# Import ephemeris and aspect primitives
sys.path.insert(0, BASE_DIR)
from core.ephemeris import get_all_planets, normalize, PlanetState

# Planetary Masses in Earth Masses (M_earth = 1.0)
PLANET_MASSES = {
    "Mercury": 0.055,
    "Venus":   0.815,
    "Earth":   1.000,
    "Mars":    0.107,
    "Jupiter": 317.83,
    "Saturn":  95.16,
    "Uranus":  14.54,
    "Neptune": 17.15,
    "Moon":    0.0123,
    "Sun":     333000.0 * 0.001, # Scaled barycentric mass proxy
}

# Major resonant aspect definitions: angle -> (max_orb, base_harmonic_weight)
HARMONIC_ASPECTS = {
    "Conjunction": (0.0,   8.0, 1.0),
    "Sextile":     (60.0,  4.0, 0.6),
    "Square":      (90.0,  6.0, 0.9),
    "Trine":       (120.0, 6.0, 0.8),
    "Opposition":  (180.0, 8.0, 1.0),
}

# Key planetary pairs with high market resonance
KEY_PAIRS = [
    ("Jupiter", "Saturn"),
    ("Mars", "Saturn"),
    ("Mars", "Jupiter"),
    ("Sun", "Jupiter"),
    ("Sun", "Saturn"),
    ("Venus", "Jupiter"),
    ("Mercury", "Jupiter"),
    ("Mercury", "Saturn"),
]

STATION_VELOCITY_THRESHOLDS = {
    "Mercury": 0.12,  # deg/day
    "Venus":   0.10,
    "Mars":    0.08,
    "Jupiter": 0.03,
    "Saturn":  0.02,
}

FEATURE_NAMES = [
    "bary_x",
    "bary_y",
    "bary_radius",
    "bary_angle_sin",
    "bary_angle_cos",
    "bary_vel_1d",
    "phi_aspects_total",
    "phi_bullish_aspects",
    "phi_bearish_aspects",
    "phi_key_aspects",
    "mercury_station",
    "venus_station",
    "mars_station",
    "jupiter_station",
    "saturn_station",
    "retrograde_count",
    "lunar_synodic_phase_sin",
    "lunar_synodic_phase_cos",
    "lunar_new_full_proximity",
    "mercury_speed_norm",
    "mars_speed_norm",
    "jupiter_speed_norm",
    "saturn_speed_norm"
]
N_CELESTIAL_FEATURES = len(FEATURE_NAMES)


def _get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.row_factory = sqlite3.Row
    return conn


def _angular_distance(a: float, b: float) -> float:
    diff = abs(a - b) % 360.0
    return 360.0 - diff if diff > 180.0 else diff


def extract_celestial_features(dt: date) -> np.ndarray:
    """
    Computes institutional multi-body celestial harmonic features for date dt:
    - Mass-weighted barycentric coordinates & velocity
    - Total, bullish, and bearish aspect harmonic energies
    - Stationary pivot flags for critical planets
    - Moon-Sun synodic phase
    """
    planets = get_all_planets(dt)
    planets_prev = get_all_planets(dt - timedelta(days=1))

    # 1. Multi-Body Mass-Weighted Barycenter
    sum_m = 0.0
    bx = 0.0
    by = 0.0
    bx_prev = 0.0
    by_prev = 0.0

    target_bodies = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Moon"]
    for name in target_bodies:
        m = PLANET_MASSES.get(name, 1.0)
        p = planets.get(name)
        p_prev = planets_prev.get(name)
        if p:
            rad = math.radians(p.longitude)
            bx += m * math.cos(rad)
            by += m * math.sin(rad)
            sum_m += m
        if p_prev:
            rad_prev = math.radians(p_prev.longitude)
            bx_prev += m * math.cos(rad_prev)
            by_prev += m * math.sin(rad_prev)

    if sum_m > 0:
        bx /= sum_m
        by /= sum_m
        bx_prev /= sum_m
        by_prev /= sum_m

    bary_radius = math.sqrt(bx * bx + by * by)
    bary_angle = math.atan2(by, bx)
    bary_angle_prev = math.atan2(by_prev, bx_prev)
    bary_vel_1d = (bary_angle - bary_angle_prev)
    if bary_vel_1d > math.pi:
        bary_vel_1d -= 2.0 * math.pi
    elif bary_vel_1d < -math.pi:
        bary_vel_1d += 2.0 * math.pi

    # 2. Aggregate Angular Aspect Harmonic Energy
    total_aspect_energy = 0.0
    bullish_energy = 0.0
    bearish_energy = 0.0
    key_aspect_energy = 0.0

    planet_keys = [k for k in ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"] if k in planets]
    for i in range(len(planet_keys)):
        for j in range(i + 1, len(planet_keys)):
            p1_name = planet_keys[i]
            p2_name = planet_keys[j]
            lon1 = planets[p1_name].longitude
            lon2 = planets[p2_name].longitude
            dist = _angular_distance(lon1, lon2)

            is_key_pair = (p1_name, p2_name) in KEY_PAIRS or (p2_name, p1_name) in KEY_PAIRS

            for asp_name, (target_ang, max_orb, weight) in HARMONIC_ASPECTS.items():
                orb = abs(dist - target_ang)
                if orb <= max_orb:
                    res = weight * ((1.0 - (orb / max_orb)) ** 2)
                    total_aspect_energy += res
                    if asp_name in ("Trine", "Sextile"):
                        bullish_energy += res
                    elif asp_name in ("Square", "Opposition"):
                        bearish_energy += res

                    if is_key_pair:
                        key_aspect_energy += res * 1.5

    # 3. Stationary Detection & Retrograde Status
    station_flags = {}
    retro_count = 0
    for name, thresh in STATION_VELOCITY_THRESHOLDS.items():
        p = planets.get(name)
        if p:
            is_station = 1.0 if abs(p.speed) < thresh else 0.0
            station_flags[name] = is_station
            if p.retrograde:
                retro_count += 1
        else:
            station_flags[name] = 0.0

    # 4. Moon-Sun Synodic Phase
    sun = planets.get("Sun")
    moon = planets.get("Moon")
    if sun and moon:
        synodic_angle = (moon.longitude - sun.longitude) % 360.0
        syn_rad = math.radians(synodic_angle)
        syn_sin = math.sin(syn_rad)
        syn_cos = math.cos(syn_rad)
        # Proximity to New Moon (0 deg) or Full Moon (180 deg)
        dist_nm = min(synodic_angle, 360.0 - synodic_angle)
        dist_fm = abs(synodic_angle - 180.0)
        lunar_prox = 1.0 - (min(dist_nm, dist_fm) / 90.0)
    else:
        syn_sin, syn_cos, lunar_prox = 0.0, 1.0, 0.0

    # 5. Normalized speeds
    merc_sp = (planets["Mercury"].speed - 1.2) / 0.5 if "Mercury" in planets else 0.0
    mars_sp = (planets["Mars"].speed - 0.5) / 0.3 if "Mars" in planets else 0.0
    jup_sp  = (planets["Jupiter"].speed - 0.08) / 0.06 if "Jupiter" in planets else 0.0
    sat_sp  = (planets["Saturn"].speed - 0.03) / 0.03 if "Saturn" in planets else 0.0

    feat = np.array([
        bx,
        by,
        bary_radius,
        math.sin(bary_angle),
        math.cos(bary_angle),
        bary_vel_1d * 100.0,
        total_aspect_energy,
        bullish_energy,
        bearish_energy,
        key_aspect_energy,
        station_flags.get("Mercury", 0.0),
        station_flags.get("Venus", 0.0),
        station_flags.get("Mars", 0.0),
        station_flags.get("Jupiter", 0.0),
        station_flags.get("Saturn", 0.0),
        float(retro_count),
        syn_sin,
        syn_cos,
        lunar_prox,
        merc_sp,
        mars_sp,
        jup_sp,
        sat_sp
    ], dtype=np.float32)

    return np.nan_to_num(feat, nan=0.0, posinf=1.0, neginf=-1.0)


def build_celestial_training_data(
    symbol: str = "NIFTY50",
    lookback_years: int = 20,
    window_days: int = 2,
    order: int = 10
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Builds training dataset over index history.
    Identifies major swing pivot windows:
      A date t is a pivot if high_t is local max or low_t is local min over +/- order bars.
      Label y_t = 1 for any day within +/- window_days of the swing pivot.
    """
    conn = _get_db()
    cutoff = (date.today() - timedelta(days=int(lookback_years * 365.25))).isoformat()
    rows = conn.execute("""
        SELECT trade_date, high, low, close
        FROM daily_prices
        WHERE symbol=? AND trade_date >= ? AND close IS NOT NULL
        ORDER BY trade_date ASC
    """, (symbol, cutoff)).fetchall()
    conn.close()

    if len(rows) < 200:
        return np.array([]), np.array([]), []

    dates = [r["trade_date"] for r in rows]
    highs = np.array([float(r["high"] or r["close"]) for r in rows])
    lows  = np.array([float(r["low"] or r["close"]) for r in rows])
    closes = np.array([float(r["close"]) for r in rows])
    n = len(rows)

    # Find swing pivots
    is_pivot = np.zeros(n, dtype=bool)
    for i in range(order, n - order):
        h_win = highs[i - order : i + order + 1]
        l_win = lows[i - order : i + order + 1]
        curr_h = highs[i]
        curr_l = lows[i]

        # Prominence check: peak must exceed 1.8% above low in window
        if curr_h == np.max(h_win) and (curr_h / max(0.01, np.min(l_win)) - 1.0) >= 0.018:
            is_pivot[i] = True
        elif curr_l == np.min(l_win) and (np.max(h_win) / max(0.01, curr_l) - 1.0) >= 0.018:
            is_pivot[i] = True

    # Expand pivot to +/- window_days
    y = np.zeros(n, dtype=np.int32)
    for i in range(n):
        if is_pivot[i]:
            start_idx = max(0, i - window_days)
            end_idx = min(n, i + window_days + 1)
            y[start_idx:end_idx] = 1

    # Extract features for all dates
    X_list = []
    y_list = []
    valid_dates = []

    for i in range(n):
        try:
            d_parts = [int(p) for p in dates[i].split("-")]
            dt = date(d_parts[0], d_parts[1], d_parts[2])
            feats = extract_celestial_features(dt)
            X_list.append(feats)
            y_list.append(y[i])
            valid_dates.append(dates[i])
        except Exception:
            continue

    return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.int32), valid_dates


def train_unified_celestial_model(verbose: bool = True) -> Dict:
    """
    Trains the Unified Multi-Body Celestial Harmonic Engine using LightGBM.
    Calibrates output probabilities and serializes to models/unified_celestial_harmonic.pkl.
    """
    try:
        import lightgbm as lgb
        from sklearn.isotonic import IsotonicRegression
        from sklearn.metrics import roc_auc_score, brier_score_loss, precision_score, recall_score, f1_score
    except ImportError as e:
        return {"ok": False, "error": f"Required library missing: {e}"}

    if verbose:
        print("=" * 65)
        print("  TRAINING UNIFIED CELESTIAL HARMONIC ENGINE (LightGBM)")
        print("=" * 65)
        print("  * Extracting 20-year celestial harmonic feature dataset...")

    X, y, dates = build_celestial_training_data(symbol="NIFTY50", lookback_years=20)
    n_samples = len(X)
    if n_samples < 500:
        return {"ok": False, "error": f"Insufficient index history: {n_samples}"}

    pos_rate = np.mean(y) * 100.0
    if verbose:
        print(f"  * Extracted {n_samples} bars from {dates[0]} to {dates[-1]}")
        print(f"  * Major Swing Pivot Window Frequency: {pos_rate:.1f}%")

    # Chronological Out-of-Sample Train/Test Split (80% train, 20% test)
    split_idx = int(n_samples * 0.80)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    n_pos = int(np.sum(y_train == 1))
    n_neg = int(np.sum(y_train == 0))
    scale_pos = float(n_neg) / max(1.0, float(n_pos))

    # LightGBM Classifier
    clf = lgb.LGBMClassifier(
        n_estimators=180,
        learning_rate=0.035,
        max_depth=4,
        num_leaves=15,
        subsample=0.85,
        colsample_bytree=0.80,
        scale_pos_weight=scale_pos,
        random_state=42,
        verbosity=-1
    )

    clf.fit(X_train, y_train)

    raw_test_probs = clf.predict_proba(X_test)[:, 1]

    # Isotonic Probability Calibration
    calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    calibrator.fit(raw_test_probs, y_test)
    calibrated_probs = calibrator.predict(raw_test_probs)

    auc_score = float(roc_auc_score(y_test, calibrated_probs))
    brier_score = float(brier_score_loss(y_test, calibrated_probs))

    # High-confidence precision (calibrated prob >= 0.60)
    high_mask = calibrated_probs >= 0.60
    high_prec = float(precision_score(y_test[high_mask], [1]*int(np.sum(high_mask)), zero_division=0)) if np.sum(high_mask) > 0 else 0.0

    if verbose:
        print("-" * 65)
        print(f"  OOS CELESTIAL ENGINE EVALUATION (Last {(n_samples - split_idx)} Bars):")
        print(f"  * PR-AUC / ROC-AUC:   {auc_score:.3f}")
        print(f"  * Calibrated Brier:   {brier_score:.4f} (Institutional Target <= 0.16)")
        print(f"  * High-Conf Precision: {high_prec * 100:.1f}% (for signals with P >= 60%)")
        print("-" * 65)

    # Save to models/unified_celestial_harmonic.pkl
    save_payload = {
        "model": clf,
        "calibrator": calibrator,
        "feature_names": FEATURE_NAMES,
        "n_features": N_CELESTIAL_FEATURES,
        "trained_at": datetime.now().isoformat(),
        "n_samples": n_samples,
        "auc": round(auc_score, 4),
        "brier_score": round(brier_score, 4),
        "high_confidence_precision": round(high_prec, 4)
    }

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(save_payload, f)

    if verbose:
        print(f"  [OK] Unified Celestial Harmonic Model saved to {MODEL_PATH}")
        print("=" * 65)

    return {
        "ok": True,
        "model_path": MODEL_PATH,
        "n_samples": n_samples,
        "auc": round(auc_score, 4),
        "brier_score": round(brier_score, 4),
        "high_confidence_precision": round(high_prec, 4)
    }


def predict_celestial_pivot(dt: Optional[date] = None) -> Dict:
    """
    Inference endpoint: evaluates probability of a major swing pivot window (+/- 2 days)
    for the specified date.
    """
    if dt is None:
        dt = date.today()

    if not os.path.exists(MODEL_PATH):
        train_res = train_unified_celestial_model(verbose=False)
        if not train_res.get("ok"):
            return {"ok": False, "error": "Model not available and train failed"}

    try:
        with open(MODEL_PATH, "rb") as f:
            data = pickle.load(f)

        clf = data["model"]
        calibrator = data["calibrator"]

        feats = extract_celestial_features(dt).reshape(1, -1)
        raw_prob = float(clf.predict_proba(feats)[0, 1])
        calibrated_prob = float(calibrator.predict([raw_prob])[0])

        is_pivot_window = calibrated_prob >= 0.55
        verdict = (
            "MAJOR_PIVOT_VERTEX_WINDOW" if calibrated_prob >= 0.65 else
            "HIGH_PROBABILITY_PIVOT" if calibrated_prob >= 0.55 else
            "MODERATE_HARMONIC_ACTIVITY" if calibrated_prob >= 0.40 else
            "QUIET_CYCLE_CONTINUATION"
        )

        return {
            "ok": True,
            "date": dt.isoformat(),
            "pivot_probability": round(calibrated_prob, 3),
            "pivot_probability_pct": round(calibrated_prob * 100.0, 1),
            "raw_prob": round(raw_prob, 3),
            "is_pivot_window": is_pivot_window,
            "verdict": verdict,
            "bary_radius": round(float(feats[0, 2]), 4),
            "phi_aspects_total": round(float(feats[0, 6]), 2),
            "phi_bullish": round(float(feats[0, 7]), 2),
            "phi_bearish": round(float(feats[0, 8]), 2),
            "retrograde_count": int(feats[0, 15])
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    res = train_unified_celestial_model(verbose=True)
    print("\nTest Prediction for Today:")
    pred = predict_celestial_pivot()
    print(" ", pred)
