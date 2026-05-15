"""HTTP routes for agent voice, chat, and reminder replies."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from memory.memory_manager import save_interaction
from orchestration.agent_executor import run_agent
from orchestration.orchestrator import orchestrate_message
from scheduler.reminder_delivery import _pending_by_patient, acknowledge_patient_message
from schemas.agent_schemas import (
    AgentResponse,
    ChatMessageRequest,
    ReminderReplyRequest,
    VoiceMessageRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])

# Fixed copy for reminder taps/replies only (no LLM/STT/TTS on this path).
_REMINDER_REPLY_CONFIRMATION = "Great, noted!"


def _normalize_patient_id(raw: str | int) -> str:
    pid = str(raw).strip()
    if not pid:
        raise HTTPException(status_code=422, detail="patient_id must not be empty")
    return pid


@router.post("/voice", response_model=AgentResponse)
async def agent_voice(req: VoiceMessageRequest) -> AgentResponse:
    try:
        return await orchestrate_message(
            patient_id=_normalize_patient_id(req.patient_id),
            message=req.message,
            language=req.language,
            run_agent=run_agent,
        )
    except Exception:
        logger.exception("POST /agent/voice failed patient_id=%s", req.patient_id)
        raise HTTPException(status_code=500, detail="Internal server error.") from None


@router.post("/chat", response_model=AgentResponse)
async def agent_chat(req: ChatMessageRequest) -> AgentResponse:
    logger.info("POST /agent/chat hit | patient_id=%s | language=%s | message=%s", req.patient_id, req.language, req.message)
    try:
        return await orchestrate_message(
            patient_id=_normalize_patient_id(req.patient_id),
            message=req.message,
            language=req.language,
            run_agent=run_agent,
        )
    except Exception:
        logger.exception("POST /agent/chat failed patient_id=%s", req.patient_id)
        raise HTTPException(status_code=500, detail="Internal server error.") from None


@router.get("/reminders/pending")
async def agent_reminders_pending(patient_id: int = Query(...)) -> dict:
    pid = str(patient_id)
    if pid in _pending_by_patient:
        pending = _pending_by_patient[pid]
        return {"has_reminder": True, "message": pending.message}
    return {"has_reminder": False, "message": None}


@router.post("/reminder-reply", response_model=AgentResponse)
async def agent_reminder_reply(req: ReminderReplyRequest) -> AgentResponse:
    pid = str(req.patient_id)
    try:
        ack = None
        if req.confirmed:
            ack = acknowledge_patient_message(pid)

        ts = datetime.now(timezone.utc).isoformat()
        user_payload = {
            "event": "reminder_reply",
            "patient_id": pid,
            "reminder_type": ack.reminder_type if ack else None,
            "item_label": ack.item_label if ack else None,
            "confirmed": req.confirmed,
            "timestamp": ts,
            "scheduler_reminder_id": ack.reminder_id if ack else None,
        }
        save_interaction(
            patient_id=pid,
            user_text=json.dumps(user_payload, ensure_ascii=False),
            assistant_text=_REMINDER_REPLY_CONFIRMATION,
            detected_intent="REMINDER_RESPONDED",
            confusion_flag=False,
        )

        return AgentResponse(
            response=_REMINDER_REPLY_CONFIRMATION,
            patient_id=pid,
        )
    except Exception:
        logger.exception("POST /agent/reminder-reply failed patient_id=%s", pid)
        raise HTTPException(status_code=500, detail="Internal server error.") from None


__all__ = ["router"]
