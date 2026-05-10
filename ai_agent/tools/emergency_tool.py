"""
Orchestrator-only emergency escalation (not a LangChain agent tool).

Delegates notification to backend2 via HTTP POST to /internal/emergency.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EscalationOutcome:
    """What the orchestrator needs after an emergency route."""

    patient_reply: str
    escalated: bool


def _post_emergency(backend2_url: str, *, patient_id: str, caregiver_body: str) -> bool:
    payload = json.dumps(
        {
            "patient_id": patient_id,
            "message": caregiver_body,
        }
    ).encode()
    base = backend2_url.rstrip("/")
    req = urllib.request.Request(
        f"{base}/internal/emergency",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    ok = False
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            ok = 200 <= resp.status < 300
    except Exception:
        logger.exception("[emergency_tool] backend2 POST failed")
        ok = False
    return ok


# Builds reassurance for the patient, then POSTs backend2 for caregiver escalation.
async def escalate_to_caregiver(
    *,
    patient_id: str,
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
        f"Patient said: {user_message.strip()[:500]}\n"
        "Please contact them immediately."
    )

    ok = False
    backend2_url = os.getenv("BACKEND2_URL", "").strip()
    if backend2_url:
        ok = await asyncio.to_thread(
            _post_emergency,
            backend2_url,
            patient_id=patient_id,
            caregiver_body=caregiver_body,
        )

    if not backend2_url:
        logger.warning(
            "[emergency_tool] BACKEND2_URL unset; skipping escalation patient_id=%s",
            patient_id,
        )
    elif ok:
        logger.info("[emergency_tool] backend2 escalation ok patient_id=%s", patient_id)

    return EscalationOutcome(patient_reply=patient_reply, escalated=ok)


__all__ = ["EscalationOutcome", "escalate_to_caregiver"]
