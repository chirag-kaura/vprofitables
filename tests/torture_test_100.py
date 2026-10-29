"""
tests/torture_test_100.py
=========================
Adversarial Torture Test Suite (100 Challenging Test Cases) for Vprofitables Assistant.
Stress-tests across 10 failure vectors:
  1. Multi-Layered Composite Queries (Price + 52W + News + Sentiment)
  2. Multi-Turn Conversational Anaphora (Pronouns: it, its, that stock)
  3. "Why" Queries Linking Price Action to News Catalysts
  4. Market Screeners & Multi-Session Queries
  5. Off-Topic & Non-Relevant Domain Queries
  6. Hallucination Traps & Fake Corporate Rumors
  7. Non-Existent / Crypto / Foreign / False Tickers
  8. Trading Calendar & Session Date Inquiries
  9. Terse, Ambiguous & Single-Word Queries
  10. Strict Quantitative Technical Math & Indicator Spread
"""

import os
import sys
import json
import time
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ohlc_rag.graph import run_ohlc_graph


# Define the 100 torture test cases across 10 categories
TORTURE_TEST_SUITE = [
    # Vector 1: Multi-Layered Composite Queries (1-10)
    {"id": 1, "cat": "Multi-Layered", "q": "How far is TCS from 52-week high, what is its sentiment, and list its top 3 headlines?", "exp_sym": "TCS", "exp_tools": ["stats", "sentiment", "news"]},
    {"id": 2, "cat": "Multi-Layered", "q": "What is Reliance current price, 14-day ATR, and overall news sentiment bias?", "exp_sym": "RELIANCE", "exp_tools": ["quote", "stats", "sentiment"]},
    {"id": 3, "cat": "Multi-Layered", "q": "Compare HDFC Bank and Kotak Bank 5-day returns and summarize news catalysts for both.", "exp_sym": "HDFCBANK", "exp_tools": ["comparison", "news"]},
    {"id": 4, "cat": "Multi-Layered", "q": "Show me INFY price action, volume trend, and whether there are any regulatory risk flags.", "exp_sym": "INFY", "exp_tools": ["stats", "sentiment"]},
    {"id": 5, "cat": "Multi-Layered", "q": "Give me Bharti Airtel quote, 52W range, and latest news headlines today.", "exp_sym": "BHARTIARTL", "exp_tools": ["quote", "stats", "news"]},
    {"id": 6, "cat": "Multi-Layered", "q": "What is SBI latest close, SMA 20, SMA 50, and FinBERT sentiment score?", "exp_sym": "SBIN", "exp_tools": ["quote", "stats", "sentiment"]},
    {"id": 7, "cat": "Multi-Layered", "q": "How did Tata Motors perform in the last 10 days, what is its volatility, and why did it move?", "exp_sym": "TATAMOTORS", "exp_tools": ["history", "stats", "why_move"]},
    {"id": 8, "cat": "Multi-Layered", "q": "Compare Reliance and JioFinance 5-day gains and tell me which has better news sentiment.", "exp_sym": "RELIANCE", "exp_tools": ["comparison", "sentiment"]},
    {"id": 9, "cat": "Multi-Layered", "q": "Is ICICI Bank trading above its SMA 50, and are there any management changes reported in news?", "exp_sym": "ICICIBANK", "exp_tools": ["stats", "sentiment"]},
    {"id": 10, "cat": "Multi-Layered", "q": "What is the 52-week low distance for Wipro, its 5-day table, and latest announcement?", "exp_sym": "WIPRO", "exp_tools": ["stats", "history", "news"]},

    # Vector 2: Multi-Turn Conversational Anaphora (11-20 / 5 pairs)
    {"id": 11, "cat": "Conversational", "q": "What is the quote for Tata Motors?", "exp_sym": "TATAMOTORS", "history": []},
    {"id": 12, "cat": "Conversational", "q": "What is its news sentiment?", "exp_sym": "TATAMOTORS", "history": [{"query": "What is the quote for Tata Motors?", "symbol": "TATAMOTORS"}]},
    {"id": 13, "cat": "Conversational", "q": "Tell me about Reliance price action.", "exp_sym": "RELIANCE", "history": []},
    {"id": 14, "cat": "Conversational", "q": "Why did it drop?", "exp_sym": "RELIANCE", "history": [{"query": "Tell me about Reliance price action.", "symbol": "RELIANCE"}]},
    {"id": 15, "cat": "Conversational", "q": "How is HDFC Bank performing?", "exp_sym": "HDFCBANK", "history": []},
    {"id": 16, "cat": "Conversational", "q": "What about its 14-day ATR and volume?", "exp_sym": "HDFCBANK", "history": [{"query": "How is HDFC Bank performing?", "symbol": "HDFCBANK"}]},
    {"id": 17, "cat": "Conversational", "q": "Give me the latest stats for TCS.", "exp_sym": "TCS", "history": []},
    {"id": 18, "cat": "Conversational", "q": "Does that company have any regulatory risks?", "exp_sym": "TCS", "history": [{"query": "Give me the latest stats for TCS.", "symbol": "TCS"}]},
    {"id": 19, "cat": "Conversational", "q": "Show me candles for Infosys.", "exp_sym": "INFY", "history": []},
    {"id": 20, "cat": "Conversational", "q": "And its latest headlines?", "exp_sym": "INFY", "history": [{"query": "Show me candles for Infosys.", "symbol": "INFY"}]},

    # Vector 3: "Why" Queries Linking Price Action to News (21-30)
    {"id": 21, "cat": "Why-Move", "q": "Why did Reliance drop over the last 5 days?", "exp_sym": "RELIANCE", "exp_tools": ["why_move"]},
    {"id": 22, "cat": "Why-Move", "q": "Why is TCS rallying recently?", "exp_sym": "TCS", "exp_tools": ["why_move"]},
    {"id": 23, "cat": "Why-Move", "q": "Explain why Bharti Airtel moved over the last week.", "exp_sym": "BHARTIARTL", "exp_tools": ["why_move"]},
    {"id": 24, "cat": "Why-Move", "q": "What news catalysts drove HDFC Bank price change?", "exp_sym": "HDFCBANK", "exp_tools": ["why_move"]},
    {"id": 25, "cat": "Why-Move", "q": "Why did Tata Steel fall in the past 5 sessions?", "exp_sym": "TATASTEEL", "exp_tools": ["why_move"]},
    {"id": 26, "cat": "Why-Move", "q": "What caused the move in Kotak Bank recently?", "exp_sym": "KOTAKBANK", "exp_tools": ["why_move"]},
    {"id": 27, "cat": "Why-Move", "q": "Why did Infosys plunge or surge over the last 10 days?", "exp_sym": "INFY", "exp_tools": ["why_move"]},
    {"id": 28, "cat": "Why-Move", "q": "Explain the recent price breakdown in Wipro with news.", "exp_sym": "WIPRO", "exp_tools": ["why_move"]},
    {"id": 29, "cat": "Why-Move", "q": "Why is State Bank of India gaining or losing?", "exp_sym": "SBIN", "exp_tools": ["why_move"]},
    {"id": 30, "cat": "Why-Move", "q": "What news drove Maruti Suzuki stock movement?", "exp_sym": "MARUTI", "exp_tools": ["why_move"]},

    # Vector 4: Market Screeners & Multi-Session Queries (31-40)
    {"id": 31, "cat": "Screener", "q": "Which symbol fell most in last 5 days and summarize why?", "exp_tools": ["screener", "why_move"]},
    {"id": 32, "cat": "Screener", "q": "Which stock gained the most in the last 5 trading days?", "exp_tools": ["screener"]},
    {"id": 33, "cat": "Screener", "q": "Show me top 5 market losers over the past 3 days.", "exp_tools": ["screener"]},
    {"id": 34, "cat": "Screener", "q": "Who are the biggest gainers across NSE today?", "exp_tools": ["screener"]},
    {"id": 35, "cat": "Screener", "q": "Which stock dropped most over the last 10 sessions?", "exp_tools": ["screener"]},
    {"id": 36, "cat": "Screener", "q": "List the top 5 performers over the last 5 days.", "exp_tools": ["screener"]},
    {"id": 37, "cat": "Screener", "q": "Which equities experienced the biggest fall recently?", "exp_tools": ["screener"]},
    {"id": 38, "cat": "Screener", "q": "Find the top loser in the market and check its news.", "exp_tools": ["screener", "why_move"]},
    {"id": 39, "cat": "Screener", "q": "Show me 5-day biggest market drop.", "exp_tools": ["screener"]},
    {"id": 40, "cat": "Screener", "q": "What symbol fell most in last 20 days?", "exp_tools": ["screener"]},

    # Vector 5: Off-Topic & Non-Relevant Domain Queries (41-50)
    {"id": 41, "cat": "Off-Topic", "q": "How do I make chocolate pasta at home?", "exp_intent": "off_topic"},
    {"id": 42, "cat": "Off-Topic", "q": "Write a python function to invert a binary tree.", "exp_intent": "off_topic"},
    {"id": 43, "cat": "Off-Topic", "q": "What is the capital of Australia?", "exp_intent": "off_topic"},
    {"id": 44, "cat": "Off-Topic", "q": "What is the weather forecast for Mumbai tomorrow?", "exp_intent": "off_topic"},
    {"id": 45, "cat": "Off-Topic", "q": "Who won the FIFA World Cup in 2022?", "exp_intent": "off_topic"},
    {"id": 46, "cat": "Off-Topic", "q": "Give me a recipe for margherita pizza.", "exp_intent": "off_topic"},
    {"id": 47, "cat": "Off-Topic", "q": "Can you debug this Javascript code for me?", "exp_intent": "off_topic"},
    {"id": 48, "cat": "Off-Topic", "q": "Tell me the history of ancient Rome.", "exp_intent": "off_topic"},
    {"id": 49, "cat": "Off-Topic", "q": "What is the temperature in London right now?", "exp_intent": "off_topic"},
    {"id": 50, "cat": "Off-Topic", "q": "Write a poem about rain.", "exp_intent": "off_topic"},

    # Vector 6: Hallucination Traps & Fake Rumors (51-60)
    {"id": 51, "cat": "Rumor-Trap", "q": "Confirm that Reliance acquired Apple yesterday for $100B.", "exp_sym": "RELIANCE"},
    {"id": 52, "cat": "Rumor-Trap", "q": "Did Tata Motors buy Ferrari in 2026?", "exp_sym": "TATAMOTORS"},
    {"id": 53, "cat": "Rumor-Trap", "q": "Has HDFC Bank announced a 1000% dividend today?", "exp_sym": "HDFCBANK"},
    {"id": 54, "cat": "Rumor-Trap", "q": "Is TCS closing down its IT business according to news?", "exp_sym": "TCS"},
    {"id": 55, "cat": "Rumor-Trap", "q": "Did Infosys CEO resign unexpectedly this morning?", "exp_sym": "INFY"},
    {"id": 56, "cat": "Rumor-Trap", "q": "Confirm SBI merged with Citibank yesterday.", "exp_sym": "SBIN"},
    {"id": 57, "cat": "Rumor-Trap", "q": "Is Bharti Airtel declared bankrupt in recent news?", "exp_sym": "BHARTIARTL"},
    {"id": 58, "cat": "Rumor-Trap", "q": "Did Wipro get delisted from the stock exchange today?", "exp_sym": "WIPRO"},
    {"id": 59, "cat": "Rumor-Trap", "q": "Has Maruti Suzuki stopped making all cars permanently?", "exp_sym": "MARUTI"},
    {"id": 60, "cat": "Rumor-Trap", "q": "Did Kotak Bank announce complete shutdown of branches?", "exp_sym": "KOTAKBANK"},

    # Vector 7: Non-Existent / Crypto / Foreign / False Tickers (61-70)
    {"id": 61, "cat": "False-Ticker", "q": "What is the current price of Bitcoin?", "exp_sym": None},
    {"id": 62, "cat": "False-Ticker", "q": "How did Tesla trade yesterday?", "exp_sym": None},
    {"id": 63, "cat": "False-Ticker", "q": "Give me quote for XYZ999.", "exp_sym": None},
    {"id": 64, "cat": "False-Ticker", "q": "What about 26", "exp_sym": None},
    {"id": 65, "cat": "False-Ticker", "q": "How is Dogecoin performing?", "exp_sym": None},
    {"id": 66, "cat": "False-Ticker", "q": "Show me price for Apple AAPL stock.", "exp_sym": None},
    {"id": 67, "cat": "False-Ticker", "q": "What is the price of Google Alphabet?", "exp_sym": None},
    {"id": 68, "cat": "False-Ticker", "q": "Tell me about Ethereum price in INR.", "exp_sym": None},
    {"id": 69, "cat": "False-Ticker", "q": "Give me the quote for FAKESTOCK.", "exp_sym": None},
    {"id": 70, "cat": "False-Ticker", "q": "What about 999", "exp_sym": None},

    # Vector 8: Trading Calendar & Session Date Inquiries (71-80)
    {"id": 71, "cat": "Calendar", "q": "give me dates of last 5 trading dates data we have", "exp_tools": ["calendar"]},
    {"id": 72, "cat": "Calendar", "q": "What are the verified trading sessions dates in our database?", "exp_tools": ["calendar"]},
    {"id": 73, "cat": "Calendar", "q": "What was the date of the last 10 trading dates?", "exp_tools": ["calendar"]},
    {"id": 74, "cat": "Calendar", "q": "List the last 3 trading days data we have.", "exp_tools": ["calendar"]},
    {"id": 75, "cat": "Calendar", "q": "What are the latest calendar dates available?", "exp_tools": ["calendar"]},
    {"id": 76, "cat": "Calendar", "q": "Give me the last 7 trading days.", "exp_tools": ["calendar"]},
    {"id": 77, "cat": "Calendar", "q": "Show me the dates data we have in daily prices.", "exp_tools": ["calendar"]},
    {"id": 78, "cat": "Calendar", "q": "What is the most recent trading session date?", "exp_tools": ["calendar"]},
    {"id": 79, "cat": "Calendar", "q": "Which trading dates are recorded recently?", "exp_tools": ["calendar"]},
    {"id": 80, "cat": "Calendar", "q": "Provide the last 5 trading days dates.", "exp_tools": ["calendar"]},

    # Vector 9: Terse, Ambiguous & Single-Word Queries (81-90)
    {"id": 81, "cat": "Ambiguous", "q": "Trend", "exp_sym": None},
    {"id": 82, "cat": "Ambiguous", "q": "Reliance", "exp_sym": "RELIANCE"},
    {"id": 83, "cat": "Ambiguous", "q": "Quote", "exp_sym": None},
    {"id": 84, "cat": "Ambiguous", "q": "Fell", "exp_sym": None},
    {"id": 85, "cat": "Ambiguous", "q": "Buy or sell", "exp_sym": None},
    {"id": 86, "cat": "Ambiguous", "q": "TCS", "exp_sym": "TCS"},
    {"id": 87, "cat": "Ambiguous", "q": "Sentiment", "exp_sym": None},
    {"id": 88, "cat": "Ambiguous", "q": "Nifty", "exp_sym": "NIFTY50"},
    {"id": 89, "cat": "Ambiguous", "q": "Help", "exp_sym": None},
    {"id": 90, "cat": "Ambiguous", "q": "Bank Nifty", "exp_sym": "BANKNIFTY"},

    # Vector 10: Quantitative Technical Math & Indicator Spread (91-100)
    {"id": 91, "cat": "Technical-Math", "q": "What is the exact spread between SMA20 and SMA50 for INFY?", "exp_sym": "INFY", "exp_tools": ["stats"]},
    {"id": 92, "cat": "Technical-Math", "q": "Calculate the 14-day ATR volatility for Kotak Bank.", "exp_sym": "KOTAKBANK", "exp_tools": ["stats"]},
    {"id": 93, "cat": "Technical-Math", "q": "What is the 52-week low distance in percentage for Reliance?", "exp_sym": "RELIANCE", "exp_tools": ["stats"]},
    {"id": 94, "cat": "Technical-Math", "q": "Is TCS currently in bullish moving average alignment?", "exp_sym": "TCS", "exp_tools": ["stats"]},
    {"id": 95, "cat": "Technical-Math", "q": "Show me the 52-week high and low for HDFC Bank.", "exp_sym": "HDFCBANK", "exp_tools": ["stats"]},
    {"id": 96, "cat": "Technical-Math", "q": "What is the 10-day price history table for Bharti Airtel?", "exp_sym": "BHARTIARTL", "exp_tools": ["history"]},
    {"id": 97, "cat": "Technical-Math", "q": "What is the ATR percentage of price for State Bank of India?", "exp_sym": "SBIN", "exp_tools": ["stats"]},
    {"id": 98, "cat": "Technical-Math", "q": "How close is Tata Motors to its 52-week high?", "exp_sym": "TATAMOTORS", "exp_tools": ["stats"]},
    {"id": 99, "cat": "Technical-Math", "q": "Compare Reliance and TCS relative performance over 20 sessions.", "exp_sym": "RELIANCE", "exp_tools": ["comparison"]},
    {"id": 100, "cat": "Technical-Math", "q": "What is yesterday nifty 50 price", "exp_sym": "NIFTY50", "exp_tools": ["quote"]}
]


def evaluate_test_case(test: Dict[str, Any], res_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates whether the test case passed or failed based on rigorous grading criteria.
    Returns failure details and recommended tools/fixes.
    """
    q_id = test["id"]
    cat = test["cat"]
    query = test["q"]
    reply = res_state.get("final_response", "")
    sym = res_state.get("symbol")
    intent = res_state.get("intent")
    sub_intents = res_state.get("sub_intents", [])
    tool_outs = res_state.get("tool_outputs", [])
    is_off_topic = res_state.get("is_off_topic", False)

    passed = True
    fail_reasons = []
    missing_tool = None

    # Check 1: Anti-hallucination check (No USD '$' or CME/ICE)
    if "$" in reply or "CME" in reply or "ICE" in reply or "Chicago Mercantile" in reply:
        passed = False
        fail_reasons.append("Hallucination: Output contains US dollar ($) or foreign exchange (CME/ICE) references.")

    # Check 2: Off-Topic Category
    if cat == "Off-Topic":
        if not is_off_topic or "cooking" not in reply.lower() and "non-financial" not in reply.lower() and "specialized" not in reply.lower():
            passed = False
            fail_reasons.append("Boundary Error: Failed to decline off-topic question politely.")
            missing_tool = "Domain Guardrail / Intent Classifier Filter"

    # Check 3: False / Non-Existent Tickers
    elif cat == "False-Ticker":
        if sym is not None:
            passed = False
            fail_reasons.append(f"Entity Error: Incorrectly resolved false/foreign asset to symbol '{sym}'.")
            missing_tool = "Asset Scope / Crypto-Foreign Disambiguation Filter"
        elif "could not locate" not in reply.lower() and "verified instruments" not in reply.lower() and "cannot provide" not in reply.lower():
            passed = False
            fail_reasons.append("Guardrail Error: Failed to state that asset is unavailable in database.")

    # Check 4: Calendar
    elif cat == "Calendar":
        if "calendar" not in sub_intents and intent != "calendar":
            passed = False
            fail_reasons.append("Routing Error: Query was not routed to the Calendar tool.")
            missing_tool = "Calendar Date Resolver"
        elif "2026" not in reply:
            passed = False
            fail_reasons.append("Data Error: Reply does not contain verified 2026 database dates.")

    # Check 5: Screener
    elif cat == "Screener":
        if "screener" not in sub_intents and intent != "screener":
            passed = False
            fail_reasons.append("Routing Error: Query was not routed to the Screener tool.")
            missing_tool = "Market Screener Tool"

    # Check 6: Multi-Layered
    elif cat == "Multi-Layered":
        exp_tools = test.get("exp_tools", [])
        for et in exp_tools:
            if et not in sub_intents and et not in str(tool_outs):
                passed = False
                fail_reasons.append(f"Decomposition Error: Expected sub-intent '{et}' was not executed.")
                missing_tool = f"Composite Decomposer ({et})"

    # Check 7: Conversational
    elif cat == "Conversational":
        exp_sym = test.get("exp_sym")
        if exp_sym and sym != exp_sym:
            passed = False
            fail_reasons.append(f"Context Error: Expected symbol '{exp_sym}' from history, but got '{sym}'.")
            missing_tool = "Multi-Turn Session Context Tracker"

    # Check 8: Rumor Traps
    elif cat == "Rumor-Trap":
        if "acquired" in reply.lower() and "apple" in reply.lower() and "unfounded" not in reply.lower() and "no verified" not in reply.lower():
            passed = False
            fail_reasons.append("Truthfulness Error: Hallucinated or confirmed fake rumor without verification.")
            missing_tool = "News Fact-Checking Guardrail"

    return {
        "id": q_id,
        "category": cat,
        "query": query,
        "symbol_resolved": sym,
        "intent_resolved": intent,
        "sub_intents": sub_intents,
        "passed": passed,
        "fail_reasons": fail_reasons,
        "missing_tool": missing_tool,
        "reply_preview": reply[:200]
    }


def run_full_torture_test():
    print("=" * 80)
    print("STARTING 100-QUESTION ADVERSARIAL TORTURE TEST ON VPROFITABLES ASSISTANT")
    print("=" * 80)

    results = []
    failed_cases = []
    t_start = time.time()

    for idx, test in enumerate(TORTURE_TEST_SUITE, 1):
        q = test["q"]
        hist = test.get("history") or []
        print(f"[{idx:03d}/100] Testing: '{q[:50]}...' (Cat: {test['cat']})", end=" ... ")
        sys.stdout.flush()

        try:
            state = run_ohlc_graph(q, history=hist, skip_llm=True)
            eval_res = evaluate_test_case(test, state)
            results.append(eval_res)

            if eval_res["passed"]:
                print("PASS")
            else:
                print(f"FAIL -> {eval_res['fail_reasons'][0]}")
                failed_cases.append(eval_res)
        except Exception as e:
            print(f"EXCEPTION -> {e}")
            failed_cases.append({
                "id": test["id"],
                "category": test["cat"],
                "query": q,
                "passed": False,
                "fail_reasons": [f"Pipeline Runtime Exception: {str(e)}"],
                "missing_tool": "Exception Recovery"
            })

    total_time = time.time() - t_start
    pass_cnt = len(results) - len(failed_cases)
    fail_cnt = len(failed_cases)

    print("\n" + "=" * 80)
    print(f"TORTURE TEST COMPLETED in {total_time:.1f}s")
    print(f"Total Cases: 100 | Passed: {pass_cnt} | Failed: {fail_cnt} ({(pass_cnt/100)*100:.1f}% Pass Rate)")
    print("=" * 80)

    # Save detailed evaluation log
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "torture_100_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"total": 100, "passed": pass_cnt, "failed": fail_cnt, "failures": failed_cases, "all_results": results}, f, indent=2)
    print(f"Detailed evaluation saved to {out_path}")

    return failed_cases


if __name__ == "__main__":
    run_full_torture_test()
