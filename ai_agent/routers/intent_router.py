"""
Classifies patient messages into routes: DB, RAG, DB_RAG, LLM, CLARIFY, EMERGENCY.

SQL strings are raw LLM output; callers must validate with tools/sql_validator before execution.

Orchestrator should call get_recent_turns() first and pass recent_history into route_intent.
"""

import json
import logging

from core.config import config
from core.connections import async_openai_client
from prompts.intent_prompt import INTENT_ROUTER_PROMPT

logger = logging.getLogger(__name__)

VALID_ROUTES = {"DB", "RAG", "DB_RAG", "LLM", "CLARIFY", "EMERGENCY"}

# Fallback keyword set when OpenAI fails - still escalate physical-danger language.
EMERGENCY_KEYWORDS = {
    "fell", "fall", "fallen", "help", "pain", "hurt", "hurts",
    "breathe", "breathing", "emergency", "bleeding", "bleed",
    "heart", "attack", "chest", "dying", "die", "can't move",
    "can't get up", "unconscious", "fainted", "choking",
}

CLARIFY_FALLBACK = {
    "route": "CLARIFY",
    "entities": {
        "medication_names": [],
        "symptoms": [],
        "body_parts": [],
        "time_references": [],
        "activities": [],
        "emotions": [],
        "medical_concepts": [],
    },
    "sql": None,
    "confidence": "low",
    "reasoning": "Failed to parse router response; defaulting to CLARIFY.",
}

EMERGENCY_FALLBACK = {
    "route": "EMERGENCY",
    "entities": {
        "medication_names": [],
        "symptoms": [],
        "body_parts": [],
        "time_references": [],
        "activities": [],
        "emotions": [],
        "medical_concepts": [],
    },
    "sql": None,
    "confidence": "high",
    "reasoning": "Emergency keywords detected in message - API failure fallback.",
}


# Fallback only: detects danger-related words when the model or JSON parsing fails.
def _is_emergency_message(message: str) -> bool:
    """
    Lightweight keyword check used ONLY as a fallback when the OpenAI
    API call fails or JSON parsing fails.
    """
    words = set(message.lower().split())
    return bool(words & EMERGENCY_KEYWORDS)


# Calls the classifier model (intent_router_model from config) with INTENT_ROUTER_PROMPT and returns route + metadata.
async def route_intent(
    message: str,
    recent_history: str,
    patient_id: str,
) -> dict:
    """
    Classifies a patient message. On API/parse/validation failures, uses
    EMERGENCY_FALLBACK if emergency keywords match, otherwise CLARIFY_FALLBACK.
    """
    prompt = INTENT_ROUTER_PROMPT.format(
        message=message,
        recent_history=recent_history if recent_history else "No history yet.",
        patient_id=patient_id,
    )

    try:
        response = await async_openai_client.chat.completions.create(
            model=config.intent_router_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=800,
            response_format={"type": "json_object"},
        )

        raw_output = response.choices[0].message.content

    except Exception:
        logger.exception("OpenAI API call failed during intent routing (patient_id=%s)", patient_id)
        if _is_emergency_message(message):
            logger.warning(
                "Emergency keyword fallback after API failure (patient_id=%s)",
                patient_id,
            )
            return EMERGENCY_FALLBACK
        return CLARIFY_FALLBACK

    if not raw_output or not raw_output.strip():
        logger.error(
            "Intent router returned empty content (patient_id=%s)",
            patient_id,
        )
        if _is_emergency_message(message):
            return EMERGENCY_FALLBACK
        return CLARIFY_FALLBACK

    try:
        result = json.loads(raw_output)
    except json.JSONDecodeError:
        logger.exception(
            "Failed to parse intent router JSON (patient_id=%s, raw_len=%s)",
            patient_id,
            len(raw_output),
        )
        logger.debug("Intent router raw output sample: %.500s", raw_output)
        if _is_emergency_message(message):
            logger.warning(
                "Emergency keyword fallback after JSON parse failure (patient_id=%s)",
                patient_id,
            )
            return EMERGENCY_FALLBACK
        return CLARIFY_FALLBACK

    if not _validate_result(result):
        logger.error(
            "Intent router output failed validation: patient_id=%s payload=%s",
            patient_id,
            result,
        )
        if _is_emergency_message(message):
            return EMERGENCY_FALLBACK
        return CLARIFY_FALLBACK

    logger.info(
        "Intent routed: patient_id=%s route=%s confidence=%s reasoning=%s",
        patient_id,
        result["route"],
        result["confidence"],
        result["reasoning"],
    )

    return result


# Ensures required keys, enums, EMERGENCY confidence, DB SQL rules, and entity lists exist.
def _validate_result(result: dict) -> bool:
    """Returns True if result is usable; patches missing entity keys and EMERGENCY confidence."""
    required_fields = ["route", "entities", "sql", "confidence", "reasoning"]
    for field in required_fields:
        if field not in result:
            logger.error("Intent router missing field: %s", field)
            return False

    if result["route"] not in VALID_ROUTES:
        logger.error("Intent router invalid route: %s", result.get("route"))
        return False

    if result["confidence"] not in {"high", "medium", "low"}:
        logger.error("Intent router invalid confidence: %s", result.get("confidence"))
        return False

    if result["route"] == "EMERGENCY":
        result["confidence"] = "high"

    if result["route"] in {"DB", "DB_RAG"} and not result["sql"]:
        logger.error("Intent router missing sql for DB route: %s", result["route"])
        return False

    if result["route"] not in {"DB", "DB_RAG"} and result["sql"] is not None:
        logger.warning(
            "SQL present on non-DB route %s; clearing sql field.",
            result["route"],
        )
        result["sql"] = None

    required_entity_keys = {
        "medication_names", "symptoms", "body_parts",
        "time_references", "activities", "emotions", "medical_concepts",
    }
    if not isinstance(result["entities"], dict):
        logger.error("Intent router entities is not a dict")
        return False

    for key in required_entity_keys:
        if key not in result["entities"]:
            result["entities"][key] = []

    return True
