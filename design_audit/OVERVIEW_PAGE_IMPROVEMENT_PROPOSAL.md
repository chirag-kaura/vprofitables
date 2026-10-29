# Overview page improvement proposal

**Purpose:** Review the proposed implementation scope, architecture choices, future page layout and measurable outcomes before any code changes are authorized.

**Date:** 2026-10-28

## Recommendation

Deliver this in two implementation releases:

1. **Release 1: Trust and page performance.** Keep the current Python/SQLite stack, correct misleading values, add clear freshness/provenance, reduce first-load work, and reorganize the page. This is the smallest, safest path to material improvement.
2. **Release 2: Scale only if measured.** Improve database connection/query patterns and separate analytical workloads only if the baseline shows SQLite is the bottleneck. Do not start with a wholesale database or framework migration: the local DB passes `quick_check`, is indexed for key price reads, and the current known critical issues are application/data semantics, not proven SQLite failure.

**Preferred stack:** keep the existing Python backend, plain JS frontend, and SQLite for local operation. Add read-only query connections, materialized overview snapshots, versioned API payloads, and metrics. Use DuckDB only for larger analytical batch jobs if benchmarks justify it; it is not a drop-in concurrent OLTP replacement for positions, watchlists, or ingestion writes. A framework migration (FastAPI, React, etc.) should be evaluated separately, because it would not by itself fix fabricated values, stale data, SQL work, or source quality.

## Files likely to change

### Release 1: required code paths

| File | Planned change |
|---|---|
| `pages/page_overview.py` | Rebuild the Overview markup, CSS and render functions; proper accessible tabs; dashboard hierarchy; per-panel loading/error/stale states; remove fabricated F&O values and news fallback; display source/as-of/unit; show verified stop states; render only schema-validated and escaped recommendations. |
| `app.py` | Split/trim `_get_overview_data()` into a fast dashboard summary and lazy panel endpoints; replace randomized `1D` series with actual intraday rows; correct instrument/universe semantics; shared long/short risk-distance calculation; attach provenance/freshness metadata; avoid repeated dashboard reads; query real derivatives only when fresh/valid; bound deal lookback. |
| `core/api_contracts.py` | Define/version the new overview payload contracts and required provenance/coverage fields. |
| `core/paths.py` | Add an explicit read-only DB connection helper/policy for page endpoints; centralize consistent PRAGMAs without setting journal mode for every read. |
| `core/scheduler.py` | Reuse latest quote snapshot safely and expose quote timestamp/source; update cache invalidation when an ingest completes. |
| `download_history.py` | Validate/record price source and timestamp consistently; quality checks for OHLC/return continuity; preserve idempotent writes. Only schema changes needed for the selected provenance contract. |
| `core/fetch_institutional.py` | Ensure deal source/fetch provenance and date range semantics are consistent for recent-deal insights. |
| `core/sentiment_db.py` | Confirm sentiment score absence vs neutral; expose model version/confidence/source URL; preserve null/unavailable state. |
| `core/overview_service.py` *(new)* | Encapsulate overview queries, source metadata, quality gates, and DTO/payload construction instead of growing route logic in `app.py`. |
| `core/overview_snapshots.py` *(new, optional for Release 1)* | Build/cache compact overview snapshots after ingest and by algorithm version, if baseline reveals synchronous analytics are costly. Could start as in-memory/SQLite derived tables later. |
| `core/migrations/00xx_overview_provenance.sql` *(new if schema needs it)* | Add backward-compatible provenance/unit/session/validation columns and indexes. Run explicit, backed-up migration rather than recreating the large DB. |
| `tests/test_overview_contract.py` *(new)* | Check endpoint schema, freshness and unavailable-data behavior. |
| `tests/test_overview_risk.py` *(new)* | Cover long/short stop geometry, stop breached vs near, zero/missing CMP/SL. |
| `tests/test_overview_data_quality.py` *(new)* | Cover universe membership, commodity unit/return continuity, stale derivatives and session coverage. |
| `tests/test_overview_ui.py` *(new)* | Browser smoke coverage for tabs, keyboard access, error/empty/stale state, XSS-safe rendering and console errors. |
| `design_audit/OVERVIEW_PAGE_PRODUCT_AUDIT.md` | Existing audit reference; update findings to resolved/remaining after implementation. |

### Existing shared paths that may need small changes

- `pages/_shared.js`: only if the current `api()` helper needs request cancellation, retry/backoff, response metadata, or stale-cache behavior.
- `pages/_html_head.html`: only if shared tab/button tokens or responsive/accessibility CSS belong at the app shell level.
- `START.bat`: no change expected for Release 1. It may change only if a chosen migration introduces an explicit one-time migration/backup step; ordinary startup should not silently rewrite the DB.
- `requirements.txt`, `Dockerfile`, `docker-compose.yml`: no change expected for Release 1. Change only if a measured architecture decision adds a dependency/service.

This is an expected change map, not a commitment to touch every listed file. Implementation should avoid unrelated code, tests, assets and database cleanup.

## Future Overview layout

### Shared page header

```text
Overview     Market: CLOSED · EOD       Data as of 27 Oct 2026, 15:30 IST
NIFTY 50  22,749.75   −0.02%       Breadth  1.00 (250 up / 250 down)       Refresh

Dashboard | Discover | Derivatives | Commodities | Indices | News
```

Every value in the header should come with a source/market-session tooltip or detail drawer. The product must distinguish local DB refresh time from exchange observation time.

### Dashboard (initial tab)

```text
┌ Portfolio summary ───────────────────────────────┐  ┌ Market context ────────────┐
│ Value · invested · unrealized P&L · day P&L      │  │ Benchmark · breadth · score│
│ As of quote time · View positions                │  │ Score method + confidence  │
└──────────────────────────────────────────────────┘  └────────────────────────────┘

┌ ACTION REQUIRED ───────────────────────────────────────────────────────────────┐
│ Breached stop (red) → Near stop (amber) → Concentration (neutral/amber)          │
│ CMP · stop · signed distance · position side · source/time · View position       │
└────────────────────────────────────────────────────────────────────────────────┘

┌ Watchlist ───────────────────────────────────┐  ┌ Relevant opportunities ─────┐
│ Symbol · price · change · freshness           │  │ Setup · entry · stop/target │
│ Add symbol                                   │  │ R/R · horizon · generated   │
└──────────────────────────────────────────────┘  └─────────────────────────────┘

┌ Portfolio-linked news ─────────────────────────────────────────────────────────┐
│ Entity matched · headline · sentiment/confidence · publisher/time · open source │
└────────────────────────────────────────────────────────────────────────────────┘
```

- If no positions exist, show **“No portfolio positions connected”** and offer the relevant portfolio action. Do not infer that cash is liquid or that safeguards are active.
- Empty, stale, loading and failed states appear inside each card; one failure must not block the rest of the dashboard.
- Risk is an ordered action list, not a large wall of equivalent alerts.
- News must state whether it matched a holding, watchlist symbol, or broad market.

### Discover

```text
Universe: Nifty 50 ▾    As of: ...
Gainers/Losers | Most traded volume | Performance | Technical screens | Signals

Top movers table: Symbol | Last | Change | Volume | Quality/freshness
Sector heatmap/list (optional)       Selected sector members
Performance: 1W / 1M / 1Y / 5Y, with exact start/end dates and survivorship note
```

Replace hand-coded “cap” approximations with a sourced universe/membership. “Most Bought” becomes **Most traded by volume**, with traded quantity and turnover clearly separated.

### Derivatives

```text
Market session + data status: EOD / morning snapshot / unavailable
Underlying | expiry | spot/future | OI | OI change | PCR | source/as-of
Index and Stock filters · session/expiry filters
```

Show a metric only when backed by the correct instrument/date/expiry/session data and freshness checks. Distinguish spot index from futures contract. If all inputs are zero/missing, show unavailable rather than a 0.00 PCR or a fabricated contract.

### Commodities

```text
Commodity | exchange/contract | quote unit/currency | last | change | expiry/roll | as-of
Trend chart with explicit contract continuity and roll markers
```

Do not compare across a contract roll as if it were a like-for-like daily return. Explain unit and contract size.

### Indices

```text
Index | value | change | open/high/low/previous close | source/as-of
Observed intraday chart when candles exist; otherwise daily history, clearly labeled
```

The 1D chart uses observed `intraday_prices` candles only. It must never interpolate/randomize a path and present it as market history.

### News

```text
Filters: Portfolio | Watchlist | Market | Symbol | Sentiment | Date
Headline · matched entity · source link · published time · fetched time
Sentiment label + score + confidence/model version (or “not scored”)
```

“Portfolio” and “Watchlist” are strict match filters. No unrelated fallback. Sentiment labels show model coverage and time decay only if that behavior is intentionally part of the UI.

## Before and after metrics

**Important:** only the “Observed now” entries below are measured from the source/local DB. “Target” means acceptance objective after implementation, not a promised achieved result. A browser/API baseline is not yet measured, so latency, throughput and visual metrics must be captured before coding using the same machine and data snapshot.

| Metric | Observed now | Target after implementation | How measured |
|---|---:|---:|---|
| Fabricated OI/PCR/rollover fields | 4 displayed fields use formulas; all are unsupported by source rows | 0 | Trace each rendered metric to a row/source/session; otherwise assert unavailable |
| Synthetic intraday chart | 25 randomized points generated for each index | 0 synthetic points; observed candles only | Compare chart points exactly to selected `intraday_prices` rows |
| Stop status | Long/short semantics not consistently applied; negative “distance” may be presented as proximity | 100% of alerts direction-aware; breached and near are distinct | Risk unit/property cases; compare portfolio and alert outputs |
| Quote provenance | Overview response has no common panel-level as-of/source/session contract | 100% of quote/derivative/news panels show required provenance | Contract/UI assertions for every panel |
| Sample price freshness | `daily_prices` latest trade date: 2026-10-27; overview in-process cache TTL: 30s | Label actual quote timestamp and EOD/live mode; age itself depends on feed SLA | Compare rendered metadata to DB/provider observation and market calendar |
| Wrong-scope portfolio news | Up to 3 broad latest headlines can be displayed when exact holdings match = 0 | 0 unrelated headlines under Portfolio filter | Fixture with no symbol match; assert empty state |
| Placeholder recommendation values | Missing potential can become 5%; missing prices can become ₹0 | 0 incomplete setups shown as valid recommendation | Contract and malformed-record fixtures |
| Initial market data API breadth | One endpoint builds dashboard + discovery + technicals + signals + news | Summary only at initial load; remaining panels lazy | Network trace and endpoint payload contracts |
| Initial page API requests | One `overview_data` plus 5 parallel dashboard endpoints (6 requests) | 1–2 bounded dashboard calls; optional panels lazy | Browser network trace; count and dependency review |
| Initial payload bytes | Not measured yet | ≤100 KB compressed for summary; lazy payloads paginated/limited | `Content-Length`/compressed transfer capture |
| Initial useful content latency | Not measured yet | p95 ≤1.5 s on documented reference machine | 30 cold + 100 warm local runs; record p50/p95/p99 |
| Summary API latency | Not measured yet | p95 ≤300 ms warm and ≤800 ms cold | Server timing around endpoint and DB spans |
| Discovery/technical work on first view | Scans up to 35 symbols for technical/pattern data in overview request | 0 discovery/pattern scans before user opens Discover | Query counters/traces on dashboard-only load |
| SQLite DB file size | 1,497,276,416 bytes (~1.39 GiB); 2,082,045 daily rows; 3,613,307 intraday rows | No arbitrary size reduction target in Release 1; measure I/O and keep needed history | DB file/page counts, backup size, retained history policy |
| Database validation | `PRAGMA quick_check`: `ok` | Continue passing before/after migration | Backup copy, migration validation, quick_check |
| SQLite lock failures | No contention benchmark captured | 0 failed requests in defined 10-reader + ingestion scenario | Concurrent local load with lock-wait/error metrics |
| Client JavaScript errors | Not measured in a browser during audit | 0 in supported Overview flows | Browser smoke and console capture |
| Accessibility | Clickable div tabs; no tablist keyboard behavior | Keyboard operable, semantic tabs, visible focus, text labels independent of color | Automated accessibility + keyboard walkthrough |
| Scroll to primary risk/portfolio action | Not measured; current dashboard has multiple stacked panels | Portfolio and action queue visible in first viewport at 1366×768 | Fixed viewport screenshot and scroll-height comparison |
| Feed quality coverage | Unknown by panel; option-chain latest NIFTY/BANKNIFTY rows are morning session; latest stored PCR sample includes zeros | Coverage/freshness shown; no stale or invalid metric presented as current | Per-session completeness and quality dashboard |

### Expected qualitative changes

| User concern | Current experience | Proposed experience |
|---|---|---|
| “Is this data current?” | Generic LTP/live wording; user must infer | Source, exchange/session, observed time and age next to the value |
| “What should I do first?” | Several large panels compete for attention | Action queue ordered by severity and tied to a holding |
| “Can I trust derivatives?” | Plausible-looking generated values | Real contracts/expiry/session or explicit unavailable state |
| “Why is this recommended?” | General copy/default values | Validated levels, calculated risk/reward, time horizon and reason data |
| “Is this news about me?” | Broad fallback can appear as portfolio news | Exact holding/watchlist match or clearly marked market news |
| “Why does the first page take time?” | All panel data built before user chooses a tab | Small dashboard loads first; large panels fetch on demand |

## Benchmark plan before implementation

Capture a repeatable local baseline before editing code:

1. Use the same machine, local DB, market state and browser viewport. Record CPU, memory, Python version and DB bytes.
2. Time `overview_data` cold/warm and each dashboard endpoint separately; include database query durations and serialized/compressed bytes.
3. Use browser network/performance recording for first content, largest content, usable dashboard, request count, JS errors and layout shift.
4. Repeat at least 30 cold and 100 warm page loads; report p50/p95/p99 and sample conditions.
5. Run a defined concurrency case (for example 10 simultaneous readers while ingestion is writing) and capture errors, busy wait and tail latency.
6. Keep these exact baseline scripts/results in a separate performance artifact so after-values compare like for like.

## Architecture choices and migration thresholds

| Option | Recommendation | Use when |
|---|---|---|
| Keep SQLite + improve queries/snapshots | **Start here** | Local single-user app, current data volume and current evidence; lowest migration risk |
| DuckDB for analytical snapshots/batch computations | Consider selectively | CPU-heavy aggregates dominate measured latency; keep SQLite as transactional owner for positions/watchlists/ingestion state |
| PostgreSQL | Not for Release 1 | Multiple concurrent writers/users, remote service deployment, or multi-machine access becomes a supported product requirement |
| FastAPI + React/Vue | Not required to meet this proposal | A separate product/UI modernization is desired and team can absorb routing, packaging, auth, build and offline/local startup changes |
| Redis/materialized service cache | Defer | Multiple app processes or distributed workers need shared cache and measured cache contention exists |

SQLite is 1.39 GiB and has millions of rows, so scale is nontrivial. However, the audit did not capture slow-query timings or lock failures, and key indexes exist. Database migration before profiling risks substantial work while leaving the actual data-trust bugs untouched. If the eventual move is to PostgreSQL, keep the schema and repository/service boundary portable, run a local shadow dual-write/read comparison, migrate from a verified backup, compare row counts/checksums, and retain rollback. Do not make `START.bat` silently migrate production data.

## Decisions needed before implementation

1. **Data mode:** Is the app meant to show truly live broker data, a delayed feed, or latest ingested market/EOD values? Choose acceptable age by asset type.
2. **Data vendors:** Confirm source/provider and entitlements for NSE/BSE/MCX/index/options/news data, including deep links/attribution requirements.
3. **Look and feel:** Keep the existing dark theme, or use the proposed more compact institutional dashboard in the same theme? Default recommendation: same dark theme, cleaner hierarchy, less emoji, no framework migration.
4. **“Portfolio”:** Imported real Demat, manually tracked, or paper positions? What fields are authoritative for value and P&L?
5. **Performance reference:** Which PC should be the reference, and is ≤1.5 s p95 initial usable dashboard acceptable?
6. **History retention:** Required years of 1-minute candles/options data and backup/restore expectations before any archive/compression policy is enacted?

## Approval boundary

This document proposes file scope and design only. No implementation, DB migration, dependency change or visual page change has been performed. Once the product/data decisions above are settled, implement Release 1 and establish measured before/after values; choose any tech-stack migration only from those measurements and an explicit operational requirement.
