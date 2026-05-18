"""
Meal reminders: APScheduler cron hooks; rows from ``patient_meals`` / ``meals.meal_type``.
"""

from __future__ import annotations

import logging
from datetime import tzinfo

from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.cron import CronTrigger

from scheduler._time_utils import hour_minute_from_db_time
from scheduler.queries.patient_meals import select_meal_schedule_rows
from scheduler.reminder_delivery import deliver_reminder_to_patient

logger = logging.getLogger(__name__)

JOB_PREFIX = "cognicare:dyn:meal:"


def fire_meal_reminder(patient_id: str, meal_label: str | None, schedule_row_id: str) -> None:
    label = (meal_label or "your meal").strip()
    pid = patient_id.strip()
    text = f"It's about time for {label}. Please tap reply when you've eaten."
    deliver_reminder_to_patient(
        patient_id=pid,
        patient_message=text,
        reminder_type="meal",
        item_label=label,
        patient_meal_id=str(schedule_row_id),
    )


def register_meal_jobs(scheduler: BaseScheduler, scheduler_tz: tzinfo) -> None:
    for row in select_meal_schedule_rows():
        rid = row.get("patient_meal_id")
        pid = str(row.get("patient_id") or "").strip()
        hm = hour_minute_from_db_time(row.get("meal_time"))
        if rid is None or not pid or hm is None:
            continue
        h, m = hm
        meal_disp = row.get("meal_type")
        job_id = f"{JOB_PREFIX}{rid}"
        try:
            scheduler.add_job(
                fire_meal_reminder,
                CronTrigger(hour=h, minute=m, timezone=scheduler_tz),
                kwargs={
                    "patient_id": pid,
                    "meal_label": str(meal_disp) if meal_disp else None,
                    "schedule_row_id": str(rid),
                },
                id=job_id,
                replace_existing=True,
            )
            logger.debug(
                "[meal_reminder] job=%s patient_id=%s time=%02d:%02d",
                job_id,
                pid,
                h,
                m,
            )
        except Exception:
            logger.exception("[meal_reminder] add_job failed patient_id=%s", pid)


__all__ = ["register_meal_jobs", "fire_meal_reminder"]
