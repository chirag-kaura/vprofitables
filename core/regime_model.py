"""
core/regime_model.py — 3-State Markov-Switching Persistence Model
================================================================
Institutional Market Regime Detector implemented in pure NumPy / SciPy.
Replaces time-blind Gaussian Mixture Models (GMM) with a temporal
Hidden Markov Model enforcing state persistence (A_ii >= 0.85).

Guarantees:
  - Zero external C++ compiler dependencies (pure NumPy & SciPy).
  - Explicit State Persistence: P(S_t = i | S_{t-1} = i) >= 0.85.
  - Forward-Backward Baum-Welch EM with Viterbi decoding.
  - Three distinct institutional macro states:
      0: BULLISH_LOW_VOL  (Persistent Uptrend, Expansion)
      1: BEARISH_HIGH_VOL (High-Volatility Correction, Liquidation)
      2: CHOPPY_SIDEWAYS  (Mean-Reverting Range, Consolidation)
  - Model persistence to models/regime_hmm.pkl.
"""

import os
import sys
import pickle
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import multivariate_normal

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)
REGIME_MODEL_PATH = os.path.join(MODEL_DIR, "regime_hmm.pkl")

sys.path.insert(0, BASE_DIR)
from core.quant_engine import get_price_series

logger = logging.getLogger("regime_model")
logger.setLevel(logging.INFO)

MIN_PERSISTENCE = 0.85
N_REGIMES = 3


class MarkovSwitchingRegimeModel:
    """
    Pure NumPy/SciPy 3-State First-Order Hidden Markov Model
    with constrained diagonal state persistence: A_ii >= 0.85.
    """

    def __init__(self, n_regimes: int = N_REGIMES, min_persistence: float = MIN_PERSISTENCE):
        self.n_regimes = n_regimes
        self.min_persistence = min_persistence

        # Initial distribution
        self.pi = np.full(n_regimes, 1.0 / n_regimes, dtype=np.float64)

        # Transition matrix with persistent diagonal prior
        self.A = np.zeros((n_regimes, n_regimes), dtype=np.float64)
        for i in range(n_regimes):
            self.A[i, i] = self.min_persistence
            off_diag = (1.0 - self.min_persistence) / (n_regimes - 1)
            for j in range(n_regimes):
                if i != j:
                    self.A[i, j] = off_diag

        # Emission parameters: Means [mu_ret, mu_vol] and Covariances
        self.means = np.zeros((n_regimes, 2), dtype=np.float64)
        self.covs = np.zeros((n_regimes, 2, 2), dtype=np.float64)
        self.state_map = {0: "BULLISH_LOW_VOL", 1: "BEARISH_HIGH_VOL", 2: "CHOPPY_SIDEWAYS"}
        self.is_fitted = False

    def _enforce_persistence(self):
        """Enforces row normalization and minimum diagonal persistence A_ii >= min_persistence."""
        for i in range(self.n_regimes):
            # Clip diagonal
            self.A[i, i] = max(self.min_persistence, min(0.98, self.A[i, i]))
            remaining = 1.0 - self.A[i, i]
            off_sum = np.sum([self.A[i, j] for j in range(self.n_regimes) if j != i])
            if off_sum > 0:
                for j in range(self.n_regimes):
                    if j != i:
                        self.A[i, j] = (self.A[i, j] / off_sum) * remaining
            else:
                off_val = remaining / (self.n_regimes - 1)
                for j in range(self.n_regimes):
                    if j != i:
                        self.A[i, j] = off_val

    def _emission_probs(self, X: np.ndarray) -> np.ndarray:
        """
        Computes emission probability matrix B where B[t, k] = P(X_t | S_t = k).
        """
        T = len(X)
        B = np.zeros((T, self.n_regimes), dtype=np.float64)
        eps_cov = np.eye(2) * 1e-5

        for k in range(self.n_regimes):
            cov_k = self.covs[k] + eps_cov
            try:
                rv = multivariate_normal(mean=self.means[k], cov=cov_k, allow_singular=True)
                pdf_vals = rv.pdf(X)
            except Exception:
                # Diagonal fallback
                var = np.maximum(np.diag(cov_k), 1e-5)
                diff = X - self.means[k]
                exp_term = np.exp(-0.5 * np.sum((diff ** 2) / var, axis=1))
                pdf_vals = exp_term / (2.0 * np.pi * np.sqrt(np.prod(var)))

            B[:, k] = np.maximum(pdf_vals, 1e-12)

        return B

    def forward_backward(self, B: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
        """
        Scaled Forward-Backward algorithm for numerical stability.
        Returns:
          gamma: smoothed posterior state probabilities P(S_t = k | X_{1:T})
          xi: smoothed transition probabilities P(S_t = j, S_{t+1} = k | X_{1:T})
          alpha: filtered forward probabilities
          log_likelihood: total log-likelihood
        """
        T = len(B)
        alpha = np.zeros((T, self.n_regimes), dtype=np.float64)
        c = np.zeros(T, dtype=np.float64)

        # Forward step
        alpha[0] = self.pi * B[0]
        c[0] = np.sum(alpha[0])
        if c[0] == 0 or np.isnan(c[0]):
            c[0] = 1e-12
        alpha[0] /= c[0]

        for t in range(1, T):
            alpha[t] = (alpha[t - 1] @ self.A) * B[t]
            c[t] = np.sum(alpha[t])
            if c[t] == 0 or np.isnan(c[t]):
                c[t] = 1e-12
            alpha[t] /= c[t]

        # Backward step
        beta = np.zeros((T, self.n_regimes), dtype=np.float64)
        beta[-1] = 1.0

        for t in range(T - 2, -1, -1):
            beta[t] = (self.A @ (B[t + 1] * beta[t + 1])) / c[t + 1]

        # Posterior marginals gamma
        gamma = alpha * beta
        gamma_sum = np.sum(gamma, axis=1, keepdims=True)
        gamma = np.where(gamma_sum > 0, gamma / gamma_sum, 1.0 / self.n_regimes)

        # Posterior transitions xi
        xi = np.zeros((T - 1, self.n_regimes, self.n_regimes), dtype=np.float64)
        for t in range(T - 1):
            denom = c[t + 1]
            if denom <= 0:
                denom = 1e-12
            xi_t = np.outer(alpha[t], B[t + 1] * beta[t + 1]) * self.A / denom
            xi_sum = np.sum(xi_t)
            xi[t] = xi_t / xi_sum if xi_sum > 0 else 1.0 / (self.n_regimes ** 2)

        log_likelihood = float(np.sum(np.log(c)))
        return gamma, xi, alpha, log_likelihood

    def viterbi(self, X: np.ndarray) -> np.ndarray:
        """
        Viterbi log-space dynamic programming to find most probable hidden state sequence.
        """
        B = self._emission_probs(X)
        T = len(B)
        log_A = np.log(np.maximum(self.A, 1e-12))
        log_B = np.log(np.maximum(B, 1e-12))
        log_pi = np.log(np.maximum(self.pi, 1e-12))

        omega = np.zeros((T, self.n_regimes), dtype=np.float64)
        backtrack = np.zeros((T, self.n_regimes), dtype=np.int32)

        omega[0] = log_pi + log_B[0]

        for t in range(1, T):
            for k in range(self.n_regimes):
                scores = omega[t - 1] + log_A[:, k]
                best_prev = int(np.argmax(scores))
                omega[t, k] = scores[best_prev] + log_B[t, k]
                backtrack[t, k] = best_prev

        states = np.zeros(T, dtype=np.int32)
        states[-1] = int(np.argmax(omega[-1]))

        for t in range(T - 2, -1, -1):
            states[t] = backtrack[t + 1, states[t + 1]]

        return states

    def fit(self, X: np.ndarray, max_iter: int = 50, tol: float = 1e-4):
        """
        Fits 3-state parameters via Expectation-Maximization (Baum-Welch)
        under strict persistence constraint A_ii >= min_persistence.
        """
        T, D = X.shape
        if T < 30:
            return

        # Smart K-Means-like initialization based on volatility quantiles
        vols = X[:, 1]
        rets = X[:, 0]

        p33 = np.percentile(vols, 33.3)
        p66 = np.percentile(vols, 66.6)

        idx_low_vol = vols <= p33
        idx_high_vol = vols >= p66
        idx_mid_vol = (~idx_low_vol) & (~idx_high_vol)

        masks = [idx_low_vol, idx_high_vol, idx_mid_vol]
        for k in range(self.n_regimes):
            m = masks[k]
            if np.sum(m) > 5:
                self.means[k] = np.mean(X[m], axis=0)
                diff = X[m] - self.means[k]
                self.covs[k] = (diff.T @ diff) / np.sum(m) + np.eye(2) * 1e-4
            else:
                self.means[k] = np.mean(X, axis=0)
                self.covs[k] = np.cov(X.T) + np.eye(2) * 1e-4

        self._enforce_persistence()

        prev_ll = -np.inf
        for it in range(max_iter):
            B = self._emission_probs(X)
            gamma, xi, _, log_lik = self.forward_backward(B)

            # M-Step: Update initial state
            self.pi = gamma[0]

            # M-Step: Update Transition Matrix
            sum_xi = np.sum(xi, axis=0)
            sum_gamma = np.sum(gamma[:-1], axis=0, keepdims=True).T
            self.A = np.where(sum_gamma > 0, sum_xi / sum_gamma, self.A)
            self._enforce_persistence()

            # M-Step: Update Means and Covariances
            for k in range(self.n_regimes):
                w = gamma[:, k]
                w_sum = np.sum(w)
                if w_sum > 1e-6:
                    self.means[k] = np.sum(w[:, None] * X, axis=0) / w_sum
                    diff = X - self.means[k]
                    self.covs[k] = (diff.T @ (w[:, None] * diff)) / w_sum + np.eye(2) * 1e-4

            if abs(log_lik - prev_ll) < tol:
                break
            prev_ll = log_lik

        # Assign institutional semantic regime mapping
        self._align_regime_labels()
        self.is_fitted = True
        logger.info(f"[Regime HMM] Model successfully fitted. Diagonal persistence: {np.diag(self.A).round(3)}")

    def _align_regime_labels(self):
        """
        Orders states systematically:
          0: BULLISH_LOW_VOL  (Positive returns, lowest volatility)
          1: BEARISH_HIGH_VOL (Negative returns or highest volatility)
          2: CHOPPY_SIDEWAYS  (Intermediate volatility, near-zero return)
        """
        vol_means = self.means[:, 1]
        ret_means = self.means[:, 0]

        high_vol_idx = int(np.argmax(vol_means))
        low_vol_idx = int(np.argmin(vol_means))
        mid_vol_idx = int([i for i in range(self.n_regimes) if i not in (high_vol_idx, low_vol_idx)][0])

        new_mapping = {
            low_vol_idx: "BULLISH_LOW_VOL",
            high_vol_idx: "BEARISH_HIGH_VOL",
            mid_vol_idx: "CHOPPY_SIDEWAYS"
        }
        self.state_map = new_mapping


class RegimeDetector:
    """
    Drop-in institutional replacement for core/regime_model.py RegimeDetector.
    Uses 3-State Markov-Switching Persistence Model in pure NumPy/SciPy.
    """

    def __init__(self, n_regimes: int = N_REGIMES):
        self.n_regimes = n_regimes
        self.model = MarkovSwitchingRegimeModel(n_regimes=n_regimes, min_persistence=MIN_PERSISTENCE)
        self.is_fitted = False
        self._load_cached_model()

    def _load_cached_model(self):
        if os.path.exists(REGIME_MODEL_PATH):
            try:
                with open(REGIME_MODEL_PATH, "rb") as f:
                    self.model = pickle.load(f)
                self.is_fitted = getattr(self.model, "is_fitted", False)
            except Exception as e:
                logger.warning(f"[Regime Detector] Could not load cached model: {e}")

    def _save_model(self):
        try:
            with open(REGIME_MODEL_PATH, "wb") as f:
                pickle.dump(self.model, f)
        except Exception as e:
            logger.warning(f"[Regime Detector] Could not save model: {e}")

    def prepare_data(self, df: pd.DataFrame) -> np.ndarray:
        """
        Extracts orthogonal return and annualized volatility features for Markov-Switching.
        """
        df = df.copy()
        if 'close' not in df.columns:
            return np.empty((0, 2))

        closes = df['close'].values.astype(float)
        if len(closes) < 15:
            return np.empty((0, 2))

        returns = np.diff(closes) / closes[:-1]
        # 10-day rolling annualized volatility
        vol = pd.Series(returns).rolling(window=10).std().values * np.sqrt(252)

        # Align lengths
        features = np.column_stack([returns[9:], vol[9:]])
        features = np.nan_to_num(features, nan=0.0)
        return features

    def fit(self, df: pd.DataFrame):
        """Trains the Markov-Switching Persistence Model on historical price data."""
        features = self.prepare_data(df)
        if len(features) < 30:
            return
        self.model.fit(features)
        self.is_fitted = True
        self._save_model()

    def predict_current_regime(self, df: pd.DataFrame) -> dict:
        """
        Predicts filtered current regime state and state probabilities.
        """
        features = self.prepare_data(df)
        if len(features) < 15:
            return {
                "state_id": 2,
                "regime_name": "CHOPPY_SIDEWAYS",
                "probabilities": {"BULLISH_LOW_VOL": 0.33, "BEARISH_HIGH_VOL": 0.33, "CHOPPY_SIDEWAYS": 0.34},
                "persistence": 0.85
            }

        if not self.is_fitted:
            self.fit(df)

        B = self.model._emission_probs(features)
        gamma, _, alpha, _ = self.model.forward_backward(B)

        latest_probs = alpha[-1]  # Filtered real-time probability
        latest_state_id = int(np.argmax(latest_probs))
        regime_label = self.model.state_map.get(latest_state_id, "CHOPPY_SIDEWAYS")

        prob_dict = {
            self.model.state_map.get(i, f"STATE_{i}"): round(float(latest_probs[i]), 3)
            for i in range(self.n_regimes)
        }

        # Diagonal persistence of current state
        persistence_val = float(self.model.A[latest_state_id, latest_state_id])

        return {
            "state_id": latest_state_id,
            "regime_name": regime_label,
            "probabilities": prob_dict,
            "persistence": round(persistence_val, 3)
        }


def get_market_regime(symbol: str = "NIFTY50") -> dict:
    """Convenience wrapper for the overall market regime."""
    data = get_price_series(symbol, symbol, years=3)
    if "error" in data or "closes" not in data or len(data["closes"]) < 30:
        return {"state_id": 2, "regime_name": "CHOPPY_SIDEWAYS", "persistence": 0.85}

    df = pd.DataFrame({"close": data["closes"]})
    detector = RegimeDetector()
    return detector.predict_current_regime(df)


if __name__ == "__main__":
    print("Testing 3-State Markov-Switching Persistence Model on NIFTY50...")
    regime = get_market_regime("NIFTY50")
    print("Result:", regime)
