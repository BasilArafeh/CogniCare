"""
Pydantic request/response shapes for Twilio-related HTTP APIs.

Covers caregiver SMS alerts triggered from the backend, test SMS payloads,
and internal service calls from ai_agent (reminders and emergency escalation).
"""

from pydantic import BaseModel


class SendCaregiverAlertRequest(BaseModel):
    """Starts a caregiver SMS alert flow for a patient (timed escalation chain, no HTTP callback)."""

    patient_id: int
    message: str


class AgentAlertSessionResponse(BaseModel):
    """Return type after starting or checking an agent-driven caregiver alert session."""

    patient_id: int
    caregiver_id: int | None = None
    responded: bool


class TestSMSRequest(BaseModel):
    """Sends an arbitrary SMS to one number — used by the test endpoint only."""

    to_number: str
    message: str


class InternalReminderRequest(BaseModel):
    """Body from ai_agent when a scheduled reminder fires and backend2 must act."""

    patient_id: str
    message: str


class InternalEmergencyRequest(BaseModel):
    """Body from ai_agent when an emergency intent is detected and caregivers must be reached."""

    patient_id: str
    message: str
