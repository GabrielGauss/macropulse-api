# Testing Patterns

**Analysis Date:** 2026-03-18

## Test Framework

**Status:** No formal testing framework detected in codebase.

**Python:**
- No test runner configured (pytest/unittest not in `requirements.txt` or `pyproject.toml`)
- No test files found in codebase
- Development and production code follow the same structure without test separation

**JavaScript/Frontend:**
- No test framework configured (no Jest, Vitest, or Playwright config)
- No test files found in src/
- Development relies on manual testing and browser dev tools

**Note:** This is a critical gap — the codebase lacks automated testing infrastructure.

## Test File Organization

**Current state:**
- No dedicated test directories (`tests/`, `__tests__/`, `*.test.js`, `*.spec.py`)
- Test infrastructure would need to be established from scratch

**Recommended structure (if implemented):**
- Python tests in top-level `tests/` directory mirroring src structure
  - `tests/test_api_routes.py` for FastAPI endpoints
  - `tests/test_auth.py` for authentication
  - `tests/test_services.py` for business logic
- JavaScript tests co-located with components or in `src/__tests__/`

## Error Handling in Code (Current Patterns)

The codebase demonstrates error handling that would need to be validated by tests:

**Python Error Scenarios:**

1. **Authentication failures** (`api/auth.py`):
   - Missing API key → 401 Unauthorized
   - Invalid/revoked key → 403 Forbidden
   - Dev-mode bypass when no keys configured and DB unreachable
   - Scenarios that should be tested:
     - Valid key lookup in database
     - Expired/revoked key rejection
     - Owner key special access
     - Legacy env-key support
     - Dev-mode activation

2. **API tier gating** (`api/deps.py`):
   - Free-tier users blocked from premium endpoints
   - Scenarios that should be tested:
     - Free tier rejection with upgrade message
     - Paid tier pass-through
     - Owner tier bypass

3. **Data availability** (`api/routes/analysis.py`):
   - Missing regime data → 503 Service Unavailable
   - Analysis computation errors wrapped as 500
   - Scenarios:
     - Graceful degradation when data missing
     - Exception context preservation

4. **Database connection** (`database/connection.py`):
   - Pool initialization on first use
   - Connection exhaustion handling
   - Scenarios:
     - Pool min/max connections enforced
     - Concurrent access under load
     - Graceful connection cleanup

**JavaScript Error Scenarios:**

1. **API fetch failures** (`src/lib/api.js`):
   - Non-200 response → throw with status/statusText
   - Network errors
   - Scenarios:
     - 4xx errors (auth, not found)
     - 5xx errors (backend down)
     - Network timeouts

2. **Hook state management** (`src/hooks/useFetch.js`):
   - Loading state transitions
   - Error state capture
   - Refetch capability
   - Scenarios:
     - Loading → data flow
     - Loading → error flow
     - Refetch clears error and sets loading

3. **React error boundary** (`src/components/ErrorBoundary.jsx`):
   - Render errors caught and displayed
   - Recovery via "try again" button
   - Console logging of errors
   - Scenarios:
     - Error display without blank screen
     - State recovery after error

## Test Structure (Recommended)

**If testing framework is added, follow these patterns:**

**Python (pytest structure):**
```python
# tests/test_api_auth.py
import pytest
from fastapi.testclient import TestClient
from api.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_require_api_key_missing_header(client):
    """Missing API key header should return 401."""
    response = client.get("/v1/regime/current")
    assert response.status_code == 401
    assert "X-MacroPulse-Key" in response.json()["detail"]

def test_require_api_key_invalid(client, monkeypatch):
    """Invalid API key should return 403."""
    # Mock database lookup to return None
    def mock_lookup(key):
        return None
    monkeypatch.setattr("api.auth._lookup_key", mock_lookup)

    response = client.get("/v1/regime/current", headers={"X-MacroPulse-Key": "invalid"})
    assert response.status_code == 403

def test_free_tier_endpoint_blocking(client, monkeypatch):
    """Free tier users should be blocked from premium endpoints."""
    # Mock API key lookup to return free tier
    def mock_lookup(key):
        return {"tier": "free", "user_id": 1}
    monkeypatch.setattr("api.auth._lookup_key", mock_lookup)

    response = client.get("/v1/backtest", headers={"X-MacroPulse-Key": "test"})
    assert response.status_code == 403
```

**JavaScript (recommended Jest/Vitest structure):**
```javascript
// src/__tests__/api.test.js
import { api } from '../lib/api.js';

describe('api.js', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
    localStorage.clear();
  });

  describe('apiFetch', () => {
    it('should throw on non-200 response', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found'
      });

      await expect(api.getCurrentRegime()).rejects.toThrow('API 404: Not Found');
    });

    it('should include API key header when stored', async () => {
      localStorage.setItem('mp_api_key', 'test-key-123');
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({})
      });

      await api.getCurrentRegime();

      expect(global.fetch).toHaveBeenCalledWith(
        '/v1/regime/current',
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-MacroPulse-Key': 'test-key-123'
          })
        })
      );
    });
  });

  describe('useFetch hook', () => {
    it('should handle loading and success states', async () => {
      const { renderHook, waitFor } = require('@testing-library/react');
      const { useFetch } = require('../hooks/useFetch.js');

      const mockFetch = jest.fn().mockResolvedValue({ data: 'test' });
      const { result } = renderHook(() => useFetch(mockFetch));

      expect(result.current.loading).toBe(true);
      expect(result.current.data).toBe(null);

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
        expect(result.current.data).toEqual({ data: 'test' });
      });
    });
  });
});
```

## Mocking Strategy

**What to Mock:**

1. **External APIs:** FRED API, Anthropic API, Paddle billing
   - Use mock responses for integration tests
   - Example: mock `fredapi` client for data ingestion tests

2. **Database connections:** Mock `database.queries` functions
   - Return test data fixtures instead of real DB queries
   - Example: mock `fetch_current_regime()` to return test regime data

3. **Service layers:** Mock heavy computation services
   - Example: mock `RegimeInferenceService.infer()` to return pre-computed results

4. **HTTP requests:** Mock `httpx` for external service calls
   - Mock webhook notifications, email sends, Discord posts

**What NOT to Mock:**

1. **Core business logic:** Regime classification, HMM inference
   - Test with real mathematical outputs
   - Use fixtures of pre-computed model artifacts

2. **Route handlers:** Test full FastAPI endpoints with real dependency injection
   - Mock only external services (DB, APIs)

3. **React hooks:** Use actual React rendering in tests
   - Test state transitions with userEvent/fireEvent, not mocking React

## Test Fixtures and Factories

**Recommended patterns (not currently in use):**

```python
# tests/fixtures.py
import pytest

@pytest.fixture
def sample_regime_row():
    """Sample regime record from database."""
    return {
        "time": "2024-03-15",
        "regime": "expansion",
        "risk_score": 45,
        "prob_expansion": 0.8,
        "prob_tightening": 0.1,
        "prob_risk_off": 0.05,
        "prob_recovery": 0.05,
        "volatility_state": "normal",
        "model_version": "v1",
    }

@pytest.fixture
def sample_api_key():
    """Valid API key record."""
    return {
        "user_id": 123,
        "email": "test@example.com",
        "tier": "pro",
        "key_prefix": "mp_test1234",
        "is_active": True,
    }

@pytest.fixture
def free_tier_key():
    """Free tier API key record."""
    return {
        "user_id": 456,
        "email": "free@example.com",
        "tier": "free",
        "key_prefix": "mp_free5678",
        "is_active": True,
    }
```

## Coverage Targets

**Current:** No coverage measurement configured

**Recommended targets (if testing added):**
- API routes: 80%+ coverage
- Authentication/authorization: 100% coverage (critical path)
- Database queries: 70%+ coverage
- Service layer: 75%+ coverage
- Frontend components: 60%+ (emphasis on interactive components)

**Critical paths requiring high coverage:**
- `api/auth.py` - authentication logic
- `api/deps.py` - tier gating
- `database/queries.py` - data access layer
- `frontend/src/components/ErrorBoundary.jsx` - error handling

## Performance Testing Considerations

**Areas needing validation:**

1. **Database connection pool behavior:**
   - Min/max connections held
   - Concurrent query handling
   - Stress test with rate limits

2. **Inference latency:**
   - Model loading time
   - PCA transform throughput
   - HMM inference speed

3. **Frontend performance:**
   - WebSocket reconnection under poor network
   - Large history data rendering (1000+ regime records)
   - Concurrent API requests

## Gaps and Recommendations

**Critical missing test infrastructure:**

1. **No unit testing framework**
   - Recommendation: Add pytest to requirements.txt with fixtures and plugins
   - Setup conftest.py with database test fixtures and mocking

2. **No integration test setup**
   - Recommendation: Containerize PostgreSQL for integration tests
   - Use testcontainers or docker-compose test profile

3. **No API contract testing**
   - Recommendation: Add Pydantic schema validation tests
   - Test OpenAPI schema completeness

4. **No frontend component tests**
   - Recommendation: Add Vitest + React Testing Library
   - Focus on user interactions and error states

5. **No end-to-end tests**
   - Recommendation: Consider Playwright for critical user journeys
   - Test auth flow, dashboard loading, WebSocket connection

6. **No performance/load testing**
   - Recommendation: Add locust or k6 for load testing
   - Validate rate limits and concurrent connection handling

---

*Testing analysis: 2026-03-18*
