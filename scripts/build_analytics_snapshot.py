"""Build and benchmark a local DuckDB/Parquet snapshot of daily price history.

The SQLite source is opened read-only. A validated snapshot is published by
atomic directory rename, then the current.json manifest is replaced atomically.
Earlier snapshots are retained for rollback and comparison.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import statistics
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "market_data_v2.db"
DEFAULT_OUTPUT = ROOT / "data" / "analytics" / "daily_prices"
CHUNK_ROWS = 100_000

SQLITE_AGG = """
SELECT symbol, COUNT(*) AS row_count, MIN(trade_date) AS first_date,
       MAX(trade_date) AS last_date, AVG(close) AS avg_close,
       AVG(volume) AS avg_volume
FROM daily_prices
WHERE trade_date >= ?
GROUP BY symbol
ORDER BY symbol
"""
DUCKDB_AGG = """
SELECT symbol, COUNT(*) AS row_count, MIN(trade_date) AS first_date,
       MAX(trade_date) AS last_date, AVG(close) AS avg_close,
       AVG(volume) AS avg_volume
FROM read_parquet(?)
GROUP BY symbol
ORDER BY symbol
"""
SQLITE_PERFORMANCE = """
SELECT p1.symbol, p1.close,
       (SELECT p2.close FROM daily_prices p2
        WHERE p2.symbol=p1.symbol AND p2.trade_date<=? AND p2.close>0
        ORDER BY p2.trade_date DESC LIMIT 1) AS old_close,
       (SELECT p2.trade_date FROM daily_prices p2
        WHERE p2.symbol=p1.symbol AND p2.trade_date<=? AND p2.close>0
        ORDER BY p2.trade_date DESC LIMIT 1) AS old_date
FROM daily_prices p1
WHERE p1.trade_date=? AND p1.close>0
  AND p1.symbol NOT LIKE '%NIFTY%' AND p1.symbol NOT LIKE '^%'
  AND p1.symbol NOT IN ('INDIAVIX','GOLD','SILVER','COPPER','CRUDEOIL','NATURALGAS','TEST_SYM')
"""
DUCKDB_PERFORMANCE = """
WITH end_rows AS (
    SELECT symbol, close AS end_close FROM read_parquet(?)
    WHERE trade_date=? AND close>0
      AND symbol NOT LIKE '%NIFTY%' AND symbol NOT LIKE '^%'
      AND symbol NOT IN ('INDIAVIX','GOLD','SILVER','COPPER','CRUDEOIL','NATURALGAS','TEST_SYM')
), start_ranked AS (
    SELECT symbol, close AS old_close, trade_date AS old_date,
           ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) AS rn
    FROM read_parquet(?) WHERE trade_date<=? AND close>0
)
SELECT e.symbol, e.end_close, s.old_close, s.old_date
FROM end_rows e LEFT JOIN start_ranked s ON s.symbol=e.symbol AND s.rn=1
ORDER BY e.symbol
"""
TRAINING_SQLITE = """
SELECT symbol, trade_date, open, high, low, close, volume,
       vwap, deliverable_qty, deliverable_pct
FROM daily_prices
WHERE trade_date >= ? AND close IS NOT NULL
ORDER BY symbol, trade_date
"""
TRAINING_DUCKDB = """
SELECT symbol, trade_date, open, high, low, close, volume,
       vwap, deliverable_qty, deliverable_pct
FROM read_parquet(?)
WHERE trade_date >= ? AND close IS NOT NULL
ORDER BY symbol, trade_date
"""


def _readonly_connection(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(f"SQLite source database not found: {path}")
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
    conn.execute("PRAGMA query_only=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _median_query_times(callable_, repeats: int) -> tuple[list[float], Any]:
    timings: list[float] = []
    result = None
    for _ in range(repeats):
        start = time.perf_counter()
        result = callable_()
        timings.append(time.perf_counter() - start)
    return timings, result


def _assert_parity(sqlite_rows: list[tuple], duck_rows: list[tuple]) -> None:
    if len(sqlite_rows) != len(duck_rows):
        raise RuntimeError(f"Symbol count differs: SQLite={len(sqlite_rows)}, DuckDB={len(duck_rows)}")
    for left, right in zip(sqlite_rows, duck_rows):
        if left[:4] != right[:4]:
            raise RuntimeError(f"Non-numeric aggregate mismatch: SQLite={left[:4]}, DuckDB={right[:4]}")
        for field, a, b in (("avg_close", left[4], right[4]), ("avg_volume", left[5], right[5])):
            if a is None or b is None:
                if a != b:
                    raise RuntimeError(f"{field} null mismatch for {left[0]}: {a!r} != {b!r}")
            elif abs(float(a) - float(b)) > max(1e-8, abs(float(a)) * 1e-10):
                raise RuntimeError(f"{field} mismatch for {left[0]}: {a!r} != {b!r}")


def build_snapshot(db_path: Path, output_root: Path, since: str | None, repeats: int) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    conn = _readonly_connection(db_path)
    snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    staging = output_root / f".staging-{snapshot_id}"
    published = output_root / snapshot_id
    staging.mkdir()
    part_rows: list[dict[str, Any]] = []
    export_started = time.perf_counter()
    try:
        latest = conn.execute("SELECT MAX(trade_date) FROM daily_prices").fetchone()[0]
        if not latest:
            raise RuntimeError("daily_prices has no rows; cannot build an analytical snapshot")
        if since is None:
            # Keep a buffer beyond the app's 5-year (1826-day) horizon.
            cutoff = (date.fromisoformat(latest[:10]) - timedelta(days=365 * 6)).isoformat()
        else:
            cutoff = date.fromisoformat(since).isoformat()

        source_count = int(conn.execute(
            "SELECT COUNT(*) FROM daily_prices WHERE trade_date >= ?", (cutoff,)
        ).fetchone()[0])
        source_bounds = conn.execute(
            "SELECT MIN(trade_date), MAX(trade_date) FROM daily_prices WHERE trade_date >= ?", (cutoff,)
        ).fetchone()
        latest_updated_at = conn.execute(
            "SELECT MAX(updated_at) FROM daily_prices WHERE trade_date=?", (latest,)
        ).fetchone()[0]
        if source_count == 0:
            raise RuntimeError(f"No daily_prices rows at or after {cutoff}")

        parquet_writer = duckdb.connect(":memory:")
        cursor = conn.execute("""
            SELECT symbol, trade_date, open, high, low, close, volume, change_pct, updated_at,
                   vwap, deliverable_qty, deliverable_pct
            FROM daily_prices WHERE trade_date >= ? ORDER BY trade_date, symbol
        """, (cutoff,))
        columns = [item[0] for item in cursor.description]
        exported = 0
        while True:
            rows = cursor.fetchmany(CHUNK_ROWS)
            if not rows:
                break
            frame = pd.DataFrame.from_records(rows, columns=columns)
            parquet_writer.register("batch", frame)
            part = staging / f"part-{len(part_rows):05d}.parquet"
            escaped = str(part.resolve()).replace("'", "''")
            parquet_writer.execute(
                f"COPY (SELECT symbol::VARCHAR AS symbol, trade_date::VARCHAR AS trade_date, "
                f"open::DOUBLE AS open, high::DOUBLE AS high, low::DOUBLE AS low, "
                f"close::DOUBLE AS close, volume::DOUBLE AS volume, "
                f"change_pct::DOUBLE AS change_pct, updated_at::VARCHAR AS updated_at, "
                f"vwap::DOUBLE AS vwap, deliverable_qty::BIGINT AS deliverable_qty, "
                f"deliverable_pct::DOUBLE AS deliverable_pct FROM batch) TO '{escaped}' "
                "(FORMAT PARQUET, COMPRESSION ZSTD)"
            )
            parquet_writer.unregister("batch")
            exported += len(frame)
            part_rows.append({"file": part.name, "rows": len(frame), "bytes": part.stat().st_size,
                              "sha256": _sha256(part)})
        parquet_writer.close()
        if exported != source_count:
            raise RuntimeError(f"Export row count mismatch: source={source_count}, exported={exported}")

        export_seconds = time.perf_counter() - export_started
        glob_path = str((staging / "part-*.parquet").resolve()).replace("'", "''")
        duck = duckdb.connect(":memory:")

        def run_sqlite():
            return conn.execute(SQLITE_AGG, (cutoff,)).fetchall()

        def run_duckdb():
            return duck.execute(DUCKDB_AGG, [glob_path]).fetchall()

        sqlite_times, sqlite_result = _median_query_times(run_sqlite, repeats)
        duck_times, duck_result = _median_query_times(run_duckdb, repeats)
        _assert_parity(sqlite_result, duck_result)

        end_date = str(source_bounds[1])
        target_date = (date.fromisoformat(end_date[:10]) - timedelta(days=1826)).isoformat()

        def run_sqlite_performance():
            raw = conn.execute(SQLITE_PERFORMANCE, (target_date, target_date, end_date)).fetchall()
            return sorted((str(row[0]), float(row[1]), float(row[2]), str(row[3]))
                          for row in raw if row[2] is not None and row[3])

        def run_duckdb_performance():
            raw = duck.execute(DUCKDB_PERFORMANCE,
                               [glob_path, end_date, glob_path, target_date]).fetchall()
            return sorted((str(row[0]), float(row[1]), float(row[2]), str(row[3]))
                          for row in raw if row[2] is not None and row[3])

        sqlite_perf_times, sqlite_perf = _median_query_times(run_sqlite_performance, repeats)
        duck_perf_times, duck_perf = _median_query_times(run_duckdb_performance, repeats)
        if len(sqlite_perf) != len(duck_perf):
            raise RuntimeError(f"5Y performer count differs: SQLite={len(sqlite_perf)}, DuckDB={len(duck_perf)}")
        for left, right in zip(sqlite_perf, duck_perf):
            if left[0] != right[0] or left[3] != right[3] or abs(left[1] - right[1]) > 1e-8 or abs(left[2] - right[2]) > 1e-8:
                raise RuntimeError(f"5Y performer result mismatch: SQLite={left}, DuckDB={right}")

        training_cutoff = (date.fromisoformat(end_date[:10]) - timedelta(days=365 * 3)).isoformat()
        sqlite_training_times, sqlite_training_rows = _median_query_times(
            lambda: conn.execute(TRAINING_SQLITE, (training_cutoff,)).fetchall(), repeats
        )
        duck_training_times, duck_training_rows = _median_query_times(
            lambda: duck.execute(TRAINING_DUCKDB, [glob_path, training_cutoff]).fetchall(), repeats
        )
        if sqlite_training_rows != duck_training_rows:
            raise RuntimeError(
                f"ML training input row mismatch: SQLite={len(sqlite_training_rows)}, "
                f"DuckDB={len(duck_training_rows)}"
            )

        manifest: dict[str, Any] = {
            "snapshot_id": snapshot_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "dataset": "daily_prices",
            "source_database": str(db_path.resolve()),
            "source_database_bytes": db_path.stat().st_size,
            "source_table": "daily_prices",
            "source_latest_trade_date": latest,
            "source_latest_updated_at": latest_updated_at,
            "start_date": source_bounds[0],
            "end_date": source_bounds[1],
            "row_count": source_count,
            "symbol_count": len(sqlite_result),
            "schema": columns,
            "files": part_rows,
            "export_seconds": round(export_seconds, 4),
            "benchmark": {
                "repeats": repeats,
                "sqlite_seconds": [round(value, 6) for value in sqlite_times],
                "duckdb_parquet_seconds": [round(value, 6) for value in duck_times],
                "sqlite_median_seconds": round(statistics.median(sqlite_times), 6),
                "duckdb_median_seconds": round(statistics.median(duck_times), 6),
                "speedup_ratio": round(statistics.median(sqlite_times) / statistics.median(duck_times), 4),
                "parity": "passed",
                "scope": "same grouped per-symbol aggregate over the same date range; export cost reported separately",
            },
            "five_year_performance_query": {
                "target_date": target_date,
                "rows": len(sqlite_perf),
                "repeats": repeats,
                "sqlite_seconds": [round(value, 6) for value in sqlite_perf_times],
                "duckdb_parquet_seconds": [round(value, 6) for value in duck_perf_times],
                "sqlite_median_seconds": round(statistics.median(sqlite_perf_times), 6),
                "duckdb_median_seconds": round(statistics.median(duck_perf_times), 6),
                "speedup_ratio": round(statistics.median(sqlite_perf_times) / statistics.median(duck_perf_times), 4),
                "parity": "passed",
                "scope": "same nearest-close-per-symbol 5Y ranking input; only rows with a valid start close are compared",
            },
            "ml_training_price_read": {
                "start_date": training_cutoff,
                "rows": len(sqlite_training_rows),
                "repeats": repeats,
                "sqlite_seconds": [round(value, 6) for value in sqlite_training_times],
                "duckdb_parquet_seconds": [round(value, 6) for value in duck_training_times],
                "sqlite_median_seconds": round(statistics.median(sqlite_training_times), 6),
                "duckdb_median_seconds": round(statistics.median(duck_training_times), 6),
                "speedup_ratio": round(statistics.median(sqlite_training_times) / statistics.median(duck_training_times), 4),
                "parity": "passed",
                "scope": "same full-universe 3Y price/volume/VWAP/delivery rows in the ML loader projection",
            },
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        conn.close()
        duck.close()
        staging.rename(published)
        current_tmp = output_root / ".current.json.tmp"
        current_tmp.write_text(json.dumps({"snapshot_id": snapshot_id, "manifest": f"{snapshot_id}/manifest.json"}, indent=2), encoding="utf-8")
        os.replace(current_tmp, output_root / "current.json")
        manifest["snapshot_path"] = str(published)
        return manifest
    except Exception:
        conn.close()
        # Keep the failed staging directory for diagnosis; never delete prior snapshots.
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite source database (read-only)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Local snapshot directory")
    parser.add_argument("--since", help="Inclusive YYYY-MM-DD cutoff; default is five years before latest trade date")
    parser.add_argument("--repeats", type=int, default=5, help="Read-query benchmark repetitions (default: 5)")
    args = parser.parse_args()
    if args.repeats < 3:
        parser.error("--repeats must be at least 3")
    result = build_snapshot(args.db.resolve(), args.output.resolve(), args.since, args.repeats)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
