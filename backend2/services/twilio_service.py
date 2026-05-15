"""
Twilio integration for CogniCare: outbound SMS (test endpoint) and WhatsApp (caregiver
alerts), E.164 validation, caregiver alert chains with in-memory session state,
caregiver_priority ordering, time-based escalation via escalate_stale_alerts, and
inbound reply handling (acknowledge / escalate semantics with optional priority swap
when a backup responds).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status

from core.config import settings
from db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

ACK_WORDS = {"yes", "ok", "okay", "done", "taken", "received", "ack", "confirmed"}
ESCALATE_WORDS = {"no", "cant", "can't", "unable", "busy", "not me", "cannot"}

# One active alert flow per patient, stored in memory only
ACTIVE_ALERTS: dict[int, dict] = {}


# Returns True when TWILIO_MOCK_MODE is enabled (no live Twilio sends).
def is_twilio_mock_mode() -> bool:
    return settings.TWILIO_MOCK_MODE.lower() == "true"


# Current UTC time for expiry and recorded timestamps.
def _now() -> datetime:
    return datetime.now(timezone.utc)


# ISO-8601 UTC string for Supabase alert rows.
def _now_iso() -> str:
    return _now().isoformat()


# Validates and normalizes a phone number to E.164; raises 400 if invalid.
def _require_e164(phone: str) -> str:
    cleaned = phone.strip().replace(" ", "").replace("-", "")
    if not cleaned.startswith("+"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Phone number '{phone}' is not in E.164 format. Store numbers like +9627XXXXXXXX.",
        )
    return cleaned


# Lazily constructs the official Twilio REST client from env credentials.
def get_twilio_client() -> Any:
    try:
        from twilio.rest import Client  # type: ignore[reportMissingImports]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Twilio SDK is not installed. Run: pip install twilio",
        )
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN in .env",
        )
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


# Loads a single patient row by patient_id, or None.
def get_patient(patient_id: int) -> dict | None:
    client = get_supabase_client()
    result = (
        client.table("patients")
        .select("*")
        .eq("patient_id", patient_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


# Loads a caregiver by primary key caregiver_id.
def get_caregiver_by_id(caregiver_id: int) -> dict | None:
    client = get_supabase_client()
    result = (
        client.table("caregiver")
        .select("*")
        .eq("caregiver_id", caregiver_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


# Looks up a caregiver by registered contact_no (E.164 as stored).
def get_caregiver_by_phone(phone: str) -> dict | None:
    client = get_supabase_client()
    result = (
        client.table("caregiver")
        .select("*")
        .eq("contact_no", phone)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


# Returns caregivers for a patient ordered by caregiver_priority.priority_level when present.
def get_prioritized_caregivers(patient_id: int) -> list[dict]:
    client = get_supabase_client()

    priority_result = (
        client.table("caregiver_priority")
        .select("*")
        .eq("patient_id", patient_id)
        .order("priority_level")
        .execute()
    )
    priority_rows = priority_result.data or []

    caregivers_result = (
        client.table("caregiver")
        .select("*")
        .eq("patient_id", patient_id)
        .execute()
    )
    caregivers = caregivers_result.data or []
    caregivers_by_id = {row["caregiver_id"]: row for row in caregivers}

    ordered: list[dict] = []

    if priority_rows:
        for row in priority_rows:
            caregiver = caregivers_by_id.get(row["caregiver_id"])
            if caregiver:
                ordered.append(
                    {
                        **caregiver,
                        "priority_level": row["priority_level"],
                        "contact_method": row["contact_method"],
                    }
                )
        return ordered

    caregivers.sort(key=lambda x: x["caregiver_id"])
    return caregivers


# Persists a row in alerts for escalation / resolution tracking.
def create_alert_record(caregiver_id: int, alert_type: str) -> dict:
    client = get_supabase_client()
    payload = {
        "caregiver_id": caregiver_id,
        "alert_time": _now_iso(),
        "alert_type": alert_type,
        "resolved_time": None,
        "resolved": False,
    }
    result = client.table("alerts").insert(payload).execute()
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create alert record",
        )
    return result.data[0]


# Returns the latest unresolved alert for a caregiver, if any.
def get_latest_open_alert_for_caregiver(caregiver_id: int) -> dict | None:
    client = get_supabase_client()
    result = (
        client.table("alerts")
        .select("*")
        .eq("caregiver_id", caregiver_id)
        .eq("resolved", False)
        .order("alert_time", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


# Marks an alert as resolved with a resolved_time.
def resolve_alert(alert_id: int) -> None:
    client = get_supabase_client()
    client.table("alerts").update(
        {
            "resolved": True,
            "resolved_time": _now_iso(),
        }
    ).eq("alert_id", alert_id).execute()


# If the responding caregiver was not already priority 1, swaps their caregiver_priority levels with the priority-1 row.
def swap_caregiver_priority(patient_id: int, responding_caregiver_id: int) -> None:
    client = get_supabase_client()
    result = (
        client.table("caregiver_priority")
        .select("*")
        .eq("patient_id", patient_id)
        .order("priority_level")
        .execute()
    )
    rows = result.data or []

    p1_row = next((r for r in rows if r.get("priority_level") == 1), None)
    responder_row = next(
        (r for r in rows if r.get("caregiver_id") == responding_caregiver_id),
        None,
    )

    if not p1_row or not responder_row:
        logger.info(
            "[twilio] swap_caregiver_priority skipped: missing priority-1 or responder row patient_id=%s",
            patient_id,
        )
        return

    if p1_row["caregiver_id"] == responding_caregiver_id:
        return

    level_top = p1_row["priority_level"]
    level_resp = responder_row["priority_level"]

    client.table("caregiver_priority").update({"priority_level": level_resp}).eq(
        "patient_id", patient_id
    ).eq("caregiver_id", p1_row["caregiver_id"]).execute()
    client.table("caregiver_priority").update({"priority_level": level_top}).eq(
        "patient_id", patient_id
    ).eq("caregiver_id", responding_caregiver_id).execute()

    logger.info(
        "[twilio] swapped caregiver_priority patient_id=%s: caregiver %s <-> %s (levels %s <-> %s)",
        patient_id,
        p1_row["caregiver_id"],
        responding_caregiver_id,
        level_top,
        level_resp,
    )


# Sends one SMS via Twilio (or mock dict) with optional status callback URL.
def send_sms(to_number: str, body: str) -> dict[str, Any]:
    to_number = _require_e164(to_number)

    if not settings.TWILIO_PHONE_NUMBER:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing TWILIO_PHONE_NUMBER in .env",
        )

    from_number = _require_e164(settings.TWILIO_PHONE_NUMBER)

    if is_twilio_mock_mode():
        return {
            "sid": "MOCK_TWILIO_SID",
            "status": "queued",
            "to": to_number,
            "from": from_number,
            "body": body,
            "source": "mock",
        }

    twilio_client = get_twilio_client()

    status_callback = None
    if settings.APP_BASE_URL:
        status_callback = f"{settings.APP_BASE_URL}/webhooks/twilio/status"

    message = twilio_client.messages.create(
        body=body,
        from_=from_number,
        to=to_number,
        status_callback=status_callback,
    )

    return {
        "sid": message.sid,
        "status": message.status,
        "to": message.to,
        "from": message.from_,
        "body": body,
        "source": "twilio",
    }


# Sends one WhatsApp message via Twilio (or mock dict); destination is E.164, channel prefix added.
def send_whatsapp(to_number: str, body: str) -> dict[str, Any]:
    to_number = _require_e164(to_number)
    to_whatsapp = f"whatsapp:{to_number}"
    from_whatsapp = (settings.TWILIO_WHATSAPP_NUMBER or "").strip()
    if not from_whatsapp and not is_twilio_mock_mode():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing TWILIO_WHATSAPP_NUMBER in .env",
        )

    if is_twilio_mock_mode():
        return {
            "sid": "MOCK_TWILIO_SID",
            "status": "queued",
            "to": to_whatsapp,
            "from": from_whatsapp or "whatsapp:+14155238886",
            "body": body,
            "source": "mock",
        }

    twilio_client = get_twilio_client()

    message = twilio_client.messages.create(
        body=body,
        from_=from_whatsapp,
        to=to_whatsapp,
    )

    return {
        "sid": message.sid,
        "status": message.status,
        "to": message.to,
        "from": message.from_,
        "body": body,
        "source": "whatsapp",
    }


# Builds the alert body shown to caregivers with patient name and YES/NO hint.
def build_alert_message(patient_id: int, base_message: str) -> str:
    patient = get_patient(patient_id)
    if not patient:
        return f"{base_message}\nReply YES to acknowledge or NO to escalate."

    full_name = f"{patient['first_name']} {patient['last_name']}"
    return (
        f"Patient alert for {full_name} (ID {patient_id}).\n"
        f"{base_message}\n"
        f"Reply YES to acknowledge or NO to escalate."
    )


# Starts (or short-circuits) the in-memory alert chain: WhatsApp first caregiver, track session and expiry.
def start_agent_alert(patient_id: int, message: str) -> dict:
    existing = ACTIVE_ALERTS.get(patient_id)
    if existing and existing["status"] in {"pending", "escalated"} and not existing["responded"]:
        return {
            "patient_id": patient_id,
            "caregiver_id": None,
            "responded": False,
        }

    caregivers = get_prioritized_caregivers(patient_id)
    if not caregivers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No caregiver available for this patient",
        )

    first_caregiver = caregivers[0]
    sms_body = build_alert_message(patient_id, message)
    send_whatsapp(first_caregiver["contact_no"], sms_body)
    create_alert_record(first_caregiver["caregiver_id"], "agent_alert")

    ACTIVE_ALERTS[patient_id] = {
        "patient_id": patient_id,
        "message": message,
        "caregivers": caregivers,
        "current_index": 0,
        "current_caregiver_id": first_caregiver["caregiver_id"],
        "responded": False,
        "status": "pending",
        "expires_at": _now() + timedelta(seconds=settings.TWILIO_REPLY_TIMEOUT_SECONDS),
    }

    return {
        "patient_id": patient_id,
        "caregiver_id": None,
        "responded": False,
    }


# Moves alert to the next prioritized caregiver: resolves current alert, sends WhatsApp, updates state.
def _escalate_to_next_caregiver(
    patient_id: int,
    reason_message: str,
) -> bool:
    state = ACTIVE_ALERTS.get(patient_id)
    if not state:
        return False

    current_caregiver_id = state["current_caregiver_id"]
    open_alert = get_latest_open_alert_for_caregiver(current_caregiver_id)
    if open_alert:
        resolve_alert(open_alert["alert_id"])

    next_index = state["current_index"] + 1
    caregivers = state["caregivers"]

    if next_index >= len(caregivers):
        state["status"] = "expired"
        state["current_caregiver_id"] = None
        return False

    next_caregiver = caregivers[next_index]
    sms_body = build_alert_message(patient_id, reason_message)
    send_whatsapp(next_caregiver["contact_no"], sms_body)
    create_alert_record(next_caregiver["caregiver_id"], "agent_alert")

    state["current_index"] = next_index
    state["current_caregiver_id"] = next_caregiver["caregiver_id"]
    state["status"] = "escalated"
    state["expires_at"] = _now() + timedelta(seconds=settings.TWILIO_REPLY_TIMEOUT_SECONDS)

    return True


# Twilio (or test) inbound handler: YES resolves and may promote responder; NO escalates or ends chain.
def handle_incoming_caregiver_reply(from_number: str, to_number: str, body: str) -> str:
    _ = to_number

    caregiver = get_caregiver_by_phone(from_number)
    if not caregiver:
        return "Your number is not registered as a caregiver in the system."

    patient_id = caregiver["patient_id"]
    state = ACTIVE_ALERTS.get(patient_id)

    if not state:
        return "No active alert was found for this patient."

    if state["current_caregiver_id"] != caregiver["caregiver_id"]:
        return "You are not the current caregiver assigned to this active alert."

    normalized = body.strip().lower()
    open_alert = get_latest_open_alert_for_caregiver(caregiver["caregiver_id"])

    if normalized in ACK_WORDS:
        if open_alert:
            resolve_alert(open_alert["alert_id"])

        if state["current_index"] > 0:
            swap_caregiver_priority(patient_id, caregiver["caregiver_id"])

        state["responded"] = True
        state["status"] = "responded"

        return "Thank you. The alert has been acknowledged and marked as resolved."

    if normalized in ESCALATE_WORDS:
        if open_alert:
            resolve_alert(open_alert["alert_id"])

        escalated = _escalate_to_next_caregiver(
            patient_id=patient_id,
            reason_message="Previous caregiver could not confirm handling this alert.",
        )

        if escalated:
            return "Thank you. The alert has been escalated to the next caregiver."

        return "Thank you. No backup caregiver was available for escalation."

    return "Reply YES to acknowledge the alert or NO to escalate it to the next caregiver."


# Called by scheduler: auto-escalates when the current step’s reply window has expired.
def escalate_stale_alerts() -> list[dict]:
    results = []
    now = _now()

    for patient_id, state in list(ACTIVE_ALERTS.items()):
        if state["responded"]:
            continue

        if state["status"] not in {"pending", "escalated"}:
            continue

        if state["expires_at"] > now:
            continue

        current_caregiver_id = state["current_caregiver_id"]

        escalated = _escalate_to_next_caregiver(
            patient_id=patient_id,
            reason_message="Previous caregiver did not respond in time.",
        )

        results.append(
            {
                "patient_id": patient_id,
                "caregiver_id": current_caregiver_id,
                "responded": False,
                "escalated": escalated,
            }
        )

    return results


# Dev hook for Twilio MessageStatus webhooks (delivery outcomes).
def record_twilio_status_callback(
    message_sid: str,
    message_status: str,
    to_number: str | None,
    error_code: str | None,
) -> None:
    logger.info(
        "twilio status callback message_sid=%s message_status=%s to=%s error_code=%s",
        message_sid,
        message_status,
        to_number,
        error_code,
    )
