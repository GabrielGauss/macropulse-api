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
