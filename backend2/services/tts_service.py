import logging
import os
import re
import uuid

import requests
from fastapi import HTTPException, status

from core.config import settings

logger = logging.getLogger(__name__)

GENERATED_AUDIO_DIR = "generated_audio"
os.makedirs(GENERATED_AUDIO_DIR, exist_ok=True)


def normalize_language(language: str | None) -> str:
    if not language:
        return "en"

    language = language.strip().lower()

    if language.startswith("ar"):
        return "ar"

    return "en"


def get_voice_id_for_language(language: str) -> str:
    normalized = normalize_language(language)

    if normalized == "ar":
        voice_id = settings.ELEVENLABS_VOICE_ID_AR
        if not voice_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Missing ELEVENLABS_VOICE_ID_AR in .env",
            )
        return voice_id

    voice_id = settings.ELEVENLABS_VOICE_ID_EN
    if not voice_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing ELEVENLABS_VOICE_ID_EN in .env",
        )
    return voice_id


def remove_tts_file(file_path: str) -> None:
    if os.path.exists(file_path):
        os.remove(file_path)


def _clean_text(text: str) -> str:
    # Replace literal \n and actual newlines with a space
    t = text.replace("\\n", " ").replace("\n", " ")
    # Remove bullet dashes at line starts
    t = re.sub(r"(?m)^\s*[-•]\s+", " ", t)
    # Replace number ranges like ٤-٦ or 4-6 with "إلى"
    t = re.sub(r"([\d\u0660-\u0669])\s*-\s*([\d\u0660-\u0669])", r"\1 إلى \2", t)
    # Remove multiple spaces
    t = " ".join(t.split()).strip()
    if t and t[-1] not in ".!?":
        t += "."
    return t


def synthesize_speech(text: str, patient_id: int, language: str) -> str:
    _ = patient_id

    normalized_lang = normalize_language(language)
    cleaned_text = _clean_text(text)

    if not cleaned_text:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Text is empty after cleaning",
        )

    voice_id = get_voice_id_for_language(normalized_lang)
    logger.info("TTS voice_id=%s language=%s", voice_id, normalized_lang)

    if not settings.ELEVENLABS_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing ELEVENLABS_API_KEY in .env",
        )

    url = (
        f"https://api.elevenlabs.io/v1/text-to-speech/"
        f"{voice_id}/stream?output_format=mp3_44100_128"
    )
    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": cleaned_text,
        "model_id": "eleven_multilingual_v2" if normalized_lang == "ar" else "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.35,
            "similarity_boost": 0.90,
            "style": 0.35,
            "use_speaker_boost": True,
            "speed": 1.05,
        },
    }

    response = requests.post(url, headers=headers, json=payload, timeout=120, stream=True)

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"ElevenLabs TTS failed ({response.status_code}): {response.text[:800]}",
        )

    output_path = os.path.join(GENERATED_AUDIO_DIR, f"{uuid.uuid4()}.mp3")
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=4096):
            if chunk:
                f.write(chunk)

    return output_path
