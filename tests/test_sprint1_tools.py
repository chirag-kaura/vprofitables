"""
tests/test_sprint1_tools.py
===========================
Verification test suite for Sprint 1 Unified Tool Adapters.
Tests Derivatives, Smart Money, Quant/Gann, Wyckoff, Astro/Nakshatra, and Deep ML tools.
"""

import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tools.contracts import ToolResult
from core.tools.derivatives_tools import derivatives_pcr_maxpain, derivatives_participant_oi
from core.tools.smart_money_tools import smart_money_deal_flow
from core.tools.quant_tools import quant_gann_sq9, quant_wyckoff_structure
from core.tools.astro_tools import astro_nakshatra_guidance, astro_planetary_aspects
from core.tools.ml_signal_tools import ml_trend_continuation, ml_deep_reversal_score

def test_all_tools():
    print("=" * 60)
    print("STARTING SPRINT 1 TOOL ADAPTER VERIFICATION")
    print("=" * 60)

    test_cases = [
        ("Derivatives PCR & Max Pain", lambda: derivatives_pcr_maxpain("NIFTY")),
        ("Derivatives Participant OI", lambda: derivatives_participant_oi()),
        ("Smart Money Bulk Deals (Reliance)", lambda: smart_money_deal_flow("RELIANCE", limit=4)),
        ("Smart Money Deals (Market-wide)", lambda: smart_money_deal_flow(None, limit=3)),
        ("Quant Gann Square of 9 (Reliance)", lambda: quant_gann_sq9("RELIANCE")),
        ("Quant Wyckoff Structure (TCS)", lambda: quant_wyckoff_structure("TCS")),
        ("Astro Nakshatra Guidance (Reliance)", lambda: astro_nakshatra_guidance("RELIANCE")),
        ("Astro Planetary Aspects", lambda: astro_planetary_aspects()),
        ("Deep ML Trend Continuation (Reliance)", lambda: ml_trend_continuation("RELIANCE")),
        ("Deep ML Reversal Score (Reliance)", lambda: ml_deep_reversal_score("RELIANCE")),
    ]

    all_passed = True
    for name, tool_fn in test_cases:
        t0 = time.perf_counter()
        try:
            res: ToolResult = tool_fn()
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            assert isinstance(res, ToolResult), f"Expected ToolResult instance, got {type(res)}"
            assert res.domain, "Missing domain"
            assert res.headline_metric, "Missing headline_metric"
            assert res.tabular_summary, "Missing tabular_summary"
            assert isinstance(res.raw_data, dict), "raw_data must be dict"

            md_output = res.to_markdown()
            assert len(md_output) > 20, "Markdown rendering too short"

            print(f" [PASS] {name} ({elapsed_ms}ms)")
            print(f"        Domain: {res.domain} | Symbol: {res.symbol}")
            print(f"        Headline: {res.headline_metric[:80]}...")
        except Exception as e:
            all_passed = False
            print(f" [FAIL] {name}: {e}")

    print("=" * 60)
    if all_passed:
        print(" SPRINT 1 VERIFICATION COMPLETE: ALL 10 TOOLS PASSED PERFECTLY!")
    else:
        print(" SPRINT 1 VERIFICATION HAD FAILURES.")
    print("=" * 60)

if __name__ == "__main__":
    test_all_tools()
