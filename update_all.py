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
from download_bulk_deals import import_csv_folder
from data.instruments import ALL_INSTRUMENTS
from core.fundamental_engine import fetch_fundamentals

def download_missing_deals():
    missing = get_missing_trading_days(30)
    if not missing:
        print("  [UPDATE] No missing trading days for bulk/block deals. DB is up to date.")
        return

    deals_dir = os.path.join(BASE_DIR, "deals_csv")
    os.makedirs(deals_dir, exist_ok=True)
    
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    })

    downloaded = 0
    print(f"  [UPDATE] Found {len(missing)} missing days. Attempting to download CSVs...")
    for d in missing:
        ymd = d.strftime("%Y%m%d")
        dmy = d.strftime("%d%m%Y")
        
        for kind, urls in [
            ("bulkdeals", [
                f"https://archives.nseindia.com/archives/equities/bultrans/bulkdeals{ymd}.csv",
                f"https://archives.nseindia.com/archives/equities/bultrans/bulkdeals{dmy}.csv",
                f"https://nsearchives.nseindia.com/archives/equities/bultrans/bulkdeals{ymd}.csv"
            ]),
            ("blockdeals", [
                f"https://archives.nseindia.com/archives/equities/blockdeals/blockdeals{ymd}.csv",
                f"https://archives.nseindia.com/archives/equities/blockdeals/blockdeals{dmy}.csv",
                f"https://nsearchives.nseindia.com/archives/equities/blockdeals/blockdeals{ymd}.csv"
            ])
        ]:
            for url in urls:
                try:
                    r = sess.get(url, timeout=10)
                    # Check if response is valid CSV (not HTML, not 404, size > 30 bytes)
                    if r.status_code == 200 and len(r.content) > 30 and b"<html" not in r.content.lower() and b"404" not in r.content[:100]:
                        file_path = os.path.join(deals_dir, f"{kind}_{ymd}.csv")
                        with open(file_path, "wb") as f:
                            f.write(r.content)
                        downloaded += 1
                        break
                except Exception:
                    continue
        time.sleep(1) # respectful delay
        
    if downloaded > 0:
        print(f"  [UPDATE] Downloaded {downloaded} CSV files to deals_csv/. Importing...")
    else:
        print(f"  [UPDATE] No new CSV files downloaded automatically (NSE might be blocking).")
        print(f"           Checking if you manually placed any CSVs in deals_csv/ ...")
        
    import_csv_folder(deals_dir)

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

    print("\n[1/5] Updating Daily Prices & Pivots...")
    subprocess.run([sys.executable, "-X", "utf8", "download_history.py", "--topup"], env=env)

    print("\n[2/5] Updating News Sentiment...")
    subprocess.run([sys.executable, "-X", "utf8", "bulk_news_fetch.py"], env=env)

    print("\n[3/5] Updating Fundamentals...")
    update_fundamentals()

    print("\n[4/5] Updating Volume Anomalies...")
    subprocess.run([sys.executable, "-X", "utf8", "core/fetch_institutional.py", "--volume-only"], env=env)

    print("\n[5/7] Updating Bulk/Block Deals via CSV...")
    download_missing_deals()

    print("\n[6/7] Updating Option Chain Open Interest (Bhavcopy)...")
    subprocess.run([sys.executable, "-X", "utf8", "download_bhavcopy.py", "--incremental"], env=env)

    print("\n[7/7] Retraining ML Reversal Models (Deep Signal Engine)...")
    try:
        subprocess.run(
            [sys.executable, "-X", "utf8", "core/deep_signal_engine.py"],
            env=env,
            timeout=600  # 10-minute hard limit — avoids hanging the pipeline
        )
    except subprocess.TimeoutExpired:
        print("  [WARN] ML training exceeded 10 min — skipping this cycle. Models from last run remain active.")

    print("\n" + "=" * 60)
    print("  All updates and ML training completed successfully!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
