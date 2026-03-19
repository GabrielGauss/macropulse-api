---
phase: 05-pipeline-quality-and-noise-reduction
plan: "02"
subsystem: testing
tags: [hmmlearn, arch, garch, hmm, pytest, websocket, convergence]

requires:
  - phase: 05-pipeline-quality-and-noise-reduction
    provides: "Phase 5 context — pipeline quality decisions, HMM and GARCH correctness fixes"

provides:
  - "HMM convergence guard in predict_proba and predict — raises RuntimeError on non-convergence"
  - "GARCH forecast_vol uses stored _arch_result.forecast() — no re-fit on inference"
  - "WebSocket broadcast_regime catches (WebSocketDisconnect, RuntimeError) not bare Exception"
  - "Two green tests: test_hmm_convergence_check, test_garch_no_refit_on_inference"

affects:
  - 05-pipeline-quality-and-noise-reduction
  - models
  - api

tech-stack:
  added: []
  patterns:
    - "Convergence guard pattern: hasattr(obj, 'monitor_') and not obj.monitor_.converged before inference"
    - "Stored-result inference: use self._arch_result.forecast() not arch_model().fit() per inference call"
    - "Narrow exception catching: catch specific exceptions (WebSocketDisconnect, RuntimeError) not bare Exception"

key-files:
  created:
    - tests/test_pipeline_quality.py
  modified:
    - models/hmm_model.py
    - models/garch_model.py
    - api/routes/websocket.py

key-decisions:
  - "HMM convergence guard uses hasattr() to handle legacy artifacts without monitor_ attribute"
  - "GARCH forecast_vol keeps returns_series parameter and len(clean)<30 fallback — only the re-fit block is replaced"
  - "WebSocketDisconnect already imported from fastapi — no new import needed for narrow except"
  - "Pre-existing frozenset bug in daily_pipeline.py (from 05-01) deferred — not caused by 05-02 changes"

patterns-established:
  - "Halt-on-non-convergence: raise RuntimeError with message including 'did not converge' before any inference"
  - "Log convergence pass: logger.info('HMM convergence check passed (converged=True)') on every successful call"

requirements-completed: [PIPE-03, PIPE-04]

duration: 20min
completed: 2026-03-19
---

# Phase 5 Plan 02: Pipeline Quality — HMM Convergence Guard and GARCH Inference Fix Summary

**HMM convergence guard halts pipeline on non-convergence; GARCH forecast uses stored result without re-fitting on every call**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-19T22:46:00Z
- **Completed:** 2026-03-19T23:06:11Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Added convergence guard to both `HMMModel.predict_proba` and `predict` — raises `RuntimeError` when `monitor_.converged=False` with `hasattr` guard for legacy artifacts
- Fixed `GARCHModel.forecast_vol` to use `self._arch_result.forecast()` instead of calling `arch_model().fit()` on every inference call — eliminates 2-5s re-fit overhead and restores reproducibility
- Narrowed broad `except Exception` in `broadcast_regime()` to `(WebSocketDisconnect, RuntimeError)` — stale connection cleanup preserved, silent swallowing of other exceptions eliminated
- Two green pytest tests for PIPE-03 and PIPE-04 with proper mock isolation (no disk artifacts, no real model fitting)

## Task Commits

Each task was committed atomically:

1. **Task 1: HMM convergence guard** - `5c1f660` (feat)
2. **Task 2: GARCH no-refit + WebSocket except narrowing** - `95ac9ff` (feat)
3. **Task 3: Tests for PIPE-03 and PIPE-04 (initial bad commit)** - `364f74b` (test — superseded)
4. **Task 3: Tests for PIPE-03 and PIPE-04 (correct implementation)** - `a7e70a6` (test)

_Note: TDD tasks committed RED (failing tests) then GREEN (implementations) then corrected test file._

## Files Created/Modified

- `models/hmm_model.py` — Added convergence guard to `predict_proba` and `predict` (+12 lines)
- `models/garch_model.py` — Replaced re-fit block in `forecast_vol` with stored-result call (-7 net lines)
- `api/routes/websocket.py` — Narrowed `except Exception` to `(WebSocketDisconnect, RuntimeError)`
- `tests/test_pipeline_quality.py` — PIPE-03 and PIPE-04 xfail stubs replaced with real implementations

## Decisions Made

- `hasattr(self.hmm, "monitor_")` guard used in convergence check to handle legacy HMM artifacts saved before hmmlearn 0.3 added `monitor_` — prevents AttributeError on old artifacts
- GARCH `returns_series` parameter and `len(clean) < 30` fallback kept unchanged — only the re-fit block replaced, no API break
- `WebSocketDisconnect` was already imported from `fastapi` in websocket.py — no new import required
- Pre-existing `frozenset.add()` bug in `daily_pipeline.py` (affecting PIPE-01/02 tests from 05-01) deferred to `deferred-items.md` — out of scope for 05-02

## Deviations from Plan

None — plan executed exactly as written. TDD flow followed: RED (failing tests) then GREEN (production code) then verified.

**Note on git state:** An intermediate commit (364f74b) captured the wrong test file version during Task 3. The correct implementation was committed in the follow-up commit (a7e70a6). All tests pass as required.

## Issues Encountered

- Git CRLF line-ending warnings (Windows environment) — cosmetic, no functional impact
- The 364f74b commit accidentally captured the old xfail stub file instead of the new test implementation. Fixed by editing the file directly and creating a new commit (a7e70a6)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- HMM convergence guard ready — pipeline will halt loudly on non-convergence rather than silently producing unreliable regime probabilities
- GARCH inference now reproducible and fast — no re-fit on every call
- WebSocket broadcast exception handling is precise — unexpected errors will surface rather than being silently swallowed
- 05-03 (threshold consolidation) can proceed

---
*Phase: 05-pipeline-quality-and-noise-reduction*
*Completed: 2026-03-19*
