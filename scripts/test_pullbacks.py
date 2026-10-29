import sys, os
sys.path.insert(0, os.getcwd())
from core.trend_continuation_engine import scan_trend_pullbacks

pullbacks = scan_trend_pullbacks(horizon="swing", min_confidence=60, max_results=5)
print(f"Found {len(pullbacks)} pullbacks:")
for p in pullbacks[:3]:
    print(p.get("symbol"), p.get("price"), p.get("sector"), p.get("confidence"), p.get("rr_ratio"))
