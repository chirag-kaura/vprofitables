import os
import sys
import time
import subprocess
import requests
from datetime import date

# Add core path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core.fetch_institutional import get_missing_trading_days
from data.instruments import ALL_INSTRUMENTS
from core.fundamental_engine import fetch_fundamentals

def update_fundamentals():
    print("  [UPDATE] Updating fundamentals cache for all equities...")
    equities = {s: i for s, i in ALL_INSTRUMENTS.items() if i.instrument_type == "EQUITY"}
    for i, (sym, inst) in enumerate(equities.items()):
        try:
            print(f"    [{i+1}/{len(equities)}] Fetching fundamentals for {sym}...", end=" ", flush=True)
            # Default TTL checks are in fundamental_engine so it won't fetch unnecessarily if cached
            data = fetch_fundamentals(sym, inst.yfinance_symbol)
            source = data.get('source', 'unknown')
            print(f"[{source}]")
        except Exception as e:
            print(f"Error: {e}")

def main():
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    print("=" * 60)
    print("  GANN-ASTRO v3.9 — Automated Daily Update")
    print("=" * 60)

    print("\n[1/5] Updating Daily Prices & Pivots (Yahoo)...")
    subprocess.run([sys.executable, "-X", "utf8", "download_history.py", "--topup"], env=env)

    print("\n[1.2/5] Updating Intraday 5m/15m Candles (Yahoo)...")
    subprocess.run([sys.executable, "-X", "utf8", "download_intraday.py", "--all", "--incremental"], env=env)

    print("\n[1.5/5] Updating Equity Bhavcopy (NSE) for official VWAP and Deliverable Qtys...")
    subprocess.run([sys.executable, "-X", "utf8", "download_equity_bhavcopy.py", "--incremental"], env=env)

    print("\n[2/5] Updating News Sentiment...")
    subprocess.run([sys.executable, "-X", "utf8", "bulk_news_fetch.py"], env=env)

    print("\n[2.1/5] Scoring News Headlines with FinBERT (Batch)...")
    try:
        subprocess.run([sys.executable, "-X", "utf8", "core/finbert_batch.py"], env=env, timeout=300)
    except Exception as e:
        print(f"  [WARN] FinBERT batch scoring step skipped: {e}")

    print("\n[2.2/5] Applying Market Feedback Labels & Retraining Sentiment Model...")
    try:
        subprocess.run([sys.executable, "-X", "utf8", "core/market_feedback.py"], env=env, timeout=300)
    except Exception as e:
        print(f"  [WARN] Market feedback step skipped: {e}")

    print("\n[3/7] Updating Bulk/Block Deals via nselib...")
    subprocess.run([sys.executable, "-X", "utf8", "scrape_deals.py", "--days", "30"], env=env)
    
    print("\n[3.5/7] Processing Bulk Deals into Net Flows...")
    subprocess.run([sys.executable, "-X", "utf8", "process_bulk_deals.py"], env=env)

    print("\n[4/7] Updating Option Chain Open Interest (Bhavcopy)...")
    subprocess.run([sys.executable, "-X", "utf8", "download_bhavcopy.py", "--incremental"], env=env)

    print("\n[4.5/7] Updating Participant-Wise Open Interest (Smart Money vs. Retail)...")
    subprocess.run([sys.executable, "-X", "utf8", "download_participant_oi.py", "--days", "30"], env=env)

    print("\n[5/7] Updating Volume Anomalies...")
    subprocess.run([sys.executable, "-X", "utf8", "core/fetch_institutional.py", "--volume-only"], env=env)

    print("\n[6/7] Retraining ML Reversal Models (Deep Signal Engine)...")
    try:
        subprocess.run(
            [sys.executable, "-X", "utf8", "core/deep_signal_engine.py", "--train"],
            env=env,
            timeout=600  # 10-minute hard limit — avoids hanging the pipeline
        )
    except subprocess.TimeoutExpired:
        print("  [WARN] ML training exceeded 10 min — skipping this cycle. Models from last run remain active.")

    print("\n[6.5/7] Retraining AI Trend Continuation Models (XGBoost + PyTorch MLP)...")
    try:
        subprocess.run(
            [sys.executable, "-X", "utf8", "core/continuation_deep_engine.py"],
            env=env,
            timeout=600
        )
    except subprocess.TimeoutExpired:
        print("  [WARN] Continuation training exceeded 10 min — skipping this cycle. Models from last run remain active.")

    print("\n[7/7] Running Autonomous Radar-to-Sniper Trade Tracker Desk & Alert Dispatcher...")
    try:
        subprocess.run(
            [sys.executable, "-X", "utf8", "run_daily_tracker_desk.py"],
            env=env,
            timeout=300
        )
    except Exception as e:
        print(f"  [WARN] Tracker desk step skipped: {e}")

    print("\n[8/9] Updating Fundamentals Cache...")
    try:
        update_fundamentals()
    except Exception as e:
        print(f"  [WARN] Fundamentals update step skipped: {e}")

    print("\n[8.5/9] Synchronizing Screener Deep Fundamentals & Concall Transcripts...")
    try:
        subprocess.run(
            [sys.executable, "-X", "utf8", "core/screener_sync.py", "--incremental"],
            env=env,
            timeout=600
        )
    except Exception as e:
        print(f"  [WARN] Screener fundamental/transcript sync skipped: {e}")

    print("\n" + "=" * 60)
    print("  All updates, ML training, and Tracker Desk runs completed successfully!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
