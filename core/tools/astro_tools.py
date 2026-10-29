"""
core/tools/astro_tools.py
========================
Celestial & Astro Timing Tool Adapter.
Integrates Vedic Nakshatra trading astrology, Rahu Kaal / Abhijit Muhurat timing windows,
and western planetary aspects / stationing retrograde cycles.
"""

import time
from datetime import date
from typing import Optional, Dict, Any, List
from core.tools.contracts import ToolResult
from core.nakshatra_engine import get_current_nakshatra, compute_nakshatra_alignment
from core.aspects import detect_aspects, detect_stations
from core.swarm.cache import ttl_cached, TTL_DAILY_MATH

@ttl_cached(ttl=TTL_DAILY_MATH, namespace="astro_nakshatra")
def astro_nakshatra_guidance(symbol: Optional[str] = "NIFTY") -> ToolResult:
    """
    Get Vedic Nakshatra timing guidance, Lordship, Guna, favored sectors,
    inauspicious Rahu Kaal periods, auspicious Abhijit Muhurat, and stock alignment score.
    """
    t0 = time.perf_counter()
    today = date.today()
    sym = (symbol or "NIFTY").upper().strip()

    try:
        # 1. Base Nakshatra of the day
        nak_info = get_current_nakshatra(today)
        nak_name = nak_info.get("name", "Unknown")
        lord = nak_info.get("ruler", "Unknown")
        guna = nak_info.get("guna", "Unknown")
        behavior = nak_info.get("behavior", "Unknown")
        fav_sec = nak_info.get("fav_sectors", "General")
        rahu = nak_info.get("rahu_kaal", "None")
        abhijit = nak_info.get("abhijit_muhurat", "11:30-12:00")
        trade_style = nak_info.get("trade_style", "Normal")
        caution = nak_info.get("caution", "None")

        # 2. Stock Alignment
        alignment = compute_nakshatra_alignment(sym, today)
        align_score = alignment.get("alignment_score", 50)
        verdict = alignment.get("verdict", "NEUTRAL")
        action = alignment.get("action", "HOLD")

        headline = f"Today's Nakshatra: {nak_name} (Lord: {lord}, {guna}) | Alignment for {sym}: {align_score}/100 ({verdict})"

        table_lines = [
            "| Timing Dimension | Astrological State | Quantitative Guidance |",
            "| :--- | :--- | :--- |",
            f"| **Current Nakshatra** | **{nak_name} (Pada {nak_info.get('pada', 1)})** | Nature: {behavior} |",
            f"| **Planetary Ruler (Lord)** | {lord} | Dominant elemental vibration |",
            f"| **Guna / Energy Mode** | {guna} | Recommended Style: {trade_style} |",
            f"| **Favored Sectors** | {fav_sec} | Astrologically aligned sectors today |",
            f"| **Alignment Score ({sym})**| **{align_score} / 100 ({verdict})** | Action guidance: **{action}** |",
            f"| **Inauspicious Rahu Kaal** | {rahu} IST | High volatility whipsaw risk window |",
            f"| **Auspicious Abhijit Muhurat** | {abhijit} IST | Optimal execution entry window |",
            f"| **Astro Caution Note** | {caution} | Risk discipline |"
        ]

        raw = {
            "date": today.isoformat(),
            "symbol": sym,
            "nakshatra": nak_name,
            "lord": lord,
            "guna": guna,
            "alignment_score": align_score,
            "verdict": verdict,
            "action": action,
            "rahu_kaal": rahu,
            "abhijit_muhurat": abhijit
        }

        return ToolResult(
            domain="ASTRO",
            symbol=sym,
            headline_metric=headline,
            tabular_summary="\n".join(table_lines),
            raw_data=raw,
            execution_ms=int((time.perf_counter() - t0) * 1000)
        )
    except Exception as e:
        return ToolResult(
            domain="ASTRO",
            symbol=sym,
            headline_metric=f"Error evaluating Nakshatra for {sym}",
            tabular_summary=f"> Execution error: {e}",
            execution_ms=int((time.perf_counter() - t0) * 1000),
            error=str(e)
        )

@ttl_cached(ttl=TTL_DAILY_MATH, namespace="astro_aspects")
def astro_planetary_aspects() -> ToolResult:
    """
    Detect major planetary aspects, harmonic angles (conjunctions, oppositions, trines, squares),
    and planetary stations (retrograde turning points).
    """
    t0 = time.perf_counter()
    today = date.today()

    try:
        aspects = detect_aspects(today, orb_override=3.0)
        stations = detect_stations(today, days_window=7)

        active_aspects_desc = []
        table_lines = [
            "| Planet A | Aspect | Planet B | Exact Orb | Nature / Market Consequence |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ]

        for asp in aspects[:6]:
            nature = "Harmonious (Expansion)" if asp.aspect_name in ("Trine", "Sextile") else ("Stressful (Volatility Spike)" if asp.aspect_name in ("Square", "Opposition") else "Potent Conjunction")
            table_lines.append(f"| {asp.planet_a} | **{asp.aspect_name} ({asp.angle:.1f} deg)** | {asp.planet_b} | {asp.orb:.2f} deg orb | {nature} |")
            active_aspects_desc.append(f"{asp.planet_a} {asp.aspect_name} {asp.planet_b}")

        if not aspects:
            table_lines.append("| None | No tight orbs (<3.0 deg) | None | 0.00 | Neutral planetary background |")

        station_notes = [f"{s.get('planet')} stationary {s.get('station_type')} on {s.get('date')}" for s in stations]
        station_str = ", ".join(station_notes) if station_notes else "No major planetary stations within 7 days"

        headline = f"Active Aspects: {len(aspects)} within 3 deg orb | Stations: {station_str}"

        raw = {
            "date": today.isoformat(),
            "aspects_count": len(aspects),
            "aspects": [f"{a.planet_a} {a.aspect_name} {a.planet_b} (orb {a.orb:.2f})" for a in aspects],
            "stations": stations
        }

        return ToolResult(
            domain="ASTRO",
            symbol="CELESTIAL",
            headline_metric=headline,
            tabular_summary="\n".join(table_lines),
            raw_data=raw,
            execution_ms=int((time.perf_counter() - t0) * 1000)
        )
    except Exception as e:
        return ToolResult(
            domain="ASTRO",
            headline_metric="Error computing planetary aspects",
            tabular_summary=f"> Execution error: {e}",
            execution_ms=int((time.perf_counter() - t0) * 1000),
            error=str(e)
        )
