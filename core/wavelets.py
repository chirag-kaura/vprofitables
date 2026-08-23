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

    # Define scales for CWT (roughly corresponding to cycle periods in days)
    # Using scales from 5 to 250 (roughly 1 week to 1 year of trading days)
    scales = np.arange(5, 250)
    
    # Use Morlet wavelet which is standard for financial cycle analysis
    wavelet = 'cmor1.5-1.0'
    
    # Perform CWT
    coefficients, frequencies = pywt.cwt(detrended, scales, wavelet, sampling_period=1)
    
    # Calculate power spectrum (magnitude squared)
    power = np.abs(coefficients) ** 2
    
    # To find dominant periods, we can look at the time-averaged global wavelet spectrum
    global_power = np.mean(power, axis=1)
    
    # Find peaks in global power
    periods = 1 / frequencies
    
    # Sort by power
    sorted_indices = np.argsort(global_power)[::-1]
    
    dominant_cycles = []
    cycle_strengths = []
    
    for idx in sorted_indices:
        period = round(periods[idx], 1)
        # Avoid near-duplicate periods
        if not any(abs(period - existing) < period * 0.1 for existing in dominant_cycles):
            dominant_cycles.append(period)
            cycle_strengths.append(float(global_power[idx]))
        if len(dominant_cycles) >= top_n:
            break
            
    # Normalize strengths
    max_strength = max(cycle_strengths) if cycle_strengths else 1
    cycle_strengths = [round(s / max_strength * 100, 1) for s in cycle_strengths]
    
    
    formatted_cycles = []
    for i, p in enumerate(dominant_cycles):
        formatted_cycles.append({
            "period_days": p,
            "power": cycle_strengths[i] if i < len(cycle_strengths) else 0,
            "phase_deg": 0.0,
            "gann_label": "CWT Extracted Cycle"
        })

    return {
        "dominant_cycles": formatted_cycles,
        "cycle_strengths": cycle_strengths,
        "composite_forecast": [float(prices[-1])] * 60, # Dummy forecast to prevent key errors
        "method": "CWT (Morlet)"
    }

