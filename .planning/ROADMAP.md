# Roadmap: MacroPulse v1.0 — Ship-Ready

## Overview

MacroPulse v0 shipped with all core capabilities: regime signal pipeline, REST API, dashboard, marketing site, and API docs. This milestone resolves every known critical issue before monetization — hardcoded secrets, race conditions, UI bugs, and UX gaps — leaving a clean, correct, and visually consistent product.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (1.1, 1.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Security & Backend Bugs** - Eliminate hardcoded credentials, race conditions, and data correctness bugs (completed 2026-03-18)
- [x] **Phase 2: Dashboard UX** - Fix all user-facing dashboard issues and missing UI elements (completed 2026-03-18)
- [x] **Phase 3: Marketing Site** - Polish the public-facing site for conversion readiness (completed 2026-03-18)
- [x] **Phase 4: API Docs** - Consolidate and unify the API reference into one authoritative page (completed 2026-03-18)

## Phase Details

### Phase 1: Security & Backend Bugs
**Goal**: The backend is secure, correct, and free of known reliability issues
**Depends on**: Nothing (first phase)
**Requirements**: SEC-01, SEC-02, SEC-03, BUG-01, BUG-02
**Success Criteria** (what must be TRUE):
  1. The owner API key is not present anywhere in source code and is loaded exclusively from an environment variable
  2. A single alerting event fires exactly one alert — no duplicate notifications are observed
  3. Sending requests from multiple concurrent clients does not trigger a rate limit counter race (counter stays consistent under load)
  4. Data lag warnings trigger correctly after 3 days of staleness, not 2
  5. When one WebSocket client disconnects mid-broadcast, all other connected clients continue receiving messages normally
**Plans**: 4 plans

Plans:
- [ ] 01-env-example-audit-PLAN.md — Document all missing env vars in .env.example (SEC-01)
- [ ] 01-pipeline-fixes-PLAN.md — Remove duplicate regime alert call and fix data-lag threshold (SEC-02, BUG-01)
- [ ] 01-rate-limit-race-PLAN.md — Add per-IP asyncio.Lock to anonymous rate-limit counter (SEC-03)
- [x] 01-websocket-disconnect-PLAN.md — Snapshot _connections before broadcast iteration (BUG-02)

### Phase 2: Dashboard UX
**Goal**: The dashboard presents correct, complete information and provides the guidance users need
**Depends on**: Phase 1
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06, DASH-07
**Success Criteria** (what must be TRUE):
  1. An owner or paid-tier user loading the dashboard sees the calendar initialized to 1-year range on first render, not 30 days
  2. Clicking the 1Y or 2Y view button shifts the calendar scroll position to the correct start date immediately
  3. Clicking the header logo navigates to macropulse.live (home page)
  4. The AI commentary panel displays a lock icon and "Coming Soon" label with a countdown to the next pipeline run
  5. A help/guide button is visible in the dashboard nav header and opens contextual guidance when clicked
  6. A webhook setup guide is visible at the bottom of the dashboard without any additional navigation
  7. The regime card displays today's date and shows data that matches the most recent pipeline run
**Plans**: 2 plans

Plans:
- [ ] 02-01-PLAN.md — Create useCountdown hook, refactor Header.jsx (logo + hook), wire countdown into CommentaryCard (DASH-03, DASH-04)
- [ ] 02-02-PLAN.md — Fix calendar tier race, open WebhookGuide by default, fix RegimeCard date, verify all 7 DASH requirements (DASH-01, DASH-02, DASH-05, DASH-06, DASH-07)

### Phase 3: Marketing Site
**Goal**: The marketing site is accurate, interactive, and optimized for its first impression on potential customers
**Depends on**: Phase 2
**Requirements**: SITE-01, SITE-02, SITE-03, SITE-04
**Success Criteria** (what must be TRUE):
  1. The hero section leads with the strongest hook (narrative or code snippet, whichever was evaluated as more compelling)
  2. Clicking an open FAQ accordion item a second time collapses it closed
  3. The "Data Edge" section content is accurate and complete as verified by the owner
  4. The macro regime calendar on the marketing site opens in a 6-month centered view by default
**Plans**: 3 plans

Plans:
- [ ] 03-01-PLAN.md — Update hero H1 to "Stop predicting. Start allocating." and social meta tags (SITE-01)
- [ ] 03-02-PLAN.md — Change calendar default from 90 to 180 days; swap 6M button active state (SITE-04)
- [ ] 03-03-PLAN.md — Browser smoke-test all 4 SITE requirements (SITE-01, SITE-02, SITE-03, SITE-04)

### Phase 4: API Docs
**Goal**: Developers have one definitive, visually polished API reference to consult
**Depends on**: Phase 3
**Requirements**: DOCS-01, DOCS-02
**Success Criteria** (what must be TRUE):
  1. There is exactly one API docs page that contains all endpoint documentation — the detailed /api-docs content and the dashboard sidebar reference are unified
  2. The unified API docs page matches the dark visual style of macropulse.live (no light-mode or mismatched styling)
**Plans**: 2 plans

Plans:
- [ ] 04-01-sidebar-link-fix-PLAN.md — Fix "API Docs" sidebar link to point to macropulse.live/api-docs.html (DOCS-01)
- [ ] 04-02-api-docs-token-align-PLAN.md — Align api-docs.html CSS tokens to match index.html brand values (DOCS-02)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Security & Backend Bugs | 4/4 | Complete    | 2026-03-18 |
| 2. Dashboard UX | 1/2 | Complete    | 2026-03-18 |
| 3. Marketing Site | 2/3 | Complete    | 2026-03-18 |
| 4. API Docs | 2/2 | Complete    | 2026-03-18 |
| 5. Pipeline Quality and Noise Reduction | 4/4 | Complete    | 2026-03-19 |

### Phase 5: Pipeline Quality and Noise Reduction

**Goal:** Fix internal pipeline reliability — silent data failures, missing HMM convergence guards, scattered magic number thresholds. No user-facing API changes.
**Requirements**: PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05
**Depends on:** Phase 4
**Plans:** 4/4 plans complete

Plans:
- [ ] 05-00-PLAN.md — Install pytest, create test stubs and fixtures for all PIPE requirements (PIPE-01 through PIPE-05)
- [ ] 05-01-PLAN.md — Critical data halt (FRED/VIX), commodity column exclusion from PCA (PIPE-01, PIPE-02)
- [ ] 05-02-PLAN.md — HMM convergence guard, GARCH no-refit fix, narrow WebSocket except (PIPE-03, PIPE-04)
- [ ] 05-03-PLAN.md — Migrate 27 magic number thresholds to settings.py with env-var overrides (PIPE-05)

---
*Roadmap created: 2026-03-18 — v1.0 Ship-Ready milestone*
*Updated: 2026-03-18 — Phase 1 planned (4 plans)*
*Updated: 2026-03-18 — Phase 2 planned (2 plans)*
*Updated: 2026-03-18 — Phase 3 planned (3 plans)*
*Updated: 2026-03-18 — Phase 4 planned (2 plans)*
*Updated: 2026-03-19 — Phase 5 planned (4 plans)*

---

# Roadmap: MacroPulse v1.1 — Production Hardening

## Overview

v1.0 shipped a clean, visually consistent product with no known bugs. v1.1 closes the institutional deployment gap: secrets purged from git history, webhook bypass removed, auth endpoints hardened against brute-force, async DB driver replacing the sync bottleneck, Prometheus observability wired in, Paddle billing completed, GDPR erasure endpoint added, and automated test coverage established for all critical paths. Phases 6–12 deliver these capabilities in dependency order — security first, then DB, then observability, then billing and compliance, then tests that validate everything.

## Phases

- [ ] **Phase 6: Secrets, Webhooks, and Infrastructure Hardening** - Purge committed secrets, enforce webhook signature checking, and lock down infrastructure configuration
- [ ] **Phase 7: Auth Endpoint Rate Limiting** - Protect registration and OTP recovery flows against brute-force with persistent rate limit state
- [ ] **Phase 8: Async Database Migration** - Replace psycopg2 blocking driver with asyncpg throughout the codebase
- [ ] **Phase 9: Observability and Alerting** - Expose Prometheus metrics and fire automated pipeline failure alerts
- [ ] **Phase 10: Paddle Billing** - Complete Paddle checkout, webhook handling, and subscription lifecycle management
- [ ] **Phase 11: GDPR Compliance** - Implement user data erasure and data retention hygiene
- [ ] **Phase 12: Test Coverage** - Establish automated test suite covering auth, billing webhooks, rate limiting, and DB migrations

## Phase Details

### Phase 6: Secrets, Webhooks, and Infrastructure Hardening
**Goal**: The production environment contains no committed secrets and no webhook handler that can silently accept unauthenticated events
**Depends on**: Nothing (first v1.1 phase; v1.0 complete)
**Requirements**: SEC-10, SEC-11, SEC-12, SEC-13, SEC-20, SEC-21, SEC-22, SEC-40, SEC-41, SEC-42
**Success Criteria** (what must be TRUE):
  1. `git log` and `git show` across the full repository history contain no Brevo API key, MTA Ed25519 key, FRED key, or owner API key values
  2. Starting the API with `LS_WEBHOOK_SECRET` unset causes the Lemon Squeezy webhook endpoint to return 500 on every request — no event is processed
  3. Sending a Lemon Squeezy webhook request with a tampered signature returns 401 and logs the rejection; the event handler is never called
  4. The `model_artifacts` Docker volume is mounted with the `ro` flag in `docker-compose.yml` — a write attempt from the API container is rejected by the OS
  5. The application refuses to start when `ENV=production` and `CORS_ORIGINS` contains a wildcard `*`
**Plans**: 4 plans

Plans:
- [ ] 06-00-PLAN.md — Wave 0: test stubs for webhook and startup guard tests (SEC-20, SEC-21, SEC-22, SEC-42)
- [ ] 06-01-PLAN.md — Purge .env from git history, complete .env.example, create deployment guide (SEC-10, SEC-11, SEC-12, SEC-13)
- [ ] 06-02-PLAN.md — LS webhook fail-closed fix, startup guard for LS secret, Paddle replay verification (SEC-20, SEC-21, SEC-22)
- [ ] 06-03-PLAN.md — model_artifacts :ro volume, Nginx CSP header, CORS wildcard startup guard (SEC-40, SEC-41, SEC-42)

### Phase 7: Auth Endpoint Rate Limiting
**Goal**: Registration and OTP recovery flows reject brute-force attempts and survive process restarts without losing rate limit state
**Depends on**: Phase 6
**Requirements**: SEC-30, SEC-31, SEC-32, SEC-33
**Success Criteria** (what must be TRUE):
  1. Sending 6 registration attempts from the same IP within one hour results in a 429 response on the 6th attempt
  2. After 5 failed OTP verification attempts on the same email within 15 minutes, the OTP is invalidated and all subsequent attempts return a rejection until a new OTP is requested
  3. Rate limit counters survive an API container restart — the 6th attempt after a restart still returns 429 if 5 attempts were made before restart
  4. OTP recovery endpoints return a backoff-indicating response after the 3rd failure within the window
**Plans**: TBD

### Phase 8: Async Database Migration
**Goal**: All database I/O in the API runs on an async driver and never blocks FastAPI's event loop
**Depends on**: Phase 7
**Requirements**: DB-10, DB-11, DB-12, DB-13
**Success Criteria** (what must be TRUE):
  1. `database/connection.py` contains no import of `psycopg2` — `asyncpg` (or `psycopg3` async) is the only DB driver
  2. Every function in `database/queries.py` is declared `async def` — no synchronous DB calls exist anywhere in the API codebase
  3. Setting `DB_POOL_MIN=1` and `DB_POOL_MAX=5` via environment variables changes the connection pool limits without code changes
  4. The full existing test suite passes after the migration with no query regressions
**Plans**: TBD

### Phase 9: Observability and Alerting
**Goal**: Pipeline health is visible in a Grafana dashboard and failures trigger an automated alert within 5 minutes
**Depends on**: Phase 8
**Requirements**: OBS-01, OBS-02, OBS-03, OBS-04, OBS-05
**Success Criteria** (what must be TRUE):
  1. `GET /metrics` returns a valid Prometheus text exposition response containing `macropulse_api_requests_total`, `macropulse_pipeline_runs_total`, `macropulse_pipeline_last_success_timestamp`, `macropulse_active_api_keys`, and `macropulse_db_pool_size`
  2. Inserting a `status='failed'` row into `pipeline_runs` triggers an email alert to the owner address within 5 minutes
  3. When `macropulse_pipeline_last_success_timestamp` is more than 26 hours old, a staleness alert fires
  4. The Grafana dashboard JSON at `infrastructure/grafana/macropulse-dashboard.json` imports cleanly into a fresh Grafana instance and displays all five tracked metrics
**Plans**: TBD

### Phase 10: Paddle Billing
**Goal**: Users can subscribe via Paddle checkout, manage their subscription via the portal, and tier changes apply automatically from webhook events
**Depends on**: Phase 9
**Requirements**: BILL-01, BILL-02, BILL-03, BILL-04, BILL-05
**Success Criteria** (what must be TRUE):
  1. `POST /v1/billing/paddle/checkout` returns a Paddle-hosted checkout URL for both starter and pro tiers
  2. Receiving a `subscription.activated` Paddle webhook event upgrades the user's `api_keys.tier` to the subscribed tier within one processing cycle
  3. Receiving a `subscription.cancelled` Paddle webhook event reverts the user's API key tier to `free` within one processing cycle
  4. Sending the same Paddle webhook event ID twice results in only one DB write — the second delivery is deduplicated via `webhook_idempotency`
  5. `GET /v1/billing/paddle/portal` returns a valid Paddle customer portal URL for the authenticated user
**Plans**: TBD

### Phase 11: GDPR Compliance
**Goal**: Users can permanently delete their data and the system enforces retention limits on ephemeral verification records
**Depends on**: Phase 10
**Requirements**: GDPR-01, GDPR-02, GDPR-03, GDPR-04
**Success Criteria** (what must be TRUE):
  1. An authenticated user calling `DELETE /v1/auth/me` receives a success response; their `users` row has email replaced with `deleted_<uuid>@macropulse.invalid` and `deleted_at` timestamp set
  2. After account deletion, all `api_keys` for that user are deactivated — API calls with their keys return 401
  3. `macropulse.live/privacy` is a reachable page that documents data categories, retention periods, and erasure rights
  4. `email_verifications` rows older than 30 days are absent from the database after the daily cleanup job runs
**Plans**: TBD

### Phase 12: Test Coverage
**Goal**: Automated tests exist for all critical security and reliability paths and pass in CI against a real TimescaleDB schema
**Depends on**: Phase 11
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05
**Success Criteria** (what must be TRUE):
  1. Running `pytest` against the test suite produces passing tests for registration, OTP verification, recovery, and key rotation flows
  2. Paddle webhook tests cover `subscription.activated` and `subscription.cancelled` with both valid and invalid signatures — invalid signatures produce 401
  3. Lemon Squeezy webhook tests confirm valid-signature acceptance, invalid-signature rejection (401), and missing-secret rejection (500)
  4. Rate limit middleware tests confirm OTP lockout after 5 attempts and per-IP throttle on auth registration
  5. Running all migrations in `database/migrations/` against a fresh TimescaleDB schema in CI completes without errors
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 6 → 7 → 8 → 9 → 10 → 11 → 12

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 6. Secrets, Webhooks, and Infrastructure Hardening | 2/4 | In Progress|  |
| 7. Auth Endpoint Rate Limiting | 0/? | Not started | - |
| 8. Async Database Migration | 0/? | Not started | - |
| 9. Observability and Alerting | 0/? | Not started | - |
| 10. Paddle Billing | 0/? | Not started | - |
| 11. GDPR Compliance | 0/? | Not started | - |
| 12. Test Coverage | 0/? | Not started | - |

---
*v1.1 roadmap created: 2026-03-28 — Production Hardening milestone*
