import logging
import re

import requests
from fastapi import HTTPException, UploadFile, status

from core.config import settings

logger = logging.getLogger(__name__)

OPENAI_STT_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_TRANSLATE_URL = "https://api.openai.com/v1/audio/translations"


def is_stt_mock_mode() -> bool:
    import os
    val = os.getenv("SPEECH_MOCK_MODE", "false")
    return val.lower() == "true"


def _contains_arabic(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", text or ""))


def _openai_audio_request(
    url: str,
    audio_bytes: bytes,
    filename: str,
    mime_type: str | None,
    prompt: str | None = None,
    language_hint: str | None = None,
) -> dict:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing OPENAI_API_KEY in .env",
        )

    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
    }

    files = {
        "file": (filename, audio_bytes, mime_type or "application/octet-stream"),
    }

    data = {
        "model": "whisper-1",
        "response_format": "verbose_json",
    }

    if prompt:
        data["prompt"] = prompt

    if language_hint and url == OPENAI_STT_URL:
        data["language"] = language_hint

    response = requests.post(
        url,
        headers=headers,
        files=files,
        data=data,
        timeout=120,
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Whisper STT failed: {response.text}",
        )

    return response.json()


def _detect_original_language_and_text(
    audio_bytes: bytes,
    filename: str,
    mime_type: str | None,
) -> tuple[str, str]:
    """
    First pass:
    - detect the spoken language
    - get the raw transcript
    This pass is intentionally neutral and does NOT use the large prompt,
    because the prompt can bias language detection.
    """
    result = _openai_audio_request(
        url=OPENAI_STT_URL,
        audio_bytes=audio_bytes,
        filename=filename,
        mime_type=mime_type,
    )

    raw_text = (result.get("text") or "").strip()
    detected_language = (result.get("language") or "").strip().lower()

    # Fix false Arabic detections on English-only transcripts
    if detected_language == "ar" and not _contains_arabic(raw_text):
        detected_language = "en"

    # If language is missing or unclear, infer from transcript characters
    if not detected_language:
        detected_language = "ar" if _contains_arabic(raw_text) else "en"

    return detected_language, raw_text


def _translate_audio_to_english(
    audio_bytes: bytes,
    filename: str,
    mime_type: str | None,
) -> str:
    """
    Second pass:
    translate spoken non-English audio into English.
    """
    result = _openai_audio_request(
        url=OPENAI_TRANSLATE_URL,
        audio_bytes=audio_bytes,
        filename=filename,
        mime_type=mime_type,
    )

    english_text = (result.get("text") or "").strip()

    if not english_text:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Translation returned empty text",
        )

    return english_text


async def transcribe_audio_file(file: UploadFile) -> dict:
    logger.info("[STT] transcribe_audio_file called — filename=%s content_type=%s", file.filename, file.content_type)

    if is_stt_mock_mode():
        logger.info("[STT] mock mode active — returning canned response")
        return {
            "text": "Mock transcription result. Replace with real STT API when budget is available.",
            "language": "en",
        }

    audio_bytes = await file.read()
    logger.info("[STT] read %d bytes from upload", len(audio_bytes))

    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty",
        )

    filename = file.filename or "speech_input.wav"
    mime_type = file.content_type or "audio/wav"

    logger.info("[STT] sending to Whisper — filename=%s mime=%s", filename, mime_type)
    spoken_language, raw_text = _detect_original_language_and_text(
        audio_bytes=audio_bytes,
        filename=filename,
        mime_type=mime_type,
    )
    logger.info("[STT] Whisper detected language=%s raw_text=%r", spoken_language, raw_text)

    if spoken_language == "en":
        english_text = raw_text
    else:
        logger.info("[STT] non-English detected — translating to English")
        english_text = _translate_audio_to_english(
            audio_bytes=audio_bytes,
            filename=filename,
            mime_type=mime_type,
        )
        logger.info("[STT] translation result=%r", english_text)

    if not english_text:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="STT returned empty text",
        )

    return {
        "text": english_text,
        "original_text": raw_text,
        "language": spoken_language,
    }