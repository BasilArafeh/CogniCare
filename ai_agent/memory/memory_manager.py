"""
agent/memory/memory_manager.py
--------------------------------
Handles all memory operations for the agent layer.
Reads and writes to Supabase for long-term memory.
LangChain InMemorySaver handles short-term memory automatically.

Functions:
  - get_recent_turns()  → used by intent router before classification
  - load_full_memory()  → used by agent at session start
  - save_interaction()  → called after every turn
"""

import logging
from datetime import datetime, timezone

from agent.core.connections import supabase_client

logger = logging.getLogger(__name__)


# Fetches last n turns for a patient as a plain string.
# Called by intent_router.py to give the router recent context.
def get_recent_turns(patient_id: int, n: int = 3) -> str:
    try:
        response = (
            supabase_client
            .table("interaction_log")
            .select("user_text, assistant_text, interaction_timestamp")
            .eq("patient_id", patient_id)
            .order("interaction_timestamp", desc=True)
            .limit(n)
            .execute()
        )

        rows = response.data
        if not rows:
            return ""

        # Reverse so oldest turn comes first
        rows = list(reversed(rows))

        turns = []
        for row in rows:
            turns.append(f"Patient: {row['user_text']}")
            turns.append(f"Agent: {row['assistant_text']}")

        return "\n".join(turns)

    except Exception as e:
        logger.error(f"Failed to fetch recent turns for patient {patient_id}: {e}")
        return ""


# Fetches full conversation history + patient memory profile.
# Called by orchestrator.py when building the agent's context at session start.
def load_full_memory(patient_id: int) -> dict:
    try:
        history_response = (
            supabase_client
            .table("interaction_log")
            .select("user_text, assistant_text, interaction_timestamp")
            .eq("patient_id", patient_id)
            .order("interaction_timestamp", desc=True)
            .limit(20)
            .execute()
        )

        memory_response = (
            supabase_client
            .table("patient_memory")
            .select("*")
            .eq("patient_id", patient_id)
            .maybe_single()          # returns None instead of raising if no row exists
            .execute()
        )

        return {
            "history": list(reversed(history_response.data or [])),
            "profile": memory_response.data or {}
        }

    except Exception as e:
        logger.error(f"Failed to load full memory for patient {patient_id}: {e}")
        return {"history": [], "profile": {}}


# Saves a completed turn to interaction_log after every agent response.
# Called by orchestrator.py after the agent returns its response.
def save_interaction(
    patient_id: int,
    user_text: str,
    assistant_text: str,
    detected_intent: str,
    confusion_flag: bool = False
) -> None:
    try:
        supabase_client.table("interaction_log").insert({
            "patient_id": patient_id,
            "user_text": user_text,
            "assistant_text": assistant_text,
            "detected_intent": detected_intent,
            "confusion_flag": confusion_flag,
            "interaction_timestamp": datetime.now(timezone.utc).isoformat()
        }).execute()

    except Exception as e:
        logger.error(f"Failed to save interaction for patient {patient_id}: {e}")