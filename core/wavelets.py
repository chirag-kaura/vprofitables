"""
core/wavelets.py

Decompose price series into dominant cycles using Continuous Wavelet Transforms (CWT).
Solves the FFT end-point repainting problem for non-stationary financial data.
"""
import pywt
import numpy as np
from typing import List, Dict

def wavelet_cycle_analysis(closes: List[float], top_n: int = 5) -> Dict:
    """
    Decompose price series into dominant cycles using Continuous Wavelet Transforms (CWT).
    Solves the FFT end-point repainting problem for non-stationary financial data.
    """
    n = len(closes)
    if n < 60:
        return {"error": "Need at least 60 data points"}

    prices = np.array(closes, dtype=float)
    
    # Detrend to remove linear drift
    x = np.arange(n)
    poly = np.polyfit(x, prices, 1)
    trend = np.polyval(poly, x)
    detrended = prices - trend

    # Define scales for CWT bounded by Nyquist / sample length
    max_scale = max(6, min(250, n // 2))
    scales = np.arange(5, max_scale)
    
    # Use Morlet wavelet which is standard for financial cycle analysis
    wavelet = 'cmor1.5-1.0'
    
    # Perform CWT
    coefficients, frequencies = pywt.cwt(detrended, scales, wavelet, sampling_period=1)
    
    # Calculate power spectrum (magnitude squared)
    power = np.abs(coefficients) ** 2
    
    # Cone of Influence (COI) masking: e-folding time tau = sqrt(2) * scale
    valid_power = []
    for i, s in enumerate(scales):
        coi = int(np.ceil(np.sqrt(2.0) * s))
        if coi < n // 2:
            row_power = power[i, coi : n - coi]
            valid_power.append(float(np.mean(row_power)) if len(row_power) > 0 else float(np.mean(power[i])))
        else:
            valid_power.append(float(np.mean(power[i])))
    global_power = np.array(valid_power)
    
    # Find peaks in global power
    periods = 1.0 / frequencies
    
    # Sort by power
    sorted_indices = np.argsort(global_power)[::-1]
    
    dominant_cycles = []
    cycle_strengths = []
    cycle_phases = []
    
    for idx in sorted_indices:
        period = round(float(periods[idx]), 1)
        # Avoid near-duplicate periods within 10%
        if not any(abs(period - existing) < period * 0.1 for existing in dominant_cycles):
            dominant_cycles.append(period)
            cycle_strengths.append(float(global_power[idx]))
            # Calculate instantaneous phase at current bar (latest edge)
            phase_rad = float(np.angle(coefficients[idx, -1]))
            phase_deg = round(float(np.degrees(phase_rad)) % 360.0, 1)
            cycle_phases.append(phase_deg)
        if len(dominant_cycles) >= top_n:
            break
            
    # Normalize strengths 0-100%
    max_strength = max(cycle_strengths) if cycle_strengths else 1.0
    norm_strengths = [round(s / max_strength * 100, 1) for s in cycle_strengths]
    
    formatted_cycles = []
    for i, p in enumerate(dominant_cycles):
        formatted_cycles.append({
            "period_days": p,
            "power": norm_strengths[i] if i < len(norm_strengths) else 0.0,
            "phase_deg": cycle_phases[i] if i < len(cycle_phases) else 0.0,
            "gann_label": f"CWT Wavelet Cycle ({p:.0f}d)"
        })

    # Continuous cyclical forward projection (60 bars)
    last_p = float(prices[-1])
    forecast = []
    if dominant_cycles:
        p_dom = dominant_cycles[0]
        amp = float(np.std(detrended) * 0.5)
        top_idx = sorted_indices[0]
        phase_0 = float(np.angle(coefficients[top_idx, -1]))
        omega = 2.0 * np.pi / max(5.0, p_dom)
        trend_slope = float(poly[0])
        for step in range(1, 61):
            cyc_val = amp * np.sin(phase_0 + omega * step)
            proj = last_p + trend_slope * step + cyc_val
            forecast.append(round(float(proj), 2))
    else:
        forecast = [last_p] * 60

    return {
        "dominant_cycles": formatted_cycles,
        "cycle_strengths": norm_strengths,
        "composite_forecast": forecast,
        "method": "CWT (Morlet)"
    }
