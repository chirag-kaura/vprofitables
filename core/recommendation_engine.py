# -*- coding: utf-8 -*-
"""
core/recommendation_engine.py — Personalized Recommendation Pipeline
"""
import json
import os
from data.instruments import ALL_INSTRUMENTS

def generate_personalized_recommendations(user_id: str, candidates: list, conn) -> tuple:
    """
    Filters candidates based on user preferences and adds sizing + explanations.
    Returns: (passed_recommendations: list, blocked: bool, reason: str)
    """
    # 1. Fetch risk profile
    profile = conn.execute("SELECT * FROM risk_profiles WHERE user_id=?", (user_id,)).fetchone()
    if not profile:
        return [], False, "Profile not completed. Please run onboarding first."

    # 2. Check kill switch
    rs_row = conn.execute(
        "SELECT kill_switch, max_position_pct, max_sector_pct FROM risk_settings WHERE user_id=?",
        (user_id,)
    ).fetchone()
    
    kill_switch = bool(rs_row[0]) if rs_row else False
    if kill_switch:
        return [], True, "Kill switch is active."

    # 3. Read profile preferences
    total_capital = float(profile["starting_capital"] or 100000)
    
    # Safe JSON parse preferred markets/styles/sectors
    def safe_json_load(val, default):
        if not val:
            return default
        try:
            return json.loads(val)
        except Exception:
            return default

    pref_markets = safe_json_load(profile["preferred_markets"], ["Indian Stocks"])
    pref_styles = safe_json_load(profile["trading_styles"], ["Long-term investing", "Swing trading"])
    pref_sectors = safe_json_load(profile["preferred_sectors"], ["IT", "Banking", "Pharma"])
    
    # Capital limits
    max_pos_pct = float(profile["max_position_pct"] or (rs_row[1] if rs_row else 10.0))
    max_sec_pct = float(profile["max_sector_pct"] or (rs_row[2] if rs_row else 30.0))
    
    # Fetch current portfolio exposure
    open_trades = conn.execute("""
        SELECT symbol, entry_price, shares 
        FROM positions 
        WHERE status='OPEN' AND portfolio_id = (
            SELECT id FROM portfolios WHERE user_id=? LIMIT 1
        )
    """, (user_id,)).fetchall()

    symbol_exposure = {}
    sector_exposure = {}
    for tr in open_trades:
        sym, entry, shares = tr
        last_px_row = conn.execute("SELECT close FROM daily_prices WHERE symbol=? ORDER BY trade_date DESC LIMIT 1", (sym,)).fetchone()
        cmp = last_px_row[0] if last_px_row else entry
        val = cmp * shares
        symbol_exposure[sym] = symbol_exposure.get(sym, 0.0) + val
        
        inst = ALL_INSTRUMENTS.get(sym)
        sec = inst.sector if inst else "Other"
        sector_exposure[sec] = sector_exposure.get(sec, 0.0) + val

    passed_recommendations = []
    
    for cand in candidates:
        sym = cand.get("symbol")
        if not sym:
            continue
            
        inst = ALL_INSTRUMENTS.get(sym)
        sector = inst.sector if inst else "Other"
        market = inst.exchange if inst else "NSE" # Default to Indian Stocks
        
        # Determine market tag
        market_tag = "Indian Stocks" if "NSE" in market or "BSE" in market else "US Stocks"
        
        # Constraint: Preferred sectors filter (exclude if not preferred)
        if sector not in pref_sectors:
            continue
            
        # Constraint: Market filter
        if market_tag not in pref_markets:
            continue

        # Sizing recommendation (target: 5% or 10% of capital depending on risk comfort)
        comfort = profile["risk_comfort"] or "Moderate"
        sizing_pct = 5.0
        if comfort == "Conservative":
            sizing_pct = 4.0
        elif comfort == "Moderate":
            sizing_pct = 7.5
        elif comfort == "Aggressive":
            sizing_pct = 12.0
        elif comfort == "Very Aggressive":
            sizing_pct = 15.0
            
        # Cap by user max position percentage
        sizing_pct = min(sizing_pct, max_pos_pct)
        recommended_allocation = (total_capital * sizing_pct) / 100.0
        
        # Check current position cap limits
        current_sym_val = symbol_exposure.get(sym, 0.0)
        current_sym_pct = (current_sym_val / total_capital) * 100.0
        if current_sym_pct >= max_pos_pct:
            continue # Already concentrated
            
        # Check sector concentration limits
        current_sec_val = sector_exposure.get(sector, 0.0)
        current_sec_pct = (current_sec_val / total_capital) * 100.0
        if current_sec_pct >= max_sec_pct:
            continue # Sector capacity filled

        # Generate "Why am I seeing this?" annotations
        explanation_tags = [
            f"This matches your interest in the {sector} sector.",
            f"Conforms to your preferred trading environment ({market_tag}).",
            f"Recommended allocation is ₹{recommended_allocation:,.2f} ({sizing_pct}% of total capital), keeping you within your {max_pos_pct}% per-stock comfort limit."
        ]
        
        # Match styles
        matched_styles = []
        cand_styles = cand.get("styles", ["Swing trading", "Technical analysis"])
        for s in cand_styles:
            if s in pref_styles:
                matched_styles.append(s)
        if matched_styles:
            explanation_tags.append(f"Aligned with your trading style: {', '.join(matched_styles)}.")
            
        cand_copy = dict(cand)
        cand_copy["sizing"] = {
            "allocation_pct": sizing_pct,
            "allocation_value": recommended_allocation,
            "max_position_pct": max_pos_pct,
            "max_sector_pct": max_sec_pct
        }
        cand_copy["explanations"] = explanation_tags
        passed_recommendations.append(cand_copy)
        
    return passed_recommendations, False, ""
