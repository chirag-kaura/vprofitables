"""
intraday_engine.py — GANN-ASTRO v4.0 Intraday Reversal Engine
==============================================================
The Astro-Quant Intraday Trichotomy Strategy:
1. PRICE: Gann Opening Price Grid (Angles projected from 09:15 Opening Print).
2. TIME: Planetary Hora (Planetary Hours) + Sidereal Meridian shifts (4m/day).
3. MOMENTUM: Volume Weighted Average Price (VWAP) overextension bands.
"""

import math
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple, Optional
from data.instruments import ALL_INSTRUMENTS

# ── Sunrise/Sunset calculation for Mumbai Coordinates (NSE) ────────────────
def get_sunrise_sunset_mumbai(target_date: date) -> Tuple[float, float]:
    latitude = 19.076
    longitude = 72.8777
    day_of_year = target_date.timetuple().tm_yday
    lat_rad = math.radians(latitude)
    declination = math.radians(23.45 * math.sin(math.radians(360 / 365 * (day_of_year - 80))))
    cos_hour_angle = (math.sin(math.radians(-0.83)) - math.sin(lat_rad) * math.sin(declination)) / (math.cos(lat_rad) * math.cos(declination))
    cos_hour_angle = max(-1.0, min(1.0, cos_hour_angle))
    hour_angle_deg = math.degrees(math.acos(cos_hour_angle))
    local_solar_noon = 12.0 + (82.5 - longitude) / 15.0
    sunrise_hour = local_solar_noon - (hour_angle_deg / 15.0)
    sunset_hour = local_solar_noon + (hour_angle_deg / 15.0)
    return sunrise_hour, sunset_hour

# ── Planetary Hours (Hora) ────────────────────────────────────────────────
def get_planetary_hours_mumbai(target_date: date) -> List[Dict]:
    sunrise, sunset = get_sunrise_sunset_mumbai(target_date)
    day_length = sunset - sunrise
    hour_length = day_length / 12.0
    
    # Starting planet for the day of the week
    weekday = target_date.weekday()
    day_rulers = {
        0: "Moon",      # Monday
        1: "Mars",      # Tuesday
        2: "Mercury",   # Wednesday
        3: "Jupiter",   # Thursday
        4: "Venus",     # Friday
        5: "Saturn",    # Saturday
        6: "Sun"        # Sunday
    }
    start_planet = day_rulers[weekday]
    
    # Chaldean order
    chaldean = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
    start_idx = chaldean.index(start_planet)
    
    hours = []
    for i in range(12):
        start_time_float = sunrise + i * hour_length
        end_time_float = start_time_float + hour_length
        planet = chaldean[(start_idx + i) % 7]
        
        def float_to_time(h_float):
            h = int(h_float)
            m = int((h_float - h) * 60)
            return f"{h:02d}:{m:02d}"
            
        hours.append({
            "hour_num": i + 1,
            "start": float_to_time(start_time_float),
            "end": float_to_time(end_time_float),
            "start_float": start_time_float,
            "end_float": end_time_float,
            "ruler": planet
        })
    return hours

# ── Gann Opening Price Grid ──────────────────────────────────────────────
def calculate_opening_reversal_grid(opening_price: float) -> Dict[str, float]:
    """
    Calculate support and resistance angles projected from the opening print using Square of 9.
    Formula: Price = (sqrt(Open) + degrees/180)^2
    """
    if opening_price <= 0:
        return {}
    sqrt_op = math.sqrt(opening_price)
    
    angles = {
        "15°": 15, "30°": 30, "45°": 45, "60°": 60, "90°": 90, "120°": 120, "180°": 180
    }
    
    grid = {}
    for label, deg in angles.items():
        grid[f"support_{label}"] = round((sqrt_op - deg / 180.0) ** 2, 2)
        grid[f"resistance_{label}"] = round((sqrt_op + deg / 180.0) ** 2, 2)
    grid["center"] = round(opening_price, 2)
    return grid

# ── VWAP calculation ──────────────────────────────────────────────────────
def compute_vwap(df) -> Tuple[float, float]:
    """
    Compute current VWAP and standard deviation of typical prices from VWAP.
    """
    if df.empty:
        return 0.0, 0.0
    typical_prices = (df["High"] + df["Low"] + df["Close"]) / 3.0
    cum_pv = (typical_prices * df["Volume"]).cumsum()
    cum_v = df["Volume"].cumsum()
    vwap_series = cum_pv / cum_v.replace(0, 1)
    
    current_vwap = vwap_series.iloc[-1]
    
    # Calculate standard deviation from VWAP
    diffs = typical_prices - vwap_series
    variance = (diffs ** 2).mean()
    std_dev = math.sqrt(variance)
    
    return float(current_vwap), float(max(0.01, std_dev))

# ── Master Intraday Analyzer ──────────────────────────────────────────────
def analyze_intraday(symbol: str, target_date: date, df_15m) -> Dict:
    """
    Analyses real-time 15-minute price data alongside astrological timings to trigger signals.
    """
    inst = ALL_INSTRUMENTS.get(symbol)
    if not inst or df_15m.empty:
        return {"ok": False, "reason": "No instrument or price data"}
        
    # 1. Price analysis
    open_price = float(df_15m.iloc[0]["Open"])
    current_price = float(df_15m.iloc[-1]["Close"])
    current_high = float(df_15m.iloc[-1]["High"])
    current_low = float(df_15m.iloc[-1]["Low"])
    
    # Gann Opening Price grid
    grid = calculate_opening_reversal_grid(open_price)
    
    # VWAP & Bands
    vwap, std_dev = compute_vwap(df_15m)
    upper_band_1 = vwap + 1.2 * std_dev
    lower_band_1 = vwap - 1.2 * std_dev
    upper_band_2 = vwap + 2.0 * std_dev
    lower_band_2 = vwap - 2.0 * std_dev
    
    # 2. Time analysis
    current_time_str = datetime.now().strftime("%H:%M")
    current_time_float = datetime.now().hour + datetime.now().minute / 60.0
    
    # Hora Hour
    hours = get_planetary_hours_mumbai(target_date)
    current_hora = None
    for h in hours:
        if h["start_float"] <= current_time_float <= h["end_float"]:
            current_hora = h
            break
            
    is_ruler_active = False
    if current_hora:
        is_ruler_active = (current_hora["ruler"] in [inst.ruling_planet, inst.secondary_planet])
        
    # Sidereal reversal times
    from core.gann_math import get_intraday_reversal_times
    reversal_times = get_intraday_reversal_times(symbol, target_date)
    
    # Check proximity to reversal times (within 15 minutes)
    near_reversal_time = False
    for rt in reversal_times:
        rh, rm = map(int, rt.split(":"))
        rt_float = rh + rm / 60.0
        if abs(current_time_float - rt_float) <= 0.25:  # 15 minutes window
            near_reversal_time = True
            break
            
    # 3. Confluence Triggers
    direction = "NEUTRAL"
    signal_level = 0.0
    trigger_reason = []
    
    # Nearest levels (for pending planned setups)
    support_levels = [lvl for key, lvl in grid.items() if "support" in key and lvl < current_price]
    nearest_support = max(support_levels) if support_levels else open_price * 0.99
    
    resistance_levels = [lvl for key, lvl in grid.items() if "resistance" in key and lvl > current_price]
    nearest_resistance = min(resistance_levels) if resistance_levels else open_price * 1.01
    
    active_trigger = False
    # Check Support Reversals (Buy)
    for key, lvl in grid.items():
        if "support" in key:
            # Price comes within 0.15% of Gann support level or crosses it
            if abs(current_low - lvl) / lvl <= 0.0015 or (current_low <= lvl <= current_high):
                # Volatility overextension filter (Pillar 3)
                if current_price <= lower_band_1:
                    direction = "BUY"
                    signal_level = lvl
                    trigger_reason.append(f"Gann Opening {key.replace('support_', '')} support ₹{lvl:.2f} hit")
                    trigger_reason.append(f"Price overextended below VWAP bands (CMP ₹{current_price:.2f} vs VWAP ₹{vwap:.2f})")
                    active_trigger = True
                    break
                    
    # Check Resistance Reversals (Sell/Short)
    if not active_trigger:
        for key, lvl in grid.items():
            if "resistance" in key:
                if abs(current_high - lvl) / lvl <= 0.0015 or (current_low <= lvl <= current_high):
                    if current_price >= upper_band_1:
                        direction = "SELL"
                        signal_level = lvl
                        trigger_reason.append(f"Gann Opening {key.replace('resistance_', '')} resistance ₹{lvl:.2f} hit")
                        trigger_reason.append(f"Price overextended above VWAP bands (CMP ₹{current_price:.2f} vs VWAP ₹{vwap:.2f})")
                        active_trigger = True
                        break
                        
    # Fallback to Planned Setup if no active trigger is running right now
    if not active_trigger:
        direction = "BUY"
        signal_level = nearest_support
        trigger_reason.append(f"Setup planned: Limit Buy order at Gann Opening support level (₹{nearest_support:.2f})")
        trigger_reason.append(f"VWAP dynamic center is at ₹{vwap:.2f} (deviation ±{std_dev:.2f})")

    # Add timing confirmation details
    if is_ruler_active:
        trigger_reason.append(f"Timing: Hour ruled by planet of the asset ({current_hora['ruler']}) is active")
    if near_reversal_time:
        trigger_reason.append(f"Timing: Near predicted sidereal reversal time window")
            
    # Confidence calibration
    confidence = 50.0
    if active_trigger:
        confidence += 10.0
    if is_ruler_active: 
        confidence += 15.0
    if near_reversal_time: 
        confidence += 15.0
    if current_price <= lower_band_2 or current_price >= upper_band_2: 
        confidence += 10.0
        
    # Calculate entry/SL/Targets for the trade
    entry = signal_level
    sl = 0.0
    t1 = 0.0
    t2 = 0.0
    
    if direction == "BUY":
        sl = round(signal_level - 0.5 * std_dev, 2)
        sl = min(sl, round(entry * 0.995, 2))  # Minimum 0.5% stop loss
        t1 = round(vwap, 2)
        t1 = max(t1, round(entry * 1.01, 2))  # T1 minimum 1.0% (RR 1:2)
        t2 = round(vwap + 1.0 * std_dev, 2)
        t2 = max(t2, round(entry * 1.02, 2))  # T2 minimum 2.0%
    elif direction == "SELL":
        sl = round(signal_level + 0.5 * std_dev, 2)
        sl = max(sl, round(entry * 1.005, 2))
        t1 = round(vwap, 2)
        t1 = min(t1, round(entry * 0.99, 2))  # T1 minimum 1.0%
        t2 = round(vwap - 1.0 * std_dev, 2)
        t2 = min(t2, round(entry * 0.98, 2))
        
    return {
        "ok": True,
        "symbol": symbol,
        "direction": direction,
        "confidence": confidence,
        "opening_price": open_price,
        "vwap": round(vwap, 2),
        "std_dev": round(std_dev, 2),
        "current_price": current_price,
        "signal_level": signal_level,
        "reasons": trigger_reason,
        "entry": entry,
        "stop_loss": sl,
        "target1": t1,
        "target2": t2,
        "hora": current_hora["ruler"] if current_hora else "N/A"
    }
