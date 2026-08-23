"""
volume_profile.py — GANN-ASTRO v4.0
=====================================
PURPOSE: Build structural price levels from historical volume distribution.

WHAT IT DOES:
  Divides the price range into N bins and sums the volume traded at each
  price bin over the lookback period. This creates a Volume Profile.

KEY LEVELS PRODUCED:
  VPOC  — Volume Point of Control: price bin with the MOST volume traded.
          This is the magnetic centre of price — price returns to VPOC
          during consolidation. Strong S/R when price is away from it.

  HVN   — High Volume Nodes: price clusters with above-average volume.
          These are areas of past agreement between buyers and sellers.
          Price tends to SLOW DOWN at HVNs — they act as S/R.

  LVN   — Low Volume Nodes: price gaps with below-average volume.
          These are areas of past disagreement. Price tends to MOVE
          QUICKLY through LVNs — thin air between two price structures.

  VAH   — Value Area High: upper boundary of the 70% value area.
  VAL   — Value Area Low: lower boundary of the 70% value area.

HOW USED IN REVERSAL ZONE:
  reversal_map.py calls get_vpoc_levels() for each symbol and checks
  whether a Sq9 level / Gann cycle zone coincides with a VPOC or HVN.
  Coincidence = stronger zone (adds +1 signal to the zone count).

INTEGRATION:
  from core.volume_profile import get_vpoc_levels, VolumeProfile
  vp = get_vpoc_levels(symbol, closes, volumes)
  # vp.vpoc, vp.hvn_levels, vp.lvn_levels, vp.vah, vp.val
"""

import sqlite3
import os
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(os.path.dirname(BASE_DIR), "market_data_v2.db")


@dataclass
class VolumeProfile:
    symbol:     str
    vpoc:       float          # price with highest volume
    vah:        float          # value area high (70% of volume above this + vpoc)
    val:        float          # value area low  (70% of volume below this + vpoc)
    hvn_levels: List[float] = field(default_factory=list)   # high volume nodes
    lvn_levels: List[float] = field(default_factory=list)   # low volume nodes
    lookback_days: int = 252
    bins:       int = 50


def build_volume_profile(
    closes:  List[float],
    volumes: List[float],
    bins:    int = 50,
    value_area_pct: float = 0.70,
) -> Optional[VolumeProfile]:
    """
    Build a volume profile from close prices and volumes.

    Args:
        closes:          list of close prices (most recent last)
        volumes:         list of volumes matching closes
        bins:            number of price buckets (default 50)
        value_area_pct:  fraction of total volume defining value area (default 0.70)

    Returns:
        VolumeProfile or None if insufficient data.
    """
    if len(closes) < 20 or len(volumes) < 20:
        return None

    lo = min(closes)
    hi = max(closes)
    if hi <= lo:
        return None

    # Build price bins
    bin_size  = (hi - lo) / bins
    hist      = [0.0] * bins

    for c, v in zip(closes, volumes):
        b = min(int((c - lo) / bin_size), bins - 1)
        hist[b] += v

    total_vol = sum(hist)
    if total_vol <= 0:
        return None

    # VPOC — bin with highest volume
    vpoc_bin   = hist.index(max(hist))
    vpoc_price = round(lo + vpoc_bin * bin_size + bin_size / 2, 2)

    # Value Area — 70% of total volume centred on VPOC
    # Expand outward from VPOC until we capture value_area_pct of volume
    val_vol = hist[vpoc_bin]
    lo_idx  = vpoc_bin
    hi_idx  = vpoc_bin

    while val_vol / total_vol < value_area_pct:
        lo_candidate = hist[lo_idx - 1] if lo_idx > 0          else 0
        hi_candidate = hist[hi_idx + 1] if hi_idx < bins - 1   else 0
        if lo_candidate == 0 and hi_candidate == 0:
            break
        if hi_candidate >= lo_candidate:
            hi_idx += 1
            val_vol += hi_candidate
        else:
            lo_idx -= 1
            val_vol += lo_candidate

    vah = round(lo + hi_idx * bin_size + bin_size, 2)
    val = round(lo + lo_idx * bin_size, 2)

    # HVN — bins with volume > 1.3× average
    avg_vol   = total_vol / bins
    hvn_levels = sorted(set(
        round(lo + i * bin_size + bin_size / 2, 2)
        for i, v in enumerate(hist)
        if v > avg_vol * 1.30
    ))

    # LVN — bins with volume < 0.4× average and not at extremes
    lvn_levels = sorted(set(
        round(lo + i * bin_size + bin_size / 2, 2)
        for i, v in enumerate(hist)
        if v < avg_vol * 0.40 and 2 <= i <= bins - 3
    ))

    return VolumeProfile(
        symbol="",
        vpoc=vpoc_price,
        vah=vah,
        val=val,
        hvn_levels=hvn_levels,
        lvn_levels=lvn_levels,
        bins=bins,
    )


def get_vpoc_levels(
    symbol:       str,
    closes:       Optional[List[float]] = None,
    volumes:      Optional[List[float]] = None,
    lookback_days: int = 252,
    bins:          int = 50,
) -> Optional[VolumeProfile]:
    """
    Main entry point. Builds volume profile for a symbol.

    If closes/volumes are supplied, uses those directly.
    Otherwise fetches from DB (market_data_v2.db daily_prices table).

    Returns VolumeProfile or None.
    """
    # Use supplied data if available
    if closes and volumes and len(closes) >= 20:
        vp = build_volume_profile(closes[-lookback_days:], volumes[-lookback_days:], bins)
        if vp:
            vp.symbol = symbol
            vp.lookback_days = lookback_days
        return vp

    # Fetch from DB
    if not os.path.exists(DB_PATH):
        return None

    try:
        cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()
        conn   = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        rows   = conn.execute("""
            SELECT close, volume FROM daily_prices
            WHERE symbol=? AND close IS NOT NULL AND trade_date >= ?
            ORDER BY trade_date ASC
        """, (symbol, cutoff)).fetchall()
        conn.close()

        if len(rows) < 20:
            return None

        closes_db  = [float(r[0]) for r in rows]
        volumes_db = [float(r[1] or 0) for r in rows]
        vp = build_volume_profile(closes_db, volumes_db, bins)
        if vp:
            vp.symbol = symbol
            vp.lookback_days = lookback_days
        return vp

    except Exception:
        return None


def is_near_vpoc(price: float, vp: VolumeProfile, tolerance: float = 0.015) -> bool:
    """Returns True if price is within tolerance% of VPOC."""
    return abs(price - vp.vpoc) / max(vp.vpoc, 0.01) <= tolerance


def nearest_hvn(price: float, vp: VolumeProfile) -> Optional[float]:
    """Returns the nearest HVN level to the given price, or None."""
    if not vp.hvn_levels:
        return None
    return min(vp.hvn_levels, key=lambda h: abs(h - price))


def is_in_value_area(price: float, vp: VolumeProfile) -> bool:
    """Returns True if price is within the 70% value area."""
    return vp.val <= price <= vp.vah


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import random
    random.seed(42)
    # Simulate 300 bars with volume cluster around 500
    closes  = [480 + 40 * (i % 7) / 7 for i in range(300)]
    volumes = [100_000 + (50_000 if 490 <= closes[i] <= 510 else 0)
               + random.randint(-10_000, 10_000) for i in range(300)]

    vp = build_volume_profile(closes, volumes, bins=30)
    print(f"VPOC : {vp.vpoc}")
    print(f"VAH  : {vp.vah}")
    print(f"VAL  : {vp.val}")
    print(f"HVN  : {vp.hvn_levels}")
    print(f"LVN  : {vp.lvn_levels[:5]}")
    assert 490 <= vp.vpoc <= 515, f"VPOC should be near 500 cluster, got {vp.vpoc}"
    print("PASSED")