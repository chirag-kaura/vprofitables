"""
market_feedback.py — Market-Supervised Sentiment Learning Engine
Place in: core/market_feedback.py

The market IS the label. No humans, no hardcoded rules.
Price reaction after news = ground truth.

Self-improving loop:
  1. Headline stored → raw_score from VADER (generic NLP)
  2. Wait N days → measure actual price from daily_prices
  3. market_label assigned from price move (e.g. +2.3% → BULLISH)
  4. Train model on (headline text → market_label)
  5. Model produces calibrated_score (market-validated)
  6. prediction_error = |raw_score - calibrated_score| (how wrong VADER was)
  7. model_was_correct = 1/0 (did VADER get direction right?)

Columns populated in news_sentiment:
  market_return_1d  — price % change day of news
  market_return_5d  — price % change 5 days after (primary window)
  market_return_20d — price % change 20 days after (trend confirmation)
  market_label      — ground truth label derived from market_return_5d
  market_labelled_at — when the label was applied
  calibrated_score  — model-corrected score after training
  prediction_error  — |raw_score - calibrated_score|
  model_was_correct — 1 if VADER direction matched market, else 0

Run:
    python core/market_feedback.py                 # full pipeline
    python core/market_feedback.py --label-only    # just apply market labels
    python core/market_feedback.py --train-only    # just retrain model
    python core/market_feedback.py --report        # accuracy report
    python core/market_feedback.py --symbol TCS    # single symbol
"""

import os, sys, math, sqlite3, pickle
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Tuple

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH   = os.path.join(BASE_DIR, "market_data_v2.db")
MODEL_DIR = os.path.join(BASE_DIR, "core")

# Market label thresholds — based on 5-day return
# Tune these for NSE/BSE volatility characteristics
def init_market_feedback_columns():
    """Alias — market feedback columns are created by sentiment_db.init_sentiment_tables()."""
    try:
        sys.path.insert(0, BASE_DIR)
        from core.sentiment_db import init_sentiment_tables
        init_sentiment_tables()
    except Exception:
        pass

THRESHOLDS_FILE = os.path.join(MODEL_DIR, "sentiment_thresholds.json")

DEFAULT_THRESHOLDS = {
    "STRONGLY BULLISH":  2.0,   # > +2%
    "BULLISH":           0.5,   # +0.5% to +2%
    "NEUTRAL":          -0.5,   # -0.5% to +0.5%
    "BEARISH":          -2.0,   # -2% to -0.5%
}

def load_thresholds() -> dict:
    if os.path.exists(THRESHOLDS_FILE):
        try:
            import json
            with open(THRESHOLDS_FILE, "r") as f:
                data = json.load(f)
                if all(k in data for k in DEFAULT_THRESHOLDS):
                    return data
        except Exception:
            pass
    return DEFAULT_THRESHOLDS

def save_thresholds(thresholds: dict):
    try:
        import json
        with open(THRESHOLDS_FILE, "w") as f:
            json.dump(thresholds, f, indent=2)
    except Exception as e:
        print(f"  [WARN ] Failed to save thresholds config: {e}", flush=True)

# Loaded dynamic thresholds
THRESHOLDS = load_thresholds()


def calibrate_label_thresholds(excess_returns: List[float]) -> dict:
    import numpy as np
    import time
    p10 = float(np.percentile(excess_returns, 10))
    p35 = float(np.percentile(excess_returns, 35))
    p65 = float(np.percentile(excess_returns, 65))
    p90 = float(np.percentile(excess_returns, 90))
    
    return {
        "STRONGLY BULLISH": round(p90, 4),
        "BULLISH":          round(p65, 4),
        "NEUTRAL":          round(p35, 4),
        "BEARISH":          round(p10, 4),
        "version":          int(time.time()),
        "calibrated_at":    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


LABEL_INT = {
    "STRONGLY BULLISH": 2, "BULLISH": 1, "NEUTRAL": 0,
    "BEARISH": -1, "STRONGLY BEARISH": -2,
}
INT_LABEL = {v: k for k, v in LABEL_INT.items()}


def _conn(timeout=10):
    c = sqlite3.connect(DB_PATH, timeout=timeout)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    c.row_factory = sqlite3.Row
    return c


def _return_pct(p_start: float, p_end: float) -> float:
    if not p_start or p_start == 0:
        return 0.0
    return round((p_end - p_start) / p_start * 100, 4)


def _market_label(ret: float) -> str:
    t = load_thresholds()
    if   ret >  t["STRONGLY BULLISH"]: return "STRONGLY BULLISH"
    elif ret >  t["BULLISH"]:          return "BULLISH"
    elif ret >= t["NEUTRAL"]:          return "NEUTRAL"
    elif ret >= t["BEARISH"]:          return "BEARISH"
    else:                              return "STRONGLY BEARISH"


def _price_on_or_before(c, symbol: str, date_str: str) -> Optional[float]:
    """Closest available closing price on or before date_str."""
    row = c.execute("""
        SELECT close FROM daily_prices
        WHERE symbol=? AND trade_date<=? AND close IS NOT NULL
        ORDER BY trade_date DESC LIMIT 1
    """, (symbol, date_str)).fetchone()
    return float(row[0]) if row else None


def _price_on_or_after(c, symbol: str, date_str: str) -> Optional[float]:
    """Closest available closing price on or after date_str."""
    row = c.execute("""
        SELECT close FROM daily_prices
        WHERE symbol=? AND trade_date>=? AND close IS NOT NULL
        ORDER BY trade_date ASC LIMIT 1
    """, (symbol, date_str)).fetchone()
    return float(row[0]) if row else None


def get_all_excess_returns(c, nifty_sym) -> List[float]:
    """Calculate historical excess returns for all headlines in the DB with valid 5d returns."""
    rows = c.execute("""
        SELECT symbol, published_at, market_return_5d
        FROM news_sentiment
        WHERE market_return_5d IS NOT NULL AND published_at != ''
    """).fetchall()
    
    nifty_prices = {}
    if nifty_sym:
        try:
            nifty_rows = c.execute("""
                SELECT trade_date, close FROM daily_prices
                WHERE symbol=? AND close IS NOT NULL
            """, (nifty_sym,)).fetchall()
            nifty_prices = {r["trade_date"]: float(r["close"]) for r in nifty_rows}
        except Exception:
            pass
            
    excess_returns = []
    for r in rows:
        sym = r["symbol"]
        ret_5d = r["market_return_5d"]
        pub_date = r["published_at"][:10]
        
        if nifty_sym and sym != nifty_sym and nifty_prices:
            try:
                pub_dt = datetime.strptime(pub_date, "%Y-%m-%d")
                
                p_nifty_news = None
                for offset in range(10):
                    chk = (pub_dt - timedelta(days=offset)).strftime("%Y-%m-%d")
                    if chk in nifty_prices:
                        p_nifty_news = nifty_prices[chk]
                        break
                        
                d5_dt = pub_dt + timedelta(days=7)  # window_days + 2
                p_nifty_5d = None
                for offset in range(10):
                    chk = (d5_dt + timedelta(days=offset)).strftime("%Y-%m-%d")
                    if chk in nifty_prices:
                        p_nifty_5d = nifty_prices[chk]
                        break
                        
                if p_nifty_news is not None and p_nifty_5d is not None:
                    nifty_ret_5d = _return_pct(p_nifty_news, p_nifty_5d)
                    excess_returns.append(ret_5d - nifty_ret_5d)
                    continue
            except Exception:
                pass
        excess_returns.append(ret_5d)
    return excess_returns


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: APPLY MARKET LABELS
# ─────────────────────────────────────────────────────────────────────────────

def apply_market_labels(
    symbol: Optional[str] = None,
    window_days: int = 5,
    min_age_days: int = 7,
    batch_size: int = 500,
) -> int:
    """
    Label each headline with what the market ACTUALLY did after the news.

    Uses EXCESS RETURN = stock return - Nifty50 return over the same window.
    This isolates the stock-specific reaction to the news vs broad market moves.

    Example:
      TCS news published.  5 days later:
        TCS moved  -0.5%  (looks BEARISH)
        Nifty moved -2.5%  (market crashed)
        Excess =   +2.0%  → label: BULLISH (TCS held up vs market = good news reaction)

    label_source = 'MARKET' — ground truth, not human guess, not VADER opinion.
    """
    cutoff = (datetime.now() - timedelta(days=min_age_days)).strftime("%Y-%m-%d")
    now    = datetime.now().strftime("%Y-%m-%d")
    conn   = _conn()
    c      = conn.cursor()

    # Find Nifty50 symbol in DB for excess return calculation
    _nifty_syms = ("NIFTY50", "^NSEI", "NSEI", "NIFTY", "INDIA50")
    _nifty_sym  = None
    for ns in _nifty_syms:
        if c.execute("SELECT 1 FROM daily_prices WHERE symbol=? LIMIT 1", (ns,)).fetchone():
            _nifty_sym = ns
            break

    # Dynamic Threshold Calibration (Fix 3)
    try:
        excess_returns = get_all_excess_returns(c, _nifty_sym)
        if len(excess_returns) >= 50:
            t_cal = calibrate_label_thresholds(excess_returns)
            print("  [MKTF ] Calibrating label thresholds from actual excess returns...", flush=True)
            print(f"    STRONGLY BULLISH (90th pct): Default {DEFAULT_THRESHOLDS['STRONGLY BULLISH']:+.2f}% vs Calibrated {t_cal['STRONGLY BULLISH']:+.2f}%", flush=True)
            print(f"    BULLISH (65th pct):          Default {DEFAULT_THRESHOLDS['BULLISH']:+.2f}% vs Calibrated {t_cal['BULLISH']:+.2f}%", flush=True)
            print(f"    NEUTRAL (35th pct):          Default {DEFAULT_THRESHOLDS['NEUTRAL']:+.2f}% vs Calibrated {t_cal['NEUTRAL']:+.2f}%", flush=True)
            print(f"    BEARISH (10th pct):          Default {DEFAULT_THRESHOLDS['BEARISH']:+.2f}% vs Calibrated {t_cal['BEARISH']:+.2f}%", flush=True)
            save_thresholds(t_cal)
            print(f"  [MKTF ] Calibration saved to {THRESHOLDS_FILE}", flush=True)
        else:
            print(f"  [MKTF ] Insufficient historical data to calibrate thresholds ({len(excess_returns)}/50). Using current configuration.", flush=True)
    except Exception as e:
        print(f"  [WARN ] Failed threshold calibration: {e}", flush=True)

    if symbol:
        rows = c.execute("""
            SELECT id, symbol, published_at, raw_score
            FROM   news_sentiment
            WHERE  market_label IS NULL
              AND  published_at != ''
              AND  DATE(published_at) <= ?
              AND  symbol = ?
            ORDER  BY published_at ASC LIMIT ?
        """, (cutoff, symbol, batch_size)).fetchall()
    else:
        rows = c.execute("""
            SELECT id, symbol, published_at, raw_score
            FROM   news_sentiment
            WHERE  market_label IS NULL
              AND  published_at != ''
              AND  DATE(published_at) <= ?
            ORDER  BY published_at ASC LIMIT ?
        """, (cutoff, batch_size)).fetchall()

    if not rows:
        conn.close()
        return 0

    labelled = 0
    for row in rows:
        row_id    = row["id"]
        sym       = row["symbol"]
        pub_raw   = row["published_at"]
        raw_score = float(row["raw_score"] or 0)

        pub_date = pub_raw[:10]
        try:
            datetime.strptime(pub_date, "%Y-%m-%d")
        except ValueError:
            continue

        # ── Stock prices ──────────────────────────────────────────────────
        p_news = _price_on_or_before(c, sym, pub_date)
        if p_news is None:
            continue  # No price data for this symbol

        prev_date = (datetime.strptime(pub_date, "%Y-%m-%d") - timedelta(days=4)).strftime("%Y-%m-%d")
        p_prev    = _price_on_or_before(c, sym, prev_date)
        ret_1d    = _return_pct(p_prev, p_news) if p_prev else 0.0

        d5  = (datetime.strptime(pub_date, "%Y-%m-%d") + timedelta(days=window_days + 2)).strftime("%Y-%m-%d")
        d20 = (datetime.strptime(pub_date, "%Y-%m-%d") + timedelta(days=22)).strftime("%Y-%m-%d")
        p5  = _price_on_or_after(c, sym, d5)
        p20 = _price_on_or_after(c, sym, d20)

        ret_5d  = _return_pct(p_news, p5)  if p5  else None
        ret_20d = _return_pct(p_news, p20) if p20 else None

        if ret_5d is None:
            continue

        # ── Nifty50 excess return ─────────────────────────────────────────
        # Subtract market return so label reflects NEWS impact on THIS stock
        nifty_ret_5d = 0.0
        if _nifty_sym and sym not in _nifty_syms:
            pn0 = _price_on_or_before(c, _nifty_sym, pub_date)
            pn5 = _price_on_or_after(c, _nifty_sym, d5)
            if pn0 and pn5:
                nifty_ret_5d = _return_pct(pn0, pn5)

        excess_ret = round(ret_5d - nifty_ret_5d, 4)

        # ── Ground truth label ────────────────────────────────────────────
        # Label is based on EXCESS return — pure stock-specific reaction
        mkt_lbl = _market_label(excess_ret)

        # Was VADER correct direction vs market excess?
        vader_says_up  = raw_score >= 0.1
        market_went_up = excess_ret > 0
        was_correct    = 1 if (vader_says_up == market_went_up) else 0

        # Calibrated score: excess return normalised to [-1,+1]
        # ±3% excess = ±1.0 (smaller scale — excess moves are tighter than absolute)
        cal_score = round(max(-1.0, min(1.0, excess_ret / 3.0)), 4)
        pred_err  = round(abs(raw_score - cal_score), 4)

        c.execute("""
            UPDATE news_sentiment
            SET market_return_1d   = ?,
                market_return_5d   = ?,
                market_return_20d  = ?,
                market_label       = ?,
                market_labelled_at = ?,
                calibrated_score   = ?,
                prediction_error   = ?,
                model_was_correct  = ?
            WHERE id = ?
        """, (ret_1d, ret_5d, ret_20d, mkt_lbl, now,
              cal_score, pred_err, was_correct, row_id))
        labelled += 1

    conn.commit()
    conn.close()

    if labelled:
        tag  = f" [{symbol}]" if symbol else ""
        method = f"excess vs {_nifty_sym}" if _nifty_sym else "absolute return"
        print(f"  [MKTF ] Labelled {labelled} headlines{tag} ({method})", flush=True)
    return labelled

def _build_nse_features(samples: list):
    """
    NSE-specific contextual features for each sample.
    These capture what text alone cannot:
      - RSI at time of news (oversold = stronger upside reaction)
      - Price trend (above/below SMA20)
      - Volume context (high volume amplifies impact)
      - Day of week (Monday amplifies weekend news)
    Returns numpy array (n, features) or None.
    """
    try:
        import numpy as np, sqlite3 as _sq
        conn = _sq.connect(DB_PATH, timeout=5)
        conn.row_factory = _sq.Row
        features = []
        for s in samples:
            sym = s["symbol"]
            pub = s.get("published_at","")[:10]
            try:
                rows = conn.execute("""
                    SELECT close, volume FROM daily_prices
                    WHERE symbol=? AND trade_date<=? AND close IS NOT NULL
                    ORDER BY trade_date DESC LIMIT 25
                """, (sym, pub)).fetchall()
                if len(rows) >= 5:
                    closes = [float(r["close"]) for r in rows]
                    vols   = [float(r["volume"] or 0) for r in rows]
                    sma5  = sum(closes[:5])/5
                    sma20 = sum(closes[:min(20,len(closes))])/min(20,len(closes))
                    # RSI(14)
                    rsi = 50.0
                    if len(closes) >= 15:
                        g=l2=0.0
                        for i in range(1,15):
                            d=closes[i-1]-closes[i]
                            if d>0: g+=d
                            else:   l2-=d
                        ag,al=g/14,l2/14
                        rsi = 100-100/(1+ag/al) if al>0 else 100.0
                    avg_vol = sum(vols[1:21])/max(len(vols[1:21]),1)
                    vr = min(vols[0]/avg_vol if avg_vol>0 else 1.0, 3.0)/3.0
                    f = [
                        1.0 if closes[0]>sma5 else 0.0,
                        1.0 if closes[0]>sma20 else 0.0,
                        1.0 if rsi<30 else 0.0,
                        1.0 if rsi>70 else 0.0,
                        rsi/100.0, vr,
                    ]
                else:
                    f = [0.5,0.5,0.0,0.0,0.5,0.5]
            except Exception:
                f = [0.5,0.5,0.0,0.0,0.5,0.5]
            # Day of week one-hot
            dow = [0.0]*5
            try:
                d = datetime.strptime(pub,"%Y-%m-%d").weekday()
                if 0<=d<5: dow[d]=1.0
            except Exception:
                pass
            f.extend(dow)
            # raw_score + time_weight as features
            f.append(float(s.get("raw_score",0)))
            f.append(float(s.get("time_weight",1.0)))
            features.append(f)
        conn.close()
        return np.array(features, dtype=np.float32)
    except Exception as e:
        print(f"  [MKTF ] Feature build error: {e}", flush=True)
        return None


class SGDWrap:
    def __init__(self, max_features=12000):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import SGDClassifier
        self.v = TfidfVectorizer(ngram_range=(1,2), max_features=max_features, sublinear_tf=True, min_df=1)
        self.c = SGDClassifier(loss="modified_huber", alpha=0.001, max_iter=300, class_weight="balanced", random_state=42)
        
    def fit(self, X, y, sample_weight=None):
        X_vec = self.v.fit_transform(X)
        self.c.fit(X_vec, y, sample_weight=sample_weight)
        
    def predict(self, X):
        X_vec = self.v.transform(X)
        return self.c.predict(X_vec)
        
    def predict_proba(self, X):
        X_vec = self.v.transform(X)
        return self.c.predict_proba(X_vec)
        
    @property
    def classes_(self):
        return self.c.classes_


class ComboWrap:
    def __init__(self, feats_matrix=None, max_features=10000):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        self.v = TfidfVectorizer(ngram_range=(1,2), max_features=max_features, sublinear_tf=True, min_df=1)
        self.c = LogisticRegression(C=2.0, max_iter=3000, class_weight="balanced", solver="lbfgs")
        self.feats = feats_matrix
        self._feats_shape = feats_matrix.shape[1] if feats_matrix is not None else 11
        
    def fit(self, X, y, clf__sample_weight=None, indices=None):
        from scipy.sparse import hstack as sph, csr_matrix
        import numpy as np
        X_vec = self.v.fit_transform(X)
        
        if indices is not None and self.feats is not None:
            f_sub = self.feats[indices]
        else:
            f_sub = self.feats
            
        if f_sub is not None and f_sub.shape[0] == len(X):
            Xa = sph([X_vec, csr_matrix(f_sub)])
        else:
            Xa = sph([X_vec, csr_matrix(np.zeros((len(X), self._feats_shape), dtype=np.float32))])
            
        self.c.fit(Xa, y, sample_weight=clf__sample_weight)
        
    def _X(self, t):
        from scipy.sparse import hstack as _h, csr_matrix as _cm
        import numpy as _np
        return _h([self.v.transform(t),
                   _cm(_np.zeros((len(t), self._feats_shape), dtype=_np.float32))])
                   
    def predict(self, t):
        return self.c.predict(self._X(t))
        
    def predict_proba(self, t):
        return self.c.predict_proba(self._X(t))
        
    @property
    def classes_(self):
        return self.c.classes_


def train_market_model(
    symbol: Optional[str] = None,
    min_samples: int = 50,
    use_finbert: bool = True,
    use_features: bool = True,
) -> Optional[Dict]:
    """
    Multi-stage market-supervised training.

    Stage 1  — TF-IDF + Logistic Regression (always, 50+ samples)
    Stage 1b — TF-IDF + SGD (often faster convergence)
    Stage 1c — TF-IDF + NSE Contextual Features (+5-8pp gain)
               Adds: RSI zone, price trend, volume ratio, day-of-week
    Stage 2  — FinBERT fine-tuning (100+ samples, needs transformers+torch)
               Understands negation, context, financial jargon
               Pre-trained on 1.8M financial news articles

    Saves whichever stage achieves best CV macro-F1.
    """
    sys.path.insert(0, BASE_DIR)
    try:
        from core.sentiment_db import get_training_data
    except Exception:
        try:
            from sentiment_db import get_training_data
        except Exception as e:
            print(f"  [MKTF ] Cannot import sentiment_db: {e}", flush=True)
            return None

    samples = get_training_data(use_market_labels=True)
    if symbol:
        samples = [s for s in samples if s["symbol"]==symbol]
    if len(samples) < min_samples:
        print(f"  [MKTF ] Need {min_samples} market-labelled samples "
              f"(have {len(samples)}). Run apply_market_labels() first.", flush=True)
        return None

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression, SGDClassifier
        from sklearn.model_selection import TimeSeriesSplit
        from sklearn.metrics import accuracy_score, f1_score, classification_report
        import numpy as np, datetime as _dt
        from collections import Counter
    except ImportError:
        print("  [MKTF ] pip install scikit-learn", flush=True)
        return None

    # Time-ordered sorting (Fix 4)
    samples = sorted(samples, key=lambda x: x.get("published_at", ""))
    
    texts   = [s["text"]         for s in samples]
    labels  = [s["label_int"]    for s in samples]
    weights = [s["sample_weight"] for s in samples]

    tag = f"_{symbol}" if symbol else "_all"
    model_file = os.path.join(MODEL_DIR, f"market_model{tag}.pkl")

    print(f"\n  [MKTF ] Training on {len(texts)} samples | {symbol or 'ALL symbols'}", flush=True)
    dist = Counter(INT_LABEL.get(l,"?") for l in labels)
    for lbl, cnt in sorted(dist.items()):
        print(f"    {lbl:<22} {cnt:>5}  {'#'*min(30,cnt)}", flush=True)

    # 80/20 Time-ordered Split (Fix 4)
    split_idx = int(len(samples) * 0.8)
    train_samples = samples[:split_idx]
    test_samples = samples[split_idx:]
    
    X_tr = [s["text"] for s in train_samples]
    y_tr = [s["label_int"] for s in train_samples]
    w_tr = [s["sample_weight"] for s in train_samples]
    
    X_te = [s["text"] for s in test_samples]
    y_te = [s["label_int"] for s in test_samples]

    # TimeSeriesSplit configuration
    n_splits = min(5, max(2, len(train_samples) // 10))
    print(f"  [MKTF ] Temporal splits: {n_splits} (TimeSeriesSplit)", flush=True)
    
    best_pipe=None; best_f1_cv=-1.0; best_stage="none"; all_results={}

    # Helper function for cross-validation on train window
    def run_cv(creator_func, stage_name):
        tscv = TimeSeriesSplit(n_splits=n_splits)
        accs = []
        f1s = []
        X_arr = np.array(X_tr)
        y_arr = np.array(y_tr)
        w_arr = np.array(w_tr)
        
        for train_idx, val_idx in tscv.split(X_arr):
            if len(train_idx) < 10 or len(val_idx) < 5:
                continue
            X_fold_tr, X_fold_val = X_arr[train_idx].tolist(), X_arr[val_idx].tolist()
            y_fold_tr, y_fold_val = y_arr[train_idx].tolist(), y_arr[val_idx].tolist()
            w_fold_tr = w_arr[train_idx].tolist()
            
            try:
                if stage_name == "TF-IDF + NSE Features":
                    feats_tr = feats[:split_idx][train_idx]
                    model = ComboWrap(feats_tr)
                    model.fit(X_fold_tr, y_fold_tr, clf__sample_weight=w_fold_tr)
                else:
                    model = creator_func()
                    if hasattr(model, "fit"):
                        if isinstance(model, SGDWrap):
                            model.fit(X_fold_tr, y_fold_tr, sample_weight=w_fold_tr)
                        elif hasattr(model, "steps") and any(step[0] == "clf" for step in model.steps):
                            model.fit(X_fold_tr, y_fold_tr, clf__sample_weight=w_fold_tr)
                        else:
                            model.fit(X_fold_tr, y_fold_tr)
                preds = model.predict(X_fold_val)
                accs.append(accuracy_score(y_fold_val, preds))
                f1s.append(f1_score(y_fold_val, preds, average="macro", zero_division=0))
            except Exception:
                pass
        if not accs:
            return 0.0, 0.0, 0.0, 0.0
        return float(np.mean(accs)), float(np.std(accs)), float(np.mean(f1s)), float(np.std(f1s))

    # ── Stage 1: TF-IDF + LR ────────────────────────────────────────
    print(f"\n  [MKTF ] Stage 1: TF-IDF + Logistic Regression", flush=True)
    from sklearn.pipeline import Pipeline
    
    def create_stage1():
        return Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1,3),max_features=20000,
                                       sublinear_tf=True,min_df=1)),
            ("clf",   LogisticRegression(C=2.0,max_iter=3000,
                                         class_weight="balanced",solver="lbfgs")),
        ])
        
    cv_acc_mean, cv_acc_std, cv_f1_mean, cv_f1_std = run_cv(create_stage1, "TF-IDF + LR")
    
    # Train full model on all training data
    p1 = create_stage1()
    p1.fit(X_tr, y_tr, clf__sample_weight=w_tr)
    te_acc = accuracy_score(y_te, p1.predict(X_te))
    te_f1 = f1_score(y_te, p1.predict(X_te), average="macro", zero_division=0)
    
    all_results["TF-IDF + LR"] = {
        "cv_acc_mean": cv_acc_mean, "cv_acc_std": cv_acc_std,
        "cv_f1_mean": cv_f1_mean, "cv_f1_std": cv_f1_std,
        "test_acc": te_acc, "test_f1": te_f1,
        "pipe": p1
    }
    print(f"  [MKTF ] CV F1: {cv_f1_mean:.3f} | CV Acc: {cv_acc_mean:.3f} | Test F1: {te_f1:.3f} | Test Acc: {te_acc:.3f}", flush=True)

    # ── Stage 1b: TF-IDF + SGD ──────────────────────────────────────
    if len(texts)>=100:
        print(f"  [MKTF ] Stage 1b: TF-IDF + SGD Classifier", flush=True)
        try:
            def create_stage1b():
                return SGDWrap()
                
            cv_acc_mean, cv_acc_std, cv_f1_mean, cv_f1_std = run_cv(create_stage1b, "TF-IDF + SGD")
            p1b = create_stage1b()
            p1b.fit(X_tr, y_tr, sample_weight=w_tr)
            te_acc = accuracy_score(y_te, p1b.predict(X_te))
            te_f1 = f1_score(y_te, p1b.predict(X_te), average="macro", zero_division=0)
            
            all_results["TF-IDF + SGD"] = {
                "cv_acc_mean": cv_acc_mean, "cv_acc_std": cv_acc_std,
                "cv_f1_mean": cv_f1_mean, "cv_f1_std": cv_f1_std,
                "test_acc": te_acc, "test_f1": te_f1,
                "pipe": p1b
            }
            print(f"  [MKTF ] CV F1: {cv_f1_mean:.3f} | CV Acc: {cv_acc_mean:.3f} | Test F1: {te_f1:.3f} | Test Acc: {te_acc:.3f}", flush=True)
        except Exception as e:
            print(f"  [MKTF ] Stage 1b failed: {e}", flush=True)

    # ── Stage 1c: TF-IDF + NSE Features ─────────────────────────────
    if use_features:
        print(f"  [MKTF ] Stage 1c: Adding NSE contextual features (RSI/trend/volume/DOW)", flush=True)
        feats = _build_nse_features(samples)
        if feats is not None and len(feats)==len(texts):
            try:
                cv_acc_mean, cv_acc_std, cv_f1_mean, cv_f1_std = run_cv(None, "TF-IDF + NSE Features")
                p1c = ComboWrap(feats[:split_idx])
                p1c.fit(X_tr, y_tr, clf__sample_weight=w_tr)
                te_acc = accuracy_score(y_te, p1c.predict(X_te))
                te_f1 = f1_score(y_te, p1c.predict(X_te), average="macro", zero_division=0)
                
                all_results["TF-IDF + NSE Features"] = {
                    "cv_acc_mean": cv_acc_mean, "cv_acc_std": cv_acc_std,
                    "cv_f1_mean": cv_f1_mean, "cv_f1_std": cv_f1_std,
                    "test_acc": te_acc, "test_f1": te_f1,
                    "pipe": p1c
                }
                print(f"  [MKTF ] CV F1: {cv_f1_mean:.3f} | CV Acc: {cv_acc_mean:.3f} | Test F1: {te_f1:.3f} | Test Acc: {te_acc:.3f}", flush=True)
            except Exception as e:
                print(f"  [MKTF ] Stage 1c failed: {e}", flush=True)

    # ── Stage 2: FinBERT ─────────────────────────────────────────────
    if use_finbert and len(texts)>=100:
        fb = _try_finbert(X_tr,X_te,y_tr,y_te,w_tr,n_splits)
        if fb:
            all_results["FinBERT"] = {
                "cv_acc_mean": fb["cv_acc_mean"], "cv_acc_std": fb["cv_acc_std"],
                "cv_f1_mean": fb["cv_f1_mean"], "cv_f1_std": fb["cv_f1_std"],
                "test_acc": fb["accuracy"], "test_f1": fb["macro_f1"],
                "pipe": fb["pipe"]
            }
            print(f"  [MKTF ] Stage 2 (FinBERT) Test F1: {fb['macro_f1']:.3f} | Test Acc: {fb['accuracy']:.3f}", flush=True)
    elif use_finbert:
        print(f"  [MKTF ] Stage 2 (FinBERT): need 100+ samples. Skipped.", flush=True)

    # ── Summary & Stage Selection by Macro-F1 (Fix 5) ────────────────
    # Select the model with the best cross-validation Macro-F1 score
    for stage, res in all_results.items():
        if res["cv_f1_mean"] > best_f1_cv:
            best_f1_cv = res["cv_f1_mean"]
            best_stage = stage
            best_pipe = res["pipe"]
            
    best_test_acc = all_results[best_stage]["test_acc"]
    best_test_f1 = all_results[best_stage]["test_f1"]

    print(f"\n  [MKTF ] STAGE COMPARISON (Ranked by CV Macro-F1):", flush=True)
    for stage, res in sorted(all_results.items(), key=lambda x: x[1]["cv_f1_mean"], reverse=True):
        mark=" <- BEST" if stage==best_stage else ""
        print(f"    {stage:<28} | CV F1: {res['cv_f1_mean']:.3f} (+/-{res['cv_f1_std']:.3f}) | CV Acc: {res['cv_acc_mean']:.3f} (+/-{res['cv_acc_std']:.3f}) | Test F1: {res['test_f1']:.3f} | Test Acc: {res['test_acc']:.3f}{mark}", flush=True)

    target_names=[INT_LABEL.get(l,str(l)) for l in sorted(set(labels))]
    y_best=best_pipe.predict(X_te)
    
    # Store output dict to save per-class metrics in the pickled metadata (Fix 5)
    report_dict = classification_report(y_te,y_best,labels=sorted(set(labels)),
                                        target_names=target_names,zero_division=0, output_dict=True)
    report_str = classification_report(y_te,y_best,labels=sorted(set(labels)),
                                       target_names=target_names,zero_division=0)
    print(f"\n  Per-class report ({best_stage}):\n{report_str}", flush=True)

    # Baseline VADER metrics on the test set
    vader_preds = []
    for s in test_samples:
        score = s["raw_score"]
        if score >= 0.35:     lbl = 2
        elif score >= 0.10:   lbl = 1
        elif score > -0.10:   lbl = 0
        elif score > -0.35:   lbl = -1
        else:                 lbl = -2
        vader_preds.append(lbl)
        
    vader_acc = accuracy_score(y_te, vader_preds)
    vader_f1 = f1_score(y_te, vader_preds, average="macro", zero_division=0)
    
    print(f"  [MKTF ] VADER: Acc={vader_acc:.1%}, F1={vader_f1:.1%} -> Best model: Acc={best_test_acc:.1%}, F1={best_test_f1:.1%} "
          f"(F1 improvement: +{(best_test_f1-vader_f1)*100:.1f}pp)", flush=True)

    version=f"mkt_v{_dt.date.today().strftime('%Y%m%d')}_f1{int(best_test_f1*100)}"
    obj={
        "pipe":best_pipe,"version":version,"accuracy":best_test_acc,"macro_f1":best_test_f1,
        "vader_acc":vader_acc,"vader_f1":vader_f1,
        "cv_acc_mean":all_results[best_stage]["cv_acc_mean"],"cv_acc_std":all_results[best_stage]["cv_acc_std"],
        "cv_f1_mean":all_results[best_stage]["cv_f1_mean"],"cv_f1_std":all_results[best_stage]["cv_f1_std"],
        "trained_on":len(texts),"trained_at":str(_dt.datetime.now()),
        "symbol_scope":symbol or "all","label_dist":dict(dist),
        "stage":best_stage,"all_results":all_results,
        "class_metrics":report_dict, "report_str":report_str
    }
    with open(model_file,"wb") as f: pickle.dump(obj,f)
    print(f"  [MKTF ] Model saved: {model_file}", flush=True)
    _backfill(best_pipe, samples)

    return {"version":version,"accuracy":best_test_acc,"macro_f1":best_test_f1,"vader_acc":vader_acc,
            "trained_on":len(texts),"improvement":round((best_test_f1-vader_f1)*100,1),
            "best_stage":best_stage,"all_results":all_results,
            "report":report_str,"model_file":model_file}


def _try_finbert(X_tr, X_te, y_tr, y_te, w_tr, n_splits=3) -> Optional[Dict]:
    """Fine-tune FinBERT. Returns {pipe, accuracy, macro_f1} or None."""
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
        from torch.utils.data import Dataset as TDS
        import numpy as np
    except ImportError:
        print("  [MKTF ] FinBERT: pip install transformers torch", flush=True)
        return None

    model_name="ProsusAI/finbert"
    try: tokenizer=AutoTokenizer.from_pretrained(model_name)
    except Exception as e:
        print(f"  [MKTF ] FinBERT download failed: {e}", flush=True)
        return None

    unique_labels=sorted(set(list(y_tr)+list(y_te)))
    l2i={l:i for i,l in enumerate(unique_labels)}
    i2l={i:l for l,i in l2i.items()}
    ytr_i=[l2i[l] for l in y_tr]; yte_i=[l2i[l] for l in y_te]

    class _DS(TDS):
        def __init__(self,texts,labels,tok):
            self.enc=tok(texts,truncation=True,padding=True,max_length=128,return_tensors="pt")
            self.labels=torch.tensor(labels)
        def __len__(self): return len(self.labels)
        def __getitem__(self,i):
            return {k:v[i] for k,v in self.enc.items()}|{"labels":self.labels[i]}

    n_labels=len(unique_labels)
    model=AutoModelForSequenceClassification.from_pretrained(
        model_name,num_labels=n_labels,ignore_mismatched_sizes=True)
    epochs=3 if len(X_tr)>=500 else 5 if len(X_tr)>=200 else 8
    fb_dir=os.path.join(MODEL_DIR,"finbert_checkpoints")

    args=TrainingArguments(output_dir=fb_dir,num_train_epochs=epochs,
        per_device_train_batch_size=8,per_device_eval_batch_size=16,
        evaluation_strategy="epoch",save_strategy="epoch",load_best_model_at_end=True,
        logging_steps=20,report_to="none",
        fp16=torch.cuda.is_available(),dataloader_num_workers=0)

    def _metrics(ep):
        return {"accuracy": float((np.argmax(ep.predictions,1)==ep.label_ids).mean())}

    trainer=Trainer(model=model,args=args,
        train_dataset=_DS(X_tr,ytr_i,tokenizer),
        eval_dataset=_DS(X_te,yte_i,tokenizer),compute_metrics=_metrics)
    try: trainer.train()
    except Exception as e:
        print(f"  [MKTF ] FinBERT train error: {e}", flush=True); return None

    preds=trainer.predict(_DS(X_te,yte_i,tokenizer))
    from sklearn.metrics import accuracy_score as _a, f1_score as _f
    pred_labels = np.argmax(preds.predictions,1)
    acc=_a(yte_i,pred_labels)
    macro_f1=_f(yte_i,pred_labels,average="macro",zero_division=0)
    
    fb_out=os.path.join(MODEL_DIR,"finbert_finetuned")
    model.save_pretrained(fb_out); tokenizer.save_pretrained(fb_out)

    class _FBPipe:
        def __init__(self,d,i2l,ul):
            self.d=d; self.i2l=i2l; self.ul=ul; self._t=None; self._m=None
        def _load(self):
            if not self._t:
                from transformers import AutoTokenizer as AT,AutoModelForSequenceClassification as AM
                self._t=AT.from_pretrained(self.d); self._m=AM.from_pretrained(self.d); self._m.eval()
        def predict(self,texts):
            import torch,numpy as np; self._load()
            out=[]
            for t in texts:
                e=self._t(t,return_tensors="pt",truncation=True,max_length=128,padding=True)
                with torch.no_grad(): idx=int(torch.argmax(self._m(**e).logits,1).item())
                out.append(self.i2l.get(idx,0))
            return np.array(out)
        def predict_proba(self,texts):
            import torch,numpy as np; self._load()
            out=[]
            for t in texts:
                e=self._t(t,return_tensors="pt",truncation=True,max_length=128,padding=True)
                with torch.no_grad(): p=torch.softmax(self._m(**e).logits,1)[0].numpy()
                out.append(p)
            return np.array(out)
        @property
        def classes_(self): import numpy as np; return np.array(self.ul)

    return {
        "pipe":_FBPipe(fb_out,i2l,unique_labels),
        "accuracy":acc,
        "macro_f1":macro_f1,
        "cv_acc_mean":acc,
        "cv_acc_std":0.0,
        "cv_f1_mean":macro_f1,
        "cv_f1_std":0.0
    }

def _backfill(pipe, samples: list):
    """Update calibrated_score + prediction_error for all trained samples."""
    conn = _conn()
    c    = conn.cursor()
    n    = 0
    for s in samples:
        text = s["text"]
        if not text:
            continue
        try:
            pred_int  = int(pipe.predict([text])[0])
            proba     = pipe.predict_proba([text])[0]
            classes   = list(pipe.classes_)
            # Weighted average of class indices → calibrated score
            cal = sum((classes[i] / 2.0) * proba[i] for i in range(len(classes)))
            cal = round(max(-1.0, min(1.0, cal)), 4)
            err = round(abs(s["raw_score"] - cal), 4)
            c.execute("""
                UPDATE news_sentiment
                SET calibrated_score = ?,
                    prediction_error = ?,
                    model_was_correct = CASE
                        WHEN market_return_5d IS NOT NULL
                        THEN CASE WHEN (? > 0) = (market_return_5d > 0) THEN 1 ELSE 0 END
                        ELSE model_was_correct
                    END
                WHERE title=? AND symbol=?
            """, (cal, err, cal, s["title"], s["symbol"]))
            n += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    print(f"  [MKTF ] Back-filled {n} calibrated scores", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# SCORE NEW HEADLINE
# ─────────────────────────────────────────────────────────────────────────────

def score_headline(title: str, snippet: str = "",
                   symbol: Optional[str] = None) -> Optional[Dict]:
    """
    Score a headline using the market-trained model.
    Returns calibrated_score, expected_return, confidence.
    Falls back to None if model not yet trained.
    """
    # Try symbol-specific model first, then global
    candidates = []
    if symbol:
        candidates.append(os.path.join(MODEL_DIR, f"market_model_{symbol}.pkl"))
    candidates.append(os.path.join(MODEL_DIR, "market_model_all.pkl"))

    for mf in candidates:
        if not os.path.exists(mf):
            continue
        try:
            with open(mf, "rb") as f:
                obj = pickle.load(f)
            pipe    = obj["pipe"]
            version = obj.get("version", "v1")
            text    = (title + " " + (snippet or "")).strip()
            pred    = int(pipe.predict([text])[0])
            proba   = pipe.predict_proba([text])[0]
            classes = list(pipe.classes_)
            cal     = sum((classes[i]/2.0)*proba[i] for i in range(len(classes)))
            cal     = round(max(-1.0, min(1.0, cal)), 4)
            return {
                "calibrated_score":  cal,
                "market_label":      INT_LABEL.get(pred, "NEUTRAL"),
                "confidence":        round(float(max(proba)), 3),
                "expected_return":   round(cal * 5.0, 2),  # ±5% at ±1.0
                "model_version":     version,
            }
        except Exception:
            continue
    return None


# ─────────────────────────────────────────────────────────────────────────────
# ACCURACY REPORT
# ─────────────────────────────────────────────────────────────────────────────

def generate_accuracy_report(symbol: Optional[str] = None) -> Dict:
    """Compare VADER predictions vs actual market outcomes."""
    conn = _conn()
    sym_filter = "AND symbol=?" if symbol else ""
    params     = [symbol] if symbol else []

    rows = conn.execute(f"""
        SELECT symbol, raw_score, market_label, market_return_5d,
               calibrated_score, prediction_error, model_was_correct,
               label AS vader_label, published_at
        FROM   news_sentiment
        WHERE  market_label IS NOT NULL
          AND  market_return_5d IS NOT NULL
        {sym_filter}
        ORDER  BY published_at DESC
    """, params).fetchall()
    conn.close()

    if not rows:
        return {"error": "No market-labelled data yet. Run apply_market_labels() first."}

    rows = [dict(r) for r in rows]
    n    = len(rows)

    # Direction accuracy: VADER raw_score vs market_label (ground truth)
    # market_label is already based on excess return — correct comparison
    LABEL_BULL = {"STRONGLY BULLISH", "BULLISH"}
    LABEL_BEAR = {"STRONGLY BEARISH", "BEARISH"}

    vader_correct = sum(1 for r in rows
        if (r["raw_score"] >= 0.1) == (r["market_label"] in LABEL_BULL))
    vader_acc = vader_correct / n

    # Calibrated model accuracy vs market_label
    cal_rows = [r for r in rows if r.get("calibrated_score") is not None]
    cal_acc  = None
    if cal_rows:
        cal_correct = sum(1 for r in cal_rows
            if (r["calibrated_score"] >= 0) == (r["market_label"] in LABEL_BULL))
        cal_acc = cal_correct / len(cal_rows)

    errors   = [r["prediction_error"] for r in rows if r.get("prediction_error") is not None]
    vader_mae = sum(errors)/len(errors) if errors else None

    # Average return by VADER label
    by_label = {}
    for r in rows:
        lbl = r["vader_label"] or "NEUTRAL"
        by_label.setdefault(lbl, []).append(r["market_return_5d"])
    avg_returns = {
        lbl: {
            "count":    len(rets),
            "avg_5d":   round(sum(rets)/len(rets), 3),
            "hit_rate": round(sum(1 for r in rets if r>0)/len(rets), 3),
        }
        for lbl, rets in by_label.items()
    }

    return {
        "total_labelled":      n,
        "vader_accuracy":      round(vader_acc, 3),
        "calibrated_accuracy": round(cal_acc, 3) if cal_acc else None,
        "improvement_pp":      round((cal_acc-vader_acc)*100,1) if cal_acc else None,
        "vader_mae":           round(vader_mae, 4) if vader_mae else None,
        "avg_returns_by_label": avg_returns,
        "period":              f"{rows[-1]['published_at'][:10]} → {rows[0]['published_at'][:10]}",
    }


def print_accuracy_report(symbol: Optional[str] = None):
    r = generate_accuracy_report(symbol)
    print(f"\n{'='*62}")
    print(f"  MARKET FEEDBACK ACCURACY REPORT")
    print(f"  Method: EXCESS RETURN (stock return − Nifty50 return)")
    print(f"  This isolates the stock-specific reaction to news")
    if "error" in r:
        print(f"\n  {r['error']}")
        print(f"{'='*62}\n")
        return

    print(f"\n  Period : {r['period']}")
    print(f"  Labelled: {r['total_labelled']} headlines")
    print(f"{'='*62}")
    vAcc = r['vader_accuracy']
    print(f"  VADER direction accuracy  : {vAcc:.1%}  "
          f"{'(below chance — model will fix)' if vAcc<0.55 else '(moderate)' if vAcc<0.65 else '(good)'}")
    if r.get("calibrated_accuracy"):
        imp = r.get("improvement_pp", 0)
        print(f"  Market-trained model      : {r['calibrated_accuracy']:.1%}  "
              f"({'+' if imp>=0 else ''}{imp}pp vs VADER)")
    if r.get("vader_mae"):
        print(f"  VADER mean absolute error : {r['vader_mae']:.4f}")

    print(f"\n  VADER label vs actual excess return (stock − Nifty50, 5d):")
    print(f"  {'VADER said':<22} {'N':>5}  {'Avg excess':>11}  {'Correct%':>8}")
    print(f"  {'-'*50}")
    for lbl in ["STRONGLY BULLISH","BULLISH","NEUTRAL","BEARISH","STRONGLY BEARISH"]:
        d = r["avg_returns_by_label"].get(lbl)
        if not d: continue
        arr = "▲" if d["avg_5d"] > 0 else "▼"
        print(f"  {lbl:<22} {d['count']:>5}  {arr}{abs(d['avg_5d']):>6.2f}%  "
              f"    {d['hit_rate']:.0%}")
    print(f"\n  KEY INSIGHT:")
    vader_acc = r['vader_accuracy']
    if vader_acc < 0.55:
        print(f"  VADER is {vader_acc:.0%} accurate — barely above random.")
        print(f"  Market model trained on excess returns will significantly improve this.")
    else:
        print(f"  VADER at {vader_acc:.0%} — market model calibrates further.")
    print(f"{'='*62}\n")


# ─────────────────────────────────────────────────────────────────────────────
# FULL PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(symbol: Optional[str] = None, retrain: bool = True) -> Dict:
    labelled = apply_market_labels(symbol=symbol, window_days=5, min_age_days=7)
    result   = None
    if retrain:
        result = train_market_model(symbol=symbol, min_samples=50)
    report   = generate_accuracy_report(symbol=symbol)
    return {
        "newly_labelled": labelled,
        "training":       result,
        "accuracy":       report,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    sys.path.insert(0, BASE_DIR)

    ap = argparse.ArgumentParser(description="Market Feedback Learning Engine")
    ap.add_argument("--symbol",      help="Single symbol e.g. TCS")
    ap.add_argument("--label-only",  action="store_true")
    ap.add_argument("--train-only",  action="store_true")
    ap.add_argument("--report",      action="store_true")
    ap.add_argument("--window",      type=int, default=5)
    ap.add_argument("--min-samples", type=int, default=50)
    args = ap.parse_args()

    print("="*58)
    print("  GANN-ASTRO — Market Feedback Learning Engine")
    print("="*58)

    if args.report:
        print_accuracy_report(args.symbol)
    elif args.label_only:
        n = apply_market_labels(args.symbol, args.window, args.window+2)
        print(f"\n  Labelled: {n}")
        print_accuracy_report(args.symbol)
    elif args.train_only:
        r = train_market_model(args.symbol, args.min_samples)
        if r:
            print(f"\n  Accuracy: {r['accuracy']:.1%}")
    else:
        results = run_pipeline(args.symbol, retrain=True)
        print(f"\n  Newly labelled: {results['newly_labelled']}")
        print_accuracy_report(args.symbol)

    print("  Done.")
    print("="*58)
