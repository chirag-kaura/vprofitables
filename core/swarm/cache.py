"""
core/swarm/cache.py
===================
Sprint 3: Performance Caching & Latency Budgeting for Multi-Agent Swarm.
Provides thread-safe in-memory TTL caching with granular TTL profiles:
  - DAILY_MATH_TTL (24 hours): Gann Square of 9, Wyckoff Phase, Vedic Nakshatra,
    Planetary Ephemeris, Audited 10Y Balance Sheets.
  - INTRADAY_TTL (60 seconds): Live Options PCR, Smart Money Deals, Deep ML forward passes.
  - QUERY_TTL (120 seconds): Exact query response caching for sub-millisecond repeat queries.
"""

import time
import functools
import threading
import hashlib
import copy
from typing import Any, Optional, Dict, Tuple, Callable

# Default TTL presets in seconds
TTL_DAILY_MATH = 86400        # 24 hours (astrological date, EOD geometric angles, audited statements)
TTL_INTRADAY = 60             # 60 seconds (derivatives microstructures, deal flows)
TTL_QUERY_RESPONSE = 120      # 2 minutes (identical natural language prompt deduplication)

class SwarmMemoryCache:
    """Thread-safe TTL in-memory cache with eviction and hit rate telemetry."""
    
    def __init__(self):
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._store.get(key)
            if item is None:
                self.misses += 1
                return None
            expiry, value = item
            if time.time() > expiry:
                del self._store[key]
                self.misses += 1
                return None
            self.hits += 1
            return value

    def set(self, key: str, value: Any, ttl: float):
        with self._lock:
            self._store[key] = (time.time() + ttl, value)

    def invalidate(self, key: str):
        with self._lock:
            if key in self._store:
                del self._store[key]

    def clear(self):
        with self._lock:
            self._store.clear()
            self.hits = 0
            self.misses = 0

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            active_count = sum(1 for exp, _ in self._store.values() if exp > now)
            total_reqs = self.hits + self.misses
            hit_ratio = (self.hits / total_reqs * 100.0) if total_reqs > 0 else 0.0
            return {
                "active_items": active_count,
                "hits": self.hits,
                "misses": self.misses,
                "hit_ratio_pct": round(hit_ratio, 2)
            }

# Global singleton cache instance
global_cache = SwarmMemoryCache()


def ttl_cached(ttl: float, namespace: str = "default"):
    """
    Decorator for caching function results with a given TTL and namespace.
    Generates a deterministic hash key from function args and kwargs.
    """
    def decorator(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            # Build deterministic cache key
            raw_key = f"{namespace}:{fn.__name__}:{repr(args)}:{repr(sorted(kwargs.items()))}"
            cache_key = hashlib.md5(raw_key.encode("utf-8")).hexdigest()

            cached_val = global_cache.get(cache_key)
            if cached_val is not None:
                try:
                    return copy.deepcopy(cached_val)
                except Exception:
                    return cached_val

            result = fn(*args, **kwargs)
            if result is not None:
                global_cache.set(cache_key, result, ttl)
                try:
                    return copy.deepcopy(result)
                except Exception:
                    return result
        return wrapper
    return decorator


def make_query_key(query: str, symbol: Optional[str] = None) -> str:
    """Helper to produce normalized query hash for conversation caching."""
    norm = f"{query.strip().lower()}|{str(symbol).strip().upper()}"
    return f"query:{hashlib.md5(norm.encode('utf-8')).hexdigest()}"
