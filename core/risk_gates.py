# core/risk_gates.py
"""
Risk Gates Validator — Phase 1 Rebuild.
Validates risk limits (Max Positions, Sector exposure, single stock weight, correlation)
before recommending or executing a trade.

PHASE 1 FIX (S1):
  All portfolio queries now target the unified `positions` table (status='OPEN').
  The old `paper_portfolio` table is no longer used — it was a phantom table
  that made all risk checks silently pass.
"""

import math
import sqlite3
import os
from typing import Tuple, Dict

def _db():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "market_data_v2.db")
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def calculate_correlation(sym1: str, sym2: str) -> float:
    """
    Computes Pearson correlation coefficient of daily returns for sym1 and sym2.
    PHASE 2 FIX (Fix 9): Cache-first check. Checks correlation_cache table before doing live EOD query.
    """
    if sym1 == sym2:
        return 1.0

    conn = _db()
    try:
        # Check cache first
        cached = conn.execute(
            "SELECT corr FROM correlation_cache WHERE (sym1=? AND sym2=?) OR (sym1=? AND sym2=?)",
            (sym1, sym2, sym2, sym1)
        ).fetchone()
        if cached is not None:
            return float(cached[0])

        # Fallback to live 120 trading days
        rows1 = conn.execute(
            "SELECT trade_date, close FROM daily_prices WHERE symbol=? AND close IS NOT NULL ORDER BY trade_date DESC LIMIT 120",
            (sym1,)
        ).fetchall()
        rows2 = conn.execute(
            "SELECT trade_date, close FROM daily_prices WHERE symbol=? AND close IS NOT NULL ORDER BY trade_date DESC LIMIT 120",
            (sym2,)
        ).fetchall()
    finally:
        conn.close()

    map1 = {r[0]: float(r[1]) for r in rows1}
    map2 = {r[0]: float(r[1]) for r in rows2}

    common_dates = sorted(set(map1.keys()).intersection(set(map2.keys())), reverse=True)[:100]
    if len(common_dates) < 10:
        return 0.0  # not enough overlap, assume no correlation

    series1 = [map1[d] for d in common_dates]
    series2 = [map2[d] for d in common_dates]

    ret1 = [(series1[i] - series1[i+1]) / series1[i+1] for i in range(len(series1)-1)]
    ret2 = [(series2[i] - series2[i+1]) / series2[i+1] for i in range(len(series2)-1)]

    n = len(ret1)
    if n == 0:
        return 0.0
    mean1 = sum(ret1) / n
    mean2 = sum(ret2) / n
    num  = sum((ret1[i] - mean1) * (ret2[i] - mean2) for i in range(n))
    den1 = sum((x - mean1)**2 for x in ret1)
    den2 = sum((x - mean2)**2 for x in ret2)

    if den1 == 0 or den2 == 0:
        return 0.0

    return round(num / math.sqrt(den1 * den2), 4)


def validate_candidate(candidate: dict, current_allocation: dict, risk_settings: dict) -> Tuple[bool, str]:
    """
    Validates a candidate trade against active risk limits.

    PHASE 1 FIX:
      Now reads open positions from the unified `positions` table (filtered by
      portfolio_id if provided), not the phantom `paper_portfolio` table.

    candidate fields:
      - symbol, sector, price, entry, stop_loss
      - portfolio_id (optional — if provided, only that portfolio's positions are checked)

    risk_settings fields:
      - capital, max_risk_pct, max_positions, daily_loss_limit
      - max_sector_pct, max_position_pct, max_correlation_exposure, kill_switch
    """
    # 0. Kill Switch
    if risk_settings.get("kill_switch", False):
        return False, "Kill Switch is Active. All new trades blocked."

    portfolio_id = candidate.get("portfolio_id")

    # PHASE 1 FIX: Query `positions` table, scoped to portfolio if available
    conn = _db()
    try:
        if portfolio_id:
            open_positions = conn.execute(
                "SELECT symbol, entry_price, shares FROM positions WHERE status='OPEN' AND portfolio_id=?",
                (portfolio_id,)
            ).fetchall()
        else:
            # Fallback: all open positions (single-user mode)
            open_positions = conn.execute(
                "SELECT symbol, entry_price, shares FROM positions WHERE status='OPEN'"
            ).fetchall()
    finally:
        conn.close()

    # 1. Max positions constraint
    max_pos    = int(risk_settings.get("max_positions", 5))
    open_syms  = [p[0] for p in open_positions]
    if candidate["symbol"] not in open_syms:
        if len(open_syms) >= max_pos:
            return False, f"Maximum position limit reached ({max_pos} open positions)"

    # Compute candidate position size from risk settings
    capital      = float(risk_settings.get("capital", 1000000.0))
    deployed     = float(current_allocation.get("total_deployed_capital", 0.0))
    max_risk_pct = float(risk_settings.get("max_risk_pct", 2.0))
    risk_amount  = capital * (max_risk_pct / 100.0)
    price_diff   = abs(candidate["entry"] - candidate["stop_loss"])

    shares = int(risk_amount / price_diff) if price_diff > 0 else 1
    shares = max(shares, 1)

    candidate_size = shares * candidate["entry"]

    # Clamp to max single position weight
    max_pos_pct      = float(risk_settings.get("max_position_pct", 10.0))
    max_allowed_size = capital * (max_pos_pct / 100.0)
    if candidate_size > max_allowed_size:
        shares         = max(int(max_allowed_size / candidate["entry"]), 1)
        candidate_size = shares * candidate["entry"]

    # 2. Max position % check
    candidate_weight = (candidate_size / capital) * 100.0
    if candidate_weight > max_pos_pct * 1.01:
        if shares == 1:
            pass # Allow minimum 1 share for expensive stocks
        else:
            return False, (
                f"Position size ₹{candidate_size:,.0f} exceeds {max_pos_pct}% single-position cap "
                f"(estimated weight: {candidate_weight:.1f}%)"
            )

    # 3. Max sector % check — uses live positions from `positions` table
    max_sector_pct = float(risk_settings.get("max_sector_pct", 30.0))
    from data.instruments import ALL_INSTRUMENTS
    sector_invested: Dict[str, float] = {}
    for p_sym, p_entry, p_shares in open_positions:
        invested = p_entry * p_shares
        inst     = ALL_INSTRUMENTS.get(p_sym)
        p_sec    = inst.sector if inst else "Other"
        sector_invested[p_sec] = sector_invested.get(p_sec, 0.0) + invested

    cand_sec = candidate.get("sector", "Other")
    sector_invested[cand_sec] = sector_invested.get(cand_sec, 0.0) + candidate_size
    new_sector_weight = (sector_invested[cand_sec] / capital) * 100.0
    if new_sector_weight > max_sector_pct:
        return False, (
            f"Sector '{cand_sec}' exposure would be {new_sector_weight:.1f}%, "
            f"exceeding the {max_sector_pct}% sector cap"
        )

    # 4. Correlation check
    max_corr = float(risk_settings.get("max_correlation_exposure", 0.7))
    for open_sym in open_syms:
        if open_sym == candidate["symbol"]:
            continue
        corr = calculate_correlation(candidate["symbol"], open_sym)
        if corr > max_corr:
            return False, (
                f"{candidate['symbol']} has high correlation ({corr:.2f}) with open position "
                f"'{open_sym}' (threshold: {max_corr}). Avoid concentrated correlation risk."
            )

    return True, f"All risk gates passed — estimated position size ₹{candidate_size:,.0f} ({shares} shares)"
