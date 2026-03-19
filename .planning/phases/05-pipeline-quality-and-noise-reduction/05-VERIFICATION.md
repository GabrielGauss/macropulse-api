---
phase: 05-pipeline-quality-and-noise-reduction
verified: 2026-03-19T23:55:00Z
status: passed
score: 12/12 must-haves verified
re_verification: false
---

# Phase 5: Pipeline Quality and Noise Reduction — Verification Report

**Phase Goal:** Fix internal pipeline reliability — silent data failures, missing HMM convergence guards, scattered magic number thresholds. No user-facing API changes. Signal output becomes more trustworthy.
**Verified:** 2026-03-19T23:55:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                            | Status     | Evidence                                                                                     |
|----|--------------------------------------------------------------------------------------------------|------------|----------------------------------------------------------------------------------------------|
| 1  | Pipeline halts (status='halted', stale_data=True) when WALCL/DGS10/DGS2 is missing or all-NaN  | VERIFIED   | `daily_pipeline.py` lines 133-146: `_missing_or_all_nan` guard + halt + alert               |
| 2  | Pipeline halts when VIX is missing or all-NaN                                                    | VERIFIED   | Same guard covers `_CRITICAL_MARKET_COLS = frozenset({"vix"})` at line 55                   |
| 3  | Optional commodity columns absent (not zero-filled) when data unavailable                        | VERIFIED   | `feature_engineering.py` lines 94-114: else branches only log warning, no column assignment  |
| 4  | Owner alert fires on critical-data halt via `alert_drift_warning('pipeline_halt_critical_data')` | VERIFIED   | `daily_pipeline.py` line 145: exact call present                                             |
| 5  | HMMModel.predict_proba raises RuntimeError when monitor_.converged is False                      | VERIFIED   | `hmm_model.py` lines 63-68: hasattr + not converged guard in both predict_proba and predict  |
| 6  | HMMModel.predict raises RuntimeError when monitor_.converged is False                            | VERIFIED   | `hmm_model.py` lines 73-78: identical guard in predict method                                |
| 7  | GARCHModel.forecast_vol uses stored _arch_result.forecast(), not arch_model().fit()              | VERIFIED   | `garch_model.py` lines 137-148: `self._arch_result.forecast(horizon=1, reindex=False)`       |
| 8  | broadcast_regime() catches (WebSocketDisconnect, RuntimeError) not bare Exception               | VERIFIED   | `websocket.py` line 55: `except (WebSocketDisconnect, RuntimeError):`                        |
| 9  | 27 threshold fields in settings.py with env-var validation_alias overrides                       | VERIFIED   | `config/settings.py` lines 120-236: 28 Field entries confirmed (28 validation_alias counts)  |
| 10 | Five source files use settings references instead of bare magic number literals                  | VERIFIED   | All five files import and call get_settings(); no catalogued bare literals remain             |
| 11 | GARCH_VOL_LOW env var overrides settings.garch_vol_low at runtime                               | VERIFIED   | test_settings_env_override: cache_clear + os.environ set + assertion passes                  |
| 12 | Full test suite: 7 passed, 0 xfailed, 0 errors, exit 0                                          | VERIFIED   | Actual test run: `7 passed in 3.70s`                                                         |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact                              | Expected                                              | Status     | Details                                                                              |
|---------------------------------------|-------------------------------------------------------|------------|--------------------------------------------------------------------------------------|
| `tests/test_pipeline_quality.py`      | 7 real tests (no xfail stubs)                         | VERIFIED   | All 7 tests are real implementations; no @pytest.mark.xfail decorators present       |
| `tests/conftest.py`                   | Shared fixtures for mocking                           | VERIFIED   | 5 fixtures: mock_fred_df, mock_market_df, mock_hmm_model_converged, mock_hmm_model_not_converged, mock_garch_model |
| `pytest.ini`                          | pytest configuration                                  | VERIFIED   | Present at project root with testpaths=tests                                          |
| `tests/__init__.py`                   | Package init                                          | VERIFIED   | Present (empty)                                                                       |
| `data/pipelines/daily_pipeline.py`    | Critical series guard, halt logic, available_cols PCA | VERIFIED   | _CRITICAL_FRED_COLS, _CRITICAL_MARKET_COLS, _missing_or_all_nan, halt block at 2b; available_cols filter at step 7 |
| `data/processing/feature_engineering.py` | No zero-fill for optional commodity columns        | VERIFIED   | Else branches for gold/oil/btc/eth only log warnings; no fallback column assignment   |
| `models/hmm_model.py`                 | Convergence guard in predict_proba and predict        | VERIFIED   | Lines 63-68, 73-78: hasattr + converged check raising RuntimeError                   |
| `models/garch_model.py`               | forecast_vol uses stored result; settings refs        | VERIFIED   | Line 140: `self._arch_result.forecast()`; classify_vol_state uses settings.*         |
| `api/routes/websocket.py`             | Narrowed except clause                                | VERIFIED   | Line 55: `except (WebSocketDisconnect, RuntimeError):`                                |
| `config/settings.py`                  | 27+ threshold fields with validation_alias            | VERIFIED   | 28 validation_alias entries found; all pipeline quality thresholds present with Field() |

### Key Link Verification

| From                               | To                                    | Via                                                    | Status   | Details                                                                    |
|------------------------------------|---------------------------------------|--------------------------------------------------------|----------|----------------------------------------------------------------------------|
| `data/pipelines/daily_pipeline.py` | `services/alerting.py`                | `alert_drift_warning('pipeline_halt_critical_data', 1.0, 0.0, ...)` | WIRED | Line 145: exact call present                                       |
| `data/pipelines/daily_pipeline.py` | `_log_run`                            | `_log_run('halted', data_lag=False, ...)`              | WIRED    | Line 144: call within halt block                                           |
| `data/processing/feature_engineering.py` | `daily_pipeline.py`             | `build_features()` returns DataFrame without d_gold/d_oil when unavailable | WIRED | Confirmed by test_optional_series_excluded_not_zeroed passing     |
| `models/hmm_model.py`              | `hmmlearn.hmm.GaussianHMM`            | `self.hmm.monitor_.converged` bool check               | WIRED    | Lines 63, 73: guard present in both inference methods                      |
| `models/garch_model.py`            | `arch ARCHModelResult`                | `self._arch_result.forecast(horizon=1, reindex=False)` | WIRED   | Line 140: direct call on stored result                                     |
| `config/settings.py`               | `services/orchestrator.py`            | `settings = get_settings(); settings.orchestrator_dominant_prob` | WIRED | Lines 84, 171, 250, 328, 457: get_settings() called in each function |
| `config/settings.py`               | `models/garch_model.py`               | `settings = get_settings(); settings.garch_vol_low`    | WIRED    | Line 181: settings used in classify_vol_state()                            |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                   | Status    | Evidence                                                                          |
|-------------|-------------|-----------------------------------------------------------------------------------------------|-----------|-----------------------------------------------------------------------------------|
| PIPE-01     | 05-00, 05-01 | Pipeline halts (stale_data:true) on missing/all-NaN critical FRED series; optional commodity columns excluded | SATISFIED | _missing_or_all_nan guard; feature_engineering.py no-zero-fill; 3 tests pass |
| PIPE-02     | 05-00, 05-01 | Pipeline halts (stale_data:true) when VIX data missing/all-NaN                               | SATISFIED | _CRITICAL_MARKET_COLS includes "vix"; test_vix_failure_halts_pipeline passes      |
| PIPE-03     | 05-00, 05-02 | HMM inference halts with RuntimeError when monitor_.converged is False                        | SATISFIED | hmm_model.py convergence guard in predict_proba and predict; test passes           |
| PIPE-04     | 05-00, 05-02 | GARCH forecast_vol() uses stored ARCHModelResult.forecast() instead of re-fitting             | SATISFIED | garch_model.py line 140; test_garch_no_refit_on_inference confirms no arch_model() call |
| PIPE-05     | 05-00, 05-03 | 20+ magic number thresholds in settings.py with env-var overrides                             | SATISFIED | 27 fields added with Field(validation_alias=...); 5 source files use settings; 2 tests pass |

All 5 phase requirements are SATISFIED. REQUIREMENTS.md marks all five as "Planned" — they are now COMPLETE by code evidence.

### Anti-Patterns Found

| File                               | Line | Pattern                              | Severity | Impact                                                                    |
|------------------------------------|------|--------------------------------------|----------|---------------------------------------------------------------------------|
| `data/pipelines/daily_pipeline.py` | 313  | `pass` after CLI WebSocket comment   | Info     | Intentional placeholder for future daily brief feature; no logic omitted  |
| `services/orchestrator.py`         | 96   | `0.20` bare literal                  | Info     | Intentional per plan — not in threshold catalogue; documented with inline comment referencing orchestrator_dominant_prob |

No blockers or warnings found. Both items are intentional and documented.

### Human Verification Required

No items require human verification for this phase. All goals are verifiable programmatically, and the tests confirm the behavioral contracts.

The following aspects were automatically confirmed:
- `pytest tests/test_pipeline_quality.py -v` → 7 passed in 3.70s
- All 27 threshold fields accessible at correct defaults via `get_settings()`
- `GARCH_VOL_LOW` env var overrides `garch_vol_low` at runtime (test_settings_env_override confirms)
- `_missing_or_all_nan()` frozenset.add() bug documented in deferred-items.md was fixed (line 60 uses `set(cols)` not `frozenset`)
- broadcast_regime exception narrowed to `(WebSocketDisconnect, RuntimeError)`

### Note on deferred-items.md

The `deferred-items.md` file documented a `frozenset.add()` AttributeError in `_missing_or_all_nan()` discovered mid-phase. The bug was fixed before the phase completed: `daily_pipeline.py` line 60 correctly initializes `missing` as `set[str] = set(cols) - set(df.columns)`, allowing `.add()`. The two affected tests (test_critical_fred_failure_halts, test_vix_failure_halts_pipeline) both pass, confirming the fix.

### Gaps Summary

No gaps. All must-haves verified. Phase goal fully achieved.

The pipeline now:
1. Halts loudly on critical data failures (WALCL, DGS10, DGS2, VIX) instead of producing signals from incomplete inputs
2. Excludes optional commodity columns rather than zero-filling them
3. Raises RuntimeError before HMM inference when the model did not converge
4. Uses the stored GARCH fit for inference instead of re-fitting on every call
5. Centralizes all 27 operational thresholds in settings.py with env-var overrides

---
_Verified: 2026-03-19T23:55:00Z_
_Verifier: Claude (gsd-verifier)_
