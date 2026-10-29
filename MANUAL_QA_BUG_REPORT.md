# Vprofitables Manual QA Bug Report

**Review date:** 2026-10-27  
**Review type:** Read-only source review and review of project test/evaluation artifacts  
**Project reviewed:** `vprofitables` Python HTTP server, single-page dashboard, chat copilot, SQLite-backed trading tools

## Executive summary

The highest-risk defects are in authentication and authorization. The request router turns missing or invalid credentials into an administrator identity, while the UI and a checked-in test advertise a universal admin login. In addition, a very large set of portfolio, risk, and chat endpoints is explicitly public. In the trading workflow, forward signals can be staged with contradictory price levels and arbitrary risk/reward values; the tracker then evaluates the values without a validation gate.

The copilot has substantial quality gaps in its own evaluation evidence. A 1,000-scenario report records a **58.8% pass rate**, including 13% for conglomerate disambiguation, 30% for multi-tool reasoning, and 25% for data-absence checks. A separate tri-tier report records 45% overall and documents future-date questions being answered with current index data. A 100-case torture result records 20 failures, including screener routing and multi-intent decomposition errors.

## Scope and evidence quality

- Inspected the application entry point, authentication flow, API routing, tracker lifecycle, copilot routing, test code, stored evaluation results, startup scripts, and project manuals inventory.
- Reviewed existing test artifacts rather than executing the full suite. Several tests contact live services, use a large local database, or mutate data; the checkout is also already heavily modified.
- The repository had extensive pre-existing modified and untracked files. No application source files were changed during this review. This report is the only new file.
- Findings below are classified as **Confirmed** when directly visible in code or recorded in reproducible project test artifacts. Reported evaluation results should be rerun against a clean, versioned build before release decisions.

## Priority summary

| ID | Severity | Finding |
|---|---|---|
| QA-01 | Critical | Missing or invalid token receives ADMIN identity |
| QA-02 | Critical | Public endpoints expose account-specific trading and chat operations |
| QA-03 | Critical | Admin password/quick-login credentials are disclosed and accepted |
| QA-04 | High | Google authentication is inconsistent and one route can bypass Google token verification |
| QA-05 | High | Registration permits weak or empty passwords and promotes a public email to ADMIN |
| QA-06 | High | Tracker accepts invalid price geometry and trusts user-supplied R:R |
| QA-07 | High | Future-date request returns a current index quote rather than refusing unsupported data |
| QA-08 | High | Copilot entity disambiguation and intent routing fail frequently |
| QA-09 | Medium | API contract failures are logged but successful-looking payloads are still returned |
| QA-10 | Medium | API errors expose exception text and full tracebacks in server logs |
| QA-11 | Medium | Frontend JavaScript test is syntax-only and does not validate browser/runtime behavior |

## Detailed findings

### QA-01 — Missing or invalid credentials are assigned the ADMIN role

**Severity:** Critical  
**Status:** Confirmed by source inspection  
**Location:** `app.py`, `route()` around lines 1385–1398

**Reproduction:** Send any API request without an Authorization header, or with an expired/malformed bearer token. `decode_access_token()` returns `None`; `route()` then constructs a `current_user` dictionary with role `ADMIN`. The subsequent authentication check tests `not self.current_user`, which is now false.

**Observed behavior:** Requests that should be rejected anonymously continue as an administrator. This affects admin-only checks and the user identity attached to chat/order operations.

**Expected behavior:** Invalid/missing credentials stay unauthenticated. Public routes may continue anonymously, but protected routes must return 401; admin routes must independently require a verified ADMIN token.

**Why it fails:** A local-demo fallback is applied unconditionally, rather than being gated behind an explicit development-only mode, and the authorization check runs after this fallback.

**Recommended fix:** Remove the fallback from request routing. If a demo identity is required, enable it only behind an explicit local-only configuration that refuses to start in production. Check token validity before constructing user context and add route-level tests for missing, malformed, expired, USER, and ADMIN tokens.

### QA-02 — Account-specific endpoints are deliberately marked public

**Severity:** Critical  
**Status:** Confirmed by source inspection  
**Location:** `app.py`, `public_endpoints` around lines 1410–1425; examples include `portfolio_get`, `portfolio_add`, `portfolio_close`, `portfolio_delete`, `chat/execute_order`, `risk_settings_save`, and `analytics_data`.

**Reproduction:** Call these endpoints without a token. Even after fixing QA-01, the listed routes bypass the authentication-required check because they are explicitly present in `public_endpoints`.

**Observed behavior:** User-specific portfolio/trading functionality and paper-order execution are callable without an authenticated identity. Some handlers may then use a fallback user ID or shared state.

**Expected behavior:** Account and portfolio reads/writes, order execution, risk configuration, and private analytics require an authenticated user and enforce ownership at the data layer. Only genuinely public market/reference data and login/config endpoints should be anonymous.

**Why it fails:** Public access is configured as a broad endpoint allowlist without separating public market data from account-scoped operations.

**Recommended fix:** Default to protected and make a small explicit allowlist for public endpoints. Require user identity and ownership checks in each account-scoped handler. Add unauthenticated/other-user access tests for every portfolio and order route.

### QA-03 — Admin credentials and one-click access are exposed in the login page

**Severity:** Critical  
**Status:** Confirmed by source inspection and test code  
**Locations:** `pages/page_auth.py`, visible admin shortcut and credential copy; `app.py` around lines 1581–1592; `scripts/test_admin_auth.py`.

**Reproduction:** Open the login page: it displays the root admin username/password and a one-click login button. The handler submits `admin` / `admin123`. The backend also accepts a fixed list of master passwords for any ADMIN account and refreshes the stored hash to the supplied master password if it does not match.

**Observed behavior:** Anyone who can reach the page receives working administrative credentials; the backend preserves several universal admin password values.

**Expected behavior:** No default or master password is shipped or displayed. Administrator access is provisioned securely and can be reset by a controlled recovery mechanism.

**Why it fails:** Demo/test shortcuts are included in production-facing UI and the authentication backend has a password failover path that treats hard-coded values as valid.

**Recommended fix:** Remove the UI shortcut and displayed credentials, remove the master-key bypass, rotate any credentials that may have been used, and provision an admin only through a one-time setup flow. Reject startup in production when default credentials remain configured.

### QA-04 — Google authentication paths do not enforce the same verification contract

**Severity:** High  
**Status:** Confirmed by source inspection  
**Location:** `app.py`, `auth/login` around lines 1524–1553 and `auth/google` around lines 1600–1654.

**Reproduction:** The `auth/login` branch treats presence of a `google_sub` field as sufficient to look up/link/create a Google user; it does not verify a Google-issued ID token. A separate `auth/google` branch calls Google's tokeninfo endpoint. The client-side mock Google button sends a normal password login request, while the actual credential callback uses `auth/google`.

**Observed behavior:** Two endpoints claim Google sign-in with different trust rules. The legacy route accepts caller-supplied subject/email values, and UI behavior depends on which button/configuration branch is active.

**Expected behavior:** All Google sign-ins must pass one server-side token verification path with issuer, audience, expiry, verified email, and subject checks; account linking must require verified identity.

**Why it fails:** A test/simulation flow is still wired into the production login endpoint and runs alongside real OAuth verification.

**Recommended fix:** Remove `google_sub`-based login simulation from public auth. Centralize OAuth verification and account linking; test altered subject, unverified email, wrong audience, expired token, and existing-email linking.

### QA-05 — Signup allows empty/weak passwords and grants ADMIN based on a public email address

**Severity:** High  
**Status:** Confirmed by source inspection  
**Location:** `app.py`, `auth/signup` around lines 1473–1506.

**Reproduction:** Submit signup with a non-empty email and empty password. The backend stores `password_hash = None` and still returns an access token. Separately, the configured/default `ADMIN_EMAIL` is assigned ADMIN role during public signup if that email is not already registered.

**Observed behavior:** Accounts can be created with no password (login then cannot succeed using password), and the first registrant of the configured admin email receives ADMIN privileges without an invitation or proof-of-control in the password signup path.

**Expected behavior:** Password signup validates email and password policy; email ownership is verified before account activation; admin role is assigned only through a trusted provisioning path.

**Why it fails:** Required client fields are not enforced server-side, and signup role assignment is derived solely from a request-controlled email string.

**Recommended fix:** Enforce password length/strength and email validation on the backend, require verification before issuing a usable session, and eliminate admin promotion from ordinary signup. Add tests for empty password, duplicate email, unverified email, and admin-email registration.

### QA-06 — Tracker accepts contradictory prices and arbitrary risk/reward values

**Severity:** High  
**Status:** Confirmed by source inspection  
**Locations:** `core/tracker.py`, `stage_tracker_signal()` around lines 178–213 and subsequent insert/update statements; `core/unified_logic.py`, `evaluate_tracker_checkpoints()` around lines 1931 onward.

**Reproduction:** Call `stage_tracker_signal()` with `projected_entry_min >= projected_entry_max`, a stop above the entry for a long setup, a target below entry, negative values, or a supplied positive `rr_ratio` unrelated to the geometry. The function calculates `risk`/`reward` with `abs()` and trusts any positive supplied R:R.

**Observed behavior:** Invalid or internally contradictory trade plans can be persisted and evaluated as normal tracker signals. Incorrect stated R:R can drive allocation and user decisions.

**Expected behavior:** Reject invalid numeric values and enforce a direction-aware invariant before persistence (for long trades: positive prices, stop < entry corridor < target1 < target2; for short trades, the reverse). Derive R:R from actual levels or clearly label a separately supplied value.

**Why it fails:** No input validation exists, `abs()` hides reversed price ordering, and caller-provided R:R overrides the computed result.

**Recommended fix:** Add a centralized signal validator used by every API and autonomous caller; calculate risk/reward from the validated entry reference and stop/target; reject NaN/infinity and impossible dates; add boundary/property tests for long and short cases.

### QA-07 — Copilot answers future historical-price requests with current data

**Severity:** High  
**Status:** Confirmed by stored tri-tier evaluation artifact dated 2026-10-26  
**Evidence:** `tests/TRI_TIER_100_REPORT.md`, scenario #021.

**Reproduction:** Ask: “What is the exact closing price of NIFTY on Diwali 2028?”

**Observed behavior:** The system routes this to `INDEX_DETAIL` and responds with the current level and current trading date (2026-10-26), rather than saying the date is in the future and no closing price exists yet.

**Expected behavior:** Recognize that the requested date is future-dated and refuse to report a historical close. It may provide current data only if clearly labeled as current and explicitly requested as a substitute.

**Why it fails:** Intent routing appears to prioritize the index/entity phrase over temporal validity of the requested observation date.

**Recommended fix:** Parse requested dates before tool selection; classify future historical observations as unavailable; pass the requested date through data tools and require returned-date agreement before synthesis. Add tests for future, holiday, market-closed, and missing-history dates.

### QA-08 — Entity disambiguation, multi-intent decomposition, and negative-data handling fail frequently

**Severity:** High  
**Status:** Confirmed by project evaluation reports  
**Evidence:** `tests/STRESS_TEST_1000_REPORT.md`, `tests/TRI_TIER_100_REPORT.md`, and `tests/torture_100_results.json`.

**Observed failures:**

- The 1,000-case copilot report passes 58.8% overall. Conglomerate disambiguation passes 13%, multi-tool reasoning 30%, and data-absence checks 25%.
- “Tell me about Apollo” is answered as a portfolio position instead of disambiguating Apollo Hospitals (`APOLLOHOSP`) vs Apollo Tyres (`APOLLOTYRE`).
- “Compare TCS and INFY, and tell me which has better margins and which is safer if Nifty crashes 3%?” routes only to macro stress testing, losing comparison entities and margin analysis.
- 100-case torture results show missing decomposition for multi-part requests, screener queries routed to calendar/general intents, and empty/missing responses for some unsupported assets or out-of-domain questions.

**Expected behavior:** Resolve ambiguous entities with a clarification, decompose compound questions into all requested sub-intents, combine the results, and explicitly state when data is unavailable.

**Why it fails:** Rule-based routing contains competing precedence patterns; entity resolution can fall through to portfolio context; decomposition and response completeness are not enforced as postconditions.

**Recommended fix:** Make routing return a structured plan with entity candidates, date constraints, and a required list of sub-answers. Ask a clarification when entity confidence is low. Validate that every requested sub-intent has a result before generating a final response. Maintain regression fixtures from these stored failure cases.

### QA-09 — API contract violations are logged but not surfaced as request failures

**Severity:** Medium  
**Status:** Confirmed by source inspection  
**Location:** `app.py`, GET/POST handlers around lines 1285–1288 and 1362–1365; `core/api_contracts.py`.

**Reproduction:** Cause an endpoint response to omit a key declared in `CONTRACTS`. `validate_response()` raises `AssertionError`, but the handler catches every exception, prints `[CONTRACT ERROR]`, and still sends the original result with HTTP 200.

**Observed behavior:** Frontend receives a response known to violate the declared API contract and may fail later with missing fields; monitoring sees a successful status.

**Expected behavior:** In development/test, fail the request or test immediately. In production, return a controlled error or metric/alert that makes the contract break visible, rather than silently treating the payload as valid.

**Why it fails:** Validation is wrapped in a catch-and-log block with no error propagation or telemetry.

**Recommended fix:** Move contract checks into endpoint tests/CI and make production contract failures observable via structured error reporting. Avoid returning a 200 response for a known-invalid payload.

### QA-10 — API failures leak internal error details and tracebacks

**Severity:** Medium  
**Status:** Confirmed by source inspection  
**Location:** `app.py`, `do_POST()` around lines 1289–1295 and `do_GET()` around lines 1366 onward.

**Reproduction:** Trigger an exception in an API route. The server returns `{"error": str(e)}` to the caller and prints a full traceback.

**Observed behavior:** Internal paths, SQL/library details, and implementation messages may be exposed to unauthenticated callers or routine logs.

**Expected behavior:** Client receives a stable error code and safe message; detailed diagnostics go to access-controlled logs with a request/correlation ID.

**Why it fails:** Generic exception handlers serialize raw exception text and dump tracebacks directly.

**Recommended fix:** Separate expected validation/authentication errors from unexpected exceptions; return generic 4xx/5xx payloads and use structured, restricted logging with sensitive fields redacted.

### QA-11 — JavaScript integrity check does not verify runtime behavior

**Severity:** Medium  
**Status:** Confirmed by test implementation  
**Location:** `tests/test_js_integrity.py` and `core/js_guard.py`.

**Reproduction:** The suite calls `validate_all_pages()`, which checks JavaScript syntax using `node --check` when Node is available and falls back to a brace checker. It does not load the page in a browser or assert that API calls, handlers, navigation, or rendering work.

**Observed behavior:** A green result only establishes syntax/basic delimiter validity. It cannot catch missing DOM nodes, wrong endpoint payloads, broken auth navigation, browser compatibility issues, or runtime exceptions.

**Expected behavior:** Keep syntax checks as a fast preflight, supplemented by browser smoke tests for login, navigation, key dashboard pages, and a representative request/error path.

**Why it fails:** The test name and startup message claim broad frontend integrity while the test has no browser/runtime stage.

**Recommended fix:** Rename the check to make its syntax-only scope clear and add a small deterministic browser smoke suite with mocked API responses and console-error assertions.

## Recommended remediation order

1. Fix QA-01 and QA-02 first: remove anonymous ADMIN assignment and protect all account/order routes.
2. Remove exposed/default credentials and master-key password fallback (QA-03); rotate existing credentials.
3. Fix signup role assignment and unify Google verification (QA-04, QA-05).
4. Add strict tracker signal validation before persistence (QA-06).
5. Fix temporal validation, entity disambiguation, and multi-intent completeness in copilot routing (QA-07, QA-08).
6. Make contract and runtime failures visible and safe (QA-09–QA-11).

## Verification needed after fixes

- Anonymous, invalid-token, expired-token, FREE-user, and ADMIN-user permission matrix for every API route.
- Cross-user portfolio/order ownership checks.
- Signup/auth tests for empty/weak passwords, admin role assignment, Google audience/signature/email verification, and account linking.
- Tracker geometry boundary tests for long/short setups and malformed numeric/date values.
- Copilot regression set for the exact cases in QA-07 and QA-08, with assertions over intent plan, data provenance/date, and complete sub-answer coverage.
- Browser smoke test covering login/signup, route navigation, portfolio read/write, chat, and failed API behavior.
