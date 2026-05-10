"""
Agent execution layer (ReAct with tools, or direct LLM when no tools).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from core.config import config
from core.language_tags import normalize_primary_language
from prompts.agent_prompt import AGENT_PROMPT

logger = logging.getLogger(__name__)


# Formats the patient context into the shared AGENT_PROMPT template.
def _build_agent_system_prompt(
    *,
    intent: str,
    patient_name: str,
    diagnosis_stage: str,
    patient_profile: Any,
    conversation_history: str,
    language: str,
) -> str:
    norm_lang = normalize_primary_language(language)
    profile_text = (
        patient_profile
        if isinstance(patient_profile, str)
        else json.dumps(patient_profile, ensure_ascii=False, default=str, indent=2)
    )
    critical = (
        f"CRITICAL INSTRUCTION: You MUST respond ONLY in "
        f"{'Jordanian Arabic dialect (عامية أردنية). Write exactly as a Jordanian person would speak, not Modern Standard Arabic.' if normalize_primary_language(language) == 'ar' else 'English'}. No exceptions.\n\n"
    )
    return critical + AGENT_PROMPT.format(
        patient_name=patient_name,
        diagnosis_stage=diagnosis_stage,
        patient_profile=profile_text,
        conversation_history=conversation_history,
        intent=intent,
        language=norm_lang,
    )


# Builds the user-facing input, appending SQL context for DB/DB_RAG when present.
def _build_agent_input_message(*, message: str, intent: str, sql: Any) -> str:
    if intent in {"DB", "DB_RAG"} and isinstance(sql, str) and sql.strip():
        return f"{message}\n\nPlanned SQL from router:\n{sql.strip()}"
    return message


# Executes one turn via LangGraph ReAct when tools exist, otherwise direct ChatOpenAI.
async def run_agent(
    *,
    message: str,
    intent: str,
    sql: Any,
    tools: list[Any],
    patient_name: str,
    diagnosis_stage: str,
    patient_profile: Any,
    conversation_history: str,
    language: str = "en",
) -> str:
    lang = normalize_primary_language(language)
    safe_fallback = (
        (
            f"أنا هنا معك يا {patient_name}. أواجه مشكلة صغيرة الآن، لكن يمكنني المحاولة مرة أخرى."
            if lang == "ar"
            else f"I'm here with you, {patient_name}. I'm having a little trouble right now, but I can try again."
        )
    )
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI
        from langgraph.prebuilt import create_react_agent

        logger.info(
            "run_agent started intent=%s tools=%s model=%s",
            intent,
            len(tools),
            config.agent_llm_model,
        )

        system_prompt = _build_agent_system_prompt(
            intent=intent,
            patient_name=patient_name,
            diagnosis_stage=diagnosis_stage,
            patient_profile=patient_profile,
            conversation_history=conversation_history,
            language=lang,
        )
        user_input = _build_agent_input_message(message=message, intent=intent, sql=sql)

        if tools:
            logger.info("run_agent using LangGraph ReAct path")
            llm = ChatOpenAI(model=config.agent_llm_model, temperature=0.4)

            agent = create_react_agent(
                model=llm,
                tools=tools,
                prompt=system_prompt,
            )

            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": user_input}]}
            )

            messages = result.get("messages", [])
            last = messages[-1] if messages else None
            text = str(getattr(last, "content", "") or "").strip()
            return text or safe_fallback

        logger.info("run_agent using direct ChatOpenAI path")
        llm = ChatOpenAI(model=config.agent_llm_model, temperature=0.4)
        rsp = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_input),
            ]
        )
        text = str(getattr(rsp, "content", "") or "").strip()
        return text or safe_fallback
    except Exception:
        logger.exception("run_agent failed")
        return safe_fallback
