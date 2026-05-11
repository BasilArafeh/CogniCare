"""
Medication reminders: APScheduler cron hooks; rows from ``scheduler.queries`` (patient_medications).
"""

from __future__ import annotations

import logging
from datetime import tzinfo

from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.cron import CronTrigger

from scheduler._time_utils import hour_minute_from_db_time
from scheduler.queries.patient_medications import select_medication_schedule_rows
from scheduler.reminder_delivery import deliver_reminder_to_patient

logger = logging.getLogger(__name__)

JOB_PREFIX = "cognicare:dyn:med:"


def fire_medication_reminder(patient_id: str, medication_name: str | None, schedule_row_id: str) -> None:
    name = (medication_name or "your medication").strip()
    pid = patient_id.strip()
    text = (
        f"It's time to take {name}. Please confirm when you've taken it, "
        "or tap reply so I know you're alright."
    )
    deliver_reminder_to_patient(
        patient_id=pid,
        patient_message=text,
        reminder_type="medication",
        item_label=name,
        patient_medications_id=str(schedule_row_id),
    )


def register_medication_jobs(scheduler: BaseScheduler, scheduler_tz: tzinfo) -> None:
    for row in select_medication_schedule_rows():
        rid = row.get("patient_medications_id")
        pid = str(row.get("patient_id") or "").strip()
        hm = hour_minute_from_db_time(row.get("medication_time"))
        if rid is None or not pid or hm is None:
            continue
        h, m = hm
        med_name = row.get("medication_name")
        job_id = f"{JOB_PREFIX}{rid}"
        try:
            scheduler.add_job(
                fire_medication_reminder,
                CronTrigger(hour=h, minute=m, timezone=scheduler_tz),
                kwargs={
                    "patient_id": pid,
                    "medication_name": str(med_name) if med_name else None,
                    "schedule_row_id": str(rid),
                },
                id=job_id,
                replace_existing=True,
            )
            logger.debug(
                "[medication_reminder] job=%s patient_id=%s time=%02d:%02d",
                job_id,
                pid,
                h,
                m,
            )
        except Exception:
            logger.exception("[medication_reminder] add_job failed patient_id=%s", pid)


__all__ = ["register_medication_jobs", "fire_medication_reminder"]
