"""
Insert/update ``reminders`` rows for scheduled push follow-up (sent / missed / responded / superseded).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from core.connections import supabase_client

logger = logging.getLogger(__name__)

VALID_STATUSES = frozenset({"sent", "missed", "responded", "superseded"})


# Creates one reminder instance when a cron job fires; returns reminder_id or None on failure.
def insert_reminder_instance(
    *,
    patient_id: str,
    reminder_type: str,
    patient_medications_id: str | None,
    patient_meal_id: str | None,
    patient_activity_id: str | None,
) -> str | None:
    if supabase_client is None:
        logger.warning("[queries.reminders_write] Supabase unavailable; skip insert")
        return None

    payload: dict[str, Any] = {
        "patient_id": patient_id.strip(),
        "reminder_type": reminder_type.strip(),
        "reminder_time": datetime.now(timezone.utc).isoformat(),
        "status": "sent",
        "patient_medications_id": patient_medications_id,
        "patient_meal_id": patient_meal_id,
        "patient_activity_id": patient_activity_id,
    }

    try:
        resp = supabase_client.table("reminders").insert(payload).execute()
        rows = resp.data or []
        if not rows:
            # fallback: query the latest reminder for this patient
            fallback = (
                supabase_client.table("reminders")
                .select("reminder_id")
                .eq("patient_id", patient_id.strip())
                .order("reminder_time", desc=True)
                .limit(1)
                .execute()
            )
            rows = fallback.data or []
        if not rows:
            logger.error("[queries.reminders_write] insert returned no row patient_id=%s", patient_id)
            return None
        rid = rows[0].get("reminder_id")
        sid = str(rid) if rid is not None else None
        if sid:
            logger.info("[queries.reminders_write] inserted reminder_id=%s type=%s", sid, reminder_type)
        return sid
    except Exception:
        logger.exception("[queries.reminders_write] insert failed patient_id=%s", patient_id)
        return None


# Sets lifecycle status after patient reply, timeout, or superseding by a newer reminder.
def update_reminder_status(reminder_id: str | None, status: str) -> None:
    if not reminder_id or status not in VALID_STATUSES:
        if reminder_id:
            logger.warning("[queries.reminders_write] invalid status=%s reminder_id=%s", status, reminder_id)
        return
    if supabase_client is None:
        logger.warning("[queries.reminders_write] Supabase unavailable; skip update reminder_id=%s", reminder_id)
        return

    try:
        supabase_client.table("reminders").update({"status": status}).eq(
            "reminder_id",
            reminder_id,
        ).execute()
        logger.info("[queries.reminders_write] reminder_id=%s -> %s", reminder_id, status)
    except Exception:
        logger.exception("[queries.reminders_write] update failed reminder_id=%s", reminder_id)


__all__ = ["VALID_STATUSES", "insert_reminder_instance", "update_reminder_status"]
