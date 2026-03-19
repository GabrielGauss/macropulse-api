---
phase: 05-pipeline-quality-and-noise-reduction
plan: "03"
subsystem: config
tags: [pydantic-settings, thresholds, env-vars, garch, orchestrator, signals, pipeline]

# Dependency graph
requires:
  - phase: 05-pipeline-quality-and-noise-reduction
    provides: 05-01 and 05-02 GARCH/HMM implementation and pipeline halt guards
provides:
  - 27 named threshold fields in settings.py with env-var overrides
  - Magic number literals removed from orchestrator, signals, garch, regime_classifier, daily_pipeline
  - PIPE-05 tests passing (test_thresholds_in_settings, test_settings_env_override)
affects: [future-phases-using-thresholds, operational-tuning]

# Tech tracking
tech-stack:
  added: []
  patterns: [settings-driven-thresholds, validation_alias-env-override, get_settings-per-function]

key-files:
  created: []
  modified:
    - config/settings.py
    - data/pipelines/daily_pipeline.py
    - services/orchestrator.py
    - services/signals.py
    - models/garch_model.py
    - models/regime_classifier.py
    - tests/test_pipeline_quality.py

key-decisions:
  - "All 27 threshold fields use Field(validation_alias=...) so env vars override at runtime without code changes"
  - "orchestrator.py: 0.20 risk_off_suppressed threshold left as literal (not in RESEARCH.md catalogue); documented with inline comment referencing orchestrator_dominant_prob"
  - "build_signal_range() confidence logic also migrated (was duplicate of _persistence_and_confidence) using a local s = get_settings() to avoid a re-import"
  - "get_settings.cache_clear() pattern documented in docstring for test isolation"

patterns-established:
  - "Threshold pattern: Field(default=X, validation_alias='ENV_VAR_NAME') with inline doc comment explaining purpose and default rationale"
  - "Function-local settings: call settings = get_settings() once at top of each function body that needs thresholds — no module-level threshold constants"

requirements-completed: [PIPE-05]

# Metrics
duration: 15min
completed: 2026-03-19
---

# Phase 5 Plan 03: Magic Number Threshold Migration Summary

**27 operational threshold literals extracted from five source files into settings.py as named, env-var-overridable fields — any decision boundary now tunable without redeployment**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-19T23:15:00Z
- **Completed:** 2026-03-19T23:30:00Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Added 27 threshold fields to Settings class with pydantic Field(validation_alias) env-var overrides and inline doc comments
- Removed all catalogued magic number literals from orchestrator.py, signals.py, garch_model.py, regime_classifier.py, and daily_pipeline.py — each function now calls get_settings() locally
- PIPE-05 tests green: test_thresholds_in_settings verifies 14 representative defaults; test_settings_env_override confirms GARCH_VOL_LOW=0.3 override works at runtime

## Task Commits

Each task was committed atomically:

1. **Task 1: Add 27 threshold fields to config/settings.py** - `8dfd6ae` (feat)
2. **Task 2: Replace magic number literals in five source files** - `1db39d8` (feat)
3. **Task 3: Write two green tests for PIPE-05** - `3e9dc99` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `config/settings.py` - Added `from pydantic import Field`, 27 new threshold fields in "Pipeline quality thresholds" section, cache_clear note in docstring
- `services/orchestrator.py` - Added get_settings import; removed _MIN_ROWS/_DOMINANT_PROB; added settings = get_settings() in analyse_equity/rates/credit/liquidity/composite_analysis; replaced all catalogued literals
- `services/signals.py` - Added settings = get_settings() in _persistence_and_confidence() and _net_liquidity_signals(); replaced confidence and liquidity trend literals including duplicate in build_signal_range()
- `models/garch_model.py` - Removed _VOL_LOW/NORMAL/ELEVATED; added settings = get_settings() in classify_vol_state(); uses settings.garch_vol_* comparisons
- `models/regime_classifier.py` - Added settings = get_settings() in classify_volatility(); uses settings.vix_diff_elevated/compressed
- `data/pipelines/daily_pipeline.py` - Removed _DRIFT_VARIANCE_WARN/PERSISTENCE_WARN/FEATURE_SHIFT_WARN module constants; uses settings.pipeline_drift_* in alert section (settings already called at line 108)
- `tests/test_pipeline_quality.py` - Replaced two xfail stubs with real implementations; full suite 7 passed

## Decisions Made
- All 27 threshold fields use Field(validation_alias="ENV_VAR_NAME") — env vars override at runtime without code changes or redeployment
- The 0.20 risk_off_suppressed threshold in orchestrator.py analyse_equity is NOT in the RESEARCH.md catalogue; left as literal with inline comment referencing orchestrator_dominant_prob for context
- build_signal_range() had a duplicate confidence threshold block; migrated it too (same logic, same settings fields) — consistent with the plan intent even though that function wasn't explicitly listed
- get_settings() called once per function body (not module-level) so env-var overrides in tests take effect correctly when cache is cleared

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Migrated duplicate confidence logic in build_signal_range()**
- **Found during:** Task 2 (signals.py magic number replacement)
- **Issue:** signals.py has confidence threshold logic in both _persistence_and_confidence() and build_signal_range(); only the former was listed in the plan. Leaving the duplicate as a bare literal would mean the env-var override only worked for the single-date path, not the range path.
- **Fix:** Added `s = get_settings()` in the build_signal_range() loop and replaced the 0.70/0.50 literals with s.signal_confidence_high_threshold and s.signal_confidence_moderate_threshold
- **Files modified:** services/signals.py
- **Verification:** Import smoke test passes; behaviour identical with default settings values
- **Committed in:** 1db39d8 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing critical consistency fix)
**Impact on plan:** Auto-fix ensures env-var override works for both API paths (single date and date range). No scope creep.

## Issues Encountered
None — all tasks executed smoothly against existing file structure. No import errors, no test failures.

## User Setup Required
None — no external service configuration required. All new thresholds have sensible defaults. To override, set env vars (e.g., `GARCH_VOL_LOW=0.3`) in the deployment environment or .env file.

## Next Phase Readiness
- Phase 5 plan 03 complete — all 5 plans in Phase 5 are now done
- All 27 operational thresholds are auditable in config/settings.py and overridable via env vars
- Full test suite: 7 passed, 0 xfailed, exit 0

## Self-Check: PASSED

All files verified present. All commits verified in git log: 8dfd6ae, 1db39d8, 3e9dc99.

---
*Phase: 05-pipeline-quality-and-noise-reduction*
*Completed: 2026-03-19*
