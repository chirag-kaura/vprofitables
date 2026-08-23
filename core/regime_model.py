"""
core/regime_model.py

Implements a Gaussian Mixture Model (GMM) to dynamically classify the current market regime.
Replaces hmmlearn to avoid C++ build errors on bleeding-edge Python versions.

Regimes:
- 0: Low Volatility Bullish (Trend)
- 1: High Volatility Bearish (Crash/Correction)
- 2: Choppy / Sideways Consolidation
"""
import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
import logging
from core.quant_engine import get_price_series

logging.basicConfig(level=logging.INFO)

class RegimeDetector:
    def __init__(self, n_regimes=3):
        self.n_regimes = n_regimes
        # Using GMM instead of HMM avoids the hmmlearn C++ compilation error on newer Python
        self.model = GaussianMixture(n_components=n_regimes, covariance_type="full", max_iter=100, random_state=42)
        self.is_fitted = False
        
    def prepare_data(self, df: pd.DataFrame) -> np.ndarray:
        """
        Prepares returns and volatility for GMM clustering.
        """
        df = df.copy()
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(window=10).std()
        df = df.dropna()
        
        # We feed daily return and 10-day historical volatility as features
        features = np.column_stack([df['returns'].values, df['volatility'].values])
        return features

    def fit(self, df: pd.DataFrame):
        """Trains the GMM on historical data."""
        features = self.prepare_data(df)
        self.model.fit(features)
        self.is_fitted = True
        logging.info("GMM Regime Model successfully fitted.")
        
    def predict_current_regime(self, df: pd.DataFrame) -> dict:
        """
        Predicts the regime for the latest day.
        """
        if not self.is_fitted:
            self.fit(df)
            
        features = self.prepare_data(df)
        hidden_states = self.model.predict(features)
        
        current_state = hidden_states[-1]
        
        # Analyze state means to map to human-readable regimes
        means = self.model.means_
        
        # We classify based on return and volatility characteristics
        state_mapping = {}
        for i in range(self.n_regimes):
            ret_mean, vol_mean = means[i]
            if vol_mean > np.median(means[:, 1]) and ret_mean < 0:
                state_mapping[i] = "BEARISH_HIGH_VOL"
            elif vol_mean < np.median(means[:, 1]) and ret_mean > 0:
                state_mapping[i] = "BULLISH_LOW_VOL"
            else:
                state_mapping[i] = "CHOPPY_SIDEWAYS"
                
        return {
            "state_id": int(current_state),
            "regime_name": state_mapping.get(current_state, "UNKNOWN")
        }

def get_market_regime(symbol: str = "NIFTY50") -> dict:
    """Convenience wrapper for the overall market regime."""
    data = get_price_series(symbol, symbol, years=3)
    if "error" in data:
        return {"regime_name": "UNKNOWN"}
        
    df = pd.DataFrame({"close": data["closes"]})
    detector = RegimeDetector()
    return detector.predict_current_regime(df)

if __name__ == "__main__":
    print(get_market_regime())
