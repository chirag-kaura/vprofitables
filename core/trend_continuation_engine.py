"""
trend_continuation_engine.py — Institutional Trend Continuation & Pullback Engine
==================================================================================
Identifies high-probability pullback and continuation setups within strong institutional trends.

In professional quantitative trading:
  • 70% of profits come from Trend Continuations & Pullbacks (riding the momentum wave).
  • 30% of profits come from Cyclical Reversals (inflections at exhaustion extremes).

Combines:
  1. Multi-Timeframe Trend Alignment (Price > EMA20 > EMA50 > EMA200, ADX > 22)
  2. Institutional Pullback Zones (EMA20, Session VWAP, Gann Sq9 45°/90° Angles)
  3. Selling Exhaustion Signature (Volume drying up during pullback < 70% of 20-day avg)
  4. Relative Strength vs. NIFTY50 (Outperforming leaders pull back least and explode first)
  5. Asymmetric Risk-Reward (Tight stop below pullback swing low; Targets at Swing High & 1.618x Ext)
"""

import os
import sys
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "market_data_v2.db")

sys.path.insert(0, BASE_DIR)
from data.instruments import ALL_INSTRUMENTS, get_instrument
from core.gann_math import nearest_sq9, sq9_levels
from core.continuation_deep_engine import predict_continuation_probability

def _conn():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def compute_ema(series: np.ndarray, span: int) -> np.ndarray:
    """Fast exponential moving average."""
    return pd.Series(series).ewm(span=span, adjust=False).mean().values

def compute_adx(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Computes ADX, +DI, -DI."""
    n = len(closes)
    if n < period * 2:
        return np.zeros(n), np.zeros(n), np.zeros(n)
        
    tr1 = highs[1:] - lows[1:]
    tr2 = np.abs(highs[1:] - closes[:-1])
    tr3 = np.abs(lows[1:] - closes[:-1])
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    
    up_move = highs[1:] - highs[:-1]
    down_move = lows[:-1] - lows[1:]
    
    pdm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    ndm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    atr = pd.Series(tr).ewm(alpha=1.0/period, adjust=False).mean().values
    pdm_smooth = pd.Series(pdm).ewm(alpha=1.0/period, adjust=False).mean().values
    ndm_smooth = pd.Series(ndm).ewm(alpha=1.0/period, adjust=False).mean().values
    
    atr_safe = np.where(atr > 0, atr, 1.0)
    pdi = 100.0 * (pdm_smooth / atr_safe)
    ndi = 100.0 * (ndm_smooth / atr_safe)
    
    dx_denom = pdi + ndi
    dx = 100.0 * np.abs(pdi - ndi) / np.where(dx_denom > 0, dx_denom, 1.0)
    adx = pd.Series(dx).ewm(alpha=1.0/period, adjust=False).mean().values
    
    # Pad first element
    adx_full = np.insert(adx, 0, 0.0)
    pdi_full = np.insert(pdi, 0, 0.0)
    ndi_full = np.insert(ndi, 0, 0.0)
    return adx_full, pdi_full, ndi_full

def evaluate_stock_trend(closes: np.ndarray, highs: np.ndarray, lows: np.ndarray, volumes: np.ndarray) -> Dict:
    """
    Evaluates whether a stock is in an institutional trend, ranging, or in a pullback.
    """
    n = len(closes)
    if n < 50:
        return {"regime": "INSUFFICIENT_DATA", "adx": 0.0, "is_bull": False, "is_bear": False}

    ema20  = compute_ema(closes, 20)
    ema50  = compute_ema(closes, 50)
    ema200 = compute_ema(closes, 200) if n >= 200 else compute_ema(closes, n // 2)
    adx, pdi, ndi = compute_adx(highs, lows, closes, 14)

    curr_close = closes[-1]
    curr_ema20 = ema20[-1]
    curr_ema50 = ema50[-1]
    curr_ema200 = ema200[-1]
    curr_adx = adx[-1]

    # Bullish Alignment: Close > EMA20 > EMA50 > EMA200
    is_super_bull = (curr_close > curr_ema20 > curr_ema50 > curr_ema200) and (curr_adx >= 22)
    is_bull_trend = (curr_ema20 > curr_ema50) and (curr_close > curr_ema50)
    
    # Bearish Alignment: Close < EMA20 < EMA50 < EMA200
    is_super_bear = (curr_close < curr_ema20 < curr_ema50 < curr_ema200) and (curr_adx >= 22)
    is_bear_trend = (curr_ema20 < curr_ema50) and (curr_close < curr_ema50)

    # Pullback Detection in Bull Trend
    # Price was above EMA20, but recently dipped near EMA20 (within 1.5%) or between EMA20 and EMA50
    dist_to_ema20_pct = (curr_close - curr_ema20) / curr_ema20 * 100.0
    dist_to_ema50_pct = (curr_close - curr_ema50) / curr_ema50 * 100.0
    
    # Recent 5-day volume vs 20-day avg volume (Volume drying up check)
    avg_vol_20 = np.mean(volumes[-25:-5]) if len(volumes) >= 25 else np.mean(volumes)
    recent_vol = np.mean(volumes[-3:])
    vol_dry_up = (recent_vol < avg_vol_20 * 0.85) if avg_vol_20 > 0 else False

    is_bull_pullback = False
    pullback_quality = 0.0

    if is_bull_trend:
        # Shallow Pullback: Touching or within 1.2% of EMA20 while staying above EMA50
        if -1.5 <= dist_to_ema20_pct <= 1.2 and curr_close > curr_ema50:
            is_bull_pullback = True
            pullback_quality = 80.0
            if vol_dry_up:
                pullback_quality += 15.0  # High edge: institutional volume dry-up
        # Deeper Pullback: Retraced to 50 EMA
        elif -1.5 <= dist_to_ema50_pct <= 1.0:
            is_bull_pullback = True
            pullback_quality = 70.0
            if vol_dry_up:
                pullback_quality += 15.0

    return {
        "regime": "SUPER_BULL_TREND" if is_super_bull else "BULL_TREND" if is_bull_trend else "SUPER_BEAR_TREND" if is_super_bear else "BEAR_TREND" if is_bear_trend else "RANGING_CHOP",
        "adx": round(float(curr_adx), 1),
        "is_bull": bool(is_bull_trend),
        "is_bear": bool(is_bear_trend),
        "is_bull_pullback": bool(is_bull_pullback),
        "pullback_quality": round(float(pullback_quality), 1),
        "vol_dry_up": bool(vol_dry_up),
        "ema20": round(float(curr_ema20), 2),
        "ema50": round(float(curr_ema50), 2),
        "ema200": round(float(curr_ema200), 2),
        "dist_to_ema20_pct": round(float(dist_to_ema20_pct), 2)
    }

def scan_trend_pullbacks(symbol: Optional[str] = None, horizon: str = "swing", min_confidence: int = 65, max_results: int = 15) -> List[Dict]:
    """
    Scans entire universe of equities (or a single requested symbol) for high-conviction
    institutional pullback continuation setups.
    """
    conn = _conn()
    candidates = []

    # Get active symbols with prices
    if symbol:
        sym_clean = symbol.upper().strip()
        symbols = [sym_clean] if sym_clean in ALL_INSTRUMENTS else []
    else:
        symbols = [s for s, inst in ALL_INSTRUMENTS.items() if inst.instrument_type == "EQUITY"]

    # Also fetch Nifty 50 20-day return for Relative Strength calculation
    nifty_rows = conn.execute("""
        SELECT close FROM daily_prices WHERE symbol='NIFTY50' ORDER BY trade_date DESC LIMIT 21
    """).fetchall()
    nifty_ret_20 = 0.0
    if len(nifty_rows) >= 21:
        nifty_ret_20 = (float(nifty_rows[0][0]) / float(nifty_rows[-1][0]) - 1.0) * 100.0

    # Fetch macro context
    part_ctx = "Smart Money: Neutral"
    vix_ctx = "India VIX: Normal"
    try:
        prow = conn.execute("SELECT smart_money_bias, reversal_setup, fii_index_long_pct FROM participant_sentiment_summary ORDER BY trade_date DESC LIMIT 1").fetchone()
        if prow:
            part_ctx = f"Smart Money: {prow[0]} ({prow[1]}) · FII Long {prow[2]:.1f}%"
        vrow = conn.execute("SELECT close FROM daily_prices WHERE symbol='INDIAVIX' ORDER BY trade_date DESC LIMIT 1").fetchone()
        if vrow:
            vix_ctx = f"India VIX: {float(vrow[0]):.1f}"
    except Exception:
        pass

    hold_days_map = {"intraday": 1, "swing": 4, "short": 25, "long": 90}
    hold_days = hold_days_map.get(horizon, 4)

    for sym in symbols:
        try:
            inst = get_instrument(sym)
            rows = conn.execute("""
                SELECT trade_date, open, high, low, close, volume, vwap
                FROM daily_prices
                WHERE symbol = ? AND close IS NOT NULL
                ORDER BY trade_date DESC LIMIT 120
            """, (sym,)).fetchall()

            if len(rows) < 50:
                continue

            rows = list(reversed(rows))
            dates_s   = [r["trade_date"] for r in rows]
            closes_s  = np.array([float(r["close"]) for r in rows])
            highs_s   = np.array([float(r["high"] or r["close"]) for r in rows])
            lows_s    = np.array([float(r["low"] or r["close"]) for r in rows])
            volumes_s = np.array([float(r["volume"] or 0) for r in rows])

            trend_info = evaluate_stock_trend(closes_s, highs_s, lows_s, volumes_s)
            
            # Filter for Pullback in Bull Trend
            if not trend_info["is_bull_pullback"] and not (trend_info["is_bull"] and -2.0 <= trend_info["dist_to_ema20_pct"] <= 1.5):
                continue

            curr_price = round(float(closes_s[-1]), 2)
            high_20d = round(float(np.max(highs_s[-20:])), 2)
            low_5d = round(float(np.min(lows_s[-5:])), 2)
            
            # Stock 20-day return vs Nifty
            sym_ret_20 = (closes_s[-1] / closes_s[-21] - 1.0) * 100.0 if len(closes_s) >= 21 else 0.0
            relative_strength = round(sym_ret_20 - nifty_ret_20, 2)
            
            # Gann Square of 9 support check
            sq9_res, sq9_sup, *_ = nearest_sq9(curr_price)
            
            # Trade Levels
            entry_mid = curr_price
            zone_low = round(min(entry_mid * 0.995, trend_info["ema20"] * 0.997), 2)
            zone_high = round(max(entry_mid * 1.005, trend_info["ema20"] * 1.003), 2)
            stop_loss = round(min(low_5d * 0.995, trend_info["ema50"] * 0.995), 2)
            
            risk_amt = max(0.1, entry_mid - stop_loss)
            target1 = round(high_20d, 2)  # Re-test of 20-day swing high
            target2 = round(entry_mid + 1.618 * (high_20d - low_5d), 2)  # 1.618x extension
            
            rr_ratio = round((target1 - entry_mid) / risk_amt, 2)
            if rr_ratio < 1.3:
                continue  # Discard unfavorable reward-to-risk

            # Confidence score assembly
            confidence = int(trend_info["pullback_quality"])
            reasons = [
                f"Established {trend_info['regime']} (ADX {trend_info['adx']})",
                f"Controlled Pullback to 20 EMA (₹{trend_info['ema20']})",
            ]
            
            if trend_info["vol_dry_up"]:
                confidence += 5
                reasons.append("Selling Volume Dried Up (<85% of 20d avg)")
                
            if relative_strength > 2.0:
                confidence += 5
                reasons.append(f"Leader Outperforming NIFTY (+{relative_strength}% RS)")
                
            if abs(curr_price - sq9_sup) / curr_price <= 0.01:
                confidence += 5
                reasons.append(f"Confluence with Gann Sq9 Level (₹{sq9_sup:,.2f})")

            # Deep Learning & ML Continuation Probability (Ensemble: XGBoost + PyTorch MLP)
            ai_continuation_prob = 0.50
            ai_verdict = "MODERATE_CONTINUATION"
            try:
                ai_res = predict_continuation_probability(sym, dates_s[-1])
                if ai_res.get("ok"):
                    ai_continuation_prob = float(ai_res.get("continuation_prob", 0.50))
                    ai_verdict = ai_res.get("verdict", "MODERATE_CONTINUATION")
                    if ai_continuation_prob >= 0.65:
                        confidence += 8
                        reasons.append(f"AI Deep Learning Edge: {int(ai_continuation_prob*100)}% continuation probability ({ai_verdict})")
                    elif ai_continuation_prob < 0.40:
                        confidence -= 10
            except Exception:
                pass

            confidence = min(95, max(50, confidence))
            if confidence < min_confidence:
                continue

            # Position Sizing: 1% risk rule for ₹1,00,000 capital
            rec_qty = max(1, int(1000.0 / risk_amt))

            # Target exit date calculation
            last_date_str = dates_s[-1]
            try:
                dt_obj = datetime.strptime(last_date_str, "%Y-%m-%d")
                exit_dt = (dt_obj + timedelta(days=hold_days + 2)).strftime("%Y/%m/%d")
                buy_dt_formatted = dt_obj.strftime("%Y/%m/%d")
            except Exception:
                exit_dt = "—"
                buy_dt_formatted = last_date_str

            candidates.append({
                "symbol": sym,
                "name": inst.name,
                "sector": inst.sector,
                "strategy_type": "TREND_PULLBACK_CONTINUATION",
                "setup_name": "Institutional 20-EMA Dip & Rip",
                "pattern_archetype": "CONTINUATION",
                "archetype_label": "⚡ CONTINUATION (20-EMA Pullback)",
                "ai_continuation_prob": ai_continuation_prob,
                "ai_continuation_pct": round(ai_continuation_prob * 100.0, 1),
                "ai_verdict": ai_verdict,
                "inv_type": horizon,
                "action": "BUY",
                "price": curr_price,
                "entry": entry_mid,
                "entry_zone_low": zone_low,
                "entry_zone_high": zone_high,
                "stop_loss": stop_loss,
                "target1": target1,
                "target2": target2,
                "rr_ratio": rr_ratio,
                "confidence": confidence,
                "recommended_qty": rec_qty,
                "risk_per_share": round(risk_amt, 2),
                "hold_days": hold_days,
                "buy_date": buy_dt_formatted,
                "sell_date": exit_dt,
                "buy_time": "09:30 IST",
                "regime": trend_info["regime"],
                "execution_rule": "Institutional Dip-Buyer: Enter inside zone on 5m green confirmation candle. Never chase above zone high.",
                "time_invalidation_rule": f"Time Stop: Invalidate position if price does not break above entry within {min(3, hold_days)} sessions.",
                "relative_strength_vs_nifty": relative_strength,
                "adx_strength": trend_info["adx"],
                "ruling_planet": inst.ruling_planet,
                "analysis_date": dates_s[-1],
                "participant_context": part_ctx,
                "vix_context": vix_ctx,
                "reasons": reasons,
                "scores": {
                    "Trend (ADX)": f"{trend_info['adx']}",
                    "RS vs NIFTY": f"+{relative_strength}%",
                    "EMA20 Support": f"₹{trend_info['ema20']}",
                    "Gann Sq9": f"₹{sq9_sup}"
                },
                "analysis": f"Strong institutional uptrend ({trend_info['regime']}) with selling exhaustion into the 20-day exponential moving average. FII macro posture: {part_ctx}. Asymmetric risk-reward setup with initial target at recent swing highs."
            })
        except Exception:
            continue

    conn.close()
    
    # Sort by highest confidence and best relative strength
    candidates.sort(key=lambda x: (x["confidence"], x["relative_strength_vs_nifty"]), reverse=True)
    return candidates[:max_results]

def scan_intraday_vwap_pullbacks(symbol: str = "NIFTY50", target_date: Optional[str] = None) -> List[Dict]:
    """
    Detects intraday Trend Continuation Pullbacks to Session VWAP on 5m candles.
    The highest-conviction intraday trade:
      1. Morning impulse breaks above VWAP (+1.5σ)
      2. Price pulls back to test session VWAP (Institutional Average Price)
      3. Lower shadow pin bar prints at VWAP on lower volume -> Long continuation to Day High.
    """
    conn = _conn()
    if not target_date:
        row = conn.execute("SELECT SUBSTR(candle_time, 1, 10) FROM intraday_prices WHERE symbol=? ORDER BY candle_time DESC LIMIT 1", (symbol,)).fetchone()
        target_date = row[0] if row else datetime.now().strftime("%Y-%m-%d")

    df = pd.read_sql_query("""
        SELECT candle_time, open, high, low, close, volume, vwap
        FROM intraday_prices
        WHERE symbol = ? AND interval = '5m' AND candle_time LIKE ?
        ORDER BY candle_time ASC
    """, conn, params=(symbol, f"{target_date}%"))
    conn.close()

    if df.empty or len(df) < 15:
        return []

    # Calculate VWAP & Sigma bands
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    cum_pv = (typical * df["volume"]).cumsum()
    cum_v = df["volume"].cumsum()
    df["calc_vwap"] = np.where(cum_v > 0, cum_pv / cum_v, df["close"])
    
    setups = []
    times = df["candle_time"].values
    opens = df["open"].values
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    vols = df["volume"].values
    vwaps = df["calc_vwap"].values

    avg_vol_20 = pd.Series(vols).rolling(20, min_periods=5).mean().values

    for i in range(10, len(df)):
        c_time = times[i]
        c_open, c_high, c_low, c_close = opens[i], highs[i], lows[i], closes[i]
        c_vwap = vwaps[i]
        
        # Bullish VWAP Pullback:
        # 1. Day's high so far was significantly above VWAP (> 0.4%)
        day_high_so_far = np.max(highs[:i])
        if (day_high_so_far - c_vwap) / c_vwap < 0.003:
            continue
            
        # 2. Current bar touches or dips within 0.15% of VWAP, but closes ABOVE VWAP
        touches_vwap = (c_low <= c_vwap * 1.001) and (c_high >= c_vwap * 0.999)
        closes_above = c_close >= c_vwap
        
        # 3. Candlestick rejection: lower wick >= 45% of total candle range
        rng = c_high - c_low
        if rng <= 0: continue
        lower_wick = min(c_open, c_close) - c_low
        has_lower_wick = (lower_wick / rng) >= 0.45
        
        if touches_vwap and closes_above and has_lower_wick:
            stop_loss = round(float(c_low * 0.998), 2)
            target1 = round(float(day_high_so_far), 2)
            c_close_f = round(float(c_close), 2)
            c_vwap_f = round(float(c_vwap), 2)
            risk = max(0.05, float(c_close_f - stop_loss))
            rr = round(float((target1 - c_close_f) / risk), 2)
            
            if rr >= 1.5:
                setups.append({
                    "symbol": symbol,
                    "time": str(c_time),
                    "strategy": "INTRADAY_VWAP_PULLBACK_CONTINUATION",
                    "action": "BUY_AT_VWAP",
                    "entry": c_close_f,
                    "vwap_support": c_vwap_f,
                    "stop_loss": stop_loss,
                    "target_day_high": target1,
                    "risk_reward_ratio": rr,
                    "recommended_qty_1pct": max(1, int(1000.0 / risk)),
                    "reasons": [
                        f"Retest of Institutional Average VWAP (₹{c_vwap_f:.2f})",
                        f"Lower Wick Absorption Pin Bar ({round(float(lower_wick/rng*100))}% wick)",
                        f"Targeting Day's High Retest (₹{target1:.2f})"
                    ]
                })

    return setups

if __name__ == "__main__":
    print("=" * 60)
    print("  Testing Institutional Trend Pullback Engine")
    print("=" * 60)
    results = scan_trend_pullbacks(horizon="swing", min_confidence=60, max_results=5)
    print(f"Found {len(results)} high-conviction trend pullback candidates:")
    for r in results:
        print(f"  • {r['symbol']} ({r['sector']}) — Conf: {r['confidence']}% | R:R {r['rr_ratio']}:1")
        print(f"    Entry: ₹{r['entry']} (Zone: ₹{r['entry_zone_low']} - ₹{r['entry_zone_high']}) | SL: ₹{r['stop_loss']} | T1: ₹{r['target1']}")
        print(f"    Reasons: {'; '.join(r['reasons'])}")
        print()
