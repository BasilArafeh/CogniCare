"""
Supabase: ``patient_medications`` + nested ``medication`` (schema: medication_time, dosage, FK medication_id).
"""

from __future__ import annotations

import logging
from typing import Any

from core.connections import supabase_client
from scheduler._time_utils import hour_minute_from_db_time

logger = logging.getLogger(__name__)

# FK embed name must match Supabase/PostgREST (typically singular table ``medication``).
_SELECT = (
    "patient_medications_id,medication_id,patient_id,medication_time,dosage,"
    "medication(medication_name)"
)


# Returns cron-ready rows with flat ``medication_name`` for the reminder layer.
def select_medication_schedule_rows() -> list[dict[str, Any]]:
    if supabase_client is None:
        logger.warning("[queries.patient_medications] Supabase unavailable")
        return []
    try:
        resp = (
            supabase_client.table("patient_medications")
            .select(_SELECT)
            .execute()
        )
    except Exception:
        logger.exception("[queries.patient_medications] select failed table=patient_medications")
        return []

    rows: list[dict[str, Any]] = []
    for raw in resp.data or []:
        if hour_minute_from_db_time(raw.get("medication_time")) is None:
            continue
        med = raw.get("medication")
        med_name = med.get("medication_name") if isinstance(med, dict) else None
        rows.append(
            {
                "patient_medications_id": raw.get("patient_medications_id"),
                "patient_id": raw.get("patient_id"),
                "medication_time": raw.get("medication_time"),
                "dosage": raw.get("dosage"),
                "medication_id": raw.get("medication_id"),
                "medication_name": med_name,
            }
        )

    logger.info("[queries.patient_medications] %s cron-ready row(s)", len(rows))
    return rows


__all__ = ["select_medication_schedule_rows"]
