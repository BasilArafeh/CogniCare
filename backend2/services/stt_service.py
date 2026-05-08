import re

import requests
from fastapi import HTTPException, UploadFile, status

from core.config import settings

OPENAI_STT_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_TRANSLATE_URL = "https://api.openai.com/v1/audio/translations"


def is_stt_mock_mode() -> bool:
    return settings.SPEECH_MOCK_MODE.lower() == "true"


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
    if is_stt_mock_mode():
        return {
            "text": "Mock transcription result. Replace with real STT API when budget is available.",
            "language": "en",
        }

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty",
        )

    filename = file.filename or "speech_input.wav"
    mime_type = file.content_type or "audio/wav"

    spoken_language, raw_text = _detect_original_language_and_text(
        audio_bytes=audio_bytes,
        filename=filename,
        mime_type=mime_type,
    )

    # Final text sent to the agent must ALWAYS be English
    if spoken_language == "en":
        english_text = raw_text
    else:
        english_text = _translate_audio_to_english(
            audio_bytes=audio_bytes,
            filename=filename,
            mime_type=mime_type,
        )

    if not english_text:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="STT returned empty text",
        )

    return {
        "text": english_text,
        "language": spoken_language,
    }