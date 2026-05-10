"""
Speech-to-text for backend2: transcribes patient audio with OpenAI, normalizes language,
and translates Arabic transcripts to English for downstream agent / RAG use.
"""

import logging

import requests
from fastapi import HTTPException, UploadFile, status

from core.config import settings

logger = logging.getLogger(__name__)

OPENAI_STT_URL = "https://api.openai.com/v1/audio/transcriptions"

STT_PROMPT = (
    "Alzheimer's, dementia, caregiver, medication, dosage, "
    "Donepezil, Memantine, Panadol, appointment, reminder, "
    "breakfast, lunch, dinner, activity"
)


# Calls OpenAI audio transcription; JSON response includes {"text": "..."} only.
def _transcribe(audio_bytes: bytes, filename: str, mime_type: str) -> dict:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OPENAI_API_KEY is not configured",
        )

    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
    files = {"file": (filename, audio_bytes, mime_type)}
    data = {
        "model": "gpt-4o-transcribe",
        "response_format": "json",
        "prompt": STT_PROMPT,
    }

    resp = requests.post(OPENAI_STT_URL, headers=headers, files=files, data=data, timeout=120)

    if resp.status_code != 200:
        logger.error("OpenAI transcription failed: %s", resp.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI transcription failed ({resp.status_code}): {resp.text[:800]}",
        )

    try:
        return resp.json()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenAI transcription returned invalid JSON",
        )


def _detect_language(text: str) -> str:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OPENAI_API_KEY is not configured",
        )

    stripped = text.strip()
    if not stripped:
        return "en"

    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Detect the language of the following text. Reply with only 'ar' if Arabic "
                    "or 'en' if English. Nothing else."
                ),
            },
            {"role": "user", "content": stripped},
        ],
        "temperature": 0.1,
    }

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )
    except requests.RequestException:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenAI language detection request failed",
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI language detection failed ({resp.status_code}): {resp.text[:800]}",
        )

    try:
        body = resp.json()
        content = (
            body.get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )
    except (TypeError, IndexError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenAI language detection returned an unexpected response",
        )

    if content is None or not str(content).strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenAI language detection returned empty content",
        )

    reply = str(content).strip().lower()
    return "ar" if reply.startswith("ar") else "en"


# Uses chat completions to translate Arabic text into English only.
def _translate(text: str) -> str:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OPENAI_API_KEY is not configured",
        )

    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a translator. Translate the given Arabic text to English. "
                    "Return only the translated text, nothing else."
                ),
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0.2,
    }

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )
    except requests.RequestException:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenAI translation request failed",
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI translation failed ({resp.status_code}): {resp.text[:800]}",
        )

    try:
        body = resp.json()
        content = (
            body.get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )
    except (TypeError, IndexError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenAI translation returned an unexpected response",
        )

    if content is None or not str(content).strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenAI translation returned empty content",
        )

    return str(content).strip()


# End-to-end: upload → transcribe → optional Arabic→English → { text, language }.
async def transcribe(file: UploadFile) -> dict:
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty",
        )

    filename = file.filename or "audio.wav"
    mime_type = file.content_type or "audio/wav"

    decoded = _transcribe(audio_bytes, filename, mime_type)
    raw_text = (decoded.get("text") or "").strip()

    language = _detect_language(raw_text)

    if language == "en":
        english_text = raw_text
    else:
        english_text = _translate(raw_text)

    if not english_text:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Transcription produced empty English text",
        )

    return {"text": english_text, "language": language}
