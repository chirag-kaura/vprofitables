# core/portfolio_state.py
"""
Portfolio State Reader — Phase 1 Rebuild.
Provides real-time portfolio allocations and available capital readings.

PHASE 1 FIX (S1):
  All queries now target the unified `positions` table (status='OPEN').
  The old `paper_portfolio` table is no longer read — it was returning empty
  results, making `get_available_capital()` always return the full starting
  capital and effectively removing all capital constraint checks.

  get_available_capital() now accepts an optional portfolio_id so that
  multi-user environments are correctly scoped.
"""

from data.instruments import ALL_INSTRUMENTS


def _db():
    import sqlite3
    import os
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "market_data_v2.db"
    )
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def get_current_allocation(portfolio_id: str = None) -> dict:
    """
    Reads open positions from `positions` table, groups by inv_type and sector.
    Returns weights by symbol, sector, inv_type, and total deployed capital.

    Args:
        portfolio_id: If provided, only positions from that portfolio are included.
                      If None, sums across all portfolios (single-user fallback).
    """
    conn = _db()
    try:
        if portfolio_id:
            open_trades = conn.execute(
                "SELECT symbol, inv_type, entry_price, shares "
                "FROM positions WHERE status='OPEN' AND portfolio_id=?",
                (portfolio_id,)
            ).fetchall()
        else:
            open_trades = conn.execute(
                "SELECT symbol, inv_type, entry_price, shares "
                "FROM positions WHERE status='OPEN'"
            ).fetchall()
    finally:
        conn.close()

    total_invested     = 0.0
    symbol_invested    = {}
    sector_invested    = {}
    inv_type_invested  = {}

    for symbol, inv_type, entry_price, shares in open_trades:
        invested = entry_price * shares
        total_invested += invested

        symbol_invested[symbol] = symbol_invested.get(symbol, 0.0) + invested

        inst   = ALL_INSTRUMENTS.get(symbol)
        sector = inst.sector if inst else "Other"
        sector_invested[sector] = sector_invested.get(sector, 0.0) + invested

        inv_type_invested[inv_type] = inv_type_invested.get(inv_type, 0.0) + invested

    symbol_weight   = {}
    sector_weight   = []
    inv_type_weight = {}

    if total_invested > 0:
        for sym, amt in symbol_invested.items():
            symbol_weight[sym] = round((amt / total_invested) * 100, 2)

        for sec, amt in sector_invested.items():
            sector_weight.append({
                "sector": sec,
                "pct":    round((amt / total_invested) * 100, 2)
            })

        for itype, amt in inv_type_invested.items():
            inv_type_weight[itype] = round((amt / total_invested) * 100, 2)

    return {
        "symbol_exposure":       symbol_weight,
        "sector_exposure":       sector_weight,
        "inv_type_exposure":     inv_type_weight,
        "total_deployed_capital": round(total_invested, 2),
    }


def get_available_capital(risk_settings: dict = None, portfolio_id: str = None,
                          user_id: str = None) -> float:
    """
    Returns starting_capital minus currently deployed capital in open positions.

    Resolution order for starting capital:
      1. risk_settings["capital"] if provided by caller.
      2. risk_settings table in SQLite (per-user row if user_id given, else id=1).
      3. risk_profiles table starting_capital (if user_id given).
      4. Default ₹10,00,000 fallback.

    PHASE 1 FIX: reads deployed capital from `positions` (not paper_portfolio).
    """
    # ── Resolve starting capital ──────────────────────────────────────────────
    if risk_settings and "capital" in risk_settings:
        capital = float(risk_settings["capital"])
    else:
        conn = _db()
        try:
            # Try per-user risk_settings row first
            if user_id:
                cap_row = conn.execute(
                    "SELECT capital FROM risk_settings WHERE user_id=?",
                    (user_id,)
                ).fetchone()
                if not cap_row:
                    # Fall back to risk_profiles
                    cap_row = conn.execute(
                        "SELECT starting_capital FROM risk_profiles WHERE user_id=?",
                        (user_id,)
                    ).fetchone()
            else:
                cap_row = conn.execute(
                    "SELECT capital FROM risk_settings WHERE id=1"
                ).fetchone()
            capital = float(cap_row[0]) if cap_row and cap_row[0] else 1_000_000.0
        finally:
            conn.close()

    # ── Compute deployed capital from `positions` ────────────────────────────
    conn = _db()
    try:
        if portfolio_id:
            sum_row = conn.execute(
                "SELECT SUM(entry_price * shares) FROM positions "
                "WHERE status='OPEN' AND portfolio_id=?",
                (portfolio_id,)
            ).fetchone()
        else:
            sum_row = conn.execute(
                "SELECT SUM(entry_price * shares) FROM positions WHERE status='OPEN'"
            ).fetchone()
        deployed = float(sum_row[0]) if sum_row and sum_row[0] is not None else 0.0
    finally:
        conn.close()

    return round(max(0.0, capital - deployed), 2)
