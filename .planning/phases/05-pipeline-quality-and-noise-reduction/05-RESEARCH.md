# Phase 5: Pipeline Quality and Noise Reduction — Research

**Researched:** 2026-03-19
**Domain:** Python data pipeline reliability — error propagation, HMM convergence, config consolidation, PCA input hygiene
**Confidence:** HIGH (all findings derived from direct code inspection)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Critical data failure policy**
- When WALCL (FRED) or VIX (yfinance) fails to fetch, halt the pipeline entirely
- No signal is written for that run
- API continues to serve the last valid signal with a `stale_data: true` flag
- Owner alert fires on halt
- "Critical" series: WALCL, DGS10, DGS2, VIX — these are non-negotiable inputs
- "Optional" series: gold, oil, BTC, ETH — handled separately (see below)

**Optional commodity features (gold, oil, BTC, ETH)**
- When any commodity fetch fails or returns NaN, exclude that column from PCA input entirely
- Do NOT zero-fill — synthetic zeros bias PCA factors
- Model runs with fewer inputs but all real ones
- No pipeline halt for commodity failures — they are genuinely optional

**HMM convergence policy**
- If HMM EM fails to converge during inference, halt the pipeline — same policy as data failure
- Non-convergence = unreliable regime probabilities = worse than no signal
- Convergence check must run before any inference output is trusted
- Log the convergence monitor state on every run (converged or not)

**Threshold consolidation**
- All 20+ magic number thresholds move to settings.py with documented defaults
- Each threshold controllable via environment variable (no code changes needed to tune)
- Thresholds to consolidate: confidence levels (0.70/0.50), liquidity trend counts (12/20), drift warnings (0.10/0.97/1.5), orchestrator signal thresholds (0.50/0.20/0.60/0.002 etc.), VIX vol thresholds, GARCH vol state bounds, conviction bounds
- Each setting gets a comment explaining its meaning and the reasoning for the default value

### Claude's Discretion
- Exact naming of new settings keys
- Whether GARCH refit-on-inference is fixed in this phase or deferred (fix it if clean, defer if risky)
- Whether to fix the duplicate persistence calculation (signals.py vs orchestrator.py) in this phase
- Exact log message format for convergence/failure events

### Deferred Ideas (OUT OF SCOPE)
- Statistical significance tests for trend detection in orchestrator (replace slope sign with t-test) — more involved, separate phase
- Feature shift drift baseline fixed to training date (not moving window) — model versioning work, future phase
- Duplicate persistence calculation consolidation (signals.py vs orchestrator.py) — Claude's discretion whether to include
</user_constraints>

---

## Summary

This phase is a pure internal quality pass — no API contracts change, no new dependencies are needed. Every change is either: (a) promoting a silent failure to a loud halt, (b) moving a literal number out of logic code into configuration, or (c) replacing a broad `except Exception` with the specific exception type that is actually expected. The codebase already has all the infrastructure needed: `ValidationReport` for structured errors, `alerting.py` for owner notifications, `pydantic-settings` in `config/settings.py` for typed env-var config, and a status-dict return convention from `daily_pipeline.py`.

The largest single change is the threshold migration: 20+ magic numbers scattered across five files need to move to `settings.py`. This is the riskiest part only because of volume — each individual move is mechanical and low-risk, but the total surface area is wide. The HMM convergence guard is the most impactful safety fix: the model's `monitor_.converged` attribute is already populated by hmmlearn after `fit()` and also available on the loaded artifact, so the check is a one-liner guard before `predict_proba`.

The GARCH `forecast_vol()` re-fit issue is real and fixable. The method currently re-constructs an `arch_model` and calls `model.fit()` on every inference call, discarding the stored `_arch_result`. The fix is to use `_arch_result.forecast()` directly on the already-fitted result stored on the instance, removing the redundant fit entirely.

**Primary recommendation:** Implement as four sequential plans: (1) critical data halt + stale_data flag, (2) HMM convergence guard, (3) threshold migration to settings.py, (4) GARCH forecast fix + broad-except narrowing.

---

## Standard Stack

### Core (already installed — no new dependencies required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic-settings | >=2.2 | Typed env-var config with `Field` defaults | Already the project pattern in `settings.py` |
| hmmlearn | >=0.3 | GaussianHMM — `monitor_.converged` attribute exists post-fit | Already in use |
| arch | >=6.0 | GARCH — `ARCHModelResult.forecast()` works without re-fitting | Already in use |

No new packages needed. All changes are within the existing stack.

---

## Architecture Patterns

### Established Project Patterns (HIGH confidence — direct code inspection)

**Pattern 1: Pydantic-Settings Field**

New thresholds follow the exact form already in `settings.py`:
```python
# Source: config/settings.py (direct inspection)
# Minimum trailing days for a regime count as "EXPANDING" trend
signal_liquidity_trend_min_pos: int = Field(
    default=12,
    validation_alias="SIGNAL_LIQUIDITY_TREND_MIN_POS",
)
```
`SettingsConfigDict` with `case_sensitive=False` means env vars are matched case-insensitively. The `Field(default=..., validation_alias=...)` pattern gives each threshold an explicit env-var override name.

**Pattern 2: Pipeline Halt via RuntimeError + _log_run**

The existing halt pattern in `daily_pipeline.py` is:
```python
# Source: data/pipelines/daily_pipeline.py lines 108-113, 118-123
except Exception as exc:
    duration = time.monotonic() - t0
    logger.error("Data fetch failed: %s", exc)
    _log_run("failed", data_lag=False, duration=duration, error=str(exc), model_version=version)
    raise
```
Critical-series halts should follow the same shape: log, call `_log_run("failed", ...)`, then raise (or return a `{"status": "halted", ...}` dict — see stale_data pattern below).

**Pattern 3: Status Dict with Flag**

The existing `data_lag` pattern shows how the pipeline communicates partial state:
```python
# Source: data/pipelines/daily_pipeline.py lines 150-152
_log_run("partial", data_lag=True, duration=duration, model_version=version)
return {"status": "data_lag", "timestamp": today.isoformat()}
```
The new `stale_data: true` flag should follow the same return-dict convention. The API layer that calls the pipeline can then read `result.get("stale_data")` to decide what to serve.

**Pattern 4: ValidationReport**

`services/validation.py` already defines:
```python
# Source: services/validation.py lines 20-35
@dataclass
class ValidationReport:
    passed: bool = True
    warnings: list[str]
    errors: list[str]

    def warn(self, msg: str) -> None: ...
    def fail(self, msg: str) -> None: ...
```
This is the right vehicle for pre-halt validation. A new `_validate_critical_series(fred_df, market_df)` function can return a `ValidationReport`, and the pipeline halts when `report.passed is False`.

**Pattern 5: hmmlearn Monitor**

```python
# Source: models/hmm_model.py line 51 — already logged at fit time
self.hmm.monitor_.converged  # bool, populated by GaussianHMM.fit()
```
The same attribute is accessible on the loaded artifact because the full `GaussianHMM` object (including its `monitor_` attribute) is joblib-serialized. The convergence guard in `predict_proba` and `predict` is:
```python
if not self.hmm.monitor_.converged:
    raise RuntimeError(
        "HMM did not converge during training. "
        "Inference output is unreliable. Halting pipeline."
    )
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HMM convergence detection | Custom log-likelihood delta tracking | `hmm.monitor_.converged` (hmmlearn built-in) | Already set after fit(); persists in saved artifact |
| GARCH 1-step forecast | Re-fit model from scratch | `self._arch_result.forecast(horizon=1, reindex=False)` (arch built-in) | Result object already cached; forecast() uses stored params |
| Env-var overridable thresholds | Custom config parser or .env reader | `pydantic-settings Field(default=..., validation_alias=...)` | Already the project pattern; no new code needed |
| Alert on pipeline halt | New alerting path | `alert_drift_warning()` from `services/alerting.py` | Existing SMTP + webhook delivery; reuse with a new metric name `"pipeline_halt"` |

**Key insight:** Every problem in this phase has an existing solution in the codebase or the already-installed library. The work is wiring, not invention.

---

## Common Pitfalls

### Pitfall 1: PCA Zero-Fill Bias
**What goes wrong:** Optional commodity columns (d_gold, d_oil, d_btc, d_eth) are currently zero-filled in `feature_engineering.py` lines 116-121 when the fetch fails. PCA treats zero as a real observation. A constant-zero column has zero variance and contributes nothing useful, but can deflate the variance captured by existing components, shifting the factor loadings.
**Why it happens:** Zero-fill was chosen as "safe" but synthetic zeros are not neutral — they are fake observations at exactly the mean of a mean-zero series, which biases covariance estimates toward zero for those pairs.
**How to avoid:** Exclude the column from the matrix passed to `pca_model.transform()` entirely. The PCA artifact was fitted with a specific column set; the transform must receive the same columns. The solution is: track which optional columns are present at runtime, filter `MODEL_FEATURE_COLS` to the available set before calling `transform()`. For the loaded v1/v2 model to still work, this requires the PCA artifact to have been fitted without those columns OR a compatibility shim. See Open Questions #1.
**Warning signs:** PCA explained variance ratio changes significantly between runs when commodity data is unavailable.

### Pitfall 2: hmmlearn Monitor on Loaded Artifact
**What goes wrong:** `HMMModel.load()` uses `joblib.load()` on the raw `GaussianHMM` object. If the artifact was saved before hmmlearn 0.3 (which added `monitor_`), `monitor_` may not exist.
**Why it happens:** joblib restores the exact Python object state. If `monitor_` was not present when the artifact was saved, `hasattr(hmm, "monitor_")` will be False.
**How to avoid:** Guard the convergence check: `if hasattr(self.hmm, "monitor_") and not self.hmm.monitor_.converged`. For the common case (fresh artifacts), this is a no-op. For legacy artifacts, log a warning and skip the halt.
**Warning signs:** `AttributeError: 'GaussianHMM' object has no attribute 'monitor_'` on load.

### Pitfall 3: GARCH forecast_vol Re-fit
**What goes wrong:** `GARCHModel.forecast_vol()` (lines 142-158) constructs a new `arch_model`, calls `model.fit()`, and discards the stored `_arch_result`. This means: (a) every inference is ~2-5 seconds slower, (b) the parameters used for classification may differ from those used at training time, breaking reproducibility.
**Root cause:** The method was written to accept a fresh returns series to "reflect the most recent observations" — but the intent of the GARCH model is to use the trained parameters and simply forecast forward. The fix is to call `self._arch_result.forecast(horizon=1, reindex=False)` directly, which uses the stored fit parameters.
**Warning signs:** Pipeline runs slower than expected; GARCH vol state changes erratically between runs with identical input data.

### Pitfall 4: Broad `except Exception: pass` in WebSocket Broadcast
**What goes wrong:** `broadcast_regime()` in `api/routes/websocket.py` line 55 catches `Exception` broadly and silently discards stale connections. This is actually correct for a connection that was closed: the expected exception is `WebSocketDisconnect` or `starlette.websockets.WebSocketState`-related errors.
**How to avoid:** Replace `except Exception` with `except (WebSocketDisconnect, RuntimeError)` — RuntimeError covers send-on-closed-connection cases in Starlette. This is a narrowing not a removal; the stale-connection cleanup logic stays.

### Pitfall 5: settings.py lru_cache Invalidation
**What goes wrong:** `get_settings()` is decorated with `@lru_cache(maxsize=1)`. If tests or scripts call `get_settings()` before setting environment variables, the cached instance will have wrong values for the new threshold fields.
**How to avoid:** This is pre-existing behavior — no change needed. Just document in comments that tests must set env vars before the first import or call `get_settings.cache_clear()`.

### Pitfall 6: Critical FRED Series — Fetch vs. Column Presence
**What goes wrong:** `fetch_all_fred()` currently catches per-series exceptions and logs a warning, only raising if ALL series fail. A critical series (WALCL, DGS10, DGS2) silently drops from the DataFrame while the pipeline continues.
**How to avoid:** After `fetch_all_fred()` returns, check that the critical columns are present in the resulting DataFrame. The check belongs in `daily_pipeline.py` after the fetch, not inside `fred_client.py` — keeping ingestion and policy separate.

---

## Code Examples

All examples are from direct inspection of the current codebase.

### Magic Numbers Inventory — Full Catalogue

**`data/pipelines/daily_pipeline.py` (lines 54-56):**
```python
_DRIFT_VARIANCE_WARN = 0.10
_DRIFT_PERSISTENCE_WARN = 0.97
_DRIFT_FEATURE_SHIFT_WARN = 1.5
```

**`services/signals.py` (lines 57-63):**
```python
# confidence thresholds
if max_prob >= 0.70:  → HIGH
elif max_prob >= 0.50:  → MODERATE
# liquidity trend counts (line 145-147)
if pos >= 12:  → EXPANDING
elif neg >= 12:  → CONTRACTING
```

**`services/orchestrator.py` (lines 31-37, and throughout):**
```python
_MIN_ROWS = 5          # minimum rows for rolling trend
_DOMINANT_PROB = 0.50  # risk-off threshold
_SCORE_MAX = 100.0
_SCORE_MIN = -100.0
# inline in analyse_equity(): 0.20, 0.6, 0.3, 0.002
# inline in analyse_rates(): 0.0005, 0.001, 0.002
# inline in analyse_credit(): 0.1, 0.2
# inline in analyse_liquidity(): 0.5, 0.1
# conviction thresholds in composite_analysis(): 20.0, 45.0
# composite signal thresholds: 20, -20
# equity signal thresholds: 25, -25 (and credit, rates, liquidity)
```

**`models/garch_model.py` (lines 27-29):**
```python
_VOL_LOW = 0.5
_VOL_NORMAL = 1.5
_VOL_ELEVATED = 2.5
```

**`models/regime_classifier.py` (line 112-115):**
```python
if vix_diff > 2.0:   → "elevated"
if vix_diff < -2.0:  → "compressed"
```

### Proposed Settings Key Names

```python
# Drift warning thresholds
pipeline_drift_variance_warn: float = Field(default=0.10, ...)
pipeline_drift_persistence_warn: float = Field(default=0.97, ...)
pipeline_drift_feature_shift_warn: float = Field(default=1.5, ...)

# Signal confidence thresholds
signal_confidence_high_threshold: float = Field(default=0.70, ...)
signal_confidence_moderate_threshold: float = Field(default=0.50, ...)

# Liquidity trend counts
signal_liquidity_trend_min_pos: int = Field(default=12, ...)
signal_liquidity_trend_window: int = Field(default=20, ...)

# Orchestrator domain thresholds
orchestrator_min_rows: int = Field(default=5, ...)
orchestrator_dominant_prob: float = Field(default=0.50, ...)
orchestrator_equity_growth_prob_high: float = Field(default=0.60, ...)
orchestrator_equity_growth_prob_low: float = Field(default=0.30, ...)
orchestrator_equity_growth_trend: float = Field(default=0.002, ...)
orchestrator_rates_curve_slope: float = Field(default=0.0005, ...)
orchestrator_rates_10y_fall: float = Field(default=0.001, ...)
orchestrator_rates_10y_rise_sharp: float = Field(default=0.002, ...)
orchestrator_rates_10y_rise_modest: float = Field(default=0.001, ...)
orchestrator_credit_slope_strong: float = Field(default=0.1, ...)
orchestrator_credit_net_threshold: float = Field(default=0.2, ...)
orchestrator_liquidity_slope_strong: float = Field(default=0.5, ...)
orchestrator_liquidity_slope_mild: float = Field(default=0.1, ...)
orchestrator_conviction_high_std: float = Field(default=20.0, ...)
orchestrator_conviction_medium_std: float = Field(default=45.0, ...)
orchestrator_composite_signal_threshold: float = Field(default=20.0, ...)
orchestrator_domain_signal_threshold: float = Field(default=25.0, ...)

# GARCH vol state bounds
garch_vol_low: float = Field(default=0.5, ...)
garch_vol_normal: float = Field(default=1.5, ...)
garch_vol_elevated: float = Field(default=2.5, ...)

# VIX diff classification thresholds
vix_diff_elevated: float = Field(default=2.0, ...)
vix_diff_compressed: float = Field(default=-2.0, ...)
```

### GARCH Forecast Fix — Before/After

**Current (re-fits on every call):**
```python
# Source: models/garch_model.py lines 142-158
model = arch_model(clean * 100, vol="Garch", p=1, q=1, dist="normal", rescale=False)
result = model.fit(disp="off", show_warning=False)
forecast = result.forecast(horizon=1, reindex=False)
```

**Fixed (uses stored result):**
```python
# Use the stored fit result — no re-fit required
forecast = self._arch_result.forecast(horizon=1, reindex=False)
cond_var = float(forecast.variance.iloc[-1, 0])
cond_vol = float(np.sqrt(max(cond_var, 0.0)))
```

Note: `ARCHModelResult.forecast()` does not require the original data series when called on a stored result — it uses the fitted parameters and the last observed residuals stored internally. This is the standard usage pattern for production GARCH inference with the `arch` library.

### HMM Convergence Guard — Implementation Pattern

```python
# In HMMModel.predict_proba() and HMMModel.predict():
def predict_proba(self, factors: np.ndarray) -> np.ndarray:
    if hasattr(self.hmm, "monitor_") and not self.hmm.monitor_.converged:
        raise RuntimeError(
            "HMM model did not converge (monitor_.converged=False). "
            "Regime probabilities are unreliable. Halting pipeline."
        )
    logger.info("HMM convergence check passed (converged=True)")
    return self.hmm.predict_proba(factors)
```

### Critical Series Halt Pattern in daily_pipeline.py

```python
# After fetch_all_fred() and fetch_market_data() succeed:
CRITICAL_FRED_COLS = {"WALCL", "DGS10", "DGS2"}
CRITICAL_MARKET_COLS = {"vix"}

missing_fred = CRITICAL_FRED_COLS - set(fred_df.columns)
missing_market = CRITICAL_MARKET_COLS - set(market_df.columns)

# Also check for all-NaN critical columns
for col in CRITICAL_FRED_COLS:
    if col in fred_df.columns and fred_df[col].isna().all():
        missing_fred.add(col)
for col in CRITICAL_MARKET_COLS:
    if col in market_df.columns and market_df[col].isna().all():
        missing_market.add(col)

if missing_fred or missing_market:
    duration = time.monotonic() - t0
    msg = f"Critical series missing or all-NaN: FRED={missing_fred} market={missing_market}"
    logger.error("PIPELINE HALT — %s", msg)
    _log_run("halted", data_lag=False, duration=duration, error=msg, model_version=version)
    alert_drift_warning("pipeline_halt_critical_data", 1.0, 0.0, today.isoformat())
    return {"status": "halted", "stale_data": True, "reason": msg, "timestamp": today.isoformat()}
```

### Column Exclusion for Optional Commodities in feature_engineering.py

The current zero-fill (lines 116-121) must change to column exclusion. The key design question (see Open Questions #1) is whether the stored PCA artifact expects a fixed column count. Given that v1 uses `MODEL_FEATURE_COLS_V1` (8 cols, no commodities) and v2 uses `MODEL_FEATURE_COLS` (10 cols), the safest approach for this phase is:

- `feature_engineering.build_features()` no longer zero-fills; it simply does not add the column if data is unavailable
- The caller (`daily_pipeline.py`) filters `feature_cols` to columns actually present in the feature DataFrame before calling `pca_model.transform(X)`
- The MODEL_FEATURE_COLS lists remain unchanged as the "full" column sets; the pipeline computes the intersection at runtime

```python
# In daily_pipeline.py, step 7:
available_cols = [c for c in feature_cols if c in features.columns]
if len(available_cols) < len(feature_cols):
    excluded = set(feature_cols) - set(available_cols)
    logger.warning("Optional feature columns excluded from PCA: %s", excluded)
X = features[available_cols].values
factors = pca_model.transform(X)
```

This only works if the PCA artifact was fitted without those columns OR if the model accepts variable-dimension input. Standard `sklearn.decomposition.PCA` does NOT accept variable dimension input at transform time — it raises `ValueError: X has 9 features, but PCA is expecting 10 features`. See Open Questions #1 for the resolution.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Zero-fill missing commodities | Column exclusion from PCA input | This phase | Removes synthetic bias from factor loadings |
| Silent FRED series drop | Halt on critical series missing | This phase | Pipeline fails loudly; API serves stale signal |
| GARCH re-fit on every inference | Forecast using stored result object | This phase (if clean) | ~2-5s faster per run; reproducible vol state |
| Magic number thresholds in logic | Named settings with env-var overrides | This phase | Operational tuning without code deploys |
| Broad `except Exception` in broadcast | Narrow to `(WebSocketDisconnect, RuntimeError)` | This phase | Unexpected errors surface in logs |

---

## Open Questions

1. **PCA column dimension mismatch when optional features are excluded**
   - What we know: `sklearn.PCA.transform()` requires input to match the n_features seen at fit time. If d_gold/d_oil were included during training (v2 model), excluding them at inference produces a `ValueError`.
   - What's unclear: Were the v2 model artifacts trained WITH d_gold/d_oil in `MODEL_FEATURE_COLS`? If yes, excluding those columns at inference is incompatible with the stored PCA.
   - Recommendation: Two options. Option A — Only apply column exclusion to v1 model (which was trained without commodities; `MODEL_FEATURE_COLS_V1` has 8 cols, no gold/oil). For v2, keep the current zero-fill behaviour until a new model is trained. Option B — Re-train the v2 model excluding optional columns before this phase goes live. Since this phase is a quality fix, **Option A is preferred** for now: exclude optional cols only for v1 model path; log a warning for v2. Document the model re-training requirement.

2. **`stale_data: true` flag — which API layer reads it?**
   - What we know: `run_daily_pipeline()` returns a dict. The scheduler (`services/scheduler.py`) calls the pipeline. The API does not call the pipeline directly — it reads from the database via `queries.fetch_current_regime()`.
   - What's unclear: Where should the `stale_data` flag be persisted so the API can serve it? Options: (a) a new `pipeline_runs` DB column, or (b) an in-memory flag on the scheduler, or (c) a dedicated `stale_data` key in the pipeline_run log row.
   - Recommendation: The simplest path is to write `stale_data=True` into the `pipeline_runs` table (already written by `_log_run`) and add an API query that reads the most recent pipeline_run status. The API can then include `"stale_data": true` in the signal response when the last run was halted. This avoids in-memory state and is durable across restarts.

3. **Duplicate persistence calculation — fix in this phase?**
   - What we know: `_persistence_and_confidence()` in `signals.py` (lines 50-63) and the inline persistence loop in `build_signal_range()` (lines 353-358) both compute regime streaks. They use slightly different iteration strategies.
   - Recommendation: Fix it in this phase. It's three lines to extract the streak loop into the existing `_persistence_and_confidence()` helper and call it from `build_signal_range()`. The risk is minimal and it eliminates a silent correctness divergence.

---

## Validation Architecture

No pytest infrastructure exists in the project. This phase is refactoring + reliability work with no new external behavior, so the verification strategy is:

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None installed — manual validation only |
| Config file | None |
| Quick run command | `python -c "from data.pipelines.daily_pipeline import run_daily_pipeline; print('import ok')"` |
| Full suite command | N/A — no test suite |

### Phase Requirements → Test Map

| Behavior | Test Type | Verification Method |
|----------|-----------|---------------------|
| Critical series halt fires when WALCL is all-NaN | manual smoke | Patch `fred_df["WALCL"] = np.nan` in a local script and verify `status == "halted"` returned |
| Optional commodity column excluded from PCA (no zero-fill) | manual smoke | Confirm `d_gold` absent from `features.columns` when gold data unavailable |
| HMM convergence guard raises RuntimeError on non-converged model | manual smoke | Set `hmm.monitor_.converged = False` on a loaded model and verify `predict_proba` raises |
| All magic numbers callable from env vars | manual smoke | `export GARCH_VOL_LOW=0.3 && python -c "from config.settings import get_settings; s=get_settings(); assert s.garch_vol_low == 0.3"` |
| GARCH forecast uses stored result, not re-fit | manual smoke | Add a log line inside the removed fit block to confirm it is never reached |
| Broad except in broadcast narrowed | static review | Read websocket.py and confirm `except (WebSocketDisconnect, RuntimeError)` |

### Wave 0 Gaps
- [ ] `tests/` directory does not exist — create if any automated tests are added
- [ ] No pytest installed — `pip install pytest` if tests are written
- [ ] Existing import-smoke commands are sufficient for this phase's scope

---

## Sources

### Primary (HIGH confidence — direct code inspection)
- `config/settings.py` — pydantic-settings pattern, existing field structure
- `data/pipelines/daily_pipeline.py` — halt pattern, _log_run, status dict convention
- `services/validation.py` — ValidationReport dataclass and usage
- `services/alerting.py` — alert_drift_warning() signature and delivery
- `models/hmm_model.py` — monitor_.converged attribute, joblib serialization
- `models/garch_model.py` — _arch_result storage, forecast_vol() re-fit issue
- `data/ingestion/fred_client.py` — fetch_all_fred() silent exception handling
- `data/ingestion/market_client.py` — missing VIX halt logic
- `data/processing/feature_engineering.py` — zero-fill at lines 116-121
- `services/orchestrator.py` — full magic number inventory
- `services/signals.py` — confidence/liquidity thresholds, duplicate persistence
- `models/regime_classifier.py` — VIX diff thresholds
- `api/routes/websocket.py` — broad except Exception in broadcast_regime()
- `requirements.txt` + `pyproject.toml` — stack versions and no test framework

### Secondary (MEDIUM confidence — library documentation)
- hmmlearn GaussianHMM: `monitor_` attribute is an instance of `ConvergenceMonitor` with `.converged` (bool) set after `fit()`. Confirmed by hmmlearn source and the existing usage in `hmm_model.py` line 51.
- arch library: `ARCHModelResult.forecast(horizon, reindex)` is a documented method that does not require the original data. The `reindex=False` argument is already used in the existing code.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all existing
- Architecture: HIGH — patterns derived from direct code inspection, not inference
- Pitfalls: HIGH — all pitfalls identified from concrete lines of existing code
- Open questions: MEDIUM — resolution options are clear but require a decision before planning

**Research date:** 2026-03-19
**Valid until:** 2026-06-19 (stable internal codebase; no external API changes expected)
