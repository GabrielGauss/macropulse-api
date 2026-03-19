# Phase 5: Pipeline Quality and Noise Reduction - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix internal pipeline reliability issues: silent data failures, missing HMM convergence guards, and scattered magic number thresholds. No user-facing API changes. Signal output becomes more trustworthy and the pipeline fails loudly when something is wrong rather than quietly producing bad data.

</domain>

<decisions>
## Implementation Decisions

### Critical data failure policy
- When WALCL (FRED) or VIX (yfinance) fails to fetch, **halt the pipeline entirely**
- No signal is written for that run
- API continues to serve the last valid signal with a `stale_data: true` flag
- Owner alert fires on halt
- "Critical" series: WALCL, DGS10, DGS2, VIX — these are non-negotiable inputs
- "Optional" series: gold, oil, BTC, ETH — handled separately (see below)

### Optional commodity features (gold, oil, BTC, ETH)
- When any commodity fetch fails or returns NaN, **exclude that column from PCA input entirely**
- Do NOT zero-fill — synthetic zeros bias PCA factors
- Model runs with fewer inputs but all real ones
- No pipeline halt for commodity failures — they are genuinely optional

### HMM convergence policy
- If HMM EM fails to converge during inference, **halt the pipeline** — same policy as data failure
- Non-convergence = unreliable regime probabilities = worse than no signal
- Convergence check must run before any inference output is trusted
- Log the convergence monitor state on every run (converged or not)

### Threshold consolidation
- All 20+ magic number thresholds move to **settings.py** with documented defaults
- Each threshold controllable via environment variable (no code changes needed to tune)
- Thresholds to consolidate: confidence levels (0.70/0.50), liquidity trend counts (12/20), drift warnings (0.10/0.97/1.5), orchestrator signal thresholds (0.50/0.20/0.60/0.002 etc.), VIX vol thresholds, GARCH vol state bounds, conviction bounds
- Each setting gets a comment explaining its meaning and the reasoning for the default value

### Claude's Discretion
- Exact naming of new settings keys
- Whether GARCH refit-on-inference is fixed in this phase or deferred (fix it if clean, defer if risky)
- Whether to fix the duplicate persistence calculation (signals.py vs orchestrator.py) in this phase
- Exact log message format for convergence/failure events

</decisions>

<specifics>
## Specific Ideas

- "Clean pipelines, low noise" — user's north star. Prioritize correctness over cleverness.
- The audit identified the orchestrator as the noisiest file (4/10) — consolidating its thresholds is high priority
- GARCH refitting on every inference is wasteful and breaks reproducibility — fix if it can be done cleanly
- Broad `except Exception: pass` blocks (especially in WebSocket broadcast) should be narrowed to specific exceptions

</specifics>

<code_context>
## Existing Code Insights

### Files to modify
- `data/ingestion/fred_client.py` — separate critical vs optional series, make critical failures fatal
- `data/ingestion/market_client.py` — add timeout, make VIX failure fatal
- `data/processing/feature_engineering.py` — replace zero-fill with column exclusion for missing commodities
- `models/hmm_model.py` — add convergence check before predict/predict_proba
- `data/pipelines/daily_pipeline.py` — wire up halt logic, narrow broad exception catches
- `services/orchestrator.py` — extract all magic numbers to settings
- `services/signals.py` — extract confidence/liquidity thresholds to settings
- `models/regime_classifier.py` — extract vol thresholds to settings
- `models/garch_model.py` — extract vol state bounds, fix refit-on-inference if clean
- `config/settings.py` — destination for all extracted thresholds

### Established Patterns
- Pydantic-settings in `config/settings.py` — all new thresholds follow this pattern (Field with default + env var name)
- `ValidationReport` dataclass in `services/validation.py` — existing pattern for structured error reporting
- Pipeline already returns a status dict — `data_lag: True` pattern exists, `stale_data: True` follows same pattern

### Integration Points
- Pipeline halt must set a failure status that the API can read to serve stale signal with flag
- Owner alerting already exists in `services/alerting.py` — reuse for convergence/data halt alerts
- `daily_pipeline.py` is the orchestration point — all halt decisions flow through here

</code_context>

<deferred>
## Deferred Ideas

- Statistical significance tests for trend detection in orchestrator (replace slope sign with t-test) — more involved, separate phase
- Feature shift drift baseline fixed to training date (not moving window) — model versioning work, future phase
- Duplicate persistence calculation consolidation (signals.py vs orchestrator.py) — Claude's discretion whether to include

</deferred>

---

*Phase: 05-pipeline-quality-and-noise-reduction*
*Context gathered: 2026-03-19*
