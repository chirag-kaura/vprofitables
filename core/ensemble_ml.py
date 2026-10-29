"""
core/ensemble_ml.py — Institutional Dynamic ML Ensemble Scorer
==============================================================
Modernized Walk-Forward Rolling Retraining Pipeline.
Eliminates unconstrained daily partial_fit() catastrophic forgetting.

Architecture:
  - 252-day Rolling Walk-Forward Retraining Buffer.
  - Exponential Time-Decay Sample Weighting (lambda = 0.995).
  - Regularized L2 Loss with Robust Standardization.
  - State persistence to models/ensemble_ml_state.pkl.
  - Fallback Bayesian regime heuristics when buffer is warming up.
"""

import os
import sys
import pickle
import logging
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger("ensemble_ml")
logger.setLevel(logging.INFO)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)
ENSEMBLE_STATE_PATH = os.path.join(MODEL_DIR, "ensemble_ml_state.pkl")

ROLLING_WINDOW_DAYS = 252
DECAY_LAMBDA = 0.995


class DynamicScorer:
    """
    Institutional Walk-Forward Ensemble Scorer.
    Maintains a 252-day rolling window of historical signals and trade outcomes.
    Weights each historical sample with exponential decay lambda^(T - t).
    """

    def __init__(self, window_size: int = ROLLING_WINDOW_DAYS, decay_lambda: float = DECAY_LAMBDA):
        self.window_size = window_size
        self.decay_lambda = decay_lambda

        # Rolling buffers (FIFO)
        self.buffer_X = deque(maxlen=window_size)
        self.buffer_y = deque(maxlen=window_size)

        # Base learner: Regularized Logistic Regression with L2 penalty
        # avoids catastrophic forgetting while adapting to concept drift
        self.model = LogisticRegression(
            C=1.0,
            solver='lbfgs',
            max_iter=500,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.last_retrained = None

        # Try loading persisted state
        self._load_state()

    def _load_state(self):
        """Loads state and buffer if available on disk."""
        if os.path.exists(ENSEMBLE_STATE_PATH):
            try:
                with open(ENSEMBLE_STATE_PATH, "rb") as f:
                    state = pickle.load(f)
                self.buffer_X = deque(state.get("buffer_X", []), maxlen=self.window_size)
                self.buffer_y = deque(state.get("buffer_y", []), maxlen=self.window_size)
                self.model = state.get("model", self.model)
                self.scaler = state.get("scaler", self.scaler)
                self.is_trained = state.get("is_trained", False)
                self.last_retrained = state.get("last_retrained")
                logger.info(f"[Ensemble ML] Loaded state with {len(self.buffer_X)} samples in rolling buffer.")
            except Exception as e:
                logger.warning(f"[Ensemble ML] Could not load state: {e}")

    def _save_state(self):
        """Persists model and rolling buffer to disk."""
        try:
            state = {
                "buffer_X": list(self.buffer_X),
                "buffer_y": list(self.buffer_y),
                "model": self.model,
                "scaler": self.scaler,
                "is_trained": self.is_trained,
                "last_retrained": self.last_retrained,
                "decay_lambda": self.decay_lambda,
                "window_size": self.window_size,
            }
            with open(ENSEMBLE_STATE_PATH, "wb") as f:
                pickle.dump(state, f)
        except Exception as e:
            logger.warning(f"[Ensemble ML] Failed to persist state: {e}")

    def _compute_decay_weights(self, n_samples: int) -> np.ndarray:
        """
        Computes exponential recency weights:
        w_i = lambda^(n_samples - 1 - i)
        Newest sample has weight 1.0, older samples decay smoothly.
        """
        indices = np.arange(n_samples)
        steps_ago = (n_samples - 1) - indices
        weights = np.power(self.decay_lambda, steps_ago)
        return weights

    def retrain_walk_forward(self):
        """
        Performs walk-forward retraining on the 252-day rolling window
        using exponential time-decay sample weighting.
        """
        if len(self.buffer_X) < 10:
            return

        X = np.array(self.buffer_X, dtype=np.float32)
        y = np.array(self.buffer_y, dtype=np.int32)

        # Check if we have both classes
        unique_classes = np.unique(y)
        if len(unique_classes) < 2:
            return

        sample_weights = self._compute_decay_weights(len(X))

        # Fit Scaler and Retrain Classifier
        scaled_X = self.scaler.fit_transform(X)
        self.model.fit(scaled_X, y, sample_weight=sample_weights)
        self.is_trained = True
        self.last_retrained = datetime.now().isoformat()
        self._save_state()
        logger.info(f"[Ensemble ML] Walk-forward retrained on {len(X)} rolling instances (lambda={self.decay_lambda}).")

    def train(self, historical_signals: np.ndarray, historical_outcomes: np.ndarray):
        """
        Full batch initialization / historical backfill.
        Populates the 252-day rolling buffer with the most recent history.
        """
        if len(historical_signals) == 0:
            return

        # Keep the most recent window_size samples
        take_n = min(len(historical_signals), self.window_size)
        init_X = historical_signals[-take_n:]
        init_y = historical_outcomes[-take_n:]

        self.buffer_X.clear()
        self.buffer_y.clear()

        for x_row, y_val in zip(init_X, init_y):
            self.buffer_X.append(np.array(x_row, dtype=np.float32))
            self.buffer_y.append(int(y_val))

        self.retrain_walk_forward()
        logger.info(f"[Ensemble ML] Initialized rolling buffer with {len(self.buffer_X)} instances.")

    def continuous_train(self, latest_signals: np.ndarray, latest_outcomes: np.ndarray):
        """
        Incremental learning step called at the end of each trading day.
        Appends new outcomes to the 252-day rolling FIFO buffer and triggers
        walk-forward weighted retraining. Eliminates catastrophic forgetting.
        """
        signals = np.atleast_2d(latest_signals)
        outcomes = np.atleast_1d(latest_outcomes)

        for sig, out in zip(signals, outcomes):
            self.buffer_X.append(np.array(sig, dtype=np.float32))
            self.buffer_y.append(int(out))

        self.retrain_walk_forward()

    def get_dynamic_score(
        self,
        gann_score: float,
        cwt_score: float,
        sentiment_score: float,
        macro_score: float,
        regime_id: int
    ) -> float:
        """
        Returns a calibrated probability score (0.0 to 100.0) based on
        dynamically adapted walk-forward ML weights.
        """
        if not self.is_trained:
            # Institutional regime-adaptive heuristic fallback
            if regime_id == 1:  # Bearish / High Vol
                return (gann_score * 0.15) + (cwt_score * 0.45) + (sentiment_score * 0.10) + (macro_score * 0.30)
            elif regime_id == 0:  # Bullish / Low Vol Trend
                return (gann_score * 0.35) + (cwt_score * 0.30) + (sentiment_score * 0.20) + (macro_score * 0.15)
            else:  # Choppy / Sideways
                return (gann_score * 0.25) + (cwt_score * 0.30) + (sentiment_score * 0.25) + (macro_score * 0.20)

        try:
            features = np.array([[gann_score, cwt_score, sentiment_score, macro_score, float(regime_id)]], dtype=np.float32)
            scaled = self.scaler.transform(features)
            prob = self.model.predict_proba(scaled)[0][1]
            return float(np.clip(prob * 100.0, 0.0, 100.0))
        except Exception as e:
            logger.warning(f"[Ensemble ML] Predict error: {e}")
            return (gann_score + cwt_score + sentiment_score + macro_score) / 4.0


# Global singleton instance
scorer = DynamicScorer()


def compute_dynamic_score(scores_dict: dict, regime_id: int = 2) -> float:
    """Wrapper used by unified_logic.py to fetch the institutional AI-weighted score."""
    return scorer.get_dynamic_score(
        gann_score=scores_dict.get('gann', 0),
        cwt_score=scores_dict.get('quant', 0),
        sentiment_score=scores_dict.get('sentiment', 0),
        macro_score=scores_dict.get('macro', 0),
        regime_id=regime_id
    )


def update_model_daily(features: list, outcomes: list):
    """
    Hook for execution and backtesting pipelines to deliver daily trade feedback
    into the 252-day walk-forward retraining buffer.
    """
    if features and outcomes:
        scorer.continuous_train(np.array(features), np.array(outcomes))
