"""
Orchestrator-only emergency escalation (not a LangChain agent tool).

Delegates SMS delivery to integrations.twilio_sms.deliver_sms.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass

from integrations.twilio_sms import deliver_sms

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EscalationOutcome:
    """What the orchestrator needs after an emergency route."""

    patient_reply: str
    escalated: bool


# Builds reassurance for the patient, then asks integrations to SMS the caregiver.
async def escalate_to_caregiver(
    *,
    patient_id: str,
    session_id: str,
    patient_first_name: str,
    user_message: str,
) -> EscalationOutcome:
    name = patient_first_name.strip() or "there"

    patient_reply = (
        f"I'm getting help for you right away, {name}. "
        "Please stay calm and stay where it is safest for you."
    )

    caregiver_body = (
        "COGNICARE EMERGENCY\n"
        f"Patient ID: {patient_id}\n"
        f"Session: {session_id}\n"
        f"Patient said: {user_message.strip()[:500]}\n"
        "Please contact them immediately."
    )

    caregiver_phone = os.getenv("CAREGIVER_ALERT_SMS", "").strip()
    if not caregiver_phone:
        logger.warning(
            "[emergency_tool] CAREGIVER_ALERT_SMS unset; skipping SMS patient_id=%s",
            patient_id,
        )
        return EscalationOutcome(patient_reply=patient_reply, escalated=False)

    ok = await asyncio.to_thread(
        deliver_sms,
        to_phone=caregiver_phone,
        body=caregiver_body,
    )
    if not ok:
        return EscalationOutcome(patient_reply=patient_reply, escalated=False)

    logger.info("[emergency_tool] Caregiver SMS dispatched patient_id=%s", patient_id)
    return EscalationOutcome(patient_reply=patient_reply, escalated=True)


__all__ = ["EscalationOutcome", "escalate_to_caregiver"]
