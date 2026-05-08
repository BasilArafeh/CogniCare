from fastapi import APIRouter, Form, Response
from twilio.twiml.messaging_response import MessagingResponse

from services.twilio_service import (
    handle_incoming_caregiver_reply,
    record_twilio_status_callback,
)

router = APIRouter(prefix="/webhooks/twilio", tags=["twilio-webhooks"])


@router.post("/incoming")
def twilio_incoming_webhook(
    from_number: str = Form(..., alias="From"),
    to_number: str = Form(..., alias="To"),
    body: str = Form("", alias="Body"),
):
    reply_text = handle_incoming_caregiver_reply(
        from_number=from_number,
        to_number=to_number,
        body=body,
    )

    twiml = MessagingResponse()
    twiml.message(reply_text)

    return Response(
        content=str(twiml),
        media_type="application/xml",
    )


@router.post("/status")
def twilio_status_webhook(
    message_sid: str = Form(..., alias="MessageSid"),
    message_status: str = Form(..., alias="MessageStatus"),
    to_number: str | None = Form(None, alias="To"),
    error_code: str | None = Form(None, alias="ErrorCode"),
):
    record_twilio_status_callback(
        message_sid=message_sid,
        message_status=message_status,
        to_number=to_number,
        error_code=error_code,
    )
    return {"ok": True}