"""
tests/test_financials_judge.py
==============================
LLM-as-a-Judge Benchmark Evaluation for 3rd Data Source (Audited 10Y Financials,
Balance Sheets, Shareholding, and Multi-Domain Queries).
Evaluates accuracy, completeness, latency, and boundary handling across 25 diverse
and adversarial test scenarios.
"""

import os
import sys
import json
import time
import sqlite3
import pandas as pd
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ohlc_rag.graph import run_ohlc_graph
from core.ohlc_rag.chunker import DB_PATH


# 25 Diverse, Multi-Domain & Adversarial Test Scenarios
FINANCIALS_TEST_SCENARIOS = [
    # Group 1: Audited P&L, Sales & Net Profit CAGR (1-4)
    {"id": 1, "group": "P&L / Growth", "q": "What is Reliance 3-year sales and net profit growth in crores?", "symbol": "RELIANCE", "expected_tools": ["financials_growth"]},
    {"id": 2, "group": "P&L / Growth", "q": "Show me TCS annual revenue, operating profit margin, and PAT over the last 5 years.", "symbol": "TCS", "expected_tools": ["financials_growth"]},
    {"id": 3, "group": "P&L / Growth", "q": "What is Infosys operating margin (OPM%) trend in recent audited years?", "symbol": "INFY", "expected_tools": ["financials_growth"]},
    {"id": 4, "group": "P&L / Growth", "q": "How has Bharti Airtel revenue grown over the past 3 fiscal years?", "symbol": "BHARTIARTL", "expected_tools": ["financials_growth"]},

    # Group 2: Balance Sheet Solvency & Debt-to-Equity (5-8)
    {"id": 5, "group": "Balance Sheet", "q": "What are the total borrowings, cash balances, and debt-to-equity ratio of Tata Motors?", "symbol": "TATAMOTORS", "expected_tools": ["financials_balance_sheet"]},
    {"id": 6, "group": "Balance Sheet", "q": "Is TCS debt-free? Check its borrowings and net worth.", "symbol": "TCS", "expected_tools": ["financials_balance_sheet"]},
    {"id": 7, "group": "Balance Sheet", "q": "What is Reliance total debt and operating cash flow as of the latest balance sheet?", "symbol": "RELIANCE", "expected_tools": ["financials_balance_sheet"]},
    {"id": 8, "group": "Balance Sheet", "q": "Check Wipro balance sheet reserves, cash, and leverage solvency.", "symbol": "WIPRO", "expected_tools": ["financials_balance_sheet"]},

    # Group 3: Institutional Shareholding Trajectory (9-12)
    {"id": 9, "group": "Shareholding", "q": "Did FIIs or DIIs increase their stake in HDFC Bank over the last 4 quarters?", "symbol": "HDFCBANK", "expected_tools": ["financials_shareholding"]},
    {"id": 10, "group": "Shareholding", "q": "What is the promoter holding and pledged percentage in TCS?", "symbol": "TCS", "expected_tools": ["financials_shareholding"]},
    {"id": 11, "group": "Shareholding", "q": "Show quarterly institutional shareholding breakdown for State Bank of India.", "symbol": "SBIN", "expected_tools": ["financials_shareholding"]},
    {"id": 12, "group": "Shareholding", "q": "What is the foreign institutional ownership (FII%) in Kotak Bank?", "symbol": "KOTAKBANK", "expected_tools": ["financials_shareholding"]},

    # Group 4: Banking Asset Quality & NPAs (13-16)
    {"id": 13, "group": "Asset Quality", "q": "What are the Gross NPA and Net NPA trends for State Bank of India?", "symbol": "SBIN", "expected_tools": ["financials_banking"]},
    {"id": 14, "group": "Asset Quality", "q": "Show me HDFC Bank financing profit and asset quality over recent years.", "symbol": "HDFCBANK", "expected_tools": ["financials_banking"]},
    {"id": 15, "group": "Asset Quality", "q": "What are the bad loans and NPA percentages for Kotak Bank?", "symbol": "KOTAKBANK", "expected_tools": ["financials_banking"]},
    {"id": 16, "group": "Asset Quality", "q": "What is ICICI Bank gross NPA percentage?", "symbol": "ICICIBANK", "expected_tools": ["financials_banking"]},

    # Group 5: Negative & Boundary Edge Cases (17-20)
    {"id": 17, "group": "Boundary/Edge", "q": "What is the Gross NPA percentage of TCS?", "symbol": "TCS", "expected_boundary": "NPA not applicable to non-bank"},
    {"id": 18, "group": "Boundary/Edge", "q": "Show me the audited financials and balance sheet of Flipkart.", "symbol": None, "expected_boundary": "Unlisted/Private entity"},
    {"id": 19, "group": "Boundary/Edge", "q": "What is the debt-to-equity ratio of OpenAI?", "symbol": None, "expected_boundary": "Foreign/Unlisted"},
    {"id": 20, "group": "Boundary/Edge", "q": "What is the bad loan NPA percentage of Reliance Industries?", "symbol": "RELIANCE", "expected_boundary": "NPA not applicable to non-bank"},

    # Group 6: Triple-Domain Multi-Layered Inquiries (21-23)
    {"id": 21, "group": "Triple-Domain", "q": "Give me Reliance 52-week low distance, latest news sentiment, and 3-year revenue CAGR.", "symbol": "RELIANCE", "expected_tools": ["stats", "sentiment", "financials_growth"]},
    {"id": 22, "group": "Triple-Domain", "q": "What is TCS current close price, recent news headlines, and balance sheet debt-to-equity?", "symbol": "TCS", "expected_tools": ["quote", "news", "financials_balance_sheet"]},
    {"id": 23, "group": "Triple-Domain", "q": "Compare HDFC Bank and Kotak Bank 5-day return and their FII shareholding stakes.", "symbol": "HDFCBANK", "expected_tools": ["comparison", "financials_shareholding"]},

    # Group 7: Head-to-Head Financial Comparisons (24-25)
    {"id": 24, "group": "Comparison", "q": "Compare TCS and Infosys annual sales and net profit growth.", "symbol": "TCS", "expected_tools": ["comparison", "financials_growth"]},
    {"id": 25, "group": "Comparison", "q": "Which bank has higher foreign investment stake: HDFC Bank or SBI?", "symbol": "HDFCBANK", "expected_tools": ["financials_shareholding"]}
]


def run_judge_evaluation(scenario: Dict[str, Any], agent_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Automated Judge that grades the response across:
      1. Grounding & Zero-Hallucination (0-10)
      2. Tool & Sub-Intent Completeness (0-10)
      3. Boundary & Non-Applicability Handling (0-10)
    """
    q_id = scenario["id"]
    group = scenario["group"]
    query = scenario["q"]
    reply = agent_result.get("final_response", "")
    tool_outs = "\n".join(agent_result.get("tool_outputs", []))
    sub_ints = agent_result.get("sub_intents", [])
    sym = agent_result.get("symbol")

    # Metric 1: Grounding Score
    grounding_score = 10
    grounding_notes = []
    if "$" in reply or "CME" in reply or "ICE" in reply:
        grounding_score -= 6
        grounding_notes.append("Hallucinated US dollars or foreign exchanges.")
    if "Cr" not in reply and "Crores" not in reply and "N/A" not in reply and group in ("P&L / Growth", "Balance Sheet"):
        grounding_score -= 3
        grounding_notes.append("Failed to quote financial metrics in verified ₹ Crores.")

    # Metric 2: Completeness Score
    completeness_score = 10
    completeness_notes = []
    exp_tools = scenario.get("expected_tools", [])
    for et in exp_tools:
        if et not in sub_ints and et not in tool_outs:
            completeness_score -= 4
            completeness_notes.append(f"Missing expected data tool/intent: '{et}'.")

    # Metric 3: Boundary & Edge Handling
    boundary_score = 10
    boundary_notes = []
    exp_bound = scenario.get("expected_boundary")
    if exp_bound:
        if "not applicable" in reply.lower() or "unlisted" in reply.lower() or "could not locate" in reply.lower() or "not traded" in reply.lower():
            boundary_score = 10
            boundary_notes.append("Correctly recognized boundary constraint.")
        else:
            boundary_score -= 6
            boundary_notes.append(f"Failed to handle boundary: expected '{exp_bound}'.")

    overall_score = round((grounding_score * 0.4) + (completeness_score * 0.4) + (boundary_score * 0.2), 1)
    passed = overall_score >= 7.0 and len(completeness_notes) == 0

    return {
        "id": q_id,
        "group": group,
        "query": query,
        "symbol": sym,
        "overall_score": overall_score,
        "grounding_score": grounding_score,
        "completeness_score": completeness_score,
        "boundary_score": boundary_score,
        "passed": passed,
        "issues": grounding_notes + completeness_notes + boundary_notes,
        "reply_preview": reply[:250].replace("\n", " ")
    }


def execute_financials_benchmark(fast_mode: bool = True):
    print("=" * 80)
    print("STARTING 3RD DATA SOURCE (10Y FINANCIALS) LLM-AS-A-JUDGE BENCHMARK")
    print(f"Total Scenarios: {len(FINANCIALS_TEST_SCENARIOS)} | Fast Mode: {fast_mode}")
    print("=" * 80)

    results = []
    failed_cases = []
    t_start = time.time()

    for sc in FINANCIALS_TEST_SCENARIOS:
        q = sc["q"]
        print(f"[{sc['id']:02d}/25] Testing: '{q[:45]}...' ({sc['group']})", end=" ... ")
        sys.stdout.flush()

        try:
            t0 = time.time()
            st = run_ohlc_graph(q, skip_llm=fast_mode)
            dur = round(time.time() - t0, 2)
            eval_res = run_judge_evaluation(sc, st)
            eval_res["duration_s"] = dur
            results.append(eval_res)

            if eval_res["passed"]:
                print(f"PASS (Score: {eval_res['overall_score']}/10 in {dur}s)")
            else:
                print(f"FAIL (Score: {eval_res['overall_score']}/10) -> {eval_res['issues'][0] if eval_res['issues'] else 'Low score'}")
                failed_cases.append(eval_res)
        except Exception as e:
            print(f"EXCEPTION -> {e}")
            failed_cases.append({
                "id": sc["id"],
                "group": sc["group"],
                "query": q,
                "passed": False,
                "overall_score": 0.0,
                "issues": [f"Exception: {str(e)}"]
            })

    total_time = round(time.time() - t_start, 1)
    pass_cnt = len(results) - len(failed_cases)
    fail_cnt = len(failed_cases)
    avg_score = round(sum(r.get("overall_score", 0) for r in results) / len(results), 1) if results else 0

    print("\n" + "=" * 80)
    print(f"BENCHMARK COMPLETED in {total_time}s")
    print(f"Passed: {pass_cnt}/{len(FINANCIALS_TEST_SCENARIOS)} | Failed: {fail_cnt} | Avg Judge Score: {avg_score}/10")
    print("=" * 80)

    # Save Judge results report
    out_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "financials_judge_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "total": len(FINANCIALS_TEST_SCENARIOS),
            "passed": pass_cnt,
            "failed": fail_cnt,
            "avg_score": avg_score,
            "failures": failed_cases,
            "all_results": results
        }, f, indent=2)
    print(f"Results saved to {out_file}")

    return results, failed_cases


if __name__ == "__main__":
    execute_financials_benchmark(fast_mode=True)
