# Local data architecture implementation

**Updated:** 29 October 2026

## Implemented

- `core.paths` is now the shared SQLite connection policy. Read-only mode uses SQLite URI `mode=ro` plus `query_only`; writer connections no longer change journal mode on every open. The application, scheduler, and personalization database helper use this policy, with an 8 MiB per-connection page-cache target.
- Database startup now records numbered schema migrations and applies additive migration 2, `data_ingest_run_provenance`. It creates `data_ingest_runs` and its dataset/completion index; it does not rewrite existing price rows.
- Successful EOD Yahoo Finance daily-price batches write one provenance row with provider, observed market date, row count, batch start/completion timestamps, and request settings in the same SQLite transaction as the batch.
- Daily-price writes bump an in-process data revision; the overview RAM-cache key includes that revision, so scheduler updates invalidate old responses without waiting for the TTL.
- `scripts/build_analytics_snapshot.py` creates a read-only SQLite export of six years of daily prices, writes typed Zstandard-compressed Parquet parts, verifies row counts and benchmark result parity, hashes each part, and atomically publishes a versioned `current.json` pointer. Older snapshots are retained. Generated snapshots are Git-ignored.
- The overview response reports whether the local analytical snapshot exists and is current relative to the latest SQLite trade date and latest row update timestamp. SQLite remains the serving and operational source of truth.
- README database claims now distinguish the main SQLite database from the existing, separate DuckDB one-minute poller store.

## Local benchmark

Machine-local run against `market_data_v2.db` on 29 October 2026. SQLite was opened read-only. Source file: 1,537,748,992 bytes. The snapshot contains 696,037 rows for 2,741 symbols from 2020-10-30 through 2026-10-29; compressed Parquet parts total about 22.3 MB. Export took 41.6 seconds.

| Workload | SQLite median | DuckDB/Parquet median | Ratio | Result |
|---|---:|---:|---:|---|
| Grouped per-symbol six-year summary | 1.314 s | 0.076 s | 17.4x | Exact summary parity; query-only gain, export cost excluded |
| Five-year nearest-close ranking input | 0.040 s | 0.093 s | 0.43x | Parity passed; SQLite remains faster |
| Full-universe three-year ML price-row projection (375,603 rows) | 3.505 s | 2.084 s | 1.68x | Exact row parity; below the 2x adoption gate |

The benchmark covers query timings and data parity, not full model-training time, dashboard latency, or concurrent ingestion. The winning broad aggregate is not currently a serving-path calculation. The tested ML read does not meet the proposed 2x gate. Therefore the Parquet lane is an opt-in pilot, not a production query backend. No application calculation has been redirected to DuckDB based on this run.

## Safety and rollout notes

- The existing database was not modified during the snapshot/benchmark run. Its file was read-only; the migration will run on the next application startup.
- Snapshot export is manual and opt-in. Automatic EOD refresh is deferred until the runtime workload is selected and storage/refresh budget is agreed; a 41.6-second full snapshot export should not silently become daily startup work.
- Failed staging snapshots are left for diagnosis and do not replace the last good pointer. Remove only `.staging-*` directories after confirming the failed attempt is no longer needed.
- The pre-existing changes to model files and logs in the working tree were not edited by this implementation.

## Next gate

Use the pilot for a measured, representative analytical batch or full ML training run. Adopt that workload only when end-to-end time (including snapshot cost), result parity, memory/disk use, and freshness meet the agreed thresholds. Keep the portfolio, position, ingestion, and user-state writes on SQLite.

