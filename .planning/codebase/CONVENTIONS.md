# Coding Conventions

**Analysis Date:** 2026-03-18

## Naming Patterns

**Files:**
- Python files: `lowercase_with_underscores.py` (snake_case)
  - Examples: `api/auth.py`, `services/inference.py`, `database/connection.py`
- React/JSX files: `PascalCase.jsx` for components, `camelCase.js` for utilities
  - Examples: `src/components/RegimeCard.jsx`, `src/hooks/useFetch.js`, `src/lib/api.js`
- CSS/Config files: lowercase with hyphens
  - Examples: `tailwind.config.js`, `vite.config.js`, `postcss.config.js`

**Functions:**
- Python functions: snake_case
  - Examples: `hash_key()`, `_lookup_key()`, `require_api_key()`, `get_sync_cursor()`
  - Private functions prefixed with underscore: `_get_pool()`, `_lookup_key()`
- JavaScript functions: camelCase
  - Examples: `apiFetch()`, `useRegimeSocket()`, `getCurrentRegime()`, `getKey()`
  - Hooks follow React convention: `useFetch()`, `useRegimeSocket()`
- React components: PascalCase (enforced by JSX)
  - Examples: `ErrorBoundary`, `StatCard`, `RegimeCard`

**Variables:**
- Python: snake_case throughout
  - Examples: `feature_matrix`, `regime_row`, `api_keys`, `db_password`
  - Module-level constants: UPPERCASE_WITH_UNDERSCORES
  - Private module variables: prefixed with underscore `_pool`, `_header_scheme`
- JavaScript: camelCase throughout
  - Examples: `activeSection`, `guideMode`, `historyDays`, `isFree`
  - Constants: UPPERCASE_WITH_UNDERSCORES (e.g., `FREE_HISTORY_LIMIT = 30`)

**Types:**
- Python: Use `from __future__ import annotations` for forward references
  - Type hints use pipe for unions: `str | None`, `dict[str, Any]`
  - Examples: `def infer(self, feature_matrix: np.ndarray, vix_diff: float | None = None)`
- JavaScript: JSDoc comments for prop types (no TypeScript)
  - Example: `/** @type {import('tailwindcss').Config} */`

## Code Style

**Formatting:**
- Ruff (Python linter) - configured in `pyproject.toml`
  - Line length: 100 characters
  - Target: Python 3.11+
  - Enabled rule sets: E, F, I, N, W, UP, B, SIM

**Linting:**
- Python: Ruff for linting and isort for imports
  - Configuration in `pyproject.toml`:
    - `select = ["E", "F", "I", "N", "W", "UP", "B", "SIM"]`
    - `line-length = 100`
    - isort known-first-party: `["api", "config", "data", "database", "models", "services"]`
- Python: mypy for type checking
  - Configuration in `pyproject.toml`:
    - `strict = true`
    - `warn_return_any = true`
    - `ignore_missing_imports = true`
- JavaScript: No formal linter configured (no `.eslintrc` or `eslint.config.js` in project root)
  - Formatting: Tailwind CSS classes use arbitrary values inline with style objects
  - Pattern: mix of className strings and style object props

**Indentation and Spacing:**
- Python: 4 spaces (PEP 8)
- JavaScript: 2 spaces (Vite/React default)

## Import Organization

**Order (Python):**
1. `from __future__ import annotations` (always first)
2. Standard library imports (alphabetical)
3. Third-party imports (alphabetical)
4. Local application imports (alphabetical by module)

**Examples from codebase:**
```python
# api/main.py
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from api.middleware.rate_limit import RateLimitMiddleware
from api.routes.auth import router as auth_router
from config.settings import get_settings
```

**Order (JavaScript):**
1. React/third-party imports
2. Local component imports
3. Hook imports
4. Utility/lib imports

**Examples from codebase:**
```jsx
// src/App.jsx
import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import { useFetch } from './hooks/useFetch';
import { GuideModeContext, useGuideModeState } from './lib/guideMode';
import { useRegimeSocket } from './hooks/useRegimeSocket';
import { api } from './lib/api';
```

**Path Aliases:**
- Not used in this codebase (relative imports throughout)

## Error Handling

**Python Patterns:**
- Use typed `dict[str, Any]` for auth records and query results instead of custom classes
  - Example from `api/auth.py`: returns `dict[str, Any]` with keys like `user_id`, `email`, `tier`
- HTTP exceptions using FastAPI's `HTTPException` with status codes
  - Example: `raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="...")`
- Logging errors with `logger.error()`, `logger.warning()`, `logger.exception()`
  - Exception context logged: `logger.exception("Composite analysis failed: %s", exc)`
- Dev-mode fallback: return synthetic defaults if DB/config unavailable
  - Example in `api/auth.py`: dev mode returns `{"user_id": 0, "email": "dev@localhost", "tier": "pro", ...}`
- Service layer catches and re-raises as HTTP exceptions for clarity
  - Example in `api/routes/analysis.py`: catch orchestrator exceptions and convert to 500 response

**JavaScript Patterns:**
- API errors thrown from `apiFetch()` as generic Error with status
  - Example: `throw new Error(`API ${res.status}: ${res.statusText}`)`
- Caught and handled in useFetch hook: `catch(setError)` stores error state
- Error state handled in components: check `data.error && <ErrorBoundary>`
- React error boundary component catches unhandled render errors
  - Class component using `getDerivedStateFromError()` and `componentDidCatch()`
  - Renders error message and "try again" button

## Logging

**Framework:** Python uses standard `logging` module with root logger from settings

**Patterns:**
- Initialize logger at module level: `logger = logging.getLogger(__name__)`
- Configure via `pyproject.toml` and `config/settings.py` with log level from env
- Format: `"%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"` (from `api/main.py`)
- Use appropriate levels:
  - `logger.info()` for lifecycle events: startup, shutdown, request summaries
  - `logger.warning()` for rejected auth, invalid data: `logger.warning("Rejected invalid API key prefix=%s…", raw_key[:8])`
  - `logger.error()` for exceptions with context: `logger.error("DB error during key lookup: %s", exc)`
  - `logger.exception()` in except blocks: `logger.exception("Composite analysis failed: %s", exc)`

**JavaScript:** Uses browser console (no centralized logging framework)
- Error boundary logs to console.error: `console.error('[MacroPulse] Unhandled render error:', error, info)`

## Comments

**When to Comment:**
- Document public function/class purposes with docstrings (Python)
- Explain non-obvious logic or workarounds
- Mark sections with ASCII dividers for large files

**Docstring Examples:**

```python
# From api/main.py
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start / stop the background scheduler and DB pool with the app lifecycle."""
    ...

# From database/connection.py
@contextlib.contextmanager
def get_sync_cursor(
    autocommit: bool = False,
) -> Generator[psycopg2.extras.RealDictCursor, None, None]:
    """Context-managed cursor with automatic commit / rollback and pool return."""
    ...
```

**JSDoc/TSDoc:**
- React components use inline comments to explain complex JSX
- No formal JSDoc decorators in use

```jsx
/**
 * Global React error boundary.
 * Catches any unhandled JS error in the component tree and renders
 * a recoverable error card instead of a blank screen.
 */
export default class ErrorBoundary extends Component {
  ...
}
```

**Section Markers:**
- ASCII divider pattern: `# ── Section Name ─────────────────────────────`
- Used to organize large files into logical sections
- Examples: auth.py uses section markers for "Dev-mode", "Owner key", "Primary path"

## Function Design

**Size:**
- Functions typically 20-80 lines
- Shorter functions preferred for async handlers
- Service/inference functions may be longer if logically cohesive

**Parameters:**
- Use type hints for all parameters and return values
- Optional parameters documented in docstrings
- Use `Depends()` for FastAPI dependency injection

**Return Values:**
- Python: Always return typed values or None
  - Service methods return `dict[str, Any]` with documented keys
  - Route handlers return Pydantic response models
- JavaScript: Return objects/arrays or null for empty states
  - API methods return promises resolved with JSON data
  - Hooks return objects with `{ data, loading, error, refetch }`

## Module Design

**Exports:**
- Python: Use explicit imports in route files, no wildcard imports
  - Example: `from api.routes.auth import router as auth_router`
- JavaScript: Named exports for utilities, default exports for components/views
  - Example: `export const api = { ... }` for lib/api.js
  - Example: `export default function StatCard() { ... }` for components

**Barrel Files:**
- Not used in this codebase
- Each route defines its own router: `router = APIRouter(prefix="/v1", tags=[...])`

## Configuration and Constants

**Python:**
- All config centralized in `config/settings.py` using Pydantic BaseSettings
- Environment variables prefixed with app domain (e.g., `FRED_API_KEY`, `DB_HOST`)
- Settings accessed via singleton: `get_settings()` with `@lru_cache`
- Constants in files where used (e.g., `_FREE_HISTORY_LIMIT = 30` in `api/routes/regime.py`)

**JavaScript:**
- Constants defined in component files or lib utilities
- API base URL: empty string for relative paths (proxied by Vite dev server)
- Feature flags/limits: inline constants (e.g., `const FREE_HISTORY_LIMIT = 30`)
- Configuration via localStorage for API keys

## Class Design (Python)

**Pattern:**
- Use dataclasses or simple dicts instead of full OOP for data structures
- Service classes used for stateful operations with lazy initialization
  - Example: `RegimeInferenceService` with lazy-loaded models via `@property`
- Dependency injection via FastAPI `Depends()` instead of class inheritance

**Example from `services/inference.py`:**
```python
class RegimeInferenceService:
    def __init__(self, model_version: str | None = None) -> None:
        self.version = model_version or settings.default_model_version
        self._pca: PCAModel | None = None
        self._hmm: HMMModel | None = None

    @property
    def pca(self) -> PCAModel:
        if self._pca is None:
            self._pca = PCAModel.load(self.version)
        return self._pca
```

---

*Convention analysis: 2026-03-18*
