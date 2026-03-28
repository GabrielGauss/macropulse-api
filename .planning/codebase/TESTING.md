# Testing Patterns

**Analysis Date:** 2026-03-28

## Test Framework

**Runner:** pytest
- Config: `pytest.ini`
- Python test directory: `tests/`

**Test Commands:**
```bash
pytest                    # Run all tests
pytest -v                 # Verbose output
pytest tests/test_pipeline_quality.py::test_critical_fred_failure_halts  # Single test
pytest --cov              # With coverage (if coverage plugin installed)
```

**pytest Configuration (`pytest.ini`):**
```
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -q
```

**Assertion Library:** Python standard `assert` statements

## Test File Organization

**Location:** `tests/` directory at project root

**Current test files:**
- `tests/test_pipeline_quality.py` — Phase 5 pipeline quality tests for PIPE-01 through PIPE-05

**Naming Convention:**
- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`

**Current Structure:**
```
tests/
├── conftest.py                      # Shared pytest fixtures
└── test_pipeline_quality.py         # Phase 5 pipeline quality tests
```

## Shared Fixtures

**Location:** `tests/conftest.py`

**Available Fixtures:**

```python
@pytest.fixture()
def mock_fred_df() -> pd.DataFrame:
    """Minimal FRED DataFrame with all critical columns present and non-NaN."""
    # 60 business days of FRED data
    # Columns: WALCL, DGS10, DGS2, RRPONTSYD, WTREGEN, BAMLH0A0HYM2
```

```python
@pytest.fixture()
def mock_market_df() -> pd.DataFrame:
    """Minimal market DataFrame with VIX and SP500."""
    # 60 business days of market data
    # Columns: vix, sp500, dxy
```

```python
@pytest.fixture()
def mock_hmm_model_converged() -> MagicMock:
    """Mock HMMModel whose HMM has converged."""
    # Configured with hmm.monitor_.converged = True
```

```python
@pytest.fixture()
def mock_hmm_model_not_converged() -> MagicMock:
    """Mock HMMModel whose HMM did NOT converge."""
    # Configured with hmm.monitor_.converged = False
```

```python
@pytest.fixture()
def mock_garch_model() -> MagicMock:
    """Mock GARCHModel with pre-fitted _arch_result."""
    # Returns forecast variance mocked as 0.25
```

## Test Structure

**Test Organization Pattern:**

All tests in `tests/test_pipeline_quality.py` follow this structure:

1. **Section headers with ASCII dividers:**
   ```python
   # ── PIPE-01: Critical FRED failure halts pipeline ─────────────────────
   ```

2. **Test function naming:** `test_<feature_description>`
   ```python
   def test_critical_fred_failure_halts(mock_fred_df, mock_market_df):
   ```

3. **Test anatomy:**
   - Arrange: Set up fixtures and mock state
   - Act: Call the function being tested
   - Assert: Verify expected behavior

**Example from `test_pipeline_quality.py`:**

```python
def test_critical_fred_failure_halts(mock_fred_df, mock_market_df):
    """Pipeline returns status='halted' with stale_data=True when WALCL is all-NaN."""
    # Arrange
    mock_fred_df["WALCL"] = np.nan  # all-NaN critical series

    # Act
    with patch("data.pipelines.daily_pipeline.fetch_all_fred", return_value=mock_fred_df), \
         patch("data.pipelines.daily_pipeline.fetch_market_data", return_value=mock_market_df), \
         patch("data.pipelines.daily_pipeline.validate_raw_fred") as mock_val_fred, \
         patch("data.pipelines.daily_pipeline.validate_market_data") as mock_val_mkt, \
         patch("data.pipelines.daily_pipeline.queries.insert_pipeline_run"), \
         patch("data.pipelines.daily_pipeline.alert_drift_warning"):
        mock_val_fred.return_value = MagicMock(passed=True, errors=[])
        mock_val_mkt.return_value = MagicMock(passed=True, errors=[])
        from data.pipelines.daily_pipeline import run_daily_pipeline
        result = run_daily_pipeline()

    # Assert
    assert result["status"] == "halted"
    assert result.get("stale_data") is True
```

## Mocking Patterns

**Framework:** unittest.mock (MagicMock, patch)

**Imports:**
```python
from unittest.mock import MagicMock, patch
```

**What to Mock:**

1. **External data sources:**
   - `data.pipelines.daily_pipeline.fetch_all_fred()` → return mock FRED DataFrame
   - `data.pipelines.daily_pipeline.fetch_market_data()` → return mock market DataFrame
   - `data.pipelines.daily_pipeline.validate_raw_fred()` → return validation result mock

2. **Database operations:**
   - `data.pipelines.daily_pipeline.queries.insert_pipeline_run` → no-op mock
   - `database.queries.get_api_key_by_hash()` → return key record or None

3. **Services:**
   - `data.pipelines.daily_pipeline.alert_drift_warning` → no-op mock

**Patch Pattern:**
```python
with patch("module.path.to.function", return_value=mock_value) as mock_obj:
    # Test code
    assert mock_obj.called
```

**What NOT to Mock:**

1. **Core business logic classes:** GARCHModel, HMMModel, PCAModel
   - Test with real math operations (use fixtures for pre-computed states)

2. **Pydantic models and validators:** Settings, response schemas
   - Test directly with real objects

3. **Python stdlib:** logging, datetime, etc.
   - Test with real implementations

## Test Types

**Unit Tests:**
- Located in: `tests/test_pipeline_quality.py`
- Scope: Individual function/method behavior
- Pattern: Mock dependencies, assert output
- Example: `test_critical_fred_failure_halts()` — test pipeline halts when FRED data missing

**Integration Tests:**
- Not yet implemented
- Would test: Database writes + reads, full pipeline end-to-end
- Recommendation: Add with containerized PostgreSQL (testcontainers)

**API Tests:**
- Not yet implemented
- Would use: `from fastapi.testclient import TestClient`
- Recommendation: Test route handlers with mocked services

## Settings & Configuration in Tests

**Pattern:** Settings must be cleared between tests that modify environment

**Example from `test_settings_env_override()`:**
```python
def test_settings_env_override():
    import os
    from config.settings import get_settings

    # Must clear cache BEFORE setting env var
    get_settings.cache_clear()
    os.environ["GARCH_VOL_LOW"] = "0.3"
    try:
        s = get_settings()
        assert s.garch_vol_low == pytest.approx(0.3)
    finally:
        # Restore: remove env var and clear cache
        del os.environ["GARCH_VOL_LOW"]
        get_settings.cache_clear()
```

**Key Point:** Cached Settings singleton must be cleared to force re-initialization with new env vars

## Test Coverage

**Current Status:**
- No coverage measurement configured
- Tests exist for: Pipeline quality thresholds, FRED/VIX failure modes, HMM convergence, GARCH refitting, Settings defaults

**Areas Tested:**
- `models/hmm_model.py` — convergence validation
- `models/garch_model.py` — no-refit behavior on inference
- `config/settings.py` — threshold defaults and env var overrides
- `data/pipelines/daily_pipeline.py` — failure modes (critical FRED, VIX, feature engineering)

**Areas NOT Yet Tested:**
- API routes (auth, regime, analysis, etc.)
- Frontend components
- Database query correctness
- Service orchestrator logic
- Email/notification flows

## Testing Phase 5 Features

**Test Naming Convention:** Tests prefixed with domain (PIPE-01, PIPE-02, etc.)

**PIPE-01: Critical FRED failure halts pipeline**
- Test: `test_critical_fred_failure_halts()` — WALCL all-NaN halts with stale_data=True
- Test: `test_optional_series_excluded_not_zeroed()` — d_gold, d_oil excluded when unavailable

**PIPE-02: VIX failure halts pipeline**
- Test: `test_vix_failure_halts_pipeline()` — VIX all-NaN halts with stale_data=True

**PIPE-03: HMM convergence guard**
- Test: `test_hmm_convergence_check()` — Raises RuntimeError if monitor_.converged is False

**PIPE-04: GARCH no-refit on inference**
- Test: `test_garch_no_refit_on_inference()` — Verify _arch_result.forecast() called, not arch_model()

**PIPE-05: Thresholds in settings**
- Test: `test_thresholds_in_settings()` — All Phase 5 threshold fields present with correct defaults
- Test: `test_settings_env_override()` — GARCH_VOL_LOW env var overrides setting value

## Recommended Test Additions

**High Priority (Critical Paths):**

1. **Authentication tests (`tests/test_auth.py`):**
   - Valid API key lookup
   - Invalid key rejection
   - Dev-mode bypass
   - Owner key special access
   - Rate limit headers

2. **Tier gating tests (`tests/test_deps.py`):**
   - Free tier endpoint blocking
   - Starter tier pass-through
   - Pro tier unlimited access

3. **Route handler tests (`tests/test_api_routes.py`):**
   - GET `/v1/regime/current` — returns signed response
   - GET `/v1/analysis/composite` — orchestrator integration
   - POST `/v1/backtest` — parameter validation

**Medium Priority:**

4. **Database query tests (`tests/test_queries.py`):**
   - Upsert semantics verification
   - Concurrent write handling
   - Data retrieval completeness

5. **Service tests (`tests/test_services.py`):**
   - Orchestrator domain signal calculations
   - Scorecard building
   - Email template rendering

6. **Frontend tests (`frontend/src/__tests__/`):**
   - Component rendering with useFetch
   - Error boundary error capture
   - API key localStorage persistence

## Test Execution

**Run all tests:**
```bash
cd /path/to/macropulse
pytest
```

**Run with verbose output:**
```bash
pytest -v
```

**Run single test file:**
```bash
pytest tests/test_pipeline_quality.py
```

**Run single test:**
```bash
pytest tests/test_pipeline_quality.py::test_critical_fred_failure_halts
```

**Run matching pattern:**
```bash
pytest -k "hmm_convergence"
```

**With coverage (if pytest-cov installed):**
```bash
pytest --cov=. --cov-report=html
# Coverage report in htmlcov/index.html
```

---

*Testing analysis: 2026-03-28*
