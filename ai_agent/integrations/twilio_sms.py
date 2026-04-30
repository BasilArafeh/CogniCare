"""
Twilio outbound SMS — single entry point used by orchestration / emergency escalation.

Reads env:
  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, and the destination `to`.
"""

from __future__ import annotations

import base64
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)


def deliver_sms(*, to_phone: str, body: str) -> bool:
    """
    Sends one SMS via Twilio REST. Prefer replacing this body's implementation with your
    existing Twilio client if the project uses the official SDK elsewhere.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()

    if not account_sid or not auth_token:
        logger.warning("[twilio_sms] Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN")
        return False
    if not from_number:
        logger.warning("[twilio_sms] Missing TWILIO_FROM_NUMBER")
        return False
    if not to_phone.strip():
        logger.warning("[twilio_sms] Empty destination phone")
        return False

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    payload = urllib.parse.urlencode(
        {"To": to_phone.strip(), "From": from_number, "Body": body}
    ).encode()
    credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()

    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            ok = 200 <= resp.status < 300
            if ok:
                logger.info("[twilio_sms] Message accepted status=%s", resp.status)
            return ok
    except urllib.error.HTTPError:
        logger.exception("[twilio_sms] Twilio HTTP error")
        return False
    except Exception:
        logger.exception("[twilio_sms] Twilio request failed")
        return False


__all__ = ["deliver_sms"]
