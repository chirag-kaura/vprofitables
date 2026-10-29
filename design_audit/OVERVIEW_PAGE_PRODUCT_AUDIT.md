# Vprofitables Overview page: product and engineering audit

**Scope:** `http://localhost:5050/#overview`, including its seven subtabs, the overview API, and only the data/storage paths those panels consume. This is a source and local-database audit, not an independent verification of exchange feeds or a live browser performance trace.

**Audit date:** 2026-10-28 (Asia/Kolkata)

## Executive summary

The page has useful breadth, but it currently mixes end-of-day market data, stale/zero derivatives data, generated placeholder metrics, portfolio state and AI copy without consistently showing the source or observation time. Several high visibility values are misleading enough that correctness must be fixed before optimizing or expanding the page.

Highest priority findings:

1. **The F&O panels show invented values.** `renderIndexFnO()` and `renderStocksFnO()` derive OI, PCR, OI change and rollover from price arithmetic in the browser. They are not sourced from derivatives tables.
2. **The index “1D” chart is fabricated.** The API generates 25 randomized points between daily open and close; it does not use intraday candles.
3. **The sample portfolio stop-loss warnings are directionally wrong for some holdings.** For a long position where market price is below the stop, `(CMP - SL) / CMP` returns a negative “distance”; the UI reports this as “within -3.4%,” even though the stop has already been crossed. This needs direction-aware validation and an explicit “breached” state.
4. **Freshness is hidden and the UI says live.** The local `daily_prices` table tops out at 2026-10-27. The `overview_data` response is cached for 30 seconds, but that is cache age, not quote age. Intraday candles do extend to 2026-10-27 15:25, but the overview price cards do not use them.
5. **Portfolio news is not reliably portfolio-specific.** If no exact symbol match exists, the code displays the latest three broad news rows under the Portfolio News toggle.
6. **The initial request does too much work.** One overview endpoint prepares discovery rankings, multiple time horizons, patterns and screeners before showing the dashboard; then the dashboard issues five additional API requests.

Do not claim “1000x” improvement without establishing a baseline. The realistic objective is to improve trust first, then measure and reduce first-content latency and database contention against explicit targets.

## What was inspected

- `pages/page_overview.py`: tabs, rendering, risk/news handling and F&O panel calculations.
- `app.py`: `_get_overview_data()`, overview cache, portfolio insight helper, portfolio/risk/watchlist/recommendation API handlers.
- `core/paths.py`, `core/scheduler.py`, `download_history.py`, `core/sentiment_db.py`, `core/fetch_institutional.py`: database path, quote cache, schemas, indexes and ingestion patterns.
- `market_data_v2.db`: SQLite schema and read-only aggregates. `PRAGMA quick_check` returned `ok`.
- Existing audit/QA documentation and database inspection scripts.

## Evidence-backed findings

| Priority | Area | Finding and evidence | User impact |
|---|---|---|---|
| P0 | F&O trust | `pages/page_overview.py`, `renderIndexFnO()` uses `(idx.ltp * 1234 % 100000)` and `(0.8 + idx.ltp % 5 / 10)` for OI/PCR. `renderStocksFnO()` uses price-derived formulas for OI change and rollover. | False derivatives data can directly affect trading decisions. Remove these values or display “unavailable” until tied to real records. |
| P0 | Chart truth | `app.py` builds `intraday_pts` with seeded random noise between daily OHLC bounds and assigns it to `histories['1D']`. | A chart appears to show an observed intraday path but is synthetic. Use `intraday_prices` by interval/candle time or label it as unavailable. |
| P0 | Stop-loss state | `app.py::_get_portfolio_ai_insights()` and the page risk renderer use `(CMP-SL)/CMP` without checking side or whether the level has been crossed. The supplied example has LGEINDIA CMP ₹1677.80 below SL ₹1679.31 yet says “within -0.1%.” | Users can misread a breached/inconsistent stop as a proximity warning. Validate long/short geometry, calculate distance using risk-side semantics, and flag breached separately. |
| P0 | Price freshness | `daily_prices`: 2,082,045 rows, 2,730 symbols, latest date `2026-10-27`; 517 records on latest date. The page request has a 30-second in-process cache but no as-of/source metadata. | “Live”, “LTP”, and “today” overstate what an EOD snapshot establishes. Display “As of” timestamp, source and EOD/delayed/live state per section. |
| P0 | Instrument units | `instruments` explicitly stores commodities as MCX, but overview maps their `daily_prices.close` into `₹` formatting. Local values include SILVER `54.38`, NATURALGAS `3.00`, COPPER `6.66`; the UI labels them as rupees without a contract/unit descriptor. | Users cannot know whether the value represents a contract quote, normalized unit, or an instrument-specific price. Read exchange/unit/lot/quote metadata and render it. |
| P1 | Commodity change | `daily_prices.change_pct` for 2026-10-27 includes SILVER `+0.51%`, NATURALGAS `+15.45%`; the overview recomputes commodity percent from the previous row close. Supplied snapshot shows SILVER `-71.80%`, which is not matched by the inspected latest row and warrants unit/corporate/contract continuity investigation. | A potentially severe outlier appears without a stale/rollover/quality warning. Do not silently trust row-to-row contract comparisons. |
| P1 | “Most Bought” | `app.py` sorts `daily_prices.volume DESC`, labels the result “Most Bought,” and does not filter by a canonical instrument universe; breadth may include stale/odd symbols. | Volume is traded quantity, not net buying or investor demand. Rename “Most Traded by Volume,” add as-of and universe, and exclude invalid instruments. |
| P1 | Movers / market breadth | Gainers and losers use every eligible symbol on the latest global date; `gainers_n500` is actually the whole result, and Nifty 50 uses a hand-maintained list with fallback to all symbols when empty. `ad_ratio` then uses these counts. | Universe labels and A/D ratio can be wrong; that ratio feeds market sentiment. Drive membership from dated index constituents and return coverage counts. |
| P1 | Market status | Sentiment is an app score blending a price-change/count formula with a market-brain value; its detail claims “Market Brain Harmonized.” The gauge has no methodology, constituents, confidence, or timestamp. | A precise 0–100 score looks authoritative without explainable evidence or calibration. Show inputs and method/version, or present as a clearly named heuristic. |
| P1 | Portfolio/news scope | `renderNewsCards()` falls back to `allNews.slice(0, 3)` if there is no exact held-symbol match; headline tagging can be commodity/market-specific. | The Portfolio News toggle can show unrelated stories while implying a portfolio relationship. Use explicit entity/portfolio relevance and show why it matched; otherwise say none found. |
| P1 | Personalized insights | Portfolio summary is deterministic templated copy, and fallback text makes unverified claims such as “fully liquid,” “constructive astro-quant momentum,” and safeguards being active. Institutional deal alert query does not constrain by deal date. | AI branding and stale/unsupported statements create false confidence. Separate generated summary from rules, cite input data, limit deal lookback, and avoid claims without evidence. |
| P1 | Recommendation trust | Recommendation card defaults missing potential to `5.0`, target/SL to zero, parses JSON without local error handling, and renders server/database content into `innerHTML`. | Missing/invalid records can look like complete trade setups; DB-fed strings could also inject markup. Validate schema/levels and render escaped text. |
| P1 | F&O source data | DB has `option_chain_data` (775,328 rows), `pcr_summary` (11,106), and `participant_oi` (665); at latest date, NIFTY/BANKNIFTY option rows are only `morning` session, and latest PCR rows show `pcr=0.0` despite available OI. Thus data exists but requires completeness/session validation; it does not justify fabricated browser-side data. | Correct sources are available in principle, but freshness/session and zero-data semantics must be made explicit. |
| P1 | Latency / work | `_get_overview_data()` does database ranking, long-horizon joins, index/commodity history, news and up to 35-symbol technical/pattern passes before responding. `loadOverview()` fetches that whole payload even though discovery is hidden; `renderUserDashboard()` then independently fetches portfolio, risk, watchlist, recommendations and insights. | Unnecessary first-load work, larger payload and repeated access to SQLite delay primary value and create contention with ingestion. |
| P2 | DB size / retention | `market_data_v2.db` is 1,497,276,416 bytes (~1.39 GiB); 2.08M daily rows plus 3.61M intraday rows, 775k option-chain rows, 216k deals, 18.5k news. Intraday begins 2026-07-20 while fetch timestamps begin 2026-10-13, suggesting a bulk historical import; retention/partition policy is not clear from inspected source. | Backups, startup, disk I/O and query cache pressure can grow. Define retention by product need and archive cold data; do not delete history until ownership/retention is agreed. |
| P2 | Cache/concurrency | `_db()` sets WAL and `busy_timeout=30s`, but only 8 MB page cache per connection. Overview caching is process-local and 30 seconds; no query timing, cache hit ratio, lock-wait or API p95 instrumentation is visible here. | A single-user desktop may be fine at present, but behavior under simultaneous tabs/ingestion cannot be sized or safely optimized from assumptions. |
| P2 | UI density and navigation | Seven horizontal tabs sit above a dashboard with many equally emphasized panels; discovery itself stacks 8 sections, while separate F&O/indices/news tabs duplicate data. Inline styles and hand-coded templates dominate; errors are not consistently surfaced per panel. | High cognitive load and excessive scrolling. Users cannot quickly distinguish “what changed”, “what needs action”, or what is stale. |
| P2 | Accessibility | Tabs are clickable `<div>` elements without tablist/tab/tabpanel semantics or keyboard handling; gauge score is communicated via color/emoji and visual needle. | Keyboard/screen-reader use is incomplete; color alone does not communicate state. |

### Data storage and quality observations

- SQLite uses WAL, `synchronous=NORMAL`, a 30-second busy timeout, and appropriate `daily_prices` indexes including `(symbol, trade_date DESC)` and `trade_date`. The latest-date movers query plan uses the date index and a temporary B-tree for sorting. Avoid adding indexes without measuring their write and size cost.
- `news_sentiment` has title/source/published_at/score/label and deduplication/indexing support. Among 256 rows dated 2026-10-27 onward, 109 have raw score 0 and 118 are labeled NEUTRAL. Zero may be a real neutral score or a model/data fallback; the UI needs score confidence/model/version and coverage rather than assuming equivalent quality.
- `bulk_block_deals` has 216,355 rows and data through 2026-10-27. The AI insight query takes the latest three deals by date for held symbols, but has no “recent” limit and selects both buys and sells without netting or context.
- Date and source provenance are inconsistent across datasets: daily prices include `updated_at`, intraday has `fetched_at`, news has `fetched_at`, option chain has `fetched_at`, but the overview API generally omits these fields.
- No destructive DB operations were run. `PRAGMA quick_check` passed. The DB was inspected read-only.

## Product design proposal

### Make the first viewport answer four questions

1. Is the market open, closed, or delayed, and what is the latest data time?
2. What is happening to my portfolio today (value, P&L, daily move, currency and as-of time)?
3. What needs attention now (breached stop, near stop, concentration), ordered by severity?
4. What is the single most relevant next action or insight, and why?

Recommended dashboard hierarchy:

1. **Compact market header:** market state, NIFTY benchmark, breadth, data freshness; compact “show method” for sentiment.
2. **Portfolio summary:** value, invested capital, unrealized P&L, day P&L, last price time; “view positions.” Empty/guest state should say “No portfolio connected” rather than implying capital is liquid.
3. **Action queue:** breached stop first, near-stop second, concentration third. Each alert includes entry, CMP, stop, signed distance, direction, source/as-of, and a path to position details.
4. **Watchlist and relevant opportunities:** watchlist should load quickly. Recommendations need setup type, entry range, stop/target, calculated reward/risk, horizon, generated time, expiry, and supporting reasons; hide incomplete setups.
5. **Relevant news:** exact symbol/entity match, timestamp, source link, sentiment score/confidence; an explicit “market-wide” label when applicable. Never substitute broad news under a portfolio-specific label.

Move market exploration into purposeful tabs: **Discover**, **Derivatives**, **Commodities**, **Indices**, **News**. Within Discover, use sub-navigation/filters for movers, volume leaders, performance, and technical screens. Avoid showing the same quote as separate cards in multiple areas when a compact table suffices.

Use consistent card spacing and responsive grid; reserve green/red for measured change and severity, use text labels, avoid emoji-heavy headings, and make data age visible. Preserve user tab on refresh with URL hash/state; use true buttons with focus rings, keyboard arrow navigation, ARIA tab semantics, and reduced-motion support.

## Performance and data architecture plan

### Phase 0 — Stop misleading output (first release)

- Remove generated OI/PCR/rollover calculations. Read verified derivative rows only; if none are fresh/complete, show “No validated data for this session.”
- Remove synthetic intraday series. Query `intraday_prices` at the required interval and exact market date; if no data, show no chart and why.
- Fix stop-loss semantics for long vs short, distinguish crossed stop from proximity, and reconcile AI and risk-alert logic through one backend calculation.
- Add a page-level `as_of`, source, market session, and quote mode. Use correct currency/unit/contract metadata for all instruments.
- Correct “Most Bought” to “Most Traded by Volume”; use proper index membership and remove fallback-universe behavior.
- Remove the broad-news fallback; stop defaulting missing recommendation values to plausible-looking numbers.

### Phase 1 — Make first paint cheap and predictable

- Split the monolithic endpoint into a small dashboard summary and lazy tab endpoints (e.g. `overview/summary`, `overview/discovery`, `overview/derivatives`, `overview/news`). Keep a versioned payload contract.
- Render the summary first; fetch watchlist/alerts/news together in a bounded, authenticated dashboard response if ownership rules allow. Request recommendations only when the card is visible or after primary content renders.
- Move technical indicator/pattern computation out of the page request. Compute after ingestion or on demand with a cache keyed by `(symbol, date, algorithm_version)`.
- Use SQL filters/limits before Python materialization. Avoid transferring full cross-universe rows where only top 10 are rendered; keep sorting and filtering in SQL where possible.
- Add skeletons per card, independent stale/error states, retry controls, and stale-while-revalidate behavior. Do not hide the entire page behind one request.
- Use HTTP gzip (already imported in app; verify endpoint response path), ETags/revision tokens, and response-size logging before introducing additional storage layers.

### Phase 2 — Reliable provenance and precomputed views

- Add canonical `instrument_id`/symbol mapping with exchange, asset class, currency, quote unit, lot size, index membership validity dates, and expiry/continuous-contract rules.
- Store observation timestamp, exchange trade date, source/provider, source record key, ingestion time, validation status, session, and adjustment/roll metadata for every feed.
- Keep raw immutable source observations and normalized current/historical tables separately. Idempotent upserts use source identity plus instrument/time/session; do not overwrite provenance.
- Materialize small overview snapshots on ingestion close (e.g. latest quotes, breadth per universe, top movers, volume leaders) with `computed_at`, `source_max_at`, and algorithm version. UI reads snapshots, not a repeated full scan.
- Add quality gates: OHLC bounds, positive prices, duplicate keys, missing-symbol/session coverage, stale age, implausible return/outlier, corporate-action and futures-roll continuity checks. Quarantine failed rows and preserve raw values.
- Keep news score nullable when unavailable; track sentiment model/version/confidence and source URL. Calibrate or label scores using measured validation results.

### Phase 3 — Concurrency and growth

- Instrument endpoint p50/p95/p99, query duration, rows scanned/returned, DB busy/lock waits, WAL size/checkpoints, cache hit rate, response bytes, JS render time and tab usage.
- Establish a read-only connection policy for page queries; centralize SQLite settings rather than changing journal mode on every request. Keep short read transactions and batch writes during ingestion.
- Evaluate connection pooling carefully for the local server; SQLite WAL supports readers alongside a writer but still permits one writer. Serialize ingestion write batches and avoid long transactions.
- Set an explicit retention and archive policy for intraday and option chain data by product value and compliance requirements. Preserve raw/cold history on a separate file before compaction; measure backup/restore duration. Do not VACUUM or delete in the live DB without a backup/maintenance workflow.
- Introduce a dedicated analytical store only if measured concurrent query/write load outgrows SQLite. The README describes DuckDB, but the inspected live DB is SQLite; verify actual running architecture before designing around that claim.

## Suggested measurable targets

Baseline these with a repeatable local run first; targets are acceptance objectives, not current results.

| Metric | Initial target |
|---|---:|
| Dashboard shell + portfolio/alerts first usable | p95 ≤ 1.5 s on reference machine |
| Initial summary API | p95 ≤ 300 ms warm, ≤ 800 ms cold |
| Lazy tab API | p95 ≤ 500 ms warm |
| Freshness display | 100% of market-value panels show source/as-of/session |
| F&O fabricated metrics / synthetic chart points | 0 |
| Client JavaScript exception on overview flows | 0 in smoke pass |
| SQLite busy timeout/error under 10 concurrent dashboard reads + ingestion | 0 request failures; collect p95 lock waits |
| Payload budget | dashboard summary ≤ 100 KB compressed; lazy results paginated/limited |

## Implementation backlog

### P0 — Trust and correctness

1. Remove placeholder derivatives math and synthetic daily chart series.
2. Fix stop validation and shared risk-distance calculation; add breached state and long/short cases.
3. Add quote/source/as-of/session/unit metadata; accurately label EOD versus intraday.
4. Fix commodity continuity and percentage validation, particularly the supplied SILVER outlier.
5. Correct universe membership and rename volume leaders.
6. Make portfolio news matching explicit; remove unrelated fallback.
7. Validate/escape recommendation and insight content; never display missing levels as zero/default trade setups.

### P1 — Speed and resilience

1. Create lightweight initial dashboard contract; defer/lazy-load discovery, technicals, news and derivatives.
2. Eliminate per-load CPU indicator/pattern scans via versioned computed snapshot.
3. Consolidate overlapping dashboard portfolio/risk/insight reads and avoid duplicate price queries.
4. Add per-widget loading/error/empty/stale states and refresh controls.
5. Add server/browser timing instrumentation and representative concurrency scenarios.

### P2 — UX and scale

1. Rework information hierarchy around market context, portfolio, action queue, watchlist, and relevant news.
2. Reduce duplication and scrolling; add compact tables and visible filters.
3. Implement accessible tabs, keyboard support, responsive layouts and number/date formatting.
4. Add retention/archival jobs only after agreeing required history and recovery expectations.

## Questions for product/data owners before implementation

1. Should “live” mean broker/exchange streaming, scheduled delayed data, or latest local ingestion? What delay is acceptable per instrument class?
2. What exact source/provider and licensing terms apply to equities, index, MCX, options, participant OI, deals and news?
3. What does each commodity price unit mean in this product (per gram, kg, contract quote, continuous futures)? Which continuous-contract/roll methodology is intended?
4. Are positions simulated, imported Demat holdings, or actual broker holdings? What should “portfolio value” include (cash, fees, realized P&L, shorts, FX)?
5. Which index universes and historical membership dates define Nifty 50/500 and market breadth?
6. What is the approved meaning and calibration target for the 0–100 market score? Is it descriptive sentiment or a decision signal?
7. Which local machines and concurrency level should define performance baselines? What is an acceptable cold start after `START.bat`?
8. How much intraday/options history must remain online, and what backup/restore or audit retention is required?
9. Are recommendations informational research or intended trade instructions? What disclosure and risk language is required?

## Decision

Authorize a **correctness-first first sprint** limited to the Overview page and its API: (1) remove fabricated data, (2) fix stop semantics, (3) show source/freshness/units, and (4) remove incorrect portfolio-news fallback. Then capture a baseline and split/lazy-load the expensive panels. The supplied example should not be considered a trustworthy live-market dashboard until the P0 findings are resolved.
