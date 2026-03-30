---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: planning
stopped_at: Completed 08-00-PLAN.md — asyncpg pool + async connection layer (DB-10, DB-12)
last_updated: "2026-03-30T22:39:45Z"
last_activity: 2026-03-30 — Phase 8 Plan 00 complete (DB-10, DB-12 active)
progress:
  total_phases: 12
  completed_phases: 5
  total_plans: 21
  completed_plans: 20
---

# MacroPulse — State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-28)

**Core value:** Signal must be accurate, fresh, and delivered with zero friction
**Current focus:** v1.1 Production Hardening — roadmap complete, ready to plan Phase 6

## Current Position

Phase: Phase 8 — Async DB Migration (in progress)
Plan: 08-00 complete (asyncpg pool + connection layer)
Status: Phase 8 in progress — DB-10, DB-12 active; 08-01 (query migration) next
Last activity: 2026-03-30 — Phase 8 Plan 00 complete (asyncpg pool, lifespan wired)

Progress (v1.1): [███░░░░░░░] 25%

v1.0 complete: Phases 1–5 shipped (2026-03-18 to 2026-03-19)
Phase 6 complete: Secrets, Webhooks, Infra Hardening (2026-03-29)
Phase 7 complete: Auth Rate Limiting — SEC-30–33 (2026-03-30)
Phase 8 in progress: Plan 00 complete — asyncpg pool layer done

## v1.1 Phase Overview

| Phase | Goal | Requirements | Status |
|-------|------|--------------|--------|
| 6. Secrets, Webhooks, Infra | Purge secrets, enforce webhooks, lock infra config | SEC-10–13, SEC-20–22, SEC-40–42 | Complete |
| 7. Auth Rate Limiting | Brute-force protection for registration and OTP | SEC-30–33 | Complete |
| 8. Async DB Migration | Replace psycopg2 with asyncpg | DB-10–13 | In progress (08-00 done) |
| 9. Observability and Alerting | Prometheus metrics + pipeline failure alerts | OBS-01–05 | Not started |
| 10. Paddle Billing | Checkout, webhooks, subscription lifecycle | BILL-01–05 | Not started |
| 11. GDPR Compliance | User erasure endpoint, retention cleanup | GDPR-01–04 | Not started |
| 12. Test Coverage | Automated tests for auth, billing, rate limiting, migrations | TEST-01–05 | Not started |

## Performance Metrics

**Velocity (v1.0 reference):**
- Total plans completed: 14 (v1.0)
- Average duration: ~5 min/plan
- Total execution time: ~70 min

**By Phase (v1.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-security-backend-bugs | 1 | <1 min | <1 min |
| 02-dashboard-ux | 2 | ~7 min | ~3.5 min |
| 03-marketing-site | 3 | <3 min | <1 min |
| 04-api-docs | 2 | <2 min | <1 min |
| 05-pipeline-quality-and-noise-reduction | 4 | ~55 min | ~14 min |

*v1.1 metrics will be populated after plans execute*
| Phase 06-secrets-webhooks-infra-hardening P00 | 1 | 2 tasks | 2 files |
| Phase 06-secrets-webhooks-infra-hardening P02 | 6 | 2 tasks | 4 files |

## Accumulated Context

### Roadmap Evolution
- Phase 5 added: Pipeline Quality and Noise Reduction — fix silent data failures, HMM convergence gaps, consolidate magic number thresholds into config
- v1.1 roadmap created 2026-03-28: 7 phases (6–12), 35 requirements

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Pre-GSD]: Owner key placed in source code (expedient for v0) — must be removed in Phase 1
- [Pre-GSD]: Two alerting modules created accidentally — consolidate in Phase 1
- [Pre-GSD]: APScheduler in-process — single point of failure, revisit in later milestone
- [01-04]: Use list(_connections) snapshot to prevent RuntimeError in broadcast_regime() — simplest fix, zero overhead for small connection sets
- [Phase 01-security-backend-bugs]: Removed alert_regime_change() and its unused import; send_regime_change_alerts() is now the sole regime-change notification path (SEC-02)
- [Phase 01-security-backend-bugs]: Data-lag guard threshold corrected from > 3 to >= 3 so warnings fire on day 3 as specified (BUG-01)
- [Phase 01-security-backend-bugs]: OWNER_API_KEY placed in Auth section with generation command — deployers can now discover the master credential and generate a secure value without guessing
- [Phase 01-security-backend-bugs]: Lock scope tight: only counter state ops inside asyncio.Lock; await call_next stays outside to avoid holding lock across network I/O (SEC-03)
- [Phase 02-dashboard-ux]: useCountdown hook extracted as standalone named export — avoids duplicating setInterval logic across Header and CommentaryCard
- [Phase 02-dashboard-ux]: MacroPulse wordmark rendered as text anchor with inline styles in Header.jsx — consistent with existing inline-style pattern, no SVG asset needed (DASH-03)
- [Phase 02-dashboard-ux]: Tier null guard in RegimeCalendar useEffect prevents 30-day flash; raw tier prop passed from App.jsx alongside derived isFree boolean
- [Phase 02-dashboard-ux]: RegimeCard uses new Date() for today's date — card represents current regime state, not pipeline run timestamp (DASH-07)
- [Phase 03-marketing-site]: Calendar default changed to 180 days via renderRegimeCalendar argument and HTML button active class swap — setCalRange() unchanged as it correctly manages state on user interaction (SITE-04)
- [Phase 03-marketing-site]: 'allocating' as hero action word — contrarian framing positions MacroPulse against forecasting tools for quant/developer audience (SITE-01)
- [Phase 03-marketing-site]: No code changes in plan 03-03 — human-verify checkpoint confirmed all 4 SITE requirements visually in browser before phase close
- [Phase 04-api-docs]: API Docs sidebar link points to macropulse.live/api-docs.html — the hosted reference page replaces the raw GitHub repo URL (DOCS-01)
- [Phase 04-api-docs]: CSS tokens in api-docs.html now match index.html exactly — single source of truth for MacroPulse dark theme (DOCS-02)
- [Phase 05-pipeline-quality-and-noise-reduction]: pytest 9.0.2 installed as test runner; xfail stubs with pytest.fail('not implemented') keep suite green while implementation pending
- [Phase 05-pipeline-quality-and-noise-reduction]: conftest.py fixtures use MagicMock not real models — avoids DB/network dependencies at scaffold stage
- [Phase 05-pipeline-quality-and-noise-reduction]: HMM convergence guard uses hasattr() to handle legacy artifacts; raises RuntimeError on non-convergence before any inference output
- [Phase 05-pipeline-quality-and-noise-reduction]: GARCH forecast_vol uses stored _arch_result.forecast() — no re-fit on inference; keeps returns_series parameter and len(clean)<30 fallback (no API break)
- [Phase 05-pipeline-quality-and-noise-reduction]: broadcast_regime() catches (WebSocketDisconnect, RuntimeError) not bare Exception — stale connection cleanup preserved, unexpected errors now surface
- [Phase 05-pipeline-quality-and-noise-reduction]: Pipeline halts loudly (status=halted, stale_data=True) when critical series WALCL/DGS10/DGS2/VIX is missing or all-NaN — no silent degradation on non-negotiable inputs (PIPE-01)
- [Phase 05-pipeline-quality-and-noise-reduction]: Optional commodity columns (d_gold, d_oil, d_btc, d_eth) excluded from build_features() output when unavailable — not zero-filled — zero-fill corrupts signal with false stability (PIPE-02)
- [Phase 05-pipeline-quality-and-noise-reduction]: All 27 threshold fields use Field(validation_alias) so env vars override at runtime without code changes or redeployment
- [Phase 05-pipeline-quality-and-noise-reduction]: Function-local settings pattern: call get_settings() once at top of each function body — no module-level threshold constants — so env-var overrides in tests work correctly via cache_clear()
- [Phase 06-secrets-webhooks-infra-hardening]: xfail stubs with strict=True give suite green exit while blocking accidental pass-through once implemented
- [Phase 06-secrets-webhooks-infra-hardening]: No top-level app import in Phase 6 test stubs — lifespan triggers DB connection not available at test collection time
- [Phase 06-02]: _ls_verify_signature logs error (not warning) when failing closed — distinguishes severity from dev-mode warning
- [Phase 06-02]: test_paddle_replay_window patches PADDLE_WEBHOOK_SECRET to reach timestamp check — Paddle secret guard comes before timestamp check in verify_webhook()
- [Phase 06-02]: Settings.env uses AliasChoices('ENV', 'env') consistent with all 27 existing threshold fields
- [Phase 07-01]: Email extraction before check_auth_rate_limit in verify() and recover_verify() — email is the rate-limit identifier; this is not a side effect
- [Phase 07-01]: Patch database.queries.get_sync_cursor not database.connection.get_sync_cursor — queries.py imports get_sync_cursor at module level; patch must target the binding site
- [Phase 07-01]: recover() check fires before queries.get_user_by_email() — anti-enumeration: attacker must not learn if email exists before hitting the limit
- [Phase 08-00]: get_sync_cursor() compatibility shim added to connection.py — importable but raises RuntimeError at call time; keeps unmigrated modules (queries.py, routes) loadable until plan 08-01 migrates every call site
- [Phase 08-00]: JSONB codec registered per-connection via asyncpg create_pool init= callback — correct asyncpg pattern; set_type_codec must be called on each connection individually

### Pending Todos

- Phase 6 must begin immediately: `.env` in git history contains live Brevo API key and MTA Ed25519 private key
- Paddle approval pending — Phase 10 unblocks once approved

### Blockers/Concerns

- Live secrets in git history (Brevo API key, MTA Ed25519 key) — Phase 6 is highest priority
- Lemon Squeezy webhook has silent-accept vulnerability when LS_WEBHOOK_SECRET is unset — Phase 6
- Paddle approval still pending — Phase 10 may need to wait on external approval

## Session Continuity

Last session: 2026-03-30T22:39:45Z
Stopped at: Completed 08-00-PLAN.md — asyncpg pool + async connection layer (DB-10, DB-12 complete)
Resume file: None
