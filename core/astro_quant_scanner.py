# core/astro_quant_scanner.py

"""
Astro-Quant Scanner Engine (V4.0 - Phase 3).
Executes combined ASTRO aspect + QUANT Fourier scans across the instrument universe.
"""

import math
import sqlite3
import os
from datetime import date, timedelta
from typing import List, Dict, Optional

from data.instruments import ALL_INSTRUMENTS, get_instrument, get_natal, get_transit_to_natal_aspects
from core.aspects import detect_aspects, detect_stations
from core.quant_engine import full_quant_analysis

def _db():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "market_data_v2.db")
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.execute("PRAGMA busy_timeout=30000")
    return conn

def get_latest_price(symbol: str, analysis_date: date) -> float:
    conn = _db()
    try:
        row = conn.execute(
            "SELECT close FROM daily_prices WHERE symbol=? AND trade_date<=? "
            "AND close IS NOT NULL ORDER BY trade_date DESC LIMIT 1",
            (symbol, analysis_date.isoformat())
        ).fetchone()
        if row:
            return float(row[0])
    except Exception:
        pass
    finally:
        conn.close()
    
    inst = ALL_INSTRUMENTS.get(symbol)
    return inst.all_time_high * 0.5 if inst else 100.0

def scan_universe(inv_type: str = "swing", risk_pref: str = "balanced", analysis_date: Optional[date] = None, ratio_astro_quant: float = 0.5) -> List[Dict]:
    """
    Scans the 40-symbol universe. Calculates astro and quant scores, combines them,
    generates entry/exit levels, and returns sorted candidates.
    """
    today = analysis_date or date.today()
    candidates = []

    # Get aspects and stations for the date once
    try:
        active_aspects = detect_aspects(today)
        stations = detect_stations(today, days_window=5)
    except Exception:
        active_aspects = []
        stations = []

    for symbol, inst in ALL_INSTRUMENTS.items():
        if inst.instrument_type != "EQUITY":
            continue

        price = get_latest_price(symbol, today)
        if price <= 0:
            continue

        # ── 1. Astronomical Score (0-100) ──
        natal_score = 12.0
        planet_score = 0.0
        try:
            natal_chart = get_natal(symbol)
            if natal_chart:
                natal_transits = get_transit_to_natal_aspects(natal_chart, today)
                bull_signals = [a for a in natal_transits if a.get("nature") == "BULLISH"
                                and a.get("orb", 99) <= 3.0 and a.get("applying") is not False]
                bear_signals = [a for a in natal_transits if a.get("nature") in ("BEARISH", "VOLATILE")
                                and a.get("orb", 99) <= 3.0 and a.get("applying") is not False]
                bull_count = len(bull_signals)
                bear_count = len(bear_signals)
                if bull_count > bear_count:
                    natal_score = min(25, 10 + (bull_count - bear_count) * 3)
                elif bear_count > bull_count:
                    natal_score = max(0, 12 - (bear_count - bull_count) * 3)
                else:
                    natal_score = 12
        except Exception:
            pass

        try:
            ruling_aspects = [a for a in active_aspects
                              if a.planet_a == inst.ruling_planet or a.planet_b == inst.ruling_planet]
            bull_ruling = sum(1 for a in ruling_aspects if a.bullish_bearish == "BULLISH" and a.orb <= 5)
            bear_ruling = sum(1 for a in ruling_aspects if a.bullish_bearish == "BEARISH" and a.orb <= 5)
            if bull_ruling > bear_ruling:
                planet_score = min(25, 8 + bull_ruling * 4)
            elif bull_ruling == bear_ruling and bull_ruling > 0:
                planet_score = 8
            for s in stations:
                if s.get("planet") == inst.ruling_planet:
                    planet_score = min(25, planet_score + 8)
        except Exception:
            pass

        natal_100 = min(100, natal_score * 4)
        planet_100 = min(100, planet_score * 4)
        astro_score = (natal_100 + planet_100) / 2.0

        # ── 2. Quant Score (0-100) ──
        quant_score = 40.0
        fourier_buy_price = None
        fourier_sell_price = None
        fourier_buy_date = None
        fourier_sell_date = None
        sr_data = {}
        fourier_data = {}
        chart_data = {}
        regime_str = "UNKNOWN"

        try:
            qres = full_quant_analysis(
                symbol=symbol, yf_symbol=inst.yfinance_symbol,
                current_price=price, atl=inst.all_time_low, ath=inst.all_time_high,
                as_of_date=today.isoformat()
            )
            reg = qres.get("regime", {})
            regime_str = reg.get("regime", "UNKNOWN")
            regime_map = {"STRONG_BULL": 25, "WEAK_BULL": 18, "SIDEWAYS": 10,
                          "WEAK_BEAR": 5, "STRONG_BEAR": 0, "HIGH_VOLATILITY": 8}
            base_quant = regime_map.get(regime_str, 10) * 4
            
            sr_data = qres.get("support_resistance", {})
            fourier_data = qres.get("fourier", {})
            chart_data = qres.get("chart", {})

            # Simons Fourier trough proximity
            simons_100 = base_quant
            fc60 = fourier_data.get("forecast_60d", [])
            if fc60:
                buy_w_map = {"swing": 15, "short": 30, "long": 60}
                bw = buy_w_map.get(inv_type, 15)
                buy_slice = [(d, p) for d, p in fc60[:bw] if p > 0]
                if buy_slice:
                    trough = min(buy_slice, key=lambda x: x[1])
                    if trough[1] < price * 0.995:
                        fourier_buy_price = round(trough[1], 2)
                        fourier_buy_date = trough[0]
                    
                    # Proximity scoring
                    dist_pct = abs(price - trough[1]) / price
                    if dist_pct <= 0.02:
                        simons_100 = min(100, simons_100 + 40)
                    elif dist_pct <= 0.05:
                        simons_100 = min(100, simons_100 + 20)
                    elif dist_pct <= 0.10:
                        simons_100 = min(100, simons_100 + 10)

                sell_w_map = {"swing": 15, "short": 45, "long": 60}
                sw = sell_w_map.get(inv_type, 15)
                sell_slice = [(d, p) for d, p in fc60[:sw] if p > 0]
                if sell_slice:
                    peak = max(sell_slice, key=lambda x: x[1])
                    if peak[1] > price * 1.005:
                        fourier_sell_price = round(peak[1], 2)
                        fourier_sell_date = peak[0]

                r2 = fourier_data.get("r_squared", 0)
                quant_score = min(100, simons_100 + int(r2 * 20))
        except Exception:
            pass

        # ── 3. Combined Astro-Quant Score ──
        astro_quant_score = (astro_score * ratio_astro_quant) + (quant_score * (1.0 - ratio_astro_quant))
        astro_quant_score = round(max(0.0, min(100.0, astro_quant_score)), 2)

        # ── 4. Entry / SL / Targets Generation ──
        # Anchor to Sq9 pivots or S/R
        sqp = math.sqrt(price)
        sq9_sup1 = round(max(0.01, sqp - 0.5)**2, 2)
        sq9_sup2 = round(max(0.01, sqp - 1.0)**2, 2)

        all_sup = sorted([r for r in sr_data.get("supports", []) if r.get("price", 0) < price],
                         key=lambda x: x.get("price", 0), reverse=True)
        all_res = sorted([r for r in sr_data.get("resistances", []) if r.get("price", 0) > price],
                         key=lambda x: x.get("price", 0))

        sl_pct = {"swing": 0.015, "short": 0.04, "long": 0.09}.get(inv_type, 0.04)
        t1_pct = {"swing": 0.025, "short": 0.08, "long": 0.16}.get(inv_type, 0.08)
        t2_pct = {"swing": 0.05, "short": 0.15, "long": 0.35}.get(inv_type, 0.15)

        # Compute entry
        entry = price
        entry_source = "Current Market Price"
        if all_sup:
            entry = round(all_sup[0]["price"] * 1.001, 2)
            entry_source = "S/R support level"
        else:
            entry = round(sq9_sup1, 2)
            entry_source = "Sq9 support level"

        # Clamp entry within valid range
        max_entry_gap = {"swing": 0.02, "short": 0.05, "long": 0.12}.get(inv_type, 0.05)
        entry = round(max(price * (1 - max_entry_gap), min(price * 1.005, entry)), 2)

        # SL
        if all_sup and all_sup[0].get("price", 0) > entry * (1 - sl_pct * 2):
            sl = round(all_sup[0]["price"] * 0.995, 2)
            sl_source = "Structural S/R support"
        else:
            sl = round(entry * (1 - sl_pct), 2)
            sl_source = f"Fixed SL {sl_pct*100:.1f}%"

        # T1 / T2
        if all_res:
            t1 = round(all_res[0]["price"], 2)
            t1_source = "Nearest S/R resistance"
            t2 = round(all_res[1]["price"], 2) if len(all_res) >= 2 else round(entry * (1 + t2_pct), 2)
            t2_source = "Second S/R resistance" if len(all_res) >= 2 else "Fixed Target 2"
        else:
            t1 = round(entry * (1 + t1_pct), 2)
            t1_source = f"Fixed Target 1 {t1_pct*100:.1f}%"
            t2 = round(entry * (1 + t2_pct), 2)
            t2_source = f"Fixed Target 2 {t2_pct*100:.1f}%"

        # Post clamps and safety checks
        if t1 <= entry:
            t1 = round(entry * 1.03, 2)
        if t2 <= t1:
            t2 = round(t1 * 1.05, 2)
        if sl >= entry:
            sl = round(entry * 0.97, 2)

        candidates.append({
            "symbol": symbol,
            "name": inst.name,
            "sector": inst.sector,
            "price": float(round(price, 2)),
            "entry": float(round(entry, 2)),
            "stop_loss": float(round(sl, 2)),
            "target1": float(round(t1, 2)),
            "target2": float(round(t2, 2)),
            "entry_source": entry_source,
            "sl_source": sl_source,
            "t1_source": t1_source,
            "t2_source": t2_source,
            "astro_score": float(round(astro_score, 2)),
            "quant_score": float(round(quant_score, 2)),
            "astro_quant_score": float(astro_quant_score),
            "inv_type": inv_type,
            "regime": regime_str
        })

    # Sort by AstroQuantScore descending
    candidates.sort(key=lambda x: x["astro_quant_score"], reverse=True)
    return candidates
