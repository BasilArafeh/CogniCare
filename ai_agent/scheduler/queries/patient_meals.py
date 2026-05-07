"""
Supabase: ``patient_meals`` + nested ``meals`` (schema: meal_time, FK meal_id → meal_type).
"""

from __future__ import annotations

import logging
from typing import Any

from core.connections import supabase_client
from scheduler._time_utils import hour_minute_from_db_time

logger = logging.getLogger(__name__)

_SELECT = "patient_meal_id,meal_id,patient_id,meal_time,meals(meal_type)"


# Returns cron-ready rows with flat ``meal_type`` for reminder copy.
def select_meal_schedule_rows() -> list[dict[str, Any]]:
    if supabase_client is None:
        logger.warning("[queries.patient_meals] Supabase unavailable")
        return []
    try:
        resp = (
            supabase_client.table("patient_meals")
            .select(_SELECT)
            .execute()
        )
    except Exception:
        logger.exception("[queries.patient_meals] select failed table=patient_meals")
        return []

    rows: list[dict[str, Any]] = []
    for raw in resp.data or []:
        if hour_minute_from_db_time(raw.get("meal_time")) is None:
            continue
        meal = raw.get("meals")
        meal_type = meal.get("meal_type") if isinstance(meal, dict) else None
        rows.append(
            {
                "patient_meal_id": raw.get("patient_meal_id"),
                "patient_id": raw.get("patient_id"),
                "meal_id": raw.get("meal_id"),
                "meal_time": raw.get("meal_time"),
                "meal_type": meal_type,
            }
        )

    logger.info("[queries.patient_meals] %s cron-ready row(s)", len(rows))
    return rows


__all__ = ["select_meal_schedule_rows"]
