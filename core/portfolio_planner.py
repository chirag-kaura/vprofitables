# core/portfolio_planner.py

"""
Personalized Portfolio Planner (V4.0 - Phase 5).
Combines Scanner, Portfolio State, and Risk Gates to generate optimized,
actionable allocation plans.
"""

from typing import List, Dict, Optional
import sqlite3
import os

from core.portfolio_state import get_current_allocation, get_available_capital
from core.astro_quant_scanner import scan_universe
from core.risk_gates import validate_candidate

def _db():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "market_data_v2.db")
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.execute("PRAGMA busy_timeout=30000")
    return conn

def get_active_risk_settings() -> dict:
    conn = _db()
    try:
        row = conn.execute(
            "SELECT capital,max_risk_pct,max_positions,daily_loss_limit,max_sector_pct,kill_switch,max_position_pct,max_correlation_exposure FROM risk_settings WHERE id=1"
        ).fetchone()
        if row:
            return {
                "capital": float(row[0]),
                "max_risk_pct": float(row[1]),
                "max_positions": int(row[2]),
                "daily_loss_limit": float(row[3]),
                "max_sector_pct": float(row[4]),
                "kill_switch": bool(row[5]),
                "max_position_pct": float(row[6]),
                "max_correlation_exposure": float(row[7])
            }
    except Exception:
        pass
    finally:
        conn.close()

    # Fallback default settings
    return {
        "capital": 1000000.0,
        "max_risk_pct": 2.0,
        "max_positions": 5,
        "daily_loss_limit": 50000.0,
        "max_sector_pct": 30.0,
        "kill_switch": False,
        "max_position_pct": 10.0,
        "max_correlation_exposure": 0.7
    }

def generate_plan(inv_type: str = "swing", risk_pref: str = "balanced", ratio_astro_quant: float = 0.5) -> dict:
    """
    Fetches capital, runs universe scan, filters via Risk Gates,
    and returns an actionable, risk-controlled allocation plan.
    """
    risk_settings = get_active_risk_settings()
    
    # 0. Check Kill Switch
    if risk_settings.get("kill_switch", False):
        return {
            "ok": False,
            "error": "Kill Switch is Active. All planning operations blocked."
        }

    # Fetch allocations and scanner candidates
    current_alloc = get_current_allocation()
    candidates = scan_universe(inv_type=inv_type, risk_pref=risk_pref, ratio_astro_quant=ratio_astro_quant)

    plan_items = []
    
    # We will build the plan items by validating candidates sequentially.
    # When a candidate passes, we dynamically update our simulated allocation
    # so subsequent candidates are checked against the new allocation state!
    simulated_alloc = {
        "symbol_exposure": dict(current_alloc.get("symbol_exposure", {})),
        "sector_exposure": list(current_alloc.get("sector_exposure", [])),
        "total_deployed_capital": float(current_alloc.get("total_deployed_capital", 0.0))
    }
    
    capital = risk_settings["capital"]
    max_risk_pct = risk_settings["max_risk_pct"]
    max_pos_pct = risk_settings["max_position_pct"]

    for cand in candidates:
        # Check if candidate passes risk gates
        is_ok, reason = validate_candidate(cand, simulated_alloc, risk_settings)
        if not is_ok:
            continue

        # Compute position size
        price_diff = abs(cand["entry"] - cand["stop_loss"])
        risk_amount = capital * (max_risk_pct / 100.0)
        
        if price_diff > 0:
            shares = int(risk_amount / price_diff)
        else:
            shares = 1

        # Apply single position weight cap
        max_allowed_size = capital * (max_pos_pct / 100.0)
        candidate_size = shares * cand["entry"]
        if candidate_size > max_allowed_size:
            shares = int(max_allowed_size / cand["entry"])
            candidate_size = shares * cand["entry"]

        if shares <= 0:
            shares = 1
            candidate_size = shares * cand["entry"]

        expected_risk_val = float(round(shares * price_diff, 2))

        plan_items.append({
            "symbol": cand["symbol"],
            "name": cand["name"],
            "sector": cand["sector"],
            "shares": int(shares),
            "entry": float(cand["entry"]),
            "stop_loss": float(cand["stop_loss"]),
            "target1": float(cand["target1"]),
            "target2": float(cand["target2"]),
            "expected_risk_val": expected_risk_val,
            "astro_quant_score": float(cand["astro_quant_score"])
        })

        # Update simulated allocation state for next iteration
        simulated_alloc["total_deployed_capital"] += candidate_size
        simulated_alloc["symbol_exposure"][cand["symbol"]] = round((candidate_size / capital) * 100.0, 2)
        
        # Update simulated sector exposure
        found_sec = False
        for sec_item in simulated_alloc["sector_exposure"]:
            if sec_item["sector"] == cand["sector"]:
                sec_item["pct"] = round(sec_item["pct"] + (candidate_size / capital) * 100.0, 2)
                found_sec = True
                break
        if not found_sec:
            simulated_alloc["sector_exposure"].append({
                "sector": cand["sector"],
                "pct": round((candidate_size / capital) * 100.0, 2)
            })

    # Return structured plan
    return {
        "ok": True,
        "plan": plan_items,
        "total_deployed_capital": round(simulated_alloc["total_deployed_capital"], 2),
        "available_capital": get_available_capital(risk_settings)
    }
