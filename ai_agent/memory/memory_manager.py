"""
Supabase-backed long-term memory: recent turns, session history + profile, and interaction logging.

In-session buffering is handled by LangChain separately.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from core.connections import supabase_client

logger = logging.getLogger(__name__)


# Fetches the last n chat turns as a single string so the intent router has recent context.
def get_recent_turns(patient_id: str, n: int = 3) -> str:
    """
    Fetches last n turns for a patient as a plain string.
    Called by intent_router.py to provide the router with recent context.

    Args:
        patient_id: UUID string of the active patient.
        n: Number of recent turns to retrieve. Default is 3.

    Returns:
        Plain string of turns formatted as:
            Patient (timestamp): <message>
            Agent (timestamp): <response>
        Returns empty string if no history exists or on error.
    """
    if supabase_client is None:
        logger.warning(
            "get_recent_turns skipped: Supabase is not configured (patient_id=%s).",
            patient_id,
        )
        return ""
    try:
        response = (
            supabase_client.table("interaction_log")
            .select("user_text, assistant_text, interaction_timestamp")
            .eq("patient_id", patient_id)
            .order("interaction_timestamp", desc=True)
            .limit(n)
            .execute()
        )

        rows = response.data
        if not rows:
            logger.debug(
                "get_recent_turns: no rows for patient_id=%s n=%s",
                patient_id,
                n,
            )
            return ""

        # Reverse so oldest turn comes first (correct order for LLM context)
        rows = list(reversed(rows))

        turns = []
        for row in rows:
            ts = row.get("interaction_timestamp", "")
            user_text = row.get("user_text") or ""
            assistant_text = row.get("assistant_text") or ""
            turns.append(f"Patient ({ts}): {user_text}")
            turns.append(f"Agent ({ts}): {assistant_text}")

        logger.debug(
            "get_recent_turns: retrieved %s turn(s) for patient_id=%s",
            len(rows),
            patient_id,
        )
        return "\n".join(turns)

    except Exception:
        logger.exception("Failed to fetch recent turns for patient_id=%s", patient_id)
        return ""


# Loads capped interaction history and the patient_memory row used when assembling agent context at session start.
def load_full_memory(patient_id: str) -> dict[str, Any]:
    """
    Fetches full conversation history + patient memory profile.
    Called by orchestrator.py when building the agent's context at session start.

    Returns:
        dict with keys:
            "history": list of dicts (oldest to newest), max 20 turns
            "profile": dict for patient_memory row, or {}

    The orchestrator should format "history" into a plain string before {conversation_history}.
    """
    if supabase_client is None:
        logger.warning(
            "load_full_memory skipped: Supabase is not configured (patient_id=%s).",
            patient_id,
        )
        return {"history": [], "profile": {}}
    try:
        history_response = (
            supabase_client.table("interaction_log")
            .select("user_text, assistant_text, interaction_timestamp")
            .eq("patient_id", patient_id)
            .order("interaction_timestamp", desc=True)
            .limit(20)
            .execute()
        )

        memory_response = (
            supabase_client.table("patient_memory")
            .select("*")
            .eq("patient_id", patient_id)
            .maybe_single()
            .execute()
        )

        history = list(reversed(history_response.data or []))
        raw_profile = memory_response.data
        if raw_profile is None:
            profile: dict[str, Any] = {}
        elif isinstance(raw_profile, list):
            profile = raw_profile[0] if raw_profile else {}
        else:
            profile = raw_profile
        logger.info(
            "load_full_memory: patient_id=%s history_turns=%s profile_present=%s",
            patient_id,
            len(history),
            bool(profile),
        )
        return {"history": history, "profile": profile}

    except Exception:
        logger.exception("Failed to load full memory for patient_id=%s", patient_id)
        return {"history": [], "profile": {}}


def _coerce_single_row(data: Any) -> dict[str, Any]:
    if data is None:
        return {}
    if isinstance(data, list):
        return data[0] if data else {}
    if isinstance(data, dict):
        return data
    return {}


# Fast path for per-turn orchestration: patients row + patient_memory merged.
def load_patient_profile(patient_id: str) -> dict[str, Any]:
    if supabase_client is None:
        logger.warning(
            "load_patient_profile skipped: Supabase is not configured (patient_id=%s).",
            patient_id,
        )
        return {}
    try:
        patient_response = (
            supabase_client.table("patients")
            .select("patient_id, first_name, last_name, address, diagnosis_stage")
            .eq("patient_id", patient_id)
            .limit(1)
            .execute()
        )
        patient_row = _coerce_single_row(patient_response.data)

        memory_response = (
            supabase_client.table("patient_memory")
            .select("*")
            .eq("patient_id", patient_id)
            .maybe_single()
            .execute()
        )
        memory_row = _coerce_single_row(memory_response.data)

        profile: dict[str, Any] = {**patient_row, **memory_row}
        if patient_row.get("first_name"):
            profile["first_name"] = patient_row["first_name"]
        elif memory_row.get("preferred_name"):
            profile["first_name"] = memory_row["preferred_name"]
        if patient_row.get("diagnosis_stage"):
            profile["diagnosis_stage"] = patient_row["diagnosis_stage"]

        logger.info(
            "load_patient_profile: patient_id=%s first_name=%s profile_keys=%s",
            patient_id,
            profile.get("first_name"),
            sorted(profile.keys()),
        )
        return profile
    except Exception:
        logger.exception("Failed to load patient profile for patient_id=%s", patient_id)
        return {}


# Writes one completed user message + assistant reply to interaction_log after a turn finishes.
def save_interaction(
    patient_id: str,
    user_text: str,
    assistant_text: str,
    detected_intent: str,
    confusion_flag: bool = False,
) -> None:
    """
    Saves a completed turn to interaction_log after every agent response.

    confusion_flag is forced True when detected_intent is CLARIFY.
    """
    if detected_intent == "CLARIFY":
        confusion_flag = True

    if supabase_client is None:
        logger.warning(
            "save_interaction skipped: Supabase is not configured (patient_id=%s).",
            patient_id,
        )
        return

    try:
        supabase_client.table("interaction_log").insert(
            {
                "patient_id": patient_id,
                "user_text": user_text,
                "assistant_text": assistant_text,
                "detected_intent": detected_intent,
                "confusion_flag": confusion_flag,
                "interaction_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()

        logger.info(
            "Interaction saved: patient_id=%s intent=%s confusion=%s",
            patient_id,
            detected_intent,
            confusion_flag,
        )

    except Exception:
        logger.exception("Failed to save interaction for patient_id=%s", patient_id)
