"""
agent/router/intent_router.py
------------------------------
Classifies incoming patient messages into one of six routes:
DB, RAG, DB_RAG, LLM, CLARIFY, EMERGENCY.

Calls get_recent_turns() from memory_manager for context before classification.
Returns a structured dict consumed by orchestrator.py.

Note: SQL returned here is raw LLM output.
      Validation happens in tools/sql_validator.py before any execution.
"""

import json
import logging

from agent.core.connections import async_openai_client
from agent.prompts.intent_prompt import INTENT_ROUTER_PROMPT

logger = logging.getLogger(__name__)

VALID_ROUTES = {"DB", "RAG", "DB_RAG", "LLM", "CLARIFY", "EMERGENCY"}

CLARIFY_FALLBACK = {
    "route": "CLARIFY",
    "entities": {
        "medication_names": [],
        "symptoms": [],
        "body_parts": [],
        "time_references": [],
        "activities": [],
        "emotions": [],
        "medical_concepts": []
    },
    "sql": None,
    "confidence": "low",
    "reasoning": "Failed to parse router response — defaulting to CLARIFY."
}


async def route_intent(
    message: str,
    recent_history: str,
    patient_id: int
) -> dict:
    """
    Classifies a patient message into one of six routes:
    DB, RAG, DB_RAG, LLM, CLARIFY, EMERGENCY.

    Args:
        message:        The current patient message.
        recent_history: Last 2-3 conversation turns as a plain string.
        patient_id:     The active patient's ID for SQL generation.

    Returns:
        A dict containing route, entities, sql, confidence, and reasoning.
    """

    # Step 1: Format the prompt with runtime values
    prompt = INTENT_ROUTER_PROMPT.format(
        message=message,
        recent_history=recent_history if recent_history else "No history yet.",
        patient_id=patient_id
    )

    # Step 2: Call OpenAI
    try:
        response = await async_openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0,      # deterministic — consistent classification
            max_tokens=800,     # SQL JOINs can be verbose
            response_format={"type": "json_object"}
        )

        raw_output = response.choices[0].message.content

    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}")
        return CLARIFY_FALLBACK

    # Step 3: Parse the JSON response
    try:
        result = json.loads(raw_output)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse router JSON output: {e}\nRaw output: {raw_output}")
        return CLARIFY_FALLBACK

    # Step 4: Validate the result
    validated = _validate_result(result)
    if not validated:
        logger.error(f"Router result failed validation: {result}")
        return CLARIFY_FALLBACK

    # Step 5: Log the routing decision
    logger.info(
        f"[ROUTER] patient_id={patient_id} | "
        f"route={result['route']} | "
        f"confidence={result['confidence']} | "
        f"reasoning={result['reasoning']}"
    )

    return result


def _validate_result(result: dict) -> bool:
    """
    Validates the router output has all required fields and valid values.

    Args:
        result: The parsed JSON dict from the LLM.

    Returns:
        True if valid, False otherwise.
    """

    # Check required fields exist
    required_fields = ["route", "entities", "sql", "confidence", "reasoning"]
    for field in required_fields:
        if field not in result:
            logger.error(f"Missing required field in router output: {field}")
            return False

    # Check route is valid
    if result["route"] not in VALID_ROUTES:
        logger.error(f"Invalid route returned: {result['route']}")
        return False

    # Check confidence is valid
    if result["confidence"] not in {"high", "medium", "low"}:
        logger.error(f"Invalid confidence value: {result['confidence']}")
        return False

    # Check SQL is present for DB and DB_RAG routes
    if result["route"] in {"DB", "DB_RAG"} and not result["sql"]:
        logger.error(f"Missing SQL for route: {result['route']}")
        return False

    # Check SQL is null for non-DB routes
    if result["route"] not in {"DB", "DB_RAG"} and result["sql"] is not None:
        logger.warning(f"SQL present for non-DB route {result['route']} — clearing it.")
        result["sql"] = None

    # Check entities structure
    required_entity_keys = {
        "medication_names", "symptoms", "body_parts",
        "time_references", "activities", "emotions", "medical_concepts"
    }
    if not isinstance(result["entities"], dict):
        logger.error("Entities field is not a dict.")
        return False

    for key in required_entity_keys:
        if key not in result["entities"]:
            result["entities"][key] = []  # auto-fill missing entity lists

    return True