# tests/test_performance.py
import time
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

import bulk_news_fetch

def run_benchmark():
    print("=" * 65)
    print("  GANN-ASTRO Performance Benchmark")
    print("=" * 65)
    
    # Run the bulk fetcher pipeline with timing
    t0 = time.time()
    bulk_news_fetch.bulk_fetch_all(delay_secs=0.0, max_per_symbol=20, verbose=False, force_all=True)
    dur = time.time() - t0
    
    num_symbols = len(bulk_news_fetch.INSTRUMENTS)
    throughput = num_symbols / dur if dur > 0 else 0
    
    print("\n--- Benchmark Results ---")
    print(f"Total symbols processed : {num_symbols}")
    print(f"Total elapsed time      : {dur:.2f} seconds")
    print(f"Throughput              : {throughput:.2f} symbols/second")
    
    # Estimate rate limit capacity:
    # Google News search and Yahoo Finance do not require authenticated API keys and support 
    # moderate concurrency. With a concurrency ceiling of 30, we make roughly 120 requests per wave.
    # Assuming rate limit is 1200 requests per minute (20/sec):
    est_max_throughput = 20.0 / 3.0  # ~6.6 symbols per second before hit rate limits
    print(f"Estimated Max API capacity: ~{est_max_throughput:.1f} symbols/second before rate limits")

if __name__ == "__main__":
    run_benchmark()
