"""
tests/test_unified_terminal_graph.py
====================================
End-to-end verification of the Unified Multi-Domain LangGraph pipeline.
Validates queries across:
  1. Derivatives (PCR, Max Pain)
  2. Participant OI (FII Index Futures)
  3. Smart Money Deals (Institutional Bulk/Block Deals)
  4. Quant Gann (Square of 9 Geometry)
  5. Quant Wyckoff (Accumulation/Distribution Phase & Squeeze)
  6. Astro Nakshatra (Vedic Timing & Alignment)
  7. Deep ML Predictive Signals (PyTorch Continuation MLP)
  8. Cross-Domain Multi-Stock Comparison
  9. Comprehensive Quant Dossier
  10. Guardrail (Off-topic)
"""

import os
import sys
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
import time
import json

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ohlc_rag.graph import run_ohlc_graph

TEST_QUERIES = [
    {
        "domain": "Derivatives",
        "query": "what is Nifty PCR and Max Pain",
        "expected_substrings": ["PCR", "Max Pain"]
    },
    {
        "domain": "Participant OI",
        "query": "what is today participant OI and FII long ratio",
        "expected_substrings": ["FII", "Long"]
    },
    {
        "domain": "Smart Money Deals",
        "query": "show me bulk deals in Reliance",
        "expected_substrings": ["Reliance", "Deal"]
    },
    {
        "domain": "Quant Gann Sq9",
        "query": "what are the Gann Square of 9 levels for Reliance",
        "expected_substrings": ["Gann", "Support", "Resistance"]
    },
    {
        "domain": "Quant Wyckoff",
        "query": "what is the Wyckoff phase and accumulation score for TCS",
        "expected_substrings": ["Wyckoff", "Phase"]
    },
    {
        "domain": "Astro Nakshatra",
        "query": "what is today's Nakshatra and is Reliance aligned",
        "expected_substrings": ["Nakshatra", "Rahu Kaal"]
    },
    {
        "domain": "Deep ML Continuation",
        "query": "what does the deep continuation model say about Reliance",
        "expected_substrings": ["Continuation", "Probability"]
    },
    {
        "domain": "Multi-Stock Quant Comparison",
        "query": "compare Reliance and TCS on Wyckoff phase and deep continuation probability",
        "expected_substrings": ["Reliance", "TCS"]
    },
    {
        "domain": "Comprehensive Dossier",
        "query": "give me a full quant dossier on Reliance",
        "expected_substrings": ["Reliance", "Rs."]
    },
    {
        "domain": "Guardrail Off-Topic",
        "query": "how to make chocolate cake",
        "expected_substrings": ["cannot assist", "Vprofitables"]
    }
]

def run_tests():
    print("=" * 70)
    print("RUNNING UNIFIED MULTI-DOMAIN TERMINAL GRAPH VERIFICATION")
    print("=" * 70)

    results = []
    total_passed = 0

    for i, t in enumerate(TEST_QUERIES, 1):
        q = t["query"]
        dom = t["domain"]
        expected = t["expected_substrings"]

        t0 = time.perf_counter()
        # Use skip_llm=True for fast deterministic graph verification, then test LLM synthesis
        out = run_ohlc_graph(q, skip_llm=False)
        elapsed_s = round(time.perf_counter() - t0, 2)

        resp = out.get("final_response", "")
        intent = out.get("intent", "")
        sub_ints = out.get("sub_intents", [])

        # Check expected substrings (case-insensitive)
        matched = [sub for sub in expected if sub.lower() in resp.lower()]
        passed = len(matched) == len(expected)

        if passed:
            total_passed += 1
            status = "[PASS]"
        else:
            status = "[FAIL]"

        print(f"\n{status} Test {i}/10 [{dom}] ({elapsed_s}s)", flush=True)
        print(f"       Query: '{q}'", flush=True)
        print(f"       Intent: {intent} | Sub-Intents: {sub_ints}", flush=True)
        print(f"       Response Preview: {resp[:120]}...", flush=True)
        if not passed:
            print(f"       MISSING EXPECTED: {[s for s in expected if s not in matched]}", flush=True)

        results.append({
            "test_num": i,
            "domain": dom,
            "query": q,
            "passed": passed,
            "elapsed_s": elapsed_s,
            "response_preview": resp[:200]
        })

    print("\n" + "=" * 70)
    print(f"SUMMARY: {total_passed}/{len(TEST_QUERIES)} TESTS PASSED ({total_passed/len(TEST_QUERIES)*100:.0f}%)")
    print("=" * 70)

    with open("tests/unified_graph_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_tests()
