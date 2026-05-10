"""
Reminder pipeline (Teammate 2 owns push UI; we own scheduling + persistence).

Boot (see ``scheduler.scheduler``): APScheduler loads all patients' med/meal/activity
times from Supabase, registers cron jobs, and reloads schedules every hour.

When a cron fires:
  - Insert a ``reminders`` row (status ``sent``), log outbound copy to ``interaction_log``,
    POST JSON ``{patient_id, message}`` to ``PATIENT_REMINDER_WEBHOOK_URL``, then start a
    5-minute ``threading.Timer``.

If the patient replies in time:
  - Teammate 2 calls ``POST /agent/reminder-reply`` (structured reply, no LLM) or any
    normal chat invokes ``acknowledge_patient_message``: timer cancelled,
    reminder row ``responded``.

If the timer fires:
  - Reminder marked ``missed``, missed turn logged to ``interaction_log``.
  - Optional POST to ``MISSED_REMINDER_ESCALATION_WEBHOOK_URL`` (e.g. service that SMSes
    via Twilio). We do not send SMS from this module.

Supersede: if a new reminder queues for the same patient before the window closes,
the prior row becomes ``superseded`` without caregiver escalation.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Literal

from memory.memory_manager import save_interaction
from scheduler.queries.reminders_write import insert_reminder_instance, update_reminder_status

logger = logging.getLogger(__name__)

RESPONSE_WINDOW_SEC = 300

ReminderKind = Literal["medication", "meal", "activity"]


@dataclass(frozen=True)
class AcknowledgedReminder:
    """Populated when a pending reminder window was cleared (explicit reply or any chat/voice turn)."""

    reminder_id: str | None
    reminder_type: ReminderKind
    item_label: str


@dataclass
class _PendingFollowup:
    timer: threading.Timer
    reminder_id: str | None
    reminder_type: ReminderKind
    item_label: str
    message: str


_pending_by_patient: dict[str, _PendingFollowup] = {}


# Cancels outbound window and marks the reminder row as responded.
def acknowledge_patient_message(patient_id: str) -> AcknowledgedReminder | None:
    pid = patient_id.strip()
    if not pid:
        return None
    pending = _pending_by_patient.pop(pid, None)
    if pending is None:
        return None
    pending.timer.cancel()
    update_reminder_status(pending.reminder_id, "responded")
    logger.info(
        "[reminder_delivery] Patient responded within window patient_id=%s reminder_id=%s",
        pid,
        pending.reminder_id,
    )
    return AcknowledgedReminder(
        reminder_id=pending.reminder_id,
        reminder_type=pending.reminder_type,
        item_label=pending.item_label,
    )


def _patient_webhook_post(patient_id: str, body: str) -> None:
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


def _post_missed_reminder_escalation(
    *,
    patient_id: str,
    reminder_kind: ReminderKind,
    item_label: str,
    reminder_id: str | None,
    detail_suffix: str,
) -> bool:
    """
    Notify an external service (e.g. Teammate 2) so they can SMS the caregiver via Twilio.
    Returns True if an HTTP POST was attempted and returned 2xx.
    """
    url = (os.getenv("MISSED_REMINDER_ESCALATION_WEBHOOK_URL") or "").strip()
    if not url:
        logger.info(
            "[reminder_delivery] MISSED_REMINDER_ESCALATION_WEBHOOK_URL unset; "
            "no missed-reminder escalation POST patient_id=%s",
            patient_id,
        )
        return False

    readable = {"medication": "medication", "meal": "meal", "activity": "activity"}[reminder_kind]
    summary = (
        f"No reply within {RESPONSE_WINDOW_SEC // 60} minutes after outbound {readable} "
        f"reminder for '{item_label}'."
    )
    payload_obj = {
        "event": "reminder_missed_no_reply",
        "patient_id": patient_id,
        "reminder_type": reminder_kind,
        "item_label": item_label,
        "reminder_id": reminder_id,
        "summary": summary.strip(),
        "detail": detail_suffix.strip()[:500],
    }
    payload = json.dumps(payload_obj).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            ok = 200 <= resp.status < 300
            if ok:
                logger.info("[reminder_delivery] Missed-reminder escalation POST ok patient_id=%s", patient_id)
            else:
                logger.error(
                    "[reminder_delivery] Escalation webhook HTTP %s patient_id=%s",
                    resp.status,
                    patient_id,
                )
            return ok
    except urllib.error.HTTPError as e:
        logger.error("[reminder_delivery] Escalation webhook failed patient_id=%s code=%s", patient_id, e.code)
        return False
    except Exception:
        logger.exception("[reminder_delivery] Escalation webhook error patient_id=%s", patient_id)
        return False


def _log_missed_interaction(
    *,
    patient_id: str,
    reminder_kind: ReminderKind,
    item_label: str,
    reminder_id: str | None,
    escalation_sent: bool,
) -> None:
    label = {"medication": "Medication", "meal": "Meal", "activity": "Activity"}[reminder_kind]
    tail = f" Reminder record: {reminder_id}." if reminder_id else ""
    follow = (
        " Escalation webhook delivered."
        if escalation_sent
        else " Escalation webhook not configured or failed."
    )
    save_interaction(
        patient_id=patient_id,
        user_text="[No patient reply within reminder follow-up window]",
        assistant_text=(
            f"System ({label.lower()} reminder): no timely response; recorded as missed "
            f"for '{item_label}'.{follow}{tail}"
        ),
        detected_intent="REMINDER_MISSED",
        confusion_flag=False,
    )


def _schedule_followup(
    pid: str,
    *,
    patient_message: str,
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
        posted = _post_missed_reminder_escalation(
            patient_id=pid,
            reminder_kind=reminder_kind,
            item_label=item_label,
            reminder_id=reminder_id,
            detail_suffix=detail_suffix,
        )
        _log_missed_interaction(
            patient_id=pid,
            reminder_kind=reminder_kind,
            item_label=item_label,
            reminder_id=reminder_id,
            escalation_sent=posted,
        )

    t = threading.Timer(RESPONSE_WINDOW_SEC, _fire)
    captured_timer_holder[0] = t
    t.daemon = True
    _pending_by_patient[pid] = _PendingFollowup(
        timer=t,
        reminder_id=reminder_id,
        reminder_type=reminder_kind,
        item_label=item_label,
        message=patient_message,
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
        patient_message=msg,
        reminder_id=reminder_id,
        reminder_kind=reminder_type,
        item_label=label,
        detail_suffix=detail,
    )


__all__ = [
    "AcknowledgedReminder",
    "RESPONSE_WINDOW_SEC",
    "ReminderKind",
    "acknowledge_patient_message",
    "deliver_reminder_to_patient",
]
