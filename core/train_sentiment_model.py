"""
train_sentiment_model.py — Fine-tune a sentiment model on your collected headlines
Place in: core/train_sentiment_model.py
Run:      python core/train_sentiment_model.py

STAGE 1 (available now, no GPU):
    Uses scikit-learn TF-IDF + Logistic Regression
    Trains on your collected headlines from sentiment_training_data.jsonl
    Saves model to: core/sentiment_model.pkl
    Typical accuracy: 75–85% on financial headlines

STAGE 2 (optional upgrade, needs GPU or patience):
    Fine-tunes FinBERT (HuggingFace) on your labelled data
    Requires:  pip install transformers torch
    Much higher accuracy: 88–95%

WORKFLOW:
    1. Run the app and analyse stocks — headlines auto-saved to .jsonl
    2. Open core/sentiment_training_data.jsonl
    3. For each entry, fill in "human_label": "BULLISH" / "BEARISH" / "NEUTRAL"
       (only label the ones you're sure about — even 50 labelled = useful)
    4. Run this script
    5. Model is saved and auto-loaded by sentiment_external.py
"""

import os, sys
import warnings
warnings.filterwarnings('ignore')

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE  = os.path.join(BASE_DIR, "sentiment_model.pkl")
REPORT_FILE = os.path.join(BASE_DIR, "sentiment_model_report.txt")

LABEL_MAP   = {"STRONGLY BULLISH": 2, "BULLISH": 1, "NEUTRAL": 0,
               "BEARISH": -1, "STRONGLY BEARISH": -2}
REV_MAP     = {v: k for k, v in LABEL_MAP.items()}


def load_data(use_human_only=False):
    """Load training data from market_data_v2.db → news_sentiment + sentiment_labels."""
    try:
        from core.sentiment_db import get_training_data, get_stats
    except ImportError:
        print("  ERROR: core.sentiment_db not found.")
        print("  Make sure sentiment_db.py is in your core/ folder.")
        return [], []

    stats = get_stats()
    print(f"  DB stats: {stats.get('total_headlines',0):,} headlines  "
          f"| {stats.get('human_labelled',0)} human-labelled "
          f"| {stats.get('unique_symbols',0)} symbols")

    samples = get_training_data(use_human_only=use_human_only)
    if not samples:
        print("  No training data in DB yet.")
        print("  Analyse stocks in the app — headlines are collected automatically.")
        return [], []

    texts  = [s["text"] for s in samples]
    labels = [s["label_int"] for s in samples]
    h_ct   = sum(1 for s in samples if s["label_source"] == "HUMAN")
    v_ct   = sum(1 for s in samples if s["label_source"] == "VADER")
    m_ct   = sum(1 for s in samples if s["label_source"] == "MODEL")
    print(f"  Loaded {len(texts)} samples  "
          f"({h_ct} human  {m_ct} model  {v_ct} VADER-labelled)")
    return texts, labels


def train_sklearn(texts, labels, all_samples=None):
    """
    TF-IDF + Logistic Regression.
    After training, saves model predictions back to DB so every
    headline gets a model_score alongside the VADER score.
    Accuracy improves month-over-month as more data accumulates.
    """
    try:
        from sklearn.pipeline import Pipeline
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import cross_val_score, train_test_split
        from sklearn.metrics import classification_report
        import numpy as np
        import pickle
        import datetime as _dt2
    except ImportError:
        print("  scikit-learn not found. Install: pip install scikit-learn")
        return None

    print(f"\n  -- STAGE 1: TF-IDF + Logistic Regression ({len(texts)} samples) --")

    label_counts = {}
    for l in labels: label_counts[l] = label_counts.get(l, 0) + 1
    can_stratify = all(c >= 2 for c in label_counts.values()) and len(set(labels)) > 1

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42,
        stratify=labels if can_stratify else None
    )

    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 3), max_features=10000,
                                  sublinear_tf=True, min_df=1)),
        ("clf",   LogisticRegression(C=1.5, max_iter=2000,
                                     class_weight="balanced", solver="lbfgs")),
    ])

    if len(texts) >= 50:
        cv = min(5, min(label_counts.values()))
        if cv >= 2:
            cv_s = cross_val_score(pipe, texts, labels, cv=cv, scoring="accuracy")
            print(f"  Cross-val accuracy : {cv_s.mean():.3f} +/- {cv_s.std():.3f}")

    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    acc    = float((np.array(y_pred) == np.array(y_test)).mean())
    print(f"  Test accuracy      : {acc:.3f}  ({int(acc*len(y_test))}/{len(y_test)} correct)")

    target_names = [REV_MAP.get(l, str(l)) for l in sorted(set(labels))]
    report = classification_report(y_test, y_pred, labels=sorted(set(labels)),
                                   target_names=target_names, zero_division=0)
    print(f"\n  Per-class report:\n{report}")

    # Save model with metadata
    version    = f"v{_dt2.date.today().strftime('%Y%m%d')}_acc{int(acc*100)}"
    model_obj  = {"pipe": pipe, "version": version, "accuracy": acc,
                  "trained_on": len(texts), "trained_at": str(_dt2.datetime.now())}
    with open(MODEL_FILE, "wb") as f2:
        pickle.dump(model_obj, f2)
    print(f"  Model saved        : {MODEL_FILE}  [{version}]")

    with open(REPORT_FILE, "w", encoding="utf-8") as f3:
        f3.write(f"GANN-ASTRO Sentiment Model\nVersion: {version}\n")
        f3.write(f"Samples: {len(texts)}  Accuracy: {acc:.3f}\n\n{report}")
    print(f"  Report saved       : {REPORT_FILE}")

    # Back-fill model predictions to DB
    if all_samples:
        print(f"\n  Back-filling {len(all_samples)} model predictions to DB...")
        try:
            sys.path.insert(0, os.path.join(BASE_DIR, "core"))
            from sentiment_db import save_model_prediction
            saved_ct = 0
            for s in all_samples:
                text2 = s.get("text", "")
                if not text2: continue
                pred_int    = int(pipe.predict([text2])[0])
                proba       = pipe.predict_proba([text2])[0]
                pred_label  = REV_MAP.get(pred_int, "NEUTRAL")
                pred_score  = pred_int / 2.0
                ok = save_model_prediction(s["symbol"], s["title"],
                         pred_label, pred_score, float(max(proba)), version)
                if ok: saved_ct += 1
            print(f"  Saved {saved_ct}/{len(all_samples)} model predictions to DB")
        except Exception as e2:
            print(f"  Could not save predictions: {e2}")

    return pipe


def train_finbert(texts, labels):
    """
    Stage 2: Fine-tune FinBERT (much higher accuracy, needs GPU/patience).
    Only runs if transformers + torch are installed.
    """
    try:
        import torch
        from transformers import (AutoTokenizer, AutoModelForSequenceClassification,
                                  TrainingArguments, Trainer)
        import numpy as np
        from torch.utils.data import Dataset
    except ImportError:
        print("\n  ── STAGE 2: FinBERT fine-tuning ──")
        print("  Not available. Install: pip install transformers torch")
        print("  Skip to Stage 1 for now.")
        return None

    print("\n  ── STAGE 2: FinBERT fine-tuning ──")
    model_name = "ProsusAI/finbert"
    tokenizer  = AutoTokenizer.from_pretrained(model_name)
    num_labels = len(set(labels))

    # Remap labels to 0-indexed for PyTorch
    unique_labels = sorted(set(labels))
    label_to_idx  = {l: i for i, l in enumerate(unique_labels)}
    idx_to_label  = {i: l for l, i in label_to_idx.items()}
    y_indexed     = [label_to_idx[l] for l in labels]

    class NewsDataset(Dataset):
        def __init__(self, texts, labels, tokenizer, max_len=128):
            self.encodings = tokenizer(texts, truncation=True, padding=True,
                                       max_length=max_len, return_tensors="pt")
            self.labels    = torch.tensor(labels)
        def __len__(self):  return len(self.labels)
        def __getitem__(self, i):
            return {k: v[i] for k, v in self.encodings.items()} | {"labels": self.labels[i]}

    split = int(len(texts) * 0.8)
    train_ds = NewsDataset(texts[:split],     y_indexed[:split],  tokenizer)
    eval_ds  = NewsDataset(texts[split:],     y_indexed[split:],  tokenizer)

    model = AutoModelForSequenceClassification.from_pretrained(model_name,
                                                                num_labels=num_labels)
    args = TrainingArguments(
        output_dir    = os.path.join(BASE_DIR, "finbert_checkpoints"),
        num_train_epochs         = 3,
        per_device_train_batch_size = 8,
        per_device_eval_batch_size  = 16,
        evaluation_strategy      = "epoch",
        save_strategy            = "epoch",
        load_best_model_at_end   = True,
        logging_dir              = os.path.join(BASE_DIR, "finbert_logs"),
        logging_steps            = 10,
        report_to                = "none",
    )
    trainer = Trainer(model=model, args=args, train_dataset=train_ds, eval_dataset=eval_ds)
    trainer.train()

    # Save
    finbert_out = os.path.join(BASE_DIR, "finbert_finetuned")
    model.save_pretrained(finbert_out)
    tokenizer.save_pretrained(finbert_out)
    print(f"  FinBERT model saved → {finbert_out}")
    return model


def score_with_model(text):
    """Use saved model to score a headline. Returns dict or None."""
    if not os.path.exists(MODEL_FILE):
        return None
    try:
        import pickle
        with open(MODEL_FILE, "rb") as f4:
            obj = pickle.load(f4)
        pipe     = obj["pipe"]     if isinstance(obj, dict) else obj
        version  = obj.get("version",  "v1")   if isinstance(obj, dict) else "v1"
        accuracy = obj.get("accuracy",  None)   if isinstance(obj, dict) else None
        pred_int    = int(pipe.predict([text])[0])
        proba       = pipe.predict_proba([text])[0]
        return {
            "score":      round(pred_int / 2.0, 3),
            "label":      REV_MAP.get(pred_int, "NEUTRAL"),
            "confidence": round(float(max(proba)), 3),
            "version":    version,
            "accuracy":   round(float(accuracy), 3) if accuracy else None,
        }
    except Exception:
        return None


def show_training_stats():
    """Print statistics about sentiment data from market_data_v2.db."""
    try:
        from core.sentiment_db import get_stats
    except ImportError:
        print("  ERROR: core/sentiment_db.py not found.")
        return

    s = get_stats()
    if "error" in s:
        print(f"  DB error: {s['error']}")
        return

    total   = s.get("total_headlines", 0)
    human   = s.get("human_labelled",  0)
    model   = s.get("model_labelled",  0)
    syms    = s.get("unique_symbols",  0)
    latest  = s.get("latest_fetch",    "—")

    print(f"\n  ═══ SENTIMENT DB STATS ═══")
    print(f"  Total headlines  : {total:,}")
    print(f"  Unique symbols   : {syms}")
    print(f"  Human-labelled   : {human}  ({'%.0f' % (human/total*100) if total else 0}%)")
    print(f"  Model-labelled   : {model}")
    print(f"  Latest fetch     : {latest}")

    print(f"\n  Label distribution (VADER scores):")
    for row in s.get("label_distribution", []):
        lbl = row.get("label","?"); cnt = row.get("cnt",0)
        bar = "█" * (cnt * 30 // max(total,1))
        print(f"    {lbl:<20} {cnt:>5}  {bar}")

    print(f"\n  Top symbols by article count:")
    for row in s.get("top_symbols", []):
        print(f"    {row.get('symbol','?'):<22} {row.get('cnt',0):>5} articles")

    print()
    if human < 20:
        print("  ⚠  Need 20+ human labels for quality training.")
        print("  Label headlines using the app UI or via SQL:")
        print("    UPDATE sentiment_labels")
        print("    SET human_label = 'BULLISH', labelled_at = datetime('now')")
        print("    WHERE label_source = 'VADER' AND title LIKE '%beats estimates%';")
    else:
        print(f"  ✓  {human} human labels — ready to train!")
        print(f"     Run: python core/train_sentiment_model.py")


if __name__ == "__main__":
    print("=" * 58)
    print("  GANN·ASTRO — Sentiment Model Training")
    print("=" * 58)

    show_training_stats()
    texts, labels = load_data(use_human_labels=True)

    if not texts:
        print("\n  No data to train on. Analyse some stocks in the app first.")
        sys.exit(0)

    if len(texts) < 10:
        print(f"\n  Only {len(texts)} samples — need at least 10 to train.")
        print("  Keep using the app; headlines are collected automatically.")
        sys.exit(0)

    # Stage 1: load all sample objects so predictions go back to DB
    try:
        sys.path.insert(0, os.path.join(BASE_DIR, "core"))
        from sentiment_db import get_training_data as _gd
        all_samples = _gd()
    except Exception:
        all_samples = None
    model = train_sklearn(texts, labels, all_samples=all_samples)

    # Stage 2 only if transformers available and > 100 samples
    if len(texts) >= 100:
        train_finbert(texts, labels)
    else:
        print(f"\n  ── STAGE 2: FinBERT ──")
        print(f"  Need 100+ samples (have {len(texts)}). Keep collecting data.")

    print("\n  ✓ Training complete.")
    print(f"  Model saved to: {MODEL_FILE}")
    print(f"\n  To use the model scores in the app, the sentiment_external.py")
    print(f"  will auto-load it via score_with_model() if the .pkl file exists.")
    print("=" * 58)
