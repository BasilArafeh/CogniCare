"""
APScheduler bootstrap for CogniCare reminders.

On FastAPI startup (lifespan), ``start_scheduler()`` starts a background scheduler that
reads every patient's medication, meal, and activity times from Supabase, registers cron
jobs for those clock times, and reloads the full schedule from the database every hour.
Jobs run silently until a slot fires; see ``scheduler.reminder_delivery`` for outbound
logging, Teammate 2 webhook delivery, and the 5-minute reply window.
"""

from __future__ import annotations

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from scheduler.activity_reminder import register_activity_jobs
from scheduler.meal_reminder import register_meal_jobs
from scheduler.medication_reminder import register_medication_jobs

logger = logging.getLogger(__name__)

_dynamic_prefix = "cognicare:dyn:"
_reload_job_id = "cognicare:meta:reload_schedules"
_scheduler_singleton: BackgroundScheduler | None = None


# Drops DB-backed jobs before re-reading Supabase/PG via REST clients.
def _remove_dynamic_jobs(scheduler: BackgroundScheduler) -> None:
    for job in scheduler.get_jobs():
        jid = str(job.id or "")
        if jid.startswith(_dynamic_prefix):
            scheduler.remove_job(jid)


# Rebuilds meds/meals/activity cron fires from Postgres (Supabase).
def reload_schedule_jobs(scheduler: BackgroundScheduler) -> None:
    timezone_str = (os.getenv("SCHEDULER_TIMEZONE") or "UTC").strip()

    _remove_dynamic_jobs(scheduler)
    register_medication_jobs(scheduler, timezone_str)
    register_meal_jobs(scheduler, timezone_str)
    register_activity_jobs(scheduler, timezone_str)
    logger.info(
        "[scheduler] Dynamic jobs refreshed total_jobs=%s",
        len(scheduler.get_jobs()),
    )


# Spins up daemon threads with APScheduler unless COGNICARE_SCHEDULER_ENABLED is ``false``.
def start_scheduler() -> BackgroundScheduler:
    global _scheduler_singleton
    enabled = os.getenv("COGNICARE_SCHEDULER_ENABLED", "true").strip().lower() not in {"0", "false", "no"}

    timezone_str = (os.getenv("SCHEDULER_TIMEZONE") or "UTC").strip()
    scheduler = BackgroundScheduler(timezone=timezone_str)
    if not enabled:
        logger.info("[scheduler] Disabled via COGNICARE_SCHEDULER_ENABLED")
        scheduler.start(paused=True)
        _scheduler_singleton = scheduler
        return scheduler

    reload_schedule_jobs(scheduler)
    scheduler.add_job(
        lambda: reload_schedule_jobs(scheduler),
        IntervalTrigger(hours=1),
        id=_reload_job_id,
        replace_existing=True,
    )
    scheduler.start()
    _scheduler_singleton = scheduler
    logger.info("[scheduler] APScheduler running timezone=%s", timezone_str)
    return scheduler


# Idempotent teardown for graceful shutdown.
def shutdown_scheduler(wait: bool = True) -> None:
    global _scheduler_singleton
    if _scheduler_singleton is None:
        return
    try:
        _scheduler_singleton.shutdown(wait=wait)
        logger.info("[scheduler] Shutdown complete wait=%s", wait)
    except Exception:
        logger.exception("[scheduler] Shutdown error")
    _scheduler_singleton = None


__all__ = ["reload_schedule_jobs", "start_scheduler", "shutdown_scheduler"]
