---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Completed 05-pipeline-quality-and-noise-reduction/05-03-PLAN.md
last_updated: "2026-03-19T23:19:54.829Z"
last_activity: "2026-03-18 — Completed plan 04: WebSocket disconnect fix (BUG-02)"
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 15
  completed_plans: 15
  percent: 75
---

# MacroPulse — State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-18)

**Core value:** Signal must be accurate, fresh, and delivered with zero friction
**Current focus:** v1.0 Ship-Ready — Phase 1: Security & Backend Bugs

## Current Position

Phase: 1 of 4 (Security & Backend Bugs)
Plan: 1 of 6
Status: In progress
Last activity: 2026-03-18 — Completed plan 04: WebSocket disconnect fix (BUG-02)

Progress: [████████░░] 75%

## Performance Metrics

**Velocity:**
- Total plans completed: 1
- Average duration: <1 min
- Total execution time: <1 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-security-backend-bugs | 1 | <1 min | <1 min |

**Recent Trend:**
- Last 5 plans: 01-04 (<1 min)
- Trend: —

*Updated after each plan completion*
| Phase 01-security-backend-bugs P01 | 5 | 2 tasks | 1 files |
| Phase 01-security-backend-bugs P01-env-example-audit | 8 | 1 tasks | 1 files |
| Phase 01-security-backend-bugs P01-rate-limit-race | 5 | 2 tasks | 1 files |
| Phase 02-dashboard-ux P01 | 2 | 3 tasks | 3 files |
| Phase 02-dashboard-ux P02 | 5min | 3 tasks | 4 files |
| Phase 03-marketing-site P02 | <1min | 1 tasks | 1 files |
| Phase 03-marketing-site P01 | <1min | 1 tasks | 1 files |
| Phase 03-marketing-site P03 | <1min | 1 tasks | 0 files |
| Phase 04-api-docs P01 | <1min | 1 tasks | 1 files |
| Phase 04-api-docs P02 | <1min | 1 tasks | 1 files |
| Phase 05-pipeline-quality-and-noise-reduction P00 | 15min | 3 tasks | 4 files |
| Phase 05-pipeline-quality-and-noise-reduction P02 | 20min | 3 tasks | 4 files |
| Phase 05-pipeline-quality-and-noise-reduction P01 | 5min | 3 tasks | 3 files |
| Phase 05-pipeline-quality-and-noise-reduction P03 | 15min | 3 tasks | 7 files |

## Accumulated Context

### Roadmap Evolution
- Phase 5 added: Pipeline Quality and Noise Reduction — fix silent data failures, HMM convergence gaps, consolidate magic number thresholds into config

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

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 1: Owner API key hardcoded at `api/auth.py:86` — must be removed before any public exposure
- Phase 2: Calendar viewDays initializes to 30 before tier resolves async — affects owner/paid UX on every load

## Session Continuity

Last session: 2026-03-19T23:16:15.976Z
Stopped at: Completed 05-pipeline-quality-and-noise-reduction/05-03-PLAN.md
Resume file: None
