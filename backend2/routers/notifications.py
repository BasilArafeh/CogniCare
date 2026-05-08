from fastapi import APIRouter

from schemas.notifications import (
    AgentAlertSessionResponse,
    SendCaregiverAlertRequest,
)
from services.twilio_service import (
    escalate_stale_alerts,
    start_agent_alert,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/caregiver-alert", response_model=AgentAlertSessionResponse)
def send_caregiver_alert(payload: SendCaregiverAlertRequest):
    return start_agent_alert(
        patient_id=payload.patient_id,
        message=payload.message,
        callback_url=str(payload.callback_url),
    )


@router.post("/escalate-stale-alerts")
def escalate_old_alerts():
    return {
        "escalated": escalate_stale_alerts()
    }