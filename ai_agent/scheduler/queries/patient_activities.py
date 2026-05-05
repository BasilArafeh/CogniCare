"""
Supabase: ``patient_activities`` + nested ``activity`` (daily cron uses clock from ``start_time``).

Schema: start_time, end_time, description, FK activity_id → activity_type.
"""

from __future__ import annotations

import logging
from typing import Any

from core.connections import supabase_client
from scheduler._time_utils import hour_minute_from_db_time

logger = logging.getLogger(__name__)

_SELECT = (
    "patient_activity_id,activity_id,patient_id,start_time,end_time,description,"
    "activity(activity_type)"
)


# Daily reminder at the calendar time extracted from ``start_time`` (TIME or timestamptz).
def select_activity_schedule_rows() -> list[dict[str, Any]]:
    if supabase_client is None:
        logger.warning("[queries.patient_activities] Supabase unavailable")
        return []
    try:
        resp = (
            supabase_client.table("patient_activities")
            .select(_SELECT)
            .execute()
        )
    except Exception:
        logger.exception("[queries.patient_activities] select failed table=patient_activities")
        return []

    rows: list[dict[str, Any]] = []
    for raw in resp.data or []:
        if hour_minute_from_db_time(raw.get("start_time")) is None:
            continue
        act = raw.get("activity")
        activity_type = act.get("activity_type") if isinstance(act, dict) else None
        rows.append(
            {
                "patient_activity_id": raw.get("patient_activity_id"),
                "patient_id": raw.get("patient_id"),
                "activity_id": raw.get("activity_id"),
                "start_time": raw.get("start_time"),
                "end_time": raw.get("end_time"),
                "description": raw.get("description"),
                "activity_type": activity_type,
            }
        )

    logger.info("[queries.patient_activities] %s cron-ready row(s)", len(rows))
    return rows


__all__ = ["select_activity_schedule_rows"]
