"""
core/tools/ml_signal_tools.py
============================
Deep Learning & Machine Learning Predictive Signal Tool Adapter.
Integrates:
  1. PyTorch Multi-Layer Perceptron (MLP) Institutional Trend Continuation Engine.
  2. XGBoost / Gradient-Boosted Multi-Horizon Directional Reversal Classifier.
"""

import time
from typing import Optional, Dict, Any
from core.tools.contracts import ToolResult
from core.continuation_deep_engine import predict_continuation_probability
from core.deep_signal_engine import predict_reversal
from core.swarm.cache import ttl_cached, TTL_INTRADAY

@ttl_cached(ttl=TTL_INTRADAY, namespace="ml_continuation")
def ml_trend_continuation(symbol: str) -> ToolResult:
    """
    Evaluate PyTorch Deep MLP continuation probability, Morlet continuous wavelet transform (CWT) phase,
    ADX trend acceleration, institutional delivery volume absorption, and FII index future tailwind.
    """
    t0 = time.perf_counter()
    sym = symbol.upper().strip()

    try:
        res = predict_continuation_probability(sym)
        if not res.get("ok"):
            return ToolResult(
                domain="DEEP_ML",
                symbol=sym,
                headline_metric=f"Deep continuation inference unavailable for {sym}",
                tabular_summary=f"> {res.get('error', 'Insufficient historical price series.')}",
                execution_ms=int((time.perf_counter() - t0) * 1000),
                error=res.get("error")
            )

        prob = res.get("prob")
        prob_pct = res.get("prob_pct") or (prob * 100 if prob is not None else 50.0)
        verdict = res.get("verdict", "UNCERTAIN").replace("_", " ")
        feats = res.get("features", {})
        adx = feats.get("trend_adx", 0.0)
        cwt = feats.get("cwt_phase", 0.0)
        deliv = feats.get("delivery_pct", 0.0)
        fii = feats.get("fii_long_ratio", 50.0)
        vix = feats.get("india_vix", 15.0)

        headline = f"Continuation Probability: {prob_pct:.1f}% | Regime Verdict: {verdict} | ADX: {adx:.1f}"

        table_lines = [
            "| Deep Neural Network Feature | Calibrated Value | Institutional Model Context |",
            "| :--- | :--- | :--- |",
            f"| **Continuation Probability** | **{prob_pct:.1f}%** | PyTorch MLP calibrated softmax output |",
            f"| **Structural Verdict** | **{verdict}** | Multi-horizon classification regime |",
            f"| **ADX Trend Strength** | {adx:.1f} | Values >25 indicate strong directional momentum |",
            f"| **CWT Wavelet Phase** | {cwt:.2f} rad | Continuous Morlet wavelet frequency cycle |",
            f"| **Delivery Absorption** | {deliv:.1f}% | NSE delivery volume ratio |",
            f"| **FII Index Long Tail** | {fii:.1f}% | Institutional market-wide beta tailwind |",
            f"| **India VIX Macro Vol** | {vix:.2f} | Baseline risk regime |"
        ]

        raw = {
            "symbol": sym,
            "prob_pct": round(prob_pct, 2),
            "verdict": verdict,
            "adx": round(adx, 2),
            "cwt_phase": round(cwt, 2),
            "delivery_pct": round(deliv, 2),
            "fii_long_ratio": round(fii, 2),
            "india_vix": round(vix, 2)
        }

        return ToolResult(
            domain="DEEP_ML",
            symbol=sym,
            headline_metric=headline,
            tabular_summary="\n".join(table_lines),
            raw_data=raw,
            execution_ms=int((time.perf_counter() - t0) * 1000)
        )
    except Exception as e:
        return ToolResult(
            domain="DEEP_ML",
            symbol=sym,
            headline_metric=f"Error evaluating Deep Continuation for {sym}",
            tabular_summary=f"> Execution error: {e}",
            execution_ms=int((time.perf_counter() - t0) * 1000),
            error=str(e)
        )

@ttl_cached(ttl=TTL_INTRADAY, namespace="ml_reversal")
def ml_deep_reversal_score(symbol: str) -> ToolResult:
    """
    Evaluate XGBoost multi-horizon directional reversal model, predicting swing exhaustion,
    spring/upthrust inflection points, and directional probability.
    """
    t0 = time.perf_counter()
    sym = symbol.upper().strip()

    try:
        res = predict_reversal(symbol=sym)
        if res.get("error"):
            return ToolResult(
                domain="DEEP_ML",
                symbol=sym,
                headline_metric=f"Deep Reversal model notice for {sym}",
                tabular_summary=f"> {res.get('error')}",
                execution_ms=int((time.perf_counter() - t0) * 1000),
                error=res.get("error")
            )

        direction = res.get("direction", "NEUTRAL")
        conf = float(res.get("confidence") or 0.0) * 100
        score = float(res.get("score") or 0.0)
        feats = res.get("features", {})
        rsi_div = feats.get("rsi_divergence", 0.0)
        vol_div = feats.get("vol_price_divergence", 0.0)

        headline = f"Reversal Direction: {direction} | Model Confidence: {conf:.1f}% | Conviction Score: {score:+.2f}"

        table_lines = [
            "| Reversal Diagnostic | Reading | Algorithmic Definition |",
            "| :--- | :--- | :--- |",
            f"| **Predicted Direction** | **{direction}** | High-probability inflection target |",
            f"| **Model Confidence** | **{conf:.1f}%** | Cross-validated ensemble certainty |",
            f"| **Conviction Score** | {score:+.2f} | Scaled signal strength (-1.0 to +1.0) |",
            f"| **RSI Momentum Divergence** | {rsi_div:+.2f} | Price vs oscillator discrepancy |",
            f"| **Volume/Price Divergence** | {vol_div:+.2f} | Smart money stealth accumulation/distribution |"
        ]

        raw = {
            "symbol": sym,
            "direction": direction,
            "confidence_pct": round(conf, 2),
            "score": round(score, 2),
            "rsi_divergence": round(rsi_div, 2),
            "vol_price_divergence": round(vol_div, 2)
        }

        return ToolResult(
            domain="DEEP_ML",
            symbol=sym,
            headline_metric=headline,
            tabular_summary="\n".join(table_lines),
            raw_data=raw,
            execution_ms=int((time.perf_counter() - t0) * 1000)
        )
    except Exception as e:
        return ToolResult(
            domain="DEEP_ML",
            symbol=sym,
            headline_metric=f"Error evaluating Deep Reversal for {sym}",
            tabular_summary=f"> Execution error: {e}",
            execution_ms=int((time.perf_counter() - t0) * 1000),
            error=str(e)
        )
