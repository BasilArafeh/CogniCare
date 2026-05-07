"""
Activity reminders: cron at clock time from ``start_time``; label from ``activity_type`` / ``description``.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.cron import CronTrigger

from scheduler._time_utils import hour_minute_from_db_time
from scheduler.queries.patient_activities import select_activity_schedule_rows
from scheduler.reminder_delivery import deliver_reminder_to_patient

logger = logging.getLogger(__name__)

JOB_PREFIX = "cognicare:dyn:act:"


def fire_activity_reminder(patient_id: str, activity_label: str | None, schedule_row_id: str) -> None:
    label = (activity_label or "your scheduled activity").strip()
    pid = patient_id.strip()
    text = f"It's time for {label}. Please reply once you've started or finished safely."
    deliver_reminder_to_patient(
        patient_id=pid,
        patient_message=text,
        reminder_type="activity",
        item_label=label,
        patient_activity_id=str(schedule_row_id),
    )


def register_activity_jobs(scheduler: BaseScheduler, scheduler_tz: str) -> None:
    for row in select_activity_schedule_rows():
        rid = row.get("patient_activity_id")
        pid = str(row.get("patient_id") or "").strip()
        hm = hour_minute_from_db_time(row.get("start_time"))
        if rid is None or not pid or hm is None:
            continue
        h, m = hm
        act_type = row.get("activity_type")
        desc = row.get("description")
        label = (str(act_type).strip() if act_type else "") or (str(desc).strip() if desc else "") or None
        job_id = f"{JOB_PREFIX}{rid}"
        try:
            scheduler.add_job(
                fire_activity_reminder,
                CronTrigger(hour=h, minute=m, timezone=scheduler_tz),
                kwargs={
                    "patient_id": pid,
                    "activity_label": label,
                    "schedule_row_id": str(rid),
                },
                id=job_id,
                replace_existing=True,
            )
            logger.debug(
                "[activity_reminder] job=%s patient_id=%s time=%02d:%02d",
                job_id,
                pid,
                h,
                m,
            )
        except Exception:
            logger.exception("[activity_reminder] add_job failed patient_id=%s", pid)


__all__ = ["register_activity_jobs", "fire_activity_reminder"]
