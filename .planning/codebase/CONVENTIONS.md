# Coding Conventions

**Analysis Date:** 2026-03-28

## Python Code Style

**Linting & Formatting:**
- Tool: Ruff
- Config: `pyproject.toml` [tool.ruff]
- Line length: 100 characters
- Selectors: E, F, I, N, W, UP, B, SIM (error, pyflakes, isort, pep8-naming, pycodestyle, upgrade, bugbear, simplify)

**Type Checking:**
- Tool: mypy
- Config: `pyproject.toml` [tool.mypy]
- Mode: strict
- Python version: 3.11+

**Import Organization:**
- First-party modules configured: api, config, data, database, models, services
- isort enforcement via Ruff
- Circular import avoidance via deferred imports where needed (e.g., `api/auth.py` defers `database.queries` import)

## Naming Patterns

**Files:**
- Python: snake_case (e.g., `garch_model.py`, `daily_pipeline.py`)
- Frontend: camelCase components (e.g., `Header.jsx`, `CommentaryCard.jsx`), snake_case utilities (e.g., `useFetch.js`)

**Functions & Methods:**
- Python: snake_case (e.g., `predict_proba()`, `upsert_macro_features()`)
- Frontend: camelCase (e.g., `getCurrentRegime()`, `saveKey()`)

**Variables:**
- Python: snake_case (e.g., `model_version`, `daily_limit`)
- Frontend: camelCase (e.g., `keyDraft`, `showKeyInput`, `pipelineStatus`)

**Constants:**
- Python: UPPER_SNAKE_CASE (e.g., `_REGIME_ID`, `TIER_LIMITS`)
- Frontend: camelCase or CONST (e.g., `TIER_COLOR`, `GATE_COPY`)
- Internal/private: prefixed with underscore (e.g., `_EXEMPT_PATHS`, `_reset_ts()`)

**Types & Classes:**
- Python: PascalCase (e.g., `RegimeResponse`, `GARCHModel`, `HMMModel`)
- Frontend components: PascalCase (e.g., `Header`, `RegimeCard`)
- Python type aliases: PascalCase (e.g., `VolState = Literal[...]`)

## Module Organization

**Backend Structure:**
- `api/` — FastAPI routes and schemas
  - `routes/` — endpoint handlers organized by domain (regime.py, analysis.py, etc.)
  - `schemas/` — Pydantic response models
  - `middleware/` — CORS, rate-limiting, custom middleware
  - `main.py` — FastAPI app initialization, lifespan, static serving
  - `auth.py` — API key validation logic
  - `deps.py` — Shared FastAPI dependencies (require_api_key, require_paid)

- `config/` — Configuration management
  - `settings.py` — Single Settings class with all env vars, defaults, computed properties

- `database/` — Data layer
  - `queries.py` — Parameterized SQL queries (all writes use INSERT...ON CONFLICT upsert)
  - `connection.py` — Sync/async connection pooling
  - `migrations/` — SQL migration files (numbered, applied in order)

- `services/` — Business logic (orchestrator, scheduler, email, etc.)
- `models/` — ML model classes (HMMModel, GARCHModel, PCAModel)
- `data/` — Data ingestion and processing (FRED client, market data, feature engineering)

**Frontend Structure:**
- `src/components/` — React components (Cards, Charts, Views)
- `src/views/` — Full-page views (InflationView, GrowthView, etc.) lazy-loaded with React.lazy()
- `src/hooks/` — Custom React hooks (useFetch, useCountdown, useRegimeSocket)
- `src/lib/` — Utilities and helpers (api.js for endpoint definitions, utils.js for constants)

## Error Handling

**Python Pattern:**
- FastAPI routes raise `HTTPException` with `status_code` and `detail`
- Service functions log exceptions with `logger.exception()` then re-raise or convert to HTTPException
- Database operations wrapped in try-except, with context managers ensuring cursor cleanup
- Validation failures raise early with clear error messages

**Example from `api/routes/analysis.py`:**
```python
try:
    result = composite_analysis(regime_row, history, features, liquidity)
except Exception as exc:
    logger.exception("Composite analysis failed: %s", exc)
    raise HTTPException(
        status_code=500,
        detail=f"Analysis computation failed: {exc}",
    ) from exc
```

**Frontend Pattern:**
- API calls use Promise rejection; errors caught in hooks or try-catch blocks
- Components render error states from `useFetch()` error property
- User-facing errors displayed via modal (not console output)

## Logging

**Framework:** Python standard library logging module

**Configuration:** `config/settings.py`
- Log level field (default: INFO)
- Format: `"%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"`
- All loggers: `logger = logging.getLogger(__name__)`

**Patterns:**
- Info level for operations: `logger.info("Starting MacroPulse API v%s", settings.app_version)`
- Warning level for non-fatal issues: `logger.warning("Health check DB ping failed: %s", exc)`
- Exception level for handled errors: `logger.exception("Migration failed (%s): %s", path.name, exc)`

## Docstrings

**Style:** Google-style (parameters, returns, raises)

**Module-level:** Docstring at top describing purpose
- `api/main.py` example: Lists served endpoints and scheduler integration

**Functions (Python):**
```python
def forecast_vol(self, returns_series: pd.Series) -> np.ndarray:
    """
    Forecast conditional volatility for next trading day.

    Parameters
    ----------
    returns_series:
        Daily log-return series to forecast volatility for.

    Returns
    -------
    np.ndarray
        Conditional variance forecast.
    """
```

**Frontend:** Minimal JSDoc; rely on self-documenting code

## API Design

**Response Models:** Pydantic BaseModel in `api/schemas/responses.py`
- RegimeResponse, CompositeAnalysisResponse, DomainSignal, etc.
- All fields typed with validation (Field(..., ge=0, le=1) for probabilities)

**Endpoints:**
- Prefix: `/v1` (versioning)
- RESTful: GET for reads, POST for mutations
- Tags: By domain (MacroPulse, Analysis, Billing)
- Rate-limited via middleware per tier in Settings

**Error Responses:**
- HTTP status codes (404, 500, 503, 403)
- Body: `{"detail": "Human-readable message"}`

## Frontend Conventions

**Component Props:**
- Destructure in signature
- Callback props prefixed with `on` (e.g., `onToggleGuide`, `onClick`)

**State Management:**
- useState for local state
- useCallback to memoize callbacks
- Custom hooks (useFetch, useCountdown) for logic reuse
- Context API (GuideModeContext) for app-level state

**Styling:**
- Tailwind CSS (config: `frontend/tailwind.config.js`)
- Custom palette: surface-0 to surface-4, regime-colors
- No rounded corners (border-radius: 0)
- Font: JetBrains Mono throughout

**Lazy Loading:**
- React.lazy() for views: `const InflationView = React.lazy(() => import('./views/InflationView'))`
- Suspense wrapper in App.jsx

## Comments

**When to Comment:**
- Non-obvious algorithms (z-score normalization, volatility classification)
- Business logic justifications (threshold rationales)
- Security notes (e.g., header-only API key in `api/auth.py`: keys in URLs appear in logs)
- Config-driven behavior explanations

**Example from `api/routes/regime.py`:**
```python
# Build response without signature first so we can sign the exact bytes
# that will appear in JSON body. Using model_dump(mode="json") ensures
# Pydantic's serialization rules produce the same values IRL Engine sees.
```

**Avoid:** Reiterating what code obviously does

## Database Patterns

**Query Style:** `database/queries.py`
- All parameterized (no string concatenation)
- Passed as dict: `cur.execute(sql, row)`
- Upsert semantics: `INSERT...ON CONFLICT(time) DO UPDATE SET`
- No inline SQL in route handlers

**Connection Management:**
```python
with get_sync_cursor() as cur:
    cur.execute(sql, row)
```
- Context manager ensures cleanup on exception

## Configuration

**Environment Variables:** `config/settings.py`
- Loaded via Pydantic Settings
- Case-insensitive
- File: `.env` (example: `.env.example`)
- Never commit secrets

**Settings Class:**
- Singleton: `@lru_cache` on `get_settings()`
- Tests must call `get_settings.cache_clear()` after env changes
- Property methods for computed values (database_url, async_database_url)

**Thresholds:** All ML/algorithm parameters in Settings
- Prefixed: `pipeline_drift_*`, `signal_confidence_*`, `orchestrator_*`, `garch_vol_*`
- Overridable via environment variables
- Default values suitable for local development

## Shared Principles

**DRY:**
- Auth logic centralized in `api/auth.py` → used via Depends()
- API endpoints in `frontend/src/lib/api.js` → imported everywhere
- DB queries in `database/queries.py`

**Single Responsibility:**
- Route handlers call services
- Services contain business logic
- Database queries are pure SQL
- Middleware handles cross-cutting concerns

**Fail Fast:**
- Validate at entry point (route, middleware)
- Early raises with clear messages
- Database read failures propagate as HTTP errors

---

*Convention analysis: 2026-03-28*
