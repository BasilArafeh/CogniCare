"""
Twilio-related HTTP routes: caregiver WhatsApp alerting, escalation flows, utility SMS,
non-Twilio-form inbound reply handling, and internal hooks used by ai_agent
(reminder fan-out and emergency escalation to caregivers).
"""

import logging

import requests
from fastapi import APIRouter, Form, HTTPException, status

from core.config import settings
from schemas.twilio import (
    AgentAlertSessionResponse,
    InternalEmergencyRequest,
    InternalReminderRequest,
    SendCaregiverAlertRequest,
    TestSMSRequest,
)
from services.twilio_service import (
    get_prioritized_caregivers,
    handle_incoming_caregiver_reply,
    send_sms,
    send_whatsapp,
    start_agent_alert,
)

logger = logging.getLogger(__name__)

# Patient app / caregiver alert flows initiated from CogniCare services.
router = APIRouter(prefix="/twilio", tags=["twilio"])

# Service-to-service calls from ai_agent (no public browser traffic expected).
internal_router = APIRouter(prefix="/internal", tags=["internal"])


# Starts the timed caregiver WhatsApp escalation chain for agent-driven alerts.
@router.post("/caregiver-alert", response_model=AgentAlertSessionResponse)
def send_caregiver_alert(payload: SendCaregiverAlertRequest):
    return start_agent_alert(
        patient_id=payload.patient_id,
        message=payload.message,
    )


# Sends a one-off SMS for integration testing (explicit destination and body).
@router.post("/test-sms")
def test_sms(payload: TestSMSRequest):
    return send_sms(
        to_number=payload.to_number,
        body=payload.message,
    )


# Parses an inbound caregiver reply without Twilio TwiML wrappers (explicit form fields).
@router.post("/incoming-reply")
def incoming_reply(
    from_number: str = Form(),
    to_number: str = Form(),
    body: str = Form(""),
):
    clean_from = from_number.strip()
    clean_to = to_number.strip()
    if clean_from.lower().startswith("whatsapp:"):
        clean_from = clean_from.split(":", 1)[1]
    if clean_to.lower().startswith("whatsapp:"):
        clean_to = clean_to.split(":", 1)[1]
    reply_text = handle_incoming_caregiver_reply(
        from_number=clean_from,
        to_number=clean_to,
        body=body,
    )
    return {"reply": reply_text}


# Sends an emergency WhatsApp to the top-priority caregiver for the given patient (ai_agent).
@internal_router.post("/emergency")
def notify_emergency(body: InternalEmergencyRequest) -> dict[str, bool | int]:
    try:
        pid = int(str(body.patient_id).strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="patient_id must be an integer",
        ) from exc

    caregivers = get_prioritized_caregivers(pid)
    if not caregivers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No caregiver available for this patient",
        )

    send_whatsapp(caregivers[0]["contact_no"], body.message.strip())
    logger.info("[internal] Emergency WhatsApp dispatched patient_id=%s", pid)
    return {"ok": True, "patient_id": pid}


# Forwards reminder text to the patient-facing app webhook configured in PATIENT_REMINDER_WEBHOOK_URL.
@internal_router.post("/reminder")
def notify_reminder(body: InternalReminderRequest) -> dict[str, bool]:
    url = (settings.PATIENT_REMINDER_WEBHOOK_URL or "").strip()
    if not url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PATIENT_REMINDER_WEBHOOK_URL is not configured",
        )
    payload = {"patient_id": body.patient_id, "message": body.message}
    try:
        resp = requests.post(url, json=payload, timeout=15)
    except requests.RequestException as exc:
        logger.exception("[internal] Reminder webhook request failed patient_id=%s", body.patient_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Reminder webhook request failed",
        ) from exc
    if not (200 <= resp.status_code < 300):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Reminder webhook returned HTTP {resp.status_code}",
        )
    logger.info("[internal] Reminder forwarded patient_id=%s", body.patient_id)
    return {"ok": True}
