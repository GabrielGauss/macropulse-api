"""
Pipeline scheduler for MacroPulse.

Uses APScheduler to run the daily pipeline on a cron schedule.
Can be started standalone or embedded in the API process.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import get_settings
from data.pipelines.daily_pipeline import run_daily_pipeline

logger = logging.getLogger(__name__)


def _run_pipeline_with_alert() -> None:
    """Run the daily pipeline and email the owner if it fails."""
    try:
        run_daily_pipeline()
    except Exception as exc:
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
