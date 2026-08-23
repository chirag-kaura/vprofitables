"""
core/ml_ensemble_engine.py — Advanced Multi-Model Ensemble Machine Learning Engine (v1.0)
Trains and ensembles:
  1. Scikit-Learn HistGradientBoostingClassifier
  2. XGBoost XGBClassifier
  3. LightGBM LGBMClassifier
  4. Scikit-Learn MLPClassifier (Deep Learning Neural Network)

Wraps models in a weighted consensus voting estimator.
"""

import numpy as np
import pickle
import os
from typing import Tuple
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score

# Attempt importing advanced libraries
try:
    from xgboost import XGBClassifier
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

try:
    from lightgbm import LGBMClassifier
    LGBM_AVAILABLE = True
except ImportError:
    LGBM_AVAILABLE = False


class EnsembleClassifier(BaseEstimator, ClassifierMixin):
    def __init__(self, models_dict, weights=None):
        self.models_dict = models_dict
        self.weights = weights if weights else {k: 1.0 / len(models_dict) for k in models_dict.keys()}
        self.classes_ = np.array([-1, 0, 1])

    def fit(self, X, y):
        # Sub-models are assumed pre-fitted in the main training routine
        return self

    def predict_proba(self, X):
        probs = np.zeros((X.shape[0], 3))
        total_w = 0.0

        for name, model in self.models_dict.items():
            if model is None:
                continue
            w = self.weights.get(name, 1.0)
            total_w += w

            # Predict raw probabilities
            p_sub = model.predict_proba(X)
            
            # Map probabilities based on class labels defined in the model
            # Standard models use [-1, 0, 1]. XGB/LGB use [0, 1, 2] (non-negative).
            aligned_p = np.zeros((X.shape[0], 3))
            
            # Attempt to resolve sub-model classes from the final step of a Pipeline, or the model directly
            if hasattr(model, "steps"):
                sub_classes = model.steps[-1][1].classes_
            else:
                sub_classes = getattr(model, "classes_", np.array([0, 1, 2]))

            for col_idx, cls in enumerate(sub_classes):
                # Map sub-model output columns to targets:
                # target columns: 0 -> -1 (DOWN), 1 -> 0 (NEUTRAL), 2 -> 1 (UP)
                if cls == -1:
                    target_col = 0
                elif cls == 0:
                    # If model has only [0, 1, 2] (XGB/LGB), 0 maps to -1 (col 0).
                    # If model has [-1, 0, 1] (HGB/MLP), 0 maps to 0 (col 1).
                    if -1 in sub_classes:
                        target_col = 1
                    else:
                        target_col = 0
                elif cls == 1:
                    if -1 in sub_classes:
                        target_col = 2
                    else:
                        target_col = 1
                elif cls == 2:
                    target_col = 2
                else:
                    target_col = 1 # Fallback

                if 0 <= target_col < 3:
                    aligned_p[:, target_col] = p_sub[:, col_idx]

            probs += aligned_p * w

        if total_w > 0:
            probs = probs / total_w
        return probs

    def predict(self, X):
        probs = self.predict_proba(X)
        preds_idx = np.argmax(probs, axis=1)
        return self.classes_[preds_idx]


def train_single_ensemble(X_tr, y_tr, X_te, y_te, verbose=True) -> Tuple[EnsembleClassifier, dict]:
    """
    Train and optimize all 4 classifiers, compute validation metrics,
    and wrap them in a weighted Consensus Ensemble.
    """
    models = {}
    weights = {}
    accuracies = {}

    # 1. Scikit-Learn HistGradientBoosting
    if verbose: print("    Fitting HistGradientBoostingClassifier...", flush=True)
    try:
        hgb = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", HistGradientBoostingClassifier(
                learning_rate=0.05, max_iter=150, max_depth=6, random_state=42
            ))
        ])
        hgb.fit(X_tr, y_tr)
        models["hgb"] = hgb
        acc = accuracy_score(y_te, hgb.predict(X_te))
        accuracies["hgb"] = acc
        weights["hgb"] = max(acc - 0.33, 0.05) # Weight proportional to excess accuracy above chance
    except Exception as e:
        if verbose: print(f"      HGB fitting failed: {e}", flush=True)

    # 2. XGBoost
    if XGB_AVAILABLE:
        if verbose: print("    Fitting XGBoost Classifier...", flush=True)
        try:
            # Map [-1, 0, 1] to [0, 1, 2]
            y_tr_mapped = y_tr + 1
            y_te_mapped = y_te + 1
            
            xgb = Pipeline([
                ("scaler", StandardScaler()),
                ("clf", XGBClassifier(
                    n_estimators=120, max_depth=5, learning_rate=0.05, 
                    eval_metric="mlogloss", random_state=42
                ))
            ])
            xgb.fit(X_tr, y_tr_mapped)
            models["xgb"] = xgb
            
            # Map predictions back to [-1, 0, 1]
            xgb_preds = xgb.predict(X_te) - 1
            acc = accuracy_score(y_te, xgb_preds)
            accuracies["xgb"] = acc
            weights["xgb"] = max(acc - 0.33, 0.05)
        except Exception as e:
            if verbose: print(f"      XGBoost fitting failed: {e}", flush=True)
    else:
        if verbose: print("    XGBoost is not installed or available.", flush=True)

    # 3. LightGBM
    if LGBM_AVAILABLE:
        if verbose: print("    Fitting LightGBM Classifier...", flush=True)
        try:
            y_tr_mapped = y_tr + 1
            y_te_mapped = y_te + 1
            
            lgb = Pipeline([
                ("scaler", StandardScaler()),
                ("clf", LGBMClassifier(
                    n_estimators=100, max_depth=5, learning_rate=0.05,
                    verbosity=-1, random_state=42
                ))
            ])
            lgb.fit(X_tr, y_tr_mapped)
            models["lgb"] = lgb
            
            lgb_preds = lgb.predict(X_te) - 1
            acc = accuracy_score(y_te, lgb_preds)
            accuracies["lgb"] = acc
            weights["lgb"] = max(acc - 0.33, 0.05)
        except Exception as e:
            if verbose: print(f"      LightGBM fitting failed: {e}", flush=True)
    else:
        if verbose: print("    LightGBM is not installed or available.", flush=True)

    # 4. Multi-Layer Perceptron (Neural Network / Deep Learning)
    if verbose: print("    Fitting MLP Deep Learning Classifier...", flush=True)
    try:
        mlp = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", MLPClassifier(
                hidden_layer_sizes=(64, 32), max_iter=300, 
                activation="relu", solver="adam", early_stopping=True,
                random_state=42
            ))
        ])
        mlp.fit(X_tr, y_tr)
        models["mlp"] = mlp
        acc = accuracy_score(y_te, mlp.predict(X_te))
        accuracies["mlp"] = acc
        weights["mlp"] = max(acc - 0.33, 0.05)
    except Exception as e:
        if verbose: print(f"      MLP fitting failed: {e}", flush=True)

    # Normalize weights so they sum to 1.0
    sum_w = sum(weights.values())
    if sum_w > 0:
        weights = {k: v / sum_w for k, v in weights.items()}
    else:
        weights = {k: 1.0 / len(models) for k in models.keys()}

    # Create the Ensemble Estimator wrapper
    ensemble = EnsembleClassifier(models, weights=weights)
    
    # Calculate Ensemble Accuracy
    ens_preds = ensemble.predict(X_te)
    ens_acc = accuracy_score(y_te, ens_preds)
    
    metrics = {
        "individual_accuracies": accuracies,
        "ensemble_weights": weights,
        "ensemble_accuracy": ens_acc
    }
    
    if verbose:
        print(f"      Ensemble formed. Accuracy = {ens_acc*100:.2f}% (Weights: { {k: round(v, 2) for k, v in weights.items()} })", flush=True)
        
    return ensemble, metrics
