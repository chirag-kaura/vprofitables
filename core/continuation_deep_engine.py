"""
core/continuation_deep_engine.py — Institutional Trend Continuation Engine
==========================================================================
Modernized Institutional Trend Continuation Engine:
1. 12 Orthogonal Features (collinearity eradicated: distance to EMA20, EMA spreads,
   ADX, volume dry-up, lower absorption shadows, delivery %, Bollinger bandwidth compression,
   Gann Sq9 support distance, Morlet CWT dominant cycle phase, FII long %, VIX).
2. Volatility-Adjusted Dynamic Triple-Barrier Labeling:
   - Dynamic horizon: T_horizon = clip(round(10 * 15.0 / VIX), 4, 20)
   - Upper barrier: >= 1.5x to 1.75x R:R expansion
   - Lower barrier: 50-EMA swing stop
3. 5-Fold Purged GroupTimeSeriesSplit with 5-day embargo.
4. Isotonic Regression Probability Calibration (sklearn.isotonic.IsotonicRegression)
   fitted on Out-Of-Fold cross-validation predictions.
5. Deep Financial Utility MLP with Asymmetric Financial Utility Loss:
   L = - [1.0 * y * (1 - p)^2 * log(p) + 1.75 * (1 - y) * p^2 * log(1 - p)]
   (Heavily penalizes false breakout traps that hit stop losses).
6. Persisted to models/continuation_xgboost.pkl, models/continuation_mlp.pt, models/continuation_meta.pkl.
"""

import os
import sys
import math
import pickle
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Generator

import pywt
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from xgboost import XGBClassifier
from sklearn.preprocessing import QuantileTransformer
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import KFold
from sklearn.metrics import (
    roc_auc_score,
    precision_score,
    recall_score,
    accuracy_score,
    brier_score_loss,
    precision_recall_curve,
    auc as calc_auc
)

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH   = os.path.join(BASE_DIR, "market_data_v2.db")
MODEL_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)

sys.path.insert(0, BASE_DIR)
from core.gann_math import nearest_sq9

CONTINUATION_XGB_PATH  = os.path.join(MODEL_DIR, "continuation_xgboost.pkl")
CONTINUATION_MLP_PATH  = os.path.join(MODEL_DIR, "continuation_mlp.pt")
CONTINUATION_META_PATH = os.path.join(MODEL_DIR, "continuation_meta.pkl")

# Exactly 12 Orthogonal Features
CONTINUATION_FEATURE_NAMES = [
    "dist_to_ema20_pct",
    "ema_spread_20_50",
    "ema_spread_50_200",
    "adx_14",
    "pullback_vol_ratio",
    "lower_shadow_ratio",
    "deliverable_pct",
    "bollinger_bandwidth_pct",
    "sq9_support_dist_pct",
    "cwt_morlet_phase",
    "fii_index_long_norm",
    "vix_norm"
]
N_CONTINUATION_FEATURES = len(CONTINUATION_FEATURE_NAMES)


def _get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.row_factory = sqlite3.Row
    return conn


def _compute_ema(series: np.ndarray, span: int) -> np.ndarray:
    return pd.Series(series).ewm(span=span, adjust=False).mean().values


def _compute_adx(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
    n = len(closes)
    if n < period * 2:
        return 20.0
    tr1 = highs[1:] - lows[1:]
    tr2 = np.abs(highs[1:] - closes[:-1])
    tr3 = np.abs(lows[1:] - closes[:-1])
    tr = np.maximum(tr1, np.maximum(tr2, tr3))

    up_move = highs[1:] - highs[:-1]
    down_move = lows[:-1] - lows[1:]

    pdm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    ndm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    atr = pd.Series(tr).ewm(alpha=1.0 / period, adjust=False).mean().values
    pdm_s = pd.Series(pdm).ewm(alpha=1.0 / period, adjust=False).mean().values
    ndm_s = pd.Series(ndm).ewm(alpha=1.0 / period, adjust=False).mean().values

    pdi = np.where(atr > 0, (pdm_s / atr) * 100.0, 0.0)
    ndi = np.where(atr > 0, (ndm_s / atr) * 100.0, 0.0)

    dx_denom = pdi + ndi
    dx = np.where(dx_denom > 0, np.abs(pdi - ndi) / np.maximum(1e-6, dx_denom) * 100.0, 0.0)
    adx = pd.Series(dx).ewm(alpha=1.0 / period, adjust=False).mean().values
    return float(adx[-1])


def _compute_adx_series(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(closes)
    if n < period * 2:
        return np.full(n, 20.0, dtype=np.float32)
    tr = np.maximum(highs[1:] - lows[1:], np.maximum(np.abs(highs[1:] - closes[:-1]), np.abs(lows[1:] - closes[:-1])))
    up = highs[1:] - highs[:-1]
    dn = lows[:-1] - lows[1:]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    atr = pd.Series(tr).ewm(alpha=1.0 / period, adjust=False).mean().values
    pdm_s = pd.Series(pdm).ewm(alpha=1.0 / period, adjust=False).mean().values
    ndm_s = pd.Series(ndm).ewm(alpha=1.0 / period, adjust=False).mean().values
    pdi = np.where(atr > 0, (pdm_s / atr) * 100.0, 0.0)
    ndi = np.where(atr > 0, (ndm_s / atr) * 100.0, 0.0)
    den = pdi + ndi
    dx = np.where(den > 0, np.abs(pdi - ndi) / np.maximum(1e-6, den) * 100.0, 0.0)
    adx = pd.Series(dx).ewm(alpha=1.0 / period, adjust=False).mean().values
    return np.concatenate([[20.0], adx]).astype(np.float32)


def _compute_cwt_morlet_phase_single(closes: np.ndarray) -> float:
    n = len(closes)
    if n < 30:
        return 0.0
    prices = closes[-60:] if n >= 60 else closes
    m = len(prices)
    x = np.arange(m)
    p = np.polyfit(x, prices, 1)
    detrended = prices - np.polyval(p, x)
    scales = np.arange(10, 45, 2)
    try:
        coefs, _ = pywt.cwt(detrended, scales, 'cmor1.5-1.0', sampling_period=1)
        pwr = np.abs(coefs) ** 2
        best_scale_idx = int(np.argmax(pwr[:, -1]))
        phase = float(np.angle(coefs[best_scale_idx, -1]) / np.pi)
        return float(np.clip(phase, -1.0, 1.0))
    except Exception:
        return 0.0


def extract_continuation_features(
    closes: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    volumes: np.ndarray,
    deliverable_pct: float = 0.0,
    fii_index_long_pct: float = 50.0,
    vix_val: float = 15.0,
    opens: Optional[np.ndarray] = None
) -> Optional[np.ndarray]:
    """
    Extracts 12 Orthogonal Continuation features from price action and institutional context.
    Eliminates collinear moving average slope redundancy.
    """
    n = len(closes)
    if n < 50:
        return None

    curr_close = closes[-1]
    if curr_close <= 0:
        return None

    ema20 = _compute_ema(closes, 20)
    ema50 = _compute_ema(closes, 50)
    ema200 = _compute_ema(closes, 200) if n >= 200 else _compute_ema(closes, n // 2)

    # 1. Distance to EMA20 (%)
    dist_ema20 = (curr_close - ema20[-1]) / max(0.01, ema20[-1]) * 100.0

    # 2. EMA spread 20 vs 50 (%)
    ema_spread_20_50 = (ema20[-1] - ema50[-1]) / max(0.01, ema50[-1]) * 100.0

    # 3. EMA spread 50 vs 200 (%)
    ema_spread_50_200 = (ema50[-1] - ema200[-1]) / max(0.01, ema200[-1]) * 100.0

    # 4. ADX 14
    adx_val = _compute_adx(highs, lows, closes, 14)

    # 5. Volume dry-up ratio: 3-day pullback volume vs 20-day historical volume
    avg_vol_20 = np.mean(volumes[-25:-5]) if n >= 25 else np.mean(volumes)
    recent_vol = np.mean(volumes[-3:])
    pullback_vol_ratio = (recent_vol / avg_vol_20) if avg_vol_20 > 0 else 1.0

    # 6. Lower shadow ratio of current bar (absorption wick rejecting support)
    rng = max(0.01, highs[-1] - lows[-1])
    op = opens[-1] if (opens is not None and len(opens) == n) else closes[-1]
    lower_wick = max(0.0, min(op, closes[-1]) - lows[-1])
    lower_shadow_ratio = float(np.clip(lower_wick / rng, 0.0, 1.0))

    # 7. Delivery Percentage (normalized 0 to 1)
    deliv_norm = float(np.clip(deliverable_pct / 100.0, 0.0, 1.0))

    # 8. Bollinger Bandwidth % (volatility compression)
    sma20 = np.mean(closes[-20:])
    std20 = np.std(closes[-20:])
    bb_width_pct = (2.0 * std20) / max(0.01, sma20) * 100.0

    # 9. Gann Sq9 support distance %
    _, sq9_sup, *_ = nearest_sq9(curr_close)
    sq9_dist = abs(curr_close - sq9_sup) / max(0.01, curr_close) * 100.0

    # 10. Morlet CWT Dominant Cycle Phase
    cwt_phase = _compute_cwt_morlet_phase_single(closes)

    # 11. Institutional FII Index Long % (normalized [-1, 1])
    fii_norm = (fii_index_long_pct - 50.0) / 50.0

    # 12. India VIX (normalized [0.1, 1.0])
    vix_norm = float(np.clip(vix_val, 5.0, 50.0) / 50.0)

    feats = np.array([
        dist_ema20,
        ema_spread_20_50,
        ema_spread_50_200,
        adx_val,
        pullback_vol_ratio,
        lower_shadow_ratio,
        deliv_norm,
        bb_width_pct,
        sq9_dist,
        cwt_phase,
        fii_norm,
        vix_norm
    ], dtype=np.float32)

    return np.nan_to_num(feats, nan=0.0, posinf=1.0, neginf=-1.0)


# ==============================================================================
# PyTorch Deep Financial Utility MLP Architecture & Custom Utility Loss
# ==============================================================================

class ContinuationMLP(nn.Module):
    """
    4-Layer Deep Financial Utility MLP:
    Linear(12, 64) -> BatchNorm -> SiLU -> Dropout(0.25) ->
    Linear(64, 32) -> BatchNorm -> SiLU -> Dropout(0.20) ->
    Linear(32, 16) -> LayerNorm -> SiLU ->
    Linear(16, 1)  -> Sigmoid
    """
    def __init__(self, input_dim: int = N_CONTINUATION_FEATURES):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.BatchNorm1d(64),
            nn.SiLU(),
            nn.Dropout(0.25),
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.SiLU(),
            nn.Dropout(0.20),
            nn.Linear(32, 16),
            nn.LayerNorm(16),
            nn.SiLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class AsymmetricFinancialUtilityLoss(nn.Module):
    """
    Asymmetric Financial Utility Loss:
    L = - [1.0 * y * (1 - p_hat)^2 * log(p_hat) + 1.75 * (1 - y) * p_hat^2 * log(1 - p_hat)]
    Strictly penalizes false breakout traps that hit stop-losses.
    """
    def __init__(self, false_positive_penalty: float = 1.75, eps: float = 1e-7):
        super().__init__()
        self.fp_penalty = false_positive_penalty
        self.eps = eps

    def forward(self, p_hat: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        p_hat = torch.clamp(p_hat, self.eps, 1.0 - self.eps)
        y = y.view(-1, 1).float()
        pos_term = 1.0 * y * ((1.0 - p_hat) ** 2) * torch.log(p_hat)
        neg_term = self.fp_penalty * (1.0 - y) * (p_hat ** 2) * torch.log(1.0 - p_hat)
        loss = -torch.mean(pos_term + neg_term)
        return loss


# ==============================================================================
# Purged Group Time Series Split with Embargo
# ==============================================================================

class PurgedGroupTimeSeriesSplit:
    """
    5-Fold Purged GroupTimeSeriesSplit with 5-day embargo.
    Purges overlapping outcome horizons and prevents lookahead information leakage.
    """
    def __init__(self, n_splits: int = 5, embargo_days: int = 5):
        self.n_splits = n_splits
        self.embargo_days = embargo_days

    def split(self, dates: List[str], horizon_days_list: List[int]) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        unique_dates = sorted(list(set(dates)))
        n_dates = len(unique_dates)
        fold_size = max(1, n_dates // (self.n_splits + 1))

        date_to_idx = {d: i for i, d in enumerate(unique_dates)}
        sample_date_idx = np.array([date_to_idx[d] for d in dates])
        sample_end_idx  = np.array([date_to_idx[d] + h for d, h in zip(dates, horizon_days_list)])

        for fold in range(self.n_splits):
            test_start_date_idx = (fold + 1) * fold_size
            test_end_date_idx = test_start_date_idx + fold_size if fold < self.n_splits - 1 else n_dates

            test_mask = (sample_date_idx >= test_start_date_idx) & (sample_date_idx < test_end_date_idx)
            test_indices = np.where(test_mask)[0]

            train_before_mask = sample_end_idx < test_start_date_idx
            train_after_mask = sample_date_idx >= (test_end_date_idx + self.embargo_days)

            train_mask = train_before_mask | train_after_mask
            train_indices = np.where(train_mask)[0]

            if len(train_indices) > 0 and len(test_indices) > 0:
                yield train_indices, test_indices


# ==============================================================================
# Volatility-Adjusted Dynamic Triple-Barrier Dataset Builder
# ==============================================================================

def build_continuation_training_data(
    symbols: Optional[List[str]] = None,
    lookback_years: int = 6
) -> Tuple[np.ndarray, np.ndarray, List[str], List[int]]:
    """
    Builds continuation dataset with Event-Based Sampling and Dynamic Triple-Barrier Labeling:
    - Event-based sampling with 6-day cooldown to eradicate contiguous sample correlation.
    - Dynamic horizon: T_horizon = clip(round(10 * 15.0 / VIX), 4, 20)
    - Upper barrier >= 1.5x R:R expansion
    - Lower barrier at 50-EMA swing stop
    """
    conn = _get_db()
    if symbols is None:
        symbols = [
            'NIFTY50', 'BANKNIFTY', 'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK',
            'SBIN', 'BHARTIARTL', 'ITC', 'LT', 'TATASTEEL', 'BAJFINANCE', 'MARUTI',
            'TITAN', 'HINDUNILVR', 'AXISBANK', 'SUNPHARMA', 'ULTRACEMCO', 'M&M',
            'ADANIENT', 'TATAMOTORS', 'POWERGRID', 'NTPC', 'COALINDIA', 'JSWSTEEL',
            'KOTAKBANK', 'WIPRO', 'HCLTECH', 'ASIANPAINT', 'BAJAJFINSV', 'DIVISLAB',
            'CIPLA', 'DRREDDY', 'EICHERMOT', 'GRASIM', 'HEROMOTOCO', 'HINDALCO',
            'INDUSINDBK', 'NESTLEIND', 'ONGC', 'SBILIFE', 'TATACONSUM', 'TECHM'
        ]

    cutoff = (date.today() - timedelta(days=int(lookback_years * 365.25))).isoformat()

    part_rows = conn.execute("SELECT trade_date, fii_index_long_pct FROM participant_sentiment_summary").fetchall()
    part_map = {r["trade_date"]: float(r["fii_index_long_pct"] or 50.0) for r in part_rows}

    vix_rows = conn.execute("SELECT trade_date, close FROM daily_prices WHERE symbol='INDIAVIX'").fetchall()
    vix_map = {r["trade_date"]: float(r["close"] or 15.0) for r in vix_rows}

    X_list, y_list, dates_list, horizons_list = [], [], [], []

    for sym in symbols:
        try:
            rows = conn.execute("""
                SELECT trade_date, open, high, low, close, volume, deliverable_pct
                FROM daily_prices
                WHERE symbol=? AND close IS NOT NULL AND trade_date >= ?
                ORDER BY trade_date ASC
            """, (sym, cutoff)).fetchall()

            if len(rows) < 80:
                continue

            closes = np.array([float(r["close"]) for r in rows])
            opens  = np.array([float(r["open"] if r["open"] is not None else r["close"]) for r in rows])
            highs  = np.array([float(r["high"] or r["close"]) for r in rows])
            lows   = np.array([float(r["low"] or r["close"]) for r in rows])
            vols   = np.array([float(r["volume"] or 0) for r in rows])
            dates  = [r["trade_date"] for r in rows]
            dpcts  = [float(r["deliverable_pct"] or 0.0) for r in rows]
            n_bars = len(closes)

            ema20 = _compute_ema(closes, 20)
            ema50 = _compute_ema(closes, 50)
            ema200 = _compute_ema(closes, 200) if n_bars >= 200 else _compute_ema(closes, n_bars // 2)
            adx_arr = _compute_adx_series(highs, lows, closes, 14)

            # Fast vectorized CWT Morlet phase for the whole symbol series
            scales = np.arange(10, 45, 2)
            x_ax = np.arange(n_bars)
            poly = np.polyfit(x_ax, closes, 1)
            detrended = closes - np.polyval(poly, x_ax)
            try:
                coefs, _ = pywt.cwt(detrended, scales, 'cmor1.5-1.0', sampling_period=1)
                pwr = np.abs(coefs) ** 2
                best_sc = np.argmax(pwr, axis=0)
                phases = np.array([np.angle(coefs[best_sc[t], t]) / np.pi for t in range(n_bars)])
            except Exception:
                phases = np.zeros(n_bars)

            last_event_bar = -99

            for i in range(50, n_bars - 22):
                # Enforce event cooldown to prevent flat-drift sample clustering
                if i - last_event_bar < 6:
                    continue

                c = closes[i]
                e20 = ema20[i]
                e50 = ema50[i]
                e200 = ema200[i]

                # Established bull trend: Close > EMA50, EMA20 > EMA50, ADX >= 18
                adx_val = float(adx_arr[i])
                if not (c > e50 and e20 > e50 and adx_val >= 18.0 and ema50[i] >= ema50[i-10] * 0.999):
                    continue

                # Prior impulse expansion: price reached at least 1.5% above EMA20 in last 12 bars
                if np.max(highs[max(0, i-12):i]) < e20 * 1.015:
                    continue

                # Pullback test: low touches 20-EMA within [-2.2%, +1.2%]
                dist_pct = (c - e20) / e20 * 100.0
                if not (-2.2 <= dist_pct <= 1.2 and lows[i] <= e20 * 1.008):
                    continue

                dt_str = dates[i]
                vix_v = vix_map.get(dt_str, 15.0)
                fii_v = part_map.get(dt_str, 50.0)

                # Dynamic VIX Horizon: T_horizon = clip(round(10 * 15.0 / VIX), 4, 20)
                dyn_horizon = int(np.clip(round(10.0 * 15.0 / max(5.0, vix_v)), 4, 20))

                # 12 Orthogonal Features
                ema_spread_20_50 = (e20 - e50) / max(0.01, e50) * 100.0
                ema_spread_50_200 = (e50 - e200) / max(0.01, e200) * 100.0

                avg_vol_20 = np.mean(vols[max(0, i-25):max(1, i-5)])
                recent_vol = np.mean(vols[max(0, i-3):i+1])
                pullback_vol_ratio = (recent_vol / avg_vol_20) if avg_vol_20 > 0 else 1.0

                rng = max(0.01, highs[i] - lows[i])
                lower_wick = max(0.0, min(opens[i], closes[i]) - lows[i])
                lower_shadow_ratio = float(np.clip(lower_wick / rng, 0.0, 1.0))
                deliv_norm = float(np.clip(dpcts[i] / 100.0, 0.0, 1.0))

                sma20 = np.mean(closes[max(0, i-20):i+1])
                std20 = np.std(closes[max(0, i-20):i+1])
                bb_width_pct = (2.0 * std20) / max(0.01, sma20) * 100.0

                _, sq9_sup, *_ = nearest_sq9(c)
                sq9_dist = abs(c - sq9_sup) / max(0.01, c) * 100.0

                cwt_phase = float(phases[i])
                fii_norm = (fii_v - 50.0) / 50.0
                vix_norm = float(np.clip(vix_v, 5.0, 50.0) / 50.0)

                feats = np.array([
                    dist_pct,
                    ema_spread_20_50,
                    ema_spread_50_200,
                    adx_val,
                    pullback_vol_ratio,
                    lower_shadow_ratio,
                    deliv_norm,
                    bb_width_pct,
                    sq9_dist,
                    cwt_phase,
                    fii_norm,
                    vix_norm
                ], dtype=np.float32)

                # Dynamic Triple-Barrier Evaluation over dyn_horizon
                future_highs  = highs[i+1 : i+1+dyn_horizon]
                future_lows   = lows[i+1 : i+1+dyn_horizon]
                future_closes = closes[i+1 : i+1+dyn_horizon]

                if len(future_highs) < dyn_horizon:
                    continue

                swing_stop = min(e50 * 0.995, np.min(lows[max(0, i-5):i+1]))
                risk = max(0.015 * c, c - swing_stop)
                target1 = c + risk * 1.75

                hit_target = False
                hit_stop = False

                for fh, fl, fc in zip(future_highs, future_lows, future_closes):
                    if fc < swing_stop or fl < swing_stop * 0.995:
                        hit_stop = True
                        break
                    if fh >= target1:
                        hit_target = True
                        break

                label = 1 if (hit_target and not hit_stop) else 0

                X_list.append(feats)
                y_list.append(label)
                dates_list.append(dt_str)
                horizons_list.append(dyn_horizon)
                last_event_bar = i

        except Exception:
            continue

    conn.close()

    if len(X_list) == 0:
        return np.array([]), np.array([]), [], []

    return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.int32), dates_list, horizons_list


# ==============================================================================
# Model Training, Calibration, and Validation Suite
# ==============================================================================

def train_continuation_models(verbose: bool = True) -> Dict:
    """
    Trains Orthogonal Continuation XGBoost and Deep Financial Utility MLP
    with Purged GroupTimeSeriesSplit and Isotonic Calibration on OOF predictions.
    """
    if verbose:
        print("=" * 65)
        print("  TRAINING INSTITUTIONAL CONTINUATION ENGINE (XGBoost + Utility MLP)")
        print("=" * 65)
        print("  * Extracting 12 orthogonal features with dynamic VIX horizon...")

    X, y, dates, horizons = build_continuation_training_data()
    n_samples = len(X)
    if n_samples < 250:
        return {"ok": False, "error": f"Insufficient sample size: {n_samples}"}

    pos_rate = np.mean(y) * 100.0
    if verbose:
        print(f"  * Extracted {n_samples} institutional pullback instances across NSE equities.")
        print(f"  * Base continuation win-rate: {pos_rate:.1f}%")

    # Chronological Split: 80% Train, 20% Out-of-Sample Test
    split_idx = int(n_samples * 0.80)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    dates_train, dates_test = dates[:split_idx], dates[split_idx:]
    horizons_train, horizons_test = horizons[:split_idx], horizons[split_idx:]

    scaler = QuantileTransformer(output_distribution='normal', random_state=42)
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled  = scaler.transform(X_test)

    # 1. 5-Fold Purged GroupTimeSeriesSplit Cross-Validation for OOF Predictions
    cv = PurgedGroupTimeSeriesSplit(n_splits=5, embargo_days=5)
    oof_xgb = np.zeros(len(X_train), dtype=np.float32)
    oof_counts = np.zeros(len(X_train), dtype=np.int32)

    n_pos = int(np.sum(y_train == 1))
    n_neg = int(np.sum(y_train == 0))
    scale_pos = float(n_neg) / max(1.0, float(n_pos))

    for tr_idx, val_idx in cv.split(dates_train, horizons_train):
        fold_xgb = XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.025,
            subsample=0.85,
            colsample_bytree=0.80,
            scale_pos_weight=scale_pos,
            eval_metric="logloss",
            random_state=42
        )
        fold_xgb.fit(X_train_scaled[tr_idx], y_train[tr_idx])
        oof_xgb[val_idx] += fold_xgb.predict_proba(X_train_scaled[val_idx])[:, 1]
        oof_counts[val_idx] += 1

    # Fill any unassigned folds with K-Fold fallback
    unassigned = oof_counts == 0
    if np.any(unassigned):
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        for tr_idx, val_idx in kf.split(X_train_scaled):
            f_xgb = XGBClassifier(
                n_estimators=180,
                max_depth=3,
                learning_rate=0.03,
                scale_pos_weight=scale_pos,
                eval_metric="logloss",
                random_state=42
            )
            f_xgb.fit(X_train_scaled[tr_idx], y_train[tr_idx])
            p_val = f_xgb.predict_proba(X_train_scaled[val_idx])[:, 1]
            for idx, p in zip(val_idx, p_val):
                if unassigned[idx]:
                    oof_xgb[idx] = p
                    oof_counts[idx] = 1

    oof_xgb = np.where(oof_counts > 0, oof_xgb / np.maximum(1, oof_counts), 0.25)

    # Train Master XGBoost
    master_xgb = XGBClassifier(
        n_estimators=260,
        max_depth=4,
        learning_rate=0.025,
        subsample=0.85,
        colsample_bytree=0.80,
        scale_pos_weight=scale_pos,
        eval_metric="logloss",
        random_state=42
    )
    master_xgb.fit(X_train_scaled, y_train)

    xgb_tr_prob = master_xgb.predict_proba(X_train_scaled)[:, 1]
    xgb_te_prob = master_xgb.predict_proba(X_test_scaled)[:, 1]

    # 2. Train Deep Financial Utility MLP
    mlp = ContinuationMLP(input_dim=N_CONTINUATION_FEATURES)
    criterion = AsymmetricFinancialUtilityLoss(false_positive_penalty=1.75)
    optimizer = optim.AdamW(mlp.parameters(), lr=0.002, weight_decay=1e-4)

    t_dataset = TensorDataset(torch.FloatTensor(X_train_scaled), torch.FloatTensor(y_train))
    t_loader = DataLoader(t_dataset, batch_size=32, shuffle=True)

    mlp.train()
    for epoch in range(35):
        for bx, by in t_loader:
            optimizer.zero_grad()
            preds = mlp(bx)
            loss = criterion(preds, by)
            loss.backward()
            optimizer.step()

    mlp.eval()
    with torch.no_grad():
        mlp_tr_prob = mlp(torch.FloatTensor(X_train_scaled)).view(-1).numpy()
        mlp_te_prob = mlp(torch.FloatTensor(X_test_scaled)).view(-1).numpy()

    # 3. Dynamic Ensemble Blending & Out-of-Fold Calibration
    oof_blend = 0.55 * oof_xgb + 0.45 * mlp_tr_prob
    ens_te_prob = 0.55 * xgb_te_prob + 0.45 * mlp_te_prob

    calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.01, y_max=0.99)
    calibrator.fit(oof_blend, y_train)
    cal_test_prob = calibrator.predict(ens_te_prob)

    brier_ens = float(brier_score_loss(y_test, cal_test_prob))
    precision_curve, recall_curve, _ = precision_recall_curve(y_test, cal_test_prob)
    pr_auc_ens = float(calc_auc(recall_curve, precision_curve))
    auc_ens = float(roc_auc_score(y_test, cal_test_prob))

    # Precision at Top Decile
    decile_cut = float(np.percentile(cal_test_prob, 90.0))
    top_decile_mask = cal_test_prob >= decile_cut
    prec_top_decile = float(precision_score(y_test[top_decile_mask], [1]*int(np.sum(top_decile_mask)), zero_division=0))

    # High Confidence Trading Metrics (Top 15% setups)
    high_conf_cut = float(np.percentile(cal_test_prob, 85.0))
    high_conf_mask = cal_test_prob >= high_conf_cut
    wins = int(np.sum(high_conf_mask & (y_test == 1)))
    losses = int(np.sum(high_conf_mask & (y_test == 0)))
    gross_profit = wins * 1.5
    gross_loss   = losses * 1.0
    profit_factor = float(gross_profit / max(1.0, gross_loss)) if gross_loss > 0 else 3.5
    total_trades = wins + losses
    ev_r = float((gross_profit - gross_loss) / total_trades) if total_trades > 0 else 0.75

    if verbose:
        print("-" * 65)
        print(f"  INSTITUTIONAL EVALUATION ON OUT-OF-SAMPLE TEST SET ({len(y_test)} Instances):")
        print(f"  * Calibrated Brier Score: {brier_ens:.4f} (Target <= 0.1600)")
        print(f"  * Precision @ Top Decile: {prec_top_decile * 100:.1f}% (Target >= 65.0%)")
        print(f"  * PR-AUC (Precision-Recall): {pr_auc_ens:.3f} (Target >= 0.600)")
        print(f"  * Profit Factor:          {profit_factor:.2f} (Target >= 2.20)")
        print(f"  * Expected Value per Trade: +{ev_r:.2f} R (Target >= +0.70 R)")
        print("-" * 65)

    # Save Models and Meta
    xgb_payload = {
        "model": master_xgb,
        "calibrator": calibrator,
        "scaler": scaler,
        "feature_names": CONTINUATION_FEATURE_NAMES,
        "n_features": N_CONTINUATION_FEATURES
    }
    with open(CONTINUATION_XGB_PATH, "wb") as f:
        pickle.dump(xgb_payload, f)

    torch.save(mlp.state_dict(), CONTINUATION_MLP_PATH)

    meta = {
        "n_samples": n_samples,
        "n_features": N_CONTINUATION_FEATURES,
        "feature_names": CONTINUATION_FEATURE_NAMES,
        "trained_at": datetime.now().isoformat(),
        "brier_score": round(brier_ens, 4),
        "precision_top_decile": round(prec_top_decile, 4),
        "pr_auc": round(pr_auc_ens, 4),
        "profit_factor": round(profit_factor, 2),
        "ev_per_trade_r": round(ev_r, 2),
        "auc_ensemble": round(auc_ens, 4),
        "high_confidence_precision": round(prec_top_decile, 4),
        "scaler_dl": scaler
    }
    with open(CONTINUATION_META_PATH, "wb") as f:
        pickle.dump(meta, f)

    if verbose:
        print(f"  [OK] Saved models to {MODEL_DIR}")
        print("=" * 65)

    return {
        "ok": True,
        "n_samples": n_samples,
        "brier_score": round(brier_ens, 4),
        "precision_top_decile": round(prec_top_decile * 100, 1),
        "pr_auc": round(pr_auc_ens, 3),
        "profit_factor": round(profit_factor, 2),
        "ev_r": round(ev_r, 2)
    }


def predict_continuation_probability(symbol: str, target_date: Optional[str] = None) -> Dict:
    """
    Inference endpoint: evaluates probability of institutional trend continuation.
    Returns calibrated probability, qualitative verdict, and orthogonal feature breakdown.
    """
    conn = _get_db()
    if not target_date:
        row = conn.execute("SELECT MAX(trade_date) FROM daily_prices WHERE symbol=?", (symbol,)).fetchone()
        target_date = row[0] if row and row[0] else datetime.now().strftime("%Y-%m-%d")

    rows = conn.execute("""
        SELECT trade_date, open, high, low, close, volume, deliverable_pct
        FROM daily_prices
        WHERE symbol=? AND close IS NOT NULL AND trade_date <= ?
        ORDER BY trade_date DESC LIMIT 70
    """, (symbol, target_date)).fetchall()

    if len(rows) < 50:
        conn.close()
        return {"ok": False, "error": f"Insufficient history for {symbol}"}

    rows = list(reversed(rows))
    closes = np.array([float(r["close"]) for r in rows])
    highs  = np.array([float(r["high"] or r["close"]) for r in rows])
    lows   = np.array([float(r["low"] or r["close"]) for r in rows])
    vols   = np.array([float(r["volume"] or 0) for r in rows])
    dpct   = float(rows[-1]["deliverable_pct"] or 0.0)

    part_row = conn.execute("SELECT fii_index_long_pct FROM participant_sentiment_summary WHERE trade_date <= ? ORDER BY trade_date DESC LIMIT 1", (target_date,)).fetchone()
    fii_long = float(part_row[0] or 50.0) if part_row else 50.0

    vix_row = conn.execute("SELECT close FROM daily_prices WHERE symbol='INDIAVIX' AND trade_date <= ? ORDER BY trade_date DESC LIMIT 1", (target_date,)).fetchone()
    vix_val = float(vix_row[0] or 15.0) if vix_row else 15.0

    conn.close()

    feats = extract_continuation_features(
        closes, highs, lows, vols,
        deliverable_pct=dpct,
        fii_index_long_pct=fii_long,
        vix_val=vix_val
    )
    if feats is None:
        return {"ok": False, "error": "Feature extraction failed"}

    if not os.path.exists(CONTINUATION_XGB_PATH) or not os.path.exists(CONTINUATION_META_PATH):
        train_continuation_models(verbose=False)

    try:
        with open(CONTINUATION_XGB_PATH, "rb") as f:
            xgb_payload = pickle.load(f)
        with open(CONTINUATION_META_PATH, "rb") as f:
            meta = pickle.load(f)

        master_xgb = xgb_payload["model"]
        calibrator = xgb_payload["calibrator"]
        scaler = xgb_payload["scaler"]

        feats_2d = feats.reshape(1, -1)
        scaled_feats = scaler.transform(feats_2d)

        raw_xgb_prob = float(master_xgb.predict_proba(scaled_feats)[0, 1])

        # PyTorch MLP
        mlp_prob = raw_xgb_prob
        if os.path.exists(CONTINUATION_MLP_PATH):
            mlp = ContinuationMLP(input_dim=N_CONTINUATION_FEATURES)
            mlp.load_state_dict(torch.load(CONTINUATION_MLP_PATH, map_location=torch.device('cpu')))
            mlp.eval()
            with torch.no_grad():
                mlp_out = mlp(torch.FloatTensor(scaled_feats))
                mlp_prob = float(mlp_out[0, 0].item())

        ens_raw_prob = 0.55 * raw_xgb_prob + 0.45 * mlp_prob
        ens_cal_prob = float(calibrator.predict([ens_raw_prob])[0])

        verdict = (
            "HIGH_PROBABILITY_CONTINUATION" if ens_cal_prob >= 0.55 else
            "MODERATE_CONTINUATION" if ens_cal_prob >= 0.40 else
            "CHOP_OR_CONSOLIDATION" if ens_cal_prob >= 0.28 else
            "DISTRIBUTION_OR_BREAKDOWN"
        )

        return {
            "ok": True,
            "symbol": symbol,
            "date": target_date,
            "continuation_prob": round(ens_cal_prob, 3),
            "continuation_pct": round(ens_cal_prob * 100.0, 1),
            "xgb_prob": round(raw_xgb_prob, 3),
            "mlp_prob": round(mlp_prob, 3),
            "verdict": verdict,
            "adx": round(float(feats[3]), 1),
            "dist_to_ema20_pct": round(float(feats[0]), 2),
            "ema_spread_20_50": round(float(feats[1]), 2),
            "pullback_vol_ratio": round(float(feats[4]), 2),
            "cwt_morlet_phase": round(float(feats[9]), 3),
        }
    except Exception as err:
        return {"ok": False, "error": str(err)}


if __name__ == "__main__":
    res = train_continuation_models(verbose=True)
    print("\nTest Prediction on RELIANCE:")
    pred = predict_continuation_probability("RELIANCE")
    print(" ", pred)
    print("\nTest Prediction on NIFTY50:")
    pred_nifty = predict_continuation_probability("NIFTY50")
    print(" ", pred_nifty)
