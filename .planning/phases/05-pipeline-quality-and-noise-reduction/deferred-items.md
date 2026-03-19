# Deferred Items — Phase 05

## Pre-existing Issue: frozenset .add() bug in daily_pipeline.py

**Discovered during:** 05-02 execution (full suite run)
**File:** `data/pipelines/daily_pipeline.py`, line 68
**Error:** `AttributeError: 'frozenset' object has no attribute 'add'`

**Root cause:** `_missing_or_all_nan()` uses `frozenset` for `cols` parameter but calls `missing.add(col)`. `frozenset` is immutable — `set` should be used instead.

**Affected tests:** `test_critical_fred_failure_halts`, `test_vix_failure_halts_pipeline` (PIPE-01, PIPE-02 from plan 05-01)

**Status:** Pre-existing bug, not caused by 05-02 changes. Will be addressed in plan 05-01 GREEN phase or as a separate fix.
