"""Shared outbound integrations (Twilio, etc.)."""

from integrations.twilio_sms import deliver_sms

__all__ = ["deliver_sms"]
