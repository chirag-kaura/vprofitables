"""
core/strategy_engine.py — Multi-Regime Quantitative Strategy Engine (v1.1)
Implements target setups for all 4 investment types:
  1. Intraday: Expiry attraction and Option Concentration support/resistance channel.
  2. Swing: PCR momentum shifts and planetary reversal hour offsets.
  3. Short Term: Multi-expiry Max Pain trend-following alignments.
  4. Long Term: Extreme PCR fear exhaustion floor accumulation.

Supports optional 'target_date' parameter (date object or YYYY-MM-DD string) for backtesting and historical evaluation.
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import date, datetime
from core.paths import DB_PATH
from core.gann_math import get_intraday_reversal_times

def get_db_connection():
    return sqlite3.connect(DB_PATH, timeout=15.0)


def _parse_target_date(conn, symbol: str, target_date) -> str:
    """Helper to parse target_date or fallback to the latest date in the database."""
    if target_date:
        if isinstance(target_date, (date, datetime)):
            return target_date.strftime("%Y-%m-%d")
        return str(target_date)
        
    # Get latest date from daily_prices
    row = conn.execute(
        "SELECT MAX(trade_date) FROM daily_prices WHERE symbol=? OR symbol=?",
        (symbol, f"{symbol}50")
    ).fetchone()
    if row and row[0]:
        return row[0]
        
    # Fallback to absolute max date
    row = conn.execute("SELECT MAX(trade_date) FROM daily_prices").fetchone()
    return row[0] if row else date.today().strftime("%Y-%m-%d")


def get_intraday_strategy_signal(symbol: str, target_date=None) -> dict:
    """
    Expiry Day Mean Reversion & Strike Pinning Strategy.
    Pins spot close near Max Pain on expiry days.
    """
    conn = get_db_connection()
    try:
        latest_date = _parse_target_date(conn, symbol, target_date)
        
        # 1. Fetch spot price on target date
        spot_row = conn.execute(
            """SELECT close FROM daily_prices 
               WHERE (symbol=? OR symbol=?) AND trade_date<=?
               ORDER BY trade_date DESC LIMIT 1""",
            (symbol, f"{symbol}50", latest_date)
        ).fetchone()
        
        if not spot_row:
            spot_row = conn.execute(
                """SELECT close FROM daily_prices 
                   WHERE symbol LIKE ? AND trade_date<=?
                   ORDER BY trade_date DESC LIMIT 1""",
                (f"%{symbol}%", latest_date)
            ).fetchone()
            
        if not spot_row:
            return {"status": "error", "message": f"No price data found for symbol: {symbol} on or before {latest_date}"}
            
        spot_price = spot_row[0]
        
        # 2. Fetch nearest expiry metrics on that date
        pcr_row = conn.execute(
            """SELECT expiry_date, max_pain, pcr 
               FROM pcr_summary 
               WHERE symbol=? AND trade_date=? AND expiry_date >= ?
               ORDER BY expiry_date ASC LIMIT 1""",
            (symbol, latest_date, latest_date)
        ).fetchone()
        
        if not pcr_row:
            return {
                "symbol": symbol,
                "spot_price": round(spot_price, 2),
                "trade_date": latest_date,
                "signal": "HOLD",
                "reason": f"No active options chain/expiry data found for {latest_date}.",
                "support": round(spot_price * 0.98, 2),
                "resistance": round(spot_price * 1.02, 2)
            }
            
        expiry_date, max_pain, pcr = pcr_row
        is_expiry_day = (expiry_date == latest_date)
        
        # 3. Find option concentration boundaries (strikes with max OI)
        max_pe_row = conn.execute(
            """SELECT strike FROM option_chain_data 
               WHERE symbol=? AND trade_date=? AND expiry_date=? AND option_type='PE'
               ORDER BY oi DESC LIMIT 1""",
            (symbol, latest_date, expiry_date)
        ).fetchone()
        
        max_ce_row = conn.execute(
            """SELECT strike FROM option_chain_data 
               WHERE symbol=? AND trade_date=? AND expiry_date=? AND option_type='CE'
               ORDER BY oi DESC LIMIT 1""",
            (symbol, latest_date, expiry_date)
        ).fetchone()
        
        support = max_pe_row[0] if max_pe_row else spot_price * 0.98
        resistance = max_ce_row[0] if max_ce_row else spot_price * 1.02
        
        # 4. Generate Signal
        dist_pct = (spot_price - max_pain) / spot_price
        signal = "HOLD"
        reason = "Market trading in equilibrium."
        
        if is_expiry_day:
            if dist_pct > 0.0075:
                signal = "SELL (Expiry Mean Reversion)"
                reason = f"Spot is {dist_pct*100:.2f}% above Max Pain ({max_pain}). Targeting Max Pain pull-back."
            elif dist_pct < -0.0075:
                signal = "BUY (Expiry Mean Reversion)"
                reason = f"Spot is {abs(dist_pct)*100:.2f}% below Max Pain ({max_pain}). Targeting Max Pain rebound."
            else:
                signal = "PINNED (Neutral)"
                reason = f"Spot is trading near Max Pain ({max_pain}) on Expiry Day."
        else:
            if spot_price <= support * 1.002:
                signal = "BUY (Support Bounce)"
                reason = f"Spot is testing maximum Put Open Interest support wall at {support}."
            elif spot_price >= resistance * 0.998:
                signal = "SELL (Resistance Reject)"
                reason = f"Spot is testing maximum Call Open Interest resistance wall at {resistance}."
                
        return {
            "symbol": symbol,
            "trade_date": latest_date,
            "spot_price": round(spot_price, 2),
            "max_pain": max_pain,
            "pcr": round(pcr, 2),
            "expiry_date": expiry_date,
            "is_expiry_day": is_expiry_day,
            "support": support,
            "resistance": resistance,
            "signal": signal,
            "reason": reason
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def get_swing_strategy_signal(symbol: str, target_date=None) -> dict:
    """
    Swing momentum based on PCR regime shift and astro reversal times.
    """
    conn = get_db_connection()
    try:
        latest_date = _parse_target_date(conn, symbol, target_date)
        
        # Fetch last 5 trading days PCR values up to target_date
        df_pcr = pd.read_sql_query(
            """SELECT trade_date, pcr 
               FROM pcr_summary 
               WHERE symbol=? AND trade_date <= ?
               ORDER BY trade_date DESC LIMIT 5""",
            conn, params=(symbol, latest_date)
        )
        
        if len(df_pcr) < 3:
            return {
                "symbol": symbol,
                "trade_date": latest_date,
                "signal": "HOLD",
                "reason": f"Insufficient historical PCR data on or before {latest_date}."
            }
            
        df_pcr = df_pcr.sort_values("trade_date")
        latest_pcr = df_pcr.iloc[-1]["pcr"]
        prev_pcr = df_pcr.iloc[-2]["pcr"]
        
        # Identify planetary reversal times
        t_date = datetime.strptime(latest_date, "%Y-%m-%d").date()
        from data.instruments import ALL_INSTRUMENTS
        inst = ALL_INSTRUMENTS.get(symbol)
        ruling_planet = inst.ruling_planet if inst else "Sun"
        reversal_times = get_intraday_reversal_times(symbol, t_date, ruling_planet=ruling_planet)
        
        signal = "HOLD"
        reason = f"PCR regime neutral at {latest_pcr:.2f}."
        
        if latest_pcr < 0.85 and latest_pcr > prev_pcr:
            signal = "BUY (PCR Momentum Breakout)"
            reason = f"PCR is rising ({latest_pcr:.2f} vs {prev_pcr:.2f}) from strong bullish regime (<0.85)."
        elif prev_pcr > 1.40 and latest_pcr < prev_pcr:
            signal = "BUY (Contrarian Reversal)"
            reason = f"PCR turning down ({latest_pcr:.2f} vs {prev_pcr:.2f}) from extreme fear overbought level (>1.40)."
        elif latest_pcr > 1.30 and latest_pcr > prev_pcr:
            signal = "SELL (Risk Off)"
            reason = f"PCR is rising in fear zone ({latest_pcr:.2f}), suggesting high protection build."
            
        return {
            "symbol": symbol,
            "trade_date": latest_date,
            "latest_pcr": round(latest_pcr, 2),
            "prev_pcr": round(prev_pcr, 2),
            "ruling_planet": ruling_planet,
            "reversal_windows": reversal_times,
            "signal": signal,
            "reason": reason
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def get_short_term_strategy_signal(symbol: str, target_date=None) -> dict:
    """
    Short Term (15-45 days) Trend using Multi-Expiry monthly Max Pain alignment.
    """
    conn = get_db_connection()
    try:
        latest_date = _parse_target_date(conn, symbol, target_date)
        
        # Get the next 3 expiries available on that trade date
        expiries_df = pd.read_sql_query(
            """SELECT expiry_date, max_pain, pcr
               FROM pcr_summary 
               WHERE symbol=? AND trade_date=?
               ORDER BY expiry_date ASC LIMIT 3""",
            conn, params=(symbol, latest_date)
        )
        
        if len(expiries_df) < 2:
            return {
                "symbol": symbol,
                "trade_date": latest_date,
                "signal": "HOLD",
                "reason": f"Fewer than 2 active expiries available on {latest_date}."
            }
            
        mp_current = expiries_df.iloc[0]["max_pain"]
        mp_next = expiries_df.iloc[1]["max_pain"]
        
        signal = "HOLD"
        reason = "Rollover strikes are flat."
        
        if len(expiries_df) == 3:
            mp_far = expiries_df.iloc[2]["max_pain"]
            if mp_current < mp_next < mp_far:
                signal = "ACCUMULATE (Bullish Roll Trend)"
                reason = f"Max Pain strikes are scaling upward: Current ({mp_current}) < Next ({mp_next}) < Far ({mp_far})."
            elif mp_current > mp_next > mp_far:
                signal = "DISTRIBUTE (Bearish Roll Trend)"
                reason = f"Max Pain strikes are scaling downward: Current ({mp_current}) > Next ({mp_next}) > Far ({mp_far})."
        else:
            if mp_current < mp_next:
                signal = "ACCUMULATE (Bullish Roll)"
                reason = f"Next expiry Max Pain ({mp_next}) is higher than current expiry ({mp_current})."
            elif mp_current > mp_next:
                signal = "DISTRIBUTE (Bearish Roll)"
                reason = f"Next expiry Max Pain ({mp_next}) is lower than current expiry ({mp_current})."
                
        return {
            "symbol": symbol,
            "trade_date": latest_date,
            "expiries_profile": expiries_df.to_dict(orient="records"),
            "signal": signal,
            "reason": reason
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def get_long_term_strategy_signal(symbol: str, target_date=None) -> dict:
    """
    Long Term Strategy: Extreme PCR exhaustion floor accumulator.
    Triggers buy when PCR stays > 1.50 for 3 days.
    """
    conn = get_db_connection()
    try:
        latest_date = _parse_target_date(conn, symbol, target_date)
        
        # Fetch last 30 days of PCR history up to target_date
        df = pd.read_sql_query(
            """SELECT trade_date, pcr, spot_price 
               FROM pcr_summary 
               WHERE symbol=? AND trade_date <= ?
               ORDER BY trade_date DESC LIMIT 30""",
            conn, params=(symbol, latest_date)
        )
        
        if df.empty:
            return {"symbol": symbol, "trade_date": latest_date, "signal": "HOLD", "reason": "No option data available."}
            
        df = df.sort_values("trade_date")
        latest_pcr = df.iloc[-1]["pcr"]
        
        # Check if PCR was above 1.5 for 3 consecutive days in the last 10 days
        df['high_pcr_strike'] = df['pcr'] >= 1.50
        df['consecutive_high'] = df['high_pcr_strike'].rolling(3).sum()
        
        has_consecutive_extreme = (df['consecutive_high'].max() >= 3)
        
        signal = "HOLD"
        reason = f"Long-term indices neutral. Current PCR: {latest_pcr:.2f}."
        
        if has_consecutive_extreme and latest_pcr < 1.30:
            signal = "BUY / ACCUMULATE (Post-Fear Floor Rebound)"
            reason = "Capitulation floor confirmed: PCR hit >1.50 for 3 consecutive days and is now recovering."
        elif latest_pcr >= 1.50:
            signal = "ACCUMULATION ZONE (Extreme Fear)"
            reason = f"Current PCR is {latest_pcr:.2f}, indicating historical retail panic. Highly favorable risk-to-reward ratio."
        elif latest_pcr < 0.70:
            signal = "PARTIAL PROFIT BOOKING (Extreme Euphoria)"
            reason = f"PCR is exceptionally low at {latest_pcr:.2f}, suggesting call buying is overheated."
            
        return {
            "symbol": symbol,
            "trade_date": latest_date,
            "latest_pcr": round(latest_pcr, 2),
            "highest_pcr_30d": round(df["pcr"].max(), 2),
            "lowest_pcr_30d": round(df["pcr"].min(), 2),
            "signal": signal,
            "reason": reason
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()
