"""
Top-level orchestration for one patient turn.

Flow:
1) Input from frontend: patient_id, message, language
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

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from core.config import config
from core.language_tags import normalize_primary_language
from memory.memory_manager import get_recent_turns, load_patient_profile, save_interaction
from orchestration.agent_executor import run_agent as default_run_agent
from prompts.llm_prompt import LLM_PROMPT
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


# LLM-only route: single completion with LLM_PROMPT (no tools / no ReAct).
async def _run_llm_fallback(
    *,
    message: str,
    patient_name: str,
    diagnosis_stage: str,
    conversation_history: str,
    language: str,
) -> str:
    lang = normalize_primary_language(language)
    safe_fallback = (
        (
            f"أنا هنا معك يا {patient_name}. أواجه مشكلة صغيرة الآن، لكن يمكنني المحاولة مرة أخرى."
        )
        if lang == "ar"
        else f"I'm here with you, {patient_name}. I'm having a little trouble right now, but I can try again."
    )
    try:
        system_content = LLM_PROMPT.format(
            patient_name=patient_name,
            diagnosis_stage=diagnosis_stage,
            conversation_history=conversation_history,
            message=message,
            language=lang,
        )
        llm = ChatOpenAI(model=config.agent_llm_model, temperature=0.4)
        rsp = await llm.ainvoke([SystemMessage(content=system_content)])
        text = str(getattr(rsp, "content", "") or "").strip()
        return text or safe_fallback
    except Exception:
        logger.exception("_run_llm_fallback failed")
        return safe_fallback


# Builds the route-appropriate tool list (DB, RAG, DB_RAG, or empty).
def _build_tools_for_route(route: str, patient_id: str, patient_name: str, sql_query: str | None) -> list[Any]:
    db_tools = create_database_tools(
        patient_id=patient_id,
        patient_first_name=patient_name,
        sql_query=sql_query or "",
    )
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
    message: str,
    language: str = "en",
    *,
    run_agent: AgentRunner | None = None,
) -> AgentResponse:
    logger.info("Orchestration started patient_id=%s", patient_id)

    effective_lang = normalize_primary_language(language)

    recent_turns = get_recent_turns(patient_id=patient_id, n=3)
    profile = load_patient_profile(patient_id=patient_id)
    patient_name, diagnosis_stage = _extract_patient_identity(profile if isinstance(profile, dict) else {})
    conversation_history = recent_turns or "No history yet."

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
            patient_id=patient_id,
        )

    acknowledge_patient_message(patient_id)

    if route in {"LLM", "CLARIFY"}:
        assistant_text = await _run_llm_fallback(
            message=message,
            patient_name=patient_name,
            diagnosis_stage=diagnosis_stage,
            conversation_history=conversation_history,
            language=effective_lang,
        )
    else:
        tools = _build_tools_for_route(route, patient_id, patient_name, sql_query)
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
            language=effective_lang,
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
        patient_id=patient_id,
    )
