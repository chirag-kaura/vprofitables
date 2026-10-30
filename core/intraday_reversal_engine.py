"""
intraday_reversal_engine.py — Precise Intraday Reversal Price & Time Engine
===========================================================================
Pinpoints exact reversal price and exact minute across 5m and 15m bars
by combining:
  1. VWAP +/- 2-Sigma Standard Deviation Exhaustion Bands
  2. Institutional Candlestick Liquidity Formations (Pin Bar / Hammer / Engulfing)
  3. Astro-Planetary Reversal Window Confluence
  4. Option Chain Put/Call Wall Pinning
  5. 5-Minute RSI Bullish/Bearish Divergence
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
from data.instruments import ALL_INSTRUMENTS
from core.paths import get_db_connection as _open_sqlite_connection

def get_intraday_data(symbol: str, target_date: str, interval: str = "5m") -> pd.DataFrame:
    """Fetch 5m or 15m candles for a specific date from SQLite DB."""
    conn = _open_sqlite_connection(readonly=True, timeout=10, path=DB_PATH)
    query = """
        SELECT candle_time, open, high, low, close, volume, vwap
        FROM intraday_prices
        WHERE symbol = ? AND interval = ? AND candle_time LIKE ?
        ORDER BY candle_time ASC
    """
    df = pd.read_sql_query(query, conn, params=(symbol, interval, f"{target_date}%"))
    conn.close()
    return df

def compute_vwap_bands(df: pd.DataFrame) -> pd.DataFrame:
    """Compute Intraday VWAP and +/- 1.5, +/- 2.0 Sigma standard deviation bands."""
    if df.empty:
        return df

    df = df.copy()
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    pv = typical * df["volume"]
    cum_pv = pv.cumsum()
    cum_v = df["volume"].cumsum()
    df["calc_vwap"] = np.where(cum_v > 0, cum_pv / cum_v, df["close"]).round(2)

    # Variance from VWAP
    diff_sq = (typical - df["calc_vwap"]) ** 2
    cum_diff_sq_v = (diff_sq * df["volume"]).cumsum()
    variance = np.where(cum_v > 0, cum_diff_sq_v / cum_v, 0.0)
    std_dev = np.sqrt(np.maximum(variance, 0.0))

    df["vwap_upper_1"] = (df["calc_vwap"] + 1.0 * std_dev).round(2)
    df["vwap_lower_1"] = (df["calc_vwap"] - 1.0 * std_dev).round(2)
    df["vwap_upper_2"] = (df["calc_vwap"] + 2.0 * std_dev).round(2)
    df["vwap_lower_2"] = (df["calc_vwap"] - 2.0 * std_dev).round(2)
    return df

def compute_intraday_rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Compute fast rolling RSI for intraday divergence detection."""
    n = len(closes)
    rsi = np.full(n, 50.0, dtype=float)
    if n <= period:
        return rsi

    deltas = np.diff(closes)
    gains = np.maximum(deltas, 0.0)
    losses = -np.minimum(deltas, 0.0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, n):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        rs = avg_gain / avg_loss if avg_loss > 0 else 100.0
        rsi[i] = 100.0 - (100.0 / (1.0 + rs))
    return rsi

def detect_intraday_reversals(symbol: str, target_date: Optional[str] = None, interval: str = "5m") -> Dict:
    """
    Scans every intraday bar for price exhaustion, VWAP deviation,
    candlestick liquidity rejection, and astro alignment.
    """
    if not target_date:
        conn = _open_sqlite_connection(readonly=True, timeout=5, path=DB_PATH)
        row = conn.execute("SELECT SUBSTR(candle_time, 1, 10) FROM intraday_prices WHERE symbol=? ORDER BY candle_time DESC LIMIT 1", (symbol,)).fetchone()
        conn.close()
        target_date = row[0] if row else datetime.now().strftime("%Y-%m-%d")

    df = get_intraday_data(symbol, target_date, interval=interval)
    if df.empty or len(df) < 10:
        return {
            "symbol": symbol,
            "target_date": target_date,
            "status": "NO_INTRADAY_DATA",
            "reversals": []
        }

    df = compute_vwap_bands(df)
    closes = df["close"].values
    highs  = df["high"].values
    lows   = df["low"].values
    opens  = df["open"].values
    vols   = df["volume"].values
    times  = df["candle_time"].values
    vwaps  = df["calc_vwap"].values
    up_2   = df["vwap_upper_2"].values
    dn_2   = df["vwap_lower_2"].values

    rsi_vals = compute_intraday_rsi(closes, period=14)

    # 1. Fetch Option Chain Support & Resistance Walls for that date
    pe_wall, ce_wall, max_pain = None, None, None
    try:
        conn = _open_sqlite_connection(readonly=True, timeout=5, path=DB_PATH)
        p_row = conn.execute("""
            SELECT max_pain FROM pcr_summary 
            WHERE symbol = ? AND trade_date <= ? ORDER BY trade_date DESC LIMIT 1
        """, (symbol, target_date)).fetchone()
        if p_row:
            max_pain = p_row[0]

        pe_row = conn.execute("""
            SELECT strike FROM option_chain_data
            WHERE symbol = ? AND trade_date <= ? AND option_type = 'PE' AND oi > 0
            ORDER BY oi DESC LIMIT 1
        """, (symbol, target_date)).fetchone()
        if pe_row:
            pe_wall = pe_row[0]

        ce_row = conn.execute("""
            SELECT strike FROM option_chain_data
            WHERE symbol = ? AND trade_date <= ? AND option_type = 'CE' AND oi > 0
            ORDER BY oi DESC LIMIT 1
        """, (symbol, target_date)).fetchone()
        if ce_row:
            ce_wall = ce_row[0]
        conn.close()
    except Exception:
        pass

    # 2. Fetch Astro Intraday Reversal Windows
    astro_windows = []
    try:
        from core.strategy_engine import get_intraday_reversal_times
        inst = ALL_INSTRUMENTS.get(symbol)
        rp = inst.ruling_planet if inst else "Sun"
        t_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
        astro_windows = get_intraday_reversal_times(symbol, t_dt, ruling_planet=rp)
    except Exception:
        pass

    reversal_points = []
    avg_vol_20 = pd.Series(vols).rolling(20, min_periods=5).mean().values

    for i in range(5, len(df)):
        c_time = times[i]
        c_open, c_high, c_low, c_close = opens[i], highs[i], lows[i], closes[i]
        c_vol = vols[i]
        c_vwap = vwaps[i]
        c_rsi = rsi_vals[i]
        time_hhmm = c_time[11:16]

        rng = c_high - c_low
        if rng <= 0:
            continue

        body = abs(c_close - c_open)
        lower_wick = min(c_open, c_close) - c_low
        upper_wick = c_high - max(c_open, c_close)
        vol_spike = c_vol >= (avg_vol_20[i] * 1.35) if avg_vol_20[i] > 0 else False

        # Astro window check (within 15 minutes of any astro reversal point)
        astro_hit = False
        astro_label = ""
        for win in astro_windows:
            if isinstance(win, dict):
                w_start = win.get("start", "")
                w_end   = win.get("end", "")
                if w_start <= time_hhmm <= w_end:
                    astro_hit = True
                    astro_label = f"Astro Window ({win.get('event', 'Harmonic Pivot')})"
                    break
            elif isinstance(win, str):
                try:
                    w_dt = datetime.strptime(win[:5], "%H:%M")
                    c_dt = datetime.strptime(time_hhmm, "%H:%M")
                    if abs((c_dt - w_dt).total_seconds()) <= 15 * 60:
                        astro_hit = True
                        astro_label = f"Astro Harmonic Turn ({win[:5]})"
                        break
                except Exception:
                    pass

        # Check BULLISH BOTTOM Reversal
        # Condition: Price at/below -1.5 Sigma VWAP or Put Wall, forming a Hammer or Bullish Engulfing
        is_hammer = (lower_wick / rng >= 0.55) and (body / rng <= 0.35) and (c_close >= c_open or lower_wick > 2 * body)
        is_bull_engulf = (c_close > c_open) and (opens[i-1] > closes[i-1]) and (c_close >= opens[i-1]) and (c_open <= closes[i-1])
        near_vwap_lower = c_low <= dn_2[i] or (c_low <= c_vwap * 0.99)
        near_put_wall = pe_wall and (abs(c_low - pe_wall) / pe_wall <= 0.003)

        if (is_hammer or is_bull_engulf) and (near_vwap_lower or near_put_wall):
            confluence = 1
            reasons = []
            if is_hammer: reasons.append("Hammer Liquidity Absorption")
            if is_bull_engulf: reasons.append("Bullish Engulfing")
            if near_vwap_lower:
                confluence += 1
                reasons.append(f"VWAP -2σ Oversold ({dn_2[i]})")
            if near_put_wall:
                confluence += 2
                reasons.append(f"Tested Option Put Wall ({pe_wall})")
            if astro_hit:
                confluence += 2
                reasons.append(astro_label)
            if vol_spike:
                confluence += 1
                reasons.append(f"Volume Spike ({c_vol:,})")
            if c_rsi <= 35:
                confluence += 1
                reasons.append(f"RSI Oversold ({c_rsi:.1f})")

            # Entry, Target, Stop-Loss, Zones & Risk Rules
            sl_price = round(c_low * 0.997, 2)
            risk_unit = max(0.05, c_close - sl_price)
            reversal_points.append({
                "type": "BULLISH_REVERSAL_BOTTOM",
                "time": c_time,
                "exact_reversal_price": round(c_low, 2),
                "reversal_zone_low": round(c_low * 0.997, 2),
                "reversal_zone_high": round(c_low * 1.003, 2),
                "trigger_price": round(c_close, 2),
                "target_price": round(c_vwap, 2),
                "stop_loss": sl_price,
                "risk_reward_ratio": round((c_vwap - c_close) / risk_unit, 2),
                "confluence_score": confluence,
                "execution_rule": "Sweep & Reclaim: Wait for 5m candle lower wick rejection and close above zone.",
                "time_stop_rule": "Time Invalidation: Cut trade if price does not expand toward VWAP within 3 bars (15 mins).",
                "recommended_qty_1pct": max(1, int(1000.0 / risk_unit)),
                "reasons": reasons
            })

        # Check BEARISH TOP Reversal
        # Condition: Price at/above +1.5 Sigma VWAP or Call Wall, forming a Shooting Star or Bearish Engulfing
        is_star = (upper_wick / rng >= 0.55) and (body / rng <= 0.35)
        is_bear_engulf = (c_close < c_open) and (closes[i-1] > opens[i-1]) and (c_close <= opens[i-1]) and (c_open >= closes[i-1])
        near_vwap_upper = c_high >= up_2[i] or (c_high >= c_vwap * 1.01)
        near_call_wall = ce_wall and (abs(c_high - ce_wall) / ce_wall <= 0.003)

        if (is_star or is_bear_engulf) and (near_vwap_upper or near_call_wall):
            confluence = 1
            reasons = []
            if is_star: reasons.append("Shooting Star Rejection")
            if is_bear_engulf: reasons.append("Bearish Engulfing")
            if near_vwap_upper:
                confluence += 1
                reasons.append(f"VWAP +2σ Overbought ({up_2[i]})")
            if near_call_wall:
                confluence += 2
                reasons.append(f"Tested Option Call Wall ({ce_wall})")
            if astro_hit:
                confluence += 2
                reasons.append(astro_label)
            if vol_spike:
                confluence += 1
                reasons.append(f"Volume Spike ({c_vol:,})")
            if c_rsi >= 65:
                confluence += 1
                reasons.append(f"RSI Overbought ({c_rsi:.1f})")

            sl_price_bear = round(c_high * 1.003, 2)
            risk_unit_bear = max(0.05, sl_price_bear - c_close)
            reversal_points.append({
                "type": "BEARISH_REVERSAL_TOP",
                "time": c_time,
                "exact_reversal_price": round(c_high, 2),
                "reversal_zone_low": round(c_high * 0.997, 2),
                "reversal_zone_high": round(c_high * 1.003, 2),
                "trigger_price": round(c_close, 2),
                "target_price": round(c_vwap, 2),
                "stop_loss": sl_price_bear,
                "risk_reward_ratio": round((c_close - c_vwap) / risk_unit_bear, 2),
                "confluence_score": confluence,
                "execution_rule": "Sweep & Reclaim: Wait for 5m candle upper wick rejection and close below zone.",
                "time_stop_rule": "Time Invalidation: Cut trade if price does not retreat toward VWAP within 3 bars (15 mins).",
                "recommended_qty_1pct": max(1, int(1000.0 / risk_unit_bear)),
                "reasons": reasons
            })

    # Sort reversals by highest confluence score first
    reversal_points.sort(key=lambda x: x["confluence_score"], reverse=True)

    return {
        "symbol": symbol,
        "target_date": target_date,
        "interval": interval,
        "total_candles": len(df),
        "day_open": float(opens[0]),
        "day_high": float(np.max(highs)),
        "day_low": float(np.min(lows)),
        "day_close": float(closes[-1]),
        "intraday_vwap": float(vwaps[-1]),
        "put_wall_support": pe_wall,
        "call_wall_resistance": ce_wall,
        "reversals_detected": len(reversal_points),
        "reversals": reversal_points
    }

def get_time_of_day_distribution(symbol: str, interval: str = "5m") -> Dict:
    """Computes historical probability of Day High and Day Low occurring by 30-min time buckets."""
    conn = _open_sqlite_connection(readonly=True, timeout=10, path=DB_PATH)
    df = pd.read_sql_query("""
        SELECT candle_time, high, low
        FROM intraday_prices
        WHERE symbol = ? AND interval = ?
        ORDER BY candle_time ASC
    """, conn, params=(symbol, interval))
    conn.close()

    if df.empty:
        return {}

    df["date"] = df["candle_time"].str[:10]
    df["time"] = df["candle_time"].str[11:16]

    high_times, low_times = [], []
    for d, grp in df.groupby("date"):
        if len(grp) < 20: continue
        h_idx = grp["high"].idxmax()
        l_idx = grp["low"].idxmin()
        high_times.append(grp.loc[h_idx, "time"])
        low_times.append(grp.loc[l_idx, "time"])

    def bucket_times(t_list):
        buckets = {
            "09:15-10:00 (Opening Shakeout)": 0,
            "10:00-11:30 (Morning Trend)": 0,
            "11:30-13:00 (Midday Consolidation)": 0,
            "13:00-14:30 (European Open Shift)": 0,
            "14:30-15:30 (Closing Squeeze)": 0
        }
        for t in t_list:
            if "09:15" <= t < "10:00": buckets["09:15-10:00 (Opening Shakeout)"] += 1
            elif "10:00" <= t < "11:30": buckets["10:00-11:30 (Morning Trend)"] += 1
            elif "11:30" <= t < "13:00": buckets["11:30-13:00 (Midday Consolidation)"] += 1
            elif "13:00" <= t < "14:30": buckets["13:00-14:30 (European Open Shift)"] += 1
            elif "14:30" <= t <= "15:30": buckets["14:30-15:30 (Closing Squeeze)"] += 1

        total = len(t_list) if len(t_list) > 0 else 1
        return {k: round(v / total * 100, 1) for k, v in buckets.items()}

    return {
        "symbol": symbol,
        "total_days_analyzed": len(set(df["date"])),
        "day_low_reversal_odds": bucket_times(low_times),
        "day_high_reversal_odds": bucket_times(high_times)
    }
