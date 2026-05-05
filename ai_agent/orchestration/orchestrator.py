"""
Top-level orchestration for one patient turn.

Flow:
1) Input from frontend: patient_id, session_id, message
2) Load memory: recent turns + profile/notes
3) Route intent
4) EMERGENCY bypass -> tools.emergency_tool.escalate_to_caregiver (no agent)
5) Build tools for route (DB / RAG / DB_RAG / none)
6) Run agent
7) Save interaction and return AgentResponse
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from memory.memory_manager import get_recent_turns, load_full_memory, save_interaction
from orchestration.agent_executor import run_agent as default_run_agent
from routers.intent_router import route_intent
from schemas.agent_schemas import AgentResponse
from scheduler.reminder_delivery import acknowledge_patient_message
from tools.db_tools import create_database_tools
from tools.emergency_tool import escalate_to_caregiver
from tools.rag_tool import create_rag_tools

logger = logging.getLogger(__name__)

AgentRunner = Callable[..., Awaitable[str]]


# Returns display name and stage from profile dict with safe defaults.
def _extract_patient_identity(profile: dict[str, Any]) -> tuple[str, str]:
    first_name = str(profile.get("first_name") or "there").strip() or "there"
    diagnosis_stage = str(profile.get("diagnosis_stage") or "moderate").strip().lower()
    if diagnosis_stage not in {"mild", "moderate", "severe"}:
        diagnosis_stage = "moderate"
    return first_name, diagnosis_stage


# Converts loaded history rows into prompt-friendly conversation lines.
def _history_rows_to_text(history_rows: list[dict[str, Any]]) -> str:
    if not history_rows:
        return "No history yet."
    lines: list[str] = []
    for row in history_rows:
        user_text = row.get("user_text") or ""
        assistant_text = row.get("assistant_text") or ""
        lines.append(f"Patient: {user_text}")
        lines.append(f"Assistant: {assistant_text}")
    return "\n".join(lines)


# Builds the route-appropriate tool list (DB, RAG, DB_RAG, or empty).
def _build_tools_for_route(route: str, patient_id: str, patient_name: str) -> list[Any]:
    db_tools = create_database_tools(patient_id=patient_id, patient_first_name=patient_name)
    rag_tools = create_rag_tools()

    if route == "DB":
        return db_tools
    if route == "RAG":
        return rag_tools
    if route == "DB_RAG":
        return db_tools + rag_tools
    return []


# Main orchestration entry: memory, routing, emergency tool, agent, persistence.
async def orchestrate_message(
    patient_id: str,
    session_id: str,
    message: str,
    *,
    run_agent: AgentRunner | None = None,
) -> AgentResponse:
    logger.info("Orchestration started patient_id=%s session_id=%s", patient_id, session_id)

    acknowledge_patient_message(patient_id)

    recent_turns = get_recent_turns(patient_id=patient_id, n=3)
    full_memory = load_full_memory(patient_id=patient_id)
    profile = full_memory.get("profile", {}) if isinstance(full_memory, dict) else {}
    history_rows = full_memory.get("history", []) if isinstance(full_memory, dict) else []
    patient_name, diagnosis_stage = _extract_patient_identity(profile if isinstance(profile, dict) else {})
    conversation_history = _history_rows_to_text(history_rows if isinstance(history_rows, list) else [])

    routed = await route_intent(
        message=message,
        recent_history=recent_turns,
        patient_id=patient_id,
    )
    route = str(routed.get("route") or "CLARIFY")
    sql_query = routed.get("sql")
    logger.info("Orchestration route selected patient_id=%s route=%s", patient_id, route)

    if route == "EMERGENCY":
        outcome = await escalate_to_caregiver(
            patient_id=patient_id,
            session_id=session_id,
            patient_first_name=patient_name,
            user_message=message,
        )
        save_interaction(
            patient_id=patient_id,
            user_text=message,
            assistant_text=outcome.patient_reply,
            detected_intent="EMERGENCY",
            confusion_flag=False,
        )
        return AgentResponse(
            response=outcome.patient_reply,
            intent="EMERGENCY",
            session_id=session_id,
            patient_id=patient_id,
            emergency_escalated=outcome.escalated,
            confusion_flag=False,
        )

    tools = _build_tools_for_route(route, patient_id, patient_name)
    runner = run_agent or default_run_agent

    assistant_text = await runner(
        message=message,
        intent=route,
        sql=sql_query,
        tools=tools,
        patient_name=patient_name,
        diagnosis_stage=diagnosis_stage,
        patient_profile=profile,
        conversation_history=conversation_history,
    )

    confusion_flag = route == "CLARIFY"
    save_interaction(
        patient_id=patient_id,
        user_text=message,
        assistant_text=assistant_text,
        detected_intent=route,
        confusion_flag=confusion_flag,
    )

    return AgentResponse(
        response=assistant_text,
        intent=route,  # type: ignore[arg-type]
        session_id=session_id,
        patient_id=patient_id,
        emergency_escalated=False,
        confusion_flag=confusion_flag,
    )
