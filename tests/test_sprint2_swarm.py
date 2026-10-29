"""
tests/test_sprint2_swarm.py
===========================
Sprint 2 Verification Test Suite: Hierarchical LangGraph Multi-Agent Swarm.
Tests dynamic domain routing, parallel subgraphs fan-out, dossier aggregation, and local LLM synthesis.
"""

import os
import sys
import time
import json

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.swarm.graph import run_swarm_graph

SWARM_TESTS = [
    {
        "name": "Derivatives Specialist Subgraph",
        "query": "what is Nifty PCR and Max Pain",
        "expected_domains": ["derivatives_agent"],
        "expected_substrings": ["PCR", "Max Pain"]
    },
    {
        "name": "Participant OI Market-Wide Subgraph",
        "query": "what is today participant OI and FII long ratio",
        "expected_domains": ["derivatives_agent"],
        "expected_substrings": ["FII", "Long"]
    },
    {
        "name": "Quant Gann Specialist Subgraph",
        "query": "what are the Gann Square of 9 levels for Reliance",
        "expected_domains": ["quant_agent"],
        "expected_substrings": ["Gann", "Support", "Resistance"]
    },
    {
        "name": "Quant Wyckoff Specialist Subgraph",
        "query": "what is the Wyckoff phase and accumulation score for TCS",
        "expected_domains": ["quant_agent"],
        "expected_substrings": ["Wyckoff", "Phase"]
    },
    {
        "name": "Deep ML Continuation Subgraph",
        "query": "what does the deep continuation model say about Reliance",
        "expected_domains": ["deep_ml_agent"],
        "expected_substrings": ["Continuation", "Probability"]
    },
    {
        "name": "Vedic Astro Specialist Subgraph",
        "query": "what is today's Nakshatra and is Reliance aligned",
        "expected_domains": ["astro_agent"],
        "expected_substrings": ["Nakshatra", "Rohini"]
    },
    {
        "name": "Fundamental 10Y Audited Subgraph",
        "query": "what is Reliance sales and net profit growth over last 3 years",
        "expected_domains": ["fundamental_agent"],
        "expected_substrings": ["Sales", "Profit"]
    },
    {
        "name": "Multi-Agent Fan-Out Comparison (Quant + ML)",
        "query": "compare Reliance and TCS on Wyckoff phase and deep continuation probability",
        "expected_domains": ["quant_agent", "deep_ml_agent"],
        "expected_substrings": ["Reliance", "TCS"]
    },
    {
        "name": "All 6 Agents Full Swarm Dossier",
        "query": "give me a full quant dossier on Reliance",
        "expected_domains": ["derivatives_agent", "quant_agent", "deep_ml_agent", "astro_agent", "fundamental_agent", "ohlc_agent"],
        "expected_substrings": ["Reliance", "Rs."]
    },
    {
        "name": "Guardrail Domain Filter",
        "query": "how to make chocolate cake",
        "expected_domains": [],
        "expected_substrings": ["cannot assist", "Vprofitables"]
    }
]

def run_swarm_verification():
    print("=" * 70, flush=True)
    print("STARTING SPRINT 2: HIERARCHICAL MULTI-AGENT SWARM VERIFICATION", flush=True)
    print("=" * 70, flush=True)

    passed_count = 0
    results = []

    for i, t in enumerate(SWARM_TESTS, 1):
        name = t["name"]
        q = t["query"]
        expected_doms = t["expected_domains"]
        expected_subs = t["expected_substrings"]

        t0 = time.perf_counter()
        res = run_swarm_graph(q, skip_llm=False)
        elapsed_s = round(time.perf_counter() - t0, 2)

        actual_doms = res.get("domains") or []
        resp = res.get("final_response") or ""
        tool_results = res.get("tool_results") or []

        # Verify domains
        dom_match = all(d in actual_doms for d in expected_doms) if expected_doms else (len(actual_doms) == 0)
        # Verify response text
        sub_match = all(s.lower() in resp.lower() for s in expected_subs)

        passed = dom_match and sub_match

        if passed:
            passed_count += 1
            status = "[PASS]"
        else:
            status = "[FAIL]"

        print(f"\n{status} Test {i}/10 [{name}] ({elapsed_s}s)", flush=True)
        print(f"       Query: '{q}'", flush=True)
        print(f"       Routed Domains: {actual_doms} (Expected: {expected_doms})", flush=True)
        print(f"       Tool Results Collected: {len(tool_results)} results", flush=True)
        print(f"       Response Snippet: {resp[:120]}...", flush=True)
        if not passed:
            print(f"       FAILURE DETAILS: dom_match={dom_match}, sub_match={sub_match}", flush=True)
            if not sub_match:
                print(f"       Missing substrings: {[s for s in expected_subs if s.lower() not in resp.lower()]}", flush=True)

        results.append({
            "test_num": i,
            "name": name,
            "query": q,
            "passed": passed,
            "domains": actual_doms,
            "tool_results_count": len(tool_results),
            "elapsed_s": elapsed_s,
            "response_preview": resp[:200]
        })

    print("\n" + "=" * 70, flush=True)
    print(f"SPRINT 2 SWARM RESULTS: {passed_count}/{len(SWARM_TESTS)} PASSED ({passed_count/len(SWARM_TESTS)*100:.0f}%)", flush=True)
    print("=" * 70, flush=True)

    with open("tests/swarm_sprint2_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_swarm_verification()
