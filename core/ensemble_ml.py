"""
core/ensemble_ml.py

Replaces rigid static scoring weights with a dynamic Machine Learning ensemble.
Upgraded (Phase 2): Uses SGDClassifier for Online / Continual Learning, 
allowing the model to adapt weights daily without full retraining.
"""
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)

class DynamicScorer:
    def __init__(self):
        # SGDClassifier with log_loss acts like Logistic Regression but supports partial_fit
        self.model = SGDClassifier(loss='log_loss', learning_rate='optimal', random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def train(self, historical_signals: np.ndarray, historical_outcomes: np.ndarray):
        """
        Full batch train (used on historical backfill).
        """
        scaled_signals = self.scaler.fit_transform(historical_signals)
        self.model.fit(scaled_signals, historical_outcomes)
        self.is_trained = True
        logging.info("Dynamic ML Scorer (SGD) batch trained.")
        
    def continuous_train(self, latest_signals: np.ndarray, latest_outcomes: np.ndarray):
        """
        Incremental learning step. To be called at the end of each trading day.
        Updates model weights dynamically to combat concept drift.
        """
        if not self.is_trained:
            # First time training needs classes specified
            self.scaler.fit(latest_signals)
            scaled = self.scaler.transform(latest_signals)
            self.model.partial_fit(scaled, latest_outcomes, classes=np.array([0, 1]))
            self.is_trained = True
        else:
            # Continual update
            # Note: In production, scaler should technically be updated (partial_fit for scaler too)
            self.scaler.partial_fit(latest_signals)
            scaled = self.scaler.transform(latest_signals)
            self.model.partial_fit(scaled, latest_outcomes)
            
    def get_dynamic_score(self, gann_score: float, cwt_score: float, 
                          sentiment_score: float, macro_score: float, regime_id: int) -> float:
        """
        Returns a probability of success (0.0 to 1.0) based on dynamic ML weighting.
        """
        if not self.is_trained:
            # Fallback to smart heuristic if untrained
            if regime_id == 1:
                return (gann_score * 0.2) + (cwt_score * 0.4) + (sentiment_score * 0.1) + (macro_score * 0.3)
            elif regime_id == 0:
                return (gann_score * 0.4) + (cwt_score * 0.3) + (sentiment_score * 0.2) + (macro_score * 0.1)
            else:
                return (gann_score * 0.25) + (cwt_score * 0.25) + (sentiment_score * 0.25) + (macro_score * 0.25)
                
        features = np.array([[gann_score, cwt_score, sentiment_score, macro_score, regime_id]])
        scaled_features = self.scaler.transform(features)
        prob = self.model.predict_proba(scaled_features)[0][1] # Probability of class 1 (Win)
        return float(prob) * 100.0

# Global instance
scorer = DynamicScorer()

def compute_dynamic_score(scores_dict: dict, regime_id: int = 2) -> float:
    """Wrapper used by unified_logic.py to fetch the AI-weighted score."""
    return scorer.get_dynamic_score(
        gann_score=scores_dict.get('gann', 0),
        cwt_score=scores_dict.get('quant', 0),
        sentiment_score=scores_dict.get('sentiment', 0),
        macro_score=scores_dict.get('macro', 0),
        regime_id=regime_id
    )

def update_model_daily(features: list, outcomes: list):
    """
    Hook for the backtester or live execution to pass the day's trades to the model.
    """
    if features and outcomes:
        scorer.continuous_train(np.array(features), np.array(outcomes))
