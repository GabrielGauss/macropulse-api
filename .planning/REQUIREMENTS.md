# Requirements: MacroPulse

**Defined:** 2026-03-18
**Core Value:** Signal must be accurate, fresh, and delivered with zero friction

## v1 Requirements

Requirements for v1.0 Ship-Ready milestone.

### Dashboard

- [x] **DASH-01**: Calendar initializes to correct date range for user's tier (1Y for paid/owner) on mount, not 30d default
- [x] **DASH-02**: Calendar scroll position updates correctly when user switches between 1Y / 2Y view buttons
- [x] **DASH-03**: Header logo acts as clickable anchor link to macropulse.live home page
- [x] **DASH-04**: AI commentary panel displays lock icon and "Coming Soon" label with countdown to next pipeline run
- [x] **DASH-05**: Help/guide button is present in dashboard nav header and opens contextual guidance
- [x] **DASH-06**: Webhook setup guide is visible at the bottom of the dashboard
- [x] **DASH-07**: Current macro regime card displays today's date and fresh data (no stale dates)

### Marketing Site

- [x] **SITE-01**: Hero section uses the most compelling hook (code snippet evaluated and replaced if weaker than narrative alternative)
- [x] **SITE-02**: FAQ accordion items toggle closed when clicked a second time
- [x] **SITE-03**: "The Data Edge" section content is accurate and complete
- [x] **SITE-04**: Macro regime calendar on marketing site defaults to 6-month centered view

### API Docs

- [x] **DOCS-01**: Single unified API docs page merging the detailed /api-docs content with the dashboard API reference sidebar
- [ ] **DOCS-02**: Unified API docs page matches the dark visual style of macropulse.live

### Security

- [x] **SEC-01**: Owner API key sourced exclusively from environment variable, removed from source code
- [x] **SEC-02**: Duplicate alerting system consolidated — only one module fires alerts
- [x] **SEC-03**: Rate limit IP counter uses async-safe atomic operations (no TOCTOU race)

### Backend Bugs

- [x] **BUG-01**: Data lag guard threshold corrected to >3 days stale (was incorrectly >2 days)
- [x] **BUG-02**: WebSocket broadcast continues to all healthy clients when one client connection fails

## v2 Requirements

Deferred — next milestone (monetization).

### Payments

- **PAY-01**: User can subscribe to paid tier via Stripe/Paddle
- **PAY-02**: User can manage subscription (upgrade, cancel, billing portal)
- **PAY-03**: Paid tier features unlock immediately after successful payment

### User Self-Serve

- **USR-01**: User can register for free tier without contacting owner
- **USR-02**: User receives API key via email after registration
- **USR-03**: User can rotate their own API key from dashboard

### Testing

- **TEST-01**: Core pipeline steps have unit test coverage
- **TEST-02**: API endpoints have integration test coverage
- **TEST-03**: CI runs tests on every push

## Out of Scope

| Feature | Reason |
|---------|--------|
| Mobile app | Web-first product; mobile deferred indefinitely |
| Model retraining UI | CLI sufficient for ops; not a user-facing need |
| Real-time chat | Not core to the product value |
| OAuth / social login | Email/API-key auth sufficient for v1 |
| Multi-region deployment | Single VPS adequate for current scale |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SEC-01 | Phase 1 | Complete |
| SEC-02 | Phase 1 | Complete |
| SEC-03 | Phase 1 | Complete |
| BUG-01 | Phase 1 | Complete |
| BUG-02 | Phase 1 | Complete |
| DASH-01 | Phase 2 | Complete |
| DASH-02 | Phase 2 | Complete |
| DASH-03 | Phase 2 | Complete |
| DASH-04 | Phase 2 | Complete |
| DASH-05 | Phase 2 | Complete |
| DASH-06 | Phase 2 | Complete |
| DASH-07 | Phase 2 | Complete |
| SITE-01 | Phase 3 | Complete |
| SITE-02 | Phase 3 | Complete |
| SITE-03 | Phase 3 | Complete |
| SITE-04 | Phase 3 | Complete |
| DOCS-01 | Phase 4 | Complete |
| DOCS-02 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-03-18 — traceability updated after roadmap creation*
