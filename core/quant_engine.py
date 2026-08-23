"""
quant_engine.py — Jim Simons / Medallion Fund style quantitative analysis
==========================================================================
What Simons actually did (documented from interviews + academic papers):

1. FOURIER / SPECTRAL ANALYSIS
   - Decompose price series into sine waves of different frequencies
   - Find which cycles actually repeat (periodogram peaks)
   - Simons: "Markets have hidden periodicities — we find them statistically"

2. AUTOCORRELATION & SERIAL CORRELATION
   - At which lag (days) does price most predict future price?
   - If lag-X autocorrelation is significant, that's a real cycle
   - Simons hired mathematicians (not economists) specifically for this

3. MARKET REGIME DETECTION (HMM-inspired)
   - Bull / Bear / Sideways / Volatile — detect current regime
   - Different signals work in different regimes
   - Simons: "The same signal that's profitable in one regime is toxic in another"

4. SIGNAL BACKTESTING
   - For each astro/Gann signal: does it actually predict price moves?
   - Compute hit rate, average move, Sharpe, max drawdown
   - Simons: "We only trade if the signal has statistical significance"

5. SUPPORT & RESISTANCE via FRACTAL DENSITY
   - Where do prices cluster / reverse most often?
   - Volume-weighted price levels = real S/R
   - Combine with Gann Sq9 levels for confluence

6. FORECASTING WITH MOMENTUM + MEAN REVERSION
   - Short-term: momentum (trending)
   - Medium-term: mean reversion to key levels
   - Combine with astro signals for directional bias

All calculations run on synthetic/historical price data when live data unavailable.
With yfinance installed, uses real NSE/BSE prices automatically.
"""

import math
import numpy as np
from datetime import date, timedelta
from typing import Dict, List, Tuple, Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from scipy.stats import chi2
except ImportError:
    chi2 = None


# ══════════════════════════════════════════════════════════════════════════
# 1. DATA LAYER — real data if yfinance available, else synthetic
# ══════════════════════════════════════════════════════════════════════════

def get_price_series(symbol: str, yf_symbol: str, years: int = 25,
                     as_of_date: Optional[str] = None) -> Optional[Dict]:
    """
    Fetch historical OHLCV.
    as_of_date: 'YYYY-MM-DD' — if set, only return data UP TO this date (backtest mode).
    Priority order:
      1. daily_prices SQLite table (already downloaded — instant, no API call)
      2. yfinance live fetch (fallback if DB empty)
      3. None (caller generates synthetic)
    """
    # ── 1. Read from local DB first ───────────────────────────────────────
    try:
        import sqlite3, os as _os
        # quant_engine.py is at core/quant_engine.py
        # DB is at <root>/market_data_v2.db = dirname(dirname(__file__))
        _here = _os.path.dirname(_os.path.abspath(__file__))
        db_path = _os.path.join(_os.path.dirname(_here), "market_data_v2.db")
        # Fallback: check CWD too (for non-standard setups)
        if not _os.path.exists(db_path):
            db_path = _os.path.join(_os.getcwd(), "market_data_v2.db")
        if _os.path.exists(db_path):
            conn = sqlite3.connect(db_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA cache_size=-16000")
            conn.execute("PRAGMA mmap_size=134217728")
            # Fetch all available history — Gann and Simons need the longest series possible
            end_date = as_of_date if as_of_date else date.today().isoformat()
            cutoff   = (date.fromisoformat(end_date) - timedelta(days=int(years * 365))).isoformat()
            rows = conn.execute("""
                SELECT trade_date, open, high, low, close, volume, change_pct
                FROM daily_prices
                WHERE symbol=? AND close IS NOT NULL
                  AND trade_date >= ? AND trade_date <= ?
                ORDER BY trade_date ASC
            """, (symbol, cutoff, end_date)).fetchall()
            conn.close()
            if len(rows) >= 60:   # need meaningful history
                dates   = [r[0] for r in rows]
                opens   = [float(r[1]) if r[1] else float(r[4]) for r in rows]
                highs   = [float(r[2]) if r[2] else float(r[4]) for r in rows]
                lows    = [float(r[3]) if r[3] else float(r[4]) for r in rows]
                closes  = [float(r[4]) for r in rows]
                volumes = [int(r[5]) if r[5] else 1_000_000 for r in rows]
                return {"dates": dates, "opens": opens, "closes": closes,
                        "highs": highs, "lows": lows, "volumes": volumes,
                        "source": "db", "n_rows": len(rows)}
    except Exception:
        pass

    # ── 2. yfinance fallback ──────────────────────────────────────────────
    try:
        import yfinance as yf, io as _io, sys as _sys
        end   = date.today()
        start = end - timedelta(days=int(years * 365))
        old_err = _sys.stderr; _sys.stderr = _io.StringIO()
        try:
            df = yf.Ticker(yf_symbol).history(
                start=start.isoformat(), end=end.isoformat(),
                auto_adjust=True, actions=False)
        finally:
            _sys.stderr = old_err
        if df is None or df.empty:
            return None
        # Flatten MultiIndex columns if present (yfinance ≥0.2)
        import pandas as _pd
        if isinstance(df.columns, _pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        # Flatten MultiIndex columns if present (yfinance >=0.2 quirk)
        try:
            import pandas as _pd
            if isinstance(df.columns, _pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
        except Exception:
            pass
        df = df.sort_index().dropna(subset=["Close"])
        closes  = df["Close"].tolist()
        volumes = [int(v) if v == v else 1_000_000 for v in df.get("Volume", [1_000_000]*len(df)).tolist()]
        highs   = df["High"].tolist()
        lows    = df["Low"].tolist()
        dates   = [str(d.date()) for d in df.index]
        return {"dates": dates, "closes": closes, "highs": highs,
                "lows": lows, "volumes": volumes, "source": "yfinance",
                "n_rows": len(closes)}
    except Exception:
        return None


def generate_synthetic_series(
    base_price: float, atl: float, ath: float,
    n_days: int = 756,  # 3 years
    trend_up: bool = True,
    seed: int = 42,
) -> Dict:
    """
    Generate realistic synthetic price series using:
    - Long-term trend component
    - Seasonal/cyclical components (Gann cycles baked in)
    - Random walk noise
    Used when live data is unavailable.
    """
    np.random.seed(seed)
    prices = [base_price]
    highs, lows, volumes = [base_price], [base_price], [1_000_000]

    # Hidden cycles (what Simons would find via Fourier)
    annual_cycle   = 2 * math.pi / 252    # ~1yr
    half_yr        = 2 * math.pi / 126
    quarter        = 2 * math.pi / 63
    mars_cycle     = 2 * math.pi / 180    # ~Mars ~687d ÷ 4
    jupiter_cycle  = 2 * math.pi / 756    # partial Jupiter

    trend = (ath / base_price) ** (1 / n_days) if trend_up else (atl / base_price) ** (1 / n_days)
    trend = max(0.9995, min(1.0005, trend))

    for i in range(1, n_days):
        t = i
        # Cyclical components
        cycle = (
            0.008 * math.sin(annual_cycle * t + 0.5) +
            0.005 * math.sin(half_yr * t + 1.2) +
            0.003 * math.sin(quarter * t + 0.8) +
            0.002 * math.sin(mars_cycle * t) +
            0.001 * math.sin(jupiter_cycle * t)
        )
        # Random daily move
        daily_vol = 0.012 if base_price > 10000 else 0.018
        noise = np.random.normal(0, daily_vol)
        # Trend + cycle + noise
        ret = (trend - 1) + cycle + noise
        new_price = prices[-1] * (1 + ret)
        new_price = max(atl * 0.8, min(ath * 1.2, new_price))
        prices.append(round(new_price, 2))
        daily_range = abs(noise) * prices[-1] * 0.5 + prices[-1] * 0.003
        highs.append(round(new_price + daily_range, 2))
        lows.append(round(max(atl * 0.5, new_price - daily_range), 2))
        volumes.append(int(np.random.lognormal(14, 0.5)))

    today = date.today()
    dates = [(today - timedelta(days=n_days - i)).isoformat() for i in range(n_days)]
    return {"dates": dates, "closes": prices, "highs": highs,
            "lows": lows, "volumes": volumes, "source": "synthetic"}


# ══════════════════════════════════════════════════════════════════════════
# 2. FOURIER CYCLE ANALYSIS (the Simons approach)
# ══════════════════════════════════════════════════════════════════════════

def fourier_cycle_analysis(closes: List[float], top_n: int = 5) -> Dict:
    """
    Decompose price series into dominant cycles using FFT.
    This is the core of what Simons did — find hidden periodicities.

    Returns:
    - dominant_cycles: periods (in days) of strongest cycles
    - cycle_strengths: relative power of each cycle
    - next_cycle_dates: projected dates for next peaks/troughs
    - composite_forecast: 60-day forward projection
    """
    n = len(closes)
    if n < 60:
        return {"error": "Need at least 60 data points"}

    # Detrend: remove linear trend to find cycles
    prices = np.array(closes, dtype=float)
    x = np.arange(n)
    slope, intercept = np.polyfit(x, prices, 1)
    trend_line = slope * x + intercept
    detrended = prices - trend_line

    # FFT
    fft_result = np.fft.rfft(detrended)
    freqs = np.fft.rfftfreq(n, d=1)  # d=1 day
    power = np.abs(fft_result) ** 2

    # Find dominant periods (skip DC component at freq=0)
    valid = (freqs > 0) & (freqs < 0.5)
    valid_power = power.copy()
    valid_power[~valid] = 0

    # Top cycles by power
    top_indices = np.argsort(valid_power)[-top_n:][::-1]
    dominant = []
    for idx in top_indices:
        if freqs[idx] > 0:
            period = round(1 / freqs[idx], 1)
            strength_pct = round(valid_power[idx] / valid_power[valid].sum() * 100, 2)
            phase = np.angle(fft_result[idx])
            # Days to next peak from today (end of series)
            days_to_peak = round(((math.pi / 2 - phase) % (2 * math.pi)) / (2 * math.pi / period), 0)
            days_to_trough = round(((3 * math.pi / 2 - phase) % (2 * math.pi)) / (2 * math.pi / period), 0)
            dominant.append({
                "period_days": period,
                "strength_pct": strength_pct,
                "phase_deg": round(math.degrees(phase) % 360, 1),
                "days_to_next_peak":   int(days_to_peak)   if days_to_peak <= period else int(days_to_peak % period),
                "days_to_next_trough": int(days_to_trough) if days_to_trough <= period else int(days_to_trough % period),
                "gann_label": _label_gann_cycle(period),
                "planetary_ruler": _planet_for_period(period),
            })

    # Composite 60-day forecast using top-5 cycles
    forecast_days = 60
    forecast = []
    top5 = top_indices[:5]
    for fd in range(forecast_days):
        composite = trend_line[-1] + slope * fd
        for idx in top5:
            if freqs[idx] > 0:
                amp = np.abs(fft_result[idx]) / (n / 2)
                phi = np.angle(fft_result[idx])
                composite += amp * np.cos(2 * math.pi * freqs[idx] * (n + fd) + phi)
        forecast.append(round(float(composite), 2))

    # Truncated reconstruction using only top_n components actually reported
    truncated_fft = np.zeros_like(fft_result)
    for idx in top_indices:
        if freqs[idx] > 0:
            truncated_fft[idx] = fft_result[idx]
    reconstructed_top_n = np.real(np.fft.irfft(truncated_fft, n=n)) + trend_line
    ss_res_top_n = np.sum((prices - reconstructed_top_n) ** 2)
    ss_tot = np.sum((prices - prices.mean()) ** 2)
    r_squared = round(1 - ss_res_top_n / max(ss_tot, 1e-9), 4)

    # Old full reconstruction R²
    reconstructed_full = np.real(np.fft.irfft(fft_result, n=n)) + trend_line
    ss_res_full = np.sum((prices - reconstructed_full) ** 2)
    full_spectrum_r_squared = round(1 - ss_res_full / max(ss_tot, 1e-9), 4)

    today = date.today()
    forecast_dates = [(today + timedelta(days=i)).isoformat() for i in range(forecast_days)]

    # Coverage ratio: 120 days covered out of 715 days range (25 to 740)
    gann_bin_coverage = round(120.0 / 715.0, 4)

    return {
        "dominant_cycles": dominant,
        "forecast_60d": list(zip(forecast_dates, forecast)),
        "r_squared": r_squared,
        "full_spectrum_r_squared": full_spectrum_r_squared,
        "trend_direction": "UP" if slope > 0 else "DOWN",
        "trend_per_day": round(float(slope), 4),
        "method": "FFT (Fast Fourier Transform) — Simons/Medallion approach",
        "gann_bin_coverage_ratio": gann_bin_coverage,
    }


def _label_gann_cycle(period: float) -> str:
    GANN_CYCLES = [
        (28, 30,    "Monthly (30d)"),
        (43, 47,    "7-week (45d)"),
        (58, 62,    "Bimonthly (60d)"),
        (88, 92,    "Quarter (90d)"),
        (118, 122,  "1/3 year (120d)"),
        (142, 146,  "5-month (144d Gann)"),
        (176, 184,  "Half-year (180d)"),
        (235, 245,  "9-month (240d)"),
        (350, 370,  "Annual (360d)"),
        (410, 430,  "Mars (420d)"),
        (530, 550,  "18-month (540d)"),
        (710, 730,  "2-year (720d)"),
    ]
    for lo, hi, label in GANN_CYCLES:
        if lo <= period <= hi:
            return label
    return f"Custom ({period:.0f}d)"


def _planet_for_period(period: float) -> str:
    if period < 32:    return "Moon (27.3d)"
    if period < 95:    return "Sun (quarterly)"
    if period < 100:   return "Mercury (88d)"
    if period < 240:   return "Venus (225d)"
    if period < 400:   return "Sun (annual)"
    if period < 720:   return "Mars (687d)"
    if period < 1500:  return "Jupiter (partial)"
    return "Saturn (long)"


# ══════════════════════════════════════════════════════════════════════════
# 3. AUTOCORRELATION — which lags predict returns?
# ══════════════════════════════════════════════════════════════════════════

def autocorrelation_analysis(closes: List[float], max_lag: int = 120) -> Dict:
    """
    Compute autocorrelation of returns at each lag.
    Significant lags = real predictive cycles.
    Simons: "We look for serial correlation in returns, not prices"
    """
    prices = np.array(closes, dtype=float)
    returns = np.diff(np.log(prices))  # log returns
    n = len(returns)

    mean_r = returns.mean()
    var_r  = returns.var()
    if var_r < 1e-12:
        return {"error": "Insufficient price variation"}

    # ── FFT-based Autocorrelation O(n log n) ──
    x = returns - mean_r
    padded = np.pad(x, (0, n), 'constant')
    fft_val = np.fft.fft(padded)
    power = np.abs(fft_val) ** 2
    acf_fft = np.fft.ifft(power).real

    lags_tested = list(range(1, min(max_lag + 1, n // 2)))
    M = len(lags_tested)
    raw_results = []

    # Verification loop check to assert FFT matches manual loop
    for lag in lags_tested:
        cov = acf_fft[lag] / (n - lag)
        acf = cov / var_r
        z_stat = acf * math.sqrt(n)
        # Two-tailed normal p-value
        p_val = 1.0 - math.erf(abs(z_stat) / math.sqrt(2.0))
        raw_results.append({
            "lag": lag,
            "acf": acf,
            "p_value": p_val
        })

    # Assert close match for first 5 lags to verify O(n log n) correctness
    for lag in lags_tested[:5]:
        shifted = returns[lag:]
        original = returns[:len(shifted)]
        cov_man = np.mean((original - mean_r) * (shifted - mean_r))
        acf_man = cov_man / var_r
        cov_fft = acf_fft[lag] / (n - lag)
        acf_fft_val = cov_fft / var_r
        assert abs(acf_man - acf_fft_val) < 1e-9, f"FFT ACF drift at lag {lag}: {acf_man} vs {acf_fft_val}"

    # ── Benjamini-Hochberg FDR correction ──
    sorted_by_p = sorted(raw_results, key=lambda x: x["p_value"])
    Q = 0.05
    max_k = -1
    for k in range(M):
        if sorted_by_p[k]["p_value"] <= (k + 1) / M * Q:
            max_k = k

    significant_lags_bh = set()
    if max_k != -1:
        for k in range(max_k + 1):
            significant_lags_bh.add(sorted_by_p[k]["lag"])

    significant_lags = []
    raw_significant_lags = []
    sig_threshold = 1.96 / math.sqrt(n)
    autocorrs = []

    for item in raw_results:
        lag = item["lag"]
        acf = item["acf"]
        p_val = item["p_value"]
        autocorrs.append({"lag": lag, "acf": round(float(acf), 5)})

        gann_label = _label_gann_cycle(lag)
        planet_ruler = _planet_for_period(lag)
        lag_data = {
            "lag": lag,
            "acf": round(float(acf), 5),
            "p_value": round(float(p_val), 6),
            "direction": "MEAN_REVERT" if acf < 0 else "MOMENTUM",
            "strength": "STRONG" if abs(acf) > 2 * sig_threshold else "MODERATE",
            "gann_label": gann_label,
            "planet": planet_ruler,
        }

        if lag in significant_lags_bh:
            significant_lags.append(lag_data)
        if abs(acf) > sig_threshold:
            raw_significant_lags.append(lag_data)

    top_lags = sorted(significant_lags, key=lambda x: abs(x["acf"]), reverse=True)[:10]

    # Ljung-Box Q statistic (joint significance test of first 20 lags)
    q_stat = n * (n + 2) * sum(a["acf"] ** 2 / (n - a["lag"]) for a in autocorrs[:20])

    # Convert Ljung-Box Q statistic to chi-square p-value
    df = min(20, len(autocorrs))
    ljung_box_p_value = 1.0
    try:
        if chi2 is not None:
            ljung_box_p_value = float(chi2.sf(q_stat, df))
        else:
            raise ImportError("scipy not available")
    except Exception:
        # Wilson-Hilferty transformation fallback
        try:
            z = (((q_stat / df) ** (1/3)) - (1.0 - 2.0 / (9.0 * df))) / math.sqrt(2.0 / (9.0 * df))
            ljung_box_p_value = 1.0 - 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
        except Exception:
            ljung_box_p_value = 1.0 if q_stat < df else 0.0

    serial_correlation_confirmed = ljung_box_p_value < 0.05
    interpretation = (
        "Strong serial correlation detected — market has predictable cycles"
        if serial_correlation_confirmed else
        "Near-random walk — few detectable cycles"
    )

    return {
        "significant_lags": significant_lags[:20],
        "raw_significant_lags": raw_significant_lags[:20],
        "top_10_lags": top_lags,
        "autocorrelations": autocorrs[:max_lag],
        "sig_threshold": round(sig_threshold, 5),
        "ljung_box_q": round(q_stat, 2),
        "ljung_box_p_value": round(ljung_box_p_value, 5),
        "serial_correlation_confirmed": serial_correlation_confirmed,
        "interpretation": interpretation,
        "n_significant": len(significant_lags),
    }


# ══════════════════════════════════════════════════════════════════════════
# 4. MARKET REGIME DETECTION
# ══════════════════════════════════════════════════════════════════════════

def detect_market_regime(closes: List[float], lookback: int = 20) -> Dict:
    """
    Detect current market regime using multiple indicators + Gaussian HMM.
    Simons: different signals work in different regimes.

    Regimes:
    - STRONG_BULL:   trending up, low volatility
    - WEAK_BULL:     drifting up, moderate volatility
    - SIDEWAYS:      range-bound
    - WEAK_BEAR:     drifting down
    - STRONG_BEAR:   trending down, high volatility
    - HIGH_VOL:      volatile/indeterminate
    """
    if len(closes) < 50:
        return {"regime": "INSUFFICIENT_DATA"}

    prices = np.array(closes, dtype=float)
    n = len(prices)

    # Key calculations
    sma20  = prices[-20:].mean()
    sma50  = prices[-50:].mean() if n >= 50 else sma20
    sma200 = prices[-200:].mean() if n >= 200 else sma50
    current = prices[-1]

    # Returns
    ret_1d  = (current - prices[-2]) / prices[-2]
    ret_5d  = (current - prices[-6]) / prices[-6] if n >= 6 else ret_1d
    ret_20d = (current - prices[-21]) / prices[-21] if n >= 21 else ret_5d
    ret_60d = (current - prices[-61]) / prices[-61] if n >= 61 else ret_20d

    # Volatility (annualised)
    log_rets = np.diff(np.log(prices[-21:]))
    daily_vol = log_rets.std()
    annual_vol = daily_vol * math.sqrt(252) * 100

    # ATR proxy
    recent_highs = np.array([max(prices[max(0,i-5):i+1]) for i in range(n-5, n)])
    recent_lows  = np.array([min(prices[max(0,i-5):i+1]) for i in range(n-5, n)])
    atr_pct = float((recent_highs - recent_lows).mean() / current * 100)

    # ADX proxy (trend strength via slope consistency)
    slopes = np.diff(prices[-21:])
    positive_days = (slopes > 0).sum()
    trend_consistency = abs(positive_days - 10) / 10  # 0=no trend, 1=perfect trend
    adx_proxy = trend_consistency * 50

    # Regime logic
    above_200 = current > sma200
    above_50  = current > sma50
    above_20  = current > sma20

    if annual_vol > 40:
        regime = "HIGH_VOLATILITY"
        color  = "orange"
        bias   = "NEUTRAL"
    elif above_200 and above_50 and above_20 and ret_20d > 0.03:
        regime = "STRONG_BULL"
        color  = "green"
        bias   = "BUY_DIPS"
    elif above_200 and above_50 and ret_20d > 0:
        regime = "WEAK_BULL"
        color  = "lightgreen"
        bias   = "HOLD_LONG"
    elif not above_200 and not above_50 and ret_20d < -0.03:
        regime = "STRONG_BEAR"
        color  = "red"
        bias   = "SELL_RALLIES"
    elif not above_200 and ret_20d < 0:
        regime = "WEAK_BEAR"
        color  = "salmon"
        bias   = "REDUCE_LONGS"
    else:
        regime = "SIDEWAYS"
        color  = "yellow"
        bias   = "RANGE_TRADE"

    # What signals work in this regime (Simons insight)
    signal_filter = {
        "STRONG_BULL":   "Momentum signals dominate. Mean-reversion unreliable. Buy breakouts.",
        "WEAK_BULL":     "Mixed signals. Planetary BULLISH aspects valid. Avoid shorts.",
        "SIDEWAYS":      "Mean-reversion signals dominate. Sq9 S/R levels highly reliable.",
        "WEAK_BEAR":     "Mixed signals. Only BEARISH planetary aspects valid. Avoid longs.",
        "STRONG_BEAR":   "Momentum (downside) dominates. Mean-reversion traps. Sell rallies.",
        "HIGH_VOLATILITY":"Reduce signal confidence. Wait for regime clarity. Wider stops.",
    }

    # Simons-style regime probability estimate
    confidence = min(0.95, 0.5 + trend_consistency * 0.4 + min(0.1, abs(ret_20d) * 2))

    res = {
        "regime": regime,
        "color": color,
        "bias": bias,
        "confidence": round(confidence * 100, 1),
        "signal_advice": signal_filter[regime],
        "metrics": {
            "current": round(float(current), 2),
            "sma20":   round(float(sma20), 2),
            "sma50":   round(float(sma50), 2),
            "sma200":  round(float(sma200), 2),
            "ret_1d":  round(ret_1d * 100, 2),
            "ret_5d":  round(ret_5d * 100, 2),
            "ret_20d": round(ret_20d * 100, 2),
            "ret_60d": round(ret_60d * 100, 2),
            "annual_vol_pct": round(annual_vol, 1),
            "atr_pct": round(atr_pct, 2),
            "adx_proxy": round(adx_proxy, 1),
            "trend_consistency_pct": round(trend_consistency * 100, 1),
        }
    }

    # ── HMM Regime Detection ──
    try:
        all_returns = np.diff(np.log(prices))
        if len(all_returns) >= 100:
            # Train HMM on last 500 trading days (~2 years of data) for speed & relevancy
            hmm_returns = all_returns[-500:]
            hmm = GaussianHMM(n_states=3, max_iter=20)
            hmm.fit(hmm_returns)
            decoded_states = hmm.predict_states(all_returns)
            current_state = int(decoded_states[-1])
            hmm_states = ["HMM_BEAR", "HMM_SIDEWAYS", "HMM_BULL"]
            res["hmm"] = {
                "regime": hmm_states[current_state],
                "transition_matrix": hmm.A.tolist(),
                "means": (hmm.means * 100).tolist(),
                "vars": (hmm.vars * 10000).tolist(),
                "recent_states": decoded_states[-60:].tolist()
            }
    except Exception as e:
        res["hmm_error"] = str(e)

    return res


# ══════════════════════════════════════════════════════════════════════════
# 5. SUPPORT & RESISTANCE via FRACTAL DENSITY + VOLUME
# ══════════════════════════════════════════════════════════════════════════

def find_support_resistance(
    closes: List[float],
    highs: List[float],
    lows: List[float],
    volumes: List[float],
    n_levels: int = 8,
    current_price: Optional[float] = None,
) -> Dict:
    closes_arr  = np.array(closes, dtype=float)
    highs_arr   = np.array(highs, dtype=float)
    lows_arr    = np.array(lows, dtype=float)
    vols_arr    = np.array(volumes, dtype=float) + 1  # avoid zero

    current = current_price or closes_arr[-1]
    n = len(closes_arr)

    pivot_highs, pivot_lows = [], []
    for i in range(5, n - 5):
        if highs_arr[i] == highs_arr[i-5:i+6].max():
            pivot_highs.append(highs_arr[i])
        if lows_arr[i] == lows_arr[i-5:i+6].min():
            pivot_lows.append(lows_arr[i])

    cluster_prices = []
    window = 20
    for i in range(0, n - window, window // 2):
        chunk_c = closes_arr[i:i+window]
        chunk_v = vols_arr[i:i+window]
        vwap = (chunk_c * chunk_v).sum() / chunk_v.sum()
        cluster_prices.append(float(vwap))

    all_levels = pivot_highs + pivot_lows + cluster_prices
    if not all_levels:
        all_levels = [current * r for r in [0.85, 0.90, 0.95, 1.05, 1.10, 1.15]]

    all_levels = sorted(all_levels)
    clustered = []
    tol = current * 0.005

    i = 0
    while i < len(all_levels):
        group = [all_levels[i]]
        j = i + 1
        while j < len(all_levels) and all_levels[j] - all_levels[i] <= tol:
            group.append(all_levels[j])
            j += 1
        centroid = sum(group) / len(group)
        touches  = len(group)
        clustered.append({"price": round(centroid, 2), "touches": touches})
        i = j

    def score(lvl):
        dist_pct = abs(lvl["price"] - current) / current
        if dist_pct > 0.25:
            return 0
        proximity_score = 1 / (dist_pct + 0.01)
        return proximity_score * lvl["touches"]

    clustered.sort(key=score, reverse=True)
    top_levels = clustered[:n_levels * 2]

    supports   = sorted([l for l in top_levels if l["price"] < current * 0.998], key=lambda x: -x["price"])
    resistances = sorted([l for l in top_levels if l["price"] > current * 1.002], key=lambda x: x["price"])

    def enrich(levels, is_support):
        result = []
        for l in levels[:n_levels // 2 + 1]:
            dist_pct = (current - l["price"]) / current * 100 if is_support else (l["price"] - current) / current * 100
            strength = "STRONG" if l["touches"] >= 3 else "MODERATE" if l["touches"] >= 2 else "WEAK"
            result.append({
                "price": l["price"],
                "distance_pct": round(abs(dist_pct), 2),
                "touches": l["touches"],
                "strength": strength,
                "type": "SUPPORT" if is_support else "RESISTANCE",
            })
        return result

    return {
        "current_price": round(float(current), 2),
        "supports":    enrich(supports, True),
        "resistances": enrich(resistances, False),
        "method": "Fractal density + Volume cluster analysis",
        "n_pivot_highs": len(pivot_highs),
        "n_pivot_lows":  len(pivot_lows),
        "n_clusters":    len(clustered),
    }


# ══════════════════════════════════════════════════════════════════════════
# 6. SIGNAL BACKTESTER — Simons' core validation step
# ══════════════════════════════════════════════════════════════════════════

def backtest_signal(
    closes: List[float],
    signal_dates_indices: List[int],
    forward_days: int = 10,
    signal_direction: str = "BULLISH",
) -> Dict:
    prices = np.array(closes, dtype=float)
    n = len(prices)
    outcomes = []

    for idx in signal_dates_indices:
        if idx + forward_days >= n:
            continue
        entry_price = prices[idx]
        exit_prices = prices[idx + 1: idx + forward_days + 1]
        returns = [(p - entry_price) / entry_price for p in exit_prices]
        final_ret  = returns[-1] if returns else 0
        max_gain   = max(returns) if returns else 0
        max_loss   = min(returns) if returns else 0
        if signal_direction == "BULLISH":
            hit = final_ret > 0.005
        else:
            hit = final_ret < -0.005
        outcomes.append({
            "signal_idx": idx,
            "final_ret_pct": round(final_ret * 100, 3),
            "max_gain_pct":  round(max_gain * 100, 3),
            "max_loss_pct":  round(max_loss * 100, 3),
            "hit": hit,
        })

    if not outcomes:
        return {"error": "No testable signal dates found"}

    n_signals = len(outcomes)
    n_hits    = sum(1 for o in outcomes if o["hit"])
    hit_rate  = n_hits / n_signals

    final_rets = [o["final_ret_pct"] for o in outcomes]
    avg_ret    = sum(final_rets) / n_signals
    std_ret    = (sum((r - avg_ret) ** 2 for r in final_rets) / max(n_signals - 1, 1)) ** 0.5
    sharpe     = (avg_ret / std_ret * math.sqrt(252 / forward_days)) if std_ret > 0 else 0

    win_rets  = [r for r in final_rets if r > 0]
    loss_rets = [r for r in final_rets if r < 0]
    avg_win   = sum(win_rets) / len(win_rets) if win_rets else 0
    avg_loss  = sum(loss_rets) / len(loss_rets) if loss_rets else 0
    expectancy = hit_rate * avg_win + (1 - hit_rate) * avg_loss

    t_stat = avg_ret / (std_ret / math.sqrt(n_signals)) if std_ret > 0 else 0
    p_value_approx = 2 * (1 - min(0.9999, 0.5 + 0.5 * math.erf(abs(t_stat) / math.sqrt(2))))

    valid = hit_rate > 0.55 and avg_ret > 0.3 and p_value_approx < 0.10
    confidence_label = (
        "TRADEABLE SIGNAL" if valid else
        "WEAK SIGNAL" if hit_rate > 0.50 else
        "INVALID — DO NOT TRADE"
    )

    return {
        "n_signals": n_signals,
        "n_hits": n_hits,
        "hit_rate_pct": round(hit_rate * 100, 1),
        "avg_return_pct": round(avg_ret, 3),
        "std_return_pct": round(std_ret, 3),
        "sharpe_ratio": round(sharpe, 3),
        "expectancy_pct": round(expectancy, 3),
        "avg_win_pct":  round(avg_win, 3),
        "avg_loss_pct": round(avg_loss, 3),
        "t_statistic": round(t_stat, 3),
        "p_value": round(p_value_approx, 4),
        "is_statistically_valid": valid,
        "confidence": confidence_label,
        "forward_days": forward_days,
        "outcomes_sample": outcomes[:5],
        "simons_verdict": (
            f"KEEP: hit={hit_rate*100:.0f}%, sharpe={sharpe:.2f}, p={p_value_approx:.3f}"
            if valid else
            f"DISCARD: insufficient edge (hit={hit_rate*100:.0f}%, p={p_value_approx:.3f})"
        )
    }


# ══════════════════════════════════════════════════════════════════════════
# 7. RUN DYNAMIC CYCLE BACKTEST
# ══════════════════════════════════════════════════════════════════════════

def run_cycle_backtest(closes: List[float], period: float, phase: float, forward_days: int = 10) -> Dict:
    n = len(closes)
    omega = 2 * math.pi / period
    trough_indices = []
    for t in range(1, n - 1):
        val_prev = math.cos(omega * (t - 1) + phase)
        val_curr = math.cos(omega * t + phase)
        val_next = math.cos(omega * (t + 1) + phase)
        if val_curr < val_prev and val_curr < val_next:
            trough_indices.append(t)

    if not trough_indices:
        trough_indices = list(range(int(period), n - 10, int(period)))

    return backtest_signal(closes, trough_indices, forward_days=forward_days)


# ══════════════════════════════════════════════════════════════════════════
# 8. FULL QUANTITATIVE ANALYSIS — combines everything
# ══════════════════════════════════════════════════════════════════════════

def full_quant_analysis(
    symbol: str,
    yf_symbol: str,
    current_price: float,
    atl: float,
    ath: float,
    trend_up: bool = True,
    as_of_date: Optional[str] = None,
    signal_type: str = "fourier",
    forward_days: int = 10,
) -> Dict:
    data = get_price_series(symbol, yf_symbol, years=25, as_of_date=as_of_date)

    try:
        if data and len(data.get("lows", [])) > 10:
            db_min = min(data["lows"])
            db_max = max(data["highs"]) if data.get("highs") else ath
            if db_min > 0 and db_min >= atl * 0.20:
                atl = min(atl, db_min)
            if db_max > ath:
                ath = db_max
    except Exception:
        pass
    if data is None or len(data.get("closes", [])) < 60:
        seed = sum(ord(c) for c in symbol) % 1000
        data = generate_synthetic_series(current_price, atl, ath,
                                          n_days=756, trend_up=trend_up, seed=seed)
        data["closes"][-1] = current_price
    elif as_of_date:
        if data["closes"] and data["closes"][-1] > 0:
            current_price = data["closes"][-1]
    elif data["closes"][-1] != current_price and current_price > 0:
        data["closes"][-1] = current_price

    closes  = data["closes"]
    opens   = data.get("opens", data["closes"])
    highs   = data["highs"]
    lows    = data["lows"]
    volumes = data["volumes"]
    dates   = data["dates"]

    fourier = wavelet_cycle_analysis(closes)
    acf = autocorrelation_analysis(closes)
    regime = detect_market_regime(closes)
    sr = find_support_resistance(closes, highs, lows, volumes, current_price=current_price)

    # Dynamic GARCH Volatility Forecast
    try:
        rets = np.diff(np.log(closes))
        w, alpha, beta, forecasted_vol = estimate_garch11(rets)
        garch_data = {
            "omega": w,
            "alpha": alpha,
            "beta": beta,
            "forecasted_vol_ann": round(forecasted_vol, 2),
            "last_variance": round(w + alpha * (rets[-1]**2) + beta * (w / (1.0 - alpha - beta)), 8)
        }
    except Exception as e:
        garch_data = {"error": str(e), "forecasted_vol_ann": regime["metrics"]["annual_vol_pct"]}

    # Automatically compute Fourier backtests for Swing (10d), Short-Term (45d), and Long-Term (90d)
    bt_swing = run_simons_backtest(closes, dates, symbol, signal_type="fourier", forward_days=10)
    bt_short = run_simons_backtest(closes, dates, symbol, signal_type="fourier", forward_days=45)
    bt_long  = run_simons_backtest(closes, dates, symbol, signal_type="fourier", forward_days=90)

    # Run cycle-specific backtests on top-3 dominant cycles
    dominant_cycles = fourier.get("dominant_cycles", [])
    cycle_backtests = []
    for cyc in dominant_cycles[:3]:
        period = cyc["period_days"]
        phase = math.radians(cyc["phase_deg"])
        res = run_cycle_backtest(closes, period, phase, forward_days=forward_days)
        if "error" not in res:
            verdict_status = "TRADEABLE" if res.get("is_statistically_valid") else "does not"
            if verdict_status == "TRADEABLE":
                verdict = f"the {period:.0f}-day cycle backtests as TRADEABLE (hit={res.get('hit_rate_pct',0):.0f}%, p={res.get('p_value',1):.2f})"
            else:
                verdict = f"the {period:.0f}-day cycle does not (hit={res.get('hit_rate_pct',0):.0f}%, p={res.get('p_value',1):.2f})"
            cycle_backtests.append({
                "period_days": period,
                "gann_label": cyc["gann_label"],
                "backtest": res,
                "verdict": verdict
            })

    # Baseline 90-day backtest
    baseline_indices = list(range(90, len(closes) - 10, 90))
    bt_baseline = backtest_signal(closes, baseline_indices, forward_days=forward_days)
    if "error" not in bt_baseline:
        bt_baseline["label"] = "90-Day Fixed Baseline"

    chart_n = min(504, len(closes))
    chart_data = {
        "dates":   dates[-chart_n:],
        "opens":   [round(o, 2) for o in opens[-chart_n:]],
        "closes":  [round(c, 2) for c in closes[-chart_n:]],
        "highs":   [round(h, 2) for h in highs[-chart_n:]],
        "lows":    [round(l, 2) for l in lows[-chart_n:]],
        "volumes": volumes[-chart_n:],
        "sma20":   [round(float(np.array(closes[max(0,i-20):i+1]).mean()), 2)
                    for i in range(len(closes)-chart_n, len(closes))],
        "sma50":   [round(float(np.array(closes[max(0,i-50):i+1]).mean()), 2)
                    for i in range(len(closes)-chart_n, len(closes))],
        "sma200":  [round(float(np.array(closes[max(0,i-200):i+1]).mean()), 2)
                    for i in range(len(closes)-chart_n, len(closes))],
        "data_source": data["source"],
    }

    return {
        "symbol": symbol,
        "current_price": round(current_price, 2),
        "data_source": data["source"],
        "n_days": len(closes),
        "chart": chart_data,
        "fourier": fourier,
        "autocorrelation": acf,
        "regime": regime,
        "garch": garch_data,
        "support_resistance": sr,
        "backtest_swing": bt_swing,
        "backtest_short": bt_short,
        "backtest_long": bt_long,
        "cycle_backtests": cycle_backtests,
        "backtest_90d_cycle": bt_baseline,
    }


# ══════════════════════════════════════════════════════════════════════════
# v4.0 HELPER: get_fourier_dates()
# Returns dominant trough/peak as date objects for reversal_map.py
# ══════════════════════════════════════════════════════════════════════════

def get_fourier_dates(
    closes: List[float],
    analysis_date=None,
    horizon_days: int = 60,
) -> dict:
    from datetime import date as _date, timedelta as _td
    today = analysis_date or _date.today()

    empty = {
        "trough_date":     None,
        "peak_date":       None,
        "dominant_period": 0.0,
        "r_squared":       0.0,
        "days_to_trough":  999,
        "days_to_peak":    999,
    }

    if len(closes) < 60:
        return empty

    try:
        result = wavelet_cycle_analysis(closes)
        if not result or "dominant_cycles" not in result:
            return empty

        cycles = result.get("dominant_cycles", [])
        if not cycles:
            return empty

        dom = max(cycles, key=lambda c: c.get("strength_pct", 0))

        dt_trough = int(dom.get("days_to_next_trough", 999))
        dt_peak   = int(dom.get("days_to_next_peak",   999))
        period    = float(dom.get("period_days", 0))
        r2        = float(result.get("r_squared", 0))

        trough_date = None
        peak_date   = None

        if 0 <= dt_trough <= horizon_days:
            trough_date = today + _td(days=dt_trough)
            while trough_date.weekday() >= 5:
                trough_date += _td(days=1)

        if 0 <= dt_peak <= horizon_days:
            peak_date = today + _td(days=dt_peak)
            while peak_date.weekday() >= 5:
                peak_date += _td(days=1)

        return {
            "trough_date":     trough_date,
            "peak_date":       peak_date,
            "dominant_period": period,
            "r_squared":       r2,
            "days_to_trough":  dt_trough,
            "days_to_peak":    dt_peak,
        }

    except Exception:
        return empty


# ══════════════════════════════════════════════════════════════════════════
# NEW QUANT MATH SOLVERS (HMM, GARCH, DYNAMIC BACKTEST, KELLY)
# ══════════════════════════════════════════════════════════════════════════

class GaussianHMM:
    """
    3-State Hidden Markov Model with Gaussian emissions.
    Optimised using Baum-Welch (EM) algorithm.
    Decoded via Viterbi path.
    """
    def __init__(self, n_states: int = 3, max_iter: int = 15, tol: float = 1e-4):
        self.n_states = n_states
        self.max_iter = max_iter
        self.tol = tol
        self.means = np.zeros(self.n_states)
        self.vars = np.zeros(self.n_states)
        self.pi = np.zeros(self.n_states)
        self.A = np.zeros((self.n_states, self.n_states))

    def fit(self, returns: np.ndarray):
        N = len(returns)
        if N < 20:
            return

        # 1. Smarter initialization by sorting returns
        sorted_idx = np.argsort(returns)
        splits = np.array_split(sorted_idx, self.n_states)
        for s in range(self.n_states):
            subset = returns[splits[s]]
            self.means[s] = subset.mean()
            self.vars[s] = max(subset.var(), 1e-6)

        self.pi = np.ones(self.n_states) / self.n_states
        self.A = np.ones((self.n_states, self.n_states)) / self.n_states

        # 2. EM Loop
        for it in range(self.max_iter):
            # Compute Gaussian likelihoods
            B = np.zeros((N, self.n_states))
            for s in range(self.n_states):
                diff = returns - self.means[s]
                B[:, s] = np.exp(-0.5 * (diff**2) / self.vars[s]) / np.sqrt(2 * np.pi * self.vars[s])
            B = np.clip(B, 1e-12, 1e12)

            # Forward pass (scaled)
            alpha = np.zeros((N, self.n_states))
            c = np.zeros(N)
            alpha[0] = self.pi * B[0]
            c[0] = 1.0 / max(alpha[0].sum(), 1e-12)
            alpha[0] *= c[0]

            for t in range(1, N):
                alpha[t] = np.dot(alpha[t-1], self.A) * B[t]
                c[t] = 1.0 / max(alpha[t].sum(), 1e-12)
                alpha[t] *= c[t]

            # Backward pass (scaled)
            beta = np.zeros((N, self.n_states))
            beta[N-1] = np.ones(self.n_states) * c[N-1]
            for t in range(N-2, -1, -1):
                beta[t] = np.dot(self.A, beta[t+1] * B[t+1]) * c[t]

            # Posteriors
            gamma = alpha * beta
            row_sums = gamma.sum(axis=1, keepdims=True)
            gamma /= np.where(row_sums > 0, row_sums, 1.0)

            # Vectorized xi computation (avoiding slow python loop over N)
            num_xi = alpha[:-1, :, np.newaxis] * (beta[1:, np.newaxis, :] * B[1:, np.newaxis, :]) * self.A[np.newaxis, :, :]
            sums_xi = num_xi.sum(axis=(1, 2), keepdims=True)
            xi = num_xi / np.where(sums_xi > 0, sums_xi, 1e-12)

            # Updates
            new_pi = gamma[0]
            new_A = xi.sum(axis=0)
            col_sums = gamma[:-1].sum(axis=0, keepdims=True).T
            new_A /= np.where(col_sums > 0, col_sums, 1.0)
            new_A /= new_A.sum(axis=1, keepdims=True)

            new_means = np.zeros(self.n_states)
            new_vars = np.zeros(self.n_states)
            for s in range(self.n_states):
                gsum = gamma[:, s].sum()
                if gsum > 1e-5:
                    new_means[s] = (gamma[:, s] * returns).sum() / gsum
                    new_vars[s] = max((gamma[:, s] * (returns - new_means[s])**2).sum() / gsum, 1e-6)
                else:
                    new_means[s] = self.means[s]
                    new_vars[s] = self.vars[s]

            # Convergence check
            diff = np.abs(self.means - new_means).max() + np.abs(self.A - new_A).max()
            self.pi = new_pi
            self.A = new_A
            self.means = new_means
            self.vars = new_vars

            if diff < self.tol:
                break

        # 3. Sort states by return mean: 0=Bearish, 1=Sideways, 2=Bullish
        idx = np.argsort(self.means)
        self.means = self.means[idx]
        self.vars = self.vars[idx]
        self.pi = self.pi[idx]
        self.A = self.A[idx][:, idx]

    def predict_states(self, returns: np.ndarray) -> np.ndarray:
        N = len(returns)
        B = np.zeros((N, self.n_states))
        for s in range(self.n_states):
            diff = returns - self.means[s]
            B[:, s] = np.exp(-0.5 * (diff**2) / self.vars[s]) / np.sqrt(2 * np.pi * self.vars[s])
        B = np.clip(B, 1e-12, 1e12)

        log_A = np.log(np.where(self.A > 0, self.A, 1e-12))
        log_B = np.log(B)
        log_pi = np.log(np.where(self.pi > 0, self.pi, 1e-12))

        V = np.zeros((N, self.n_states))
        path = np.zeros((N, self.n_states), dtype=int)
        V[0] = log_pi + log_B[0]

        for t in range(1, N):
            for s in range(self.n_states):
                probs = V[t-1] + log_A[:, s]
                best = np.argmax(probs)
                V[t, s] = probs[best] + log_B[t, s]
                path[t, s] = best

        states = np.zeros(N, dtype=int)
        states[N-1] = np.argmax(V[N-1])
        for t in range(N-2, -1, -1):
            states[t] = path[t+1, states[t+1]]
        return states


def estimate_garch11(returns: np.ndarray) -> Tuple[float, float, float, float]:
    """
    Solve GARCH(1,1) maximum likelihood estimator using localized grid coordinate search.
    Returns: (omega, alpha, beta, forecasted_volatility_annualised_pct)
    """
    N = len(returns)
    r2 = returns ** 2
    sample_var = float(returns.var())
    if sample_var < 1e-12:
        return 1e-6, 0.05, 0.90, 1.0

    best_llh = -1e15
    best_params = (sample_var * 0.05, 0.05, 0.90)

    # Grid search parameters
    alphas = [0.01, 0.05, 0.10, 0.15, 0.20]
    betas = [0.70, 0.80, 0.85, 0.90, 0.95]

    for a in alphas:
        for b in betas:
            if a + b >= 0.999:
                continue
            w = sample_var * (1.0 - a - b)
            if w <= 0:
                continue

            sig2 = np.zeros(N)
            sig2[0] = sample_var
            for t in range(1, N):
                sig2[t] = w + a * r2[t-1] + b * sig2[t-1]

            llh = -0.5 * np.sum(np.log(sig2) + r2 / sig2)
            if llh > best_llh:
                best_llh = llh
                best_params = (w, a, b)

    w, a, b = best_params

    # Conditional variance filter to project tomorrow's variance
    sig2_final = sample_var
    for t in range(1, N):
        sig2_final = w + a * r2[t-1] + b * sig2_final

    forecast_var = w + a * r2[-1] + b * sig2_final
    forecast_vol_ann = math.sqrt(max(forecast_var, 1e-12) * 252) * 100

    return w, a, b, forecast_vol_ann


def get_fourier_signals(closes: List[float], dates: List[str]) -> List[int]:
    n = len(closes)
    if n < 60:
        return []
    prices = np.array(closes, dtype=float)
    x = np.arange(n)
    slope, intercept = np.polyfit(x, prices, 1)
    detrended = prices - (slope * x + intercept)

    fft_result = np.fft.rfft(detrended)
    freqs = np.fft.rfftfreq(n, d=1)
    power = np.abs(fft_result) ** 2
    valid = (freqs > 0) & (freqs < 0.5)
    valid_power = power.copy()
    valid_power[~valid] = 0
    top_indices = np.argsort(valid_power)[-5:]
    if len(top_indices) == 0:
        return []

    top_idx = top_indices[-1]
    if freqs[top_idx] <= 0:
        return []

    period = 1.0 / freqs[top_idx]
    phase = np.angle(fft_result[top_idx])
    omega = 2 * np.pi / period

    signals = []
    for t in range(1, n - 1):
        val_prev = math.cos(omega * (t - 1) + phase)
        val_curr = math.cos(omega * t + phase)
        val_next = math.cos(omega * (t + 1) + phase)
        if val_curr < val_prev and val_curr < val_next:
            signals.append(t)

    if not signals:
        signals = list(range(int(period), n - 10, int(period)))
    return signals


def get_gann_signals(closes: List[float], dates: List[str]) -> List[int]:
    min_p, max_p = min(closes), max(closes)
    levels = []
    start_s = math.floor(math.sqrt(min_p))
    end_s = math.ceil(math.sqrt(max_p))
    s = start_s
    while s <= end_s:
        levels.append(s ** 2)
        s += 0.25

    signals = []
    for t in range(1, len(closes)):
        prev = closes[t-1]
        curr = closes[t]
        for lvl in levels:
            if prev <= lvl < curr:
                signals.append(t)
                break
    return signals


def get_astro_signals(closes: List[float], dates: List[str], symbol: str) -> List[int]:
    from data.instruments import INSTRUMENTS
    ruling_planet = "Jupiter"
    for inst in INSTRUMENTS:
        if inst.symbol == symbol:
            ruling_planet = inst.ruling_planet
            break

    from core.aspects import detect_aspects
    from datetime import date as _date
    signals = []
    n = len(closes)
    # Check aspects in last 180 trading days to preserve speed
    start_idx = max(0, n - 180)
    for t in range(start_idx, n):
        try:
            dt = _date.fromisoformat(dates[t])
            aspects = detect_aspects(dt)
            ruling_aspects = [
                a for a in aspects
                if (a.planet_a == ruling_planet or a.planet_b == ruling_planet)
                and a.orb <= 3
            ]
            if any(a.is_major for a in ruling_aspects):
                signals.append(t)
        except Exception:
            pass
    return signals


def run_simons_backtest(
    closes: List[float],
    dates: List[str],
    symbol: str,
    signal_type: str = "fourier",
    forward_days: int = 10
) -> Dict:
    if signal_type == "fourier":
        sig_indices = get_fourier_signals(closes, dates)
    elif signal_type == "gann":
        sig_indices = get_gann_signals(closes, dates)
    elif signal_type == "astro":
        sig_indices = get_astro_signals(closes, dates, symbol)
    else:
        n = len(closes)
        sig_indices = list(range(90, n - 10, 90))

    if not sig_indices:
        return {"error": f"No {signal_type} signals found for backtest."}

    res = backtest_signal(closes, sig_indices, forward_days=forward_days)

    if "error" not in res:
        p = res["hit_rate_pct"] / 100.0
        avg_win = res["avg_win_pct"] / 100.0
        avg_loss = abs(res["avg_loss_pct"]) / 100.0
        b = avg_win / max(avg_loss, 1e-4)

        f = p - (1.0 - p) / b if b > 0 else 0.0
        full_k = max(0.0, min(1.0, f))
        half_k = 0.5 * full_k

        res["kelly"] = {
            "payoff_ratio": round(b, 2),
            "full_kelly_pct": round(full_k * 100, 1),
            "half_kelly_pct": round(half_k * 100, 1)
        }
        res["signal_type"] = signal_type
        res["n_signals"] = len(sig_indices)

    return res
# Added CWT functionality
from core.wavelets import wavelet_cycle_analysis
