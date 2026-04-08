"""
MacroPulse – FastAPI application entry point.

Run with:
    uvicorn api.main:app --reload

Serves:
  • REST API (regime, liquidity, factors, drift, backtest)
  • WebSocket stream (/ws/regime)
  • Built-in pipeline scheduler
  • Static frontend (production builds of the dashboard)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app

from api.middleware.rate_limit import RateLimitMiddleware
from api.routes.auth import router as auth_router
from api.routes.billing import router as billing_router
from api.routes.analysis import router as analysis_router
from api.routes.backtest import router as backtest_router
from api.routes.commentary import router as commentary_router
from api.routes.dashboard import router as dashboard_router
from api.routes.forecast import router as forecast_router
from api.routes.performance import router as performance_router
from api.routes.regime import router as regime_router
from api.routes.public_config import router as public_config_router
from api.routes.signals import router as signals_router
from api.routes.model import router as model_router
from api.routes.pipeline import router as pipeline_router
from api.routes.public import router as public_router
from api.routes.webhook import router as webhook_router
from api.routes.websocket import router as ws_router
from api.routes.irl import router as irl_router
from api.schemas.responses import HealthResponse
from config.settings import get_settings

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def _run_migrations() -> None:
    """Apply all SQL migration files in order. All DDL uses IF NOT EXISTS — safe to re-run."""
    from database.connection import get_db_conn

    migrations_dir = Path(__file__).parent.parent / "database" / "migrations"
    if not migrations_dir.is_dir():
        return
    sql_files = sorted(migrations_dir.glob("*.sql"))
    for path in sql_files:
        sql = path.read_text(encoding="utf-8")
        try:
            async with get_db_conn() as conn:
                await conn.execute(sql)
            logger.info("Migration applied: %s", path.name)
        except Exception as exc:
            logger.error("Migration failed (%s): %s", path.name, exc)
            raise


def _validate_webhook_secrets() -> None:
    """Raise at startup if LS_WEBHOOK_SECRET is not set in production."""
    import os
    env = get_settings().env
    secret = os.getenv("LS_WEBHOOK_SECRET", "").strip()
    if not secret:
        if env == "production":
            raise RuntimeError(
                "LS_WEBHOOK_SECRET must be set in production. "
                "Configure it in .env or via environment injection before starting."
            )
        else:
            logger.warning(
                "LS_WEBHOOK_SECRET not set — Lemon Squeezy webhook validation disabled. "
                "This must be set before deploying to production (ENV=production)."
            )


def _validate_cors_origins() -> None:
    """Raise at startup if CORS wildcard is configured in production (SEC-42)."""
    settings = get_settings()
    if settings.env == "production" and "*" in settings.cors_origins:
        raise RuntimeError(
            "CORS wildcard '*' is not allowed in production. "
            "Set CORS_ORIGINS to explicit allowed origins (e.g., https://macropulse.live) "
            "in .env or via environment injection before starting."
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start / stop the background scheduler and DB pool with the app lifecycle."""
    from services.scheduler import start_scheduler, stop_scheduler
    from services.mta_signer import init_signer
    from database.connection import init_pool, close_pool

    logger.info("Starting MacroPulse API v%s", settings.app_version)
    await init_pool(settings.database_url)
    await _run_migrations()
    init_signer(settings.mta_signing_key_hex)
    _validate_webhook_secrets()   # SEC-20: raise if production + LS_WEBHOOK_SECRET missing
    _validate_cors_origins()      # SEC-42: raise if production + CORS wildcard
    start_scheduler()
    yield
    stop_scheduler()
    await close_pool()
    logger.info("MacroPulse API shut down.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Macro regime intelligence API. "
        "Produces daily probabilistic macro regime signals derived from "
        "PCA latent factors, Hidden Markov Models, GARCH volatility, "
        "ARIMA forecasts, and rule-based multi-domain analysis."
    ),
    lifespan=lifespan,
    docs_url=None,    # Disabled — use branded docs at macropulse.live/api-docs
    redoc_url=None,
    openapi_url="/openapi.json",  # schema still available for tooling
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware, limit_per_day=settings.rate_limit_per_day)

# ── Routes ───────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(regime_router)
app.include_router(commentary_router)
app.include_router(dashboard_router)
app.include_router(backtest_router)
app.include_router(ws_router)
app.include_router(forecast_router)
app.include_router(analysis_router)
app.include_router(performance_router)
app.include_router(public_config_router)
app.include_router(signals_router)
app.include_router(model_router)
app.include_router(pipeline_router)
app.include_router(public_router)
app.include_router(webhook_router)
app.include_router(irl_router)

# ── Prometheus metrics ────────────────────────────────────────────────
# Mounted after all API routes so it doesn't shadow any route prefix.
# Exempted from rate limiting in api/middleware/rate_limit.py.
_metrics_app = make_asgi_app()
app.mount("/metrics", _metrics_app)


@app.get("/docs", include_in_schema=False)
def redirect_docs():
    """Redirect to branded API documentation page."""
    return RedirectResponse("https://macropulse.live/api-docs", status_code=301)


@app.get("/dashboard", include_in_schema=False)
def redirect_dashboard():
    """Redirect /dashboard to root — the React SPA handles all views."""
    return RedirectResponse("/", status_code=301)


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """Liveness probe — includes database connectivity check."""
    from database.connection import get_db_conn

    db_status = "ok"
    try:
        async with get_db_conn() as conn:
            await conn.execute("SELECT 1")
    except Exception as exc:
        logger.warning("Health check DB ping failed: %s", exc)
        db_status = "error"

    overall = "ok" if db_status == "ok" else "degraded"
    return HealthResponse(
        status=overall,
        version=settings.app_version,
        checks={"database": db_status},
    )


# ── Static frontend (served in production) ───────────────────────
# NOTE: must be mounted AFTER all API routes — StaticFiles catches everything
_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    _index_html = _frontend_dist / "index.html"

    @app.get("/", include_in_schema=False)
    def serve_root():
        """Serve index.html with no-cache so stale JS hashes never break the app."""
        return FileResponse(str(_index_html), headers={"Cache-Control": "no-store"})

    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
    logger.info("Serving frontend from %s", _frontend_dist)
