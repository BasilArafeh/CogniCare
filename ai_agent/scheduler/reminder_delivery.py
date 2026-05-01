"""
Reminder pipeline: insert ``reminders`` row, log outbound text like a normal turn, then wait for reply.

On timeout: mark ``missed``, log interaction, SMS caregiver that they likely missed the item.
On patient message (orchestrator): mark ``responded`` (interaction turn is saved separately by orchestrator).

If a new reminder fires before the prior window closes, the prior row is marked ``superseded``.
"""

from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Literal

from integrations.twilio_sms import deliver_sms
from memory.memory_manager import save_interaction
from scheduler.queries.reminders_write import insert_reminder_instance, update_reminder_status

logger = logging.getLogger(__name__)

RESPONSE_WINDOW_SEC = 300

ReminderKind = Literal["medication", "meal", "activity"]


@dataclass
class _PendingFollowup:
    timer: threading.Timer
    reminder_id: str | None
    reminder_type: ReminderKind
    item_label: str


_pending_by_patient: dict[str, _PendingFollowup] = {}


# Cancels outbound window and marks the reminder row as responded when the patient sends any chat message.
def acknowledge_patient_message(patient_id: str) -> None:
    pid = patient_id.strip()
    if not pid:
        return
    pending = _pending_by_patient.pop(pid, None)
    if pending is None:
        return
    pending.timer.cancel()
    update_reminder_status(pending.reminder_id, "responded")
    logger.info(
        "[reminder_delivery] Patient responded within window patient_id=%s reminder_id=%s",
        pid,
        pending.reminder_id,
    )


def _patient_webhook_post(patient_id: str, body: str) -> None:
    import os

    url = (os.getenv("PATIENT_REMINDER_WEBHOOK_URL") or "").strip()
    if not url:
        return
    payload = json.dumps({"patient_id": patient_id, "message": body}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            if resp.status >= 400:
                logger.error("[reminder_delivery] Webhook HTTP %s patient_id=%s", resp.status, patient_id)
    except urllib.error.HTTPError as e:
        logger.error("[reminder_delivery] Webhook failed patient_id=%s code=%s", patient_id, e.code)
    except Exception:
        logger.exception("[reminder_delivery] Webhook error patient_id=%s", patient_id)


# Closes prior pending reminder without notifying caregiver when a newer reminder queues for same patient.
def _supersede_active_reminder(pid: str) -> None:
    pending = _pending_by_patient.pop(pid, None)
    if pending is None:
        return
    pending.timer.cancel()
    update_reminder_status(pending.reminder_id, "superseded")
    logger.info(
        "[reminder_delivery] Prior reminder superseded patient_id=%s old_reminder_id=%s",
        pid,
        pending.reminder_id,
    )


def _notify_caregiver_missed(
    *,
    patient_id: str,
    reminder_kind: ReminderKind,
    item_label: str,
    reminder_id: str | None,
    detail_suffix: str,
) -> None:
    import os

    phone = (os.getenv("CAREGIVER_ALERT_SMS") or "").strip()
    if not phone:
        logger.warning(
            "[reminder_delivery] CAREGIVER_ALERT_SMS unset; caregiver SMS skipped patient_id=%s",
            patient_id,
        )
        return

    readable = {"medication": "medication", "meal": "meal", "activity": "activity"}[reminder_kind]
    body = (
        "CogniCare — reminder follow-up\n"
        f"The patient likely missed their scheduled {readable}: {item_label}.\n"
        f"No reply within {RESPONSE_WINDOW_SEC // 60} minutes after we sent the reminder.\n"
        f"Patient ID: {patient_id}\n"
    )
    if reminder_id:
        body += f"Reminder ID: {reminder_id}\n"
    if detail_suffix.strip():
        body += f"{detail_suffix.strip()[:300]}"

    ok = deliver_sms(to_phone=phone, body=body.strip())
    if ok:
        logger.info("[reminder_delivery] Caregiver SMS sent (likely missed) patient_id=%s", patient_id)
    else:
        logger.error("[reminder_delivery] Caregiver SMS failed patient_id=%s", patient_id)


def _log_missed_interaction(
    *,
    patient_id: str,
    reminder_kind: ReminderKind,
    item_label: str,
    reminder_id: str | None,
) -> None:
    label = {"medication": "Medication", "meal": "Meal", "activity": "Activity"}[reminder_kind]
    tail = f" Reminder record: {reminder_id}." if reminder_id else ""
    save_interaction(
        patient_id=patient_id,
        user_text="[No patient reply within reminder follow-up window]",
        assistant_text=(
            f"System ({label.lower()} reminder): no timely response recorded as missed "
            f"for '{item_label}'. Caregiver was notified.{tail}"
        ),
        detected_intent="REMINDER_MISSED",
        confusion_flag=False,
    )


def _schedule_followup(
    pid: str,
    *,
    reminder_id: str | None,
    reminder_kind: ReminderKind,
    item_label: str,
    detail_suffix: str,
) -> None:
    captured_timer_holder: list[threading.Timer | None] = [None]

    def _fire() -> None:
        pending = _pending_by_patient.get(pid)
        tref = captured_timer_holder[0]
        if pending is None or tref is None or pending.timer is not tref:
            return
        _pending_by_patient.pop(pid, None)
        update_reminder_status(reminder_id, "missed")
        _log_missed_interaction(
            patient_id=pid,
            reminder_kind=reminder_kind,
            item_label=item_label,
            reminder_id=reminder_id,
        )
        _notify_caregiver_missed(
            patient_id=pid,
            reminder_kind=reminder_kind,
            item_label=item_label,
            reminder_id=reminder_id,
            detail_suffix=detail_suffix,
        )

    t = threading.Timer(RESPONSE_WINDOW_SEC, _fire)
    captured_timer_holder[0] = t
    t.daemon = True
    _pending_by_patient[pid] = _PendingFollowup(
        timer=t,
        reminder_id=reminder_id,
        reminder_type=reminder_kind,
        item_label=item_label,
    )
    t.start()
    logger.info(
        "[reminder_delivery] Follow-up timer started patient_id=%s window_sec=%s kind=%s reminder_id=%s",
        pid,
        RESPONSE_WINDOW_SEC,
        reminder_kind,
        reminder_id,
    )


# Persists outbound assistant line for reporting, then starts the response window.
def deliver_reminder_to_patient(
    *,
    patient_id: str,
    patient_message: str,
    reminder_type: ReminderKind,
    item_label: str,
    patient_medications_id: str | None = None,
    patient_meal_id: str | None = None,
    patient_activity_id: str | None = None,
) -> None:
    pid = patient_id.strip()
    msg = patient_message.strip()
    label = (item_label or "scheduled item").strip()

    _supersede_active_reminder(pid)

    reminder_id = insert_reminder_instance(
        patient_id=pid,
        reminder_type=reminder_type,
        patient_medications_id=patient_medications_id,
        patient_meal_id=patient_meal_id,
        patient_activity_id=patient_activity_id,
    )

    save_interaction(
        patient_id=pid,
        user_text="[Scheduled reminder — patient was not typing]",
        assistant_text=msg,
        detected_intent="REMINDER_OUTBOUND",
        confusion_flag=False,
    )

    logger.info(
        "[reminder_delivery] Outbound reminder logged patient_id=%s type=%s reminder_id=%s",
        pid,
        reminder_type,
        reminder_id,
    )
    _patient_webhook_post(pid, msg)

    detail = (
        f"{reminder_type} label={label} "
        f"med_row={patient_medications_id} meal_row={patient_meal_id} act_row={patient_activity_id}"
    )
    _schedule_followup(
        pid,
        reminder_id=reminder_id,
        reminder_kind=reminder_type,
        item_label=label,
        detail_suffix=detail,
    )


__all__ = [
    "RESPONSE_WINDOW_SEC",
    "ReminderKind",
    "acknowledge_patient_message",
    "deliver_reminder_to_patient",
]
