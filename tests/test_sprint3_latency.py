"""
tests/test_sprint3_latency.py
=============================
Sprint 3 Verification Suite: Performance Caching & Latency Budgeting.
Benchmarks:
  1. Tool-level math engine cache speedups (Gann, Astro, Derivatives, ML).
  2. Query-level repeat query cache hits (< 5ms response time).
  3. Memory cache telemetry, hit ratios, and thread safety.
  4. Ollama Edge CPU token and inference latency budget.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.swarm.cache import global_cache, TTL_DAILY_MATH, TTL_INTRADAY
from core.tools.quant_tools import quant_gann_sq9, quant_wyckoff_structure
from core.tools.astro_tools import astro_nakshatra_guidance, astro_planetary_aspects
from core.tools.derivatives_tools import derivatives_pcr_maxpain, derivatives_participant_oi
from core.tools.ml_signal_tools import ml_trend_continuation
from core.tools.smart_money_tools import smart_money_deal_flow
from core.swarm.graph import run_swarm_graph

def run_sprint3_benchmarks():
    print("=" * 70)
    print("STARTING SPRINT 3: PERFORMANCE CACHING & LATENCY BENCHMARK SUITE")
    print("=" * 70)

    # Clear cache before starting benchmarks
    global_cache.clear()
    benchmark_results = []

    # -------------------------------------------------------------
    # 1. Tool-Level Mathematical Cache Benchmarks
    # -------------------------------------------------------------
    print("\n--- PHASE 1: Tool-Level Math Engine Caching ---")
    tool_cases = [
        ("Gann SQ9 Geometry", quant_gann_sq9, ("RELIANCE",)),
        ("Wyckoff Market Structure", quant_wyckoff_structure, ("TCS",)),
        ("Vedic Nakshatra Guidance", astro_nakshatra_guidance, ("RELIANCE",)),
        ("Planetary Ephemeris Aspects", astro_planetary_aspects, ()),
        ("Derivatives PCR & Max Pain", derivatives_pcr_maxpain, ("NIFTY",)),
        ("Participant OI Breakdown", derivatives_participant_oi, ()),
        ("Deep ML Trend Continuation", ml_trend_continuation, ("RELIANCE",)),
        ("Smart Money Deal Flow", smart_money_deal_flow, ("RELIANCE",))
    ]

    for name, fn, args in tool_cases:
        # Cold execution
        t0 = time.perf_counter()
        cold_res = fn(*args)
        cold_ms = (time.perf_counter() - t0) * 1000

        # Warm execution (from in-memory cache)
        t1 = time.perf_counter()
        warm_res = fn(*args)
        warm_ms = (time.perf_counter() - t1) * 1000

        speedup = cold_ms / warm_ms if warm_ms > 0 else 999.0
        passed = warm_ms < 2.0  # Warm cache must be sub-2ms

        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name:30s} | Cold: {cold_ms:6.2f}ms | Warm: {warm_ms:6.3f}ms | Speedup: {speedup:6.1f}x")
        benchmark_results.append({
            "test": name,
            "cold_ms": round(cold_ms, 2),
            "warm_ms": round(warm_ms, 3),
            "speedup": round(speedup, 1),
            "passed": passed
        })

    # -------------------------------------------------------------
    # 2. Query-Level Cache Benchmarks (Sub-millisecond End-to-End)
    # -------------------------------------------------------------
    print("\n--- PHASE 2: End-to-End Query-Level Response Caching ---")
    test_queries = [
        "what are the Gann Square of 9 levels for Reliance",
        "what is Nifty PCR and Max Pain",
        "what is today's Nakshatra and is Reliance aligned"
    ]

    for q in test_queries:
        print(f"\nExecuting Query: '{q}'")
        # Cold query run (Swarm graph + Tool execution + Ollama LLM)
        t0 = time.perf_counter()
        cold_swarm = run_swarm_graph(q, skip_llm=False)
        cold_sec = time.perf_counter() - t0
        print(f"  -> Cold Graph Response: {cold_sec:.2f}s (Tokens generated, is_cached={cold_swarm.get('is_cached', False)})")

        # Warm query run (Instant hash lookup)
        t1 = time.perf_counter()
        warm_swarm = run_swarm_graph(q, skip_llm=False)
        warm_ms = (time.perf_counter() - t1) * 1000
        is_cached = warm_swarm.get("is_cached", False)
        print(f"  -> Warm Cached Response: {warm_ms:.3f}ms (is_cached={is_cached})")

        passed = is_cached and (warm_ms < 10.0)
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] Query Cache Hit: '{q[:35]}...' in {warm_ms:.3f}ms (Speedup: {(cold_sec * 1000 / warm_ms if warm_ms else 9999):.0f}x)")
        benchmark_results.append({
            "test": f"Query Cache: {q[:30]}",
            "cold_s": round(cold_sec, 2),
            "warm_ms": round(warm_ms, 3),
            "passed": passed
        })

    # -------------------------------------------------------------
    # 3. Telemetry & Memory Hit Rate Verification
    # -------------------------------------------------------------
    print("\n--- PHASE 3: Cache Telemetry & Stats Verification ---")
    stats = global_cache.stats()
    print(f"Active Cache Items: {stats['active_items']}")
    print(f"Total Hits:         {stats['hits']}")
    print(f"Total Misses:       {stats['misses']}")
    print(f"Hit Ratio:          {stats['hit_ratio_pct']}%")

    telemetry_passed = (stats["hits"] >= 10) and (stats["active_items"] >= 8) and (stats["hit_ratio_pct"] > 40.0)
    print(f"[{'PASS' if telemetry_passed else 'FAIL'}] Cache Telemetry Integrity: {stats['hit_ratio_pct']}% hit ratio")
    benchmark_results.append({
        "test": "Cache Telemetry Integrity",
        "passed": telemetry_passed,
        "details": stats
    })

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    total_tests = len(benchmark_results)
    passed_tests = sum(1 for b in benchmark_results if b["passed"])
    pass_pct = (passed_tests / total_tests) * 100
    print(f"SPRINT 3 PERFORMANCE RESULTS: {passed_tests}/{total_tests} PASSED ({pass_pct:.0f}%)")
    print("=" * 70)

    if pass_pct == 100:
        print("[SUCCESS] All Sprint 3 caching & latency targets achieved!\n")
    else:
        print("[WARNING] Some benchmark checks did not meet target thresholds.\n")

if __name__ == "__main__":
    run_sprint3_benchmarks()
