"""
Pipeline scheduler for MacroPulse.

Uses APScheduler to run the daily pipeline on a cron schedule.
Can be started standalone or embedded in the API process.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from api.metrics import (
    DB_POOL_IDLE,
    DB_POOL_SIZE,
    PIPELINE_DURATION_SECONDS,
    PIPELINE_LAST_SUCCESS_TIMESTAMP,
    PIPELINE_RUNS_TOTAL,
)
from config.settings import get_settings
from data.pipelines.daily_pipeline import run_daily_pipeline

logger = logging.getLogger(__name__)

_STALENESS_THRESHOLD_HOURS = 26


def _run_pipeline_with_alert() -> None:
    """Run the daily pipeline, emit Prometheus metrics, and email the owner if it fails."""
    t0 = time.monotonic()
    try:
        run_daily_pipeline()
        PIPELINE_RUNS_TOTAL.labels(status="success").inc()
        PIPELINE_LAST_SUCCESS_TIMESTAMP.set(time.time())
    except Exception as exc:
        PIPELINE_RUNS_TOTAL.labels(status="failure").inc()
        logger.error("Daily pipeline FAILED: %s", exc, exc_info=True)
        settings = get_settings()
        if settings.pipeline_alert_email:
            try:
                from services.email import send_email
                send_email(
                    to=settings.pipeline_alert_email,
                    subject="[MacroPulse] Pipeline failure",
                    html=(
                        f"<p>The MacroPulse daily pipeline failed at "
                        f"<strong>{__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</strong>.</p>"
                        f"<p><code>{exc}</code></p>"
                        f"<p>Check the server logs for full traceback. "
                        f"The previous regime signal is still being served.</p>"
                    ),
                )
            except Exception as mail_exc:
                logger.error("Could not send pipeline failure alert: %s", mail_exc)
        raise
    finally:
        PIPELINE_DURATION_SECONDS.observe(time.monotonic() - t0)


def _update_pool_metrics() -> None:
    """Refresh DB pool size/idle gauges from the asyncpg pool. Scheduled every 60s."""
    from database.connection import _pool
    if _pool is not None:
        try:
            DB_POOL_SIZE.set(_pool.get_size())
            DB_POOL_IDLE.set(_pool.get_idle_size())
        except Exception as exc:
            logger.debug("Could not read pool metrics: %s", exc)


async def _fetch_last_successful_run_ts() -> datetime | None:
    """Return the run_ts of the last successful pipeline run, or None."""
    from database import queries
    row = await queries.fetch_latest_pipeline_run()
    if row is None:
        return None
    # Only consider successful runs
    if row.get("status") != "success":
        return None
    run_ts = row.get("run_ts")
    if run_ts is None:
        return None
    # run_ts may be a datetime or a string — normalise to naive UTC datetime
    if isinstance(run_ts, str):
        run_ts = datetime.fromisoformat(run_ts.rstrip("Z"))
    # Strip timezone info for consistent arithmetic
    if hasattr(run_ts, "tzinfo") and run_ts.tzinfo is not None:
        run_ts = run_ts.replace(tzinfo=None)
    return run_ts


def _check_pipeline_staleness() -> None:
    """
    Alert via Brevo email if the last successful pipeline run is >26 hours old.

    Runs every 30 minutes. Uses asyncio.run() because BackgroundScheduler jobs
    execute in threads (no running event loop).
    """
    try:
        last_success = asyncio.run(_fetch_last_successful_run_ts())
    except Exception as exc:
        logger.error("Staleness check DB query failed: %s", exc)
        return

    if last_success is None:
        # No successful run recorded yet — skip alerting
        return

    age_hours = (datetime.utcnow() - last_success).total_seconds() / 3600
    if age_hours <= _STALENESS_THRESHOLD_HOURS:
        return

    logger.warning(
        "Pipeline staleness detected: last success was %.1f hours ago (threshold %dh)",
        age_hours,
        _STALENESS_THRESHOLD_HOURS,
    )

    settings = get_settings()
    alert_email = settings.pipeline_alert_email
    if not alert_email:
        logger.debug("pipeline_alert_email not set; skipping staleness email.")
        return

    try:
        from services.email import send_email
        send_email(
            to=alert_email,
            subject="[MacroPulse] Pipeline staleness alert",
            html=(
                f"<p>The MacroPulse daily pipeline has <strong>not run successfully</strong> "
                f"in the past <strong>{age_hours:.1f} hours</strong> "
                f"(threshold: {_STALENESS_THRESHOLD_HOURS}h).</p>"
                f"<p>Last successful run timestamp: "
                f"<code>{last_success.strftime('%Y-%m-%d %H:%M UTC')}</code></p>"
                f"<p>Check the server logs and pipeline status.</p>"
            ),
        )
    except Exception as mail_exc:
        logger.error("Could not send staleness alert email: %s", mail_exc)


_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> BackgroundScheduler:
    """Initialise and start the background scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        logger.info("Scheduler already running.")
        return _scheduler

    settings = get_settings()
    _scheduler = BackgroundScheduler(timezone="UTC")

    trigger = CronTrigger(
        hour=settings.pipeline_cron_hour,
        minute=settings.pipeline_cron_minute,
        timezone="UTC",
    )

    _scheduler.add_job(
        _run_pipeline_with_alert,
        trigger=trigger,
        id="daily_macro_pipeline",
        name="MacroPulse Daily Pipeline",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    _scheduler.add_job(
        _update_pool_metrics,
        trigger=IntervalTrigger(seconds=60),
        id="db_pool_metrics",
        name="DB Pool Metrics",
        replace_existing=True,
    )

    _scheduler.add_job(
        _check_pipeline_staleness,
        trigger=IntervalTrigger(minutes=30),
        id="pipeline_staleness_check",
        name="Pipeline Staleness Check",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "Scheduler started — pipeline runs daily at %02d:%02d UTC",
        settings.pipeline_cron_hour,
        settings.pipeline_cron_minute,
    )
    return _scheduler


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
        _scheduler = None
